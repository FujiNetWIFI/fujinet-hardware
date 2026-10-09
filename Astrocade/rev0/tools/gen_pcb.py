#!/usr/bin/env python3
"""Generate FujiNet-Astrocade-Rev0.kicad_pcb (placed, unrouted) from design.py.

Board: 96 x 58 mm Astrocade cassette PCB (x 52..148, y 30..88).  STACKUP picks
  4 layers: F.Cu signal / In1.Cu GND plane / In2.Cu power plane / B.Cu signal
  6 layers: F.Cu / In1.Cu GND / In2.Cu + In3.Cu signal / In4.Cu power plane / B.Cu
The power plane is +3V3 (buck: S3, CP2102N, microSD) with a +3V3_RP island
under the RP2354A region (its own LDO) and a DVDD island under the core.  y=88 is the insertion
edge; the 26 contact lands are on B.Cu along it and the console blade wipes
the south 16.5 mm of the underside, so that strip is a B.Cu rule area.
y=30 is the trailing edge: USB-C and the microSD slot exit there, the
ESP32-S3 antenna overhangs it.

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
X0, Y0, X1, Y1 = 52.0, 30.0, 148.0, 88.0
TAB_Y = Y1                # no connector tab: the routable body reaches the insertion edge
BODY = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
OUTLINE = BODY            # (the 2 mm corner radii are cut by outline(); routers keep 0.25+ off the edge)
BLADE_Y = 71.5            # B.Cu rule area: y >= BLADE_Y
HOLES = [(55, 33, 3.2), (145, 33, 3.2), (55, 84, 3.2), (145, 84, 3.2)]   # (x, y, diameter) M3 NPTH, shell posts
FIDUCIALS = [('FID1', 139.0, 32.2), ('FID2', 60.5, 75.0), ('FID3', 139.5, 75.0)]   # board-only, not in the BOM/CPL

STACKUP = 6               # 4 or 6 copper layers: 4 was tried first and did not close (docs/design-review-rev0.md)
SIGNAL_LAYERS = ('F.Cu', 'B.Cu') if STACKUP == 4 else ('F.Cu', 'In2.Cu', 'In3.Cu', 'B.Cu')
PWR_LAYER = 'In2.Cu' if STACKUP == 4 else 'In4.Cu'
RP_RAIL = '+3V3_RP'
# +3V3_RP island on the power plane (board coordinates): the RP2354A, its decoupling and
# pull-ups, the crystal, and the AP2112K LDO -- the rest of the plane is +3V3
RP_ISLAND = [(82.0, 50.3), (90.0, 50.3), (90.0, 49.0), (96.5, 49.0), (96.5, 46.0), (104.5, 46.0), (104.5, 49.0), (116.0, 49.0),
             (116.0, 56.0), (123.5, 56.0), (123.5, 71.0), (82.0, 71.0)]   # keeps the SD / CP2102N +3V3 parts out

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
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-astrocade-gen.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    t = parse(open(fn).read())
    out = {}
    for c in findall(find(t, 'components'), 'comp'):
        COMP_SHEET[str(find(c, 'ref')[1])] = str(find(find(c, 'sheetpath'), 'names')[1])
    for n in findall(find(t, 'nets'), 'net'):
        name = str(find(n, 'name')[1])
        for nd in findall(n, 'node'):
            out[(str(find(nd, 'ref')[1]), str(find(nd, 'pin')[1]))] = name
    return out


NETLIST = {}
COMP_SHEET = {}  # ref -> the sheet kicad-cli files the component under ('/rp-core/')
import re as _re


def load_netlist():
    if not NETLIST:
        NETLIST.update(schematic_netlist())
    return NETLIST


def NET(short):
    """Full KiCad net name for a design.py net: nets local to a sheet carry its path
    (/cart-bus/CA0), nets wired between sheets on the root /NET; rails none."""
    names = set(load_netlist().values())
    if short in names:
        return short
    hits = [n for n in names if n.endswith('/' + short)]
    if len(hits) != 1:
        raise SystemExit('net %s: %s' % (short, hits or 'not in the schematic netlist'))
    return hits[0]


def fp_sheet_unit(p, syms):
    """The sheet and symbol unit a footprint links to.  A part drawn on several sheets (its units
    split between them: the RP2354A, unit A on cart-bus, B on rp-core) is filed by KiCad under the
    first of those sheets in hierarchy order, with the uuids of the units drawn there; the footprint
    path takes the lowest of those units.  Cross-checked against the netlist kicad-cli wrote."""
    units = gen_sch.units_of(syms[p.lib_id])
    on = {u: p.unit_sheets.get(u, p.sheet) for u in units}
    stem = min(set(on.values()), key=D.SHEET_ORDER.index)
    u = min(u for u, sh in on.items() if sh == stem)
    load_netlist()
    if COMP_SHEET and COMP_SHEET.get(p.ref) != '/%s/' % stem:
        raise SystemExit('%s: design puts the footprint on /%s/, kicad-cli on %s' % (p.ref, stem, COMP_SHEET.get(p.ref)))
    return stem, u


def SHORT(full):
    return full.rsplit('/', 1)[-1] if not full.startswith('unconnected-') else full
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
                if net and SHORT(sn or '') != net:
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


GRAFT = parse(open(os.path.join(HERE, 'rpi_core_graft.sexpr')).read())


GRAFT_NET = {'+3V3': RP_RAIL}   # the reference's single 3.3 V rail is this board's RP rail


def gnet(e):
    n = str(find(e, 'net')[1])
    return Q(NET(GRAFT_NET.get(n, n)))


def graft_copper(ux, uy):
    """Raspberry Pi's regulator-corner copper (tools/rpi_graft.py), moved to our U1."""
    out = []
    for i, e in enumerate(GRAFT[1:]):
        if e[0] == 'segment':
            s_, t_ = find(e, 'start'), find(e, 'end')
            if max(abs(float(s_[1])), abs(float(s_[2]))) < 3.1 or max(abs(float(t_[1])), abs(float(t_[2]))) < 3.1:
                continue    # under the package: the +3V3 ring (rp_ring) replaces it
            out.append(['segment', ['start', round(ux + float(s_[1]), 4), round(uy + float(s_[2]), 4)],
                        ['end', round(ux + float(t_[1]), 4), round(uy + float(t_[2]), 4)],
                        ['width', float(find(e, 'width')[1])], ['layer', find(e, 'layer')[1]], ['locked', 'yes'],
                        ['net', gnet(e)], ['uuid', uid('graft', i)]])
        elif e[0] == 'via':
            a = find(e, 'at')
            out.append(['via', ['at', round(ux + float(a[1]), 4), round(uy + float(a[2]), 4)], ['size', 0.6],
                        ['drill', 0.3], ['layers', Q('F.Cu'), Q('B.Cu')], ['locked', 'yes'],
                        ['net', gnet(e)], ['uuid', uid('graft', i)]])
        elif e[0] == 'zone':
            if str(find(e, 'net')[1]) == 'GND':
                continue    # the board-wide GND_top pour covers this corner (solid-connected, see .kicad_dru)
            pts = [(round(ux + float(p[1]), 4), round(uy + float(p[2]), 4)) for p in find(e, 'pts')[1:]]
            z = ['zone', ['net', gnet(e)], ['layer', find(e, 'layer')[1]], ['uuid', uid('graft', i)],
                 ['name', Q('rpi_graft_%d' % i)], ['hatch', 'edge', 0.5], ['priority', int(find(e, 'priority')[1]) + 10],
                 ['connect_pads', 'yes', ['clearance', float(find(e, 'clearance')[1])]],
                 ['min_thickness', float(find(e, 'min_thickness')[1])],
                 ['fill', 'yes', ['thermal_gap', 0.3], ['thermal_bridge_width', 0.3], ['island_removal_mode', 0]],
                 ['polygon', ['pts'] + [['xy', x, y] for x, y in pts]]]
            out.append(z)
    return out


