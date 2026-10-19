#!/usr/bin/env python3
"""Gate on the fab outputs themselves (not the .kicad_pcb): the gerbers and drills that
tools/export.py zipped for JLCPCB, checked against the edge footprint and gen_pcb.py's outline.
(FujiNet-5200 Rev0's check, for the NES's 72-pin edge.)

  1. Edge.Cuts: the 93.5 mm tab's straight sides from the tab base to the insertion edge, and
     the 100 mm body
  2. F.Cu / B.Cu: exactly 36 fingers per face, each at its pad's x and size from
     FujiNet-NES.pretty/NES_Cart_Edge_72.kicad_mod (pins 1-36 on F.Cu, pin N+36 behind pin N),
     1.0-13.0 mm in from the edge
  3. no other outer copper in the finger field (each finger's stub leaves within its width)
  4. F.Mask / B.Mask: every finger's contact zone (from 1.0 mm in to the opening's depth: 6.5 mm
     front, 11.0 mm back, as Nintendo's boards) inside a mask opening
  5. In1-In4: no copper on the tab
  6. no drill hit and no paste on the tab; no silkscreen in either finger mask window
Gerber y is KiCad's y negated (KiCad 10 exports with y up); coordinates are mm, format 4.6.

Usage: python3 tools/audit/check_gerbers.py          exit 1 on any failure
"""
import os, re, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gen_pcb as G
import design as D
from sexpr import parse as sparse, find, findall

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
    """Every dark object as a KiCad-frame box (x0, y0, x1, y1, kind, size), kind flash/draw/region.
    Clear-polarity objects (%LPC%) remove ink, so they are skipped."""
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
    hits = []
    for line in text.splitlines():
        m = re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)', line.strip())
        if m:
            hits.append((float(m.group(1)), -float(m.group(2))))
    return hits


def edge_footprint():
    """{pad number: (face, x0, y0, x1, y1)} in board coordinates, and {face: mask window y0}."""
    G.do_placement(G.place)
    jx, jy, jr = G.PLACE['J1']
    assert jr == 0
    fp = sparse(open(os.path.join(PRJ, D.LIB + '.pretty', 'NES_Cart_Edge_72.kicad_mod')).read())
    pads = {}
    for p in findall(fp, 'pad'):
        a, sz = find(p, 'at'), find(p, 'size')
        cx, cy, w, h = jx + float(a[1]), jy + float(a[2]), float(sz[1]), float(sz[2])
        face = str(find(p, 'layers')[1])[0]
        pads[int(p[1])] = (face, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    win = {}
    for r in findall(fp, 'fp_rect'):
        L = str(find(r, 'layer')[1])
        if L.endswith('.Mask'):
            win[L[0]] = jy + min(float(find(r, 'start')[2]), float(find(r, 'end')[2]))
    return pads, win


def main():
    if not os.path.exists(ZIP):
        raise SystemExit('missing %s: run tools/export.py' % os.path.relpath(ZIP, PRJ))
    with zipfile.ZipFile(ZIP) as f:
        files = {n: f.read(n).decode() for n in f.namelist()}
    layer = lambda suffix: parse(next(t for n, t in files.items() if n.endswith(suffix)))
    pads, win = edge_footprint()
    y1, tab_y = G.Y1, G.TAB_Y

    # 1. outline: vertical runs of the profile
    edges = [o for o in layer('Edge_Cuts.gbr') if o[4] == 'draw']
    w = 0.1
    vert = [(round((o[0] + o[2]) / 2, 3), round(o[1] + w / 2, 3), round(o[3] - w / 2, 3)) for o in edges
            if abs((o[2] - o[0]) - w) < 1e-3]
    for xx, what in ((G.TAB_X0, 'tab west'), (G.TAB_X1, 'tab east')):
        check(any(abs(v[0] - xx) < EPS and abs(v[1] - tab_y) < EPS and abs(v[2] - y1) < EPS for v in vert),
              '1. %s side at x %.2f, y %.1f..%.1f' % (what, xx, tab_y, y1))
    x0, x1 = min(o[0] for o in edges) + w / 2, max(o[2] for o in edges) - w / 2
    check(abs((x1 - x0) - (G.X1 - G.X0)) < EPS, '1. board width %.2f mm (want %.2f)' % (x1 - x0, G.X1 - G.X0))

    # 2-4. fingers, the finger field, the mask windows
    field_y = min(p[2] for p in pads.values())          # finger copper starts here (13 mm in)
    for face, nums in (('F', range(1, 37)), ('B', range(37, 73))):
        cu = layer('%s_Cu.gbr' % face)
        want = {n: pads[n] for n in nums}
        assert all(p[0] == face for p in want.values()), 'edge footprint: pins %d.. not all on %s.Cu' % (nums[0], face)
        found, bad = [], []
        for n, (_, px0, py0, px1, py1) in want.items():
            o = next((o for o in cu if o[4] == 'flash' and abs(o[0] - px0) < EPS and abs(o[1] - py0) < EPS
                      and abs(o[2] - px1) < EPS and abs(o[3] - py1) < EPS), None)
            (found if o else bad).append(o or n)
        check(not bad, '2. %s.Cu: %d / %d fingers at their pads (%.1f..%.1f mm in from the edge)%s'
              % (face, len(found), len(want), y1 - field_y, y1 - min(p[4] for p in want.values()),
                 ' -- missing pins %s' % bad if bad else ''))
        stray = [o for o in cu if o not in found and o[3] > field_y + EPS
                 and not any(f[0] - EPS <= o[0] and o[2] <= f[2] + EPS for f in found)]
        check(not stray, '3. %s.Cu: no copper between the fingers in the finger field (%d stray)' % (face, len(stray)))
        mask = layer('%s_Mask.gbr' % face)
        zone = lambda f: (f[0], win[face], f[2], f[3])
        cov = [f for f in found if any(m[0] <= zone(f)[0] + EPS and m[1] <= zone(f)[1] + EPS and m[2] >= zone(f)[2] - EPS
                                       and m[3] >= zone(f)[3] - EPS for m in mask)]
        check(len(cov) == len(found), '4. %s.Mask: %d / %d fingers open from %.1f mm in to the edge'
              % (face, len(cov), len(found), y1 - win[face]))

    # 5-6. the tab
    for n in ('In1_Cu', 'In2_Cu', 'In3_Cu', 'In4_Cu'):
        low = max(o[3] for o in layer(n + '.gbr'))
        check(low <= tab_y + EPS, '5. %s: lowest copper at y %.2f, tab from %.2f' % (n, low, tab_y))
    for n in ('F_Paste', 'B_Paste'):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= tab_y + EPS, '6. %s: lowest object at y %.2f (tab from %.2f)' % (n, low, tab_y))
    for n, face in (('F_Silkscreen', 'F'), ('B_Silkscreen', 'B')):
        low = max((o[3] for o in layer(n + '.gbr')), default=0)
        check(low <= win[face] - 0.1, '6. %s: lowest ink at y %.2f, finger mask window from %.2f' % (n, low, win[face]))
    for n, t in files.items():
        if n.endswith('.drl'):
            h = drills(t)
            low = max((p[1] for p in h), default=0)
            check(low <= tab_y + EPS, '6. %s: %d hits, lowest at y %.2f (tab from %.2f)' % (n, len(h), low, tab_y))
    print('%d failures' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
