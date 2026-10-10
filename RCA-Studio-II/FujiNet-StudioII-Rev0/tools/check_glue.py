#!/usr/bin/env python3
"""Evaluate the schematic's glue, gate by gate from the netlist, for every combination of its
inputs, against the firmware's own equations.

The reference is fujinet-firmware pico/studio2/firmware/include/s2_cart.h: s2_glue_drive(mrd_n,
drive_n, pwrok) and s2_glue_cartcs(mrd_n, claim_n, pwrok), compiled with the host C compiler in the
system temp directory and run over all 8 inputs of each.  The equations, written out below, must
agree with them too.

Inputs (4): /MRD from edge pin 21; /DRIVE and /CLAIM from the RP GPIOs s2_cart.h names; the console
supply as the '14 Schmitt input the edge pin 15 divider feeds (pwrok is that sense, and GPIO
PWROK_PIN must follow it through two '14 stages).  Outputs: the 74HCT541 drives D0-D7 when both its
enables, /OE1 (pin 1) and /OE2 (pin 19), are low; CART CS is the net on edge pin 22.  The 16 joint
combinations cover each equation's 8 twice.

Also checks the netlist structure the timing depends on: every used gate input is driven, nothing
loops, /MRD reaches /OE1 with no gate and CART CS through one, /DRIVE and /CLAIM never reach each
other's output, and two safe states: the RP unpowered (/DRIVE and /CLAIM held high by their pull-ups)
and the console off (the RP, running from USB, leaving anything on its pins) -- in both the cart
neither drives D nor raises CART CS.

Usage: python3 tools/check_glue.py         exit 1 on any failure
"""
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, define, unconn

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
FWDIR = os.path.join(FW, 'pico/studio2/firmware')
INC = os.path.join(FWDIR, 'include')
CART = os.path.join(INC, 's2_cart.h')

# gate tables from the 74HC/HCT datasheets: (input pins, output pin, function)
NOR = lambda *a: int(not any(a))
OR = lambda *a: int(any(a))
INV = lambda a: int(not a)
GATES = {
    '74HCT1G02': [((1, 2), 4, NOR)],                          # Nexperia: 1 B, 2 A, 4 Y
    '74HCT32': [((1, 2), 3, OR), ((4, 5), 6, OR), ((9, 10), 8, OR), ((12, 13), 11, OR)],
    '74HCT14': [((1,), 2, INV), ((3,), 4, INV), ((5,), 6, INV), ((9,), 8, INV), ((11,), 10, INV), ((13,), 12, INV)],
}
EDGE_PIN = {'MRD': 21, 'CARTCS': 22, 'PWR': 15}
OE1, OE2 = 1, 19                 # 74HCT541 output enables, active low
NAMES = ['MRD', 'DRIVE', 'CLAIM', 'PWR']

fails = 0


def fail(msg):
    global fails
    fails += 1
    print('FAIL:', msg)


def spec(b):
    """The equations as specified: the '541 drives while /MRD and /DRIVE are both low and the
    console is powered; CART CS is NOR(/MRD, /CLAIM) while the console is powered."""
    return (int(not b['MRD'] and not b['DRIVE'] and b['PWR']),
            int(not (b['MRD'] or b['CLAIM']) and b['PWR']))


