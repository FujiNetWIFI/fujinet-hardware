#!/usr/bin/env python3
"""Gate on the fab outputs themselves (not the .kicad_pcb): the gerbers and drills that
tools/export.py zipped for JLCPCB, checked against tools/edge_geom.py.

  1. the zip holds the 4 copper layers (F, In1, In2, B), both masks, pastes and silkscreens, the
     outline, plated and unplated Excellon -- and nothing for a 6-layer stack
  2. Edge.Cuts: FliP's 90.912 mm width, both sides straight from the insertion edge's chamfers to the
     notch and from the notch to the rounded top corners, the two notches and the two corners as
     arcs, the board's height (FliP's 83.49 + edge_geom.EXT_H)
  3. B.Cu: exactly 22 fingers, each at its pin's x (0.156", pin 1 east seen from F.Cu), 1.905 mm
     wide, 0.70-8.95 mm in from the edge
  4. B.Cu: no other copper between the fingers in the finger field (stubs leave each finger within
     its own width)
  5. F.Cu: nothing in the finger field (the contacts are on B.Cu only)
  6. B.Mask: every finger inside a mask opening; F.Mask: no opening in the finger field
  7. In1 / In2: no copper in the finger field (the planes stop 9.55 mm in)
  8. no paste closer to the edge than edge_geom.PARTS_Y (no parts there); no silkscreen in the
     fingers' mask openings; no drill hit in the finger field; the two 8.128 mm post holes in the
     NPTH file at their places
  9. no plated hole inside an inner-layer pour of another net: each PTH hit takes its net from the
     copper flashed at it (KiCad's X2 %TO.N attributes), and every In1 / In2 region (zone fill) that
     contains it must carry that net.  The plot is of the SAVED fills: vias added after the last fill
     sat inside the In2 power pours (427 GND vias in the first 2026-10-11 zip) while DRC with
     --refill-zones passed.
Gerber y is KiCad's y negated (KiCad 10 exports with y up); coordinates are mm, format 4.6.

Usage: python3 tools/audit/check_gerbers.py          exit 1 on any failure
"""
import io, os, re, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import edge_geom as EG
import gen_pcb as G
import design as D

PRJ = os.path.dirname(os.path.dirname(HERE))
ZIP = os.path.join(PRJ, 'exports', 'jlcpcb', D.PROJECT + '-gerbers.zip')
EPS = 0.02
fails = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        fails.append(msg)


def aperture_half(defn):
    """(half-width, half-height) of a standard or RoundRect aperture definition."""
    m = re.match(r'([A-Za-z]+),(.*)', defn)
    kind, args = m.group(1), [float(a) for a in m.group(2).split('X') if a]
    if kind == 'C':
        return args[0] / 2, args[0] / 2
    if kind in ('R', 'O'):
        return args[0] / 2, args[1] / 2
    if kind == 'RoundRect':
        r, xs, ys = args[0], args[1:9:2], args[2:9:2]
        return max(abs(v) for v in xs) + r, max(abs(v) for v in ys) + r
    if kind == 'P':          # polygon: outer diameter
        return args[0] / 2, args[0] / 2
    return 0.5, 0.5           # unknown macro: a conservative 1 mm


