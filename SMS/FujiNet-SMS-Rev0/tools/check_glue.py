#!/usr/bin/env python3
"""Evaluate the schematic's 74HCT glue, gate by gate from the netlist, for every
combination of its inputs, against the firmware's own equations.

The reference is fujinet-firmware pico/sms/firmware/include/sms_cart.h
(sms_glue_oe / sms_glue_we), compiled with the host C compiler into a truth
table in the system temp directory; the spec's equations, written out below,
must agree with it too.  Inputs (13): A12-A15, /RD, /WR, /CE from the edge
pins, GAME / MBOX / RAM_WE / LOAD / SRAM A19 from the RP GPIOs sms_cart.h
names, console power as the '14 Schmitt input the edge +5V divider feeds.
Outputs: SRAM /OE, /WE (shared by both chips) and each chip's /CE.

Also checks the netlist structure the timing depends on: every gate input is
driven, nothing loops, and the console's /RD and /WR reach /WE through at most
two gates (the write ends two gate delays after the strobe does).

Usage: python3 tools/check_glue.py         exit 1 on any failure
"""
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, define

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
INC = os.path.join(FW, 'pico/sms/firmware/include')
CART = os.path.join(INC, 'sms_cart.h')

# gate tables from the 74HC/HCT datasheets: (input pins, output pin, function)
NAND = lambda *a: int(not all(a))
NOR = lambda *a: int(not any(a))
INV = lambda a: int(not a)
GATES = {
    '74HCT14': [((1,), 2, INV), ((3,), 4, INV), ((5,), 6, INV), ((9,), 8, INV), ((11,), 10, INV), ((13,), 12, INV)],
    '74HCT00': [((1, 2), 3, NAND), ((4, 5), 6, NAND), ((9, 10), 8, NAND), ((12, 13), 11, NAND)],
    '74HCT10': [((1, 2, 13), 12, NAND), ((3, 4, 5), 6, NAND), ((9, 10, 11), 8, NAND)],
    '74HCT27': [((1, 2, 13), 12, NOR), ((3, 4, 5), 6, NOR), ((9, 10, 11), 8, NOR)],
}
EDGE_PIN = {'A12': 33, 'A13': 7, 'A14': 6, 'A15': 36, 'RD_N': 4, 'WR_N': 2, 'CE_N': 13, '+5V': 1}
NAMES = ['A12', 'A13', 'A14', 'A15', 'PWR', 'GAME', 'MBOX', 'RAM_WE', 'LOAD', 'RD', 'WR', 'CE', 'A19']

fails = 0


def fail(msg):
    global fails
    fails += 1
    print('FAIL:', msg)


def spec(v):
    """The equations as specified (active-high logic levels): (oe, we)."""
    A12, A13, A14, A15, PWR, GAME, MBOX, RAM_WE, LOAD, RD, WR, CE = v[:12]
    HIGH16 = A15 and A14
    SLOT2 = A15 and not A14
    WIN8 = A15 and not A14 and not A13
    ARENA = A15 and not A14 and A13 and A12
    oe = PWR and GAME and RD and CE and not HIGH16 and not (MBOX and ARENA)
    we = PWR and CE and ((LOAD and RD and WIN8) or (RAM_WE and WR and SLOT2 and not (MBOX and ARENA)))
    return int(bool(oe)), int(bool(we))


