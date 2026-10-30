#!/usr/bin/env python3
"""Fabrication + documentation outputs for FujiNet-O2 Rev0 (JLCPCB).

Always (from the schematic / design.py):
  FujiNet-O2-Rev0-BOM.csv                    full BOM with MPN, manufacturer, LCSC and description (DNP flagged)
  exports/jlcpcb/BOM-JLCPCB.csv                    Comment,Designator,Footprint,LCSC Part # (no DNP / no-BOM parts)
  docs/FujiNet-O2-Rev0-schematic.pdf

Once FujiNet-O2-Rev0.kicad_pcb exists:
  exports/jlcpcb/CPL-JLCPCB.csv                    Designator,Mid X,Mid Y,Layer,Rotation (JLC-corrected)
  exports/jlcpcb/FujiNet-O2-Rev0-gerbers.zip  gerbers + Excellon drill, F.Silkscreen with the order-number text
  exports/jlcpcb/ORDER-JLCPCB.md                   the order, step by step, numbers from the board
  docs/assembly-top.pdf                            F.Fab + F.Silkscreen + outline: references, pin 1
  docs/layout-front.svg, docs/layout-back.svg, docs/board-top.png, docs/board-bottom.png

While tools/edge_geom.VERIFIED is False ORDER-JLCPCB.md opens with DO NOT ORDER and
tools/audit/check_fab.py fails (it is True: the edge is checked against three built carts).

CPL rotations and origins: JLCPCB places each part by the EasyEDA footprint of its LCSC code.
tools/audit/jlc/jlc_rotations.json holds, per (footprint, LCSC code), the rotation correction and
the origin offset measured by comparing our footprint with that EasyEDA footprint pad by pad
(tools/audit/jlc/measure_rotations.py); the CPL applies them.  Still check the placement preview on
JLCPCB's order page before paying.

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
    return {p.ref for p in D.PARTS if p.bom and not p.dnp}


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
    """exports/jlcpcb/ORDER-JLCPCB.md: the order, step by step, with the references from design.py
    and the numbers from the board."""
    k = D.KEY
    rs = lambda *keys: ', '.join(sorted((k[x] for x in keys), key=ref_key))
    dnp = ', '.join(sorted((p.ref for p in D.PARTS if p.bom and p.dnp), key=ref_key)) or 'none'
    f = fab_numbers()
    src = os.path.join(DOCS, 'sourcing.md')
    stock = (open(src).readline().strip('# \n').split('(')[-1].rstrip(')') if os.path.exists(src) else 'build day')
    n_parts = len([p for p in D.PARTS if p.bom and not p.dnp])
    doc = ('' if EG.VERIFIED else DO_NOT_ORDER) + """# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `%(prj)s-gerbers.zip`: gerbers + Excellon drill. Its top silkscreen carries the order-number text
  `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

## Before ordering (VERIFY)

1. **The edge.** `tools/audit/edge_orientation.py` passes: the pinout (Dan Boris's O2 Tech Specs) and
   the footprint against three built Videopac carts (bwack's USBCART, PicoPAC, wilco2009's microSD
   cart): pins 1-15 on the parts face, A-R behind them, %(pitch).4f mm pitch. Not measured on an
   original cart: its exact pitch (built carts use 3.93-3.96 mm; all play) and its label face.
2. **Stock** (`python3 tools/audit/sourcing.py` re-reads it; `docs/sourcing.md`, %(stock)s). On 2026-10-30
   the crystal %(y)s, ABM8-272-T3 (C20625731), was short at JLCPCB (0; LCSC 57). The RP2354B (C39843328)
   and the RP2350 core inductor %(l)s, AOTA-B201610S3R3-101-T (C42411119), swing between in stock and
   none. For a short line, buy it into your JLCPCB parts inventory first (Parts Manager, "Order
   parts", from LCSC) or consign it. The inductor's alternate is TDK VLS201610HBX-3R3M-1 (C695624, same
   2016 size; Raspberry Pi specifies the polarity-marked AOTA); the crystal is Raspberry Pi's
   minimal-design part (CL 10 pF), so substitute it deliberately.
3. **The thickness.** %(thick).1f mm is ordered: the Videopac slot takes the 1.6 mm bwack / PicoPAC boards.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 +5V with +3V3 / +3V3_RP / CONS_5V islands, B.Cu) |
| Size | %(w).2f x %(h).2f mm (the whole 63 mm bottom edge is the insertion edge) |
| Thickness | %(thick).1f mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 30 fingers (15 on each face, %(pitch).4f mm pitch), **30 degree bevel** on the insertion edge |
| Minimum track / clearance | %(track).2f mm / %(clear).2f mm (the RP2354B's 0.4 mm pitch); smallest via %(vd).2f mm drill / %(vp).2f mm pad |
| Via in pad | the 3 x 3 vias in the RP2354B's exposed pad and the CP2102N's: epoxy filled and capped if offered for 4 layers, else plain (tented from B.Cu) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | the board is narrower than JLC's 70 mm single-board minimum: let JLC add rails on the left and right edges only. Never on the insertion edge or the top edge (the ESP32-S3 antenna, the USB-C) |
| Holes | two 5.0 mm non-plated holes (the shell posts), and the two side notches: route them as drawn |

## Assembly

Top side only (B.Cu carries only the A-R fingers and copper). %(n)d parts per board. Not fitted
(DNP): %(dnp)s. The %(ntp)d test pads are bare copper.

1. Upload the zip; set the options above.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2354B, the ESP32-S3 module, the regulators, the mux, the CP2102N, the crystal, the
   inductors, the USB-C, the microSD) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - %(rp)s (RP2354B, QFN-80), %(s3)s (ESP32-S3-WROOM-1: the antenna at the top edge), %(ldo)s (AP2112K,
     SOT-23-5), %(mux)s (TPS2116, SOT-583), %(buck)s (AP63203, TSOT-23-6), %(uart)s (CP2102N, QFN-28),
     %(esd)s (USBLC6, SOT-23-6), %(auto)s (UMH3N), %(rst)s (BAT54C), %(usb)s (USB-C), %(sd)s (microSD: the
     card slot at the left edge), %(y)s (crystal): pin 1 / orientation against the silkscreen.
   - %(led)s (red LED), %(ws)s (WS2812B-2020): polarity / pin 1.
   - The regulator corner beside the RP2354B: %(l)s (AOTA 2016), %(corner)s (0402, Raspberry Pi's
     minimal-design land pattern).
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start %(land0).2f mm from
   the edge and run to %(land1).2f mm, %(finger).2f mm wide, on both faces, on purpose; no part sits
   closer than %(parts).1f mm to that edge.
""" % dict(prj=D.PROJECT, thick=f['thick'], stock=stock, w=f['w'], h=f['h'], pitch=f['pitch'],
           track=f['track'], clear=f['clear'], vd=f['via'][1], vp=f['via'][0], n=n_parts, dnp=dnp,
           land0=f['land0'], land1=f['land1'], finger=f['finger'], parts=f['parts'],
           rp=k['U_RP'], ldo=k['U_LDO'], s3=k['U_S3'], mux=k['U_MUX'], buck=k['U_BUCK'], uart=k['U_UART'],
           esd=k['U_ESD'], auto=k['U_AUTOPROG'], rst=k['D_RST'], sd=k['J_SD'], ws=k['D_WS'],
           ntp=len([p for p in D.PARTS if p.prefix == 'TP']),
           usb=k['J_USB'], y=k['Y_RP'], led=k['D_LED'], l=k['L_RP'],
           corner=rs('C_VREGIN', 'C_DVBULK', 'C_AVDD', 'R_AVDD', 'R_USBP', 'R_USBM', 'C_OTP'))
    open(os.path.join(JOUT, 'ORDER-JLCPCB.md'), 'w').write(doc)


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


JLC_TEXT = 'JLCJLCJLCJLC'      # JLCPCB prints its order number here ("specify a location" on the order page)


def jlc_board():
    """A copy of the board with the order-number text on F.Silkscreen at placement.JLC_ORDER (a
    clear spot: tools/audit/check_fab.py checks it), for the JLCPCB zip."""
    import placement as PL
    from sexpr import parse, dump, Q
    (x, y), h = PL.JLC_ORDER
    t = parse(open(PCB).read())
    t.append(['gr_text', Q(JLC_TEXT), ['at', x, y, 0], ['layer', Q('F.SilkS')],
              ['uuid', Q('6a1c0000-0000-4000-8000-0000000a2001')],
              ['effects', ['font', ['size', h, h], ['thickness', 0.15]]]])
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
    shutil.rmtree(os.path.dirname(jb))
    return zf


def assembly():
    run('kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'F.Fab,F.SilkS,Edge.Cuts', '--mode-single',
        '--include-border-title', '-o', os.path.join(DOCS, 'assembly-top.pdf'), PCB)


def sch_docs():
    os.makedirs(DOCS, exist_ok=True)
    run('kicad-cli', 'sch', 'export', 'pdf', '-o', os.path.join(DOCS, D.PROJECT + '-schematic.pdf'), SCH)


def pcb_docs():
    run('kicad-cli', 'pcb', 'export', 'svg', '--layers', 'F.Cu,F.SilkS,F.Mask,Edge.Cuts', '--mode-single',
        '--fit-page-to-board', '-o', os.path.join(DOCS, 'layout-front.svg'), PCB)
    run('kicad-cli', 'pcb', 'export', 'svg', '--layers', 'B.Cu,B.SilkS,B.Mask,Edge.Cuts', '--mode-single',
        '--mirror', '--fit-page-to-board', '-o', os.path.join(DOCS, 'layout-back.svg'), PCB)
    for side, fn in (('top', 'board-top.png'), ('bottom', 'board-bottom.png')):
        run('kicad-cli', 'pcb', 'render', '--side', side, '--width', '1200', '--height', '1600',
            '--quality', 'high', '--background', 'opaque', '-o', os.path.join(DOCS, fn), PCB)


def main():
    os.makedirs(JOUT, exist_ok=True)
    refs = boms()
    sch_docs()
    if not os.path.exists(PCB):
        print('BOM (%d lines), JLCPCB BOM, schematic PDF written; no %s yet: CPL, gerbers and layout '
              'renders skipped' % (len(groups(False)), os.path.basename(PCB)))
        return
    order_docs()
    rows = positions()
    n = cpl(refs, rows)
    zf = gerbers()
    assembly()
    pcb_docs()
    print('BOM (%d lines): %d placed refs; JLC CPL: %d rows; %s%s' % (
        len(groups(False)), len(refs), n, os.path.relpath(zf, PRJ),
        '' if EG.VERIFIED else '  [PROVISIONAL edge: DO NOT ORDER]'))


if __name__ == '__main__':
    main()
