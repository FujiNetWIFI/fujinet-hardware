#!/usr/bin/env python3
"""One-time: graft the RP2350 core-regulator corner from Raspberry Pi's "RP2350A minimal" reference
layout (RPI-RP2350A-MINIMAL_R4-S1, MIT license: tools/RPI-MINIMAL-LICENSE.txt,
https://datasheets.raspberrypi.com/rp2350/Minimal-KiCAD.zip) onto the RP2354B's QFN-80.

Raspberry Pi publishes the minimal design for the QFN-60 only.  The five regulator pins (VREG_AVDD,
PGND, LX, VREG_VIN, FB), USB_DM / DP, USB_OTP_VDD and QSPI_IOVDD sit in the same order at the same
0.4 mm pitch on both packages, starting at the same corner of the same side: QFN-60 pins 46-54 at
x 2.8 .. -0.4 on its north row (y -3.45), QFN-80 pins 61-69 at x 3.8 .. 0.6 on its north row (y
-4.95).  So the reference's parts and copper in front of those pins move by (+1.0, -1.5) and land on
the QFN-80 exactly as they sat on the QFN-60.  Only that corner is taken: the reference's
inductor, its two 4.7 uF (VREG_VIN, DVDD out), the VREG_AVDD RC, the USB 27R and the 100 nF on
USB_OTP_VDD / QSPI_IOVDD, with the small copper pours and traces between them and the pins.
Dropped: its QSPI flash lines (the RP2354B has its flash inside), the 0.8 mm USB lines toward its
connector, the copper on the corner pins of the next side (QFN-60 44 / 45: the QFN-80's corner is
0.5 mm further out), the under-package +3V3 / +1V1 rings, bar and B.Cu link (gen_pcb.rp_support
draws this board's, sized for the QFN-80).

Writes tools/rpi_core_graft.sexpr: parts (by this board's design.py key) and copper in the QFN-80's
rotation-0 frame, relative to its centre; gen_pcb.graft_parts / graft_copper turn it with the RP.
The RPI_* footprints in FujiNet-O2.pretty are the reference's (via Fujiversal-Atari2600 Rev1,
whose tools/rpi_graft.py wrote them from the same file).

Usage: rpi_graft.py <RPI-RP2350A-MINIMAL_R4-S1.kicad_pcb>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q

HERE = os.path.dirname(os.path.abspath(__file__))
DX, DY = 1.0, -1.5                        # QFN-60 pin 46 (2.8, -3.45) -> QFN-80 pin 61 (3.8, -4.95)
# reference designator -> (this board's key, footprint)
PARTS = {'L1': ('L_RP', 'RPI_L_AOTA-B201610S3R3'), 'C6': ('C_VREGIN', 'RPI_C0402_wide'),
         'C7': ('C_DVBULK', 'RPI_C0402_wide'), 'C9': ('C_AVDD', 'RPI_C0402'), 'R3': ('R_AVDD', 'RPI_R0402'),
         'R7': ('R_USBP', 'RPI_R0402'), 'R8': ('R_USBM', 'RPI_R0402'), 'C12': ('C_OTP', 'RPI_C0402')}
# the reference's net names -> this board's (design.py)
NETS = {'+1V1': 'DVDD', '/VREG_LX': 'RP_LX', '/VREG_AVDD': 'VREG_AVDD', '+3V3': '+3V3', 'GND': 'GND',
        'Net-(U1-USB_DP)': 'RP_USB_DP', 'Net-(U1-USB_DM)': 'RP_USB_DM', '/USB_D+': 'USB_DP', '/USB_D-': 'USB_DM'}
# the corner, in the reference's U1-relative frame: x -2.6 .. 4.7, y -9.0 .. -3.0 (the pads' outer half on)
BOX = (-2.6, -9.0, 4.7, -3.0)


def ref_of(fp):
    return [str(p[2]) for p in findall(fp, 'property') if p[1] == 'Reference'][0]


def main(fn):
    t = parse(open(fn).read())
    netnames = {str(e[1]): str(e[2]) for e in t if isinstance(e, list) and e and e[0] == 'net' and len(e) > 2}
    nm = lambda e: (lambda n: netnames.get(str(n[1]), str(n[-1])) if n else None)(find(e, 'net'))
    fps = {ref_of(e): e for e in t if isinstance(e, list) and e and e[0] == 'footprint'}
    u = fps['U1']
    ux, uy = (float(v) for v in find(u, 'at')[1:3])
    assert len(find(u, 'at')) < 4 or float(find(u, 'at')[3]) == 0
    pads = {str(p[1]): (float(find(p, 'at')[1]), float(find(p, 'at')[2]), nm(p)) for p in findall(u, 'pad')}
    # the pin row this graft relies on: 46-54 = AVDD PGND LX VIN FB DM DP OTP QSPI_IOVDD at 0.4 mm
    want = ['/VREG_AVDD', 'GND', '/VREG_LX', '+3V3', '+1V1', 'Net-(U1-USB_DM)', 'Net-(U1-USB_DP)', '+3V3', '+3V3']
    for i, n in enumerate(range(46, 55)):
        x, y, net = pads[str(n)]
        assert abs(x - (2.8 - 0.4 * i)) < 1e-3 and abs(y + 3.45) < 1e-3 and net == want[i], (n, x, y, net)
    mv = lambda x, y: (round(x - ux + DX, 4), round(y - uy + DY, 4))
    inb = lambda x, y: BOX[0] <= x - ux <= BOX[2] and BOX[1] <= y - uy <= BOX[3]
    out = ['rpi_core_graft', ['source', Q('RPI-RP2350A-MINIMAL_R4-S1 (Raspberry Pi Ltd, MIT), QFN-60 -> QFN-80 '
                                           'shift (%g, %g)' % (DX, DY))]]
    for r, (key, name) in PARTS.items():
        e = fps[r]
        a = find(e, 'at')
        assert str(e[1]).split(':')[-1] and r in fps
        rot = float(a[3]) if len(a) > 3 else 0.0
        pn = {str(p[1]): NETS[nm(p)] for p in findall(e, 'pad')}
        out.append(['part', Q(key), Q(name), ['at', *mv(float(a[1]), float(a[2])), rot],
                    ['pads'] + [[Q(k), Q(v)] for k, v in sorted(pn.items())]])
    keep = 0
    for e in t:
        if not (isinstance(e, list) and e) or e[0] not in ('segment', 'via', 'zone'):
            continue
        net = nm(e)
        if net not in NETS:                       # QSPI, GPIO, ...
            continue
        if e[0] == 'segment':
            s_, t_ = find(e, 'start'), find(e, 'end')
            a, b = (float(s_[1]), float(s_[2])), (float(t_[1]), float(t_[2]))
            if not (inb(*a) or inb(*b)):
                continue
            if str(find(e, 'layer')[1]) != 'F.Cu' or net in ('/USB_D+', '/USB_D-'):
                continue                          # the B.Cu 1V1 link and the 0.8 mm USB lines
            if min(abs(a[1] - uy), abs(b[1] - uy)) < 3.0 and max(abs(a[1] - uy), abs(b[1] - uy)) <= 3.45 \
                    and not (abs(a[1] - uy) > 3.4 or abs(b[1] - uy) > 3.4):
                continue                          # wholly under the package: rp_support's rings instead
            if min(abs(a[1] - uy), abs(b[1] - uy)) < 3.3:
                continue                          # the inward stubs to the reference's bar / rings
            if max(a[0] - ux, b[0] - ux) > 3.35 and net == '+3V3':
                continue                          # QFN-60 pins 44 / 45 (the next side's corner)
            out.append(['segment', ['start', *mv(*a)], ['end', *mv(*b)], ['width', float(find(e, 'width')[1])],
                        ['layer', Q('F.Cu')], ['net', Q(NETS[net])]])
            keep += 1
        elif e[0] == 'via':
            a = find(e, 'at')
            x, y = float(a[1]), float(a[2])
            if not inb(x, y) or abs(y - uy) < 3.3:
                continue
            out.append(['via', ['at', *mv(x, y)], ['size', float(find(e, 'size')[1])],
                        ['drill', float(find(e, 'drill')[1])], ['net', Q(NETS[net])]])
            keep += 1
        else:
            pts = [(float(p[1]), float(p[2])) for p in find(find(e, 'polygon'), 'pts')[1:]]
            if not all(BOX[0] <= x - ux <= BOX[2] and BOX[1] <= y - uy <= -2.6 for x, y in pts):
                continue                          # the under-package rings (the VIN pour starts 0.4 under the pad)
            cp = find(e, 'connect_pads')
            out.append(['zone', ['net', Q(NETS[net])], ['layer', Q(str(find(e, 'layer')[1]))],
                        ['priority', int(find(e, 'priority')[1])],
                        ['clearance', float(find(cp, 'clearance')[1])],
                        ['min_thickness', float(find(e, 'min_thickness')[1])],
                        ['pts'] + [['xy', *mv(x, y)] for x, y in pts]])
            keep += 1
    open(os.path.join(HERE, 'rpi_core_graft.sexpr'), 'w').write(dump(out) + '\n')
    print('graft: %d parts, %d copper items -> tools/rpi_core_graft.sexpr' % (len(PARTS), keep))


if __name__ == '__main__':
    main(sys.argv[1])
