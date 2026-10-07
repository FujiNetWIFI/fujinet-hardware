#!/usr/bin/env python3
"""Atari 7800 cart-bus timing for the Rev0 glue: a static-timing walk of the gate network read
from tools/design.py (every 74HCT package, pin roles from GATE_PINS), against the 6502 (SALLY)
bus cycle and MARIA's DMA reads.

Sources (datasheets/, pages in analysis/deep_review.json):
  gates, worst tpd at VCC 4.5 V, CL 50 pF, -40..85 C (typical in brackets, 25 C):
    SN74HCT14 40 [20] ns (TI SCLS225G 6.6), SN74HCT00 25 [11] ns (TI SCLS062 5.5),
    CD74HCT20 35 [11 at 5 V / 15 pF] ns (TI SCHS417 6.5)
  console U4 74LS08: A15, A14, A12 reach the edge through it (EXT gating, C025231) -- 20 ns max
  AS6C4008-55: tAA 55, tOE 30, tWP 45, tDW 25, tDH 0, tWR 0, tAS 0, tAW 50 (Alliance, AC table)
  6502: no SALLY datasheet exists; Synertek SY6500 2 MHz table (SY6502A.pdf p.6, image-only):
    TADS 150 max, TRWS 150 max, TDSU 50 min, THR 10 min, TMDS 100 max, THW 30 min (60 typ),
    THA 30 min (60 typ), THRW 30 min; PWH phi2 = PWH phi0 - 40 .. - 10
  7800: 14.31818 MHz / 8 = 1.79 MHz (T = 558.7 ns); MARIA DMA (GCC1702B p.27-28): display list /
    list list / character map reads 2 x 7.16 MHz cycles, ~184 ns from address to data needed;
    graphics 3 cycles, ~285 ns; "display lists must be in fast (RAM) memory"
  firmware (a78_pio.h): a slot change reaches SA13-SA18 / ROM_EN / RAM_EN / A8MASK <= 45 ns after
    A13-A15 change

Usage: python3 tools/audit/timing_margins.py [--typ]      (--typ: 25 C typical gate delays)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import design as D

TYP = '--typ' in sys.argv
TPD = {'74HCT14': 20.0, '74HCT00': 11.0, '74HCT20': 11.0} if TYP else \
      {'74HCT14': 40.0, '74HCT00': 25.0, '74HCT20': 35.0}
TPD_MIN = 3.0                                     # no datasheet minimum: a fast gate
T_LS08 = 10.0 if TYP else 20.0                    # console U4 on A15 / A14 / A12
tAA, tOE, tWP, tDW, tDH, tWR = 55.0, 30.0, 45.0, 25.0, 0.0, 0.0
T = 1e3 / (14.31818 / 8)                          # 558.7 ns
PWH2 = T / 2 - 25.0                               # phi2 high (PWH phi0 - 40..-10): 254 ns
T_PHI2R = T - PWH2                                # phi2 rises (cycle starts at phi1 rise)
S = dict(TADS=150.0, TRWS=150.0, TDSU=50.0, THR=10.0, TMDS=100.0, THW=30.0, THA=30.0, THRW=30.0)
T_PIO = 45.0
DL_WINDOW, GFX_WINDOW = 184.0, 285.0
GATED = ('A15', 'A14', 'A12')                     # through the console's 74LS08


def network():
    """net -> (gate tpd, [input nets], ref, value) for every glue gate output."""
    drv = {}
    for p in D.PARTS:
        if p.value not in D.GATE_PINS:
            continue
        for ins, out in D.GATE_PINS[p.value]:
            o = p.pins.get(str(out))
            if o:
                drv[o] = (TPD[p.value], [p.pins.get(str(i)) for i in ins], p.ref, p.value)
    return drv


def arrival(net, t0, drv, memo=None):
    """Latest settle time of `net`; nets in t0 settle then, other primaries at 0 (static)."""
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
    print('  %-30s %6.1f ns  %s' % (title, res[0], ' -> '.join(res[1])))


def addr_times(t_addr):
    t = {'A%d' % i: t_addr for i in range(16)}
    for a in GATED:
        t[a] = t_addr + T_LS08
    t_slot = max(t['A13'], t['A14'], t['A15']) + T_PIO
    for n in ('ROM_EN', 'RAM_EN', 'A8MASK') + tuple('SA%d' % i for i in range(13, 19)):
        t[n] = t_slot
    return t


def data_valid(t, drv, oe_from):
    """Data at the SRAM's DQ pins: tAA after its last address (A0-A12 direct, SA8 through the
    glue, SA13-18 from the PIO) or tOE after /OE, whichever is later; /OE timed from oe_from."""
    sa8 = arrival('SA8', t, drv)[0]
    t_addr_sram = max([t['A%d' % i] for i in range(13) if i != 8] + [sa8, t['SA13']])
    t0 = dict(t)
    for n in list(t0):
        if n not in oe_from and n not in ('RW', 'PWR_OK_N', 'VSENSE'):
            t0[n] = -1e6           # settled long before (static for this case)
    t0['VSENSE'] = -1e6
    oe = arrival('SRAM_OE_N', t0, drv)
    return max(t_addr_sram + tAA, oe[0] + tOE), oe, t_addr_sram


def main():
    drv = network()
    corner = 'typical, 25 C' if TYP else 'worst case: 4.5 V, 50 pF, -40..85 C'
    print('gate tpd (%s): %s; console 74LS08 %.0f ns; PIO slot change %.0f ns'
          % (corner, ', '.join('%s %.0f' % kv for kv in sorted(TPD.items())), T_LS08, T_PIO))
    print('6502 at 1.79 MHz: T %.1f ns, phi2 high %.0f ns (rises at %.0f); SY6502A 2 MHz proxy'
          % (T, PWH2, T_PHI2R))

    print('\n== glue paths')
    paths = {}
    for s, d in (('A15', 'SRAM_OE_N'), ('A14', 'SRAM_OE_N'), ('A12', 'SRAM_OE_N'), ('A11', 'SRAM_OE_N'),
                 ('A13', 'SRAM_OE_N'), ('RW', 'SRAM_OE_N'), ('ROM_EN', 'SRAM_OE_N'),
                 ('PHI2', 'SRAM_WE_N'), ('RW', 'SRAM_WE_N'), ('RAM_EN', 'SRAM_WE_N'), ('A13', 'SRAM_WE_N'),
                 ('A8', 'SA8'), ('A8MASK', 'SA8')):
        r = path_delay(s, d, drv)
        if r:
            paths[(s, d)] = r[0]
            show('%s -> %s' % (s, d), r)

    # ---- CPU read from the cart SRAM: data needed TDSU before phi2 falls -------------------
    print('\n== 6502 read of the cart SRAM (t = 0 at phi1 rise)')
    need = T - S['TDSU']
    for name, oe_from in (('game $4000-$FFFF (A15 | A14 decide)', ('A15', 'A14', 'RW', 'ROM_EN')),
                          ('HSC $1000-$17FF / $3000-$3FFF (A13 path)', ('A15', 'A14', 'A13', 'A12', 'A11', 'RW', 'ROM_EN'))):
        t = addr_times(S['TADS'])
        t['RW'] = S['TRWS']
        dv, oe, ta = data_valid(t, drv, oe_from)
        print('  %-46s /OE %.0f ns, data valid %.0f ns, needed %.0f ns: margin %+.0f ns' % (name, oe[0], dv, need, need - dv))

    # ---- MARIA DMA reads: address at 0, R/W held high, not phi2-aligned ---------------------------
    print('\n== MARIA DMA reads (t = 0 at MARIA address valid; R/W pulled up, static high)')
    sa8_a8 = path_delay('A8', 'SA8', drv)[0]
    same = max(tAA, sa8_a8 + tAA)
    t = addr_times(0.0)
    t['RW'] = -1e6
    t['A8MASK'] = -1e6                      # the slot changes, A8MASK does not
    dv_slot, oe, ta = data_valid(t, drv, ('A15', 'A14', 'ROM_EN'))
    t = addr_times(0.0)
    t['RW'] = -1e6
    dv_mask, oe2, ta2 = data_valid(t, drv, ('A15', 'A14', 'ROM_EN'))
    for name, dv in (('same 8K slot (A0-A12, SA8 via A8)', same),
                     ('slot change (PIO 45 ns, /OE via A15|A14)', dv_slot),
                     ('slot change toggling A8MASK (mram board)', dv_mask)):
        print('  %-42s data valid %3.0f ns: display-list window %.0f -> %+4.0f ns; graphics %.0f -> %+4.0f ns'
              % (name, dv, DL_WINDOW, DL_WINDOW - dv, GFX_WINDOW, GFX_WINDOW - dv))
    print('  A8MASK is set only by the mram board (a78map.c: slots 2-3, $4000-$7FFF RAM); "display lists must be in'
          ' fast (RAM) memory" -- console RAM, or cart RAM read in the same slot')
    t = addr_times(0.0)
    t['RW'] = -1e6
    t['A8MASK'] = -1e6
    dv_hsc, _, _ = data_valid(t, drv, ('A15', 'A14', 'A13', 'A12', 'A11', 'ROM_EN'))
    print('  HSC $1000-$3FFF (the 5-gate A13 path)       data valid %3.0f ns: display-list %+4.0f; graphics %+4.0f ns'
          % (dv_hsc, DL_WINDOW - dv_hsc, GFX_WINDOW - dv_hsc))

    # ---- CPU write into the cart SRAM ------------------------------------------------------------
    print('\n== 6502 write to the cart SRAM (RAM_EN slot)')
    t = addr_times(S['TADS'])
    t['RW'] = S['TRWS']
    t['PHI2'] = T_PHI2R
    t0 = {k: v for k, v in t.items()}
    t0['VSENSE'] = -1e6
    we_fall = arrival('SRAM_WE_N', t0, drv)
    show('/WE falls (latest)', we_fall)
    p2we = paths[('PHI2', 'SRAM_WE_N')]
    decode = arrival('CSEL_P', dict(t0, PHI2=-1e6), drv)[0]
    print('  decode (CSEL_P) settles at %.0f ns vs phi2 rise %.0f: %+.0f ns before the strobe can open (A13 path:'
          ' a glitch window only between $1000-$3FFF neighbours)' % (decode, T_PHI2R, T_PHI2R - decode))
    t_we_rise = T + p2we
    print('  /WE rises <= %.0f ns after phi2 falls (one gate); 6502 holds address >= %.0f, data >= %.0f ns (SY6502A min):'
          ' margin %+.0f / %+.0f ns (typ hold 60: %+.0f)' % (p2we, S['THA'], S['THW'], S['THA'] - p2we, S['THW'] - p2we,
                                                               60 - p2we))
    print('  write pulse >= %.0f ns (phi2 high %.0f - %.0f + %.0f) vs tWP %.0f; data setup >= %.0f ns (phi2 high - TMDS %.0f'
          ' + tpd min) vs tDW %.0f' % (PWH2 - p2we + TPD_MIN, PWH2, p2we, TPD_MIN, tWP, PWH2 - S['TMDS'] + TPD_MIN,
                                         S['TMDS'], tDW))
    print('  address valid to /WE rise >= %.0f ns vs tAW %.0f' % (T - S['TADS'] + TPD_MIN, 50.0))
    # ---- the R/W turnaround: /OE must close before the CPU drives a write ------------------------
    rw_oe = paths[('RW', 'SRAM_OE_N')]
    print('\n== read -> write turnaround: R/W falls <= %.0f ns into the cycle, /OE closes %.0f ns later, SRAM tOHZ 20:'
          ' bus free by %.0f ns; the 6502 drives write data from phi2 rise %.0f ns: %+.0f ns'
          % (S['TRWS'], rw_oe, S['TRWS'] + rw_oe + 20, T_PHI2R, T_PHI2R - (S['TRWS'] + rw_oe + 20)))


if __name__ == '__main__':
    main()