def parse(text):
    """Every dark object as a KiCad-frame box (x0, y0, x1, y1, kind, size) with kind flash/draw/
    region.  Clear-polarity objects (%LPC%: KiCad's --subtract-soldermask cut-outs in the
    silkscreen) remove ink, so they are skipped."""
    aps, cur, x, y, out, region, dark = {}, None, 0.0, 0.0, [], None, True
    for m in re.finditer(r'%ADD(\d+)([^*]*)\*%', text):
        aps[int(m.group(1))] = aperture_half(m.group(2))
    body = re.sub(r'%LP([DC])\*%', lambda m: 'LP' + m.group(1) + '*', text)
    body = re.sub(r'%[^%]*%', '', body)
    for cmd in body.replace('\n', '').split('*'):
        if not cmd:
            continue
        if cmd in ('LPD', 'LPC'):
            dark = cmd == 'LPD'
            continue
        if not dark:
            if cmd == 'G37':
                region = None
            elif cmd == 'G36':
                region = []
            m = re.fullmatch(r'(?:G0?1)?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0?([123])', cmd)
            if m:
                x = int(m.group(1)) / 1e6 if m.group(1) else x
                y = -int(m.group(2)) / 1e6 if m.group(2) else y
            continue
        if cmd == 'G36':
            region = []
            continue
        if cmd == 'G37':
            if region:
                xs, ys = [p[0] for p in region], [p[1] for p in region]
                out.append((min(xs), min(ys), max(xs), max(ys), 'region', tuple(region)))
            region = None
            continue
        m = re.fullmatch(r'D(\d+)', cmd)
        if m and int(m.group(1)) >= 10:
            cur = int(m.group(1))
            continue
        m = re.fullmatch(r'(?:G0?1)?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0?([123])', cmd)
        if not m:
            continue
        nx = int(m.group(1)) / 1e6 if m.group(1) else x
        ny = -int(m.group(2)) / 1e6 if m.group(2) else y
        op = m.group(3)
        if region is not None:
            if op == '2':
                region.append((nx, ny))
            elif op == '1':
                if not region:
                    region.append((x, y))
                region.append((nx, ny))
        elif op == '3':
            hw, hh = aps.get(cur, (0, 0))
            out.append((nx - hw, ny - hh, nx + hw, ny + hh, 'flash', (round(2 * hw, 3), round(2 * hh, 3))))
        elif op == '1':
            hw, hh = aps.get(cur, (0, 0))
            out.append((min(x, nx) - hw, min(y, ny) - hh, max(x, nx) + hw, max(y, ny) + hh, 'draw', None))
        x, y = nx, ny
    return out


def net_objects(text):
    """(regions, flashes) of a copper layer with their X2 nets: regions [(net, [contour...])] (a G36 /
    G37 block, a contour per D02), flashes [(x, y, net)] (KiCad frame)."""
    regions, flashes, net, x, y, reg, contour = [], [], None, 0.0, 0.0, None, None
    for cmd in text.replace('\n', '').split('*'):
        cmd = cmd.strip('%')
        if cmd.startswith('TO.N,'):
            net = cmd[5:]
            continue
        if cmd == 'TD':
            net = None
            continue
        if cmd == 'G36':
            reg, contour = [], None
            continue
        if cmd == 'G37':
            if contour:
                reg.append(contour)
            regions.append((net, reg))
            reg = contour = None
            continue
        m = re.fullmatch(r'(?:G0?1)?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0?([123])', cmd)
        if not m:
            continue
        x = int(m.group(1)) / 1e6 if m.group(1) else x
        y = -int(m.group(2)) / 1e6 if m.group(2) else y
        if reg is not None:
            if m.group(3) == '2':
                if contour:
                    reg.append(contour)
                contour = [(x, y)]
            elif m.group(3) == '1':
                contour = (contour or []) + [(x, y)]
        elif m.group(3) == '3':
            flashes.append((x, y, net))
    return regions, flashes


def inside(px, py, contours):
    """Even-odd over all contours of one region (KiCad fractures a fill's holes into its outline)."""
    c = False
    for poly in contours:
        for i in range(len(poly)):
            (x0, y0), (x1, y1) = poly[i - 1], poly[i]
            if (y0 > py) != (y1 > py) and px < x0 + (py - y0) * (x1 - x0) / (y1 - y0):
                c = not c
    return c


def drills(text):
    """[(x, y, diameter)] hits of an Excellon file (tool table T<n>C<dia>)."""
    hits, tools, cur = [], {}, None
    for line in text.splitlines():
        line = line.strip()
        m = re.fullmatch(r'T(\d+)C([\d.]+)', line)
        if m:
            tools[int(m.group(1))] = float(m.group(2))
            continue
        m = re.fullmatch(r'T(\d+)', line)
        if m:
            cur = tools.get(int(m.group(1)))
            continue
        m = re.match(r'X(-?[\d.]+)Y(-?[\d.]+)(?:G85X(-?[\d.]+)Y(-?[\d.]+))?', line)
        if m and m.group(3):            # a slot (G85): its centre
            hits.append(((float(m.group(1)) + float(m.group(3))) / 2, -(float(m.group(2)) + float(m.group(4))) / 2, cur))
        elif m:
            hits.append((float(m.group(1)), -float(m.group(2)), cur))
    return hits