def firmware_tables():
    """({3-bit word (mrd_n, drive_n, pwrok): drive}, {3-bit word (mrd_n, claim_n, pwrok): cartcs})
    from s2_cart.h, or None without a C compiler."""
    cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if not cc:
        print('note: no C compiler; checking against the written-out equations only')
        return None
    d = tempfile.mkdtemp(prefix='fujinet-studio2-glue-')
    try:
        src = os.path.join(d, 'glue.c')
        open(src, 'w').write(r'''#include <stdio.h>
#include "s2_cart.h"
/* key bits: mrd_n, drive_n / claim_n, pwrok */
int main(void)
{
    for (unsigned k = 0; k < 8u; k++) {
        bool a = k & 1u, b = (k >> 1) & 1u, p = (k >> 2) & 1u;
        printf("%u %d %d\n", k, s2_glue_drive(a, b, p) ? 1 : 0, s2_glue_cartcs(a, b, p) ? 1 : 0);
    }
    return 0;
}
''')
        exe = os.path.join(d, 'glue')
        r = subprocess.run([cc, '-std=c11', '-D_DEFAULT_SOURCE', '-I', FWDIR, '-I', INC, src, '-o', exe],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit('s2_cart.h does not compile on the host (or its glue is not '
                             's2_glue_drive(mrd_n, drive_n, pwrok) / s2_glue_cartcs(mrd_n, claim_n, pwrok)):\n'
                             + r.stderr)
        r = subprocess.run([exe], capture_output=True, text=True, check=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    drive, cartcs = {}, {}
    for line in r.stdout.split('\n'):
        if line:
            k, dr, cs = map(int, line.split())
            drive[k], cartcs[k] = dr, cs
    return drive, cartcs


def main():
    N = Netlist()
    U1, J1, BUF = N.one('RP2354B'), N.one('StudioII_Cart_Edge_22'), N.one('74HCT541')
    U14 = N.one('74HCT14')
    if None in (U1, J1, BUF, U14):
        raise SystemExit("RP2354B, the edge, the '541 or the '14 missing from the netlist")

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
    v5 = N.net(BUF, 20)

    # console power: the '14 input fed from edge pin 15 through the divider
    cons = N.net(J1, EDGE_PIN['PWR'])
    vsense = None
    for ins, out, fn in GATES['74HCT14']:
        n = N.net(U14, ins[0])
        for r, (val, _) in N.parts.items():
            if re.match(r'R\d+$', r) and {N.net(r, 1), N.net(r, 2)} == {cons, n}:
                vsense = n
    if vsense is None:
        raise SystemExit("no '14 input on the edge pin 15 divider")
    P = {k: define(CART, k + '_PIN') for k in ('MRD', 'DRIVE', 'CLAIM', 'PWROK')}
    inputs = {'MRD': N.net(J1, EDGE_PIN['MRD']), 'DRIVE': rp(P['DRIVE']), 'CLAIM': rp(P['CLAIM']), 'PWR': vsense}
    for k, n in inputs.items():
        if unconn(n):
            fail('glue input %s is unconnected' % k)
    oe1, oe2, cartcs = N.net(BUF, OE1), N.net(BUF, OE2), N.net(J1, EDGE_PIN['CARTCS'])
    pwrok_pin = rp(P['PWROK'])

    # structure: every gate input driven, no loops, the depths the timing depends on
    known = set(inputs.values()) | {'GND', v5}
    for g in gates:
        for n in g[2]:
            if n not in known and n not in drivers:
                fail('%s unit %d input on %s: nothing drives it' % (g[0], g[1], n))
    for n, what in ((oe1, "'541 /OE1"), (oe2, "'541 /OE2"), (cartcs, 'CART CS (edge 22)'), (pwrok_pin, 'PWR_OK')):
        if n not in drivers and n not in known:
            fail('%s on %s: nothing drives it' % (what, n))

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
    for out, name in ((oe1, '/OE1'), (oe2, '/OE2'), (cartcs, 'CART CS'), (pwrok_pin, 'PWR_OK')):
        print('%-8s <- %s' % (name, ', '.join('%s %s' % (k, depth(out, inputs[k])) for k in NAMES)))
    if depth(oe1, inputs['MRD']) != 0:
        fail("/MRD is not the '541's /OE1 itself: the end of a read must release D0-D7 with no gate")
    if depth(cartcs, inputs['MRD']) != 1:
        fail('CART CS is not one gate from /MRD')
    if depth(oe2, inputs['DRIVE']) is None or depth(cartcs, inputs['CLAIM']) is None:
        fail("/DRIVE does not reach the '541 or /CLAIM does not reach CART CS")
    if depth(cartcs, inputs['DRIVE']) is not None or depth(oe1, inputs['CLAIM']) is not None \
            or depth(oe2, inputs['CLAIM']) is not None:
        fail("/DRIVE reaches CART CS or /CLAIM reaches the '541")
    if depth(pwrok_pin, vsense) != 2:
        fail("PWR_OK (GP%d) is not two '14 stages from the console sense" % P['PWROK'])
    used = {n for g in gates for n in g[2]} | {oe1, oe2, cartcs, pwrok_pin}
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

    fw = firmware_tables()
    mism = 0
    print('%-4s %-6s %-6s %-4s | %-6s | %-5s %-5s %-6s %-7s | %-5s %s' % (
        '/MRD', '/DRIVE', '/CLAIM', 'PWR', 'PWR_OK', '/OE1', '/OE2', 'drive', 'CART_CS', 'spec', 's2_cart.h'))
    for v in range(1 << len(NAMES)):
        b = dict(zip(NAMES, [(v >> i) & 1 for i in range(len(NAMES))]))
        get = evaluate({inputs[k]: b[k] for k in NAMES})
        o1, o2, cs = get(oe1), get(oe2), get(cartcs)
        got = (int(o1 == 0 and o2 == 0), cs)
        want = spec(b)
        fwv = None
        if fw:
            fwv = (fw[0][b['MRD'] | b['DRIVE'] << 1 | b['PWR'] << 2], fw[1][b['MRD'] | b['CLAIM'] << 1 | b['PWR'] << 2])
        ok = got == want and (fwv is None or got == fwv)
        mism += not ok
        if get(pwrok_pin) != b['PWR']:
            fail('%s: PWR_OK (GP%d) does not follow the console sense' % (b, P['PWROK']))
        print('%-4d %-6d %-6d %-4d | %-6d | %-5d %-5d %-6d %-7d | %d %d   %s%s' % (
            b['MRD'], b['DRIVE'], b['CLAIM'], b['PWR'], get(pwrok_pin), o1, o2, got[0], got[1], want[0], want[1],
            '-' if fwv is None else '%d %d' % fwv, '' if ok else '   MISMATCH'))
        if not ok:
            fail('%s: netlist (drive, cartcs) %s, spec %s, s2_cart.h %s' % (b, got, want, fwv))
    if fw:
        n_drive = sum(1 for k in range(8) if fw[0][k] == int(not (k & 1) and not (k & 2) and bool(k & 4)))
        n_cs = sum(1 for k in range(8) if fw[1][k] == int(not ((k & 1) or (k & 2)) and bool(k & 4)))
        print('s2_glue_drive: %d / 8 combinations as specified; s2_glue_cartcs: %d / 8' % (n_drive, n_cs))
        if n_drive != 8 or n_cs != 8:
            fail('s2_cart.h glue differs from the written-out equations')
    # the RP unpowered or booting: its pins float, the pull-ups hold /DRIVE and /CLAIM high
    for k in ('DRIVE', 'CLAIM'):
        n = inputs[k]
        pu = [r for r, (val, _) in N.parts.items() if re.match(r'R\d+$', r) and {N.net(r, 1), N.net(r, 2)} == {n, v5}]
        if len(pu) != 1:
            fail('/%s has no pull-up to the glue supply %s' % (k, v5))
    quiet = 0
    for v in range(4):
        get = evaluate({inputs['MRD']: v & 1, inputs['PWR']: v >> 1, inputs['DRIVE']: 1, inputs['CLAIM']: 1})
        quiet += not (get(oe1) == 0 and get(oe2) == 0 or get(cartcs))
    if quiet != 4:
        fail('the RP unpowered: the cart is not silent in every /MRD / console state')
    off = 0
    for v in range(8):
        get = evaluate({inputs['MRD']: v & 1, inputs['DRIVE']: (v >> 1) & 1, inputs['CLAIM']: v >> 2, inputs['PWR']: 0})
        off += not (get(oe1) == 0 and get(oe2) == 0 or get(cartcs))
    if off != 8:
        fail('the console off: the cart drives D0-D7 or CART CS for some RP state')
    print('glue: %d input combinations, %d mismatches against %s' %
          (1 << len(NAMES), mism, 's2_glue_drive() / s2_glue_cartcs() (compiled) and the spec equations' if fw
           else 'the spec equations'))
    print('RP unpowered (/DRIVE, /CLAIM pulled high): D0-D7 released and CART CS low in %d / 4 /MRD x console '
          'states' % quiet)
    print('console off (PWR_OK low), RP on USB: D0-D7 released and CART CS low in %d / 8 /MRD x /DRIVE x /CLAIM '
          'states' % off)
    print('%d gates in use in %d packages, %d unused gates tied off' % (len(gates), len({g[0] for g in gates}), len(unused)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
