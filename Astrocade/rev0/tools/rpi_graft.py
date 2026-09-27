#!/usr/bin/env python3
"""One-time: graft the RP2350A core-regulator corner from Raspberry Pi's
"RP2350A minimal" reference layout (RPI-RP2350A-MINIMAL_R4-S1, MIT license,
https://datasheets.raspberrypi.com/rp2350/Minimal-KiCAD.zip).

The five regulator pins 46-50 (VREG_AVDD, PGND, LX, VREG_VIN, FB) sit next to
each other at 0.4 mm pitch beside USB_DM/DP; Raspberry Pi's own placement
of the inductor, the two 4.7 uF caps, the AVDD RC and the USB series
resistors (0402, with small copper pours for LX / 1V1 / GND) is the proven
answer, so it is copied rather than re-invented.

Writes:
  FujiNet-Astrocade.pretty/RPI_*.kicad_mod        the reference's footprints
  tools/rpi_core_graft.sexpr                      part offsets + copper, relative to U1
  tools/RPI-MINIMAL-LICENSE.txt                   the reference's license
Usage: rpi_graft.py <unzipped RPI-RP2350A-MINIMAL_R4-S1_public dir>
"""
import copy, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q

SRC = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
t = parse(open(os.path.join(SRC, 'RPI-RP2350A-MINIMAL_R4-S1.kicad_pcb')).read())

# reference part -> (our ref, library footprint name we give it)
PARTS = {'U1': ('U1', 'RPI_RP2350A_QFN60'), 'L1': ('L1', 'RPI_L_AOTA-B201610S3R3'),
         'C7': ('C15', 'RPI_C0402_wide'), 'C6': ('C10', 'RPI_C0402_wide'),
         'C9': ('C16', 'RPI_C0402'), 'R3': ('R1', 'RPI_R0402'),
         'R7': ('R11', 'RPI_R0402'), 'R8': ('R12', 'RPI_R0402'), 'C12': ('C8', 'RPI_C0402')}
NETS = {'+1V1': 'DVDD', '/VREG_LX': 'RP_LX', '/VREG_AVDD': 'VREG_AVDD', '+3V3': '+3V3', 'GND': 'GND',
        'Net-(U1-USB_DP)': 'RP_USB_DP', 'Net-(U1-USB_DM)': 'RP_USB_DM', '/USB_D+': 'USB_DP',
        '/USB_D-': 'USB_DM'}
# the north cluster, in reference coordinates (U1 at 100,100)
BOX = (96.8, 90.9, 104.9, 97.35)


def ref_of(fp):
    return [str(p[2]) for p in findall(fp, 'property') if p[1] == 'Reference'][0]


def netname(e):
    n = find(e, 'net')
    return str(n[-1]) if n else None


fps = {ref_of(e): e for e in t if isinstance(e, list) and e and e[0] == 'footprint'}
ux, uy = (float(v) for v in find(fps['U1'], 'at')[1:3])
lib = os.path.join(PRJ, 'FujiNet-Astrocade.pretty')
graft = ['rpi_core_graft', ['source', Q('RPI-RP2350A-MINIMAL_R4-S1 (Raspberry Pi Ltd, MIT)')]]
written = set()
for rref, (ours, name) in PARTS.items():
    fp = fps[rref]
    at = find(fp, 'at')
    x, y = float(at[1]), float(at[2])
    rot = float(at[3]) if len(at) > 3 else 0.0
    graft.append(['part', Q(ours), Q(name), ['at', round(x - ux, 4), round(y - uy, 4), rot]])
    if name in written:
        continue
    written.add(name)
    # board footprint -> library footprint: angles back to footprint-relative, no nets
    lf = ['footprint', Q(name), ['version', 20241229], ['generator', Q('fujinet_gen')],
          ['generator_version', Q('1.0')], ['layer', Q('F.Cu')],
          ['descr', Q('From Raspberry Pi RP2350A minimal design (MIT): %s' % str(fp[1]))]]
    for e in fp[1:]:
        if not isinstance(e, list) or not e:
            continue
        k = e[0]
        if k in ('layer', 'uuid', 'at', 'path', 'sheetname', 'sheetfile', 'descr', 'tags'):
            continue
        e = copy.deepcopy(e)
        if k in ('property', 'fp_text', 'pad'):
            a = find(e, 'at')
            if a and len(a) > 3:
                ang = (float(a[3]) - rot) % 360
                a[:] = a[:3] + ([ang] if ang else [])
            e = [x for x in e if not (isinstance(x, list) and x and x[0] in ('net', 'uuid', 'pinfunction', 'pintype'))]
            if k == 'property' and e[1] in ('Reference', 'Value'):
                e[2] = Q('REF**' if e[1] == 'Reference' else name)
            if k == 'property' and e[1] not in ('Reference', 'Value'):
                continue
        if k == 'model':
            continue
        lf.append(e)
    open(os.path.join(lib, name + '.kicad_mod'), 'w').write(dump(lf) + '\n')


def inside(xs, ys):
    return min(xs) >= BOX[0] and max(xs) <= BOX[2] and min(ys) >= BOX[1] and max(ys) <= BOX[3]


for e in t:
    if not (isinstance(e, list) and e):
        continue
    n = netname(e)
    if e[0] in ('segment', 'via', 'zone') and n not in NETS:
        continue
    if e[0] == 'segment':
        s, en = find(e, 'start'), find(e, 'end')
        xs, ys = [float(s[1]), float(en[1])], [float(s[2]), float(en[2])]
        if inside(xs, ys):
            graft.append(['segment', ['start', round(xs[0] - ux, 4), round(ys[0] - uy, 4)],
                          ['end', round(xs[1] - ux, 4), round(ys[1] - uy, 4)], ['width', float(find(e, 'width')[1])],
                          ['layer', Q(str(find(e, 'layer')[1]))], ['net', Q(NETS[n])]])
    elif e[0] == 'via':
        a = find(e, 'at')
        # (the two 1V1 vias drop the regulator output onto the DVDD island under the chip)
        if inside([float(a[1])], [float(a[2])]):
            graft.append(['via', ['at', round(float(a[1]) - ux, 4), round(float(a[2]) - uy, 4)], ['net', Q(NETS[n])]])
    elif e[0] == 'zone':
        pts = [(float(p[1]), float(p[2])) for p in find(find(e, 'polygon'), 'pts')[1:]]
        if inside([p[0] for p in pts], [p[1] for p in pts]):
            pr = find(e, 'priority')
            cp = find(e, 'connect_pads')
            graft.append(['zone', ['net', Q(NETS[n])], ['layer', Q(str(find(e, 'layer')[1]))],
                          ['priority', int(pr[1]) if pr else 0],
                          ['connect', str(cp[1]) if cp and len(cp) > 1 and not isinstance(cp[1], list) else 'thermal'],
                          ['clearance', float(find(cp, 'clearance')[1]) if cp and find(cp, 'clearance') else 0.15],
                          ['min_thickness', float(find(e, 'min_thickness')[1])],
                          ['pts'] + [['xy', round(x - ux, 4), round(y - uy, 4)] for x, y in pts]])
open(os.path.join(HERE, 'rpi_core_graft.sexpr'), 'w').write(dump(graft) + '\n')
shutil.copy(os.path.join(SRC, 'LICENSE.txt'), os.path.join(HERE, 'RPI-MINIMAL-LICENSE.txt'))
print('\n'.join(dump(x) for x in graft if x[0] in ('part', 'zone')))
print(sum(1 for x in graft if x[0] == 'segment'), 'segments', sum(1 for x in graft if x[0] == 'via'), 'vias')
