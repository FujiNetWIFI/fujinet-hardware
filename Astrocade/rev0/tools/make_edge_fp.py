#!/usr/bin/env python3
"""Write FujiNet-Astrocade.pretty/Astrocade_Cart_Edge_26.kicad_mod.

26 contact lands on the cart UNDERSIDE (B.Cu), 2.54 mm pitch, 63.5 mm span,
1.7 x 14 mm, 1 mm back from the insertion edge (local y=0 is the board edge,
+y points into the board).  The console blade slides under the PCB and wipes
the whole strip, so the board keeps B.Cu free of tracks/vias there (rule
area in gen_pcb.py).  Each land therefore carries its own escape inside the
footprint: a 0.5 mm neck under solder mask (B.Cu, no mask opening) running
past the wipe zone to a 0.3/0.6 mm plated hole -- pads are allowed in the
rule area, tracks/vias are not.  Pad 1 is at local x = -31.75.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PITCH, N = 2.54, 26
LAND_W, LAND_Y0, LAND_Y1 = 1.7, 1.0, 15.0      # local y of land
NECK_W, VIA_Y = 0.5, 17.4                      # plated escape 17.4 mm in from the edge
VIA_D, VIA_DRILL = 0.6, 0.3
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]

fp = ['footprint', Q('Astrocade_Cart_Edge_26'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('Bally Astrocade cartridge contact lands: 1x26, 0.100in pitch, on the cart UNDERSIDE '
                  '(blade-style console connector presses up). Span 63.5mm. Each land escapes through a '
                  'masked neck to a plated hole 17.4mm from the edge, outside the blade wipe zone. '
                  'Hard gold recommended, no paste.')],
      ['tags', Q('astrocade cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, 19.2, 0], ['layer', Q('F.SilkS')], F()],
      ['property', Q('Value'), Q('Astrocade_Cart_Edge_26'), ['at', 0, 21, 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom'],
      ['fp_line', ['start', -33.5, 0], ['end', 33.5, 0], ['stroke', ['width', 0.12], ['type', 'solid']],
       ['layer', Q('F.Fab')]],
      ['fp_rect', ['start', -33.0, -0.2], ['end', 33.0, VIA_Y + 0.6], ['stroke', ['width', 0.05], ['type', 'solid']],
       ['fill', 'no'], ['layer', Q('B.CrtYd')]],
      ['fp_text', 'user', Q('contact side (bottom) - keep clean'), ['at', 0, 16.2, 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]]]
for i in range(N):
    x = round(-31.75 + i * PITCH, 3)
    n = Q(str(i + 1))
    fp.append(['pad', n, 'smd', 'rect', ['at', x, (LAND_Y0 + LAND_Y1) / 2], ['size', LAND_W, LAND_Y1 - LAND_Y0],
               ['layers', Q('B.Cu'), Q('B.Mask')], ['solder_mask_margin', 0.05]])
    neck_y0, neck_y1 = LAND_Y1 - 0.3, VIA_Y
    fp.append(['pad', n, 'smd', 'rect', ['at', x, (neck_y0 + neck_y1) / 2], ['size', NECK_W, neck_y1 - neck_y0],
               ['layers', Q('B.Cu')]])
    fp.append(['pad', n, 'thru_hole', 'circle', ['at', x, VIA_Y], ['size', VIA_D, VIA_D], ['drill', VIA_DRILL],
               ['layers', Q('*.Cu')], ['remove_unused_layers', 'no']])
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-Astrocade.pretty', 'Astrocade_Cart_Edge_26.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok')
