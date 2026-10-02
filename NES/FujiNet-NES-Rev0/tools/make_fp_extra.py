#!/usr/bin/env python3
"""Write the two stock-KiCad-style footprints the Rev0 redo added and that no
installed library provides here: SOT-23-5 (AP2112K LDO) and
SOIC-8_3.9x4.9mm_P1.27mm (ATtiny13A CIClone).  Pad geometry follows the
KiCad Package_TO_SOT_SMD / Package_SO generators (IPC-7351 nominal).

Usage: python3 tools/make_fp_extra.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = lambda s=1.0: ['effects', ['font', ['size', s, s], ['thickness', 0.15 if s >= 1 else 0.1]]]


def line(a, b, layer, w):
    return ['fp_line', ['start', *a], ['end', *b], ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]


def rect(a, b, layer, w):
    return ['fp_rect', ['start', *a], ['end', *b], ['stroke', ['width', w], ['type', 'solid']], ['fill', 'no'],
            ['layer', Q(layer)]]


def footprint(name, descr, tags, pads, body, crt, silk, model):
    """pads: [(num, x, y, w, h)]; body/crt: (x0, y0, x1, y1); silk: list of lines."""
    bx0, by0, bx1, by1 = body
    fp = ['footprint', Q(name), ['version', 20241229], ['generator', Q('fujinet_gen')],
          ['generator_version', Q('1.0')], ['layer', Q('F.Cu')], ['descr', Q(descr)], ['tags', Q(tags)],
          ['property', Q('Reference'), Q('REF**'), ['at', 0, by0 - 1.2, 0], ['layer', Q('F.SilkS')], F()],
          ['property', Q('Value'), Q(name), ['at', 0, by1 + 1.2, 0], ['layer', Q('F.Fab')], F()],
          ['property', Q('Footprint'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['property', Q('Datasheet'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['property', Q('Description'), Q(''), ['at', 0, 0, 0], ['layer', Q('F.Fab')], ['hide', 'yes'], F()],
          ['attr', 'smd'],
          rect((bx0, by0), (bx1, by1), 'F.Fab', 0.1),
          line((bx0, by0 + 1.0), (bx0 + 1.0, by0), 'F.Fab', 0.1),   # pin-1 chamfer
          rect((crt[0], crt[1]), (crt[2], crt[3]), 'F.CrtYd', 0.05),
          ['fp_text', 'user', Q('${REFERENCE}'), ['at', 0, 0, 0], ['layer', Q('F.Fab')], F(0.8)]]
    fp += [line(a, b, 'F.SilkS', 0.12) for a, b in silk]
    for num, x, y, w, h in pads:
        fp.append(['pad', Q(str(num)), 'smd', 'roundrect', ['at', x, y], ['size', w, h],
                   ['layers', Q('F.Cu'), Q('F.Paste'), Q('F.Mask')], ['roundrect_rratio', 0.25]])
    fp.append(['model', Q('${KIPRJMOD}/3d/' + model), ['offset', ['xyz', 0, 0, 0]],
               ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz', 0, 0, 0]]])
    fp.append(['embedded_fonts', 'no'])
    return fp


def sot23_5():
    pads = [(1, -1.1, -0.95, 1.06, 0.65), (2, -1.1, 0, 1.06, 0.65), (3, -1.1, 0.95, 1.06, 0.65),
            (4, 1.1, 0.95, 1.06, 0.65), (5, 1.1, -0.95, 1.06, 0.65)]
    silk = [((-0.9, -1.56), (0.9, -1.56)), ((-0.9, 1.56), (0.9, 1.56)), ((-1.75, -1.56), (-0.9, -1.56))]
    return footprint('SOT-23-5', 'SOT-23-5, 5 pin, 0.95 mm pitch (KiCad Package_TO_SOT_SMD geometry)',
                     'SOT-23-5', pads, (-0.8, -1.45, 0.8, 1.45), (-1.9, -1.7, 1.9, 1.7), silk, 'SOT-23-5.step')


def soic8():
    ys = (-1.905, -0.635, 0.635, 1.905)
    pads = [(i + 1, -2.475, y, 1.95, 0.6) for i, y in enumerate(ys)] + \
           [(8 - i, 2.475, y, 1.95, 0.6) for i, y in enumerate(ys)]
    silk = [((-1.95, -2.56), (1.95, -2.56)), ((-1.95, 2.56), (1.95, 2.56)), ((-3.45, -2.56), (-1.95, -2.56))]
    return footprint('SOIC-8_3.9x4.9mm_P1.27mm', 'SOIC, 8 Pin, 3.9 x 4.9 mm body, 1.27 mm pitch (KiCad Package_SO geometry)',
                     'SOIC SO', pads, (-1.95, -2.45, 1.95, 2.45), (-3.7, -2.7, 3.7, 2.7), silk,
                     'SOIC-8_3.9x4.9mm_P1.27mm.step')


if __name__ == '__main__':
    lib = os.path.join(PRJ, 'FujiNet-NES.pretty')
    for fp in (sot23_5(), soic8()):
        open(os.path.join(lib, str(fp[1]) + '.kicad_mod'), 'w').write(dump(fp) + '\n')
        print('wrote', fp[1])
