#!/usr/bin/env python3
"""Bring the routed board's footprint fields (Value, MPN, Manufacturer, LCSC, Datasheet, Description) in
step with design.py without touching any copper or position: for a sourcing change (an MPN or LCSC code)
after the board was routed.  The schematic is regenerated first (tools/gen_sch.py); DRC with
--schematic-parity then proves the two agree.

Usage: python3 tools/sync_fields.py [--redraw=KEY,KEY]   (--redraw: those parts' silk / fab / courtyard
       drawing from the library too, after a footprint's drawing changed; never their pads)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
import design as D
import gen_sch

syms = gen_sch.load_symbols()
PCB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), D.PROJECT + '.kicad_pcb')
b = parse(open(PCB).read())
n = 0
for fp in findall(b, 'footprint'):
    ref = next(str(p[2]) for p in findall(fp, 'property') if str(p[1]) == 'Reference')
    part = D.BY_REF.get(ref)
    if not part:
        continue
    ds = part.ds or next((str(pr[2]) for pr in findall(syms[part.lib_id], 'property') if pr[1] == 'Datasheet'), '')
    want = {'Value': part.value, 'MPN': part.mpn, 'Manufacturer': part.mfr, 'LCSC': part.lcsc,
            'Datasheet': ds, 'Description': part.desc}
    for pr in findall(fp, 'property'):
        k = str(pr[1])
        if k in want and want[k] and str(pr[2]) != want[k]:
            pr[2] = Q(want[k])
            n += 1
# footprint graphics (silk / fab / courtyard, never pads) from the library, for footprints whose drawing
# changed after routing; and the board's gr_text items from gen_pcb
import gen_pcb as G
REDRAW = next((a.split('=', 1)[1].split(',') for a in sys.argv[1:] if a.startswith('--redraw=')), [])
g = 0
for fp in findall(b, 'footprint'):
    ref = next(str(p[2]) for p in findall(fp, 'property') if str(p[1]) == 'Reference')
    part = D.BY_REF.get(ref)
    if not part or part.key not in REDRAW:
        continue
    lib = G.load_fp(part.footprint.split(':')[1])
    drawn = lambda e: isinstance(e, list) and e and e[0] in ('fp_line', 'fp_rect', 'fp_poly', 'fp_circle', 'fp_arc', 'fp_text')
    new = [e for e in lib if drawn(e)]
    old = [e for e in fp if drawn(e)]
    strip = lambda e: [x for x in e if not (isinstance(x, list) and x and x[0] == 'uuid')]
    if [strip(e) for e in old] != [strip(e) for e in new]:
        fp[:] = [e for e in fp if not drawn(e)]
        k = next(i for i, e in enumerate(fp) if isinstance(e, list) and e and e[0] == 'pad')
        fp[k:k] = [list(e) + [['uuid', G.uid(ref, 'gfx', i)]] for i, e in enumerate(new)]
        g += 1
G.do_placement(G.place)
b = [e for e in b if not (isinstance(e, list) and e and e[0] == 'gr_text')]
k = next(i for i, e in enumerate(b) if isinstance(e, list) and e and e[0] == 'embedded_fonts')
b[k:k] = G.silk_texts()
open(PCB, 'w').write(dump(b) + '\n')
print('sync_fields: %d footprint fields updated, %d footprints redrawn, board texts rewritten' % (n, g))
