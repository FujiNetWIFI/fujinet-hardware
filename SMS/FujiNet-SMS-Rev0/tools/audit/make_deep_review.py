#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev0 schematic audit (kicad-happy Deep
Review; docs/design-review-rev0.md).  The first audit's three fixes (VBUS pull-down,
/WAIT pull-up, CONS_5V bulk) are fitted and verified here; v2 adds the RP2350-E9
pull-downs and the WS2812C / TS-1187A stock swaps.

References are resolved from tools/design.py by topology (part value / MPN and
the nets on its pins), never hard-coded, so the file tracks regeneration and
reference shifts; net names are mapped onto the analyzer's names (which may
carry a sheet prefix, e.g. /edge/A0).  Datasheet pages were located in the PDFs
in datasheets/ with the gate's own matcher; page numbers are those files' PDF
pages.  Computations: tools/audit/{margins,timing_margins,spice_checks}.py.

Usage: python3 tools/audit/make_deep_review.py
       python3 <kicad-happy>/skills/kicad/review/scripts/deep_review_gate.py \
           analysis/deep_review.json --analysis-dir analysis/
"""
import datetime, json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

run = json.load(open(os.path.join(PRJ, 'analysis', 'manifest.json')))['current']
SCH = json.load(open(os.path.join(PRJ, 'analysis', run, 'schematic.json')))
ANETS = set(SCH['nets'])
M, T, SP = 'tools/audit/margins.py', 'tools/audit/timing_margins.py', 'tools/audit/spice_checks.py'


# ---- design lookups --------------------------------------------------------------
def parts(pred):
    return [p for p in D.PARTS if pred(p)]


def ref(pred, what):
    hit = parts(pred)
    if not hit:
        raise SystemExit('make_deep_review: no part for %s' % what)
    return hit[0].ref


def mpn(m):
    return [p.ref for p in D.PARTS if p.mpn == m]


def res(a, b):
    return ref(lambda p: p.prefix == 'R' and sorted(p.pins.values()) == sorted([a, b]), 'R %s-%s' % (a, b))


def cap(net, value=None):
    return [p.ref for p in D.PARTS if p.prefix == 'C' and net in p.pins.values() and (value is None or p.value == value)]


def gate(value):
    return [p.ref for p in D.PARTS if p.value == value]


def net(n):
    """design net name -> the analyzer's name for it (it may carry a sheet prefix)."""
    if n in ANETS:
        return n
    for a in sorted(ANETS):
        if a.endswith('/' + n):
            return a
    raise SystemExit('make_deep_review: net %s not in the analyzer JSON' % n)


def nets(*ns):
    return [net(n) for n in ns]


U_RP = ref(lambda p: p.value == 'RP2354B', 'RP2354B')
J_EDGE = ref(lambda p: p.value.startswith('SMS_Cart_Edge'), 'edge')
SRAMS = mpn('AS6C4008-55TIN')
Q_WAIT = ref(lambda p: p.value == '2N7002', '2N7002')
R_WAIT = ref(lambda p: p.prefix == 'R' and 'WAIT_GATE' in p.pins.values(), 'WAIT pull-up')
Q_CONS = ref(lambda p: p.mpn == 'AO3401A', 'P-FET')
D_VBUS = ref(lambda p: p.mpn == 'SS34', 'SS34')
R_VBH, R_VBL = res('VBUS', 'VBUS_SNS'), res('VBUS_SNS', 'GND')
R_VSH, R_VSL = res('CONS_5V', 'VSENSE'), res('VSENSE', 'GND')
U14, U27, U10, U00 = gate('74HCT14'), gate('74HCT27'), gate('74HCT10'), gate('74HCT00')
U_S3 = ref(lambda p: p.mpn.startswith('ESP32-S3'), 'S3')
U_UART = ref(lambda p: p.mpn.startswith('CP2102N'), 'CP2102N')
U_BUCK = ref(lambda p: p.mpn == 'AP63203WU-7', 'buck')
U_LDO = ref(lambda p: p.mpn == 'AP2112K-3.3TRG1', 'LDO')
D_WS = ref(lambda p: p.mpn == 'WS2812C-2020-V1', 'WS2812')
D_LED = ref(lambda p: p.mpn == 'KT-0603R', 'LED')
R_LED = ref(lambda p: p.prefix == 'R' and 'RP_LED' in p.pins.values(), 'LED R')
Y1 = ref(lambda p: p.mpn == 'ABM8-272-T3', 'crystal')
RNS = [p.ref for p in D.PARTS if p.mpn == '4D03WGJ0101T5E']
TP_CONT = ref(lambda p: p.prefix == 'TP' and 'CONT_N' in p.pins.values(), 'TP CONT')
TP_BREQ = ref(lambda p: p.prefix == 'TP' and 'BUSREQ_N' in p.pins.values(), 'TP BUSREQ')
C_CONS = cap('CONS_5V')
GLUE = U14 + U27 + U10 + U00
R_VBPD = res('VBUS', 'GND')
E9 = [p.ref for p in D.PARTS if p.prefix == 'R' and 'RP2350-E9' in p.desc]
E9_NETS = [next(n for n in p.pins.values() if n != 'GND') for p in D.PARTS if p.ref in E9]
SRAM_CE = {p.pins[str(D.SRAM_PIN['CE#'])]: p.ref for p in D.PARTS if p.mpn == 'AS6C4008-55TIN'}
TIED = ', '.join('%s pin %s to %s' % (p.ref, k, v) for p in D.PARTS if p.value.startswith('74HCT')
                 for k, v in sorted(p.pins.items()) if v in ('+5V', 'GND') and k not in ('7', '14'))


