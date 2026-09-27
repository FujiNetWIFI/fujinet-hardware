#!/usr/bin/env python3
"""One-time: build FujiNet-Astrocade.pretty/TF-SMD_TF-015.kicad_mod from the
EasyEDA footprint of LCSC C113206 (SOFNG TF-015), as fetched by
`easyeda2kicad --lcsc_id C113206 --footprint --3d`.

Changes vs. the EasyEDA export: the two plastic locating posts become NPTH,
the courtyard is enlarged to cover every pad, silk is kept, the 3D model
points at ${KIPRJMOD}/3d/TF-015.step.  Card inserts from +Y.
Usage: make_tf015_fp.py <easyeda .pretty dir>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q

src = os.path.join(sys.argv[1], 'TF-SMD_TF-015.kicad_mod')
prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = parse(open(src).read())
T = lambda *k: ['effects', ['font', ['size', 1, 1], ['thickness', 0.15]]]
out = ['footprint', Q('TF-SMD_TF-015'), ['version', 20241229], ['generator', Q('fujinet_gen')],
       ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
       ['descr', Q('SOFNG TF-015 microSD push-push (LCSC C113206); card inserts from +Y')],
       ['property', Q('Reference'), Q('REF**'), ['at', 0, -7.4, 0], ['layer', Q('F.SilkS')], T()],
       ['property', Q('Value'), Q('TF-SMD_TF-015'), ['at', 0, 10.8, 0], ['layer', Q('F.Fab')], T()],
       ['attr', 'smd']]
for ln in findall(m, 'fp_line'):
    if find(ln, 'layer')[1] != 'F.SilkS':
        continue
    s, e = find(ln, 'start'), find(ln, 'end')
    if s[1:] == e[1:]:
        continue
    out.append(['fp_line', ['start', float(s[1]), float(s[2])], ['end', float(e[1]), float(e[2])],
                ['stroke', ['width', 0.12], ['type', 'solid']], ['layer', Q('F.SilkS')]])
out.append(['fp_rect', ['start', -8.75, -6.4], ['end', 8.75, 9.8],
            ['stroke', ['width', 0.05], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.CrtYd')]])
out.append(['fp_rect', ['start', -7.3, -4.2], ['end', 7.5, 9.55],
            ['stroke', ['width', 0.1], ['type', 'solid']], ['fill', 'no'], ['layer', Q('F.Fab')]])
out.append(['fp_text', 'user', Q('card slot'), ['at', 0, 8.5, 0], ['layer', Q('F.Fab')], T()])
for p in findall(m, 'pad'):
    num, kind = str(p[1]), p[2]
    at, size = find(p, 'at'), find(p, 'size')
    x, y = float(at[1]), float(at[2])
    if kind == 'thru_hole':
        d = float(find(p, 'drill')[1])
        out.append(['pad', Q(''), 'np_thru_hole', 'circle', ['at', x, y], ['size', d, d], ['drill', d],
                    ['layers', Q('*.Cu'), Q('*.Mask')]])
    else:
        out.append(['pad', Q(num), 'smd', 'rect', ['at', x, y], ['size', float(size[1]), float(size[2])],
                    ['layers', Q('F.Cu'), Q('F.Paste'), Q('F.Mask')]])
out.append(['model', Q('${KIPRJMOD}/3d/TF-015.step'), ['offset', ['xyz', 0, 0, 0]],
            ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz', 0, 0, 0]]])
open(os.path.join(prj, 'FujiNet-Astrocade.pretty', 'TF-SMD_TF-015.kicad_mod'), 'w').write(dump(out) + '\n')
print('ok')