def firmware_table():
    """{12-bit input word: (oe, we)} from sms_cart.h, or None without a C compiler."""
    cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if not cc:
        print('note: no C compiler; checking against the written-out equations only')
        return None
    d = tempfile.mkdtemp(prefix='fujinet-sms-glue-')
    try:
        src = os.path.join(d, 'glue.c')
        open(src, 'w').write(r'''#include <stdio.h>
#include "sms_cart.h"
int main(void)
{
    for (unsigned v = 0; v < 4096u; v++) {
        uint16_t a = (uint16_t)((v & 0xFu) << 12);          /* A12-A15 */
        sms_glue_t g = { (v >> 4) & 1, (v >> 5) & 1, (v >> 6) & 1, (v >> 7) & 1, (v >> 8) & 1 };
        bool rd = (v >> 9) & 1, wr = (v >> 10) & 1, ce = (v >> 11) & 1;
        printf("%u %d %d\n", v, sms_glue_oe(g, a, rd, ce), sms_glue_we(g, a, rd, wr, ce));
    }
    return 0;
}
''')
        exe = os.path.join(d, 'glue')
        subprocess.run([cc, '-std=c11', '-I', INC, src, '-o', exe], check=True, capture_output=True)
        out = subprocess.run([exe], check=True, capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    tab = {}
    for line in out.split('\n'):
        if line:
            v, oe, we = map(int, line.split())
            tab[v] = (oe, we)
    return tab


def main():
    N = Netlist()
    U1, J1 = N.one('RP2354B'), N.one('SMS_Cart_Edge_50')
    srams = N.by_value('AS6C4008-55TIN')
    if None in (U1, J1) or len(srams) != 2:
        raise SystemExit('RP2354B, edge or the two SRAMs missing from the netlist')

    def rp(gpio):
        for (ref, f), n in N.func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        raise SystemExit('GP%d not in the netlist' % gpio)

    # the gate network
    gates = []        # (ref, unit, [input nets], output net, fn)
    for ref, (val, _) in sorted(N.parts.items()):
        if val in GATES:
            for k, (ins, out, fn) in enumerate(GATES[val]):
                gates.append((ref, k + 1, [N.net(ref, p) for p in ins], N.net(ref, out), fn))
    drivers = {}
    for g in gates:
        if g[3] in drivers:
            fail('net %s driven by two gates' % g[3])
        drivers[g[3]] = g
    v5 = N.func_net.get((srams[0], 'VCC'))
    cons = N.net(J1, EDGE_PIN['+5V'])

    # console power: the '14 input fed from the edge +5V through the divider
    u14 = N.one('74HCT14')
    vsense = None
    for ins, out, fn in GATES['74HCT14']:
        n = N.net(u14, ins[0])
        for r, (val, _) in N.parts.items():
            if r.startswith('R') and not r.startswith('RN') and {N.net(r, 1), N.net(r, 2)} == {cons, n}:
                vsense = n
    if vsense is None:
        raise SystemExit("no '14 input on the edge +5V divider")
    P = {k: define(CART, k + '_PIN') for k in ('GAME', 'MBOX', 'RAMWE', 'LOAD', 'BANK', 'PWROK')}
    inputs = {'A12': N.net(J1, 33), 'A13': N.net(J1, 7), 'A14': N.net(J1, 6), 'A15': N.net(J1, 36),
              'RD_N': N.net(J1, 4), 'WR_N': N.net(J1, 2), 'CE_N': N.net(J1, 13), 'PWR': vsense,
              'GAME': rp(P['GAME']), 'MBOX': rp(P['MBOX']), 'RAM_WE': rp(P['RAMWE']), 'LOAD': rp(P['LOAD']),
              'A19': rp(P['BANK'] + 6)}
    oe_n, we_n = N.func_net.get((srams[0], '~{OE}')), N.func_net.get((srams[0], '~{WE}'))
    ce_n = [N.func_net.get((r, '~{CE}')) for r in srams]
    if N.func_net.get((srams[1], '~{OE}')) != oe_n or N.func_net.get((srams[1], '~{WE}')) != we_n:
        fail('the two SRAMs do not share /OE and /WE')

    # structure: every gate input driven, no loops; strobe depth to /WE
    known = set(inputs.values()) | {'GND', v5}
    for g in gates:
        for n in g[2]:
            if n not in known and n not in drivers:
                fail('%s unit %d input on %s: nothing drives it' % (g[0], g[1], n))

    depth_memo = {}

    def depth(net, src, seen=()):
        """Gates from src to net along the longest path (None if net does not depend on src)."""
        if net == src:
            return 0
        if net not in drivers:
            return None
        if net in seen:
            raise SystemExit('combinational loop through %s' % net)
        key = (net, src)
        if key not in depth_memo:
            ds = [depth(n, src, seen + (net,)) for n in drivers[net][2]]
            ds = [d for d in ds if d is not None]
            depth_memo[key] = 1 + max(ds) if ds else None
        return depth_memo[key]
    for s in ('RD_N', 'WR_N'):
        d = depth(we_n, inputs[s])
        print('%s -> SRAM /WE: %s gates' % (s, d))
        if d is None or d > 2:
            fail('%s reaches /WE through %s gates (want <= 2)' % (s, d))
    print('RD_N -> SRAM /OE: %s gates; CE_N -> /OE: %s; CE_N -> /WE: %s' %
          (depth(oe_n, inputs['RD_N']), depth(oe_n, inputs['CE_N']), depth(we_n, inputs['CE_N'])))
    pwr_ok = drivers.get(rp(P['PWROK']))
    if not pwr_ok or depth(rp(P['PWROK']), vsense) != 2:
        fail("PWR_OK (GP%d) is not two '14 stages from the console sense" % P['PWROK'])
    used = {n for g in gates for n in g[2]} | {oe_n, we_n, *ce_n, rp(P['PWROK'])}
    for g in gates:
        if g[3] not in used:
            fail('%s unit %d output %s goes nowhere' % (g[0], g[1], g[3]))
    if fails:
        sys.exit(1)

    def evaluate(env):
        val = dict(env)
        val['GND'], val[v5] = 0, 1

        def get(n):
            if n not in val:
                ref, unit, ins, out, fn = drivers[n]
                val[n] = fn(*[get(i) for i in ins])
            return val[n]
        return get

    fw = firmware_table()
    rows = mism = 0
    for v in range(1 << 13):
        bits = [(v >> i) & 1 for i in range(13)]
        b = dict(zip(NAMES, bits))
        env = {inputs['A12']: b['A12'], inputs['A13']: b['A13'], inputs['A14']: b['A14'], inputs['A15']: b['A15'],
               inputs['PWR']: b['PWR'], inputs['GAME']: b['GAME'], inputs['MBOX']: b['MBOX'],
               inputs['RAM_WE']: b['RAM_WE'], inputs['LOAD']: b['LOAD'], inputs['RD_N']: 1 - b['RD'],
               inputs['WR_N']: 1 - b['WR'], inputs['CE_N']: 1 - b['CE'], inputs['A19']: b['A19']}
        get = evaluate(env)
        got = (1 - get(oe_n), 1 - get(we_n))
        want = spec(bits)
        if fw is not None:
            word = sum(bits[i] << i for i in range(12))
            if fw[word] != want:
                fail('the spec equations disagree with sms_cart.h at %s: spec %s, firmware %s' % (b, want, fw[word]))
        sel = [1 - get(n) for n in ce_n]
        rows += 1
        if got != want or sel != [1 - b['A19'], b['A19']]:
            mism += 1
            if mism <= 10:
                fail('%s: netlist /OE,/WE asserted %s, want %s; chip selects %s' % (b, got, want, sel))
    print('glue: %d input combinations, %d mismatches against %s' %
          (rows, mism, 'sms_cart.h (compiled) and the spec equations' if fw else 'the spec equations'))
    print('%d gates in %d packages' % (len(gates), len({g[0] for g in gates})))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
