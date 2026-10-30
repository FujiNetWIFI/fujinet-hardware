#!/usr/bin/env python3
"""Generate FujiNet-O2-Rev0.kicad_pcb (placed, unrouted) from design.py.

Board (tools/edge_geom.py; tools/placement.py owns the frame): x 68.5..131.5, y 45..130, bwack's /
PicoPAC's 63 x 85 Videopac outline -- the full bottom edge carries the 2x15 gold fingers at y = 130
(the insertion edge), its corners chamfered, two side notches and two 5 mm shell-post holes.  No
parts below the shell's bottom (edge_geom.PARTS_Y) or near a post.  1.6 mm, 4 copper layers
(JLC04161H-7628):
  F.Cu  signals + GND pour            (pins 1-15: T0, DB0-DB7, A10, P14, P11, P10, A11, A9)
  In1   GND plane
  In2   +5V plane (the mux's output), with a +3V3_RP island under the RP2354B, its ring and its LDO,
        a +3V3 island (the buck: the S3 band along the top and a strip down the right edge to the
        buck) and a CONS_5V island from the +5V finger up under the mux
  B.Cu  signals + GND pour            (pins A-R behind them)
The finger field is a rule area on F/B (fingers only); the inner planes stop above it.  The
ESP32-S3 antenna (the top 6 mm of the module) sits flush with the top edge over a band that is
copper-free on every layer.

The RP2354B's supplies join under the package in two F.Cu rings (rp_support, FujiNet-StudioII
Rev0's), and its core-regulator corner is Raspberry Pi's own RP2350A minimal-design layout moved
onto the QFN-80 (tools/rpi_core_graft.sexpr, MIT): its parts and copper are placed relative to the
RP2354B and turned with it (datasheet 6.3.8: "follow this layout as closely as possible").

Footprints are written as S-expressions (the SWIG pcbnew bindings are not reliable under Python
3.14); route.py does the DSN/SES round trip and the zone fills through pcbnew.

Usage: python3 tools/gen_pcb.py
"""
import os, sys, math, copy, json, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
import design as D
import gen_sch

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')

# ---- geometry (mm, KiCad frame: y down) -----------------------------------
import edge_geom as EG
import placement as PL
X0, Y0, X1, Y1 = PL.X0, PL.Y0, PL.X1, PL.Y_EDGE
XC = PL.XC
FINGER_Y = Y1 - EG.FIELD_TOP    # finger field: no tracks / vias / pour on F.Cu or B.Cu below this
TAB_Y = FINGER_Y - 0.5    # routers stay above this; a finger is entered at its neck
BLADE_Y = TAB_Y           # (fanout.py name)
PLANE_Y = Y1 - EG.PLANE_Y # inner planes stop short of the fingers and the bevel
PARTS_MAX_Y = Y1 - EG.PARTS_Y   # courtyards above the shell's bottom
THICKNESS = EG.THICKNESS
HOLES = list(PL.HOLES)    # the shell posts: (x, y, diameter)
HOLE_CU = EG.HOLE_D / 2 + 0.6   # no copper within this radius of a post
_S3X, _S3Y = PL.S3
ANT_KEEP = (_S3X - 24.0, Y0, X1, _S3Y - 6.75)     # antenna band: the module footprint's keep-out (its antenna end, 24 mm each side)
PWR_LAYER = 'In2.Cu'
UNDER = 4.6               # half-size of the square under the RP2354B the finisher keeps off F.Cu
RP_KEEP = 4.45            # half-size of the square under the RP2354B Freerouting never enters (route.rp_keepout)
# Raspberry Pi's regulator corner (RP rotation-0 frame): no F.Cu GND pour here -- the RP2350 datasheet
# 6.3.8.1: "cut away any extra copper underneath the inductor", keep the switching loops "isolated (i.e.
# only connect to main GND at one point)": the graft's PGND pour joins main GND through its own two vias
REG_CUT = [(1.75, -4.6), (6.1, -4.6), (6.1, -10.3), (1.75, -10.3)]
K = D.KEY

