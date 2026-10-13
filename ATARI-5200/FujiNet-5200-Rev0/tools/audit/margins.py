#!/usr/bin/env python3
"""Numbers behind the Rev0 audit (docs/design-review-rev0.md): the console-sense divider against
the SN74HCT14 thresholds, the console-path P-FET gate, the RP2350-E9 pull-down, logic levels across
the 3.3 V / 5 V boundary, PHI2 into the 74LVC1G17, +5V from each of its three sources, the cart's
draw from the console's VR1 and from the edge's raw DC (PTC, 2.2R, AP63205), the ADC divider, LED
current, crystal load and the RP LDO.

Parts are found by their nets in tools/design.py (not by reference), so the script keeps working
when references move.  Datasheet limits are the figures quoted (with pages) in
analysis/deep_review.json (tools/audit/make_deep_review.py).

Usage: python3 tools/audit/margins.py
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import design as D


def find(pred):
    hits = [p for p in D.PARTS if pred(p)]
    return hits[0] if hits else None


def two_pin(a, b):
    """The resistor between nets a and b (either orientation), or None."""
    return find(lambda p: p.prefix == 'R' and sorted(n for n in p.pins.values()) == sorted([a, b]))


def ohms(p):
    m = re.match(r'([\d.]+)([kMR]?)', p.value)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]


def par(*rs):
    return 1.0 / sum(1.0 / r for r in rs)


# ---- datasheet limits (pages in analysis/deep_review.json) -----------------
HCT14_VTP = {4.5: (1.2, 1.9), 5.5: (1.4, 2.1)}     # SN74HCT14 VT+ min/max
HCT14_VTN = {4.5: (0.5, 1.2), 5.5: (0.6, 1.4)}     # VT- min/max
HCT_VIH, HCT_VIL = 2.0, 0.8                         # 74HCT inputs, VCC 4.5-5.5 V
HCT_VOH_6MA = 3.84                                  # SN74HCT541 VOH at IOH -6 mA, VCC 4.5 V
LVC17_VTN_MIN, LVC17_VTP_MAX = 1.32, (2.36, 2.79)   # 74LVC1G17 VT- min (4.5 V), VT+ max (4.5 / 5.5 V)
RP_VOH_MIN, RP_VIH_FT = 2.62, 2.0                   # RP2350 at IOVDD 3.3 V
NMOS_VOH, LS_VOH = 2.4, 2.7                         # 6502 address VOH (SY6500 p.3), 74LS VOH min
E9_RMAX = 8.2e3                                     # RP2350-E9: a pull to GND of <= 8.2k overcomes the leakage
E9_ILEAK = 120e-6                                   # its typical source current, holding the pad near 2.2 V
WS_MA = 12e-3                                       # WS2812B-2020-V6: 12 mA per channel
PTC_HOLD = {23: 0.35, 40: 0.30, 50: 0.27}           # Littelfuse 1206L035/30: hold current vs ambient (p.1)
PTC_R1MAX = 1.20                                    # its resistance one hour after a trip / reflow, max
R0603_W = 0.1                                       # Yageo RC0603: 1/10 W
VR1_A = 0.5                                         # 78M05 (CX5200 FSM parts list, CA018087 VR1 / VR2)


def main():
    out = print
    k = D.KEY
    # ---- console sense: VSENSE = CONS_5V * Rb / (Rt + Rb) into the '14 -----------------
    rt, rb = two_pin('CONS_5V', 'VSENSE'), two_pin('VSENSE', 'GND')
    kk = ohms(rb) / (ohms(rt) + ohms(rb))
    out('== PWR_OK sense: %s %s / %s %s, ratio %.3f' % (rt.ref, rt.value, rb.ref, rb.value, kk))
    for v in (4.5, 4.75, 5.0, 5.25, 5.5):
        out('  CONS_5V %.2f V -> VSENSE %.2f V' % (v, v * kk))
    out('  rising: PWR_OK guaranteed high once VSENSE > VT+max 1.9 V (VCC 4.5) / 2.1 V (VCC 5.5): CONS_5V > %.2f / %.2f V'
        % (1.9 / kk, 2.1 / kk))
    out('  falling: PWR_OK guaranteed low once VSENSE < VT-min 0.5 / 0.6 V: CONS_5V < %.2f / %.2f V; '
        'may already drop at VT-max 1.2 / 1.4 V: CONS_5V < %.2f / %.2f V' % (0.5 / kk, 0.6 / kk, 1.2 / kk, 1.4 / kk))
    out('  margin at the console minimum (4.5 V): VSENSE %.2f V - VT+max 1.9 V = %+.2f V' % (4.5 * kk, 4.5 * kk - 1.9))
    out('  VI <= VCC (USB or raw DC runs +5V, P-FET off, body diode ~0.7 V): CONS_5V 5.25 -> VSENSE %.2f V <= +5V >= %.2f V'
        % (5.25 * kk, 5.25 - 0.7))

    # ---- the console-path gate ---------------------------------------------------------------
    vh, vl, vpd = two_pin('VBUS', 'VBUS_SNS'), two_pin('VBUS_SNS', 'GND'), two_pin('VBUS', 'GND')
    ppd, opd = two_pin('PRE5V', 'GND'), two_pin('CONS_OFF', 'GND')
    rv = par(ohms(vh) + ohms(vl), ohms(vpd))
    out('\n== %s AO3401A gate CONS_OFF = %s BAT54C OR (VBUS, PRE5V), %s %s to GND' % (k['Q_CONS'], k['D_OFF'], opd.ref, opd.value))
    out('  console only: VBUS node %.1fk to GND (%s + %s || %s), PRE5V node %s %s: SS34 leakage I_R lifts each by I_R x R'
        % (rv / 1e3, vh.value, vl.value, vpd.value, ppd.ref, ppd.value))
    for ua in (10, 100, 500):
        v = ua * 1e-6 * max(rv, ohms(ppd))
        out('    I_R %3d uA: node %.2f V, gate <= %.2f V (minus the BAT54C), VGS >= %+.2f V' % (ua, v, v, v - 5.0))
    out('  the FET stays fully on (VGS <= -2.5 V, RDS(on) < 85 mOhm) up to I_R ~%.0f uA (SS34 IR max at 40 V: 0.5 mA at 25 C)'
        % (2.5 / max(rv, ohms(ppd)) * 1e6))
    out('  pull-down costs: %s %.2f mA from VBUS (USB in), %s %.2f mA from PRE5V (raw DC in), %s %.0f uA'
        % (vpd.ref, 5.0 / ohms(vpd) * 1e3, ppd.ref, 5.0 / ohms(ppd) * 1e3, opd.ref, 4.7 / ohms(opd) * 1e6))

    # ---- RP2350-E9 -------------------------------------------------------------------------------
    e9 = [p for p in D.PARTS if p.prefix == 'R' and 'E9' in p.desc]
    out('\n== RP2350-E9 (A2 stepping): pad input enabled, output off, between VIL and VIH -> ~%.0f uA source, pad near '
        '2.2 V; a pull to GND of <= %.1fk overcomes it' % (E9_ILEAK * 1e6, E9_RMAX / 1e3))
    for p in e9:
        r = ohms(p)
        net = next(n for n in p.pins.values() if n != 'GND')
        out('  %-4s %-5s on %-7s%s: worst leakage into it %.2f V (< VIL 0.8 V: %s); %.2f mA from the RP pin while it drives high'
            % (p.ref, p.value, net, ' (DNP)' if p.dnp else '', E9_ILEAK * r, 'yes' if E9_ILEAK * r < 0.8 else 'NO', 3.3 / r * 1e3))
    out("  BUF_EN low keeps %s's /OE2 high (SERVE_N), so a floating GPIO26 can never open the '541 onto the console bus"
        % k['U_BUF'])

    # ---- logic levels across the boundary ---------------------------------------------------
    out('\n== levels')
    out("  RP out (RP_D0-7, BUF_EN) -> 74HCT in: VOH %.2f V min vs VIH %.1f V: %+.2f V" % (RP_VOH_MIN, HCT_VIH, RP_VOH_MIN - HCT_VIH))
    out("  console -> RP FT pads (A0-A13 from the 6502 / 74LS244, /EN40 /EN80 from a 74LS139): VIH %.1f V at IOVDD 3.3 V; "
        "NMOS VOH %.1f V: %+.2f V, LS VOH %.1f V: %+.2f V" % (RP_VIH_FT, NMOS_VOH, NMOS_VOH - RP_VIH_FT, LS_VOH, LS_VOH - RP_VIH_FT))
    out("  console /EN40 /EN80 -> %s 74HCT08: LS VOH %.1f / VOL 0.5 V vs HCT VIH %.1f / VIL %.1f V: %+.2f / %+.2f V"
        % (k['U_AND'], LS_VOH, HCT_VIH, HCT_VIL, LS_VOH - HCT_VIH, HCT_VIL - 0.5))
    out("  %s 74HCT541 -> console data bus: VOH %.2f V at -6 mA vs the 6502's data VIH 2.0 V: %+.2f V"
        % (k['U_BUF'], HCT_VOH_6MA, HCT_VOH_6MA - 2.0))
    out("  PHI2 (2-port): console 74LS125 VOL 0.35-0.5 V + CR9 1N914 ~0.6 V -> pin 14 low 0.94-1.09 V (spice_checks.py) vs "
        "%s 74LVC1G17 VT- min %.2f V: %+.2f V worst; high via %s %s to CONS_5V, >= 4.2 V vs VT+ max %.2f V"
        % (k['U_PHI2'], LVC17_VTN_MIN, LVC17_VTN_MIN - 1.09, two_pin('CONS_5V', 'PHI2').ref, two_pin('CONS_5V', 'PHI2').value,
           LVC17_VTP_MAX[1]))
    out("  PHI2 on the RP directly would fail: 0.94-1.09 V low vs the RP's VIL 0.8 V; hence the Schmitt buffer at 5 V")
    out("  PWR_OK (74HCT14) and PHI2_RP (74LVC1G17) at 5 V into RP GPIO24 / 25: FT pads, IOVDD up whenever +5V is")
    adc_h, adc_l = two_pin('CONS_5V', 'VSENSE_ADC'), two_pin('VSENSE_ADC', 'GND')
    ka = ohms(adc_l) / (ohms(adc_h) + ohms(adc_l))
    out('  VSENSE_ADC (GPIO40, not FT): %s / %s = %.2f x: 4.5 / 5.0 / 5.5 V read %.2f / %.2f / %.2f V (ADC full scale 3.3 V); '
        'before IOVDD is up the pad sees <= %.0f uA through %s' % (adc_h.value, adc_l.value, ka, 4.5 * ka, 5.0 * ka, 5.5 * ka,
                                                               (5.5 * ka - 0.3) / ohms(adc_h) * 1e6 + 5.5 / ohms(adc_h) * 0, adc_h.ref))

    # ---- +5V from each source -----------------------------------------------------------------
    out('\n== +5V')
    out('  console only: CONS_5V through the P-FET (60 mOhm at -4.5 V): +5V = CONS_5V - ~30 mV at 0.5 A')
    for vbus in (5.25, 5.0, 4.75):
        out('  USB: VBUS %.2f V - SS34 VF 0.35-0.45 V -> +5V %.2f-%.2f V%s' % (vbus, vbus - 0.45, vbus - 0.35,
                                                                       '  (< 4.5 V 74HCT VCC min)' if vbus - 0.45 < 4.5 else ''))
    out('  raw DC: PRE5V 4.95-5.05 V (AP63205 VFB, CCM) - SS34 VF -> +5V 4.50-4.70 V; with VR1 above PRE5V by more than the '
        'diode difference the console still feeds part of the load through the body diode (spice_checks.py: <= 85 mA)')

    # ---- the cart's draw ---------------------------------------------------------------------
    out('\n== the cart on +5V')
    eta = 0.85
    s3_peak, s3_avg = 0.355, 0.12          # ESP32-S3-WROOM-1 802.11b TX at 20.5 dBm; FujiNet average (estimate)
    sd, cp = 0.10, 0.012                   # microSD write peak; CP2102N active
    buck_pk = 3.3 * (s3_peak + sd + cp) / (5.0 * eta)
    buck_avg = 3.3 * (s3_avg + 0.02 + cp) / (5.0 * eta)
    rp = 0.060                             # RP2350 at 200 MHz + IO (LDO: input = output current)
    hct = 3 * 0.00008 + 10 * 0.0005        # ICC 80 uA each + ~0.5 mA per input at a TTL / 3.3 V level
    ws = 3 * WS_MA
    misc = 5.0 / 4.7e3 + 5.0 / 122e3 + 5.0 / 200e3 + 3.3 / 4.7e3 + 0.0015   # PHI2 pull-up, dividers, BUF_EN, LED
    pk = buck_pk + rp + hct + ws + misc
    av = buck_avg + 0.04 + hct + 0.005 + misc
    out('  buck input %.0f mA peak (S3 TX 355 mA + SD 100 + CP2102N 12 at 3.3 V, eta %.2f), %.0f mA average'
        % (buck_pk * 1e3, eta, buck_avg * 1e3))
    out('  RP LDO %.0f, 74HCT + LVC %.0f, WS2812B %.0f (full white), misc %.1f mA' % (rp * 1e3, hct * 1e3, ws * 1e3, misc * 1e3))
    out('  total: ~%.0f mA peak (WiFi TX burst, LED white), ~%.0f mA average' % (pk * 1e3, av * 1e3))
    out('\n== from the console (no raw DC, no USB): VR1 = 78M05, %.1f A, which also feeds the console RAM, its expansion '
        'and the controllers (CA018087)' % VR1_A)
    out('  the cart alone: %.0f%% of VR1 at its peak, %.0f%% on average -- VR1 cannot also carry the console through '
        'a TX burst; on CA018087 (no raw DC on pin 11) run WiFi with USB power or cap the S3 TX power'
        % (pk / VR1_A * 100, av / VR1_A * 100))
    out('  P-FET loss at the peak: %.0f mW (60 mOhm)' % (pk * pk * 0.060 * 1e3))
    out('\n== from the edge raw DC (universal boards: pin 11, ahead of the power switch)')
    for vin in (9.0, 11.0, 13.0):
        for name, i5 in (('peak', pk), ('average', av)):
            pin = 5.0 * i5 / 0.88                          # AP63205 ~88 % at 5 V out, 9-13 V in
            iin = pin / vin
            vbuck = vin - iin * (ohms(two_pin('UNREG_F', 'PRE_VIN')) + PTC_R1MAX)
            out('  UNREG %4.1f V, %-7s: %.0f mA in; 2.2R %.0f mW (0603 %.0f mW), PTC hold %.2f / %.2f A at 23 / 40 C; '
                'AP63205 VIN %.1f V' % (vin, name, iin * 1e3, iin * iin * 2.2 * 1e3, R0603_W * 1e3,
                                         PTC_HOLD[23], PTC_HOLD[40], vbuck))
    out('  the peak is a WiFi burst of milliseconds: the PTC (seconds to trip at 2 x hold) and the 0603 (5 s at 2.5 x rated) '
        'ride it; the average sits well under both')
    cin = 2 * 22e-6
    out('  hot plug with the adapter live: %.0f uF of input ceramics through 2.2R + PTC: %.1f A peak, tau %.0f us'
        % (cin * 1e6, 13.0 / (2.2 + 0.3), (2.2 + 0.3) * cin * 1e6))

    # ---- misc --------------------------------------------------------------------------------
    rl = find(lambda p: p.prefix == 'R' and 'RP_LED' in p.pins.values())
    out('\n== misc')
    out('  RP LED: (3.3 - 1.8..2.0 V) / %s = %.1f-%.1f mA (KT-0603R VF 1.8-2.4 V at 20 mA)'
        % (rl.value, (3.3 - 2.0) / ohms(rl) * 1e3, (3.3 - 1.8) / ohms(rl) * 1e3))
    out('  crystal: 15 * 15 / 30 + 3 pF stray = %.1f pF (ABM8-272-T3 CL 10 pF)' % (15 * 15 / 30 + 3))
    for ma in (30, 60):
        out('  AP2112K at %d mA: %.0f mW from 5.0 V, Tj +%.0f C (SOT-23-5 ~250 C/W)' % (ma, (5.0 - 3.3) * ma, (5.0 - 3.3) * ma / 1e3 * 250))


if __name__ == '__main__':
    main()
