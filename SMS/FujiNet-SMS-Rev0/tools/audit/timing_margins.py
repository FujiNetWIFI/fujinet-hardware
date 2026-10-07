#!/usr/bin/env python3
"""SMS cart-bus timing for the Rev0 glue (the NES board's timing_margins.py,
ported to the Z80 and to a static-timing walk of the gate network).

The gate network is read from tools/design.py (every 74HCT package, pin roles
from GATE_PINS), so the paths follow the circuit, not a hand-written list.
Gate delays: worst-case tpd at VCC 4.5 V, CL 50 pF, -40..85 C:
  SN74HCT14 40 ns (TI SCLS225G p.6), SN74HCT00 25 ns (TI SCLS062F p.5),
  74HCT27 26 ns (Nexperia 74HC_HCT27 rev.7 p.6), 74HCT10 30 ns (Nexperia 74HC_HCT10 rev.5 p.6).
SRAM: AS6C4008-55 tAA/tACE 55, tOE 30, tWP 45, tDW 25, tDH 0, tWR 0, tAS 0 (Alliance p.4).
Z80: Zilog PS0178 (Z8400 NMOS, 4 MHz column; the SMS1 also uses NEC D780C-1 / Z0840004),
     AC characteristics p.38-39: #6 TdCr(A) 110, #8 TdCf(MREQf) 85, #13 TdCf(RDf) 95,
     #15 TsD(Cr) 35 (M1), #25 TsD(Cf) 50 (M2-M5), #30 TdCf(WRf) 80, #32 TdCf(WRr) 80,
     #53 TdCf(D) 150, #31 TwWR = TcC - 30, #35 TdWRr(D) = TwCl + TfC - 70, #45 TdCTr(A) = TwCl + TfC - 50.
Console /CE: /MREQ gated by the I/O chip's slot enable (315-5216 / 315-5237); no published delay,
     T_CE below is an assumption (PROVISIONAL).  SMS clock 3.579545 MHz, taken as 50 % duty.

Usage: python3 tools/audit/timing_margins.py [--ti]
  --ti: the TI second sources for the out-of-stock Nexperia parts, CD74HCT27M96 29 ns and
        CD74HCT10M 30 ns (TI SCHS406 / SCHS404, 4.5 V, 50 pF, -40..85 C).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import design as D

TPD = {'74HCT14': 40.0, '74HCT00': 25.0, '74HCT27': 26.0, '74HCT10': 30.0}
if '--ti' in sys.argv:
    TPD.update({'74HCT27': 29.0, '74HCT10': 30.0})
TPD_MIN = 3.0                                    # ns, no datasheet minimum: assume a fast gate
tAA, tOE, tWP, tDW, tDH, tWR = 55.0, 30.0, 45.0, 25.0, 0.0, 0.0
TC = 1e3 / 3.579545                              # 279.4 ns
TWCH = TWCL = TC / 2
TFC = 0.0                                        # clock fall time: 0 is the pessimistic end of the formulas
T_CE = 40.0                                      # console /CE after /MREQ (PROVISIONAL)
Z = dict(TdCrA=110.0, TdCfMREQf=85.0, TdCfRDf=95.0, TsDCr=35.0, TsDCf=50.0, TdCfWRf=80.0,
         TdCfWRr=80.0, TdCfD=150.0)
Z['TwWR'] = TC - 30.0
Z['TdWRrD'] = TWCL + TFC - 70.0
Z['TdCTrA'] = TWCL + TFC - 50.0
LOAD_HOLD = 30 / 200e6 * 1e9                     # firmware: busy_wait_at_least_cycles(30) at 200 MHz after /RD rises


def network():
    """net -> (gate tpd, [input nets]) for every glue gate output."""
    drv = {}
    for p in D.PARTS:
        if p.value not in D.GATE_PINS:
            continue
        for ins, out in D.GATE_PINS[p.value]:
            o = p.pins.get(str(out))
            if o:
                drv[o] = (TPD[p.value], [p.pins.get(str(i)) for i in ins], p.ref, p.value)
    return drv


def arrival(net, t0, drv, memo=None, trace=None):
    """Latest settle time of `net` given primary-input settle times t0 (unlisted inputs settle at 0)."""
    if memo is None:
        memo = {}
    if net in memo:
        return memo[net]
    if net in t0 or net not in drv:
        memo[net] = (t0.get(net, 0.0), [net])
        return memo[net]
    tpd, ins, ref, val = drv[net]
    best = max((arrival(i, t0, drv, memo) for i in ins if i not in ('GND', '+5V')), key=lambda x: x[0])
    memo[net] = (best[0] + tpd, best[1] + ['%s(%s %s)' % (net, ref, val[4:])])
    return memo[net]


def path_delay(src, dst, drv):
    """Longest delay from one input net to an output net (other inputs static)."""
    def walk(n):
        if n == src:
            return 0.0, [src]
        if n not in drv:
            return None
        tpd, ins, ref, val = drv[n]
        subs = [walk(i) for i in ins if i not in ('GND', '+5V')]
        subs = [s for s in subs if s]
        if not subs:
            return None
        b = max(subs, key=lambda x: x[0])
        return b[0] + tpd, b[1] + ['%s(%s %s)' % (n, ref, val[4:])]
    return walk(dst)


def show(title, res):
    print('  %-34s %6.1f ns  %s' % (title, res[0], ' -> '.join(res[1])))


def main():
    drv = network()
    print('gate tpd (ns): %s' % ', '.join('%s %.0f' % kv for kv in sorted(TPD.items())))
    print('Z80 at %.4f MHz: T = %.1f ns, TwCl = %.1f ns; console /CE assumed %.0f ns after /MREQ (PROVISIONAL)'
          % (1e3 / TC, TC, TWCL, T_CE))
    print('\n== glue paths (worst tpd, 4.5 V, 50 pF, 85 C)')
    paths = {}
    for s, d in (('RD_N', 'SRAM_OE_N'), ('CE_N', 'SRAM_OE_N'), ('A12', 'SRAM_OE_N'), ('A15', 'SRAM_OE_N'),
                 ('WR_N', 'SRAM_WE_N'), ('RD_N', 'SRAM_WE_N'), ('CE_N', 'SRAM_WE_N'), ('A12', 'SRAM_WE_N'),
                 ('LOAD', 'SRAM_WE_N'), ('RAM_WE', 'SRAM_WE_N'), ('GAME', 'SRAM_OE_N'), ('VSENSE', 'SRAM_OE_N')):
        r = path_delay(s, d, drv)
        if r:
            paths[(s, d)] = r[0]
            show('%s -> %s' % (s, d), r)
    n_rd_we = sum(1 for _ in path_delay('WR_N', 'SRAM_WE_N', drv)[1]) - 1

    # ---- M1 opcode fetch: data sampled at T3 rising (2 T after T1 rising) --------------------
    print('\n== M1 fetch from the SRAM (t = 0 at T1 rising)')
    t_addr = Z['TdCrA']
    t_mreq = TWCH + Z['TdCfMREQf']
    t_rd = TWCH + Z['TdCfRDf']
    t_ce = t_mreq + T_CE
    oe = arrival('SRAM_OE_N', {'RD_N': t_rd, 'CE_N': t_ce, 'A12': t_addr, 'A13': t_addr, 'A14': t_addr,
                               'A15': t_addr, 'GAME': 0.0, 'MBOX': 0.0, 'VSENSE': -1e6}, drv)
    show('/OE falls at', oe)
    t_data = max(oe[0] + tOE, t_addr + tAA)
    need = 2 * TC - Z['TsDCr']
    print('  data valid %.1f ns (max(/OE + tOE %.0f, A0-A12 + tAA %.0f)); needed by %.1f ns (T3 rise - TsD %.0f): margin %+.1f ns'
          % (t_data, tOE, tAA, need, Z['TsDCr'], need - t_data))
    print('  without the console /CE delay: margin %+.1f ns; /CE delay that uses it all up: %.0f ns'
          % (need - max(arrival('SRAM_OE_N', {'RD_N': t_rd, 'CE_N': t_mreq, 'A12': t_addr, 'A13': t_addr,
                                                          'A14': t_addr, 'A15': t_addr, 'VSENSE': -1e6}, drv)[0] + tOE, t_addr + tAA),
             T_CE + need - t_data))
    # /OE glitch: OE_ADDR (6 gates from A12) must settle before RD_CEP can open /OE.  RD_CEP needs the
    # console /CE, which follows /MREQ, which the Z80 holds off >= #7 TdA(MREQf) = TwCh + TfC - 65 after the address.
    t_amreq = TWCH + TFC - 65.0
    oe_addr = path_delay('A12', 'OE_ADDR', drv)
    rd_cep = path_delay('CE_N', 'RD_CEP', drv)
    print('  /OE glitch check (same gate corner): OE_ADDR settles %.0f ns after the address; RD_CEP can open /OE'
          ' >= %.1f (#7) + /CE + %.0f ns: %+.1f ns before T_CE' % (oe_addr[0], t_amreq, rd_cep[0], t_amreq + rd_cep[0] - oe_addr[0]))
    bank_budget = need - tAA - t_addr
    print('  SA13-SA19 (and SA19 = chip select) are put by core1 per 1K page on every address change:')
    print('    address valid %.0f ns -> core1 must have SA13-19 at the SRAM by %.1f ns: %.0f ns = %d cycles at 200 MHz'
          % (t_addr, need - tAA, bank_budget, int(bank_budget / 5)))
    # ---- memory read (M2-M5): data sampled at T3 falling ----------------------------------------
    need_r = 2 * TC + TWCH - Z['TsDCf']
    print('\n== memory read (M2-M5): data needed by %.1f ns (T3 fall - TsD %.0f): margin %+.1f ns; core1 bank budget %.0f ns'
          % (need_r, Z['TsDCf'], need_r - t_data, need_r - tAA - t_addr))

    # ---- RAM_WE write (memory write cycle) ----------------------------------------------------
    print('\n== RAM_WE write (Z80 memory write, slot 2, t = 0 at T1 rising)')
    t_wr_f = TC + TWCH + Z['TdCfWRf']
    t_wr_r_min = 2 * TC + TWCH
    t_data_w = TWCH + Z['TdCfD']
    we = arrival('SRAM_WE_N', {'WR_N': t_wr_f, 'CE_N': t_ce, 'A12': t_addr, 'A13': t_addr, 'A14': t_addr,
                               'A15': t_addr, 'RD_N': -1e6, 'LOAD': -1e6, 'RAM_WE': 0.0, 'MBOX': 0.0, 'VSENSE': -1e6}, drv)
    show('/WE falls at (latest)', we)
    t_we_rise = paths[('WR_N', 'SRAM_WE_N')]
    print('  /WE rises <= %.0f ns after /WR rises (%d gates); Z80 holds data >= %.1f ns (#35 TwCl + TfC - 70):'
          ' data hold margin %+.1f ns vs tDH %.0f' % (t_we_rise, n_rd_we, Z['TdWRrD'], Z['TdWRrD'] - t_we_rise, tDH))
    print('  address hold (#45 TwCl + TfC - 50 = %.1f ns) vs /WE rise %.0f ns: %+.1f ns vs tWR %.0f'
          % (Z['TdCTrA'], t_we_rise, Z['TdCTrA'] - t_we_rise, tWR))
    print('  at Zilog\'s assumed TfC = 20 ns: data hold %+.1f ns, address hold %+.1f ns'
          % (Z['TdWRrD'] + 20 - t_we_rise, Z['TdCTrA'] + 20 - t_we_rise))
    print('  write pulse >= %.0f ns (TwWR %.0f - %.0f skew) vs tWP %.0f; data setup >= %.0f ns vs tDW %.0f; '
          'decode settles %.0f ns before /WR falls (no glitch)'
          % (Z['TwWR'] - t_we_rise + n_rd_we * TPD_MIN, Z['TwWR'], t_we_rise - n_rd_we * TPD_MIN, tWP,
             t_wr_r_min - t_data_w, tDW,
             TC + TWCH - arrival('RAMWIN_N', {'A12': t_addr, 'A13': t_addr, 'A14': t_addr, 'A15': t_addr, 'MBOX': 0.0}, drv)[0]))

    # ---- LOAD: the console reads $8000-$9FFF, the RP drives D0-D7, the SRAM writes it ------------
    print('\n== LOAD copy (console read of the load window, RP drives the data)')
    t_load_we = paths[('RD_N', 'SRAM_WE_N')]
    print('  /WE rises <= %.0f ns after /RD rises; core1 keeps driving %.0f ns after it sees /RD high: hold margin %+.0f ns'
          % (t_load_we, LOAD_HOLD, LOAD_HOLD - t_load_we))
    print('  address hold after /RD rise (#45) %.1f ns vs %.0f ns: %+.1f ns -- non-M1 reads only: in an M1 fetch the'
          ' refresh address (I:R) replaces A0-A15 at T3 rise, with /RD' % (Z['TdCTrA'], t_load_we, Z['TdCTrA'] - t_load_we))
    print('  -> LOAD must only be set while the console copies with data reads (LDIR/LD), never while it executes from $8000-$9FFF')


if __name__ == '__main__':
    main()
