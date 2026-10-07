#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev1 datasheet pass (kicad-happy Deep
Review).  Component references come from tools/design.py keys so they track
regeneration; datasheet pages were located with tools/audit/find_quote_page.py
in the PDFs datasheets/ holds (LCSC copies: page numbers are those files').
Computations: tools/audit/margins.py.  Validate with kicad-happy's
deep_review_gate.py (see README "Audit")."""
import datetime, json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

K = {k: v for k, v in D.KEY.items()}
R = lambda *keys: [K[k] for k in keys]
run = json.load(open(os.path.join(PRJ, 'analysis', 'manifest.json')))['current']
H = 'tools/audit/margins.py'


def f(cat, sev, conf, summary, comps, nets, ds=(), comp=None, desc='', rec=''):
    ev = {'components': comps, 'nets': nets}
    if ds:
        ev['datasheet'] = [{'mpn': m, 'page': p, 'quote': q} for m, p, q in ds]
    if comp:
        ev['computation'] = comp
    return {'detector': 'deep_review', 'category': cat, 'severity': sev, 'confidence': conf, 'summary': summary,
            'description': desc, 'recommendation': rec, 'evidence': ev}


BUS = ['CA%d' % i for i in range(13)] + ['CD%d' % i for i in range(8)]
F = [
 f('io', 'info', 'high', 'Cart bus wired straight to RP2354A GPIO2-22: all are Digital IO (FT), 5.5 V-tolerant while IOVDD is 3.3 V',
   R('U_RP', 'J_EDGE'), BUS,
   [('RP2354A', 14, 'GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)'),
    ('RP2354A', 1332, 'tolerate voltages up to 5.5 V, provided IOVDD is powered to 3.3 V'),
    ('RP2354A', 1336, 'VPIN_FT')],
   None,
   'A0-A12 on GP2-14 and D0-D7 on GP15-22 exactly as vcs_pins.h; every one is below GPIO26 (the QFN-60 ADC pins, which are not FT). '
   'A 3.3 V high clears the 6507/TIA/RIOT TTL VIH of 2.0 V. No buffer, so the firmware output enable alone sets the direction.',
   'Firmware: drop DIR_PIN, keep DATA_RELEASE before the address changes; scope D0-D7 contention at the A12 edge on hardware.'),
 f('power', 'info', 'high', 'Whole RP on the AP2112K (+3V3_RP, 20 us start-up) so IOVDD rises with the console 5 V before the bus can reach 3.63 V',
   R('U_RP', 'U_LDO', 'Q_CONS'), ['+3V3_RP', '+5V', 'CONS_5V'],
   [('AP2112K-3.3TRG1', 4, 'Start-up Time'), ('RP2354A', 1336, 'VPIN_FT')],
   {'description': 'LDO output tracks CONS_5V minus dropout; FT limit 3.63 V unpowered / 4.2 V at IOVDD 2.5 V / 5.5 V at 3.3 V',
    'script': H, 'result': 'AP2112K 51-102 mW at 30-60 mA from 5 V'},
   'The console bus lines are driven from the same 5 V rail that feeds the LDO through the P-FET, so they never exceed the FT limit for the IOVDD present.'),
 f('power', 'info', 'high', 'VREG_VIN and VREG_AVDD powered together from the 3.3 V LDO rail (combined supplies, Figure 19)',
   R('U_RP', 'R_FILT', 'C_FILT', 'C_VIN', 'L_VREG', 'C_VOUT'), ['+3V3_RP', 'VREG_AVDD', 'DVDD', 'RP_LX'],
   [('RP2354A', 402, 'With the exception of the two voltage regulator supplies'),
    ('RP2354A', 408, 'a single combined supply can be used for both VREG_VIN and'),
    ('RP2354A', 412, 'must be RC filtered'), ('RP2354A', 413, 'we recommend the AOTA-B201610S3R3-101-T')],
   None, '33R / 4.7 uF RC on VREG_AVDD, 4.7 uF C_IN and C_OUT, the polarity-marked AOTA 3.3 uH; the corner is Raspberry Pi\'s own minimal-design layout grafted at the RP.'),
 f('power', 'info', 'high', 'DVDD: 100 nF on pins 39 and 6, 4.7 uF on pin 23 (the far pin), all on the In2 DVDD island',
   R('U_RP', 'C_DVDD39', 'C_DVDD6', 'C_DVDD23'), ['DVDD'],
   [('RP2354A', 401, 'The DVDD pin furthest from the regulator should be decoupled')], None,
   'At the RP\'s 90 degree rotation pin 23 sits among the east-side escapes, so the three caps sit at the south-west corner on a DVDD lobe of In2 joined to the island under the core.'),
 f('pinout', 'info', 'high', 'RP2350 Table 1432 lists QFN-60 IOVDD as 11, 20, 30, 38, 45, 54; Figure 2 shows pin 1 = IOVDD and 54 = QSPI_IOVDD (table erratum)',
   R('U_RP'), ['+3V3_RP'],
   [('RP2354A', 1335, '11, 20, 30, 38, 45, 54'), ('RP2354A', 16, 'IOVDD 1')], None,
   'KiCad\'s RP2354A symbol follows the figure (IOVDD 1, 11, 20, 30, 38, 45). The board ties 1, 11, 20, 30, 38, 45 AND 54 to +3V3_RP, so it is right either way.'),
 f('io', 'info', 'high', 'Console 5 V sense on GPIO27 (ADC pin, not FT): 100k/150k = 3.15 V at 5.25 V, under IOVDD; 2.70 V at 4.5 V, over VIH',
   R('U_RP', 'R_VSH', 'R_VSL', 'C_VS'), ['VSENSE', 'CONS_5V'],
   [('RP2354A', 1331, 'GPIO26_ADC0')],
   {'description': 'VSENSE = CONS_5V x 150k / 250k', 'script': H, 'result': '2.70 V at 4.50 V, 3.15 V at 5.25 V, 3.30 V at 5.50 V; tau 6 ms'},
   'GPIO26 (the RP2040 board\'s DIR pin) is left unconnected so the unported firmware\'s DIR write is harmless.'),
 f('usb', 'info', 'high', 'RP USB D+/D- through 27R to the S3 (USB host)', R('U_RP', 'R_USBP', 'R_USBM', 'U_S3'),
   ['RP_USB_DP', 'RP_USB_DM', 'USB_DP', 'USB_DM'], [('RP2354A', 1333, 'external 27Ω series resistors')]),
 f('power', 'warning', 'high', 'SS34 reverse leakage lifts the P-FET gate (the VBUS net) when only the console powers the cart: 4.7k pull-down added',
   R('Q_CONS', 'D_VBUS', 'R_VBPD', 'R_VBH', 'R_VBL'), ['VBUS', 'CONS_5V', '+5V'],
   [('SS34', 2, 'Maximum DC reverse current'), ('AO3401A', 2, 'Gate Threshold Voltage')],
   {'description': 'gate = I_R x (R_VBPD || (22k + 47k)); AO3401A VGS(th) -0.5..-1.3 V, source ~5 V', 'script': H,
    'result': '500 uA -> 2.20 V, VGS -2.80 V (on); without the pull-down 50 uA already gives VGS -1.55 V'},
   'The 22k/47k CP2102N sense divider was the gate\'s only pull-down (69k). A warm Schottky reverse-biased by +5V could half-close the FET, leaving the console feeding the cart through the body diode (~0.7 V drop).',
   'Fitted: R_VBPD 4.7k VBUS-GND (0.5 mA from VBUS when USB is plugged in).'),
 f('led', 'info', 'high', 'WS2812B-2020 on +5V (datasheet VDD 3.7-5.3 V); VIH 2.7 V accepts the S3\'s 3.3 V data through 330R',
   R('D_WS', 'R_WS'), ['+5V', 'WS_DIN'],
   [('WS2812B-2020-V6', 3, '+3.7~+5.3'), ('WS2812B-2020-V6', 3, '2.7V'), ('WS2812B-2020-V6', 2, 'DATA IN')]),
 f('led', 'info', 'high', 'RP activity LED red (KT-0603R) from a 3.3 V pin through 680R: ~2 mA', R('D_LED', 'R_LED'), ['RP_LED', 'RP_LED_A'],
   [('KT-0603R', 3, 'Forward Voltage')], {'description': '(3.3 - 1.9 V) / 680R', 'script': H, 'result': '2.1 mA'},
   'Rev0\'s green part (VF 3.1 V) would barely light from 3.3 V.'),
 f('usb', 'info', 'high', 'CP2102N VBUS sense 22k/47k: 3.41 V at 5 V, between VIH (VIO - 0.6 = 2.7 V) and VIO + 2.5 V',
   R('U_UART', 'R_VBH', 'R_VBL'), ['VBUS_SNS', 'VBUS'],
   [('CP2102N-A02-GQFN28R', 8, 'There are two relevant restrictions on the VBUS pin voltage')],
   {'description': 'VBUS x 47k / 69k', 'script': H, 'result': '3.41 V at 5.0 V, 3.00 V at 4.4 V'}),
 f('mcu', 'info', 'high', 'ESP32-S3 EN RC 10k / 1 uF as Espressif recommends; RESET also pulls EN through the BAT54C',
   R('U_S3', 'R_EN', 'C_EN', 'D_RST'), ['S3_EN'], [('ESP32-S3-WROOM-1-N16R8', 41, 'RC delay circuit at the EN pin')]),
 f('oscillator', 'info', 'high', 'ABM8-272-T3 (CL 10 pF): 15 pF loads give 10.5 pF with stray; 1k in XOUT as the minimal design', R('Y_XTAL', 'C_XIN', 'C_XOUT', 'R_XOUT'),
   ['XIN', 'XOUT', 'XOUT_Y'], [('ABM8-272-T3', 1, 'Load capacitance')],
   {'description': '15 x 15 / 30 + 3 pF stray (also the SPICE run)', 'script': H, 'result': '10.5 pF'}),
 f('power', 'info', 'high', 'AP63203 input is +5V (4.3-5.0 V after the P-FET or Schottky), inside its 3.8-32 V range', R('U_BUCK', 'L_BUCK'),
   ['+5V', '+3V3', 'BUCK_SW'], [('AP63203WU-7', 1, '3.8V to 32V')]),
 f('power', 'info', 'high', 'AP2112K EN tied to VIN (+5V): EN high threshold 1.5 V, maximum 6.0 V', R('U_LDO'), ['+5V'],
   [('AP2112K-3.3TRG1', 4, 'VEN High Voltage')]),
 f('rf', 'warning', 'medium', 'ESP32-S3 antenna flush with the top edge over a copper-free band; side clearance short of the footprint\'s 15 mm',
   R('U_S3', 'J_USB'), [], [('ESP32-S3-WROOM-1-N16R8', 10, 'Keepout Zone')], None,
   'JLCPCB standard assembly (needed for gold fingers) adds edge rails, which rules out Rev0\'s 6.4 mm antenna overhang. '
   'The antenna band (top 6.8 mm, x < 97.6 mm) is copper-free on all four layers; the module footprint\'s own 48 x 21 mm keep-out is honoured on the board; '
   'the microSD moved to the right edge so the nearest metal (USB-C shell) is ~22 mm from the antenna centre.',
   'Bring-up: compare RSSI against an ESP32-S3 DevKit at the same spot; Rev2 option: a WROOM-1U (u.FL) module.'),
 f('thermal', 'info', 'high', 'RP LDO dissipation 27-68 mW (Tj 32-42 C): the analyzer\'s 95 C assumed a 165 mA heuristic load',
   R('U_LDO', 'U_RP'), ['+3V3_RP'], [('RP2354A', 1345, 'hello_usb')],
   {'description': 'RP2350 Table 1693 ~16 mA total at 3.3 V for a USB application; 40 mA allowed flat out', 'script': H,
    'result': '16 mA: 27 mW, Tj 32 C; 40 mA: 68 mW, Tj 42 C (SOT-23-5 at 250 C/W, 25 C ambient)'},
   'kicad-happy TS-003 (95 C) used (5.0 - 3.3 V) x 0.165 A, a generic LDO load; the RP2354A is the only load on +3V3_RP.'),
 f('usb', 'info', 'high', 'USB pairs are full-speed: 6.5 mm (RP-S3) and 5.7 mm (USB-C-CP2102N) length mismatch is ~40 ps against 4-20 ns edges',
   R('U_RP', 'U_S3', 'U_UART', 'J_USB'), ['USB_DP', 'USB_DM', 'UBRG_DP', 'UBRG_DM'], (),
   {'description': 'routed lengths from kicad-happy pcb.json (current run), 6.7 ps/mm', 'script': H,
    'result': 'USB_DP/DM 39.2/45.7 mm (44 ps), UBRG_DP/DM 20.8/26.4 mm (38 ps)'},
   'kicad-happy DP-001/DP-003/DP-004 apply high-speed rules; the RP2350, the S3 host port and the CP2102N are all 12 Mb/s full-speed, where neither the skew nor the two layer changes matter. No controlled impedance is ordered.'),
 f('emc', 'info', 'medium', 'Address lines on B.Cu reference In2, which is split (+3V3 / +3V3_RP / DVDD islands) under the RP; the bus is a 1.19 MHz TTL bus',
   R('U_RP', 'J_EDGE'), ['CA3', 'CA6', 'CA11'], (),
   {'description': 'kicad-happy GP-001 / RP-001 on the bus nets; inner planes stop 9 mm from the insertion edge by design (bevel)',
    'result': 'all In2 islands are decoupled to GND next to the RP; In1 is a solid GND plane under every F.Cu signal'},
   'The finger runs cross the plane setback at the tab (as every cartridge does) and the B.Cu runs cross island edges; at the 2600 bus rate (838 ns cycle, ns edges from the RP) the return-path detour is not an emissions concern for a prototype.',
   'If pre-compliance testing shows bus harmonics, a Rev2 can move the islands off the address-line paths.'),
]
out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1)
print('deep_review.json: %d findings for run %s' % (len(F), run))