# the RP2354B's supply rings under the package (F.Cu, after Raspberry Pi's minimal design; FujiNet-
# StudioII Rev0's): the exposed pad (GND, 3.4 mm) in the middle, a DVDD ring round it, a +3V3_RP ring
# round that, the pin rows' inner ends at 4.55 -- every supply pin stubs inward to its ring
RING_DVDD = 2.75    # the DVDD zone: a square of this half-size (the exposed pad cuts its middle out)
RING_3V3 = 3.9      # the +3V3_RP zone: this half-size (the DVDD zone, higher priority, cuts its middle)
STUB_3V3 = 3.35     # a +3V3_RP pin's stub ends here (mid-ring)
STUB_DVDD = 2.3     # a DVDD pin's stub ends here (mid-ring, through the +3V3_RP ring)


def outline_pts():
    """Board outline, clockwise from the top-left (y down): the top corners rounded (edge_geom.TOP_R),
    the side notches (edge_geom.NOTCH_L / NOTCH_R, seen from F.Cu) and the chamfered bottom corners."""
    r = EG.TOP_R
    arc = lambda cx, cy, a0, a1: [(round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / 6)), 4),
                                   round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / 6)), 4))
                                  for k in range(7)]
    nd = EG.NOTCH_D
    (rl, rh), (ll, lh) = EG.NOTCH_R, EG.NOTCH_L
    return (arc(X0 + r, Y0 + r, 180, 270) + arc(X1 - r, Y0 + r, 270, 360) +
            [(X1, Y1 - rh), (X1 - nd, Y1 - rh), (X1 - nd, Y1 - rl), (X1, Y1 - rl),
             (X1, Y1 - EG.CHAMF_Y), (X1 - EG.CHAMF_X, Y1), (X0 + EG.CHAMF_X, Y1), (X0, Y1 - EG.CHAMF_Y),
             (X0, Y1 - ll), (X0 + nd, Y1 - ll), (X0 + nd, Y1 - lh), (X0, Y1 - lh)])


def clip_below(pts, ymax):
    """The outline polygon cut off at y = ymax (for planes / pours)."""
    out = []
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        if ya <= ymax:
            out.append((xa, ya))
        if (ya - ymax) * (yb - ymax) < 0:
            t = (ymax - ya) / (yb - ya)
            out.append((round(xa + t * (xb - xa), 4), ymax))
    return out


OUTLINE = outline_pts()
BODY = clip_below(OUTLINE, PLANE_Y)       # planes and pours

# ref -> (x, y, rotation deg CCW)  -- top view, y down
PLACE = {}


def place(key, x, y, rot=0):
    """placement.py names parts by design.py key; PLACE is by reference."""
    PLACE[D.KEY[key]] = (round(x, 4), round(y, 4), rot % 360)


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
    """The board's (schematic's) net name -> design.py's: /cart-bus/CA0, /USB_DP, GND -> CA0, USB_DP, GND."""
    return n if n.startswith('unconnected') else n.rsplit('/', 1)[-1]


COMP_SHEET = {}  # ref -> the sheet kicad-cli files the component under ('/cart-bus/')
FULL = {}        # design.py net name -> the schematic's (board's) net name


