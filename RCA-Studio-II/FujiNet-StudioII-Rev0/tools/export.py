#!/usr/bin/env python3
"""Schematic-stage outputs for FujiNet-StudioII Rev0 (there is no board yet):

  FujiNet-StudioII-Rev0-BOM.csv          full BOM with MPN, manufacturer, LCSC and description (DNP flagged)
  exports/jlcpcb/BOM-JLCPCB.csv          Comment,Designator,Footprint,LCSC Part # (no DNP / no-BOM parts)
  docs/FujiNet-StudioII-Rev0-schematic.pdf

Usage: python3 tools/export.py
"""
import csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
SCH = os.path.join(PRJ, D.PROJECT + '.kicad_sch')
ref_key = lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))


def groups(bom_only):
    g = {}
    for p in D.PARTS:
        if bom_only and (not p.bom or p.dnp):
            continue
        k = (p.value, p.footprint, p.mpn, p.lcsc, p.dnp)
        g.setdefault(k, []).append(p)
    return sorted(g.items(), key=lambda kv: ref_key(min((p.ref for p in kv[1]), key=ref_key)))


def main():
    with open(os.path.join(PRJ, D.PROJECT + '-BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Qty', 'References', 'Value', 'Footprint', 'MPN', 'Manufacturer', 'LCSC', 'Description', 'Notes'])
        for (val, fp, mpn, lcsc, dnp), ps in groups(False):
            refs = sorted((p.ref for p in ps), key=ref_key)
            note = 'DNP' if dnp else ('not in BOM' if not ps[0].bom else '')
            descs = sorted({p.desc for p in ps})
            desc = descs[0] if len(descs) == 1 else {'C': 'capacitor', 'R': 'resistor', 'SW': 'push button',
                                                       'D': 'diode', 'TP': 'test pad'}.get(
                ps[0].prefix, ps[0].prefix) + ' (several uses: see schematic)'
            w.writerow([len(ps), ' '.join(refs), val, fp.split(':')[-1], mpn, ps[0].mfr, lcsc, desc, note])
    os.makedirs(os.path.join(PRJ, 'exports', 'jlcpcb'), exist_ok=True)
    with open(os.path.join(PRJ, 'exports', 'jlcpcb', 'BOM-JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (val, fp, mpn, lcsc, dnp), ps in groups(True):
            w.writerow([val, ','.join(sorted((p.ref for p in ps), key=ref_key)), fp.split(':')[-1], lcsc])
    os.makedirs(os.path.join(PRJ, 'docs'), exist_ok=True)
    r = subprocess.run(['kicad-cli', 'sch', 'export', 'pdf', '-o',
                        os.path.join(PRJ, 'docs', D.PROJECT + '-schematic.pdf'), SCH], capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('kicad-cli sch export pdf failed')
    print('BOM (%d lines), JLCPCB BOM, schematic PDF written' % len(groups(False)))


if __name__ == '__main__':
    main()
