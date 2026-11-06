#!/usr/bin/env python3
"""Fabrication + documentation outputs for Inty-FujiCard, for JLCPCB and for PCBWay.

Always (from the schematic / design.py):
  Inty-FujiCard-BOM.csv                    full BOM with MPN, manufacturer, LCSC and description
  exports/jlcpcb/BOM-JLCPCB.csv            Comment,Designator,Footprint,LCSC Part #
  exports/pcbway/BOM-PCBWay.csv            Line#,Qty,Designator,MPN,Manufacturer,Description,Package,Type,...
  docs/Inty-FujiCard-schematic.pdf

From Inty-FujiCard.kicad_pcb:
  exports/jlcpcb/CPL-JLCPCB.csv            Designator,Mid X,Mid Y,Layer,Rotation
  exports/jlcpcb/Inty-FujiCard-gerbers.zip gerbers + Excellon, the order-number text on B.Silkscreen
  exports/jlcpcb/ORDER-JLCPCB.md           the order, step by step, numbers from the board
  exports/pcbway/Centroid-PCBWay.csv       the same placements, with footprint and value
  exports/pcbway/Inty-FujiCard-gerbers.zip the same gerbers without the order-number text
  exports/pcbway/Assembly-top.pdf          F.Fab + F.Silkscreen + outline: references, pin 1
  exports/pcbway/ORDER-PCBWay.md
  docs/assembly-top.pdf, docs/layout-front.svg, docs/layout-back.svg, docs/board-top.png, docs/board-bottom.png

The board is Yannick Erb's, and so are its footprints: LCSC's own EasyEDA footprints, the ones
JLCPCB places by.  So the CPL is KiCad's own placement file, from the drill / place origin (the
board's lower-left corner, EasyEDA's (0, 0)), with no rotation table: tools/audit/check_fab.py
proves every row equals Yannick's own pick-and-place file (Original/PickAndPlace_*.csv).
The gerbers are plotted from the saved zone fills, never refilled (no --check-zones), and are
proven equal to Yannick's by tools/audit/gerber_equiv.py.

Usage: python3 tools/export.py
"""
import csv, json, os, re, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tmpdir import tmp
import design as D

PRJ = os.path.dirname(HERE)
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
SCH = os.path.join(PRJ, D.PROJECT + '.kicad_sch')
JOUT = os.path.join(PRJ, 'exports', 'jlcpcb')
POUT = os.path.join(PRJ, 'exports', 'pcbway')
DOCS = os.path.join(PRJ, 'docs')
ref_key = lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))
# JLCPCB prints its order number on B.Silkscreen here ("Specify a location"): a clear spot of the
# back, over the B.Cu GND pour, away from the fingers, the holes, the USB-C's legs and every mask
# opening (tools/audit/check_fab.py checks it)
JLC_ORDER = ((150.3, 112.2), 1.0, 'B')
JLC_TEXT = 'JLCJLCJLCJLC'
GERBER_LAYERS = 'F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('failed: ' + ' '.join(a))
    return r.stdout


def groups(bom_only):
    g = {}
    for p in D.PARTS:
        if bom_only and (not p.bom or p.dnp):
            continue
        k = (p.value, p.footprint, p.mpn, p.lcsc, p.dnp)
        g.setdefault(k, []).append(p)
    return sorted(g.items(), key=lambda kv: ref_key(min((p.ref for p in kv[1]), key=ref_key)))


KIND = {'R': 'Resistor', 'RN': 'Resistor array', 'C': 'Capacitor', 'L': 'Inductor', 'SW': 'Tactile switch',
        'J': 'Connector', 'Q': 'Transistor'}
# PCBWay BOM notes, by MPN
NOTES = {'RP2354A': 'Raspberry Pi RP2354A, QFN-60 7x7, 0.4 mm pitch (2 MB flash in the package)',
         'AOTA-B201610S3R3-101-T': 'the inductor the RP2350 datasheet specifies for its core regulator',
         'TYPE-C 16PIN 2MD(073)': 'SHOU HAN; 4 through-hole shell legs (paste-in-hole: paste is printed on them)',
         'ESP32-S3-WROOM-1-N16R8': '16 MB flash, 8 MB octal PSRAM (N16R8 required)'}


