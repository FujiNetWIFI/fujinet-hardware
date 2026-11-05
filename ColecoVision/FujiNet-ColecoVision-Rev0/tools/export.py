#!/usr/bin/env python3
"""Fabrication + documentation outputs for FujiNet-ColecoVision Rev0, for JLCPCB and for PCBWay.

Always (from the schematic / design.py):
  FujiNet-ColecoVision-Rev0-BOM.csv            full BOM with MPN, manufacturer, LCSC and description (DNP flagged)
  exports/jlcpcb/BOM-JLCPCB.csv                Comment,Designator,Footprint,LCSC Part # (no DNP / no-BOM parts)
  exports/pcbway/BOM-PCBWay.csv                Line#,Qty,Designator,MPN,Manufacturer,Description,Package,Type
  docs/FujiNet-ColecoVision-Rev0-schematic.pdf

Once FujiNet-ColecoVision-Rev0.kicad_pcb exists:
  exports/jlcpcb/CPL-JLCPCB.csv                Designator,Mid X,Mid Y,Layer,Rotation (JLC-corrected)
  exports/jlcpcb/FujiNet-ColecoVision-Rev0-gerbers.zip   gerbers + Excellon, the order-number text on B.Silkscreen
  exports/jlcpcb/ORDER-JLCPCB.md               the order, step by step, numbers from the board
  exports/pcbway/Centroid-PCBWay.csv           Designator,Mid X,Mid Y,Layer,Rotation (KiCad's own)
  exports/pcbway/FujiNet-ColecoVision-Rev0-gerbers.zip   the same gerbers without the order-number text
  exports/pcbway/Assembly-top.pdf              F.Fab + F.Silkscreen + outline: references, pin 1
  exports/pcbway/ORDER-PCBWay.md
  docs/assembly-top.pdf, docs/layout-front.svg, docs/layout-back.svg, docs/board-top.png, docs/board-bottom.png

While tools/edge_geom.VERIFIED is False the ORDER files open with DO NOT ORDER and
tools/audit/check_fab.py fails (it is True: the edge is checked against MAME's table and two built carts).

CPL rotations and origins: JLCPCB places each part by the EasyEDA footprint of its LCSC code.
tools/audit/jlc/jlc_rotations.json holds, per (footprint, LCSC code), the rotation correction and
the origin offset measured by comparing our footprint with that EasyEDA footprint pad by pad
(tools/audit/jlc/measure_rotations.py); the CPL applies them.  PCBWay places by our footprints and the
assembly drawing: its centroid file is KiCad's own.  Still check the placement preview before paying.

Usage: python3 tools/export.py
"""
import csv, json, math, os, re, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tmpdir import tmp
import design as D
import edge_geom as EG

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
ref_key = lambda r: (re.sub(r'\d', '', r), int(re.sub(r'\D', '', r) or 0))


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


def boms():
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
            w.writerow([line, len(ps), ','.join(sorted((p.ref for p in ps), key=ref_key)), mpn, ps[0].mfr,
                        pcbway_desc(val, fp, ps), fp.split(':')[-1], 'SMD', lcsc, NOTES.get(mpn, '')])
    return {p.ref for p in D.PARTS if p.bom and not p.dnp}


KIND = {'R': 'Resistor', 'RN': 'Resistor array', 'C': 'Capacitor', 'L': 'Inductor', 'Y': 'Crystal',
        'SW': 'Tactile switch', 'J': 'Connector'}
# PCBWay BOM notes, by MPN
NOTES = {'RP2350A': 'Raspberry Pi RP2350A, QFN-60 7x7, 0.4 mm pitch (no stacked flash: the W25Q16JV is its boot flash)',
         'SN74LVC245APWR': 'LVC required: 5 V-tolerant inputs at 3.3 V (not HC / HCT)',
         'SN74LVC1G11DBVR': 'LVC required: 5 V-tolerant inputs at 3.3 V',
         'SN74LVC1G08DBVR': 'LVC required: 5 V-tolerant inputs at 3.3 V',
         'AOTA-B201610S3R3-101-T': 'the inductor the RP2350 datasheet specifies for its core regulator; '
                                   'TDK VLS201610HBX-3R3M-1 is the only accepted alternate'}


