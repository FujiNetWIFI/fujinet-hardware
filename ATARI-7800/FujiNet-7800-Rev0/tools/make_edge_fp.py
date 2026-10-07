#!/usr/bin/env python3
"""Write FujiNet-7800.pretty/Atari7800_Cart_Edge_32.kicad_mod from edge_geom.py.

The Atari 7800 32-pin cartridge edge: 18 positions at 2.54 mm per face, positions 3 and 16 being
the console's key slots (no finger; the slots are notches in the board OUTLINE that gen_pcb.py
draws -- this footprint has no Edge.Cuts, only an F.Fab picture of them).  Pins 1-16 on F.Cu (the
component side, which faces the console's rear), pin 1 at the left seen from F.Cu with the
fingers down, pin k over pin 33-k on B.Cu.  audit/edge_orientation.py checks this file against
the published 7800 boards and this repository's working FujiPlusCart prototype.

Local frame: y = 0 is the insertion edge and the board extends in -y, so the footprint goes on
the SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q
import edge_geom as E

F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
FM = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]
X0, X1 = E.pin_x(1) - E.FINGER_W / 2 - 0.5, E.pin_x(16) + E.FINGER_W / 2 + 0.5   # finger field
D = E.FIELD_TOP


def line(a, b, layer, w=0.1):
    return ['fp_line', ['start', a[0], a[1]], ['end', b[0], b[1]],
            ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]


def tab_picture(layer):
    """The tab outline with its two key slots (documentation only; Edge.Cuts comes from gen_pcb)."""
    h, out = E.TAB_W / 2, []
    pts = [(-h, -D), (-h, -E.CH_TAB), (-h + E.CH_TAB, 0)]
    for sx in E.SLOT_X:
        a, b = sx - E.SLOT_W / 2, sx + E.SLOT_W / 2
        pts += [(a, 0), (a, -E.SLOT_D), (b, -E.SLOT_D), (b, 0)]
    pts += [(h - E.CH_TAB, 0), (h, -E.CH_TAB), (h, -D)]
    for a, b in zip(pts, pts[1:]):
        out.append(line(a, b, layer))
    return out


fp = ['footprint', Q('Atari7800_Cart_Edge_32'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('2.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Atari 7800 32-pin cartridge edge: 18 positions at 2.54 mm per face, positions 3 and 16 '
                  'are key slots (board notches, drawn by gen_pcb); pins 1-16 F.Cu (component side, console '
                  'rear, pin 1 left), pins 17-32 B.Cu, pin k over pin 33-k; pins 3-14 / 19-30 are the 2600 '
                  'edge.  Fingers %.1f x %.1f mm from %.1f mm in.  Hard gold, bevel.'
                  % (E.FINGER_W, E.LAND_Y1 - E.LAND_Y0, E.LAND_Y0))],
      ['tags', Q('atari 7800 prosystem cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(D + 1.5), 0], ['layer', Q('F.SilkS')], F()],
      ['property', Q('Value'), Q('Atari7800_Cart_Edge_32'), ['at', 0, -(D + 3.5), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom', 'allow_soldermask_bridges']]
fp += tab_picture('F.Fab')
for lay in ('F.CrtYd', 'B.CrtYd'):
    fp.append(['fp_rect', ['start', -E.TAB_W / 2, 0], ['end', E.TAB_W / 2, -D],
               ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q(lay)]])
for lay in ('F.Mask', 'B.Mask'):   # one opening per face over the finger field (pads carry no mask)
    fp.append(['fp_rect', ['start', X0, 0.2], ['end', X1, -E.MASK_Y1],
               ['stroke', ['width', 0], ['type', 'solid']], ['fill', 'yes'], ['layer', Q(lay)]])
ty = -(E.MASK_Y1 + 1.2)
fp += [['fp_text', 'user', Q('1'), ['at', E.pin_x(1), ty, 0], ['layer', Q('F.SilkS')], F()],
       ['fp_text', 'user', Q('16'), ['at', E.pin_x(16), ty, 0], ['layer', Q('F.SilkS')], F()],
       ['fp_text', 'user', Q('32'), ['at', E.pin_x(32), ty, 0], ['layer', Q('B.SilkS')], FM()],
       ['fp_text', 'user', Q('17'), ['at', E.pin_x(17), ty, 0], ['layer', Q('B.SilkS')], FM()]]
yc = -(E.LAND_Y0 + E.LAND_Y1) / 2
for pin in range(1, 33):
    fp.append(['pad', Q(str(pin)), 'smd', 'rect', ['at', E.pin_x(pin), yc],
               ['size', E.FINGER_W, E.LAND_Y1 - E.LAND_Y0], ['layers', Q(E.pin_face(pin) + '.Cu')]])
fp.append(['embedded_fonts', 'no'])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-7800.pretty', 'Atari7800_Cart_Edge_32.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: 18 positions, key slots at x=%+.2f/%+.2f; pins 1/32 x=%+.2f, 16/17 x=%+.2f; 1-16 F.Cu; '
      'fingers %g x %g mm from %g mm; slot clearance %.2f mm'
      % (E.SLOT_X[0], E.SLOT_X[1], E.pin_x(1), E.pin_x(16), E.FINGER_W, E.LAND_Y1 - E.LAND_Y0, E.LAND_Y0,
         E.slot_clearance()))
