#!/usr/bin/env python3
"""Write FujiNet-StudioII.pretty/StudioII_Cart_Edge_22.kicad_mod from edge_geom.py.

The RCA Studio II 22-pin cartridge edge: 22 contacts at 3.96 mm (0.156") on one face, pin 1 at the
left seen from that face with the fingers down.  Every dimension but the pitch and the count is
PROVISIONAL (edge_geom.py): measure a real cartridge before any layout.

Local frame: y = 0 is the insertion edge and the board extends in -y, so the footprint goes on the
SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q
import edge_geom as E

F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
NAME = 'StudioII_Cart_Edge_22'
X0, X1 = E.pin_x(1) - E.FINGER_W / 2 - 0.5, E.pin_x(E.N_PINS) + E.FINGER_W / 2 + 0.5   # finger field


def line(a, b, layer, w=0.1):
    return ['fp_line', ['start', a[0], a[1]], ['end', b[0], b[1]],
            ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]


def rect(layer, x0, y0, x1, y1, w=0.05, fill='no'):
    return ['fp_rect', ['start', x0, y0], ['end', x1, y1],
            ['stroke', ['width', w], ['type', 'solid']], ['fill', fill], ['layer', Q(layer)]]


def tab_picture(layer):
    h, c, d = E.TAB_W / 2, E.CH_TAB, E.TAB_D
    pts = [(-h, -d), (-h, -c), (-h + c, 0), (h - c, 0), (h, -c), (h, -d)]
    return [line(a, b, layer) for a, b in zip(pts, pts[1:])]


face = E.FACE + '.'
fp = ['footprint', Q(NAME), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('2.0')], ['layer', Q('F.Cu')],
      ['descr', Q('RCA Studio II 22-pin cartridge edge: 22 contacts at 3.96 mm (0.156") on %s.Cu, pin 1 at the '
                  'left.  PROVISIONAL: fingers %.2f mm wide, copper %.1f-%.1f mm from the edge, tab %.1f mm; '
                  'measure a real cartridge first.  Hard gold, 30-45 deg bevel.'
                  % (E.FACE, E.FINGER_W, E.LAND_Y0, E.LAND_Y1, E.TAB_W))],
      ['tags', Q('rca studio ii cartridge edge connector 0.156')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(E.TAB_D + 1.5), 0], ['layer', Q('F.Fab')], F()],
      ['property', Q('Value'), Q(NAME), ['at', 0, -(E.TAB_D + 3.5), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom', 'allow_soldermask_bridges']]
fp += tab_picture('F.Fab')
fp.append(rect('F.CrtYd', -E.TAB_W / 2, 0, E.TAB_W / 2, -E.TAB_D))
fp.append(rect(face + 'Mask', X0, 0.2, X1, -E.MASK_Y1, 0, 'yes'))   # one opening over the finger field
ty = -(E.MASK_Y1 + 1.0)
fp += [['fp_text', 'user', Q('1'), ['at', E.pin_x(1), ty, 0], ['layer', Q(face + 'SilkS')], F()],
       ['fp_text', 'user', Q('22'), ['at', E.pin_x(E.N_PINS), ty, 0], ['layer', Q(face + 'SilkS')], F()]]
for pin in range(1, E.N_PINS + 1):
    fp.append(['pad', Q(str(pin)), 'smd', 'rect', ['at', E.pin_x(pin), round(-(E.LAND_Y0 + E.LAND_Y1) / 2, 4)],
               ['size', E.FINGER_W, round(E.LAND_Y1 - E.LAND_Y0, 4)], ['layers', Q(face + 'Cu')]])
fp.append(['embedded_fonts', 'no'])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-StudioII.pretty', NAME + '.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: %d pins at %.2f mm on %s.Cu; pin 1 x=%+.2f, pin %d x=%+.2f; fingers %g mm, copper %g-%g; '
      'tab %g x %g (PROVISIONAL)' % (E.N_PINS, E.PITCH, E.FACE, E.pin_x(1), E.N_PINS, E.pin_x(E.N_PINS),
                                     E.FINGER_W, E.LAND_Y0, E.LAND_Y1, E.TAB_W, E.TAB_D))
