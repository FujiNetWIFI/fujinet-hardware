#!/usr/bin/env python3
"""Gate on the JLCPCB package tools/export.py writes, against the board and design.py (the JLC half of
FujiNet-5200 Rev0's check_fab.py; this board has no PCBWay package and no order-number text):

  1. designators: JLC BOM = JLC CPL = the board's assembled parts (every footprint design.py puts in
     the BOM and does not mark DNP), each exactly once
  2. JLC BOM: every line has an LCSC code, the one design.py gives its parts
  3. JLC CPL: every row has a measured rotation / origin entry (tools/audit/jlc/jlc_rotations.json)
     and sits at the footprint's centre plus that origin offset, turned with the footprint, at its
     rotation plus the correction; every part on the top side
  4. drills: the zip's Excellon hit count equals the board's vias + plated and unplated holes
  5. contact lands, from the zip itself: B.Mask opens exactly 26 lands at J1's pitch and span, land 1
     at the east end; B.Paste is empty (no paste on the lands, no bottom-side parts); no drill hit
     inside the land strip (the escapes are 17.4 mm in from the edge)

Usage: python3 tools/audit/check_fab.py          exit 1 on any failure
"""
import csv, json, math, os, re, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
sys.dont_write_bytecode = True
import design as D  # noqa: E402
from sexpr import parse, find, findall  # noqa: E402

PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
J = os.path.join(PRJ, 'exports', 'jlcpcb')
ZIP = os.path.join(J, D.PROJECT + '-gerbers.zip')
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
        pads = []
        for p in findall(fp, 'pad'):
            pat = find(p, 'at')
            px, py = float(pat[1]), float(pat[2])
            t_ = math.radians(-rot)
            pads.append((str(p[1]), x + px * math.cos(t_) - py * math.sin(t_),
                         y + px * math.sin(t_) + py * math.cos(t_), str(p[2])))
        fps[ref] = dict(x=x, y=y, rot=rot, pads=pads, layer=str(find(fp, 'layer')[1]))
    return t, fps, len(findall(t, 'via'))


def flashes(text):
    """(aperture, x, y) of every D03 flash, KiCad y (gerber y negated), mm (format 4.6)."""
    out, ap = [], None
    for line in text.splitlines():
        m = re.match(r'^D(\d+)\*$', line)
        if m and int(m.group(1)) >= 10:
            ap = int(m.group(1))
        m = re.match(r'^X(-?\d+)Y(-?\d+)D03\*$', line)
        if m:
            out.append((ap, int(m.group(1)) / 1e6, -int(m.group(2)) / 1e6))
    return out


