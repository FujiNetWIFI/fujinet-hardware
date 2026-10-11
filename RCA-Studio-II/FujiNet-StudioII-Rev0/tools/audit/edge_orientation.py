#!/usr/bin/env python3
"""Check FujiNet-StudioII.pretty/StudioII_Cart_Edge_22.kicad_mod, tools/edge_geom.py and
tools/design.py EDGE against the sources for the RCA Studio II cartridge edge (read 2026-10-11; the
numbers below are transcribed from the files, which are not vendored):

  [1] FliP (Philip Marien) RCA Studio II multicart v5.1, github.com/vodkaflip/RCA_Studio_II,
      multicart_pcb/rca_studio_II_mutli.brd (Eagle 9.6.2) and GerberFiles.zip (2023-09-20; the job
      file: 2 layers, 1.57 mm, 90.912 x 83.49).  Built, runs in real consoles, fits original shells.
      Package RCA_22PINEDGE, element P1 at (45.72, 0) unrotated on Top: 22 smd 1.905 x 8.255 at
      local x -41.6052 + 3.9624 (n - 1), y 4.826, layer Top (nothing on Bottom in the field; a
      bRestrict 0-12.7 mm).  Its pads' signals (the SST39SF040 IC2, the 4042 IC3, D1): 1-5 DQ7-DQ3,
      6 GND, 7 shorted to 6 by a Top bar, 8-10 DQ2-DQ0, 11-14 A0-A3, 15 VCC, 16-18 A4-A6, 19 the
      4042 (TPA), 20 A7, 21 the flash /OE (/MRD), 22 D1's cathode (CART CS).  Outline (Dimension):
      x 0.254-91.166, straight to 73.33, chamfered to 12.37 / 79.0478 at 83.49; milled circles r
      4.064 at (9.906, 68.58) / (81.28, 68.58) and r 1.8316 at (0, 20.828) / (90.932, 20.828).  An
      Eagle top view looks at Top: seen from the contact face pin 1 is at the LEFT.
  [2] EJK's RCA Studio II console schematic (Rev 1.1, 2012; bitsavers components/rca/cosmac/
      studio_II), CN1: 1-5 D7-D3, 6 ROM DISABLE, 7 GND, 8-10 D2-D0, 11-14 A0-A3, 15 +5, 16-18
      A4-A6, 19 TPA (buffered: gated to reads), 20 A7, 21 /MRD, 22 CART CS; the lettered row of the
      2x22 connector unconnected.  Its edge note: "CART LABEL PIC TO BACK OF CONSOLE".
  [3] cosmacvip.com RCA Tester 1 photos (lg/11.jpg, lg/12.jpg): an original game board, single-
      sided, its copper fingers on the picture-label face; its component side reads "22" at the
      left and "1" at the right, so seen from the contact face pin 1 is at the left.

The checks: 22 pads on B.Cu at edge_geom.pin_x, pin 1 at +x (east) seen from F.Cu with the
fingers down; design.py EDGE equal to [1]'s pad signals and [2]'s pinout pin for pin; every finger
at [1]'s position mirrored; the finger size and copper span, the outline, the holes and notches."""
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


t = open(os.path.join(PRJ, 'FujiNet-StudioII.pretty', 'StudioII_Cart_Edge_22.kicad_mod')).read()
pads = {}
for m in re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+) ([-\d.]+)\)\s*'
                     r'\(layers "([FB])\.Cu"\)', t):
    pads[int(m.group(1))] = (float(m.group(2)), -float(m.group(3)), float(m.group(4)), float(m.group(5)),
                             m.group(6))
check(sorted(pads) == list(range(1, 23)), 'footprint: 22 pads numbered 1-22 (%d found)' % len(pads))
check(EG.FACE == 'B' and all(p[4] == 'B' for p in pads.values()),
      'every finger on B.Cu: the face away from the parts, as on an original cart [3]')
