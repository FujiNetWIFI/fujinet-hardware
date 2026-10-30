#!/usr/bin/env python3
"""The Odyssey 2 / Videopac edge against its sources: the footprint (FujiNet-O2.pretty/
Videopac_Cart_Edge_30) and design.EDGE (the netlist) against the published pinout and three built,
working carts.

Sources (copied here by hand on 2026-10-30, not imported, so a slip in design.py or edge_geom.py shows):
  BORIS    Dan Boris, "Odyssey 2 Technical Specs" v1.1 section 2.0 (atarihq.com/danb/files/o2doc.pdf):
           "Top Row: A B C D E F G H J K L M N P R / Bottom Row: 1 .. 15", A ~WR, B / C GND, D +5V,
           E external RAM enable, F ~PSEN, G-M A0-A5, P A6, N A7, R A8; 1 T0, 2-9 D0-D7, 10 A10,
           11 P14, 12 P11, 13 P10, 14 A11, 15 A9.
  BWACK    bwack, Videopac_USBCART (LGPL-3.0), KiCad/videopac-usbcart-kicad5.kicad_pcb: the edge
           footprint placed in the board (pad, x, layer, net).  His net names: 11 "CS" = P14, 12 "A12"
           = P11, 13 "A13" = P10 (the bank lines as address bits), E "#CS".
  PICOPAC  aotta, PicoPAC, Kicad/PicoPAC.kicad_pcb: the same footprint and outline as bwack's, its own
           nets (12 "A12" and 13 "A13" go to GP12 / GP13, which picopac_cart.c calls P11_PIN /
           P10_PIN; 11 "CS" = CS_PIN = P14; E "~{CS}" = NOTCS_PIN).  Dimensions and names only: no licence.
  WILCO    wilco2009, Videopac-micro-SD-Cart v2.2 (GPL-3.0), Eagle "... 2.2 - alt.brd": element U$1
           (pad, x, layer 1 = top / 16 = bottom, signal); 3.96 mm pitch.  B goes to a jumper (N$7).
Checks:
  1. every source agrees with design.EDGE on every pin (names translated to Boris's)
  2. the footprint: 30 lands, 1..15 on F.Cu and A..R on B.Cu, each letter directly behind its number,
     pin 1 / A at the left seen from F.Cu, edge_geom.PITCH along each row -- the arrangement all
     three built boards have (1..15 on their top layer, pin 1 at the left seen from the top, A behind 1)
  3. power and ground: +5V on D, GND on C; B pulled down (GND on a G7000; Boris lists it as GND)
Not a check (README "Edge connector"): the exact pitch of an original cart (bwack / PicoPAC 3.9286,
Gust 3.937, wilco 3.96: all play) and which face of an original cart carries its label.

Usage: python3 tools/audit/edge_orientation.py          exit 1 on any failure
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D
import edge_geom as EG
from sexpr import parse, find, findall

BORIS = {'A': '/WR', 'B': 'GND', 'C': 'GND', 'D': '+5V', 'E': 'E', 'F': '/PSEN', 'G': 'A0', 'H': 'A1',
         'J': 'A2', 'K': 'A3', 'L': 'A4', 'M': 'A5', 'P': 'A6', 'N': 'A7', 'R': 'A8',
         '1': 'T0', '2': 'D0', '3': 'D1', '4': 'D2', '5': 'D3', '6': 'D4', '7': 'D5', '8': 'D6', '9': 'D7',
         '10': 'A10', '11': 'P14', '12': 'P11', '13': 'P10', '14': 'A11', '15': 'A9'}
# (x from the footprint centre seen from F.Cu, layer, net)
BWACK = {'1': (-27.5, 'F', 'T0'), '2': (-23.571, 'F', 'D0'), '3': (-19.643, 'F', 'D1'), '4': (-15.714, 'F', 'D2'),
         '5': (-11.786, 'F', 'D3'), '6': (-7.857, 'F', 'D4'), '7': (-3.929, 'F', 'D5'), '8': (0.0, 'F', 'D6'),
         '9': (3.929, 'F', 'D7'), '10': (7.857, 'F', 'A10'), '11': (11.786, 'F', 'CS'), '12': (15.714, 'F', 'A12'),
         '13': (19.643, 'F', 'A13'), '14': (23.571, 'F', 'A11'), '15': (27.5, 'F', 'A9'),
         'A': (-27.5, 'B', '#WR'), 'B': (-23.571, 'B', 'GND'), 'C': (-19.643, 'B', 'GND'), 'D': (-15.714, 'B', '5V_CART'),
         'E': (-11.786, 'B', '#CS'), 'F': (-7.857, 'B', '#PSEN'), 'G': (-3.929, 'B', 'A0'), 'H': (0.0, 'B', 'A1'),
         'J': (3.929, 'B', 'A2'), 'K': (7.857, 'B', 'A3'), 'L': (11.786, 'B', 'A4'), 'M': (15.714, 'B', 'A5'),
         'N': (19.643, 'B', 'A7'), 'P': (23.571, 'B', 'A6'), 'R': (27.5, 'B', 'A8')}
PICOPAC = {'1': 'T0', '2': 'D0', '3': 'D1', '4': 'D2', '5': 'D3', '6': 'D4', '7': 'D5', '8': 'D6', '9': 'D7',
           '10': 'A10', '11': 'CS', '12': 'A12', '13': 'A13', '14': 'A11', '15': 'A9',
           'A': '~{WR}', 'B': 'GND', 'C': 'GND', 'D': '+5V', 'E': '~{CS}', 'F': '~{PSEN}', 'G': 'A0', 'H': 'A1',
           'J': 'A2', 'K': 'A3', 'L': 'A4', 'M': 'A5', 'N': 'A7', 'P': 'A6', 'R': 'A8'}
WILCO = {'1': (-27.683, 'T', 'T0'), '2': (-23.723, 'T', 'BUSD0'), '3': (-19.763, 'T', 'BUSD1'),
         '4': (-15.803, 'T', 'BUSD2'), '5': (-11.843, 'T', 'BUSD3'), '6': (-7.883, 'T', 'BUSD4'),
         '7': (-3.923, 'T', 'BUSD5'), '8': (0.037, 'T', 'BUSD6'), '9': (3.997, 'T', 'BUSD7'),
         '10': (7.957, 'T', 'BUSA10'), '11': (11.917, 'T', 'P14'), '12': (15.877, 'T', 'P11'),
         '13': (19.837, 'T', 'P10'), '14': (23.797, 'T', 'BUSA11'), '15': (27.757, 'T', 'BUSA9'),
         'A': (-27.683, 'B', '/BUSWR'), 'B': (-23.723, 'B', 'N$7'), 'C': (-19.763, 'B', 'GND'),
         'D': (-15.803, 'B', 'VCC'), 'E': (-11.843, 'B', 'EXTRAM'), 'F': (-7.883, 'B', '/PSEN'),
         'G': (-3.923, 'B', 'BUSA0'), 'H': (0.037, 'B', 'BUSA1'), 'J': (3.997, 'B', 'BUSA2'),
         'K': (7.957, 'B', 'BUSA3'), 'L': (11.917, 'B', 'BUSA4'), 'M': (15.877, 'B', 'BUSA5'),
         'N': (19.837, 'B', 'BUSA7'), 'P': (23.797, 'B', 'BUSA6'), 'R': (27.757, 'B', 'BUSA8')}

# each source's names -> Boris's
_COMMON = {'CS': 'P14', 'A12': 'P11', 'A13': 'P10'}
TO_BORIS = {
    'BWACK': dict(_COMMON, **{'#WR': '/WR', '5V_CART': '+5V', '#CS': 'E', '#PSEN': '/PSEN'}),
    'PICOPAC': dict(_COMMON, **{'~{WR}': '/WR', '~{CS}': 'E', '~{PSEN}': '/PSEN'}),
    'WILCO': {'/BUSWR': '/WR', 'VCC': '+5V', 'EXTRAM': 'E', 'N$7': 'B (jumper)'},
}

fails = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        fails.append(msg)


def board_name(net):
    """design.EDGE net -> Boris's signal name."""
    special = {'CONS_5V': '+5V', 'GND': 'GND', 'WR_N': '/WR', 'PSEN_N': '/PSEN', 'EXTRAM': 'E', 'T0': 'T0',
               'VPB': 'B'}
    if net in special:
        return special[net]
    return net[1:] if net[:2] in ('CA', 'CD', 'CP') else net


