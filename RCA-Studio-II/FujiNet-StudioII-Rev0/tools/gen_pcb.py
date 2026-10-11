#!/usr/bin/env python3
"""Generate FujiNet-StudioII-Rev0.kicad_pcb (placed, pre-routed where it matters, unrouted
otherwise) from design.py.

Board (KiCad frame, mm, y down; tools/placement.py owns the frame, tools/edge_geom.py the edge):
FliP's Studio II multicart outline from the insertion edge up -- 90.912 mm wide, x 54.544..145.456,
the insertion edge at y = 150, the full width enters the console, no tab; a half-round notch in each
side 20.83 mm in, two 8.128 mm holes 68.58 mm in -- then taller than his board, 111.49 mm overall
(edge_geom.CART_H), the top edge at y = 38.51 with rounded corners: the ESP32-S3's antenna, the USB-C
and the microSD sit along it.  1.6 mm, 4 copper layers (JLC04161H-7628):
  F.Cu  signals + GND pour       (every part; no pour over the RP2350's regulator corner)
  In1   GND plane
  In2   +5V (the mux's output) with islands: +3V3 under the RP2354B and its LDO, +3V3_S3 under the
        S3 band, CONS_5V from finger 15 to the TPS2116 mux
  B.Cu  signals + GND pour       (the 22 edge fingers: the face away from the parts)
The ESP32-S3 module footprint's keep-out (its antenna plus Espressif's 15 mm) holds nothing on any
layer.
The finger field (the fingers in their mask openings, 9.55 mm from the edge) carries nothing but
the fingers and a short locked stub from each; inner layers start above it.  Below 23.5 mm
(edge_geom.PARTS_Y) the board carries copper but no part: the address bus's locked two-layer twist
(address_twist) and the data bus's fan-in to the '541 (data_fanin).

Locked before the routers (the FujiNet-5200 lesson: escapes the router walls in cannot be won
back afterwards): the finger stubs, the address twist, the data fan-in, the RP2354B's supply rings
and stubs (rp_support), Raspberry Pi's regulator corner (graft_copper), the USB-C pad join
(usbc_link), the S3 buck's input loop (buck_loop), the pin-to-capacitor links (cap_links) and the
plane fan-out (fanout.py).

Footprints are written as S-expressions (the SWIG pcbnew bindings are not reliable under Python
3.14); route.py does the DSN/SES round trip and the zone fills through pcbnew.  Net names come from
the schematic's netlist (hierarchical: /cart-bus/D0, /USB_DP, GND); NET() maps design.py's name to
it.

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
HW = EG.BOARD_W / 2
X0, X1 = XC - HW, XC + HW
Y0 = Y1 - EG.CART_H             # top edge: the ESP32-S3's antenna, the USB-C, the microSD
SIDE_Y = Y0 + EG.TOP_R          # the sides are straight from the insertion edge up to the top corners' arcs
KEEP_Y = Y1 - EG.PARTS_Y        # no part south of this
PAD_TOP_Y = Y1 - EG.LAND_Y1     # finger copper ends here
FIELD_Y = Y1 - EG.FIELD_TOP     # the finger field: nothing but the stubs below this
STUB_Y = Y1 - EG.STUB_TOP       # every finger stub ends here
BLADE_Y = FIELD_Y               # routers: no tracks/vias at y >= BLADE_Y
THICKNESS = EG.THICKNESS
NOTCH_Y = Y1 - EG.NOTCH_Y
NOTCH_DY = math.sqrt(EG.NOTCH_R ** 2 - EG.NOTCH_INSET ** 2)


def _arc_pts(c, r, a0, a1, n=8):
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]


# the outline, clockwise on screen: top edge, its rounded right corner, right side (notch), insertion
# edge, left side (notch), the rounded left corner.  FliP's outline from the insertion edge up; this
# board's sides then run straight on past his chamfers to the taller top (edge_geom.CART_H)
_cr = (X1 - EG.NOTCH_INSET, NOTCH_Y)
_cl = (X0 + EG.NOTCH_INSET, NOTCH_Y)
_R = EG.TOP_R
_c45 = _R * (1 - math.sqrt(0.5))
OUTLINE_ITEMS = [
    ('line', (X0 + _R, Y0), (X1 - _R, Y0)),
    ('arc', (X1 - _R, Y0), (X1 - _c45, Y0 + _c45), (X1, Y0 + _R)),
    ('line', (X1, SIDE_Y), (X1, NOTCH_Y - NOTCH_DY)),
    ('arc', (X1, NOTCH_Y - NOTCH_DY), (_cr[0] - EG.NOTCH_R, NOTCH_Y), (X1, NOTCH_Y + NOTCH_DY)),
    ('line', (X1, NOTCH_Y + NOTCH_DY), (X1, Y1 - EG.CH_EDGE)),
    ('line', (X1, Y1 - EG.CH_EDGE), (X1 - EG.CH_EDGE, Y1)),
    ('line', (X1 - EG.CH_EDGE, Y1), (X0 + EG.CH_EDGE, Y1)),
    ('line', (X0 + EG.CH_EDGE, Y1), (X0, Y1 - EG.CH_EDGE)),
    ('line', (X0, Y1 - EG.CH_EDGE), (X0, NOTCH_Y + NOTCH_DY)),
    ('arc', (X0, NOTCH_Y + NOTCH_DY), (_cl[0] + EG.NOTCH_R, NOTCH_Y), (X0, NOTCH_Y - NOTCH_DY)),
    ('line', (X0, NOTCH_Y - NOTCH_DY), (X0, SIDE_Y)),
    ('arc', (X0, SIDE_Y), (X0 + _c45, Y0 + _c45), (X0 + _R, Y0)),
]
OUTLINE_ITEMS = [(k, *[(round(x, 4), round(y, 4)) for x, y in pts]) for k, *pts in OUTLINE_ITEMS]


def _arc_through(a, m, b, n=8):
    """n + 1 points along the circular arc from a through m to b."""
    ax, ay = a; mx, my = m; bx, by = b
    d = 2 * (ax * (my - by) + mx * (by - ay) + bx * (ay - my))
    ux = ((ax * ax + ay * ay) * (my - by) + (mx * mx + my * my) * (by - ay) + (bx * bx + by * by) * (ay - my)) / d
    uy = ((ax * ax + ay * ay) * (bx - mx) + (mx * mx + my * my) * (ax - bx) + (bx * bx + by * by) * (mx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    t0, tm, t1 = (math.atan2(p[1] - uy, p[0] - ux) for p in (a, m, b))
    # sweep from t0 to t1 through tm
    def norm(t):
        return (t - t0) % (2 * math.pi)
    sweep = norm(t1) if norm(tm) < norm(t1) else norm(t1) - 2 * math.pi
    return [(ux + r * math.cos(t0 + sweep * i / n), uy + r * math.sin(t0 + sweep * i / n)) for i in range(n + 1)]


# the same outline as a polygon (the arcs sampled) for point-in-board tests and the finisher
OUTLINE = []
for _it in OUTLINE_ITEMS:
    if _it[0] == 'line':
        OUTLINE.append(_it[1])
    else:
        OUTLINE += [(round(x, 4), round(y, 4)) for x, y in _arc_through(*_it[1:])][:-1]
BODY = [(X0, Y0), (X1, Y0), (X1, FIELD_Y), (X0, FIELD_Y)]   # planes / pours (KiCad clips them to the outline)
# the shell posts (placement.HOLES): (x, y, diameter); no parts within HOLE_KEEP of a centre, no copper
# within HOLE_CU
HOLES = list(PL.HOLES)
HOLE_KEEP, HOLE_CU = PL.HOLE_KEEP, PL.HOLE_CU
UNDER = 4.6         # half-size of the square under the RP2354B the finisher keeps clear (rings, stubs, EP vias)

# the RP2354B's supply rings under the package (F.Cu, after Raspberry Pi's minimal design): the
# exposed pad (GND, 3.4 mm) in the middle, a DVDD ring round it, a +3V3 ring round that, the pin rows'
# inner ends at 4.55 -- every supply pin stubs inward to its ring
RING_DVDD = 2.75    # the DVDD zone: a square of this half-size (the exposed pad cuts its middle out)
RING_3V3 = 3.9      # the +3V3 zone: this half-size (the DVDD zone, higher priority, cuts its middle)
STUB_3V3 = 3.35     # a +3V3 pin's stub ends here (mid-ring)
STUB_DVDD = 2.3     # a DVDD pin's stub ends here (mid-ring, through the +3V3 ring)

# Raspberry Pi's regulator corner (RP rotation-0 frame): no F.Cu GND pour here -- the RP2350 datasheet
# 6.3.8.1: "cut away any extra copper underneath the inductor", keep the switching loops "isolated (i.e.
# only connect to main GND at one point)": the graft's PGND pour joins main GND through its own two vias
REG_CUT = [(1.75, -4.6), (6.1, -4.6), (6.1, -10.3), (1.75, -10.3)]
RP_KEEP = 4.45      # half-size of the square under the RP2354B the routers never enter (rings, stubs, EP vias)

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
COMP_SHEET = {} # ref -> the sheet name kicad-cli files the component under ('/cart-bus/')


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


SMALL = re.compile(r'_0603_|_0805_|_0402|0402|SOD-523|SOT-23|SOT-363|SOT-583|R_Array|AOTA|Crystal_SMD|WS2812|TSOT|TestPoint')


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
            elif isinstance(g, list) and g and g[0] == 'fp_poly' and find(g, 'layer')[1] == 'F.CrtYd':
                for q in find(g, 'pts')[1:]:
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


def path(pts, w, layer, net, key):
    return [seg(*pts[i], *pts[i + 1], w, layer, net, key + (i,)) for i in range(len(pts) - 1)
            if math.dist(pts[i], pts[i + 1]) > 1e-6]


def footprint_of(board, ref):
    return [e for e in board if isinstance(e, list) and e and e[0] == 'footprint'
            and any(p[1] == 'Reference' and p[2] == ref for p in findall(e, 'property'))][0]


def pads_of(board, key):
    return {p.num: p for p in board_pads([footprint_of(board, K[key])])[0]}


# ---- the edge -----------------------------------------------------------------
def finger_x(pin):
    return round(XC + EG.pin_x(pin), 4)


def finger_stubs(board):
    """Every finger gets a locked stub on B.Cu from 0.2 mm inside its inner end up out of the finger
    field (y = STUB_Y), so the routers only ever touch the stub end; the field itself is a
    track / via keep-out.  The GND fingers (6 ROM DISABLE, 7) get a via at the stub end into the In1
    plane, the console 5 V finger (15) a wide stub and a via into the In2 CONS_5V island.  The
    address and data lines continue as address_twist / data_fanin draw them."""
    out = []
    j1 = footprint_of(board, K['J_EDGE'])
    fx = float(find(j1, 'at')[1])      # the edge sits at rotation 0: pad x is footprint x + local x
    for pd in findall(j1, 'pad'):
        net = str(find(pd, 'net')[1])
        assert str(find(pd, 'layers')[1]) == 'B.Cu'
        x = round(fx + float(find(pd, 'at')[1]), 4)
        w = 0.8 if net == NET('CONS_5V') else 0.6 if net == 'GND' else 0.25
        out.append(seg(x, PAD_TOP_Y + 0.05, x, STUB_Y, w, 'B.Cu', net, ('fstub', str(pd[1]))))
        if net in ('GND', NET('CONS_5V')):
            out.append(via(x, STUB_Y, net, ('fvia', str(pd[1])), 0.8, 0.4))
    return out


# the ten address lines, by finger pin: (pin, design.py net, the 330R's key)
ADDR = [(21, 'MRD_N', 'R_MRD'), (20, 'MA7', 'R_MA7'), (19, 'TPA', 'R_TPA'), (18, 'MA6', 'R_MA6'),
        (17, 'MA5', 'R_MA5'), (16, 'MA4', 'R_MA4'), (14, 'MA3', 'R_MA3'), (13, 'MA2', 'R_MA2'),
        (12, 'MA1', 'R_MA1'), (11, 'MA0', 'R_MA0')]
TWIST_W = 0.25          # the twist's tracks
TWIST_TOP = 127.6       # its highest level (y) ...
TWIST_PITCH = 1.0       # ... and the step between levels
TWIST_VIA = (0.6, 0.3)
TWIST_M = 0.6           # copper margin between a level's track and a foreign via / column (0.125 + 0.15 + 0.3)


def address_twist(board):
    """The ten address lines (/MRD, MA7, TPA, MA6 .. MA0 west to east at the fingers) reach the 330R
    row in the RP2354B's GPIO order (MA0 .. MA7, TPA, /MRD west to east: placement.BANK), a full
    reversal no flow-through route can make on one layer.  It is made here, in the parts-free band
    above the fingers, as a two-layer ladder: each line rises from its finger stub on B.Cu to a level
    of its own, crosses on F.Cu along that level to its resistor's column, and rises into the
    resistor's edge-side pad (pad 1, F.Cu):
      * a line moving east (/MRD, MA7, TPA, MA6, MA5, MA4) rises the last stretch on F.Cu (one via);
      * a line moving west (MA2, MA1, MA0) on B.Cu, then through a via under the resistor (two more):
        an F.Cu rise for both directions would form a cycle -- /MRD's level spans MA0's column and
        MA0's spans /MRD's -- so one direction must change layer;
      * a line that already sits under its resistor (MA3) rises straight on B.Cu to that via.
    No level may cross a foreign F.Cu column or pass a foreign via, so a line whose level spans
    another's column lies below it: the levels are a topological sort of those constraints (it
    fails loudly on a cycle or an impossible column)."""
    L = []
    for pin, net, rk in ADDR:
        rp = pads_of(board, rk)['1']
        assert rp.net == NET(net) and abs(rp.cy - (PL.BANK_Y + 0.825)) < 0.01, (rk, rp.net, rp.cy)
        s_, t_ = finger_x(pin), rp.cx
        mode = 'd' if abs(s_ - t_) < TWIST_M else ('f' if t_ > s_ else 'b')
        L.append({'pin': pin, 'net': NET(net), 's': s_, 't': t_, 'm': mode, 'py': rp.cy, 'ph': rp.hh})
    n = len(L)
    below = {i: set() for i in range(n)}      # below[i]: the lines whose level must lie north of i's
    for i, a in enumerate(L):
        for j, b in enumerate(L):
            if i == j:
                continue
            if a['m'] == 'd' or b['m'] == 'd':
                c = (a['s'], b['t'], b['m']) if a['m'] == 'd' else (b['s'], a['t'], a['m'])
                assert not (c[2] == 'b' and abs(c[0] - c[1]) < TWIST_M), 'address_twist: a straight rise beside a B.Cu column'
                continue
            lo, hi = min(a['s'], a['t']) - TWIST_M, max(a['s'], a['t']) + TWIST_M
            if b['m'] == 'f' and lo < b['t'] < hi:
                below[i].add(j)               # i's level crosses j's F.Cu column
            if abs(a['s'] - b['t']) < TWIST_M:
                below[i].add(j)               # i's via (and B.Cu rise) beside j's column
            if a['m'] == 'b' and abs(a['t'] - b['s']) < TWIST_M:
                below[j].add(i)               # j's B.Cu rise under i's column via
    order, done = [], {i for i in range(n) if L[i]['m'] == 'd'}
    while len(done) < n:
        ready = [i for i in range(n) if i not in done and below[i] <= done]
        if not ready:
            raise SystemExit('address_twist: the level constraints form a cycle (move placement.BANK_X0)')
        i = min(ready, key=lambda k: L[k]['s'])
        order.append(i); done.add(i)
    out = []
    for i in range(n):
        a = L[i]
        y_top = round(a['py'] + a['ph'] + 0.35, 4)          # the column via just under the resistor's pad 1
        if a['m'] == 'd':
            out += path([(a['s'], STUB_Y), (a['s'], y_top)], TWIST_W, 'B.Cu', a['net'], ('tw', a['pin'], 'b'))
            out.append(via(a['s'], y_top, a['net'], ('tw', a['pin'], 'vt'), *TWIST_VIA))
            out += path([(a['s'], y_top), (a['t'], a['py'])], TWIST_W, 'F.Cu', a['net'], ('tw', a['pin'], 'ft'))
            continue
        y = round(TWIST_TOP + order.index(i) * TWIST_PITCH, 4)
        assert y < STUB_Y - 1.0, 'address_twist: too many levels for the band'
        assert y > y_top + 0.9
        a['y'] = y
        out += path([(a['s'], STUB_Y), (a['s'], y)], TWIST_W, 'B.Cu', a['net'], ('tw', a['pin'], 'b'))
        out.append(via(a['s'], y, a['net'], ('tw', a['pin'], 'v'), *TWIST_VIA))
        out += path([(a['s'], y), (a['t'], y)], TWIST_W, 'F.Cu', a['net'], ('tw', a['pin'], 'f'))
        if a['m'] == 'f':
            out += path([(a['t'], y), (a['t'], a['py'])], TWIST_W, 'F.Cu', a['net'], ('tw', a['pin'], 'fc'))
        else:
            out.append(via(a['t'], y, a['net'], ('tw', a['pin'], 'vc'), *TWIST_VIA))
            out += path([(a['t'], y), (a['t'], y_top)], TWIST_W, 'B.Cu', a['net'], ('tw', a['pin'], 'bc'))
            out.append(via(a['t'], y_top, a['net'], ('tw', a['pin'], 'vt'), *TWIST_VIA))
            out += path([(a['t'], y_top), (a['t'], a['py'])], TWIST_W, 'F.Cu', a['net'], ('tw', a['pin'], 'ft'))
    print('address twist: levels %s; F.Cu rises %s, B.Cu rises %s, straight %s' % (
        ' '.join(str(L[i]['pin']) for i in order), ' '.join(str(a['pin']) for a in L if a['m'] == 'f'),
        ' '.join(str(a['pin']) for a in L if a['m'] == 'b'), ' '.join(str(a['pin']) for a in L if a['m'] == 'd')))
    return out


# the data fan-in: finger -> B.Cu up / west along a lane / up to a via under the '541's Y row -> F.Cu
DATA_LANES = {7: 128.0, 6: 128.6, 5: 129.2, 4: 129.8, 3: 130.4, 2: 131.0, 0: 132.0, 1: 132.6}
DATA_VIA_ROWS = (121.15, 122.35)      # even bits on the row nearer the '541, odd bits on the far row


def data_fanin(board):
    """D0-D7 from their fingers (west to east D0 D1 D2 [GND GND] D3 .. D7) to the '541's Y row
    (D0 .. D7 west to east at 0.65 mm: design.py reverses its channels for this), locked: B.Cu
    straight up from the stub to the line's own lane, along the lane to the column of its '541 pin,
    up to a via in one of two staggered rows just south of the row, then F.Cu into the pin.  Lines
    moving west turn on lanes ordered east-highest, so no lane crosses a rise; D0 and D1 (moving
    east) on lanes of their own below."""
    u = pads_of(board, 'U_BUF')
    out = []
    data_pins = {0: 10, 1: 9, 2: 8, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1}
    for bit, fpin in data_pins.items():
        net = NET('D%d' % bit)
        yp = [p for p in u.values() if p.net == net]
        assert len(yp) == 1 and abs(yp[0].cy - (PL.BUF_XY[1] + 2.8625)) < 0.01, ('data_fanin', bit)
        yp = yp[0]
        s, v = finger_x(fpin), yp.cx
        lane = DATA_LANES[bit]
        vy = DATA_VIA_ROWS[bit % 2]
        out += path([(s, STUB_Y), (s, lane), (v, lane), (v, vy)], TWIST_W, 'B.Cu', net, ('dfan', bit, 'b'))
        out.append(via(v, vy, net, ('dfan', bit, 'v'), *TWIST_VIA))
        out += path([(v, vy), (v, yp.cy)], 0.25, 'F.Cu', net, ('dfan', bit, 'f'))
    return out


# ---- the RP2354B -----------------------------------------------------------------
def rp_frame(board):
    u1 = footprint_of(board, K['U_RP'])
    at = find(u1, 'at')
    ux, uy, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
    pads, _ = board_pads([u1])
    return (ux, uy, rot), {p.num: p for p in pads}


def rp_xy(lx, ly):
    """RP-local (rotation 0, y down) -> board coordinates, turned with the RP."""
    ux, uy, ur = PLACE[K['U_RP']]
    dx, dy = rot_pt(lx, ly, ur)
    return round(ux + dx, 4), round(uy + dy, 4)


def square(h):
    return [rp_xy(x, y) for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))]


def rp_support(board):
    """Locked copper under the RP2354B, after Raspberry Pi's minimal design (which joins its supply
    pins the same way under the QFN-60), sized for the QFN-80:
      * two concentric F.Cu pours inside the pin rows: DVDD round the exposed pad (half-size
        RING_DVDD, the exposed pad cuts its middle) and +3V3 round that (RING_3V3, the DVDD pour --
        higher priority -- cuts its middle);
      * every +3V3 supply pin (IOVDD x8, ADC_AVDD, VREG_VIN, USB_OTP_VDD, QSPI_IOVDD) stubs straight
        inward into the +3V3 ring, every DVDD pin (10, 32, 51) through it into the DVDD ring, so no
        supply pin needs a via among the bus pins;
      * the +3V3 ring drops to the In2 plane through a via at each of its corners;
      * the DVDD ring joins the regulator's output node (the graft's two DVDD vias by C_DVBULK /
        L_RP) through a via and a 0.6 mm B.Cu link, as the reference does;
      * the exposed pad's 3 x 3 GND via grid is fanout.py's (EP_ARRAYS)."""
    (ux, uy, rot), P = rp_frame(board)
    out = []
    p3, pdv = NET('+3V3'), NET('DVDD')
    for num, p in P.items():
        if p.net not in (p3, pdv) or num == '81' or num == '65':
            continue                                   # 65 (VREG_FB) reaches DVDD through the graft
        lx, ly = rot_pt(p.cx - ux, p.cy - uy, -rot)    # back to the RP's rotation-0 frame
        r = STUB_3V3 if p.net == p3 else STUB_DVDD
        if abs(lx) > abs(ly):
            end = (math.copysign(r, lx), ly)
        else:
            end = (lx, math.copysign(r, ly))
        out += path([(p.cx, p.cy), rp_xy(*end)], 0.2, 'F.Cu', p.net, ('rpstub', num))
    zs = [zone('rp_dvdd_ring', pdv, 'F.Cu', square(RING_DVDD), priority=9, clearance=0.15, min_thick=0.2),
          zone('rp_3v3_ring', p3, 'F.Cu', square(RING_3V3), priority=8, clearance=0.15, min_thick=0.2)]
    c = (RING_DVDD + 0.15 + RING_3V3) / 2
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        out.append(via(*rp_xy(sx * c, sy * c), p3, ('rp3v3v', i), 0.5, 0.25))
    # DVDD: a via in the ring on the regulator side, B.Cu straight out to the graft's two DVDD vias
    gv = sorted((float(find(e, 'at')[1]), float(find(e, 'at')[2])) for e in GRAFT[1:]
                if e[0] == 'via' and str(find(e, 'net')[1]) == 'DVDD')
    assert len(gv) == 2 and abs(gv[0][0] - gv[1][0]) < 1e-6, gv
    gx = gv[0][0]
    a = (gx, -STUB_DVDD)
    out.append(via(*rp_xy(*a), pdv, ('rpdvv',), 0.5, 0.25))
    out += path([rp_xy(*a), rp_xy(gx, min(v[1] for v in gv))], 0.6, 'B.Cu', pdv, ('rpdvb',))
    # ... and on the bus side (south at rotation 90) to DVDD 32's 100 nF (pin 32 sits on the east side
    # between XOUT and SWCLK, with no room outside it), below DVDD 10's: a via in the ring beside pin
    # 10's stub, B.Cu out under 10's capacitor to a via between the two, F.Cu into 32's DVDD pad
    c = pads_of(board, 'C_DV32')['1']
    c10 = pads_of(board, 'C_DV10')['2']
    assert c.net == pdv and abs(c.cx - c10.cx) < 1e-3 and c.cy > c10.cy
    p10 = P['10']
    lx, ly = rot_pt(p10.cx - ux, p10.cy - uy, -rot)
    assert abs(lx) > abs(ly), 'rp_support: DVDD 10 moved off the rotation-0 west side'
    b0 = (math.copysign(STUB_DVDD, lx), ly - 0.8)               # 0.8 mm beside pin 10's stub, in the ring
    bx, by = rp_xy(*b0)
    vx, vy = c.cx, (c10.cy + c10.hh + c.cy - c.hh) / 2            # between 10's GND pad and 32's DVDD pad
    out.append(via(bx, by, pdv, ('rpdvs', 0), 0.5, 0.25))
    out += path([(bx, by), (bx, vy - abs(vx - bx)), (vx, vy)], 0.4, 'B.Cu', pdv, ('rpdvs', 'b'))
    out.append(via(vx, vy, pdv, ('rpdvs', 1), 0.5, 0.25))
    out += path([(vx, vy), (c.cx, c.cy)], 0.25, 'F.Cu', pdv, ('rpdvs', 'f'))
    return out, zs


# ---- Raspberry Pi RP2350 minimal-design regulator corner (tools/rpi_graft.py) ----
GRAFT = parse(open(os.path.join(HERE, 'rpi_core_graft.sexpr')).read())
GRAFT_REFS = {K[str(e[1])] for e in GRAFT[1:] if e[0] == 'part'}


def graft_parts():
    ur = PLACE[K['U_RP']][2]
    for e in GRAFT[1:]:
        if e[0] == 'part':
            key = str(e[1])
            a = find(e, 'at')
            x, y = rp_xy(float(a[1]), float(a[2]))
            PLACE[K[key]] = (x, y, (float(a[3]) + ur) % 360)
            want = {str(q[0]): str(q[1]) for q in find(e, 'pads')[1:]}
            have = {k: v for k, v in D.BY_KEY[key].pins.items()}
            assert want == have, ('graft %s: reference pads %s, design.py %s' % (key, want, have))


def graft_copper():
    """Raspberry Pi's regulator-corner copper, moved and turned with the RP."""
    out, zs = [], []
    for i, e in enumerate(GRAFT[1:]):
        if e[0] == 'segment':
            s_, t_ = find(e, 'start'), find(e, 'end')
            out.append(seg(*rp_xy(float(s_[1]), float(s_[2])), *rp_xy(float(t_[1]), float(t_[2])),
                           float(find(e, 'width')[1]), 'F.Cu', NET(str(find(e, 'net')[1])), ('graft', i)))
        elif e[0] == 'via':
            a = find(e, 'at')
            out.append(via(*rp_xy(float(a[1]), float(a[2])), NET(str(find(e, 'net')[1])), ('graft', i),
                           float(find(e, 'size')[1]), float(find(e, 'drill')[1])))
        elif e[0] == 'zone':
            pts = [rp_xy(float(p[1]), float(p[2])) for p in find(e, 'pts')[1:]]
            zs.append(zone('rpi_graft_%d' % i, NET(str(find(e, 'net')[1])), 'F.Cu', pts,
                           priority=int(find(e, 'priority')[1]) + 10, clearance=float(find(e, 'clearance')[1]),
                           min_thick=float(find(e, 'min_thickness')[1]), solid=True))
    return out, zs