def schematic_netlist():
    """(ref, pad) -> net name, from the generated schematic (kicad-cli), so the
    board carries exactly the schematic's nets -- hierarchical names (/cart-bus/CA0,
    /USB_DP, GND) and KiCad's own unconnected-(...) names for no-connect pins."""
    from tmpdir import tmp
    fn = tmp('gen.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    t = parse(open(fn).read())
    out = {}
    for c in findall(find(t, 'components'), 'comp'):
        COMP_SHEET[str(find(c, 'ref')[1])] = str(find(find(c, 'sheetpath'), 'names')[1])
    for n in findall(find(t, 'nets'), 'net'):
        name = str(find(n, 'name')[1])
        FULL[canon(name)] = name
        for nd in findall(n, 'node'):
            out[(str(find(nd, 'ref')[1]), str(find(nd, 'pin')[1]))] = name
    return out


def NET(n):
    """design.py's net name -> the board's."""
    if not FULL:
        NETLIST.update(schematic_netlist())
    return FULL[n]


def fp_sheet_unit(p, syms):
    """The sheet and symbol unit a footprint links to.  A part drawn on several sheets (its units
    split between them) is filed by KiCad under the first of those sheets in hierarchy order, with
    the uuid of the lowest unit drawn there; cross-checked against kicad-cli's netlist."""
    units = gen_sch.units_of(syms[p.lib_id])
    on = {u: p.unit_sheets.get(u, p.sheet) for u in units}
    stem = min(set(on.values()), key=D.SHEET_ORDER.index)
    u = min(u for u, sh in on.items() if sh == stem)
    NET('GND')
    if COMP_SHEET and COMP_SHEET.get(p.ref) != '/%s/' % stem:
        raise SystemExit('%s: design puts the footprint on /%s/, kicad-cli on %s' % (p.ref, stem, COMP_SHEET.get(p.ref)))
    return stem, u


NETLIST = {}
import re as _re
SMALL = _re.compile(r'_0603_|_0805_|0402|SOD-523|SOT-23|SOT-363|SOT-583|R_Array|AOTA|Crystal_SMD|WS2812|TSOT|TestPoint')


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
              'Datasheet': datasheet, 'Description': part.desc, 'MPN': part.mpn, 'LCSC': part.lcsc}
    if part.mfr:
        fields['Manufacturer'] = part.mfr        # the schematic carries it (gen_sch), so parity wants it too
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
        if k not in done:
            out.append(['property', Q(k), Q(v), ['at', 0, 0, rot], ['layer', Q('F.Fab')], ['hide', 'yes'],
                        ['uuid', uid(part.ref, 'prop', k)],
                        ['effects', ['font', ['size', 1.27, 1.27], ['thickness', 0.15]]]])
    if path:
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
            out.append(e)
        else:
            out.append(copy.deepcopy(e))
    out.append(['embedded_fonts', 'no'])
    return out


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


def zone(name, net, layer, pts, keepout=None, priority=0, clearance=0.25, min_thick=0.25, solid=False):
    """keepout: None (copper zone) or a dict of rule-area permissions overriding 'not_allowed'."""
    z = ['zone', ['net', Q(net or '')], ['layer', Q(layer)], ['uuid', uid('zone', name, layer)],
         ['name', Q(name)], ['hatch', 'edge', 0.5]]
    if priority:
        z.append(['priority', priority])
    z += [['connect_pads'] + (['yes'] if solid else []) + [['clearance', 0 if keepout is not None else clearance]],
          ['min_thickness', min_thick]]
    if keepout is not None:
        perm = {'tracks': 'not_allowed', 'vias': 'not_allowed', 'pads': 'allowed', 'copperpour': 'not_allowed',
                'footprints': 'allowed'}
        perm.update(keepout)
        z.append(['keepout'] + [[k, perm[k]] for k in ('tracks', 'vias', 'pads', 'copperpour', 'footprints')])
        z.append(['placement', ['enabled', 'no'], ['sheetname', Q('')]])
        z.append(['fill', ['thermal_gap', 0.5], ['thermal_bridge_width', 0.5], ['island_removal_mode', 0]])
    else:
        z.append(['fill', 'yes', ['thermal_gap', 0.3], ['thermal_bridge_width', 0.4], ['island_removal_mode', 0]])
    z.append(['polygon', ['pts'] + [['xy', round(x, 4), round(y, 4)] for x, y in pts]])
    return z


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        if (ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya):
            inside = not inside
    return inside


def footprint_of(board, ref):
    return next(e for e in board if isinstance(e, list) and e and e[0] == 'footprint'
                and any(p[1] == 'Reference' and p[2] == ref for p in findall(e, 'property')))


