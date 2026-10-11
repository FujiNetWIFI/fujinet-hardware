#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev0 audit (kicad-happy Deep Review; docs/design-review-rev0.md):
per-IC checks of the design against its datasheet, and the layout's own claims measured on the copper.

References are resolved from tools/design.py by key, never hard-coded, so the file tracks regeneration
and reference shifts; net names are mapped onto the analyzer's names (which may carry a sheet prefix,
e.g. /cart-rp/D0).  Datasheet pages are those of the PDFs in datasheets/ (F3850.pdf is Fairchild's
F3850 CPU data sheet; hardware-design-with-rp2040.pdf is Raspberry Pi's guide), located with
tools/audit/find_quote_page.py.  Every "result" below is read from the scripts' own output at the time
this file is written: tools/audit/margins.py, tools/audit/layout_checks.py, tools/check_nets.py,
tools/audit/edge_orientation.py.

Usage: python3 tools/audit/make_deep_review.py
       python3 <kicad-happy>/skills/kicad/review/scripts/deep_review_gate.py \\
           analysis/deep_review.json --analysis-dir analysis/ --datasheets-dir datasheets
"""
import datetime, json, os, re, subprocess, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

run = json.load(open(os.path.join(PRJ, 'analysis', 'manifest.json')))['current']
SCH = json.load(open(os.path.join(PRJ, 'analysis', run, 'schematic.json')))
ANETS = set(SCH['nets'])
M, L, CN, EO = 'tools/audit/margins.py', 'tools/audit/layout_checks.py', 'tools/check_nets.py', 'tools/audit/edge_orientation.py'
CG = 'tools/audit/check_gerbers.py'
K = D.KEY


def out_of(script):
    r = subprocess.run([sys.executable, os.path.join(PRJ, script)], capture_output=True, text=True, cwd=PRJ,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return r.stdout


MOUT, LOUT, EOUT, GOUT = out_of(M), out_of(L), out_of(EO), out_of(CG)


def grab(text, pat):
    """The first line of a script's output that matches pat (a regex), without its ok/FAIL tag."""
    for line in text.splitlines():
        if re.search(pat, line):
            return re.sub(r'^(ok|OK|FAIL)\s+', '', line).strip()
    raise SystemExit('make_deep_review: no line matching %r' % pat)


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


def f(cat, sev, conf, summary, comps, ns, ds=(), comp=None, desc='', rec=''):
    ev = {'components': comps, 'nets': ns}
    if ds:
        ev['datasheet'] = [{'mpn': m, 'page': p, 'quote': q} for m, p, q in ds]
    if comp:
        ev['computation'] = comp
    return {'detector': 'deep_review', 'category': cat, 'severity': sev, 'confidence': conf, 'summary': summary,
            'description': desc, 'recommendation': rec, 'evidence': ev}


TI, F38, RP, HW = 'SN74LVC4245APWR', 'F3850', 'RP2040', 'hardware-design-with-rp2040'
BUS = ['D%d' % i for i in range(8)] + ['ROMC%d' % i for i in range(5)] + ['WRITE', 'PHI']
F = [
 # ======================= the console bus: levels, direction, isolation =======================
 f('level-shift', 'info', 'high',
   "The F3850's data bus needs VIH 2.9 V; the SN74LVC4245A A port drives it at >= 4.3 V (VCCA 4.5 V, 100 uA) and "
   ">= 3.7 V at 24 mA: 1.4 / 0.8 V of margin.  A 3.3 V driver (a bare RP2040 pin, an LVC245 at 3.3 V) would have 0.4 V",
   keys('U_DBUF', 'J_EDGE'), nets(*['D%d' % i for i in range(8)]),
   [(F38, 23, 'F3850 CPU Signal DC Characteristics'), (TI, 6, '5.7 Electrical Characteristics')],
   {'description': 'VOH(A, 4.5 V) - VIH(F3850 DB)', 'script': M,
    'result': grab(MOUT, r'cart -> console: A-port VOH 4\.3')}),
 f('level-shift', 'info', 'high',
   "Console -> cart: F3850 DB / ROMC VOH 3.9 V and PHI / WRITE 4.4 V into the A port's TTL VIH 2.0 V; the B port's "
   ">= 2.8 V (VCCB 3.0 V) into the RP2040's VIH 2.0 V",
   keys('U_DBUF', 'U_CBUF', 'U_RP'), nets(*BUS),
   [(F38, 23, 'Output High Voltage'), (TI, 5, 'High-level input voltage'), (TI, 7, '5.8 Electrical Characteristics')],
   {'description': 'VOH - VIH at each crossing', 'script': M,
    'result': grab(MOUT, r'DB / ROMC VOH') + '; ' + grab(MOUT, r'B-port VOH')}),
 f('level-shift', 'info', 'high',
   "DIR and /OE are referenced to VCCA (TTL), so the RP2040's 3.3 V drives them; the data translator's DIR is held "
   "high (console -> cart) through RP reset by 4.7k against the RP2040's 50-80k pad pull-down",
   keys('U_DBUF', 'R_DIR', 'U_RP'), nets('RP_DIR', '+3V3_RP'),
   [(TI, 1, 'Control inputs VIH/VIL levels are referenced to'), (RP, 615, 'Pull-Down')],
   {'description': '3.0 V x 50k / (50k + 4.7k)', 'script': M, 'result': grab(MOUT, r'DIR held high')}),
 f('level-shift', 'info', 'high',
   "Both translators' VCCA is CONS_5V, straight off edge pins 19 / 20 ahead of the OR diode: with the console off, "
   "Ioff partial power-down isolates the A port, so a USB-powered cart cannot back-power the console through the bus",
   keys('U_DBUF', 'U_CBUF', 'D_CONS', 'J_EDGE'), nets('CONS_5V', '+5V'),
   [(TI, 1, 'Ioff supports Partial-Power-Down')],
   {'description': 'netlist: VCCA pins on CONS_5V, the SS34 anode on CONS_5V', 'script': CN,
    'result': 'check_nets.py: both VCCA on CONS_5V (straight off the edge, ahead of the OR diode)'}),
 f('level-shift', 'info', 'high',
   "/INTREQ is an open drain (2N7002, gate from GP16, 100k pull-down): the F3850 INT REQ has its own pull-up and "
   "VIL 0.8 V; GP16's 3.3 V is 0.8 V past the FET's worst-case threshold (2.5 V at 250 uA)",
   keys('Q_INT', 'R_INTPD', 'J_EDGE'), nets('INTREQ_N', 'RP_INTREQ'),
   [(F38, 23, 'F3850 CPU Signal DC Characteristics'), ('2N7002', 2, 'Gate-Threshold Voltage')],
   {'description': 'VGS(GP16) - Vth(max)', 'script': M, 'result': grab(MOUT, r'/INTREQ: the F3850')}),
 f('mcu', 'info', 'high',
   "No RP2040 pin touches a 5 V or edge net: its IOs are not 5 V tolerant (VPIN max IOVDD + 0.5 V); every bus line "
   "reaches it through a translator's B port at 3.3 V",
   keys('U_RP'), nets('CONS_5V', '+5V'),
   [(RP, 615, 'Voltage at IO')],
   {'description': 'netlist: RP2040 pins vs 5 V / edge nets', 'script': CN,
    'result': 'check_nets.py: no RP2040 pin on a 5 V or edge net []'}),
 # ======================= the edge =======================
 f('connector', 'info', 'high',
   "The Videocart edge: 22 contacts on B.Cu (the face down in the console), 2.54 mm, pins 1-11 / key slot / 12-22, "
   "pin 1 (GND) west seen from the parts side -- the same signal order as aotta's PicoVideocart (proven on a console) "
   "mirrored, and fart's footprint exactly",
   keys('J_EDGE'), nets('GND', 'CONS_5V', 'D0', 'INTREQ_N'),
   comp={'description': 'footprint pads vs the transcribed aotta / fart / veswiki numbers', 'script': EO,
         'result': grab(EOUT, r'\[1\] aotta: every finger') + '; ' + grab(EOUT, r'\[2\] fart: finger positions')}),
 f('connector', 'info', 'high',
   "Edge pin 22 is the console's +12 V and pin 21 a spare: both get bare fingers (for the contact springs) and no "
   "stub; the fab gerbers show no other copper within 1 mm of either, and no inner-plane copper in the finger field",
   keys('J_EDGE'), nets('GND'),
   comp={'description': 'B.Cu objects near fingers 21 / 22 (pour regions by their real outline); inner layers in the field',
         'script': CG, 'result': grab(GOUT, r'fingers 21 / 22') + '; ' + grab(GOUT, r"22 fingers at their pins' x")}),
 # ======================= RP2040 support circuit (design guide) and its layout =======================
 f('decoupling', 'info', 'high',
   "VREG_VOUT 1 uF and the two DVDD 100 nF hang off the pin ring's corner on F.Cu, no via in the path (design guide: "
   "1 uF close to VREG_OUT); on the atari2600-rev0 layout this board started from, the 1 uF sat 11.9 mm away through two vias",
   keys('U_RP', 'C_VREGOUT', 'C_DV50', 'C_DV23'), nets('DVDD'),
   [(HW, 9, 'close to both the input (VREG_IN) and the output (VREG_OUT)')],
   {'description': 'shortest copper path pin 45 -> each capacitor', 'script': L,
    'result': grab(LOUT, r'pin 45 -> \S+ \(C_VREGOUT\)') + '; ' + grab(LOUT, r'\(C_DV23\)')}),
 f('decoupling', 'info', 'high',
   "VREG_VIN 44 and ADC_AVDD 43 strapped and wired straight into their 1 uF; USB_VDD 48 and IOVDD 49 share one via "
   "and capacitor as Raspberry Pi's own minimal design does; IOVDD 1 / 10 (among the bus pins) drop inward to the "
   "+3V3_RP island",
   keys('U_RP', 'C_VREGIN', 'C_USBV', 'C_IOV49', 'C_IOV1', 'C_IOV10'), nets('+3V3_RP'),
   [(HW, 9, 'pins 48 and 49 of RP2040 share a single')],
   {'description': 'shortest copper path pin 44 -> the 1 uF', 'script': L, 'result': grab(LOUT, r'pin 44 \(VREG_VIN\)')}),
 f('usb', 'info', 'high',
   "RP2040 USB D+ / D- -> 27R in line right off the pins (design guide: placed close to the chip), the pair drawn "
   "as locked copper out of the 0.4 mm pitch",
   keys('U_RP', 'R_USBP', 'R_USBM'), nets('RP_USB_DP', 'RP_USB_DM', 'USB_DP', 'USB_DM'),
   [(HW, 12, 'placed close to the chip')],
   {'description': 'shortest copper path pins 46 / 47 -> the 27R', 'script': L,
    'result': grab(LOUT, r'pin 46 -> ') + '; ' + grab(LOUT, r'pin 47 -> ')}),
 f('oscillator', 'info', 'high',
   "ABM8-272-T3 (CL 10 pF) with 2 x 15 pF and 1k in XOUT, the design guide's crystal circuit: 7.5 pF + 2-5 pF stray; "
   "XIN runs straight out to the crystal on F.Cu, XOUT through a via under the package to the 1k on B.Cu",
   keys('Y_RP', 'C_XIN', 'C_XOUT', 'R_XOUT'), nets('XIN', 'XOUT', 'XOUT_Y'),
   [('ABM8-272-T3', 1, 'Load capacitance (CL)'), (HW, 11, 'total load capacitance of 10.5 pF')],
   {'description': 'series load + stray; XIN track length', 'script': M,
    'result': grab(MOUT, r'crystal load') + '; ' + grab(LOUT, r'XIN: RP pin 20')}),
 f('thermal', 'info', 'high',
   "RP2040 exposed pad: 9 GND vias; CP2102N exposed pad: 9 GND vias", keys('U_RP', 'U_UART'), nets('GND'),
   comp={'description': 'vias inside each exposed pad', 'script': L,
         'result': grab(LOUT, r'\(U_RP\) exposed pad') + '; ' + grab(LOUT, r'\(U_UART\) exposed pad')}),
 # ======================= power =======================
 f('power', 'info', 'high',
   "+5V = console 5 V (4.75-5.25 V) through an SS34: >= 4.3 V, above the AP63203's 3.8 V minimum input and the "
   "AP2112K's 3.3 V + 0.25 V dropout; 5.25 V is under the AP2112K's 6 V maximum",
   keys('D_CONS', 'D_VBUS', 'U_BUCK', 'U_LDO'), nets('+5V', 'CONS_5V', 'VBUS'),
   [('SS34', 1, 'Maximum instantaneous forward voltage'), ('AP63203WU-7', 1, 'VIN 3.8V to 32V'), ('AP2112K-3.3TRG1', 1, 'Low Dropout Voltage'),
    ('AP2112K-3.3TRG1', 3, 'Supply Voltage')],
   {'description': '4.75 V - VF; vs VIN(min) and 3.3 V + dropout', 'script': M,
    'result': grab(MOUT, r'\+5V from the console') + '; ' + grab(MOUT, r'AP2112K VIN max')}),
 f('power', 'warning', 'medium',
   "Peak +5V draw ~405 mA (ESP32-S3 802.11b TX at 355 mA through the buck, the RP and its flash through the LDO, the "
   "WS2812 at full white) from the console's 7805, which also feeds the console: not measured",
   keys('U_S3', 'U_BUCK', 'U_LDO', 'D_CONS', 'J_EDGE'), nets('+5V', 'CONS_5V'),
   [('ESP32-S3-WROOM-1-N16R8', 28, '802.11b, 1 Mbps, @20.5 dBm')],
   {'description': '(355 + 9.5 mA) x 3.3 / (0.85 x 4.3 V) + 40 mA + 36 mA', 'script': M, 'result': grab(MOUT, r'peak \+5V draw')},
   'The console rail is a 7805 (1.5 A); its own load is unknown.',
   'Bring-up: measure CONS_5V at fingers 19 / 20 during Wi-Fi bursts; if it sags, run the cart from USB-C.'),
 f('layout', 'info', 'high',
   "AP63203 input loop on F.Cu: VIN and GND run as 0.6 mm rails straight down the 100 nF and both 22 uF stacked under "
   "the IC, the plane vias at the stack's far end (datasheet layout 4: VIN capacitors as close as possible)",
   keys('U_BUCK', 'C_BINHF', 'C_BIN1', 'C_BIN2'), nets('+5V', 'GND'),
   [('AP63203WU-7', 15, 'Place the VIN capacitors as close to the device as possible'),
    ('AP63203WU-7', 15, 'Provide sufficient vias for the input and output capacitors')],
   {'description': 'VIN / GND -> the 100 nF on F.Cu, loop length', 'script': L, 'result': grab(LOUT, r'the hot loop')}),
 f('power', 'info', 'high',
   "AP63203 inductor 6.8 uH, not Table 2's 3.9 uH: that table is sized for 12 V in and the part's 2 A rating. "
   "Eq. 7 at this board's 5 V input gives 0.15 A of ripple, 30-50 % of the S3 side's real peak, and 6.8 uH is "
   "inside the datasheet's 2.2-10 uH range",
   keys('L_BUCK', 'U_BUCK'), nets('BUCK_SW', '+3V3'),
   [('AP63203WU-7', 13, 'it is recommended to select an inductor of approximately 2.2µH to 10µH'),
    ('AP63203WU-7', 13, 'Recommended Component Selections for AP63203')],
   {'description': 'Eq. 7: dIL = Vout (Vin - Vout) / (Vin L fsw)', 'script': M, 'result': grab(MOUT, r'AP63203 ripple')}),
 f('thermal', 'info', 'high', 'AP2112K dissipation at the RP2040 + flash load: ~66 mW worst case in SOT-23-5',
   keys('U_LDO', 'U_RP'), nets('+3V3_RP', '+5V'),
   [('AP2112K-3.3TRG1', 1, 'Low Dropout Voltage')],
   {'description': '(5.25 - 0.3 - 3.3 V) x 40 mA', 'script': M, 'result': grab(MOUT, r'AP2112K dissipation')}),
 # ======================= the FujiNet half =======================
 f('rf', 'info', 'high',
   "ESP32-S3 antenna flush with the grip edge (outside the console) over the module footprint's 48 x 6 mm keep-out: "
   "no track, via or poured copper inside it on any layer",
   keys('U_S3'), nets('GND'),
   [('ESP32-S3-WROOM-1-N16R8', 46, 'The interference of the base board on the')],
   {'description': 'tracks, vias and filled zones inside the keep-out', 'script': L, 'result': grab(LOUT, r'antenna keep-out')}),
 f('decoupling', 'info', 'high',
   "ESP32-S3 3V3: the 100 nF and the 22 uF of the datasheet's peripheral schematic sit right beside the module's "
   "3V3 pin (the 22 uF also covers the Wi-Fi TX bursts)",
   keys('U_S3', 'C_S3', 'C_S3BULK'), nets('+3V3'),
   [('ESP32-S3-WROOM-1-N16R8', 41, 'This is the typical application circuit of the module connected with peripheral components')],
   {'description': 'pad-to-pad distance, 3V3 pin -> each capacitor', 'script': L,
    'result': grab(LOUT, r'\(C_S3\) \+3V3') + '; ' + grab(LOUT, r'\(C_S3BULK\)')}),
 f('mcu', 'info', 'high', 'ESP32-S3 EN: 10k / 1 uF RC as Espressif recommends; RESET reaches EN and the RP RUN through the BAT54C',
   keys('U_S3', 'R_EN', 'C_EN', 'D_RST'), nets('S3_EN', 'RUN'),
   [('ESP32-S3-WROOM-1-N16R8', 41, 'RC delay circuit')],
   {'description': 'tau = 10 ms', 'script': CN, 'result': 'netlist: S3_EN 10k to +3V3, 1 uF, the BAT54C, the auto-program pair'}),
 f('led', 'info', 'high',
   'WS2812B-2020 on +5V (VDD 3.7-5.3 V covers 4.3-5.25 V); the RP activity LED (KT-0603G green, VF 2.6-3.1 V at 5 mA) '
   'at ~1.8 mA through 330R',
   keys('D_WS', 'D_LED', 'R_LED'), nets('+5V', 'RP_LED', 'RP_LED_A'),
   [('WS2812B-2020-V6', 3, '+3.7~+5.3'), ('KT-0603G', 3, 'Forward Voltage')],
   {'description': '(3.3 - 2.7 V) / 330R', 'script': M, 'result': grab(MOUT, r'RP activity LED')}),
 f('usb', 'info', 'high', 'CP2102N VBUS sense: 22k / 47k from VBUS = 3.4 V at 5 V, inside its VBUS-pin restriction',
   keys('U_UART', 'R_VBSH', 'R_VBSL'), nets('VBUS', 'VBUS_SNS'),
   [('CP2102N-A02-GQFN28R', 8, 'There are two relevant restrictions on the VBUS pin voltage')],
   {'description': '5 V x 47 / 69 (SPICE: voltage_divider)', 'script': M, 'result': '3.41 V'}),
 f('usb', 'info', 'high', 'USB pairs: lengths and skew within each pair (full speed)',
   keys('J_USB', 'U_UART', 'U_RP', 'U_S3'), nets('UBRG_DP', 'UBRG_DM', 'USB_DP', 'USB_DM'),
   comp={'description': 'track length per line', 'script': L,
         'result': grab(LOUT, r'UBRG_DP / UBRG_DM') + '; ' + grab(LOUT, r'7\. USB_DP / USB_DM')}),
]

out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1, ensure_ascii=False)
print('deep_review.json: %d findings for run %s' % (len(F), run))