# capacitors that sit straight out from their RP pin: a locked F.Cu link pin -> the capacitor's pad 1
CAP_LINKS = [('10', 'C_DV10'), ('15', 'C_IOV15'), ('41', 'C_IOV41'), ('50', 'C_IOV50'), ('51', 'C_DV51'),
             ('59', 'C_ADC'), ('60', 'C_IOV60')]


def cap_links(board):
    (ux, uy, rot), P = rp_frame(board)
    out = []
    for num, key in CAP_LINKS:
        p = P[num]
        c = pads_of(board, key)['1']
        assert c.net == p.net, (num, key, c.net, p.net)
        # out of the pin along its own axis to 0.45 mm past the pad's outer end, then to the pad
        lx, ly = rot_pt(p.cx - ux, p.cy - uy, -rot)
        if abs(lx) > abs(ly):
            m = rp_xy(math.copysign(abs(lx) + 0.4 + 0.45, lx), ly)
        else:
            m = rp_xy(lx, math.copysign(abs(ly) + 0.4 + 0.45, ly))
        out += path([(p.cx, p.cy), m, (c.cx, c.cy)], 0.2, 'F.Cu', p.net, ('caplink', num))
    return out


DATA_FAN_DC = 0.6      # the data fan's diagonals: x - y steps this much from line to line (0.42 mm apart)


