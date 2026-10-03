#!/usr/bin/env python3
"""Power-path numbers for the Rev0 audit (docs/design-review-rev0.md).
Datasheet figures: AP63203 tSS 4 ms (Diodes DS, Electrical Characteristics);
AP2112K-3.3 tS 20 us typ (no load, 1 uF), short-current limit 50 mA at VOUT = 0 V
(fold-back), dropout 250 mV typ at 600 mA, SOT-25 theta-JA ~250 C/W class; SS34 VF ~0.35-0.4 V at 0.4 A (MCC curve); RP2350 FT pads 5.5 V only with
IOVDD at 3.3 V (DS p.1332), VIH 0.65 x IOVDD; WS2812B-2020-V6 VDD 3.7-5.3 V,
VIH 2.7 V min; KT-0603G VF 2.6-3.1 V."""
print('IOVDD source: buck soft-start %.0f us vs LDO start-up %.0f us -> pads unpowered for up to ~%.0f ms on the old buck feed'
      % (4000, 20, 4))
c_rp = 9 * 0.1 + 4.7 + 10 + 4.7 + 1.0      # uF on +3V3_RP: 9 x 100 nF, VREG_VIN 4.7, bulk 10, VREG_AVDD 4.7 (33R), LDO out 1
print('+3V3_RP capacitance %.1f uF: a STEP input (hot plug) charges it at the 50 mA fold-back limit in up to %.1f ms'
      % (c_rp, c_rp * 3.3 / 50e3 * 1e3))
for ramp in (0.5, 1.0, 2.0):     # console rail slew, V/ms (a 7805 behind big caps: ms-scale)
    print('console rail ramping %.1f V/ms: tracking it needs %.0f mA (< 50 mA limit: IOVDD follows CONS_5V - VF while in dropout)'
          % (ramp, c_rp * ramp))
for cons in (4.75, 5.0, 5.25, 5.5):
    vs = cons * 150 / (100 + 150)
    print('CONS_5V %.2f V -> VSENSE %.2f V (GP26 ADC pad, IOVDD 3.3 V: abs max IOVDD + 0.5; VIH 2.15 V)' % (cons, vs))
print('VSENSE reads high down to %.2f V of console rail' % (2.145 / 0.6))
for cons in (4.75, 5.0):
    v5 = cons - 0.38
    print('CONS_5V %.2f V -> +5V %.2f V: buck VIN min 3.8 V (margin %.2f), LDO needs 3.3 + 0.25 = 3.55 V (margin %.2f), '
          'WS2812 VDD min 3.7 V (margin %.2f)' % (cons, v5, v5 - 3.8, v5 - 3.55, v5 - 3.7))
i_rp = 0.060
print('LDO: RP2354A ~%.0f mA (IOVDD + VREG_VIN, core SMPS) x (5.0-0.38-3.3) V = %.0f mW, ~+%.0f C in SOT-23-5'
      % (i_rp * 1e3, i_rp * (5.0 - 0.38 - 3.3) * 1e3, i_rp * (5.0 - 0.38 - 3.3) * 250))
print('WS2812 data: S3 VOH ~3.3 V vs VIH min 2.7 V -> %.1f V margin; 330R series' % (3.3 - 2.7))
print('activity LED: 1k gave (3.3 - 2.85) / 1k = %.2f mA; 330R gives %.1f-%.1f mA (VF 2.85-2.6 V; GP25 4 mA drive)' % ((3.3 - 2.85) / 1.0, (3.3 - 2.85) / 0.33, (3.3 - 2.6) / 0.33))