def main():
    want = sorted(p.ref for p in D.PARTS if p.bom and not p.dnp)
    t, fps, nvia = board()
    # ---- 1. designator sets -------------------------------------------------------------------------
    jb = list(csv.DictReader(open(os.path.join(J, 'BOM-JLCPCB.csv'))))
    jc = list(csv.DictReader(open(os.path.join(J, 'CPL-JLCPCB.csv'))))
    on_board = sorted(r for r in want if r in fps)
    check(on_board == want, '1. every assembled design.py part is on the board (%d)' % len(want))
    for name, lst in (('JLC BOM', [r for row in jb for r in refs_of(row['Designator'])]),
                      ('JLC CPL', [row['Designator'] for row in jc])):
        check(sorted(lst) == want and len(lst) == len(set(lst)),
              '1. %s designators = the assembled parts, once each (%d)' % (name, len(lst)))
    # ---- 2. BOM sourcing column ---------------------------------------------------------------------
    bad = [row['Designator'] for row in jb
           if any(D.BY_REF[r].lcsc != row['LCSC Part #'] or not row['LCSC Part #'] for r in refs_of(row['Designator']))]
    check(not bad, '2. JLC BOM: every line carries its parts\' LCSC code%s' % (' (bad: %s)' % bad if bad else ''))
    # ---- 3. JLC CPL ---------------------------------------------------------------------------------
    rot = {(e['footprint'], e['lcsc']): e for e in json.load(open(os.path.join(HERE, 'jlc', 'jlc_rotations.json')))}
    errs = []
    for row in jc:
        r = row['Designator']
        p, f = D.BY_REF[r], fps[r]
        e = rot.get((p.footprint.split(':')[1], p.lcsc))
        if e is None or e.get('rotation_correction_deg') is None:
            errs.append('%s: no rotation entry' % r)
            continue
        if f['layer'] != 'F.Cu' or row['Layer'] != 'Top':
            errs.append('%s: not on the top side' % r)
        dx, dy = e['origin_offset_mm']
        th = math.radians(f['rot'])
        # CPL frame: x right, y up (KiCad y negated); the offset is in the footprint frame (y down)
        ex = f['x'] + dx * math.cos(th) + dy * math.sin(th)
        ey = -f['y'] + dx * math.sin(th) - dy * math.cos(th)
        if abs(mm(row['Mid X']) - ex) > 0.002 or abs(mm(row['Mid Y']) - ey) > 0.002:
            errs.append('%s: at (%s, %s), want (%.4f, %.4f)' % (r, row['Mid X'], row['Mid Y'], ex, ey))
        d = (float(row['Rotation']) - (f['rot'] + e['rotation_correction_deg'])) % 360
        if min(d, 360 - d) > 0.01:
            errs.append('%s: rotation %s, want %g' % (r, row['Rotation'], (f['rot'] + e['rotation_correction_deg']) % 360))
    check(not errs, '3. JLC CPL: measured rotation / origin for every row, positions and rotations recomputed%s'
          % (': ' + '; '.join(errs[:8]) if errs else ' (%d rows)' % len(jc)))
    # ---- 4. drills ----------------------------------------------------------------------------------
    plated = sum(1 for f in fps.values() for p in f['pads'] if p[3] == 'thru_hole')
    npth = sum(1 for f in fps.values() for p in f['pads'] if p[3] == 'np_thru_hole')
    zf = zipfile.ZipFile(ZIP)
    hits = []
    for n in zf.namelist():
        if n.endswith('.drl'):
            for line in zf.read(n).decode().splitlines():
                # a hit, or a routed slot (X..Y..G85X..Y..: the USB-C shell tabs)
                m = re.match(r'^X(-?[\d.]+)Y(-?[\d.]+)(G85X-?[\d.]+Y-?[\d.]+)?$', line)
                if m:
                    hits.append((float(m.group(1)), -float(m.group(2))))
    check(len(hits) == nvia + plated + npth, '4. drills: %d hits = %d vias + %d plated pads + %d unplated'
          % (len(hits), nvia, plated, npth))
    # ---- 5. contact lands, from the gerbers ---------------------------------------------------------
    names = zf.namelist()
    mask = zf.read(next(n for n in names if n.endswith('B_Mask.gbr'))).decode()
    paste = zf.read(next(n for n in names if n.endswith('B_Paste.gbr'))).decode()
    j1 = fps['J1']
    lands = sorted([(x, y) for (n, x, y, kind) in j1['pads'] if kind == 'smd'], key=lambda c: -c[0])
    land_xy = {}
    for (n, x, y, kind) in j1['pads']:          # the 1.7 x 14 land is the pad whose centre is mid-strip
        if kind == 'smd' and abs(y - (j1['y'] - 8.0)) < 0.01:
            land_xy[n] = (x, y)
    xs = [land_xy[str(i)][0] for i in range(1, 27)] if len(land_xy) == 26 else []
    ok_pitch = len(xs) == 26 and all(abs((xs[i] - xs[i + 1]) - 2.54) < 0.001 for i in range(25))
    check(ok_pitch and abs(xs[0] - xs[-1] - 63.5) < 0.001 and xs[0] > j1['x'],
          '5. board: 26 lands at 2.54 mm, span 63.5 mm, land 1 east (x %s)' % ('%.2f' % xs[0] if xs else '?'))
    fl = flashes(mask)
    opened = [n for n, (x, y) in land_xy.items()
              if any(abs(fx - x) < 0.01 and abs(fy - y) < 0.01 for (_, fx, fy) in fl)]
    check(len(opened) == 26, '5. B.Mask: every land has its own mask opening (%d of 26)' % len(opened))
    check(not flashes(paste) and not re.search(r'D0[12]\*', paste),
          '5. B.Paste: empty (no paste on the lands, no bottom-side parts)')
    y_edge = j1['y']
    strip = [h for h in hits if xs and xs[-1] - 1.0 < h[0] < xs[0] + 1.0 and y_edge - 15.1 < h[1] < y_edge + 0.1]
    check(not strip, '5. no drill hit inside the land strip (%d found)' % len(strip))
    print('check_fab: %s' % ('%d failure(s)' % len(FAIL) if FAIL else 'all checks pass'))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