def boms():
    with open(os.path.join(PRJ, D.PROJECT + '-BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Qty', 'References', 'Value', 'Footprint', 'MPN', 'Manufacturer', 'LCSC', 'Description', 'Notes'])
        for (val, fp, mpn, lcsc, dnp), ps in groups(False):
            refs = sorted((p.ref for p in ps), key=ref_key)
            note = 'DNP' if dnp else ('not in BOM' if not ps[0].bom else '')
            descs = sorted({p.desc for p in ps})
            desc = descs[0] if len(descs) == 1 else {'C': 'capacitor', 'R': 'resistor', 'SW': 'push button',
                                                       'D': 'diode', 'TP': 'test pad', 'Q': 'transistor',
                                                       'H': 'mounting hole'}.get(
                ps[0].prefix, ps[0].prefix) + ' (several uses: see schematic)'
            w.writerow([len(ps), ' '.join(refs), val, fp.split(':')[-1], mpn, ps[0].mfr, lcsc, desc, note])
    with open(os.path.join(JOUT, 'BOM-JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (val, fp, mpn, lcsc, dnp), ps in groups(True):
            if not lcsc:
                raise SystemExit('no LCSC code for ' + ps[0].ref)
            w.writerow([val, ','.join(sorted((p.ref for p in ps), key=ref_key)), fp.split(':')[-1], lcsc])
    with open(os.path.join(POUT, 'BOM-PCBWay.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Line#', 'Qty', 'Designator', 'MPN', 'Manufacturer', 'Description', 'Package', 'Type',
                    'LCSC (reference)', 'Notes'])
        line = 0
        for (val, fp, mpn, lcsc, dnp), ps in groups(True):
            if not (mpn and ps[0].mfr):
                raise SystemExit('no MPN / manufacturer for ' + ps[0].ref)
            line += 1
            typ = 'SMD + THT legs' if ps[0].ref == 'J1' else 'SMD'
            w.writerow([line, len(ps), ','.join(sorted((p.ref for p in ps), key=ref_key)), mpn, ps[0].mfr,
                        pcbway_desc(val, fp, ps), fp.split(':')[-1], typ, lcsc, NOTES.get(mpn, '')])
    return {p.ref for p in D.PARTS if p.bom and not p.dnp}


def pcbway_desc(val, fp, ps):
    """A line's description for PCBWay's sourcing: what the part is (kind, value, package), and its
    function only when every designator on the line shares it."""
    kind = KIND.get(ps[0].prefix)
    pkg = fp.split(':')[1]
    head = '%s %s %s' % (kind, val, pkg) if kind else '%s %s' % (val, pkg)
    descs = {p.desc for p in ps}
    return head + ('; ' + ps[0].desc if len(descs) == 1 and ps[0].desc else '')


def fab_numbers():
    """What the fab needs to know, read from the board itself."""
    import pcbnew
    b = pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(PCB, None)
    bb = b.GetBoardEdgesBoundingBox()
    lw = max(d.GetWidth() for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts)
    tr = [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T]
    vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    small = min(vias, key=lambda v: v.GetDrill())
    k1 = b.FindFootprintByReference('K1')
    return dict(w=(bb.GetWidth() - lw) / 1e6, h=(bb.GetHeight() - lw) / 1e6, track=min(t.GetWidth() for t in tr) / 1e6,
                vd=small.GetDrill() / 1e6, vp=small.GetWidth(pcbnew.F_Cu) / 1e6, nvia=len(vias),
                thick=b.GetDesignSettings().GetBoardThickness() / 1e6,
                nfinger=sum(1 for p in k1.Pads()), clear=0.107)


def order_docs():
    f = fab_numbers()
    n_parts = len([p for p in D.PARTS if p.bom and not p.dnp])
    src = os.path.join(DOCS, 'sourcing.md')
    stock = (open(src).readline().strip('# \n').split('(')[-1].rstrip(')') if os.path.exists(src) else 'build day')
    v = dict(f, prj=D.PROJECT, n=n_parts, stock=stock, nlines=len(groups(True)),
             ntp=len([p for p in D.PARTS if p.prefix == 'TP']))
    common = """## Before ordering (VERIFY)

1. **The options Yannick has not stated.** His EasyEDA files give the copper, the masks, the paste,
   the silkscreen and the drills, not the order options: the finish, the gold fingers and the bevel
   below are the house recommendation for a cartridge edge. Confirm them with Yannick Erb.
2. **The paste on the gold fingers.** His paste layers open every finger (22 on F.Paste, 22 on
   B.Paste), and so do these gerbers (they equal his). A stencil cut from them prints solder paste on
   the top fingers. Ask the fab to leave the fingers out of the stencil (or confirm with Yannick how
   his boards were built).
3. **Spacing below the fab's standard figures** (Yannick's own EasyEDA rule is 0.1016 mm): six spots
   at 0.107-0.121 mm in the RP2354A's and the CP2102N's fan-out, and %(nvia)d vias of which the small
   ones are %(vd).3f mm drill / %(vp).3f mm pad (a 0.1015 mm ring). See README "Design rules".
4. **Stock** (`python3 tools/audit/sourcing.py`; `docs/sourcing.md`, %(stock)s).

## Board options

| Option | Value |
|---|---|
| Layers | 2 |
| Size | %(w).1f x %(h).1f mm (the whole 58.2 mm bottom edge is the insertion edge) |
| Thickness | %(thick).1f mm |
| Surface finish | ENIG (recommended; not stated by Yannick) |
| Gold fingers | hard gold on the %(nfinger)d fingers (22 on each face, 2.54 mm pitch), 30 degree bevel on the insertion edge (recommended; not stated by Yannick) |
| Minimum track / clearance | %(track).3f mm / %(clear).3f mm (six spots; 0.127 mm everywhere else) |
| Smallest via | %(vd).3f mm drill / %(vp).3f mm pad |
| Solder mask / silkscreen | any colour; white silk |

""" % v
    look = """   - U1 (RP2354A, QFN-60 0.4 mm), U3 (CP2102N, QFN-28), U7 (ESP32-S3-WROOM-1: the antenna overhangs the
     top edge), U2 (AP63203, TSOT-26), Q1 / Q3 / Q4 (BC847BT, SOT-523), Q2 (UMH3N, SOT-363), U5 (crystal),
     U8 (microSD, top-right), J1 (USB-C, top-left): pin 1 / orientation against the silkscreen.
   - D1 / D2 (SS34), D3-D5 (ESD5Z), C29 (electrolytic), D6 (SK6805-EC20): polarity / pin 1."""
    jlc = """# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/gerber_equiv.py`:

- `%(prj)s-gerbers.zip`: gerbers + Excellon drill, equal to Yannick Erb's own set. Its bottom
  silkscreen carries the order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a
  location"** for the order number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part # (Yannick's LCSC codes).
- `CPL-JLCPCB.csv`: positions and rotations, equal to Yannick's own pick-and-place file (his
  footprints are LCSC's, so no correction applies).

""" % v + common + """## Assembly

Top side only (B.Cu carries the odd fingers and copper). %(n)d parts per board on %(nlines)d BOM lines.
The %(ntp)d test pads are bare copper; the edge and the two holes are not parts.

1. Upload the zip; set the options above.
2. **PCB Assembly: Standard** (the RP2354A is 0.4 mm pitch, and gold fingers need Standard). Top side.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part.
4. **Stencil / paste:** see "The paste on the gold fingers" above.
5. **Placement preview, before paying:**
""" % v + look + "\n"
    pcbway = """# Ordering at PCBWay

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `%(prj)s-gerbers.zip`: gerbers + Excellon drill (no order-number text), equal to Yannick Erb's own set.
- `BOM-PCBWay.csv`: Line#, Qty, Designator, MPN, Manufacturer, Description, Package, Type, the
  LCSC code for reference, Notes.
- `Centroid-PCBWay.csv`: KiCad's centres and rotations (the same as the JLCPCB CPL).
- `Assembly-top.pdf`: references and pin-1 marks on the outline.

""" % v + common + """### PCBWay specifics

1. PCB: the options above; ask for **hard gold fingers with a 30 degree bevel** on the insertion edge.
2. Assembly: **turnkey**, top side. PCBWay sources every line by MPN.
3. Upload `BOM-PCBWay.csv`, `Centroid-PCBWay.csv` and `Assembly-top.pdf`.
4. In the order notes: "Gold fingers: hard gold, 30 degree bevel on the 58.2 mm bottom edge only. No
   solder paste on the gold fingers. Check the orientation of the ICs and the polarity of the diodes
   and the LED against Assembly-top.pdf:
""" % v + look + '"\n'
    open(os.path.join(JOUT, 'ORDER-JLCPCB.md'), 'w').write(jlc)
    open(os.path.join(POUT, 'ORDER-PCBWay.md'), 'w').write(pcbway)


def positions():
    pos = tmp('pos.csv')
    run('kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
        '--exclude-dnp', '--use-drill-file-origin', '-o', pos, PCB)
    return list(csv.DictReader(open(pos)))


def placements(bom_refs, rows):
    seen = set()
    with open(os.path.join(JOUT, 'CPL-JLCPCB.csv'), 'w', newline='') as fj, \
            open(os.path.join(POUT, 'Centroid-PCBWay.csv'), 'w', newline='') as fp:
        wj, wp = csv.writer(fj), csv.writer(fp)
        wj.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        wp.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation', 'Footprint', 'Value'])
        for r in sorted(rows, key=lambda r: ref_key(r['Ref'])):
            ref = r['Ref']
            if ref not in bom_refs:
                continue
            if r['Side'] != 'top':
                raise SystemExit('%s is on the bottom' % ref)
            x, y, rot = float(r['PosX']), float(r['PosY']), float(r['Rot']) % 360
            wj.writerow([ref, '%.4fmm' % x, '%.4fmm' % y, 'Top', '%g' % rot])
            wp.writerow([ref, '%.4fmm' % x, '%.4fmm' % y, 'Top', '%g' % rot, r['Package'], r['Val']])
            seen.add(ref)
    missing = bom_refs - seen
    if missing:
        raise SystemExit('BOM parts missing from the placement file: ' + ' '.join(sorted(missing)))
    return len(seen)


def jlc_board():
    """A copy of the board with the order-number text on the silkscreen (JLC_ORDER), for the JLCPCB zip."""
    from sexpr import parse, dump, Q
    (x, y), h, side = JLC_ORDER
    t = parse(open(PCB).read())
    eff = ['effects', ['font', ['size', h, h], ['thickness', 0.15]]] + ([['justify', 'mirror']] if side == 'B' else [])
    t.append(['gr_text', Q(JLC_TEXT), ['at', x, y, 0], ['layer', Q('%s.SilkS' % side)],
              ['uuid', Q('6a1c0000-0000-4000-8000-0000000a2001')], eff])
    d = tmp('jlc-board')                      # same file name as the board, so the plot names match
    os.makedirs(d, exist_ok=True)
    fn = os.path.join(d, D.PROJECT + '.kicad_pcb')
    open(fn, 'w').write(dump(t) + '\n')
    for ext in ('.kicad_pro', '.kicad_dru'):
        shutil.copy(os.path.join(PRJ, D.PROJECT + ext), os.path.join(d, D.PROJECT + ext))
    return fn


def plot(board, zf):
    g = tmp('gerbers')
    shutil.rmtree(g, ignore_errors=True)
    os.makedirs(g)
    # the saved fills, as they are: no --check-zones (it refills), and his silkscreen is not clipped
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', GERBER_LAYERS, '--no-protel-ext',
        '--use-drill-file-origin', '-o', g + '/', board)
    run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
        '--excellon-units', 'mm', '--drill-origin', 'plot', '--generate-map', '--map-format', 'gerberx2',
        '-o', g + '/', board)
    with zipfile.ZipFile(zf, 'w', zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(g)):
            data = open(os.path.join(g, fn), 'rb').read()
            # KiCad stamps the plot date / time: a fixed one keeps the zip diffable
            data = re.sub(rb'(CreationDate,)[^*\n]*', rb'\g<1>2026-11-04T00:00:00', data)
            data = re.sub(rb'(; DRILL file .*? date )\S+', rb'\g<1>2026-11-04T00:00:00', data)
            data = re.sub(rb'("CreationDate":\s*")[^"]*', rb'\g<1>2026-11-04T00:00:00', data)
            data = re.sub(rb'(G04 Created by KiCad \([^)]*\) date )[^*]*', rb'\g<1>2026-11-04 00:00:00', data)
            z.writestr(zipfile.ZipInfo(fn, date_time=(2026, 11, 4, 0, 0, 0)), data, zipfile.ZIP_DEFLATED)
    shutil.rmtree(g)


