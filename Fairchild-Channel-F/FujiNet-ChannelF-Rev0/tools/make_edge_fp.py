#!/usr/bin/env python3
"""Write FujiNet-ChannelF.pretty/ChannelF_Videocart_Edge_22.kicad_mod from edge_geom.py.

The Fairchild Channel F Videocart edge: 22 contacts on ONE face at 2.54 mm, pins 1-11, a 4-pitch
gap for the key slot, pins 12-22 (tools/audit/edge_orientation.py records the sources and
re-checks this file).  The contacts are on the face that is down in the console; this board is
assembled on F.Cu only, which faces up, so every finger is on B.Cu.  Seen from F.Cu with the
fingers down, pin 1 (GND) is at the left.

Finger geometry (edge_geom.py): 1.8 mm wide, copper 0.5-12.0 mm from the edge, one B.Mask window
to 12.5 mm.  The board outline (the 68.3 mm tab, its corner chamfers, the key slot and its
lead-in, the taper) belongs to gen_pcb.py; this footprint only marks the tab and the slot on the
fab and courtyard layers.

Local frame: y = 0 is the insertion edge and the board extends in -y, x = 0 at the key slot, so
the footprint goes on the SOUTH edge at rotation 0.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q
import edge_geom as E

F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
FM = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]
NAME = 'ChannelF_Videocart_Edge_22'
X0, X1 = E.pin_x(1) - E.FINGER_W / 2 - 0.5, E.pin_x(22) + E.FINGER_W / 2 + 0.5   # finger field


def line(a, b, layer, w=0.1):
    return ['fp_line', ['start', round(a[0], 4), round(a[1], 4)], ['end', round(b[0], 4), round(b[1], 4)],
            ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]


def rect(layer, x0, y0, x1, y1, w=0.05, fill='no'):
    return ['fp_rect', ['start', round(x0, 4), round(y0, 4)], ['end', round(x1, 4), round(y1, 4)],
            ['stroke', ['width', w], ['type', 'solid']], ['fill', fill], ['layer', Q(layer)]]


def tab_picture(layer):
    h, c, d = E.TAB_W / 2, E.CH_TAB, E.TAB_D
    s, l = E.SLOT_W / 2, E.LEADIN_W / 2
    pts = [(-h, -d), (-h, -c), (-h + c, 0), (-l, 0), (-s, -E.LEADIN_D), (-s, -(E.SLOT_D - s)),
           (0, -E.SLOT_D), (s, -(E.SLOT_D - s)), (s, -E.LEADIN_D), (l, 0), (h - c, 0), (h, -c), (h, -d)]
    return [line(a, b, layer) for a, b in zip(pts, pts[1:])]


fp = ['footprint', Q(NAME), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('2.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Fairchild Channel F Videocart edge: 22 contacts on one face (B.Cu: the face down in the console) '
                  'at 2.54 mm, pins 1-11 / key slot / 12-22, pin 1 (GND) at the left seen from the parts side.  '
                  'Fingers %.2f mm wide, copper %.1f-%.1f mm from the edge.  Tab %.1f mm, slot %.3f x %.2f.  '
                  'Hard gold, 30-45 deg bevel.' % (E.FINGER_W, E.LAND_Y0, E.LAND_Y1, E.TAB_W, E.SLOT_W, E.SLOT_D))],
      ['tags', Q('fairchild channel f videocart cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(E.TAB_D - 4.0), 0], ['layer', Q('F.Fab')], F()],
      ['property', Q('Value'), Q(NAME), ['at', 0, -(E.TAB_D - 6.0), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom', 'allow_soldermask_bridges']]
fp += tab_picture('F.Fab') + tab_picture('B.Fab')
for lay in ('F.CrtYd', 'B.CrtYd'):
    fp.append(rect(lay, -E.TAB_W / 2, 0, E.TAB_W / 2, -E.TAB_D))
# one B.Mask opening over the finger field (the pads carry no mask layer of their own); F.Mask stays
fp.append(rect('B.Mask', X0, 0.2, X1, -E.MASK_Y1, 0, 'yes'))
ty = -(E.MASK_Y1 + 1.0)
fp += [['fp_text', 'user', Q(str(p)), ['at', E.pin_x(p), ty, 0], ['layer', Q('B.SilkS')], FM()]
       for p in (1, 11, 12, 22)]
for pin in range(1, E.N_PINS + 1):
    fp.append(['pad', Q(str(pin)), 'smd', 'rect', ['at', E.pin_x(pin), round(-(E.LAND_Y0 + E.LAND_Y1) / 2, 4)],
               ['size', E.FINGER_W, round(E.LAND_Y1 - E.LAND_Y0, 4)], ['layers', Q('B.Cu')]])
fp.append(['embedded_fonts', 'no'])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-ChannelF.pretty', NAME + '.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: 22 pins at %.2f mm on B.Cu, gap %d pitches; pins 1/11/12/22 x=%+.2f/%+.2f/%+.2f/%+.2f; fingers %g mm, '
      'copper %g-%g; tab %g x %g; slot %g x %g'
      % (E.PITCH, E.GAP, E.pin_x(1), E.pin_x(11), E.pin_x(12), E.pin_x(22), E.FINGER_W, E.LAND_Y0, E.LAND_Y1,
         E.TAB_W, E.TAB_D, E.SLOT_W, E.SLOT_D))
