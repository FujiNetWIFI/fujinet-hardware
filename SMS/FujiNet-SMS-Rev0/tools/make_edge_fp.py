#!/usr/bin/env python3
"""Write FujiNet-SMS.pretty/SMS_Cart_Edge_50.kicad_mod.

The Sega Master System / SMS2 50-pin cartridge edge: 25 positions per face at
2.54 mm (0.1 in) pitch, odd pins on one face and even pins on the other,
pin 2k-1 directly over pin 2k (the user-corrected pin list in design.py).

PROVISIONAL -- nothing here has been measured on a real cartridge yet:
  * which face carries the odd pins: assumed the component side (F.Cu);
  * which end pin 1 is at: assumed the RIGHT (+x, east) looking at the
    component side with the fingers down, the NES footprint's convention;
  * finger width / length, copper start, tab width and depth: generic 0.1 in
    card-edge values (FINGER_W, LAND_Y0/1, TAB_W, TAB_D below).
check_nets.py asserts the pitch, the face split and pin 1's end from this
file, so a correction here is checked the next time the build runs.

Local frame: y=0 is the insertion edge and the board extends in -y, so the
footprint goes on the SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PITCH, N = 2.54, 25
FINGER_W = 1.78                       # PROVISIONAL: 0.070 in, the common 0.1 in card-edge land
LAND_Y0, LAND_Y1 = 0.5, 8.5           # PROVISIONAL: copper, distance in from the edge
TAB_W, TAB_D = 65.0, 10.0             # PROVISIONAL: the connector tab the fingers sit on
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]


def pos_x(k):
    """Position k (1..25: pins 2k-1 / 2k) centre x: pin 1 east."""
    return round((N - 1) * PITCH / 2 - (k - 1) * PITCH, 3)


fp = ['footprint', Q('SMS_Cart_Edge_50'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Sega Master System 50-pin cartridge edge: 2 x 25 fingers, 2.54 mm pitch, odd pins F.Cu '
                  '(pin 1 east), even pins B.Cu, pin 2k-1 over pin 2k.  PROVISIONAL geometry and face '
                  'assignment: verify against a real cartridge PCB.  Hard gold, bevel.')],
      ['tags', Q('sega master system sms cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(TAB_D + 1.5), 0], ['layer', Q('F.SilkS')], F()],
      ['property', Q('Value'), Q('SMS_Cart_Edge_50'), ['at', 0, -(TAB_D + 3.5), 0], ['layer', Q('F.Fab')], F()],
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
      ['fp_text', 'user', Q('49'), ['at', pos_x(N), -(TAB_D + 0.9), 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('2'), ['at', pos_x(1), -(TAB_D + 0.9), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]],
      ['fp_text', 'user', Q('50'), ['at', pos_x(N), -(TAB_D + 0.9), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]]]
yc = -(LAND_Y0 + LAND_Y1) / 2
for k in range(1, N + 1):
    for num, layer in ((2 * k - 1, 'F'), (2 * k, 'B')):
        fp.append(['pad', Q(str(num)), 'smd', 'rect', ['at', pos_x(k), yc], ['size', FINGER_W, LAND_Y1 - LAND_Y0],
                   ['layers', Q(layer + '.Cu')]])
fp.append(['embedded_fonts', 'no'])
assert pos_x(1) > 0 and pos_x(N) < 0
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-SMS.pretty', 'SMS_Cart_Edge_50.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: pins 1/2 at x=%+.2f, 49/50 at x=%+.2f; odd F.Cu, even B.Cu; fingers %g x %g mm (PROVISIONAL)'
      % (pos_x(1), pos_x(N), FINGER_W, LAND_Y1 - LAND_Y0))
