#!/usr/bin/env python3
"""Generate Fujiversal-Atari2600-Rev1.kicad_pcb (placed, unrouted) from design.py.

Board: 54.4 x 88 mm (x 72.8..127.2, y 30..118), the FujiPlusCart prototype's
proven silhouette (Rev0): a 32.4 mm tab carrying the 2x12 gold fingers at
y = 118 (the insertion edge), 45-degree shoulders, full width from y = 92.3
up.  No parts below the shell's bottom (y 90.9): that part of the board goes
into the slot.  1.6 mm, 4 copper layers:
  F.Cu  signals + GND pour            (faces the console REAR: fingers 13-24)
  In1   GND plane
  In2   +3V3 plane, with a +3V3_RP island under the RP2354A and its ring and
        a DVDD island under its core (tongue to the regulator's 1V1 vias)
  B.Cu  signals + GND pour            (faces the console FRONT: fingers 1-12)
The finger strip (y > 110) is a rule area on F/B (fingers only); the inner
planes stop at y 109.  The ESP32-S3 antenna (the top 6 mm of the module) sits
flush with the top edge over a band that is copper-free on every layer.

The RP2350 core-regulator corner is Raspberry Pi's own RP2350A minimal-design
layout (tools/rpi_core_graft.sexpr, MIT): its parts and copper are placed
relative to the RP2354A and turned with it (datasheet 6.3.8: "follow this
layout as closely as possible").

Footprints are written as S-expressions (the SWIG pcbnew bindings are not
reliable under Python 3.14); route.py does the DSN/SES round trip and the
zone fills through pcbnew.

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
X0, Y0, X1, Y1 = 72.8, 30.0, 127.2, 118.0
XC = (X0 + X1) / 2
TAB_HW = 16.2             # tab half-width (32.4 mm, as the prototype)
TAB_TOP = Y1 - 15.56      # tab straight section ends here ...
SHOULDER = Y1 - 25.72     # ... and the 45-degree shoulders reach full width here
CHAMF = 1.0               # tab corner chamfer
FINGER_Y = Y1 - 8.0       # finger strip: no tracks / vias / pour on F.Cu or B.Cu below this
TAB_Y = FINGER_Y - 0.5    # routers stay above this; a finger is entered at its neck (y < 110)
BLADE_Y = TAB_Y           # (fanout.py name)
PLANE_Y = Y1 - 9.0        # inner planes stop short of the fingers and the bevel
PARTS_MAX_Y = 90.5        # courtyards above the shell's bottom (case: bottom_y 90.9)
THICKNESS = 1.6
HOLES = [(76.0, 60.4, 3.2), (124.6, 63.6, 3.2), (76.0, 88.6, 3.2), (125.0, 88.6, 3.2)]   # M3 shell screws
ANT_KEEP = (X0, Y0, 97.6, 36.8)   # antenna band: module antenna (6 mm) + 0.7 mm, 5.3 mm past its side
PWR_LAYER = 'In2.Cu'
UNDER = 3.0               # half-size of the square under the RP2354A the finisher keeps off F.Cu


def outline_pts():
    """Board outline, clockwise from the top-left (y down)."""
    return [(X0, Y0), (X1, Y0), (X1, SHOULDER), (XC + TAB_HW, TAB_TOP), (XC + TAB_HW, Y1 - CHAMF),
            (XC + TAB_HW - CHAMF, Y1), (XC - TAB_HW + CHAMF, Y1), (XC - TAB_HW, Y1 - CHAMF),
            (XC - TAB_HW, TAB_TOP), (X0, SHOULDER)]


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


def schematic_netlist():
    """(ref, pad) -> net name, from the generated schematic (kicad-cli), so the
    board carries exactly the schematic's nets -- including KiCad's own
    unconnected-(...) names for no-connect pins."""
    fn = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-rev1-gen.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    t = parse(open(fn).read())
    out = {}
    for n in findall(find(t, 'nets'), 'net'):
        name = str(find(n, 'name')[1])
        for nd in findall(n, 'node'):
            out[(str(find(nd, 'ref')[1]), str(find(nd, 'pin')[1]))] = name
    return out


NETLIST = {}
import re as _re
SMALL = _re.compile(r'_0603_|_0805_|0402|SOD-523|SOT-23|SOT-363|R_Array|AOTA|Crystal_SMD|WS2812|TSOT|TestPoint')


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
                if net and sn != net:
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


def zone(name, net, layer, pts, keepout=None, priority=0):
    """keepout: None (copper zone) or a dict of rule-area permissions overriding 'not_allowed'."""
    z = ['zone', ['net', Q(net or '')], ['layer', Q(layer)], ['uuid', uid('zone', name, layer)],
         ['name', Q(name)], ['hatch', 'edge', 0.5]]
    if priority:
        z.append(['priority', priority])
    z += [['connect_pads', ['clearance', 0 if keepout is not None else 0.25]], ['min_thickness', 0.25]]
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


# ---- Raspberry Pi RP2350A minimal-design regulator corner -------------------
GRAFT = parse(open(os.path.join(HERE, 'rpi_core_graft.sexpr')).read())
# the reference's designators -> this board's design.py keys (same footprints, same pad nets)
GRAFT_KEY = {'U1': 'U_RP', 'L1': 'L_VREG', 'C15': 'C_VOUT', 'C10': 'C_VIN', 'C16': 'C_FILT',
             'R1': 'R_FILT', 'R11': 'R_USBP', 'R12': 'R_USBM', 'C8': 'C_OTP'}
GRAFT_NET = {'+3V3': D.RP_RAIL}      # the reference's single 3.3 V rail is this board's RP rail
# DVDD island on In2, relative to U1 at rotation 0 (y down): under the core, plus a tongue
# north to the regulator's two 1V1 vias by L1 (graft vias at (0.5, -5.2) / (0.5, -5.8))
DVDD_ISLAND = [(-2.9, -2.9), (0.0, -2.9), (0.0, -6.15), (1.0, -6.15), (1.0, -2.9), (2.9, -2.9),
               (2.9, 2.9), (-2.9, 2.9)]


def rp_xy(lx, ly):
    """U1-local (rotation 0) -> board coordinates, turned with the RP."""
    ux, uy, ur = PLACE['U1']
    dx, dy = rot_pt(lx, ly, ur)
    return round(ux + dx, 4), round(uy + dy, 4)


def graft_parts():
    ur = PLACE['U1'][2]
    for e in GRAFT[1:]:
        if e[0] == 'part' and e[1] != 'U1':
            a = find(e, 'at')
            x, y = rp_xy(float(a[1]), float(a[2]))
            PLACE[D.KEY[GRAFT_KEY[str(e[1])]]] = (x, y, (float(a[3]) + ur) % 360)


def gnet(e):
    n = str(find(e, 'net')[1])
    return GRAFT_NET.get(n, n)


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
    """Copper under the RP2354A, after the minimal design:
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
    u1 = [e for e in board if isinstance(e, list) and e and e[0] == 'footprint'
          and any(p[1] == 'Reference' and p[2] == 'U1' for p in findall(e, 'property'))][0]
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
    from placement import RP_ISLAND, DVDD_LOBE
    if point_in_poly(x, y, [rp_xy(px, py) for px, py in DVDD_ISLAND]) or point_in_poly(x, y, DVDD_LOBE):
        return 'DVDD'
    if point_in_poly(x, y, RP_ISLAND):
        return D.RP_RAIL
    return '+3V3'


