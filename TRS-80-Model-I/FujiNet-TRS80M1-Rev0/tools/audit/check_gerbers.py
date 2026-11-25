#!/usr/bin/env python3
"""Gate on the fab outputs themselves (not the .kicad_pcb): the gerbers and drills that
tools/export.py zipped for JLCPCB, checked against tools/header_geom.py and tools/placement.py.

  1. the zip holds the 4 copper layers (F, In1, In2, B), both masks, pastes and silkscreens, the
     outline, plated and unplated Excellon -- and nothing for a 6-layer stack
  2. Edge.Cuts: the board's width and height (header_geom.BOARD_W x BOARD_H)
  3. the NPTH drill: exactly the four M3 corner holes (header_geom.HOLE_D) where placement.HOLES has them
  4. the PTH drill: the box header's 40 holes, each at its pin's position (placement.hdr_pin), 1.1 mm,
     with a pad flashed on F.Cu and B.Cu and a mask opening on both sides
  5. the antenna band (gen_pcb.ANT_KEEP): no copper on any layer, no drill hit
  6. no paste and no copper (but the header's shroud has none: it is plastic) past the outline
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
import header_geom as EG
import placement as PL
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

    # 2. outline
    edges = [o for o in layer('Edge_Cuts.gbr') if o[4] == 'draw']
    x0, y0 = min(o[0] for o in edges) + 0.05, min(o[1] for o in edges) + 0.05
    x1, y1 = max(o[2] for o in edges) - 0.05, max(o[3] for o in edges) - 0.05
    check(abs((x1 - x0) - EG.BOARD_W) < EPS and abs((y1 - y0) - EG.BOARD_H) < EPS,
          '2. board %.3f x %.3f mm (want %g x %g)' % (x1 - x0, y1 - y0, EG.BOARD_W, EG.BOARD_H))
    check(abs(x0 - PL.X0) < EPS and abs(y0 - PL.Y0) < EPS, '2. the outline where placement.py puts it (%.2f, %.2f)' % (x0, y0))
    # 3. NPTH: the corner holes
    npth = drills(next(t for n, t in files.items() if n.endswith('-NPTH.drl')))
    want_h = sorted((round(x, 2), round(y, 2), d) for x, y, d in PL.HOLES)
    got_h = sorted((round(x, 2), round(y, 2), d) for x, y, d in npth if d >= 3.0)   # (the connectors' pegs are NPTH too)
    check(len(got_h) == 4 and all(abs(a[0] - b[0]) < EPS and abs(a[1] - b[1]) < EPS and abs(a[2] - b[2]) < 0.01
                                  for a, b in zip(want_h, got_h)),
          '3. NPTH: the four %.1f mm corner holes %s' % (EG.HOLE_D, got_h if len(got_h) != 4 else ''))
    # 4. the header's holes, pads and mask openings
    pth = drills(next(t for n, t in files.items() if n.endswith('-PTH.drl')))
    fcu, bcu = layer('F_Cu.gbr'), layer('B_Cu.gbr')
    fm, bm = layer('F_Mask.gbr'), layer('B_Mask.gbr')
    covers = lambda objs, x, y, r: any(o[4] == 'flash' and o[0] <= x - r + EPS and o[2] >= x + r - EPS and
                                       o[1] <= y - r + EPS and o[3] >= y + r - EPS for o in objs)
    bad = []
    for n in range(1, 41):
        hx, hy = PL.hdr_pin(n)
        hit = [h for h in pth if abs(h[0] - hx) < EPS and abs(h[1] - hy) < EPS]
        if len(hit) != 1 or abs(hit[0][2] - 1.1) > 0.01:
            bad.append('%d: hole %s' % (n, hit))
            continue
        for nm, objs in (('F.Cu', fcu), ('B.Cu', bcu), ('F.Mask', fm), ('B.Mask', bm)):
            if not covers(objs, hx, hy, 0.8):
                bad.append('%d: no %s pad' % (n, nm))
    check(not bad, '4. the box header: 40 x 1.1 mm plated holes at their pins, pads and mask openings both sides%s'
          % (' -- %s' % bad[:6] if bad else ''))
    # 5. the antenna band
    ax0, ay0, ax1, ay1 = G.ANT_KEEP
    inband = lambda o: o[2] > ax0 + EPS and o[0] < ax1 - EPS and o[3] > ay0 + EPS and o[1] < ay1 - EPS
    grid = [(ax0 + 0.05 + 0.25 * i, ay0 + 0.05 + 0.25 * j) for i in range(int((ax1 - ax0) / 0.25)) for j in range(int((ay1 - ay0) / 0.25))]
    for n in ('F_Cu.gbr', 'In1_Cu.gbr', 'In2_Cu.gbr', 'B_Cu.gbr'):
        text = next(t for k, t in files.items() if k.endswith(n))
        objs = [o for o in parse(text) if o[4] != 'region' and inband(o)]          # pads, tracks
        regs = [r for _net, r in net_objects(text)[0]]                              # pours: point in polygon
        filled = [(x, y) for x, y in grid if any(inside(x, y, r) for r in regs)]
        check(not objs and not filled, '5. %s: no copper in the antenna band x %.1f..%.1f, y %.1f..%.1f%s'
              % (n[:-4], ax0, ax1, ay0, ay1, ' -- %d objects, %d filled points, e.g. %s' % (len(objs), len(filled), (objs[:1] or filled[:1])) if objs or filled else ''))
    hits = [h for h in pth + npth if ax0 < h[0] < ax1 and ay0 < h[1] < ay1]
    check(not hits, '5. no drill hit in the antenna band%s' % (' -- %s' % hits[:3] if hits else ''))
    # 6. nothing past the outline
    for n in ('F_Paste.gbr', 'F_Cu.gbr', 'B_Cu.gbr'):
        out = [o for o in layer(n) if o[0] < x0 - EPS or o[2] > x1 + EPS or o[1] < y0 - EPS or o[3] > y1 + EPS]
        check(not out, '6. %s: nothing past the outline%s' % (n[:-4], ' -- %s' % [o[:4] for o in out[:3]] if out else ''))
    # 8. plated holes against the inner pours of other nets
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