check(all(abs(pads[n][0] - EG.pin_x(n)) < 1e-6 for n in pads), 'pads at edge_geom.pin_x')
check(pads[1][0] > 0 > pads[22][0], 'pin 1 east (+x), pin 22 west, seen from F.Cu with the fingers down')
check(all(pads[n][0] > pads[n + 1][0] for n in range(1, 22)), 'pins 1..22 run east to west seen from F.Cu')
check(all(abs(pads[n][0] - pads[n + 1][0] - 0.156 * 25.4) < 2e-4 for n in range(1, 22)), '0.156" (3.9624 mm) pitch')

# ---- [1] FliP v5.1 ----------------------------------------------------------------------------------
FLIP_P1_X = 45.72
FLIP_LOCAL = {n: -41.6052 + 3.9624 * (n - 1) for n in range(1, 23)}
FLIP_PAD_Y, FLIP_PAD_W, FLIP_PAD_H = 4.826, 1.905, 8.255
FLIP_SIG = {1: 'DQ7', 2: 'DQ6', 3: 'DQ5', 4: 'DQ4', 5: 'DQ3', 6: 'GND', 7: 'GND(bar to 6)', 8: 'DQ2', 9: 'DQ1',
            10: 'DQ0', 11: 'A0', 12: 'A1', 13: 'A2', 14: 'A3', 15: 'VCC', 16: 'A4', 17: 'A5', 18: 'A6',
            19: 'TPA(4042)', 20: 'A7', 21: '/OE', 22: 'CS(D1 cathode)'}
FLIP_OUTLINE = ((0.254, 0.0), (91.166, 0.0), (91.166, 73.33), (79.0478, 83.49), (12.37, 83.49), (0.254, 73.33))
FLIP_HOLES = ((9.906, 68.58, 4.064), (81.28, 68.58, 4.064))
FLIP_NOTCHES = ((0.0, 20.828, 1.8316), (90.932, 20.828, 1.8316))
canon = {'DQ%d' % i: 'D%d' % i for i in range(8)}
canon.update({'A%d' % i: 'MA%d' % i for i in range(8)})
canon.update({'GND': 'GND', 'GND(bar to 6)': 'GND', 'VCC': 'CONS_5V', 'TPA(4042)': 'TPA', '/OE': 'MRD_N',
              'CS(D1 cathode)': 'CART_CS'})
check([canon[FLIP_SIG[p]] for p in range(1, 23)] == [D.EDGE[p][0] for p in range(1, 23)],
      '[1] FliP: the signal on every pad equals design.py EDGE (pin 6 grounded as his, 7 GND)')
xc1 = (FLIP_OUTLINE[0][0] + FLIP_OUTLINE[1][0]) / 2
mirrored = {n: -(FLIP_P1_X + x - xc1) for n, x in FLIP_LOCAL.items()}        # his contact-face view -> our F.Cu view
dev = max(abs(mirrored[n] - EG.pin_x(n)) for n in range(1, 23))
check(dev < 0.02, '[1] FliP: every finger at his position mirrored (max %.4f mm: his field is %.3f off his board '
      'centre)' % (dev, FLIP_P1_X - xc1))
check(FLIP_LOCAL[1] < 0, '[1] FliP: pin 1 at the left seen from his contact face (Top) -> at the right from our F.Cu')
y0 = min(p[1] - p[3] / 2 for p in pads.values()); y1 = max(p[1] + p[3] / 2 for p in pads.values())
check(abs(y0 - (FLIP_PAD_Y - FLIP_PAD_H / 2)) < 0.01 and abs(y1 - (FLIP_PAD_Y + FLIP_PAD_H / 2)) < 0.01
      and all(abs(p[2] - FLIP_PAD_W) < 1e-6 for p in pads.values()),
      '[1] FliP: fingers %.3f wide, copper %.3f-%.3f mm in (his %.4f-%.4f)'
      % (EG.FINGER_W, y0, y1, FLIP_PAD_Y - FLIP_PAD_H / 2, FLIP_PAD_Y + FLIP_PAD_H / 2))