def data_rp_fan(board):
    """GPIO16-23 (the RP2354B's south-east corner at rotation 90: 16-20 on the south side west to east,
    21-23 up the east side) to the '541's A row (RP_D0 .. RP_D7 west to east at 0.65 mm), locked: each
    line leaves its pin straight out, runs a 45-degree diagonal down to the south-east, and drops into its
    pin.  The diagonals are parallel lines x - y = c with c rising DATA_FAN_DC per line (the five south pins
    first, as early as each pin allows; the three east pins after, as soon as they clear the package), so
    no two cross and each keeps 0.22 mm from its neighbours.  Planar by design (the '541 takes its
    channels reversed); a router left RP_D2 open in this corner (V2)."""
    (ux, uy, rot), P = rp_frame(board)
    assert rot == 90, 'data_rp_fan is drawn for the RP at rotation 90'
    u = pads_of(board, 'U_BUF')
    pins = [P[str(D.RP_GPIO_PIN[16 + bit])] for bit in range(8)]
    south = [k for k, p in enumerate(pins) if abs(p.cy - uy) > abs(p.cx - ux)]
    assert south == list(range(len(south))), 'data_rp_fan: the south pins must come first'
    # the south pins' diagonals, fixed from the last one, which starts right at its pad end: each line
    # west of it starts 0.2 mm lower (0.6 mm of c against 0.4 mm of pin pitch)
    ls = pins[south[-1]]
    c_last = ls.cx - (ls.cy + ls.hh + 0.15)
    out, c_prev = [], None
    for bit, p in enumerate(pins):
        net = NET('RP_D%d' % bit)
        t = next(q for q in u.values() if q.net == net)
        assert p.net == net and t.cy > p.cy
        top = t.cy - t.hh                                         # the '541 pad's north end
        if bit in south:                                          # south side: out south, then the diagonal
            c = c_last - DATA_FAN_DC * (south[-1] - bit)
            start = (p.cx, p.cx - c)
        else:                                                     # east side: out east, then the diagonal
            x0 = p.cx + p.hw + 0.15
            c = max(c_prev + DATA_FAN_DC, x0 - p.cy)
            start = (p.cy + c, p.cy)
        assert c_prev is None or c - c_prev >= DATA_FAN_DC - 1e-6, ('data_rp_fan: lines too close', bit)
        end = (t.cx, t.cx - c)
        assert end[1] < top - 0.3, ('data_rp_fan: the diagonal reaches the row too late', bit)
        out += path([(p.cx, p.cy), start, end, (t.cx, t.cy)], 0.2, 'F.Cu', net, ('dfanrp', bit))
        c_prev = c
    return out


