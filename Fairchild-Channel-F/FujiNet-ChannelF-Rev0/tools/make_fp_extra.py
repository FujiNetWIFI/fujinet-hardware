#!/usr/bin/env python3
"""Write the board-only footprint no copied library provides:
  * MountingHole_5.6mm_NPTH: the original Videocart shell's four bosses pass through 5.6 mm holes
    (aotta/PicoVideocart's board file; its 2024 fab gerbers had 5.0), with a 4.8 mm-radius
    courtyard -- the boss base and the parts ring placement.py keeps (HOLE_KEEP).
Fiducial_1mm_Mask2mm.kicad_mod is a copy of the FujiNet-5200 Rev0 library's (KiCad library geometry).

Usage: python3 tools/make_fp_extra.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q
import edge_geom as EG
import placement as PL

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = lambda s=1.0: ['effects', ['font', ['size', s, s], ['thickness', 0.15]]]


def mounting_hole():
    name = 'MountingHole_%gmm_NPTH' % EG.HOLE_D
    return ['footprint', Q(name), ['version', 20241229], ['generator', Q('fujinet_gen')],
            ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
            ['descr', Q('Videocart shell boss clearance hole, NPTH %g mm' % EG.HOLE_D)],
            ['tags', Q('mounting hole npth videocart boss')],
            ['property', Q('Reference'), Q('REF**'), ['at', 0, -PL.HOLE_KEEP - 1, 0], ['layer', Q('F.Fab')], F()],
            ['property', Q('Value'), Q(name), ['at', 0, PL.HOLE_KEEP + 1, 0], ['layer', Q('F.Fab')], F()],
            ['attr', 'exclude_from_pos_files', 'exclude_from_bom', 'board_only'],
            ['fp_circle', ['center', 0, 0], ['end', PL.HOLE_KEEP, 0], ['stroke', ['width', 0.05], ['type', 'solid']],
             ['fill', 'no'], ['layer', Q('F.CrtYd')]],
            ['fp_circle', ['center', 0, 0], ['end', EG.HOLE_D / 2, 0], ['stroke', ['width', 0.1], ['type', 'solid']],
             ['fill', 'no'], ['layer', Q('F.Fab')]],
            ['pad', Q(''), 'np_thru_hole', 'circle', ['at', 0, 0], ['size', EG.HOLE_D, EG.HOLE_D],
             ['drill', EG.HOLE_D], ['layers', Q('*.Cu'), Q('*.Mask')]],
            ['embedded_fonts', 'no']]


if __name__ == '__main__':
    lib = os.path.join(PRJ, 'FujiNet-ChannelF.pretty')
    for fp in (mounting_hole(),):
        open(os.path.join(lib, str(fp[1]) + '.kicad_mod'), 'w').write(dump(fp) + '\n')
        print('wrote', fp[1])
