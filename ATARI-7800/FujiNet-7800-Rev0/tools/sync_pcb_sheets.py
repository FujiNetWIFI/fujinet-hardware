#!/usr/bin/env python3
"""Point the routed board's footprints at the schematic sheets design.py now
assigns them to, and give them design.py's current Value / Description / MPN /
LCSC fields, without touching anything else in the .kicad_pcb.

Each footprint carries the path of its schematic symbol (/sheet-uuid/symbol-
uuid) plus the sheet's name and file; gen_pcb.py writes them from p.sheet, so a
full rebuild needs nothing from here.  When parts move between sheets on an
already routed board (the 2026-10-04 redraw split cart-rp2354b into edge-cic,
rp2354b, sram and glue), this rewrites just those three fields, by reference,
with the same uuid formula gen_pcb.py uses -- copper, nets and placement stay
byte for byte.  The four fields follow a part change that keeps its footprint
(R_HALT 1k -> 10k after the 2026-10-07 /HALT SPICE check), so the routed board
need not be rebuilt for it.  Then: kicad-cli pcb drc --schematic-parity.

Usage: python3 tools/sync_pcb_sheets.py
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D
import gen_sch

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')


def main():
    syms = gen_sch.load_symbols()
    want, fields = {}, {}
    for p in D.PARTS:
        fields[p.ref] = {'Value': p.value, 'Description': p.desc, 'MPN': p.mpn, 'LCSC': p.lcsc}
        u = gen_sch.units_of(syms[p.lib_id])[0]
        want[p.ref] = ('/%s/%s' % (gen_sch.uid('sheet', p.sheet), gen_sch.uid(p.sheet, p.ref, u)),
                       '/%s/' % p.sheet, p.sheet + '.kicad_sch')
    text = open(PCB).read()
    # footprint blocks start at a tab-indented "(footprint" line; split there
    parts = re.split(r'(?m)^(?=\t\(footprint ")', text)
    seen, changed = set(), 0
    for i, blk in enumerate(parts):
        if not blk.startswith('\t(footprint "'):
            continue
        m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not m or m.group(1) not in want:
            continue
        ref = m.group(1)
        path, name, file = want[ref]
        new = re.sub(r'\(path "[^"]*"\)', '(path "%s")' % path, blk, count=1)
        new = re.sub(r'\(sheetname "[^"]*"\)', '(sheetname "%s")' % name, new, count=1)
        new = re.sub(r'\(sheetfile "[^"]*"\)', '(sheetfile "%s")' % file, new, count=1)
        for k, v in fields[ref].items():
            v = (v or '').replace('\\', '\\\\').replace('"', '\\"')
            new = re.sub(r'\(property "%s" "(?:[^"\\]|\\.)*"' % k,
                         lambda _m: '(property "%s" "%s"' % (k, v), new, count=1)
        changed += new != blk
        parts[i] = new
        seen.add(ref)
    missing = sorted(set(want) - seen)
    if missing:
        raise SystemExit('not on the board: %s' % ', '.join(missing))
    open(PCB, 'w').write(''.join(parts))
    print('%d footprints, %d re-pointed or re-fielded' % (len(seen), changed))


if __name__ == '__main__':
    main()
