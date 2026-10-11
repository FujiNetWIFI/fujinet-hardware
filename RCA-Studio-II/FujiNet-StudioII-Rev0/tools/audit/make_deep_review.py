#!/usr/bin/env python3
"""Emit analysis/deep_review.json for the Rev0 audit (kicad-happy Deep Review; docs/design-review-rev0.md):
per-IC checks of the design against its datasheet, and the layout's own claims measured on the copper.

References are resolved from tools/design.py by key, never hard-coded, so the file tracks regeneration and
reference shifts; net names are mapped onto the analyzer's names (which may carry a sheet prefix, e.g.
/cart-bus/D0).  Datasheet pages are those of the PDFs in datasheets/ (RP2354B.pdf is Raspberry Pi's RP2350
datasheet), located with tools/audit/find_quote_page.py.  Every "result" below is read from the scripts' own
output at the time this file is written: tools/audit/margins.py, tools/audit/layout_checks.py,
tools/check_nets.py, tools/audit/edge_orientation.py, tools/audit/check_gerbers.py.

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


MOUT, LOUT, EOUT, GOUT, NOUT = out_of(M), out_of(L), out_of(EO), out_of(CG), out_of(CN)


def grab(text, pat):
    """The first line of a script's output that matches pat (a regex), without its ok/FAIL tag."""
    for line in text.splitlines():
        if re.search(pat, line):
            return re.sub(r'^(ok|OK|FAIL|PASS)\s+', '', line).strip()
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


RP, BUF, OR_, INV, NOR = 'RP2354B', 'SN74HCT541PWR', 'SN74HCT32DR', 'SN74HCT14DR', '74HCT1G02GV,125'
MUX, BUCK, S3, CP, ESD, WS = 'TPS2116DRLR', 'AP63203WU-7', 'ESP32-S3-WROOM-1-N16R8', 'CP2102N-A02-GQFN28R', \
    'USBLC6-2SC6', 'WS2812B-2020-V6'
