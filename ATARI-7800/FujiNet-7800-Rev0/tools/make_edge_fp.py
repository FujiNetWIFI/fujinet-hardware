#!/usr/bin/env python3
"""Write FujiNet-7800.pretty/Atari7800_Cart_Edge_32.kicad_mod.

The Atari 7800 32-pin cartridge edge: 16 positions per face at 2.54 mm
(0.1 in) pitch, pins 1-16 on one face and 17-32 on the other, pin k directly
over pin 33-k (design.py EDGE).  Pins 3-14 and 19-30 are the 2600's 24 in
the middle of the edge; 1-2 / 31-32 and 15-16 / 17-18 extend it at each end.

Face and pin-1 end follow the 2600 Rev1 footprint in this repository, whose
geometry and orientation come from the working FujiPlusCart prototype: 2600
pins 13-24 (7800 pins 3-14) on F.Cu, the console's REAR, left to right with
the fingers down.  ASSUMED for the 7800, verify against a real 7800 cart PCB:
  * F.Cu (console rear) carries pins 1-16, pin 1 at the LEFT (-x, west)
    looking at F.Cu with the fingers down; B.Cu (label side, console front)
    carries 32..17 left to right, pin 32 behind pin 1;
PROVISIONAL, not measured:
  * fingers 1.5 x 7.0 mm from 0.5 mm in (the 2600 prototype's lands),
    extended unchanged to the 7800's four extra positions per face;
  * tab 42.6 mm wide (the 2600 tab's 2.23 mm end margins round 16 positions)
    and 10.0 mm deep.
check_nets.py asserts the pitch, the face split and pin 1's end from this
file, so a correction here is checked the next time the build runs.

Local frame: y=0 is the insertion edge and the board extends in -y, so the
footprint goes on the SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PITCH, N = 2.54, 16
FINGER_W = 1.5                        # PROVISIONAL: the 2600 prototype's land
LAND_Y0, LAND_Y1 = 0.5, 7.5           # PROVISIONAL: copper, distance in from the edge
TAB_W, TAB_D = 42.6, 10.0             # PROVISIONAL: the connector tab the fingers sit on
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]


def pos_x(k):
    """Position k (1..16: pins k / 33-k) centre x: pin 1 west."""
    return round(-(N - 1) * PITCH / 2 + (k - 1) * PITCH, 3)


fp = ['footprint', Q('Atari7800_Cart_Edge_32'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Atari 7800 32-pin cartridge edge: 2 x 16 fingers, 2.54 mm pitch, pins 1-16 F.Cu '
                  '(console rear, pin 1 west), pins 17-32 B.Cu, pin k over pin 33-k; pins 3-14 / 19-30 '
                  'are the 2600 edge.  ASSUMED face assignment, PROVISIONAL geometry: verify against a '
                  'real 7800 cartridge PCB.  Hard gold, bevel.')],
      ['tags', Q('atari 7800 prosystem cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(TAB_D + 1.5), 0], ['layer', Q('F.SilkS')], F()],
      ['property', Q('Value'), Q('Atari7800_Cart_Edge_32'), ['at', 0, -(TAB_D + 3.5), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom', 'allow_soldermask_bridges'],
      ['fp_rect', ['start', -TAB_W / 2, 0], ['end', TAB_W / 2, -TAB_D],
       ['stroke', ['width', 0.1], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.Fab')]],
      ['fp_rect', ['start', -TAB_W / 2, 0], ['end', TAB_W / 2, -TAB_D],
       ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.CrtYd')]],
      ['fp_rect', ['start', -TAB_W / 2, 0], ['end', TAB_W / 2, -TAB_D],
       ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('B.CrtYd')]],
      # one mask opening per face across the finger field (the pads carry no mask layer)
      ['fp_rect', ['start', -TAB_W / 2, 0.2], ['end', TAB_W / 2, -(LAND_Y1 + 0.5)],
       ['stroke', ['width', 0], ['type', 'solid']], ['fill', 'yes'], ['layer', Q('F.Mask')]],
      ['fp_rect', ['start', -TAB_W / 2, 0.2], ['end', TAB_W / 2, -(LAND_Y1 + 0.5)],
       ['stroke', ['width', 0], ['type', 'solid']], ['fill', 'yes'], ['layer', Q('B.Mask')]],
      ['fp_text', 'user', Q('1'), ['at', pos_x(1), -(TAB_D + 0.9), 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('16'), ['at', pos_x(N), -(TAB_D + 0.9), 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('32'), ['at', pos_x(1), -(TAB_D + 0.9), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]],
      ['fp_text', 'user', Q('17'), ['at', pos_x(N), -(TAB_D + 0.9), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]]]
yc = -(LAND_Y0 + LAND_Y1) / 2
for k in range(1, N + 1):
    for num, layer in ((k, 'F'), (33 - k, 'B')):
        fp.append(['pad', Q(str(num)), 'smd', 'rect', ['at', pos_x(k), yc], ['size', FINGER_W, LAND_Y1 - LAND_Y0],
                   ['layers', Q(layer + '.Cu')]])
fp.append(['embedded_fonts', 'no'])
assert pos_x(1) < 0 < pos_x(N)
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-7800.pretty', 'Atari7800_Cart_Edge_32.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: pins 1/32 at x=%+.2f, 16/17 at x=%+.2f; 1-16 F.Cu, 17-32 B.Cu; fingers %g x %g mm (PROVISIONAL)'
      % (pos_x(1), pos_x(N), FINGER_W, LAND_Y1 - LAND_Y0))
