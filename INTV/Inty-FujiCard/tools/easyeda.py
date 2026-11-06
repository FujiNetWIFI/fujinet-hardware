"""Reading Yannick Erb's EasyEDA Std board JSON (Original/PCB_*.json) where KiCad's importer falls short.

EasyEDA Std stores coordinates in units of 10 mil (0.254 mm), y down; the JSON head's (x, y) is the
board's lower-left corner, which KiCad 10.0.8's importer puts at (120, 140) mm (and EasyEDA's own
gerbers at (0, 0)).  Shared by tools/convert.py and tools/audit/gerber_equiv.py.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
SRC = os.path.join(PRJ, 'Original', 'PCB_PINTY-FUJI-CARD-PCB-v1.1_2026-11-04.json')
KI_ORIGIN = (120.0, 140.0)      # mm: where KiCad's importer puts the JSON head's (x, y)
UNIT = 0.254                    # mm per EasyEDA unit
_doc = None


def doc():
    global _doc
    if _doc is None:
        _doc = json.load(open(SRC))
    return _doc


def origin():
    h = doc()['head']
    return float(h['x']), float(h['y'])


def kicad_mm(x, y):
    """EasyEDA units -> KiCad mm (absolute, y down)."""
    ox, oy = origin()
    return KI_ORIGIN[0] + (x - ox) * UNIT, KI_ORIGIN[1] + (y - oy) * UNIT


def libs():
    """[(reference, [part fields])] for every footprint (LIB record)."""
    out = []
    for s in doc()['shape']:
        if s.startswith('LIB~'):
            parts = [p.split('~') for p in s.split('#@$')]
            ref = next(f[10] for f in parts if f[0] == 'TEXT' and f[1] == 'P')
            out.append((ref, parts))
    return out


def texts():
    """Every TEXT record (board-level and inside footprints):
    dict(text, kind 'P' reference / 'N' value / 'L' plain, layer (EasyEDA id), shown,
    angle (deg), owner (the footprint's reference or None), ink (x0, y0, x1, y1) KiCad mm, the
    bounding box of EasyEDA's own glyph strokes (field 11, the centre lines))."""
    rows = [(None, s.split('~')) for s in doc()['shape'] if s.startswith('TEXT~')]
    for ref, parts in libs():
        rows += [(ref, f) for f in parts if f[0] == 'TEXT']
    out = []
    for owner, f in rows:
        v = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', f[11])]
        pts = [kicad_mm(x, y) for x, y in zip(v[0::2], v[1::2])]
        ink = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) \
            if pts else None
        out.append(dict(text=f[10], kind=f[1], layer=f[7], shown=f[12] != 'none', angle=float(f[5]) % 360,
                        owner=owner, ink=ink))
    return out
