#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev0 schematic audit (kicad-happy Deep Review;
docs/design-review-rev0.md, Part 1).

References come from tools/design.py keys (never hard-coded), net names are mapped onto the
analyzer's (which may carry a sheet path).  Datasheet pages are the PDF pages of the files in
datasheets/, located with tools/audit/find_quote_page.py; the console references (Atari 7800
schematic C025231 / C070354, the GCC1702B MARIA specification, the 7800 Software Guide, the POKEY
cart schematics) are in datasheets/ too -- the schematics are scans, so findings that rest on them
carry a computation and say where in the drawing.  Computations: tools/audit/{margins,
timing_margins,spice_checks,edge_orientation}.py.

Usage: python3 tools/audit/make_deep_review.py
       python3 <kicad-happy>/skills/kicad/review/scripts/deep_review_gate.py \
           analysis/deep_review.json --analysis-dir analysis/ --datasheets-dir datasheets
"""
import datetime, json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

run = json.load(open(os.path.join(PRJ, 'analysis', 'manifest.json')))['current']
SCH = json.load(open(os.path.join(PRJ, 'analysis', run, 'schematic.json')))
ANETS = set(SCH['nets'])
M, T, SP, EO = ('tools/audit/margins.py', 'tools/audit/timing_margins.py', 'tools/audit/spice_checks.py',
                'tools/audit/edge_orientation.py')
K = lambda *keys: [D.KEY[k] for k in keys]


def net(n):
    """design net name -> the analyzer's name for it (it may carry a sheet path)."""
    if n in ANETS:
        return n
    hits = sorted(a for a in ANETS if a.endswith('/' + n))
    if not hits:
        raise SystemExit('make_deep_review: net %s not in the analyzer JSON' % n)
    return hits[0]


def nets(*ns):
    return [net(n) for n in ns]


def f(cat, sev, conf, summary, comps, ns, ds=(), comp=None, desc='', rec=''):
    ev = {'components': comps, 'nets': ns}
    if ds:
        ev['datasheet'] = [{'mpn': m, 'page': p, 'quote': q} for m, p, q in ds]
    if comp:
        ev['computation'] = comp
    return {'detector': 'deep_review', 'category': cat, 'severity': sev, 'confidence': conf, 'summary': summary,
            'description': desc, 'recommendation': rec, 'evidence': ev}