def finger_gnd_vias(board):
    """The two GND fingers (12 on B.Cu, 24 on F.Cu) stitch straight into the In1
    plane at the top of their necks.  The fingers are back to back, so a via ON
    a neck would hit the other face's neck: go 1.27 mm outboard, between columns."""
    out = []
    for e in board:
        if isinstance(e, list) and e and e[0] == 'footprint' and \
                any(p[1] == 'Reference' and p[2] == D.KEY['J_EDGE'] for p in findall(e, 'property')):
            jx, jy = float(find(e, 'at')[1]), float(find(e, 'at')[2])
            for pd in findall(e, 'pad'):
                a, sz = find(pd, 'at'), find(pd, 'size')
                if find(pd, 'net') and str(find(pd, 'net')[1]) == 'GND' and float(sz[1]) < 1.0:    # the neck
                    nx, ny = jx + float(a[1]), round(jy + float(a[2]) - float(sz[2]) / 2 + 0.4, 4)
                    vx = round(nx + math.copysign(1.27, nx - jx), 4)
                    layer = [str(l) for l in find(pd, 'layers')[1:]][0]
                    out.append(seg(nx, ny, vx, ny, 0.4, layer, 'GND', ('fingergnds', pd[1])))
                    out.append(via(vx, ny, 'GND', ('fingergnd', pd[1])))
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
    skip = {id(p) for p in pads if id(p) in served and (p.net == 'GND' or p.ref == 'U1')}

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
        if p.net in ('+3V3', D.RP_RAIL, 'DVDD') and plane_net_at(*via_spot(p)) != p.net:
            skip.add(id(p))
    keep = [crt[r] for r in (D.KEY[k] for k in ('J_SD', 'J_USB', 'SW_RESET', 'SW_BOOTSEL', 'SW_S3EN', 'SW_S3BOOT'))
            if r in crt]
    ux, uy, _ = PLACE['U1']
    keep.append((ux - UNDER, uy - UNDER, ux + UNDER, uy + UNDER))   # no fan-out vias under the RP2354A
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
    pro['pcbnew'] = pro.get('pcbnew', {})
    pro['pcbnew'].setdefault('last_paths', {})['specctra_dsn'] = ''
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')
    K = D.KEY
    solid = ' || '.join("A.memberOfFootprint('%s')" % K[k] for k in ('U_RP', 'U_UART', 'U_BUCK', 'U_LDO'))
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
             '// Board (KiCad) coordinates; the shell file maps them with Y().',
             'board = [%g, %g, %g, %g];   // x0, y0, x1, y1 (top edge y0, insertion edge y1)' % (X0, Y0, X1, Y1),
             'shoulder_y = %g;             // full board width above this y; shell stops above it' % SHOULDER,
             'sw_reset   = [%g, %g];' % at('SW_RESET'),
             'sw_bootsel = [%g, %g];' % at('SW_BOOTSEL'),
             'sw_s3rst   = [%g, %g];' % at('SW_S3EN'),
             'sw_s3boot  = [%g, %g];' % at('SW_S3BOOT'),
             'ws_led     = [%g, %g];   // WS2812 light pipe' % at('D_WS'),
             'rp_led     = [%g, %g];   // RP activity LED' % at('D_LED'),
             'usb_x      = %g;         // USB-C exits the top edge' % at('J_USB')[0],
             'sd_y       = %g;         // microSD exits the right edge' % at('J_SD')[1],
             'ant        = [%g, %g];   // ESP32-S3 module centre (antenna flush with the top edge)' % at('U_S3'),
             'holes = [%s];' % ', '.join('[%g, %g]' % (x, y) for x, y, d in HOLES), '']
    os.makedirs(os.path.join(PRJ, 'case'), exist_ok=True)
    open(os.path.join(PRJ, 'case', 'board-anchors.scad'), 'w').write('\n'.join(lines))


