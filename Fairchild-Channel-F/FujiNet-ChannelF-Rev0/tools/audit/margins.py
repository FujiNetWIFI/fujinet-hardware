#!/usr/bin/env python3
"""Numbers behind the Rev0 audit (docs/design-review-rev0.md): logic levels across the console's
5 V bus, the two SN74LVC4245A and the RP2040; the DIR pull-up against the RP2040's pad pull-down;
/INTREQ's open drain; +5V through the OR diodes into the two regulators; the cart's draw from the
console's 7805; the crystal's load; the LED currents.

Parts are found by their nets in tools/design.py (not by reference), so the script keeps working
when references move.  Every datasheet figure is quoted with its source here and, with pages, in
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
F38_DB_VIH = 2.9          # F3850 Table 7: DB0-7 VIH min (VDD 5 V +- 5 %)
F38_DB_VOH = 3.9          # DB0-7 VOH min, IOH -100 uA
F38_ROMC_VOH = 3.9        # ROMC0-4 VOH min
F38_PHI_WR_VOH = 4.4      # PHI, WRITE VOH min, IOH -50 uA
F38_INT_VIL = 0.8         # INT REQ VIL max; internal pull-up, IIL -0.1 .. -1.0 mA at VSS
F38_INT_IIL = 1.0e-3
LVC_A_VIH, LVC_A_VIL = 2.0, 0.8          # SN74LVC4245A A port (and DIR, /OE), VCCA 4.5-5.5 V (SCAS375K 5.3)
LVC_A_VOH_100U = 4.3                      # A port VOH, VCCA 4.5 V, IOH -100 uA (5.7)
LVC_A_VOH_24M = 3.7                       # ... IOH -24 mA
LVC_B_VOH = 3.0 - 0.2                     # B port VOH, VCCB 3.0 V, IOH -100 uA: VCCB - 0.2 (5.8)
LVC_VCCA = (4.5, 5.5)                     # recommended VCCA
RP_VIH, RP_VIL = 2.0, 0.8                 # RP2040 IOVDD 3.3 V: VIH min / VIL max (datasheet 5.5.3)
RP_PD_MIN = 50e3                          # RP2040 pad pull-down, 50-80 kOhm (5.5.3)
RP_IOVDD_MIN = 3.0                        # the AP2112K's 3.3 V -10 % worst case used here
CONSOLE_5V = (4.75, 5.25)                 # FVE100: 7805 (Q5) +5 V, 1.5 A; +-5 %
CONSOLE_5V_A = 1.5
SS34_VF = 0.45                            # SS34 at ~0.5 A (Vishay curve; 0.5 V max at 3 A)
AP2112_DROP = 0.25                        # AP2112K-3.3 dropout typ at 600 mA (0.4 max); ~0.1 V at 100 mA
AP2112_VIN_MAX = 6.0
AP63203_VIN_MIN = 3.8                     # AP63203 VIN 3.8-32 V
S3_PEAK = 0.355                           # ESP32-S3-WROOM-1 Table 6-4: 802.11b TX peak, 3.3 V
S3_RX = 0.097
RP_ACTIVE = 0.04                          # RP2040 at 125 MHz, both cores busy, plus its flash: ~40 mA
CP2102N = 0.0095                          # CP2102N active (datasheet: 9.5 mA typ)
WS_MAX = 3 * 0.012                        # WS2812B-2020: 12 mA per channel
BUCK_EFF = 0.85
BUCK_FSW = 1.1e6                          # AP63203 switching frequency
XTAL_CL = 10e-12                          # ABM8-272-T3 load capacitance
C_STRAY = (2e-12, 5e-12)                  # board + RP2040 XIN/XOUT pin capacitance, typical range


def main():
    fails = []
    out = []

    def line(name, val, ok):
        out.append('%-4s %s' % ('ok' if ok else 'FAIL', name % val if '%' in name else name))
        if not ok:
            fails.append(name)

    # ---- 1. the bus levels -------------------------------------------------------------------------
    line('console -> cart: F3850 DB / ROMC VOH %.1f V into the A-port VIH 2.0 V: margin %%.1f V' % F38_DB_VOH,
         min(F38_DB_VOH, F38_ROMC_VOH) - LVC_A_VIH, min(F38_DB_VOH, F38_ROMC_VOH) > LVC_A_VIH)
    line('console -> cart: PHI / WRITE VOH 4.4 V into the A-port VIH 2.0 V: margin %.1f V',
         F38_PHI_WR_VOH - LVC_A_VIH, F38_PHI_WR_VOH > LVC_A_VIH)
    line('cart -> console: A-port VOH 4.3 V (VCCA 4.5 V, 100 uA) into the F3850 DB VIH 2.9 V: margin %.1f V',
         LVC_A_VOH_100U - F38_DB_VIH, LVC_A_VOH_100U > F38_DB_VIH)
    line('cart -> console at 24 mA: A-port VOH 3.7 V vs DB VIH 2.9 V: margin %.1f V',
         LVC_A_VOH_24M - F38_DB_VIH, LVC_A_VOH_24M > F38_DB_VIH)
    line('translators -> RP2040: B-port VOH 2.8 V (VCCB 3.0 V) into the RP VIH 2.0 V: margin %.1f V',
         LVC_B_VOH - RP_VIH, LVC_B_VOH > RP_VIH)
    line('the console 5 V (%.2f-%.2f V) inside the translators\' VCCA range 4.5-5.5 V' % CONSOLE_5V, None,
         LVC_VCCA[0] <= CONSOLE_5V[0] and CONSOLE_5V[1] <= LVC_VCCA[1])
    # ---- 2. DIR: the pull-up against the pad pull-down through reset / boot ----------------------------
    rdir = two_pin(D.RP_RAIL, 'RP_DIR')
    v = RP_IOVDD_MIN * RP_PD_MIN / (RP_PD_MIN + ohms(rdir))
    line('DIR held high through RP reset: %s to %s against a 50 kOhm pad pull-down at %.1f V: %%.2f V >= VIH 2.0'
         % (rdir.value, D.RP_RAIL, RP_IOVDD_MIN), v, v >= LVC_A_VIH)
    # ---- 3. /INTREQ: the open drain -------------------------------------------------------------------
    rpd = two_pin('RP_INTREQ', 'GND')
    line('/INTREQ gate pull-down %s: the FET stays off with GP16 floating (never driven by the firmware)'
         % rpd.value, None, ohms(rpd) <= 1e6)
    # JSCJ 2N7002: Vth(GS) 1.0-2.5 V at 250 uA; RDS(on) <= 7 Ohm only at VGS 5 V.  At VGS 3.3 V (0.8 V past the
    # worst threshold) VOL <= 0.8 V at 1 mA needs only RDS <= 800 Ohm: orders of magnitude of room
    line('/INTREQ: the F3850 pull-up sinks up to %.1f mA; GP16 at 3.3 V is %%.1f V past the 2N7002\'s worst Vth '
         '(2.5 V at 250 uA), and VOL < VIL 0.8 needs RDS < 800 Ohm' % (F38_INT_IIL * 1e3), 3.3 - 2.5, 3.3 > 2.5)
    # ---- 4. +5V and the regulators ---------------------------------------------------------------------
    v5 = CONSOLE_5V[0] - SS34_VF
    line('+5V from the console: %.2f V - SS34 %.2f V = %%.2f V >= AP63203 VIN 3.8 V' % (CONSOLE_5V[0], SS34_VF),
         v5, v5 >= AP63203_VIN_MIN)
    line('+3V3_RP: AP2112K needs 3.3 + %.2f V; +5V min %%.2f V' % AP2112_DROP, v5, v5 >= 3.3 + AP2112_DROP)
    line('AP2112K VIN max 6.0 V >= +5V max %.2f V', CONSOLE_5V[1], CONSOLE_5V[1] <= AP2112_VIN_MAX)
    # ---- 5. the cart's draw from the console's 7805 ----------------------------------------------------
    i3 = S3_PEAK + CP2102N
    i5 = i3 * 3.3 / (BUCK_EFF * v5) + RP_ACTIVE + WS_MAX
    line('peak +5V draw (S3 TX %.0f mA + CP2102N through the buck, RP + flash through the LDO, WS2812 white): '
         '%%.0f mA' % (S3_PEAK * 1e3), i5 * 1e3, i5 < 0.6)
    line('... of the console 7805\'s %.1f A (the console itself draws an unknown share: measure at bring-up)'
         % CONSOLE_5V_A, None, i5 < CONSOLE_5V_A)
    # ---- 5b. the buck's inductor: datasheet Eq. 7 at this board's input (its Table 2's 3.9 uH is for 12 V in
    # and a 2 A load; it allows 2.2-10 uH and asks for a ripple of 30-50 % of the maximum load)
    lb = next(p for p in D.PARTS if p.key == 'L_BUCK')
    L = float(lb.value.replace('uH', '')) * 1e-6
    vin = 5.0
    ripple = 3.3 * (vin - 3.3) / (vin * L * BUCK_FSW)
    line('AP63203 ripple, %s at %.1f V in, %.1f MHz: %%.2f A = %.0f %%%% of the S3 side\'s %.2f A peak (datasheet: 30-50 %%%%; '
         'L within its 2.2-10 uH)' % (lb.value, vin, BUCK_FSW / 1e6, 100 * ripple / i3, i3), ripple,
         0.3 * i3 * 0.95 <= ripple <= 0.5 * i3 and 2.2e-6 <= L <= 10e-6)
    p_ldo = (CONSOLE_5V[1] - 0.3 - 3.3) * RP_ACTIVE
    line('AP2112K dissipation (5.25 V - 0.3 V diode - 3.3 V) x %.0f mA: %%.0f mW (SOT-23-5)' % (RP_ACTIVE * 1e3),
         p_ldo * 1e3, p_ldo < 0.3)
    # ---- 6. crystal -----------------------------------------------------------------------------------
    cx = D.CAP['15pF']
    cl = [7.5e-12 + c for c in C_STRAY]
    line('crystal load: 2 x 15 pF in series + %.0f-%.0f pF stray = %%s pF vs ABM8-272-T3 CL 10 pF'
         % (C_STRAY[0] * 1e12, C_STRAY[1] * 1e12), '%.1f-%.1f' % (cl[0] * 1e12, cl[1] * 1e12),
         cl[0] <= XTAL_CL * 1.3 and cl[1] >= XTAL_CL * 0.85)
    # ---- 7. LEDs --------------------------------------------------------------------------------------
    rl = two_pin('RP_LED', 'RP_LED_A')
    i = (3.3 - 2.7) / ohms(rl)          # KT-0603G (InGaN green): VF 2.6-3.1 V at 5 mA, ~2.7 V near 2 mA
    line('RP activity LED: (3.3 - ~2.7 V) / %s = %%.1f mA (KT-0603G green, VF 2.6-3.1 V at 5 mA)' % rl.value,
         i * 1e3, 0.5e-3 < i < 10e-3)
    print('\n'.join(out))
    print('margins: %s' % ('%d FAILED' % len(fails) if fails else 'all positive'))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
