#!/usr/bin/env python3
"""Build the two footprints this board takes from the parts JLCPCB places, into FujiNet-TRS80M1.pretty:

  IDC-Header_2x20_P2.54mm_Horizontal_BH254R-40P   XFCN BH254R-40P (LCSC C48603651), a right-angle
      shrouded 2x20 box header; second source Ckmtw B-3000R40P-0110 (C146628): the same 40 holes
  SW_DIP_SPSTx03_SMD_P2.54mm_HX                    HANXIA 2.54-3P TPGT (LCSC C7421520), a 3-way SMD
      DIP switch

Pads and body outlines come from each part's EasyEDA footprint (tools/audit/jlc/easyeda_cache/<LCSC>.json,
the official JLCEDA library JLCPCB assembles by), so tools/audit/jlc/measure_rotations.py measures
both at 0 deg / 0 mm.  The footprint origin is EasyEDA's.  Units there are 10 mil, +y down as KiCad.

The header: odd pins on the row away from the mouth (y -1.27), even pins on the mouth's row (y +1.27),
pin 1 at x +24.13; the shroud lies on the board from y +3.43 to its mouth at y +12.24.  The board
edge goes at the mouth (tools/header_geom.py).  3D: KiCad's generic IDC-Header_2x20_P2.54mm_Horizontal.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
CACHE = os.path.join(HERE, 'audit', 'jlc', 'easyeda_cache')
LIB = os.path.join(PRJ, 'FujiNet-TRS80M1.pretty')
MIL10 = 0.254


def easyeda(lcsc):
    d = json.load(open(os.path.join(CACHE, lcsc + '.json')))['result']['packageDetail']['dataStr']
    x0, y0 = float(d['head']['x']), float(d['head']['y'])
    pads = []
    for sh in d['shape']:
        f = sh.split('~')
        if f[0] == 'PAD':
            pads.append(dict(num=f[8], shape=f[1], x=round((float(f[2]) - x0) * MIL10, 3),
                             y=round((float(f[3]) - y0) * MIL10, 3), w=round(float(f[4]) * MIL10, 3),
                             h=round(float(f[5]) * MIL10, 3), drill=round(2 * float(f[9]) * MIL10, 3) if f[9] else 0))
    return pads


def T(size=1.0):
    return ['effects', ['font', ['size', size, size], ['thickness', 0.15 * size]]]


def line(a, b, layer, w):
    return ['fp_line', ['start', *a], ['end', *b], ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(layer)]]


def rect(a, b, layer, w):
    return ['fp_rect', ['start', *a], ['end', *b], ['stroke', ['width', w], ['type', 'solid']], ['fill', 'no'],
            ['layer', Q(layer)]]


def head(name, descr, ref_at, val_at, attr):
    return ['footprint', Q(name), ['version', 20241229], ['generator', Q('fujinet_gen')],
            ['generator_version', Q('1.0')], ['layer', Q('F.Cu')], ['descr', Q(descr)],
            ['property', Q('Reference'), Q('REF**'), ['at', *ref_at, 0], ['layer', Q('F.SilkS')], T()],
            ['property', Q('Value'), Q(name), ['at', *val_at, 0], ['layer', Q('F.Fab')], T()],
            ['attr'] + attr]


def model(f, off, rot):
    return ['model', Q('${KIPRJMOD}/3d/' + f), ['offset', ['xyz', *off]], ['scale', ['xyz', 1, 1, 1]],
            ['rotate', ['xyz', *rot]]]


def header():
    name = 'IDC-Header_2x20_P2.54mm_Horizontal_BH254R-40P'
    pads = easyeda('C48603651')
    assert len(pads) == 40 and {p['num'] for p in pads} == {str(i) for i in range(1, 41)}
    p1 = next(p for p in pads if p['num'] == '1')
    assert (p1['x'], p1['y']) == (24.13, -1.27), p1
    fp = head(name, 'XFCN BH254R-40P (LCSC C48603651) 2x20 2.54 mm right-angle shrouded box header; Ckmtw '
              'B-3000R40P-0110 (C146628) fits the same holes. Odd pins on the row away from the mouth, the '
              'mouth toward +Y at y 12.24 (pads and outline from the EasyEDA footprint)',
              (0, -3.6), (0, 13.6), ['through_hole'])
    # the shroud on the board, its mouth at +y; the pins' rows behind it
    bx, by0, by1 = 29.3, 3.43, 12.24
    fp.append(rect((-bx, by0), (bx, by1), 'F.Fab', 0.1))
    fp.append(rect((-bx, -2.25), (bx, by0), 'F.Fab', 0.1))
    fp.append(['fp_text', 'user', Q('mouth / ribbon'), ['at', 0, 10.4, 0], ['layer', Q('F.Fab')], T(0.8)])
    s = 0.12
    fp.append(rect((-bx - 0.11, by0 - 0.11), (bx + 0.11, by1 + 0.11), 'F.SilkS', s))
    # pin-1 mark: a triangle beside pin 1, outside the shroud's end
    x1 = p1['x'] + 1.9
    fp.append(['fp_poly', ['pts', ['xy', x1, -1.27], ['xy', x1 + 0.9, -1.87], ['xy', x1 + 0.9, -0.67]],
               ['stroke', ['width', s], ['type', 'solid']], ['fill', 'yes'], ['layer', Q('F.SilkS')]])
    fp.append(rect((-bx - 0.5, -2.45), (bx + 0.5, by1 + 0.5), 'F.CrtYd', 0.05))
    for p in sorted(pads, key=lambda p: int(p['num'])):
        shape = 'rect' if p['num'] == '1' else 'circle'
        fp.append(['pad', Q(p['num']), 'thru_hole', shape, ['at', p['x'], p['y']], ['size', p['w'], p['w']],
                   ['drill', p['drill']], ['layers', Q('*.Cu'), Q('*.Mask')], ['remove_unused_layers', 'no']])
    # KiCad's generic model: its pin 1 at its origin, even row at +x, pins along +y.  Ours: pin 1 at
    # (24.13, -1.27), pins along -x, even row at +y -> turned -90 about z, pin 1 moved onto ours
    fp.append(model('IDC-Header_2x20_P2.54mm_Horizontal.step', (24.13, 1.27, 0), (0, 0, -90)))
    fp.append(['embedded_fonts', 'no'])
    return name, fp


def dip():
    name = 'SW_DIP_SPSTx03_SMD_P2.54mm_HX'
    pads = easyeda('C7421520')
    assert sorted(p['num'] for p in pads) == ['1', '2', '3', '4', '5', '6']
    fp = head(name, 'HANXIA 2.54-3P TPGT (LCSC C7421520) 3-way SMD DIP switch, 2.54 mm; pins 1-3 / 6-4 '
              'switch pairs, ON toward pins 4-6 (pads from the EasyEDA footprint)',
              (0, -6.4), (0, 6.4), ['smd'])
    fp.append(rect((-3.81, -3.05), (3.81, 3.05), 'F.Fab', 0.1))
    fp.append(rect((-3.93, -3.17), (3.93, 3.17), 'F.SilkS', 0.12))
    fp.append(['fp_text', 'user', Q('ON'), ['at', -2.9, -2.1, 0], ['layer', Q('F.SilkS')], T(0.7)])
    fp.append(['fp_text', 'user', Q('1'), ['at', -2.54, 2.1, 0], ['layer', Q('F.SilkS')], T(0.7)])
    fp.append(rect((-4.3, -5.45), (4.3, 5.45), 'F.CrtYd', 0.05))
    for p in sorted(pads, key=lambda p: int(p['num'])):
        fp.append(['pad', Q(p['num']), 'smd', 'rect', ['at', p['x'], p['y']], ['size', p['w'], p['h']],
                   ['layers', Q('F.Cu'), Q('F.Paste'), Q('F.Mask')]])
    # KiCad's SW_DIP_SPSTx03_Slide_6.7x9.18mm (pins 1-3 down its left column): turned +90 about z
    fp.append(model('SW_DIP_SPSTx03_Slide_6.7x9.18mm_W8.61mm_P2.54mm_LowProfile.step', (0, 0, 0), (0, 0, 90)))
    fp.append(['embedded_fonts', 'no'])
    return name, fp


if __name__ == '__main__':
    for name, fp in (header(), dip()):
        open(os.path.join(LIB, name + '.kicad_mod'), 'w').write(dump(fp) + '\n')
        print('wrote', name)