UNDER = 3.0   # half-size of the square under the RP2354A the finisher keeps off F.Cu/In2
# DVDD island on the power plane, relative to U1 (y down): under the core, plus a tongue
# north to the regulator's 1V1 vias by L1
DVDD_ISLAND = [(-2.9, -2.9), (0.0, -2.9), (0.0, -6.15), (1.0, -6.15), (1.0, -2.9), (2.9, -2.9), (2.9, 2.9), (-2.9, 2.9)]


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % n]
        if (ya > y) != (yb > y) and x < xa + (y - ya) * (xb - xa) / (yb - ya):
            inside = not inside
    return inside


def dvdd_island():
    return DVDD_ISLAND


def plane_net_at(x, y):
    """Which net the power plane carries at (x, y)."""
    ux, uy, _ = PLACE['U1']
    if point_in_poly(x - ux, y - uy, DVDD_ISLAND):
        return 'DVDD'
    if point_in_poly(x, y, RP_ISLAND):
        return RP_RAIL
    return '+3V3'


def rp_ring(board, ux, uy):
    """Copper under the RP2354A, after Raspberry Pi's RP2350A minimal design:
      * a +3V3 bar under the north pin row (as the reference does) joins
        VREG_VIN (pin 49, boxed in by LX/FB and walled off from any via) to
        pins 53/54, whose decoupling cap C8 has the plane via
      * each DVDD pin (6, 23, 39) runs a short stub inward to a via under the
        package, and those vias -- with the regulator's two 1V1 vias by L1 --
        meet on a DVDD island in the In4 (+3V3) plane under the chip
    Everything here is locked copper the routers work around."""
    bar_y = -2.7
    out = []
    for i, (x0, y0, x1, y1) in enumerate(((1.6, -3.45, 1.6, bar_y), (1.6, bar_y, -0.4, bar_y),
                                          (0.0, -3.45, 0.0, bar_y), (-0.4, -3.45, -0.4, bar_y))):
        out.append(['segment', ['start', round(ux + x0, 4), round(uy + y0, 4)], ['end', round(ux + x1, 4), round(uy + y1, 4)],
                    ['width', 0.2], ['layer', Q('F.Cu')], ['locked', 'yes'], ['net', Q(RP_RAIL)], ['uuid', uid('rpbar', i)]])
    island = DVDD_ISLAND
    out.append(['zone', ['net', Q('DVDD')], ['layer', Q(PWR_LAYER)], ['uuid', uid('rpdvdd')],
                ['name', Q('rp_dvdd_island')], ['hatch', 'edge', 0.5], ['priority', 5],
                ['connect_pads', 'yes', ['clearance', 0.2]], ['min_thickness', 0.2],
                ['fill', 'yes', ['thermal_gap', 0.3], ['thermal_bridge_width', 0.3], ['island_removal_mode', 0]],
                ['polygon', ['pts'] + [['xy', round(ux + dx, 4), round(uy + dy, 4)] for dx, dy in island]]])
    u1 = [e for e in board if isinstance(e, list) and e and e[0] == 'footprint'
          and any(p[1] == 'Reference' and p[2] == 'U1' for p in findall(e, 'property'))][0]
    for pd in findall(u1, 'pad'):
        n = find(pd, 'net')
        if not n or str(n[1]) != 'DVDD' or pd[2] != 'smd':
            continue
        a = find(pd, 'at')
        px, py = float(a[1]), float(a[2])
        if py < -3.0:        # VREG_FB (pin 50) is on the regulator's own DVDD pour already
            continue
        if abs(px) > abs(py):
            vx, vy = math.copysign(2.35, px), py
        else:
            vx, vy = px, math.copysign(2.35, py)
        num = str(pd[1])
        out.append(['segment', ['start', round(ux + px, 4), round(uy + py, 4)], ['end', round(ux + vx, 4), round(uy + vy, 4)],
                    ['width', 0.2], ['layer', Q('F.Cu')], ['locked', 'yes'], ['net', Q('DVDD')], ['uuid', uid('rpdv', num)]])
        out.append(['via', ['at', round(ux + vx, 4), round(uy + vy, 4)], ['size', 0.5], ['drill', 0.25],
                    ['layers', Q('F.Cu'), Q('B.Cu')], ['locked', 'yes'], ['net', Q('DVDD')], ['uuid', uid('rpdvv', num)]])
    return out