def gerbers():
    jb = jlc_board()
    zf = os.path.join(JOUT, D.PROJECT + '-gerbers.zip')
    plot(jb, zf)
    shutil.rmtree(os.path.dirname(jb))
    plot(PCB, os.path.join(POUT, D.PROJECT + '-gerbers.zip'))
    return zf


def assembly():
    for out in (os.path.join(DOCS, 'assembly-top.pdf'), os.path.join(POUT, 'Assembly-top.pdf')):
        run('kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'F.Fab,F.SilkS,Edge.Cuts', '--mode-single',
            '--include-border-title', '-o', out, PCB)


def sch_docs():
    os.makedirs(DOCS, exist_ok=True)
    run('kicad-cli', 'sch', 'export', 'pdf', '-o', os.path.join(DOCS, D.PROJECT + '-schematic.pdf'), SCH)


def pcb_docs():
    run('kicad-cli', 'pcb', 'export', 'svg', '--layers', 'F.Cu,F.SilkS,F.Mask,Edge.Cuts', '--mode-single',
        '--fit-page-to-board', '-o', os.path.join(DOCS, 'layout-front.svg'), PCB)
    run('kicad-cli', 'pcb', 'export', 'svg', '--layers', 'B.Cu,B.SilkS,B.Mask,Edge.Cuts', '--mode-single',
        '--mirror', '--fit-page-to-board', '-o', os.path.join(DOCS, 'layout-back.svg'), PCB)
    for fn in ('layout-front.svg', 'layout-back.svg'):      # a fixed date in the title keeps them diffable
        f = os.path.join(DOCS, fn)
        open(f, 'w').write(re.sub(r'(<title>SVG Image created as \S+ date )[^ <]*', r'\g<1>2026-11-04T00:00:00',
                                  open(f).read(), count=1))
    for side, fn in (('top', 'board-top.png'), ('bottom', 'board-bottom.png')):
        run('kicad-cli', 'pcb', 'render', '--side', side, '--width', '1400', '--height', '1440',
            '--quality', 'high', '--background', 'opaque', '-o', os.path.join(DOCS, fn), PCB)


def main():
    os.makedirs(JOUT, exist_ok=True)
    os.makedirs(POUT, exist_ok=True)
    refs = boms()
    sch_docs()
    order_docs()
    n = placements(refs, positions())
    zf = gerbers()
    assembly()
    pcb_docs()
    print('BOM (%d lines): %d placed refs; CPL / centroid: %d rows; %s' % (
        len(groups(False)), len(refs), n, os.path.relpath(zf, PRJ)))


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        print(e, flush=True)
        os._exit(1 if e.code else 0)
    sys.stdout.flush()
    os._exit(0)
