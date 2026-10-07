#!/usr/bin/env python3
"""Fabrication + documentation outputs for Fujiversal-Atari2600 Rev1.

Always (from the schematic / design.py):
  Fujiversal-Atari2600-Rev1-BOM.csv         full BOM (DNP parts flagged)
  exports/jlcpcb/BOM-JLCPCB.csv             Comment,Designator,Footprint,LCSC Part # (no DNP parts)
  docs/Fujiversal-Atari2600-Rev1-schematic.pdf

Only once Fujiversal-Atari2600-Rev1.kicad_pcb exists:
  exports/jlcpcb/CPL-JLCPCB.csv             Designator,Mid X,Mid Y,Layer,Rotation
  exports/jlcpcb/Fujiversal-Atari2600-Rev1-gerbers.zip   gerbers + Excellon drill
  docs/layout-front.svg, docs/layout-back.svg, docs/board-top.png, docs/board-bottom.png

CPL rotations and origins: JLCPCB places each part by the EasyEDA footprint of
its LCSC code.  tools/audit/jlc/jlc_rotations.json holds, per footprint, the
rotation correction and the origin offset measured by comparing every one of
our footprints with that EasyEDA footprint pad by pad (polarity by cathode
marks, not pad numbers); the CPL applies them.  Still check the placement
preview on JLCPCB's order page before paying.

Usage: python3 tools/export.py
"""
import csv, json, math, os, re, shutil, subprocess, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
SCH = os.path.join(PRJ, D.PROJECT + '.kicad_sch')
OUT = os.path.join(PRJ, 'exports', 'jlcpcb')
DOCS = os.path.join(PRJ, 'docs')

JLC = {}     # footprint -> (rotation correction deg, origin offset (dx, dy) mm in the footprint frame)
for _e in json.load(open(os.path.join(HERE, 'audit', 'jlc', 'jlc_rotations.json'))):
    JLC[_e['footprint']] = (_e['rotation_correction_deg'], tuple(_e['origin_offset_mm']))


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('failed: ' + ' '.join(a))
    return r.stdout


def boms():
    groups = {}
    for p in D.PARTS:
        if not p.bom:
            continue
        key = (p.value, p.footprint, p.mpn, p.lcsc, p.dnp)
        groups.setdefault(key, []).append(p)
    ref_key = lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))
    rows = sorted(groups.items(), key=lambda kv: ref_key(kv[1][0].ref))
    with open(os.path.join(PRJ, D.PROJECT + '-BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(['Refs', 'Value', 'Footprint', 'MPN', 'LCSC', 'Description', 'DNP'])
        for (val, fp, mpn, lcsc, dnp), ps in rows:
            refs = ','.join(sorted((p.ref for p in ps), key=ref_key))
            w.writerow([refs, val, fp.split(':')[1], mpn, lcsc, ps[0].desc, 'DNP' if dnp else ''])
    with open(os.path.join(OUT, 'BOM-JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (val, fp, mpn, lcsc, dnp), ps in rows:
            if dnp:
                continue       # not assembled: the CPL export skips DNP parts too
            if not lcsc:
                raise SystemExit('no LCSC code for ' + ps[0].ref)
            w.writerow([val, ','.join(sorted((p.ref for p in ps), key=ref_key)), fp.split(':')[1], lcsc])
    return {p.ref for p in D.PARTS if p.bom and not p.dnp}


def cpl(bom_refs):
    tmp = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-rev1-pos.csv')
    run('kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
        '--exclude-dnp', '-o', tmp, PCB)
    rows = list(csv.DictReader(open(tmp)))
    seen = set()
    with open(os.path.join(OUT, 'CPL-JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in rows:
            ref = r['Ref']
            if ref not in bom_refs:
                continue
            rot = float(r['Rot'])
            fpname = D.BY_REF[ref].footprint.split(':')[1]
            if fpname not in JLC:
                raise SystemExit('no JLC rotation/offset measured for footprint ' + fpname)
            corr, (dx, dy) = JLC[fpname]
            t = math.radians(rot)
            # the EasyEDA origin, in the .pos frame (Y up): footprint frame +y is down
            x = float(r['PosX']) + dx * math.cos(t) + dy * math.sin(t)
            y = float(r['PosY']) + dx * math.sin(t) - dy * math.cos(t)
            w.writerow([ref, '%.4fmm' % x, '%.4fmm' % y, 'Top' if r['Side'] == 'top' else 'Bottom',
                        '%g' % ((rot + corr) % 360)])
            seen.add(ref)
    missing = bom_refs - seen
    if missing:
        raise SystemExit('BOM parts missing from the placement file: ' + ' '.join(sorted(missing)))
    return len(seen)


def gerbers():
    g = os.path.join(OUT, 'gerbers')
    shutil.rmtree(g, ignore_errors=True)
    os.makedirs(g)
    layers = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', layers, '--subtract-soldermask',
        '--no-protel-ext', '-o', g + '/', PCB)
    run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
        '--generate-map', '--map-format', 'gerberx2', '-o', g + '/', PCB)
    zf = os.path.join(OUT, D.PROJECT + '-gerbers.zip')
    with zipfile.ZipFile(zf, 'w', zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(g)):
            z.write(os.path.join(g, fn), fn)
    shutil.rmtree(g)
    return zf


def sch_docs():
    os.makedirs(DOCS, exist_ok=True)
    run('kicad-cli', 'sch', 'export', 'pdf', '-o', os.path.join(DOCS, D.PROJECT + '-schematic.pdf'), SCH)


def pcb_docs():
    run('kicad-cli', 'pcb', 'export', 'svg', '--layers', 'F.Cu,F.SilkS,F.Mask,Edge.Cuts', '--mode-single',
        '--fit-page-to-board', '-o', os.path.join(DOCS, 'layout-front.svg'), PCB)
    run('kicad-cli', 'pcb', 'export', 'svg', '--layers', 'B.Cu,B.SilkS,B.Mask,Edge.Cuts', '--mode-single',
        '--mirror', '--fit-page-to-board', '-o', os.path.join(DOCS, 'layout-back.svg'), PCB)
    for side, fn in (('top', 'board-top.png'), ('bottom', 'board-bottom.png')):
        run('kicad-cli', 'pcb', 'render', '--side', side, '--width', '1600', '--height', '1000',
            '--quality', 'high', '--background', 'opaque', '-o', os.path.join(DOCS, fn), PCB)


def main():
    os.makedirs(OUT, exist_ok=True)
    refs = boms()
    sch_docs()
    if not os.path.exists(PCB):
        print('BOM: %d placed refs; schematic PDF written. No %s yet: CPL, gerbers and layout '
              'renders skipped.' % (len(refs), os.path.basename(PCB)))
        return
    n = cpl(refs)
    zf = gerbers()
    pcb_docs()
    print('BOM: %d placed refs; CPL: %d rows; %s' % (len(refs), n, os.path.relpath(zf, PRJ)))


if __name__ == '__main__':
    main()
