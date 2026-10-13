#!/usr/bin/env python3
"""Fabrication + documentation outputs for FujiNet-5200 Rev0, for JLCPCB and for PCBWay.

Always (from the schematic / design.py):
  FujiNet-5200-Rev0-BOM.csv                   full BOM with MPN, manufacturer, LCSC (DNP flagged)
  exports/jlcpcb/BOM-JLCPCB.csv                Comment,Designator,Footprint,LCSC Part # (no DNP parts)
  exports/pcbway/BOM-PCBWay.csv                Line#,Qty,Designator,MPN,Manufacturer,Description,Package,Type
  exports/jlcpcb/consigned.csv                 the lines to consign to JLCPCB (only if CONSIGN lists any)
  docs/FujiNet-5200-Rev0-schematic.pdf

Only once FujiNet-5200-Rev0.kicad_pcb exists:
  exports/jlcpcb/CPL-JLCPCB.csv                Designator,Mid X,Mid Y,Layer,Rotation (JLC-corrected)
  exports/jlcpcb/FujiNet-5200-Rev0-gerbers.zip gerbers + Excellon drill, F.Silkscreen with the order-number text
  exports/pcbway/Centroid-PCBWay.csv           Designator,Mid X,Mid Y,Layer,Rotation (KiCad's own)
  exports/pcbway/FujiNet-5200-Rev0-gerbers.zip the same gerbers without it
  exports/pcbway/Assembly-top.pdf              F.Fab + F.Silkscreen + outline: references, pin 1
  docs/layout-front.svg, docs/layout-back.svg, docs/board-top.png, docs/board-bottom.png

CPL rotations and origins (JLCPCB only): JLCPCB places each part by the EasyEDA footprint of
its LCSC code.  tools/audit/jlc/jlc_rotations.json holds, per footprint, the rotation
correction and the origin offset measured by comparing every one of our footprints with that
EasyEDA footprint pad by pad (polarity by cathode marks, not pad numbers); the CPL applies them.
Still check the placement preview on JLCPCB's order page before paying.  PCBWay places by our
footprints and the assembly drawing, so its centroid carries KiCad's rotations unchanged --
never the JLC-corrected ones.

Usage: python3 tools/export.py
"""
import csv, json, math, os, re, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tmpdir import tmp
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
SCH = os.path.join(PRJ, D.PROJECT + '.kicad_sch')
JOUT = os.path.join(PRJ, 'exports', 'jlcpcb')
POUT = os.path.join(PRJ, 'exports', 'pcbway')
DOCS = os.path.join(PRJ, 'docs')

JLC = {}     # (footprint, LCSC) -> (rotation correction deg, origin offset (dx, dy) mm in the footprint frame, confidence)
for _e in json.load(open(os.path.join(HERE, 'audit', 'jlc', 'jlc_rotations.json'))):
    JLC[(_e['footprint'], _e['lcsc'])] = (_e['rotation_correction_deg'], tuple(_e['origin_offset_mm']),
                                          _e.get('confidence', ''))
THT = re.compile(r'PinHeader|TestPoint_THT')
ref_key = lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit('failed: ' + ' '.join(a))
    return r.stdout


def groups():
    g = {}
    for p in D.PARTS:
        if p.bom:
            g.setdefault((p.value, p.footprint, p.mpn, p.mfr, p.lcsc, p.dnp), []).append(p)
    return sorted(g.items(), key=lambda kv: ref_key(kv[1][0].ref))


KIND = {'R': 'Resistor', 'RN': 'Resistor array', 'C': 'Capacitor', 'L': 'Inductor', 'Y': 'Crystal',
        'SW': 'Tactile switch', 'J': 'Connector'}


def pcbway_desc(val, fp, ps):
    """A line's description for PCBWay's sourcing: what the part is (kind, value, package), and its
    function only when every designator on the line shares it -- a 26-capacitor line must not read
    as 'IOVDD decoupling'."""
    pkg = re.sub(r'_\d+Metric$', '', fp.split(':')[1])
    kind = KIND.get(ps[0].prefix)
    head = '%s %s %s' % (kind, val, pkg) if kind else '%s %s' % (val, pkg)
    descs = {p.desc for p in ps}
    return head + ('; ' + ps[0].desc if len(descs) == 1 and ps[0].desc else '')


