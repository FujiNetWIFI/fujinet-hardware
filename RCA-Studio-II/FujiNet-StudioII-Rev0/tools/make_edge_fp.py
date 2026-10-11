#!/usr/bin/env python3
"""Write FujiNet-StudioII.pretty/StudioII_Cart_Edge_22.kicad_mod from edge_geom.py.

The RCA Studio II 22-pin cartridge edge: 22 contacts on ONE face at 0.156" (3.9624 mm), the
geometry of FliP's multicart v5.1 (tools/edge_geom.py; tools/audit/edge_orientation.py records the
sources and re-checks this file).  The contacts are on B.Cu, every part on F.Cu, as on an original
cart; seen from the contact face with the fingers down pin 1 (D7) is at the left, so seen from F.Cu
it is at the RIGHT.

Fingers 1.905 mm wide, copper 0.70-8.95 mm from the edge, each in its own B.Mask opening (0.1 mm a
side, from the edge).  The board outline (no tab: the full 90.9 mm edge enters; the notches and the
shell-post holes) belongs to gen_pcb.py; this footprint marks the finger field on the fab and
courtyard layers only.

Local frame: y = 0 is the insertion edge and the board extends in -y, x = 0 at the board centre, so
the footprint goes on the SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q
import edge_geom as E

F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
FM = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]
NAME = 'StudioII_Cart_Edge_22'
X0 = E.pin_x(E.N_PINS) - E.FINGER_W / 2 - 0.5          # the finger field, west (pin 22) ..
X1 = E.pin_x(1) + E.FINGER_W / 2 + 0.5                 # .. east (pin 1)
assert E.FACE == 'B'


def line(a, b, layer, w=0.1):
    return ['fp_line', ['start', round(a[0], 4), round(a[1], 4)], ['end', round(b[0], 4), round(b[1], 4)],
            ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]


def rect(layer, x0, y0, x1, y1, w=0.05, fill='no'):
    return ['fp_rect', ['start', round(x0, 4), round(y0, 4)], ['end', round(x1, 4), round(y1, 4)],
            ['stroke', ['width', w], ['type', 'solid']], ['fill', fill], ['layer', Q(layer)]]


def field_picture(layer):
    """The insertion edge and the finger field's top, on the fab layers."""
    h, c, d = E.BOARD_W / 2, E.CH_EDGE, E.FIELD_TOP
    pts = [(-h, -d), (-h, -c), (-h + c, 0), (h - c, 0), (h, -c), (h, -d)]
    return [line(a, b, layer) for a, b in zip(pts, pts[1:])] + [line((X0, -E.MASK_Y1), (X1, -E.MASK_Y1), layer, 0.05)]


fp = ['footprint', Q(NAME), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('3.0')], ['layer', Q('F.Cu')],
      ['descr', Q('RCA Studio II 22-pin cartridge edge: 22 contacts on one face (B.Cu, away from the parts) at '
                  '3.9624 mm (0.156"), pin 1 (D7) at the right seen from the parts side (the left seen from the '
                  'contacts).  Fingers %.3f mm wide, copper %.2f-%.2f mm from the edge, each in its own mask '
                  'opening (FliP multicart v5.1 geometry).  No tab: the full %.3f mm edge enters.  Hard gold, '
                  '45 deg bevel.' % (E.FINGER_W, E.LAND_Y0, E.LAND_Y1, E.BOARD_W))],
      ['tags', Q('rca studio ii cartridge edge connector 0.156')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(E.FIELD_TOP + 2.0), 0], ['layer', Q('F.Fab')], F()],
      ['property', Q('Value'), Q(NAME), ['at', 0, -(E.FIELD_TOP + 4.0), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom']]
fp += field_picture('F.Fab') + field_picture('B.Fab')
for lay in ('F.CrtYd', 'B.CrtYd'):
    fp.append(rect(lay, -E.BOARD_W / 2, 0, E.BOARD_W / 2, -E.FIELD_TOP))
# each finger's own B.Mask opening, from just past the edge to MASK_Y1 (the pads carry no mask layer)
for pin in range(1, E.N_PINS + 1):
    x = E.pin_x(pin)
    fp.append(rect('B.Mask', x - E.FINGER_W / 2 - E.MASK_X, 0.2, x + E.FINGER_W / 2 + E.MASK_X, -E.MASK_Y1, 0, 'yes'))
ty = -(E.MASK_Y1 + 1.2)
fp += [['fp_text', 'user', Q(str(p)), ['at', E.pin_x(p), ty, 0], ['layer', Q('B.SilkS')], FM()]
       for p in (1, 10, 11, 22)]
for pin in range(1, E.N_PINS + 1):
    fp.append(['pad', Q(str(pin)), 'smd', 'rect', ['at', E.pin_x(pin), round(-(E.LAND_Y0 + E.LAND_Y1) / 2, 4)],
               ['size', E.FINGER_W, round(E.LAND_Y1 - E.LAND_Y0, 4)], ['layers', Q('B.Cu')]])
fp.append(['embedded_fonts', 'no'])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-StudioII.pretty', NAME + '.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: 22 pins at %.4f mm on %s.Cu; pin 1 x=%+.3f (east, seen from F.Cu), pin 22 x=%+.3f; fingers %g mm, '
      'copper %g-%g; board edge %g' % (E.PITCH, E.FACE, E.pin_x(1), E.pin_x(22), E.FINGER_W, E.LAND_Y0, E.LAND_Y1,
                                       E.BOARD_W))