def usb_c_ties():
    """Locked copper joining the USB-C receptacle's two D+ and two D- pads.  On this
    footprint the pairs interleave (B6 A7 A6 B7, 0.5 mm pitch), which the routers handle
    badly: D+ loops round on F.Cu south of the pads, D- drops through two staggered
    0.45/0.25 mm vias (0.1 mm ring: JLCPCB multilayer minimum is 0.25/0.15) between the loop and the pad ends and is joined on B.Cu."""
    jx, jy, jr = PLACE['J3']
    pos = lambda lx, ly: tuple(round(v, 4) for v in (jx + rot_pt(lx, ly, jr)[0], jy + rot_pt(lx, ly, jr)[1]))
    end = 4.045 + 0.725                      # pad far end (local y, toward the board)
    dp, dm = NET('UBRG_DP'), NET('UBRG_DM')
    a6, b6, a7, b7 = (pos(x, -4.045) for x in (-0.25, 0.75, 0.25, -0.75))
    loop_y, via_y = -(end + 1.75), -(end + 0.85)
    out = []

    def sg(p, q, layer, net, k):
        out.append(['segment', ['start', *p], ['end', *q], ['width', 0.2], ['layer', Q(layer)], ['locked', 'yes'],
                    ['net', Q(net)], ['uuid', uid('usbtie', k)]])
    pts = [a6, pos(-0.25, loop_y), pos(0.75, loop_y), b6]
    for i in range(3):
        sg(pts[i], pts[i + 1], 'F.Cu', dp, ('dp', i))
    for k, (pad, lx) in enumerate(((a7, 0.25), (b7, -0.75))):
        v = pos(lx, via_y)
        sg(pad, v, 'F.Cu', dm, ('dm', k))
        out.append(['via', ['at', *v], ['size', 0.45], ['drill', 0.25], ['layers', Q('F.Cu'), Q('B.Cu')],
                    ['locked', 'yes'], ['net', Q(dm)], ['uuid', uid('usbtiev', k)]])
    sg(pos(0.25, via_y), pos(-0.75, via_y), 'B.Cu', dm, ('dm', 'b'))
    return out


