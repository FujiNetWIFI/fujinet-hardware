#!/usr/bin/env python3
"""Evaluate the schematic's 74HCT glue, gate by gate from the netlist, for every combination of
its inputs, against the firmware's own equation.

The reference is fujinet-firmware pico/atari-5200/firmware/include/a52_cart.h a52_glue_drive(),
compiled with the host C compiler in the system temp directory and run over all 16 inputs.  The
spec's equation, written out below, must agree with it too.

Inputs (4): /EN40 and /EN80 from the edge pins; the console supply as the '14 Schmitt input the
edge pin 26 divider feeds (PWR_OK is that, twice inverted); BUF_EN from the RP GPIO a52_cart.h
names.  Output: the 74HCT541 drives D0-D7 when both its enables, /OE1 (pin 1) and /OE2 (pin 19),
are low.

Also checks the netlist structure the timing depends on: every used gate input is driven, nothing
loops, /EN40 and /EN80 are exactly one gate from one of the two enables (they are equivalent), PWR_OK is two '14 stages from the sense and
reaches GPIO PWROK_PIN, and every unused gate has its inputs tied and its output open.

Usage: python3 tools/check_glue.py         exit 1 on any failure
"""
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, define, unconn

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
INC = os.path.join(FW, 'pico/atari-5200/firmware/include')
CART = os.path.join(INC, 'a52_cart.h')

# gate tables from the 74HC/HCT datasheets: (input pins, output pin, function)
AND = lambda *a: int(all(a))
INV = lambda a: int(not a)
GATES = {
    '74HCT14': [((1,), 2, INV), ((3,), 4, INV), ((5,), 6, INV), ((9,), 8, INV), ((11,), 10, INV), ((13,), 12, INV)],
    '74HCT08': [((1, 2), 3, AND), ((4, 5), 6, AND), ((9, 10), 8, AND), ((12, 13), 11, AND)],
}
EDGE_PIN = {'EN40': 10, 'EN80': 9, 'PWR': 26}
OE1, OE2 = 1, 19                 # 74HCT541 output enables, active low
NAMES = ['EN40', 'EN80', 'PWR', 'BUFEN']

fails = 0


def fail(msg):
    global fails
    fails += 1
    print('FAIL:', msg)


def spec(b):
    """The equation as specified: the '541 drives while either enable is low, the console is
    powered and the RP is serving."""
    return int(bool(not (b['EN40'] and b['EN80']) and b['PWR'] and b['BUFEN']))


