#!/usr/bin/env python3
"""Write the footprint no copied library provides: PinHeader_1x03_P2.54mm_Vertical
(the RP debug UART header), to the KiCad Connector_PinHeader_2.54mm geometry
(1.7 mm pads, 1.0 mm drill, pad 1 square).  Every other footprint in
FujiNet-7800.pretty is a copy of the NES Rev0 project's (KiCad library
geometry; see that project's README).

Usage: python3 tools/make_fp_extra.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = lambda s=1.0: ['effects', ['font', ['size', s, s], ['thickness', 0.15 if s >= 1 else 0.1]]]


def line(a, b, layer, w):
    return ['fp_line', ['start', *a], ['end', *b], ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]


def header_1x03():
    name = 'PinHeader_1x03_P2.54mm_Vertical'
    n = 3
    y1 = (n - 1) * 2.54
    fp = ['footprint', Q(name), ['version', 20241229], ['generator', Q('fujinet_gen')],
          ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
          ['descr', Q('Through hole straight pin header, 1x03, 2.54mm pitch, single row (KiCad library geometry)')],
          ['tags', Q('Through hole pin header THT 1x03 2.54mm single row')],
          ['property', Q('Reference'), Q('REF**'), ['at', 0, -2.33, 0], ['layer', Q('F.SilkS')], F()],
          ['property', Q('Value'), Q(name), ['at', 0, y1 + 2.33, 0], ['layer', Q('F.Fab')], F()],
          ['property', Q('Footprint'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['property', Q('Datasheet'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['property', Q('Description'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['attr', 'through_hole'],
          line((-0.635, -1.27), (1.27, -1.27), 'F.Fab', 0.1), line((1.27, -1.27), (1.27, y1 + 1.27), 'F.Fab', 0.1),
          line((1.27, y1 + 1.27), (-1.27, y1 + 1.27), 'F.Fab', 0.1), line((-1.27, y1 + 1.27), (-1.27, -0.635), 'F.Fab', 0.1),
          line((-1.27, -0.635), (-0.635, -1.27), 'F.Fab', 0.1),
          line((-1.33, 1.27), (-1.33, y1 + 1.33), 'F.SilkS', 0.12), line((1.33, 1.27), (1.33, y1 + 1.33), 'F.SilkS', 0.12),
          line((-1.33, 1.27), (1.33, 1.27), 'F.SilkS', 0.12), line((-1.33, y1 + 1.33), (1.33, y1 + 1.33), 'F.SilkS', 0.12),
          line((-1.33, 0), (-1.33, -1.33), 'F.SilkS', 0.12), line((-1.33, -1.33), (0, -1.33), 'F.SilkS', 0.12),
          ['fp_rect', ['start', -1.8, -1.8], ['end', 1.8, y1 + 1.8], ['stroke', ['width', 0.05], ['type', 'solid']],
           ['fill', 'no'], ['layer', Q('F.CrtYd')]],
          ['fp_text', 'user', Q('${REFERENCE}'), ['at', 0, y1 / 2, 90], ['layer', Q('F.Fab')], F()]]
    for i in range(n):
        fp.append(['pad', Q(str(i + 1)), 'thru_hole', 'rect' if i == 0 else 'oval', ['at', 0, i * 2.54],
                   ['size', 1.7, 1.7], ['drill', 1.0], ['layers', Q('*.Cu'), Q('*.Mask')],
                   ['remove_unused_layers', 'no']])
    fp.append(['embedded_fonts', 'no'])
    return fp


if __name__ == '__main__':
    lib = os.path.join(PRJ, 'FujiNet-7800.pretty')
    for fp in (header_1x03(),):
        open(os.path.join(lib, str(fp[1]) + '.kicad_mod'), 'w').write(dump(fp) + '\n')
        print('wrote', fp[1])
