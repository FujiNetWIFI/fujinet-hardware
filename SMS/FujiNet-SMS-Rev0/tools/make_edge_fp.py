#!/usr/bin/env python3
"""Write FujiNet-SMS.pretty/SMS_Cart_Edge_50.kicad_mod.

The Sega Master System / SMS2 50-pin cartridge edge: 25 positions per face at
2.54 mm (0.1 in) pitch, odd pins on one face and even pins on the other,
pin 2k-1 directly behind pin 2k (the corrected pin list in design.py).

Face and pin-1 end (every source agrees; tools/audit/edge_orientation.py
records them and re-checks this file):
  * the EVEN pins (2..50) are on the component side, which faces the label
    and the front of the console: SMS Power's slot diagram (front row 50..2,
    back row 49..1, seen from above with the label toward the viewer),
    little-scale's 32K cart build ("the front side has the even numbers ...
    the ROM chip faces upwards"), the component-side silkscreen of an
    original 171-5519 board ("50" left ... "2" right), raphnet's SMS4MBIT
    fab drawing and the barbeque and reidrac KiCad footprints;
  * pin 2 is at the RIGHT (+x, east) seen from the component side with the
    fingers down, so pin 1 (behind it) is at the right seen from the front
    too and at the left seen from the solder side.
This board is assembled on F.Cu only, so F.Cu is the component side: even
pads on F.Cu, odd pads on B.Cu, pins 1/2 east.

Finger geometry (mm, measured / CAD values in the audit script): fingers
1.70-1.76 wide on the original and every open design (1.75 here), copper
from about 0.5-1.25 to 9.5-10.1 above the edge (0.75 -> 9.5 here, inside
every source's contact zone), a full-width connector tab 65.8 wide (the
original board is 66.0 x 40.1, raphnet 65.80, barbeque 65.8), outermost
finger centres 2.42 from the tab sides.  The board outline (1 mm corner
chamfers, the bevel, the shoulders above TAB_D) belongs to gen_pcb.py; this
footprint only marks the tab on the fab and courtyard layers.

Local frame: y=0 is the insertion edge and the board extends in -y, so the
footprint goes on the SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PITCH, N = 2.54, 25
FINGER_W = 1.75                       # original 1.65-1.76, raphnet 1.75, barbeque / reidrac 1.70
LAND_Y0, LAND_Y1 = 0.75, 9.5          # copper, distance in from the edge
TAB_W, TAB_D = 65.8, 15.0             # the connector tab: full board width up to TAB_D (shoulders above)
MASK_Y1 = 10.0                        # one mask opening per face across the finger field
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]


def pos_x(k):
    """Position k (1..25: pins 2k-1 / 2k) centre x: pins 1/2 east."""
    return round((N - 1) * PITCH / 2 - (k - 1) * PITCH, 3)


def rect(layer, y0, y1, w=0.05, fill='no'):
    return ['fp_rect', ['start', -TAB_W / 2, y0], ['end', TAB_W / 2, y1],
            ['stroke', ['width', w], ['type', 'solid']], ['fill', fill], ['layer', Q(layer)]]


fp = ['footprint', Q('SMS_Cart_Edge_50'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Sega Master System 50-pin cartridge edge: 2 x 25 fingers, 2.54 mm pitch.  Even pins on F.Cu '
                  '(component / label side, faces the console front), odd pins on B.Cu, pin 2k-1 behind pin 2k, '
                  'pins 1/2 east seen from F.Cu.  Fingers 1.75 x 8.75 mm, 0.75-9.5 mm from the edge; tab 65.8 mm. '
                  'Hard gold, 30-45 deg bevel.')],
      ['tags', Q('sega master system sms cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(TAB_D + 1.5), 0], ['layer', Q('F.SilkS')], F()],
      ['property', Q('Value'), Q('SMS_Cart_Edge_50'), ['at', 0, -(TAB_D + 3.5), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom', 'allow_soldermask_bridges'],
      rect('F.Fab', 0, -TAB_D, 0.1), rect('F.CrtYd', 0, -TAB_D), rect('B.CrtYd', 0, -TAB_D),
      # one mask opening per face across the finger field (the pads carry no mask layer)
      rect('F.Mask', 0.2, -MASK_Y1, 0, 'yes'), rect('B.Mask', 0.2, -MASK_Y1, 0, 'yes'),
      ['fp_text', 'user', Q('2'), ['at', pos_x(1), -(MASK_Y1 + 1.2), 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('50'), ['at', pos_x(N), -(MASK_Y1 + 1.2), 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('1'), ['at', pos_x(1), -(MASK_Y1 + 1.2), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]],
      ['fp_text', 'user', Q('49'), ['at', pos_x(N), -(MASK_Y1 + 1.2), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]]]
yc = -(LAND_Y0 + LAND_Y1) / 2
for k in range(1, N + 1):
    for num, layer in ((2 * k, 'F'), (2 * k - 1, 'B')):
        fp.append(['pad', Q(str(num)), 'smd', 'rect', ['at', pos_x(k), yc], ['size', FINGER_W, LAND_Y1 - LAND_Y0],
                   ['layers', Q(layer + '.Cu')]])
fp.append(['embedded_fonts', 'no'])
assert pos_x(1) > 0 and pos_x(N) < 0
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-SMS.pretty', 'SMS_Cart_Edge_50.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: pins 2/1 at x=%+.2f, 50/49 at x=%+.2f; even F.Cu, odd B.Cu; fingers %g x %g mm, tab %g x %g'
      % (pos_x(1), pos_x(N), FINGER_W, LAND_Y1 - LAND_Y0, TAB_W, TAB_D))
