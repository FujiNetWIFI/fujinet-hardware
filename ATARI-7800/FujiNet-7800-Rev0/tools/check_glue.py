#!/usr/bin/env python3
"""Evaluate the schematic's 74HCT glue, gate by gate from the netlist, for every
combination of its inputs, against the firmware's own equations.

The reference is fujinet-firmware pico/atari-7800/firmware/include/a78_cart.h
(a78_glue_oe / a78_glue_we / a78_glue_a8, through a78_cartsel), compiled with
the host C compiler in the system temp directory.  The harness runs them over
the whole input space -- all 65536 addresses x the six other inputs -- and
first proves they read no address bit but A8 and A11-A15, so the 12 inputs
the glue sees are the whole truth table.  The spec's equations, written out
below, must agree with it too.

Inputs (12): A8, A11-A15, R/W, PHI2 from the edge pins; ROM_EN, RAM_EN,
A8MASK from the RP GPIOs a78_cart.h / a78map.h name (SLOT_PIN + slot-word
bit); console power as the '14 Schmitt input the edge +5V divider feeds.
Outputs: SRAM /OE, /WE and SRAM A8.

Also checks the netlist structure the timing depends on: every gate input is
driven, nothing loops, PHI2 is exactly one gate from /WE (the write ends one
gate delay after PHI2 falls), R/W one gate from /OE, A8 at most two from
SRAM A8; the address depths to /OE are reported.

Usage: python3 tools/check_glue.py         exit 1 on any failure
"""
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, define

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
INC = os.path.join(FW, 'pico/atari-7800/firmware/include')
CART = os.path.join(INC, 'a78_cart.h')
MAP = os.path.join(INC, 'a78map.h')

# gate tables from the 74HC/HCT datasheets: (input pins, output pin, function)
NAND = lambda *a: int(not all(a))
INV = lambda a: int(not a)
GATES = {
    '74HCT14': [((1,), 2, INV), ((3,), 4, INV), ((5,), 6, INV), ((9,), 8, INV), ((11,), 10, INV), ((13,), 12, INV)],
    '74HCT00': [((1, 2), 3, NAND), ((4, 5), 6, NAND), ((9, 10), 8, NAND), ((12, 13), 11, NAND)],
    '74HCT20': [((1, 2, 4, 5), 6, NAND), ((9, 10, 12, 13), 8, NAND)],
}
EDGE_PIN = {'A8': 12, 'A11': 10, 'A12': 8, 'A13': 15, 'A14': 16, 'A15': 17, 'RW': 1, 'PHI2': 32, '+5V': 13}
NAMES = ['A8', 'A11', 'A12', 'A13', 'A14', 'A15', 'PWR', 'RW', 'PHI2', 'ROM_EN', 'RAM_EN', 'A8MASK']

fails = 0


def fail(msg):
    global fails
    fails += 1
    print('FAIL:', msg)


def spec(b):
    """The equations as specified (active-high logic levels): (oe, we, sram_a8)."""
    A15, A14, A13, A12, A11 = b['A15'], b['A14'], b['A13'], b['A12'], b['A11']
    cartsel = A15 or A14 or (not A15 and not A14 and not A13 and A12 and not A11) or \
        (not A15 and not A14 and A13 and A12)
    oe = b['PWR'] and b['RW'] and b['ROM_EN'] and cartsel
    we = b['PWR'] and not b['RW'] and b['PHI2'] and b['RAM_EN'] and cartsel
    a8 = b['A8'] and not b['A8MASK']
    return int(bool(oe)), int(bool(we)), int(bool(a8))