F = [
 # ======================= the console bus: levels and supplies =======================
 f('level-shift', 'info', 'high',
   "The 74HCT541 drives the CDP1802's data bus at CMOS levels (VOH >= 4.4 V with +5V at its low corner, "
   "IOH -20 uA) against the 1802's VIH 0.7 VDD = 3.5 V; its TTL-level inputs take the RP2354B's 3.3 V",
   keys('U_BUF', 'U_RP'), nets('D0', 'D7', 'RP_D0', 'RP_D7'),
   [(BUF, 4, 'High-level input voltage'), (BUF, 4, 'Supply voltage')],
   {'description': "VOH min at VCC 4.5 V (4.4 V) less the VCC shortfall; RP VOH 3.0 V vs VIH 2.0 V", 'script': M,
    'result': grab(MOUT, r"'541 VOH") + '; ' + grab(MOUT, r'RP VOH vs 74HCT VIH')}),
 f('power', 'info', 'high',
   "+5V is the TPS2116 power mux's output, USB VBUS first, the console's 5 V second: at most 60 mOhm either way, so "
   "the 74HCT glue sits at >= 4.72 V on either source at the cart's ~470 mA peak, inside its 4.5-5.5 V; VBUS takes "
   "priority above 3.96-4.64 V, below the USB minimum 4.75 V",
   keys('U_MUX', 'R_PRH', 'R_PRL', 'U_BUF', 'U_OR', 'U_INV', 'U_NOR'), nets('+5V', 'VBUS', 'CONS_5V', 'VBUS_PR'),
   [(MUX, 6, 'PR1 reference voltage'), (MUX, 12, 'connect MODE to VIN1'), (MUX, 6, 'On-Resistance'),
    (BUF, 4, 'Supply voltage')],
   {'description': 'VIN low corner - IOUT x RON max; PR1 divider x VREF', 'script': M,
    'result': grab(MOUT, r'\+5V on USB') + '; ' + grab(MOUT, r'\+5V on the console') + '; ' + grab(MOUT, r'PR1 = VBUS') +
    '; ' + grab(MOUT, r'USB VBUS low corner above')}),
 f('power', 'info', 'high',
   "The mux blocks reverse current, so neither source back-feeds the other (USB into an unpowered console, or the "
   "console into a USB host); its VIN stays inside 5.5 V on either source's high corner",
   keys('U_MUX'), nets('VBUS', 'CONS_5V', '+5V'),
   [(MUX, 1, 'Reverse Current Blocking when VOUT > VINx'), (MUX, 4, 'Input Voltage')],
   {'description': 'VIN high corners vs the recommended VIN max', 'script': M,
    'result': grab(MOUT, r'mux VIN2 at the console') + '; ' + grab(MOUT, r'mux VIN1 at the USB')}),
 f('level-shift', 'info', 'medium',
   "The console's 5 V logic (/MRD into the '541's /OE1 and the '1G02) stays under VCC + 0.5 V even with +5V at its "
   "low corner: no input-clamp current",
   keys('U_BUF', 'U_NOR'), nets('MRD_N', '+5V'),
   [(BUF, 4, 'Input clamp current'), (NOR, 3, 'input clamping current')],
   {'description': 'console VOH vs +5V low corner + 0.5 V', 'script': M, 'result': grab(MOUT, r'console 5 V logic into an HCT input')}),
 f('mcu', 'info', 'high',
   'The console reaches GPIO0-9 through 330R: the RP2350 fault-tolerant pads take 5.5 V once IOVDD is at 3.3 V, '
   'and the LDO rises with +5V, so the pads are never unpowered with 5 V on them',
   keys('U_RP', 'R_MA0', 'R_MRD', 'U_LDO'), nets('MA0', 'RP_MA0', '+3V3'),
   [(RP, 1336, 'they will tolerate voltages up to 5.5 V, provided IOVDD is powered to 3.3 V')],
   {'description': 'series R >= 100 Ohm (current limit while IOVDD rises)', 'script': M, 'result': grab(MOUT, r'series R into the RP')}),
 f('logic', 'info', 'high',
   "PWR_OK: 22k / 100k puts 0.82 x the console's 5 V on the 74HCT14; it asserts by 2.3 V and drops by 0.6-1.5 V, "
   "inside the 7805's range, and VSENSE stays within the '14's input range at the +5V low corner",
   keys('U_INV', 'R_VSH', 'R_VSL'), nets('CONS_5V', 'VSENSE', 'PWR_OK_N', 'PWR_OK'),
   [(INV, 5, 'Positive-going threshold'), (INV, 5, 'Negative-going threshold')],
   {'description': 'VT+/VT- at VCC 4.5 V divided by 0.82', 'script': M,
    'result': grab(MOUT, r'VSENSE = ') + '; ' + grab(MOUT, r'VSENSE at 5.25 V')}),
 f('logic', 'info', 'high',
   "/DRIVE and /CLAIM: 10k to +5V holds the '541 off and CART CS low while the RP2354B is unpowered or booting, "
   "even against a pad latched by RP2350-E9 (~120 uA)",
   keys('R_PUDRIVE', 'R_PUCLAIM', 'U_OR'), nets('DRIVE_N', 'CLAIM_N'),
   [(OR_, 4, 'High-level input voltage')],
   {'description': '5 V - 120 uA x 10k vs VIH 2.0 V', 'script': M, 'result': grab(MOUT, r'/DRIVE with 10k')}),
 f('power', 'info', 'high', 'AP2112K-3.3 headroom: 4.72 V in at the +5V low corner, ~0.05 V dropout at ~50 mA',
   keys('U_LDO'), nets('+5V', '+3V3'),
   [('AP2112K-3.3TRG1', 1, 'Low Dropout Voltage (3.3V): 250mV (Typ.) @IOUT = 600mA')],
   {'description': 'VIN low corner vs 3.3 V + dropout', 'script': M, 'result': grab(MOUT, r'AP2112K input at the')}),
 f('power', 'info', 'high',
   "The S3 side's 3.3 V: the AP63203 2 A buck from +5V (>= 4.72 V against its 3.8 V minimum) carries the S3's WiFi "
   "peak, the microSD and the CP2102N with margin; the module wants a supply good for 0.5 A",
   keys('U_BUCK', 'L_BUCK', 'U_S3'), nets('+5V', '+3V3_S3', 'BUCK_SW'),
   [(BUCK, 1, 'VIN 3.8V to 32V'), (S3, 27, 'Current delivered by external power supply')],
   {'description': 'buck VIN vs +5V low corner; the S3 side peak vs 2 A', 'script': M,
    'result': grab(MOUT, r'AP63203 input at the') + '; ' + grab(MOUT, r'AP63203 output current') + '; ' +
    grab(MOUT, r'\+5V draw:')}),
 f('power', 'warning', 'medium',
   "With no USB the console's 7805 feeds the whole cart: ~140 mA average and ~470 mA peak with the S3 on WiFi. The "
   "console's own load and the 7805's headroom are unmeasured",
   keys('U_MUX', 'U_BUCK', 'U_S3'), nets('CONS_5V', '+5V'),
   [(S3, 27, 'Current delivered by external power supply')],
   {'description': 'the cart budget (margins.py)', 'script': M, 'result': grab(MOUT, r'\+5V draw:')},
   rec="Bring-up step 2: measure CONS_5V (TP_CONS5V) under WiFi bursts with no USB; if the console's rail sags, run "
       "the cart from USB-C (the mux then takes nothing from the console)."),
 f('layout', 'info', 'high',
   "The AP63203's input loop closes on F.Cu: VIN and GND to the 100 nF without a via, the plane vias at the far end of "
   "the 22 uF stack",
   keys('U_BUCK', 'C_BINHF', 'C_BIN', 'C_5VBULK'), nets('+5V', 'GND'),
   [(BUCK, 4, 'Supply Voltage')],
   {'description': 'copper path IC pin -> 100 nF pad; loop length', 'script': L,
    'result': grab(LOUT, r'10\. AP63203 pin 3') + '; ' + grab(LOUT, r'10\. the hot loop')}),
 # ======================= the ESP32-S3 half =======================
 f('rf', 'info', 'high',
   "The ESP32-S3-WROOM-1's antenna is flush with the top edge and its keep-out (the antenna area plus Espressif's "
   "15 mm, the module footprint's zone) holds no track, via, pour or part on any layer",
   keys('U_S3'), nets('GND'),
   [(S3, 10, 'Keepout Zone')],
   {'description': 'tracks / vias / fills / parts inside the zone; module edge vs the board edge', 'script': L,
    'result': grab(LOUT, r'9\. ESP32-S3 antenna keep-out') + '; ' + grab(LOUT, r'9\. the antenna end')}),
 f('mcu', 'info', 'high',
   "The S3: 3V3 on the buck's rail (3.0-3.6 V) with its 100 nF and 22 uF at the pin; EN on the recommended 10k / 1 uF "
   "power-on delay; the strapping pins IO3 / IO45 / IO46 unloaded, IO0 on BOOT and the auto-program pair; the "
   "fujiversal-studio2.h pins (SD 38-41, UART0 43 / 44, WS2812 48) and the USB host on IO19 / IO20",
   keys('U_S3', 'C_S3', 'C_S3BULK', 'R_EN', 'C_EN'), nets('+3V3_S3', 'S3_EN', 'S3_IO0'),
   [(S3, 41, 'The recommended setting for the RC delay circuit')],
   {'description': 'tools/check_nets.py (S3 pin map, strapping, EN RC); the 3V3 capacitors on the copper',
    'script': L, 'result': grab(LOUT, r'9\. ESP32-S3 3V3 .*\(C_S3\)') + '; ' + grab(NOUT, r'checks, \d+ failed')}),
 f('mcu', 'warning', 'high',
   "The S3 forces the RP2354B's RUN and BOOTSEL from IO4 / IO5 through 1k (fujiversal-intv.h's pins), but "
   "fujiversal-studio2.h does not declare PIN_RP2040_RUN / _BOOTSEL yet: until it does, the FujiNet firmware cannot "
   "re-flash the RP2354B through them",
   keys('U_S3', 'R_RUNCTL', 'R_BSELCTL', 'U_RP'), nets('RUN_CTL', 'BOOTSEL_CTL', 'RUN', 'QSPI_SS'),
   comp={'description': 'tools/check_nets.py: the pin map vs the board', 'script': CN, 'result': grab(NOUT, r'WARN: ')},
   rec='Add PIN_RP2040_RUN GPIO_NUM_4 and PIN_RP2040_BOOTSEL GPIO_NUM_5 to include/pinmap/fujiversal-studio2.h '
       '(firmware, not this board).'),
 f('interface', 'info', 'high',
   "CP2102N: self-powered on the S3 rail, VBUS sensed through 22k / 47k (3.24 V at 4.75 V over VIH VIO - 0.6 V; 3.58 V "
   "at 5.25 V under VIO + 2.5 V), RSTb on the recommended 1k pull-up",
   keys('U_UART', 'R_VBSH', 'R_VBSL', 'R_CPRST'), nets('VBUS_SNS', 'CP_RST', '+3V3_S3'),
   [(CP, 5, 'pull-up on the RSTb pin is recommended'), (CP, 8, 'VIO + 2.5 V')],
   {'description': 'divider at the VBUS corners', 'script': M,
    'result': grab(MOUT, r'CP2102N VBUS sense at VBUS 4.75') + '; ' + grab(MOUT, r'CP2102N VBUS sense at VBUS 5.25')}),
 f('esd', 'info', 'high',
   "USB-C D+ / D- / VBUS behind a USBLC6-2SC6: 3.5 pF max per line (no load on a full-speed link), routed "
   "flow-through as ST draws it: each line in at one I/O pin and out of its twin, the twins joined straight under "
   "the body, VBUS (5) dropping through a via between the rows",
   keys('U_ESD', 'J_USB'), nets('UBRG_DP', 'UBRG_DM', 'VBUS'),
   [(ESD, 1, 'Very low capacitance: 3.5 pF max'), (ESD, 9, 'D+in'), (ESD, 5, 'must be as short as')],
   {'description': 'the flow-through joins (copper path pin to twin pin) and the pair length / skew', 'script': L,
    'result': grab(LOUT, r'7\. U\d+ pins 4 / 3') + '; ' + grab(LOUT, r'7\. UBRG_DP: no loop') + '; ' +
    grab(LOUT, r'7\. UBRG_DP / UBRG_DM')}),
 f('esd', 'info', 'high',
   "ST's layout figure puts a 100 nF (CBUS) at the USBLC6-2SC6's VBUS pin: C_VBUSHF sits beside the package, 5.3 mm "
   "of copper from pin 5 (its via between the pad rows, B.Cu, the capacitor's own via); the 1 uF stays at the "
   "receptacle's VBUS pads",
   keys('U_ESD', 'C_VBUSHF', 'C_VBUS'), nets('VBUS'),
   [(ESD, 9, 'CBUS = 100nF'), (ESD, 5, 'must be as short as')],
   {'description': 'copper path U_ESD pin 5 -> C_VBUSHF pad 1', 'script': L,
    'result': grab(LOUT, r'7\. U\d+ VBUS \(pin 5\)')}),
 f('led', 'info', 'high',
   "WS2812B-2020 on +5V (4.72-5.25 V, inside its 3.7-5.3 V) takes the S3's 3.3 V data (VIH 2.7 V min)",
   keys('D_WS', 'R_WS', 'C_WS'), nets('+5V', 'WS_DIN', 'LED_STRIP'),
   [(WS, 3, '+3.7~+5.3'), (WS, 3, 'High Voltage Input')],
   {'description': 'VDD corners; data VOH vs VIH', 'script': M,
    'result': grab(MOUT, r'WS2812 VDD \(\+5V\) high corner') + '; ' + grab(MOUT, r"the S3's 3.3 V data")}),
 # ======================= the RP2354B core =======================
 f('layout', 'info', 'high',
   "The core regulator is Raspberry Pi's minimal-design corner, grafted onto the QFN-80 (same pin run, same pitch, "
   "from the same corner): its pours join VREG_VIN to C_IN, LX to the inductor, PGND to both 4.7 uF, the inductor to "
   "C_OUT; FB reaches C_OUT on F.Cu",
   keys('U_RP', 'L_RP', 'C_VREGIN', 'C_DVBULK'), nets('RP_LX', 'DVDD', '+3V3'),
   [(RP, 453, 'The most critical part of an RP2350 PCB layout is the core voltage regulator')],
   {'description': 'filled pours containing both pads; FB copper path', 'script': L,
    'result': grab(LOUT, r'VREG_VIN 64') + '; ' + grab(LOUT, r'LX 63') + '; ' + grab(LOUT, r'PGND 62 -> C_DVBULK')}),
 f('layout', 'info', 'high',
   'No top-layer GND pour over the regulator corner: nothing but its pads under the inductor, and the PGND pour meets '
   'main GND only through its own two vias (one point)',
   keys('L_RP', 'U_RP'), nets('RP_LX', 'GND'),
   [(RP, 455, 'cut away any extra copper underneath the inductor')],
   {'description': 'gen_pcb.REG_CUT: a hole in the F.Cu GND pour; stitching kept out of it', 'script': L,
    'result': grab(LOUT, r'PGND 62 -> C_VREGIN')}),
 f('layout', 'info', 'high', 'VREG_AVDD: the 33R / 4.7 uF RC straight off pin 61, its capacitor on its own GND via',
   keys('U_RP', 'R_AVDD', 'C_AVDD'), nets('VREG_AVDD'),
   [(RP, 455, 'VREG_AVDD is a noise sensitive signal and must be RC filtered')],
   {'description': 'copper path pin 61 -> C_AVDD', 'script': L, 'result': grab(LOUT, r'VREG_AVDD 61')}),
 f('decoupling', 'info', 'high',
   'Supply rings under the package: every +3V3 supply pin (IOVDD x8, ADC_AVDD, VREG_VIN, USB_OTP_VDD, QSPI_IOVDD) '
   'stubs into a filled +3V3 ring with four vias to the In2 plane, every DVDD pin into a DVDD ring tied to the '
   "regulator output by a B.Cu link -- no supply via among the bus pins",
   keys('U_RP'), nets('+3V3', 'DVDD'),
   comp={'description': 'stub ends inside the filled rings; ring vias; DVDD link path', 'script': L,
         'result': grab(LOUT, r'2\. every RP supply pin') + '; ' + grab(LOUT, r'2\. the \+3V3 ring') + '; ' +
         grab(LOUT, r'2\. the DVDD ring')}),
 f('decoupling', 'info', 'high',
   "Straight-out decoupling: DVDD 10 and IOVDD 15 / 41 / 50 / 60 and ADC_AVDD 59 reach their 100 nF over F.Cu with "
   "no via; the other supply capacitors sit within 12 mm on the rings and the plane",
   keys('C_DV10', 'C_IOV15', 'C_IOV41', 'C_IOV50', 'C_IOV60', 'C_ADC'), nets('+3V3', 'DVDD'),
   comp={'description': 'copper path pin -> capacitor pad', 'script': L,
         'result': '; '.join(grab(LOUT, r'3\. RP pin %s -> ' % n) for n in ('10', '15', '41', '50', '59', '60'))}),
 f('usb', 'info', 'high', "The USB 27R sit at the RP's USB pins (Raspberry Pi's placement)",
   keys('U_RP', 'R_USBP', 'R_USBM'), nets('RP_USB_DP', 'RP_USB_DM'),
   [(RP, 1336, 'USB operation requires external 27Ω series resistors')],
   {'description': 'copper path pins 66 / 67 -> each 27R', 'script': L,
    'result': grab(LOUT, r'4\. RP pin 66') + '; ' + grab(LOUT, r'4\. RP pin 67')}),
 f('clock', 'info', 'high', "12 MHz crystal: 15 pF + ~3 pF strays = 10.5 pF against the ABM8-272-T3's 10 pF; XIN short",
   keys('Y_RP', 'C_XIN', 'C_XOUT', 'R_XOUT'), nets('XIN', 'XOUT_Y'),
   [('ABM8-272-T3', 1, 'Load capacitance (CL)')],
   {'description': 'CL = C1 C2 / (C1 + C2) + Cstray; XIN copper length', 'script': L,
    'result': grab(MOUT, r'CL = ') + '; ' + grab(LOUT, r'5\. XIN')}),
 f('thermal', 'info', 'high', "The RP2354B's exposed pad carries a 3 x 3 GND via grid to In1 / B.Cu",
   keys('U_RP'), nets('GND'),
   comp={'description': 'GND vias inside the exposed pad', 'script': L, 'result': grab(LOUT, r'6\. .*exposed pad')}),
 f('usb', 'info', 'high', 'USB pairs: lengths and skew within each pair (full speed): the RP <-> S3 link and its 27R',
   keys('U_S3', 'U_RP', 'R_USBP', 'R_USBM'), nets('USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM'),
   comp={'description': 'track length per line', 'script': L,
         'result': grab(LOUT, r'7\. USB_DP / USB_DM') + '; ' + grab(LOUT, r'7\. RP_USB_DP / RP_USB_DM')}),
 f('thermal', 'info', 'high', "The CP2102N's exposed pad carries a GND via grid",
   keys('U_UART'), nets('GND'),
   comp={'description': 'GND vias inside the exposed pad', 'script': L, 'result': grab(LOUT, r'11\. ')}),
 # ======================= the edge =======================
 f('connector', 'info', 'high',
   "The edge matches FliP's built multicart (pads, signals, outline, holes, notches) and EJK's console pinout; "
   "contacts on B.Cu, pin 1 (D7) at the right seen from the parts",
   keys('J_EDGE'), nets('D7', 'MA0', 'CONS_5V', 'CART_CS'),
   comp={'description': 'tools/audit/edge_orientation.py against FliP / EJK / the original board', 'script': EO,
         'result': grab(EOUT, r'edge_orientation:') + '; ' + grab(EOUT, r'\[1\] FliP: the signal on every pad')}),
 f('layout', 'info', 'high',
   'The plotted inner layers short nothing: every plated hole in the zip takes its net from the copper flashed at it, '
   'and no In1 / In2 pour of another net contains it.  The board is refilled and saved after the last via '
   '(tools/fill_zones.py) and the DRC gate runs on the saved fills: before that, the zip plotted fills from before '
   'GND stitching, with 427 GND vias inside the In2 power pours, while DRC with --refill-zones passed',
   keys('U_RP', 'U_S3'), nets('GND', '+5V', '+3V3', '+3V3_S3', 'CONS_5V'),
   comp={'description': 'tools/audit/check_gerbers.py check 9 on the JLCPCB zip (X2 net attributes)', 'script': CG,
         'result': grab(GOUT, r'9\. \d+ plated holes')}),
 f('layout', 'info', 'high',
   'The address bus twist and the data fan-in are intact: every address finger reaches its 330R (<= 3 vias), every '
   "data finger its '541 pin (one via); nothing on the inner layers in the finger field",
   keys('J_EDGE', 'U_BUF', 'R_MA0', 'R_MRD'), nets('MA0', 'MRD_N', 'D0', 'D7'),
   comp={'description': 'copper paths finger -> part; filled inner copper south of the field', 'script': L,
         'result': grab(LOUT, r'8\. the address twist') + '; ' + grab(LOUT, r'8\. the data fan-in') + '; ' +
         grab(LOUT, r'8\. In1 / In2')}),
 f('connector', 'info', 'high', 'The firmware contract: the netlist against s2_cart.h and the edge map',
   keys('U_RP', 'J_EDGE'), nets('RP_MA0', 'RP_D0', 'DRIVE_N', 'CLAIM_N', 'PWR_OK'),
   comp={'description': 'tools/check_nets.py', 'script': CN, 'result': grab(NOUT, r'checks, \d+ failed')}),
]

out = {'schema_version': '1.0', 'produced_for_run_id': run,
       'produced_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
       'findings': F, 'quarantined': []}
json.dump(out, open(os.path.join(PRJ, 'analysis', 'deep_review.json'), 'w'), indent=1, ensure_ascii=False)
print('deep_review.json: %d findings for run %s' % (len(F), run))
