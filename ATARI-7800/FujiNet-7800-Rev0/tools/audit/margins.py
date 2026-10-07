#!/usr/bin/env python3
"""Numbers behind the Rev0 schematic audit (docs/design-review-rev0.md, Part 1):
the console-sense divider against the SN74HCT14 thresholds, the P-FET gate under the SS34's
reverse leakage, the /IRQ FET against the console's 2.2k pull-up, the RP2350-E9 pull-downs, the
/HALT isolation, logic levels across the 3.3 V / 5 V boundary, the cart audio against a POKEY
cart into the console's EXT AUDIO input, the +5V rail with USB plugged in, the console 5 V
budget, the power-on race against the BIOS, LED current, crystal load and the RP LDO.

Parts are found by their nets in tools/design.py (not by reference).  Datasheet limits are the
figures quoted (with pages) in analysis/deep_review.json; console facts from the Atari 7800
schematic C025231-001 (NTSC) / C070354 (PAL) and the GCC1702B MARIA specification.

Usage: python3 tools/audit/margins.py
"""
import math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import design as D


def find(pred):
    hits = [p for p in D.PARTS if pred(p)]
    return hits[0] if hits else None


def two_pin(a, b, prefix='R'):
    return find(lambda p: p.prefix == prefix and sorted(n for n in p.pins.values()) == sorted([a, b]))


def val(p):
    m = re.match(r'([\d.]+)\s*([kMRunp]?)', p.value)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0, 'u': 1e-6, 'n': 1e-9, 'p': 1e-12}[m.group(2)]


def par(*rs):
    return 1.0 / sum(1.0 / r for r in rs)


# ---- datasheet / console limits ---------------------------------------------------------------
HCT14_VTP = {4.5: (1.2, 1.9), 5.5: (1.4, 2.1)}     # SN74HCT14 VT+ min/max (TI SCLS225G)
HCT_VIH = 2.0                                       # 74HCT inputs, VCC 4.5-5.5 V
SRAM_VIH = 2.4                                      # AS6C4008 at VCC 4.5-5.5 V
RP_VOH_MIN, RP_VIH_FT = 2.62, 2.0                   # RP2350 at IOVDD 3.3 V
N7002_VTH_MAX = 2.5                                 # 2N7002 (CJ) VGS(th) max
N7002_K_MIN = 0.5 / (10 - 2.5) ** 2                 # A/V^2 from ID(on) >= 500 mA at VGS 10 V, worst VTH
SS34_IR = (0.5e-3, 20e-3)                           # SS34 max reverse current at 40 V, 25 / 100 C
R_IRQ_PU = 2.2e3                                    # console R32 2.2k /IRQ pull-up (NTSC and PAL)
SALLY_VIL = 0.8                                     # NMOS 6502 input low
EAUD_C, EAUD_R = 0.1e-6, 6.8e3                      # console C10 0.1 uF + R5 6.8k into the audio sum
TIA_R_NTSC, TIA_R_PAL = 18e3, 6.8e3                 # R6: the TIA's own resistor into that sum
POKEY_RL, POKEY_RS = 1e3, 12e3                      # POKEY carts C026461 / C301105: 1k pull-up, 12k series
MARIA_IOH, MARIA_CL = 100e-6, 25e-12                # MARIA HALT output: Ioh 100 uA at 2.4 V; 30 ns into 25 pF
E9_LIMIT = 8.2e3                                    # RP2350-E9: an external pull-down of 8.2k or less


