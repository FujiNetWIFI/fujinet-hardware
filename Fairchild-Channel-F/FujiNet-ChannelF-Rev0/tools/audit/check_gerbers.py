#!/usr/bin/env python3
"""Gate on the fab outputs themselves (not the .kicad_pcb): the gerbers and drills that
tools/export.py zipped for JLCPCB, checked against tools/edge_geom.py.

  1. the zip holds the 4 copper layers (F, In1, In2, B), both masks, pastes and silkscreens, the
     outline, plated and unplated Excellon -- and nothing for a 6-layer stack
  2. Edge.Cuts: the 68.3 mm tab's straight sides, the 77 mm body, the key slot's two sides
     (1.651 mm apart, from the lead-in up to the round top)
  3. B.Cu: exactly 22 fingers, each at its pin's x (2.54 mm, the 4-pitch gap at the slot, pin 1
     west seen from F.Cu), 1.8 mm wide, 0.5-12.0 mm in from the edge
  4. B.Cu: no other copper between the fingers in the finger field (stubs leave each finger within
     its own width), and none within 1 mm of fingers 21 (spare) / 22 (+12 V) but their own pads
  5. F.Cu: nothing in the finger field (the contacts are on B.Cu only)
  6. B.Mask: every finger inside the mask opening; F.Mask: no opening in the finger field
  7. In1 / In2: no copper in the finger field (the planes stop 13.5 mm in, past the slot's top)
  8. no paste on the tab (no parts within KEEP_D of the edge); no silkscreen in the fingers' mask
     window; no drill hit in the finger field; the four 5.6 mm boss holes in the NPTH file
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
        m = re.match(r'X(-?[\d.]+)Y(-?[\d.]+)', line)
        if m:
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

    xc, y1, tab_y, field_y = G.XC, G.Y1, G.TAB_Y, G.FIELD_Y
    # 2. outline: the profile is drawn segment by segment; collect vertical runs
    edges = [o for o in layer('Edge_Cuts.gbr') if o[4] == 'draw']
    w = 0.1
    vert = [(round((o[0] + o[2]) / 2, 3), round(o[1] + w / 2, 3), round(o[3] - w / 2, 3)) for o in edges
            if abs((o[2] - o[0]) - w) < 1e-3]
    for xx, what in ((xc - EG.TAB_W / 2, 'tab west'), (xc + EG.TAB_W / 2, 'tab east')):
        check(any(abs(v[0] - xx) < EPS and abs(v[1] - tab_y) < EPS and abs(v[2] - (y1 - EG.CH_TAB)) < EPS
                  for v in vert), '2. %s side at x %.2f, y %.1f..%.1f' % (what, xx, tab_y, y1 - EG.CH_TAB))
    for xx, what in ((G.X0, 'body west'), (G.X1, 'body east')):
        check(any(abs(v[0] - xx) < EPS for v in vert), '2. %s side at x %.2f' % (what, xx))
    s0, s1 = y1 - EG.SLOT_D + EG.SLOT_W / 2, y1 - EG.LEADIN_D
    for xx, what in ((xc - EG.SLOT_W / 2, 'slot west'), (xc + EG.SLOT_W / 2, 'slot east')):
        check(any(abs(v[0] - xx) < EPS and abs(v[1] - s0) < EPS and abs(v[2] - s1) < EPS for v in vert),
              '2. %s side at x %.3f, y %.2f..%.2f (the round top above it)' % (what, xx, s0, s1))
    check('G75' in next(t for n, t in files.items() if n.endswith('Edge_Cuts.gbr')), '2. the slot\'s round top is an arc')
    x0, x1 = min(o[0] for o in edges) + w / 2, max(o[2] for o in edges) - w / 2
    check(abs((x1 - x0) - EG.BODY_W) < EPS, '2. board width %.2f mm (want %.2f)' % (x1 - x0, EG.BODY_W))

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
          '3. B.Cu: %d fingers at their pins\' x (pin 1 at %.2f, pin 22 at %.2f), %.2f wide, %.1f..%.1f mm in%s'
          % (len(fing), xc + EG.pin_x(1), xc + EG.pin_x(22), EG.FINGER_W, EG.LAND_Y0, EG.LAND_Y1,
             ' -- bad pins %s' % bad if bad else ''))
    stray = [o for o in cu if o not in fing and o[3] > field_y + EPS
             and not any(f[0] - EPS <= o[0] and o[2] <= f[2] + EPS for f in fing)]
    check(not stray, '4. B.Cu: no copper between the fingers in the finger field (%d stray)' % len(stray))
    nc = [round(xc + EG.pin_x(p), 3) for p in EG.NC_PINS]

    def in_region(px, py, pts):
        c = False
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
                c = not c
        return c
    band = [(x + dx, field_y - dy) for x in nc for dx in (-EG.FINGER_W / 2 - 0.9, 0, EG.FINGER_W / 2 + 0.9)
            for dy in (0.05, 0.5, 1.0, 1.5, 1.95)]
    near = [o for o in cu if o not in fing and o[3] > field_y - 2.0 and
            any(o[0] < x + EG.FINGER_W / 2 + 1.0 and o[2] > x - EG.FINGER_W / 2 - 1.0 for x in nc)
            and (o[4] != 'region' or any(in_region(px, py, list(o[5])) for px, py in band))]   # pours: their real outline
    check(not near, '4. B.Cu: nothing within 1 mm of fingers 21 / 22 (+12 V) but their own pads (%d)' % len(near))
    fcu = [o for o in layer('F_Cu.gbr') if o[3] > field_y + EPS]
    check(not fcu, '5. F.Cu: nothing in the finger field (%d objects)' % len(fcu))
    mask = layer('B_Mask.gbr')
    cov = [f for f in fing if any(m[0] <= f[0] + EPS and m[1] <= f[1] + EPS and m[2] >= f[2] - EPS
                                  and m[3] >= f[3] - EPS for m in mask)]
    check(len(cov) == len(fing), '6. B.Mask: %d / %d fingers inside the mask opening' % (len(cov), len(fing)))
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
                ok = len(boss) == 4 and all(any(abs(p[0] - hx) < EPS and abs(p[1] - hy) < EPS for p in boss)
                                            for hx, hy, _ in G.HOLES)
                check(ok, '8. NPTH: the four %.1f mm boss holes at their places (%d found)' % (EG.HOLE_D, len(boss)))
    print('%d failures' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
