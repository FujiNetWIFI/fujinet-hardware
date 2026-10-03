#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev0 datasheet pass (kicad-happy deep
review format).  Component refs come from tools/design.py so they track
regeneration; datasheet pages were located with tools/audit/find_quote_page.py
against the PDFs in datasheets/ (clean-MPN symlinks)."""
import datetime, json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D


def ref(value=None, desc=None, nth=0):
    hits = [p for p in D.PARTS if (value is None or p.value == value) and (desc is None or desc in p.desc)]
    return hits[nth].ref


U1, US3, UCP, UMH, UBUCK, ULDO = (ref(v) for v in ('RP2354A', 'ESP32-S3-WROOM-1-N16R8', 'CP2102N-A02-GQFN28',
                                                   'UMH3N', 'AP63203WU', 'AP2112K-3.3'))
DBAT, DLED, DWS = ref('BAT54C'), ref('green'), ref('WS2812B-2020-V6')
DCON, DUSB = ref(desc='console 5V OR-ing'), ref(desc='USB VBUS OR-ing')
Y1, J1, J2, J3 = ref('12MHz'), ref('Astrocade_Cart_Edge_26'), ref('microSD'), ref('USB-C')
RTOP, RBOT = ref(desc='console 5V sense (GP26'), ref(desc='console 5V sense -> 3.0V')
RCCS, RCD, RLED = ref(desc='/CCS idle-high'), ref(desc='card-detect pull-up'), ref(desc='LED series')
CVB1, CVB2 = ref(desc='VBUS decoupling at the connector'), ref(desc='VBUS HF decoupling')
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
 f('power', 'info', 'high', 'RP2354A (all supplies) moved from the 4 ms buck to a 20 us LDO, so its 5 V-tolerant pads are powered before the console bus is',
   [U1, ULDO, UBUCK], ['+3V3_RP', '+5V', 'CONS_5V'],
   [('RP2354A', 14, 'GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)'),
    ('RP2354A', 1332, 'provided IOVDD is powered to 3.3 V'),
    ('AP2112K-3.3TRG1', 4, 'Start-up Time'), ('AP2112K-3.3TRG1', 4, 'Short Current Limit'),
    ('AP63203WU-7', 5, 'Soft-Start Period')],
   {'description': 'AP63203 tSS 4 ms (after UVLO) vs the LDO tracking the console ramp in dropout; 21.3 uF on +3V3_RP '
                   'against the 50 mA fold-back limit; LDO dissipation at ~60 mA', 'script': H + 'por_window.py',
    'result': 'tracks a console ramp up to ~2.3 V/ms (1 V/ms needs 21 mA); a hot-plug step takes up to 1.4 ms; 79 mW, ~+20 C'},
   'The first Rev0 fed IOVDD from the buck: on console power its soft-start left the RP pads unpowered for up to 4 ms '
   'while the console drove A0-A12 and /CCS at 5 V -- outside the datasheet condition (the README listed it as a bring-up '
   'risk).  Every RP supply pin (IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN, VREG_AVDD via 33R) is now on '
   '+3V3_RP from an AP2112K-3.3 straight off +5V.',
   'Bring-up: scope +3V3_RP against CONS_5V and CA0 at a console cold start.'),
 f('power', 'info', 'high', 'RP2350 supply order: only VREG_VIN and VREG_AVDD must rise together; both are on the LDO rail',
   [U1, ULDO], ['+3V3_RP', 'VREG_AVDD'],
   [('RP2354A', 402, 'which should be powered up together')]),
 f('power', 'info', 'high', 'Diode OR keeps headroom: +5V >= 4.37 V at a 4.75 V console rail (buck VIN min 3.8 V, LDO 3.55 V, WS2812 3.7 V)',
   [DCON, DUSB, UBUCK, ULDO, DWS], ['+5V', 'CONS_5V', 'VBUS'],
   [('SS34', 3, 'Forward Voltage'), ('AP63203WU-7', 5, 'Soft-Start Period')],
   {'description': 'CONS_5V - VF(SS34 ~0.38 V at 0.4 A) against each load minimum', 'script': H + 'por_window.py',
    'result': 'margins 0.57 V (buck), 0.82 V (LDO), 0.67 V (WS2812) at 4.75 V'},
   'Unlike the NES cart there is no 5 V logic here, so the Schottky drop costs nothing: no P-FET needed.'),
 f('io', 'info', 'high', 'WS2812B-2020-V6 moved to +5V: datasheet VDD 3.7-5.3 V (it is NOT a 3.3 V part); VIH 2.7 V takes the S3 3.3 V data',
   [DWS], ['+5V', 'WS_DIN'],
   [('WS2812B-2020-V6', 3, '+3.7~+5.3'), ('WS2812B-2020-V6', 3, 'High Voltage Input')],
   None, 'The first Rev0 powered it from +3V3 on the belief that the V6 part is 3.3 V-rated (its description said so); '
         'the LCSC datasheet for C52917434 does not support that.'),
 f('io', 'info', 'high', 'VSENSE divider 100k/150k: 3.0 V at 5.0 V, 3.30 V at 5.5 V on GP26 (plain ADC pad); reads high down to a 3.6 V console rail',
   [RTOP, RBOT, U1], ['VSENSE', 'CONS_5V'],
   [('RP2354A', 1339, '0.65*IOVDD')],
   {'description': 'CONS_5V x 0.6 vs IOVDD and VIH', 'script': H + 'por_window.py', 'result': '2.85-3.30 V for 4.75-5.5 V'}),
 f('io', 'info', 'medium', '/CCS pull-up on the RP rail: the cart serves only while /CCS is low AND VSENSE is high (firmware gate)',
   [RCCS, U1], ['CCS_N', 'VSENSE'], (),
   {'description': '+3V3_RP through the 10k pull-up into an unpowered console input clamp', 'result': '~0.3 mA'},
   'With a USB-powered cart in an unpowered console the 10k pull-up feeds ~0.3 mA into the console\'s input clamps; '
   'VSENSE (sensed before the OR diode) is low, so firmware never drives D0-D7 into the dead console.'),
 f('io', 'info', 'high', 'microSD card detect: TF-015 CD switch is open with no card and closes to the shell with a card in -> SD_CD low = card present',
   [J2, RCD], ['SD_CD'], [('TF-015', 1, 'CD PIN')], None,
   'The first Rev0 left the polarity as a bring-up question; the SOFNG drawing (page 1, "CARD DETECTION SWITCH" table) settles it.',
   'fujiversal-astrocade.h: PIN_CARD_DETECT = IO42, active low.'),
 f('usb', 'info', 'high', 'VBUS decoupling added at the USB-C (1 uF + 100 nF), as the analyzer rule UC-001 asked', [CVB1, CVB2, J3], ['VBUS'], (),
   {'description': 'kicad-happy UC-001 on the first Rev0 (no decoupling capacitor on VBUS at J3)', 'result': 'C24 1 uF + C25 100 nF on VBUS; UC-001 clear'}),
 f('led', 'info', 'high', 'RP activity LED was ~0.45 mA (1k from 3.3 V, green VF 2.85 V); 330R gives 1.4-2.1 mA',
   [DLED, RLED], ['RP_LED_A'], [('KT-0603G', 3, 'Forward Voltage')],
   {'description': '(3.3 - VF) / R', 'script': H + 'por_window.py', 'result': '0.45 mA -> 1.4-2.1 mA'}),
 f('timing', 'info', 'medium', 'Read budget: the RP must drive D0-D7 within ~590 ns of /CCS for an M1 fetch (Z80 at 1.79 MHz)',
   [U1, J1], ['CCS_N', 'CD0'], (),
   {'description': 'Z80 T = 558.7 ns; data sampled 2 T (M1) / 2.5 T (read) after T1; /MREQ + an assumed 100 ns console decode',
    'script': H + 'timing_margins.py', 'result': '588 ns (M1), 867 ns (read): ~88 RP clocks at 150 MHz'},
   'The console decoder delay is not published (assumed); the firmware latency is measured at bring-up.'),
 f('pinout', 'info', 'high', 'RP2354A QFN-60 pin table (GP0-29, IOVDD 1/11/20/30/38/45, DVDD 6/23/39, VREG 46-50, USB 51/52) checked against the KiCad symbol on every build',
   [U1], [], [('RP2354A', 16, 'RP2354A')], {'description': 'gen_sch.verify_pin_tables()', 'script': 'tools/gen_sch.py', 'result': 'pass'}),
 f('pinout', 'info', 'high', 'CP2102N QFN28: 6 VDD, 7 VREGIN (both +3V3, regulator bypassed), 8 VBUS sense, 9 RSTb, 24 RTS, 25 RXD, 26 TXD, 28 DTR', [UCP], [],
   [('CP2102N-A02-GQFN28R', 28, '5V Regulator Input'), ('CP2102N-A02-GQFN28R', 28, 'VBUS Sense Input')]),
 f('pinout', 'info', 'medium', 'UMH3N (two DTC143T): 1 E1, 2 B1, 3 C2, 4 E2, 5 B2, 6 C1 = the DevKitC-1 auto-program wiring', [UMH], [],
   [('UMH3N', 1, 'Two DTC143T chips in a package')], None, 'Pin order read from the JCET inner-circuit figure (no text table).'),
 f('pinout', 'info', 'high', 'AP63203WU TSOT26: 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST', [UBUCK], [], [('AP63203WU-7', 2, 'Power Ground')]),
 f('pinout', 'info', 'high', 'AP2112K SOT-25: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT', [ULDO], [], [('AP2112K-3.3TRG1', 4, 'Output Voltage')]),
 f('pinout', 'info', 'medium', 'BAT54C common cathode on pin 3 (RESET button), anodes 1 (RP RUN) and 2 (S3 EN)', [DBAT], [],
   [('BAT54C', 1, 'Polarity')], None, 'From the SOT-23 diagram on page 1 (no pin table in text).'),
 f('pinout', 'info', 'high', 'ESP32-S3-WROOM-1 pads 13/14 = IO19/IO20 (USB D-/D+), 36/37 = RXD0/TXD0', [US3], [],
   [('ESP32-S3-WROOM-1-N16R8', 12, 'U0TXD, GPIO43'), ('ESP32-S3-WROOM-1-N16R8', 11, 'USB_D-')]),
 f('oscillator', 'info', 'high', 'ABM8-272-T3 CL 10 pF: 15 pF load caps give ~10.5 pF with stray (SPICE pass)', [Y1], ['XIN', 'XOUT_Y'],
   [('ABM8-272-T3', 1, 'Load')]),
 f('mechanical', 'info', 'high', 'Contact land 1 is EAST in KiCad top view on B.Cu (Tilton: "looking at the cart slot, 1 to 26, left to right")',
   [J1], [], (), {'description': 'generated board vs the published orientation', 'script': H + 'edge_orientation.py',
                 'result': 'land 1 EAST on B.Cu = Tilton pin 1 at the left of the slot'}),
]
out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1)
print('deep_review.json: %d findings for run %s' % (len(F), run))
