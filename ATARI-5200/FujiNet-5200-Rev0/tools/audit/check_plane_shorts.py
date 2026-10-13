#!/usr/bin/env python3
"""Gate on the fab zips themselves: no plated hole inside an inner-layer pour of another net.

Each PTH drill hit takes its net from the copper flashed at it (KiCad's X2 %TO.N attributes on the
pads and vias of every copper layer); every In<n>.Cu region (a zone fill, G36 / G37) that contains
the hit must carry the same net.  Slots (G85) count at their centre.  The gerbers are plotted from
the zone fills SAVED in the board, so this catches what DRC with --refill-zones cannot: vias added
after the last fill (stitch_gnd.py) sitting inside the inner power pours.  Found on FujiNet-StudioII
Rev0, 2026-10-11; see tools/fill_zones.py.

Usage: python3 tools/audit/check_plane_shorts.py [zip ...]    (default: every exports/*/*-gerbers.zip)
exit 1 on any short or any plated hole without a net-tagged flash
"""
import collections, glob, os, re, sys, zipfile

PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COORD = re.compile(r'(?:G0?1)?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0?([123])')


def fmt_scale(text):
    """Gerber coordinate scale from %FSLAX<i><d>Y..*% (KiCad: 4.6, mm)."""
    m = re.search(r'%FSLAX\d(\d)Y\d\d\*%', text)
    return 10 ** int(m.group(1)) if m else 1e6


def net_objects(text):
    """(regions [(net, [contour, ...])], flashes [(x, y, net)]) of a copper layer, y negated."""
    sc = fmt_scale(text)
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
        m = COORD.fullmatch(cmd)
        if not m:
            continue
        x = int(m.group(1)) / sc if m.group(1) else x
        y = -int(m.group(2)) / sc if m.group(2) else y
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
    """[(x, y)] of an Excellon file's hits, y negated; a G85 slot at its centre."""
    hits = []
    for line in text.splitlines():
        m = re.match(r'X(-?[\d.]+)Y(-?[\d.]+)(?:G85X(-?[\d.]+)Y(-?[\d.]+))?', line.strip())
        if m and m.group(3):
            hits.append(((float(m.group(1)) + float(m.group(3))) / 2, -(float(m.group(2)) + float(m.group(4))) / 2))
        elif m:
            hits.append((float(m.group(1)), -float(m.group(2))))
    return hits


def check(zp):
    with zipfile.ZipFile(zp) as z:
        files = {n: z.read(n).decode(errors='replace') for n in z.namelist()}
    pth = [n for n in files if re.search(r'PTH\.(drl|xln|txt)$', n, re.I) and not re.search(r'NPTH', n, re.I)]
    cu = [n for n in files if re.search(r'(F|B|In\d+)_Cu\.(gbr|g\w+)$', n)]
    inner = [n for n in cu if re.search(r'In\d+_Cu', n)]
    if not pth or not cu:
        return ['no plated drill file or copper layers in the zip']
    if not inner:
        return []
    hits = drills(files[pth[0]])
    flash = collections.defaultdict(list)          # 0.1 mm buckets
    for n in cu:
        for fx, fy, fnet in net_objects(files[n])[1]:
            if fnet:
                flash[(round(fx, 1), round(fy, 1))].append((fx, fy, fnet))

    def net_at(x, y):
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for fx, fy, fnet in flash.get((round(round(x, 1) + i / 10, 1), round(round(y, 1) + j / 10, 1)), []):
                    if abs(fx - x) < 0.01 and abs(fy - y) < 0.01:
                        return fnet
        return None
    nets = [net_at(x, y) for x, y in hits]
    bad = ['plated hole at (%.3f, %.3f) without a net-tagged flash' % h for h, n in zip(hits, nets) if n is None]
    for n in inner:
        regions = [(rn, r) for rn, r in net_objects(files[n])[0] if r]
        boxes = [(min(p[0] for c in r for p in c), min(p[1] for c in r for p in c),
                  max(p[0] for c in r for p in c), max(p[1] for c in r for p in c)) for _, r in regions]
        for (hx, hy), hn in zip(hits, nets):
            for (rn, r), (x0, y0, x1, y1) in zip(regions, boxes):
                if x0 <= hx <= x1 and y0 <= hy <= y1 and rn != hn and inside(hx, hy, r):
                    bad.append('%s: %s hole at (%.3f, %.3f) inside a %s pour' % (n.rsplit('-', 1)[-1][:-4], hn, hx, hy, rn))
    return bad


def main():
    zips = sys.argv[1:] or sorted(glob.glob(os.path.join(PRJ, 'exports', '*', '*-gerbers.zip')))
    if not zips:
        raise SystemExit('check_plane_shorts: no exports/*/*-gerbers.zip: run tools/export.py')
    fails = 0
    for zp in zips:
        bad = check(zp)
        print('%s  %s: %s' % ('ok  ' if not bad else 'FAIL', os.path.relpath(zp, PRJ),
                               'no plated hole inside an inner pour of another net' if not bad else
                               '%d problems, e.g. %s' % (len(bad), bad[:3])))
        fails += bool(bad)
    print('check_plane_shorts: %d zip(s), %d failing' % (len(zips), fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
