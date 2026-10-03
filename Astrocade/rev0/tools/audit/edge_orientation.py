#!/usr/bin/env python3
"""Prove the contact-land orientation of the generated board against the
published pinout.

Jay Tilton (ballyalley.com, 'Bally Technical Info (Cartridge Port)'): "Looking
at the cart slot, pins are being numbered here from 1 to 26, left to right."
A Videocade lies label-up and slides AWAY from the viewer into that slot, so the
viewer looking at the slot and the viewer looking down on the cart's label with
its contact edge pointing away from them see the same left/right.  In KiCad's
top view of this board the insertion edge is SOUTH (y = 88), i.e. pointing
toward the viewer: turning the board so that edge points away swaps left and
right.  So land 1 must be EAST in KiCad top view, on B.Cu (the console blade
presses up on the underside), and lands must ascend westward at 2.54 mm.
"""
import os, re, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
from sexpr import parse, find, findall
import gen_pcb as G

b = parse(open(G.PCB).read())
j1 = [e for e in b if isinstance(e, list) and e and e[0] == 'footprint'
      and any(p[1] == 'Reference' and p[2] == 'J1' for p in findall(e, 'property'))][0]
at = find(j1, 'at'); fx, fy = float(at[1]), float(at[2]); rot = float(at[3]) if len(at) > 3 else 0.0
lands = {}
for pd in findall(j1, 'pad'):
    if pd[2] != 'smd':
        continue
    sz = find(pd, 'size')
    if float(sz[2]) < 10:          # the 14 mm land, not its masked neck
        continue
    a = find(pd, 'at')
    dx, dy = G.rot_pt(float(a[1]), float(a[2]), rot)
    lands[int(pd[1])] = (fx + dx, fy + dy, [str(l) for l in find(pd, 'layers')[1:]])
xc = (G.X0 + G.X1) / 2
ok = True
ok &= lands[1][0] > xc and lands[26][0] < xc
ok &= all(abs((lands[n][0] - lands[n + 1][0]) - 2.54) < 1e-3 for n in range(1, 26))
ok &= all(l[2][0] == 'B.Cu' for l in lands.values())
ok &= all(l[1] > G.BLADE_Y for l in lands.values())
print('land 1 at x=%.2f (board centre %.1f), land 26 at x=%.2f; layer %s; pitch 2.54 descending x: %s'
      % (lands[1][0], xc, lands[26][0], lands[1][2][0], 'yes' if ok else 'NO'))
print('RESULT:', 'land 1 EAST on B.Cu = Tilton pin 1 at the left of the slot' if ok else 'MISMATCH')
sys.exit(0 if ok else 1)
