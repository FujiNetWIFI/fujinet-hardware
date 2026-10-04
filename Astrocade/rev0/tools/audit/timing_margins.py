#!/usr/bin/env python3
"""Astrocade cart read budget.  The console only READS the cart: the RP2354A must
put D0-D7 on the bus after /CCS falls, before the Z80 samples it.  Z80 at
1.789773 MHz (NTSC colour clock / 2), T = 558.7 ns.  Opcode fetch (M1) samples
data on the rising edge of T3 (2 T after T1 starts), a memory read on the
falling edge of T3 (2.5 T).  The console decodes /CCS from the address and
/MREQ, so /CCS falls with /MREQ, half a T-state into T1 plus the decoder.

Z80 NMOS timing (Zilog Z80 CPU product spec, 2.5 MHz part; the console runs it
far slower): /MREQ falls <= 100 ns after the T1 falling edge, data setup to the
sampling edge 50 ns.  The console decoder delay is NOT published: 100 ns is
assumed (PROVISIONAL, bring-up scope item).  The RP side is firmware: the core1
loop / PIO latency in astrocade_cart.c is measured at bring-up."""
T = 1e9 / 1789773
MREQ = T / 2 + 100
DEC = 100.0
SETUP = 50.0
for name, sample in (('M1 opcode fetch', 2 * T), ('memory read', 2.5 * T)):
    budget = sample - SETUP - (MREQ + DEC)
    print('%-16s data sampled %.0f ns after T1; /CCS valid ~%.0f ns -> RP must drive D0-D7 within %.0f ns of /CCS'
          % (name, sample, MREQ + DEC, budget))
print('RP2350 at 150 MHz: %.0f ns budget = %.0f system clocks' % (2 * T - SETUP - MREQ - DEC, (2 * T - SETUP - MREQ - DEC) / 6.67))