def f(cat, sev, conf, summary, comps, ns, ds=(), comp=None, desc='', rec=''):
    ev = {'components': comps, 'nets': ns}
    if ds:
        ev['datasheet'] = [{'mpn': m, 'page': p, 'quote': q} for m, p, q in ds]
    if comp:
        ev['computation'] = comp
    return {'detector': 'deep_review', 'category': cat, 'severity': sev, 'confidence': conf, 'summary': summary,
            'description': desc, 'recommendation': rec, 'evidence': ev}


BUS_IN = ['RD_N', 'WR_N', 'CE_N', 'MREQ_N', 'IORQ_N', 'M1_N', 'RESET_N', 'CLK']
F = [
 # ======================= warnings: changes planned in tools/design.py =======================
 f('power', 'info', 'high',
   'SS34 reverse leakage into the AO3401A gate (the VBUS net) when the console powers the cart: %s 4.7k VBUS-GND holds VGS at -2.8 V up to 500 uA (the 69k sense divider alone let 100 uA turn the FET off)' % R_VBPD,
   [Q_CONS, D_VBUS, R_VBH, R_VBL, R_VBPD], nets('VBUS', 'CONS_5V', '+5V'),
   [('SS34', 2, 'Maximum DC reverse current'), ('AO3401A', 2, 'Gate Threshold Voltage')],
   {'description': 'gate = I_R x (22k + 47k) [|| 4.7k]; AO3401A VGS(th) -0.5..-1.3 V with the source at +5V; ngspice decks for leakage 10-500 uA and the unplug decay',
    'script': SP,
    'result': 'without the 4.7k: 50 uA -> VGS -1.55 V (weak), >= 100 uA -> gate at +5V, FET off; '
              'with it: 500 uA -> VGS -2.80 V (Rds < 85 mOhm); after USB unplug the gate falls below 2.5 V in 3.6 ms (never without it at 50 uA)'},
   'The SS34 is reverse-biased by +5V whenever the console alone powers the cart, and its leakage flows into VBUS, the P-FET gate. '
   'Datasheet IR is 0.5 mA max at 25 C and 20 mA at 100 C (at 40 V). Found by the first audit (as in Fujiversal-Atari2600 Rev1); '
   'NES Rev0 R22 and FujiNet-7800 R24 carry the same fix.',
   'Fitted: 4.7k VBUS-GND (0603WAF4701T5E, C23162); 1.06 mA from VBUS with USB in.'),
 f('power', 'info', 'high',
   '/WAIT is held before the firmware runs: %s 4.7k gate pull-up vs the RP2350 reset pull-down (36-113k) gives >= 2.92 V against a 2N7002 VGS(th) of up to 2.5 V' % R_WAIT,
   [Q_WAIT, R_WAIT, U_RP, J_EDGE], nets('WAIT_GATE', 'WAIT_N', '+3V3_RP'),
   [('2N7002', 2, 'Gate-Threshold Voltage'), ('RP2354B', 1341, 'IOVDD=3.3V 36 113 kΩ'),
    ('RP2354B', 1337, 'GPIO34 - 43 Digital IO (FT) IOVDD Pull-Down'), ('Z0840004', 1, 'WAIT Setup Time')],
   {'description': 'gate = 3.3 V x RPD / (RPD + R_pu); 2N7002 level-1 model VTO 1.6 / 2.5 V, K = 8.9 mA/V^2 from ID(on) >= 500 mA at 10 V; console /WAIT pull-up 4.7k or 10k; Z80 VIL 0.8 V',
    'script': SP,
    'result': '4.7k: every corner held (<= 0.17 V); 10k (the first draft): VTO 2.5 V + RPD 36k -> /WAIT 4.4-4.7 V (not held); static cost 0.70 mA while GPIO34 is low'},
   'The hold exists so the Z80 cannot fetch from the cart before core1 serves it (sms_cart.h WAIT_PIN; main.c releases it after core1 starts). '
   'GPIO34 resets with its pull-down enabled; a 10k pull-up only wins with margin against a typical 2N7002.',
   'Fitted: 4.7k (0603WAF4701T5E, C23162).'),
 f('io', 'info', 'high',
   'RP2350-E9: the mode bits and the SRAM chip select (%s) each carry a 4.7k pull-down (<= 8.2k), so a pad left as an input between VIL and VIH cannot latch at ~2.2 V and enable /OE, /WE or both SRAMs' % ', '.join(E9_NETS),
   [U_RP] + E9 + SRAMS + GLUE, nets(*E9_NETS),
   [('RP2354B', 1367, 'Increased leakage current on Bank 0 GPIO when pad input is enabled'),
    ('RP2354B', 1368, 'with a low impedance source of 8.2 kΩ or less will overcome the erroneous leakage'),
    ('RP2354B', 1368, 'This doesn’t affect the pull-down behaviour of the pads immediately following a PoR or RUN reset')],
   {'description': 'E9: ~120 uA sourced by the pad, holding it near 2.2 V; 120 uA x 4.7k; current while the RP drives the line high', 'script': M,
    'result': 'worst 0.56 V (< 74HCT VIL 0.8 V) on every line; 0.70 mA per pin driven high, 3.5 mA with all five high'},
   'Affects the A2 stepping (fixed in A3/A4), and the stepping a buyer receives is not guaranteed. Right after a PoR or RUN reset the input enable is clear and the '
   "pad pull-downs work; the window is any firmware state that leaves these pads as inputs with the output off (init, a crash, core1 restart). "
   'At ~2.2 V the HCT glue reads GAME, MBOX, RAM_WE and LOAD as set, and SA19 at 2.2 V can select neither or both SRAMs, which would then fight on D0-D7. '
   'FujiNet-7800 Rev0 added the same pull-downs.',
   'Fitted: 4.7k pull-downs on GAME, LOAD, RAM_WE, MBOX and SA19; check_nets.py requires them.'),
 f('power', 'warning', 'medium',
   'Console 5 V budget: the cart can draw ~460 mA peak / ~185 mA average from the console regulator (S3 TX through the buck, RP LDO, SRAM, glue, WS2812C); no published cart-slot current',
   [J_EDGE, Q_CONS, U_BUCK, U_LDO, U_S3, D_WS] + C_CONS + SRAMS, nets('CONS_5V', '+5V'),
   [('ESP32-S3-WROOM-1-N16R8', 27, 'Current delivered by external power supply'),
    ('ESP32-S3-WROOM-1-N16R8', 28, '802.11b, 1 Mbps, @20.5 dBm'),
    ('WS2812C-2020-V1', 1, '5mA operating current per channel'),
    ('AS6C4008-55TIN', 3, 'Average Operating')],
   {'description': 'buck input = 3.3 V x (S3 355 mA + SD 100 + CP2102N 12) / (5 V x 0.85); + RP 60, SRAM 12, HCT 6, WS2812C 15 mA, E9 pull-downs 3.5 mA',
    'script': M, 'result': '~460 mA peak, ~185 mA average; P-FET 13 mW at peak'},
   'SMS2 service manual: LM7805 on a heat sink, AC adaptors DC 9 V 0.5 A (AU/EU/UK) or 1 A; no published cart-slot current. '
   'With USB plugged in the P-FET is off and USB carries the cart. The 2600 Rev1 cart has 10 uF + 100 nF on CONS_5V.',
   'Fitted: 10 uF + 100 nF on CONS_5V at the fingers (CL10A106KP8NNNC, C19702). Bring-up: measure the console rail under WiFi TX (TP on CONS_5V); '
   'firmware may cap S3 TX power; README: recommend a >= 1 A adaptor.'),
 f('sourcing', 'warning', 'high',
   'AS6C4008-55TIN, 74HCT27D,653 and 74HCT10D,653 are at 0 stock at JLCPCB and LCSC (2026-10-06); TI CD74HCT27M96 / CD74HCT10M are pin-identical second sources',
   SRAMS + U27 + U10, nets('SRAM_OE_N', 'SRAM_WE_N'),
   [('CD74HCT27M96', 3, 'Channel 1, Input C'), ('CD74HCT10M', 3, 'Channel 1, Input C'),
    ('74HCT27D,653', 2, '1C, 2C, 3C 13, 5, 11'), ('74HCT10D,653', 2, '1C, 2C, 3C 13, 5, 11')],
   {'description': 'LCSC wmsc product detail + jlcsearch; timing re-run with --ti (TI tpd CD74HCT27 29 ns, CD74HCT10 30 ns at 4.5 V, 85 C)',
    'script': T,
    'result': 'C5569980 0/0, C5984 0/0, C547236 0/0 (JLC/LCSC); C2878706 CD74HCT27M96 4/3, C2863188 CD74HCT10M 9/9; with TI parts M1 margin +105 ns, write-data hold +11.7 ns'},
   'Same pin numbers per gate (1C = 13, 1Y = 12, 2C = 5, 2Y = 6, 3C = 11, 3Y = 8). HC parts are not substitutes: the console NMOS VOH (2.4 V) and the RP 3.3 V outputs need TTL thresholds.',
   'Consign the SRAMs; order the TI gates as the JLC alternates (or consign Nexperia).'),

 # ======================= glue, levels, timing (no change) =======================
 f('pinout', 'info', 'high',
   "Stock symbols are right for the HCT parts: 74LS27/74LS10 units (1,2,13->12; 3,4,5->6; 9,10,11->8), 74HC14 (1->2 ... 13->12), 74HCT00 (1,2->3; 4,5->6; 9,10->8; 12,13->11), VCC 14, GND 7",
   GLUE, nets('SRAM_OE_N', 'SRAM_WE_N', 'PWR_OK', 'CEP_N'),
   [('74HCT27D,653', 2, '1A, 2A, 3A 1, 3, 9'), ('74HCT27D,653', 2, '1Y, 2Y, 3Y 12, 6, 8'),
    ('74HCT10D,653', 2, '1A, 2A, 3A 1, 3, 9'), ('74HCT10D,653', 2, '1Y, 2Y, 3Y 12, 6, 8'),
    ('SN74HCT14DR', 3, '1A 1 2 I Channel 1 input'), ('SN74HCT00DR', 1, 'Quadruple 2-Input Positive-NAND Gates')],
   {'description': 'every glue pin of the kicad-cli netlist compared with design.py; symbol pin types read from the lib_symbols embedded in cart-bus.kicad_sch',
    'result': '70 pins, 0 mismatches; symbol outputs are pins 12/6/8 (27, 10), 2/4/6/8/10/12 (14), 3/6/8/11 (00)'},
   'SN74HCT00 pin-out is a figure (p.3, read visually): 1A 1, 1B 2, 1Y 3, 2A 4, 2B 5, 2Y 6, GND 7, 3Y 8, 3A 9, 3B 10, 4Y 11, 4A 12, 4B 13, VCC 14. '
   'Unused inputs: %s (NAND inputs high, NOR inputs low).' % TIED),
 f('io', 'info', 'high',
   'PWR_OK sense: 0.82 x CONS_5V = 3.69 V at 4.5 V against SN74HCT14 VT+ max 1.9 V (4.5 V) / 2.1 V (5.5 V): PWR_OK is high from a 2.3-2.6 V console rail and drops at 0.6-1.7 V',
   [R_VSH, R_VSL] + U14, nets('VSENSE', 'CONS_5V', 'PWR_OK', 'PWR_OK_N'),
   [('SN74HCT14DR', 5, 'Positive-going threshold'), ('SN74HCT14DR', 5, 'TA = 25°C 1.2 1.5 1.9'),
    ('SN74HCT14DR', 5, 'Negative-going threshold')],
   {'description': 'ngspice DC sweep of CONS_5V 0-5.5 V into 22k/100k with +-1 uA HCT14 input leakage', 'script': SP,
    'result': 'VSENSE 3.67-3.71 / 4.08-4.12 / 4.49-4.53 V at 4.5 / 5.0 / 5.5 V; crosses 1.9 V at 2.30-2.34 V, 2.1 V at 2.54-2.58 V; 0.5 V at 0.59-0.63 V'},
   'The HCT14 is a TTL-threshold Schmitt, so the divider is not about reaching 0.7 x VCC: the margin is 1.8 V. The divider keeps VSENSE under the '
   "'14's VCC when USB powers +5V through the SS34 (4.3-4.9 V) and the console sits at 5.25 V (VSENSE 4.30 V). The NES Rev0 review's "
   "'VT+ 0.70 x VCC' came from datasheets/SN74HCT14DR.pdf there, which is TI's SNx4HC14 (an HC part).",
   'No change here. Replace NES Rev0 datasheets/SN74HCT14DR.pdf with sn74hct14.pdf and correct that review line.'),
 f('timing', 'info', 'high',
   'M1 fetch from the SRAM: the critical /OE path is console /CE -> 14 -> 00 -> 27 -> 10 (121 ns), not /RD (56 ns); data valid 416 ns after T1 vs 524 ns needed: +108 ns with a 40 ns /CE decode',
   GLUE + SRAMS + [J_EDGE], nets('CE_N', 'RD_N', 'CE', 'CEP_N', 'RD_CEP', 'SRAM_OE_N'),
   [('Z0840004', 1, 'Data Setup Time to Clock'), ('Z0840004', 1, 'Address Valid'),
    ('AS6C4008-55TIN', 4, 'Output Enable Access Time'), ('AS6C4008-55TIN', 4, 'Address Access Time'),
    ('74HCT27D,653', 5, 'nA, nB, nC to nY'), ('74HCT10D,653', 5, 'nA, nB to nY'), ('SN74HCT14DR', 6, 'SN74HCT14 40'),
    ('SN74HCT00DR', 5, 'Propagation delay A or B Y')],
   {'description': 'static timing walk of the design.py gate network (tpd 4.5 V/50 pF/85 C: 14 40, 00 25, 27 26, 10 30 ns) with Zilog Z8400 4 MHz figures at T = 279.4 ns',
    'script': T,
    'result': '/OE at 385.7 ns, data 415.7 ns, needed 523.7 ns (T3 rise - 35): +108 ns; /CE decode could take 148 ns; memory reads +233 ns; '
              'OE_ADDR (6 gates from A12) settles 19.7 ns + /CE before RD_CEP can open /OE (no glitch)'},
   'On SMS1/SMS2 the slot /CE is /MREQ gated by the I/O chip slot enable (no address terms), and /MREQ falls with /RD at T1 falling: '
   "/CE is not 'opened long before the strobe' (README). No published delay exists for the 315-5216 / 315-5237 /CE.",
   'No circuit change. Correct the README timing paragraph; bring-up: scope /MREQ -> /CE -> SRAM /OE on SMS1 and SMS2.'),
 f('timing', 'info', 'high',
   'RAM_WE write: /WE rises <= 52 ns (two 27s) after /WR; Z80 data stays >= 69.7 ns and the address >= 89.7 ns: +17.7 ns data hold (+11.7 with CD74HCT27), +37.7 ns address hold',
   U27 + U10 + SRAMS, nets('WR_N', 'WE_RAM', 'RAMWIN_N', 'SRAM_WE_N', 'RAM_WE'),
   [('Z0840004', 1, 'Data Stable from WR'), ('Z0840004', 2, 'Address Hold Time'),
    ('AS6C4008-55TIN', 4, 'Data Hold from End of Write Time'), ('AS6C4008-55TIN', 4, 'Write Recovery Time'),
    ('AS6C4008-55TIN', 4, 'Write Pulse Width'), ('AS6C4008-55TIN', 4, 'Data to Write Time Overlap')],
   {'description': 'Zilog #35 TdWRr(D) = TwCl + TfC - 70, #45 TdCTr(A) = TwCl + TfC - 50 at TwCl 139.7 ns, TfC 0 (pessimistic); worst 27 tpd',
    'script': T,
    'result': 'hold +17.7 ns (TfC 20 ns: +37.7); address +37.7 ns; write pulse >= 203 ns vs tWP 45; data setup >= 409 ns vs tDW 25; decode settles 183 ns before /WR falls'},
   'Positive at the datasheet corner (85 C, 4.5 V, 50 pF); the real load is two SRAM inputs, so the gates are faster. Firmware dispatches a write only after /WR rises; '
   'only the Sega mapper sets ram_we (all of slot 2 is RAM), so no mapper write races the /WE edge.',
   'No change. Keep README bring-up item 2 (scope D0-D7 against /WE).'),
 f('timing', 'info', 'high',
   'LOAD copy: /WE rises <= 52 ns after /RD; core1 drives D0-D7 150 ns past /RD (30 cycles at 200 MHz): +98 ns; address hold +37.7 ns, valid only for non-M1 reads',
   [U_RP] + U27 + U00 + SRAMS + RNS, nets('LOAD', 'LOADWIN_N', 'WE_LOAD', 'SRAM_WE_N', 'RD_N'),
   [('Z0840004', 2, 'Address Hold Time'), ('AS6C4008-55TIN', 4, 'Data Hold from End of Write Time')],
   {'description': 'sms_cart.c busy_wait_at_least_cycles(30) after /RD rises in the load window; Zilog #45', 'script': T,
    'result': 'data hold +98 ns (+92 with CD74HCT27); address hold +37.7 ns'},
   'In an M1 cycle the Z80 puts the refresh address (I:R) on A0-A15 at T3 rise, together with /RD rising, so a LOAD write during an opcode fetch from $8000-$9FFF would land at the refresh address. '
   'With GAME and LOAD both set, /OE and /WE would both fall on a load-window read.',
   'Firmware contract (README Glue): set LOAD only while the console copies with data reads, never while it executes from $8000-$9FFF; keep GAME = 0 while LOAD = 1.'),
 f('timing', 'info', 'medium',
   'SA13-SA19 are not static: core1 puts the 1K page bank (and SA19, the chip select) on every address change; an M1 fetch leaves it 359 ns from address valid (71 cycles at 200 MHz)',
   [U_RP] + SRAMS + U14, nets('SA13', 'SA19', 'SA19_N'),
   [('AS6C4008-55TIN', 4, 'Address Access Time'), ('Z0840004', 1, 'Address Valid')],
   {'description': 'deadline T3 rise - TsD 35 - tAA 55 - address valid 110 ns (M1); M2-M5 deadline T3 fall - 50', 'script': T,
    'result': 'M1: 359 ns; memory read: 483 ns'},
   "The README's 'the chips' /CE is static (SA19)' holds only within a 1K page; a slot change re-selects the chip within the cycle.",
   'No circuit change. Firmware: measure address-change -> GPIO41-47 latency on hardware (sms_cart.c budget comment).'),
 f('io', 'info', 'high',
   'RP outputs into the 5 V glue and SRAM: VOH >= 2.62 V vs 74HCT VIH 2.0 V (+0.62) and AS6C4008 VIH 2.4 V at VCC 4.5-5.5 V (+0.22; ~+0.85 into CMOS loads)',
   [U_RP] + SRAMS + U14 + U10 + U00, nets('GAME', 'MBOX', 'RAM_WE', 'LOAD', 'SA13', 'SA19'),
   [('RP2354B', 1341, 'IOVDD=3.3V 2.62 IOVDD V'), ('AS6C4008-55TIN', 3, 'Vcc: 4.5 ~ 5.5V')],
   {'description': 'VOH min at rated IOH vs VIH; loads are CMOS inputs (1 uA)', 'script': M, 'result': '+0.62 V (HCT), +0.22 V (SRAM) at VOH min'},
   'The AS6C4008 VIH is 2.4 V on a 4.5-5.5 V supply; 2.2 V (quoted by the NES Rev0 review) applies only at 2.7-4.5 V. '
   'GPIO40-47 (not FT) drive only these inputs, so no 5 V reaches them.'),
 f('io', 'info', 'high',
   'Console outputs into RP GPIO0-31 and PWR_OK into GPIO32: all Digital IO (FT), 5.5 V-tolerant with IOVDD at 3.3 V; VIH is 2.0 V (not 0.65 x IOVDD) against NMOS VOH 2.4 V',
   [U_RP, J_EDGE] + U14, nets(*BUS_IN, 'PWR_OK'),
   [('RP2354B', 1341, 'IOVDD=3.3V 2 5.5 V'), ('RP2354B', 1340, 'VPIN_FT'),
    ('RP2354B', 14, 'GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)'),
    ('RP2354B', 1336, 'tolerate voltages up to 5.5 V, provided IOVDD is powered to 3.3 V')],
   {'description': 'VIH(FT) at IOVDD 3.3 V vs TTL VOH', 'script': M, 'result': '+0.40 V'},
   'README bring-up item 7 quotes 0.65 x IOVDD (2.15 V); the RP2350 table gives 2.0 V at IOVDD 3.3 V.',
   'README: correct item 7 to VIH 2.0 V.'),
 f('power', 'info', 'high',
   'With USB and the console both on, +5V = VBUS - VF(SS34) = 4.3-4.9 V (P-FET off, console only via the body diode): the 74HCT parts can sit under their 4.5 V minimum',
   [Q_CONS, D_VBUS] + GLUE + SRAMS, nets('+5V', 'VBUS', 'CONS_5V'),
   [('SN74HCT14DR', 4, 'Supply voltage'), ('AS6C4008-55TIN', 3, 'Supply Voltage'), ('AO3401A', 2, 'Diode Forward Voltage')],
   {'description': 'VBUS 4.75-5.25 V minus SS34 VF 0.35-0.45 V', 'script': M, 'result': '4.30-4.90 V; console-only: CONS_5V - ~24 mV'},
   'Inherited from NES Rev0. HCT logic still works at 4.3 V and the SRAM is rated 2.7-5.5 V; console 5 V inputs then exceed VCC by up to ~0.9 V, through the console drivers\' impedance into the input clamps.',
   'No change for Rev0; README: plugging USB into a running console is for flashing, not play.'),
 f('memory', 'info', 'high',
   'AS6C4008-55TIN TSOP-I pin map (design.py SRAM_PIN) matches the datasheet 32/32; -55TIN is the 8 x 20 mm TSOP-I; VCC 2.7-5.5 V covers +5V',
   SRAMS, nets('SRAM_OE_N', 'SRAM_WE_N', 'SA19', 'SA19_N', 'D0', 'A0'),
   [('AS6C4008-55TIN', 2, 'TSOP-I/STSOP'), ('AS6C4008-55TIN', 14, 'AS6C4008-55TIN'), ('AS6C4008-55TIN', 3, 'Supply Voltage')],
   {'description': 'datasheet TSOP-I: 1 A11 2 A9 3 A8 4 A13 5 WE# 6 A17 7 A15 8 Vcc 9 A18 10 A16 11 A14 12 A12 13-20 A7..A0 21-23 DQ0-2 24 Vss 25-29 DQ3-7 30 CE# 31 A10 32 OE#; compared with the netlist',
    'result': '32/32 (%s /CE = SA19, %s /CE = SA19_N)' % (SRAM_CE['SA19'], SRAM_CE['SA19_N'])}),
 f('connector', 'info', 'high',
   '/CONT (edge 34) and /BUSREQ (edge 44) can stay on test pads: /CONT is a general-purpose input the I/O chip reports on the second controller port, not a boot or cart-detect line',
   [J_EDGE, TP_CONT, TP_BREQ], nets('CONT_N', 'BUSREQ_N'),
   [('SMS-CARTRIDGE-SLOT', 4, 'The value of this bit (high or low) is readable on the second controller input port'),
    ('SMS-CARTRIDGE-SLOT', 4, 'BUSREQ is normally wired-OR and requires an external pull-up')],
   {'description': 'web research: SMS Power! CartridgeSlot and Pinouts pages, Charles MacDonald smstech (BIOS detects media by the TMR SEGA header), a parts page reporting fingers 34 and 44 absent on the Sega 171-5507D board (numbering not cross-checked)',
    'result': 'stock carts leave both open; the console must pull /BUSREQ up (it runs with no cart); SMS Power lists /CONT as unnecessary for slot adaptors'},
   'Mark III / SMS1 / SMS2 boot the cart by the BIOS header check after enabling the slot through port $3E; the Power Base Converter has no BIOS. Nothing found ties boot to /CONT.',
   'No change: keep %s / %s, nothing fitted (no 0R to GND).' % (TP_CONT, TP_BREQ)),
 f('protection', 'info', 'medium',
   'No ESD parts on the 50-pin edge, as on every SMS cart; the RP2350 FT pads carry enhanced ESD protection; USB-C has ESD5Z on D+, D-, VBUS',
   [J_EDGE, U_RP], nets('RD_N', 'CE_N'),
   [('RP2354B', 1336, 'These pins have enhanced ESD protection')], None,
   'The cart is only inserted with the console off; the SRAM and glue inputs see the console bus directly.'),
 f('io', 'info', 'high',
   'D0-D7 go to the RP through 4 x 100R arrays (R_k between pins k and 9-k): RP and SRAM/console never fight at full drive on a turnaround',
   RNS + [U_RP], nets('D0', 'RP_D0', 'D7', 'RP_D7'),
   [('4D03WGJ0101T5E', 4, 'Equivalent Circuit Diagram')], None,
   'Uniroyal 4D03 drawing: R1 1-8, R2 2-7, R3 3-6, R4 4-5, isolated; design.py RN4 puts a[k] on pin k+1 and b[k] on pin 8-k.'),

 # ======================= shared FujiNet half (identical to NES Rev0) =======================
 f('power', 'info', 'high',
   'Whole RP2354B on the AP2112K (+3V3_RP, 20 us start-up), so IOVDD is up before the console bus can exceed the FT unpowered limit; VREG_VIN and VREG_AVDD together on that rail',
   [U_RP, U_LDO], nets('+3V3_RP', 'VREG_AVDD', 'DVDD'),
   [('AP2112K-3.3TRG1', 4, 'Start-up Time'), ('RP2354B', 1340, 'VPIN_FT'),
    ('RP2354B', 444, 'With the exception of the two voltage regulator supplies'), ('RP2354B', 455, 'must be RC filtered')],
   {'description': 'design.py vs NES Rev0 design.py, part by part', 'result': 'RP core, LDO and every passive on the rp-core / power sheets identical to NES Rev0 (NES review Deep Review, Power / rails)'}),
 f('power', 'info', 'high', 'RP2354B supply pins: IOVDD 5, 15, 24, 29, 41, 50, 60, 76; DVDD 10, 32, 51; 48 GPIO pin numbers checked against the datasheet table',
   [U_RP], nets('+3V3_RP', 'DVDD'),
   [('RP2354B', 1339, '5, 15, 24, 29, 41, 50, 60, 76'), ('RP2354B', 1337, 'GPIO34 - 43 Digital IO (FT) IOVDD Pull-Down')],
   {'description': 'RP_GPIO_PIN and the supply pins parsed against Table (QFN-80 column) of the PDF', 'result': '48/48 GPIOs, all supply pins match'}),
 f('power', 'info', 'high', 'AP63203 input is +5V (4.3-5.25 V after the P-FET or the SS34), inside its 3.8-32 V range; AP2112K EN tied to VIN (EN high 1.5-6.0 V)',
   [U_BUCK, U_LDO], nets('+5V', '+3V3'),
   [('AP63203WU-7', 1, '3.8V to 32V'), ('AP2112K-3.3TRG1', 4, 'VEN High Voltage')]),
 f('usb', 'info', 'high', 'CP2102N VBUS sense 22k/47k: 3.41 V at 5 V (SPICE), between VIH (VIO - 0.6 V) and VIO + 2.5 V; unchanged from NES Rev0',
   [U_UART, R_VBH, R_VBL], nets('VBUS_SNS', 'VBUS'),
   [('CP2102N-A02-GQFN28R', 8, 'There are two relevant restrictions on the VBUS pin voltage')],
   {'description': 'kicad-happy simulate_subcircuits (ngspice)', 'result': '3.4058 V at 5 V'}),
 f('mcu', 'info', 'high', 'ESP32-S3 EN RC 10k / 1 uF as Espressif recommends (SPICE 15.9 Hz); RESET reaches EN through the BAT54C',
   [U_S3] + cap('S3_EN'), nets('S3_EN'),
   [('ESP32-S3-WROOM-1-N16R8', 41, 'RC delay circuit at the EN pin')],
   {'description': 'kicad-happy simulate_subcircuits (ngspice)', 'result': '15.88 Hz'}),
 f('led', 'info', 'high', 'WS2812C-2020-V1 on +5V: VDD 3.7-5.3 V covers 4.3-5.25 V; VIH 2.7 V takes the S3 3.3 V data through 330R; 15 mA at full white',
   [D_WS], nets('+5V', 'WS_DIN'),
   [('WS2812C-2020-V1', 3, '+3.7~+5.3'), ('WS2812C-2020-V1', 3, '2.7V'), ('WS2812C-2020-V1', 1, '5mA operating current per channel')],
   None, 'Replaces the WS2812B-2020-V6 (5 at JLCPCB on 2026-10-07): same 2020 package, land and pin order (1 DO, 2 GND, 3 DI, 4 VDD).'),
 f('led', 'info', 'high', 'Activity LED red KT-0603R from GPIO33 through 1k: 1.3-1.5 mA',
   [D_LED, R_LED, U_RP], nets('RP_LED', 'RP_LED_A'),
   [('KT-0603R', 3, 'Forward Voltage')],
   {'description': '(3.3 V - VF 1.8-2.0 V) / 1k', 'script': M, 'result': '1.3-1.5 mA'},
   'Dim but visible; the 2600 Rev1 uses 680R (~2 mA) on the same LED if more brightness is wanted.'),
 f('oscillator', 'info', 'high', 'ABM8-272-T3 (CL 10 pF): 2 x 15 pF + ~3 pF stray = 10.5 pF; 1k in XOUT as the RP2350 minimal design',
   [Y1] + cap('XIN') + cap('XOUT_Y'), nets('XIN', 'XOUT_Y'),
   [('ABM8-272-T3', 1, 'Load capacitance')],
   {'description': 'kicad-happy simulate_subcircuits crystal model', 'result': '10.5 pF'}),
 f('usb', 'info', 'high', 'RP USB D+/D- through 27R to the S3 USB host pins', [U_RP], nets('RP_USB_DP', 'RP_USB_DM', 'USB_DP', 'USB_DM'),
   [('RP2354B', 1336, 'external 27Ω series resistors')]),
 f('thermal', 'info', 'high', 'RP LDO dissipation 51-102 mW at 30-60 mA from 5 V (Tj +13..+26 C); the RP core regulator is a switcher, so the LDO never carries the core current',
   [U_LDO, U_RP], nets('+3V3_RP'),
   [('RP2354B', 1348, 'hello_usb')],
   {'description': '(5.0 - 3.3 V) x I, SOT-23-5 ~250 C/W', 'script': M, 'result': '51 mW / 102 mW'}),
]

out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1, ensure_ascii=False)
print('deep_review.json: %d findings for run %s' % (len(F), run))
