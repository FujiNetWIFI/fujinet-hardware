#!/usr/bin/env python3
"""Write Fujiversal-Atari2600.pretty/Atari2600_Cart_Edge_24.kicad_mod.

Atari 2600 cartridge edge: 24 gold fingers, 12 per face, 2.54 mm pitch.
Geometry from the working FujiPlusCart prototype (ATARI-2600/
FujiPlusCart-Prototype gerbers): 1.5 mm wide lands at 0.100 in pitch, tab
32.4 mm wide.  Lands here are 1.5 x 7.0 mm starting 0.5 mm from the edge
(room for JLCPCB's bevel).

Footprint frame = board frame at rotation 0: local y = 0 is the insertion
edge, -y points into the board, +x is to the right looking at the component
(F.Cu) side.

  F.Cu (console REAR, component side), left -> right: pins 13 .. 24
  B.Cu (console FRONT, label side),    left -> right: pins 12 .. 1
  (pin 1 is directly behind pin 24, pin 12 behind pin 13)

Each land continues as a 0.5 mm neck under solder mask to y = -NECK_Y1, past
the rule area gen_pcb.py keeps over the finger strip (no tracks, vias or
pour between fingers), so the routers connect above it.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PITCH, N = 2.54, 12
LAND_W, LAND_Y0, LAND_Y1 = 1.5, 0.5, 7.5      # local -y extent of the land
NECK_W, NECK_Y1 = 0.5, 10.0                   # neck runs to 10 mm from the edge
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]


def x_of(i):
    return round((i - (N - 1) / 2) * PITCH, 3)


fp = ['footprint', Q('Atari2600_Cart_Edge_24'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Atari 2600 cartridge edge: 2x12 gold fingers, 0.100in pitch, 1.5x7.0mm, 0.5mm from '
                  'the edge. F.Cu = pins 13-24 (console rear), B.Cu = pins 12-1 (console front, pin 1 '
                  'behind pin 24). Order ENIG + gold fingers + 30deg bevel.')],
      ['tags', Q('atari 2600 vcs cartridge edge connector gold finger')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -12.2, 0], ['layer', Q('F.SilkS')], ['hide', 'yes'], F()],
      ['property', Q('Value'), Q('Atari2600_Cart_Edge_24'), ['at', 0, -13.5, 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom'],
      ['fp_line', ['start', -16.2, 0], ['end', 16.2, 0], ['stroke', ['width', 0.12], ['type', 'solid']],
       ['layer', Q('F.Fab')]]]
for layer in ('F', 'B'):
    fp.append(['fp_rect', ['start', -15.6, 0.0], ['end', 15.6, -(NECK_Y1 + 0.3)],
               ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q(layer + '.CrtYd')]])
for i in range(N):
    x = x_of(i)
    for layer, pin in (('F', 13 + i), ('B', 12 - i)):
        n = Q(str(pin))
        fp.append(['pad', n, 'smd', 'rect', ['at', x, -(LAND_Y0 + LAND_Y1) / 2],
                   ['size', LAND_W, LAND_Y1 - LAND_Y0], ['layers', Q(layer + '.Cu'), Q(layer + '.Mask')],
                   ['solder_mask_margin', 0.05]])
        ny0 = LAND_Y1 - 0.3
        fp.append(['pad', n, 'smd', 'rect', ['at', x, -(ny0 + NECK_Y1) / 2], ['size', NECK_W, NECK_Y1 - ny0],
                   ['layers', Q(layer + '.Cu')]])
# pin-1 / face markers
fp.append(['fp_text', 'user', Q('13'), ['at', x_of(0), -11.2, 0], ['layer', Q('F.SilkS')],
           ['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]]]])
fp.append(['fp_text', 'user', Q('24'), ['at', x_of(N - 1), -11.2, 0], ['layer', Q('F.SilkS')],
           ['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]]]])
fp.append(['fp_text', 'user', Q('12'), ['at', x_of(0), -11.2, 0], ['layer', Q('B.SilkS')],
           ['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]], ['justify', 'mirror']]])
fp.append(['fp_text', 'user', Q('1'), ['at', x_of(N - 1), -11.2, 0], ['layer', Q('B.SilkS')],
           ['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]], ['justify', 'mirror']]])
fp.append(['embedded_fonts', 'no'])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'Fujiversal-Atari2600.pretty', 'Atari2600_Cart_Edge_24.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok')
