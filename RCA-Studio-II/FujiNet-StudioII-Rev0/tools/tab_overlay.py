#!/usr/bin/env python3
"""docs/tab-overlay-1to1.pdf: the board's outline and its contact face (B.Cu: the 22 fingers, the
notches, the shell-post holes) at true scale, seen FROM THE CONTACT SIDE (mirrored), with a 50 mm
ruler, the pin numbers under the fingers and the instructions -- the physical check before
ordering: print at 100 % (no "fit to page"), measure the ruler, then lay a real Studio II cartridge
board contacts-up on it (the geometry is FliP's multicart v5.1; no original was measured).

The drawing comes from the routed board itself (a copy with the ruler and text added on
User.Drawings), so it shows exactly what the gerbers carry.  The text is written mirrored, so it
reads the right way round in the mirrored plot.

Usage: python3 tools/tab_overlay.py
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import design as D
import edge_geom as EG
import gen_pcb as G
from sexpr import parse, dump, Q
from tmpdir import tmp

PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
OUT = os.path.join(PRJ, 'docs', 'tab-overlay-1to1.pdf')
LAYER = 'Dwgs.User'                              # 'User.Drawings' in the editor


def line(t, a, b, w=0.15):
    t.append(['gr_line', ['start', round(a[0], 3), round(a[1], 3)], ['end', round(b[0], 3), round(b[1], 3)],
              ['stroke', ['width', w], ['type', 'solid']], ['layer', Q(LAYER)],
              ['uuid', Q(G.uid('overlay', 'l', a, b))]])


def text(t, s, at, size=1.5, just=None):
    e = ['effects', ['font', ['size', size, size], ['thickness', size * 0.15]]]
    # mirrored text: readable once the whole plot is mirrored (seen from the contact side)
    e.append(['justify'] + ([{'left': 'right', 'right': 'left'}[just]] if just else []) + ['mirror'])
    t.append(['gr_text', Q(s), ['at', round(at[0], 3), round(at[1], 3), 0], ['layer', Q(LAYER)],
              ['uuid', Q(G.uid('overlay', 't', s, at))], e])


def main():
    t = parse(open(PCB).read())
    y_edge = G.Y1                                   # the insertion edge (board y, down = out of the slot)
    x0 = G.XC - 25.0
    # a 50 mm ruler under the edge: ticks every mm, long ones every 5 / 10 mm
    yr = y_edge + 12.0
    line(t, (x0, yr), (x0 + 50, yr), 0.2)
    for i in range(51):
        h = 3.0 if i % 10 == 0 else 2.0 if i % 5 == 0 else 1.0
        line(t, (x0 + i, yr), (x0 + i, yr + h))
        if i % 10 == 0:
            text(t, str(i), (x0 + i, yr + 5.0), 1.5)
    text(t, '50 mm: measure this before trusting the print', (G.XC, yr + 8.5), 1.5)
    # the pin numbers under the fingers (B.Cu)
    for pin in (1, 5, 6, 7, 10, 11, 15, 21, 22):
        x = G.XC + EG.pin_x(pin)
        line(t, (x, y_edge + 1.0), (x, y_edge + 3.0))
        text(t, str(pin), (x, y_edge + 4.6), 1.2)
    lines = ['FujiNet-StudioII Rev0: the cartridge edge at 1:1, seen from the CONTACT side (B.Cu), edge toward you',
             'Print at 100 % (no fit-to-page) and check the 50 mm ruler. Then lay a real Studio II cart board on it,',
             'contacts up and edge toward you: the 22 contacts (0.156" / 3.96 mm), the %.1f mm width, the two' % EG.BOARD_W,
             '%.2f mm post holes and the side notches should line up within ~0.3 mm (FliP multicart v5.1 geometry).' % EG.HOLE_D,
             'Pin 1 (D7) is at the LEFT seen from this side; 15 is the console +5 V, 6 and 7 are grounded, 22 CART CS.']
    for k, s in enumerate(lines):
        text(t, s, (G.X1 + 6.0, G.Y0 - 16.0 + 3.0 * k), 1.6, 'left')
    fn = tmp('overlay.kicad_pcb')
    open(fn, 'w').write(dump(t) + '\n')
    r = subprocess.run(['kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'Edge.Cuts,B.Cu,B.SilkS,%s' % LAYER,
                        '--mode-single', '--black-and-white', '--mirror', '-o', OUT, fn], capture_output=True, text=True)
    os.remove(fn)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    print('tab overlay: %s (A4, 1:1)' % os.path.relpath(OUT, PRJ))


if __name__ == '__main__':
    main()
