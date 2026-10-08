#!/usr/bin/env python3
"""Generate FujiNet-SMS-Rev0.kicad_pcb (placed, unrouted) from design.py.

Board (KiCad frame, mm, y down): a 100 mm wide body (x 50..150, y Y0..110)
on a 65.8 mm connector tab (x 67.1..132.9, y 110..125); y = 125 is the
insertion edge.  The tab is the original Sega board's full width (65.8-66.0
measured) and carries the 50 fingers (tools/make_edge_fp.py); it stays that
narrow for its first 15 mm, where the original shell's cross-rib and the
console's connector housing are (case/case-spec.md, VERIFY), and the body
widens to 100 mm above it, inside the taller custom shell.  1.6 mm, 6 copper
layers (the NES Rev0 stack):
  F.Cu  signals + GND pour       (component side: even fingers, faces the label)
  In1   GND plane
  In2   signals
  In3   signals
  In4   +3V3 plane (the north band: S3, microSD, USB bridge, buck output) with
        a +5V island over the rest (console 5V, SRAMs, glue, LDO input), a
        +3V3_RP island under the RP2354B ring and a DVDD island under its core
  B.Cu  signals + GND pour       (odd fingers)
The fingers are the only copper on the tab; each gets a short locked stub
into the body so the routers never enter the tab.  The ESP32-S3 antenna sits
flush with the top edge over the module footprint's own keep-out (all layers).

Footprints are written as S-expressions (the SWIG pcbnew bindings are not
reliable under Python 3.14); route.py does the DSN/SES round trip and the
zone fills through pcbnew.  Net names come from the schematic's netlist
(hierarchical: /A0, /rp2354b/XIN, GND); NET() maps design.py's name to it.

Usage: python3 tools/gen_pcb.py
"""
import os, sys, math, copy, json, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
from tmpdir import tmp
import design as D
import gen_sch

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
K = D.KEY

# ---- geometry (mm, KiCad frame: y down) -----------------------------------
import edge_geom as EG
import placement as PL          # the floorplan owns the body height, holes and In4 split
XC = 100.0
X0, X1 = XC - EG.BODY_W / 2, XC + EG.BODY_W / 2     # body width 100
Y1 = 125.0                      # insertion edge
TAB_D = EG.TAB_D                # tab depth 15 (edge_geom)
TAB_Y = Y1 - TAB_D              # 110: tab base = bottom of the body
Y0 = TAB_Y - PL.BODY_H          # top (trailing) edge: USB-C, microSD, the S3 antenna
TAB_HW = EG.TAB_W / 2           # 65.8 mm tab
TAB_X0, TAB_X1 = XC - TAB_HW, XC + TAB_HW
PAD_TOP_Y = Y1 - EG.LAND_Y1     # 115.5: finger copper starts here
BLADE_Y = TAB_Y                 # routers: no tracks/vias at y >= BLADE_Y
THICKNESS = EG.THICKNESS
CH_TOP, CH_SH, CH_TAB = 2.0, 1.0, EG.CH_TAB      # corner chamfers: top corners, shoulders, insertion edge
OUTLINE = [(X0 + CH_TOP, Y0), (X1 - CH_TOP, Y0), (X1, Y0 + CH_TOP),
           (X1, TAB_Y - CH_SH), (X1 - CH_SH, TAB_Y), (TAB_X1, TAB_Y),
           (TAB_X1, Y1 - CH_TAB), (TAB_X1 - CH_TAB, Y1), (TAB_X0 + CH_TAB, Y1), (TAB_X0, Y1 - CH_TAB),
           (TAB_X0, TAB_Y), (X0 + CH_SH, TAB_Y), (X0, TAB_Y - CH_SH), (X0, Y0 + CH_TOP)]
BODY = [(X0, Y0), (X1, Y0), (X1, TAB_Y), (X0, TAB_Y)]   # planes / pours (clipped by the outline)
# M3 clearance holes for the shell's four screws (case/FujiNet-SMS-Shell.scad reads them from
# case/board-anchors.scad): (x, y, diameter); placement.py keeps parts off their 3 mm rings
HOLES = [(x, Y0 + dy if dy >= 0 else TAB_Y + dy, d) for x, dy, d in PL.HOLES]
HOLE_KEEP = 3.0                 # radius around a hole with no parts (screw head / boss)
PLANE_SPLIT_Y = PL.PLANE_SPLIT_Y    # In4: +3V3 north of this, +5V south (islands win over both)

# In4 islands, in priority order (highest wins)
RP_ISLAND = 14.0    # half-size of the +3V3_RP island under the RP2354B decoupling ring
RP_CORE = 3.6       # west edge of the DVDD island under the RP2354B core (the VREG_VIN via sits beyond it)
DVDD_R = 4.3        # its north/east/south extent: past the DVDD pins' inward vias (4.0 + 0.25 barrel)
UNDER = 4.6         # half-size of the square under the RP the finisher keeps off F.Cu (and via-free)

# ref -> (x, y, rotation deg CCW)  -- top view, y down
PLACE = {}


def place(key, x, y, rot=0):
    """placement.py names parts by design.py key; PLACE is by reference."""
    PLACE[K[key]] = (round(x, 4), round(y, 4), rot % 360)


def uid(*k):
    return gen_sch.uid('pcb', *k)


# ---------------------------------------------------------------------------
def rot_pt(x, y, a):
    r = math.radians(a)
    # KiCad: positive angle = CCW on screen (y down) -> x' = x cos + y sin, y' = -x sin + y cos
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


def load_fp(name):
    return parse(open(os.path.join(PRJ, D.LIB + '.pretty', name + '.kicad_mod')).read())


def canon(n):
    return n if n.startswith('unconnected') else n.rsplit('/', 1)[-1]


NETLIST = {}    # (ref, pad) -> the schematic's net name
FULL = {}       # design.py net name -> the schematic's (board's) net name
COMP_SHEET = {} # ref -> the sheet name kicad-cli files the component under ('/glue/')


