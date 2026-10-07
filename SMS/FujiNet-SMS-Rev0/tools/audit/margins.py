#!/usr/bin/env python3
"""Numbers behind the Rev0 schematic audit (docs/design-review-rev0.md, Part 1):
the console-sense divider against the SN74HCT14 thresholds, the P-FET gate under
the SS34's reverse leakage, the /WAIT FET gate against the RP2350 reset
pull-down, logic levels across the 3.3 V / 5 V boundary, the +5V rail with USB
plugged in, the console 5 V budget, LED current, crystal load and the RP LDO.

Parts are found by their nets in tools/design.py (not by reference), so the
script keeps working when references move.  Datasheet limits are the figures
quoted (with pages) in analysis/deep_review.json.

Usage: python3 tools/audit/margins.py
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import design as D


def find(pred, what):
    hits = [p for p in D.PARTS if pred(p)]
    if not hits:
        return None
    return hits[0]


def two_pin(a, b):
    """The resistor between nets a and b (either orientation), or None."""
    return find(lambda p: p.prefix == 'R' and sorted(n for n in p.pins.values()) == sorted([a, b]), '%s-%s' % (a, b))


def ohms(p):
    m = re.match(r'([\d.]+)([kMR]?)', p.value)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]


def par(*rs):
    return 1.0 / sum(1.0 / r for r in rs)


# ---- datasheet limits (pages in analysis/deep_review.json) -----------------
HCT14_VTP = {4.5: (1.2, 1.9), 5.5: (1.4, 2.1)}     # SN74HCT14 VT+ min/max (TI SCLS225G p.5)
HCT14_VTN = {4.5: (0.5, 1.2), 5.5: (0.6, 1.4)}     # VT- min/max
HCT_VIH, HCT_VIL = 2.0, 0.8                         # 74HCT inputs, VCC 4.5-5.5 V
SRAM_VIH_5V, SRAM_VIH_LOW = 2.4, 2.2                # AS6C4008: VCC 4.5-5.5 V / 2.7-4.5 V (p.3)
RP_VOH_MIN, RP_VIH_FT = 2.62, 2.0                   # RP2350 at IOVDD 3.3 V (p.1340)
RP_RPD = (36e3, 113e3)                              # RP2350 pull-down at IOVDD 3.3 V (p.1340)
N7002_VTH = (1.0, 1.6, 2.5)                         # 2N7002 (CJ) VGS(th) min/typ/max at 250 uA (p.2)
N7002_K_MIN = 0.5 / (10 - 2.5) ** 2                 # A/V^2 from ID(on) >= 500 mA at VGS 10 V, worst VTH
AO3401_VTH = (-0.5, -0.9, -1.3)                     # AO3401A VGS(th) (p.2)
SS34_IR = (0.5e-3, 20e-3)                           # SS34 max reverse current at 40 V, 25 C / 100 C (p.2)
Z80_VIL = 0.8                                       # Z80 input low (TTL)


def main():
    out = print
    # ---- console sense: VSENSE = CONS_5V * Rb / (Rt + Rb) into the '14 -----------------
    rt, rb = two_pin('CONS_5V', 'VSENSE'), two_pin('VSENSE', 'GND')
    k = ohms(rb) / (ohms(rt) + ohms(rb))
    out('== PWR_OK sense: %s %s / %s %s, ratio %.3f' % (rt.ref, rt.value, rb.ref, rb.value, k))
    for v in (4.5, 4.75, 5.0, 5.25, 5.5):
        out('  CONS_5V %.2f V -> VSENSE %.2f V' % (v, v * k))
    out('  rising: PWR_OK guaranteed high once VSENSE > VT+max 1.9 V (VCC 4.5) / 2.1 V (VCC 5.5): CONS_5V > %.2f / %.2f V'
        % (1.9 / k, 2.1 / k))
    out('  falling: PWR_OK guaranteed low once VSENSE < VT-min 0.5 / 0.6 V: CONS_5V < %.2f / %.2f V; '
        'may already drop at VT-max 1.2 / 1.4 V: CONS_5V < %.2f / %.2f V' % (0.5 / k, 0.6 / k, 1.2 / k, 1.4 / k))
    out('  margin at the console minimum (4.5 V): VSENSE %.2f V - VT+max 1.9 V = %+.2f V' % (4.5 * k, 4.5 * k - 1.9))
    out('  VI <= VCC check (USB in, P-FET off, body diode 0.7 V): CONS_5V 5.25 -> VSENSE %.2f V, +5V >= max(5.25-0.7, VBUS-0.45) = %.2f V'
        % (5.25 * k, 5.25 - 0.7))
    out('  divider current %.0f uA; source impedance %.1f k' % (5.0 / (ohms(rt) + ohms(rb)) * 1e6, par(ohms(rt), ohms(rb)) / 1e3))
    out('  NOTE: the NES Rev0 review used TI SNx4HC14 numbers (VT+ 0.7 x VCC) from a mis-labelled PDF; the HCT14 trips at TTL levels.')

    # ---- P-FET gate (= VBUS) with no USB: SS34 reverse leakage into the pull-down ---------
    vh, vl = two_pin('VBUS', 'VBUS_SNS'), two_pin('VBUS_SNS', 'GND')
    pd_planned = two_pin('VBUS', 'GND')
    div = ohms(vh) + ohms(vl)
    out('\n== P-FET gate (VBUS net) with the console powering the cart, SS34 reverse-biased by +5V')
    out('  pull-down today: %s + %s = %.0f k%s' % (vh.value, vl.value, div / 1e3,
                                                     ('; plus %s %s VBUS-GND' % (pd_planned.ref, pd_planned.value)) if pd_planned else ''))
    cases = [('69k divider only', div), ('with 4.7k VBUS-GND (planned)', par(div, 4.7e3))]
    for name, r in cases:
        for ua in (10, 20, 50, 100, 500):
            vg = min(ua * 1e-6 * r, 5.0)
            vgs = vg - 5.0
            state = 'fully on (Rds < 85 mOhm at -2.5 V)' if vgs <= -2.5 else 'on, weak' if vgs <= -1.3 else 'may be off: body diode carries the cart (~0.7 V drop)'
            out('  %-30s I_R %3d uA -> gate %.2f V, VGS %+.2f V: %s' % (name, ua, vg, vgs, state))
    out('  SS34 IR max at 40 V: 0.5 mA at 25 C, 20 mA at 100 C; with 4.7k the gate stays under 2.5 V up to %.0f uA'
        % (2.5 / par(div, 4.7e3) * 1e6))
    out('  4.7k costs %.2f mA from VBUS with USB in; VBUS discharge tau after unplug: %.1f ms (now %.0f ms, 1.1 uF)'
        % (5.0 / 4.7e3 * 1e3, par(div, 4.7e3) * 1.1e-6 * 1e3, div * 1.1e-6 * 1e3))

    # ---- /WAIT: 2N7002 gate = pull-up to +3V3_RP against the RP2350 reset pull-down ---------
    q = find(lambda p: p.value == '2N7002', 'Q /WAIT')
    rpu = find(lambda p: p.prefix == 'R' and 'WAIT_GATE' in p.pins.values(), 'R WAIT_GATE')
    out('\n== /WAIT hold before the firmware runs: %s gate, %s %s pull-up to +3V3_RP vs RP2350 RPD 36-113k' % (q.ref, rpu.ref, rpu.value))
    for r in sorted({ohms(rpu), 4.7e3, 2.2e3}, reverse=True):
        for vrp in (3.3, 3.0):
            vg_min = vrp * RP_RPD[0] / (RP_RPD[0] + r)
            vg_max = vrp * RP_RPD[1] / (RP_RPD[1] + r)
            ov = vg_min - N7002_VTH[2]
            idmin = N7002_K_MIN * ov * ov if ov > 0 else 0.0
            out('  pull-up %4.1fk, +3V3_RP %.1f V: gate %.2f-%.2f V; worst VTH 2.5 V -> overdrive %+.2f V, ID >= ~%.2f mA (square law)'
                % (r / 1e3, vrp, vg_min, vg_max, ov, idmin * 1e3))
        out('    static current while the firmware holds GPIO34 low: %.2f mA' % (3.3 / r * 1e3))
    for rc in (10e3, 4.7e3, 3.3e3):
        out('  console /WAIT pull-up %.1fk needs %.2f mA to reach Z80 VIL 0.8 V' % (rc / 1e3, (5.0 - Z80_VIL) / rc * 1e3))

    # ---- logic levels across the boundary -------------------------------------------------
    out('\n== levels')
    out('  RP out -> 74HCT in: VOH %.2f V (min, rated load; ~3.3 V into CMOS) vs VIH %.1f V: %+.2f V' % (RP_VOH_MIN, HCT_VIH, RP_VOH_MIN - HCT_VIH))
    out('  RP out (SA13-19, SA19 = U2 /CE) -> AS6C4008: VIH %.1f V at VCC 4.5-5.5 V: %+.2f V (min VOH); %+.2f V at 3.25 V'
        % (SRAM_VIH_5V, RP_VOH_MIN - SRAM_VIH_5V, 3.25 - SRAM_VIH_5V))
    out('  RP out (D0-D7 via 100R, LOAD) -> AS6C4008 DQ: same VIH %.1f V; -> Z80 (TTL VIH 2.0 V): %+.2f V' % (SRAM_VIH_5V, RP_VOH_MIN - 2.0))
    out('  console -> RP FT pads: VIH %.1f V at IOVDD 3.3 V (not 0.65 x IOVDD); NMOS VOH min 2.4 V: %+.2f V' % (RP_VIH_FT, 2.4 - RP_VIH_FT))

    # ---- +5V with USB in -----------------------------------------------------------------
    out('\n== +5V with USB plugged in (P-FET off, gate = VBUS)')
    for vbus in (5.25, 5.0, 4.75):
        for vf in (0.35, 0.45):
            v5 = vbus - vf
            out('  VBUS %.2f V, SS34 VF %.2f V -> +5V %.2f V (console on: >= CONS_5V - 0.7 V body diode) %s'
                % (vbus, vf, v5, '< 4.5 V 74HCT VCC min' if v5 < 4.5 else ''))

    # ---- console 5 V budget ----------------------------------------------------------------
    out('\n== cart draw from CONS_5V (console only)')
    eta = 0.85
    s3_peak, s3_avg = 0.355, 0.12          # ESP32-S3-WROOM-1 peak TX 802.11b 20.5 dBm (p.29); FujiNet average (estimate)
    sd, cp = 0.10, 0.012                   # microSD write peak; CP2102N active (self-powered)
    buck_pk = 3.3 * (s3_peak + sd + cp) / (5.0 * eta)
    buck_avg = 3.3 * (s3_avg + 0.02 + cp) / (5.0 * eta)
    rp = 0.060                             # RP2350 at 200 MHz + IO (LDO: input = output current)
    sram = 0.010 + 0.002                   # selected AS6C4008 ICC1 10 mA max at 1 us cycle; the other chip standby (U2 /CE at 3.3 V: TTL level)
    hct = 5 * 0.00002 + 12 * 0.0005        # ICC 20 uA each + ~0.5 mA per TTL-level input (dICC 2.9 mA max at 2.4 V/5.5 V)
    ws = 0.036                             # WS2812B-2020 12 mA x 3 at full white
    misc = 3.3 / 4.7e3 + 5.0 / 122e3
    pk = buck_pk + rp + sram + hct + ws + misc
    av = buck_avg + 0.04 + sram + hct + 0.005 + misc
    out('  buck input %.0f mA peak (S3 TX 355 mA + SD 100 + CP2102N 12 at 3.3 V, eta %.2f), %.0f mA average' % (buck_pk * 1e3, eta, buck_avg * 1e3))
    out('  RP LDO %.0f, SRAM %.0f, 74HCT %.0f, WS2812 %.0f, misc %.1f mA' % (rp * 1e3, sram * 1e3, hct * 1e3, ws * 1e3, misc * 1e3))
    out('  total: ~%.0f mA peak (WiFi TX burst, LED white), ~%.0f mA average' % (pk * 1e3, av * 1e3))
    out('  P-FET loss at peak: %.0f mW (60 mOhm at -4.5 V); edge contacts 2 x +5V pins' % (pk * pk * 0.060 * 1e3))

    # ---- misc --------------------------------------------------------------------------------
    rl = find(lambda p: p.prefix == 'R' and 'RP_LED' in p.pins.values(), 'R LED')
    out('\n== misc')
    out('  RP LED: (3.3 - 1.8..2.0 V) / %s = %.1f-%.1f mA (KT-0603R VF 1.8-2.4 V at 20 mA)'
        % (rl.value, (3.3 - 2.0) / ohms(rl) * 1e3, (3.3 - 1.8) / ohms(rl) * 1e3))
    out('  crystal: 15 * 15 / 30 + 3 pF stray = %.1f pF (ABM8-272-T3 CL 10 pF)' % (15 * 15 / 30 + 3))
    for ma in (30, 60):
        out('  AP2112K at %d mA: %.0f mW from 5.0 V, Tj +%.0f C (SOT-23-5 ~250 C/W)' % (ma, (5.0 - 3.3) * ma, (5.0 - 3.3) * ma / 1e3 * 250))


if __name__ == '__main__':
    main()
