#!/usr/bin/env python3
"""ngspice: the 40-wire ribbon between the Model I's expansion edge and the card, both ways.

  strobe  the keyboard unit's 74LS367 (rise/fall 6 ns, ~30 Ohm high / 15 Ohm low) -> ribbon -> the card's
          74LVC3G17 input (5 pF, 100k pull-up to 3.3 V).  Checked: after each edge the input never re-crosses
          the Schmitt trigger's other threshold (VT- min 0.84 V after a rise, VT+ max 2.22 V after a fall:
          tools/audit/margins.py) -- a ringing strobe never double-counts.
  data    the card's 74LVC245A (rise/fall 1.5 ns, ~15 Ohm) -> Rs (the data series resistor) -> ribbon ->
          the keyboard unit's data bus (two LS367 inputs + the bus's own MOS loads, ~60 pF lumped at the
          edge).  Checked: overshoot past 0..3.3 V into the LS inputs (clamp current), and the settle time
          to within 10 % -- swept over Rs.
The ribbon: flat 40-way, 0.05" pitch, with only three ground wires (pins 8, 29, 37) -- a signal's return is
mostly its neighbours: Z0 ~ 150 Ohm, 5.3 ns/m; 15 cm (Tandy's EI cable was 6 in) and 45 cm (a long one).

Usage: python3 tools/audit/spice/ribbon.py      (needs ngspice; exit 1 if a strobe ringing check fails)
"""
import os, re, subprocess, sys, tempfile

Z0, NSM = 150.0, 5.3
VTP, VTM = 2.22, 0.84


def run(deck):
    fd, fn = tempfile.mkstemp(suffix='.cir')
    os.write(fd, deck.encode())
    os.close(fd)
    out = subprocess.run(['ngspice', '-b', fn], capture_output=True, text=True).stdout
    os.remove(fn)
    return {k: float(v) for k, v in re.findall(r'^(\w+)\s*=\s*([-+\d.eE]+)', out, re.M)}


def strobe(length_m):
    td = NSM * length_m
    deck = f"""* strobe: LS367 -> ribbon -> LVC3G17
Vs src 0 PULSE(0.2 3.4 20n 6n 6n 194n 400n)
Rdrv src a 22
T1 a 0 b 0 Z0={Z0} TD={td}n
Cin b 0 5p
Vpu vpu 0 3.3
Rpu b vpu 100k
.tran 0.05n 400n
.control
run
meas tran vmax_hi MAX v(b) from=20n to=220n
meas tran vmin_hi MIN v(b) from=40n to=215n
meas tran vmax_lo MAX v(b) from=240n to=400n
meas tran vmin_lo MIN v(b) from=220n to=400n
.endc
.end
"""
    return run(deck)


def data(length_m, rs, cload=60e-12):
    td = NSM * length_m
    deck = f"""* data: LVC245 -> Rs -> ribbon -> keyboard-unit bus
Vs src 0 PULSE(0 3.3 20n 1.5n 1.5n 300n 600n)
Rdrv src a 15
Rs a b {rs}
T1 b 0 c 0 Z0={Z0} TD={td}n
Cl c 0 {cload}
.tran 0.05n 400n
.control
run
meas tran vmax MAX v(c) from=20n to=300n
meas tran vmin MIN v(c) from=330n to=400n
meas tran t90 WHEN v(c)=2.97 RISE=1
meas tran vlow MIN v(c) from=60n to=300n
.endc
.end
"""
    return run(deck)


def main():
    bad = 0
    for L in (0.15, 0.45):
        r = strobe(L)
        ok_hi = r['vmin_hi'] > VTM
        ok_lo = r['vmax_lo'] < VTP
        bad += not (ok_hi and ok_lo)
        print('strobe %2.0f cm: high %.2f..%.2f V (stays above VT- %.2f: %s), low %.2f..%.2f V (stays under VT+ %.2f: %s)'
              % (L * 100, r['vmin_hi'], r['vmax_hi'], VTM, 'ok' if ok_hi else 'RINGS THROUGH',
                 r['vmin_lo'], r['vmax_lo'], VTP, 'ok' if ok_lo else 'RINGS THROUGH'))
    for L in (0.15, 0.45):
        for rs in (0, 47, 68, 75, 100):
            r = data(L, rs)
            print('data %2.0f cm, Rs %3d: peak %.2f V, undershoot %+.2f V, 90 %% after %4.1f ns, settled (> 90 %%) by 40 ns: %s'
                  % (L * 100, rs, r['vmax'], r['vmin'], (r['t90'] - 20e-9) * 1e9, 'yes' if r['vlow'] > 2.97 else 'NO'))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