def schematic_netlist():
    """(ref, pad) -> net name, from the generated schematic (kicad-cli), so the
    board carries exactly the schematic's nets -- including KiCad's own
    unconnected-(...) names for no-connect pins."""
    fn = tmp('gen.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    t = parse(open(fn).read())
    out, full = {}, {}
    for c in findall(find(t, 'components'), 'comp'):
        COMP_SHEET[str(find(c, 'ref')[1])] = str(find(find(c, 'sheetpath'), 'names')[1])
    for n in findall(find(t, 'nets'), 'net'):
        name = str(find(n, 'name')[1])
        full[canon(name)] = name
        for nd in findall(n, 'node'):
            out[(str(find(nd, 'ref')[1]), str(find(nd, 'pin')[1]))] = name
    return out, full


def NET(n):
    """design.py's net name -> the board's."""
    if not FULL:
        nl, full = schematic_netlist()
        NETLIST.update(nl)
        FULL.update(full)
    return FULL[n]


SMALL = re.compile(r'_0603_|_0805_|SOD-523|SOT-23|SOT-363|R_Array|AOTA|Crystal_SMD|WS2812|TSOT|TestPoint')


def instance(part, x, y, rot, path, sheetname, sheetfile, datasheet=''):
    fp = load_fp(part.footprint.split(':')[1])
    for i, e in enumerate(fp):   # legacy (fp_text reference/value ...) -> (property ...)
        if isinstance(e, list) and e and e[0] == 'fp_text' and e[1] in ('reference', 'value'):
            fp[i] = ['property', Q('Reference' if e[1] == 'reference' else 'Value'), e[2]] + e[3:]
    out = ['footprint', Q(part.footprint), ['layer', Q('F.Cu')], ['uuid', uid(part.ref)],
           ['at', x, y, rot] if rot else ['at', x, y]]
    for k in ('descr', 'tags'):
        e = find(fp, k)
        if e:
            out.append(e)
    fields = {'Reference': part.ref, 'Value': part.value, 'Footprint': part.footprint,
              'Datasheet': datasheet, 'Description': part.desc, 'MPN': part.mpn, 'Manufacturer': part.mfr,
              'LCSC': part.lcsc}
    done = set()
    for pr in findall(fp, 'property'):
        k = pr[1]
        if k in fields:
            pr = copy.deepcopy(pr)
            pr[2] = Q(fields[k])
            at = find(pr, 'at')
            ang = (float(at[3]) if len(at) > 3 else 0) + rot
            at[:] = ['at', float(at[1]), float(at[2]), ang % 360]
            pr = [e for e in pr if not (isinstance(e, list) and e and e[0] == 'uuid')]
            pr.insert(3, ['uuid', uid(part.ref, 'prop', k)])
            if k == 'Reference' and SMALL.search(part.footprint):
                pr = [e for e in pr if not (isinstance(e, list) and e and e[0] == 'effects')]
                pr.append(['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]]])
            out.append(pr); done.add(k)
    for k, v in fields.items():
        if k not in done and (v or k not in ('MPN', 'Manufacturer', 'LCSC')):
            out.append(['property', Q(k), Q(v), ['at', 0, 0, rot], ['layer', Q('F.Fab')], ['hide', 'yes'],
                        ['uuid', uid(part.ref, 'prop', k)],
                        ['effects', ['font', ['size', 1.27, 1.27], ['thickness', 0.15]]]])
    out += [['path', Q(path)], ['sheetname', Q(sheetname)], ['sheetfile', Q(sheetfile)]]
    attr = find(fp, 'attr')
    a = list(attr) if attr else ['attr', 'smd']
    if not part.bom and 'exclude_from_bom' not in a:
        a.append('exclude_from_bom')
    if getattr(part, 'dnp', False) and 'dnp' not in a:
        a.append('dnp')
    out.append(a)
    for e in fp[2:]:
        if not isinstance(e, list) or not e:
            continue
        if e[0] in ('version', 'generator', 'generator_version', 'layer', 'descr', 'tags', 'property',
                    'attr', 'uuid', 'embedded_fonts'):
            continue
        if e[0] == 'fp_text':
            e = copy.deepcopy(e)
            at = find(e, 'at')
            ang = (float(at[3]) if len(at) > 3 else 0) + rot
            at[:] = ['at', float(at[1]), float(at[2]), ang % 360]
            if e[2] == '%R':
                e[2] = Q('${REFERENCE}')
            out.append(e)
        elif e[0] == 'pad':
            e = copy.deepcopy(e)
            at = find(e, 'at')
            ang = (float(at[3]) if len(at) > 3 else 0) + rot
            at[:] = ['at', float(at[1]), float(at[2])] + ([ang % 360] if ang % 360 else [])
            e = [x_ for x_ in e if not (isinstance(x_, list) and x_ and x_[0] in ('net', 'uuid'))]
            num = str(e[1])
            net = part.pins.get(num)
            if num and num not in part.pins and e[2] != 'np_thru_hole':
                raise SystemExit('%s pad %s has no pin in design.py' % (part.ref, num))
            if num and part.pins:
                sn = NETLIST.get((part.ref, num))
                if net and (sn is None or canon(sn) != net):
                    raise SystemExit('%s pad %s: design %s vs schematic %s' % (part.ref, num, net, sn))
                net = sn
            if net:
                e.append(['net', Q(net)])
            e.append(['uuid', uid(part.ref, 'pad', num, len(out))])
            out.append(e)
        elif e[0] == 'zone':  # footprint zones are stored in board coordinates
            e = copy.deepcopy(e)
            for pts in findall(find(e, 'polygon'), 'pts'):
                for xy in pts[1:]:
                    dx, dy = rot_pt(float(xy[1]), float(xy[2]), rot)
                    xy[1], xy[2] = round(x + dx, 4), round(y + dy, 4)
            # the S3 antenna keep-out lists In1..In30: keep the layers this stack has
            lay = find(e, 'layers')
            if lay:
                lay[1:] = [l for l in lay[1:] if str(l) in COPPER]
            out.append(e)
        else:
            out.append(copy.deepcopy(e))
    out.append(['embedded_fonts', 'no'])
    return out


COPPER = ('F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu')


def board_only(name, fpname, x, y, desc):
    """A board-only footprint (fiducial, mounting hole): not in the schematic, BOM or CPL."""
    fp = load_fp(fpname)
    for i, e in enumerate(fp):
        if isinstance(e, list) and e and e[0] == 'fp_text' and e[1] in ('reference', 'value'):
            fp[i] = ['property', Q('Reference' if e[1] == 'reference' else 'Value'), e[2]] + e[3:]
    inst = ['footprint', Q(D.LIB + ':' + fpname), ['layer', Q('F.Cu')], ['uuid', uid(name)], ['at', x, y]]
    for e in fp[2:]:
        if not isinstance(e, list) or not e or e[0] in ('version', 'generator', 'generator_version', 'layer',
                                                        'embedded_fonts'):
            continue
        e = copy.deepcopy(e)
        if e[0] == 'property':
            if e[1] == 'Reference':
                e[2] = Q(name)
            if e[1] == 'Description':
                e[2] = Q(desc)
            e = [x_ for x_ in e if not (isinstance(x_, list) and x_ and x_[0] == 'uuid')]
            e.insert(3, ['uuid', uid(name, 'prop', e[1])])
        elif e[0] == 'pad':
            e = [x_ for x_ in e if not (isinstance(x_, list) and x_ and x_[0] == 'uuid')]
            e.append(['uuid', uid(name, 'pad', e[1])])
        inst.append(e)
    inst.append(['embedded_fonts', 'no'])
    return inst


def board_pads(board):
    """fanout.Pad list (absolute coordinates) + courtyard boxes by ref."""
    import fanout
    pads, crt = [], {}
    for fp in board:
        if not (isinstance(fp, list) and fp and fp[0] == 'footprint'):
            continue
        at = find(fp, 'at')
        fx, fy = float(at[1]), float(at[2])
        rot = float(at[3]) if len(at) > 3 else 0.0
        ref = [str(e[2]) for e in findall(fp, 'property') if e[1] == 'Reference'][0]
        xs, ys = [], []
        for g in fp:
            if isinstance(g, list) and g and g[0] in ('fp_rect', 'fp_line') and find(g, 'layer')[1] == 'F.CrtYd':
                for k in ('start', 'end'):
                    q = find(g, k)
                    dx, dy = rot_pt(float(q[1]), float(q[2]), rot)
                    xs.append(fx + dx); ys.append(fy + dy)
            elif isinstance(g, list) and g and g[0] == 'fp_circle' and find(g, 'layer')[1] == 'F.CrtYd':
                c, e_ = find(g, 'center'), find(g, 'end')
                cx_, cy_ = rot_pt(float(c[1]), float(c[2]), rot)
                rr = math.hypot(float(e_[1]) - float(c[1]), float(e_[2]) - float(c[2]))
                xs += [fx + cx_ - rr, fx + cx_ + rr]; ys += [fy + cy_ - rr, fy + cy_ + rr]
        if xs:
            crt[ref] = (min(xs), min(ys), max(xs), max(ys))
        for e in findall(fp, 'pad'):
            pat = find(e, 'at'); sz = find(e, 'size')
            dx, dy = rot_pt(float(pat[1]), float(pat[2]), rot)
            pang = (float(pat[3]) if len(pat) > 3 else 0.0) % 180
            w, h = float(sz[1]), float(sz[2])
            if abs(pang - 90) < 1:
                w, h = h, w
            elif pang not in (0.0,):
                w = h = max(w, h)
            net = find(e, 'net')
            layers = [str(x_) for x_ in find(e, 'layers')[1:]]
            th = e[2] in ('thru_hole', 'np_thru_hole')
            if th:
                layers = ['F.Cu', 'B.Cu']
            pads.append(fanout.Pad(ref, str(e[1]), str(net[1]) if net else None, fx + dx, fy + dy,
                                   w / 2, h / 2, layers, th, (fx, fy)))
    return pads, crt


# ---------------------------------------------------------------------------
def seg(x0, y0, x1, y1, w, layer, net, key, locked=True):
    s = ['segment', ['start', round(x0, 4), round(y0, 4)], ['end', round(x1, 4), round(y1, 4)],
         ['width', w], ['layer', Q(layer)]]
    if locked:
        s.append(['locked', 'yes'])
    return s + [['net', Q(net)], ['uuid', uid(*key)]]


def via(x, y, net, key, size=0.6, drill=0.3):
    return ['via', ['at', round(x, 4), round(y, 4)], ['size', size], ['drill', drill],
            ['layers', Q('F.Cu'), Q('B.Cu')], ['locked', 'yes'], ['net', Q(net)], ['uuid', uid(*key)]]


def footprint_of(board, ref):
    return [e for e in board if isinstance(e, list) and e and e[0] == 'footprint'
            and any(p[1] == 'Reference' and p[2] == ref for p in findall(e, 'property'))][0]


def finger_stubs(board):
    """Each finger gets a locked stub on its own face from 0.2 mm inside its
    inner end up into the body (y = TAB_Y - 1.0), so the routers only ever
    touch the stub end; the tab itself is a track/via keepout.  The GND
    fingers (19, 20, 21) get a via at the stub end into the In1 plane; the
    console +5V fingers (1, 35) a 0.6 mm stub."""
    out = []
    j1 = footprint_of(board, K['J_EDGE'])
    fx = float(find(j1, 'at')[1])      # the edge sits at rotation 0: pad x is footprint x + local x
    col = {}                            # finger x -> the nets on its two faces
    for pd in findall(j1, 'pad'):
        net = find(pd, 'net')
        col.setdefault(round(fx + float(find(pd, 'at')[1]), 4), []).append(str(net[1]) if net else None)
    gnd_vias = set()
    for pd in findall(j1, 'pad'):
        a = find(pd, 'at'); net = find(pd, 'net')
        if not net or str(net[1]).startswith('unconnected-'):   # unused finger: no stub to dangle
            continue
        net = str(net[1])
        layer = str(find(pd, 'layers')[1])
        x = round(fx + float(a[1]), 4)
        w = 0.6 if net == NET('CONS_5V') else 0.3
        y = TAB_Y - 1.0
        out.append(seg(x, PAD_TOP_Y + 0.2, x, y, w, layer, net, ('fstub', str(pd[1]))))
        if net == 'GND':
            # a via on the stub end would hit the other face's stub unless that is GND too:
            # then jog half a pitch toward the all-GND column first (between the columns)
            vx = x
            if any(n != 'GND' for n in col[x]):
                gx = min((c for c, ns in col.items() if all(n == 'GND' for n in ns)), key=lambda c: abs(c - x))
                vx = round(x + math.copysign(1.27, gx - x), 4)
                out.append(seg(x, y, vx, y, 0.3, layer, net, ('fgndj', str(pd[1]))))
            if vx not in gnd_vias:
                gnd_vias.add(vx)
                out.append(via(vx, y, 'GND', ('fgnd', vx)))
    return out


def sram0_fanin(board):
    """SRAM0 in the classic ROM spot (placement.ROM_X / ROM_Y, rotation 270, pins 17-32 toward the
    fingers): the edge is the JEDEC 32-pin memory pinout unrolled, so its console lines reach the
    SRAM on F.Cu without one crossing.  Drawn here, locked, before any router runs:
      * the funnel: A3..A0, D0..D7, A10 (+ VSS) from the finger stubs straight into the pin 17-32
        row -- each line vertical, one 45-degree run (all parallel), vertical into its pad; a
        B.Cu finger first jogs half a pitch east on B.Cu to a via (east: the SRAM wants every B
        finger after its F.Cu partner);
      * the west wrap: A4 A5 A6 A7 A12 round the SRAM's south-west corner, up its west side and
        into pins 16..12 from the north (innermost = nearest the corner);
      * the east wrap: A11 A9 A8 the same way round the east side into pins 1..3;
      * the two pins trapped inside the fan, CE# (pin 30, SA19) and OE# (pin 32), on a short
        diagonal to a via each (their nets come from the RP / the glue on the inner layers).
    Pins 4-11 (SA13-SA18, WE#, VCC) stay open to the north for the routers / fan-out."""
    import placement as PL
    W, PITCH_W, VD, VDR = 0.2, 0.5, 0.6, 0.3
    out = []
    j1 = footprint_of(board, K['J_EDGE'])
    fx = float(find(j1, 'at')[1])
    finger = {}                                   # net -> (x, face)
    for pd in findall(j1, 'pad'):
        n = find(pd, 'net')
        if n:
            finger.setdefault(str(n[1]), (round(fx + float(find(pd, 'at')[1]), 4), str(find(pd, 'layers')[1])[0]))
    u = footprint_of(board, K['U_SRAM0'])
    at = find(u, 'at')
    ux, uy, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
    assert rot == 270, 'sram0_fanin is drawn for the SRAM at rotation 270'
    pin = {}                                      # pad -> (x, y, net, end_y) ; end_y = the pad's outer end
    for pd in findall(u, 'pad'):
        a = find(pd, 'at')
        dx, dy = rot_pt(float(a[1]), float(a[2]), rot)
        n = find(pd, 'net')
        sz = find(pd, 'size')
        half = max(float(sz[1]), float(sz[2])) / 2
        x, y = round(ux + dx, 4), round(uy + dy, 4)
        pin[int(pd[1])] = (x, y, str(n[1]) if n else None, y + half if y > uy else y - half)
    ystub = TAB_Y - 1.0                           # where finger_stubs ends every stub
    y0 = ystub - 0.3                              # every funnel line's 45-degree run starts here
    seg_ = lambda pts, net, key: [seg(a[0], a[1], b[0], b[1], W, 'F.Cu', net, (key, i))
                                  for i, (a, b) in enumerate(zip(pts, pts[1:])) if a != b]

    def start(net, key):
        """The F.Cu start of a finger's line: its stub top, or (B.Cu finger) a via half a pitch east."""
        x, face = finger[net]
        if face == 'F':
            return x
        xv = round(x + EG.PITCH / 2, 4)
        out.append(seg(x, ystub, xv, ystub, 0.3, 'B.Cu', net, (key, 'jog')))
        out.append(via(xv, ystub, net, (key, 'via'), VD, VDR))
        return xv
    xs_of = {}
    # the east wrap's innermost line (A11, pin 1) starts here: the OE# via sits west of its run
    xs_of['A11'] = finger[pin[1][2]][0] if finger[pin[1][2]][1] == 'F' else finger[pin[1][2]][0] + EG.PITCH / 2
    # ---- the funnel: pins 17..32 (south row) ----
    for k in range(17, 33):
        x_p, _, net, y_end = pin[k]
        if net is None or net not in finger or net == 'GND':
            continue
        x_s = start(net, 'sf%d' % k)
        xs_of[k] = xs_of[net] = x_s
        d = abs(x_p - x_s)
        assert y0 - d > y_end + 0.1, 'SRAM0 too low for the fan-in of pin %d (%.2f mm short)' % (k, y_end + 0.1 - (y0 - d))
        out += seg_([(x_s, ystub), (x_s, y0), (x_p, y0 - d), (x_p, y_end)], net, 'sf%d' % k)
    # VSS (pin 24) straight down onto the via finger_stubs puts at the all-GND finger column
    x_p, _, net, y_end = pin[24]
    cols = {}
    for pd in findall(j1, 'pad'):
        n = find(pd, 'net')
        cols.setdefault(round(fx + float(find(pd, 'at')[1]), 4), set()).add(str(n[1]) if n else None)
    gx = min((x for x, ns in cols.items() if ns == {'GND'}), key=lambda x: abs(x - x_p))
    out += seg_([(x_p, y_end), (x_p, round(ystub - abs(gx - x_p), 4)), (gx, ystub)], 'GND', 'sfvss')
    # ---- the two trapped pins, each to a via between its neighbours' 45-degree runs ----
    # a funnel line east of its pin runs x - y = c (c = its start x - y0) once diagonal
    c_of = lambda k: (xs_of[k] - y0)
    cw = xs_of['A11'] - ystub                       # the east wrap's innermost run (x - y = cw)
    # CE# (pin 30, SA19): down its own column to the midline between D7 (29) and A10 (31), along it
    x_p, _, net, y_end = pin[30]
    if net:
        c = (c_of(29) + c_of(31)) / 2
        yv = round(y0 - abs(pin[29][0] - xs_of[29]) + 1.5, 4)      # below D7's bend: both runs diagonal
        pts = [(x_p, y_end), (x_p, round(x_p - c, 4)), (round(yv + c, 4), yv)]
        out += seg_(pts, net, 'sfx30')
        out.append(via(pts[-1][0], yv, net, ('sfxv', 30), VD, VDR))
    # OE# (pin 32): east along its pad end to the midline between A10 (31) and the east wrap, down it
    x_p, _, net, y_end = pin[32]
    if net:
        c = max((c_of(31) + cw) / 2, x_p - y_end)   # the midline, or straight off the pad end if that is east of it
        yv = round(y_end + 2.0, 4)
        pts = [(x_p, y_end), (round(c + y_end, 4), y_end), (round(yv + c, 4), yv)]
        out += seg_(pts, net, 'sfx32')
        out.append(via(pts[-1][0], yv, net, ('sfxv', 32), VD, VDR))
    # ---- the wraps: round the corners into the north row ----
    body_w = 8.0
    for side, pins_in in (('W', (16, 15, 14, 13, 12)), ('E', (1, 2, 3))):
        for i, k in enumerate(pins_in):             # innermost first
            x_p, _, net, y_end = pin[k]
            x_s = start(net, 'sw%d' % k)
            if side == 'W':
                xc = ux - body_w / 2 - 0.22 - PITCH_W * i          # side column, west of the body
                ydiag = (x_s + ystub) - xc                          # x + y = const up-right
            else:
                xc = ux + body_w / 2 + 0.98 + PITCH_W * i          # east of the body (OE#'s via south of it)
                ydiag = xc - (x_s - ystub)                          # x - y = const up-left
            yt = round(y_end - 0.6 - PITCH_W * i, 4)                # turn-in height, north of the row
            out += seg_([(x_s, ystub), (round(xc, 4), round(ydiag, 4)), (round(xc, 4), yt), (x_p, yt),
                         (x_p, y_end)], net, 'sw%d' % k)
    return out


def rp_support(board, ux, uy):
    """Locked copper the RP2354B needs regardless of routing (the NES Rev0
    arrangement, same package, same rotation):
      * each DVDD pin (10, 32, 51, 65 = VREG_FB) gets a stub inward to a via
        under the package; those vias meet on a DVDD island in the In4 plane,
        which also reaches west under the core inductor and its capacitor
      * a +3V3_RP island on In4 under the whole decoupling ring, so every
        IOVDD-group pin and its 100 nF reach the LDO rail through one via
      * the exposed pad's GND via grid is left to fanout.py (EP_ARRAYS)"""
    out = []
    u1 = footprint_of(board, K['U_RP'])
    at = find(u1, 'at'); rot = float(at[3]) if len(at) > 3 else 0.0
    for pd in findall(u1, 'pad'):
        n = find(pd, 'net')
        if not n or pd[2] != 'smd':
            continue
        net, num = str(n[1]), str(pd[1])
        a = find(pd, 'at')
        px, py = float(a[1]), float(a[2])
        dx, dy = rot_pt(px, py, rot)
        if net == 'DVDD':
            r_in = 4.0     # via radius from the centre: just inside the pad ring (4.55), clear of the EP's
            # fan-out stubs (which cut diagonally toward the exposed pad) and of the EP itself (1.7)
            if abs(dx) > abs(dy):
                vx, vy = math.copysign(r_in, dx), dy
            else:
                vx, vy = dx, math.copysign(r_in, dy)
            if num == '65':       # VREG_FB: further in, so its VREG_VIN neighbour's via fits beside it
                vx, vy = math.copysign(2.8, dx), dy
            pts = [(dx, dy), (vx, vy)]
        elif net == '+3V3_RP' and num == '64':
            # VREG_VIN sits between LX (63) and FB (65), both of which leave along their own
            # axis: it reaches the island through a dog-leg stub and a via under the package
            vx, vy = math.copysign(4.0, dx), dy + math.copysign(0.2, dy)
            pts = [(dx, dy), (math.copysign(4.55, dx), dy), (vx, vy)]
        elif net == 'GND' and num == '62':
            # VREG_PGND: straight in to its own via on the GND plane (its exposed-pad stub
            # would cut through the VREG_VIN via)
            vx, vy = math.copysign(2.6, dx), dy
            pts = [(dx, dy), (vx, vy)]
        else:
            continue
        for i in range(len(pts) - 1):
            (x0_, y0_), (x1_, y1_) = pts[i], pts[i + 1]
            out.append(seg(ux + x0_, uy + y0_, ux + x1_, uy + y1_, 0.2, 'F.Cu', net, ('rpdv', num, i)))
        out.append(via(ux + vx, uy + vy, net, ('rpdvv', num), 0.5, 0.25))
    out.append(zone('rp_dvdd_island', 'DVDD', 'In4.Cu', [(ux + x, uy + y) for x, y in dvdd_island()], priority=5))
    out.append(zone('rp_io_island', '+3V3_RP', 'In4.Cu',
                    [(ux - RP_ISLAND, uy - RP_ISLAND), (ux + RP_ISLAND, uy - RP_ISLAND),
                     (ux + RP_ISLAND, uy + RP_ISLAND), (ux - RP_ISLAND, uy + RP_ISLAND)], priority=3))
    return out


def dvdd_island():
    """The DVDD island on In4, relative to the RP2354B centre (y down): the core under the
    package out to DVDD_R, which covers the DVDD pins' inward vias (rp_support: centre
    4.0, 0.5 mm barrel), the strip under the north pin row, and a lobe west under L1 /
    the DVDD capacitors (placement.RP_MACRO keeps them there).  The notch west of the core
    (x -5.0..-3.6, y > -4.0) stays +3V3_RP for the VREG_VIN via at (-4.0, -2.8).  Drawn for
    the RP at rotation 90; turned with the RP macro for any other rotation."""
    poly = [(-16.0, -5.6), (DVDD_R, -5.6), (DVDD_R, DVDD_R), (-RP_CORE, DVDD_R),
            (-RP_CORE, -4.0), (-5.0, -4.0), (-5.0, -1.6), (-16.0, -1.6)]
    rr = (PLACE[K['U_RP']][2] if K['U_RP'] in PLACE else PL.RP_ROT) - 90
    return [tuple(round(v, 4) for v in rot_pt(x, y, rr)) for x, y in poly] if rr % 360 else poly


FIVE_V_NOTCH_X = PL.FIVE_V_NOTCH_X    # the +5V island may run up the east edge under the buck input / VBUS diode


def five_v_island():
    """In4 +5V: the floorplan's polygon (placement.FIVE_V_POLY: the cart side plus a strip up the
    east edge under the buck input); the +3V3_RP and DVDD islands win over it."""
    if getattr(PL, 'FIVE_V_POLY', None):
        return PL.FIVE_V_POLY
    return [(X0, PLANE_SPLIT_Y), (FIVE_V_NOTCH_X, PLANE_SPLIT_Y), (FIVE_V_NOTCH_X, Y0 + 2.0),
            (X1, Y0 + 2.0), (X1, TAB_Y), (X0, TAB_Y)]


def in4_net_at(x, y, ux, uy):
    """Which net the In4 plane carries at (x, y)."""
    if point_in_poly(x - ux, y - uy, dvdd_island()):
        return 'DVDD'
    if abs(x - ux) <= RP_ISLAND and abs(y - uy) <= RP_ISLAND:
        return '+3V3_RP'
    if point_in_poly(x, y, five_v_island()):
        return '+5V'
    return '+3V3'


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        if (ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya):
            inside = not inside
    return inside


def add_fanout(board, extra):
    import fanout
    pads, crt = board_pads(board)
    ux, uy, _ = PLACE[K['U_RP']]
    extra_segs, extra_vias, served = [], [], set()
    for e in extra:
        if e[0] not in ('segment', 'via'):
            continue
        net = str(find(e, 'net')[1])
        if e[0] == 'segment':
            s_, t_ = find(e, 'start'), find(e, 'end')
            sg = (float(s_[1]), float(s_[2]), float(t_[1]), float(t_[2]), net, float(find(e, 'width')[1]))
            extra_segs.append(sg)
            for p in pads:
                if p.net == net and (p.dist(sg[0], sg[1]) < 1e-6 or p.dist(sg[2], sg[3]) < 1e-6):
                    served.add(id(p))
        elif e[0] == 'via':
            a = find(e, 'at')
            extra_vias.append((float(a[1]), float(a[2]), net))

    # a pad only gets a plane via where the In4 plane carries its net (GND is In1, everywhere);
    # judged where the via will sit: a fine-pitch pin's via goes straight out along its
    # axis (fanout.plan), past the DVDD strip under the RP's pin rows
    def via_spot(p):
        if min(p.hw, p.hh) <= 0.15:
            fx, fy = p.fp_xy
            if p.hh > p.hw:
                return p.cx, p.cy + math.copysign(2.0, p.cy - fy)
            return p.cx + math.copysign(2.0, p.cx - fx), p.cy
        return p.cx, p.cy
    skip = set(served)
    for p in pads:
        if p.net in ('+3V3', '+3V3_RP', '+5V', 'DVDD') and in4_net_at(*via_spot(p), ux, uy) != p.net:
            skip.add(id(p))
    keep = [crt[K[k]] for k in ('U_S3', 'J_SD', 'J_USB', 'SW_RESET', 'SW_BOOTSEL', 'SW_S3EN', 'SW_S3BOOT')
            if K[k] in crt]
    keep.append((ux - UNDER, uy - UNDER, ux + UNDER, uy + UNDER))   # no fan-out vias under the RP2354B
    sx, sy, _ = PLACE[K['U_S3']]                                      # nor in the S3 antenna keep-out
    keep.append((sx - 24.0, Y0 - 1.0, sx + 24.0, sy - 6.75 + 0.3))   # (the module footprint's zone)
    holes = [(x, y, d / 2 + 0.5) for x, y, d in HOLES]
    vias, segs, failed = fanout.plan(pads, keep, (X0, Y0, X1, TAB_Y), BLADE_Y, holes, skip_refs=(K['J_EDGE'],),
                                     extra_segs=extra_segs, extra_vias=extra_vias, skip_pads=skip)
    for i, (x, y, n) in enumerate(vias):
        board.append(via(x, y, n, ('fv', i), fanout.VIA_D, fanout.VIA_DRILL))
    for i, (x0, y0, x1, y1, n, w) in enumerate(segs):
        board.append(seg(x0, y0, x1, y1, round(w, 3), 'F.Cu', n, ('fs', i)))
    print('fan-out: %d vias, %d stubs%s' % (len(vias), len(segs),
          ('; FAILED: ' + ' '.join(failed)) if failed else ''))


def outline():
    g = []
    n = len(OUTLINE)
    for i in range(n):
        a, b = OUTLINE[i], OUTLINE[(i + 1) % n]
        g.append(['gr_line', ['start', *a], ['end', *b], ['stroke', ['width', 0.1], ['type', 'default']],
                  ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', i)]])
    return g


def zone(name, net, layer, pts, keepout=False, priority=0, no_parts=False):
    z = ['zone', ['net', Q(net)] if net else ['net', Q('')], ['layer', Q(layer)], ['uuid', uid('zone', name, layer)],
         ['name', Q(name)], ['hatch', 'edge', 0.5]]
    if priority:
        z.append(['priority', priority])
    z += [['connect_pads', ['clearance', 0 if keepout else 0.25]], ['min_thickness', 0.25]]
    if keepout:
        z.append(['keepout', ['tracks', 'allowed' if no_parts else 'not_allowed'], ['vias', 'allowed' if no_parts else 'not_allowed'],
                  ['pads', 'allowed'], ['copperpour', 'allowed' if no_parts else 'not_allowed'],
                  ['footprints', 'not_allowed' if no_parts else 'allowed']])
        z.append(['placement', ['enabled', 'no'], ['sheetname', Q('')]])
    z.append(['fill', 'yes', ['thermal_gap', 0.3], ['thermal_bridge_width', 0.4], ['island_removal_mode', 0]]
             if not keepout else
             ['fill', ['thermal_gap', 0.5], ['thermal_bridge_width', 0.5], ['island_removal_mode', 0]])
    z.append(['polygon', ['pts'] + [['xy', round(x, 4), round(y, 4)] for x, y in pts]])
    return z


def circle_pts(x, y, r, n=12):
    return [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def text(s, x, y, layer, size=1.0, mirror=False, rot=0):
    eff = ['effects', ['font', ['size', size, size], ['thickness', size * 0.15]]]
    if mirror:
        eff.append(['justify', 'mirror'])
    return ['gr_text', Q(s), ['at', x, y, rot], ['layer', Q(layer)], ['uuid', uid('text', s, layer)], eff]


# ---------------------------------------------------------------------------
from placement import do_placement  # noqa: E402  (placement table lives in its own file)


# PWR keeps the Default 0.15 mm clearance: at 0.2 Freerouting counted the locked 0.16 mm plane
# fan-out as violations and routed worse (variant runs 2026-10-07: 47 vs 44 left, 9 vs 1 after)
NETCLASSES = [  # name, clearance, track, via dia, via drill, design.py nets
    ('PWR', 0.15, 0.5, 0.8, 0.4, ['+5V', 'CONS_5V', 'BUCK_SW', '+3V3']),
    ('VBUS', 0.15, 0.3, 0.6, 0.3, ['VBUS']),
    ('USB', 0.15, 0.25, 0.6, 0.3, ['USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM']),
]
CORNER = ['DVDD', 'RP_LX', 'VREG_AVDD']   # the RP2354B core-regulator copper


def configure_project():
    """Design rules + net classes in the .kicad_pro (JLCPCB 6-layer capable)."""
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    r = pro['board']['design_settings']['rules']
    # JLCPCB multilayer: trace/space 0.09, via 0.25/0.15, annular 0.125, copper-edge 0.2; the
    # rules sit above every one of those.  No mask-bridge check: JLC opens the mask as one
    # window across 0.4 mm-pitch pins (QFN-80, QFN-28, TSOP 0.5 mm) rather than dam them.
    r.update({'min_clearance': 0.12, 'min_copper_edge_clearance': 0.25, 'min_track_width': 0.1,
              'min_via_diameter': 0.5, 'min_through_hole_diameter': 0.25, 'min_hole_clearance': 0.25,
              'min_hole_to_hole': 0.25, 'min_via_annular_width': 0.125, 'solder_mask_min_width': 0.0,
              'solder_mask_clearance': 0.0, 'solder_mask_to_copper_clearance': 0.0})
    # the 25 fingers per face share one mask window (as every cart board): KiCad reports that
    # as a mask bridge between nets; it is the intended gold-finger process
    pro['board']['design_settings'].setdefault('rule_severities', {})['solder_mask_bridge'] = 'warning'
    ns = pro['net_settings']
    base = dict(ns['classes'][0])
    base.update({'name': 'Default', 'clearance': 0.15, 'track_width': 0.2, 'via_diameter': 0.6, 'via_drill': 0.3})
    classes = [base]
    patterns = []
    for i, (name, cl, tw, vd, vdr, nets) in enumerate(NETCLASSES):
        c = dict(base)
        c.update({'name': name, 'clearance': cl, 'track_width': tw, 'via_diameter': vd, 'via_drill': vdr,
                  'priority': i})
        classes.append(c)
        patterns += [{'netclass': name, 'pattern': NET(n)} for n in nets]
    ns['classes'] = classes
    ns['netclass_patterns'] = patterns
    ns['netclass_assignments'] = None
    pro['pcbnew'] = pro.get('pcbnew', {})
    pro['pcbnew'].setdefault('last_paths', {})['specctra_dsn'] = ''
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')
    corner_a = ' || '.join("A.NetName == '%s'" % NET(n) for n in CORNER)
    corner_ab = ' && '.join("A.NetName != '%s' && B.NetName != '%s'" % (NET(n), NET(n)) for n in CORNER)
    solid = ' || '.join("A.memberOfFootprint('%s')" % K[k]
                        for k in ('U_RP', 'U_SRAM0', 'U_SRAM1', 'U_UART', 'U_BUCK', 'U_LDO'))
    open(os.path.join(PRJ, D.PROJECT + '.kicad_dru'), 'w').write(
        '(version 1)\n'
        # the RP2354B core-regulator copper (0.4 mm pitch pins, 0402-class room) may use the fab minimum
        '(rule "rp2350_core_corner"\n'
        '\t(condition "%s")\n'
        '\t(constraint clearance (min 0.12mm)))\n'
        # 0.12 mm: the floor the last links at the RP's 0.4 mm-pitch pins need (finish_route --neck);
        # the routers aim for the 0.15 mm netclass value everywhere else.  JLCPCB 6-layer minimum: 0.09
        '(rule "default_clearance"\n'
        '\t(condition "%s")\n'
        '\t(constraint clearance (min 0.12mm)))\n'
        # QFN exposed pads, the SRAM and regulator grounds join the pours solidly
        '(rule "gnd_solid_under_ics"\n'
        '\t(condition "A.NetName == \'GND\' && (%s)")\n'
        '\t(constraint zone_connection solid))\n'
        # the fingers are 0.75 mm from the bevelled edge and 1.5 mm from the tab's sides by design
        '(rule "finger_edge"\n'
        '\t(condition "A.memberOfFootprint(\'%s\')")\n'
        '\t(constraint edge_clearance (min %gmm)))\n' % (corner_a, corner_ab, solid, K['J_EDGE'],
                                                         EG.FINGER_EDGE_CLEAR))


def write_case_anchors():
    """case/board-anchors.scad: the shell openings follow the placement."""
    def at(key):
        x, y, _ = PLACE[K[key]]
        return x, y
    lines = ['// GENERATED by tools/gen_pcb.py from tools/placement.py -- do not edit.',
             '// KiCad board frame (mm, y down): body x %g..%g, y %g (top edge) .. %g (tab base);' % (X0, X1, Y0, TAB_Y),
             '// tab x %g..%g down to the insertion edge y %g.' % (TAB_X0, TAB_X1, Y1),
             'pcb_x0 = %g; pcb_x1 = %g; pcb_y0 = %g; pcb_tab_y = %g; pcb_y1 = %g; pcb_t = %g;'
             % (X0, X1, Y0, TAB_Y, Y1, THICKNESS),
             'pcb_tab_x0 = %g; pcb_tab_x1 = %g;' % (TAB_X0, TAB_X1),
             'pcb_outline = [%s];' % ', '.join('[%g, %g]' % p for p in OUTLINE),
             'pcb_holes = [%s];   // [x, y, diameter]: the shell screws' % ', '.join('[%g, %g, %g]' % h for h in HOLES),
             'sw_reset   = [%g, %g];   // RESET' % at('SW_RESET'),
             'sw_bootsel = [%g, %g];   // RP BOOTSEL (pinhole)' % at('SW_BOOTSEL'),
             'sw_s3_en   = [%g, %g];   // ESP32-S3 EN (pinhole)' % at('SW_S3EN'),
             'sw_s3_boot = [%g, %g];   // ESP32-S3 BOOT (pinhole)' % at('SW_S3BOOT'),
             'led_ws     = [%g, %g];   // WS2812 status LED' % at('D_WS'),
             'led_rp     = [%g, %g];   // RP activity LED' % at('D_LED'),
             'usb_c      = [%g, %g];   // USB-C exits the top edge' % (at('J_USB')[0], Y0),
             'microsd    = [%g, %g];   // microSD exits the top edge' % (at('J_SD')[0], Y0),
             'esp32_ant  = [%g, %g];   // ESP32-S3 antenna centre (at the top edge)' % (at('U_S3')[0], Y0),
             'label_xy   = [%g, %g];   // label recess centre: a face area clear of buttons and LEDs' % PL.LABEL[0],
             'label_wh   = [%g, %g];   // label recess size' % PL.LABEL[1], '']
    os.makedirs(os.path.join(PRJ, 'case'), exist_ok=True)
    open(os.path.join(PRJ, 'case', 'board-anchors.scad'), 'w').write('\n'.join(lines))


def check_parts_inside(board):
    """Every courtyard inside the body (the tab is the edge's alone) and clear of the
    shell-screw rings."""
    _, crt = board_pads(board)
    bad = []
    for p in D.PARTS:
        if p.ref == K['J_EDGE'] or p.ref not in crt:
            continue
        x0, y0, x1, y1 = crt[p.ref]
        if x0 < X0 + 0.3 or x1 > X1 - 0.3 or y0 < Y0 + 0.1 or y1 > TAB_Y - 0.3:
            bad.append('%s (%s) courtyard %.1f,%.1f..%.1f,%.1f outside the body' % (p.ref, p.key, x0, y0, x1, y1))
        for hx, hy, hd in HOLES:
            cx, cy = min(max(hx, x0), x1), min(max(hy, y0), y1)
            if math.hypot(cx - hx, cy - hy) < HOLE_KEEP:
                bad.append('%s (%s) within %.1f mm of the hole at %g,%g' % (p.ref, p.key, HOLE_KEEP, hx, hy))
    # footprint keep-outs (the S3 antenna: no footprints, tracks, vias or pour) hold no other part
    for fp in board:
        if not (isinstance(fp, list) and fp and fp[0] == 'footprint'):
            continue
        owner = [str(e[2]) for e in findall(fp, 'property') if e[1] == 'Reference'][0]
        for z in findall(fp, 'zone'):
            ko = find(z, 'keepout')
            if not ko or ['footprints', 'not_allowed'] not in ko:
                continue
            xy = [(float(q[1]), float(q[2])) for q in find(find(z, 'polygon'), 'pts')[1:]]
            zx0, zy0, zx1, zy1 = min(x for x, _ in xy), min(y for _, y in xy), max(x for x, _ in xy), max(y for _, y in xy)
            for r, (x0, y0, x1, y1) in crt.items():
                if r != owner and x0 < zx1 and zx0 < x1 and y0 < zy1 and zy0 < y1:
                    bad.append('%s (%s) inside %s\'s keep-out %.1f,%.1f..%.1f,%.1f' % (
                        r, D.BY_REF[r].key if r in D.BY_REF else r, owner, zx0, zy0, zx1, zy1))
    refs = sorted(r for r in crt if (r in D.BY_REF and r != K['J_EDGE']) or r.startswith('FID'))
    for r in refs:     # the fiducials too: clear of the screw holes
        if r.startswith('FID'):
            x0, y0, x1, y1 = crt[r]
            for hx, hy, hd in HOLES:
                cx, cy = min(max(hx, x0), x1), min(max(hy, y0), y1)
                if math.hypot(cx - hx, cy - hy) < HOLE_KEEP:
                    bad.append('%s within %.1f mm of the hole at %g,%g' % (r, HOLE_KEEP, hx, hy))
    for i, r1 in enumerate(refs):
        a = crt[r1]
        for r2 in refs[i + 1:]:
            b = crt[r2]
            if a[0] < b[2] - 0.01 and b[0] < a[2] - 0.01 and a[1] < b[3] - 0.01 and b[1] < a[3] - 0.01:
                kk = lambda r: D.BY_REF[r].key if r in D.BY_REF else r
                bad.append('%s (%s) and %s (%s): courtyards overlap' % (r1, kk(r1), r2, kk(r2)))
    if bad:
        raise SystemExit('placement:\n  ' + '\n  '.join(bad))


FIDUCIALS = []      # placement.py fills: (name, x, y)


def fp_sheet_unit(p, syms):
    """The sheet and symbol unit a footprint links to.  A part drawn on several sheets (its units
    split between them) is filed by KiCad under the first of those sheets in hierarchy order, with
    the uuids of the units drawn there (checked in a prototype, 2026-10-08: kicad-cli's netlist and
    --schematic-parity); the footprint path takes the lowest of those units.  Cross-checked against
    the netlist kicad-cli wrote."""
    units = gen_sch.units_of(syms[p.lib_id])
    on = {u: p.unit_sheets.get(u, p.sheet) for u in units}
    stem = min(set(on.values()), key=D.SHEET_ORDER.index)
    u = min(u for u, sh in on.items() if sh == stem)
    NET('GND')
    if COMP_SHEET and COMP_SHEET.get(p.ref) != '/%s/' % stem:
        raise SystemExit('%s: design puts the footprint on /%s/, kicad-cli on %s' % (p.ref, stem, COMP_SHEET.get(p.ref)))
    return stem, u


def main():
    configure_project()
    do_placement(place, FIDUCIALS)
    write_case_anchors()
    NET('GND')        # loads the schematic netlist
    hdr = parse(open(os.path.join(HERE, 'pcb_header.sexpr')).read())
    find(find(hdr, 'general'), 'thickness')[1] = THICKNESS
    setup = find(hdr, 'setup')
    setup.insert(2, ['solder_mask_min_width', 0])
    layers = find(hdr, 'layers')
    rest = [l for l in layers[1:] if not str(l[1]).endswith('.Cu')]
    kinds = {'F.Cu': 'signal', 'In1.Cu': 'power', 'In2.Cu': 'signal', 'In3.Cu': 'signal', 'In4.Cu': 'power',
             'B.Cu': 'signal'}
    ids = {'F.Cu': '0', 'B.Cu': '2', 'In1.Cu': '4', 'In2.Cu': '6', 'In3.Cu': '8', 'In4.Cu': '10'}
    layers[1:] = [[ids[n], Q(n), kinds[n]] for n in COPPER] + rest
    board = hdr
    missing = [p.ref for p in D.PARTS if p.ref not in PLACE]
    if missing:
        raise SystemExit('unplaced: ' + ' '.join('%s (%s)' % (r, D.BY_REF[r].key) for r in missing))
    syms = gen_sch.load_symbols()
    for p in D.PARTS:
        x, y, r = PLACE[p.ref]
        stem, u = fp_sheet_unit(p, syms)
        path = '/%s/%s' % (gen_sch.uid('sheet', stem), gen_sch.uid(stem, p.ref, u))
        path = path.replace('"', '')
        ds = p.ds
        for pr in findall(syms[p.lib_id], 'property'):
            if pr[1] == 'Datasheet' and not ds:
                ds = str(pr[2])
        board.append(instance(p, x, y, r, path, '/%s/' % stem, stem + '.kicad_sch', ds))
    for name, x, y in FIDUCIALS:
        board.append(board_only(name, 'Fiducial_1mm_Mask2mm', x, y, 'assembly fiducial'))
    for i, (x, y, d) in enumerate(HOLES):
        board.append(board_only('H%d' % (i + 1), 'MountingHole_3.2mm_NPTH', x, y, 'shell screw M3'))
    check_parts_inside(board)
    ux, uy, _ = PLACE[K['U_RP']]
    extra = finger_stubs(board) + rp_support(board, ux, uy)
    if getattr(PL, 'SRAM0_FANIN', False):
        extra += sram0_fanin(board)
    board += extra
    add_fanout(board, extra)
    board += outline()
    # the tab: fingers only -- no tracks, vias or pour on any layer (pads allowed)
    tab = [(TAB_X0 - 0.5, PAD_TOP_Y + 0.5), (TAB_X1 + 0.5, PAD_TOP_Y + 0.5), (TAB_X1 + 0.5, Y1 + 1),
           (TAB_X0 - 0.5, Y1 + 1)]
    tab_all = [(TAB_X0 - 0.5, TAB_Y), (TAB_X1 + 0.5, TAB_Y), (TAB_X1 + 0.5, Y1 + 1), (TAB_X0 - 0.5, Y1 + 1)]
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('tab_fingers_only_' + L[0], None, L, tab, keepout=True))
    for L in ('In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu'):
        board.append(zone('tab_no_copper_' + L[2], None, L, tab_all, keepout=True))
    for L in ('F.Cu', 'B.Cu'):      # and no pour on the tab at all (the stubs cross it)
        z = zone('tab_no_pour_' + L[0], None, L, tab_all, keepout=True)
        find(z, 'keepout')[1:] = [['tracks', 'allowed'], ['vias', 'allowed'], ['pads', 'allowed'],
                                  ['copperpour', 'not_allowed'], ['footprints', 'allowed']]
        board.append(z)
    for i, (x, y, d) in enumerate(HOLES):   # the shell screws: no copper near the hole, no parts on the ring
        for L in COPPER:
            board.append(zone('screw_%d' % i, None, L, circle_pts(x, y, d / 2 + 0.6), keepout=True))
    board.append(zone('GND_plane', 'GND', 'In1.Cu', BODY))
    board.append(zone('3V3_plane', '+3V3', 'In4.Cu', BODY))
    board.append(zone('5V_island_0', '+5V', 'In4.Cu', five_v_island(), priority=2))
    tx, ty = PL.TITLE_XY                       # centred above the edge, clear of parts (placement.py)
    board.append(text('FujiNet SMS Rev0', tx, ty - 1.2, 'F.SilkS', 1.5))
    board.append(text('RP2354B + ESP32-S3', tx, ty + 1.2, 'F.SilkS', 1.0))
    board.append(text('CERN-OHL-W-2.0  fujinet.online', 82.0, 69.0, 'B.SilkS', 1.0, mirror=True))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