def add_fanout(board, graft):
    import fanout
    pads, crt = board_pads(board)
    # grafted copper: obstacles for the fan-out, and U1/GND pads it already serves
    extra_segs, extra_vias, served = [], [], set()
    for e in graft:
        net = str(find(e, 'net')[1])
        if e[0] == 'segment':
            s_, t_ = find(e, 'start'), find(e, 'end')
            seg = (float(s_[1]), float(s_[2]), float(t_[1]), float(t_[2]), net, float(find(e, 'width')[1]))
            extra_segs.append(seg)
            for p in pads:
                if p.net == net and (p.dist(seg[0], seg[1]) < 1e-6 or p.dist(seg[2], seg[3]) < 1e-6):
                    served.add(id(p))
        elif e[0] == 'via':
            a = find(e, 'at')
            extra_vias.append((float(a[1]), float(a[2]), net))
        elif e[0] == 'zone':
            xy = [(float(q[1]), float(q[2])) for q in find(find(e, 'polygon'), 'pts')[1:]]
            x0_, y0_ = min(q[0] for q in xy), min(q[1] for q in xy)
            x1_, y1_ = max(q[0] for q in xy), max(q[1] for q in xy)
            zp = fanout.Pad('graft', 'zone', net, (x0_ + x1_) / 2, (y0_ + y1_) / 2, (x1_ - x0_) / 2, (y1_ - y0_) / 2,
                            ['F.Cu'], False, ((x0_ + x1_) / 2, (y0_ + y1_) / 2))
            for p in pads:
                if p.net == net and zp.dist(p.cx, p.cy) < 1e-6:
                    served.add(id(p))
            pads.append(zp)
    # GND already has the graft's own vias; U1 pins on graft copper are done
    skip = {id(p) for p in pads if id(p) in served and (p.net == 'GND' or p.ref == 'U1')}

    # a pad only gets a plane via where the power plane carries its net (GND: In1, everywhere),
    # judged where the via will sit: a fine-pitch pin's via goes straight out along its axis
    def via_spot(p):
        if min(p.hw, p.hh) <= 0.15:
            fx, fy = p.fp_xy
            if p.hh > p.hw:
                return p.cx, p.cy + math.copysign(2.0, p.cy - fy)
            return p.cx + math.copysign(2.0, p.cx - fx), p.cy
        return p.cx, p.cy
    for p in pads:
        if p.net in ('+3V3', RP_RAIL, 'DVDD') and plane_net_at(*via_spot(p)) != p.net:
            skip.add(id(p))
    keep = [crt[r] for r in ('U2', 'J2', 'J3', 'SW1', 'SW2', 'SW3', 'SW4') if r in crt]
    ux_, uy_, _ = PLACE['U1']
    keep.append((ux_ - 3.0, uy_ - 3.0, ux_ + 3.0, uy_ + 3.0))   # no fan-out vias under the RP2354A
    holes = [(x, y, d / 2) for x, y, d in HOLES]
    vias, segs, failed = fanout.plan(pads, keep, (X0, Y0, X1, Y1), BLADE_Y, holes, skip_refs=('J1', 'graft'),
                                     extra_segs=extra_segs, extra_vias=extra_vias, skip_pads=skip)
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
    g = []
    lines = [((X0 + r, Y0), (X1 - r, Y0)), ((X1, Y0 + r), (X1, Y1 - r)),
             ((X1 - r, Y1), (X0 + r, Y1)), ((X0, Y1 - r), (X0, Y0 + r))]
    for i, (a, b) in enumerate(lines):
        g.append(['gr_line', ['start', *a], ['end', *b], ['stroke', ['width', 0.1], ['type', 'default']],
                  ['layer', Q('Edge.Cuts')], ['uuid', uid('edge', i)]])
    k = r * (1 - math.sqrt(0.5))
    arcs = [((X0, Y0 + r), (X0 + k, Y0 + k), (X0 + r, Y0)), ((X1 - r, Y0), (X1 - k, Y0 + k), (X1, Y0 + r)),
            ((X1, Y1 - r), (X1 - k, Y1 - k), (X1 - r, Y1)), ((X0 + r, Y1), (X0 + k, Y1 - k), (X0, Y1 - r))]
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


