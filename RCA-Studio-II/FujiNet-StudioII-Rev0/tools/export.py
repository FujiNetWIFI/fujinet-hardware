#!/usr/bin/env python3
"""Fabrication + documentation outputs for FujiNet-StudioII Rev0 (JLCPCB).

Always (from the schematic / design.py):
  FujiNet-StudioII-Rev0-BOM.csv                    full BOM with MPN, manufacturer, LCSC and description (DNP flagged)
  exports/jlcpcb/BOM-JLCPCB.csv                     Comment,Designator,Footprint,LCSC Part # (no DNP / no-BOM parts)
  docs/FujiNet-StudioII-Rev0-schematic.pdf

Once FujiNet-StudioII-Rev0.kicad_pcb exists:
  exports/jlcpcb/CPL-JLCPCB.csv                     Designator,Mid X,Mid Y,Layer,Rotation (JLC-corrected)
  exports/jlcpcb/FujiNet-StudioII-Rev0-gerbers.zip  gerbers + Excellon drill, F.Silkscreen with the order-number text
  exports/jlcpcb/ORDER-JLCPCB.md                    the order, step by step, numbers from the board
  docs/assembly-top.pdf                             F.Fab + F.Silkscreen + outline: references, pin 1
  docs/layout-front.svg, docs/layout-back.svg, docs/board-top.png, docs/board-bottom.png

CPL rotations and origins: JLCPCB places each part by the EasyEDA footprint of its LCSC code.
tools/audit/jlc/jlc_rotations.json holds, per footprint, the rotation correction and the origin
offset measured by comparing every one of our footprints with that EasyEDA footprint pad by pad
(polarity by cathode marks, not pad numbers); the CPL applies them.  Still check the placement
preview on JLCPCB's order page before paying.

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
    the smallest via, the edge."""
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
                nvia=len(vias), clear=rules['min_clearance'], thick=EG.THICKNESS, land0=EG.LAND_Y0,
                land1=EG.LAND_Y1, finger=EG.FINGER_W, hole=EG.HOLE_D, parts=EG.PARTS_Y)


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
    doc = """# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `%(prj)s-gerbers.zip`: gerbers + Excellon drill (plated and non-plated). Its top silkscreen carries
  the order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order
  number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

## Before ordering (VERIFY)

1. **The edge.** Print `docs/tab-overlay-1to1.pdf` at 100 %% (no fit-to-page) and check its 50 mm
   ruler. Lay a real Studio II cartridge board on it, contacts up: the 22 contacts at 0.156"
   (3.96 mm), pin 1 (D7) at the LEFT seen from the contact side with the edge toward you, the
   %(w).1f mm width, the two %(hole).2f mm post holes and the side notches must match. The geometry is
   FliP's multicart v5.1 (built, runs in real consoles, fits original shells); nobody has
   measured an original cart for this board.  Above FliP's outline the board is taller (%(h).1f mm
   overall) for the ESP32-S3 half: it needs a printed shell (`case/board-anchors.scad`).
2. **The thickness.** %(thick).1f mm is ordered (FliP's boards: 1.57 mm). A 0.156" card-edge
   slot takes 1.57-1.6 mm.
3. **Stock.** `python3 tools/audit/sourcing.py` (or read `docs/sourcing.md`, %(stock)s): every line
   was in JLCPCB stock when this was written. The core inductor (%(l)s, AOTA-B201610S3R3) has the
   thinnest stock.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 power, B.Cu) |
| Size | %(w).2f x %(h).2f mm (no tab: the full width is the insertion edge) |
| Thickness | %(thick).1f mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 22 B.Cu fingers, **45 degree bevel** on the insertion edge (the %(w).1f mm bottom edge) |
| Minimum track / clearance | %(track).2f mm / %(clear).2f mm (the RP2354B's 0.4 mm pitch); smallest via %(vd).2f mm drill / %(vp).2f mm pad |
| Via in pad | the 3 x 3 vias in the RP2354B's exposed pad: epoxy filled and capped if offered for 4 layers, else plain (tented from B.Cu) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | if asked for: on the left and right edges only. Never on the insertion edge or the top edge (the ESP32-S3 antenna, USB-C, microSD) |

## Assembly

Top side only (B.Cu carries only the fingers and copper). %(n)d parts per board. Not fitted (DNP):
%(dnp)s (the debug UART header: fit it by hand for bring-up). The %(ntp)d test pads are bare copper.

### JLCPCB specifics

1. Upload the zip; set the options above. The two %(hole).2f mm holes for the shell posts are in the
   NPTH drill file, and the two side notches are in the Edge.Cuts layer.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2354B, the ESP32-S3 module, the logic, the regulators, the mux, the CP2102N, the crystal,
   the inductors, the USB-C, the microSD) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - %(rp)s (RP2354B, QFN-80), %(s3)s (ESP32-S3-WROOM-1: the antenna at the top edge), %(buf)s (74HCT541,
     TSSOP-20), %(gates)s ('32 / '14, SOIC-14), %(nor)s (74HCT1G02, SOT-23-5), %(ldo)s (AP2112K, SOT-23-5),
     %(mux)s (TPS2116, SOT-583), %(buck)s (AP63203, TSOT-23-6), %(uart)s (CP2102N, QFN-28), %(esd)s (USBLC6,
     SOT-23-6), %(auto)s (UMH3N), %(rst)s (BAT54C), %(usb)s (USB-C), %(sd)s (microSD: the card slot at the top
     edge), %(y)s (crystal): pin 1 / orientation against the silkscreen.
   - %(led)s (red LED), %(ws)s (WS2812B-2020): polarity / pin 1.
   - The regulator corner beside the RP2354B: %(l)s (AOTA 2016), %(corner)s (0402, Raspberry Pi's minimal-design
     land pattern); %(narrow)s, the 0402 100 nF straight out of IOVDD 50 / DVDD 51.
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start %(land0).2f mm from
   the edge and run to %(land1).2f mm, %(finger).3f mm wide, on one face only (B.Cu), on purpose; no part
   sits closer than %(parts).1f mm to that edge.
""" % dict(prj=D.PROJECT, thick=f['thick'], stock=stock, w=f['w'], h=f['h'], hole=f['hole'],
           track=f['track'], clear=f['clear'], vd=f['via'][1], vp=f['via'][0], n=n_parts, dnp=dnp,
           land0=f['land0'], land1=f['land1'], finger=f['finger'], parts=f['parts'],
           rp=k['U_RP'], buf=k['U_BUF'], gates=rs('U_OR', 'U_INV'), nor=k['U_NOR'], ldo=k['U_LDO'],
           s3=k['U_S3'], mux=k['U_MUX'], buck=k['U_BUCK'], uart=k['U_UART'], esd=k['U_ESD'],
           auto=k['U_AUTOPROG'], rst=k['D_RST'], sd=k['J_SD'], ws=k['D_WS'],
           ntp=len([p for p in D.PARTS if p.prefix == 'TP']),
           usb=k['J_USB'], y=k['Y_RP'], led=k['D_LED'], l=k['L_RP'],
           corner=rs('C_VREGIN', 'C_DVBULK', 'C_AVDD', 'R_AVDD', 'R_USBP', 'R_USBM', 'C_OTP'),
           narrow=rs('C_DV51', 'C_IOV50'))
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
              ['uuid', Q('6a1c0000-0000-4000-8000-0000000002c0')],
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
        run('kicad-cli', 'pcb', 'render', '--side', side, '--width', '1600', '--height', '1500',
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
    print('BOM (%d lines): %d placed refs; JLC CPL: %d rows; %s' % (len(groups(False)), len(refs), n,
                                                                  os.path.relpath(zf, PRJ)))


if __name__ == '__main__':
    main()
