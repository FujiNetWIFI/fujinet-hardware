#!/usr/bin/env python3
"""One-time helper: collect the flattened schematic symbols this board uses
into tools/symcache.sexpr (so gen_sch.py never depends on another project).

Sources: symbol caches of the INTV Rev0 sheets (CERN-OHL-W, stock KiCad
symbols as flattened by eeschema) and of the previous Astrocade sheets.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, dump, find, findall

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = [os.path.join(HERE, '../../../INTV/FujiNet-INTV-Rev0', f) for f in
       ('cart-rp2354a.kicad_sch', 'esp32s3-sd.kicad_sch', 'usb-uart.kicad_sch', 'power.kicad_sch')]
SRC += [os.path.join(HERE, '..', f) for f in ('cart-rp2040.kicad_sch',)]
WANT = sys.argv[1:]
got = {}
for fn in SRC:
    if not os.path.exists(fn):
        continue
    t = parse(open(fn).read())
    for s in findall(find(t, 'lib_symbols'), 'symbol'):
        if s[1] not in got:
            got[s[1]] = s
out = ['symcache'] + [got[k] for k in sorted(got)]
open(os.path.join(HERE, 'symcache.sexpr'), 'w').write(dump(out) + '\n')
print('\n'.join(sorted(got)))