GLUE = K('U_INV', 'U_NAND2', 'U_CSEL', 'U_STROBE')
F = [
 # ======================= errors / warnings that changed the design =======================
 f('connector', 'error', 'high',
   'Edge footprint: the 7800 edge has 18 positions at 2.54 mm with key slots at positions 3 and 16; the first footprint put pins 1, 2, 15, 16 (and 32, 31, 18, 17) one pitch inward, on the key positions, with no slots and a 42.6 mm tab',
   K('J_EDGE'), nets('RW', 'HALT_N', 'A13', 'A14', 'A15', 'EAUDIO', 'IRQ_N', 'PHI2'), (),
   {'description': 'footprint pads and edge_geom.py slots against Otaku-flash (KiCad), tdididit a78-flashcartplus (Eagle) and a78-devcart (gerbers), karri\'s measurements (AtariAge 348171), Wierer\'s C024926 photos, and the FujiPlusCart prototype gerbers in this repo (faces, power fingers)',
    'script': EO, 'result': 'all 32 pads at the published x on the right faces; slots |x| 15.31-17.71 clear both reported key centres; 0.59 mm slot-to-finger copper; prototype power fingers at 7800 pins 13/14/30'},
   'On the old footprint the four outer fingers per face would have shorted to the wrong console contacts or never mated (the console has 2 contacts, a plastic key, 12 contacts, a key, 2 contacts per row).',
   'Fixed: tools/edge_geom.py + make_edge_fp.py (18 positions, slots cut in the board outline by gen_pcb.py). Before ordering: fit a 1:1 print or a 2-layer coupon of the tab in a real 7800.'),
 f('mcu', 'warning', 'high',
   'RP2350-E9 (stepping A2): an input-enabled pad left in the undefined region floats to ~2.2 V and its internal pull-down cannot pull it low -- above the 74HCT VIH of 2.0 V on ROM_EN / RAM_EN / A8MASK before the PIO table runs',
   K('U_RP', 'R_PDROM', 'R_PDRAM', 'R_PDA8M') + GLUE, nets('ROM_EN', 'RAM_EN', 'A8MASK'),
   [('RP2354B', 1367, 'Increased leakage current on Bank 0 GPIO when pad input is enabled'),
    ('RP2354B', 1368, 'Driving / pulling the pad input low with a low impedance source of 8.2')],
   {'description': '4.7k to GND on each enable (<= 8.2k), 3.3 V / 4.7k while the PIO drives one high', 'script': M,
    'result': '0.70 mA per enable while high; ROM_EN low until the PIO runs, so the SRAM cannot answer before the firmware owns the bus'},
   'ROM_EN high with CARTSEL true opens SRAM /OE; before the firmware runs that could put the SRAM on the console\'s bus during the BIOS\'s cart check.',
   'Applied: R_PDROM / R_PDRAM / R_PDA8M 4.7k (0603WAF4701T5E, C23162).'),
 f('signal_integrity', 'warning', 'high',
   'Console /HALT (J1-2) is MARIA\'s weak NMOS output ("One MOS load"); the cart\'s ~17 pF (RP pin, the trace to its east side, a bring-up pad) slows its rise from ~30 ns to ~40 ns: isolate it with 10k at the finger',
   K('J_EDGE', 'R_HALT', 'U_RP', 'TP_HALT'), nets('HALT_N', 'HALT_RP'),
   [('MARIA-SPEC-GCC1702B', 8, 'Processor halt output. One MOS load.'),
    ('ATARI-7800-SOFTWARE-GUIDE', 2, 'distinguish MARIA ROM accesses from SALLY ROM accesses')],
   {'description': 'ngspice: MARIA pull-up ~550 ohm (its 30 ns into 25 pF), console ~15 pF, cart load directly vs behind a series R',
    'script': SP, 'result': 'J1-2 10-90 % rise 40 ns direct, 49 ns behind 1k, 23.5 ns behind 10k; the RP sees the edge ~80 ns later (observation only: the firmware never reads HALT)'},
   'Official carts leave pin 2 open. The console drives SALLY\'s /HALT through Q13 (emitter on J1-2), and HEN enables it only after the BIOS\'s second INPTCTRL write, so a cart cannot use /HALT to hold the CPU at power-on.',
   'Applied: R_HALT 10k (0603WAF1002T5E, C25804) at the finger; GPIO26 and the bring-up pad behind it.'),
 f('power', 'warning', 'medium',
   'Console 5 V budget: the cart peaks at ~474 mA (S3 TX through the buck) on top of the console\'s own ~0.35-0.5 A, from a 9 V 1 A adapter through the 7805 (no fuse): ~0.8-1.0 A at peaks, ~0.53-0.68 A average',
   K('Q_CONS', 'C_CONS', 'U_BUCK', 'U_S3'), nets('CONS_5V', '+5V', '+3V3'),
   [('ESP32-S3-WROOM-1-N16R8', 28, 'TX current consumption is rated at a 100% duty cycle.')],
   {'description': 'buck input from the S3 TX peak, SD, CP2102N; RP, SRAM, glue, WS2812; console estimate from MARIA 200 mA max + SALLY + RAM + TIA/RIOT (no measured figure exists)',
    'script': M, 'result': '474 mA peak / 179 mA average cart; 7805 at 2.4-4.4 W'},
   'Official POKEY carts drew about 0.2 A. The adapter rating is met on average; bursts lean on the console\'s 2200 uF bulk. USB-C power takes the whole cart off the console (the P-FET\'s body diode is then reverse-biased).',
   'Applied: C_CONS 10 uF at the finger. README: power the cart from USB-C for WiFi-heavy use; firmware option: cap the S3 TX power. Bench: measure the console rail under TX bursts.'),
 f('sourcing', 'warning', 'high',
   'Stock (JLCPCB, 2026-10-07): TL3342F160QG 5 and WS2812B-2020-V6 5 -> TS-1187A-B-A-B (basic, 1.68M) and WS2812C-2020-V1 (377k); AS6C4008-55TIN 0 at JLCPCB and LCSC -> consign it or let PCBWay source it',
   K('SW_RESET', 'SW_BOOTSEL', 'SW_S3EN', 'SW_S3BOOT', 'D_WS', 'U_SRAM'), nets('WS_DIN', 'RST_BTN'),
   [('WS2812C-2020-V1', 3, 'High Voltage Input'), ('WS2812C-2020-V1', 3, 'Power supply voltage'),
    ('AS6C4008-55TIN', 4, 'Address Access Time')],
   {'description': 'jlcsearch / LCSC product detail by code; JLC footprint match by tools/audit/jlc/measure_rotations.py',
    'script': 'tools/audit/jlc/measure_rotations.py', 'result': 'TS-1187A footprint (drawn from the XKB drawing) matches EasyEDA to 0.025 mm; WS2812C matches the 2020 land exactly (0.000 mm)'},
   'The WS2812C-2020-V1 has the B-2020-V6\'s pins (1 DO, 2 GND, 3 DI, 4 VDD), VDD 3.7-5.3 V and VIH 2.7 V, so the S3\'s 3.3 V data still drives it.',
   'Applied in design.py. Order: consign the AS6C4008 at JLC or use PCBWay turnkey (exports/pcbway).'),
 f('timing', 'warning', 'medium',
   'SRAM /WE rises one CD74HCT20 delay (35 ns max, 4.5 V / 50 pF / 85 C) after PHI2 falls; the 6502 guarantees only 30 ns of address and write-data hold (2 MHz SY6502A proxy; no SALLY datasheet): -5 ns at the datasheet corner, +19 ns typical',
   K('U_STROBE', 'U_SRAM'), nets('PHI2', 'SRAM_WE_N', 'RW'),
   [('CD74HCT20M96', 5, 'Propagation delay'), ('AS6C4008-55TIN', 4, 'Write Recovery Time')],
   {'description': 'static timing over the design.py gate network; SY6502A 2 MHz table (image-only PDF, p.6): THA / THW 30 ns min, 60 typ', 'script': T,
    'result': 'worst -5 ns (address and data hold); 25 C max tpd 28 ns -> +2 ns; typical 11 ns -> +19 ns (+49 against the typical 60 ns hold); write pulse >= 222 ns vs tWP 45, data setup >= 157 vs tDW 25'},
   'tWR and tDH of the AS6C4008 are 0, so the write ends safely if /WE rises before the address or data moves. Our /WE load is ~15 pF and VCC is 5.0 V, which puts the real delay well under the 50 pF / 4.5 V figure. 7800 RAM carts gate /WE with PHI2 through LS gates the same way.',
   'No change for Rev0. Bring-up: scope PHI2, A0 and SRAM /WE on a RAM_EN write. Rev1 option: a single-gate AHCT NAND for the last /WE stage.'),
 f('timing', 'warning', 'medium',
   'MARIA display-list reads from cart SRAM right after a slot change that toggles A8MASK (the mram board only) have data ready at 225 ns worst case against MARIA\'s ~184 ns window (+23 ns typical); every other case meets it',
   K('U_RP', 'U_INV', 'U_NAND2', 'U_SRAM'), nets('A8MASK', 'SA8', 'A8'),
   [('MARIA-SPEC-GCC1702B', 14, 'Display lists and list lists must be in fast (RAM) memory.'),
    ('AS6C4008-55TIN', 4, 'Address Access Time')],
   {'description': 'static timing: PIO slot change 45 ns (a78_pio.h) + A8MASK -> 74HCT14 -> 74HCT00 -> 74HCT14 -> SRAM A8 + tAA 55; MARIA DMA windows from GCC1702B p.27-28 (2 x 7.16 MHz cycles for display lists)',
    'script': T, 'result': 'same slot 120 ns (+64); slot change 145 (+39); slot change toggling A8MASK 225 (-41 worst, +23 typ); HSC A13 path 200 (-16 worst, +74 typ); graphics windows met everywhere (>= +60)'},
   'A8MASK is set only by the mram board (a78map.c, slots 2-3). Display lists usually live in console RAM; the window only matters when a game puts them in mram RAM and MARIA crosses a slot boundary into them.',
   'No change for Rev0 (the glue structure is the firmware\'s equation). Bring-up: run an mram title. Rev1 option: let the PIO drive A8MASK_N (active low) and save a gate.'),
 f('firmware', 'warning', 'high',
   'Power-on race: the PAL BIOS reads the cart ~22-62 ms after +5V (no self-test; NTSC ~0.27-0.31 s); the RP2354B must be serving the boot block by then -- bootrom, XOSC and copy_to_ram of the 69 KB image through the boot-time QSPI clock take tens of ms',
   K('U_RP', 'U_LDO', 'J_EDGE'), nets('+3V3_RP', 'CONS_5V'),
   [('AP2112K-3.3TRG1', 4, 'VEN High Voltage')],
   {'description': 'console reset R48 470k / C54 0.1 uF (C025231) and BIOS cycle counts (Dan Boris / 8bitdev disassembly); RP boot steps', 'script': M,
    'result': 'PAL deadline ~22-62 ms after +5V; RP ready time not known without measurement'},
   'An open bus at the BIOS\'s check sends PAL consoles to built-in Asteroids or 2600 mode and NTSC to 2600 mode, locked until a power cycle. No hardware hold-off exists: there is no reset on the edge and /HALT is only enabled later.',
   'Firmware: a minimal RAM-resident first stage that serves the boot block within ~10 ms; measure the RP ready time at bring-up. Users: with USB-C power plugged in before the console is switched on, the RP is already running.'),
 f('firmware', 'warning', 'high',
   'While the console\'s BIOS is mapped, its U4 (74LS08) forces A15, A14 and A12 low at the edge, so the cart never sees the PAL BIOS running at $C000-$EFFF: the firmware\'s PAL detection (a78_cart.c: reads at $C000-$EFFF while bootblk) cannot fire on hardware, and MAME does not model the gating',
   K('J_EDGE', 'U_RP'), nets('A15', 'A14', 'A12', 'A13'),
   [('ATARI-7800-SOFTWARE-GUIDE', 2, 'distinguish MARIA ROM accesses from SALLY ROM accesses')],
   {'description': 'C025231 sheet: J1-17 A15G, J1-16 A14G, J1-8 A12G are U4 74LS08 outputs (CPU A15/A14/A12 AND EXT, U11 4Q); A13 and A0-A11 pass ungated',
    'result': 'BIOS fetches at $F000-$FFFF appear as $2000-$2FFF, PAL $C000-$DFFF as $0xxx; CARTSEL (A15 | A14 | A12 & ...) is 0 for all of them'},
   'The same gating is why a 7800 cart never fights the BIOS ROM (CARTSEL stays 0), which settles the open question from the schematic-only review.',
   'fujinet-firmware: detect PAL by PHI2 frequency (1.773 vs 1.790 MHz, measurable on the PWM edge counter) or another signal; teach emu/fujinet.cpp the A15/A14/A12 gating.'),
 # ======================= confirmations =======================
 f('timing', 'info', 'high',
   'R/W stays high during MARIA DMA: SALLY releases it and MARIA\'s 3-6k pad pull-up (plus R60 4.7k on NTSC boards) holds it, so SRAM /WE (which needs R/W low) cannot fire during DMA and /OE needs no PHI2 term',
   K('U_STROBE', 'U_INV'), nets('RW', 'SRAM_OE_N', 'SRAM_WE_N'),
   [('MARIA-SPEC-GCC1702B', 7, 'eliminate discretes')],
   {'description': 'MARIA pin 39 description; C025231 R60 4.7k; the Commando cart (C301105) gates its ROM with R/W and MARIA reads it', 'script': T,
    'result': 'no HALT term needed in /WE; the cart loads R/W with three CMOS inputs and a test pad'}),
 f('timing', 'info', 'high',
   '6502 reads of the cart SRAM: data valid 375 ns worst case against 509 ns needed (+134 ns); read-to-write turnaround frees the bus 99 ns before the 6502 drives write data',
   K('U_SRAM') + GLUE, nets('SRAM_OE_N', 'A15', 'A14', 'RW'),
   [('AS6C4008-55TIN', 4, 'Output Enable Access Time'), ('SN74HCT14DR', 6, 'Propagation')],
   {'description': 'static timing with the console\'s 74LS08 on A15/A14/A12 (+20 ns) and the PIO slot change (+45 ns)', 'script': T,
    'result': 'game +134 ns, HSC +134 ns; turnaround +99 ns'}),
 f('interface', 'info', 'high',
   '/IRQ: the 2N7002 pulls the console\'s R32 2.2k to 0.08-0.17 V with GPIO28 at 3.3 V (VTO 1.6-2.5 V); the 10k gate pull-down keeps it released from power-on',
   K('Q_IRQ', 'R_IRQ', 'U_RP'), nets('IRQ_N', 'IRQ_GATE'),
   [('2N7002', 2, 'Gate-Threshold Voltage')],
   {'description': 'ngspice level-1 2N7002, K from ID(on) at worst VTH', 'script': SP, 'result': '0.08 V / 0.17 V'}),
 f('audio', 'info', 'high',
   'Cart audio into EXT AUDIO (console C10 0.1 uF + R5 6.8k into the audio sum): the PWM RC with its 10k level delivers within +-0.7 dB of a POKEY cart\'s 1k pull-up + 12k series up to 5 kHz (-4 dB at 10 kHz, the PWM low-pass)',
   K('R_AUDLP', 'C_AUDLP', 'R_AUDLVL', 'C_AUDDC', 'J_EDGE'), nets('AUD_PWM', 'AUD_LP', 'AUD_LVL', 'EAUDIO'),
   (), {'description': 'ngspice AC: 3.3 Vpp PWM vs 3.3 Vpp at POKEY AUD (C026461 / C301105 networks) into C10 + R5 to a virtual ground',
        'script': SP, 'result': '179 vs 166 uA p-p at 1 kHz (+0.7 dB); the console\'s C10 sets the 87 Hz high-pass'},
   'The 10k level is no longer PROVISIONAL: it matches a real POKEY cart. Pin 18 floats in DC between the two DC blocks, which is harmless.'),
 f('power', 'info', 'high',
   'PWR_OK: 0.82 x CONS_5V into the SN74HCT14; PWR_OK is guaranteed high above 2.3 V of console supply and low below 0.6 V; +1.79 V over VT+max at 4.5 V',
   K('R_VSH', 'R_VSL', 'U_INV'), nets('VSENSE', 'PWR_OK', 'CONS_5V'),
   [('SN74HCT14DR', 5, 'Positive-going threshold')],
   {'description': 'ngspice DC sweep with +-1 uA input leakage', 'script': SP, 'result': 'VT+max crossed at 2.30-2.34 V, VT-min at 0.59-0.63 V'}),
 f('power', 'info', 'high',
   'P-FET gate with R_VBPD 4.7k: VGS -2.80 V even at 500 uA of SS34 reverse leakage; the gate recovers 1.8 ms after USB is unplugged with the console on',
   K('Q_CONS', 'D_VBUS', 'R_VBPD'), nets('VBUS', '+5V', 'CONS_5V'),
   [('SS34', 2, 'Maximum DC reverse current'), ('AO3401A', 2, 'Gate Threshold Voltage')],
   {'description': 'ngspice gate node under 10-500 uA leakage and the unplug decay', 'script': SP, 'result': '-2.80 V at 500 uA; 1.8 ms'}),
 f('interface', 'info', 'high',
   'Levels: RP VOH 2.62 V min into 74HCT (VIH 2.0) +0.62 V, into the AS6C4008 SA lines (VIH 2.4) +0.22 V (+0.85 V into CMOS at 3.25 V); console NMOS VOH 2.4 V into the RP\'s FT pads (VIH 2.0 at IOVDD 3.3 V) +0.40 V; the FT pads see 5 V only while +3V3_RP (LDO on +5V) is up',
   K('U_RP', 'U_SRAM', 'U_LDO') + GLUE, nets('SA13', 'ROM_EN', 'RW', 'PHI2', '+3V3_RP'),
   [('RP2354B', 1337, 'Digital IO (FT)'), ('AS6C4008-55TIN', 4, 'Address Access Time')],
   {'description': 'datasheet DC limits', 'script': M, 'result': '+0.62 / +0.22 / +0.40 V'}),
 f('interface', 'info', 'medium',
   'Console decode: nothing in the console answers $0400-$047F, $1000-$17FF, $2800-$3FFF or $4000-$FFFF in 7800 mode, so CARTSEL\'s HSC ranges ($1000-$17FF, $3000-$3FFF) do not collide',
   K('U_CSEL'), nets('CSEL_P', 'A12', 'A13', 'A11'),
   [('MARIA-SPEC-GCC1702B', 14, 'Display lists and list lists must be in fast (RAM) memory.')],
   {'description': 'GCC1702B p.12 "Maria II Memory Map" (scan); MAME a7800.cpp comments on the Software Guide\'s claimed $2000 mirrors',
    'result': 'free ranges confirmed; in 2600 mode TIA / RIOT decode on A12 = 0 alone (firmware must stay off the bus there)'}),
]

out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1, ensure_ascii=False)
print('deep_review.json: %d findings for run %s' % (len(F), run))