SWD_COLS = {'35': 5.75, '34': 6.15, '33': 6.55}   # RUN, SWDIO, SWCLK: the column each turns north on (RP frame)
SWD_TP = {'33': 'TP_SWCLK', '34': 'TP_SWDIO', '35': 'TP_RUN'}


def swd_escape(board):
    """SWCLK, SWDIO and RUN (pins 33-35, east side south to north at rotation 90) out east and north as
    a 0.4 mm ribbon -- RUN, the northern pin, turning first and innermost, SWCLK outermost -- clear of
    XOUT (pin 31, which leaves east below them into its upright 1k) and of the 1k itself, then each
    to its pad in the row north (TP_RUN west .. TP_SWCLK east): planar, drawn, locked.  (The A*
    pre-route took them one by one, and its first diagonal walled in the other two.)"""
    (ux, uy, rot), P = rp_frame(board)
    assert rot == 90, 'swd_escape is drawn for the RP at rotation 90'
    out = []
    for num, col in SWD_COLS.items():
        p = P[num]
        tp = pads_of(board, SWD_TP[num])['1']
        assert p.net == tp.net, (num, p.net, tp.net)
        cx = ux + col
        y_turn = tp.cy + 1.6 + abs(tp.cx - cx)                   # leave the column for the pad at 45 degrees
        pts = [(p.cx, p.cy), (cx, p.cy), (cx, y_turn), (tp.cx, tp.cy + 1.6), (tp.cx, tp.cy)]
        out += path(pts, 0.2, 'F.Cu', p.net, ('swd', num))
    return out