def firmware_table():
    """{4-bit input word (NAMES order): drive} from a52_cart.h, or None without a C compiler."""
    cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if not cc:
        print('note: no C compiler; checking against the written-out equation only')
        return None
    d = tempfile.mkdtemp(prefix='fujinet-5200-glue-')
    try:
        src = os.path.join(d, 'glue.c')
        open(src, 'w').write(r'''#include <stdio.h>
#include "a52_cart.h"
/* key bits, NAMES order: EN40 EN80 PWR BUFEN */
int main(void)
{
    for (unsigned k = 0; k < 16u; k++)
        printf("%u %d\n", k, a52_glue_drive(k & 1u, (k >> 1) & 1u, (k >> 2) & 1u, (k >> 3) & 1u) ? 1 : 0);
    return 0;
}
''')
        exe = os.path.join(d, 'glue')
        r = subprocess.run([cc, '-std=c11', '-I', INC, src, '-o', exe], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit('a52_cart.h does not compile on the host:\n' + r.stderr)
        r = subprocess.run([exe], capture_output=True, text=True, check=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    tab = {}
    for line in r.stdout.split('\n'):
        if line:
            k, v = map(int, line.split())
            tab[k] = v
    return tab


def main():
    N = Netlist()
    U1, J1, BUF = N.one('RP2354B'), N.one('Atari5200_Cart_Edge_36'), N.one('74HCT541')
    if None in (U1, J1, BUF):
        raise SystemExit("RP2354B, the edge or the '541 missing from the netlist")

    def rp(gpio):
        for (ref, f), n in N.func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        raise SystemExit('GP%d not in the netlist' % gpio)

    # the gate network; unused gates (every input on GND, output open) are checked and set aside
    gates, unused = [], []        # (ref, unit, [input nets], output net, fn)
    for ref, (val, _) in sorted(N.parts.items()):
        if val in GATES:
            for k, (ins, out, fn) in enumerate(GATES[val]):
                g = (ref, k + 1, [N.net(ref, p) for p in ins], N.net(ref, out), fn)
                (unused if all(n == 'GND' for n in g[2]) else gates).append(g)
    for ref, unit, ins, out, fn in unused:
        if not unconn(out):
            fail('%s unit %d: inputs tied to GND but its output drives %s' % (ref, unit, out))
    drivers = {}
    for g in gates:
        if g[3] in drivers:
            fail('net %s driven by two gates' % g[3])
        drivers[g[3]] = g
    v5 = N.func_net.get((BUF, 'VCC'))
    cons = N.net(J1, EDGE_PIN['PWR'])

    # console power: the '14 input fed from edge pin 26 through the divider
    u14 = N.one('74HCT14')
    vsense = None
    for ins, out, fn in GATES['74HCT14']:
        n = N.net(u14, ins[0])
        for r, (val, _) in N.parts.items():
            if re.match(r'R\d+$', r) and {N.net(r, 1), N.net(r, 2)} == {cons, n}:
                vsense = n
    if vsense is None:
        raise SystemExit("no '14 input on the edge pin 26 divider")
    P = {k: define(CART, k + '_PIN') for k in ('BUFEN', 'PWROK', 'EN40', 'EN80')}
    inputs = {'EN40': N.net(J1, EDGE_PIN['EN40']), 'EN80': N.net(J1, EDGE_PIN['EN80']), 'PWR': vsense,
              'BUFEN': rp(P['BUFEN'])}
    for k in ('EN40', 'EN80'):
        if inputs[k] != rp(P[k]):
            fail('edge /%s is not GP%d (%s_PIN)' % (k, P[k], k))
    oe1, oe2 = N.net(BUF, OE1), N.net(BUF, OE2)

    # structure: every gate input driven, no loops; timing-critical depths
    known = set(inputs.values()) | {'GND', v5}
    for g in gates:
        for n in g[2]:
            if n not in known and n not in drivers:
                fail('%s unit %d input on %s: nothing drives it' % (g[0], g[1], n))
    for n in (oe1, oe2):
        if n not in drivers and n not in known:
            fail("'541 enable on %s: nothing drives it" % n)

    def depth(net, src, seen=()):
        """Gates from src to net along the longest path (None if net does not depend on src)."""
        if net == src:
            return 0
        if net not in drivers:
            return None
        if net in seen:
            raise SystemExit('combinational loop through %s' % net)
        ds = [depth(n, src, seen + (net,)) for n in drivers[net][2]]
        ds = [d for d in ds if d is not None]
        return 1 + max(ds) if ds else None
    # the '541 drives while /OE1 and /OE2 are both low, so either may carry the enables: the one
    # that does must be exactly one gate from both of them, the other must not depend on them
    en_oe = oe1 if depth(oe1, inputs['EN40']) is not None else oe2
    other = oe2 if en_oe == oe1 else oe1
    for k in ('EN40', 'EN80'):
        d1, d2 = depth(en_oe, inputs[k]), depth(other, inputs[k])
        print("/%s -> '541 /OE%d: %s gate(s); /OE%d: %s" % (k, 1 if en_oe == oe1 else 2, d1, 2 if en_oe == oe1 else 1, d2))
        if d1 != 1 or d2 is not None:
            fail("/%s must reach one '541 enable alone, in one gate (got %s, %s)" % (k, d1, d2))
    for k in ('PWR', 'BUFEN'):
        print("%s -> '541 /OE1: %s, /OE2: %s gate(s)" % (k, depth(oe1, inputs[k]), depth(oe2, inputs[k])))
    if depth(rp(P['PWROK']), vsense) != 2:
        fail("PWR_OK (GP%d) is not two '14 stages from the console sense" % P['PWROK'])
    used = {n for g in gates for n in g[2]} | {oe1, oe2, rp(P['PWROK'])}
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
    mism = 0
    print('%-5s %-5s %-4s %-6s | %-5s %-5s %-6s %-6s %s' % ('EN40', 'EN80', 'PWR', 'BUF_EN', '/OE1', '/OE2', 'drive',
                                                             'spec', 'a52_glue_drive'))
    for v in range(1 << len(NAMES)):
        b = dict(zip(NAMES, [(v >> i) & 1 for i in range(len(NAMES))]))
        get = evaluate({inputs[k]: b[k] for k in NAMES})
        o1, o2 = get(oe1), get(oe2)
        got = int(o1 == 0 and o2 == 0)
        if get(rp(P['PWROK'])) != b['PWR']:
            fail('%s: PWR_OK (GP%d) does not follow the console sense' % (b, P['PWROK']))
        want = spec(b)
        ok = got == want and (fw is None or got == fw[v])
        mism += not ok
        print('%-5d %-5d %-4d %-6d | %-5d %-5d %-6d %-6d %s%s' % (b['EN40'], b['EN80'], b['PWR'], b['BUFEN'], o1, o2,
                                                                 got, want, '-' if fw is None else fw[v],
                                                                 '' if ok else '   MISMATCH'))
        if not ok:
            fail('%s: netlist drive %d, spec %d, a52_glue_drive %s' % (b, got, want, None if fw is None else fw[v]))
    print('glue: %d input combinations, %d mismatches against %s' %
          (1 << len(NAMES), mism, 'a52_glue_drive() (compiled) and the spec equation' if fw else 'the spec equation'))
    print('%d gates in use in %d packages, %d unused gates tied off' % (len(gates), len({g[0] for g in gates}), len(unused)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
