#!/usr/bin/env python3
"""Check the drawn schematic against design.py.

1. Connectivity: export the netlist with kicad-cli and require that every
   (reference, pin) sits on exactly the net design.py gives it, by name, and
   that every NC pin is unconnected -- so the drawing (wires, labels, power
   symbols, hierarchy) cannot silently differ from the design.
2. Drawing: no two symbol bodies overlap, nothing leaves the paper.

Usage: python3 tools/check_sch_layout.py      exit 1 on any failure
"""
import json, os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
PAPER = {'A4': (297.0, 210.0), 'A3': (420.0, 297.0), 'A2': (594.0, 420.0)}


def main():
    fails = []
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-astrocade-layout.xml')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    got = {}
    for n in ET.parse(fn).iter('net'):
        name = n.get('name')
        if not name.startswith('unconnected-'):
            name = name.split('/')[-1]          # local labels carry their sheet path
        for nd in n.iter('node'):
            got[(nd.get('ref'), nd.get('pin'))] = name
    for p in D.PARTS:
        for pin, net in p.pins.items():
            g = got.get((p.ref, pin))
            if g is None:
                fails.append('%s.%s missing from the netlist' % (p.ref, pin))
            elif net is None:
                if not g.startswith('unconnected-'):
                    fails.append('%s.%s should be NC, is on %s' % (p.ref, pin, g))
            elif g != net:
                fails.append('%s.%s on %s, design.py says %s' % (p.ref, pin, g, net))
    refs = {p.ref for p in D.PARTS}
    for (ref, pin) in got:
        if ref not in refs and not ref.startswith('#'):
            fails.append('netlist has %s.%s, design.py has no %s' % (ref, pin, ref))

    geo = json.load(open(os.path.join(HERE, '.sch_geometry.json')))
    for stem, g in geo.items():
        W, H = PAPER[g['paper']]
        boxes = g['boxes']
        for i, (r, x0, y0, x1, y1) in enumerate(boxes):
            if x0 < 10 or y0 < 10 or x1 > W - 10 or y1 > H - 10:
                fails.append('%s: %s off the drawing area' % (stem, r))
            for (r2, a0, b0, a1, b1) in boxes[i + 1:]:
                if r2 == r:
                    continue
                if min(x1, a1) - max(x0, a0) > 0.3 and min(y1, b1) - max(y0, b0) > 0.3:
                    fails.append('%s: %s overlaps %s' % (stem, r, r2))
    for f in fails:
        print('FAIL:', f)
    n = sum(len(p.pins) for p in D.PARTS)
    print('%d pins checked against design.py, %d failures' % (n, len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