FIDUCIALS = [('FID1', 94.8, 39.4), ('FID2', 76.6, 92.6), ('FID3', 123.4, 92.6)]


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
        if y1 > PARTS_MAX_Y or x0 < X0 - 0.01 or x1 > X1 + 0.01 or y0 < Y0 - 0.2:
            bad.append('%s(%s)' % (p.ref, p.key))
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
    NETLIST.update(schematic_netlist())
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
        u = gen_sch.units_of(syms[p.lib_id])[0]
        path = '/%s/%s' % (gen_sch.uid('sheet', p.sheet), gen_sch.uid(p.sheet, p.ref, u))
        ds = ''
        for pr in findall(syms[p.lib_id], 'property'):
            if pr[1] == 'Datasheet':
                ds = str(pr[2])
        board.append(instance(p, x, y, r, path, '/%s/' % p.sheet, p.sheet + '.kicad_sch', ds))
    check_parts_inside(board)
    for i, (x, y, d) in enumerate(HOLES, 1):
        board.append(board_only('H%d' % i, 'MountingHole_3.2mm_NPTH', x, y, 'M3 shell screw'))
    for name, x, y in FIDUCIALS:
        board.append(board_only(name, 'Fiducial_1mm_Mask2mm', x, y, 'assembly fiducial'))
    extra = graft_copper() + rp_ring(board) + finger_gnd_vias(board)
    board += extra
    add_fanout(board, extra)
    board += outline()
    # finger strip: fingers only on F/B
    strip = [(XC - TAB_HW - 1, FINGER_Y), (XC + TAB_HW + 1, FINGER_Y), (XC + TAB_HW + 1, Y1 + 1),
             (XC - TAB_HW - 1, Y1 + 1)]
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('finger_strip_' + L[0], None, L, strip, keepout={}))
    # antenna band: nothing, on any layer
    ax0, ay0, ax1, ay1 = ANT_KEEP
    band = [(ax0 - 1, ay0 - 1), (ax1, ay0 - 1), (ax1, ay1), (ax0 - 1, ay1)]
    for L in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
        board.append(zone('antenna_' + L.split('.')[0], None, L, band, keepout={'pads': 'allowed'}))
    board.append(zone('GND_plane', 'GND', 'In1.Cu', BODY))
    board.append(zone('3V3_plane', '+3V3', PWR_LAYER, BODY))
    from placement import RP_ISLAND
    board.append(zone('rp_io_island', D.RP_RAIL, PWR_LAYER, RP_ISLAND, priority=3))
    board.append(text('THIS SIDE TO CONSOLE REAR', XC, 96.4, 'F.SilkS', 1.4))
    board.append(text('Fujiversal-Atari2600 Rev1', XC, 98.8, 'F.SilkS', 1.0))
    board.append(text('THIS SIDE TO CONSOLE FRONT', XC, 96.4, 'B.SilkS', 1.4, mirror=True))
    board.append(text('FujiNet  Atari 2600', XC, 99.2, 'B.SilkS', 2.0, mirror=True))
    board.append(text('RP2354A + ESP32-S3   CERN-OHL-W-2.0', XC, 101.8, 'B.SilkS', 0.9, mirror=True))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