def usbc_link(board):
    """The USB-C receptacle's data pads join, drawn (FujiNet-ChannelF Rev0): the row runs D+ (B6),
    D- (A7), D+ (A6), D- (B7) at 0.5 mm, so one pair must change layer at the pins.  D+ joins on F.Cu
    in a 0.15 mm U under the pads; D- drops through a 0.45 mm via under each of its pads -- A7's inside
    the U -- and the two vias join on B.Cu.  The routers take D+ from the U and D- from either via."""
    j = footprint_of(board, K['J_USB'])
    pads, _ = board_pads([j])
    smd = [p for p in pads if not p.th and p.net in (NET('UBRG_DP'), NET('UBRG_DM'))]
    dp = sorted((p for p in smd if p.net == NET('UBRG_DP')), key=lambda p: p.cx)
    dm = sorted((p for p in smd if p.net == NET('UBRG_DM')), key=lambda p: p.cx)
    assert len(dp) == len(dm) == 2, 'usbc_link: the pad row changed'
    if not dp[0].cx < dm[0].cx < dp[1].cx < dm[1].cx:     # turned 180: mirror the roles
        dp, dm = dm, dp
    assert dp[0].cx < dm[0].cx < dp[1].cx < dm[1].cx, 'usbc_link: the pad row changed'
    sgn = 1 if dp[0].cy > PLACE[K['J_USB']][1] else -1          # away from the receptacle body
    bot = dp[0].cy + sgn * dp[0].hh                              # the pads' outer ends
    v1 = (dm[0].cx, round(bot + sgn * 0.33, 4))
    v2 = (dm[1].cx, round(bot + sgn * 0.58, 4))
    yu = round(v1[1] + sgn * 0.5, 4)
    out = []
    u = [(dp[0].cx, dp[0].cy), (dp[0].cx, yu), (dp[1].cx, yu), (dp[1].cx, dp[1].cy)]
    out += [seg(*u[i], *u[i + 1], 0.15, 'F.Cu', dp[0].net, ('usbc', 'dp', i)) for i in range(3)]
    for k, (p, v) in enumerate(((dm[0], v1), (dm[1], v2))):
        out.append(seg(p.cx, p.cy, *v, 0.15, 'F.Cu', p.net, ('usbc', 'dms', k)))
        out.append(via(*v, p.net, ('usbc', 'dmv', k), 0.5, 0.25))
    out.append(seg(*v1, *v2, 0.2, 'B.Cu', dm[0].net, ('usbc', 'dmb')))
    return out


def bridge_link(board):
    """The USB-C pair's last stretch, USBLC6 (rotation 90: D- west, D+ east, out of its south pins 1 / 3) to
    the CP2102N (rotation 270: D- 5 / D+ 4 on its top row, between VDD 6 west and GND 3 east), drawn: at
    the QFN's 0.5 mm pitch neither router threads D- between VDD and D+ (S5 / S6 left it open).  D- drops
    past the USBLC6's GND pad, jogs 45 degrees onto pad 5's column and drops straight in; D+ drops on its
    own column, then 45 degrees onto pad 4 above the GND pad's end."""
    e_, u_ = footprint_of(board, K['U_ESD']), footprint_of(board, K['U_UART'])
    pads, _ = board_pads([e_, u_])
    P = {(p.ref, p.num): p for p in pads}
    p1, p3 = P[(K['U_ESD'], '1')], P[(K['U_ESD'], '3')]
    c5, c4 = P[(K['U_UART'], '5')], P[(K['U_UART'], '4')]
    assert p1.net == c5.net == NET('UBRG_DM') and p3.net == c4.net == NET('UBRG_DP'), 'bridge_link: nets'
    assert p1.cx < c5.cx < c4.cx < p3.cx and p1.cy < c5.cy - 3.0, 'bridge_link: the pads changed'
    top = round(c4.cy - c4.hh, 4)                       # the top row's outer ends
    yj = round(p1.cy + p1.hh + 0.3, 4)                  # past the GND pad (2) beside pin 1 before the jog
    out = path([(p1.cx, p1.cy), (p1.cx, yj), (c5.cx, round(yj + (c5.cx - p1.cx), 4)), (c5.cx, c5.cy)],
               0.2, 'F.Cu', p1.net, ('brg', 'dm'))
    out += path([(p3.cx, p3.cy), (p3.cx, round(top - (p3.cx - c4.cx), 4)), (c4.cx, top), (c4.cx, c4.cy)],
                0.2, 'F.Cu', p3.net, ('brg', 'dp'))
    # the USBLC6 is flow-through: 6 / 1 (D-) and 4 / 3 (D+) are one line inside the package, but the
    # routers see two pads to join.  Joined straight under the body, VBUS (5) dropping through a via
    # between the rows: left to Freerouting (S7), VBUS took the gap between 4 and 3 and D+ reached pin 3
    # by a 20 mm loop round the receptacle.
    p6, p4, p5, p2 = (P[(K['U_ESD'], n)] for n in ('6', '4', '5', '2'))
    assert p6.net == p1.net and p4.net == p3.net and p5.net == NET('VBUS') and p2.net == 'GND', 'bridge_link: USBLC6 pins'
    assert abs(p6.cx - p1.cx) < 1e-3 and abs(p4.cx - p3.cx) < 1e-3 and abs(p5.cx - p2.cx) < 1e-3, 'bridge_link: USBLC6 rotation'
    out += [seg(p6.cx, p6.cy, p1.cx, p1.cy, 0.25, 'F.Cu', p1.net, ('brg', 'esd_dm')),
            seg(p4.cx, p4.cy, p3.cx, p3.cy, 0.25, 'F.Cu', p3.net, ('brg', 'esd_dp'))]
    vy = round((p5.cy + p2.cy) / 2, 4)
    out += [seg(p5.cx, p5.cy, p5.cx, vy, 0.5, 'F.Cu', p5.net, ('brg', 'vbus')),
            via(p5.cx, vy, p5.net, ('brg', 'vbusv'))]
    # ST's 100 nF at pin 5 (CBUS in the datasheet's layout figure): C_VBUSHF east of the package, joined to
    # pin 5's via over B.Cu and its own via (D+'s join is between them on F.Cu)
    cb = footprint_of(board, K['C_VBUSHF'])
    c1 = {p.num: p for p in board_pads([cb])[0]}['1']
    assert c1.net == p5.net and c1.cx > p3.cx + 1.0 and c1.cy > vy, 'bridge_link: C_VBUSHF moved'
    out += [seg(p5.cx, vy, c1.cx, vy, 0.5, 'B.Cu', p5.net, ('brg', 'cbus_b')),
            via(c1.cx, vy, p5.net, ('brg', 'cbusv')),
            seg(c1.cx, vy, c1.cx, c1.cy, 0.5, 'F.Cu', p5.net, ('brg', 'cbus_f'))]
    return out


