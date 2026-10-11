#!/usr/bin/env python3
"""Check FujiNet-ChannelF.pretty/ChannelF_Videocart_Edge_22.kicad_mod, tools/edge_geom.py and
tools/design.py EDGE against the sources for the Fairchild Channel F Videocart edge (collected and
measured 2026-10-10; the numbers below are transcribed from the files, which are not vendored):

  [1] aotta/PicoVideocart (KiCad 8, shown working on a SABA Videoplay), fab gerbers
      GERBER-PiChannelF.zip (2024-08-02): fingers on F.Cu (CuTop), each a 1.9 x 8.1 mm rect at
      y 151.925 plus a 1.9 x 1.53 pad at 147.025, the insertion edge at y 156.525 -> copper 0.55 to
      10.27 mm in; finger x below; the key slot 97.989..99.640 to 12.58 mm in with a lead-in
      95.576..101.672 at the edge; the tab 64.544..132.914 at the edge; the body x 60..137 from
      34.525 mm in; holes at x 65 / 132, 37.525 / 116.1 mm in (5.0 mm in the fab gerbers, 5.6 in
      the later PiChannelF.kicad_pcb).  Its footprint numbers pads in reverse (pad n = J5 pin
      23-n: pad 1 is +12V, pad 22 GND); the nets on the pads name the signals.
  [2] timtashpulatov/fart Cart_Conn.kicad_mod (KiCad 5): 22 pads 1.524 x 12, J5 numbering, pad 1
      at local x +3.81, pads 1..11 every -2.54, pad 12 at -31.75 (10.16 past pad 11), pads 12..22
      every -2.54; placed on B.Cu (fart.kicad_pcb, rotation 0) with the tab edge NORTH, so seen
      from the parts side pad 1 is east with the edge north = west with the edge south.  Slot
      150.114..152.146 (2.03 wide), centred 151.13 = midway between pads 11 and 12; tab 68.58.
  [3] US 4,095,791 (Fairchild): the contacts are "formed in parallel along the bottom surface";
      the console's alignment key enters the slot.  channelf.se veswiki 'Pinouts': the photo of a
      real cart's contact face, pin 1 at the left with the edge up (= at the right seen from the
      other face with the edge up = at the LEFT seen from the other face with the edge down).
  Pin functions: Fairchild FVE100 schematic 06-9002-00 (J5) and the veswiki pinout (design.py
  EDGE; check_nets.py checks the firmware side).

The checks: 22 pads on B.Cu at the edge_geom.pin_x positions, pin 1 at -x (west, seen from F.Cu
with the fingers down); the signal order across the edge equal to [1] mirrored and [2] (by net
name); every finger within [1]'s and [2]'s tolerance of the position; the slot centred between
pins 11 and 12; the copper span inside what the sources share; the tab, body and hole numbers."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import edge_geom as EG
import design as D

fails = []


def check(cond, msg):
    print(('OK   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


t = open(os.path.join(PRJ, 'FujiNet-ChannelF.pretty', 'ChannelF_Videocart_Edge_22.kicad_mod')).read()
pads = {}
for m in re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+) ([-\d.]+)\)\s*'
                     r'\(layers "([FB])\.Cu"\)', t):
    pads[int(m.group(1))] = (float(m.group(2)), -float(m.group(3)), float(m.group(4)), float(m.group(5)),
                             m.group(6))
check(sorted(pads) == list(range(1, 23)), 'footprint: 22 pads numbered 1-22 (%d found)' % len(pads))
check(all(p[4] == 'B' for p in pads.values()), 'every finger on B.Cu (the face down in the console)')
check(all(abs(pads[n][0] - EG.pin_x(n)) < 1e-6 for n in pads), 'pads at edge_geom.pin_x')
check(pads[1][0] < 0 < pads[22][0], 'pin 1 west (-x), pin 22 east, seen from F.Cu with the fingers down')
check(all(pads[n + 1][0] > pads[n][0] for n in range(1, 22)), 'pins 1..22 run west to east')
pitch = sorted(round(pads[n + 1][0] - pads[n][0], 3) for n in range(1, 22))
check(pitch.count(2.54) == 20 and pitch[-1] == round(EG.GAP * 2.54, 3), '2.54 mm pitch, one %g mm gap (11-12)'
      % (EG.GAP * 2.54))

# ---- [1] aotta: F.Cu fingers, its pad n = J5 pin 23-n; x seen from ITS top (the finger face) -----------
AOTTA_X = {1: 68.244, 2: 70.814, 3: 73.384, 4: 75.954, 5: 78.524, 6: 81.075, 7: 83.664, 8: 86.234, 9: 88.804,
           10: 91.374, 11: 93.844, 12: 104.0, 13: 106.57, 14: 109.14, 15: 111.682, 16: 114.299, 17: 116.85,
           18: 119.406, 19: 122.023, 20: 124.56, 21: 127.13, 22: 129.7}
AOTTA_NET = {1: '+12V', 2: 'NC', 3: '+5V', 4: '+5V', 5: 'D7', 6: 'D6', 7: 'D5', 8: 'WRITE', 9: 'D4', 10: 'PHI',
             11: 'ROMC4', 12: 'D3', 13: 'ROMC3', 14: 'D2', 15: 'ROMC2', 16: 'ROMC1', 17: 'ROMC0', 18: '~{INTREQ}',
             19: 'D1', 20: 'D0', 21: 'GND', 22: 'GND'}
AOTTA_SLOT = (97.989, 99.640)       # at its top, 12.58 mm in
AOTTA_EDGE_Y, AOTTA_SLOT_TOP = 156.525, 143.945
AOTTA_COPPER = (0.55, 10.27)        # mm in from the edge
AOTTA_TAB = (64.544, 132.914)
AOTTA_BODY = (60.0, 137.0, 34.525)  # x0, x1, mm in
AOTTA_HOLES = [(65.0, 37.525), (132.0, 37.525), (65.0, 116.1), (132.0, 116.1)]
# ---- [2] fart: B.Cu, J5 numbering, local x on the parts-side view with the edge NORTH ---------------
FART_LOCAL = {n: 3.81 - 2.54 * (n - 1) for n in range(1, 12)}
FART_LOCAL.update({n: -31.75 - 2.54 * (n - 12) for n in range(12, 23)})
FART_NET = {1: 'GND', 2: 'GND', 3: 'D0', 4: 'D1', 5: '~INTREQ', 6: 'ROMC0', 7: 'ROMC1', 8: 'ROMC2', 9: 'D2',
            10: 'ROMC3', 11: 'D3', 12: 'ROMC4', 13: 'PHI', 14: 'D4', 15: 'WRITE', 16: 'D5', 17: 'D6', 18: 'D7',
            19: '+5V', 20: '+5V', 21: 'NC', 22: '+12V'}
FART_SLOT = (150.114, 152.146)
FART_AT_X = 177.8
FART_COPPER = (0.99, 12.99)
FART_TAB_W = 185.42 - 116.84

canon = lambda n: {'~{INTREQ}': 'INTREQ_N', '~INTREQ': 'INTREQ_N', '+5V': 'CONS_5V', 'NC': None,
                   '+12V': None}.get(n, n)
ours = {p: D.EDGE[p] for p in range(1, 23)}

# [1] mirrored onto the parts-side view (x' = c - x), renumbered to J5 (pin = 23 - pad)
c1 = (AOTTA_X[11] + AOTTA_X[12]) / 2
a_j5 = {23 - n: (round(c1 - x, 3), canon(AOTTA_NET[n])) for n, x in AOTTA_X.items()}
check([a_j5[p][1] for p in range(1, 23)] == [ours[p] for p in range(1, 23)],
      '[1] aotta: signal order (mirrored, pad n -> J5 23-n) equals design.py EDGE')
dev1 = max(abs(a_j5[p][0] - EG.pin_x(p)) for p in range(1, 23))
check(dev1 < EG.FINGER_W / 2, '[1] aotta: every finger within %.3f mm of ours (< half a finger, %.2f); its pitch '
      'is ~2.565' % (dev1, EG.FINGER_W / 2))
check(abs((AOTTA_SLOT[0] + AOTTA_SLOT[1]) / 2 - c1) < 0.15 and abs(AOTTA_SLOT[1] - AOTTA_SLOT[0] - EG.SLOT_W) < 1e-3
      and abs(AOTTA_EDGE_Y - AOTTA_SLOT_TOP - EG.SLOT_D) < 1e-3,
      '[1] aotta: slot %.3f wide, %.2f deep, %.3f off the 11/12 midpoint'
      % (AOTTA_SLOT[1] - AOTTA_SLOT[0], AOTTA_EDGE_Y - AOTTA_SLOT_TOP, (AOTTA_SLOT[0] + AOTTA_SLOT[1]) / 2 - c1))
# [2] rotated 180 into the edge-south view: x' = -(local)
f_j5 = {n: (round(-x - (-(FART_LOCAL[11] + FART_LOCAL[12]) / 2), 3), canon(FART_NET[n])) for n, x in FART_LOCAL.items()}
check([f_j5[p][1] for p in range(1, 23)] == [ours[p] for p in range(1, 23)], '[2] fart: signal order equals design.py EDGE')
dev2 = max(abs(f_j5[p][0] - EG.pin_x(p)) for p in range(1, 23))
check(dev2 < 1e-6, '[2] fart: finger positions identical (max %.4f mm)' % dev2)
check(abs((FART_SLOT[0] + FART_SLOT[1]) / 2 - (FART_AT_X + (FART_LOCAL[11] + FART_LOCAL[12]) / 2)) < 1e-3,
      '[2] fart: slot centred between pins 11 and 12')
check(f_j5[1][0] < 0 and a_j5[1][0] < 0, '[1] + [2] + [3]: pin 1 (GND) west seen from the parts side, edge south')

# copper span: start no later than both sources, end past the longer one's contact zone
y0 = min(p[1] - p[3] / 2 for p in pads.values()); y1 = max(p[1] + p[3] / 2 for p in pads.values())
check(y0 <= min(AOTTA_COPPER[0], FART_COPPER[0]) + 0.05 and y1 >= AOTTA_COPPER[1],
      'copper %.2f-%.2f mm in (aotta %.2f-%.2f, fart %.2f-%.2f)' % (y0, y1, *AOTTA_COPPER, *FART_COPPER))
check(1.524 <= EG.FINGER_W <= 1.9, 'finger width %.2f between fart 1.524 and aotta 1.9' % EG.FINGER_W)
# the tab, body and holes
aw = AOTTA_TAB[1] - AOTTA_TAB[0]
check(min(aw, FART_TAB_W) - 0.1 <= EG.TAB_W <= max(aw, FART_TAB_W), 'tab %.2f (aotta %.2f, fart %.2f)'
      % (EG.TAB_W, aw, FART_TAB_W))
check(abs(EG.BODY_W - (AOTTA_BODY[1] - AOTTA_BODY[0])) < 1e-6 and abs(EG.BODY_Y0 - AOTTA_BODY[2]) < 0.2,
      'body %.1f wide from %.2f mm in (aotta %.1f from %.3f)' % (EG.BODY_W, EG.BODY_Y0, AOTTA_BODY[1] - AOTTA_BODY[0],
                                                              AOTTA_BODY[2]))
hx = (AOTTA_HOLES[1][0] - AOTTA_HOLES[0][0]) / 2
check(abs(EG.HOLE_DX - hx) < 1e-6 and tuple(EG.HOLE_Y) == (AOTTA_HOLES[0][1], AOTTA_HOLES[2][1]),
      'holes %.1f apart at %.3f / %.1f mm in (aotta); aotta body centre is %.2f off its slot: centred here'
      % (2 * EG.HOLE_DX, *EG.HOLE_Y, (AOTTA_BODY[0] + AOTTA_BODY[1]) / 2 - (AOTTA_SLOT[0] + AOTTA_SLOT[1]) / 2))
check(set(D.EDGE[p] for p in EG.NC_PINS) == {None}, 'pins 21 (spare) and 22 (+12 V) unconnected on this board')
if fails:
    raise SystemExit('edge_orientation: %d FAILED' % len(fails))
print('edge_orientation: all checks passed')