def fiducials():
    """Assembly fiducials (board-only footprints: not in the schematic, BOM or CPL)."""
    out = []
    for ref, x, y in FIDUCIALS:
        fp = load_fp('Fiducial_1mm_Mask2mm')
        inst = ['footprint', Q(D.LIB + ':Fiducial_1mm_Mask2mm'), ['layer', Q('F.Cu')], ['uuid', uid(ref)], ['at', x, y]]
        for e in fp[2:]:
            if not isinstance(e, list) or not e or e[0] in ('version', 'generator', 'generator_version', 'layer',
                                                           'uuid', 'embedded_fonts'):
                continue
            e = copy.deepcopy(e)
            if e[0] == 'property' and e[1] == 'Reference':
                e[2] = Q(ref)
            if e[0] == 'pad':
                e.append(['uuid', uid(ref, 'pad')])
            inst.append(e)
        inst.append(['embedded_fonts', 'no'])
        out.append(inst)
    return out


def setup_stackup(hdr, order):
    """JLCPCB standard stack-ups, 1.6 mm: JLC04161H-7628 / JLC06161H-2116."""
    setup = find(hdr, 'setup')
    st = find(setup, 'stackup') if setup else None
    if st is None:
        return
    keep = [e for e in st[1:] if not (isinstance(e, list) and e and e[0] == 'layer')]
    if STACKUP == 4:
        cu = [0.035, 0.0152, 0.0152, 0.035]
        diel = [('prepreg', 0.2104, 4.4), ('core', 1.065, 4.6), ('prepreg', 0.2104, 4.4)]
    else:
        cu = [0.035, 0.0152, 0.0152, 0.0152, 0.0152, 0.035]
        diel = [('prepreg', 0.0994, 4.05), ('core', 0.55, 4.6), ('prepreg', 0.1088, 4.05), ('core', 0.55, 4.6),
                ('prepreg', 0.0994, 4.05)]
    lay = [['layer', Q('F.SilkS'), ['type', Q('Top Silk Screen')]],
           ['layer', Q('F.Paste'), ['type', Q('Top Solder Paste')]],
           ['layer', Q('F.Mask'), ['type', Q('Top Solder Mask')], ['thickness', 0.01]]]
    for i, n in enumerate(order):
        lay.append(['layer', Q(n), ['type', Q('copper')], ['thickness', cu[i]]])
        if i < len(diel):
            k, t, er = diel[i]
            lay.append(['layer', Q('dielectric %d' % (i + 1)), ['type', Q(k)], ['thickness', t],
                        ['material', Q('FR4')], ['epsilon_r', er], ['loss_tangent', 0.02]])
    lay += [['layer', Q('B.Mask'), ['type', Q('Bottom Solder Mask')], ['thickness', 0.01]],
            ['layer', Q('B.Paste'), ['type', Q('Bottom Solder Paste')]],
            ['layer', Q('B.SilkS'), ['type', Q('Bottom Silk Screen')]]]
    st[1:] = lay + keep


