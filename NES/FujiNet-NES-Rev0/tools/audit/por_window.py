#!/usr/bin/env python3
"""'595 /OE hold-off: POR_RC (1 uF to +5V, 100k to GND) through the 74HCT14,
SR_OE_N = NAND(PWR_OK, POR).  Window until the node decays below VT-."""
import math
R, C, V = 100e3, 1e-6, 5.0
for vt in (0.9, 1.6, 2.45):   # SN74HCT14 VT- min/typ/max at 4.5 V
    print('VT- = %.2f V: /OE released %.0f ms after the 5 V rail is up' % (vt, R * C * math.log(V / vt) * 1e3))
print('TI SN74HCT14 VT+ max 3.13 V at VCC 4.5 V = %.2f x VCC; VSENSE divider 100k/(22k+100k) = %.3f -> %.2f V at VCC 4.5 V' % (3.13 / 4.5, 100 / 122, 4.5 * 100 / 122))
print('LED: (5.0 - 2.85) / 1k = %.1f mA (KT-0603G VF 2.6-3.1 V at 5 mA)' % ((5.0 - 2.85) / 1.0))
print('AO3401A: Rds(on) < 60 mOhm at Vgs -4.5 V; 0.4 A cart load -> %.0f mV drop (SS34 was ~350 mV)' % (0.06 * 0.4 * 1e3))
print('LDO: ~30 mA IOVDD at (5.0-3.3) V = %.0f mW' % (0.03 * 1.7 * 1e3))
