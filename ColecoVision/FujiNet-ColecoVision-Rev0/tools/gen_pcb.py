#!/usr/bin/env python3
"""Generate FujiNet-ColecoVision-Rev0.kicad_pcb (placed, unrouted) from design.py.

Board (tools/edge_geom.py; tools/placement.py owns the frame): x 79.9..120.1, y 47.6..130, the
ColecoVision cart outline, 40.2 x 82.4 -- the full bottom edge carries the 2x15 gold fingers at y = 130
(the insertion edge), its corners chamfered, two notches in each side for the shell's ribs.  No parts
below the shell's bottom (edge_geom.PARTS_Y) or in a notch.  1.6 mm, 4 copper layers (JLC04161H-7628):
  F.Cu  signals + GND pour            (even pins 2-30: /C000, D3-D7, A11, A10, /8000, A14, /A000, A12, A9, A8, +5V)
  In1   GND plane
  In2   +5V plane (the mux's output), with a +3V3_RP island under the RP2350A, its caps, flash, bus
        logic and LDO, a DVDD island under its core, a +3V3 island (the buck: the S3, CP2102N and
        microSD, the upper half) and a CONS_5V island from the +5V finger up under the mux
  B.Cu  signals + GND pour            (odd pins 1-29 behind them)
The finger field is a rule area on F/B (fingers only); the inner planes stop above it.  The
ESP32-S3 module lies turned 90 degrees, its antenna flush with the west edge over a strip that is
copper-free on every layer (placement.ANT_KEEP).

The RP2350A's core-regulator corner is Raspberry Pi's own RP2350A minimal-design layout
(tools/rpi_core_graft.sexpr, MIT): its parts and copper are placed relative to the RP and turned with
it (datasheet 6.3.8: "follow this layout as closely as possible"); its supplies join under the package
as FujiNet-Arcadia Rev0's do (rp_ring).

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
HOLES = list(PL.HOLES)    # the shell posts: (x, y, diameter) -- none (edge_geom.HOLES_REL)
HOLE_CU = EG.HOLE_D / 2 + 0.6   # no copper within this radius of a post
ANT_KEEP = PL.ANT_KEEP    # the antenna strip along the west edge (placement.py)
PWR_LAYER = 'In2.Cu'
UNDER = 3.0               # half-size of the square under the RP2350A the finisher keeps off F.Cu
K = D.KEY


def outline_pts():
    """Board outline, clockwise from the top-left (y down): the top corners rounded (edge_geom.TOP_R),
    the side notches (edge_geom.NOTCHES_L / NOTCHES_R, seen from F.Cu) and the chamfered bottom corners."""
    r = EG.TOP_R
    arc = lambda cx, cy, a0, a1: [(round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / 6)), 4),
                                   round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / 6)), 4))
                                  for k in range(7)]
    nd = EG.NOTCH_D
    right = []
    for lo, hi in sorted(EG.NOTCHES_R, key=lambda t: -t[1]):          # down the east side
        right += [(X1, Y1 - hi), (X1 - nd, Y1 - hi), (X1 - nd, Y1 - lo), (X1, Y1 - lo)]
    left = []
    for lo, hi in sorted(EG.NOTCHES_L):                               # up the west side
        left += [(X0, Y1 - lo), (X0 + nd, Y1 - lo), (X0 + nd, Y1 - hi), (X0, Y1 - hi)]
    return (arc(X0 + r, Y0 + r, 180, 270) + arc(X1 - r, Y0 + r, 270, 360) + right +
            [(X1, Y1 - EG.CHAMF_Y), (X1 - EG.CHAMF_X, Y1), (X0 + EG.CHAMF_X, Y1), (X0, Y1 - EG.CHAMF_Y)] + left)


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
SMALL = _re.compile(r'_0603_|_0805_|0402|SOD-523|SOT-23|SOT-363|SOT-583|R_Array|AOTA|Crystal_SMD|WS2812|TSOT|TestPoint|USON|TSSOP')


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
            if num and num not in part.pins and e[2] != 'np_thru_hole' and num not in part.nc_pads:
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


def uart_link(board):
    """The CP2102N's VDD and VREGIN (pins 6 / 7, west side, under D+ / D-) joined just outside their pads,
    taken to one +3V3 plane via south-west and on to the 100 nF (C_UART): the fan-out's own stubs would
    cross in front of D- (pin 5), whose only way in is along its own axis."""
    ux, uy, ur = PLACE[D.KEY['U_UART']]
    assert ur == 0, 'uart_link: drawn for U_UART at rotation 0'
    u = footprint_of(board, D.KEY['U_UART'])
    pads, _ = board_pads([u])
    P = {p.num: p for p in pads}
    p6, p7 = P['6'], P['7']
    assert p6.net == p7.net == '+3V3' and abs(p6.cx - p7.cx) < 1e-3 and p7.cy > p6.cy, 'uart_link: pins 6 / 7'
    xl = round(p6.cx - p6.hw - 0.25, 4)
    vx, vy = round(xl - 0.5, 4), round(p7.cy + 0.6, 4)
    assert plane_net_at(vx, vy) == '+3V3', 'uart_link: the via must land on In2 +3V3'
    # and on to the 100 nF's +3V3 pad, west of the via
    c1 = {p.num: p for p in board_pads([footprint_of(board, D.KEY['C_UART'])])[0]}['1']
    assert c1.net == '+3V3' and vx - 2.0 < c1.cx < vx and abs(c1.cy - vy) < 0.6, 'uart_link: C_UART moved'
    w = 0.25
    return [seg(p6.cx, p6.cy, xl, p6.cy, w, 'F.Cu', '+3V3', ('uart', 6)),
            seg(p7.cx, p7.cy, xl, p7.cy, w, 'F.Cu', '+3V3', ('uart', 7)),
            seg(xl, p6.cy, xl, p7.cy, w, 'F.Cu', '+3V3', ('uart', 'v')),
            seg(xl, p7.cy, vx, vy, w, 'F.Cu', '+3V3', ('uart', 'd')),
            via(vx, vy, '+3V3', ('uart', 'via')),
            seg(vx, vy, c1.cx, c1.cy, w, 'F.Cu', '+3V3', ('uart', 'cap'))]


def usbc_link(board):
    """The USB-C receptacle's data pads join, drawn (FujiNet-StudioII / ChannelF Rev0's): the row runs D+
    (B6), D- (A7), D+ (A6), D- (B7) at 0.5 mm, so one pair must change layer at the pins.  D+ joins on
    F.Cu in a 0.15 mm U under the pads; D- drops through a 0.45 mm via under each of its pads -- A7's
    inside the U -- and the two vias join on B.Cu.  The routers take D+ from the U and D- from either via."""
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
    """The pair's last stretch, drawn: the USBLC6 (rotation 90, west of the CP2102N; D- pin 1 west, GND 2,
    D+ 3 east on its south row) to the CP2102N's west side (D+ 4 over D- 5, VDD / VREGIN 6 / 7 under
    them: uart_link).  The USBLC6 is flow-through (6 / 1 and 4 / 3 are one line inside) but the routers
    see two pads to join: joined straight under the body, VBUS (5) dropping through a via between the
    rows (FujiNet-StudioII Rev0's bridge_link).  D+ runs east onto pad 4's axis; D- drops down the west
    side, passes under the GND pad's via and rises onto pad 5's axis, clear of the VDD join."""
    e_, u_ = footprint_of(board, K['U_ESD']), footprint_of(board, K['U_UART'])
    pads, _ = board_pads([e_, u_])
    P = {(p.ref, p.num): p for p in pads}
    E = lambda n: P[(K['U_ESD'], n)]
    p1, p2, p3, p4, p5, p6 = (E(n) for n in '123456')
    c4, c5 = P[(K['U_UART'], '4')], P[(K['U_UART'], '5')]
    assert p1.net == p6.net == c5.net == NET('UBRG_DM') and p3.net == p4.net == c4.net == NET('UBRG_DP'), 'bridge_link: nets'
    assert p5.net == NET('VBUS') and p2.net == 'GND', 'bridge_link: USBLC6 pins'
    assert abs(p6.cx - p1.cx) < 1e-3 and abs(p4.cx - p3.cx) < 1e-3 and p1.cx < p2.cx < p3.cx and p1.cy > p6.cy, \
        'bridge_link: USBLC6 at rotation 90'
    assert p3.cx + 2.0 < c4.cx and c4.cy < c5.cy and abs(c4.cx - c5.cx) < 1e-3, 'bridge_link: the CP2102N moved'
    out = [seg(p6.cx, p6.cy, p1.cx, p1.cy, 0.25, 'F.Cu', p1.net, ('brg', 'esd_dm')),
           seg(p4.cx, p4.cy, p3.cx, p3.cy, 0.25, 'F.Cu', p3.net, ('brg', 'esd_dp'))]
    vy = round((p5.cy + p2.cy) / 2, 4)
    out += [seg(p5.cx, p5.cy, p5.cx, vy, 0.4, 'F.Cu', p5.net, ('brg', 'vbus')),
            via(p5.cx, vy, p5.net, ('brg', 'vbusv'))]
    # GND (2): a via just under its pad, D- passing beneath it
    gy = round(p2.cy + p2.hh + 0.4, 4)
    out += [seg(p2.cx, p2.cy, p2.cx, gy, 0.3, 'F.Cu', 'GND', ('brg', 'gnd')), via(p2.cx, gy, 'GND', ('brg', 'gndv'))]
    w = 0.2
    # D+: off pad 3's end, 45 degrees down onto pad 4's axis, east into it
    y3 = round(p3.cy + p3.hh, 4)
    out += path([(p3.cx, p3.cy), (p3.cx, y3), (round(p3.cx + (c4.cy - y3), 4), c4.cy), (c4.cx, c4.cy)],
                w, 'F.Cu', p3.net, ('brg', 'dp'))
    # D-: down the west side to under the GND via, east, and 45 degrees up onto pad 5's axis
    yd = round(gy + 0.3 + 0.15 + w / 2 + 0.05, 4)
    xr = round(c5.cx - c5.hw - 0.85, 4)                 # where D- is back on pad 5's axis
    xd = round(xr - (yd - c5.cy), 4)
    out += path([(p1.cx, p1.cy), (p1.cx, yd), (xd, yd), (xr, c5.cy), (c5.cx, c5.cy)], w, 'F.Cu', p1.net, ('brg', 'dm'))
    return out


def pads_of(board, key):
    return {p.num: p for p in board_pads([footprint_of(board, K[key])])[0]}


def path(pts, w, layer, net, key):
    return [seg(*pts[i], *pts[i + 1], w, layer, net, key + (i,)) for i in range(len(pts) - 1)]


# ---- Raspberry Pi RP2350A minimal-design regulator corner -------------------
GRAFT = parse(open(os.path.join(HERE, 'rpi_core_graft.sexpr')).read())
# the reference's designators -> this board's design.py keys (same footprints, same pad nets)
GRAFT_KEY = {'U1': 'U_RP', 'L1': 'L_VREG', 'C15': 'C_VOUT', 'C10': 'C_VIN', 'C16': 'C_FILT',
             'R1': 'R_FILT', 'R11': 'R_USBP', 'R12': 'R_USBM', 'C8': 'C_OTP'}
GRAFT_NET = {'+3V3': D.RP_RAIL}      # the reference's single 3.3 V rail is this board's RP rail (then NET())
# DVDD island on In2, relative to U1 at rotation 0 (y down): under the core, plus a tongue
# north to the regulator's two 1V1 vias by L1 (graft vias at (0.5, -5.2) / (0.5, -5.8))
DVDD_ISLAND = [(-2.9, -2.9), (0.0, -2.9), (0.0, -6.15), (1.0, -6.15), (1.0, -2.9), (2.9, -2.9),
               (2.9, 2.9), (-2.9, 2.9)]


def rp_xy(lx, ly):
    """U1-local (rotation 0) -> board coordinates, turned with the RP."""
    ux, uy, ur = PLACE[K['U_RP']]
    dx, dy = rot_pt(lx, ly, ur)
    return round(ux + dx, 4), round(uy + dy, 4)


def graft_parts():
    ur = PLACE[K['U_RP']][2]
    for e in GRAFT[1:]:
        if e[0] == 'part' and e[1] != 'U1':
            a = find(e, 'at')
            x, y = rp_xy(float(a[1]), float(a[2]))
            PLACE[D.KEY[GRAFT_KEY[str(e[1])]]] = (x, y, (float(a[3]) + ur) % 360)


def gnet(e):
    n = str(find(e, 'net')[1])
    return NET(GRAFT_NET.get(n, n))


def graft_copper():
    """Raspberry Pi's regulator-corner copper (tools/rpi_graft.py), moved and turned with U1."""
    out = []
    for i, e in enumerate(GRAFT[1:]):
        if e[0] == 'segment':
            s_, t_ = find(e, 'start'), find(e, 'end')
            if max(abs(float(s_[1])), abs(float(s_[2]))) < 3.1 or max(abs(float(t_[1])), abs(float(t_[2]))) < 3.1:
                continue    # under the package: rp_ring's bar replaces it
            a, b = rp_xy(float(s_[1]), float(s_[2])), rp_xy(float(t_[1]), float(t_[2]))
            out.append(seg(*a, *b, float(find(e, 'width')[1]), str(find(e, 'layer')[1]), gnet(e), ('graft', i)))
        elif e[0] == 'via':
            a = find(e, 'at')
            out.append(via(*rp_xy(float(a[1]), float(a[2])), gnet(e), ('graft', i)))
        elif e[0] == 'zone':
            if str(find(e, 'net')[1]) == 'GND':
                continue    # the board-wide F.Cu GND pour covers this corner (solid, .kicad_dru)
            pts = [rp_xy(float(p[1]), float(p[2])) for p in find(e, 'pts')[1:]]
            out.append(['zone', ['net', Q(gnet(e))], ['layer', Q(str(find(e, 'layer')[1]))], ['uuid', uid('graft', i)],
                        ['name', Q('rpi_graft_%d' % i)], ['hatch', 'edge', 0.5],
                        ['priority', int(find(e, 'priority')[1]) + 10],
                        ['connect_pads', 'yes', ['clearance', float(find(e, 'clearance')[1])]],
                        ['min_thickness', float(find(e, 'min_thickness')[1])],
                        ['fill', 'yes', ['thermal_gap', 0.3], ['thermal_bridge_width', 0.3], ['island_removal_mode', 0]],
                        ['polygon', ['pts'] + [['xy', x, y] for x, y in pts]]])
    return out


def rp_ring(board):
    """Copper under the RP2350A, after the minimal design:
      * a +3V3_RP bar under the regulator-side pin row joins VREG_VIN (pin 49,
        boxed in by LX / FB at 0.4 mm pitch, no via spot) to pins 53 / 54,
        whose shared cap C_OTP has the plane via
      * each DVDD pin (6, 23, 39) runs a short stub inward to a via under the
        package; those vias and the regulator's two 1V1 vias meet on the DVDD
        island in In2 under the chip
    All locked; the routers work around it."""
    out = []
    bar_y = -2.7
    for i, (x0, y0, x1, y1) in enumerate(((1.6, -3.45, 1.6, bar_y), (1.6, bar_y, -0.4, bar_y),
                                          (0.0, -3.45, 0.0, bar_y), (-0.4, -3.45, -0.4, bar_y))):
        out.append(seg(*rp_xy(x0, y0), *rp_xy(x1, y1), 0.2, 'F.Cu', D.RP_RAIL, ('rpbar', i)))
    out.append(zone('rp_dvdd_island', 'DVDD', PWR_LAYER, [rp_xy(x, y) for x, y in DVDD_ISLAND], priority=5))
    from placement import DVDD_LOBE
    out.append(zone('rp_dvdd_island_lobe', 'DVDD', PWR_LAYER, DVDD_LOBE, priority=6))
    u1 = footprint_of(board, K['U_RP'])
    for pd in findall(u1, 'pad'):
        n = find(pd, 'net')
        if not n or str(n[1]) != 'DVDD' or pd[2] != 'smd':
            continue
        a = find(pd, 'at')
        px, py = float(a[1]), float(a[2])                   # a footprint's pads keep U1-local coordinates
        if py < -3.0:        # VREG_FB (pin 50) is on the regulator's own DVDD copper already
            continue
        if abs(px) > abs(py):
            vx, vy = math.copysign(2.35, px), py
        else:
            vx, vy = px, math.copysign(2.35, py)
        num = str(pd[1])
        out.append(seg(*rp_xy(px, py), *rp_xy(vx, vy), 0.2, 'F.Cu', 'DVDD', ('rpdv', num)))
        out.append(via(*rp_xy(vx, vy), 'DVDD', ('rpdvv', num), 0.5, 0.25))
    return out


def plane_net_at(x, y):
    """Which net the In2 plane carries at (x, y)."""
    from placement import RP_ISLAND, DVDD_LOBE, S3_ISLAND, CONS5V_ISLAND
    if point_in_poly(x, y, [rp_xy(px, py) for px, py in DVDD_ISLAND]) or point_in_poly(x, y, DVDD_LOBE):
        return 'DVDD'
    if point_in_poly(x, y, CONS5V_ISLAND):
        return 'CONS_5V'
    if point_in_poly(x, y, RP_ISLAND):
        return D.RP_RAIL
    if point_in_poly(x, y, S3_ISLAND):
        return '+3V3'
    return '+5V'


def finger_gnd_vias(board):
    """The GND fingers (13 SHLD and 29, B.Cu) stitch straight into the In1 plane, and the +5V finger
    (30, F.Cu) into In2's CONS_5V island, at the top of their necks.  The fingers are back to back, so a
    via ON a neck would hit the other face's neck: go 1.27 mm outboard, between columns.  29 and 30 are
    the same column: the CONS_5V via sits 1.6 mm above the GND via."""
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
                    if net == 'CONS_5V':
                        vy = round(ny - 1.6, 4)
                        out += [seg(nx, ny, nx, vy, 0.4, layer, net, ('fingergnds', pd[1], 'u')),
                                seg(nx, vy, vx, vy, 0.4, layer, net, ('fingergnds', pd[1])),
                                via(vx, vy, net, ('fingergnd', pd[1]))]
                    else:
                        out.append(seg(nx, ny, vx, ny, 0.4, layer, net, ('fingergnds', pd[1])))
                        out.append(via(vx, ny, net, ('fingergnd', pd[1])))
    return out


def add_fanout(board, extra):
    import fanout
    pads, crt = board_pads(board)
    extra_segs, extra_vias, served = [], [], set()
    for e in extra:
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
        elif e[0] == 'zone' and str(find(e, 'layer')[1]) == 'F.Cu':
            xy = [(float(q[1]), float(q[2])) for q in find(find(e, 'polygon'), 'pts')[1:]]
            x0_, y0_ = min(q[0] for q in xy), min(q[1] for q in xy)
            x1_, y1_ = max(q[0] for q in xy), max(q[1] for q in xy)
            zp = fanout.Pad('graft', 'zone', net, (x0_ + x1_) / 2, (y0_ + y1_) / 2, (x1_ - x0_) / 2, (y1_ - y0_) / 2,
                            ['F.Cu'], False, ((x0_ + x1_) / 2, (y0_ + y1_) / 2))
            for p in pads:
                if p.net == net and zp.dist(p.cx, p.cy) < 1e-6:
                    served.add(id(p))
            pads.append(zp)
    # GND pads on the graft's own copper and U1 pins already on graft copper are done
    skip = {id(p) for p in pads if id(p) in served and (p.net == 'GND' or p.ref in (K['U_RP'], K['U_UART']))}

    # a pad only gets a plane via where In2 carries its net (GND is In1, everywhere),
    # judged where the via will sit: a fine-pitch pin's via goes straight out along its axis
    def via_spot(p):
        if min(p.hw, p.hh) <= 0.15:
            fx, fy = p.fp_xy
            if p.hh > p.hw:
                return p.cx, p.cy + math.copysign(2.0, p.cy - fy)
            return p.cx + math.copysign(2.0, p.cx - fx), p.cy
        return p.cx, p.cy
    for p in pads:
        if p.net in ('+5V', '+3V3', D.RP_RAIL, 'DVDD', 'CONS_5V') and plane_net_at(*via_spot(p)) != p.net:
            skip.add(id(p))
    keep = [crt[r] for r in (D.KEY[k] for k in ('J_SD', 'J_USB', 'SW_RESET', 'SW_BOOTSEL', 'SW_S3BOOT'))
            if r in crt]
    ux, uy, _ = PLACE[K['U_RP']]
    keep.append((ux - UNDER, uy - UNDER, ux + UNDER, uy + UNDER))   # no fan-out vias under the RP2350A
    keep.append(ANT_KEEP)
    holes = [(x, y, d / 2 + 0.3) for x, y, d in HOLES]
    vias, segs, failed = fanout.plan(pads, keep, (X0, Y0, X1, Y1), BLADE_Y, holes,
                                     skip_refs=(D.KEY['J_EDGE'], 'graft'), extra_segs=extra_segs,
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


# assembled height above F.Cu by footprint (datasheets; the shell's front gap clears the tallest)
PART_H = {'USB_C_Receptacle_HRO_TYPE-C-31-M-12': 3.26, 'ESP32-S3-WROOM-1': 3.1, 'L_Sunlord_SWPA4030S': 3.0,
          'TF-SMD_TF-015': 1.85, 'SW_SPST_TS-1187A': 1.5, 'C_0805_2012Metric': 1.35, 'SOT-23': 1.15,
          'SOT-23-5': 1.45, 'SOT-23-6': 1.45, 'TSOT-23-6': 1.0, 'SOT-363_SC-70-6': 1.1, 'SOT-583-8': 0.6,
          'RPI_RP2350A_QFN60': 0.9, 'TSSOP-20_4.4x6.5mm_P0.65mm': 1.2,
          'Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm': 0.6, 'QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm': 0.9,
          'Crystal_SMD_3225-4Pin_3.2x2.5mm': 0.8, 'RPI_L_AOTA-B201610S3R3': 1.0,
          'LED_WS2812B-2020_PLCC4_2.0x2.0mm': 0.84, 'R_Array_Convex_4x0603': 0.6}


def courtyard(key):
    """A part's courtyard box on the board (x0, y0, x1, y1), from its library footprint turned and moved."""
    p = D.BY_KEY[key]
    fp = load_fp(p.footprint.split(':')[1])
    pts = []
    for e in fp[1:]:
        if isinstance(e, list) and e and e[0] in ('fp_line', 'fp_rect', 'fp_poly', 'fp_circle') and \
                find(e, 'layer') and 'CrtYd' in str(find(e, 'layer')[1]):
            for k in ('start', 'end', 'center'):
                q = find(e, k)
                if q:
                    pts.append((float(q[1]), float(q[2])))
            if e[0] == 'fp_circle':
                c, q = find(e, 'center'), find(e, 'end')
                r = math.hypot(float(q[1]) - float(c[1]), float(q[2]) - float(c[2]))
                pts += [(float(c[1]) + dx * r, float(c[2]) + dy * r) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if find(e, 'pts'):
                pts += [(float(q[1]), float(q[2])) for q in find(e, 'pts')[1:]]
    x, y, r = PLACE[p.ref]
    w = [rot_pt(px, py, r) for px, py in pts]
    return (round(x + min(q[0] for q in w), 3), round(y + min(q[1] for q in w), 3),
            round(x + max(q[0] for q in w), 3), round(y + max(q[1] for q in w), 3))


def write_case_anchors():
    """case/board-anchors.scad: what the printed shell needs from the board, so its openings, keys and
    posts follow the placement and the outline (case/FujiNet-ColecoVision-Shell.scad includes it)."""
    def at(key, dx=0.0, dy=0.0):
        x, y, r = PLACE[D.KEY[key]]
        ox, oy = rot_pt(dx, dy, r)
        return round(x + ox, 3), round(y + oy, 3)
    parts = []
    for p in D.PARTS:
        if p.key in ('J_EDGE',) or p.prefix in ('TP',):
            continue
        fpn = p.footprint.split(':')[1]
        parts.append(courtyard(p.key) + (PART_H.get(fpn, 1.0),))
    hmax = max(q[4] for q in parts)
    v = lambda t: '[%s]' % ', '.join('%g' % c for c in t)
    notches = [(X0, Y1 - hi, X0 + EG.NOTCH_D, Y1 - lo) for lo, hi in EG.NOTCHES_L] + \
              [(X1 - EG.NOTCH_D, Y1 - hi, X1, Y1 - lo) for lo, hi in EG.NOTCHES_R]
    sx, sy, _ = PLACE[D.KEY['U_S3']]
    lines = ['// GENERATED by tools/gen_pcb.py from tools/placement.py and tools/edge_geom.py -- do not edit.',
             '// KiCad board frame (mm, y down), seen from F.Cu (every part; even pins 2-30):',
             '// x %g..%g, y %g (top edge) .. %g (the insertion edge). Odd pins 1-29 are on B.Cu.' % (X0, X1, Y0, Y1),
             'pcb_x0 = %g; pcb_x1 = %g; pcb_y0 = %g; pcb_y1 = %g; pcb_t = %g;' % (X0, X1, Y0, Y1, THICKNESS),
             'pcb_outline = [%s];   // the notches, chamfers and rounded top corners' % ', '.join(v(q) for q in OUTLINE),
             'pcb_holes = [%s];   // [x, y, diameter]: none (edge_geom.HOLES_REL)' % ', '.join(v(h) for h in HOLES),
             '// side notches [x0, y0, x1, y1]: the shell\'s ribs go through them',
             'pcb_notches = [%s];' % ', '.join(v(n) for n in notches),
             'parts_min_y = %g;   // no part south of this (%g mm in): the bare band and the contacts' % (PARTS_MAX_Y, EG.PARTS_Y),
             'contacts_y = %g;    // the fingers\' copper ends here (%g mm in)' % (Y1 - EG.LAND_Y1, EG.LAND_Y1),
             'parts_max_h = %g;   // tallest part above F.Cu; B.Cu has none' % hmax,
             '// every F.Cu part: [x0, y0, x1, y1, height above F.Cu] (courtyard box)',
             'parts = [%s];' % ', '.join(v(q) for q in parts),
             'esp32_ant  = %s;   // ESP32-S3 antenna, at the west edge: no metal near it' % v((X0, sy)),
             'ant_keep   = %s;   // its copper-free strip [x0, y0, x1, y1]' % v(ANT_KEEP),
             'usb_c      = %s;   // USB-C mouth on the top edge (receptacle 8.94 x 3.26, centre 1.63 above F.Cu)' % v((at('J_USB')[0], Y0)),
             'microsd    = %s;   // microSD card slot on the top edge: the card\'s centreline (between its pegs)' % v((at('J_SD', -0.9, 0.0)[0], Y0)),
             'sw_reset   = %s;   // RESET: the RP2350A and the ESP32-S3 together (back to CONFIG)' % v(at('SW_RESET')),
             'sw_bootsel = %s;   // RP BOOTSEL (hold while pressing RESET)' % v(at('SW_BOOTSEL')),
             'sw_s3boot  = %s;   // ESP32-S3 BOOT (IO0)' % v(at('SW_S3BOOT')),
             'led_status = %s;   // WS2812 status light' % v(at('D_WS')),
             'led_rp     = %s;   // RP activity LED' % v(at('D_LED')),
             '']
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
        for (nl, nh), side in [(n, X0) for n in EG.NOTCHES_L] + [(n, X1) for n in EG.NOTCHES_R]:   # the side notches
            if y1 > Y1 - nh and y0 < Y1 - nl and (x0 < X0 + EG.NOTCH_D if side == X0 else x1 > X1 - EG.NOTCH_D):
                bad.append('%s(%s) in a notch' % (p.ref, p.key))
        ax0, ay0, ax1, ay1 = ANT_KEEP               # the antenna strip
        if x0 < ax1 and y0 < ay1 and y1 > ay0 and p.key != 'U_S3':
            bad.append('%s(%s) in the antenna strip' % (p.ref, p.key))
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
        board.append(board_only('H%d' % i, 'MountingHole_3.4mm_NPTH', x, y, 'shell post'))
    for name, x, y in FIDUCIALS:
        board.append(board_only(name, 'Fiducial_1mm_Mask2mm', x, y, 'assembly fiducial'))
    extra = graft_copper() + rp_ring(board) + finger_gnd_vias(board) + mux_link(board) + uart_link(board)\
        + usbc_link(board) + bridge_link(board)
    board += extra
    add_fanout(board, extra)
    board += outline()
    # finger strip: fingers only on F/B
    strip = [(X0 - 1, FINGER_Y), (X1 + 1, FINGER_Y), (X1 + 1, Y1 + 1), (X0 - 1, Y1 + 1)]
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('finger_strip_' + L[0], None, L, strip, keepout={}))
    # antenna band: nothing, on any layer
    ax0, ay0, ax1, ay1 = ANT_KEEP
    band = [(ax0 - 1, ay0 - 1), (ax1, ay0 - 1), (ax1, ay1), (ax0 - 1, ay1)]
    for L in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
        board.append(zone('antenna_' + L.split('.')[0], None, L, band, keepout={'pads': 'allowed'}))
    # the DVDD lobe's neck into the core island under the RP: tracks yes, vias no (In2 must stay whole)
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('dvdd_neck_' + L[0], None, L, PL.DVDD_NECK_KEEP,
                          keepout={'tracks': 'allowed', 'pads': 'allowed', 'copperpour': 'allowed', 'footprints': 'allowed'}))
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
    board.append(text('FujiNet-ColecoVision Rev0   PINS 2-30', XC, ty - 1.0, 'F.SilkS', 0.9))
    board.append(text('RP2350A + ESP32-S3   CERN-OHL-W-2.0', XC, ty + 1.0, 'F.SilkS', 0.8))
    board.append(text('FujiNet  ColecoVision / ADAM', XC, ty - 1.0, 'B.SilkS', 1.0, mirror=True))
    board.append(text('BACK  (PINS 1-29)', XC, ty + 1.0, 'B.SilkS', 0.8, mirror=True))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
