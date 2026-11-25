#!/usr/bin/env python3
"""The ribbon header against the TRS-80 Model I expansion edge: the gate tools/header_geom.VERIFIED rests on.

1. The pinout.  Four independent sources, read 2026-11-24, agree on every pin but 39:
     T  TRS-80 Technical Reference Handbook (Radio Shack 26-2103, 1978) p.91 table and Fig. 22, with the
        circuit text pp.15-18 (https://www.eevblog.com/files/TRS80model1/ ... Technical Reference Handbook 1st.pdf)
     G  RetroStack's KiCad replica of the rev G keyboard-unit logic board (github.com/RetroStack/TRS-80-Model-I-G-E1):
        the edge connector's netlist (and which part drives each pin)
     H  Buzbee / Fosdick, the Tandy 26-1132 hard-disk adapter document (electrickery.hosting.philpem.me.uk)
     R  TRS-IO M1 v1.4 (github.com/apuder/TRS-IO, kicad/m1/v1.4), its swapped rows mapped back to Tandy's
   Pin 39: T's table says "+5V (limited current)", T's text that Level II machines ground it; the
   replicas have +5V on boards A, D, E and GND on G (trs-80.com: +5V removed at rev G).  This card
   leaves it open, as the EI rev D replica, TRS-IO and the HD adapter do.
2. The netlist: every header pin carries the net design.py's own copy names for that signal (and the
   open pins are open), checked against this independent table.
3. The footprint (tools/make_fp_m1.py, from the part's EasyEDA footprint): pin 1 the square pad; odd
   pins on one row, even pins on the other; pin 2k+1 and 2k+2 side by side, 2.54 mm on per pair; the
   mouth on the even row's side.
4. The cable: a straight 40-wire IDC ribbon puts wire n on IDC-socket pin n and on card-edge IDC
   position n; with the card-edge connector's pin-1 mark on the keyboard unit's pin 1 (T Fig. 22: seen
   from the rear, odd pins 1-39 on top, pin 1 at the left), header pin n = edge pin n.  The edge has no
   key slot: README "The cable" says how to plug it and what to measure first.

Usage: python3 tools/audit/header_pinout.py      exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PRJ = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from sexpr import parse, find, findall   # noqa: E402

SOURCES = 'TGHR'
PINOUT = {1: 'RAS*', 2: 'SYSRES*', 3: 'CAS*', 4: 'A10', 5: 'A12', 6: 'A13', 7: 'A15', 8: 'GND', 9: 'A11',
          10: 'A14', 11: 'A8', 12: 'OUT*', 13: 'WR*', 14: 'INTAK*', 15: 'RD*', 16: 'MUX', 17: 'A9', 18: 'D4',
          19: 'IN*', 20: 'D7', 21: 'INT*', 22: 'D1', 23: 'TEST*', 24: 'D6', 25: 'A0', 26: 'D3', 27: 'A1',
          28: 'D5', 29: 'GND', 30: 'D0', 31: 'A4', 32: 'D2', 33: 'WAIT*', 34: 'A3', 35: 'A5', 36: 'A7',
          37: 'GND', 38: 'A6', 39: '+5V (boards A-E) / GND (G)', 40: 'A2'}
# what drives each line in the keyboard unit (G, T pp.15-18): the load the card puts on it is checked
# against these in tools/audit/margins.py
DRIVER = {s: '74LS367' for s in ['A%d' % i for i in range(16)] + ['RD*', 'WR*', 'IN*', 'OUT*', 'RAS*', 'CAS*', 'MUX']}
DRIVER.update({'SYSRES*': '74LS02', 'INTAK*': '74LS32', 'INT*': 'Z80 (4.7k pull-up)', 'WAIT*': 'Z80 (4.7k pull-up)',
               'TEST*': 'Z80 BUSRQ* + buffer enables (4.7k pull-up)'})
DRIVER.update({'D%d' % i: 'keyboard-unit data bus (LS367 out except while the Z80 reads)' for i in range(8)})
OPEN = {'RAS*', 'CAS*', 'MUX', 'TEST*'}

fails = 0


def chk(desc, ok):
    global fails
    if not ok:
        fails += 1
    print('%s  %s' % ('ok  ' if ok else 'FAIL', desc))


def want_net(sig):
    if sig == 'GND':
        return 'GND'
    if sig in OPEN or sig.startswith('+5V'):
        return None
    return 'M1_' + sig.rstrip('*') + ('_N' if sig.endswith('*') else '')


def main():
    import design as D
    import header_geom as HG
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-trs80m1-rev0-hdr.xml')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    t = ET.parse(fn)
    jref = D.KEY['J_M1']
    node = {}
    for n in t.iter('net'):
        full = n.get('name')
        name = None if full.startswith('unconnected') else full.rsplit('/', 1)[-1]
        for nd in n.iter('node'):
            if nd.get('ref') == jref:
                node[int(nd.get('pin'))] = name
    print('pin  signal (sources %s)           netlist' % SOURCES)
    for p in range(1, 41):
        sig = PINOUT[p]
        got = node.get(p)
        print('%3d  %-30s %s' % (p, sig, got or 'open'))
        chk('pin %d %s -> %s' % (p, sig, want_net(sig) or 'open'), got == want_net(sig))
    chk('design.EDGE agrees with this table on every pin',
        all((D.EDGE[p][0] or None) == want_net(PINOUT[p]) for p in range(1, 41)))
    chk('three grounds (8, 29, 37); pin 39 open', [p for p in range(1, 41) if node.get(p) == 'GND'] == [8, 29, 37]
        and node.get(39) is None)
    # ---- the footprint ----
    fp = parse(open(os.path.join(PRJ, D.LIB + '.pretty', D.HDR_FP + '.kicad_mod')).read())
    pads = {str(e[1]): (e[3], float(find(e, 'at')[1]), float(find(e, 'at')[2])) for e in findall(fp, 'pad')}
    chk('40 pads, numbered 1-40', sorted(pads, key=int) == [str(i) for i in range(1, 41)])
    chk('pad 1 is the square one', pads['1'][0] == 'rect' and all(pads[str(i)][0] == 'circle' for i in range(2, 41)))
    odd = {round(pads[str(p)][2], 3) for p in range(1, 41, 2)}
    even = {round(pads[str(p)][2], 3) for p in range(2, 41, 2)}
    chk('odd pads on one row (y %s), even on the other (y %s)' % (odd, even), len(odd) == len(even) == 1 and odd != even)
    bad = [k for k in range(20) if not (abs(pads[str(2 * k + 1)][1] - pads[str(2 * k + 2)][1]) < 1e-3 and
                                        abs(pads[str(2 * k + 1)][1] - (24.13 - 2.54 * k)) < 1e-3)]
    chk('pairs (2k+1, 2k+2) side by side, 2.54 mm on per pair from pin 1 at x +24.13%s' % (
        '' if not bad else ': not at pairs %s' % bad), not bad)
    chk('the mouth (y +%.2f) on the even row\'s side' % HG.HDR_MOUTH, HG.HDR_MOUTH > next(iter(even)) > next(iter(odd)))
    # ---- the board ----
    pcb = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
    if os.path.exists(pcb):
        import placement as PL
        b = parse(open(pcb).read())
        fpe = next(e for e in b if isinstance(e, list) and e and e[0] == 'footprint'
                   and any(q[1] == 'Reference' and q[2] == jref for q in findall(e, 'property')))
        at = find(fpe, 'at')
        x, y, r = float(at[1]), float(at[2]), (float(at[3]) if len(at) > 3 else 0) % 360
        chk('header on the board at %s rot %g' % ((x, y), r), (x, y, r) == PL.HDR)
        mouth_x = x - HG.HDR_MOUTH
        chk('its mouth on the west edge (x %.2f, edge %.2f)' % (mouth_x, PL.X0), abs(mouth_x - (PL.X0 - HG.HDR_OVERHANG)) < 1e-3)
        p1, p40 = PL.hdr_pin(1), PL.hdr_pin(40)
        chk('pin 1 at the south end, inboard row (%.2f, %.2f)' % p1, p1[1] > p40[1] and p1[0] > p40[0])
    print('%s: %d failure(s)' % (os.path.basename(__file__), fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