def pcbway_desc(val, fp, ps):
    """A line's description for PCBWay's sourcing: what the part is (kind, value, package), and its
    function only when every designator on the line shares it."""
    pkg = re.sub(r'_\d+Metric$', '', fp.split(':')[1])
    kind = KIND.get(ps[0].prefix)
    head = '%s %s %s' % (kind, val, pkg) if kind else '%s %s' % (val, pkg)
    descs = {p.desc for p in ps}
    return head + ('; ' + ps[0].desc if len(descs) == 1 and ps[0].desc else '')


def fab_numbers():
    """What the fab needs to know, read from the board itself: outline size, the narrowest track,
    the smallest via."""
    from sexpr import parse, find, findall
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
                nvia=len(vias), clear=rules['min_clearance'], thick=EG.THICKNESS, land0=EG.LAND_Y0,
                land1=EG.LAND_Y1, finger=EG.LAND_W, parts=EG.PARTS_Y, pitch=EG.PITCH)


DO_NOT_ORDER = """> **DO NOT ORDER YET.** `tools/edge_geom.VERIFIED` is False: the edge no longer matches the
> sources `tools/audit/edge_orientation.py` checks it against. `tools/audit/check_fab.py` fails until
> it does.

"""


def order_docs():
    """exports/jlcpcb/ORDER-JLCPCB.md and exports/pcbway/ORDER-PCBWay.md: the order, step by step, with the
    references from design.py and the numbers from the board."""
    k = D.KEY
    rs = lambda *keys: ', '.join(sorted((k[x] for x in keys), key=ref_key))
    dnp = ', '.join(sorted((p.ref for p in D.PARTS if p.bom and p.dnp), key=ref_key)) or 'none'
    f = fab_numbers()
    src = os.path.join(DOCS, 'sourcing.md')
    stock = (open(src).readline().strip('# \n').split('(')[-1].rstrip(')') if os.path.exists(src) else 'build day')
    n_parts = len([p for p in D.PARTS if p.bom and not p.dnp])
    v = dict(prj=D.PROJECT, thick=f['thick'], stock=stock, w=f['w'], h=f['h'], pitch=f['pitch'],
             track=f['track'], clear=f['clear'], vd=f['via'][1], vp=f['via'][0], n=n_parts, dnp=dnp,
             land0=f['land0'], land1=f['land1'], finger=f['finger'], parts=f['parts'], land30=EG.land_y0('30'),
             rp=k['U_RP'], ldo=k['U_LDO'], s3=k['U_S3'], mux=k['U_MUX'], buck=k['U_BUCK'], uart=k['U_UART'],
             esd=k['U_ESD'], auto=k['U_AUTOPROG'], rst=k['D_RST'], sd=k['J_SD'], ws=k['D_WS'],
             buf=k['U_BUF'], and3=k['U_AND3'], and2=k['U_AND2'], fl=k['U_FLASH'],
             ntp=len([p for p in D.PARTS if p.prefix == 'TP']),
             usb=k['J_USB'], y=k['Y_XTAL'], led=k['D_LED'], l=k['L_VREG'],
             corner=rs('C_VIN', 'C_VOUT', 'C_FILT', 'R_FILT', 'R_USBP', 'R_USBM', 'C_OTP'))
    common = """## Before ordering (VERIFY)

1. **The edge.** `tools/audit/edge_orientation.py` passes: the pinout (MAME's ColecoVision slot table =
   the ADAM Technical Reference Manual's J1) and the footprint against two built, open carts
   (ThatOldNerd's Coleco-Game-Cart V4, Commodore-Bench's flash card): even pins on the component face,
   odd pins behind them, pin 1 / 2 at the left, %(pitch).2f mm pitch.
2. **The shell.** The outline is the open carts' (40.0-40.6 mm wide, their notch positions); the 82.4 mm
   length is proven only in printed shells. Fit an original Coleco shell only after the checks in
   the README ("Original shell"); the printed shell (`case/`) is made for this board.
3. **Stock** (`python3 tools/audit/sourcing.py` re-reads it; `docs/sourcing.md`, %(stock)s). The RP2350
   core inductor %(l)s, AOTA-B201610S3R3-101-T (C42411119), swings between in stock and none (1 at
   JLCPCB on 2026-11-04). For a short line, buy it into your JLCPCB parts inventory first (Parts
   Manager, "Order parts", from LCSC) or consign it. Its alternate is TDK VLS201610HBX-3R3M-1 (C695624,
   same 2016 size; Raspberry Pi specifies the polarity-marked AOTA). The RP2354A / RP2354B were out of
   stock everywhere on 2026-11-04: this board uses the RP2350A (C42411118) + W25Q16JVUXIQ (C2843335).
4. **The thickness.** %(thick).1f mm is ordered: the slot (Sullins EBC15DRTH replacement) takes 1.57 +- 0.2 mm.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 +5V with +3V3 / +3V3_RP / DVDD / CONS_5V islands, B.Cu) |
| Size | %(w).2f x %(h).2f mm (the whole 40.2 mm bottom edge is the insertion edge) |
| Thickness | %(thick).1f mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 30 fingers (15 on each face, %(pitch).2f mm pitch), **30 degree bevel** on the insertion edge |
| Minimum track / clearance | %(track).2f mm / %(clear).2f mm (the RP2350A's 0.4 mm pitch); smallest via %(vd).2f mm drill / %(vp).2f mm pad (Raspberry Pi's QFN-60 land pattern) |
| Via in pad | the 3 x 3 vias in the RP2350A's exposed pad (Raspberry Pi's footprint) and the CP2102N's: plain, tented from B.Cu (no filling needed) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | the board is narrower than the 70 mm assembly minimum: let the fab add rails on the left and right edges only. Never on the insertion edge or the top edge (the USB-C, the microSD) |
| Outline | four side notches (the shell's ribs) and the chamfered finger corners: route them as drawn |

""" % v
    look = """   - %(rp)s (RP2350A, QFN-60), %(fl)s (W25Q16JV, USON-8), %(buf)s (74LVC245A, TSSOP-20), %(and3)s / %(and2)s
     (74LVC1G11 SOT-23-6 / 74LVC1G08 SOT-23-5), %(s3)s (ESP32-S3-WROOM-1: the antenna at the west edge),
     %(ldo)s (AP2112K, SOT-23-5), %(mux)s (TPS2116, SOT-583), %(buck)s (AP63203, TSOT-23-6), %(uart)s (CP2102N,
     QFN-28), %(esd)s (USBLC6, SOT-23-6), %(auto)s (UMH3N), %(rst)s (BAT54C), %(usb)s (USB-C, top edge),
     %(sd)s (microSD: the card slot in the top edge), %(y)s (crystal): pin 1 / orientation against the silkscreen.
   - %(led)s (red LED), %(ws)s (WS2812B-2020): polarity / pin 1.
   - The regulator corner beside the RP2350A: %(l)s (AOTA 2016), %(corner)s (0402, Raspberry Pi's
     minimal-design land pattern).""" % v
    jlc = ('' if EG.VERIFIED else DO_NOT_ORDER) + """# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `%(prj)s-gerbers.zip`: gerbers + Excellon drill. Its bottom silkscreen carries the order-number text
  `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

""" % v + common + """## Assembly

Top side only (B.Cu carries only the odd fingers and copper). %(n)d parts per board. Not fitted
(DNP): %(dnp)s. The %(ntp)d test pads are bare copper.

1. Upload the zip; set the options above.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2350A is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts add JLC's per-part loading fee.
4. **Placement preview, before paying:**
""" % v + look + """
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start %(land0).2f mm from
   the edge (the +5V finger, 30, at %(land30).2f mm: it mates last) and run to %(land1).2f mm, %(finger).2f mm
   wide, on both faces, on purpose; no part sits closer than %(parts).1f mm to that edge.
""" % v
    pcbway = ('' if EG.VERIFIED else DO_NOT_ORDER) + """# Ordering at PCBWay

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `%(prj)s-gerbers.zip`: gerbers + Excellon drill (no order-number text).
- `BOM-PCBWay.csv`: Line#, Qty, Designator, MPN, Manufacturer, Description, Package, Type, the
  LCSC code for reference, Notes.
- `Centroid-PCBWay.csv`: KiCad's own centres and rotations (PCBWay places by our footprints and
  the assembly drawing; never the JLC-corrected CPL).
- `Assembly-top.pdf`: references and pin-1 marks on the outline.

""" % v + common + """### PCBWay specifics

1. PCB: the options above; ask for **hard gold fingers with a 30 degree bevel** on the insertion edge.
2. Assembly: **turnkey**, top side, the quantity you need. PCBWay sources every line by MPN.
3. Upload `BOM-PCBWay.csv`, `Centroid-PCBWay.csv` and `Assembly-top.pdf`.
4. In the order notes: "Gold fingers: hard gold, 30 degree bevel on the 40.2 mm bottom edge only.
   Finger 30 is deliberately shorter. Check the orientation of the ICs and the polarity of the LEDs
   against Assembly-top.pdf:
""" % v + look + """"
5. Approve PCBWay's engineering questions on the fingers (they start %(land0).2f mm from the edge, pin
   30 at %(land30).2f mm, on purpose) and the bevel.
""" % v
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
    """A copy of the board with the order-number text on the silkscreen of placement.JLC_ORDER's side
    (a clear spot: tools/audit/check_fab.py checks it), for the JLCPCB zip."""
    import placement as PL
    from sexpr import parse, dump, Q
    (x, y), h, side = PL.JLC_ORDER
    t = parse(open(PCB).read())
    eff = ['effects', ['font', ['size', h, h], ['thickness', 0.15]]] + ([['justify', 'mirror']] if side == 'B' else [])
    t.append(['gr_text', Q(JLC_TEXT), ['at', x, y, 0], ['layer', Q('%s.SilkS' % side)],
              ['uuid', Q('6a1c0000-0000-4000-8000-0000000a2001')], eff])
    d = tmp('jlc-board')                      # same file name as the board, so the plot names match
    os.makedirs(d, exist_ok=True)
    fn = os.path.join(d, D.PROJECT + '.kicad_pcb')
    open(fn, 'w').write(dump(t) + '\n')
    for ext in ('.kicad_pro', '.kicad_dru'):     # the board's own rules travel with the copy
        shutil.copy(os.path.join(PRJ, D.PROJECT + ext), os.path.join(d, D.PROJECT + ext))
    return fn