def antenna_keepout():
    """The ESP32-S3 antenna keep-out again as BOARD rule areas, one per copper layer: the module footprint's
    own zone (the antenna plus Espressif's 15 mm) is not enforced by KiCad 10's DRC once the project's
    footprint library is loaded (tried 2026-10-11: the same board reports 'items not allowed (keepout area
    of U6)' without the library, nothing with it), so the DRC gate, stitch_gnd's DRC filter and the routers
    would miss it.  Pads and footprints allowed: the module itself sits in it."""
    sx, sy, _ = PLACE[K['U_S3']]
    pts = [(sx - 24.0, Y0 - 1.0), (sx + 24.0, Y0 - 1.0), (sx + 24.0, sy - 6.75), (sx - 24.0, sy - 6.75)]
    return [zone('antenna_keepout', None, L, pts, keepout=True) for L in COPPER]


def buck_loop(board):
    """The AP63203's input loop drawn on F.Cu (FujiNet-ChannelF Rev0; its datasheet: the input capacitor
    as close to VIN and GND as possible): EN (2) strapped to VIN (3); VIN and GND (4) straight down the
    stack of the 100 nF and the two 22 uF under the IC as 0.6 mm rails; the plane vias at the stack's far
    end, two per rail, so the switching current closes on the top layer and not through In1 / In2."""
    stack = ('C_BINHF', 'C_BIN', 'C_5VBULK')
    u = footprint_of(board, K['U_BUCK'])
    caps = [footprint_of(board, K[k]) for k in stack]
    pads, _ = board_pads([u] + caps)
    P = {(p.ref, p.num): p for p in pads}
    ur = K['U_BUCK']
    vin, en, gnd = P[(ur, '3')], P[(ur, '2')], P[(ur, '4')]
    assert vin.net == en.net == NET('+5V') and gnd.net == 'GND'
    out = [seg(en.cx, en.cy, vin.cx, vin.cy, 0.3, 'F.Cu', vin.net, ('bk', 'en'))]
    for name, top, num in (('v', vin, '1'), ('g', gnd, '2')):
        chain = [top] + [P[(K[k], num)] for k in stack]
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


def tp_dvdd_link(board, graft):
    """TP_DVDD (the core rail's bring-up pad, north-west of the RP) to the graft's nearest DVDD via: a
    via just south of the pad, then B.Cu.  Drawn: the grid finisher finds no way through the regulator
    corner's locked copper, and the S3's USB pair, routed past the pad, walls it in (S1)."""
    tp = next(p for p in board_pads([footprint_of(board, K['TP_DVDD'])])[0] if p.net == NET('DVDD'))
    gv = [(float(find(e, 'at')[1]), float(find(e, 'at')[2])) for e in graft
          if e[0] == 'via' and str(find(e, 'net')[1]) == NET('DVDD')]
    tx, ty = min(gv, key=lambda v: math.dist(v, (tp.cx, tp.cy)))
    vy = round(tp.cy + tp.hh + 0.75, 4)
    return [seg(tp.cx, tp.cy, tp.cx, vy, 0.3, 'F.Cu', tp.net, ('tpdv', 'f')),
            via(tp.cx, vy, tp.net, ('tpdv', 'v')),
            seg(tp.cx, vy, tx, ty, 0.3, 'B.Cu', tp.net, ('tpdv', 'b'))]


def mux_link(board):
    """The TPS2116 at rotation 270, its two pin rows north (PR1, VIN1, VOUT, GND) and south (MODE, VIN2,
    VOUT, ST), on the CONS_5V island: drawn under the body, the two joins neither router finds at the
    0.5 mm pitch -- VOUT 2 to VOUT 7 straight across, MODE 5 to VIN1 3 diagonally (priority mode: MODE on
    VIN1, datasheet 7.6.1) -- and VOUT's stub north out of the island to its +5V plane via."""
    u = footprint_of(board, K['U_MUX'])
    ux, uy, _ = PLACE[K['U_MUX']]
    pads, _ = board_pads([u])
    P = {p.num: p for p in pads}
    v2, v7, i3, m5 = P['2'], P['7'], P['3'], P['5']
    assert v2.net == v7.net == NET('+5V') and i3.net == m5.net == NET('VBUS'), 'mux_link: nets'
    assert abs(v2.cx - v7.cx) < 1e-3 and v2.cy < uy < v7.cy, 'mux_link: VOUT 2 north, 7 south, same column'
    assert i3.cy < uy < m5.cy, 'mux_link: VIN1 north, MODE south'
    inner = lambda p: (p.cx, round(p.cy + (p.hh if p.cy < uy else -p.hh), 4))
    out = [seg(v2.cx, v2.cy, v7.cx, v7.cy, 0.25, 'F.Cu', v2.net, ('mux', 'vout'))]
    a, c = inner(m5), inner(i3)
    out += [seg(m5.cx, m5.cy, *a, 0.2, 'F.Cu', m5.net, ('mux', 'mode', 0)),
            seg(*a, *c, 0.2, 'F.Cu', m5.net, ('mux', 'mode', 1)),
            seg(*c, i3.cx, i3.cy, 0.2, 'F.Cu', m5.net, ('mux', 'mode', 2))]
    vy = round(v2.cy - v2.hh - 0.9, 4)
    out += [seg(v2.cx, v2.cy, v2.cx, vy, 0.25, 'F.Cu', v2.net, ('mux', 'vstub')),
            via(v2.cx, vy, v2.net, ('mux', 'vvia'))]
    return out


# ---- In2 ---------------------------------------------------------------------------
# +5V (the mux's output: the glue, both regulators, the WS2812) is the In2 plane's base; islands, highest
# priority first: the console's 5 V from finger 15 to the mux, the RP's +3V3 under the RP2354B and its
# LDO, the S3 side's +3V3_S3 under the top band
ISLANDS = [('CONS_5V', 'CONS5V_POLY'), ('+3V3', 'RP3V3_POLY'), ('+3V3_S3', 'S3_POLY')]
IN2_BASE = '+5V'