def boris_of(src, name):
    n = TO_BORIS[src].get(name, name)
    return n[3:] if n.startswith('BUS') else n


def main():
    # 1. the sources against design.EDGE
    pins = sorted(D.EDGE, key=EG.PINS.index)
    check(pins == EG.PINS, '1. design.EDGE has the 30 Videopac contacts 1-15, A-R')
    ours = {p: board_name(D.EDGE[p][0]) for p in pins}
    bad = [p for p in pins if not (ours[p] == BORIS[p] or (p == 'B' and ours[p] == 'B'))]
    check(not bad, '1. Boris = design.EDGE on all 30 pins (B: GND on a G7000, pulled down here)%s'
          % (' -- differ: %s' % bad if bad else ''))
    for src, tab in (('BWACK', {p: v[2] for p, v in BWACK.items()}), ('PICOPAC', PICOPAC),
                     ('WILCO', {p: v[2] for p, v in WILCO.items()})):
        bad = [p for p in pins if p != 'B' and boris_of(src, tab[p]) != ours[p]]
        check(not bad, '1. %s\'s nets = design.EDGE on the 29 signal and power pins%s'
              % (src, ' -- differ: %s' % bad if bad else ''))
    check(ours['N'] == 'A7' and ours['P'] == 'A6', '1. N = A7, P = A6 (Boris and all three boards; MAME slot.h has them swapped)')
    # 2. the footprint
    fp = parse(open(os.path.join(PRJ, D.LIB + '.pretty', 'Videopac_Cart_Edge_30.kicad_mod')).read())
    lands = {}
    for pd in findall(fp, 'pad'):
        sz = find(pd, 'size')
        if abs(float(sz[1]) - EG.LAND_W) > 1e-6:
            continue                                    # the neck
        a = find(pd, 'at')
        lands[str(pd[1])] = (float(a[1]), float(a[2]), str(find(pd, 'layers')[1]))
    check(sorted(lands, key=EG.PINS.index) == EG.PINS, '2. footprint: one land per pin 1-15, A-R (%d)' % len(lands))
    check(all(lands[p][2] == 'F.Cu' for p in EG.ROW_F) and all(lands[p][2] == 'B.Cu' for p in EG.ROW_B),
          '2. 1-15 on F.Cu (the parts face), A-R on B.Cu (as the top / bottom layers of all three boards)')
    check(all(abs(lands[f][0] - lands[b][0]) < 1e-6 for f, b in zip(EG.ROW_F, EG.ROW_B)),
          '2. each letter directly behind its number (A behind 1 ... R behind 15)')
    xs = [lands[p][0] for p in EG.ROW_F]
    steps = [b - a for a, b in zip(xs, xs[1:])]
    check(all(abs(st - EG.PITCH) < 2e-4 for st in steps) and xs[0] < 0,
          '2. %.4f mm pitch, pin 1 at the LEFT seen from F.Cu' % EG.PITCH)
    for src, tab in (('BWACK', BWACK), ('WILCO', WILCO)):
        same_side = all((tab[p][1] in ('F', 'T')) == (p in EG.ROW_F) for p in EG.PINS)
        order = all((tab[p][0] < 0) == (lands[p][0] < 0) for p in EG.PINS if abs(tab[p][0]) > 1)
        dev = max(abs(tab[p][0] - lands[p][0]) for p in EG.PINS)
        check(same_side and order, '2. %s: the same faces and the same order along the rows (largest x '
              'difference %.2f mm, inside half a %.1f mm finger)' % (src, dev, EG.LAND_W))
        check(dev < EG.LAND_W / 2, '2. %s: every finger within %.2f mm of ours' % (src, EG.LAND_W / 2))
    # 3. power and ground
    check(D.EDGE['D'][0] == 'CONS_5V' and D.EDGE['C'][0] == 'GND',
          '3. +5V on D (the 4th from the pin-A end, B.Cu), GND on C')
    check(D.EDGE['B'][0] == 'VPB', '3. B (GND on a G7000, the video-mixer input on a Videopac+): its own net, '
          'pulled down, never tied to a rail')
    print('edge_geom.VERIFIED = %s' % EG.VERIFIED)
    print('%d failures' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