def mux_link(board):
    """The TPS2116 at rotation 270, its two pin rows north (PR1, VIN1, VOUT, GND) and south (MODE, VIN2,
    VOUT, ST), the south row on the CONS_5V island: drawn under the body, the two joins neither router
    finds at the 0.5 mm pitch -- VOUT 2 to VOUT 7 straight across, MODE 5 to VIN1 3 diagonally (priority
    mode: MODE on VIN1, datasheet 7.6.1) -- and VOUT's stub north out of the island to its +5V plane via
    (FujiNet-StudioII Rev0's mux_link)."""
    u = footprint_of(board, D.KEY['U_MUX'])
    ux, uy, _ = PLACE[D.KEY['U_MUX']]
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
    assert plane_net_at(v2.cx, vy) == '+5V', 'mux_link: the VOUT via must land on In2 +5V'
    out += [seg(v2.cx, v2.cy, v2.cx, vy, 0.25, 'F.Cu', v2.net, ('mux', 'vstub')),
            via(v2.cx, vy, v2.net, ('mux', 'vvia'))]
    return out


# ---- the In2 plane and its islands -----------------------------------------------------------
def plane_net_at(x, y):
    """Which net the In2 plane carries at (x, y)."""
    from placement import RP_ISLAND, S3_ISLAND, CONS5V_ISLAND
    if point_in_poly(x, y, CONS5V_ISLAND):
        return 'CONS_5V'
    if point_in_poly(x, y, RP_ISLAND):
        return D.RP_RAIL
    if point_in_poly(x, y, S3_ISLAND):
        return '+3V3'
    return '+5V'


def pads_of(board, key):
    return {p.num: p for p in board_pads([footprint_of(board, K[key])])[0]}


