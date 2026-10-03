#!/usr/bin/env python3
"""Gate: no via may touch an SMD pad of another net.

KiCad's DRC cannot catch this: on load it re-assigns a via that sits inside a
pad to that pad's net, so a GND stitching via dropped into a +3V3_RP pad shows
up as a +3V3_RP via and passes.  This checks the board file's own nets.

Usage: python3 tools/check_vias.py [board]      exit 1 on any hit
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, find
import gen_pcb as G

PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else G.PCB
b = parse(open(PCB).read())
pads, _ = G.board_pads(b)
bad = 0
n = 0
for e in b:
    if not (isinstance(e, list) and e and e[0] == 'via'):
        continue
    n += 1
    x, y = float(find(e, 'at')[1]), float(find(e, 'at')[2])
    r = float(find(e, 'size')[1]) / 2
    net = str(find(e, 'net')[1])
    for p in pads:
        if p.th or p.net in (None, net):
            continue
        dx = max(abs(x - p.cx) - p.hw, 0)
        dy = max(abs(y - p.cy) - p.hh, 0)
        if (dx * dx + dy * dy) ** 0.5 < r:
            bad += 1
            print('FAIL: via %s at (%.3f, %.3f) touches %s.%s (%s)' % (net, x, y, p.ref, p.num, p.net))
print('%d vias checked against SMD pads of other nets, %d failures' % (n, bad))
sys.exit(1 if bad else 0)
