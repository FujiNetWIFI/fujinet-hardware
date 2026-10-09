#!/usr/bin/env python3
"""Which DVDD pin of the RP2354A is furthest from its core regulator, and how far its nearest
DVDD capacitor is, measured on the routed board (RP2350 datasheet 6.1.3: the two DVDD pins nearest
the regulator 100 nF each, the furthest 4.7 uF, each close to its pin)."""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sexpr import parse, find, findall
import design as D
PCB = os.path.join(os.path.dirname(os.path.dirname(HERE)), D.PROJECT + '.kicad_pcb')
t = parse(open(PCB).read())
pads = {}
for fp in findall(t, 'footprint'):
    ref = next(str(p[2]) for p in findall(fp, 'property') if p[1] == 'Reference')
    at = find(fp, 'at')
    x, y, r = float(at[1]), float(at[2]), math.radians(float(at[3]) if len(at) > 3 else 0)
    for pd in findall(fp, 'pad'):
        a = find(pd, 'at')
        px, py = float(a[1]), float(a[2])
        n = find(pd, 'net')
        pads[(ref, str(pd[1]))] = (x + px * math.cos(r) + py * math.sin(r), y - px * math.sin(r) + py * math.cos(r),
                                   str(n[1]) if n else '')
U = D.KEY['U_RP']
reg = pads[(U, '48')]                                   # VREG_LX: the regulator's switch pin
dist = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
caps = [(p.ref, p.value) for p in D.PARTS if p.prefix == 'C' and 'DVDD' in p.pins.values()]
for pin in D.RP_DVDD_PINS:
    pp = pads[(U, str(pin))]
    near = sorted((dist(pads[(c, '1')], pp), c, v) for c, v in caps)
    print('DVDD pin %2d: %.1f mm from VREG_LX; nearest DVDD cap %s %s at %.1f mm'
          % (pin, dist(pp, reg), near[0][1], near[0][2], near[0][0]))
far = max(D.RP_DVDD_PINS, key=lambda p: dist(pads[(U, str(p))], reg))
print('furthest DVDD pin: %d (datasheet: 4.7 uF close to it)' % far)
