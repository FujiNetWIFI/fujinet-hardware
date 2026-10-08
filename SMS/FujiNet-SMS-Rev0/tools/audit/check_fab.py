#!/usr/bin/env python3
"""Gate on the two fab packages tools/export.py writes, against the board and design.py:

  1. designators: JLC BOM = JLC CPL = PCBWay BOM = PCBWay centroid = the board's assembled parts
     (every footprint design.py puts in the BOM and does not mark DNP), each exactly once
  2. JLC BOM: every line has an LCSC code, the one design.py gives its parts
  3. PCBWay BOM: every line has an MPN and a manufacturer, design.py's
  4. JLC CPL: every row has a measured rotation / origin entry (tools/audit/jlc/jlc_rotations.json)
     and sits at the footprint's centre plus that origin offset, turned with the footprint, at its
     rotation plus the correction; every part on the top side
  5. PCBWay centroid: KiCad's own centres and rotations, unmodified
  6. drills: the zips' Excellon hit count equals the board's vias + plated and unplated holes
  7. the order-number text: inside the board, clear of every F.Cu pad, F.Silkscreen item and
     courtyard, and present only in the JLC zip's F.Silkscreen
  8. tools/audit/check_gerbers.py passes (fingers, tab, masks; zips identical but the silkscreen)

Usage: python3 tools/audit/check_fab.py          exit 1 on any failure
"""
import csv, io, json, math, os, re, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D
import placement as PL
from sexpr import parse, find, findall

PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
J, W = os.path.join(PRJ, 'exports', 'jlcpcb'), os.path.join(PRJ, 'exports', 'pcbway')
FAIL = []


def check(ok, msg):
    print('%s  %s' % ('PASS' if ok else 'FAIL', msg))
    if not ok:
        FAIL.append(msg)


def refs_of(cell):
    return [r.strip() for r in cell.split(',') if r.strip()]


def mm(v):
    return float(v.replace('mm', ''))


def board():
    t = parse(open(PCB).read())
    fps = {}
    for fp in findall(t, 'footprint'):
        ref = next(str(p[2]) for p in findall(fp, 'property') if str(p[1]) == 'Reference')
        at = find(fp, 'at')
        x, y, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        attr = find(fp, 'attr')
        flags = [str(a) for a in attr[1:]] if attr else []
        pads = []
        for p in findall(fp, 'pad'):
            pat = find(p, 'at')
            px, py = float(pat[1]), float(pat[2])
            t_ = math.radians(-rot)
            gx = x + px * math.cos(t_) - py * math.sin(t_)
            gy = y + px * math.sin(t_) + py * math.cos(t_)
            sz = find(p, 'size')
            layers = [str(l) for l in find(p, 'layers')[1:]]
            pads.append((str(p[1]), gx, gy, float(sz[1]), float(sz[2]), layers, str(p[2])))   # (pad "num" type shape ...)
        crt = [(float(find(g, 'start')[1]), float(find(g, 'start')[2]), float(find(g, 'end')[1]), float(find(g, 'end')[2]))
               for g in findall(fp, 'fp_rect') if str(find(g, 'layer')[1]) == 'F.CrtYd']
        fps[ref] = dict(x=x, y=y, rot=rot, flags=flags, pads=pads, crt=crt, layer=str(find(fp, 'layer')[1]))
    vias = len(findall(t, 'via'))
    return t, fps, vias


