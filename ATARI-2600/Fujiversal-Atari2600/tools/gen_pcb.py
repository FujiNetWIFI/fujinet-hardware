#!/usr/bin/env python3
"""Generate Fujiversal-Atari2600-Rev0.kicad_pcb (placed, unrouted) from design.py.

Board: 54.4 x 88 mm (x 72.8..127.2, y 30..118), the FujiPlusCart prototype's
proven silhouette: a 32.4 mm tab carrying the 2x12 gold fingers at y = 118
(the insertion edge), 45-degree shoulders, full width from y = 92.3 up.  No
parts below the shoulders (that part of the board goes into the slot).
4 layers: F.Cu signal / In1.Cu GND plane / In2.Cu +3V3 plane / B.Cu signal.
F.Cu faces the console REAR (pins 13-24), B.Cu the FRONT (pins 1-12).
y = 30 is the top: USB-C and the microSD slot exit there and the ESP32-S3
antenna sits flush with it.

The footprints are written as S-expressions (the SWIG pcbnew bindings are
not reliable under Python 3.14); route.py does the DSN/SES round trip and
the zone fills through pcbnew.

Usage: python3 tools/gen_pcb.py
"""
import os, sys, math, uuid, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
import design as D
import gen_sch

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
X0, Y0, X1, Y1 = 72.8, 30.0, 127.2, 118.0
XC = (X0 + X1) / 2
TAB_HW = 16.2             # tab half-width (32.4 mm, as the prototype)
TAB_TOP = Y1 - 15.56      # tab straight section ends here ...
SHOULDER = Y1 - 25.72     # ... and the 45-degree shoulders reach full width here
PARTS_MAX_Y = SHOULDER - 1.0
FINGER_Y = Y1 - 8.0       # finger strip: no tracks / vias / pour on F.Cu or B.Cu below this
BLADE_Y = FINGER_Y        # (name kept for fanout.py / finish_route.py)
PLANE_Y = Y1 - 9.0        # inner planes stop short of the fingers and the bevel
CHAMF = 1.0               # tab corner chamfer
# no fan-out vias here: the RP2040's USB pair (pins 46/47) leaves west through this lane
VIA_KEEP = [(88.8, 66.0, 102.3, 69.2)]
HOLES = [(76.0, 55.6), (125.0, 51.6), (76.0, 88.6), (124.0, 88.6)]


def outline_pts():
    """Board outline, clockwise from the top-left (top corners get arcs in outline())."""
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

# ref -> (x, y, rotation deg CCW)  -- top view, y down
PLACE = {}


