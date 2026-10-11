#!/usr/bin/env python3
"""Fabrication + documentation outputs for FujiNet-ChannelF Rev0 (JLCPCB).

Always (from the schematic / design.py):
  FujiNet-ChannelF-Rev0-BOM.csv                    full BOM with MPN, manufacturer, LCSC (DNP flagged)
  exports/jlcpcb/BOM-JLCPCB.csv                     Comment,Designator,Footprint,LCSC Part # (no DNP parts)
  docs/FujiNet-ChannelF-Rev0-schematic.pdf

Only once FujiNet-ChannelF-Rev0.kicad_pcb exists:
  exports/jlcpcb/CPL-JLCPCB.csv                     Designator,Mid X,Mid Y,Layer,Rotation (JLC-corrected)
  exports/jlcpcb/FujiNet-ChannelF-Rev0-gerbers.zip  gerbers + Excellon drill, F.Silkscreen with the order-number text
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


def groups():
    g = {}
    for p in D.PARTS:
        if p.bom:
            g.setdefault((p.value, p.footprint, p.mpn, p.mfr, p.lcsc, p.dnp), []).append(p)
    return sorted(g.items(), key=lambda kv: ref_key(min((p.ref for p in kv[1]), key=ref_key)))


def boms():
    rows = groups()
    refs = lambda ps: ','.join(sorted((p.ref for p in ps), key=ref_key))
    with open(os.path.join(PRJ, D.PROJECT + '-BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(['Qty', 'Refs', 'Value', 'Footprint', 'MPN', 'Manufacturer', 'LCSC', 'Description', 'DNP'])
        for (val, fp, mpn, mfr, lcsc, dnp), ps in rows:
            descs = sorted({p.desc for p in ps})
            desc = descs[0] if len(descs) == 1 else {'C': 'capacitor', 'R': 'resistor', 'SW': 'push button',
                                                       'D': 'diode'}.get(ps[0].prefix, ps[0].prefix) + \
                ' (several uses: see schematic)'
            w.writerow([len(ps), refs(ps), val, fp.split(':')[1], mpn, mfr, lcsc, desc, 'DNP' if dnp else ''])
    with open(os.path.join(JOUT, 'BOM-JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (val, fp, mpn, mfr, lcsc, dnp), ps in rows:
            if dnp:
                continue       # not assembled: the CPL export skips DNP parts too
            if not lcsc:
                raise SystemExit('no LCSC code for ' + ps[0].ref)
            w.writerow([val, refs(ps), fp.split(':')[1], lcsc])
    return {p.ref for p in D.PARTS if p.bom and not p.dnp}


def fab_numbers():
    """What the fab needs to know, read from the board itself: outline size, the narrowest track,
    the smallest via, the vias in the QFN exposed pads."""
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
                thick=EG.THICKNESS, land0=EG.LAND_Y0, land1=EG.LAND_Y1, slot_w=EG.SLOT_W, slot_d=EG.SLOT_D)


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
   ruler. Lay a real Videocart board on it, contacts up: the 22 contacts at 2.54 mm in two groups
   of 11, the key slot between pins 11 and 12, pin 1 (GND) at the RIGHT seen from the contact
   side with the edge toward you, the %(tab).1f mm tab and the hole pattern must match.
2. **The thickness.** The console slot is "slightly greater than the thickness" of a cartridge
   board (US 4,095,791); %(thick).1f mm is ordered, as aotta's PicoVideocart (proven on a console).
3. **Stock.** `python3 tools/audit/sourcing.py` (or read `docs/sourcing.md`, %(stock)s): every line
   was in JLCPCB stock when this was written.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 power, B.Cu) |
| Size | %(w).1f x %(h).1f mm (the %(tab).1f mm tab, %(tab_d).0f mm long, under a 77 mm body) |
| Thickness | %(thick).1f mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 22 B.Cu fingers, **30-45 degree bevel** on the tab's insertion edge (the %(tab).1f mm bottom edge) only |
| Minimum track / clearance | %(track).2f mm / %(clear).2f mm (the RP2040's 0.4 mm pitch); smallest via %(vd).2f mm drill / %(vp).2f mm pad |
| Via in pad | the vias in the RP2040's and CP2102N's exposed pads: epoxy filled and capped if offered for 4 layers, else plain (tented from B.Cu) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | if asked for: on the left and right edges of the body only. Never on the tab, the slot, or the grip edge (USB-C, microSD, antenna) |

## Assembly

Top side only (B.Cu carries only the fingers). %(n)d parts per board. Not fitted (DNP): %(dnp)s.

### JLCPCB specifics

1. Upload the zip; set the options above. The key slot (%(slot_w).3f x %(slot_d).2f mm, round top) and
   its lead-in are in the Edge.Cuts layer, and so are the four 5.6 mm holes on the shell's bosses
   (also in the NPTH drill file).
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2040 is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2040, the S3 module, the translators, the regulators) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - %(rp)s (RP2040, QFN-56), %(s3)s (ESP32-S3), %(uart)s (CP2102N, QFN-28), %(usb)s (USB-C), %(sd)s (microSD),
     %(buf)s (SN74LVC4245A, TSSOP-24), %(flash)s (W25Q16JV, SOIC-8 208 mil), %(buck)s (AP63203, TSOT-23-6),
     %(ldo)s (AP2112K, SOT-23-5), %(q)s (2N7002), %(ap)s (UMH3N): pin 1 / orientation against the silkscreen.
   - %(ws)s (WS2812B), %(rst)s (BAT54C), %(ss34)s (SS34: the cathode bar toward +5V), %(led)s (green LED),
     %(esd)s (ESD5Z): polarity.
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers, and the slot. The fingers start
   %(land0).1f mm from the edge and run to %(land1).1f mm, on one face only (B.Cu), on purpose.
""" % dict(prj=D.PROJECT, tab=f['tab'], thick=f['thick'], stock=stock, w=f['w'], h=f['h'], tab_d=f['tab_d'],
           track=f['track'], clear=f['clear'], vd=f['via'][1], vp=f['via'][0], n=n_parts, dnp=dnp,
           slot_w=f['slot_w'], slot_d=f['slot_d'], land0=f['land0'], land1=f['land1'],
           rp=k['U_RP'], s3=k['U_S3'], uart=k['U_UART'], usb=k['J_USB'], sd=k['J_SD'], buf=rs('U_DBUF', 'U_CBUF'),
           flash=k['U_FLASH'], buck=k['U_BUCK'], ldo=k['U_LDO'], q=k['Q_INT'], ap=k['U_AUTOPROG'], ws=k['D_WS'],
           rst=k['D_RST'], ss34=rs('D_CONS', 'D_VBUS'), led=k['D_LED'], esd=rs('D_ESDP', 'D_ESDM', 'D_ESDV'))
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
              ['uuid', Q('6a1c0000-0000-4000-8000-0000000001c0')],
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
    run('kicad-cli', 'pcb', 'export', 'gerbers', '--layers', GERBER_LAYERS, '--subtract-soldermask',
        '--no-protel-ext', '-o', g + '/', jb)
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
        print('BOM: %d placed refs; schematic PDF written. No %s yet: CPL, gerbers and layout '
              'renders skipped.' % (len(refs), os.path.basename(PCB)))
        return
    order_docs()
    rows = positions()
    n = cpl(refs, rows)
    zf = gerbers()
    assembly()
    pcb_docs()
    print('BOM: %d placed refs; JLC CPL: %d rows; %s' % (len(refs), n, os.path.relpath(zf, PRJ)))


if __name__ == '__main__':
    main()