def main():
    if not os.path.exists(ZIP):
        raise SystemExit('missing %s: run tools/export.py' % os.path.relpath(ZIP, PRJ))
    with zipfile.ZipFile(ZIP) as f:
        files = {n: f.read(n).decode() for n in f.namelist()}
    has = lambda suffix: any(n.endswith(suffix) for n in files)
    want = ['F_Cu.gbr', 'In1_Cu.gbr', 'In2_Cu.gbr', 'B_Cu.gbr', 'F_Mask.gbr', 'B_Mask.gbr', 'F_Paste.gbr',
            'B_Paste.gbr', 'F_Silkscreen.gbr', 'B_Silkscreen.gbr', 'Edge_Cuts.gbr', '-PTH.drl', '-NPTH.drl']
    check(all(has(s) for s in want) and not has('In3_Cu.gbr') and not has('In4_Cu.gbr'),
          '1. the zip holds the 4-layer set (%d files)%s' % (len(files), '' if all(has(s) for s in want) else
                                                             ' -- missing %s' % [s for s in want if not has(s)]))
    layer = lambda suffix: parse(next(t for n, t in files.items() if n.endswith(suffix)))

    xc, y1, field_y = G.XC, G.Y1, G.FIELD_Y
    # 2. outline: the profile is drawn segment by segment; collect vertical runs
    edges = [o for o in layer('Edge_Cuts.gbr') if o[4] == 'draw']
    w = 0.1
    vert = [(round((o[0] + o[2]) / 2, 3), round(o[1] + w / 2, 3), round(o[3] - w / 2, 3)) for o in edges
            if abs((o[2] - o[0]) - w) < 1e-3]
    lo_run = (G.NOTCH_Y + G.NOTCH_DY, y1 - EG.CH_EDGE)          # insertion-edge chamfer .. the notch
    hi_run = (G.SIDE_Y, G.NOTCH_Y - G.NOTCH_DY)                 # the notch .. the rounded top corner
    for xx, what in ((G.X0, 'west'), (G.X1, 'east')):
        for (ya, yb), part in ((lo_run, 'below'), (hi_run, 'above')):
            check(any(abs(v[0] - xx) < EPS and abs(v[1] - ya) < EPS and abs(v[2] - yb) < EPS for v in vert),
                  '2. %s side at x %.3f, %s the notch: y %.2f..%.2f' % (what, xx, part, ya, yb))
    et = next(t for n, t in files.items() if n.endswith('Edge_Cuts.gbr'))
    check('G75' in et and len(re.findall(r'G0[23]', et)) >= 4, '2. the two side notches and the two top corners are arcs')
    x0, x1 = min(o[0] for o in edges) + w / 2, max(o[2] for o in edges) - w / 2
    check(abs((x1 - x0) - EG.BOARD_W) < EPS, '2. board width %.3f mm (want %.3f, FliP)' % (x1 - x0, EG.BOARD_W))
    ytop = min(o[1] for o in edges) + w / 2
    check(abs((y1 - ytop) - EG.CART_H) < EPS, '2. board height %.2f mm (want %.2f: FliP\'s %.2f + %.1f)'
          % (y1 - ytop, EG.CART_H, EG.BOARD_H, EG.EXT_H))

    # 3-6. fingers (B.Cu only)
    cu = layer('B_Cu.gbr')
    size = (EG.FINGER_W, round(EG.LAND_Y1 - EG.LAND_Y0, 3))
    fing = [o for o in cu if o[4] == 'flash' and o[5] == size and o[3] > y1 - EG.LAND_Y0 - 1 and o[1] > y1 - EG.LAND_Y1 - EPS]
    got = {round((o[0] + o[2]) / 2, 3): o for o in fing}
    bad = []
    for p in range(1, EG.N_PINS + 1):
        xx = round(xc + EG.pin_x(p), 3)
        o = next((v for k, v in got.items() if abs(k - xx) < EPS), None)
        if o is None or abs(o[1] - (y1 - EG.LAND_Y1)) > EPS or abs(o[3] - (y1 - EG.LAND_Y0)) > EPS:
            bad.append(p)
    check(len(fing) == EG.N_PINS and not bad,
          '3. B.Cu: %d fingers at their pins\' x (pin 1 at %.2f, pin 22 at %.2f), %.3f wide, %.2f..%.2f mm in%s'
          % (len(fing), xc + EG.pin_x(1), xc + EG.pin_x(22), EG.FINGER_W, EG.LAND_Y0, EG.LAND_Y1,
             ' -- bad pins %s' % bad if bad else ''))
    stray = [o for o in cu if o not in fing and o[3] > field_y + EPS
             and not any(f[0] - EPS <= o[0] and o[2] <= f[2] + EPS for f in fing)]
    check(not stray, '4. B.Cu: no copper between the fingers in the finger field (%d stray)' % len(stray))
    fcu = [o for o in layer('F_Cu.gbr') if o[3] > field_y + EPS]
    check(not fcu, '5. F.Cu: nothing in the finger field (%d objects)' % len(fcu))
    mask = layer('B_Mask.gbr')
    cov = [f for f in fing if any(m[0] <= f[0] + EPS and m[1] <= f[1] + EPS and m[2] >= f[2] - EPS
                                  and m[3] >= f[3] - EPS for m in mask)]
    check(len(cov) == len(fing), '6. B.Mask: %d / %d fingers inside their own mask openings' % (len(cov), len(fing)))
    fm = [o for o in layer('F_Mask.gbr') if o[3] > field_y + EPS]
    check(not fm, '6. F.Mask: no opening in the finger field (%d)' % len(fm))

    # 7-8. the finger field and the tab
    for n in ('In1_Cu', 'In2_Cu'):
        low = max(o[3] for o in layer(n + '.gbr'))
        check(low <= field_y + EPS, '7. %s: lowest copper at y %.2f, finger field from %.2f' % (n, low, field_y))
    for n in ('F_Paste', 'B_Paste'):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= G.KEEP_Y + EPS, '8. %s: lowest object at y %.2f (no parts south of %.2f)' % (n, low, G.KEEP_Y))
    win = y1 - EG.MASK_Y1
    for n in ('F_Silkscreen', 'B_Silkscreen'):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= win - 0.1, '8. %s: lowest ink at y %.2f, finger mask window from %.2f' % (n, low, win))
    for n, t in files.items():
        if n.endswith('.drl'):
            h = drills(t)
            low = max((p[1] for p in h), default=0)
            check(low <= field_y + EPS, '8. %s: %d hits, lowest at y %.2f (finger field from %.2f)' % (n, len(h), low, field_y))
            if n.endswith('-NPTH.drl'):
                boss = [p for p in h if p[2] and abs(p[2] - EG.HOLE_D) < 0.01]
                ok = len(boss) == len(G.HOLES) and all(any(abs(p[0] - hx) < EPS and abs(p[1] - hy) < EPS for p in boss)
                                                       for hx, hy, _ in G.HOLES)
                check(ok, '8. NPTH: the %d %.3f mm shell-post holes at their places (%d found)' % (len(G.HOLES), EG.HOLE_D, len(boss)))

    # 9. plated holes against the inner pours of other nets
    pth = drills(next(t for n, t in files.items() if n.endswith('-PTH.drl')))
    flash = {}                      # 0.1 mm buckets of net-tagged flashes; a hit takes the one within 0.01 mm
    for n in ('F_Cu.gbr', 'B_Cu.gbr', 'In1_Cu.gbr', 'In2_Cu.gbr'):
        for fx, fy, fnet in net_objects(next(t for k, t in files.items() if k.endswith(n)))[1]:
            if fnet:
                flash.setdefault((round(fx, 1), round(fy, 1)), []).append((fx, fy, fnet))

    def net_at(x, y):
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for fx, fy, fnet in flash.get((round(round(x, 1) + i / 10, 1), round(round(y, 1) + j / 10, 1)), []):
                    if abs(fx - x) < 0.01 and abs(fy - y) < 0.01:
                        return fnet
        return None
    unknown, shorts = 0, []
    for n in ('In1_Cu.gbr', 'In2_Cu.gbr'):
        regions = net_objects(next(t for k, t in files.items() if k.endswith(n)))[0]
        boxes = [(min(p[0] for c in r for p in c), min(p[1] for c in r for p in c),
                  max(p[0] for c in r for p in c), max(p[1] for c in r for p in c)) for _, r in regions]
        for hx, hy, _d in pth:
            hnet = net_at(hx, hy)
            unknown += hnet is None and n == 'In1_Cu.gbr'
            for (rnet, r), (bx0, by0, bx1, by1) in zip(regions, boxes):
                if bx0 <= hx <= bx1 and by0 <= hy <= by1 and rnet != hnet and inside(hx, hy, r):
                    shorts.append((n[:3], hnet, rnet, round(hx, 2), round(hy, 2)))
    check(not shorts and not unknown,
          '9. %d plated holes: none inside an In1 / In2 pour of another net%s%s'
          % (len(pth), ' -- %d shorts, e.g. %s' % (len(shorts), shorts[:3]) if shorts else '',
             ' -- %d holes without a net-tagged flash' % unknown if unknown else ''))
    print('%d failures' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
