#!/usr/bin/env python3
"""RP2350-E9 against the VSENSE gate (docs/design-review-rev0.md, Part 3).

The firmware serves a read only while /CCS is low AND VSENSE (GPIO26) reads high: VSENSE is a
plain digital input (pico/astrocade main.c: gpio_init, input, pulls off; astrocade_cart.h
SERVE_MASK), so its input buffer is enabled.  On an RP2350 A2 die, a Bank 0 pad with its input
enabled that sits between VIL and VIH sources ~120 uA and holds itself near 2.2 V; only a pull of
8.2 kOhm or less overcomes it (RP2350 datasheet, erratum RP2350-E9, fixed in A3).  When the console
powers off with the cart on USB power, VSENSE falls through that band."""
IOVDD = 3.3
VIL, VIH = 0.35 * IOVDD, 0.65 * IOVDD          # RP2350 GPIO thresholds at 3.3 V (datasheet 14.9)
I_E9, V_E9 = 120e-6, 2.2                      # E9: typical source current, the voltage it holds
for name, rt, rb in (('Rev0 100k / 150k', 100e3, 150e3), ('proposed 10k / 15k', 10e3, 15e3)):
    th = rt * rb / (rt + rb)
    v_hold = min(V_E9, I_E9 * th)              # the E9 source against the divider's Thevenin pull to 0 V
    print('%-20s ratio %.2f, Thevenin %.1f kOhm (E9 needs <= 8.2 kOhm); console off: the pad can sit at '
          '~%.2f V (VIL %.2f, VIH %.2f) -> %s; console on: %.2f mA from CONS_5V'
          % (name, rb / (rt + rb), th / 1e3, v_hold, VIL, VIH,
             'reads UNDEFINED / possibly high' if v_hold > VIL else 'reads low', 5.0 / (rt + rb) * 1e3))
# before the AP2112K starts, IOVDD is ~0 V while CONS_5V ramps: GP26 (not 5 V tolerant) then takes VSENSE through
# its clamp, limited by the divider; the LDO tracks the console ramp in dropout, so this lasts only that ramp
for cons in (1.0, 2.0):
    for name, th in (('100k / 150k', 60e3), ('10k / 15k', 6e3)):
        print('CONS_5V %.1f V, IOVDD 0 V: %-11s pushes at most %3.0f uA into GP26' % (cons, name, max(0, 0.6 * cons - 0.5) / th * 1e6))
