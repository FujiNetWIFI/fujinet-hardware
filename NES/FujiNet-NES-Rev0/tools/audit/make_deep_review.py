#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev0 datasheet pass.  Component refs
come from tools/design.py so they track regeneration; pages were located
with analysis/helpers/find_quote_page.py."""
import datetime, json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

def ref(value=None, desc=None, nth=0):
    hits = [p for p in D.PARTS if (value is None or p.value == value) and (desc is None or desc in p.desc)]
    return hits[nth].ref
U1 = ref('RP2354B'); U2, U3 = ref('AS6C4008-55TIN', nth=0), ref('AS6C4008-55TIN', nth=1)
U595, U253, U14, U20, U00, U32 = (ref(v) for v in ('74HCT595', '74HCT253', '74HCT14', '74HCT20', '74HCT00', '74HCT32'))
UCIC, US3, UCP, UMH, UBUCK, ULDO = (ref(v) for v in ('ATtiny13A-SSU', 'ESP32-S3-WROOM-1-N16R8', 'CP2102N-A02-GQFN28', 'UMH3N', 'AP63203WU', 'AP2112K-3.3'))
QFET, DBAT, DLED, DWS, DSS = ref('AO3401A'), ref('BAT54C'), ref('green'), ref('WS2812B-2020-V6'), ref('SS34')
Y1, J1, J2 = ref('12MHz'), ref('NES_Cart_Edge_72'), ref('microSD')
RN100 = [p.ref for p in D.PARTS if p.value == '4x100k']
RTOP, RBOT = ref(desc='console 5V sense divider'), ref(desc='console 5V sense -> 0.82')
CPOR, RPOR = ref(desc="'595 power-on hold-off RC", nth=0), [p.ref for p in D.PARTS if "power-on hold-off" in p.desc and p.prefix == 'R'][0]
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
 f('power', 'info', 'high', 'RP2354B IOVDD group fed by a 20 us LDO so the pads are powered before the console bus is',
   [U1, ULDO, UBUCK], ['+3V3_RP', '+5V'],
   [('RP2354B', 14, 'GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)'),
    ('RP2354B', 1336, 'tolerate voltages up to 5.5 V, provided IOVDD is powered to 3.3 V'),
    ('AP2112K-3.3TRG1', 4, 'Start-up Time'), ('AP63203WU-7', 5, 'Soft-Start Period')],
   {'description': 'AP63203 soft-start 4 ms (datasheet) vs AP2112K start-up 20 us; IOVDD current ~30 mA', 'script': H + 'por_window.py',
    'result': 'LDO: ~30 mA IOVDD at (5.0-3.3) V = 51 mW'},
   'The first schematic fed IOVDD from the buck: on console-only power its 4 ms soft-start left the RP pads unpowered while the 2A03/PPU NMOS outputs were already at 5 V, outside the datasheet condition. The IOVDD/QSPI_IOVDD/USB_OTP_VDD/ADC_AVDD pins now sit on +3V3_RP from an AP2112K straight off the 5 V rail; VREG_VIN stays on the buck.',
   'Keep the LDO within ~10 mm of the RP; bring-up: scope IOVDD vs CONS_5V at console power-on.'),
 f('power', 'info', 'high', 'RP2350 supply order: only VREG_VIN and VREG_AVDD must rise together (both on the buck rail)',
   [U1, UBUCK, ULDO], ['+3V3', 'VREG_AVDD', '+3V3_RP'],
   [('RP2354B', 444, 'With the exception of the two voltage regulator supplies'), ('RP2354B', 444, 'may be powered up or down in any order')],
   None, 'VREG_VIN (pin 64) and VREG_AVDD (pin 61, through 33R) are both on +3V3; the IO rail may lead or lag.'),
 f('logic', 'info', 'high', 'Console-sense divider raised to 0.82 so the 74HCT14 always sees a powered console',
   [U14, RTOP, RBOT], ['VSENSE', 'CONS_5V'],
   [('SN74HCT14DR', 5, '3.13'), ('SN74HCT14DR', 5, 'Positive')],
   {'description': 'TI SN74HCT14 VT+ max 3.13 V at VCC 4.5 V = 0.70 x VCC; divider 100k/(22k+100k)', 'script': H + 'por_window.py',
    'result': '0.820 -> 3.69 V at VCC 4.5 V'},
   'The first schematic used 100k/150k (0.60): 2.70 V at a 4.5 V rail is below the worst-case VT+ of a TI part, so PWR_OK could stay low on a powered console. 22k/100k gives 0.82 x CONS_5V; the input stays under VCC + 0.5 V because the P-FET keeps VCC within a diode drop of CONS_5V.'),
 f('logic', 'info', 'high', 'WS2812B-2020 moved to the 5 V rail: datasheet VDD is 3.7-5.3 V, VIH 2.7 V takes the 3.3 V data line',
   [DWS], ['+5V', 'WS_DIN'],
   [('WS2812B-2020-V6', 3, '+3.7~+5.3'), ('WS2812B-2020-V6', 3, '2.7V')],
   None, 'The Astrocade-derived sheet ran the LED from +3V3 on the assumption the V6 part is 3.3 V-rated; the LCSC datasheet for C52917434 says otherwise.'),
 f('timing', 'info', 'medium', 'PRG SRAM /WE ends one 74HCT20 delay after M2 falls; write setup/pulse margins are large, hold depends on the PROVISIONAL 2A03 figure',
   [U2, U20, U14], ['PRG_WE_N', 'M2', 'ROMSEL'],
   [('AS6C4008-55TIN', 4, 'Data Hold from End of Write Time'), ('AS6C4008-55TIN', 4, 'Data to Write Time Overlap'), ('AS6C4008-55TIN', 4, 'Write Pulse Width')],
   {'description': 'NTSC bus vs AS6C4008-55 write parameters with the CD74HCT20 path', 'script': H + 'timing_margins.py',
    'result': '/WE rises 28 ns (worst) after M2 falls; 2A03 holds data 30 ns -> hold margin at /WE rise: +2 ns vs tDH 0 ns'},
   'The first schematic put /ROMSEL through the 14, 00 and 32 (up to 110 ns after M2 with the console decoder) against a ~30 ns data hold. Qualifying with M2 directly on a 4-input NAND leaves the console decoder out of the trailing edge. The 30 ns hold is nes_cart.h PROVISIONAL; bus capacitance makes real boards hold longer.',
   'Bring-up item: scope CPU D0-D7 against /WE on a loader copy.'),
 f('timing', 'info', 'high', 'PRG read path 113 ns worst after /ROMSEL against a 330 ns budget',
   [U2, U20, U14], ['PRG_CE_N', 'ROMSEL_N'],
   [('AS6C4008-55TIN', 4, 'Chip Enable Access Time')],
   {'description': '/CE through 14 + 20 then tACE 55 ns', 'script': H + 'timing_margins.py',
    'result': 'read: /CE via 14 + 20 (58 ns worst) + tACE 55 = 113 ns after /ROMSEL vs 330 ns budget'}),
 f('logic', 'info', 'high', "74HCT595 outputs held off ~70-170 ms after power-on and whenever the console is off; every bit pulled down",
   [U595, U00, U14, CPOR, RPOR] + RN100, ['SR_OE_N', 'POR_RC', 'POR', 'PWR_OK'],
   [('74HCT595D', 1, 'outputs to assume a high-impedance OFF-state'), ('SN74HCT14DR', 5, '1.55')],
   {'description': 'POR_RC = 1 uF to +5V / 100k to GND through the HCT14 Schmitt; SR_OE_N = NAND(PWR_OK, POR)', 'script': H + 'por_window.py',
    'result': 'VT- = 0.90 V: /OE released 171 ms after the 5 V rail is up'},
   'The first schematic tied /OE low: the storage register is undefined from power-on until the RP loads it (ms), and a random SRAM_EN=1 would put the PRG SRAM on the bus while the RP serves the reset vectors. With /OE gated and 100k pull-downs on all eight bits the enables default to 0 during the hold-off and while PWR_OK is low.'),
 f('logic', 'info', 'high', 'CIRAM /CE and CIRAM A10 both leave through the 74HCT253 and tri-state with PWR_OK_N',
   [U253, U32], ['CIRAM_CE_N', 'CIRAM_A10', 'PWR_OK_N', 'CIRAM_CE_PRE'],
   [('74HCT253_Nexperia', 1, 'assume a high-impedance OFF-state'), ('74HCT253_Nexperia', 3, 'multiplexer output source 2')],
   None, "The first schematic drove CIRAM /CE from a 74HCT32 output, which would push 5 V into the unpowered console's CIRAM while the cart ran on USB. The '32 now feeds all four data inputs of the '253's second half; its output enable is PWR_OK_N like the mirroring mux."),
 f('power', 'info', 'high', 'Console 5 V enters through an AO3401A P-FET (gate = VBUS): ~24 mV drop keeps the 74HCT rail at the console voltage',
   [QFET, DSS], ['CONS_5V', '+5V', 'VBUS'],
   [('AO3401A', 2, 'Gate Threshold Voltage'), ('SN74HCT14DR', 4, 'Supply voltage')],
   {'description': 'Rds(on) < 60 mOhm at Vgs -4.5 V times the cart load; 74HCT VCC minimum 4.5 V', 'script': H + 'por_window.py',
    'result': 'AO3401A: Rds(on) < 60 mOhm at Vgs -4.5 V; 0.4 A cart load -> 24 mV drop (SS34 was ~350 mV)'},
   'With VBUS present the gate is at VBUS, Vgs >= 0, the FET is off and only its body diode (pointing into the cart) remains, so USB never back-feeds the console. Without USB the 22k/47k VBUS sense divider holds the gate at 0 V and the FET is fully on.'),
 f('pinout', 'info', 'high', 'RP2354B QFN-80 pin table (48 GPIO, 8 IOVDD, 3 DVDD, VREG 61-65, USB 66/67, QSPI 69-75) matches design.py', [U1], [],
   [('RP2354B', 17, 'Pinout for QFN-80')], None, 'Figure 3 (page 16) read against RP_GPIO_PIN, RP_IOVDD_PINS, RP_DVDD_PINS and the rp dict; gen_sch.py also checks the table against the KiCad symbol.'),
 f('pinout', 'info', 'high', 'AS6C4008 TSOP-I/STSOP pin order (A11=1 ... OE#=32, A17=6, A18=9) matches SRAM_PIN', [U2, U3], [],
   [('AS6C4008-55TIN', 2, 'PIN CONFIGURATION')]),
 f('pinout', 'info', 'high', '74HCT595 pins: Q1-Q7 = 1-7, Q0 = 15, DS 14, SHCP 11, STCP 12, OE 13, MR 10', [U595], [],
   [('74HCT595D', 5, 'output enable input (active LOW)')]),
 f('pinout', 'info', 'high', '74HCT253 pins: 1OE 1, S1 2, 1I3..1I0 = 3..6, 1Y 7, 2Y 9, 2I0..2I3 = 10..13, S0 14, 2OE 15', [U253], [],
   [('74HCT253_Nexperia', 3, 'multiplexer output source 2')], None, 'S0 = MIR0, S1 = MIR1 so the select value is the firmware mirroring code (0 = PPU A10, 1 = PPU A11, 2 = 0, 3 = 1).'),
 f('pinout', 'info', 'high', '74HCT14 pin pairs 1-2, 3-4, 5-6, 9-8, 11-10, 13-12', [U14], [], [('SN74HCT14DR', 3, 'Positive')]),
 f('pinout', 'info', 'high', 'CP2102N QFN28: 6 VDD, 7 VREGIN (both 3V3, regulator bypassed), 8 VBUS sense, 9 RSTb, 23 CTS, 24 RTS, 25 RXD, 26 TXD, 28 DTR', [UCP], [],
   [('CP2102N-A02-GQFN28R', 28, '5V Regulator Input'), ('CP2102N-A02-GQFN28R', 28, 'VBUS Sense Input')]),
 f('pinout', 'info', 'high', 'UMH3N: 1 E1, 2 B1, 3 C2, 4 E2, 5 B2, 6 C1 (ROHM inner circuit) = DevKitC-1 auto-program wiring', [UMH], [],
   [('UMH3N_Farnell', 1, 'Inner circuit'), ('UMH3N', 1, 'Two DTC143T chips in a package')]),
 f('pinout', 'info', 'high', 'AP63203WU TSOT26: 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST', [UBUCK], [], [('AP63203WU-7', 2, 'Power Ground')]),
 f('pinout', 'info', 'high', 'AP2112K SOT-25: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT', [ULDO], [], [('AP2112K-3.3TRG1', 4, 'Output Voltage')]),
 f('pinout', 'info', 'high', 'AO3401A SOT-23: 1 G, 2 S, 3 D', [QFET], [], [('AO3401A', 1, '30V P-Channel MOSFET')]),
 f('pinout', 'info', 'high', 'ATtiny13A SOIC-8: 1 RESET/PB5, 2 PB3 (CLK), 3 PB4, 4 GND, 5 PB0 (toMB), 6 PB1 (toPak), 7 PB2 (+RST), 8 VCC', [UCIC], [],
   [('ATTINY13A-SSUR', 2, '(PCINT3/CLKI/ADC3) PB3'), ('ATTINY13A-SSUR', 2, '(MOSI/AIN0/OC0A/PCINT0)')]),
 f('pinout', 'info', 'medium', 'BAT54C common cathode on pin 3, anodes 1 and 2 (package drawing)', [DBAT], [],
   [('BAT54C', 1, 'Polarity: See Diagrams Below')], None, 'Verified from the SOT23 diagram on page 1 of the Diodes datasheet (no pin table in text).'),
 f('pinout', 'info', 'high', 'ESP32-S3-WROOM-1 pads 13/14 = IO19/IO20 (USB D-/D+), 36/37 = RXD0/TXD0, 25 = IO48, 31 = IO38, 35 = IO42', [US3], [],
   [('ESP32-S3-WROOM-1-N16R8', 12, 'U0TXD, GPIO43'), ('ESP32-S3-WROOM-1-N16R8', 11, 'USB_D-')]),
 f('pinout', 'info', 'high', 'TF-015: 1 DAT2, 2 CD/DAT3, 3 CMD, 4 VDD, 5 CLK, 6 VSS, 7 DAT0, 8 DAT1', [J2], [], [('TF-015', 2, 'Card Detect')]),
 f('oscillator', 'info', 'high', 'ABM8-272-T3 CL 10 pF: 15 pF load caps give 10.5 pF with stray', [Y1], ['XIN', 'XOUT_Y'],
   [('ABM8-272-T3', 1, 'Load capacitance (CL)')], {'description': 'CL = 15*15/(15+15) + 3 pF stray (spice run)', 'result': '10.5 pF'}),
 f('led', 'info', 'high', 'Activity LED ~2 mA through 1k from 5 V', [DLED], ['SR_LED_A'],
   [('KT-0603G', 3, 'Forward Voltage')], {'description': '(5.0 - 2.85 V) / 1k', 'script': H + 'por_window.py', 'result': '2.1 mA'}),
 f('mechanical', 'info', 'high', 'Edge footprint: pin 1 east on F.Cu, 2.0 x 12 mm fingers (ends 3.0 at +/-44.25), 2.50 mm pitch, copper 1.0-13.0 mm from the edge (NES-EWROM-01)',
   [J1], [], (), {'description': 'compare FujiNet-NES.pretty/NES_Cart_Edge_72.kicad_mod with the measured reference pads', 'script': H + 'edge_orientation.py',
                 'result': 'pin 1 east on F.Cu, geometry matches NES-EWROM-01'},
   'The first draft placed pad 1 west (mirrored) with 1.6 x 9.5 mm fingers 0.5 mm from the edge. nesdev: label side reads 36..1 left to right; both open-source references agree.'),
 f('io', 'info', 'medium', 'RP2350 VIH is 0.65 x IOVDD = 2.15 V against NMOS 2A03/2C02 outputs (VOH ~2.4 V min): thin but the same margin every CMOS cart lives with',
   [U1, J1], ['M2', 'RW', 'ROMSEL_N'], [('RP2354B', 1343, '0.65*IOVDD')], None, '', 'Bring-up: check M2/R/W/PPU A10-A12 high levels at the RP pins; the 74HCT inputs (VIH 2.0 V) have more room.'),
 f('sourcing', 'warning', 'high', 'AS6C4008-55TIN (C5569980) and every 74HCT253 are out of JLCPCB stock; CD74HCT20M96 has 460',
   [U2, U3, U253, U20], [], (), {'description': 'tools/lcsc.py --search AS6C4008 / 74HCT253 / 74HCT20 on 2026-10-01', 'script': 'tools/lcsc.py',
                                 'result': 'AS6C4008-55TIN 0, AS6C4008-55STIN 5, 74HCT253D 0, CD74HCT253M 0, CD74HCT20M96 460'},
   'CY62148ELL-45ZSXIT (C2952831, 50 pcs) is a 5 V TSOP-32 alternate but its A17/A18 pins must be checked against its own datasheet before substituting; the HCT253 is a DigiKey/Mouser part.',
   'Plan consigned parts or a second distributor for the SRAMs and the mux.'),
]
out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1)
print('deep_review.json: %d findings for run %s' % (len(F), run))