def main():
    want = sorted(p.ref for p in D.PARTS if p.bom and not p.dnp)
    t, fps, nvia = board()
    # ---- 1. designator sets -------------------------------------------------------------------
    jb = list(csv.DictReader(open(os.path.join(J, 'BOM-JLCPCB.csv'))))
    jc = list(csv.DictReader(open(os.path.join(J, 'CPL-JLCPCB.csv'))))
    wb = list(csv.DictReader(open(os.path.join(W, 'BOM-PCBWay.csv'))))
    wc = list(csv.DictReader(open(os.path.join(W, 'Centroid-PCBWay.csv'))))
    sets = {'JLC BOM': [r for row in jb for r in refs_of(row['Designator'])],
            'JLC CPL': [row['Designator'] for row in jc],
            'PCBWay BOM': [r for row in wb for r in refs_of(row['Designator'])],
            'PCBWay centroid': [row['Designator'] for row in wc]}
    on_board = sorted(r for r in want if r in fps)
    check(on_board == want, '1. every assembled design.py part is on the board (%d)' % len(want))
    for name, lst in sets.items():
        check(sorted(lst) == want and len(lst) == len(set(lst)),
              '1. %s designators = the assembled parts, once each (%d)' % (name, len(lst)))
    # ---- 2. / 3. BOM sourcing columns ---------------------------------------------------------------
    bad = [row['Designator'] for row in jb
           if any(D.BY_REF[r].lcsc != row['LCSC Part #'] or not row['LCSC Part #'] for r in refs_of(row['Designator']))]
    check(not bad, '2. JLC BOM: every line carries its parts\' LCSC code%s' % (' (bad: %s)' % bad if bad else ''))
    bad = [row['Designator'] for row in wb
           if not row['MPN'] or not row['Manufacturer'] or
           any((D.BY_REF[r].mpn, D.BY_REF[r].mfr) != (row['MPN'], row['Manufacturer']) for r in refs_of(row['Designator']))]
    check(not bad, '3. PCBWay BOM: every line carries its parts\' MPN and manufacturer%s' % (' (bad: %s)' % bad if bad else ''))
    # ---- 4. JLC CPL ------------------------------------------------------------------------------------
    rot = {(e['footprint'], e['lcsc']): e for e in json.load(open(os.path.join(HERE, 'jlc', 'jlc_rotations.json')))}
    errs = []
    for row in jc:
        r = row['Designator']
        p, f = D.BY_REF[r], fps[r]
        e = rot.get((p.footprint.split(':')[1], p.lcsc))
        if e is None:
            errs.append('%s: no rotation entry' % r)
            continue
        if f['layer'] != 'F.Cu' or row['Layer'] != 'Top':
            errs.append('%s: not on the top side' % r)
        dx, dy = e['origin_offset_mm']
        th = math.radians(f['rot'])
        # .pos frame: x right, y up (KiCad y negated); the offset is in the footprint frame (y down)
        ex = f['x'] + dx * math.cos(th) + dy * math.sin(th)
        ey = -f['y'] + dx * math.sin(th) - dy * math.cos(th)
        if abs(mm(row['Mid X']) - ex) > 0.002 or abs(mm(row['Mid Y']) - ey) > 0.002:
            errs.append('%s: at (%s, %s), want (%.4f, %.4f)' % (r, row['Mid X'], row['Mid Y'], ex, ey))
        if abs((float(row['Rotation']) - (f['rot'] + e['rotation_correction_deg'])) % 360) > 0.01 and \
                abs((float(row['Rotation']) - (f['rot'] + e['rotation_correction_deg'])) % 360 - 360) > 0.01:
            errs.append('%s: rotation %s, want %g' % (r, row['Rotation'], (f['rot'] + e['rotation_correction_deg']) % 360))
    check(not errs, '4. JLC CPL: measured rotation / origin for every row, positions and rotations recomputed%s'
          % (': ' + '; '.join(errs[:8]) if errs else ' (%d rows)' % len(jc)))
    # ---- 5. PCBWay centroid ---------------------------------------------------------------------------
    errs = []
    for row in wc:
        f = fps[row['Designator']]
        if abs(mm(row['Mid X']) - f['x']) > 0.002 or abs(mm(row['Mid Y']) + f['y']) > 0.002 or \
                abs((float(row['Rotation']) - f['rot']) % 360) > 0.01 and abs((float(row['Rotation']) - f['rot']) % 360 - 360) > 0.01:
            errs.append(row['Designator'])
    check(not errs, '5. PCBWay centroid: KiCad centres and rotations, unmodified%s' % (': ' + ' '.join(errs[:10]) if errs else ''))
    # ---- 6. drills ---------------------------------------------------------------------------------------
    holes = nvia + sum(1 for f in fps.values() for p in f['pads'] if p[6] == 'thru_hole')
    npth = sum(1 for f in fps.values() for p in f['pads'] if p[6] == 'np_thru_hole')
    for z in (J, W):
        zf = zipfile.ZipFile(os.path.join(z, D.PROJECT + '-gerbers.zip'))
        hits = 0
        for n in zf.namelist():
            if n.endswith('.drl'):
                # a hit, or a routed slot (X..Y..G85X..Y..: the USB-C shell tabs)
                hits += sum(1 for line in zf.read(n).decode().splitlines()
                            if re.match(r'^X-?[\d.]+Y-?[\d.]+(G85X-?[\d.]+Y-?[\d.]+)?$', line))
        check(hits == holes + npth, '6. %s drills: %d hits = %d vias + %d plated pads + %d unplated'
              % (os.path.basename(z), hits, nvia, holes - nvia, npth))
    # ---- 7. the order-number text --------------------------------------------------------------------
    (x, y), h = PL.JLC_ORDER
    w = 0.95 * h * len('JLCJLCJLCJLC')
    box = (x - w / 2 - 0.3, y - h / 2 - 0.3, x + w / 2 + 0.3, y + h / 2 + 0.3)
    hit = []
    for ref, f in fps.items():
        for (n, px, py, sx, sy, layers, kind) in f['pads']:
            if any(l in ('F.Cu', '*.Cu') for l in layers) and \
                    box[0] < px + sx / 2 and px - sx / 2 < box[2] and box[1] < py + sy / 2 and py - sy / 2 < box[3]:
                hit.append('%s pad %s' % (ref, n))
        for (x0, y0, x1, y1) in f['crt']:
            th = math.radians(-f['rot'])
            pts = [(f['x'] + a * math.cos(th) - b * math.sin(th), f['y'] + a * math.sin(th) + b * math.cos(th))
                   for a in (x0, x1) for b in (y0, y1)]
            cx0, cx1 = min(p[0] for p in pts), max(p[0] for p in pts)
            cy0, cy1 = min(p[1] for p in pts), max(p[1] for p in pts)
            if box[0] < cx1 and cx0 < box[2] and box[1] < cy1 and cy0 < box[3]:
                hit.append('%s courtyard' % ref)
    for g in findall(t, 'gr_text'):
        if str(find(g, 'layer')[1]) == 'F.SilkS':
            gx, gy = float(find(g, 'at')[1]), float(find(g, 'at')[2])
            if box[0] - 3 < gx < box[2] + 3 and box[1] - 1.5 < gy < box[3] + 1.5:
                hit.append('silk text %r' % str(g[1]))
    check(not hit, '7. order-number text at (%.1f, %.1f), %.1f mm: clear%s' % (x, y, h, (' -- hits ' + ', '.join(hit[:8])) if hit else ''))
    # the text is in the JLC zip's F.Silkscreen, and only there
    def strokes_at(zfn):
        z = zipfile.ZipFile(zfn)
        txt = z.read(next(n for n in z.namelist() if n.endswith('F_Silkscreen.gbr'))).decode()
        n, last = 0, None
        for line in txt.splitlines():
            m = re.match(r'X(-?\d+)Y(-?\d+)D0([12])\*', line)
            if m:
                px, py = int(m.group(1)) / 1e6, -int(m.group(2)) / 1e6     # gerber y up -> KiCad y
                if m.group(3) == '1' and box[0] < px < box[2] and box[1] < py < box[3]:
                    n += 1
        return n
    nj = strokes_at(os.path.join(J, D.PROJECT + '-gerbers.zip'))
    nw = strokes_at(os.path.join(W, D.PROJECT + '-gerbers.zip'))
    check(nj > 20 and nw == 0, '7. the order-number text is in the JLC F.Silkscreen (%d strokes) and not in PCBWay\'s (%d)' % (nj, nw))
    # ---- 8. gerber gate -----------------------------------------------------------------------------------
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check_gerbers.py')], capture_output=True, text=True)
    check(r.returncode == 0, '8. check_gerbers.py%s' % ('' if r.returncode == 0 else ':\n' + r.stdout[-1500:]))
    print('check_fab: %s' % ('%d failure(s)' % len(FAIL) if FAIL else 'all checks pass'))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
