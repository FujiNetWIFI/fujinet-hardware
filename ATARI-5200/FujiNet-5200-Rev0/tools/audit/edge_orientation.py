#!/usr/bin/env python3
"""Check FujiNet-5200.pretty/Atari5200_Cart_Edge_36.kicad_mod against the sources for the Atari
5200 cartridge edge (collected and measured 2026-10-08; edge_geom.py holds the numbers):

  [1] Grand Idea Studio "Pixels Past" 5200 32K cart, rev B gerbers (RS-274X, inch 2.4), traced
      from the fingers to the EPROM: top copper (the label face) carries pins 1-18, pin 1 (D0)
      at x = -21.59 seen from the top with the fingers down, pin 18 (CI1) at +21.59 starts
      1.905 mm in where the others start 0.635; bottom copper pin 36 (CI2) at -21.59, behind
      pin 1, also from 1.905.  Fingers 1.905 wide, to 6.985 mm; tab 48.006, straight to 18.54.
  [2] tdididit a52-cartridge.lbr (Eagle, ATARI-5200-LONG / -SMALL): pad 1 on layer 1 at
      x = -21.59, pad 18 on layer 1 at +21.59 from 1.8415, pad 36 on layer 16 at -21.59 from
      1.8415, pad 19 on layer 16 at +21.59; pads 1.524 wide, 0.5715 -> 7.0485 mm; tab 47.625.
  [3] sanni cartreader, 5200 adapter gerbers: top silk "1" at the left ... "18" at the right,
      "CART TOP"; and the photo of a Galaxian cart seated in it, label up.
  [4] Sullins EBC18DCWN (the substitute for Atari C018081, the console's 18/36 connector):
      slot opening 1.900" (48.26 mm), insertion depth .297" (7.54 mm), board .062" +/- .008".
  Pin functions: Atari CX5200 Field Service Manual Rev 4 (1983), schematics of CA018087,
  CA020108 and CA021374 (tools/design.py EDGE, checked against the firmware by check_nets.py).

The checks: 36 pads, pins 1-18 on F.Cu (this board's component side, the label face), pin
37-k on B.Cu directly behind pin k, pin 1 at -x (west, seen from F.Cu with the fingers
down), 2.54 mm pitch; finger width and copper span inside what the sources share (so the
console contacts land on gold); pins 18 and 36 the short pair, starting where [1] and [2]
start theirs."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import edge_geom as EG

t = open(os.path.join(PRJ, 'FujiNet-5200.pretty', 'Atari5200_Cart_Edge_36.kicad_mod')).read()
pads = {}
for m in re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+) ([-\d.]+)\)\s*'
                     r'\(layers "([FB])\.Cu"\)', t):
    pads[int(m.group(1))] = (float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)),
                             m.group(6))
ok = sorted(pads) == list(range(1, 37))
print('pads: %d (want 36 numbered 1-36): %s' % (len(pads), 'OK' if ok else 'MISMATCH'))
# (width min, width max, copper start max, copper end min, short start min, short start max)
SOURCES = {'Pixels Past rev B [1]': (1.905, 1.905, 0.635, 6.985, 1.905, 1.905),
           'tdididit lbr [2]': (1.524, 1.524, 0.5715, 7.0485, 1.8415, 1.8415)}
W_LO = min(s[0] for s in SOURCES.values())
W_HI = max(s[1] for s in SOURCES.values())
START_MAX = min(s[2] for s in SOURCES.values()) + 0.05   # no later than the earliest source start (+ tolerance)
END_MIN = min(s[3] for s in SOURCES.values())             # at least as far in as the shorter source
SHORT_LO = min(s[4] for s in SOURCES.values()) - 0.1
SHORT_HI = max(s[5] for s in SOURCES.values()) + 0.1


def span(n):
    px, py, pw, ph, pl = pads[n]
    return -py - ph / 2, -py + ph / 2


for n in (1, 2, 17, 18, 19, 20, 35, 36):
    px, py, pw, ph, pl = pads[n]
    y0, y1 = span(n)
    want_l = 'F' if n <= 18 else 'B'
    pos = n if n <= 18 else 37 - n
    want_x = (pos - 9.5) * 2.54
    good = pl == want_l and abs(px - want_x) < 1e-6
    ok &= good
    print('pad %2d: x=%+6.2f %s.Cu, %.2f wide, copper %.2f-%.2f mm from the edge  want x=%+6.2f %s.Cu  %s'
          % (n, px, pl, pw, y0, y1, want_x, want_l, 'OK' if good else 'MISMATCH'))
for k in range(1, 19):
    a, b = pads[k], pads[37 - k]
    good = a[4] == 'F' and b[4] == 'B' and abs(a[0] - b[0]) < 1e-6
    if k < 18:
        good &= abs((pads[k + 1][0] - a[0]) - 2.54) < 1e-6
    if not good:
        print('pin %d / %d: not one 2.54 mm position, F over B: MISMATCH' % (k, 37 - k))
    ok &= good
for n in range(1, 37):
    px, py, pw, ph, pl = pads[n]
    y0, y1 = span(n)
    short = n in (18, 36)
    good = W_LO - 1e-6 <= pw <= W_HI + 1e-6 and y1 >= END_MIN - 1e-6 and (
        SHORT_LO <= y0 <= SHORT_HI if short else y0 <= START_MAX)
    if not good:
        print('pad %d: %.2f wide, copper %.2f-%.2f: outside the sources (width %.3f-%.3f, start <= %.3f%s, '
              'end >= %.3f): MISMATCH' % (n, pw, y0, y1, W_LO, W_HI, START_MAX,
                                          ' / short %.2f-%.2f' % (SHORT_LO, SHORT_HI) if short else '', END_MIN))
    ok &= good
ok &= set(EG.SHORT) == {18, 36}
print('short (interlock, last-make) fingers: %s, from %.2f mm' % (sorted(EG.SHORT), EG.LAND_Y0_SHORT))
print('tab %.1f mm (sources 47.625 / 48.006; console slot 48.26)' % EG.TAB_W)
ok &= 47.6 <= EG.TAB_W <= 48.1
print('edge orientation: %s' % ('OK: pins 1-18 on F.Cu (label face), pin 1 west, pin 37-k behind pin k, '
                                '18 / 36 short' if ok else 'MISMATCH'))
sys.exit(0 if ok else 1)
