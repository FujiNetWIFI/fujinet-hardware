#!/usr/bin/env python3
"""Fetch the 3D models of Yannick's footprints from EasyEDA (the models his board was drawn with).

Each footprint carries EasyEDA's model id (its JLC_3DModel field, kept by tools/convert.py) and the
importer's model reference, ${KIPRJMOD}/EASYEDA_MODELS/<title>.step, with the offsets EasyEDA uses.
This downloads every model by id from EasyEDA's model server (easyeda2kicad's endpoint) into a new,
empty directory, checks each is a STEP file (ISO-10303-21 header), normalises it (below) and writes
it gzipped as 3d/<title>.stpZ (KiCad reads compressed STEP; the SolidWorks exports are 10x smaller
so).  tools/set_models.py then points the board and the library at them.

Normalising: EasyEDA places a model by its solid's bounding box -- the box's xy centre on the
footprint's 3D origin, its bottom on the board surface plus the node's z -- and KiCad's importer
writes those offsets as if every model's own origin were that centre and bottom.  Most of these
models are centred, but not all are: the microSD socket's solid sits 29 mm off its origin and 4-6 mm
below it (under the board: only its pads showed), the SOD-523 diodes wholly below the surface, the
0402 / 0603 parts half in it.  So every 3D point of each model is moved by the same vector (a rigid
translation) to put its vertices' box centre at the origin and their lowest point at z = 0, which
makes the importer's offsets right.

Usage: python3 tools/fetch_models.py [--out DIR]     (default: 3d/ in the project)
"""
import gzip, json, os, re, sys, tempfile, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
URL = 'https://modules.easyeda.com/qAxj6KHrDKw4blvCG8QJPs7Y/%s'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'


def models():
    """{title: uuid} from the board's footprints."""
    import pcbnew
    b = pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(os.path.join(PRJ, 'Inty-FujiCard.kicad_pcb'), None)
    out = {}
    for f in b.GetFootprints():
        if not f.HasField('JLC_3DModel'):
            continue
        uid = f.GetFieldText('JLC_3DModel')
        for m in f.Models():
            t = re.sub(r'\.step$', '', os.path.basename(m.m_Filename))
            if out.setdefault(t, uid) != uid:
                raise SystemExit('model %s: two ids %s / %s' % (t, out[t], uid))
    return out


def fetch(uid):
    for attempt in range(4):
        try:
            req = urllib.request.Request(URL % uid, headers={'User-Agent': UA})
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:                       # rate limit or a dropped connection: back off
            if attempt == 3:
                raise SystemExit('model %s: %s' % (uid, e))
            time.sleep(10 * (attempt + 1))


REP = re.compile(rb"=\s*(?:ADVANCED_BREP_SHAPE_REPRESENTATION|SHAPE_REPRESENTATION|MANIFOLD_SURFACE_SHAPE_REPRESENTATION)"
                 rb"\s*\(\s*'[^']*'\s*,\s*\(([^)]*)\)")
PT3 = re.compile(rb"(#\d+\s*=\s*CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\()\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)")


def normalise(data):
    """The STEP with every 3D point of its solids moved so that their vertex box is centred on the
    origin in x and y and its lowest vertex is at z = 0 (EasyEDA's placement convention); 2D points
    (curve parameters) and the representation's own placement are not touched.  Returns (data, the
    shift)."""
    pts = {}
    for m in re.finditer(rb"#(\d+)\s*=\s*CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)", data):
        pts[m.group(1)] = tuple(float(m.group(k)) for k in (2, 3, 4))
    vs = [pts[m.group(1)] for m in re.finditer(rb"VERTEX_POINT\s*\(\s*'[^']*'\s*,\s*#(\d+)", data) if m.group(1) in pts]
    if not vs:
        raise SystemExit('a model without vertices')
    lo = [min(v[i] for v in vs) for i in range(3)]
    hi = [max(v[i] for v in vs) for i in range(3)]
    d = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    if max(abs(x) for x in d) < 1e-6:
        return data, d
    # the shape representation's own placement (its AXIS2_PLACEMENT_3D item, at the origin) stays:
    # KiCad's STEP reader places the solids through it, so moving it as well moves them twice
    keep = set()
    for m in REP.finditer(data):
        for ref in re.findall(rb'#(\d+)', m.group(1)):
            a = re.search(rb'#%s\s*=\s*AXIS2_PLACEMENT_3D\s*\(\s*\'[^\']*\'\s*,\s*#(\d+)' % ref, data)
            if a:
                keep.add(a.group(1))

    def f(m):
        pid = re.match(rb'#(\d+)', m.group(0)).group(1)
        if pid in keep:
            return m.group(0)
        return m.group(1) + (b' %r, %r, %r )' % tuple(float(m.group(k + 2)) + d[k] for k in range(3)))
    out = PT3.sub(f, data)
    return out, d


def main():
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(PRJ, '3d')
    os.makedirs(out, exist_ok=True)
    want = models()
    tmp = tempfile.mkdtemp(prefix='inty-models-')
    total = 0
    for title, uid in sorted(want.items()):
        data = fetch(uid)
        if not data.startswith(b'ISO-10303-21;'):
            raise SystemExit('model %s (%s) is not a STEP file' % (title, uid))
        open(os.path.join(tmp, title + '.step'), 'wb').write(data)
        data, shift = normalise(data)
        z = gzip.compress(data, 9, mtime=0)
        open(os.path.join(out, title + '.stpZ'), 'wb').write(z)
        total += len(z)
        print('%-48s %s  %7d -> %6d bytes, moved (%.3f, %.3f, %.3f) mm' % ((title, uid, len(data), len(z)) + shift))
        time.sleep(2)                                # stay under the rate limit
    json.dump(want, open(os.path.join(out, 'easyeda_models.json'), 'w'), indent=1, sort_keys=True)
    print('%d models, %.1f MB compressed, in %s' % (len(want), total / 1e6, out))


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        print(e, flush=True)
        os._exit(1 if e.code else 0)
    sys.stdout.flush()
    os._exit(0)
