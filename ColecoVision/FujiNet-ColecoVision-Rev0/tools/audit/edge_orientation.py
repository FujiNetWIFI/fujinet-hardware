#!/usr/bin/env python3
"""The ColecoVision edge against its sources: the footprint (FujiNet-ColecoVision.pretty/
Coleco_Cart_Edge_30) and design.EDGE (the netlist) against the published pinout and two built, open
carts.

Sources (copied here by hand on 2026-11-04, not imported, so a slip in design.py or edge_geom.py shows):
  MAME     src/devices/bus/coleco/cartridge/exp.h, the slot's pin table (= the Coleco ADAM Technical
           Reference Manual's cartridge connector J1, CS1*-CS4* = /8000 /A000 /C000 /E000).  If a MAME
           tree is at $MAME (default ~/Workspace/mame), its comment is parsed too and must agree.
  TON      ThatOldNerd, Coleco-Game-Cart V4 (GPL-3.0), "Coleco Cart V4.brd": the CART package (pad, x from
           the board centre, layer 1 = top / 16 = bottom, signal).  CS1-CS4 = /8000 /A000 /C000 /E000,
           VCC = +5V; pin 13 on GND.  Dimensions and names only.
  CB       Commodore-Bench, ColecoVision Reprogrammable Flash Card (MIT), KiCAD/Coleco-Card3.kicad_pcb: the
           Coleco_Expansion_Card footprint (pad, x, layer, net).  ~FCE0-3 = /8000 /A000 /C000 /E000;
           pin 13 unconnected.
Checks:
  1. every source agrees with design.EDGE on every pin (names translated to MAME's)
  2. the footprint: 30 lands, the even pins on F.Cu and the odd pins on B.Cu, each odd pin directly
     behind the even pin above it, pins 1 / 2 at the left seen from F.Cu, edge_geom.PITCH along each
     row -- the arrangement both built boards have (even pins on their top copper, pin 2 at the left
     seen from the top, pin 1 behind it)
  3. power and ground: +5V on 30, GND on 29, SHLD (13) on GND as ThatOldNerd has it
Not a check (README "Original shell"): the inside of an original shell, and which face carries the
label.

Usage: python3 tools/audit/edge_orientation.py          exit 1 on any failure
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D
import edge_geom as EG
from sexpr import parse, find, findall

MAME = {'1': 'D2', '2': '/C000', '3': 'D1', '4': 'D3', '5': 'D0', '6': 'D4', '7': 'A0', '8': 'D5', '9': 'A1',
        '10': 'D6', '11': 'A2', '12': 'D7', '13': 'SHLD', '14': 'A11', '15': 'A3', '16': 'A10', '17': 'A4',
        '18': '/8000', '19': 'A13', '20': 'A14', '21': 'A5', '22': '/A000', '23': 'A6', '24': 'A12', '25': 'A7',
        '26': 'A9', '27': '/E000', '28': 'A8', '29': 'GND', '30': '+5V'}
# ThatOldNerd: (x from the board centre seen from the top, layer, signal)
_TON_SIG = {'1': 'D2', '2': 'CS3', '3': 'D1', '4': 'D3', '5': 'D0', '6': 'D4', '7': 'A0', '8': 'D5', '9': 'A1',
            '10': 'D6', '11': 'A2', '12': 'D7', '13': 'GND', '14': 'A11', '15': 'A3', '16': 'A10', '17': 'A4',
            '18': 'CS1', '19': 'A13', '20': 'A14', '21': 'A5', '22': 'CS2', '23': 'A6', '24': 'A12', '25': 'A7',
            '26': 'A9', '27': 'CS4', '28': 'A8', '29': 'GND', '30': 'VCC'}
TON = {p: (round(-17.975 + 2.54 * ((int(p) - 1) // 2), 3), 'T' if int(p) % 2 == 0 else 'B', s)
       for p, s in _TON_SIG.items()}
# Commodore-Bench: (x from the footprint centre seen from F.Cu, layer, net)
_CB_NET = {'1': '/D2', '2': '/~FCE2', '3': '/D1', '4': '/D3', '5': '/D0', '6': '/D4', '7': '/A0', '8': '/D5',
           '9': '/A1', '10': '/D6', '11': '/A2', '12': '/D7', '13': None, '14': '/A11', '15': '/A3', '16': '/A10',
           '17': '/A4', '18': '/~FCE0', '19': '/A13', '20': '/A14', '21': '/A5', '22': '/~FCE1', '23': '/A6',
           '24': '/A12', '25': '/A7', '26': '/A9', '27': '/~FCE3', '28': '/A8', '29': 'GND', '30': '+5V'}
CB = {p: (round(-17.78 + 2.54 * ((int(p) - 1) // 2), 3), 'F' if int(p) % 2 == 0 else 'B', n) for p, n in _CB_NET.items()}

TO_MAME = {
    'TON': {'CS1': '/8000', 'CS2': '/A000', 'CS3': '/C000', 'CS4': '/E000', 'VCC': '+5V'},
    'CB': {'/~FCE0': '/8000', '/~FCE1': '/A000', '/~FCE2': '/C000', '/~FCE3': '/E000', None: 'SHLD'},
}

fails = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        fails.append(msg)


def mame_tree():
    """The pin table in a local MAME tree's exp.h comment, if there is one."""
    fn = os.path.join(os.environ.get('MAME', os.path.expanduser('~/Workspace/mame')),
                      'src/devices/bus/coleco/cartridge/exp.h')
    if not os.path.exists(fn):
        return None
    out = {}
    for m in re.finditer(r'^\s+(\S+)\s+(\d+)\s+(\d+)\s+(\S+)\s*$', open(fn).read(), re.M):
        out[m.group(2)], out[m.group(3)] = m.group(1), m.group(4)
    return out


