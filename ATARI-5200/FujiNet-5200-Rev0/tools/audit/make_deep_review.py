#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev0 audit (kicad-happy Deep Review;
docs/design-review-rev0.md).  Part 1 found the first Rev0 schematic's edge assumptions wrong in
five places (pins 11, 14, 23 / 24, 26 and the interlock); the findings below record what the
regenerated design does instead, each with its datasheet or Field Service Manual evidence and the
script that computes it.

References are resolved from tools/design.py by key or topology, never hard-coded, so the file
tracks regeneration and reference shifts; net names are mapped onto the analyzer's names (which
may carry a sheet prefix, e.g. /cart-bus/A0).  Datasheet pages are those of the PDFs in
datasheets/ (CX5200-FSM.pdf is Atari's CX5200 Field Service Manual, Rev 4, 1983), located with
tools/audit/find_quote_page.py.  Computations: tools/audit/{margins,timing_margins,spice_checks}.py,
tools/check_nets.py, tools/check_glue.py, tools/audit/edge_orientation.py, tools/audit/sourcing.py.

Usage: python3 tools/audit/make_deep_review.py
       python3 <kicad-happy>/skills/kicad/review/scripts/deep_review_gate.py \\
           analysis/deep_review.json --analysis-dir analysis/ --datasheets-dir datasheets
"""
import datetime, json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

run = json.load(open(os.path.join(PRJ, 'analysis', 'manifest.json')))['current']
SCH = json.load(open(os.path.join(PRJ, 'analysis', run, 'schematic.json')))
ANETS = set(SCH['nets'])
M, T, SP = 'tools/audit/margins.py', 'tools/audit/timing_margins.py', 'tools/audit/spice_checks.py'
CN, CG, EO, SRC = 'tools/check_nets.py', 'tools/check_glue.py', 'tools/audit/edge_orientation.py', 'tools/audit/sourcing.py'
K = D.KEY


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


def keys(*ks):
    return [K[k] for k in ks]


def cap(n):
    return [p.ref for p in D.PARTS if p.prefix == 'C' and n in p.pins.values()]


def f(cat, sev, conf, summary, comps, ns, ds=(), comp=None, desc='', rec=''):
    ev = {'components': comps, 'nets': ns}
    if ds:
        ev['datasheet'] = [{'mpn': m, 'page': p, 'quote': q} for m, p, q in ds]
    if comp:
        ev['computation'] = comp
    return {'detector': 'deep_review', 'category': cat, 'severity': sev, 'confidence': conf, 'summary': summary,
            'description': desc, 'recommendation': rec, 'evidence': ev}


E9 = [p.ref for p in D.PARTS if p.prefix == 'R' and 'E9' in p.desc]
GLUE = keys('U_BUF', 'U_AND', 'U_INV')
ADDR = ['A%d' % i for i in range(14)]
F = [
 # ======================= Part 1: the edge, corrected against the console's own documents =======================
 f('connector', 'info', 'high',
   "Edge pins 23 / 24: pin 23 is GND (the shield) on every board and pin 24 is GND only on CA018087 -- the universal boards take VIDEO IN there through CR10; the first Rev0 grounded 24 and left 23 open, which would short a universal console's video input. Now 23 is GND and 24 is open",
   [K['J_EDGE']], nets('GND'),
   [('CX5200-FSM', 11, 'accommodate the VCS'), ('CX5200-FSM', 160, 'Diode 1N914')],
   {'description': 'CX5200 FSM schematics of CA018087, CA020108 and CA021374 read at the edge connector (scratchpad crops am026_cr10, am031_cr10); '
                   'check_nets.py asserts the edge map: 12 / 13 / 23 / 25 GND, 24 / 28 / 30 open, 26 CONS_5V',
    'script': CN, 'result': 'edge map 36/36 pins as the FSM; check_nets.py 366/366'},
   "The universal (VCS-adaptor-ready) boards route the adaptor's video through CR10 to pin 24 and its audio / colour reference to pin 30 (OSC CON); a stock cart grounds 23 and leaves 24 on its ground pour only on the original board.",
   'Fixed in design.py EDGE; never ground 24 or 30.'),
 f('connector', 'info', 'high',
   'Edge pin 11 is the adapter\'s raw DC (UNREG) on the universal boards, live ahead of the power switch; the first Rev0 called it NC. It now feeds the cart through %s (bridged jumper), %s (0.35 A PTC), %s 2.2R and %s AP63205 5 V buck, never to GND' % tuple(keys('JP_UNREG', 'F_UNREG', 'R_UNREG', 'U_PRE')),
   keys('J_EDGE', 'JP_UNREG', 'F_UNREG', 'R_UNREG', 'U_PRE'), nets('UNREG', 'UNREG_J', 'UNREG_F', 'PRE_VIN'),
   [('CX5200-FSM', 35, 'UNREG'), ('AP63205WU-7', 1, '3.8V to 32V'), ('1206L035_30WR', 1, '1206L035/30')],
   {'description': 'FSM 2-port schematic sheet 3 (SWITCHED / UNREG at the edge); AP63205 VIN range vs 9-13 V; PTC hold / trip; input current at the cart peak and average',
    'script': M, 'result': '9 V in: 295 mA at the WiFi peak, 108 mA average; 13 V: 204 / 75 mA; PTC hold 0.35 A (23 C) / 0.30 A (40 C)'},
   'With raw DC present the CONS_OFF OR turns the console path off, so the cart takes nothing from VR1 (the regulator that also feeds the console RAM and controllers). On CA018087 pin 11 is unconnected and the pre-buck stays off.',
   'Cut JP2 to take nothing from pin 11.'),
 f('connector', 'info', 'high',
   'Edge pin 26 is +5 V from VR1 only (a 78M05 on CA018087), not "+5 or +12 V": the first Rev0\'s AP63205 on pin 26 would have put a 4 ms soft-start between the console bus and the RP\'s IOVDD (the FT pads are 5 V-tolerant only with IOVDD up). CONS_5V now reaches +5V through %s AO3401A, and the RP\'s LDO rises with it' % K['Q_CONS'],
   keys('J_EDGE', 'Q_CONS', 'U_LDO', 'U_RP'), nets('CONS_5V', '+5V', '+3V3_RP'),
   [('CX5200-FSM', 161, 'Voltage Regulator 78M05 (5V)'), ('RP2354B', 1336, 'tolerate voltages up to 5.5 V, provided IOVDD is powered to 3.3 V'),
    ('AP63205WU-7', 5, 'Soft-Start Period'), ('AP2112K-3.3TRG1', 4, 'Start-up Time')],
   {'description': 'FSM parts list (CA018087: VR1, VR2 78M05) and schematics (Q6 switches VR1 onto pin 26 when the interlock closes); soft-start vs LDO start-up',
    'script': M, 'result': 'P-FET 13 mW at the cart peak; +5V = CONS_5V - ~30 mV'}),
 f('io', 'info', 'high',
   'Edge pin 14 (PHI2 on the 2-port, GND on CA018087) reaches the cart through the console\'s CR9 1N914, anode at pin 14: the console can only pull it low, to 0.94-1.09 V. %s 4.7k to CONS_5V pulls it up and %s 74LVC1G17 at 5 V squares it (VT- min 1.32 V); the first Rev0\'s 1k into GPIO25 would have read neither level' % (K['R_PHI2PU'], K['U_PHI2']),
   keys('J_EDGE', 'R_PHI2PU', 'U_PHI2', 'U_RP'), nets('PHI2', 'PHI2_RP', 'CONS_5V'),
   [('CX5200-FSM', 162, 'I.C. 74LS125'), ('CX5200-FSM', 160, 'Diode 1N914'), ('74LVC1G17', 6, 'negative-going'),
    ('74LVC1G17', 5, 'input capacitance')],
   {'description': 'ngspice: 74LS125 (VOL 0.35-0.5 V, source-only high) -> 1N914 -> 4.7k / 12-25 pF at 1.79 MHz',
    'script': SP, 'result': 'low 0.94 / 1.08 V vs VT- min 1.32 V (+0.24 V worst); high 4.2-4.8 V; past VT+ max 2.79 V <= 57 ns after release (half period 279 ns)'},
   'The pull-up goes to CONS_5V, not +5V: with the console off and USB running the cart, a pull-up to +5V would forward-bias CR9 into the unpowered LS125. On CA018087 pin 14 is GND: PHI2_RP reads low, harmlessly.',
   'No change. Firmware: PHI2 exists on the 2-port only.'),
 f('power', 'info', 'high',
   'Interlock 18 / 36: the stock cart\'s jumper switches VR1 on through Q8 / Q6 with ~34-61 mA at ~0.2 V, so a firmware switch there must be a low-side N-FET (%s 2N7002, D = 36, S = 18, gate pulled to +5V by %s): the first Rev0\'s P-FET could never turn on at ground potential. %s is bridged by default; the switch and its driver are DNP' % (K['Q_ILK'], K['R_ILKG'], K['JP_ILK']),
   keys('J_EDGE', 'JP_ILK', 'Q_ILK', 'R_ILKG', 'Q_ILKDRV', 'R_ILKPD'), nets('ILK_A', 'ILK_B', 'ILK_G', 'ILK'),
   [('2N7002', 2, 'Gate-Threshold Voltage')],
   {'description': 'FSM schematics: CI1 (18) to Q8, CI2 (36) to Q6 base through R57 330R (182R on CA020108) and 4.7k to UNREG; check_nets.py N-FET orientation and the E9 pull-down',
    'script': CN, 'result': 'D on pin 36, S on pin 18, gate pull-up to +5V, driver on GPIO28 with 4.7k pull-down'},
   'Once JP1 is cut the cart must be powered from USB or the edge raw DC first, or nothing turns the switch on (it is VR1 that it switches).',
   'Leave JP1 bridged unless the firmware needs a console power cycle.'),
 f('connector', 'info', 'high',
   'Edge geometry: pins 1-18 on the label face (F.Cu), pin 1 (D0) at the left, pin 37-k behind pin k, 2.54 mm; pins 18 / 36 are short (from 1.9 mm, last-make) as on every stock and open board; tab 47.8 mm. The first Rev0 footprint had every finger the same length',
   [K['J_EDGE']], nets('ILK_A', 'ILK_B', 'D0'),
   [('CX5200-FSM', 11, 'accommodate the VCS')],
   {'description': 'Pixels Past rev B gerbers (traced to the EPROM), tdididit a52 Eagle library, sanni cartreader 5200 adapter + photo; Sullins EBC18DCWN slot 48.26 mm',
    'script': EO, 'result': 'OK: 36 pads, faces, pitch, width 1.78 mm, copper 0.6-7.0 mm (18 / 36 from 1.9)'}),
 # ======================= power =======================
 f('power', 'warning', 'high',
   "Console 5 V budget: the cart can draw ~470 mA at a WiFi TX burst (~170 mA average) from VR1, a 0.5 A 78M05 on CA018087 that also feeds the console RAM and controllers: without raw DC (pin 11) or USB, a burst can pull VR1 into current limit",
   keys('J_EDGE', 'Q_CONS', 'U_BUCK', 'U_LDO', 'U_S3', 'D_WS') + cap('CONS_5V'), nets('CONS_5V', '+5V'),
   [('CX5200-FSM', 161, 'Voltage Regulator 78M05 (5V)'), ('ESP32-S3-WROOM-1-N16R8', 28, '802.11b, 1 Mbps, @20.5 dBm'),
    ('ESP32-S3-WROOM-1-N16R8', 27, 'Current delivered by external power supply'),
    ('WS2812B-2020-V6', 1, '12mA operating current per channel')],
   {'description': 'buck input = 3.3 V x (S3 355 mA + SD 100 + CP2102N 12) / (5 V x 0.85); + RP 60, logic 5, WS2812B 36 mA, pull-ups 3 mA',
    'script': M, 'result': '~467 mA peak (93 % of VR1 alone), ~172 mA average (34 %)'},
   'On the universal boards the edge raw DC takes the whole cart and the console path opens (CONS_OFF). With USB plugged in, USB carries it. Only the original 4-port (CA018087) without USB leaves the cart on VR1.',
   'README: on CA018087, run WiFi with USB power; firmware: cap the S3 TX power when PWR_OK and no VBUS / PRE5V (bring-up: measure CONS_5V under TX at TP17).'),
 f('power', 'info', 'high',
   '+5V is the OR of three sources: CONS_5V through %s (on unless CONS_OFF), VBUS through %s SS34 and PRE5V through %s SS34; CONS_OFF = VBUS OR PRE5V (%s BAT54C). The SS34s\' reverse leakage into their 4.7k pull-downs (%s, %s) keeps VGS at -2.9 V up to 500 uA each' % tuple(keys('Q_CONS', 'D_VBUS', 'D_PRE', 'D_OFF', 'R_VBPD', 'R_PREPD')),
   keys('Q_CONS', 'D_VBUS', 'D_PRE', 'D_OFF', 'R_VBPD', 'R_PREPD', 'R_OFFPD'), nets('CONS_OFF', 'VBUS', 'PRE5V', '+5V', 'CONS_5V'),
   [('SS34', 2, 'Maximum DC reverse current'), ('AO3401A', 2, 'Gate Threshold Voltage'), ('AO3401A', 1, 'RDS(ON) (at VGS=-2.5V)')],
   {'description': 'ngspice: both SS34s leaking 10-1000 uA from +5V into their nodes, BAT54C fitted model, 100k gate pull-down; USB unplug decay with Ciss 645 pF',
    'script': SP, 'result': '500 uA each: CONS_OFF 2.10 V, VGS -2.90 V (RDS(on) specified); 1 mA: -0.68 V (not reliably on); after unplug VGS < -2.5 V in 3.1 ms'},
   'SS34 IR max is 0.5 mA at 25 C at the rated 40 V; at 5 V reverse it is far lower. Until the gate settles after an unplug, the body diode carries the console path (~0.7 V drop).'),
 f('power', 'info', 'medium',
   'With raw DC (or USB) running the cart, the console still feeds part of the load through %s\'s body diode when VR1 sits more than the two diodes\' difference above PRE5V: up to ~85 mA at VR1 5.25 V / PRE5V 4.95 V, none at the nominal 5.0 V' % K['Q_CONS'],
   keys('Q_CONS', 'D_PRE', 'U_PRE'), nets('CONS_5V', 'PRE5V', '+5V'),
   [('AO3401A', 2, 'Diode Forward Voltage'), ('AP63205WU-7', 5, 'CCM, AP63205')],
   {'description': 'ngspice operating points: PRE5V 4.95 / 5.05 V, CONS_5V 4.75 / 5.0 / 5.25 V, 400 mA on +5V; level-1 AO3401A with body diode, SS34 model',
    'script': SP, 'result': '0 mA except 85 mA (PRE5V 4.95, VR1 5.25) and 3 mA (PRE5V 5.05, VR1 5.25)'},
   'Acceptable: a stock cart draws ~100 mA from VR1; the share is bounded by the body diode and only at the tolerance corner.'),
 f('power', 'info', 'high',
   'Raw DC path: %s 0.35 A PTC and %s 2.2R 0603 carry 75-108 mA on average (12-26 mW) and 204-295 mA through a WiFi burst (92-191 mW for milliseconds); the AP63205 VIN stays >= 8.0 V at 9 V in' % tuple(keys('F_UNREG', 'R_UNREG')),
   keys('F_UNREG', 'R_UNREG', 'U_PRE') + cap('PRE_VIN'), nets('UNREG_F', 'PRE_VIN'),
   [('1206L035_30WR', 1, 'Hold current: maximum current device will pass without tripping'), ('RC0603FR-072R2L', 7, 'RC0603=1/10W'),
    ('AP63205WU-7', 5, 'VIN Under Voltage Threshold (Rising)')],
   {'description': 'P_in = 5 V x I(+5V) / 0.88; I_in at 9 / 11 / 13 V; 2.2R + PTC R1max 1.2 ohm drop; hot-plug inrush into 2 x 22 uF',
    'script': M, 'result': '9 V: 295 / 108 mA, 2.2R 191 / 26 mW; 13 V: 204 / 75 mA; inrush 5.2 A peak, tau 110 us'},
   'The burst is milliseconds: the PTC needs seconds at 2 x hold to trip, and the 0603 thick-film takes 2.5 x rated for 5 s. The 2.2R exists for the inrush when the cart goes in with the adapter live.',
   'Bring-up: scope PRE_VIN on a universal console during WiFi TX; if the 2-port adapter sags under 9 V, a 0805 2.2R is the drop-in.'),
 f('power', 'info', 'high',
   'With USB and the console both on, +5V = VBUS - VF(SS34) = 4.3-4.9 V (P-FET off, console only via the body diode): the 74HCT parts can sit under their 4.5 V minimum',
   keys('Q_CONS', 'D_VBUS') + GLUE, nets('+5V', 'VBUS', 'CONS_5V'),
   [('SN74HCT14DR', 4, 'Supply voltage'), ('AO3401A', 2, 'Diode Forward Voltage')],
   {'description': 'VBUS 4.75-5.25 V minus SS34 VF 0.35-0.45 V', 'script': M, 'result': '4.30-4.90 V'},
   'Inherited from the SMS / 7800 / NES boards. HCT logic still works at 4.3 V; the body diode keeps +5V >= CONS_5V - 0.7 V.',
   'README: USB into a running console is for flashing, not play.'),
 # ======================= glue, levels, timing =======================
 f('io', 'info', 'high',
   "The '541 opens only while an enable is low, PWR_OK and BUF_EN: /OE1 = /EN40 AND /EN80 (%s '08), /OE2 = NOT(PWR_OK AND BUF_EN) ('08 + '14); BUF_EN has %s 4.7k to GND so the bus stays closed until the firmware drives GPIO26 -- exactly a52_glue_drive()" % (K['U_AND'], K['R_PDBUF']),
   GLUE + [K['R_PDBUF'], K['U_RP']], nets('EN40_N', 'EN80_N', 'EN_ANY_N', 'SERVE_N', 'BUF_EN', 'PWR_OK'),
   [('SN74HCT541PWR', 7, 'If either output-enable (OE1 or OE2) input is high, all eight outputs are'),
    ('SN74HCT08DR', 3, 'Channel 1, Input A')],
   {'description': 'check_glue.py builds the gate network from the netlist, evaluates all 16 inputs against a52_glue_drive() compiled on the host',
    'script': CG, 'result': '16/16; /EN40, /EN80 one gate from /OE1; PWR_OK two Schmitt stages from VSENSE; unused gates inputs on GND'}),
 f('pinout', 'info', 'high',
   "74HCT541 channels taken in reverse (A8 pin 9 = RP_D0 -> Y8 pin 11 = D0 ... A1 pin 2 = RP_D7 -> Y1 pin 18 = D7) so finger -> '541 -> RP GPIO16-23 is planar on F.Cu; 74LVC1G17 SOT-353: A 2, GND 3, Y 4, VCC 5",
   keys('U_BUF', 'U_PHI2', 'J_EDGE'), nets('D0', 'D7', 'RP_D0', 'RP_D7', 'PHI2', 'PHI2_RP'),
   [('SN74HCT541PWR', 7, 'If either output-enable (OE1 or OE2) input is high, all eight outputs are'),
    ('74LVC1G17', 3, 'Pin description')],
   {'description': 'netlist vs the TI pin configuration (OE1 1, A1-A8 2-9, GND 10, Y8-Y1 11-18, OE2 19, VCC 20) and the Nexperia TSSOP5 column',
    'script': CN, 'result': '20/20 and 5/5 pins; every Dk = RP_Dk through one channel'}),
 f('io', 'info', 'high',
   'PWR_OK sense: 0.82 x CONS_5V = 3.69 V at 4.5 V against SN74HCT14 VT+ max 1.9 V (4.5 V) / 2.1 V (5.5 V): PWR_OK is high from a 2.3-2.6 V console rail and drops at 0.6-1.7 V',
   keys('R_VSH', 'R_VSL', 'U_INV'), nets('VSENSE', 'CONS_5V', 'PWR_OK', 'PWR_OK_N'),
   [('SN74HCT14DR', 5, 'Positive-going threshold'), ('SN74HCT14DR', 5, 'Negative-going threshold')],
   {'description': 'ngspice DC sweep of CONS_5V 0-5.5 V into 22k/100k with +-1 uA HCT14 input leakage', 'script': SP,
    'result': 'VSENSE 3.67-3.71 / 4.08-4.12 / 4.49-4.53 V at 4.5 / 5.0 / 5.5 V; crosses 1.9 V at 2.30-2.34 V, 2.1 V at 2.54-2.58 V; 0.5 V at 0.59-0.63 V'},
   'With USB or raw DC running +5V and the console at 5.25 V, VSENSE (4.30 V) stays under the \'14\'s VCC (>= 4.55 V).'),
 f('timing', 'info', 'medium',
   "Read path: the byte is on D0-D7 125 ns after the address reaches the edge (LS244 18 + RP following 65 PROVISIONAL + '541 42 ns at 150 pF), the enable path takes 118 ns; with 2 MHz-grade 6502 timing (TADS 150, TDSU 50 ns) at 1.79 MHz the margin is +234 ns",
   GLUE + [K['U_RP'], K['J_EDGE']], nets('EN40_N', 'EN80_N', 'EN_ANY_N', 'D0', 'RP_D0', 'A0'),
   [('SN74HCT541PWR', 5, 'Switching Characteristics'), ('SN74HCT08DR', 5, 'Propagation delay')],
   {'description': 'static walk: SY6500 read timing (2 MHz / 1 MHz grade), console LS244 / LS139 delays, TI HCT541 / HCT08 maxima at 4.5 V, 85 C',
    'script': T, 'result': 'margin +234 ns (2 MHz grade) / +34 ns (1 MHz grade); the RP may take up to 299 ns to follow an address'},
   'ANTIC reads the cart too (display lists, character sets); its address-valid delay is undocumented and taken as the 6502\'s.',
   'Bring-up: scope an address bit against D0 on a 4-port and a 2-port.'),
 f('io', 'info', 'high',
   "RP outputs into the 5 V logic: VOH >= 2.62 V vs 74HCT VIH 2.0 V (+0.62 V) on RP_D0-7 and BUF_EN; the '541's outputs give the console bus VOH 3.84 V at -6 mA",
   keys('U_RP', 'U_BUF', 'U_AND'), nets('RP_D0', 'RP_D7', 'BUF_EN', 'D0'),
   [('RP2354B', 1341, 'IOVDD=3.3V 2.62 IOVDD V'), ('SN74HCT541PWR', 4, 'High-level input voltage')],
   {'description': 'VOH min at rated IOH vs VIH; loads are CMOS inputs', 'script': M, 'result': '+0.62 V (HCT)'}),
 f('io', 'info', 'high',
   'Console outputs into RP GPIO0-15 (A0-A13, /EN40, /EN80) and the 5 V PWR_OK / PHI2_RP into GPIO24 / 25: all Digital IO (FT), 5.5 V-tolerant with IOVDD at 3.3 V; VIH 2.0 V against NMOS VOH 2.4 V (+0.40 V)',
   keys('U_RP', 'J_EDGE', 'U_INV', 'U_PHI2'), nets(*ADDR, 'EN40_N', 'EN80_N', 'PWR_OK', 'PHI2_RP'),
   [('RP2354B', 1341, 'IOVDD=3.3V 2 5.5 V'), ('RP2354B', 1340, 'VPIN_FT'),
    ('RP2354B', 14, 'GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)')],
   {'description': 'VIH(FT) at IOVDD 3.3 V vs TTL / NMOS VOH; GPIO40-47 (not FT) carry only the ADC and the 3.3 V debug UART (check_nets.py)',
    'script': M, 'result': '+0.40 V (NMOS), +0.70 V (LS)'}),
 f('io', 'info', 'high',
   'RP2350-E9: BUF_EN (and the DNP interlock driver\'s ILK) carry 4.7k pull-downs (<= 8.2k), so a pad left as an input between VIL and VIH cannot latch near 2.2 V and open the \'541 onto the console bus',
   [K['U_RP']] + E9 + GLUE, nets('BUF_EN', 'ILK'),
   [('RP2354B', 1367, 'Increased leakage current on Bank 0 GPIO when pad input is enabled'),
    ('RP2354B', 1368, 'with a low impedance source of 8.2 kΩ or less will overcome the erroneous leakage')],
   {'description': 'E9: ~120 uA sourced by the pad, holding it near 2.2 V; 120 uA x 4.7k', 'script': M,
    'result': 'worst 0.56 V (< 74HCT VIL 0.8 V); 0.70 mA while GPIO26 drives high'},
   'The bus inputs (A0-A13, enables, PWR_OK, PHI2_RP) are driven by the console or 5 V logic, so E9 cannot hold them mid-rail.'),
 f('io', 'info', 'high',
   'VSENSE_ADC: CONS_5V through %s / %s 100k / 100k = 0.5 x onto GPIO40 (ADC0, not FT): 2.25-2.75 V for a 4.5-5.5 V console rail, under the 3.3 V full scale; %s 100 nF for the sample capacitor' % tuple(keys('R_ADCH', 'R_ADCL', 'C_ADCF')),
   keys('R_ADCH', 'R_ADCL', 'C_ADCF', 'U_RP'), nets('VSENSE_ADC', 'CONS_5V'),
   [('RP2354B', 1341, 'IOVDD=3.3V 2 5.5 V')],
   {'description': 'ratio and the pad current before IOVDD is up', 'script': M, 'result': '0.50 x; <= 25 uA into the pad unpowered'},
   'The first Rev0 used 100k / 22k for a 12 V pin 26 that does not exist; a52_cart.h still says "12 V-safe divider".',
   'Firmware: correct the VSENSE_PIN comment (0.5 x of a 5 V rail).'),
 # ======================= sourcing =======================
 f('sourcing', 'info', 'high',
   'Every BOM line is in JLCPCB stock (2026-10-08), including SN74HCT08DR C6767 (the first Rev0 said no 74HCT08 was stocked), SN74HCT541PWR C436096, 74LVC1G17GW C426705, AP63205WU C2071056, 1206L035/30WR C2153989; WS2812B-2020-V6 C52917434 replaces the WS2812C-2020-V1 (stock 0)',
   keys('U_AND', 'U_BUF', 'U_PHI2', 'U_PRE', 'F_UNREG', 'D_WS'), nets('EN_ANY_N', 'WS_DIN'),
   [('WS2812B-2020-V6', 3, '+3.7~+5.3'), ('WS2812B-2020-V6', 3, 'High Voltage Input')],
   {'description': "JLCPCB's own parts API per LCSC code (jlcsearch's index misses codes)", 'script': SRC,
    'result': '0 lines short for 5 boards'},
   'WS2812B-2020-V6: same 2020 package and pin order (1 DO, 2 GND, 3 DI, 4 VDD) as the WS2812C; VIH 2.7 V takes the S3 3.3 V data; 12 mA per channel goes into the budget.'),
 # ======================= the shared FujiNet half =======================
 f('power', 'info', 'high',
   'Whole RP2354B on the AP2112K (+3V3_RP), so IOVDD is up before the console bus can exceed the FT unpowered limit; VREG_VIN and VREG_AVDD together on that rail',
   keys('U_RP', 'U_LDO'), nets('+3V3_RP', 'VREG_AVDD', 'DVDD'),
   [('AP2112K-3.3TRG1', 4, 'Start-up Time'), ('RP2354B', 1340, 'VPIN_FT'),
    ('RP2354B', 444, 'With the exception of the two voltage regulator supplies'), ('RP2354B', 455, 'must be RC filtered')],
   {'description': 'design.py vs SMS Rev0 design.py, part by part (rp-core sheet)', 'script': CN,
    'result': 'RP core, LDO and every rp-core passive identical to the SMS / NES / 7800 boards'}),
 f('power', 'info', 'high', 'RP2354B supply pins: IOVDD 5, 15, 24, 29, 41, 50, 60, 76; DVDD 10, 32, 51; GPIO pin numbers checked against the datasheet table',
   [K['U_RP']], nets('+3V3_RP', 'DVDD'),
   [('RP2354B', 1339, '5, 15, 24, 29, 41, 50, 60, 76')],
   {'description': 'RP_GPIO_PIN and the supply pins parsed against the QFN-80 table', 'script': CN, 'result': 'all match'}),
 f('power', 'info', 'high', 'AP63203 / AP63205 inputs: +5V (4.3-5.25 V) and PRE_VIN (8-13 V), inside 3.8-32 V; AP2112K EN tied to VIN',
   keys('U_BUCK', 'U_PRE', 'U_LDO'), nets('+5V', '+3V3', 'PRE_VIN'),
   [('AP63203WU-7', 1, '3.8V to 32V'), ('AP63205WU-7', 1, '3.8V to 32V'), ('AP2112K-3.3TRG1', 4, 'VEN High Voltage')],
   {'description': 'rail ranges from the three-source OR and the raw DC path', 'script': M, 'result': 'all inside'}),
 f('usb', 'info', 'high', 'CP2102N VBUS sense 22k/47k: 3.41 V at 5 V, between VIH (VIO - 0.6 V) and VIO + 2.5 V',
   keys('U_UART', 'R_VBSH', 'R_VBSL'), nets('VBUS_SNS', 'VBUS'),
   [('CP2102N-A02-GQFN28R', 8, 'There are two relevant restrictions on the VBUS pin voltage')],
   {'description': '5 V x 47 / 69', 'script': M, 'result': '3.41 V'}),
 f('mcu', 'info', 'high', 'ESP32-S3 EN RC 10k / 1 uF as Espressif recommends; RESET reaches EN through the BAT54C',
   [K['U_S3']] + cap('S3_EN'), nets('S3_EN'),
   [('ESP32-S3-WROOM-1-N16R8', 41, 'RC delay circuit at the EN pin')],
   {'description': 'tau = 10 ms', 'script': CN, 'result': 'S3_EN: R6 10k to +3V3, C8 1 uF, SW3, D5, U3'}),
 f('led', 'info', 'high', 'WS2812B-2020-V6 on +5V: VDD 3.7-5.3 V covers 4.3-5.25 V; VIH 2.7 V takes the S3 3.3 V data through 330R; 36 mA at full white',
   [K['D_WS']], nets('+5V', 'WS_DIN'),
   [('WS2812B-2020-V6', 3, '+3.7~+5.3'), ('WS2812B-2020-V6', 3, 'High Voltage Input'), ('WS2812B-2020-V6', 1, '12mA operating current per channel')],
   {'description': 'rail range vs VDD; 3 x 12 mA', 'script': M, 'result': '36 mA'}),
 f('led', 'info', 'high', 'Activity LED red KT-0603R from GPIO27 through 1k: 1.3-1.5 mA',
   keys('D_LED', 'R_LED', 'U_RP'), nets('RP_LED', 'RP_LED_A'),
   [('KT-0603R', 3, 'Forward Voltage')],
   {'description': '(3.3 V - VF 1.8-2.0 V) / 1k', 'script': M, 'result': '1.3-1.5 mA'}),
 f('oscillator', 'info', 'high', 'ABM8-272-T3 (CL 10 pF): 2 x 15 pF + ~3 pF stray = 10.5 pF; 1k in XOUT as the RP2350 minimal design',
   [K['Y_RP']] + cap('XIN') + cap('XOUT_Y'), nets('XIN', 'XOUT_Y'),
   [('ABM8-272-T3', 1, 'Load capacitance')],
   {'description': 'series load', 'script': M, 'result': '10.5 pF'}),
 f('usb', 'info', 'high', 'RP USB D+/D- through 27R to the S3 USB host pins', keys('U_RP', 'R_USBP', 'R_USBM'),
   nets('RP_USB_DP', 'RP_USB_DM', 'USB_DP', 'USB_DM'),
   [('RP2354B', 1336, 'external 27Ω series resistors')],
   {'description': 'netlist', 'script': CN, 'result': 'R16 / R17 27R'}),
 f('thermal', 'info', 'high', 'RP LDO dissipation 51-102 mW at 30-60 mA from 5 V (Tj +13..+26 C); the RP core regulator is a switcher, so the LDO never carries the core current',
   keys('U_LDO', 'U_RP'), nets('+3V3_RP'),
   [('RP2354B', 1348, 'hello_usb')],
   {'description': '(5.0 - 3.3 V) x I, SOT-23-5 ~250 C/W', 'script': M, 'result': '51 mW / 102 mW'}),
]

out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1, ensure_ascii=False)
print('deep_review.json: %d findings for run %s' % (len(F), run))