def text(s, x, y, layer, size=1.0, mirror=False, rot=0):
    eff = ['effects', ['font', ['size', size, size], ['thickness', size * 0.15]]]
    if mirror:
        eff.append(['justify', 'mirror'])
    return ['gr_text', Q(s), ['at', x, y, rot], ['layer', Q(layer)], ['uuid', uid('text', s)], eff]


# ---------------------------------------------------------------------------
from placement import do_placement  # noqa: E402  (placement table lives in its own file)


SHORT_CLASSES = [  # name, clearance, track, via dia, via drill, nets (design.py names)
    # +3V3_RP stays in Default: ~60 mA, and a 0.2 mm class clearance on the RP's IOVDD pins
    # walled in their 0.4 mm-pitch signal neighbours (4 bus pins left unroutable)
    ('PWR', 0.2, 0.5, 0.8, 0.4, ['+5V', 'CONS_5V', 'BUCK_SW']),
    # VBUS threads between the USB-C pads; 0.3 mm (~0.9 A outer) covers the board's USB draw
    ('VBUS', 0.15, 0.3, 0.6, 0.3, ['VBUS']),
    ('USB', 0.15, 0.25, 0.6, 0.3, ['USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM']),
]


def netclasses():
    return [(c, cl, tw, vd, vdr, [NET(n) for n in nets]) for c, cl, tw, vd, vdr, nets in SHORT_CLASSES]


