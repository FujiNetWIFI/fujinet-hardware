#!/usr/bin/env python3
"""Write FujiNet-5200.pretty/Atari5200_Cart_Edge_36.kicad_mod from edge_geom.py.

The Atari 5200 36-pin cartridge edge: 18 positions at 2.54 mm per face, pins 1-18 on the label
face, pin 1 (D0) at the left seen from it with the fingers down, pin 37-k directly behind pin k
(tools/audit/edge_orientation.py records the sources and re-checks this file).  This board is
assembled on F.Cu only and its label faces the same way as a stock cart's, so F.Cu carries pins
1-18.  Pins 18 and 36 (the interlock) are short fingers, as on every stock and open-source board.

Finger geometry (edge_geom.py): 1.78 mm wide, copper 0.6-7.0 mm from the edge (18 / 36: 1.9-7.0),
one mask window per face to 7.5 mm.  The board outline (the 47.8 mm tab, its lead-in chamfers, the
shoulders) belongs to gen_pcb.py; this footprint only marks the tab on the fab and courtyard layers.

Local frame: y = 0 is the insertion edge and the board extends in -y, so the footprint goes on the
SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q
import edge_geom as E

F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
FM = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]
NAME = 'Atari5200_Cart_Edge_36'
X0, X1 = E.pin_x(1) - E.FINGER_W / 2 - 0.5, E.pin_x(18) + E.FINGER_W / 2 + 0.5   # finger field


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


fp = ['footprint', Q(NAME), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('2.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Atari 5200 36-pin cartridge edge: 18 positions at 2.54 mm per face, pins 1-18 on F.Cu (label '
                  'face, pin 1 = D0 at the left), pins 19-36 on B.Cu, pin k over pin 37-k.  Fingers %.2f mm wide, '
                  'copper %.1f-%.1f mm from the edge; pins 18 / 36 (interlock) short, from %.1f mm.  Tab %.1f mm.  '
                  'Hard gold, 30-45 deg bevel.' % (E.FINGER_W, E.LAND_Y0, E.LAND_Y1, E.LAND_Y0_SHORT, E.TAB_W))],
      ['tags', Q('atari 5200 supersystem cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(E.TAB_D + 1.5), 0], ['layer', Q('F.Fab')], F()],
      ['property', Q('Value'), Q(NAME), ['at', 0, -(E.TAB_D + 3.5), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom', 'allow_soldermask_bridges']]
fp += tab_picture('F.Fab')
for lay in ('F.CrtYd', 'B.CrtYd'):
    fp.append(rect(lay, -E.TAB_W / 2, 0, E.TAB_W / 2, -E.TAB_D))
for lay in ('F.Mask', 'B.Mask'):   # one opening per face over the finger field (the pads carry no mask)
    fp.append(rect(lay, X0, 0.2, X1, -E.MASK_Y1, 0, 'yes'))
ty = -(E.MASK_Y1 + 1.0)
fp += [['fp_text', 'user', Q('1'), ['at', E.pin_x(1), ty, 0], ['layer', Q('F.SilkS')], F()],
       ['fp_text', 'user', Q('18'), ['at', E.pin_x(18), ty, 0], ['layer', Q('F.SilkS')], F()],
       ['fp_text', 'user', Q('36'), ['at', E.pin_x(36), ty, 0], ['layer', Q('B.SilkS')], FM()],
       ['fp_text', 'user', Q('19'), ['at', E.pin_x(19), ty, 0], ['layer', Q('B.SilkS')], FM()]]
for pin in range(1, E.N_PINS + 1):
    y0 = E.LAND_Y0_SHORT if pin in E.SHORT else E.LAND_Y0
    fp.append(['pad', Q(str(pin)), 'smd', 'rect', ['at', E.pin_x(pin), round(-(y0 + E.LAND_Y1) / 2, 4)],
               ['size', E.FINGER_W, round(E.LAND_Y1 - y0, 4)], ['layers', Q(E.pin_face(pin) + '.Cu')]])
fp.append(['embedded_fonts', 'no'])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-5200.pretty', NAME + '.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: 36 pins on 18 positions at %.2f mm; pins 1/36 x=%+.2f, 18/19 x=%+.2f; 1-18 F.Cu; fingers %g mm, '
      'copper %g-%g (18/36 from %g); tab %g x %g'
      % (E.PITCH, E.pin_x(1), E.pin_x(18), E.FINGER_W, E.LAND_Y0, E.LAND_Y1, E.LAND_Y0_SHORT, E.TAB_W, E.TAB_D))
