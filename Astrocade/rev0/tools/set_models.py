#!/usr/bin/env python3
"""Point every footprint at a 3D model bundled in 3d/ (${KIPRJMOD}/3d/...),
in the library AND in the board (without touching routing), so the 3D
viewer / `kicad-cli pcb render` works on any machine -- no dependency on
KiCad's optional 3D-model package.

Model sources (see 3d/README.md): KiCad's own kicad-packages3D for stock
footprints; LCSC/EasyEDA models (easyeda2kicad) for the parts KiCad has none
for (RP2354A QFN-60, Abracon AOTA inductor, HRO USB-C); a simple VRML
stand-in for the WS2812B-2020 (no vendor model published).

Usage: python3 tools/set_models.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, Q

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
LIB = os.path.join(PRJ, 'FujiNet-Astrocade.pretty')
PCB = os.path.join(PRJ, 'FujiNet-Astrocade-Rev0.kicad_pcb')

# footprint -> (model file in 3d/, offset xyz mm (KiCad 3D: +y is up), rotate xyz deg)
MODELS = {
    'C_0603_1608Metric': ('C_0603_1608Metric.step', (0, 0, 0), (0, 0, 0)),
    'C_0805_2012Metric': ('C_0805_2012Metric.step', (0, 0, 0), (0, 0, 0)),
    'RPI_C0402': ('C_0402_1005Metric.step', (0, 0, 0), (0, 0, 0)),
    'RPI_C0402_wide': ('C_0402_1005Metric.step', (0, 0, 0), (0, 0, 0)),
    'R_0603_1608Metric': ('R_0603_1608Metric.step', (0, 0, 0), (0, 0, 0)),
    'RPI_R0402': ('R_0402_1005Metric.step', (0, 0, 0), (0, 0, 0)),
    'R_Array_Convex_4x0603': ('R_Array_Convex_4x0603.step', (0, 0, 0), (0, 0, 0)),
    'LED_0603_1608Metric': ('LED_0603_1608Metric.step', (0, 0, 0), (0, 0, 0)),
    'LED_WS2812B-2020_PLCC4_2.0x2.0mm': ('LED_WS2812B-2020.wrl', (0, 0, 0), (0, 0, 0)),
    'D_SMA': ('D_SMA.step', (0, 0, 0), (0, 0, 0)),
    'D_SOD-523': ('D_SOD-523.step', (0, 0, 0), (0, 0, 0)),
    'SOT-23': ('SOT-23.step', (0, 0, 0), (0, 0, 0)),
    'SOT-363_SC-70-6': ('SOT-363_SC-70-6.step', (0, 0, 0), (0, 0, 0)),
    'TSOT-23-6': ('TSOT-23-6.step', (0, 0, 0), (0, 0, 0)),
    'SOT-23-5': ('SOT-23-5.step', (0, 0, 0), (0, 0, 0)),
    'Crystal_SMD_3225-4Pin_3.2x2.5mm': ('Crystal_SMD_3225-4Pin_3.2x2.5mm.step', (0, 0, 0), (0, 0, 0)),
    'L_Sunlord_SWPA4030S': ('L_Sunlord_SWPA4030S.step', (0, 0, 0), (0, 0, 0)),
    'RPI_L_AOTA-B201610S3R3': ('AOTA-B201610S3R3.step', (0, 0, 0), (0, 0, 0)),
    'QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm': ('QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm.step', (0, 0, 0), (0, 0, 0)),
    'RPI_RP2350A_QFN60': ('RP2354A_QFN-60_7x7.step', (0, 0, 0), (0, 0, 0)),
    'ESP32-S3-WROOM-1': ('ESP32-S3-WROOM-1.step', (0, 0, 0), (0, 0, 0)),
    'SW_SPST_TL3342': ('SW_SPST_TL3342.step', (0, 0, 0), (0, 0, 0)),
    # LCSC model origin is 1.42 mm behind KiCad's footprint origin (shell tabs)
    'USB_C_Receptacle_HRO_TYPE-C-31-M-12': ('USB-C_HRO_TYPE-C-31-M-12.step', (0, 1.42, 0), (0, 0, 180)),
    'TF-SMD_TF-015': ('TF-015.step', (0, 0, 0), (0, 0, 0)),
}


def model(name):
    f, off, rot = MODELS[name]
    return ['model', Q('${KIPRJMOD}/3d/' + f), ['offset', ['xyz'] + list(off)],
            ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz'] + list(rot)]]


def set_model(fp, name):
    fp[:] = [e for e in fp if not (isinstance(e, list) and e and e[0] == 'model')]
    if name in MODELS:
        k = next((i for i, e in enumerate(fp) if isinstance(e, list) and e and e[0] == 'embedded_fonts'), len(fp))
        fp.insert(k, model(name))


for fn in sorted(os.listdir(LIB)):
    name = fn[:-len('.kicad_mod')]
    t = parse(open(os.path.join(LIB, fn)).read())
    set_model(t, name)
    open(os.path.join(LIB, fn), 'w').write(dump(t) + '\n')
    for f, *_ in [MODELS[name]] if name in MODELS else []:
        assert os.path.exists(os.path.join(PRJ, '3d', f)), f

b = parse(open(PCB).read())
n = 0
for e in b:
    if isinstance(e, list) and e and e[0] == 'footprint':
        set_model(e, str(e[1]).split(':')[1])
        n += 1
open(PCB, 'w').write(dump(b) + '\n')
missing = sorted({fn[:-10] for fn in os.listdir(LIB)} - set(MODELS))
print('models set on %d board footprints; no model (by design): %s' % (n, ', '.join(missing)))
