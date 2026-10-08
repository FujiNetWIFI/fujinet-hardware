#!/usr/bin/env python3
"""docs/tab-overlay-1to1.pdf: the board's outline and F.Cu, fingers (pins 2-50) included,
at true scale on A4, with a 50 mm ruler, a pin-number scale under the fingers and the
instructions -- the physical check before ordering: print at 100 % (no "fit to page"), measure the
ruler, then lay a real SMS cartridge's board, or the console slot's contacts, on the fingers.

The drawing comes from the routed board itself (a copy with the ruler and text added on
User.Drawings), so it shows exactly what the gerbers carry.

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
    if just:
        e.append(['justify', just])
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
    # the pin numbers under the fingers (F.Cu, even pins), seen from the component side
    for pin in (2, 10, 20, 30, 40, 50):
        x = G.XC + EG.pin_x(pin)
        line(t, (x, y_edge + 1.0), (x, y_edge + 3.0))
        text(t, str(pin), (x, y_edge + 4.6), 1.2)
    lines = ['FujiNet-SMS Rev0: edge and tab at 1:1, component side (F.Cu, even pins 2-50), fingers down',
             'Print at 100 % (no fit-to-page) and check the 50 mm ruler. Then lay a real SMS cartridge board',
             '(label side up) on the fingers: every finger and both tab edges should line up within ~0.2 mm,',
             'and the tab must match the console slot opening. Pins 1/2 are at the right as drawn here.']
    for k, s in enumerate(lines):
        text(t, s, (G.X0, G.Y0 - 22.0 + 3.0 * k), 1.6, 'left')
    fn = tmp('overlay.kicad_pcb')
    open(fn, 'w').write(dump(t) + '\n')
    r = subprocess.run(['kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'Edge.Cuts,F.Cu,%s' % LAYER,
                        '--mode-single', '--black-and-white', '-o', OUT, fn], capture_output=True, text=True)
    os.remove(fn)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    print('tab overlay: %s (A4, 1:1)' % os.path.relpath(OUT, PRJ))


if __name__ == '__main__':
    main()