def in2_net_at(x, y):
    """Which net the In2 plane carries at (x, y)."""
    for net, poly in ISLANDS:
        if point_in_poly(x, y, getattr(PL, poly)):
            return net
    return IN2_BASE


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
    def via_spot(p):
        if min(p.hw, p.hh) <= 0.15:
            fx, fy = p.fp_xy
            if p.hh > p.hw:
                return p.cx, p.cy + math.copysign(2.0, p.cy - fy)
            return p.cx + math.copysign(2.0, p.cx - fx), p.cy
        return p.cx, p.cy
    skip = set(served)
    for p in pads:
        if p.net in (NET('+3V3'), NET('+3V3_S3'), NET('+5V'), NET('CONS_5V')) and NET(in2_net_at(*via_spot(p))) != p.net:
            skip.add(id(p))
        if p.net == NET('DVDD') or p.net == NET('VBUS'):
            skip.add(id(p))                    # DVDD rides the rings / graft, VBUS is routed
        if p.ref == K['U_RP'] and p.num != '81':
            skip.add(id(p))                    # every RP supply pin is on its ring (rp_support), PGND on the graft
        if p.ref in GRAFT_REFS and (p.ref, p.num) != (K['R_AVDD'], '1'):
            skip.add(id(p))                    # the graft carries its own pours, traces and vias
    keep = [crt[K[k]] for k in ('J_USB', 'J_SD', 'U_S3', 'SW_RESET', 'SW_BOOTSEL', 'SW_S3EN', 'SW_S3BOOT')
            if K[k] in crt]
    keep.append((ux - UNDER, uy - UNDER, ux + UNDER, uy + UNDER))   # no fan-out vias under the RP2354B
    sx, sy, _ = PLACE[K['U_S3']]                                      # nor in the S3 antenna keep-out
    keep.append((sx - 24.0, Y0 - 1.0, sx + 24.0, sy - 6.75 + 0.3))   # (the module footprint's zone)
    holes = [(x, y, HOLE_CU) for x, y, d in HOLES]
    vias, segs, failed = fanout.plan(pads, keep, (X0, Y0, X1, KEEP_Y), BLADE_Y, holes, skip_refs=(K['J_EDGE'],),
                                     extra_segs=extra_segs, extra_vias=extra_vias, skip_pads=skip)
    for i, (x, y, n) in enumerate(vias):
        board.append(via(x, y, n, ('fv', i), fanout.VIA_D, fanout.VIA_DRILL))
    for i, (x0, y0, x1, y1, n, w) in enumerate(segs):
        board.append(seg(x0, y0, x1, y1, round(w, 3), 'F.Cu', n, ('fs', i)))
    print('fan-out: %d vias, %d stubs%s' % (len(vias), len(segs),
          ('; FAILED: ' + ' '.join(failed)) if failed else ''))