def place(ref, x, y, rot=0):
    PLACE[ref] = (x, y, rot)


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
    import subprocess, tempfile
    fn = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-gen.net')
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
SMALL = _re.compile(r'_0603_|_0805_|SOD-523|SOT-23|SOT-363|R_Array|L_2016|Crystal_SMD|WS2812|TSOT')


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
                # small parts: 0.8 mm refs (JLC-legible minimum) keep the RP ring tidier
                pr = [e for e in pr if not (isinstance(e, list) and e and e[0] == 'effects')]
                pr.append(['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]]])
            out.append(pr); done.add(k)
    for k, v in fields.items():
        if k not in done:
            out.append(['property', Q(k), Q(v), ['at', 0, 0, rot], ['layer', Q('F.Fab')], ['hide', 'yes'],
                        ['uuid', uid(part.ref, 'prop', k)],
                        ['effects', ['font', ['size', 1.27, 1.27], ['thickness', 0.15]]]])
    out += [['path', Q(path)], ['sheetname', Q(sheetname)], ['sheetfile', Q(sheetfile)]]
    attr = find(fp, 'attr')
    if attr:
        a = list(attr)
        if not part.bom and 'exclude_from_bom' not in a:
            a.append('exclude_from_bom')
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
            e = [x for x in e if not (isinstance(x, list) and x and x[0] in ('net', 'uuid'))]
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
            layers = [str(x) for x in find(e, 'layers')[1:]]
            th = e[2] in ('thru_hole', 'np_thru_hole')
            if th:
                layers = ['F.Cu', 'B.Cu']
            pads.append(fanout.Pad(ref, str(e[1]), str(net[1]) if net else None, fx + dx, fy + dy,
                                   w / 2, h / 2, layers, th, (fx, fy)))
    return pads, crt


UNDER = 0.0   # (finish_route.py: no special keep-off square under the RP2040)


def rp_dvdd_link(board):
    """VREG_VOUT (pin 45) -> DVDD (pins 50 and 23): locked F.Cu inside the
    RP2040's pin ring, between the pads' inner ends and the exposed pad, as
    Raspberry Pi's minimal design runs it.  Pins 46-49 (USB, USB_VDD, IOVDD)
    sit between the two, so outside the ring the link would wall in the USB
    pair."""
    u1 = [e for e in board if isinstance(e, list) and e and e[0] == 'footprint'
          and any(p[1] == 'Reference' and p[2] == 'U1' for p in findall(e, 'property'))][0]
    pads, _ = board_pads([u1])
    p = {n: [q for q in pads if q.num == n][0] for n in ('45', '50', '23')}
    cx, cy = p['45'].fp_xy
    R = 2.35      # inner band: EP edge at 1.6 mm, pad inner ends at ~3.0 mm from the centre

    def inner(q):
        if abs(q.cx - cx) > abs(q.cy - cy):
            return (round(cx + math.copysign(R, q.cx - cx), 4), q.cy)
        return (q.cx, round(cy + math.copysign(R, q.cy - cy), 4))
    a, b, c = inner(p['45']), inner(p['50']), inner(p['23'])
    # 45 -> 50 down the west band; 45 -> round the band on 45's side -> 23 on the
    # opposite face, so DVDD pin 23 needs no route across the SWD/RUN escapes
    side = math.copysign(R, a[1] - cy) if abs(a[0] - cx) > abs(a[1] - cy) else 0.0
    corner1, corner2 = (a[0], round(cy + side, 4)), (c[0], round(cy + side, 4))
    paths = [[(p['45'].cx, p['45'].cy), a, b, (p['50'].cx, p['50'].cy)],
             [a, corner1, corner2, c, (p['23'].cx, p['23'].cy)]]
    out = []
    for k, pts in enumerate(paths):
        out += [['segment', ['start', *pts[i]], ['end', *pts[i + 1]], ['width', 0.25], ['layer', Q('F.Cu')],
                 ['locked', 'yes'], ['net', Q('DVDD')], ['uuid', uid('dvdd', k, i)]] for i in range(len(pts) - 1)]
    return out


def rp_usb_link(board):
    """RP2040 USB_DM/DP (pins 46/47) -> R8/R7 (27R) as locked F.Cu, drawn
    rather than searched: the pair leaves the pins 0.4 mm apart, so a greedy
    router routing one line first always cuts off the other.  DM (the upper
    pin) takes the inner path to R8, DP the outer one to R7."""
    fps = {}
    for e in board:
        if isinstance(e, list) and e and e[0] == 'footprint':
            ref = [str(p[2]) for p in findall(e, 'property') if p[1] == 'Reference'][0]
            if ref in ('U1', 'R7', 'R8'):
                fps[ref] = e
    pads, _ = board_pads(list(fps.values()))
    pad = lambda r, n: [p for p in pads if p.ref == r and p.num == n][0]
    dm, dp = pad('U1', '46'), pad('U1', '47')
    r8, r7 = pad('R8', '2'), pad('R7', '2')          # RP-side pads (south ends)
    assert dm.cy < dp.cy and r7.cx < r8.cx, 'rp_usb_link: placement changed'
    xo = dm.cx - 1.3                                  # clear of the pin row, then spread
    y_dm, y_dp = dm.cy - 0.3, dp.cy + 0.3
    paths = {'RP_USB_DM': [(dm.cx, dm.cy), (xo, dm.cy), (xo - 0.3, y_dm), (r8.cx + 0.6, y_dm),
                           (r8.cx, y_dm - 0.6), (r8.cx, r8.cy)],
             'RP_USB_DP': [(dp.cx, dp.cy), (xo, dp.cy), (xo - 0.3, y_dp), (r7.cx + 0.6, y_dp),
                           (r7.cx, y_dp - 0.6), (r7.cx, r7.cy)]}
    out = []
    for net, pts in paths.items():
        pts = [(round(x, 4), round(y, 4)) for x, y in pts]
        out += [['segment', ['start', *pts[i]], ['end', *pts[i + 1]], ['width', 0.25], ['layer', Q('F.Cu')],
                 ['locked', 'yes'], ['net', Q(net)], ['uuid', uid('usb', net, i)]] for i in range(len(pts) - 1)]
    return out


def add_fanout(board):
    import fanout
    pads, crt = board_pads(board)
    keep = [crt[r] for r in ('U6', 'J2', 'J3', 'SW1', 'SW2', 'SW3', 'SW4') if r in crt] + VIA_KEEP
    holes = [(x, y, 1.6) for x, y in HOLES]
    locked = [(float(find(e, 'start')[1]), float(find(e, 'start')[2]), float(find(e, 'end')[1]),
               float(find(e, 'end')[2]), str(find(e, 'net')[1]), float(find(e, 'width')[1]))
              for e in board if isinstance(e, list) and e and e[0] == 'segment']   # e.g. rp_dvdd_link
    vias, segs, failed = fanout.plan(pads, keep, (X0, Y0, X1, Y1), BLADE_Y, holes, skip_refs=('J1',),
                                     extra_segs=locked, outline=outline_pts())
    for i, (x, y, n) in enumerate(vias):
        board.append(['via', ['at', x, y], ['size', fanout.VIA_D], ['drill', fanout.VIA_DRILL],
                      ['layers', Q('F.Cu'), Q('B.Cu')], ['locked', 'yes'], ['net', Q(n)], ['uuid', uid('fv', i)]])
    for i, (x0, y0, x1, y1, n, w) in enumerate(segs):
        board.append(['segment', ['start', round(x0, 4), round(y0, 4)], ['end', x1, y1],
                      ['width', round(w, 3)], ['layer', Q('F.Cu')], ['locked', 'yes'], ['net', Q(n)],
                      ['uuid', uid('fs', i)]])
    print('fan-out: %d vias, %d stubs%s' % (len(vias), len(segs),
          ('; FAILED: ' + ' '.join(failed)) if failed else ''))


def outline():
    r = 2.0
    pts = outline_pts()
    g = []
    # top edge + the two top corners as arcs; everything else straight lines
    k = r * (1 - math.sqrt(0.5))
    segs = [((X0 + r, Y0), (X1 - r, Y0)), ((X1, Y0 + r), pts[2])]
    segs += [(pts[i], pts[i + 1]) for i in range(2, len(pts) - 1)]
    segs += [(pts[-1], (X0, Y0 + r))]
    for i, (a, b) in enumerate(segs):
        g.append(['gr_line', ['start', *a], ['end', *b], ['stroke', ['width', 0.1], ['type', 'default']],
                  ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', i)]])
    arcs = [((X0, Y0 + r), (X0 + k, Y0 + k), (X0 + r, Y0)), ((X1 - r, Y0), (X1 - k, Y0 + k), (X1, Y0 + r))]
    for i, (a, m, b) in enumerate(arcs):
        g.append(['gr_arc', ['start', *a], ['mid', round(m[0], 4), round(m[1], 4)], ['end', *b],
                  ['stroke', ['width', 0.1], ['type', 'default']], ['layer', Q('Edge.Cuts')], ['uuid', uid('arc', i)]])
    return g


def zone(name, net, layer, pts, keepout=False, priority=0):
    z = ['zone', ['net', Q(net)] if net else ['net', Q('')], ['layer', Q(layer)], ['uuid', uid('zone', name)],
         ['name', Q(name)], ['hatch', 'edge', 0.5]]
    if priority:
        z.append(['priority', priority])
    z += [['connect_pads', ['clearance', 0 if keepout else 0.25]], ['min_thickness', 0.25]]
    if keepout:
        z.append(['keepout', ['tracks', 'not_allowed'], ['vias', 'not_allowed'], ['pads', 'allowed'],
                  ['copperpour', 'not_allowed'], ['footprints', 'allowed']])
        z.append(['placement', ['enabled', 'no'], ['sheetname', Q('')]])
    z.append(['fill', 'yes', ['thermal_gap', 0.3], ['thermal_bridge_width', 0.4], ['island_removal_mode', 0]]
             if not keepout else
             ['fill', ['thermal_gap', 0.5], ['thermal_bridge_width', 0.5], ['island_removal_mode', 0]])
    z.append(['polygon', ['pts'] + [['xy', x, y] for x, y in pts]])
    return z


def text(s, x, y, layer, size=1.0, mirror=False, rot=0):
    eff = ['effects', ['font', ['size', size, size], ['thickness', size * 0.15]]]
    if mirror:
        eff.append(['justify', 'mirror'])
    return ['gr_text', Q(s), ['at', x, y, rot], ['layer', Q(layer)], ['uuid', uid('text', s)], eff]


# ---------------------------------------------------------------------------
from placement import do_placement  # noqa: E402  (placement table lives in its own file)


NETCLASSES = [  # name, clearance, track, via dia, via drill, nets
    ('PWR', 0.2, 0.5, 0.8, 0.4, ['+5V', 'VIN', 'BUCK_SW']),
    # VBUS threads between the USB-C pads; 0.3 mm (~0.9 A outer) covers the board's USB draw
    ('VBUS', 0.15, 0.3, 0.6, 0.3, ['VBUS']),
    ('USB', 0.15, 0.25, 0.6, 0.3, ['USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM']),
]


def configure_project():
    """Design rules + net classes in the .kicad_pro (JLCPCB 4-layer capable)."""
    import json
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    r = pro['board']['design_settings']['rules']
    r.update({'min_clearance': 0.12, 'min_copper_edge_clearance': 0.25, 'min_track_width': 0.1,
              'min_via_diameter': 0.5, 'min_through_hole_diameter': 0.25, 'min_hole_clearance': 0.25,
              'min_hole_to_hole': 0.25, 'min_via_annular_width': 0.1})
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
    open(os.path.join(PRJ, D.PROJECT + '.kicad_dru'), 'w').write(
        '(version 1)\n'
        '(rule "default_clearance"\n'
        '\t(constraint clearance (min 0.15mm)))\n'
        # the QFN exposed pads and their via arrays: solid, no thermal spokes
        '(rule "ep_solid"\n'
        '\t(condition "A.NetName == \'GND\' && (A.memberOfFootprint(\'U1\') || A.memberOfFootprint(\'U7\'))")\n'
        '\t(constraint zone_connection solid))\n')
    # ERC: unused 74LVC245A inputs are tied straight to GND (the right thing
    # for CMOS inputs); KiCad's default matrix warns bidirectional <-> power
    # output for that.  Make that pair OK, nothing else.
    pro = json.load(open(fn))
    pm = pro['erc']['pin_map']
    pm[2][8] = pm[8][2] = 0
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')


def write_case_anchors():
    """case/board-anchors.scad: the shell openings follow the placement."""
    def at(ref):
        return PLACE[ref][0], PLACE[ref][1]
    lines = ['// GENERATED by tools/gen_pcb.py from tools/placement.py -- do not edit.',
             '// Board (KiCad) coordinates; the shell file maps them with bx()/by().',
             'board = [%g, %g, %g, %g];   // x0, y0, x1, y1 (top edge y0, insertion edge y1)' % (X0, Y0, X1, Y1),
             'shoulder_y = %g;             // full board width above this y; shell stops above it' % SHOULDER,
             'sw_reset   = [%g, %g];' % at('SW1'),
             'sw_bootsel = [%g, %g];' % at('SW2'),
             'sw_s3rst   = [%g, %g];' % at('SW3'),
             'sw_s3boot  = [%g, %g];' % at('SW4'),
             'ws_led     = [%g, %g];   // WS2812 light pipe' % at('D3'),
             'rp_led     = [%g, %g];   // RP activity LED' % at('D2'),
             'usb_x      = %g;         // USB-C exits the top edge' % at('J3')[0],
             'sd_x       = %g;         // microSD exits the top edge' % at('J2')[0],
             'ant        = [%g, %g];   // ESP32-S3 module centre (antenna at the top edge)' % at('U6'),
             'holes = [%s];' % ', '.join('[%g, %g]' % h for h in HOLES), '']
    os.makedirs(os.path.join(PRJ, 'case'), exist_ok=True)
    open(os.path.join(PRJ, 'case', 'board-anchors.scad'), 'w').write('\n'.join(lines))


def main():
    configure_project()
    do_placement(place)
    write_case_anchors()
    NETLIST.update(schematic_netlist())
    hdr = parse(open(os.path.join(HERE, 'pcb_header.sexpr')).read())
    # 4 layers: F.Cu signal / In1 GND plane / In2 +3V3 plane / B.Cu signal
    layers = find(hdr, 'layers')
    rest = [l for l in layers[1:] if not str(l[1]).endswith('.Cu')]
    kinds = {'F.Cu': 'signal', 'In1.Cu': 'power', 'In2.Cu': 'power', 'B.Cu': 'signal'}
    ids = {'F.Cu': '0', 'B.Cu': '2', 'In1.Cu': '4', 'In2.Cu': '6'}
    layers[1:] = [[ids[n], Q(n), kinds[n]] for n in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')] + rest
    board = hdr
    missing = [p.ref for p in D.PARTS if p.ref not in PLACE]
    if missing:
        raise SystemExit('unplaced: ' + ' '.join(missing))
    low = [p.ref for p in D.PARTS if p.ref != 'J1' and PLACE[p.ref][1] > PARTS_MAX_Y]
    if low:
        raise SystemExit('parts below the shoulders (they would enter the slot): ' + ' '.join(low))
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
    for i, (x, y) in enumerate(HOLES, 1):
        h = D.Part('H', D.LIB + ':MountingHole_3.2mm_NPTH', 'M3', D.FP('MountingHole_3.2mm_NPTH'), {},
                   None, desc='M3 shell screw', bom=False)
        h.ref = 'H%d' % i
        fp = instance(h, x, y, 0, '', '', '')
        fp = [e for e in fp if not (isinstance(e, list) and e and e[0] in ('path', 'sheetname', 'sheetfile'))]
        board.append(fp)
    # the edge GND fingers (pins 12, 24) stitch straight into the In1 GND
    # plane at the top of their necks -- never through a pour island
    for e in board:
        if isinstance(e, list) and e and e[0] == 'footprint' and \
                any(p[1] == 'Reference' and p[2] == 'J1' for p in findall(e, 'property')):
            jx, jy = float(find(e, 'at')[1]), float(find(e, 'at')[2])
            for pd in findall(e, 'pad'):
                a, sz = find(pd, 'at'), find(pd, 'size')
                if str(find(pd, 'net')[1]) == 'GND' and float(sz[1]) < 1.0:    # the neck
                    # fingers are back to back, so a via ON the neck would hit the
                    # other face's neck: go 1.27 mm outboard, between finger columns
                    nx, ny = jx + float(a[1]), round(jy + float(a[2]) - float(sz[2]) / 2 + 0.4, 4)
                    vx = round(nx + math.copysign(1.27, nx - jx), 4)
                    layer = [str(l) for l in find(pd, 'layers')[1:]][0]
                    board.append(['segment', ['start', nx, ny], ['end', vx, ny], ['width', 0.4], ['layer', Q(layer)],
                                  ['locked', 'yes'], ['net', Q('GND')], ['uuid', uid('fingergnds', pd[1])]])
                    board.append(['via', ['at', vx, ny], ['size', 0.6], ['drill', 0.3], ['layers', Q('F.Cu'), Q('B.Cu')],
                                  ['locked', 'yes'], ['net', Q('GND')], ['uuid', uid('fingergnd', pd[1])]])
    board += rp_dvdd_link(board)
    board += rp_usb_link(board)
    add_fanout(board)
    board += outline()
    strip = [(XC - TAB_HW - 1, FINGER_Y), (XC + TAB_HW + 1, FINGER_Y), (XC + TAB_HW + 1, Y1 + 1),
             (XC - TAB_HW - 1, Y1 + 1)]
    for L in ('F.Cu', 'B.Cu'):
        board.append(zone('finger_strip_' + L[0], None, L, strip, keepout=True))
    plane = clip_below(outline_pts(), PLANE_Y)
    board.append(zone('GND_plane', 'GND', 'In1.Cu', plane))
    board.append(zone('3V3_plane', '+3V3', 'In2.Cu', plane))
    board.append(text('THIS SIDE TO CONSOLE REAR', XC, 96.2, 'F.SilkS', 1.4))
    board.append(text('Fujiversal-Atari2600 Rev0', XC, 98.6, 'F.SilkS', 1.0))
    board.append(text('THIS SIDE TO CONSOLE FRONT', XC, 96.2, 'B.SilkS', 1.4, mirror=True))
    board.append(text('FujiNet  Atari 2600', XC, 99.0, 'B.SilkS', 2.0, mirror=True))
    board.append(text('RP2040 + ESP32-S3', XC, 101.6, 'B.SilkS', 1.0, mirror=True))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
