#!/usr/bin/env python3
"""Compare FujiNet-NES.pretty/NES_Cart_Edge_72.kicad_mod with the NES-EWROM-01
reference (Gumball2415/NES-Famicom-Cartridge-Dimensions, measured board;
cross-checked with nesos-dev/nes-dev-cart): pad 1 east on F.Cu, pitch 2.5,
end pads 3.0 wide at +/-44.25, copper 1.0..13.0 mm from the edge."""
import os, re, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
t = open(os.path.join(PRJ, 'FujiNet-NES.pretty', 'NES_Cart_Edge_72.kicad_mod')).read()
pads = {}
for m in re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+) ([-\d.]+)\)\s*\(layers "([FB])\.Cu"\)', t):
    pads[int(m.group(1))] = (float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), m.group(6))
ref = {1: (44.25, 3.0, 'F'), 2: (41.25, 2.0, 'F'), 36: (-44.25, 3.0, 'F'), 37: (44.25, 3.0, 'B'), 72: (-44.25, 3.0, 'B')}
ok = True
for n, (x, w, L) in ref.items():
    px, py, pw, ph, pl = pads[n]
    good = abs(px - x) < 1e-6 and abs(pw - w) < 1e-6 and pl == L and abs(ph - 12.0) < 1e-6 and abs(py + 7.0) < 1e-6
    ok &= good
    print('pad %2d: x=%+.2f w=%.1f %s.Cu y=%.2f h=%.1f  ref x=%+.2f w=%.1f %s  %s' % (n, px, pw, pl, py, ph, x, w, L, 'OK' if good else 'MISMATCH'))
print('pitch pad1-pad2 = %.2f (ref 3.00 incl. the wider end pad), pad2-pad3 = %.2f (ref 2.50)' % (pads[1][0] - pads[2][0], pads[2][0] - pads[3][0]))
print('RESULT:', 'pin 1 east on F.Cu, geometry matches NES-EWROM-01' if ok else 'MISMATCH')
sys.exit(0 if ok else 1)