def configure_project():
    """Design rules + net classes in the .kicad_pro (JLCPCB 4-layer capable)."""
    import json
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    r = pro['board']['design_settings']['rules']
    r.update({'min_clearance': 0.12, 'min_copper_edge_clearance': 0.25, 'min_track_width': 0.1,
              'min_via_diameter': 0.45, 'min_through_hole_diameter': 0.25, 'min_hole_clearance': 0.25,
              'min_hole_to_hole': 0.25, 'min_via_annular_width': 0.1})
    ns = pro['net_settings']
    base = dict(ns['classes'][0])
    base.update({'name': 'Default', 'clearance': 0.15, 'track_width': 0.2, 'via_diameter': 0.6, 'via_drill': 0.3})
    classes = [base]
    patterns = []
    for i, (name, cl, tw, vd, vdr, nets) in enumerate(netclasses()):
        c = dict(base)
        c.update({'name': name, 'clearance': cl, 'track_width': tw, 'via_diameter': vd, 'via_drill': vdr,
                  'priority': i})
        classes.append(c)
        patterns += [{'netclass': name, 'pattern': n} for n in nets]
    ns['classes'] = classes
    ns['netclass_patterns'] = patterns
    ns['netclass_assignments'] = None
    pro['pcbnew'] = pro.get('pcbnew', {})
    pro['pcbnew'].setdefault('last_paths', {})['specctra_dsn'] = ''
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')
    # The grafted Raspberry Pi regulator corner is drawn at 0.12 mm; allow that
    # there only (everything else keeps the 0.15 mm net-class clearance).
    core = [NET(n) for n in ('DVDD', 'RP_LX', 'VREG_AVDD')]
    anyc = ' || '.join("A.NetName == '%s'" % n for n in core)
    nonec = ' && '.join("%s.NetName != '%s'" % (s_, n) for s_ in 'AB' for n in core)
    open(os.path.join(PRJ, D.PROJECT + '.kicad_dru'), 'w').write(
        '(version 1)\n'
        '(rule "rp2350_core_corner"\n'
        '\t(condition "%s")\n'
        '\t(constraint clearance (min 0.12mm)))\n'
        '(rule "default_clearance"\n'
        '\t(condition "%s")\n'
        '\t(constraint clearance (min 0.15mm)))\n' % (anyc, nonec) +
        # the console blade's B.Cu rule area clips the bottom pour around J1's GND escape holes:
        # one spoke is enough there (the lands are fed on F.Cu / In1 through their plated holes)
        '(rule "j1_gnd_spokes"\n'
        '\t(condition "A.memberOfFootprint(\'J1\')")\n'
        '\t(constraint min_resolved_spokes 1))\n' +
        # The regulator corner's GND (C10/C15/C16 and U1's PGND + EP) joins the
        # top GND pour solidly, as Raspberry Pi's own GND pour there did
        '(rule "rp2350_core_gnd_solid"\n'
        '\t(condition "A.NetName == \'GND\' && (A.memberOfFootprint(\'C10\') || A.memberOfFootprint(\'C15\') || '
        'A.memberOfFootprint(\'C16\') || A.memberOfFootprint(\'U1\'))")\n'
        '\t(constraint zone_connection solid))\n')


def write_case_anchors():
    """case/board-anchors.scad: the shell openings follow the placement."""
    def at(ref):
        return PLACE[ref][0], PLACE[ref][1]
    sw1, sw2, ws, usb, sd, u2 = at('SW4'), at('SW1'), at('D3'), at('J3'), at('J2'), at('U2')   # RESET, BOOTSEL
    lines = ['// GENERATED by tools/gen_pcb.py from tools/placement.py -- do not edit.',
             '// Board (KiCad) coordinates through bx()/byy() defined in the shell file.',
             'sw1   = [bx(%g), byy(%g)];    // RESET  (top-face button hole)' % sw1,
             'sw2   = [bx(%g), byy(%g)];    // BOOTSEL (pinhole)' % sw2,
             'ws    = [bx(%g), byy(%g)];  // WS2812 light pipe' % ws,
             'usb   = [bx(%g), byy(%g)];    // USB-C exits trailing edge' % (usb[0], Y0),
             'sd    = [bx(%g), byy(%g)];    // microSD exits trailing edge' % (sd[0], Y0),
             'holes = [%s];' % ', '.join('[bx(%g), byy(%g)]' % h[:2] for h in HOLES),
             'ant_c = bx(%g);                // ESP32 antenna centre X (overhangs trailing edge)' % u2[0], '']
    open(os.path.join(PRJ, 'case', 'board-anchors.scad'), 'w').write('\n'.join(lines))


