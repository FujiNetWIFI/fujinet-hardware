#!/usr/bin/env python3
"""The numbers behind the design review: bus levels both ways (the address lines through 330R, the data
lines through the 74LVC245A, the selects into the 74LVC1G gates), the select-to-bus timing the buffer
adds, back-drive into a console that is off, the console-5V sense, the power mux threshold, the cart's
draw against the slot's rating, LED current, crystal load, the RP LDO.  Values come from
tools/design.py; limits are the datasheet figures cited on each line.  Exit 1 if any margin is negative.

Sources:
  Z80    Zilog Z8400 (NMOS Z80A) datasheet, DC characteristics: VIH min 2.0 V, VIL max 0.8 V (all but
         CLK); VOH min 2.4 V at -250 uA, VOL max 0.4 V at 2.0 mA; input leakage +-10 uA
  LS138  TI SN74LS138 datasheet: VOH min 2.7 V (-0.4 mA), VOL max 0.5 V (8 mA) -- the console's select
         decoder (/8000 /A000 /C000 /E000)
  LVC    TI SN74LVC245A / SN74LVC1G11 / SN74LVC1G08 datasheets at VCC 3.0-3.6 V: VIH min 2.0 V, VIL max
         0.8 V, inputs and (high-Z) I/Os 5.5 V tolerant, Ioff; VOH min VCC - 0.2 V at -100 uA, VOL max
         0.2 V at 100 uA.  Propagation / enable times are taken here as 10 ns each, above every
         datasheet maximum at 3.3 V (a conservative bound, not a datasheet figure)
  RP2350 datasheet (FT pins at IOVDD 3.3 V): VIH min 2.0 V, max 5.5 V (IOVDD powered), VIL max 0.8 V
  coleco pico/coleco/firmware coleco_cart.h: data must be on the bus ~285 ns after /CE falls (~400 ns
         after T1); core1 drives it off the address, ahead of the select
  ADAM   Coleco ADAM Technical Reference Manual, J1: the cartridge slot's +5V, "typical available current
         0.2A" (the ColecoVision's own figure is not published)
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
    m = re.match(r'(?:4x)?([\d.]+)([kMR]?)', v)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]


def margin(what, m, unit='V'):
    print('%-86s margin %+.2f %s' % (what, m, unit))
    if m < 0:
        neg.append(what)


def main():
    rs = ohms('RN_A0')
    assert all(ohms(k) == rs for k, _ in D.ADDR_PACKS)
    # ---- console -> cart: A0-A14 into the RP's FT pads through 330R
    i_in = 10e-6
    margin('A0-A14 high: Z80 VOH 2.4 V - %g R x %.0f uA vs RP VIH 2.0 V (FT)' % (rs, i_in * 1e6), 2.4 - rs * i_in - 2.0)
    margin('A0-A14 low: Z80 VOL 0.4 V + drop vs RP VIL 0.8 V', 0.8 - (0.4 + rs * i_in))
    margin('A0-A14 max: 5.25 V console vs RP FT max 5.5 V (IOVDD up: +3V3_RP rises with +5V)', 5.5 - 5.25)
    print('a console line at 5 V into a pad while IOVDD is still rising: <= %.1f mA per line through %g R'
          % ((5.0 - 0.3) / rs * 1e3, rs))
    # ---- the selects into the 74LVC1G11 / 1G08
    margin('selects high: LS138 VOH 2.7 V vs LVC VIH 2.0 V', 2.7 - 2.0)
    margin('selects low: LS138 VOL 0.5 V vs LVC VIL 0.8 V', 0.8 - 0.5)
    margin('selects / data max: 5.25 V vs LVC input 5.5 V (5 V tolerant at 3.3 V)', 5.5 - 5.25)
    pu = ohms('RN_SEL')
    print('select pull-ups %g R to +3V3_RP: an LS138 output low sinks %.2f mA more; with the console off they '
          'push %.1f mA into its unpowered decoder' % (pu, 3.3 / pu * 1e3, 4 * (3.3 - 0.7) / pu * 1e3))
    # ---- data both ways through the 74LVC245A
    margin("D0-D7 cart -> console: '245 VOH 3.1 V (VCC - 0.2 at -100 uA) vs Z80 VIH 2.0 V", 3.1 - 2.0)
    margin("D0-D7 cart -> console: '245 VOL 0.2 V vs Z80 VIL 0.8 V", 0.8 - 0.2)
    margin("D0-D7 console -> cart (bank-register writes): Z80 VOH 2.4 V vs '245 VIH 2.0 V", 2.4 - 2.0)
    margin("'245 B port -> GP15-22: VCC - 0.2 = 3.1 V vs RP VIH 2.0 V", 3.1 - 2.0)
    # ---- timing: the select gates the buffer
    t_gate, t_en, t_pd = 10e-9, 10e-9, 10e-9
    path = 2 * t_gate + t_en
    margin('select -> /CE (1G11 + 1G08) -> the \'245 enabled: %.0f ns vs the firmware\'s ~285 ns after /CE'
           % (path * 1e9), (285e-9 - path) * 1e9, 'ns')
    print("the byte itself crosses the '245 in < %.0f ns; core1 has it at GP15-22 off the address, ~400 ns after T1"
          % (t_pd * 1e9))
    print('/CE also reaches GP26 (CE_PIN) %.0f ns after the select: core1 acts on it only after the address' % (2 * t_gate * 1e9))
    # ---- back-drive into a console that is off
    print("console off: DIR is held console -> cart (GP27 from boot, R_DIR %g R through reset), so the '245 never "
          "drives the console; A0-A14 are RP inputs; only the select pull-ups and the VSENSE divider touch it"
          % ohms('R_DIR'))
    # ---- console 5 V sense on GPIO28 (ADC2: not FT, VPIN max IOVDD + 0.3 V; digital VIH 2.0 V)
    hi, lo = ohms('R_VSH'), ohms('R_VSL')
    k = lo / (hi + lo)
    margin('VSENSE at a 5.5 V console (%.2f V) vs IOVDD + 0.3 = 3.6 V (GP28 not FT)' % (5.5 * k), 3.6 - 5.5 * k)
    margin('VSENSE at a 4.50 V console (%.2f V) vs VIH 2.0 V (read as a digital input: coleco_cart.h PWR)' % (4.5 * k),
           4.5 * k - 2.0)
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
    rp, misc = 0.040, 0.020             # RP2350 at 200-250 MHz (LDO, same current at 5 V), CP2102N idle, LEDs, logic
    avg = s3_avg * 3.3 / 5.0 / eff + rp + misc
    peak = s3_peak * 3.3 / 5.0 / eff + rp + misc
    print('cart draw at 5 V without USB: ~%.0f mA average, ~%.0f mA peak (S3 via the buck at %.0f%%, RP via its LDO)'
          % (avg * 1e3, peak * 1e3, eff * 100))
    margin('average draw vs the ADAM TRM\'s cart slot rating, 0.2 A typical (the ColecoVision\'s is not published)',
           (0.2 - avg) * 1e3, 'mA')
    print('peaks above that are WiFi TX bursts (ms): run the cart on USB-C power where possible (bring-up check: '
          'CONS_5V under WiFi load, the console regulator\'s temperature)')
    # ---- small parts
    r = ohms('R_LED')
    print('RP LED: (3.3 - 1.9 V) / %d R = %.1f mA' % (r, (3.3 - 1.9) / r * 1e3))
    print('crystal load: 15*15/30 + 3 = %.1f pF (ABM8-272-T3 CL 10 pF)' % (15 * 15 / 30 + 3))
    for ma in (20, 50):
        print('AP2112K at %d mA from 5.0 V: %.0f mW -> Tj %.0f C at 25 C ambient (SOT-23-5, 250 C/W)'
              % (ma, (5.0 - 3.3) * ma, 25 + (5.0 - 3.3) * ma / 1e3 * 250))
    print('%d negative margins' % len(neg))
    return 1 if neg else 0


if __name__ == '__main__':
    sys.exit(main())
