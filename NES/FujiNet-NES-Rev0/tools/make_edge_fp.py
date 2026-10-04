#!/usr/bin/env python3
"""Write FujiNet-NES.pretty/NES_Cart_Edge_72.kicad_mod.

The NES 72-pin cartridge edge, to the geometry measured on an NES-EWROM-01
board (nesdev wiki "NES cartridge dimensions"; Gumball2415/NES-Famicom-
Cartridge-Dimensions, TAPR OHL -- dimensions only, nothing copied) and
cross-checked against nesos-dev/nes-dev-cart (tested in an NES-001):

  * 36 fingers per side at 2.50 mm pitch (NOT 0.100 in), 87.5 mm span
  * fingers 2.0 x 12.0 mm; the four end fingers (1, 36, 37, 72: GND, +5V,
    SYSTEM CLK, GND) are 3.0 mm wide
  * copper from 1.0 mm to 13.0 mm in from the board edge (the edge is
    bevelled / the connector's contacts wipe this zone)
  * solder-mask opening: front = the 6.5 mm nearest the edge, back = the
    11.0 mm nearest the edge, across the whole finger field (Nintendo's
    boards mask the inner part of the label-side fingers)
  * the connector tab is 93.5 mm wide and 14.5 mm deep; the body is 100 mm
    wide (gen_pcb.py draws it)

Orientation (nesdev "Cartridge connector"): pins 1-36 are on the LABEL side
(F.Cu, the component side), pins 37-72 on the back (B.Cu), pin N over pin
N+36.  Looking at the label side with the fingers DOWN, the fingers read
36 .. 1 from left to right: pin 1 is at the RIGHT.  Local frame: y=0 is the
insertion edge and the board extends in -y, so the footprint goes on the
SOUTH edge at rotation 0 with pad 1 at +x (east).  The first Rev0 draft had
this mirrored; check_nets.py now asserts it from this file.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import dump, Q

PITCH, N = 2.5, 36
LAND_W, END_W = 2.0, 3.0
LAND_Y0, LAND_Y1 = 1.0, 13.0          # copper, distance in from the edge
MASK_F, MASK_B = 6.5, 11.0            # mask opening depth from the edge, front / back
TAB_W, TAB_D = 93.5, 14.5             # the connector tab the fingers sit on
F = lambda: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]


def pad_x(n):
    """Pad n (1..36) centre x: pin 1 east.  The 3.0 mm end fingers sit 0.5 mm
    further out so their inner edge keeps the 0.5 mm gap (NES-EWROM-01: pad 1
    at 44.25, pad 2 at 41.25)."""
    x = (N - 1) * PITCH / 2 - (n - 1) * PITCH
    if n == 1:
        x += (END_W - LAND_W) / 2
    elif n == N:
        x -= (END_W - LAND_W) / 2
    return round(x, 3)


fp = ['footprint', Q('NES_Cart_Edge_72'), ['version', 20241229], ['generator', Q('fujinet_gen')],
      ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
      ['descr', Q('NES 72-pin cartridge edge: 2 x 36 fingers 2.0 x 12 mm (ends 3.0 mm), 2.50 mm pitch (not 0.1in), '
                  '87.5 mm span, copper 1.0-13.0 mm from the edge; pins 1-36 label side (F.Cu, pin 1 east), '
                  '37-72 back (B.Cu), pin N over pin N+36.  NES-EWROM-01 geometry (nesdev). Hard gold, bevel.')],
      ['tags', Q('nes nintendo cartridge edge connector')],
      ['property', Q('Reference'), Q('REF**'), ['at', 0, -(TAB_D + 1.5), 0], ['layer', Q('F.SilkS')], F()],
      ['property', Q('Value'), Q('NES_Cart_Edge_72'), ['at', 0, -(TAB_D + 3.5), 0], ['layer', Q('F.Fab')], F()],
      ['attr', 'smd', 'exclude_from_pos_files', 'exclude_from_bom'],
      # the tab outline on Fab, for reference (Edge.Cuts is drawn by gen_pcb.py)
      ['fp_rect', ['start', -TAB_W / 2, 0], ['end', TAB_W / 2, -TAB_D],
       ['stroke', ['width', 0.1], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.Fab')]],
      ['fp_rect', ['start', -TAB_W / 2, 0], ['end', TAB_W / 2, -TAB_D],
       ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.CrtYd')]],
      ['fp_rect', ['start', -TAB_W / 2, 0], ['end', TAB_W / 2, -TAB_D],
       ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('B.CrtYd')]],
      # mask openings across the finger field (the pads themselves carry no mask layer)
      ['fp_rect', ['start', -TAB_W / 2, 0.2], ['end', TAB_W / 2, -MASK_F],
       ['stroke', ['width', 0], ['type', 'solid']], ['fill', 'yes'], ['layer', Q('F.Mask')]],
      ['fp_rect', ['start', -TAB_W / 2, 0.2], ['end', TAB_W / 2, -MASK_B],
       ['stroke', ['width', 0], ['type', 'solid']], ['fill', 'yes'], ['layer', Q('B.Mask')]],
      ['fp_text', 'user', Q('1'), ['at', pad_x(1), -(TAB_D + 0.9), 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('36'), ['at', pad_x(36), -(TAB_D + 0.9), 0], ['layer', Q('F.SilkS')], F()],
      ['fp_text', 'user', Q('37'), ['at', pad_x(1), -(TAB_D + 0.9), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]],
      ['fp_text', 'user', Q('72'), ['at', pad_x(36), -(TAB_D + 0.9), 0], ['layer', Q('B.SilkS')],
       ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]], ['justify', 'mirror']]]]
yc = -(LAND_Y0 + LAND_Y1) / 2
for n in range(1, N + 1):
    x = pad_x(n)
    w = END_W if n in (1, N) else LAND_W
    for num, layer in ((n, 'F'), (n + N, 'B')):
        fp.append(['pad', Q(str(num)), 'smd', 'rect', ['at', x, yc], ['size', w, LAND_Y1 - LAND_Y0],
                   ['layers', Q(layer + '.Cu')]])
fp.append(['embedded_fonts', 'no'])
assert pad_x(1) > 0 and pad_x(36) < 0, 'pin 1 must be east (label side, fingers down: 36 .. 1 left to right)'
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
open(os.path.join(prj, 'FujiNet-NES.pretty', 'NES_Cart_Edge_72.kicad_mod'), 'w').write(dump(fp) + '\n')
print('ok: pad 1 at x=%+.2f (F.Cu), pad 36 at x=%+.2f; fingers %g x %g mm, copper %g..%g mm from the edge'
      % (pad_x(1), pad_x(36), LAND_W, LAND_Y1 - LAND_Y0, LAND_Y0, LAND_Y1))
