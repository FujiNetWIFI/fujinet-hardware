#!/usr/bin/env python3
"""Numbers behind the Rev0 audit (docs/design-review-rev0.md): logic levels across the console's 5 V
CDP1802 bus, the 74HCT glue and the RP2354B; the glue's supply (+5V) on each source -- USB VBUS or
the console's 7805, through the TPS2116 power mux -- against the 74HCT recommended VCC; the
console's 5 V inputs into the glue; the mux's priority threshold and ratings; PWR_OK's thresholds;
the /DRIVE / /CLAIM pull-ups; the cart's draw with the ESP32-S3 on board, the S3's buck and rail;
the WS2812 and the CP2102N's VBUS sense; the crystal's load; the LED.

Parts are found by their nets in tools/design.py (not by reference), so the script keeps working when
references move.  Every datasheet figure is quoted with its source here and, with pages, in
analysis/deep_review.json (tools/audit/make_deep_review.py).

Usage: python3 tools/audit/margins.py          exit 1 if any margin is negative
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import design as D


def find(pred):
    hits = [p for p in D.PARTS if pred(p)]
    return hits[0] if hits else None


def two_pin(a, b):
    """The resistor between nets a and b (either orientation), or None."""
    return find(lambda p: p.prefix == 'R' and sorted(n for n in p.pins.values() if n) == sorted([a, b]))


def ohms(p):
    m = re.match(r'([\d.]+)([kMR]?)', p.value)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]


# ---- datasheet limits -------------------------------------------------------------------------------
CDP_VIH = 0.7 * 5.0       # CDP1802A (RCA): BUS 0-7 VIH min 0.7 VDD (CMOS), VDD 5 V
CDP_VIL = 0.3 * 5.0
CONSOLE_VOH = 4.95        # the console's CMOS logic (CD4001 /MRD gating, the 1802): VOH ~VDD - 0.05 V
CONSOLE_5V = (4.75, 5.25) # 7805, +-5 %
HCT_VCC = (4.5, 5.5)      # SN74HCT541 / '32 / '14, 74HCT1G02: recommended VCC (TI SCLS306E 6.3; Nexperia 74HCT1G02 9)
HCT_VIH, HCT_VIL = 2.0, 0.8           # TTL-level inputs, VCC 4.5-5.5 V
HCT_VOH_4V5 = 4.4                     # VOH min, VCC 4.5 V, IOH -20 uA (SCLS306E 6.5)
HCT_VOL = 0.26                        # VOL max, VCC 4.5 V, IOL 6 mA
HCT14_VTP = (1.2, 1.9)                # SN74HCT14 VT+ at VCC 4.5 V (SCLS225G 6.5)
HCT14_VTN = (0.5, 1.2)                # VT- at VCC 4.5 V
RP_VOH = 3.3 - 0.3                    # RP2350 VOH at 4 mA drive, IOVDD 3.3 V (worst case used here)
USB_VBUS = (4.75, 5.25)               # VBUS at the source (USB 2.0): a PC port or a charger
MUX_RON = 0.060                       # TPS2116 RON max, VINx 5 V, -40..105 C (SLVSFG1A 6.5)
MUX_VIN_MAX = 5.5                     # TPS2116 recommended VIN max (6.3); 6 V absolute (6.1)
MUX_VREF = (0.92, 1.08)               # TPS2116 PR1 reference (6.5)
MUX_IMAX = 2.5                        # TPS2116 maximum continuous current (6.1)
AP2112_VIN_MIN = 3.3 + 0.05 + 0.1     # AP2112K-3.3: VOUT + ~0.05 V dropout at 60 mA + margin
BUCK_VIN_MIN = 3.8                    # AP63203 VIN 3.8-32 V (datasheet 7)
BUCK_IOUT = 2.0                       # AP63203 output current
BUCK_EFF = 0.85                       # at 0.1-0.5 A out, 5 V in (datasheet efficiency curves; taken low)
S3_V = (3.0, 3.6)                     # ESP32-S3-WROOM-1 VDD33 (datasheet 5.2)
S3_SUPPLY_MIN = 0.5                   # "current delivered by external power supply" min 0.5 A (5.2)
S3_TX_PEAK = 0.355                    # 802.11b 1 Mbps @20.5 dBm TX (5.4)
S3_AVG = 0.10                         # WiFi connected, mostly receiving / idle (~100 mA at 3.3 V)
SD_PEAK = 0.10                        # a microSD writing (SD spec: up to 100 mA)
CP_I = 0.010                          # CP2102N active
WS_V = (3.7, 5.3)                     # WS2812B-2020 VDD (datasheet p2); VIH 2.7 V min at VDD 5 V
WS_VIH = 2.7
WS_I = 0.036                          # three dies at full white (~12 mA each); the status light runs far below
CP_VIH, CP_VMAX = 3.3 - 0.6, 3.3 + 2.5   # CP2102N VBUS pin: VIH VIO - 0.6 V, abs max VIO + 2.5 V (VIO = VDD)
RP_ACTIVE = 0.045                     # RP2354B at 150 MHz, both cores busy, flash in package: ~45 mA (+3V3)
GLUE = 0.004                          # the '541 / '32 / '14 / '1G02 quiescent + switching at 1.76 MHz bus
LED_VF = 2.0                          # KT-0603R red at ~1 mA
XTAL_CL = 10.0                        # ABM8-272-T3: CL 10 pF (Raspberry Pi minimal design: 15 pF + strays)
STRAY = 3.0

fails = []


def margin(name, value, limit, unit='V', higher=True):
    m = value - limit if higher else limit - value
    ok = m >= 0
    print('%s %-62s %8.3f %s (limit %s %.3f): margin %+.3f' % ('ok  ' if ok else 'FAIL', name, value, unit,
                                                             '>=' if higher else '<=', limit, m))
    if not ok:
        fails.append(name)
    return m


# the cart's +5V: the RP side, the glue, the LEDs and the S3 side through its buck
led_i = (3.3 - LED_VF) / ohms(two_pin('RP_LED', 'RP_LED_A'))
s3_pk = S3_TX_PEAK + SD_PEAK + CP_I                       # the S3 side's 3.3 V peak (A)
i5_pk = RP_ACTIVE + GLUE + led_i + WS_I + 3.3 * s3_pk / BUCK_EFF / 4.7
i5_avg = RP_ACTIVE + GLUE + led_i + 0.005 + 3.3 * (S3_AVG + CP_I) / BUCK_EFF / 4.9
vcc_usb_lo = USB_VBUS[0] - i5_pk * MUX_RON
vcc_cons_lo = CONSOLE_5V[0] - i5_pk * MUX_RON
vcc_lo = min(vcc_usb_lo, vcc_cons_lo)

print('== the data bus: the 541 drives the 1802 ==')
margin("'541 VOH (VCC at the +5V low corner, IOH -20 uA) vs 1802 VIH", HCT_VOH_4V5 - max(0, HCT_VCC[0] - vcc_lo), CDP_VIH)
margin("'541 VOL vs 1802 VIL", HCT_VOL, CDP_VIL, higher=False)
margin('CART CS (1G02) VOH vs the console RAM /CS1 diode OR (CMOS VIH 3.5 V)', HCT_VOH_4V5 - max(0, HCT_VCC[0] - vcc_lo),
       CDP_VIH)
print('== the RP drives the glue (3.3 V into TTL-level inputs) ==')
margin("RP VOH vs 74HCT VIH", RP_VOH, HCT_VIH)
print('== the console drives the RP (5 V through 330R into 5 V-tolerant GPIO0-9) and the glue ==')
margin('series R into the RP (limits the clamp current while IOVDD rises)', ohms(two_pin('MA0', 'RP_MA0')), 100.0, 'Ohm')
print('== +5V: the TPS2116 mux output, the 74HCT supply on each source ==')
print('     +5V peak %.0f mA: the mux drops %.0f mV at its %.0f mOhm max' % (i5_pk * 1e3, i5_pk * MUX_RON * 1e3,
                                                                        MUX_RON * 1e3))
margin('+5V on USB (VBUS low corner - mux drop) vs 74HCT VCC min', vcc_usb_lo, HCT_VCC[0])
margin('+5V on the console (7805 low corner - mux drop) vs 74HCT VCC min', vcc_cons_lo, HCT_VCC[0])
margin('console 5 V logic into an HCT input, +5V at its low corner: under VCC + 0.5 V (no clamp current)',
       CONSOLE_VOH, vcc_lo + 0.5, higher=False)
margin('mux VIN2 at the console high corner vs its recommended VIN max', CONSOLE_5V[1], MUX_VIN_MAX, higher=False)
margin('mux VIN1 at the USB high corner vs its recommended VIN max', USB_VBUS[1], MUX_VIN_MAX, higher=False)
margin('mux current at the cart peak vs IMAX', i5_pk, MUX_IMAX, 'A', higher=False)
rh, rl = two_pin('VBUS', 'VBUS_PR'), two_pin('VBUS_PR', 'GND')
k = (ohms(rh) + ohms(rl)) / ohms(rl)
print('     PR1 = VBUS / %.2f: VBUS takes priority above %.2f-%.2f V' % (k, MUX_VREF[0] * k, MUX_VREF[1] * k))
margin('USB VBUS low corner above the priority threshold (VREF max): USB always wins', USB_VBUS[0], MUX_VREF[1] * k)
print('== PWR_OK (edge 15 -> 22k / 100k -> 74HCT14) ==')
rh, rl = two_pin('CONS_5V', 'VSENSE'), two_pin('VSENSE', 'GND')
k = ohms(rl) / (ohms(rh) + ohms(rl))
print('     VSENSE = %.3f x CONS_5V: PWR_OK rises by CONS_5V %.2f-%.2f V, falls by %.2f-%.2f V' % (
    k, HCT14_VTP[0] / k, HCT14_VTP[1] / k, HCT14_VTN[0] / k, HCT14_VTN[1] / k))
margin('PWR_OK asserts below the 7805 low corner', HCT14_VTP[1] / k, CONSOLE_5V[0], higher=False)
margin("VSENSE at 5.25 V within the 74HCT14 input range (VCC + 0.5 V, +5V low corner)", 5.25 * k, vcc_lo + 0.5,
       higher=False)
print('== /DRIVE, /CLAIM pull-ups against the RP2350 reset pull-down (RP2350-E9 ~120 uA latch) ==')
pu = two_pin('+5V', 'DRIVE_N')
margin('/DRIVE with 10k to +5V against a 120 uA pad sink: stays above 74HCT VIH', 5.0 - 120e-6 * ohms(pu), HCT_VIH)
print('== the cart draw, the regulators, the S3 side ==')
print('     +5V draw: ~%.0f mA average (S3 on WiFi, mostly receiving), ~%.0f mA peak (S3 TX at 20.5 dBm + a microSD '
      "write + the WS2812 at full white): from USB, or from the console's 7805 with no USB" % (i5_avg * 1e3, i5_pk * 1e3))
margin('AP2112K input at the +5V low corner vs VOUT + dropout at 60 mA', vcc_lo, AP2112_VIN_MIN)
margin('AP63203 input at the +5V low corner vs its VIN min', vcc_lo, BUCK_VIN_MIN)
margin('AP63203 output current vs the S3 side at its peak (S3 + microSD + CP2102N)', s3_pk, BUCK_IOUT, 'A', higher=False)
margin("the S3 rail's capability (the 2 A buck) vs the module's 0.5 A supply minimum", BUCK_IOUT, S3_SUPPLY_MIN, 'A')
margin('WS2812 VDD (+5V) low corner vs its 3.7 V min', vcc_lo, WS_V[0])
margin('WS2812 VDD (+5V) high corner vs its 5.3 V max', max(CONSOLE_5V[1], USB_VBUS[1]), WS_V[1], higher=False)
margin("the S3's 3.3 V data (VOH ~3.0 V) vs the WS2812 VIH min", 3.0, WS_VIH)
rh, rl = two_pin('VBUS', 'VBUS_SNS'), two_pin('VBUS_SNS', 'GND')
k = ohms(rl) / (ohms(rh) + ohms(rl))
margin('CP2102N VBUS sense at VBUS 4.75 V vs VIH (VIO - 0.6 V)', 4.75 * k, CP_VIH)
margin('CP2102N VBUS sense at VBUS 5.25 V vs abs max (VIO + 2.5 V)', 5.25 * k, CP_VMAX, higher=False)
print('== crystal ==')
cx = [p for p in D.PARTS if p.value == '15pF']
cl = 15.0 * 15.0 / 30.0 + STRAY
print('     2 x %s: CL = %.1f pF with %.0f pF strays (the crystal wants %.0f pF: Raspberry Pi\'s minimal design values)'
      % (cx[0].value if cx else '?', cl, STRAY, XTAL_CL))
print('== LED ==')
print('     red LED: %.1f mA from GPIO27 through %s' % (led_i * 1e3, two_pin('RP_LED', 'RP_LED_A').value))
print('margins: %s' % ('%d negative' % len(fails) if fails else 'all positive'))
sys.exit(1 if fails else 0)
