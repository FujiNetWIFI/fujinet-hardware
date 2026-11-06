#!/usr/bin/env python3
"""Gate on the JLCPCB and PCBWay packages (exports/), against Yannick Erb's own fab files.

  1. BOM-JLCPCB.csv: every part of Yannick's BOM (Original/BOM_*.csv), after the reference renames
     (tools/convert.py RENAME), on a line with his LCSC code; the same parts, no other; one LCSC code
     per line; the PCBWay BOM the same lines with his MPN.
  2. CPL-JLCPCB.csv: one row per BOM part, each equal to Yannick's pick-and-place file
     (Original/PickAndPlace_*.csv, EasyEDA's, made for JLCPCB) within POS mm and the same rotation, Top;
     the PCBWay centroid the same rows.
  3. the BOM, the CPL and the centroid name the same designators.
  4. the zips: the PCBWay one holds the 2-layer set (copper, masks, pastes, silkscreens, outline,
     PTH + NPTH drills) and no order-number text; the JLCPCB one the same files, equal byte for byte
     except B.Silkscreen, which holds exactly the order-number text, clear of every mask opening and
     inside the outline.
  (tools/audit/gerber_equiv.py proves the PCBWay zip's layers equal Yannick's gerbers.)

Usage: python3 tools/audit/check_fab.py      exit 1 on any failure
"""
import csv, io, os, re, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
import design as D
import convert as C
import export as E
import gerber_equiv as GE

PRJ = os.path.dirname(TOOLS)
ORIG = os.path.join(PRJ, 'Original')
POS = 0.02
fails = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        fails.append(msg)


def utf16(fn):
    return list(csv.DictReader(io.StringIO(open(fn, encoding='utf-16').read()), delimiter='\t'))


def refs(cell):
    return [r.strip() for r in cell.split(',') if r.strip()]


def mm(v):
    return float(v.rstrip('m'))


