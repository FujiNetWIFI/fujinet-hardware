#!/usr/bin/env python3
"""Write FujiNet-NES.pretty/NES_Cart_Edge_72.kicad_mod.

The NES 72-pin cartridge edge: 36 fingers per side at 2.50 mm pitch (NOT
0.100 in -- nesdev "Cartridge connector"), 87.5 mm span.  Pins 1-36 are on
the label side of the cartridge (F.Cu, the component side of a Nintendo
board), pins 37-72 on the back (B.Cu); pin N and pin N+36 share one position
(36/+5V over 72/GND, 1/GND over 37/SYSTEM CLK).

Local frame: y=0 is the insertion edge and the board extends in -y, so the
footprint placed at rotation 0 on the SOUTH edge of the board reads
correctly in top view: pin 1 west, pin 36 east, label side up.  Pad 1 is at
local x = -43.75.  Finger size (1.6 x 9.5 mm, 0.5 mm back from the edge) is
taken from Nintendo boards by eye and is a VERIFY item for the first build.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PITCH, N = 2.5, 36
LAND_W, LAND_Y0, LAND_Y1 = 1.6, 0.5, 10.0   # local -y: distance in from the edge
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]

fp = ['footprint', Q('NES_Cart_Edge_72'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('NES 72-pin cartridge edge: 2 x 36 fingers, 2.50 mm pitch (not 0.1in), 87.5 mm span. '
                  'Pins 1-36 on the label side (F.Cu), 37-72 on the back (B.Cu), pin N over pin N+36. '
                  'Hard gold, no paste; bevel the edge.')],
      ['tags', Q('nes nintendo cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -12.5, 0], ['layer', Q('F.SilkS')], F()],
      ['property', Q('Value'), Q('NES_Cart_Edge_72'), ['at', 0, -14.5, 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom'],
      ['fp_line', ['start', -46.0, 0], ['end', 46.0, 0], ['stroke', ['width', 0.12], ['type', 'solid']],
       ['layer', Q('F.Fab')]],
      ['fp_rect', ['start', -45.5, 0.2], ['end', 45.5, -(LAND_Y1 + 0.5)],
       ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.CrtYd')]],
      ['fp_rect', ['start', -45.5, 0.2], ['end', 45.5, -(LAND_Y1 + 0.5)],
       ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('B.CrtYd')]],
      ['fp_text', 'user', Q('1'), ['at', -43.75, -11.2, 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('36'), ['at', 43.75, -11.2, 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('37'), ['at', -43.75, -11.2, 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]],
      ['fp_text', 'user', Q('72'), ['at', 43.75, -11.2, 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]]]
yc = -(LAND_Y0 + LAND_Y1) / 2
for i in range(N):
    x = round(-(N - 1) * PITCH / 2 + i * PITCH, 3)
    for num, layer in ((i + 1, 'F'), (i + 37, 'B')):
        fp.append(['pad', Q(str(num)), 'smd', 'rect', ['at', x, yc], ['size', LAND_W, LAND_Y1 - LAND_Y0],
                   ['layers', Q(layer + '.Cu'), Q(layer + '.Mask')], ['solder_mask_margin', 0.05]])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-NES.pretty', 'NES_Cart_Edge_72.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok')
