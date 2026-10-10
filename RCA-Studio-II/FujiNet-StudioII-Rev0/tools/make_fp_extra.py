#!/usr/bin/env python3
"""Write the footprints no copied library provides:
  * PinHeader_1x03_P2.54mm_Vertical (the RP debug UART header), to the KiCad
    Connector_PinHeader_2.54mm geometry (1.7 mm pads, 1.0 mm drill, pad 1 square);
  * SW_SPST_TS-1187A (XKB TS-1187A-B-A-B, LCSC C318884, a JLCPCB basic part: the
    TL3342 of the NES / SMS boards had 5 in stock on 2026-10-07), from XKB drawing
    TS-1187A-X-X-X rev A0 (datasheets/TS-1187A-B-A-B.pdf): body 5.1 x 5.1 x 1.5 mm,
    PCB layout four 1.0 x 0.75 mm pads at x +-3.0, y +-1.875 (7.0 / 5.0 and 4.5 / 3.0
    outer / inner spans); A-B and C-D are each one contact, so the pads are 1 1 / 2 2.
Both as on FujiNet-5200 Rev0.  Every other footprint in FujiNet-StudioII.pretty is a
copy of that project's, except the edge (make_edge_fp.py).

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


def ts1187a():
    name = 'SW_SPST_TS-1187A'
    fp = ['footprint', Q(name), ['version', 20241229], ['generator', Q('fujinet_gen')],
          ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
          ['descr', Q('XKB TS-1187A tact switch, 5.1x5.1 mm SMD, 4 pads (XKB drawing TS-1187A-X-X-X A0)')],
          ['tags', Q('tact switch SPST SMD 5.1x5.1 TS-1187A')],
          ['property', Q('Reference'), Q('REF**'), ['at', 0, -3.6, 0], ['layer', Q('F.SilkS')], F()],
          ['property', Q('Value'), Q(name), ['at', 0, 3.6, 0], ['layer', Q('F.Fab')], F()],
          ['property', Q('Footprint'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['property', Q('Datasheet'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['property', Q('Description'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['attr', 'smd'],
          ['fp_rect', ['start', -2.55, -2.55], ['end', 2.55, 2.55], ['stroke', ['width', 0.1], ['type', 'solid']],
           ['fill', 'no'], ['layer', Q('F.Fab')]],
          ['fp_circle', ['center', 0, 0], ['end', 1.0, 0], ['stroke', ['width', 0.1], ['type', 'solid']],
           ['fill', 'no'], ['layer', Q('F.Fab')]],
          ['fp_circle', ['center', 0, 0], ['end', 1.0, 0], ['stroke', ['width', 0.12], ['type', 'solid']],
           ['fill', 'no'], ['layer', Q('F.SilkS')]],
          line((-2.66, -1.2), (-2.66, 1.2), 'F.SilkS', 0.12), line((2.66, -1.2), (2.66, 1.2), 'F.SilkS', 0.12),
          line((-2.0, -2.66), (2.0, -2.66), 'F.SilkS', 0.12), line((-2.0, 2.66), (2.0, 2.66), 'F.SilkS', 0.12),
          ['fp_rect', ['start', -3.75, -2.8], ['end', 3.75, 2.8], ['stroke', ['width', 0.05], ['type', 'solid']],
           ['fill', 'no'], ['layer', Q('F.CrtYd')]],
          ['fp_text', 'user', Q('${REFERENCE}'), ['at', 0, 0, 0], ['layer', Q('F.Fab')], F(0.8)]]
    for num, x, y in (('1', -3.0, -1.875), ('1', 3.0, -1.875), ('2', -3.0, 1.875), ('2', 3.0, 1.875)):
        fp.append(['pad', Q(num), 'smd', 'rect', ['at', x, y], ['size', 1.0, 0.75],
                   ['layers', Q('F.Cu'), Q('F.Paste'), Q('F.Mask')]])
    fp.append(['embedded_fonts', 'no'])
    return fp


if __name__ == '__main__':
    lib = os.path.join(PRJ, 'FujiNet-StudioII.pretty')
    for fp in (header_1x03(), ts1187a()):
        open(os.path.join(lib, str(fp[1]) + '.kicad_mod'), 'w').write(dump(fp) + '\n')
        print('wrote', fp[1])
