#!/usr/bin/env python3
"""PRG SRAM write and read margins on the NTSC 2A03 bus (nesdev: M2 high 350 ns
per 559 ns cycle; /ROMSEL = NAND(M2, A15) via the console's 74LS139) with the
Rev0 decode: /WE = NAND4(M2, ROMSEL, !R/W, PRG_WE_EN) on a CD74HCT20 (one gate
after M2); /CE = NAND(ROMSEL, SRAM_EN) behind the '14 inverter."""
HCT20_TPD_MAX = 28.0                          # ns, CD74HCT20 at 4.5 V, 50 pF (TI)
HCT_TPD_MAX = 30.0                            # ns, 74HCT14/00 class worst
LS139_TPD = 20.0                              # ns, the console's decoder after M2
M2_HIGH = 350.0
tDW, tDH, tWP, tACE = 25.0, 0.0, 45.0, 55.0   # AS6C4008-55 datasheet, ns
hold_2a03 = 30.0                              # 6502-class write-data hold after phi2 falls (PROVISIONAL per nes_cart.h)
we_high = HCT20_TPD_MAX                       # /WE rises this long after M2 falls (worst)
we_low = LS139_TPD + HCT_TPD_MAX + HCT20_TPD_MAX   # /WE falls after ROMSEL (LS139 + '14) + '20
print('/WE rises %.0f ns (worst) after M2 falls; 2A03 holds data %.0f ns -> hold margin at /WE rise: %+.0f ns vs tDH %.0f ns' % (we_high, hold_2a03, hold_2a03 - we_high, tDH))
print('the first draft (/ROMSEL -> 14 -> 00 -> 32) was %.0f ns worst -> %+.0f ns' % (LS139_TPD + 3 * HCT_TPD_MAX, hold_2a03 - (LS139_TPD + 3 * HCT_TPD_MAX)))
print('write pulse %.0f ns (M2 high - %.0f) vs tWP %.0f ns' % (M2_HIGH - we_low + we_high, we_low - we_high, tWP))
print('data setup to /WE rise: CPU data valid ~150 ns after M2 rise -> %.0f ns vs tDW %.0f ns' % (M2_HIGH + we_high - 150, tDW))
print('read: /CE via 14 + 20 (%.0f ns worst) + tACE %.0f = %.0f ns after /ROMSEL vs %.0f ns budget' % (HCT_TPD_MAX + HCT20_TPD_MAX, tACE, HCT_TPD_MAX + HCT20_TPD_MAX + tACE, M2_HIGH - LS139_TPD))
