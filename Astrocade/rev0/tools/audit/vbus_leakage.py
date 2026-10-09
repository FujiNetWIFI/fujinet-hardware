#!/usr/bin/env python3
"""USB's OR diode (SS34) leaks backwards into VBUS whenever the console powers the cart without a
USB cable; VBUS then holds only the CP2102N's 22k / 47k sense divider.  The CP2102N reads VBUS high
above VIH = VIO - 0.6 V (CP2102N datasheet, VBUS note) -- a phantom USB attach.  SS34 maximum reverse
current: 0.5 mA at 25 C, 20 mA at 100 C, at the rated 40 V (Vishay datasheet); at the few volts
across it here the typical figure is far lower (Fig. 4)."""
VIO, R_TOP, R_BOT = 3.3, 22e3, 47e3
vih = VIO - 0.6
v_vbus = vih * (R_TOP + R_BOT) / R_BOT
print('CP2102N VBUS reads high at %.2f V on its pin = %.2f V on VBUS through %.0fk / %.0fk' % (vih, v_vbus, R_TOP / 1e3, R_BOT / 1e3))
print('leakage that lifts VBUS that far with only the divider: %.0f uA' % (v_vbus / (R_TOP + R_BOT) * 1e6))
print('with a 4.7k VBUS pull-down (as on the 2600 Rev1 / SMS / 7800 / 5200): %.2f mA, and %.2f mA from USB when plugged'
      % (v_vbus / (4.7e3 * (R_TOP + R_BOT) / (4.7e3 + R_TOP + R_BOT)) * 1e3, 5.0 / 4.7e3 * 1e3))