def boms():
    rows = groups()
    refs = lambda ps: ','.join(sorted((p.ref for p in ps), key=ref_key))
    with open(os.path.join(PRJ, D.PROJECT + '-BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(['Refs', 'Value', 'Footprint', 'MPN', 'Manufacturer', 'LCSC', 'Description', 'DNP'])
        for (val, fp, mpn, mfr, lcsc, dnp), ps in rows:
            w.writerow([refs(ps), val, fp.split(':')[1], mpn, mfr, lcsc, ps[0].desc, 'DNP' if dnp else ''])
    with open(os.path.join(JOUT, 'BOM-JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (val, fp, mpn, mfr, lcsc, dnp), ps in rows:
            if dnp:
                continue       # not assembled: the CPL export skips DNP parts too
            if not lcsc:
                raise SystemExit('no LCSC code for ' + ps[0].ref)
            w.writerow([val, refs(ps), fp.split(':')[1], lcsc])
    with open(os.path.join(POUT, 'BOM-PCBWay.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Line#', 'Qty', 'Designator', 'MPN', 'Manufacturer', 'Description', 'Package', 'Type',
                    'LCSC (reference)', 'Notes'])
        line = 0
        for (val, fp, mpn, mfr, lcsc, dnp), ps in rows:
            if dnp:
                continue
            if not (mpn and mfr):
                raise SystemExit('no MPN / manufacturer for ' + ps[0].ref)
            line += 1
            note = NOTES.get(mpn, '')
            w.writerow([line, len(ps), refs(ps), mpn, mfr, pcbway_desc(val, fp, ps), fp.split(':')[1],
                        'THT' if THT.search(fp) else 'SMD', lcsc, note])
    return {p.ref for p in D.PARTS if p.bom and not p.dnp}


# Not stocked by JLCPCB / LCSC (docs/sourcing.md): consign them, or let JLC's Global Sourcing or
# PCBWay's turnkey service buy them.  Every line was in JLCPCB stock on 2026-10-08.
CONSIGN = {}
# PCBWay BOM notes, by MPN
NOTES = {'RP2354B': 'RP2350B with 2 MB flash stacked in the package (QFN-80 10x10, 0.4 mm pitch): Raspberry Pi '
                    'distributors / LCSC C39843328',
         'SN74HCT541PWR': 'TSSOP-20; HCT (TTL-level inputs) required: the RP2354B drives its A inputs at 3.3 V',
         'SN74HCT08DR': 'HCT required (TTL-level inputs)', 'SN74HCT14DR': 'HCT required (TTL-level inputs)',
         'AOTA-B201610S3R3-101-T': 'the inductor the RP2350 datasheet specifies for its core regulator; no substitute',
         '1206L035/30WR': 'PTC, 0.35 A hold / 30 V: a 1206 PTC of another make with the same hold current and >= 24 V is fine'}


def consigned():
    """exports/jlcpcb/consigned.csv: what to buy and ship to JLCPCB for 5 boards, a spare per line
    (not written when nothing needs consigning)."""
    fn = os.path.join(JOUT, 'consigned.csv')
    if not CONSIGN:
        if os.path.exists(fn):
            os.remove(fn)
        return 0
    n = 0
    with open(fn, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'MPN', 'Manufacturer', 'LCSC (for the BOM match)', 'Per board',
                    'For 5 boards + 1 spare', 'Where', 'Description'])
        for (val, fp, mpn, mfr, lcsc, dnp), ps in groups():
            if mpn in CONSIGN and not dnp:
                w.writerow([','.join(sorted((p.ref for p in ps), key=ref_key)), mpn, mfr, lcsc, len(ps),
                            5 * len(ps) + 1, CONSIGN[mpn], pcbway_desc(val, fp, ps)])
                n += 1
    return n


def fab_numbers():
    """What the fab needs to know, read from the board itself: outline size, the narrowest
    track, the smallest via, the number of vias in pads of the RP2354B's exposed pad."""
    from sexpr import parse, find, findall
    import edge_geom as EG
    t = parse(open(PCB).read())
    xs, ys = [], []
    for g in findall(t, 'gr_line') + findall(t, 'gr_rect') + findall(t, 'gr_arc'):
        if find(g, 'layer')[1] in ('Edge.Cuts', '"Edge.Cuts"'):
            for k in ('start', 'end', 'mid'):
                e = find(g, k)
                if e:
                    xs.append(float(e[1]))
                    ys.append(float(e[2]))
    widths = [float(find(s_, 'width')[1]) for s_ in findall(t, 'segment')]
    vias = [(float(find(v, 'size')[1]), float(find(v, 'drill')[1])) for v in findall(t, 'via')]
    rules = json.load(open(os.path.join(PRJ, D.PROJECT + '.kicad_pro')))['board']['design_settings']['rules']
    return dict(w=max(xs) - min(xs), h=max(ys) - min(ys), track=min(widths), via=min(vias),
                nvia=len(vias), clear=rules['min_clearance'], tab=EG.TAB_W, tab_d=EG.TAB_D,
                thick=EG.THICKNESS, land0=EG.LAND_Y0, land0s=EG.LAND_Y0_SHORT)


def order_docs():
    """exports/jlcpcb/ORDER-JLCPCB.md and exports/pcbway/ORDER-PCBWay.md: the order, step by step,
    with the references from design.py and the numbers from the board."""
    k = D.KEY
    rs = lambda *keys: ', '.join(sorted((k[x] for x in keys), key=ref_key))
    dnp = ', '.join(sorted((p.ref for p in D.PARTS if p.bom and p.dnp), key=ref_key))
    f = fab_numbers() if os.path.exists(PCB) else None
    if f:
        size = '%.1f x %.1f mm (a T: the %.1f mm tab, %.1f mm deep, under a 61 mm lower body and the %.0f mm wide top)' % (
            f['w'], f['h'], f['tab'], f['tab_d'], f['w'])
        rules = ("%.2f mm / %.2f mm (the RP2354B's 0.4 mm pitch); smallest via %.2f mm drill / %.2f mm pad"
                 % (f['track'], f['clear'], f['via'][1], f['via'][0]))
        thick, l0, l0s, tab = f['thick'], f['land0'], f['land0s'], f['tab']
    else:
        size, rules, thick, l0, l0s, tab = '(route the board first)', '(route the board first)', 1.6, 0.6, 1.9, 47.8
    src = os.path.join(DOCS, 'sourcing.md')
    stock = (open(src).readline().strip('# \n').split('(')[-1].rstrip(')') if os.path.exists(src) else 'build day')
    common = """## Before ordering (VERIFY)

1. **The tab.** Print `docs/tab-overlay-1to1.pdf` at 100 %% (no fit-to-page) and check its 50 mm ruler.
   Lay a real Atari 5200 cartridge board on the fingers: pins 1-18 on the label side, pin 1 (D0) at
   the left seen from the label with the fingers down; the finger span, the tab width (%.1f mm) and
   the two short fingers (pins 18 / 36, the interlock) must match.
2. **The thickness.** The console connector takes 1.57 +/- 0.2 mm; %.1f mm is ordered.
3. **Stock.** `python3 tools/audit/sourcing.py` (or read `docs/sourcing.md`, %s): every line was in
   JLCPCB stock when this was written.
4. **The jumpers.** JP%s (interlock 18-36) and JP%s (edge 11 raw DC) are bridged copper: leave them.

## Board options (both fabs)

| Option | Value |
|---|---|
| Layers | 6 (stack: F.Cu, In1 GND, In2, In3, In4 power, B.Cu) |
| Size | %s |
| Thickness | %.1f mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold, **30-45 degree bevel** on the tab's insertion edge (the %.1f mm bottom edge) only |
| Minimum track / clearance | %s |
| Via in pad | the vias in the RP2354B's exposed pad: filled and capped |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | if asked for: on the left and right edges of the wide top only. Never on the tab or the lower body, and never on the top edge (USB-C, microSD, antenna) |

## Assembly

Top side only (B.Cu has no parts). %d parts per board.  Not fitted (DNP, left off the BOM and the
CPL): %s -- the firmware-controlled interlock switch and the RP's debug-UART header.
""" % (tab, thick, stock, k['JP_ILK'][2:], k['JP_UNREG'][2:], size, thick, tab, rules,
       len([p for p in D.PARTS if p.bom and not p.dnp]), dnp)
    look = """   - %s (RP2354B), %s (ESP32-S3), %s (CP2102N), %s (USB-C), %s (microSD), %s (74HCT541,
     TSSOP-20), %s (74HCT08 / '14, SOIC-14), %s (74LVC1G17, SOT-353), %s (AP63205 / AP63203,
     TSOT-23-6), %s (AP2112K, SOT-23-5): pin 1 / orientation against the silkscreen.
   - %s (WS2812B), %s (BAT54C), %s (UMH3N), %s (SS34), %s (red LED), %s (ESD5Z): polarity.""" % (
        k['U_RP'], k['U_S3'], k['U_UART'], k['J_USB'], k['J_SD'], k['U_BUF'], rs('U_AND', 'U_INV'),
        k['U_PHI2'], rs('U_PRE', 'U_BUCK'), k['U_LDO'], k['D_WS'], rs('D_RST', 'D_OFF'), k['U_AUTOPROG'],
        rs('D_VBUS', 'D_PRE'), k['D_LED'], rs('D_ESDP', 'D_ESDM', 'D_ESDV'))
    jlc = """# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `%s-gerbers.zip`: gerbers + Excellon drill. Its top silkscreen carries the
  order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order
  number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

%s
### JLCPCB specifics

1. Upload the zip; set the options above. JLCPCB fills and caps via-in-pad on 6 layers at no charge.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm).
   Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2354B, the S3 module, the logic, the regulators) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
%s
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start %.1f mm from the
   edge and pins 18 / 36 only %.1f mm in, on purpose (the console's interlock makes last).
""" % (D.PROJECT, common, look, l0, l0s)
    pcbway = """# Ordering at PCBWay

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `%s-gerbers.zip`: gerbers + Excellon drill (no order-number text).
- `BOM-PCBWay.csv`: Line#, Qty, Designator, MPN, Manufacturer, Description, Package, Type, the
  LCSC code for reference, Notes.
- `Centroid-PCBWay.csv`: KiCad's own centres and rotations (PCBWay places by our footprints and
  the assembly drawing; never the JLC-corrected CPL).
- `Assembly-top.pdf`: references and pin-1 marks on the outline.

%s
### PCBWay specifics

1. PCB: the options above; ask for **hard gold fingers with bevel** and **resin-plugged, capped
   vias** under the RP2354B's exposed pad (note: "via-in-pad in %s EP, fill and cap").
2. Assembly: **turnkey**, top side, the quantity you need. PCBWay sources every line by MPN.
3. Upload `BOM-PCBWay.csv`, `Centroid-PCBWay.csv` and `Assembly-top.pdf`.
4. In the order notes: "Gold fingers: hard gold, 30-45 degree bevel on the %.1f mm tab edge only.
   Fingers 18 and 36 are deliberately shorter. Do not fit the DNP parts (%s). Check the
   orientation of the ICs and the polarity of the diodes against Assembly-top.pdf:
%s"
5. Approve PCBWay's engineering questions on the fingers (they start %.1f mm from the edge, pins
   18 / 36 at %.1f mm, on purpose) and the bevel.
""" % (D.PROJECT, common, k['U_RP'], tab, dnp, look, l0, l0s)
    open(os.path.join(JOUT, 'ORDER-JLCPCB.md'), 'w').write(jlc)
    open(os.path.join(POUT, 'ORDER-PCBWay.md'), 'w').write(pcbway)


def positions():
    pos = tmp('pos.csv')
    run('kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
        '--exclude-dnp', '-o', pos, PCB)
    return list(csv.DictReader(open(pos)))


def cpl(bom_refs, rows):
    seen, low = set(), set()
    with open(os.path.join(JOUT, 'CPL-JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in rows:
            ref = r['Ref']
            if ref not in bom_refs:
                continue
            rot = float(r['Rot'])
            part = D.BY_REF[ref]
            fpname = part.footprint.split(':')[1]
            if (fpname, part.lcsc) not in JLC:
                raise SystemExit('no JLC rotation/offset measured for %s %s' % (fpname, part.lcsc))
            corr, (dx, dy), conf = JLC[(fpname, part.lcsc)]
            if conf.startswith('low'):
                low.add(ref)
            if r['Side'] != 'top':
                raise SystemExit('%s is on the bottom: the measured corrections are for top-side parts' % ref)
            t = math.radians(rot)
            # the EasyEDA origin, in the .pos frame (Y up): footprint frame +y is down
            x = float(r['PosX']) + dx * math.cos(t) + dy * math.sin(t)
            y = float(r['PosY']) + dx * math.sin(t) - dy * math.cos(t)
            w.writerow([ref, '%.4fmm' % x, '%.4fmm' % y, 'Top', '%g' % ((rot + corr) % 360)])
            seen.add(ref)
    missing = bom_refs - seen
    if missing:
        raise SystemExit('BOM parts missing from the placement file: ' + ' '.join(sorted(missing)))
    if low:
        print('CPL: low-confidence rotation for %s (no EasyEDA footprint for its LCSC part): '
              'check it in JLCPCB\'s placement preview' % ' '.join(sorted(low)))
    return len(seen)


def centroid(bom_refs, rows):
    """PCBWay: KiCad's footprint centres and rotations, unmodified (they place by our footprints
    and the assembly drawing)."""
    n = 0
    with open(os.path.join(POUT, 'Centroid-PCBWay.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation', 'Footprint', 'Value'])
        for r in rows:
            if r['Ref'] not in bom_refs:
                continue
            w.writerow([r['Ref'], '%.4fmm' % float(r['PosX']), '%.4fmm' % float(r['PosY']),
                        'Top' if r['Side'] == 'top' else 'Bottom', '%g' % float(r['Rot']),
                        r['Package'], r['Val']])
            n += 1
    return n


JLC_TEXT = 'JLCJLCJLCJLC'      # JLCPCB prints its order number here ("specify a location" on the order page)


def jlc_board():
    """A copy of the board with the order-number text on F.Silkscreen at placement.JLC_ORDER (a
    clear spot: tools/audit/check_fab.py checks it), for the JLCPCB zip only."""
    import placement as PL
    from sexpr import parse, dump, Q
    (x, y), h = PL.JLC_ORDER
    t = parse(open(PCB).read())
    t.append(['gr_text', Q(JLC_TEXT), ['at', x, y, 0], ['layer', Q('F.SilkS')],
              ['uuid', Q('6a1c0000-0000-4000-8000-0000000001c0')],
              ['effects', ['font', ['size', h, h], ['thickness', 0.15]]]])
    d = tmp('jlc-board')                      # same file name as the board, so the plot names match
    os.makedirs(d, exist_ok=True)
    fn = os.path.join(d, D.PROJECT + '.kicad_pcb')
    open(fn, 'w').write(dump(t) + '\n')
    return fn


def gerbers():
    g = tmp('gerbers')
    shutil.rmtree(g, ignore_errors=True)
    os.makedirs(g)
    layers = 'F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', layers, '--subtract-soldermask',
        '--no-protel-ext', '-o', g + '/', PCB)
    run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
        '--generate-map', '--map-format', 'gerberx2', '-o', g + '/', PCB)
    # the JLCPCB set: the same files, but F.Silkscreen from the copy carrying the order-number text
    gj = tmp('gerbers-jlc')
    shutil.rmtree(gj, ignore_errors=True)
    os.makedirs(gj)
    jb = jlc_board()
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', 'F.SilkS', '--subtract-soldermask',
        '--no-protel-ext', '-o', gj + '/', jb)
    silk = [fn for fn in os.listdir(gj) if fn.endswith('F_Silkscreen.gbr')]
    assert len(silk) == 1 and silk[0] in os.listdir(g), (os.listdir(gj), sorted(os.listdir(g)))
    out = []
    for d in (JOUT, POUT):
        zf = os.path.join(d, D.PROJECT + '-gerbers.zip')
        with zipfile.ZipFile(zf, 'w', zipfile.ZIP_DEFLATED) as z:
            for fn in sorted(os.listdir(g)):
                src = os.path.join(gj, fn) if d == JOUT and fn in silk else os.path.join(g, fn)
                z.writestr(fn, open(src, 'rb').read())
        out.append(zf)
    shutil.rmtree(g)
    shutil.rmtree(gj)
    shutil.rmtree(os.path.dirname(jb))
    return out


def assembly():
    run('kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'F.Fab,F.SilkS,Edge.Cuts', '--mode-single',
        '--include-border-title', '-o', os.path.join(POUT, 'Assembly-top.pdf'), PCB)


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
    os.makedirs(JOUT, exist_ok=True)
    os.makedirs(POUT, exist_ok=True)
    refs = boms()
    consigned()
    order_docs()
    sch_docs()
    if not os.path.exists(PCB):
        print('BOM: %d placed refs; schematic PDF written. No %s yet: CPL, gerbers and layout '
              'renders skipped.' % (len(refs), os.path.basename(PCB)))
        return
    rows = positions()
    n = cpl(refs, rows)
    m = centroid(refs, rows)
    zf = gerbers()
    assembly()
    pcb_docs()
    print('BOM: %d placed refs; JLC CPL: %d rows; PCBWay centroid: %d rows; %s' %
          (len(refs), n, m, ', '.join(os.path.relpath(z, PRJ) for z in zf)))


if __name__ == '__main__':
    main()
