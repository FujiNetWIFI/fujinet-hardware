#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev1 datasheet pass.  Component refs
come from tools/design.py so they track regeneration; pages were located
with tools/audit/find_quote_page.py (pdftotext page index)."""
import datetime, json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

def ref(value=None, desc=None, nth=0):
    hits = [p for p in D.PARTS if (value is None or p.value == value) and (desc is None or desc in p.desc)]
    return hits[nth].ref
RPA, RPB = D.ROLE_REF['rp_a'], D.ROLE_REF['rp_b']
LDOA, LDOB = D.ROLE_REF['ldo_a'], D.ROLE_REF['ldo_b']
YA, YB = D.ROLE_REF['y_a'], D.ROLE_REF['y_b']
LA, LB = D.ROLE_REF['l_a'], D.ROLE_REF['l_b']
DLED = D.ROLE_REF['led']
UCIC, US3, UCP, UMH, UBUCK = (ref(v) for v in ('ATtiny13A-SSU', 'ESP32-S3-WROOM-1-N16R8', 'CP2102N-A02-GQFN28', 'UMH3N', 'AP63203WU'))
QFET, DBAT, DWS, DSS = ref('AO3401A'), ref('BAT54C'), ref('WS2812B-2020-V6'), ref('SS34')
J1, J2 = ref('NES_Cart_Edge_72'), ref('microSD')
RTOP, RBOT = ref(desc='console 5V sense, top'), ref(desc='console 5V sense, bottom')
RLED = ref(desc='status LED series')
run = json.load(open(os.path.join(PRJ, 'analysis', 'manifest.json')))['current']
H = 'tools/audit/'

def f(cat, sev, conf, summary, comps, nets, ds=(), comp=None, desc='', rec=''):
    ev = {'components': comps, 'nets': nets}
    if ds:
        ev['datasheet'] = [{'mpn': m, 'page': p, 'quote': q} for m, p, q in ds]
    if comp:
        ev['computation'] = comp
    return {'detector': 'deep_review', 'category': cat, 'severity': sev, 'confidence': conf, 'summary': summary,
            'description': desc, 'recommendation': rec, 'evidence': ev}

F = [
 f('power', 'info', 'high', 'Each RP2354B (IOVDD group, VREG_VIN, VREG_AVDD) has its own 20 us LDO off +5V, so its pads are powered before the console bus is',
   [RPA, RPB, LDOA, LDOB, UBUCK], ['+3V3_RP', '+3V3_RPB', '+5V'],
   [('RP2354B', 14, 'GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)'),
    ('RP2354B', 1336, 'tolerate voltages up to 5.5 V, provided IOVDD is powered to 3.3 V'),
    ('AP2112K-3.3TRG1', 4, 'Start-up Time'), ('AP63203WU-7', 5, 'Soft-Start Period')],
   {'description': 'AP63203 soft-start 4 ms (datasheet) vs AP2112K start-up 20 us; per RP ~60 mA (core SMPS input + IOVDD) at (5.0 - 3.3) V',
    'result': '~0.10 W per LDO; theta-JC 96 C/W (SOT25), theta-JA on the 6-layer planes well under 250 C/W -> < +25 C'},
   "Rev0's rule, kept for both RPs: the CPU bus (RP-A) and the PPU bus (RP-B) are driven by the console's NMOS parts at 5 V from the moment the console is on, so each RP's whole supply group sits on an AP2112K straight off the 5 V rail rather than on the buck. Two LDOs rather than one (one would carry ~120 mA, +34 C at 184 C/W): a layout and isolation choice, each LDO beside its RP's island.",
   'Bring-up: scope +3V3_RP / +3V3_RPB against CONS_5V at console power-on.'),
 f('power', 'info', 'high', 'RP2350 supply order: only VREG_VIN and VREG_AVDD must rise together (both on the RP\'s own LDO rail, for both RPs)',
   [RPA, RPB, LDOA, LDOB], ['+3V3_RP', '+3V3_RPB', 'VREG_AVDD', 'VREG_AVDD_B'],
   [('RP2354B', 444, 'With the exception of the two voltage regulator supplies'), ('RP2354B', 444, 'may be powered up or down in any order')],
   None, 'VREG_VIN (pin 64) and VREG_AVDD (pin 61, through 33R) share each RP\'s LDO rail with its IOVDD group.'),
 f('io', 'info', 'high', 'PWR_OK = 0.6 x CONS_5V (2.2k / 3.3k) straight into RP-A GP26 and RP-B GP24 / GP44 (ADC4): under the 3.63 V fault-tolerant limit unpowered, and a 1.32k source against erratum E9',
   [RTOP, RBOT, RPA, RPB], ['PWR_OK', 'CONS_5V'],
   [('RP2354B', 1336, 'very little current flows into the pin whilst it is below 3.63 V and IOVDD is 0 V'),
    ('RP2354B', 1367, 'Increased leakage current on Bank 0 GPIO when pad input is enabled'),
    ('RP2354B', 1368, 'Driving / pulling the pad input low with a low impedance source of 8.2 kΩ or less'),
    ('RP2354B', 1343, '0.65*IOVDD')],
   {'description': 'divider 3.3/(2.2+3.3); Thevenin 2.2k || 3.3k; VIH 0.65 x 3.3 V', 'script': 'tools/check_nets.py',
    'result': '3.30 V at 5.5 V (< 3.63), 2.70 V at 4.5 V (> 2.15 VIH), source 1.32k (< 8.2k)'},
   "Rev0's 0.82 x CONS_5V divider fed a 5 V 74HCT14, which Rev1 no longer has; wired into an RP GPIO it would put 4.5 V on a pad whose IOVDD may still be 0 V. E9 (A2 silicon) makes a high-impedance divider hold a floating-ish pad near 2.2 V; 1.32k source and a 3.3k bottom keep it out of that region. check_nets.py asserts the ratio, both limits and the impedance.",
   'Bring-up: read RP-B ADC4 against a meter on CONS_5V (firmware reports console 5 V min/max).'),
 f('io', 'info', 'medium', 'Bus outputs stay high-impedance until PWR_OK: RP-A CD0-7, RP-B PD0-7 / CIRAM A10 / CIRAM /CE are gated in firmware (OEOVER), replacing Rev0\'s tri-state \'253 and gated \'595',
   [RPA, RPB, J1], ['CD0', 'PD0', 'CIRAM_A10', 'CIRAM_CE_N', 'PWR_OK'],
   [('RP2354B', 14, 'GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)')],
   None, "With the cart on USB and the console off, the console's CIRAM and data buses must not be driven (they would back-power the console). Rev0 did this in logic ('253 /OE = PWR_OK_N); Rev1 has no glue, so the PWR_OK interrupt and the OEOVER overrides set up first thing in main() are the only gate. Out of reset the pads are inputs with pull-downs, so nothing is driven before firmware runs.",
   'Firmware review item: OEOVER before any SIO/PIO output enable; PWR_OK falling edge drops the overrides within one interrupt.'),
 f('logic', 'info', 'high', 'WS2812B-2020 on the 5 V rail: datasheet VDD is 3.7-5.3 V, VIH 2.7 V takes the 3.3 V data line',
   [DWS], ['+5V', 'WS_DIN'],
   [('WS2812B-2020-V6', 3, '+3.7~+5.3'), ('WS2812B-2020-V6', 3, '2.7V')],
   None, 'Unchanged from Rev0.'),
 f('led', 'info', 'high', 'Status LED is now a red KT-0603R (VF 1.8-2.4 V) from RP-A GP27 through 330R: the old green (VF 3.1 V) could not light from a 3.3 V GPIO',
   [DLED, RLED, RPA], ['LED'],
   [('KT-0603R', 3, 'Forward Voltage')],
   {'description': '(VOH ~3.0 V - VF 1.9 V) / 330R', 'result': '~3 mA'},
   "Rev0 drove its KT-0603G from 5 V through the '595; in Rev1 the LED hangs on an RP GPIO. JLC CPL: C2286's EasyEDA footprint numbers the cathode pad 2, so its rotation was measured cathode to cathode (tools/audit/jlc)."),
 f('power', 'info', 'high', 'Console 5 V enters through an AO3401A P-FET (gate = VBUS, 4.7k pull-down): ~24 mV drop, USB never back-feeds the console',
   [QFET, DSS], ['CONS_5V', '+5V', 'VBUS'],
   [('AO3401A', 2, 'Gate Threshold Voltage')],
   {'description': 'Rds(on) < 60 mOhm at Vgs -4.5 V times the cart load', 'result': '0.4 A -> 24 mV'},
   'Unchanged from Rev0: with VBUS present the gate is at VBUS, the FET is off and only its body diode (into the cart) remains; without USB the 4.7k holds the gate at 0 V and the FET is fully on.'),
 f('pinout', 'info', 'high', 'RP2354B QFN-80 pin table (48 GPIO, 8 IOVDD, 3 DVDD, VREG 61-65, USB 66/67, QSPI 69-75) matches design.py, both instances', [RPA, RPB], [],
   [('RP2354B', 17, 'Pinout for QFN-80')], None, 'Figure 3 read against RP_GPIO_PIN; gen_sch.py also checks the table against the KiCad symbol; check_nets.py checks both GPIO maps against the firmware headers (nes_bus.h, nes_cart.h, nes_ppu.h) and the link mirror.'),
 f('pinout', 'info', 'high', 'CP2102N QFN28: 6 VDD, 7 VREGIN (both 3V3, regulator bypassed), 8 VBUS sense, 9 RSTb, 23 CTS, 24 RTS, 25 RXD, 26 TXD, 28 DTR', [UCP], [],
   [('CP2102N-A02-GQFN28R', 28, '5V Regulator Input'), ('CP2102N-A02-GQFN28R', 28, 'VBUS Sense Input')]),
 f('pinout', 'info', 'high', 'UMH3N: 1 E1, 2 B1, 3 C2, 4 E2, 5 B2, 6 C1 (ROHM inner circuit) = DevKitC-1 auto-program wiring', [UMH], [],
   [('UMH3N_Farnell', 1, 'Inner circuit'), ('UMH3N', 1, 'Two DTC143T chips in a package')]),
 f('pinout', 'info', 'high', 'AP63203WU TSOT26: 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST', [UBUCK], [], [('AP63203WU-7', 2, 'Power Ground')]),
 f('pinout', 'info', 'high', 'AP2112K SOT-25: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT (both)', [LDOA, LDOB], [], [('AP2112K-3.3TRG1', 4, 'Output Voltage')]),
 f('pinout', 'info', 'high', 'AO3401A SOT-23: 1 G, 2 S, 3 D', [QFET], [], [('AO3401A', 1, '30V P-Channel MOSFET')]),
 f('pinout', 'info', 'high', 'ATtiny13A SOIC-8: 1 RESET/PB5, 2 PB3 (CLK), 3 PB4, 4 GND, 5 PB0 (toMB), 6 PB1 (toPak), 7 PB2 (+RST), 8 VCC', [UCIC], [],
   [('ATTINY13A-SSUR', 2, '(PCINT3/CLKI/ADC3) PB3'), ('ATTINY13A-SSUR', 2, '(MOSI/AIN0/OC0A/PCINT0)')]),
 f('pinout', 'info', 'medium', 'BAT54C common cathode on pin 3, anodes 1 and 2 (package drawing)', [DBAT], [],
   [('BAT54C', 1, 'Polarity: See Diagrams Below')], None, 'Verified from the SOT23 diagram on page 1 of the Diodes datasheet (no pin table in text).'),
 f('pinout', 'info', 'high', 'ESP32-S3-WROOM-1 pads 13/14 = IO19/IO20 (USB D-/D+), 36/37 = RXD0/TXD0, 25 = IO48, 31 = IO38, 35 = IO42', [US3], [],
   [('ESP32-S3-WROOM-1-N16R8', 12, 'U0TXD, GPIO43'), ('ESP32-S3-WROOM-1-N16R8', 11, 'USB_D-')]),
 f('pinout', 'info', 'high', 'TF-015: 1 DAT2, 2 CD/DAT3, 3 CMD, 4 VDD, 5 CLK, 6 VSS, 7 DAT0, 8 DAT1', [J2], [], [('TF-015', 2, 'Card Detect')]),
 f('oscillator', 'info', 'high', 'ABM8-272-T3 CL 10 pF: 15 pF load caps give 10.5 pF with stray (both crystals)', [YA, YB], ['XIN', 'XOUT_Y', 'XIN_B', 'XOUT_Y_B'],
   [('ABM8-272-T3', 1, 'Load capacitance (CL)')], {'description': 'CL = 15*15/(15+15) + 3 pF stray (spice run)', 'result': '10.5 pF'}),
 f('mechanical', 'info', 'high', 'Edge footprint: pin 1 east on F.Cu, 2.0 x 12 mm fingers, 2.50 mm pitch, copper 1.0-13.0 mm from the edge (NES-EWROM-01)',
   [J1], [], (), {'description': 'compare NES_Cart_Edge_72.kicad_mod with the measured reference pads', 'script': H + 'edge_orientation.py',
                 'result': 'pin 1 east on F.Cu, geometry matches NES-EWROM-01'}),
 f('mechanical', 'info', 'high', 'Fab zip checked finger by finger: 36 fingers a face at their pads, mask windows 6.5 / 11 mm, no inner copper, drill, paste or silk on the tab',
   [J1], [], (), {'description': 'the exported gerbers and drills against the edge footprint and the outline', 'script': H + 'check_gerbers.py',
                 'result': '0 failures'}),
 f('io', 'info', 'medium', 'RP2350 VIH is 0.65 x IOVDD = 2.15 V against NMOS 2A03/2C02 outputs (VOH ~2.4 V min): thin, the same margin every CMOS cart lives with, now on both buses',
   [RPA, RPB, J1], ['M2', 'RW', 'ROMSEL_N', 'PPU_RD_N', 'PPU_WR_N'], [('RP2354B', 1343, '0.65*IOVDD')], None, '',
   'Bring-up: check M2, R/W, /RD, /WR and PPU A10-A13 high levels at the RP pins.'),
 f('sourcing', 'warning', 'high', 'AOTA-B201610S3R3-101-T (C42411119), the RP2350 core inductor, is at 0 LCSC stock; Rev1 needs two',
   [LA, LB], [], (), {'description': 'LCSC product detail on 2026-10-19 (scratch bomcost.py, tools/lcsc.py)', 'script': 'tools/lcsc.py',
                     'result': 'C42411119 stock 0; RP2354B C39843328 2316; also 0 at LCSC: C2913202 (ESP32-S3 module), '
                               'C21190 / C25819 (1k / 47k, JLC Basic parts); C62684 (buck inductor) no longer listed'},
   "Rev0 has the same part. Rev1's SRAMs and '253, Rev0's other zero-stock lines, are gone. The other "
   "zero-stock lines are shared with Rev0; the two resistors are JLC Basic parts, which JLC stocks itself.",
   'Consign the inductors or substitute a 3.3 uH 2016 part with the RP2350 datasheet\'s DCR/saturation limits. '
   'At order time check JLC stock for the ESP32-S3 module and the buck inductor.'),
]
out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1)
print('deep_review.json: %d findings for run %s' % (len(F), run))
