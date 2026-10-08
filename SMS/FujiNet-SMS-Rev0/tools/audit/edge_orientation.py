#!/usr/bin/env python3
"""Check FujiNet-SMS.pretty/SMS_Cart_Edge_50.kicad_mod against the sources for
the SMS / SMS2 cartridge edge (collected 2026-10-06; the Rev0 schematic's
first footprint had the faces swapped, which would have put console +5V on
/WR):

  [1] SMS Power, "SMS cartridge" slot diagram
      https://www.smspower.org/Development/SMSCartridge -- seen from above with
      the label toward the viewer: front row 50 ... 2, back row 49 ... 1 (left
      to right), i.e. even pins on the label / front face, pins 1/2 at the right.
  [2] little-scale, "How to make a 32KB Sega Master System cartridge" (2008):
      "the front side has the even numbers ... the ROM chip faces upwards";
      the front points toward the front of the console.
  [3] MrSVCD, 1200 dpi scans of an original 171-5519 (SMS Power forum thread
      17935): component-side silkscreen "50" at the left ... "2" at the right
      (fingers down); fingers 1.65-1.76 wide, pitch 2.537-2.539, copper ~1.2 to
      ~10.1 mm from the edge, board ~66.0 x 40.1 mm.
  [4] raphnet SMS4MBIT v2 fab drawing / gerbers: 65.80 x 44.60 mm, fingers 1.75
      wide, 0.5 -> 9.5 mm, even pins on the component side, pin 2 right.
  [5] barbeque/sms-u-simple-cartridge SMS_Cartridge.kicad_mod: 1.70 x 8.5,
      1.25 -> 9.75 mm, 65.8 mm board; even pins F.Cu, pin 2 right.
  [6] reidrac/sms-cart-32k CONN1: 1.70 x 8.0, 1.0 -> 9.0 mm; even pins F.Cu.
  Pin functions: Hardware Book "Master System Cartridge" (pin 1 +5V, 2 /WR,
  19-21 GND; 31 A6, 33 A12, 35 +5V, 37 /M1 -- SMS Power's table mislabels
  those four odd rows).

The checks: even pads on F.Cu (this board's component side), odd pads on
B.Cu directly behind them, pins 1/2 at +x (east, seen from F.Cu with the
fingers down), 2.54 mm pitch, and finger width / copper span inside the
range every source shares (so the console contacts land on gold)."""
import os, re, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
t = open(os.path.join(PRJ, 'FujiNet-SMS.pretty', 'SMS_Cart_Edge_50.kicad_mod')).read()
pads = {}
for m in re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+) ([-\d.]+)\)\s*\(layers "([FB])\.Cu"\)', t):
    pads[int(m.group(1))] = (float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), m.group(6))
ok = sorted(pads) == list(range(1, 51))
# copper span common to every source: from <= 1.25 to >= 9.0 mm in from the edge
SOURCES = {'171-5519 scan [3]': (1.65, 1.76, 1.2, 10.1), 'raphnet [4]': (1.75, 1.75, 0.5, 9.5),
           'barbeque [5]': (1.70, 1.70, 1.25, 9.75), 'reidrac [6]': (1.70, 1.70, 1.0, 9.0)}
for n in (1, 2, 49, 50):
    px, py, pw, ph, pl = pads[n]
    y0, y1 = -py - ph / 2, -py + ph / 2
    want_l = 'F' if n % 2 == 0 else 'B'
    want_x = 30.48 if n in (1, 2) else -30.48
    good = pl == want_l and abs(px - want_x) < 1e-6
    ok &= good
    print('pad %2d: x=%+.2f %s.Cu, %.2f wide, copper %.2f-%.2f mm from the edge  want x=%+.2f %s.Cu  %s'
          % (n, px, pl, pw, y0, y1, want_x, want_l, 'OK' if good else 'MISMATCH'))
for k in range(1, 26):
    a, b = pads[2 * k - 1], pads[2 * k]
    ok &= a[0] == b[0] and a[4] == 'B' and b[4] == 'F'
    if k < 25:
        ok &= abs((pads[2 * k][0] - pads[2 * k + 2][0]) - 2.54) < 1e-6
w = pads[2][2]
y0, y1 = -pads[2][1] - pads[2][3] / 2, -pads[2][1] + pads[2][3] / 2
for name, (wmin, wmax, c0, c1) in SOURCES.items():
    print('  %-18s fingers %.2f-%.2f wide, copper %.2f-%.2f' % (name, wmin, wmax, c0, c1))
span_ok = 1.65 <= w <= 1.80 and y0 <= 1.25 and y1 >= 9.0
print('ours: %.2f wide, copper %.2f-%.2f  %s' % (w, y0, y1, 'inside the common span' if span_ok else 'OUTSIDE'))
ok &= span_ok
print('RESULT:', 'even pins on F.Cu, pins 1/2 east, 2.54 pitch: matches [1]-[6]' if ok else 'MISMATCH')
sys.exit(0 if ok else 1)