GERBER_LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts'


def gerbers():
    g = tmp('gerbers')
    shutil.rmtree(g, ignore_errors=True)
    os.makedirs(g)
    jb = jlc_board()
    # --check-zones: refill if the saved fills are stale (tools/fill_zones.py should already have)
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', GERBER_LAYERS, '--subtract-soldermask',
        '--no-protel-ext', '--check-zones', '-o', g + '/', jb)
    run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
        '--generate-map', '--map-format', 'gerberx2', '-o', g + '/', jb)
    zf = os.path.join(JOUT, D.PROJECT + '-gerbers.zip')
    with zipfile.ZipFile(zf, 'w', zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(g)):
            z.writestr(fn, open(os.path.join(g, fn), 'rb').read())
    shutil.rmtree(g)
    # the PCBWay set: the board itself (no order-number text)
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', GERBER_LAYERS, '--subtract-soldermask',
        '--no-protel-ext', '--check-zones', '-o', g + '/', PCB)
    run('kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
        '--generate-map', '--map-format', 'gerberx2', '-o', g + '/', PCB)
    zp = os.path.join(POUT, D.PROJECT + '-gerbers.zip')
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(g)):
            z.writestr(fn, open(os.path.join(g, fn), 'rb').read())
    shutil.rmtree(g)
    shutil.rmtree(os.path.dirname(jb))
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
    for side, fn in (('top', 'board-top.png'), ('bottom', 'board-bottom.png')):
        run('kicad-cli', 'pcb', 'render', '--side', side, '--width', '1000', '--height', '1600',
            '--quality', 'high', '--background', 'opaque', '-o', os.path.join(DOCS, fn), PCB)


def main():
    os.makedirs(JOUT, exist_ok=True)
    os.makedirs(POUT, exist_ok=True)
    refs = boms()
    sch_docs()
    if not os.path.exists(PCB):
        print('BOM (%d lines), JLCPCB BOM, schematic PDF written; no %s yet: CPL, gerbers and layout '
              'renders skipped' % (len(groups(False)), os.path.basename(PCB)))
        return
    order_docs()
    rows = positions()
    n = cpl(refs, rows)
    centroid(refs, rows)
    zf = gerbers()
    assembly()
    pcb_docs()
    print('BOM (%d lines): %d placed refs; JLC CPL: %d rows; %s%s' % (
        len(groups(False)), len(refs), n, os.path.relpath(zf, PRJ),
        '' if EG.VERIFIED else '  [PROVISIONAL edge: DO NOT ORDER]'))


if __name__ == '__main__':
    main()
