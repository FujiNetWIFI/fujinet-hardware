#!/usr/bin/env python3
"""Gate on the fab outputs themselves (not the .kicad_pcb): the gerbers and drills that
tools/export.py zipped for JLCPCB, checked against tools/edge_geom.py.

  1. the zip holds the 4 copper layers (F, In1, In2, B), both masks, pastes and silkscreens, the
     outline, plated and unplated Excellon -- and nothing for a 6-layer stack
  2. Edge.Cuts: the board's width and height, both sides' straight runs and the two side notches
     (edge_geom.NOTCH_L / NOTCH_R, NOTCH_D deep), the two 5 mm shell-post holes in the NPTH drill
  3. F.Cu: exactly 15 fingers (pins 1-15) at their pins' x; B.Cu: exactly 15 (pins A-R) behind
     them; each edge_geom.LAND_W wide, LAND_Y0..LAND_Y1 in from the edge
  4. F.Cu and B.Cu: no other copper between the fingers in the finger field (each finger's neck
     stays within its own width)
  5. F.Mask / B.Mask: every finger inside a mask opening
  6. In1 / In2: no copper in the finger field (the planes stop above it)
  7. no paste closer to the edge than edge_geom.PARTS_Y (no parts there); no silkscreen in the
     fingers' mask openings; no drill hit in the finger field
  8. no plated hole inside an inner-layer pour of another net: each PTH hit takes its net from the
     copper flashed at it (KiCad's X2 %TO.N attributes), and every In1 / In2 region (zone fill) that
     contains it must carry that net (the plot is of the SAVED fills: vias added after the last fill
     sat inside the inner power pours of five boards' zips in 2026-10)
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

    xc, y1, field_y = G.XC, G.Y1, G.FINGER_Y
    # 2. outline: the profile is drawn segment by segment; collect vertical runs
    edges = [o for o in layer('Edge_Cuts.gbr') if o[4] == 'draw']
    w = 0.1
    vert = [(round((o[0] + o[2]) / 2, 3), round(o[1] + w / 2, 3), round(o[3] - w / 2, 3)) for o in edges
            if abs((o[2] - o[0]) - w) < 1e-3]
    has_run = lambda xx, ya, yb: any(abs(v[0] - xx) < EPS and abs(v[1] - ya) < EPS and abs(v[2] - yb) < EPS
                                     for v in vert)
    for side, xx, inner, (lo, hi) in (('west', G.X0, G.X0 + EG.NOTCH_D, EG.NOTCH_L),
                                      ('east', G.X1, G.X1 - EG.NOTCH_D, EG.NOTCH_R)):
        check(has_run(xx, G.Y0 + EG.TOP_R, y1 - hi) and has_run(xx, y1 - lo, y1 - EG.CHAMF_Y),
              '2. %s side at x %.3f: y %.2f..%.2f and %.2f..%.2f' % (side, xx, G.Y0 + EG.TOP_R, y1 - hi, y1 - lo,
                                                                    y1 - EG.CHAMF_Y))
        check(has_run(inner, y1 - hi, y1 - lo), '2. %s notch at x %.3f: y %.2f..%.2f (%.1f-%.1f mm up)'
              % (side, inner, y1 - hi, y1 - lo, lo, hi))
    npth = drills(next(t for n, t in files.items() if n.endswith('-NPTH.drl')))
    posts = [(hx, hy) for hx, hy, d in npth if abs(d - EG.HOLE_D) < EPS]
    want = sorted((round(x, 2), round(y, 2)) for x, y, d in G.HOLES)
    check(sorted((round(x, 2), round(y, 2)) for x, y in posts) == want,
          '2. NPTH: the shell posts, %.1f mm, at %s' % (EG.HOLE_D, want))
    x0, x1 = min(o[0] for o in edges) + w / 2, max(o[2] for o in edges) - w / 2
    check(abs((x1 - x0) - EG.BOARD_W) < EPS, '2. board width %.3f mm (want %.3f)' % (x1 - x0, EG.BOARD_W))
    ytop = min(o[1] for o in edges) + w / 2
    check(abs((y1 - ytop) - EG.CART_H) < EPS, '2. board height %.2f mm (want %.2f)' % (y1 - ytop, EG.CART_H))

    # 3-5. fingers: pins 1-15 on F.Cu, A-R on B.Cu
    size = (EG.LAND_W, round(EG.LAND_Y1 - EG.LAND_Y0, 3))
    for side, cu_n, mask_n, pins in (('F', 'F_Cu.gbr', 'F_Mask.gbr', EG.ROW_F),
                                     ('B', 'B_Cu.gbr', 'B_Mask.gbr', EG.ROW_B)):
        cu = layer(cu_n)
        fing = [o for o in cu if o[4] == 'flash' and o[5] == size and o[3] > y1 - EG.LAND_Y0 - 1
                and o[1] > y1 - EG.LAND_Y1 - EPS]
        got = {round((o[0] + o[2]) / 2, 3): o for o in fing}
        bad = []
        for p in pins:
            xx = round(xc + EG.finger_x(p), 3)
            o = next((v for k, v in got.items() if abs(k - xx) < EPS), None)
            if o is None or abs(o[1] - (y1 - EG.LAND_Y1)) > EPS or abs(o[3] - (y1 - EG.LAND_Y0)) > EPS:
                bad.append(p)
        check(len(fing) == EG.N_PER_FACE and not bad,
              '3. %s.Cu: %d fingers at their pins\' x (pin %s at %.2f, pin %s at %.2f), %.2f wide, %.2f..%.2f mm in%s'
              % (side, len(fing), pins[0], xc + EG.finger_x(pins[0]), pins[-1], xc + EG.finger_x(pins[-1]),
                 EG.LAND_W, EG.LAND_Y0, EG.LAND_Y1, ' -- bad pins %s' % bad if bad else ''))
        stray = [o for o in cu if o not in fing and o[3] > field_y + EPS
                 and not any(f[0] - EPS <= o[0] and o[2] <= f[2] + EPS for f in fing)]
        check(not stray, '4. %s.Cu: no copper between the fingers in the finger field (%d stray)' % (side, len(stray)))
        mask = layer(mask_n)
        cov = [f for f in fing if any(m[0] <= f[0] + EPS and m[1] <= f[1] + EPS and m[2] >= f[2] - EPS
                                      and m[3] >= f[3] - EPS for m in mask)]
        check(len(cov) == len(fing), '5. %s.Mask: %d / %d fingers inside their own mask openings'
              % (side, len(cov), len(fing)))

    # 6-7. the finger field and the tab
    for n in ('In1_Cu', 'In2_Cu'):
        low = max(o[3] for o in layer(n + '.gbr'))
        check(low <= field_y + EPS, '6. %s: lowest copper at y %.2f, finger field from %.2f' % (n, low, field_y))
    for n in ('F_Paste', 'B_Paste'):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= G.PARTS_MAX_Y + EPS, '7. %s: lowest object at y %.2f (no parts south of %.2f)'
              % (n, low, G.PARTS_MAX_Y))
    win = y1 - EG.LAND_Y1 - 0.05
    for n in ('F_Silkscreen', 'B_Silkscreen'):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= win - 0.1, '7. %s: lowest ink at y %.2f, finger mask window from %.2f' % (n, low, win))
    for n, t in files.items():
        if n.endswith('.drl'):
            h = drills(t)
            low = max((p[1] for p in h), default=0)
            check(low <= field_y + EPS, '7. %s: %d hits, lowest at y %.2f (finger field from %.2f)'
                  % (n, len(h), low, field_y))

    # 8. plated holes against the inner pours of other nets
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
          '8. %d plated holes: none inside an In1 / In2 pour of another net%s%s'
          % (len(pth), ' -- %d shorts, e.g. %s' % (len(shorts), shorts[:3]) if shorts else '',
             ' -- %d holes without a net-tagged flash' % unknown if unknown else ''))
    print('%d failures' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