def main():
    ren = lambda r: C.RENAME.get(r, r)
    his_bom = utf16(os.path.join(ORIG, next(f for f in os.listdir(ORIG) if f.startswith('BOM_'))))
    his_pnp = utf16(os.path.join(ORIG, next(f for f in os.listdir(ORIG) if f.startswith('PickAndPlace_'))))
    his_lcsc = {ren(r): row['Supplier Part'] for row in his_bom for r in refs(row['Designator'])}
    his_mpn = {ren(r): row['Manufacturer Part'] for row in his_bom for r in refs(row['Designator'])}
    jb = list(csv.DictReader(open(os.path.join(E.JOUT, 'BOM-JLCPCB.csv'))))
    ours = {r: row['LCSC Part #'] for row in jb for r in refs(row['Designator'])}
    check(set(ours) == set(his_lcsc), 'JLC BOM: the %d parts of Yannick\'s BOM (%d lines), no other%s' % (
        len(his_lcsc), len(his_bom), '' if set(ours) == set(his_lcsc) else ': %s' % sorted(set(ours) ^ set(his_lcsc))))
    bad = sorted(r for r in ours if his_lcsc.get(r) != ours[r])
    check(not bad, 'JLC BOM: every part on Yannick\'s LCSC code%s' % ('' if not bad else ': %s' % bad))
    check(len(jb) == len(his_bom), 'JLC BOM: %d lines, as his' % len(jb))
    pw = list(csv.DictReader(open(os.path.join(E.POUT, 'BOM-PCBWay.csv'))))
    pmpn = {r: row['MPN'] for row in pw for r in refs(row['Designator'])}
    bad = sorted(r for r in pmpn if pmpn[r] != his_mpn.get(r))
    check(set(pmpn) == set(ours) and not bad, 'PCBWay BOM: the same parts, every one on Yannick\'s MPN%s' %
          ('' if not bad else ': %s' % bad))
    # placements against his pick-and-place
    his = {ren(r['Designator']): r for r in his_pnp}
    cpl = list(csv.DictReader(open(os.path.join(E.JOUT, 'CPL-JLCPCB.csv'))))
    off, rot = [], []
    worst = 0.0
    for r in cpl:
        h = his.get(r['Designator'])
        if h is None:
            off.append(r['Designator'] + ' (not in his file)')
            continue
        d = max(abs(mm(r['Mid X']) - mm(h['Mid X'])), abs(mm(r['Mid Y']) - mm(h['Mid Y'])))
        worst = max(worst, d)
        if d > POS:
            off.append('%s %.3f mm' % (r['Designator'], d))
        if float(r['Rotation']) % 360 != float(h['Rotation']) % 360 or r['Layer'] != 'Top' or h['Layer'] != 'T':
            rot.append('%s %s / his %s' % (r['Designator'], r['Rotation'], h['Rotation']))
    check(not off, 'CPL: all %d rows on Yannick\'s pick-and-place positions within %.2f mm (worst %.3f mm)%s'
          % (len(cpl), POS, worst, '' if not off else ': %s' % off[:6]))
    check(not rot, 'CPL: every rotation and side Yannick\'s%s' % ('' if not rot else ': %s' % rot[:6]))
    cen = list(csv.DictReader(open(os.path.join(E.POUT, 'Centroid-PCBWay.csv'))))
    same = [(r['Designator'], r['Mid X'], r['Mid Y'], r['Rotation']) for r in cpl] == \
           [(r['Designator'], r['Mid X'], r['Mid Y'], r['Rotation']) for r in cen]
    check(same, 'PCBWay centroid: the CPL\'s rows')
    names = {'BOM': set(ours), 'CPL': {r['Designator'] for r in cpl}, 'centroid': {r['Designator'] for r in cen}}
    check(len({frozenset(v) for v in names.values()}) == 1, 'BOM, CPL and centroid name the same %d designators' % len(ours))
    # the zips
    zp = zipfile.ZipFile(os.path.join(E.POUT, D.PROJECT + '-gerbers.zip'))
    zj = zipfile.ZipFile(os.path.join(E.JOUT, D.PROJECT + '-gerbers.zip'))
    need = ['-F_Cu.', '-B_Cu.', '-F_Mask.', '-B_Mask.', '-F_Paste.', '-B_Paste.',
            '-F_Silkscreen.', '-B_Silkscreen.', '-Edge_Cuts.', '-PTH.drl', '-NPTH.drl']
    pn = zp.namelist()
    layer = lambda stem: next(n for n in pn if stem in n and 'drl_map' not in n)
    miss = [s for s in need if not any(s in n for n in pn)]
    inner = [n for n in pn if re.search(r'In\d+_Cu', n)]
    check(not miss and not inner, 'PCBWay zip: the 2-layer set (%d files)%s' % (len(pn), '' if not miss and not inner
                                                                                else ': missing %s, inner %s' % (miss, inner)))
    check(sorted(zj.namelist()) == sorted(pn), 'JLC zip: the same files')
    # the drill maps carry the plotted file's own attributes (the JLC copy is a temporary board)
    body = lambda b: re.sub(rb'(?m)^(%TF.*|G04 .*)$', b'', b)
    diff = [n for n in pn if body(zp.read(n)) != body(zj.read(n))]
    check(diff == [layer('-B_Silkscreen.')],
          'JLC zip: equal to the PCBWay zip except B.Silkscreen (%s)' % ', '.join(diff))
    bs = layer('-B_Silkscreen.')
    check(not GE.raster(zp.read(bs).decode()).any(), 'PCBWay zip: no order-number text (B.Silkscreen empty)')
    txt = GE.raster(zj.read(bs).decode())
    masks = GE.raster(zj.read(layer('-B_Mask.')).decode()) | GE.raster(zj.read(layer('-F_Mask.')).decode())
    outline = GE.raster(zj.read(layer('-Edge_Cuts.')).decode())
    from scipy import ndimage
    inside = ndimage.binary_fill_holes(outline) & ~ndimage.binary_dilation(outline, iterations=20)
    holes = GE.hole_mask(GE.excellon(zj.read(layer('-PTH.drl')).decode()) +
                         GE.excellon(zj.read(layer('-NPTH.drl')).decode()))
    near = ndimage.binary_dilation(masks | holes, iterations=20)      # 0.5 mm round every opening
    check(txt.any() and not (txt & near).any() and not (txt & ~inside).any(),
          'JLC zip: the order-number text on B.Silkscreen (%.2f mm2), 0.5 mm clear of every mask opening and '
          'hole, inside the outline' % (txt.sum() / GE.PX ** 2))
    print('%d failures' % len(fails))
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == '__main__':
    main()