def main():
    # 1. the sources against design.EDGE
    mine = {p: nm for p, (net, nm) in D.EDGE.items()}
    norm = lambda s: {'~{8000}': '/8000', '~{A000}': '/A000', '~{C000}': '/C000', '~{E000}': '/E000'}.get(s, s)
    tree = mame_tree()
    if tree is None:
        print('note  no MAME tree: the hand copy of exp.h stands alone')
    else:
        check(tree == MAME, 'MAME exp.h (local tree) = the hand copy, all 30 pins')
    for p in sorted(MAME, key=int):
        want = MAME[p]
        check(norm(mine[p]) == want, 'design.EDGE pin %s %s = MAME %s' % (p, mine[p], want))
        net = D.EDGE[p][0]
        if want in ('GND', 'SHLD'):
            check(net == 'GND', 'pin %s (%s) on GND' % (p, want))
        elif want == '+5V':
            check(net == 'CONS_5V', 'pin 30 (+5V) on CONS_5V')
        for src, tab in (('TON', TON), ('CB', CB)):
            got = tab[p][2]
            got = TO_MAME[src].get(got, got)
            got = got.lstrip('/') if src == 'CB' and got not in MAME.values() else got
            ok = got == want or (want == 'SHLD' and got in ('GND', 'SHLD'))
            check(ok, '%s pin %s = %s (MAME %s)' % (src, p, tab[p][2], want))
    # 2. the footprint
    fp = parse(open(os.path.join(PRJ, D.LIB + '.pretty', 'Coleco_Cart_Edge_30.kicad_mod')).read())
    lands = {}
    for pd in findall(fp, 'pad'):
        sz = find(pd, 'size')
        if float(sz[1]) < 1.0:
            continue                                  # the masked necks
        a = find(pd, 'at')
        layer = str(find(pd, 'layers')[1]).split('.')[0]
        lands[str(pd[1])] = (float(a[1]), float(a[2]), layer, float(sz[1]), float(sz[2]))
    check(sorted(lands, key=int) == [str(i) for i in range(1, 31)], 'footprint: 30 lands, pins 1-30')
    for p, (x, y, layer, w, h) in lands.items():
        want = 'F' if int(p) % 2 == 0 else 'B'
        check(layer == want, 'pin %s on %s.Cu (%s: even = the component face)' % (p, layer, want))
    for k in range(15):
        o, e = str(2 * k + 1), str(2 * k + 2)
        check(abs(lands[o][0] - lands[e][0]) < 1e-3, 'pin %s directly behind pin %s' % (o, e))
        for src, tab in (('TON', TON), ('CB', CB)):
            check(abs(tab[o][0] - tab[e][0]) < 1e-3, '%s: pin %s behind pin %s' % (src, o, e))
    xs = [lands[str(2 * k + 2)][0] for k in range(15)]
    check(all(abs((b - a) - EG.PITCH) < 1e-3 for a, b in zip(xs, xs[1:])), 'pitch %.2f mm along the row' % EG.PITCH)
    check(xs[0] < 0 < xs[-1], 'pins 1 / 2 at the left seen from F.Cu (x %.2f), 29 / 30 at the right' % xs[0])
    for src, tab in (('TON', TON), ('CB', CB)):
        check(tab['2'][0] < 0 < tab['30'][0] and tab['2'][1] in ('T', 'F') and tab['1'][1] == 'B',
              '%s: pin 2 at the left on the top copper, pin 1 behind it' % src)
        sx = [tab[str(2 * k + 2)][0] for k in range(15)]
        check(all(abs((b - a) - 2.54) < 1e-3 for a, b in zip(sx, sx[1:])), '%s: 2.54 mm pitch' % src)
    lo = min(y for x, y, *_ in lands.values())
    check(abs(-lo - (EG.LAND_Y0 + EG.LAND_Y1) / 2) < 3.0, 'lands sit at the insertion edge (y up to %.2f)' % -lo)
    check(EG.land_y0('30') > EG.LAND_Y0, '+5V (30) starts %.1f mm in: GND mates first' % EG.land_y0('30'))
    print('%d failed' % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
