#!/usr/bin/env python3
"""Write FujiNet-O2.pretty/Videopac_Cart_Edge_30.kicad_mod.

Magnavox Odyssey 2 / Philips Videopac cartridge edge: 30 gold fingers, 15 per face, 3.9286 mm pitch
(geometry and its sources: tools/edge_geom.py).

Footprint frame = board frame at rotation 0: local y = 0 is the insertion edge, -y points into the
board, +x is to the right looking at the parts (F.Cu) side.

  F.Cu (parts side, toward the player): pins 1 .. 15 (T0, B0-B7, A10, P14, P11, P10, A11, A9)
  B.Cu (the back): pins A .. R (no I, O, Q), each directly behind its 1 .. 15 pin
  pin 1 / A at the left seen from F.Cu when edge_geom.PIN1_LEFT, else at the right

Each land continues as a neck under solder mask to y = -NECK_Y1, past the rule area gen_pcb.py
keeps over the finger field (no tracks, vias or pour between fingers), so the routers connect
above it.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q
import edge_geom as EG

NAME = 'Videopac_Cart_Edge_30'
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
HALF = (EG.N_PER_FACE - 1) / 2 * EG.PITCH + EG.LAND_W / 2 + 0.3     # courtyard half-width

fp = ['footprint', Q(NAME), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Magnavox Odyssey 2 / Philips Videopac cartridge edge: 2x15 gold fingers, %.4fmm pitch, %gx%gmm, '
                  '%gmm from the edge. F.Cu = pins 1-15, B.Cu = pins A-R (no I/O/Q), A behind 1. Order ENIG + '
                  'gold fingers + 30deg bevel. Geometry and sources: tools/edge_geom.py.'
                  % (EG.PITCH, EG.LAND_W, EG.LAND_Y1 - EG.LAND_Y0, EG.LAND_Y0))],
      ['tags', Q('magnavox odyssey2 philips videopac cartridge edge connector gold finger')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(EG.NECK_Y1 + 2.0), 0], ['layer', Q('F.SilkS')],
       ['hide', 'yes'], F()],
      ['property', Q('Value'), Q(NAME), ['at', 0, -(EG.NECK_Y1 + 3.3), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom'],
      ['fp_line', ['start', -EG.BOARD_W / 2, 0], ['end', EG.BOARD_W / 2, 0], ['stroke', ['width', 0.12], ['type', 'solid']],
       ['layer', Q('F.Fab')]]]
for layer in ('F', 'B'):
    fp.append(['fp_rect', ['start', -HALF, 0.0], ['end', HALF, -(EG.NECK_Y1 + 0.3)],
               ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q(layer + '.CrtYd')]])
for pin in EG.PINS:
    x = EG.finger_x(pin)
    layer = EG.finger_layer(pin)[0]
    n = Q(str(pin))
    fp.append(['pad', n, 'smd', 'rect', ['at', x, -(EG.LAND_Y0 + EG.LAND_Y1) / 2],
               ['size', EG.LAND_W, EG.LAND_Y1 - EG.LAND_Y0], ['layers', Q(layer + '.Cu'), Q(layer + '.Mask')],
               ['solder_mask_margin', 0.05]])
    ny0 = EG.LAND_Y1 - 0.3
    fp.append(['pad', n, 'smd', 'rect', ['at', x, -(ny0 + EG.NECK_Y1) / 2], ['size', EG.NECK_W, EG.NECK_Y1 - ny0],
               ['layers', Q(layer + '.Cu')]])
# pin-name markers at both ends of each row (B.Cu text mirrored, read from the back)
ty = -(EG.NECK_Y1 + 0.9)
for pin in ('1', '15'):
    fp.append(['fp_text', 'user', Q(str(pin)), ['at', EG.finger_x(pin), ty, 0], ['layer', Q('F.SilkS')],
               ['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]]]])
for pin in ('A', 'R'):
    fp.append(['fp_text', 'user', Q(str(pin)), ['at', EG.finger_x(pin), ty, 0], ['layer', Q('B.SilkS')],
               ['effects', ['font', ['size', 0.8, 0.8], ['thickness', 0.12]], ['justify', 'mirror']]])
fp.append(['embedded_fonts', 'no'])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-O2.pretty', NAME + '.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok')
