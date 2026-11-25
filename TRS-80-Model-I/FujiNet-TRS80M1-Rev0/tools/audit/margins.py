#!/usr/bin/env python3
"""The numbers behind the design review: bus levels both ways through the 330R, contention and
back-drive currents, the console-5V sense, the power mux threshold, the cart's draw against the
console's supply, LED current, crystal load, the RP LDO.  Values come from tools/design.py; limits
are the datasheet figures cited on each line.  Exit 1 if any margin is negative.

Sources:
  8048   Intel MCS-48 (8048AH / 8049AH) datasheet, D.C. characteristics (Vcc 5 V +-10 %): VIL max 0.8 V,
         VIH min 2.0 V (all but XTAL / RESET); VOL max 0.45 V (BUS at 2.0 mA; RD / WR / PSEN / ALE at
         1.8 mA; other outputs 1.6 mA); VOH min 2.4 V (BUS at -400 uA, RD / WR / PSEN / ALE at -100 uA,
         all other outputs -- the ports -- at -40 uA); input leakage +-10 uA.  The console's 8244 / 8245
         VDC shares the bus (no datasheet found: taken as the same NMOS / TTL levels, UNVERIFIED).
  RP2350 datasheet Table 1683 (p.1336): FT pins at IOVDD 3.3 V: VIH min 2.0 V, max 5.5 V (IOVDD
         powered), VIL max 0.8 V, VOH min 2.62 V and VOL max 0.5 V at the selected drive (2-12 mA)
  O2     the console's 5 V regulator and spare current are not published (forum figures only: a
         12 VAC / 600 mA adapter on the Odyssey 2, 9 V DC / 1.1 A on the G7000)
  TPS2116 datasheet: PR1 reference 0.92-1.08 V (the 4.3 x divider gives 3.96-4.64 V)

Usage: python3 tools/audit/margins.py
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import design as D

K = D.KEY
neg = []


def ohms(key):
    v = D.BY_REF[K[key]].value
    m = re.match(r'([\d.]+)([kMR]?)', v)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]


def margin(what, m, unit='V'):
    print('%-78s margin %+.2f %s' % (what, m, unit))
    if m < 0:
        neg.append(what)


def main():
    bus = [(cn, 'R_' + rn[3:]) for cn, rn, g, rv in D.BUS if rv == '330R']
    rs = ohms(bus[0][1])
    assert all(ohms(k) == rs for _cn, k in bus) and len(bus) == 27
    # ---- cart -> console: DB0-DB7 and T0, RP pad -> 330R -> the 8048 (+ the VDC, RAM, latch on the bus)
    i_load = 100e-6                     # 8048 +-10 uA + the VDC, the console RAM and the address latch, generous
    print('bus DC load per line taken as %.0f uA (8048 ILI 10 uA + the 8244 / 8245, RAM and latch leakage)' % (i_load * 1e6))
    margin('DB / T0 high: RP VOH 2.62 V (spec min) - %g R x %.0f uA vs 8048 VIH 2.0 V' % (rs, i_load * 1e6),
           2.62 - rs * i_load - 2.0)
    margin('DB / T0 high, typical: 3.3 V - drop vs 8048 VIH 2.0 V', 3.3 - rs * i_load - 2.0)
    margin('DB / T0 low: RP VOL 0.5 V (spec max) + drop vs 8048 VIL 0.8 V', 0.8 - (0.5 + rs * i_load))
    c_bus = 100e-12                     # generous: the 8048 bus, the VDC, RAM, latch and the slot
    print('DB edge: %g R x %.0f pF = %.0f ns (3 tau %.0f ns) in a ~2.8 us 8048 machine cycle (~1 us /PSEN)'
          % (rs, c_bus * 1e12, rs * c_bus * 1e9, 3 * rs * c_bus * 1e9))
    # ---- console -> cart: A0-A11, P10 / P11 / P14, /PSEN, /WR, E
    margin('console high: 8048 VOH 2.4 V (ports at -40 uA, the weakest) - 330R x 40 uA vs RP VIH 2.0 V (FT)',
           2.4 - rs * 40e-6 - 2.0)
    margin('console low: 8048 VOL 0.45 V vs RP VIL 0.8 V', 0.8 - 0.45)
    margin('console max: 5.5 V (the 8048\'s Vcc + 10 %) vs RP FT max 5.5 V (IOVDD powered: +3V3_RP LDO)', 5.5 - 5.5)
    print('P1 (P10 / P11 / P14) is quasi-bidirectional: a weak pull-up when high -- the RP pads need their pulls '
          'off (RP2350-E9, README firmware change 4)')
    # ---- currents the 330R bounds
    print('contention (RP high vs a console driver low, the release after /PSEN rises): <= %.1f mA per line'
          % (3.3 / rs * 1e3))
    print('back-drive into a console that is off (RP 3.3 V vs an input clamp ~0.6 V): <= %.1f mA per line, '
          '%.0f mA for DB0-DB7 + T0 -- the firmware VSENSE gate (README) keeps them released'
          % ((3.3 - 0.6) / rs * 1e3, 9 * (3.3 - 0.6) / rs * 1e3))
    print('a console line at 5 V into a pad while IOVDD is still rising: <= %.1f mA per line' % ((5.0 - 0.3) / rs * 1e3))
    rb, rpd = ohms('R_VPB'), ohms('R_VPBPD')
    print('pin B: GP28 high into a console that grounds B: %.1f mA through %g R; released, %g R holds it at 0 V'
          % (3.3 / rb * 1e3, rb, rpd))
    margin('pin B raised: 3.3 V x %g / (%g + %g) = %.2f V vs a TTL VIH 2.0 V' % (rpd, rb, rpd, 3.3 * rpd / (rb + rpd)),
           3.3 * rpd / (rb + rpd) - 2.0)
    # ---- console 5 V sense on GPIO40 (ADC0: not FT, VPIN max IOVDD + 0.3 V; digital VIH 2.0 V)
    hi, lo = ohms('R_VSH'), ohms('R_VSL')
    k = lo / (hi + lo)
    margin('VSENSE at a 5.5 V console (%.2f V) vs IOVDD + 0.3 = 3.6 V (GP40 not FT)' % (5.5 * k), 3.6 - 5.5 * k)
    margin('VSENSE at a 4.50 V console (%.2f V) vs VIH 2.0 V' % (4.5 * k), 4.5 * k - 2.0)
    z = hi * lo / (hi + lo)
    margin('VSENSE source %.1f kOhm vs RP2350-E9\'s 8.2 kOhm' % (z / 1e3), (8.2e3 - z) / 1e3, 'kOhm')
    print('VSENSE filter tau %.2f ms' % (z * 100e-9 * 1e3))
    # ---- power mux: VBUS priority threshold
    ph, pl = ohms('R_PRH'), ohms('R_PRL')
    g = (ph + pl) / pl
    margin('TPS2116 switches to USB above %.2f-%.2f V: under a 4.75 V USB source' % (0.92 * g, 1.08 * g), 4.75 - 1.08 * g)
    margin('... and above a 3.5 V droop floor', 0.92 * g - 3.5)
    # ---- the cart's draw on the console's supply (no USB)
    eff = 0.85
    s3_avg, s3_peak = 0.110, 0.400      # ESP32-S3 WiFi average / TX burst at 3.3 V (Espressif: ~355 mA TX peak)
    rp, misc = 0.040, 0.020             # RP2350 at 250 MHz flat out (LDO, same current at 5 V), CP2102N idle + LEDs
    avg = s3_avg * 3.3 / 5.0 / eff + rp + misc
    peak = s3_peak * 3.3 / 5.0 / eff + rp + misc
    print('cart draw at 5 V without USB: ~%.0f mA average, ~%.0f mA peak (S3 via the buck at %.0f%%, RP via its LDO)'
          % (avg * 1e3, peak * 1e3, eff * 100))
    print('console: its 5 V regulator and spare current are not published -- run the cart on USB-C power where '
          'possible (bring-up check: the console regulator\'s temperature and CONS_5V under WiFi load)')
    # ---- small parts
    r = ohms('R_LED')
    print('RP LED: (3.3 - 1.9 V) / %d R = %.1f mA' % (r, (3.3 - 1.9) / r * 1e3))
    print('crystal load: 15*15/30 + 3 = %.1f pF (ABM8-272-T3 CL 10 pF)' % (15 * 15 / 30 + 3))
    for ma in (16, 40):
        print('AP2112K at %d mA from 5.0 V: %.0f mW -> Tj %.0f C at 25 C ambient (SOT-23-5, 250 C/W)'
              % (ma, (5.0 - 3.3) * ma, 25 + (5.0 - 3.3) * ma / 1e3 * 250))
    print('%d negative margins' % len(neg))
    return 1 if neg else 0


if __name__ == '__main__':
    sys.exit(main())