def path(pts, w, layer, net, key):
    return [seg(*pts[i], *pts[i + 1], w, layer, net, key + (i,)) for i in range(len(pts) - 1)]


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
      * every +3V3_RP supply pin (IOVDD x8, ADC_AVDD, VREG_VIN, USB_OTP_VDD, QSPI_IOVDD) stubs straight
        inward into the +3V3 ring, every DVDD pin (10, 32, 51) through it into the DVDD ring, so no
        supply pin needs a via among the bus pins;
      * the +3V3 ring drops to the In2 plane through a via at each of its corners;
      * the DVDD ring joins the regulator's output node (the graft's two DVDD vias by C_DVBULK /
        L_RP) through a via and a 0.6 mm B.Cu link, as the reference does (the south side's DVDD 10
        and the east side's DVDD 32 have their capacitors north, on the ring through pin 51's link);
      * the exposed pad's 3 x 3 GND via grid is fanout.py's (EP_ARRAYS)."""
    (ux, uy, rot), P = rp_frame(board)
    out = []
    p3, pdv = NET(D.RP_RAIL), NET('DVDD')
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
# (the north side; the south side is the bus)
CAP_LINKS = [('41', 'C_IOV41'), ('50', 'C_IOV50'), ('51', 'C_DV51'), ('59', 'C_ADC'), ('60', 'C_IOV60')]


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


def finger_gnd_vias(board):
    """The three GND fingers (2 on B.Cu, 25 and 27 on F.Cu) stitch straight into the In1 plane, and the
    +5V finger (4, B.Cu) into In2's CONS_5V island, at the top of their necks (the description below is
    the GND case).  The
    plane at the top of their necks.  The fingers are back to back, so a via ON
    a neck would hit the other face's neck: go 1.27 mm outboard, between columns."""
    out = []
    for e in board:
        if isinstance(e, list) and e and e[0] == 'footprint' and \
                any(p[1] == 'Reference' and p[2] == D.KEY['J_EDGE'] for p in findall(e, 'property')):
            jx, jy = float(find(e, 'at')[1]), float(find(e, 'at')[2])
            for pd in findall(e, 'pad'):
                a, sz = find(pd, 'at'), find(pd, 'size')
                if find(pd, 'net') and str(find(pd, 'net')[1]) in ('GND', 'CONS_5V') and float(sz[1]) < 1.0:    # the neck
                    nx, ny = jx + float(a[1]), round(jy + float(a[2]) - float(sz[2]) / 2 + 0.4, 4)
                    vx = round(nx + math.copysign(1.27, nx - jx), 4)
                    layer = [str(l) for l in find(pd, 'layers')[1:]][0]
                    net = str(find(pd, 'net')[1])
                    out.append(seg(nx, ny, vx, ny, 0.4, layer, net, ('fingergnds', pd[1])))
                    out.append(via(vx, ny, net, ('fingergnd', pd[1])))
    return out


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

    # a pad only gets a plane via where In2 carries its net (GND is In1, everywhere),
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
        if p.net in (NET('+5V'), NET('+3V3'), NET(D.RP_RAIL), NET('CONS_5V')) and NET(plane_net_at(*via_spot(p))) != p.net:
            skip.add(id(p))
        if p.net == NET('DVDD') or p.net == NET('VBUS'):
            skip.add(id(p))                    # DVDD rides the rings / graft, VBUS is routed
        if p.ref == K['U_RP'] and p.num != '81':
            skip.add(id(p))                    # every RP supply pin is on its ring (rp_support), PGND on the graft
        if p.ref in GRAFT_REFS and (p.ref, p.num) != (K['R_AVDD'], '1'):
            skip.add(id(p))                    # the graft carries its own pours, traces and vias
    keep = [crt[K[k]] for k in ('J_USB', 'J_SD', 'SW_RESET', 'SW_BOOTSEL', 'SW_S3EN', 'SW_S3BOOT')
            if K[k] in crt]
    keep.append((ux - UNDER, uy - UNDER, ux + UNDER, uy + UNDER))   # no fan-out vias under the RP2354B
    sx, sy, _ = PLACE[K['U_S3']]                                      # nor in the S3 antenna keep-out
    keep.append((sx - 24.0, Y0 - 1.0, sx + 24.0, max(sy - 6.75, ANT_KEEP[3]) + 1.0))   # (the module footprint's zone)
    holes = [(x, y, HOLE_CU) for x, y, d in HOLES]
    vias, segs, failed = fanout.plan(pads, keep, (X0, Y0, X1, Y1), BLADE_Y, holes,
                                     skip_refs=(K['J_EDGE'],), extra_segs=extra_segs,
                                     extra_vias=extra_vias, skip_pads=skip, outline=OUTLINE)
    for i, (x, y, n) in enumerate(vias):
        board.append(via(x, y, n, ('fv', i), fanout.VIA_D, fanout.VIA_DRILL))
    for i, (x0, y0, x1, y1, n, w) in enumerate(segs):
        board.append(seg(x0, y0, x1, y1, round(w, 3), 'F.Cu', n, ('fs', i)))
    print('fan-out: %d vias, %d stubs%s' % (len(vias), len(segs),
          ('; FAILED: ' + ' '.join(failed)) if failed else ''))