def main():
    configure_project()
    do_placement(place)
    ux, uy, _ = PLACE['U1']
    for e in GRAFT[1:]:        # the regulator corner sits where Raspberry Pi put it
        if e[0] == 'part':
            a = find(e, 'at')
            PLACE[str(e[1])] = (round(ux + float(a[1]), 4), round(uy + float(a[2]), 4), float(a[3]) % 360)
    write_case_anchors()
    load_netlist()
    hdr = parse(open(os.path.join(HERE, 'pcb_header.sexpr')).read())
    # 6 layers: F.Cu / In1 GND plane / In2 signal / In3 signal / In4 +3V3 plane (+ DVDD island) / B.Cu
    layers = find(hdr, 'layers')
    cu = [l for l in layers[1:] if str(l[1]).endswith('.Cu')]
    rest = [l for l in layers[1:] if not str(l[1]).endswith('.Cu')]
    order = ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu') if STACKUP == 4 else \
            ('F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu')
    kinds = {n: ('power' if n in ('In1.Cu', PWR_LAYER) else 'signal') for n in order}
    ids = {'F.Cu': '0', 'B.Cu': '2', 'In1.Cu': '4', 'In2.Cu': '6', 'In3.Cu': '8', 'In4.Cu': '10'}
    layers[1:] = [[ids[n], Q(n), kinds[n]] for n in order] + rest
    setup_stackup(hdr, order)
    root = str(gen_sch.uid('root'))
    board = hdr
    missing = [p.ref for p in D.PARTS if p.ref not in PLACE]
    if missing:
        raise SystemExit('unplaced: ' + ' '.join(missing))
    syms = gen_sch.load_symbols()
    for p in D.PARTS:
        x, y, r = PLACE[p.ref]
        stem, u = fp_sheet_unit(p, syms)
        path = '/%s/%s' % (gen_sch.uid('sheet', stem), gen_sch.uid(stem, p.ref, u))
        ds = ''
        for pr in findall(syms[p.lib_id], 'property'):
            if pr[1] == 'Datasheet':
                ds = str(pr[2])
        board.append(instance(p, x, y, r, path, '/%s/' % stem, stem + '.kicad_sch', ds))
    for i, (x, y, _d) in enumerate(HOLES, 1):
        h = D.Part('H', D.LIB + ':MountingHole_3.2mm_NPTH', 'M3', D.FP('MountingHole_3.2mm_NPTH'), {},
                   None, desc='M3 shell screw', bom=False)
        h.ref = 'H%d' % i
        fp = instance(h, x, y, 0, '', '', '')
        fp = [e for e in fp if not (isinstance(e, list) and e and e[0] in ('path', 'sheetname', 'sheetfile'))]
        board.append(fp)
    ux, uy, _ = PLACE['U1']
    graft = graft_copper(ux, uy)
    board += graft
    ring = rp_ring(board, ux, uy)
    board += ring
    ties = usb_c_ties()
    board += ties
    graft = graft + ring + ties
    add_fanout(board, graft)
    board += outline()
    box = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
    board.append(zone('blade_strip_no_copper_B', None, 'B.Cu',
                      [(X0, BLADE_Y), (X1, BLADE_Y), (X1, Y1), (X0, Y1)], keepout=True))
    board.append(zone('GND_plane', 'GND', 'In1.Cu', box))
    board.append(zone('3V3_plane', '+3V3', PWR_LAYER, box))
    board.append(zone('rp_io_island', RP_RAIL, PWR_LAYER, RP_ISLAND, priority=3))
    board += fiducials()
    for ref, x, y in FIDUCIALS:   # bare copper + 2 mm mask opening: keep pours and tracks 1.6 mm away
        ring = [(round(x + 1.6 * math.cos(a * math.pi / 8), 3), round(y + 1.6 * math.sin(a * math.pi / 8), 3)) for a in range(16)]
        for L in ('F.Cu', 'B.Cu'):
            board.append(zone('fid_keepout_%s_%s' % (ref, L[0]), None, L, ring, keepout=True))
    board.append(text('FujiNet Astrocade Rev0', 100, 84.0, 'F.SilkS', 1.5))
    board.append(text('RP2354A + ESP32-S3', 100, 86.2, 'F.SilkS', 1.0))
    board.append(text('insert this edge into console', 100, 81.8, 'F.SilkS', 1.0))
    board.append(['embedded_fonts', 'no'])
    open(PCB, 'w').write(dump(board) + '\n')
    print('placed %d parts -> %s' % (len(D.PARTS), os.path.basename(PCB)))


if __name__ == '__main__':
    main()