def firmware_table():
    """{12-bit input word (NAMES order): (oe, we, a8)} from a78_cart.h, or None
    without a C compiler.  The harness sweeps every address and fails if the
    functions read an address bit outside A8, A11-A15."""
    cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if not cc:
        print('note: no C compiler; checking against the written-out equations only')
        return None, 0
    d = tempfile.mkdtemp(prefix='fujinet-7800-glue-')
    try:
        src = os.path.join(d, 'glue.c')
        open(src, 'w').write(r'''#include <stdio.h>
#include <string.h>
#include "a78_cart.h"
/* key bits, NAMES order: A8 A11 A12 A13 A14 A15 PWR RW PHI2 ROM_EN RAM_EN A8MASK */
int main(void)
{
    static int tab[4096];
    unsigned long n = 0;
    memset(tab, -1, sizeof tab);
    for (unsigned a = 0; a < 65536u; a++) {
        for (unsigned o = 0; o < 64u; o++) {
            bool pwr = o & 1, rw = (o >> 1) & 1, phi2 = (o >> 2) & 1;
            uint16_t slot = (uint16_t)(((o >> 3) & 1 ? A78S_ROM_EN : 0) | ((o >> 4) & 1 ? A78S_RAM_EN : 0) |
                                       ((o >> 5) & 1 ? A78S_A8MASK : 0));
            int v = a78_glue_oe(pwr, slot, (uint16_t)a, rw) | a78_glue_we(pwr, slot, (uint16_t)a, rw, phi2) << 1 |
                    a78_glue_a8(slot, (uint16_t)a) << 2;
            unsigned k = ((a >> 8) & 1) | ((a >> 11) & 0x1Fu) << 1 | o << 6;
            if (tab[k] < 0)
                tab[k] = v;
            else if (tab[k] != v) {
                printf("DEPENDS %u %u\n", a, o);
                return 1;
            }
            n++;
        }
    }
    printf("SWEPT %lu\n", n);
    for (unsigned k = 0; k < 4096u; k++)
        printf("%u %d %d %d\n", k, tab[k] & 1, (tab[k] >> 1) & 1, (tab[k] >> 2) & 1);
    return 0;
}
''')
        exe = os.path.join(d, 'glue')
        subprocess.run([cc, '-std=c11', '-I', INC, src, '-o', exe], check=True, capture_output=True)
        r = subprocess.run([exe], capture_output=True, text=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if r.returncode:
        raise SystemExit('a78_cart.h glue reads an address bit the board does not wire to the glue: %s' % r.stdout.strip())
    tab, swept = {}, 0
    for line in r.stdout.split('\n'):
        if line.startswith('SWEPT'):
            swept = int(line.split()[1])
        elif line:
            k, oe, we, a8 = map(int, line.split())
            tab[k] = (oe, we, a8)
    return tab, swept


def main():
    N = Netlist()
    U1, J1 = N.one('RP2354B'), N.one('Atari7800_Cart_Edge_32')
    srams = N.by_value('AS6C4008-55TIN')
    if None in (U1, J1) or len(srams) != 1:
        raise SystemExit('RP2354B, edge or the SRAM missing from the netlist')
    S = srams[0]

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
    v5 = N.func_net.get((S, 'VCC'))
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
    P = {k: define(CART, k + '_PIN') for k in ('SLOT', 'PWROK')}
    bit = lambda m: define(MAP, m).bit_length() - 1          # slot-word bit -> SLOT_PIN offset
    inputs = {k: N.net(J1, EDGE_PIN[k]) for k in ('A8', 'A11', 'A12', 'A13', 'A14', 'A15', 'RW', 'PHI2')}
    inputs.update({'PWR': vsense, 'ROM_EN': rp(P['SLOT'] + bit('A78S_ROM_EN')),
                   'RAM_EN': rp(P['SLOT'] + bit('A78S_RAM_EN')), 'A8MASK': rp(P['SLOT'] + bit('A78S_A8MASK'))})
    oe_n, we_n, sa8 = N.func_net.get((S, '~{OE}')), N.func_net.get((S, '~{WE}')), N.func_net.get((S, 'A8'))
    if sa8 == inputs['A8']:
        fail('SRAM A8 is the console A8 directly (A8MASK has no effect)')
    if not str(N.func_net.get((S, '~{CE}'))) == 'GND':
        fail('SRAM /CE is not tied active (GND)')

    # structure: every gate input driven, no loops; timing-critical depths
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
    for out, src, want in ((we_n, 'PHI2', 1), (oe_n, 'RW', 1)):
        d = depth(out, inputs[src])
        print('%s -> SRAM %s: %s gate(s)' % (src, '/WE' if out == we_n else '/OE', d))
        if d != want:
            fail('%s reaches %s through %s gates (want exactly %d)' % (src, out, d, want))
    d = depth(we_n, inputs['RW'])
    print('RW -> SRAM /WE: %s gates' % d)
    if d is None or d > 2:
        fail('RW reaches /WE through %s gates (want <= 2)' % d)
    d = depth(sa8, inputs['A8'])
    print('A8 -> SRAM A8: %s gates' % d)
    if d is None or d > 2:
        fail('A8 reaches SRAM A8 through %s gates (want <= 2)' % d)
    print('address -> SRAM /OE: ' + ', '.join('%s %s' % (a, depth(oe_n, inputs[a]))
                                             for a in ('A15', 'A14', 'A13', 'A12', 'A11')))
    if depth(rp(P['PWROK']), vsense) != 2:
        fail("PWR_OK (GP%d) is not two '14 stages from the console sense" % P['PWROK'])
    used = {n for g in gates for n in g[2]} | {oe_n, we_n, sa8, rp(P['PWROK'])}
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

    fw, swept = firmware_table()
    rows = mism = 0
    for v in range(1 << len(NAMES)):
        b = dict(zip(NAMES, [(v >> i) & 1 for i in range(len(NAMES))]))
        env = {inputs[k]: b[k] for k in NAMES}
        get = evaluate(env)
        got = (1 - get(oe_n), 1 - get(we_n), get(sa8))
        want = spec(b)
        rows += 1
        bad = []
        if got != want:
            bad.append('spec %s' % (want,))
        if fw is not None and got != fw[v]:
            bad.append('a78_cart.h %s' % (fw[v],))
        if bad:
            mism += 1
            if mism <= 10:
                fail('%s: netlist /OE,/WE asserted, SRAM A8 = %s; %s' % (b, got, ', '.join(bad)))
    if fw is not None:
        print('a78_cart.h: %d (address, input) combinations swept; the glue reads only A8, A11-A15' % swept)
    print('glue: %d input combinations, %d mismatches against %s' %
          (rows, mism, 'a78_cart.h (compiled) and the spec equations' if fw else 'the spec equations'))
    print('%d gates in %d packages' % (len(gates), len({g[0] for g in gates})))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