def circle_pts(x, y, r, n=16):
    return [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def outline():
    g = []
    n = len(OUTLINE)
    for i in range(n):
        a, b = OUTLINE[i], OUTLINE[(i + 1) % n]
        g.append(['gr_line', ['start', *a], ['end', *b], ['stroke', ['width', 0.1], ['type', 'default']],
                  ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', i)]])
    return g


def text(s, x, y, layer, size=1.0, mirror=False, rot=0):
    eff = ['effects', ['font', ['size', size, size], ['thickness', size * 0.15]]]
    if mirror:
        eff.append(['justify', 'mirror'])
    return ['gr_text', Q(s), ['at', x, y, rot], ['layer', Q(layer)], ['uuid', uid('text', s, layer)], eff]


# ---------------------------------------------------------------------------
from placement import do_placement  # noqa: E402  (placement table lives in its own file)


NETCLASSES = [  # name, clearance, track, via dia, via drill, nets
    ('PWR', 0.2, 0.5, 0.8, 0.4, ['+5V', 'CONS_5V', 'BUCK_SW', '+3V3']),
    # VBUS threads between the USB-C pads; 0.3 mm (~0.9 A outer) covers the board's USB draw
    ('VBUS', 0.15, 0.3, 0.6, 0.3, ['VBUS']),
    ('USB', 0.15, 0.25, 0.6, 0.3, ['USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM']),
]


def configure_project():
    """Design rules + net classes in the .kicad_pro (JLCPCB 4-layer capable)."""
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    r = pro['board']['design_settings']['rules']
    # JLCPCB multilayer: trace/space 0.09, via 0.25/0.15, annular 0.125(?), copper-edge 0.2 -- the
    # rules sit at or above each.  The RP's 0.4 mm-pitch neck-downs need 0.12 mm.
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
        nets = [NET(n) for n in nets]               # the board's (hierarchical) names
        c = dict(base)
        c.update({'name': name, 'clearance': cl, 'track_width': tw, 'via_diameter': vd, 'via_drill': vdr,
                  'priority': i})
        classes.append(c)
        patterns += [{'netclass': name, 'pattern': n} for n in nets]
    ns['classes'] = classes
    ns['netclass_patterns'] = patterns
    ns['netclass_assignments'] = None
    root = str(gen_sch.uid('root'))
    pro['sheets'] = [[root, 'Root']] + [[str(gen_sch.uid('sheet', st)), st] for st, _, _ in D.SHEETS]
    pro.setdefault('schematic', {})['top_level_sheets'] = [{'filename': D.PROJECT + '.kicad_sch', 'name': D.PROJECT,
                                                            'uuid': '00000000-0000-0000-0000-000000000000'}]
    pro['pcbnew'] = pro.get('pcbnew', {})
    pro['pcbnew'].setdefault('last_paths', {})['specctra_dsn'] = ''
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')
    K = D.KEY
    solid = ' || '.join("A.memberOfFootprint('%s')" % K[k] for k in ('U_RP', 'U_UART', 'U_BUCK', 'U_LDO', 'U_MUX'))
    open(os.path.join(PRJ, D.PROJECT + '.kicad_dru'), 'w').write(
        '(version 1)\n'
        # the grafted Raspberry Pi regulator corner and the 0.4 mm-pitch neck-downs: 0.12 mm
        # (JLCPCB multilayer minimum 0.09); the routers aim for the 0.15 mm netclass value elsewhere
        '(rule "default_clearance"\n'
        '\t(constraint clearance (min 0.12mm)))\n'
        # QFN exposed pads and the regulators' grounds join the pours solidly
        '(rule "gnd_solid_under_ics"\n'
        '\t(condition "A.NetName == \'GND\' && (%s)")\n'
        '\t(constraint zone_connection solid))\n'
        # the fingers start 0.5 mm from the bevelled insertion edge by design (make_edge_fp.py)
        '(rule "finger_edge"\n'
        '\t(condition "A.memberOfFootprint(\'%s\')")\n'
        '\t(constraint edge_clearance (min 0.4mm)))\n' % (solid, K['J_EDGE']))


def write_case_anchors():
    """case/board-anchors.scad: the shell openings follow the placement."""
    def at(key):
        x, y, _ = PLACE[D.KEY[key]]
        return x, y
    lines = ['// GENERATED by tools/gen_pcb.py from tools/placement.py -- do not edit.',
             '// Board (KiCad) coordinates, seen from the parts face (pins 1-15); outline: tools/edge_geom.py.',
             'board = [%g, %g, %g, %g];   // x0, y0, x1, y1 (top edge y0, insertion edge y1)' % (X0, Y0, X1, Y1),
             'parts_max_y = %g;            // no part below this y (the shell bottom)' % PARTS_MAX_Y,
             'notch_l = [%g, %g, %g];      // left side notch: depth, y from, y to' % (EG.NOTCH_D, Y1 - EG.NOTCH_L[1], Y1 - EG.NOTCH_L[0]),
             'notch_r = [%g, %g, %g];      // right side notch' % (EG.NOTCH_D, Y1 - EG.NOTCH_R[1], Y1 - EG.NOTCH_R[0]),
             'sw_reset   = [%g, %g];' % at('SW_RESET'),
             'sw_bootsel = [%g, %g];' % at('SW_BOOTSEL'),
             'sw_s3rst   = [%g, %g];' % at('SW_S3EN'),
             'sw_s3boot  = [%g, %g];' % at('SW_S3BOOT'),
             'ws_led     = [%g, %g];   // WS2812' % at('D_WS'),
             'rp_led     = [%g, %g];   // RP activity LED' % at('D_LED'),
             'usb_x      = %g;         // USB-C exits the top edge (shell notch)' % at('J_USB')[0],
             'sd_y       = %g;         // microSD exits the left edge (shell notch)' % at('J_SD')[1],
             'ant        = [%g, %g];   // ESP32-S3 module centre (antenna flush with the top edge)' % at('U_S3'),
             'holes = [%s];   // shell posts, %g mm' % (', '.join('[%g, %g]' % (x, y) for x, y, d in HOLES), EG.HOLE_D), '']
    os.makedirs(os.path.join(PRJ, 'case'), exist_ok=True)
    open(os.path.join(PRJ, 'case', 'board-anchors.scad'), 'w').write('\n'.join(lines))


FIDUCIALS = PL.FIDUCIALS


def board_only(name, fpname, x, y, desc):
    fp = load_fp(fpname)
    for i, e in enumerate(fp):   # legacy (fp_text reference/value ...) -> (property ...)
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


def check_parts_inside(board):
    _, crt = board_pads(board)
    bad = []
    for p in D.PARTS:
        if p.ref == D.KEY['J_EDGE'] or p.ref not in crt:
            continue
        x0, y0, x1, y1 = crt[p.ref]
        top = 1.0 if p.key == 'J_USB' else 0.2      # HRO's recommended edge: the shell face 0.46 mm past it
        if y1 > PARTS_MAX_Y or x0 < X0 - 0.01 or x1 > X1 + 0.01 or y0 < Y0 - top:
            bad.append('%s(%s)' % (p.ref, p.key))
            continue
        for hx, hy, hd in HOLES:                    # the shell posts' bosses
            dx, dy = max(x0 - hx, 0, hx - x1), max(y0 - hy, 0, hy - y1)
            if math.hypot(dx, dy) < EG.POST_KEEP:
                bad.append('%s(%s) at the post (%g, %g)' % (p.ref, p.key, hx, hy))
        for (nl, nh), side in ((EG.NOTCH_L, X0), (EG.NOTCH_R, X1)):   # the side notches
            if y1 > Y1 - nh and y0 < Y1 - nl and (x0 < X0 + EG.NOTCH_D if side == X0 else x1 > X1 - EG.NOTCH_D):
                bad.append('%s(%s) in a notch' % (p.ref, p.key))
    if bad:
        raise SystemExit('courtyard outside the shell / board: ' + ' '.join(bad))


def main():
    configure_project()
    do_placement(place)
    graft_parts()
    missing = [p.ref + '(' + p.key + ')' for p in D.PARTS if p.ref not in PLACE]
    if missing:
        raise SystemExit('unplaced: ' + ' '.join(missing))
    write_case_anchors()
    NET('GND')                                  # loads NETLIST / FULL / COMP_SHEET
    hdr = parse(open(os.path.join(HERE, 'pcb_header.sexpr')).read())
    find(find(hdr, 'general'), 'thickness')[1] = THICKNESS
    setup = find(hdr, 'setup')
    if not find(setup, 'solder_mask_min_width'):
        setup.insert(2, ['solder_mask_min_width', 0])
    layers = find(hdr, 'layers')
    rest = [l for l in layers[1:] if not str(l[1]).endswith('.Cu')]
    kinds = {'F.Cu': 'signal', 'In1.Cu': 'power', 'In2.Cu': 'power', 'B.Cu': 'signal'}
    ids = {'F.Cu': '0', 'B.Cu': '2', 'In1.Cu': '4', 'In2.Cu': '6'}
    layers[1:] = [[ids[n], Q(n), kinds[n]] for n in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')] + rest
    board = hdr
    syms = gen_sch.load_symbols()
    for p in D.PARTS:
        x, y, r = PLACE[p.ref]
        stem, u = fp_sheet_unit(p, syms)
        path = '/%s/%s' % (gen_sch.uid('sheet', stem), gen_sch.uid(stem, p.ref, u))
        ds = ''
        for pr in findall(syms[p.lib_id], 'property'):
            if pr[1] == 'Datasheet':
                ds = str(pr[2])
        board.append(instance(p, x, y, r, path, '/%s/' % stem, stem + '.kicad_sch', p.ds or ds))
    check_parts_inside(board)
    for i, (x, y, d) in enumerate(HOLES, 1):
        board.append(board_only('H%d' % i, 'MountingHole_5mm_NPTH', x, y, 'Videopac shell post'))
    for name, x, y in FIDUCIALS:
        board.append(board_only(name, 'Fiducial_1mm_Mask2mm', x, y, 'assembly fiducial'))
    rs, rzones = rp_support(board)
    gc, gzones = graft_copper()
    extra = gc + rs + cap_links(board) + finger_gnd_vias(board) + mux_link(board) + tp_dvdd_link(board, gc)
    board += extra
    add_fanout(board, extra)
    board += outline()
    board += rzones + gzones
    # finger strip: fingers only on F/B
    strip = [(X0 - 1, FINGER_Y), (X1 + 1, FINGER_Y), (X1 + 1, Y1 + 1), (X0 - 1, Y1 + 1)]
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('finger_strip_' + L[0], None, L, strip, keepout={}))
    # antenna band: nothing, on any layer
    ax0, ay0, ax1, ay1 = ANT_KEEP
    band = [(ax0 - 1, ay0 - 1), (ax1, ay0 - 1), (ax1, ay1), (ax0 - 1, ay1)]
    for L in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
        board.append(zone('antenna_' + L.split('.')[0], None, L, band, keepout={'pads': 'allowed'}))
    # the shell posts: no copper near the holes
    for i, (x, y, d) in enumerate(HOLES):
        for L in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
            board.append(zone('post_%d_%s' % (i, L.split('.')[0]), None, L, circle_pts(x, y, HOLE_CU), keepout={}))
    board.append(zone('GND_plane', 'GND', 'In1.Cu', BODY))
    board.append(zone('5V_plane', '+5V', PWR_LAYER, BODY))
    from placement import RP_ISLAND, S3_ISLAND, CONS5V_ISLAND
    board.append(zone('s3_3v3_island', '+3V3', PWR_LAYER, S3_ISLAND, priority=2))
    board.append(zone('cons5v_island', 'CONS_5V', PWR_LAYER, CONS5V_ISLAND, priority=4))
    for name, x, y in FIDUCIALS:            # fiducials: 1 mm copper in a clear 3 mm field
        board.append(zone('fid_' + name, None, 'F.Cu', circle_pts(x, y, 1.6), keepout={}))
    board.append(zone('rp_io_island', D.RP_RAIL, PWR_LAYER, RP_ISLAND, priority=3))
    ty = PARTS_MAX_Y + 2.6
    board.append(text('FujiNet-O2 Rev0   ODYSSEY 2 / VIDEOPAC', XC, ty - 1.0, 'F.SilkS', 1.0))
    board.append(text('THIS SIDE TO THE PLAYER  (PINS 1-15)', XC, ty + 1.0, 'F.SilkS', 0.9))
    board.append(text('BACK OF THE CONSOLE  (PINS A-R)', XC, ty - 1.0, 'B.SilkS', 1.0, mirror=True))
    board.append(text('RP2354B + ESP32-S3   CERN-OHL-W-2.0', XC, ty + 1.0, 'B.SilkS', 0.8, mirror=True))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
