#!/usr/bin/env python3
"""Gate on the fab outputs themselves (not the .kicad_pcb): the gerbers and drills that
tools/export.py zipped for JLCPCB and PCBWay, checked against tools/edge_geom.py.

  1. both zips hold the same files, byte for byte
  2. Edge.Cuts: the 47.0 mm tab, the two key slots (x, width, depth), the 72.4 mm body
  3. F.Cu / B.Cu: exactly 16 fingers per face, each at its pin's x (pins 1-16 on F.Cu, 32-17
     behind them on B.Cu), 1.5 mm wide, 0.5-7.5 mm in from the edge
  4. no other outer copper between the fingers in the finger field (stubs leave each finger
     within its own width)
  5. F.Mask / B.Mask: every finger inside a mask opening
  6. In1-In4: no copper in the tab (below the body's lower edge)
  7. no drill hit and no paste in the tab; no silkscreen in the fingers' mask window (the pin
     numbers 1 / 16 / 17 / 32 and J1 sit on mask above it, where they help probing)
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
ZIPS = [os.path.join(PRJ, 'exports', f, D.PROJECT + '-gerbers.zip') for f in ('jlcpcb', 'pcbway')]
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
                out.append((min(xs), min(ys), max(xs), max(ys), 'region', None))
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


def drills(text):
    hits, unit = [], 1.0
    for line in text.splitlines():
        m = re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)', line.strip())
        if m:
            hits.append((float(m.group(1)), -float(m.group(2))))
    return hits


def main():
    blobs = []
    for z in ZIPS:
        if not os.path.exists(z):
            raise SystemExit('missing %s: run tools/export.py' % os.path.relpath(z, PRJ))
        with zipfile.ZipFile(z) as f:
            blobs.append({n: f.read(n) for n in f.namelist()})
    check(blobs[0] == blobs[1], '1. JLCPCB and PCBWay zips identical (%d files)' % len(blobs[0]))
    files = {n: b.decode() for n, b in blobs[0].items()}
    layer = lambda suffix: parse(next(t for n, t in files.items() if n.endswith(suffix)))

    xc, y1, tab_y = G.XC, G.Y1, G.TAB_Y
    # 2. outline: the profile is drawn segment by segment; collect vertical runs
    edges = [o for o in layer('Edge_Cuts.gbr') if o[4] == 'draw']
    w = 0.1
    vert = [(round((o[0] + o[2]) / 2, 3), round(o[1] + w / 2, 3), round(o[3] - w / 2, 3)) for o in edges
            if abs((o[2] - o[0]) - w) < 1e-3]
    for sx in EG.SLOT_X:
        for side in (-1, 1):
            xx = round(xc + sx + side * EG.SLOT_W / 2, 3)
            ok = any(abs(v[0] - xx) < EPS and abs(v[1] - (y1 - EG.SLOT_D)) < EPS and abs(v[2] - y1) < EPS
                     for v in vert)
            check(ok, '2. key slot wall at x %.2f, y %.1f..%.1f (slot %+.2f, %.1f wide, %.1f deep)'
                  % (xx, y1 - EG.SLOT_D, y1, sx, EG.SLOT_W, EG.SLOT_D))
    for xx, what in ((xc - EG.TAB_W / 2, 'tab west'), (xc + EG.TAB_W / 2, 'tab east')):
        check(any(abs(v[0] - xx) < EPS and abs(v[1] - tab_y) < EPS for v in vert),
              '2. %s side at x %.2f from y %.1f' % (what, xx, tab_y))
    bx = [o for o in edges]
    x0, x1 = min(o[0] for o in bx) + w / 2, max(o[2] for o in bx) - w / 2
    check(abs((x1 - x0) - EG.BODY_W) < EPS, '2. body width %.2f mm' % (x1 - x0))

    # 3-4. fingers
    land = (y1 - EG.LAND_Y1, y1 - EG.LAND_Y0)
    for face, pins in (('F', range(1, 17)), ('B', range(17, 33))):
        cu = layer('%s_Cu.gbr' % face)
        fing = [o for o in cu if o[4] == 'flash' and o[5] == (EG.FINGER_W, EG.LAND_Y1 - EG.LAND_Y0)]
        want = sorted(round(xc + EG.pin_x(p), 3) for p in pins)
        got = sorted(round((o[0] + o[2]) / 2, 3) for o in fing)
        check(len(fing) == 16 and all(abs(a - b) < EPS for a, b in zip(want, got)),
              '3. %s.Cu: %d fingers at pin x (want 16)' % (face, len(fing)))
        check(all(abs(o[1] - land[0]) < EPS and abs(o[3] - land[1]) < EPS for o in fing),
              '3. %s.Cu fingers span %.1f..%.1f mm in' % (face, EG.LAND_Y0, EG.LAND_Y1))
        stray = [o for o in cu if o not in fing and o[3] > land[0] + EPS
                 and not any(f[0] - EPS <= o[0] and o[2] <= f[2] + EPS for f in fing)]
        check(not stray, '4. %s.Cu: no copper between the fingers in the finger field (%d stray)' % (face, len(stray)))
        mask = layer('%s_Mask.gbr' % face)
        cov = [f for f in fing if any(m[0] <= f[0] + EPS and m[1] <= f[1] + EPS and m[2] >= f[2] - EPS
                                      and m[3] >= f[3] - EPS for m in mask)]
        check(len(cov) == len(fing), '5. %s.Mask: %d / %d fingers inside a mask opening' % (face, len(cov), len(fing)))

    # 6-7. the tab: below the body's lower edge
    for n in ('In1_Cu', 'In2_Cu', 'In3_Cu', 'In4_Cu'):
        low = max(o[3] for o in layer(n + '.gbr'))
        check(low <= tab_y + EPS, '6. %s: lowest copper at y %.2f, tab starts at %.2f' % (n, low, tab_y))
    for n in ('F_Paste', 'B_Paste'):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= tab_y + EPS, '7. %s: lowest object at y %.2f (tab starts at %.2f)' % (n, low, tab_y))
    win = y1 - EG.MASK_Y1
    for n in ('F_Silkscreen', 'B_Silkscreen'):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= win - 0.1, '7. %s: lowest ink at y %.2f, finger mask window from %.2f' % (n, low, win))
    for n, t in files.items():
        if n.endswith('.drl'):
            h = drills(t)
            low = max((p[1] for p in h), default=0)
            check(low <= tab_y + EPS, '7. %s: %d hits, lowest at y %.2f' % (n, len(h), low))
    print('%d failures' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