def outline():
    """Edge.Cuts: the straight edges and the two notches as arcs."""
    g = []
    for i, it in enumerate(OUTLINE_ITEMS):
        if it[0] == 'line':
            g.append(['gr_line', ['start', *it[1]], ['end', *it[2]], ['stroke', ['width', 0.1], ['type', 'default']],
                      ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', i)]])
        else:
            g.append(['gr_arc', ['start', *it[1]], ['mid', *it[2]], ['end', *it[3]],
                      ['stroke', ['width', 0.1], ['type', 'default']], ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', i)]])
    return g


def zone(name, net, layer, pts, keepout=False, priority=0, no_parts=False, clearance=0.25, min_thick=0.25,
         solid=False):
    z = ['zone', ['net', Q(net)] if net else ['net', Q('')], ['layer', Q(layer)], ['uuid', uid('zone', name, layer)],
         ['name', Q(name)], ['hatch', 'edge', 0.5]]
    if priority:
        z.append(['priority', priority])
    z += [['connect_pads'] + (['yes'] if solid else []) + [['clearance', 0 if keepout else clearance]],
          ['min_thickness', min_thick]]
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
    ('PWR', 0.15, 0.5, 0.8, 0.4, ['+5V', 'CONS_5V', '+3V3', '+3V3_S3', 'BUCK_SW']),
    ('VBUS', 0.15, 0.5, 0.6, 0.3, ['VBUS']),           # the cart's whole draw when USB powers it (~0.5 A)
    ('USB', 0.15, 0.25, 0.6, 0.3, ['USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM']),
]
CORNER = ['DVDD', 'RP_LX', 'VREG_AVDD']   # the RP2350 core-regulator copper (Raspberry Pi's 0402 corner)


def configure_project():
    """Design rules + net classes in the .kicad_pro (JLCPCB 4-layer capable)."""
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    r = pro['board']['design_settings']['rules']
    # JLCPCB multilayer: trace/space 0.09, via 0.25/0.15, annular 0.125, copper-edge 0.2; the
    # rules sit above every one of those.  No mask-bridge check: JLC opens the mask as one
    # window across 0.4 mm-pitch pins (QFN-80) rather than dam them.
    r.update({'min_clearance': 0.12, 'min_copper_edge_clearance': 0.25, 'min_track_width': 0.1,
              'min_via_diameter': 0.5, 'min_through_hole_diameter': 0.25, 'min_hole_clearance': 0.25,
              'min_hole_to_hole': 0.25, 'min_via_annular_width': 0.125, 'solder_mask_min_width': 0.0,
              'solder_mask_clearance': 0.0, 'solder_mask_to_copper_clearance': 0.0})
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
    solid = ' || '.join("A.memberOfFootprint('%s')" % K[k] for k in ('U_RP', 'U_BUF', 'U_OR', 'U_INV', 'U_LDO'))
    open(os.path.join(PRJ, D.PROJECT + '.kicad_dru'), 'w').write(
        '(version 1)\n'
        # Raspberry Pi's regulator corner (0402 parts, its own 0.15 mm pours) may use the fab minimum
        '(rule "rp2350_core_corner"\n'
        '\t(condition "%s")\n'
        '\t(constraint clearance (min 0.12mm)))\n'
        # 0.12 mm: the floor the last links at the RP's 0.4 mm-pitch pins need (finish_route --neck);
        # the routers aim for the 0.15 mm netclass value everywhere else.  JLCPCB 4-layer minimum: 0.09
        '(rule "default_clearance"\n'
        '\t(condition "%s")\n'
        '\t(constraint clearance (min 0.12mm)))\n'
        # the QFN's exposed pad, the logic and regulator grounds join the pours solidly
        '(rule "gnd_solid_under_ics"\n'
        '\t(condition "A.NetName == \'GND\' && (%s)")\n'
        '\t(constraint zone_connection solid))\n'
        # the fingers are 0.70 mm from the bevelled edge by design (FliP)
        '(rule "finger_edge"\n'
        '\t(condition "A.memberOfFootprint(\'%s\')")\n'
        '\t(constraint edge_clearance (min %gmm)))\n' % (corner_a, corner_ab, solid, K['J_EDGE'],
                                                         EG.FINGER_EDGE_CLEAR))


def write_case_anchors():
    """case/board-anchors.scad: the shell openings follow the placement."""
    def at(key):
        x, y, _ = PLACE[K[key]]
        return x, y
    lines = ['// GENERATED by tools/gen_pcb.py from tools/placement.py and tools/edge_geom.py -- do not edit.',
             '// KiCad board frame (mm, y down), seen from F.Cu (the parts face; the console\'s FRONT): x %g..%g,'
             % (X0, X1),
             '// y %g (top edge, outside the console) .. %g (the insertion edge: the full width enters the slot).'
             % (Y0, Y1),
             '// The 22 contacts are on the BOTTOM face (B.Cu, toward the back of the console), %g..%g mm in.'
             % (EG.LAND_Y0, EG.LAND_Y1),
             'pcb_x0 = %g; pcb_x1 = %g; pcb_y0 = %g; pcb_y1 = %g; pcb_t = %g;' % (X0, X1, Y0, Y1, THICKNESS),
             'pcb_outline = [%s];   // the notches and the rounded top corners sampled' % ', '.join(
                 '[%g, %g]' % p for p in OUTLINE),
             'pcb_holes = [%s];   // [x, y, diameter]: FliP\'s shell-post holes, kept as anchors' % ', '.join(
                 '[%g, %g, %g]' % h for h in HOLES),
             'pcb_notches = [[%g, %g, %g], [%g, %g, %g]];   // [x, y, r]: side notches (the shell\'s rivets)'
             % (_cl[0], NOTCH_Y, EG.NOTCH_R, _cr[0], NOTCH_Y, EG.NOTCH_R),
             'parts_min_y = %g;   // no part south of this (%g mm in): the board below the shell enters the slot'
             % (KEEP_Y, EG.PARTS_Y),
             'parts_max_h = 3.3;   // tallest assembled part on F.Cu (USB-C 3.26; the ESP32-S3 module 3.1); B.Cu none',
             'dbg_header_h = 8.5;  // J_DBG (DNP): a 1x03 2.54 mm header, 8.5 mm above F.Cu when fitted for bring-up',
             'esp32_ant  = [%g, %g];   // ESP32-S3 antenna centre, at the top edge: no metal within 15 mm of it'
             % (at('U_S3')[0], Y0 + 3.0),
             'usb_c      = [%g, %g];   // USB-C (power + S3 programming) exits the top edge' % (at('J_USB')[0], Y0),
             'microsd    = [%g, %g];   // microSD card slot at the top edge (push-push)' % (at('J_SD')[0], Y0),
             'sw_s3en    = [%g, %g];   // ESP32-S3 EN (reset the FujiNet)' % at('SW_S3EN'),
             'sw_bootsel = [%g, %g];   // RP BOOTSEL (hold while pressing RESET)' % at('SW_BOOTSEL'),
             'sw_reset   = [%g, %g];   // RESET: the RP2354B and the ESP32-S3 together' % at('SW_RESET'),
             'sw_s3boot  = [%g, %g];   // ESP32-S3 BOOT (IO0)' % at('SW_S3BOOT'),
             'led_rp     = [%g, %g];   // RP activity LED (window / light pipe)' % at('D_LED'),
             'led_status = [%g, %g];   // WS2812 status light (WiFi / bus activity)' % at('D_WS'),
             'dbg_header = [%g, %g];   // debug UART (DNP): fit for bring-up' % at('J_DBG'),
             'label_xy   = [%g, %g];   // label recess centre: a face area clear of buttons and LEDs' % PL.LABEL[0],
             'label_wh   = [%g, %g];   // label recess size' % PL.LABEL[1], '']
    os.makedirs(os.path.join(PRJ, 'case'), exist_ok=True)
    open(os.path.join(PRJ, 'case', 'board-anchors.scad'), 'w').write('\n'.join(lines))


def check_parts_inside(board):
    """Every courtyard inside the outline, 0.3 mm in (0.1 at the top edge), north of KEEP_Y (the band is
    the edge's alone), clear of the shell posts' rings, and no two courtyards overlapping.  The USB-C
    is the one part past the top edge: HRO's layout has its shell face overhang the edge by 0.46 mm
    (its courtyard by 0.96)."""
    _, crt = board_pads(board)
    bad = []
    inner = lambda x, y: all(point_in_poly(x + dx, max(y + dy, Y0 + 0.31), OUTLINE)
                             for dx in (-0.3, 0.3) for dy in (-0.3, 0.3))
    for p in D.PARTS:
        if p.ref == K['J_EDGE'] or p.ref not in crt:
            continue
        x0, y0, x1, y1 = crt[p.ref]
        if p.key == 'J_USB':
            y0 = max(y0, Y0 + 0.1)
        corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1), ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)]
        if not all(inner(x, y) for x, y in corners) or y0 < Y0 + 0.1 or y1 > KEEP_Y - 0.01:
            bad.append('%s (%s) courtyard %.1f,%.1f..%.1f,%.1f outside the body' % (p.ref, p.key, x0, y0, x1, y1))
        for hx, hy, hd in HOLES:
            cx, cy = min(max(hx, x0), x1), min(max(hy, y0), y1)
            if math.hypot(cx - hx, cy - hy) < HOLE_KEEP:
                bad.append('%s (%s) within %.1f mm of the hole at %g,%g' % (p.ref, p.key, HOLE_KEEP, hx, hy))
    refs = sorted(r for r in crt if (r in D.BY_REF and r != K['J_EDGE']) or r.startswith('FID'))
    for r in refs:     # the fiducials too: clear of the posts
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
    the uuids of the units drawn there; the footprint path takes the lowest of those units.
    Cross-checked against the netlist kicad-cli wrote."""
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
    return ['title_block', ['title', Q('FujiNet RCA Studio II Rev0')], ['date', Q(gen_sch.DATE)], ['rev', Q('0')],
            ['company', Q('FujiNet')],
            ['comment', 1, Q('Generated by tools/gen_pcb.py + tools/route_board.sh - edit those, not this file')],
            ['comment', 2, Q('CERN-OHL-W-2.0 (regulator corner: Raspberry Pi RP2350 minimal design, MIT)')],
            ['comment', 3, Q(gen_sch.COMMENT3)]]


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
    graft_parts()
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
        path_ = '/%s/%s' % (gen_sch.uid('sheet', stem), gen_sch.uid(stem, p.ref, u))
        path_ = path_.replace('"', '')
        ds = p.ds
        for pr in findall(syms[p.lib_id], 'property'):
            if pr[1] == 'Datasheet' and not ds:
                ds = str(pr[2])
        board.append(instance(p, x, y, r, path_, '/%s/' % stem, stem + '.kicad_sch', ds))
    for name, x, y in FIDUCIALS:
        board.append(board_only(name, 'Fiducial_1mm_Mask2mm', x, y, 'assembly fiducial'))
    for i, (x, y, d) in enumerate(HOLES):
        board.append(board_only('H%d' % (i + 1), 'MountingHole_%gmm_NPTH' % d, x, y, 'Studio II shell post'))
    check_parts_inside(board)
    rs, rzones = rp_support(board)
    gc, gzones = graft_copper()
    extra = (finger_stubs(board) + address_twist(board) + data_fanin(board) + rs + gc + cap_links(board)
             + swd_escape(board) + data_rp_fan(board) + usbc_link(board) + bridge_link(board) + buck_loop(board)
             + mux_link(board)
             + tp_dvdd_link(board, gc))
    board += extra
    add_fanout(board, extra)
    board += outline()
    board += rzones + gzones
    # the finger field: fingers only -- no tracks, vias or pour on any layer (pads allowed); the
    # stubs leave it from inside each finger.  F.Cu and the inner layers over the field stay bare.
    fx0, fx1 = X0 - 1.0, X1 + 1.0
    field = [(fx0, PAD_TOP_Y + 0.5), (fx1, PAD_TOP_Y + 0.5), (fx1, Y1 + 1), (fx0, Y1 + 1)]
    field_all = [(fx0, FIELD_Y), (fx1, FIELD_Y), (fx1, Y1 + 1), (fx0, Y1 + 1)]
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('field_fingers_only_' + L[0], None, L, field, keepout=True))
    for L in ('In1.Cu', 'In2.Cu', 'F.Cu'):
        board.append(zone('field_no_copper_' + L[:3].replace('.', ''), None, L, field_all, keepout=True))
    z = zone('field_no_pour_B', None, 'B.Cu', field_all, keepout=True)   # B.Cu: the stubs cross it, no pour
    find(z, 'keepout')[1:] = [['tracks', 'allowed'], ['vias', 'allowed'], ['pads', 'allowed'],
                              ['copperpour', 'not_allowed'], ['footprints', 'allowed']]
    board.append(z)
    for i, (x, y, d) in enumerate(HOLES):   # the shell posts: no copper near the hole
        for L in COPPER:
            board.append(zone('post_%d' % i, None, L, circle_pts(x, y, HOLE_CU, 16), keepout=True))
    board += antenna_keepout()
    board.append(zone('GND_plane', 'GND', 'In1.Cu', BODY))
    board.append(zone('5V_plane', NET(IN2_BASE), 'In2.Cu', BODY))
    for k, (net, poly) in enumerate(ISLANDS):
        board.append(zone('%s_island_%d' % (net.strip('+'), k), NET(net), 'In2.Cu', getattr(PL, poly),
                          priority=len(ISLANDS) - k))
    tx, ty = PL.TITLE_XY                       # clear of parts (placement.py)
    board.append(text('FujiNet RCA Studio II Rev0', tx, ty - 1.4, 'F.SilkS', 1.5))
    board.append(text('RP2354B + ESP32-S3 FujiNet cart', tx, ty + 1.2, 'F.SilkS', 1.0))
    board.append(text('CERN-OHL-W-2.0  fujinet.online', XC, KEEP_Y - 4.0, 'B.SilkS', 1.0, mirror=True))
    board.append(text('CONTACTS TO THE BACK OF THE CONSOLE', XC, KEEP_Y - 1.6, 'B.SilkS', 1.0, mirror=True))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
