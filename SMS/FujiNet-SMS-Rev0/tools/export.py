#!/usr/bin/env python3
"""Documentation outputs for FujiNet-SMS Rev0 (schematic only, no board yet):

  FujiNet-SMS-Rev0-BOM.csv                  grouped BOM (NES Rev0 column set; DNP parts flagged)
  docs/FujiNet-SMS-Rev0-schematic.pdf

Usage: python3 tools/export.py
"""
import csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
SCH = os.path.join(PRJ, D.PROJECT + '.kicad_sch')
DOCS = os.path.join(PRJ, 'docs')


def bom():
    groups = {}
    for p in D.PARTS:
        if p.bom:
            groups.setdefault((p.value, p.footprint, p.mpn, p.lcsc, p.dnp), []).append(p)
    ref_key = lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))
    rows = sorted(groups.items(), key=lambda kv: ref_key(kv[1][0].ref))
    with open(os.path.join(PRJ, D.PROJECT + '-BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(['Refs', 'Value', 'Footprint', 'MPN', 'LCSC', 'Description', 'DNP'])
        for (val, fp, mpn, lcsc, dnp), ps in rows:
            refs = ','.join(sorted((p.ref for p in ps), key=ref_key))
            w.writerow([refs, val, fp.split(':')[1], mpn, lcsc, ps[0].desc, 'DNP' if dnp else ''])
    return sum(len(ps) for (k, ps) in rows if not k[4]), len(rows)


def main():
    n, lines = bom()
    os.makedirs(DOCS, exist_ok=True)
    r = subprocess.run(['kicad-cli', 'sch', 'export', 'pdf', '-o', os.path.join(DOCS, D.PROJECT + '-schematic.pdf'), SCH],
                       capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('schematic PDF export failed')
    print('BOM: %d fitted parts in %d lines; schematic PDF written' % (n, lines))


if __name__ == '__main__':
    main()
