#!/usr/bin/env python3
"""Atari 5200 cart-bus read timing for the Rev0 data path: the console puts an address on the
edge, the RP2354B follows it and puts the byte on RP_D0-7, the 74HCT541 passes it to D0-D7 while
an enable is low (the '08 / '14 glue opens it), and the 6502C (SALLY) latches it at the end of
PHI2.  There is no R/W on the edge and no clock on the 4-port consoles: the cart behaves as a
mask ROM, the RP's job being only to follow the address faster than a ROM's tACC.

Numbers (max over temperature unless noted):
  6502 family read timing, Synertek SY6500 data sheet (datasheets/SY6502A.pdf p.6, "Read/Write
    Timing"): 2 MHz grade TADS <= 150 ns, TDSU >= 50 ns, THR >= 10 ns; 1 MHz grade 300 / 100 /
    10 ns.  The 5200's SALLY runs at 3.579545 MHz / 2 = 1.79 MHz (TCYC 559 ns); the 2 MHz grade
    is the one that can run there, the 1 MHz grade is shown as an outer bound.
  console: A0-A6 through a 74LS244 on CA018087 (tPLH / tPHL 18 ns max); the enables from a 74LS139
    (A14 / A15 select -> output, 38 ns max) with its enable grounded (CX5200 FSM schematics).
  SN74HCT08: tpd 30 ns at 4.5 V (TI, 50 pF, -40..85 C).
  SN74HCT541: tpd A -> Y 29 ns at 50 pF / 42 ns at 150 pF; ten /OE -> Y 38 / 50 ns; tdis 38 ns
    (TI, 4.5 V, -40..85 C).  The console's data bus (CPU, ANTIC, GTIA, POKEY, the DRAM's
    buffer) is taken as 150 pF.
  RP2354B following the address (firmware a52_cart.c, core1 polling gpio[15:0] at ~25 ns a turn
    at 200 MHz): 2 cycles of input synchronizer (10 ns) + up to one turn to see the change + one
    turn to look the byte up and write it + the pad (~5 ns): 65 ns.  PROVISIONAL: firmware.
  ANTIC's DMA reads of the cart (display lists, character sets) are taken to meet the 6502's
    timing.  PROVISIONAL: ANTIC's address-valid delay is not in any document found.

Usage: python3 tools/audit/timing_margins.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import design as D

F_CPU = 3.579545e6 / 2
TCYC = 1e9 / F_CPU
GRADES = {'2 MHz grade (SY6502A)': dict(tads=150, tdsu=50, thr=10),
          '1 MHz grade (SY6502)': dict(tads=300, tdsu=100, thr=10)}
LS244, LS139 = 18, 38
HCT08 = 30
HCT541 = dict(tpd50=29, tpd150=42, ten50=38, ten150=50, tdis=38)
RP_FOLLOW = 10 + 25 + 25 + 5


def main():
    k = D.KEY
    print('== 5200 cart read, SALLY at %.4f MHz: TCYC %.0f ns' % (F_CPU / 1e6, TCYC))
    data = LS244 + RP_FOLLOW + HCT541['tpd150']
    oe = LS139 + HCT08 + HCT541['ten150']
    print('  address path: console LS244 %d + RP follows the address %d (PROVISIONAL) + %s 74HCT541 A->Y %d (150 pF) = %d ns'
          % (LS244, RP_FOLLOW, k['U_BUF'], HCT541['tpd150'], data))
    print('  enable path:  console LS139 %d + %s 74HCT08 %d + %s 74HCT541 /OE->Y %d (150 pF) = %d ns'
          % (LS139, k['U_AND'], HCT08, k['U_BUF'], HCT541['ten150'], oe))
    worst = max(data, oe)
    for name, g in GRADES.items():
        need = TCYC - g['tdsu']
        have = g['tads'] + worst
        print('  %-24s address valid at TADS %d ns; data valid %d ns after PHI2 falls, needed by %.0f ns '
              '(TCYC - TDSU %d): margin %+.0f ns; a mask ROM here would need tACC <= %.0f ns'
              % (name, g['tads'], have, need, g['tdsu'], need - have, TCYC - g['tads'] - g['tdsu']))
    print('  the RP can take up to %.0f ns (2 MHz grade) / %.0f ns (1 MHz grade) to follow an address before the byte is late'
          % (TCYC - GRADES['2 MHz grade (SY6502A)']['tdsu'] - GRADES['2 MHz grade (SY6502A)']['tads'] - LS244 - HCT541['tpd150'],
             TCYC - GRADES['1 MHz grade (SY6502)']['tdsu'] - GRADES['1 MHz grade (SY6502)']['tads'] - LS244 - HCT541['tpd150']))
    print('\n== release: the address leaves the cart window -> the enable rises -> the 541 lets go')
    print('  LS139 %d + 74HCT08 %d + 74HCT541 tdis %d = %d ns max after the address changes; the 6502 needs the byte held '
          'THR 10 ns after PHI2 falls and the next reader (DRAM, ~150+ ns access) drives no earlier than its own access time'
          % (LS139, HCT08, HCT541['tdis'], LS139 + HCT08 + HCT541['tdis']))
    print('\n== the A0-A13 / enable word the RP samples: no R/W, no clock (4-port); a52_cart.h counts an access once '
          'gpio[15:0] has held A52_SETTLE = 3 samples (~75 ns) -- under an enable\'s ~%.0f ns low time' % (TCYC / 2))


if __name__ == '__main__':
    main()
