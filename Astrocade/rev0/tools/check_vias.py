#!/usr/bin/env python3
"""Gate: no via may touch an SMD pad or a track of another net.

KiCad's DRC cannot catch this: on load it re-assigns a via that sits inside a
pad to that pad's net, so a GND stitching via dropped into a +3V3_RP pad shows
up as a +3V3_RP via and passes.  The same goes for a via on a track: three GND
stitching vias sat on USB_DP, CD7 and +3V3 tracks, and the zip plotted from
the stale saved fills put them inside the In1 GND pour (found 2026-10-11, removed).
This checks the board file's own nets, so it must run before any pcbnew save.

Usage: python3 tools/check_vias.py [board]      exit 1 on any hit
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, find
import gen_pcb as G

PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else G.PCB
b = parse(open(PCB).read())
pads, _ = G.board_pads(b)
segs = [(float(find(e, 'start')[1]), float(find(e, 'start')[2]), float(find(e, 'end')[1]), float(find(e, 'end')[2]),
         float(find(e, 'width')[1]), str(find(e, 'net')[1]), str(find(e, 'layer')[1]))
        for e in b if isinstance(e, list) and e and e[0] == 'segment']
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
    for s in segs:
        if s[5] == net:
            continue
        x0, y0, x1, y1, w = s[:5]
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy
        u = 0 if ll == 0 else max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / ll))
        if ((x0 + u * dx - x) ** 2 + (y0 + u * dy - y) ** 2) ** 0.5 < r + w / 2:
            bad += 1
            print('FAIL: via %s at (%.3f, %.3f) touches a %s track on %s' % (net, x, y, s[5], s[6]))
print('%d vias checked against SMD pads and tracks of other nets, %d failures' % (n, bad))
sys.exit(1 if bad else 0)