w = FLIP_OUTLINE[1][0] - FLIP_OUTLINE[0][0]
check(abs(EG.BOARD_W - w) < 1e-6 and abs(EG.BOARD_H - FLIP_OUTLINE[3][1]) < 1e-6
      and abs(EG.SIDE_H - FLIP_OUTLINE[2][1]) < 1e-6
      and abs(EG.CH_TOP_W - (FLIP_OUTLINE[1][0] - FLIP_OUTLINE[3][0])) < 0.002
      and abs(EG.CH_TOP_W - (FLIP_OUTLINE[4][0] - FLIP_OUTLINE[0][0])) < 0.002
      and abs(EG.CH_TOP_H - (FLIP_OUTLINE[3][1] - FLIP_OUTLINE[2][1])) < 1e-6,
      '[1] FliP: outline %.3f x %.2f, sides %.2f, top chamfers %.3f x %.2f' % (EG.BOARD_W, EG.BOARD_H, EG.SIDE_H,
                                                                          EG.CH_TOP_W, EG.CH_TOP_H))
ours_h = sorted((round(x, 3), y) for x, y in EG.HOLES)
his_h = sorted((round(-(x - xc1), 3), y) for x, y, r in FLIP_HOLES)
check(ours_h == his_h and abs(EG.HOLE_D - 2 * FLIP_HOLES[0][2]) < 1e-6,
      '[1] FliP: shell-post holes %g mm at %s (his, mirrored)' % (EG.HOLE_D, ours_h))
cuts = [r - (FLIP_OUTLINE[0][0] - x) if x < xc1 else r - (x - FLIP_OUTLINE[1][0]) for x, y, r in FLIP_NOTCHES]
check(abs(EG.NOTCH_R - FLIP_NOTCHES[0][2]) < 1e-6 and abs(EG.NOTCH_R + EG.NOTCH_INSET - max(cuts)) < 1e-3
      and all(abs(EG.NOTCH_Y - y) < 1e-6 for x, y, r in FLIP_NOTCHES),
      '[1] FliP: side notches r %.4f, %.3f mm deep (his %.3f / %.3f: both take the deeper), %.3f mm in'
      % (EG.NOTCH_R, EG.NOTCH_R + EG.NOTCH_INSET, *cuts, EG.NOTCH_Y))
check(abs(EG.THICKNESS - 1.57) <= 0.05, '[1] FliP: board %.2f mm (his 1.57)' % EG.THICKNESS)

# ---- [2] EJK ----------------------------------------------------------------------------------------
EJK = {1: 'D7', 2: 'D6', 3: 'D5', 4: 'D4', 5: 'D3', 6: 'ROM DISABLE', 7: 'GND', 8: 'D2', 9: 'D1', 10: 'D0',
       11: 'A0', 12: 'A1', 13: 'A2', 14: 'A3', 15: '+5', 16: 'A4', 17: 'A5', 18: 'A6', 19: 'TPA', 20: 'A7',
       21: '/MRD', 22: 'CART CS'}
ejk = {'ROM DISABLE': 'GND', '+5': 'CONS_5V', '/MRD': 'MRD_N', 'CART CS': 'CART_CS', 'GND': 'GND', 'TPA': 'TPA'}
ejk.update({'A%d' % i: 'MA%d' % i for i in range(8)})
ejk.update({'D%d' % i: 'D%d' % i for i in range(8)})
check([ejk[EJK[p]] for p in range(1, 23)] == [D.EDGE[p][0] for p in range(1, 23)],
      '[2] EJK: design.py EDGE is the console pinout, ROM DISABLE (6) grounded as a cart does')
# ---- [3] the original board ---------------------------------------------------------------------------
check(EG.FACE == 'B' and EG.pin_x(1) > 0,
      '[3] original board: pin 1 at the left seen from the contacts = at the right seen from the parts side')
if fails:
    raise SystemExit('edge_orientation: %d FAILED' % len(fails))
print('edge_orientation: all checks passed')
