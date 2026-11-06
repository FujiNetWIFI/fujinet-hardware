#!/usr/bin/env python3
"""Point every footprint at a 3D model bundled in 3d/ (${KIPRJMOD}/3d/...), in the library AND in
the board (only the model lines change), so the 3D viewer and `kicad-cli pcb render` work on any
machine.

  * Yannick's footprints with an EasyEDA model (tools/fetch_models.py: 3d/<title>.stpZ, gzipped
    STEP): the importer's ${KIPRJMOD}/EASYEDA_MODELS/<title>.step becomes ${KIPRJMOD}/3d/<title>.stpZ,
    with the importer's offset and rotation (EasyEDA's own placement of its model on its footprint).
  * U1, the RP2354A's QFN-60 (no model id on Yannick's footprint): the RP2354A model LCSC publishes
    for C41378174, as FujiNet-ColecoVision / Arcadia Rev0 bundle it, centred, no offset.
  * D6, the SK6805-EC20 (none either): the 2 x 2 mm WS2812B-2020 stand-in the sister carts use.
  * The edge, the test pads and the holes have no model.
Usage: python3 tools/set_models.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import parse, dump, find, findall, Q

PRJ = os.path.dirname(HERE)
LIB = os.path.join(PRJ, 'Inty-FujiCard.pretty')
PCB = os.path.join(PRJ, 'Inty-FujiCard.kicad_pcb')
EXTRA = {   # footprint -> (model file in 3d/, offset, rotation): the footprints EasyEDA gave none
    'QFN-60_L7.0-W7.0-P0.40-TL-EP3.4': ('RP2354A_QFN-60_7x7.step', (0, 0, 0), (0, 0, 0)),
    'LED-SMD_4P-L2.0-W2.0-TL_J-ST2020RGB-IC-P4-5-SO1': ('LED_WS2812B-2020.wrl', (0, 0, 0), (0, 0, 0)),
}


NO_MODEL = set()            # footprints left without a model (none)


def fix(fp, name, missing):
    if name in NO_MODEL or name in EXTRA:
        fp[:] = [e for e in fp if not (isinstance(e, list) and e and e[0] == 'model')]
    models = [e for e in fp if isinstance(e, list) and e and e[0] == 'model']
    for m in models:
        old = str(m[1])
        t = re.match(r'^\$\{KIPRJMOD\}/(?:EASYEDA_MODELS|3d)/(.+?)\.(step|stpZ)$', old)
        if not t:
            raise SystemExit('%s: model %s' % (name, old))
        f = t.group(1) + '.stpZ'
        m[1] = Q('${KIPRJMOD}/3d/' + f)
        if not os.path.exists(os.path.join(PRJ, '3d', f)):
            missing.add(f)
    if not models and name in EXTRA:
        f, off, rot = EXTRA[name]
        k = next((i for i, e in enumerate(fp) if isinstance(e, list) and e and e[0] == 'embedded_fonts'), len(fp))
        fp.insert(k, ['model', Q('${KIPRJMOD}/3d/' + f), ['offset', ['xyz'] + list(off)],
                      ['scale', ['xyz', 1, 1, 1]], ['rotate', ['xyz'] + list(rot)]])
        if not os.path.exists(os.path.join(PRJ, '3d', f)):
            missing.add(f)


def main():
    missing = set()
    for fn in sorted(os.listdir(LIB)):
        name = fn[:-len('.kicad_mod')]
        t = parse(open(os.path.join(LIB, fn)).read())
        fix(t, name, missing)
        open(os.path.join(LIB, fn), 'w').write(dump(t) + '\n')
    b = parse(open(PCB).read())
    n = 0
    for e in b:
        if isinstance(e, list) and e and e[0] == 'footprint':
            fix(e, str(e[1]).split(':')[1], missing)
            n += 1
    open(PCB, 'w').write(dump(b) + '\n')
    if missing:
        raise SystemExit('no model file in 3d/ for %s (run tools/fetch_models.py)' % sorted(missing))
    print('models set on %d board footprints and %d library footprints' % (n, len(os.listdir(LIB))))


if __name__ == '__main__':
    main()
