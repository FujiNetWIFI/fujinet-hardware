#!/usr/bin/env python3
"""Remove the router's copper that KiCad's DRC reports as an error (edge
clearance, annular ring, clearance, shorts): unlocked tracks and vias only,
so the finisher can redo those connections cleanly.

Usage: python3 tools/drc_fix.py [board]
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find
import gen_pcb as G

PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else G.PCB
KINDS = ('copper_edge_clearance', 'annular_width', 'clearance', 'shorting_items', 'hole_clearance', 'track_dangling', 'via_dangling')


def main():
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-astrocade-drcfix.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', fn, PCB], capture_output=True)
    d = json.load(open(fn))
    ids = {it['uuid'] for v in d.get('violations', []) if v['type'] in KINDS and v['severity'] == 'error'
           for it in v['items']}
    board = parse(open(PCB).read())
    keep, n = [], 0
    for e in board:
        if isinstance(e, list) and e and e[0] in ('segment', 'via') and find(e, 'uuid') \
                and str(find(e, 'uuid')[1]) in ids and not find(e, 'locked'):
            n += 1
            continue
        keep.append(e)
    open(PCB, 'w').write(dump(keep) + '\n')
    print('drc_fix: removed %d router items involved in DRC errors' % n)


if __name__ == '__main__':
    main()
