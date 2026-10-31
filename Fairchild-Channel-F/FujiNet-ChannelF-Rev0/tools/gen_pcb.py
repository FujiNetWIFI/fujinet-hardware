#!/usr/bin/env python3
"""Generate FujiNet-ChannelF-Rev0.kicad_pcb (placed, unrouted) from design.py.

Board (KiCad frame, mm, y down; tools/placement.py owns the frame, tools/edge_geom.py the edge):
the insertion edge at y = 150, the 68.3 mm tab (x 65.85..134.15) straight for 30 mm with the key
slot in its middle, a 45-degree taper out to the 77 mm body, the trailing (grip-end) edge at
y = 18.5; four 5.6 mm holes on the original Videocart shell's bosses.  1.6 mm, 4 copper layers
(JLC04161H-7628):
  F.Cu  signals + GND pour       (every part: the face UP in the console)
  In1   GND plane
  In2   +3V3 (the S3 half) with islands: +3V3_RP under the RP2040, its flash and the
        translators' B halves; +5V down the power column; CONS_5V under the translators' A
        halves and the tab
  B.Cu  signals + GND pour       (the 22 edge fingers: the face DOWN in the console)
The finger field (the fingers, the B.Mask window and the key slot, 13.5 mm from the edge) carries
nothing but the fingers and a short locked stub from each; above it the tab may carry tracks and
vias, never parts (edge_geom.KEEP_D).  The ESP32-S3 antenna sits flush with the grip edge over the
module footprint's own keep-out.

Footprints are written as S-expressions (the SWIG pcbnew bindings are not
reliable under Python 3.14); route.py does the DSN/SES round trip and the
zone fills through pcbnew.  Net names come from the schematic's netlist
(hierarchical: /cart-rp/D0, /USB_DP, GND); NET() maps design.py's name to it.

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
import placement as PL          # the floorplan owns the frame, holes and In2 islands
XC = PL.XC
Y1 = PL.Y_EDGE                  # insertion edge
TAB_Y = Y1 - EG.TAB_D           # top of the straight tab
KEEP_Y = Y1 - EG.KEEP_D         # no parts south of this
BODY_Y = Y1 - EG.BODY_Y0        # the body's full width ends here (the taper starts)
Y0 = Y1 - EG.BOARD_H            # trailing (grip-end) edge: USB-C, microSD, the S3 antenna
HW = EG.BODY_W / 2
X0, X1 = XC - HW, XC + HW       # the body
TAB_HW = EG.TAB_W / 2
TAB_X0, TAB_X1 = XC - TAB_HW, XC + TAB_HW
PAD_TOP_Y = Y1 - EG.LAND_Y1     # finger copper ends here
FIELD_Y = Y1 - EG.FIELD_TOP     # the finger field: no tracks / vias / pour below this but the stubs
STUB_Y = Y1 - EG.STUB_TOP       # every finger stub ends here
BLADE_Y = FIELD_Y               # routers: no tracks/vias at y >= BLADE_Y
THICKNESS = EG.THICKNESS
CH_TOP, CH_TAB = EG.CH_TOP, EG.CH_TAB
SLW, LIW = EG.SLOT_W / 2, EG.LEADIN_W / 2
SLOT_TOP = Y1 - EG.SLOT_D       # the key slot's round top
SLOT_ARC = ((XC + SLW, SLOT_TOP + SLW), (XC, SLOT_TOP), (XC - SLW, SLOT_TOP + SLW))   # start, mid, end
OUTLINE = [(X0 + CH_TOP, Y0), (X1 - CH_TOP, Y0), (X1, Y0 + CH_TOP), (X1, BODY_Y), (TAB_X1, TAB_Y),
           (TAB_X1, Y1 - CH_TAB), (TAB_X1 - CH_TAB, Y1), (XC + LIW, Y1), (XC + SLW, Y1 - EG.LEADIN_D),
           SLOT_ARC[0], SLOT_ARC[1], SLOT_ARC[2], (XC - SLW, Y1 - EG.LEADIN_D), (XC - LIW, Y1),
           (TAB_X0 + CH_TAB, Y1), (TAB_X0, Y1 - CH_TAB), (TAB_X0, TAB_Y), (X0, BODY_Y), (X0, Y0 + CH_TOP)]
OUTLINE = [(round(x, 4), round(y, 4)) for x, y in OUTLINE]
BODY = [(X0, Y0), (X1, Y0), (X1, FIELD_Y), (X0, FIELD_Y)]   # planes / pours (KiCad clips them to the outline)
# the original shell's bosses (placement.HOLES): (x, y, diameter); no parts within HOLE_KEEP of a
# centre, no copper within HOLE_CU
HOLES = list(PL.HOLES)
HOLE_KEEP, HOLE_CU = PL.HOLE_KEEP, PL.HOLE_CU
UNDER = 3.0         # half-size of the square under the RP2040 the finisher keeps off F.Cu (and via-free)
R_RING = 2.35       # the RP2040's inner band: between its exposed pad (1.6) and the pads' inner ends (3.0)

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
                pr.append(['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.15]]])   # JLC silk: >= 0.15 mm strokes
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


COPPER = ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')


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
    """Each used finger gets a locked stub on B.Cu from 0.2 mm inside its inner end up out of the
    finger field (y = STUB_Y), so the routers only ever touch the stub end; the field itself is a
    track/via keepout.  The GND fingers (1, 2) get a via at the stub end into the In1 plane, the
    console 5 V fingers (19, 20) a wide stub and a via into the In2 CONS_5V island.  Fingers 21
    (spare) and 22 (+12 V) are bare: no stub, nothing near them."""
    out = []
    j1 = footprint_of(board, K['J_EDGE'])
    fx = float(find(j1, 'at')[1])      # the edge sits at rotation 0: pad x is footprint x + local x
    for pd in findall(j1, 'pad'):
        net = find(pd, 'net')
        if not net or str(net[1]).startswith('unconnected-'):   # unused finger: no stub to dangle
            continue
        net = str(net[1])
        assert str(find(pd, 'layers')[1]) == 'B.Cu'
        x = round(fx + float(find(pd, 'at')[1]), 4)
        w = 0.8 if net == NET('CONS_5V') else 0.6 if net == 'GND' else 0.3
        out.append(seg(x, PAD_TOP_Y + 0.05, x, STUB_Y, w, 'B.Cu', net, ('fstub', str(pd[1]))))
        if net in ('GND', NET('CONS_5V')):
            out.append(via(x, STUB_Y, net, ('fvia', str(pd[1])), 0.8, 0.4))
    return out


def rp_pads(board):
    u1 = footprint_of(board, K['U_RP'])
    at = find(u1, 'at')
    ux, uy, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
    pads, _ = board_pads([u1])
    return (ux, uy, rot), {p.num: p for p in pads}


def rp_support(board):
    """Locked copper the RP2040 needs regardless of routing:
      * IOVDD 1 and 10, the supply pins on the bus side (its south side at rotation 90: GP0-GP11),
        drop through a stub inward to a 0.5 mm via in the ring's free band between the pads and the
        exposed pad, onto the +3V3_RP island on In2, so no plane via stands in the bus fan-in
        (their 100 nF sit beside the bus on the island);
      * rp_dvdd_link: VREG_VOUT (45) -> DVDD (50, 23) inside the pin ring;
      * rp_usb_link: USB_DM / DP (46 / 47) drawn to their 27R."""
    (ux, uy, rot), P = rp_pads(board)
    out = []
    for num in ('1', '10'):
        p = P[num]
        dx, dy = p.cx - ux, p.cy - uy
        assert p.net == NET('+3V3_RP'), (num, p.net)
        if abs(dy) > abs(dx):
            vx, vy = max(-R_RING, min(R_RING, dx)), math.copysign(R_RING, dy)
        else:
            vx, vy = math.copysign(R_RING, dx), max(-R_RING, min(R_RING, dy))
        # along the pad's own axis to 0.1 past its inner end, then to the via (a straight diagonal from the
        # pad centre passes 0.1 mm from the next pin)
        if abs(dy) > abs(dx):
            mx, my = p.cx, uy + math.copysign(abs(dy) - p.hh - 0.1, dy)
        else:
            mx, my = ux + math.copysign(abs(dx) - p.hw - 0.1, dx), p.cy
        out.append(seg(p.cx, p.cy, mx, my, 0.2, 'F.Cu', p.net, ('rpio', num, 0)))
        out.append(seg(mx, my, ux + vx, uy + vy, 0.2, 'F.Cu', p.net, ('rpio', num, 1)))
        out.append(via(ux + vx, uy + vy, p.net, ('rpiov', num), 0.5, 0.25))
    # XOUT (21) inward to a via in the ring's east band, on to its 1k on B.Cu: XIN (20) leaves on F.Cu
    # straight to the crystal and IOVDD 22's via sits 2 mm out between them (atari2600-rev0's XOUT)
    p = P['21']
    assert p.net == NET('XOUT') and abs(p.cx - ux) > abs(p.cy - uy)
    vx, vy = ux + math.copysign(R_RING, p.cx - ux), p.cy
    out.append(seg(p.cx, p.cy, vx, vy, 0.2, 'F.Cu', p.net, ('rpxo',)))
    out.append(via(vx, vy, p.net, ('rpxov',), 0.5, 0.25))
    # ... and on B.Cu east under the crystal to a via 1 mm beyond the 1k's XOUT pad: drawn, so the control
    # lines Freerouting brings up the RP's east side on B.Cu go round it instead of walling it in (V1)
    rx_ = [q for q in board_pads([footprint_of(board, K['R_XOUT'])])[0] if q.net == p.net][0]
    assert rx_.cx > vx + 6.0 and abs(rx_.cy - vy) < 3.0, 'XOUT link: the 1k moved'
    wx = round(rx_.cx + rx_.hw + 0.9, 4)
    by = vy + 0.6                     # 0.6 mm south (under XIN's F.Cu run): IOVDD 22's plane via sits north
    out.append(seg(vx, vy, vx + 0.6, by, 0.2, 'B.Cu', p.net, ('rpxob', 0)))
    out.append(seg(vx + 0.6, by, wx, by, 0.2, 'B.Cu', p.net, ('rpxob', 1)))
    out.append(seg(wx, by, wx, rx_.cy, 0.2, 'B.Cu', p.net, ('rpxob', 2)))
    out.append(via(wx, rx_.cy, p.net, ('rpxow',), 0.5, 0.25))
    out.append(seg(wx, rx_.cy, rx_.cx, rx_.cy, 0.2, 'F.Cu', p.net, ('rpxof',)))
    # ADC_AVDD 43 and VREG_VIN 44 (both +3V3_RP) strapped and run straight into the VREG_VIN 1 uF west of
    # them (design guide 2.1.3: 1 uF close to VREG_IN), through their +3V3_RP via on the way: 1.15 mm out
    # and 0.35 mm toward the corner, clear of the DVDD exit, the 27R and the capacitor
    p43, p44 = P['43'], P['44']
    assert p43.net == p44.net == NET('+3V3_RP') and abs(p43.cx - ux) > abs(p43.cy - uy)
    cvi = [q for q in board_pads([footprint_of(board, K['C_VREGIN'])])[0] if q.net == p43.net][0]
    out.append(seg(p44.cx, p44.cy, p43.cx, p43.cy, 0.2, 'F.Cu', p43.net, ('rp4344',)))
    sx, sy = math.copysign(1, p43.cx - ux), math.copysign(1, p43.cy - uy)
    mx = p43.cx + sx * (p43.hw + 0.4)
    vx, vy = round(p43.cx + sx * (p43.hw + 0.7), 4), round(p43.cy + sy * 0.35, 4)
    out.append(seg(p43.cx, p43.cy, mx, p43.cy, 0.25, 'F.Cu', p43.net, ('rp43', 0)))
    out.append(seg(mx, p43.cy, vx, vy, 0.3, 'F.Cu', p43.net, ('rp43', 1)))
    out.append(seg(vx, vy, cvi.cx, cvi.cy, 0.3, 'F.Cu', p43.net, ('rp43', 2)))
    out.append(via(vx, vy, p43.net, ('rp43v',), 0.6, 0.3))
    # USB_VDD 48 and IOVDD 49 (both +3V3_RP) strapped, one via 1.15 mm out from 49: the USB pair
    # leaves just north of them and the QSPI lines just south (atari2600-rev0's 48 / 49)
    p48, p49 = P['48'], P['49']
    assert rot == 90 and p48.net == p49.net == NET('+3V3_RP')
    out.append(seg(p48.cx, p48.cy, p49.cx, p49.cy, 0.2, 'F.Cu', p49.net, ('rp4849',)))
    vx = p49.cx - p49.hw - 0.7
    out.append(seg(p49.cx, p49.cy, vx, p49.cy, 0.25, 'F.Cu', p49.net, ('rp49s',)))
    out.append(via(vx, p49.cy, p49.net, ('rp49v',), 0.6, 0.3))
    return out + rp_dvdd_link(board) + rp_usb_link(board)


def rp_dvdd_link(board):
    """VREG_VOUT (pin 45) -> DVDD (pins 50 and 23): locked F.Cu inside the RP2040's pin ring,
    between the pads' inner ends and the exposed pad, as Raspberry Pi's minimal design runs it
    (the routed atari2600-rev0 board's rp_dvdd_link).  Pins 46-49 (USB, USB_VDD, IOVDD) sit between
    45 and 50, so outside the ring the link would wall in the USB pair.  The DVDD capacitors hang
    off the band's corner on 45's side (variant V6: on atari2600-rev0's B.Cu link the 1 uF sat
    11.9 mm of copper from pin 45)."""
    (cx, cy, rot), P = rp_pads(board)
    p = {n: P[n] for n in ('45', '50', '23')}
    R = R_RING

    def inner(q):
        if abs(q.cx - cx) > abs(q.cy - cy):
            return (round(cx + math.copysign(R, q.cx - cx), 4), q.cy)
        return (q.cx, round(cy + math.copysign(R, q.cy - cy), 4))
    a, b, c = inner(p['45']), inner(p['50']), inner(p['23'])
    # 45 -> 50 along their own band; 45 -> round the band on 45's side -> 23 on the opposite face,
    # so DVDD pin 23 needs no route across the SWD / RUN escapes
    if abs(a[0] - cx) > abs(a[1] - cy):           # 45 on a west / east face: go round via the north/south band
        side = math.copysign(R, a[1] - cy)
        corner1, corner2 = (a[0], round(cy + side, 4)), (c[0], round(cy + side, 4))
    else:
        side = math.copysign(R, a[0] - cx)
        corner1, corner2 = (round(cx + side, 4), a[1]), (round(cx + side, 4), c[1])
    paths = [[(p['45'].cx, p['45'].cy), a, b, (p['50'].cx, p['50'].cy)],
             [a, corner1, corner2, c, (p['23'].cx, p['23'].cy)]]
    out = []
    for k, pts in enumerate(paths):
        out += [seg(*pts[i], *pts[i + 1], 0.25, 'F.Cu', NET('DVDD'), ('dvdd', k, i)) for i in range(len(pts) - 1)]
    # the VREG_VOUT 1 uF and the two DVDD 100 nF (design guide 2.1.3: 1 uF close to VREG_VOUT): out of the
    # band's corner on 45's side diagonally between the two corner pins (0.15 mm: 0.137 mm from each pad),
    # then 0.3 mm to the 1 uF and along the row of the three capacitors' DVDD pads -- no via in the path
    ox, oy = math.copysign(1, corner1[0] - cx), math.copysign(1, corner1[1] - cy)
    d1 = (round(cx + ox * 3.65, 4), round(cy + oy * 3.65, 4))
    out.append(seg(*corner1, *d1, 0.15, 'F.Cu', NET('DVDD'), ('dvdd', 'x0')))
    caps = [footprint_of(board, K[k]) for k in ('C_VREGOUT', 'C_DV50', 'C_DV23')]
    cp = [q for q in board_pads(caps)[0] if q.net == NET('DVDD')]
    order = [next(q for q in cp if q.ref == K[k]) for k in ('C_VREGOUT', 'C_DV50', 'C_DV23')]
    assert math.dist(d1, (order[0].cx, order[0].cy)) < 2.5, 'the VREG_VOUT 1 uF moved off the corner'
    chain = [d1] + [(q.cx, q.cy) for q in order]
    for i, (pa, pb) in enumerate(zip(chain, chain[1:])):
        out.append(seg(*pa, *pb, 0.3, 'F.Cu', NET('DVDD'), ('dvdd', 'r', i)))
    return out


def rp_usb_link(board):
    """RP2040 USB_DM / DP (pins 46 / 47) -> R_USBM / R_USBP (27R) as locked F.Cu, drawn rather
    than searched: the pair leaves the pins 0.4 mm apart, so a greedy router routing one line first
    always cuts off the other (atari2600-rev0).  Drawn for the RP at rotation 90 (the pins on its
    west face, DM the northern): out past the pin row, spread to 1.0 mm (DM up 0.3, DP down 0.3), then
    straight west into the two 27R lying in line at rotation 0, staggered -- R_USBM right after the
    spread, R_USBP beyond it -- so both sit close to the chip as the design guide asks (variant V7: on
    atari2600-rev0's layout they sat ~15 mm out, north-west)."""
    (ux, uy, rot), P = rp_pads(board)
    assert rot == 90, 'rp_usb_link is drawn for the RP2040 at rotation 90'
    pads, _ = board_pads([footprint_of(board, K['R_USBM']), footprint_of(board, K['R_USBP'])])
    pad = lambda k, n: [p for p in pads if p.ref == K[k] and p.num == n][0]
    dm, dp = P['46'], P['47']
    rm, rpp = pad('R_USBM', '2'), pad('R_USBP', '2')          # RP-side pads (east ends)
    xo = dm.cx - dm.hw - 0.85                                 # clear of the pin row, then spread
    y_dm, y_dp = dm.cy - 0.3, dp.cy + 0.3
    assert dm.cy < dp.cy and rpp.cx < rm.cx < xo - 0.3 and abs(rm.cy - y_dm) < 0.01 and abs(rpp.cy - y_dp) < 0.01, \
        'rp_usb_link: placement changed'
    paths = {'RP_USB_DM': [(dm.cx, dm.cy), (xo, dm.cy), (xo - 0.3, y_dm), (rm.cx, rm.cy)],
             'RP_USB_DP': [(dp.cx, dp.cy), (xo, dp.cy), (xo - 0.3, y_dp), (rpp.cx, rpp.cy)]}
    out = []
    for net, pts in paths.items():
        out += [seg(*pts[i], *pts[i + 1], 0.25, 'F.Cu', NET(net), ('usb', net, i)) for i in range(len(pts) - 1)]
    return out


def usbc_link(board):
    """The USB-C receptacle's data pads join, drawn: the row runs D+ (B6), D- (A7), D+ (A6), D- (B7) at
    0.5 mm, so one pair must change layer at the pins, and both routers kept failing it by chance (V7 left
    D-, V8 D+ open).  D+ joins on F.Cu in a 0.15 mm U under the pads; D- drops through a 0.45 mm via under
    each of its pads -- A7's inside the U -- and the two vias join on B.Cu.  The routers take D+ from the
    U and D- from either via.  Clearances >= 0.175 mm to the U and the neighbouring pads."""
    j = footprint_of(board, K['J_USB'])
    pads, _ = board_pads([j])
    smd = [p for p in pads if not p.th and p.net in (NET('UBRG_DP'), NET('UBRG_DM'))]
    dp = sorted((p for p in smd if p.net == NET('UBRG_DP')), key=lambda p: p.cx)
    dm = sorted((p for p in smd if p.net == NET('UBRG_DM')), key=lambda p: p.cx)
    assert len(dp) == len(dm) == 2 and dp[0].cx < dm[0].cx < dp[1].cx < dm[1].cx, 'usbc_link: the pad row changed'
    sgn = 1 if dp[0].cy > PLACE[K['J_USB']][1] else -1          # away from the receptacle body (south here)
    bot = dp[0].cy + sgn * dp[0].hh                              # the pads' outer ends
    v1 = (dm[0].cx, round(bot + sgn * 0.33, 4))                  # A7's via, inside the U
    v2 = (dm[1].cx, round(bot + sgn * 0.58, 4))                  # B7's via, east of it
    yu = round(v1[1] + sgn * 0.5, 4)                             # the U's bottom
    out = []
    u = [(dp[0].cx, dp[0].cy), (dp[0].cx, yu), (dp[1].cx, yu), (dp[1].cx, dp[1].cy)]
    out += [seg(*u[i], *u[i + 1], 0.15, 'F.Cu', dp[0].net, ('usbc', 'dp', i)) for i in range(3)]
    for k, (p, v) in enumerate(((dm[0], v1), (dm[1], v2))):
        out.append(seg(p.cx, p.cy, *v, 0.15, 'F.Cu', p.net, ('usbc', 'dms', k)))
        out.append(via(*v, p.net, ('usbc', 'dmv', k), 0.5, 0.25))
    out.append(seg(*v1, *v2, 0.2, 'B.Cu', dm[0].net, ('usbc', 'dmb')))
    return out


def buck_loop(board):
    """The AP63203's input loop drawn on F.Cu (its datasheet: the input capacitor as close to VIN and GND
    as possible): EN (2) strapped to VIN (3); VIN and GND (4) straight down the stack of the 100 nF and
    the two 22 uF under the IC as 0.6 mm rails; the plane vias at the stack's far end, two per rail, so
    the switching current closes on the top layer and not through In1 / In2."""
    u = footprint_of(board, K['U_BUCK'])
    caps = [footprint_of(board, K[k]) for k in ('C_BINHF', 'C_BIN1', 'C_BIN2')]
    pads, _ = board_pads([u] + caps)
    P = {(p.ref, p.num): p for p in pads}
    ur = K['U_BUCK']
    vin, en, gnd = P[(ur, '3')], P[(ur, '2')], P[(ur, '4')]
    assert vin.net == en.net == NET('+5V') and gnd.net == 'GND'
    out = [seg(en.cx, en.cy, vin.cx, vin.cy, 0.3, 'F.Cu', vin.net, ('bk', 'en'))]
    for name, top, num in (('v', vin, '1'), ('g', gnd, '2')):
        chain = [top] + [P[(K[k], num)] for k in ('C_BINHF', 'C_BIN1', 'C_BIN2')]
        assert all(q.net == top.net for q in chain), name
        for i, (a, b) in enumerate(zip(chain, chain[1:])):
            out.append(seg(a.cx, a.cy, b.cx, b.cy, 0.6, 'F.Cu', top.net, ('bk', name, i)))
        last = chain[-1]
        sx = -1 if name == 'v' else 1                 # +5V vias west of the stack, GND vias east
        for k, dy in enumerate((0.0, -1.2)):
            vx, vy = round(last.cx + sx * (last.hw + 0.75), 4), round(last.cy + dy, 4)
            out.append(seg(last.cx, last.cy, vx, vy, 0.6, 'F.Cu', top.net, ('bkv', name, k)))
            out.append(via(vx, vy, top.net, ('bkvv', name, k), 0.8, 0.4))
    return out


ISLANDS = [('+3V3_RP', 'RP_POLY'), ('+5V', 'FIVE_V_POLY'), ('CONS_5V', 'CONS5V_POLY')]   # In2, highest first


def in2_net_at(x, y):
    """Which net the In2 plane carries at (x, y)."""
    for net, poly in ISLANDS:
        if point_in_poly(x, y, getattr(PL, poly)):
            return net
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

    # a pad only gets a plane via where the In2 plane carries its net (GND is In1, everywhere);
    # judged where the via will sit: a fine-pitch pin's via goes straight out along its axis
    # (fanout.plan)
    def via_spot(p):
        if min(p.hw, p.hh) <= 0.15:
            fx, fy = p.fp_xy
            if p.hh > p.hw:
                return p.cx, p.cy + math.copysign(2.0, p.cy - fy)
            return p.cx + math.copysign(2.0, p.cx - fx), p.cy
        return p.cx, p.cy
    skip = set(served)
    for p in pads:
        if p.net in ('+3V3', '+3V3_RP', '+5V', 'CONS_5V') and in2_net_at(*via_spot(p)) != p.net:
            skip.add(id(p))
    keep = [crt[K[k]] for k in ('U_S3', 'J_SD', 'J_USB', 'SW_RESET', 'SW_BOOTSEL', 'SW_S3EN', 'SW_S3BOOT')
            if K[k] in crt]
    keep.append((ux - UNDER, uy - UNDER, ux + UNDER, uy + UNDER))   # no fan-out vias under the RP2040
    sx, sy, _ = PLACE[K['U_S3']]                                      # nor in the S3 antenna keep-out
    keep.append((sx - 24.0, Y0 - 1.0, sx + 24.0, sy - 6.75 + 0.3))   # (the module footprint's zone)
    # off the board beside the taper and the tab
    keep += [(X0 - 1, BODY_Y + 0.5, TAB_X0 + 0.6, Y1 + 1), (TAB_X1 - 0.6, BODY_Y + 0.5, X1 + 1, Y1 + 1)]
    holes = [(x, y, HOLE_CU) for x, y, d in HOLES]
    # the RP2040's DVDD pins (45, 50, 23) are served inside the pin ring: no escape lane in front of them
    no_lane = {id(p) for p in pads if p.ref == K['U_RP'] and p.net == NET('DVDD')}
    vias, segs, failed = fanout.plan(pads, keep, (X0, Y0, X1, BLADE_Y), BLADE_Y, holes, skip_refs=(K['J_EDGE'],),
                                     extra_segs=extra_segs, extra_vias=extra_vias, skip_pads=skip,
                                     no_corridor=no_lane)
    for i, (x, y, n) in enumerate(vias):
        board.append(via(x, y, n, ('fv', i), fanout.VIA_D, fanout.VIA_DRILL))
    for i, (x0, y0, x1, y1, n, w) in enumerate(segs):
        board.append(seg(x0, y0, x1, y1, round(w, 3), 'F.Cu', n, ('fs', i)))
    print('fan-out: %d vias, %d stubs%s' % (len(vias), len(segs),
          ('; FAILED: ' + ' '.join(failed)) if failed else ''))


def outline():
    """Edge.Cuts: the polygon's straight edges, and the key slot's round top as one arc."""
    g = []
    n = len(OUTLINE)
    arc = [tuple(round(v, 4) for v in p) for p in SLOT_ARC]
    for i in range(n):
        a, b = OUTLINE[i], OUTLINE[(i + 1) % n]
        if a in arc and b in arc:
            continue
        g.append(['gr_line', ['start', *a], ['end', *b], ['stroke', ['width', 0.1], ['type', 'default']],
                  ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', i)]])
    g.append(['gr_arc', ['start', *arc[0]], ['mid', *arc[1]], ['end', *arc[2]],
              ['stroke', ['width', 0.1], ['type', 'default']], ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', 'slot')]])
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
# fan-out as violations and routed worse (FujiNet-5200 variant runs 2026-10-07)
NETCLASSES = [  # name, clearance, track, via dia, via drill, design.py nets
    ('PWR', 0.15, 0.5, 0.8, 0.4, ['+5V', 'CONS_5V', 'BUCK_SW', '+3V3', '+3V3_RP']),
    ('VBUS', 0.15, 0.3, 0.6, 0.3, ['VBUS']),
    ('USB', 0.15, 0.25, 0.6, 0.3, ['USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM']),
]


def configure_project():
    """Design rules + net classes in the .kicad_pro (JLCPCB 6-layer capable)."""
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    r = pro['board']['design_settings']['rules']
    # JLCPCB multilayer: trace/space 0.09, via 0.25/0.15, annular 0.125, copper-edge 0.2; the
    # rules sit above every one of those.  No mask-bridge check: JLC opens the mask as one
    # window across 0.4 mm-pitch pins (QFN-56, QFN-28) rather than dam them.
    r.update({'min_clearance': 0.12, 'min_copper_edge_clearance': 0.25, 'min_track_width': 0.1,
              'min_via_diameter': 0.5, 'min_through_hole_diameter': 0.25, 'min_hole_clearance': 0.25,
              'min_hole_to_hole': 0.25, 'min_via_annular_width': 0.125, 'solder_mask_min_width': 0.0,
              'solder_mask_clearance': 0.0, 'solder_mask_to_copper_clearance': 0.0})
    # the 22 fingers share one mask window (as every cart board): KiCad reports that
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
    solid = ' || '.join("A.memberOfFootprint('%s')" % K[k]
                        for k in ('U_RP', 'U_UART', 'U_BUCK', 'U_LDO', 'U_DBUF', 'U_CBUF'))
    open(os.path.join(PRJ, D.PROJECT + '.kicad_dru'), 'w').write(
        '(version 1)\n'
        # 0.12 mm: the floor the last links at the RP2040's 0.4 mm-pitch pins need (finish_route --neck);
        # the routers aim for the 0.15 mm netclass value everywhere else.  JLCPCB 4-layer minimum: 0.09
        '(rule "default_clearance"\n'
        '\t(constraint clearance (min 0.12mm)))\n'
        # QFN exposed pads, the translator and regulator grounds join the pours solidly
        '(rule "gnd_solid_under_ics"\n'
        '\t(condition "A.NetName == \'GND\' && (%s)")\n'
        '\t(constraint zone_connection solid))\n'
        # the fingers are 0.5 mm from the bevelled edge and 1.1 mm from the slot's lead-in by design
        '(rule "finger_edge"\n'
        '\t(condition "A.memberOfFootprint(\'%s\')")\n'
        '\t(constraint edge_clearance (min %gmm)))\n' % (solid, K['J_EDGE'], EG.FINGER_EDGE_CLEAR))


def write_case_anchors():
    """case/board-anchors.scad: the shell openings follow the placement."""
    def at(key):
        x, y, _ = PLACE[K[key]]
        return x, y
    lines = ['// GENERATED by tools/gen_pcb.py from tools/placement.py and tools/edge_geom.py -- do not edit.',
             '// KiCad board frame (mm, y down), seen from F.Cu (the parts face, UP in the console): body x %g..%g,'
             % (X0, X1),
             '// y %g (grip-end edge) .. %g (taper); tab x %g..%g straight from y %g down to the insertion edge y %g.'
             % (Y0, BODY_Y, TAB_X0, TAB_X1, TAB_Y, Y1),
             '// The 22 contacts are on the BOTTOM face (B.Cu), the key slot x %g..%g up to y %g.'
             % (XC - SLW, XC + SLW, SLOT_TOP),
             'pcb_x0 = %g; pcb_x1 = %g; pcb_y0 = %g; pcb_body_y1 = %g; pcb_tab_y = %g; pcb_y1 = %g; pcb_t = %g;'
             % (X0, X1, Y0, BODY_Y, TAB_Y, Y1, THICKNESS),
             'pcb_tab_x0 = %g; pcb_tab_x1 = %g;' % (TAB_X0, TAB_X1),
             'pcb_slot = [%g, %g, %g];   // x centre, width, depth from the edge' % (XC, EG.SLOT_W, EG.SLOT_D),
             'pcb_outline = [%s];' % ', '.join('[%g, %g]' % p for p in OUTLINE),
             'pcb_holes = [%s];   // [x, y, diameter]: the original shell bosses' % ', '.join(
                 '[%g, %g, %g]' % h for h in HOLES),
             'parts_max_h = 3.3;   // tallest part on F.Cu (USB-C 3.26, ESP32-S3-WROOM-1 3.1); B.Cu carries none',
             'sw_reset   = [%g, %g];   // RESET (RP + S3): reachable through the top shell' % at('SW_RESET'),
             'sw_bootsel = [%g, %g];   // RP BOOTSEL (pinhole)' % at('SW_BOOTSEL'),
             'sw_s3_en   = [%g, %g];   // ESP32-S3 EN (pinhole)' % at('SW_S3EN'),
             'sw_s3_boot = [%g, %g];   // ESP32-S3 BOOT (pinhole)' % at('SW_S3BOOT'),
             'led_ws     = [%g, %g];   // WS2812 status LED (window / light pipe)' % at('D_WS'),
             'led_rp     = [%g, %g];   // RP activity LED (window / light pipe)' % at('D_LED'),
             'usb_c      = [%g, %g];   // USB-C exits the grip-end edge' % (at('J_USB')[0], Y0),
             'microsd    = [%g, %g];   // microSD exits the grip-end edge' % (at('J_SD')[0], Y0),
             'esp32_ant  = [%g, %g];   // ESP32-S3 antenna centre (at the grip-end edge): no metal near it'
             % (at('U_S3')[0], Y0),
             'label_xy   = [%g, %g];   // label recess centre: a face area clear of buttons and LEDs' % PL.LABEL[0],
             'label_wh   = [%g, %g];   // label recess size' % PL.LABEL[1], '']
    os.makedirs(os.path.join(PRJ, 'case'), exist_ok=True)
    open(os.path.join(PRJ, 'case', 'board-anchors.scad'), 'w').write('\n'.join(lines))


def check_parts_inside(board):
    """Every courtyard inside the outline, 0.3 mm in, and north of KEEP_Y (the straight tab is the
    edge's alone), and clear of the shell bosses' rings."""
    _, crt = board_pads(board)
    bad = []
    # 0.3 mm in from every edge, but only 0.1 from the grip-end edge (the S3 antenna, the USB-C and
    # the microSD sit flush with it, as on the SMS / 7800 / 5200 boards)
    inner = lambda x, y: all(point_in_poly(x + dx, max(y + dy, Y0 + 0.31), OUTLINE)
                             for dx in (-0.3, 0.3) for dy in (-0.3, 0.3))
    for p in D.PARTS:
        if p.ref == K['J_EDGE'] or p.ref not in crt:
            continue
        x0, y0, x1, y1 = crt[p.ref]
        corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)]
        if not all(inner(x, y) for x, y in corners) or y0 < Y0 + 0.1 or y1 > KEEP_Y - 0.1:
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
        if os.environ.get('PLACE_DRAFT'):      # floorplan work: report, write the board anyway
            print('placement:\n  ' + '\n  '.join(bad))
        else:
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


def title_block():
    """The board's title block: the revision kicad-happy's release gate reads first, and the
    assembly drawing's frame."""
    return ['title_block', ['title', Q('FujiNet Channel F Rev0')], ['date', Q(gen_sch.DATE)], ['rev', Q('0')],
            ['company', Q('FujiNet')],
            ['comment', 1, Q('Generated by tools/gen_pcb.py + tools/route_board.sh - edit those, not this file')],
            ['comment', 2, Q('CERN-OHL-W-2.0 (derived from the FujiNet 5200 / Atari 2600 Rev0 boards and their sources)')],
            ['comment', 3, Q(gen_sch.COMMENT3)],
            ['comment', 4, Q(gen_sch.COMMENT4)]]


# JLCPCB JLC04161H-7628, 1.6 mm: 1 oz outer, 0.5 oz inner, 7628 prepreg (er 4.4) each side of a
# 1.065 mm core.  ENIG, the edge connector bevelled (the fingers get hard gold at order time).
STACKUP = [('F.Cu', 'copper', 0.035), ('dielectric 1', 'prepreg', 0.2104, '7628', 4.4),
           ('In1.Cu', 'copper', 0.0152), ('dielectric 2', 'core', 1.065, 'FR4', 4.6),
           ('In2.Cu', 'copper', 0.0152), ('dielectric 3', 'prepreg', 0.2104, '7628', 4.4),
           ('B.Cu', 'copper', 0.035)]


def stackup():
    lay = [['layer', Q('F.SilkS'), ['type', Q('Top Silk Screen')]],
           ['layer', Q('F.Paste'), ['type', Q('Top Solder Paste')]],
           ['layer', Q('F.Mask'), ['type', Q('Top Solder Mask')], ['thickness', 0.01]]]
    for e in STACKUP:
        if e[1] == 'copper':
            lay.append(['layer', Q(e[0]), ['type', Q('copper')], ['thickness', e[2]]])
        else:
            lay.append(['layer', Q(e[0]), ['type', Q(e[1])], ['thickness', e[2]], ['material', Q(e[3])],
                        ['epsilon_r', e[4]], ['loss_tangent', 0.02]])
    lay += [['layer', Q('B.Mask'), ['type', Q('Bottom Solder Mask')], ['thickness', 0.01]],
            ['layer', Q('B.Paste'), ['type', Q('Bottom Solder Paste')]],
            ['layer', Q('B.SilkS'), ['type', Q('Bottom Silk Screen')]]]
    assert abs(sum(e[2] for e in STACKUP) + 0.02 - THICKNESS) < 0.03
    return ['stackup'] + lay + [['copper_finish', Q('ENIG')], ['dielectric_constraints', 'no'],
                                ['edge_connector', 'bevelled']]


def main():
    configure_project()
    do_placement(place, FIDUCIALS)
    write_case_anchors()
    NET('GND')        # loads the schematic netlist
    hdr = parse(open(os.path.join(HERE, 'pcb_header.sexpr')).read())
    find(find(hdr, 'general'), 'thickness')[1] = THICKNESS
    setup = find(hdr, 'setup')
    setup.insert(1, stackup())
    if not find(setup, 'solder_mask_min_width'):
        setup.insert(2, ['solder_mask_min_width', 0])
    layers = find(hdr, 'layers')
    rest = [l for l in layers[1:] if not str(l[1]).endswith('.Cu')]
    kinds = {'F.Cu': 'signal', 'In1.Cu': 'power', 'In2.Cu': 'power', 'B.Cu': 'signal'}
    ids = {'F.Cu': '0', 'B.Cu': '2', 'In1.Cu': '4', 'In2.Cu': '6'}
    layers[1:] = [[ids[n], Q(n), kinds[n]] for n in COPPER] + rest
    board = hdr
    board.insert(board.index(find(board, 'paper')) + 1, title_block())
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
        board.append(board_only('H%d' % (i + 1), 'MountingHole_%gmm_NPTH' % d, x, y, 'Videocart shell boss'))
    check_parts_inside(board)
    extra = finger_stubs(board) + rp_support(board) + buck_loop(board) + usbc_link(board)
    board += extra
    add_fanout(board, extra)
    board += outline()
    # the finger field: fingers only -- no tracks, vias or pour on any layer (pads allowed); the
    # stubs leave it from inside each finger.  F.Cu over the field stays bare.
    tab = [(TAB_X0 - 0.5, PAD_TOP_Y + 0.5), (TAB_X1 + 0.5, PAD_TOP_Y + 0.5), (TAB_X1 + 0.5, Y1 + 1),
           (TAB_X0 - 0.5, Y1 + 1)]
    tab_all = [(TAB_X0 - 0.5, FIELD_Y), (TAB_X1 + 0.5, FIELD_Y), (TAB_X1 + 0.5, Y1 + 1), (TAB_X0 - 0.5, Y1 + 1)]
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('tab_fingers_only_' + L[0], None, L, tab, keepout=True))
    for L in ('In1.Cu', 'In2.Cu', 'F.Cu'):
        board.append(zone('tab_no_copper_' + L[:3].replace('.', ''), None, L, tab_all, keepout=True))
    z = zone('tab_no_pour_B', None, 'B.Cu', tab_all, keepout=True)   # B.Cu: the stubs cross it, no pour
    find(z, 'keepout')[1:] = [['tracks', 'allowed'], ['vias', 'allowed'], ['pads', 'allowed'],
                              ['copperpour', 'not_allowed'], ['footprints', 'allowed']]
    board.append(z)
    # the +12 V finger (22) and the spare (21): nothing within 1 mm of them on any layer
    x21 = XC + EG.pin_x(21) - EG.FINGER_W / 2 - 1.0
    x22 = XC + EG.pin_x(22) + EG.FINGER_W / 2 + 1.0
    for L in COPPER:
        board.append(zone('nc_fingers_' + L[:3].replace('.', ''), None, L,
                          [(x21, FIELD_Y - 2.0), (x22, FIELD_Y - 2.0), (x22, PAD_TOP_Y + 0.4), (x21, PAD_TOP_Y + 0.4)],
                          keepout=True))
    for i, (x, y, d) in enumerate(HOLES):   # the shell bosses: no copper near the hole
        for L in COPPER:
            board.append(zone('boss_%d' % i, None, L, circle_pts(x, y, HOLE_CU, 16), keepout=True))
    board.append(zone('GND_plane', 'GND', 'In1.Cu', BODY))
    board.append(zone('3V3_plane', '+3V3', 'In2.Cu', BODY))
    for k, (net, poly) in enumerate(ISLANDS):
        board.append(zone('%s_island' % net.strip('+'), net, 'In2.Cu', getattr(PL, poly), priority=len(ISLANDS) - k))
    tx, ty = PL.TITLE_XY                       # clear of parts (placement.py)
    board.append(text('FujiNet Channel F Rev0', tx, ty - 1.4, 'F.SilkS', 1.5))
    board.append(text('RP2040 + ESP32-S3', tx, ty + 1.2, 'F.SilkS', 1.0))
    board.append(text('CERN-OHL-W-2.0  fujinet.online', XC, TAB_Y - 6.0, 'B.SilkS', 1.0, mirror=True))
    board.append(text('CONTACTS DOWN  -  LABEL UP', XC, TAB_Y + 4.0, 'B.SilkS', 1.0, mirror=True))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