def main():
    out = print
    # ---- console sense ----------------------------------------------------------------------------
    rt, rb = two_pin('CONS_5V', 'VSENSE'), two_pin('VSENSE', 'GND')
    k = val(rb) / (val(rt) + val(rb))
    out('== PWR_OK sense: %s %s / %s %s, ratio %.3f' % (rt.ref, rt.value, rb.ref, rb.value, k))
    out('  CONS_5V 4.5 / 5.0 / 5.5 V -> VSENSE %.2f / %.2f / %.2f V' % (4.5 * k, 5.0 * k, 5.5 * k))
    out('  PWR_OK guaranteed high above CONS_5V %.2f V (VT+max 1.9 V at VCC 4.5); low below %.2f V (VT-min 0.5 V)'
        % (1.9 / k, 0.5 / k))
    out('  margin at 4.5 V: %+.2f V over VT+max' % (4.5 * k - 1.9))

    # ---- P-FET gate under SS34 leakage ---------------------------------------------------------
    vh, vl = two_pin('VBUS', 'VBUS_SNS'), two_pin('VBUS_SNS', 'GND')
    pd = two_pin('VBUS', 'GND')
    r = par(val(vh) + val(vl), val(pd))
    out('\n== P-FET gate (VBUS) with the console powering the cart: %s %s || %s+%s = %.2f k' %
        (pd.ref, pd.value, vh.value, vl.value, r / 1e3))
    for ua in (50, 100, 500):
        vg = ua * 1e-6 * r
        out('  SS34 leakage %3d uA -> gate %.2f V, VGS %+.2f V (AO3401A VGS(th) -0.5..-1.3 V): %s' %
            (ua, vg, vg - 5.0, 'fully on' if vg - 5.0 <= -2.5 else 'on' if vg - 5.0 <= -1.3 else 'MAY BE OFF'))

    # ---- /IRQ: 2N7002 against the console's 2.2k ------------------------------------------------
    rg = two_pin('IRQ_GATE', 'GND')
    i_need = (5.0 - 0.4) / R_IRQ_PU
    ov = 3.3 - N7002_VTH_MAX
    out('\n== /IRQ: console R32 2.2k pull-up; %s 2N7002 needs %.2f mA to pull to 0.4 V' %
        (find(lambda p: p.value == '2N7002').ref, i_need * 1e3))
    out('  GPIO28 high (3.3 V): worst VTH 2.5 V -> overdrive %.1f V, ID >= ~%.1f mA (square law, worst K): %s' %
        (ov, N7002_K_MIN * ov * ov * 1e3, 'OK' if N7002_K_MIN * ov * ov > i_need else 'MARGINAL'))
    out('  reset / no firmware: GPIO28 pad pull-down || %s %s holds the gate at 0 V: /IRQ released' % (rg.ref, rg.value))

    # ---- RP2350-E9 pull-downs on the slot-table enables ------------------------------------------
    out('\n== slot-table enables before the PIO runs (RP2350-E9, stepping A2: <= 8.2k overcomes the leakage)')
    for n in ('ROM_EN', 'RAM_EN', 'A8MASK'):
        p = two_pin(n, 'GND')
        out('  %-7s %s %s to GND: %s; %.2f mA while the PIO drives it high' %
            (n, p.ref, p.value, 'OK' if val(p) <= E9_LIMIT else 'TOO WEAK', 3.3 / val(p) * 1e3))

    # ---- /HALT isolation ---------------------------------------------------------------------------
    rh = two_pin('HALT_N', 'HALT_RP')
    c_cart = 5e-12 + 6e-12 + 6e-12      # RP pin + ~50 mm to the RP + the bring-up pad branch (estimate)
    out('\n== /HALT: MARIA output Ioh %.0f uA at 2.4 V, rated 30 ns into %.0f pF; console J1-2 also carries Q13'
        % (MARIA_IOH * 1e6, MARIA_CL * 1e12))
    out('  %s %s at the finger: the console sees ~1 pF of stub; the cart side (~%.0f pF) sees tau = %.0f ns'
        ' (spice_checks.py: J1-2 rise 23.5 ns with it, 40 ns without, 49 ns behind 1k)'
        % (rh.ref, rh.value, c_cart * 1e12, val(rh) * c_cart * 1e9))
    out('  without it the cart would add ~%.0f pF to a 25 pF-rated weak output' % (c_cart * 1e12))

    # ---- levels ---------------------------------------------------------------------------------
    out('\n== levels')
    out('  RP out -> 74HCT in: VOH %.2f V (min) vs VIH %.1f V: %+.2f V' % (RP_VOH_MIN, HCT_VIH, RP_VOH_MIN - HCT_VIH))
    out('  RP out (SA13-18) -> AS6C4008 VIH %.1f V: %+.2f V (min VOH), %+.2f V at 3.25 V' %
        (SRAM_VIH, RP_VOH_MIN - SRAM_VIH, 3.25 - SRAM_VIH))
    out('  RP D0-D7 via 100R -> SALLY / MARIA (NMOS, TTL VIH 2.0 V): %+.2f V' % (RP_VOH_MIN - 2.0))
    out('  console NMOS outputs -> RP FT pads: VIH %.1f V at IOVDD 3.3 V; NMOS VOH min 2.4 V: %+.2f V' %
        (RP_VIH_FT, 2.4 - RP_VIH_FT))

    # ---- cart audio vs a POKEY cart --------------------------------------------------------------
    r1, c1 = two_pin('AUD_PWM', 'AUD_LP'), two_pin('AUD_LP', 'GND', 'C')
    r2, c2 = two_pin('AUD_LP', 'AUD_LVL'), two_pin('AUD_LVL', 'EAUDIO', 'C')
    fc = 1 / (2 * math.pi * val(r1) * val(c1))
    out('\n== cart audio into the console (C10 0.1 uF + R5 6.8k into its audio sum, a transistor emitter: ~0 ohm)')
    out('  PWM low-pass %s / %s: fc %.1f kHz; level %s; DC block %s (console C10 blocks DC too)' %
        (r1.value, c1.value, fc / 1e3, r2.value, c2.value))
    v_lp = 3.3 * (val(r2) + EAUD_R) / (val(r2) + EAUD_R + val(r1))
    i_ours = v_lp / (val(r2) + EAUD_R)
    i_pokey = 3.3 / (POKEY_RS + POKEY_RL + EAUD_R)          # four channels at full volume ~3.3 Vpp at POKEY AUD
    out('  ours at full PWM swing: %.2f Vpp at AUD_LP -> %.0f uA p-p into the sum' % (v_lp, i_ours * 1e6))
    out('  a POKEY cart (C026461 / C301105: 1k pull-up, 12k series), 4 channels full volume ~3.3 Vpp: %.0f uA p-p'
        % (i_pokey * 1e6))
    out('  ratio %.2f (%+.1f dB): the 10k level matches a POKEY cart; TIA through R6 18k (NTSC) / 6.8k (PAL)'
        % (i_ours / i_pokey, 20 * math.log10(i_ours / i_pokey)))
    out('  high-pass corners: ours %.0f Hz (1 uF into 16.8k), console C10 %.0f Hz (0.1 uF into ~18k): the console\'s dominates'
        % (1 / (2 * math.pi * val(c2) * (val(r2) + EAUD_R)), 1 / (2 * math.pi * EAUD_C * (val(r2) + EAUD_R + val(r1)))))

    # ---- +5V with USB in ---------------------------------------------------------------------------
    out('\n== +5V with USB plugged in (P-FET off, gate = VBUS): VBUS 5.0 V, SS34 VF 0.35-0.45 V -> +5V 4.55-4.65 V'
        ' (74HCT VCC min 4.5 V); USB alone also powers the cart with the console off (no back-feed: body diode reversed)')

    # ---- console 5 V budget ----------------------------------------------------------------------
    eta = 0.85
    s3_peak, s3_avg = 0.355, 0.12
    buck_pk = 3.3 * (s3_peak + 0.10 + 0.012) / (5.0 * eta)
    buck_avg = 3.3 * (s3_avg + 0.02 + 0.012) / (5.0 * eta)
    rp, sram, hct, ws = 0.060, 0.010, 4 * 0.00002 + 10 * 0.0005, 0.036
    misc = 3 * 3.3 / 4.7e3 / 3 + 5.0 / 122e3
    pk = buck_pk + rp + sram + hct + ws + misc
    av = buck_avg + 0.04 + sram + hct + 0.005 + misc
    out('\n== cart draw from CONS_5V (no USB)')
    out('  buck input %.0f mA peak (S3 TX 355 mA + SD 100 + CP2102N 12 at 3.3 V, eta %.2f), %.0f mA average'
        % (buck_pk * 1e3, eta, buck_avg * 1e3))
    out('  RP LDO %.0f, SRAM %.0f, 74HCT %.0f, WS2812 %.0f mA: total ~%.0f mA peak, ~%.0f mA average'
        % (rp * 1e3, sram * 1e3, hct * 1e3, ws * 1e3, pk * 1e3, av * 1e3))
    out('  console: 9 V 1 A adapter (CX781), VR1 7805 on a heat sink, no fuse; console\'s own 5 V draw ~0.35-0.5 A'
        ' (estimate from MARIA 200 mA max + SALLY + RAM + TIA/RIOT): total peak ~%.1f-%.1f A at 5 V'
        % (0.35 + pk, 0.5 + pk))
    out('  7805 dissipation at 9.5 V in: %.1f-%.1f W; an official POKEY cart drew <= ~0.2 A'
        % ((9.5 - 5) * (0.35 + av), (9.5 - 5) * (0.5 + pk)))
    out('  P-FET loss at peak: %.0f mW; one +5V finger (pin 13), two GND (14, 30)' % (pk * pk * 0.060 * 1e3))

    # ---- power-on race -----------------------------------------------------------------------------
    out('\n== power-on: the BIOS reads the cart at ~0.27-0.31 s after +5V (NTSC: RAM tests first), ~22-62 ms (PAL:'
        ' no self-test; SALLY reset R48 470k / C54 0.1 uF ~17-57 ms after +5V)')
    out('  RP2354B: AP2112K start-up 20 us, XOSC ~1 ms, bootrom + copy_to_ram of the 69 KB image through the'
        ' boot-time QSPI clock: tens of ms (MEASURE). An open bus at the BIOS\'s check sends PAL consoles to'
        ' built-in Asteroids / 2600 mode, NTSC to 2600 mode, locked until a power cycle.')
    out('  no hardware hold-off exists: no reset on the edge, and /HALT is enabled only after the BIOS\'s second'
        ' INPTCTRL write (U11 HEN)')

    # ---- misc --------------------------------------------------------------------------------------
    rl = find(lambda p: p.prefix == 'R' and 'RP_LED' in p.pins.values())
    out('\n== misc')
    out('  RP LED: (3.3 - 1.8..2.0 V) / %s = %.1f-%.1f mA' % (rl.value, (3.3 - 2.0) / val(rl) * 1e3, (3.3 - 1.8) / val(rl) * 1e3))
    out('  crystal: 15 * 15 / 30 + 3 pF stray = %.1f pF (ABM8-272-T3 CL 10 pF)' % (15 * 15 / 30 + 3))
    for ma in (30, 60):
        out('  AP2112K at %d mA: %.0f mW from 5.0 V, Tj +%.0f C (SOT-23-5 ~250 C/W)' % (ma, (5.0 - 3.3) * ma, (5.0 - 3.3) * ma / 1e3 * 250))


if __name__ == '__main__':
    main()
