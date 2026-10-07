#!/usr/bin/env python3
"""Measure JLCPCB CPL rotation corrections and origin offsets for FujiNet-SMS Rev0.

JLCPCB places every part by the EasyEDA footprint behind its LCSC code, not by
our KiCad footprint.  For each (footprint, LCSC) pair in tools/design.py this
script compares our .kicad_mod pad by pad with that EasyEDA footprint and
writes jlc_rotations.json (same schema as the Fujiversal-Atari2600 Rev1 table):

  rotation_correction_deg  add to the KiCad rotation in the CPL (EasyEDA
                           footprint rotated CCW by this lands on ours)
  origin_offset_mm         where the EasyEDA placement origin sits in OUR
                           footprint frame (KiCad, +y down), in mm

Method (per pair):
  * EasyEDA: https://easyeda.com/api/products/<LCSC>/components (the endpoint
    easyeda2kicad uses), cached in easyeda_cache/<LCSC>.json so reruns are
    offline.  Units are 10 mil (0.254 mm), +y down like KiCad, origin =
    dataStr.head.x/y (the footprint origin EasyEDA / JLC place by).
  * Pads are matched by number: identity, EasyEDA merged numbers ('A1B12' ->
    our A1 and B12), diode/LED polarity by symbol pin NAME (K/C vs A, so an
    EasyEDA LED whose pad 2 is the cathode is matched cathode-to-cathode),
    then leftovers (shell tabs, switch contacts) by geometry.  If the numbers
    do not fit at all (e.g. a 4-pad switch numbered 1,1,2,2 vs 1,2,3,4) the
    pads are matched by geometry only and the entry says so.  Pads sharing a
    number (EP + thermal vias, shell tabs) are compared as a group (copper
    bbox centre).  Unnumbered pads (paste windows) are ignored.
  * Rotation: the one of 0/90/180/270 that minimises the RMS pad-group error
    after centring.  The number-agnostic pattern RMS is also computed to
    detect symmetric patterns (where only the numbering decides).
  * Offset: copper-bbox centre difference (robust to SOT-23-style 2+1 pad
    layouts, where a least-squares fit is biased); if both footprints have
    NPTH pegs, the mechanical features (pegs + plated THT pads) are aligned
    instead, because the pegs physically locate the part.  Components below
    0.02 mm are reported as 0.
  * Sanity: pin-1 angle about the pad-pattern centre in both footprints
    (their difference must agree with the correction), EasyEDA's layer-101
    pin-1 marker, polarity by symbol pin names, the package-name pin-1
    suffix (-TL/-BL/-BR/...).

Footprint data: EasyEDA / JLCEDA official library (https://easyeda.com,
https://lceda.cn), fetched through the public component API.

Usage:
  python3 tools/audit/jlc/measure_rotations.py            # cache-first
  python3 tools/audit/jlc/measure_rotations.py --refresh  # re-fetch everything
  python3 tools/audit/jlc/measure_rotations.py --offline  # never touch the network
"""
import argparse, json, math, os, re, sys, time
import urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
PRJ = os.path.dirname(TOOLS)
CACHE = os.path.join(HERE, 'easyeda_cache')
OUT = os.path.join(HERE, 'jlc_rotations.json')
sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True
import design as D  # noqa: E402

PRETTY = os.path.join(PRJ, D.LIB + '.pretty')
SYMCACHE = os.path.join(TOOLS, 'symcache.sexpr')
PROJECT_SYMLIB = os.path.join(PRJ, D.LIB + '.kicad_sym')

API = 'https://easyeda.com/api/products/%s/components?version=6.4.19.5'
# easyeda.com sits behind CloudFront, which answers 403 to non-browser
# User-Agents (including easyeda2kicad's) and also when rate limited.
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/120.0 Safari/537.36')
MIL10 = 0.254           # EasyEDA unit -> mm
DEADBAND = 0.02         # offsets below this (mm) are reported as 0
ROTS = (0, 90, 180, 270)

# LCSC codes with no EasyEDA component: measure against EasyEDA footprints of
# the same package on other LCSC codes and say so (confidence 'low').
# C5569980 (AS6C4008-55TIN, LCSC package 'TSOPI-32'): no EasyEDA component.
# The EasyEDA library has two TSOP-I-32 8x20 footprints, 90 deg apart:
#   TSOPI-32_L18.4-W8.0-P0.50-LS20.0-TL  (C2944637 CY62128ELL-45ZXI, C6883917 IS62WV1288)
#   TSOP-32_L8.0-W18.4-P0.50-LS20.0-BL   (C20481033 R1LV0108ESF)
# The first one listed is the primary (its name matches LCSC's 'TSOPI-32').
PROXIES = {'C5569980': ['C2944637', 'C6883917', 'C20481033']}

CATHODE = {'K', 'C', 'CATHODE', '-', 'KA'}
ANODE = {'A', 'ANODE', '+', 'AK'}


# ---------------------------------------------------------------- utilities
def r3(v):
    return round(v + 0.0, 3) + 0.0


def wrap180(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def rot_pt(p, r):
    """Rotate (x, y) [y down] CCW-on-screen by r degrees (r multiple of 90 or any)."""
    t = math.radians(r)
    c, s = round(math.cos(t), 12), round(math.sin(t), 12)
    x, y = p
    return (x * c + y * s, -x * s + y * c)


def rect_corners(x, y, w, h, a):
    """Corners of a w x h rectangle centred on (x, y), rotated by a deg (sign irrelevant for bbox)."""
    t = math.radians(a)
    c, s = math.cos(t), math.sin(t)
    out = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        out.append((x + dx * c + dy * s, y - dx * s + dy * c))
    return out


def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def bbox_centre(pts):
    x0, y0, x1, y1 = bbox(pts)
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


# ---------------------------------------------------------------- s-expressions
def sexpr(text):
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack, cur = [], []
    for t in toks:
        if t == '(':
            stack.append(cur)
            cur = []
        elif t == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
    return cur[0]


def find(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def find_all(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


# ---------------------------------------------------------------- KiCad side
class Pad:
    def __init__(self, num, x, y, extents, kind, drill=0.0):
        self.num, self.pos, self.ext, self.kind, self.drill = num, (x, y), extents, kind, drill

    def moved(self, f):
        return Pad(self.num, *f(self.pos), [f(p) for p in self.ext], self.kind, self.drill)


def kicad_footprint(name):
    fp = sexpr(open(os.path.join(PRETTY, name + '.kicad_mod')).read())
    pads, npth = [], []
    for p in find_all(fp, 'pad'):
        num, kind, shape = p[1], p[2], p[3]
        at = [float(v) for v in find(p, 'at')[1:]]
        x, y, a = at[0], at[1], (at[2] if len(at) > 2 else 0.0)
        w, h = [float(v) for v in find(p, 'size')[1:3]]
        layers = find(p, 'layers')[1:] if find(p, 'layers') else []
        drill = find(p, 'drill')
        dval = 0.0
        if drill:
            nums = [float(v) for v in drill[1:] if not isinstance(v, list) and re.match(r'^-?[\d.]+$', v)]
            dval = min(nums) if nums else 0.0
        if kind == 'np_thru_hole':
            npth.append(((x, y), dval or w))
            continue
        if not num:
            continue                      # paste windows, unnumbered copper
        if not any(l.endswith('.Cu') or l == '*.Cu' for l in layers):
            continue
        ext = rect_corners(x, y, w, h, a)
        prim = find(p, 'primitives')
        if shape == 'custom' and prim:
            for g in prim[1:]:
                if not isinstance(g, list):
                    continue
                pts = []
                if g[0] == 'gr_poly' and find(g, 'pts'):
                    pts = [(float(q[1]), float(q[2])) for q in find(g, 'pts')[1:] if q[0] == 'xy']
                elif g[0] in ('gr_rect', 'gr_line'):
                    pts = [tuple(float(v) for v in find(g, 'start')[1:3]),
                           tuple(float(v) for v in find(g, 'end')[1:3])]
                elif g[0] == 'gr_circle':
                    c = [float(v) for v in find(g, 'center')[1:3]]
                    e = [float(v) for v in find(g, 'end')[1:3]]
                    rr = math.hypot(e[0] - c[0], e[1] - c[1])
                    pts = [(c[0] - rr, c[1] - rr), (c[0] + rr, c[1] + rr)]
                # primitives are relative to the pad, in the pad's rotated frame
                for q in pts:
                    qx, qy = rot_pt(q, a)
                    ext.append((x + qx, y + qy))
        pads.append(Pad(num, x, y, ext, 'tht' if kind == 'thru_hole' else 'smd', dval))
    return pads, npth


def kicad_pin_names(lib_id):
    """pin number -> name from the harvested stock symbols (or the project library)."""
    out = {}
    lib, _, name = lib_id.partition(':')
    for path in (SYMCACHE, PROJECT_SYMLIB):
        if not os.path.exists(path):
            continue
        text = open(path).read()
        key = '(symbol "%s"' % (lib_id if path == SYMCACHE else name)
        i = text.find(key)
        if i < 0:
            continue
        # cut this symbol's s-expression out by paren matching
        depth, j = 0, i
        while True:
            ch = text[j]
            if ch == '"':
                j = text.index('"', j + 1)
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        for m in re.finditer(r'\(name "([^"]*)".*?\(number "([^"]*)"', text[i:j + 1], re.S):
            out[m.group(2)] = m.group(1)
        if out:
            return out
    return out


# ---------------------------------------------------------------- EasyEDA side
def fetch(lcsc, refresh=False, offline=False):
    fn = os.path.join(CACHE, lcsc + '.json')
    if os.path.exists(fn) and not refresh:
        return json.load(open(fn))
    if offline:
        return None
    os.makedirs(CACHE, exist_ok=True)
    req = urllib.request.Request(API % lcsc, headers={
        'User-Agent': UA, 'Accept': 'application/json, text/javascript, */*; q=0.01'})
    last = None
    for attempt in range(6):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
            break
        except urllib.error.HTTPError as e:      # 403 = CloudFront rate limit / UA block
            last = e
            time.sleep(10 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(5)
    else:
        print('  fetch %s failed: %s' % (lcsc, last), file=sys.stderr)
        return None
    with open(fn, 'w') as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    time.sleep(2)                                # stay under the rate limit
    return data


class EasyEDA:
    def __init__(self, data):
        res = data['result']
        self.part = res.get('title', '')
        pkg = res['packageDetail']
        self.package = pkg.get('title', '')
        ds = pkg['dataStr']
        ox, oy = float(ds['head']['x']), float(ds['head']['y'])
        cv = lambda x, y: ((float(x) - ox) * MIL10, (float(y) - oy) * MIL10)
        self.pads, self.holes, self.markers = [], [], []
        for s in ds['shape']:
            f = s.split('~')
            if f[0] == 'PAD':
                shape, x, y, w, h, layer, num = f[1], f[2], f[3], float(f[4]), float(f[5]), f[6], f[8]
                hole_r = float(f[9] or 0) * MIL10
                rot = float(f[11] or 0)
                plated = (f[15] if len(f) > 15 else 'Y') != 'N'
                c = cv(x, y)
                if shape == 'POLYGON' and f[10].strip():
                    v = [float(t) for t in f[10].split()]
                    ext = [cv(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
                else:
                    ext = rect_corners(c[0], c[1], w * MIL10, h * MIL10, rot)
                if not plated:
                    self.holes.append((c, 2 * hole_r))
                    continue
                kind = 'tht' if (layer == '11' and hole_r > 0) else 'smd'
                self.pads.append(Pad(num, c[0], c[1], ext, kind, 2 * hole_r))
            elif f[0] == 'HOLE':
                self.holes.append((cv(f[1], f[2]), 2 * float(f[3]) * MIL10))
            elif f[0] == 'CIRCLE' and f[5] == '101':          # component-marking layer: pin-1 dot
                self.markers.append(cv(f[1], f[2]))
        self.pins = {}
        shapes = list(res['dataStr'].get('shape', []))
        for sp in res.get('subparts', []) or []:
            shapes += sp.get('dataStr', {}).get('shape', [])
        for s in shapes:
            if s.startswith('P~'):
                segs = s.split('^^')
                num = segs[0].split('~')[3]
                name = segs[3].split('~')[4] if len(segs) > 3 and len(segs[3].split('~')) > 4 else ''
                self.pins[num] = name


# ---------------------------------------------------------------- matching
def groups_of(pads, key=lambda p: p.num):
    g = {}
    for p in pads:
        g.setdefault(key(p), []).append(p)
    return g


def group_rep(pads):
    return bbox_centre([q for p in pads for q in p.ext])


def polarity(names):
    k = [n for n, v in names.items() if v.strip().upper() in CATHODE]
    a = [n for n, v in names.items() if v.strip().upper() in ANODE]
    return (k[0], a[0]) if len(k) == 1 and len(a) == 1 else None


def number_map(e_pads, k_nums, e_pins, k_pins):
    """EasyEDA pad number -> list of our pad numbers; plus notes and the leftovers."""
    e_nums = sorted({p.num for p in e_pads})
    m, notes = {}, []
    pe, pk = polarity(e_pins), polarity(k_pins)
    if len(e_nums) == 2 and len(k_nums) == 2 and pe and pk and set(pe) == set(e_nums) and set(pk) <= set(k_nums):
        m = {pe[0]: [pk[0]], pe[1]: [pk[1]]}
        notes.append('POLARITY by symbol pin names: EasyEDA cathode = pad %s (%s), ours = pad %s (%s)'
                     % (pe[0], e_pins[pe[0]], pk[0], k_pins[pk[0]]))
        if pe[0] != pk[0]:
            notes.append('EasyEDA numbers the cathode %s, ours %s: matched cathode-to-cathode; a pad-number '
                         'match would give the opposite rotation and reverse the part' % (pe[0], pk[0]))
        return m, notes, (pe[0], pk[0])
    for n in e_nums:
        if n in k_nums:
            m[n] = [n]
            continue
        # merged numbers such as 'A1B12' = our A1 + B12
        for i in range(1, len(n)):
            if n[:i] in k_nums and n[i:] in k_nums:
                m[n] = [n[:i], n[i:]]
                notes.append("EasyEDA merged pad '%s' = our %s + %s" % (n, n[:i], n[i:]))
                break
    return m, notes, None


SYNONYMS = [{'GND', 'VSS', 'EP', 'G', 'PGND'}, {'VDD', 'VCC', 'VIN', 'IN', '3V3'}, {'DOUT', 'DO'}, {'DIN', 'DI'},
            {'DP', 'D+', 'USBD+'}, {'DN', 'DM', 'D-', 'USBD-'}, {'SH', 'SHIELD', 'EH', 'SHELL', 'MP', 'GND'},
            {'K', 'C', 'CATHODE'}, {'A', 'ANODE'}, {'DQ', 'IO'}]


def _tokens(s):
    s = s.upper().replace('~{', '').replace('}', '').replace('I/O', 'IO').replace('#', '').replace('~', '')
    return {t for t in re.split(r'[/()_,\s]+', s) if t}


def _syn(a, b):
    """same name up to a synonym, keeping any trailing index (DQ3 ~ IO3, VSS ~ GND)."""
    ma, mb = re.match(r'^(.*?)(\d*)$', a), re.match(r'^(.*?)(\d*)$', b)
    if ma.group(2) and mb.group(2) and ma.group(2) != mb.group(2):
        return False
    if ma.group(1) == mb.group(1) and len(ma.group(1)) >= 2:      # CE ~ CE1
        return True
    return any(ma.group(1) in syn and mb.group(1) in syn for syn in SYNONYMS) or any(
        a in syn and b in syn for syn in SYNONYMS)


def names_agree(a, b):
    ta, tb = _tokens(a), _tokens(b)
    if ta & tb:
        return True
    for x in ta:
        for y in tb:
            if _syn(x, y) or (len(x) > 2 and len(y) > 2 and (x in y or y in x)):
                return True
            if len(x) == 1 and y[:1] == x and y[1:].isdigit() or len(y) == 1 and x[:1] == y and x[1:].isdigit():
                return True                                           # E vs E1 (dual transistors)
    return False


def pin_name_check(nmap, e_pins, k_pins):
    """Compare symbol pin names pad by pad (EasyEDA symbol vs our KiCad symbol)."""
    meaningful = lambda n, num: n and n != num and not re.match(r'^(PIN_?\d+|R\d+\.\d|~)$', n.upper())
    same, diff = 0, []
    for en, kns in nmap.items():
        for kn in kns:
            a, b = e_pins.get(en, ''), k_pins.get(kn, '')
            if not (meaningful(a, en) and meaningful(b, kn)):
                continue
            if names_agree(a, b):
                same += 1
            else:
                diff.append('pad %s ours "%s" vs EasyEDA "%s"' % (kn, b, a))
    return same, diff


def fit(e_groups, k_groups, pairs, r):
    """RMS of matched group reps after rotation r, both patterns centred on their bbox centre
    (the 2600 table's convention); + the least-squares (centroid) translation."""
    E = [rot_pt(group_rep(e_groups[a]), r) for a, b in pairs]
    K = [group_rep(k_groups[b]) for a, b in pairs]
    ce, ck = bbox_centre(E), bbox_centre(K)
    err = [dist(sub(e, ce), sub(k, ck)) for e, k in zip(E, K)]
    return math.sqrt(sum(v * v for v in err) / len(err)), sub(centroid(K), centroid(E))


def nn_rms(e_pts, k_pts, r):
    """Number-agnostic pattern error: rotate, align bbox centres, greedy nearest-neighbour."""
    E = [rot_pt(p, r) for p in e_pts]
    t = sub(bbox_centre(k_pts), bbox_centre(E))
    E = [add(p, t) for p in E]
    cand = sorted((dist(e, k), i, j) for i, e in enumerate(E) for j, k in enumerate(k_pts))
    ui, uj, err = set(), set(), []
    for d, i, j in cand:
        if i in ui or j in uj:
            continue
        ui.add(i)
        uj.add(j)
        err.append(d)
    err += [5.0] * (max(len(E), len(k_pts)) - len(err))   # unmatched points: penalty
    return math.sqrt(sum(v * v for v in err) / len(err))


def assign_by_geometry(e_pads, k_pads, r, t):
    """Map each EasyEDA pad to the number of the nearest of our pads after rotation r + t."""
    out = {}
    for p in e_pads:
        q = add(rot_pt(p.pos, r), t)
        best = min(k_pads, key=lambda k: dist(k.pos, q))
        out.setdefault(p.num, set()).add(best.num)
    return {n: sorted(v) for n, v in out.items()}


def pin1_angle(pt, centre):
    return math.degrees(math.atan2(-(pt[1] - centre[1]), pt[0] - centre[0]))


def natural(n):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', n)]


def where(angle):
    """Pin-1 angle (deg, y up, about the pad-pattern centre) -> 'top-left' etc."""
    a = angle % 360
    for lo, hi, name in ((-10, 10, 'right'), (10, 80, 'top-right'), (80, 100, 'top'), (100, 170, 'top-left'),
                         (170, 190, 'left'), (190, 260, 'bottom-left'), (260, 280, 'bottom'),
                         (280, 350, 'bottom-right'), (350, 370, 'right')):
        if lo <= a < hi:
            return name
    return '%.0f deg' % angle


def measure(fpname, lcsc, ee, k_pads, npth, k_pins):
    """Compare one KiCad footprint with one EasyEDA footprint."""
    notes, flags = [], []
    k_groups = groups_of(k_pads)
    k_nums = set(k_groups)
    e_pads = ee.pads
    nmap, mnotes, polar = number_map(e_pads, k_nums, ee.pins, k_pins)
    notes += mnotes

    def build(nmap):
        """matched (E group key, our number) pairs with E groups keyed by our number."""
        eg = {}
        for p in e_pads:
            for kn in nmap.get(p.num, []):
                eg.setdefault(kn, []).append(p)
        return eg, [(kn, kn) for kn in sorted(eg, key=natural) if kn in k_groups]

    e_groups, pairs = build(nmap)
    by_rot = {}
    if len(pairs) >= 2 and len({tuple(map(lambda v: round(v, 3), group_rep(k_groups[b]))) for a, b in pairs}) >= 2:
        by_rot = {r: fit(e_groups, k_groups, pairs, r) for r in ROTS}
    geometric = not by_rot or min(v[0] for v in by_rot.values()) > 0.5
    if geometric:
        # numbers do not describe the same pads: match on geometry alone
        e_pts, k_pts = [p.pos for p in e_pads], [p.pos for p in k_pads]
        g_rms = {r: nn_rms(e_pts, k_pts, r) for r in ROTS}
        rbest = min(ROTS, key=lambda r: g_rms[r])
        t = sub(bbox_centre(k_pts), bbox_centre([rot_pt(p, rbest) for p in e_pts]))
        nmap = assign_by_geometry(e_pads, k_pads, rbest, t)
        notes.append('pad numbers not comparable (EasyEDA %s vs ours %s): matched by geometry, EasyEDA %s'
                     % (','.join(sorted({p.num for p in e_pads}, key=natural)), ','.join(sorted(k_nums, key=natural)),
                        ', '.join('%s->%s' % (a, '/'.join(b)) for a, b in sorted(nmap.items(), key=lambda kv: natural(kv[0])))))
        flags.append('geometric-match')
        e_groups, pairs = build(nmap)
        by_rot = {r: fit(e_groups, k_groups, pairs, r) for r in ROTS}
    rot = min(ROTS, key=lambda r: by_rot[r][0])

    # leftover EasyEDA pads (shell tabs, mounting pads): geometric at the chosen rotation
    left_e = [p for p in e_pads if p.num not in nmap]
    if left_e:
        used = {kn for v in nmap.values() for kn in v}
        left_k = [p for p in k_pads if p.num not in used]
        t = by_rot[rot][1]
        if left_k:
            extra = assign_by_geometry(left_e, left_k, rot, t)
            nmap.update(extra)
            notes.append('EasyEDA %s matched by geometry to our %s'
                         % (','.join(sorted(extra, key=natural)), ','.join(sorted({v for vs in extra.values() for v in vs}, key=natural))))
            e_groups, pairs = build(nmap)
            by_rot = {r: fit(e_groups, k_groups, pairs, r) for r in ROTS}
            rot = min(ROTS, key=lambda r: by_rot[r][0])
    un_e = sorted({p.num for p in e_pads if p.num not in nmap}, key=natural)
    un_k = sorted(k_nums - {kn for v in nmap.values() for kn in v}, key=natural)
    if un_e or un_k:
        flags.append('pad-count-mismatch')
        notes.append('UNMATCHED pad numbers: EasyEDA %s, ours %s' % (un_e or '-', un_k or '-'))

    # number-agnostic pattern symmetry
    g_rms = {r: nn_rms([p.pos for p in e_pads], [p.pos for p in k_pads], r) for r in ROTS}
    sym = [r for r in ROTS if r != rot and g_rms[r] <= g_rms[rot] + 0.05]

    # ---- offsets
    mE = [p for kn, _ in pairs for p in e_groups[kn]]
    mE = list({id(p): p for p in mE}.values())
    mK = [p for kn, _ in pairs for p in k_groups[kn]]
    Er = [p.moved(lambda q: rot_pt(q, rot)) for p in mE]
    t_bbox = sub(bbox_centre([q for p in mK for q in p.ext]), bbox_centre([q for p in Er for q in p.ext]))
    t_pc = sub(bbox_centre([p.pos for p in mK]), bbox_centre([p.pos for p in Er]))
    t_ls = by_rot[rot][1]
    res = {}
    # mechanical features: NPTH pegs + plated THT pads present on both sides
    mech_e = [(rot_pt(c, rot), 'hole') for c, d in ee.holes]
    mech_k = [(c, 'hole') for c, d in npth]
    for kn, _ in pairs:
        ke = [p for p in k_groups[kn] if p.kind == 'tht']
        ee_ = [p for p in e_groups[kn] if p.kind == 'tht']
        if ke and ee_:
            mech_k += [(p.pos, kn) for p in ke]
            mech_e += [(rot_pt(p.pos, rot), kn) for p in ee_]
    t_mech = None
    if ee.holes and npth and len(mech_e) >= 2:
        # pair each EasyEDA feature with the nearest same-kind feature of ours at the bbox offset
        prs = []
        for q, kind in mech_e:
            cands = [c for c, kk in mech_k if kk == kind]
            if cands:
                c = min(cands, key=lambda c: dist(c, add(q, t_bbox)))
                prs.append((q, c))
        if len(prs) >= 2:
            t_mech = centroid([sub(c, q) for q, c in prs])
            err_at = lambda t: max(dist(add(q, t), c) for q, c in prs)
            res['mech_origin_offset_mm'] = [r3(t_mech[0]), r3(t_mech[1])]
            res['mech_feature_err_at_bbox_offset_mm'] = r3(err_at(t_bbox))
            res['mech_feature_err_at_mech_offset_mm'] = r3(err_at(t_mech))
    t_use = t_mech if t_mech is not None else t_bbox
    offset = [0.0 if abs(v) < DEADBAND else r3(v) for v in t_use]

    def pad_err(t):
        """Pad-by-pad where a number has the same pad count on both sides (each EasyEDA pad to the
        nearest of ours); group centre where it does not (EP split differently, thermal vias)."""
        e = 0.0
        for kn, _ in pairs:
            eg, kg = e_groups[kn], k_groups[kn]
            if len(eg) == len(kg):
                for p in eg:
                    q = add(rot_pt(p.pos, rot), t)
                    e = max(e, min(dist(q, k.pos) for k in kg))
            else:
                e = max(e, dist(add(rot_pt(group_rep(eg), rot), t), group_rep(kg)))
        return e

    def group_err(t):
        return max(dist(add(rot_pt(group_rep(e_groups[kn]), rot), t), group_rep(k_groups[kn])) for kn, _ in pairs)

    t_off = tuple(offset)
    if t_mech is not None:
        res['smd_pad_err_at_mech_offset_mm'] = r3(max(
            [dist(add(rot_pt(p.pos, rot), t_mech), min((k.pos for k in k_groups[kn]), key=lambda c: dist(c, add(rot_pt(p.pos, rot), t_mech))))
             for kn, _ in pairs for p in e_groups[kn] if p.kind == 'smd'] or [0.0]))
    perr, gerr = pad_err(t_off), group_err(t_off)

    # ---- pin 1
    k_first = '1' if '1' in k_groups and '1' in e_groups else (sorted((b for a, b in pairs), key=natural)[0])
    kc = bbox_centre([group_rep(k_groups[b]) for a, b in pairs])
    ec = bbox_centre([group_rep(e_groups[a]) for a, b in pairs])
    a_k = pin1_angle(group_rep(k_groups[k_first]), kc)
    a_e = pin1_angle(group_rep(e_groups[k_first]), ec)
    raw = wrap180(a_k - a_e)
    if 'geometric-match' not in flags and abs(wrap180(raw - rot)) > 20:
        flags.append('pin1-angle-disagrees')
        notes.append('pin-1 angle difference %.1f deg does not agree with the pad-fit rotation %d' % (raw, rot))
    same, diff = pin_name_check(nmap, ee.pins, k_pins)
    if same + len(diff):
        res['symbol_pin_names_agree'] = '%d/%d' % (same, same + len(diff))
        if diff:
            res['symbol_pin_name_differences'] = diff
        if same + len(diff) >= 3 and same < 0.7 * (same + len(diff)):
            flags.append('pin-names-disagree')
            notes.append('symbol pin names agree on only %d/%d pads (ours/EasyEDA: %s)'
                         % (same, same + len(diff), ', '.join(diff[:6])))
        elif same + len(diff) >= 3:
            notes.append('symbol pin names agree on %d/%d pads' % (same, same + len(diff)))
    suffix = re.search(r'-(TL|BL|BR|TR|LT|LB|RT|RB|RD|LD|L|R)(?:[-_]|$)', ee.package)
    if suffix:
        res['easyeda_package_pin1_suffix'] = suffix.group(1)
    if len(pairs) > 2 and 'geometric-match' not in flags:
        notes.insert(0, 'pin %s: ours %s, EasyEDA %s%s -> %d deg' % (
            k_first, where(a_k), where(a_e), " ('-%s')" % suffix.group(1) if suffix else '', rot))
    # EasyEDA pin-1 marker (component-marking layer 101): must sit on the pin-1 side
    if ee.markers and e_pads:
        mk = ee.markers[0]
        res['easyeda_pin1_marker_nearest_pad'] = min(e_pads, key=lambda p: dist(p.pos, mk)).num
        e_first = sorted({p.num for p in e_pads}, key=natural)[0]
        ep1 = group_rep([p for p in e_pads if p.num == e_first])
        a_mk = pin1_angle(mk, ec)
        res['easyeda_pin1_marker_ok'] = abs(wrap180(a_mk - pin1_angle(ep1, ec))) <= 45
        if not res['easyeda_pin1_marker_ok'] and 'geometric-match' not in flags:
            notes.append("EasyEDA pin-1 marker (layer 101) is not on the side of its pad %s" % e_first)
        if polar and res['easyeda_pin1_marker_nearest_pad'] != polar[0]:
            notes.append("EasyEDA's layer-101 pin-1 dot is at pad %s, which is NOT the cathode (pad %s): "
                         "the dot marks pin 1, not polarity" % (res['easyeda_pin1_marker_nearest_pad'], polar[0]))

    # ---- confidence
    rms = by_rot[rot][0]
    others = sorted(by_rot[r][0] for r in ROTS if r != rot)
    margin_ok = others[0] >= max(3 * rms, rms + 0.2)
    lsq_vs_bbox = dist(t_ls, t_bbox)
    level = 'high'
    why = []
    if ('pad-count-mismatch' in flags or 'pin1-angle-disagrees' in flags or 'pin-names-disagree' in flags
            or not margin_ok):
        level = 'low'
        why.append('pad numbers' if 'pad-count-mismatch' in flags else
                   'pin-1 angle' if 'pin1-angle-disagrees' in flags else
                   'symbol pin names' if 'pin-names-disagree' in flags else 'rotation not separated')
    elif perr > 0.35:
        level = 'low'
        why.append('pad residual %.2f mm' % perr)
    elif perr > 0.2:
        level = 'medium'
        why.append('pad residual %.2f mm > 0.2' % perr)
    if t_mech is not None and dist(t_mech, t_bbox) > 0.1:
        level = 'medium' if level == 'high' else level
        why.append('mechanical vs pad-bbox offset differ by %.2f mm (mechanical used)' % dist(t_mech, t_bbox))
    if 'geometric-match' in flags and level == 'high':
        level = 'medium'
        why.append('matched by geometry')
    if perr > 0.2 and dist(t_pc, t_bbox) < 0.02:
        notes.append('residual %.3f mm is a land-pattern size difference symmetric about the centre '
                     '(pad-centre and copper bbox centres agree), so rotation and offset are unaffected' % perr)
    if lsq_vs_bbox > 0.05 and t_mech is None:
        notes.append('least-squares offset (%.3f, %.3f) is biased by the unequal pad count per side; the '
                     'bbox method (%.3f, %.3f) is used' % (t_ls[0], t_ls[1], t_bbox[0], t_bbox[1]))
    qual = []
    if polar:
        qual.append('cathode-matched')
    if sym:
        eq = '/'.join(str(r) for r in sorted([rot] + sym))
        if 'geometric-match' in flags:
            qual.append('symmetric: %s equivalent' % eq)
            notes.append('pad pattern alone fits equally at %s: equivalent for this part (no pin 1)' % eq)
        elif polar:
            notes.append('pad pattern alone fits equally at %s: polarity decided by the symbol pin names' % eq)
        elif len(k_nums) == 2:
            qual.append('symmetric: %s equivalent, convention pad 1 -> pad 1' % eq)
            notes.append('symmetric 2-terminal part: %s are equivalent (convention: EasyEDA pad 1 on our pad 1)'
                         % ' and '.join(str(r) for r in sorted([rot] + sym)))
        else:
            notes.append('pad pattern alone fits equally at %s: pin 1 decided by the pad numbers' % eq)
    conf = level + (' (' + '; '.join(qual + why) + ')' if qual or why else '')

    out = {
        'rotation_correction_deg': rot,
        'raw_angle_deg': round(raw, 2) + 0.0,
        'origin_offset_mm': offset,
        'pad_match_max_err_mm': r3(perr),
        'notes': '; '.join(notes),
        'confidence': conf,
        'easyeda_part': ee.part,
        'easyeda_package': ee.package,
        'origin_offset_bbox_method_mm': [r3(v) for v in t_bbox],
        'origin_offset_padcentre_bbox_mm': [r3(v) for v in t_pc],
        'origin_offset_lsq_mm': [r3(v) for v in t_ls],
        'pad_group_centre_max_err_mm': r3(gerr),
        'pad_numbers_ours': len(k_nums),
        'pad_numbers_easyeda': len({p.num for p in e_pads}),
        'pads_ours': len(k_pads),
        'pads_easyeda': len(e_pads),
        'unique_positions_ours': len({(round(p.pos[0], 3), round(p.pos[1], 3)) for p in k_pads}),
        'unique_positions_easyeda': len({(round(p.pos[0], 3), round(p.pos[1], 3)) for p in e_pads}),
        'npth_ours': len(npth),
        'holes_easyeda': len(ee.holes),
        'pin1_pad_ours': k_first,
        'pin1_pad_easyeda': '/'.join(sorted({p.num for p in e_groups[k_first]}, key=natural)),
        'pin1_angle_ours_deg': round(a_k, 2) + 0.0,
        'pin1_angle_easyeda_deg': round(a_e, 2) + 0.0,
        'pattern_rms_err_by_rotation_mm': {str(r): r3(by_rot[r][0]) for r in ROTS},
        'best_rotation_by_pattern': rot,
        'geometric_rms_err_by_rotation_mm': {str(r): r3(g_rms[r]) for r in ROTS},
        'flags': flags,
    }
    out.update(res)
    return out


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--refresh', action='store_true', help='re-fetch every EasyEDA component')
    ap.add_argument('--offline', action='store_true', help='use the cache only')
    ap.add_argument('-o', '--output', default=OUT)
    ap.add_argument('--markdown', action='store_true', help='also print the results as a Markdown table')
    args = ap.parse_args()

    combos = {}
    for p in D.PARTS:
        if not p.lcsc:
            continue
        key = (p.footprint.split(':')[1], p.lcsc)
        c = combos.setdefault(key, {'values': [], 'refs': [], 'dnp': [], 'lib_id': p.lib_id})
        if p.value not in c['values']:
            c['values'].append(p.value)
        c['refs'].append(p.ref)
        if p.dnp:
            c['dnp'].append(p.ref)

    table, problems = [], []
    for (fpname, lcsc), c in combos.items():
        entry = {'footprint': fpname, 'lcsc': lcsc, 'value': ' / '.join(c['values']), 'refs': c['refs']}
        if c['dnp']:
            entry['dnp_refs'] = c['dnp']
        k_pads, npth = kicad_footprint(fpname)
        k_pins = kicad_pin_names(c['lib_id'])
        data = fetch(lcsc, args.refresh, args.offline)
        candidates = []
        if data and data.get('success') and data.get('result'):
            candidates.append((lcsc, data))
        else:
            for px in PROXIES.get(lcsc, []):
                pd = fetch(px, args.refresh, args.offline)
                if pd and pd.get('success') and pd.get('result'):
                    candidates.append((px, pd))
        if not candidates:
            entry.update({'rotation_correction_deg': None, 'origin_offset_mm': None, 'confidence': 'UNMEASURED',
                          'notes': 'no EasyEDA footprint for %s (API: %s) and no proxy' %
                          (lcsc, (data or {}).get('message', 'fetch failed'))})
            problems.append(entry)
            table.append(entry)
            continue
        results = [(code, measure(fpname, lcsc, EasyEDA(d), k_pads, npth, k_pins)) for code, d in candidates]
        code, m = results[0]
        entry.update(m)
        if code != lcsc:
            entry['measured_against_lcsc'] = code
            entry['confidence'] = 'low (PROXY: %s has no EasyEDA footprint; measured against %s %s)' % (
                lcsc, code, m['easyeda_package'])
            alts = ['%s %s -> %d deg, offset %s' % (c2, r2['easyeda_package'], r2['rotation_correction_deg'],
                                                     r2['origin_offset_mm']) for c2, r2 in results]
            entry['proxy_results'] = {c2: {'easyeda_package': r2['easyeda_package'],
                                           'rotation_correction_deg': r2['rotation_correction_deg'],
                                           'origin_offset_mm': r2['origin_offset_mm'],
                                           'pad_match_max_err_mm': r2['pad_match_max_err_mm']} for c2, r2 in results}
            entry['notes'] = ('NO EasyEDA FOOTPRINT for %s: JLC has no library placement data for it, so the '
                              'rotation below is a proxy and must be confirmed in the JLC placement preview / DFM. '
                              'Proxies: %s. ' % (lcsc, '; '.join(alts))) + entry['notes']
            problems.append(entry)
        elif not entry['confidence'].startswith('high'):
            problems.append(entry)
        table.append(entry)

    with open(args.output, 'w') as f:
        json.dump(table, f, indent=1, ensure_ascii=False)
        f.write('\n')

    # ---- human summary
    print('%-40s %-10s %4s %-16s %6s  %s' % ('footprint', 'lcsc', 'rot', 'offset mm', 'err', 'confidence'))
    for e in table:
        if e.get('rotation_correction_deg') is None:
            print('%-40s %-10s  --  %-16s %6s  %s' % (e['footprint'][:40], e['lcsc'], '-', '-', e['confidence']))
            continue
        print('%-40s %-10s %4d %-16s %6.3f  %s' % (
            e['footprint'][:40], e['lcsc'], e['rotation_correction_deg'],
            '(%g, %g)' % tuple(e['origin_offset_mm']), e['pad_match_max_err_mm'], e['confidence']))
    # same footprint, different corrections: a footprint-keyed lookup would be wrong
    byfp = {}
    for e in table:
        if e.get('rotation_correction_deg') is not None:
            byfp.setdefault(e['footprint'], set()).add((e['rotation_correction_deg'], tuple(e['origin_offset_mm'])))
    clash = {k: v for k, v in byfp.items() if len(v) > 1}
    if clash:
        print('\nWARNING: footprints whose LCSC parts need different corrections (key the CPL lookup by '
              '(footprint, lcsc)):')
        for k, v in clash.items():
            print('  %s: %s' % (k, sorted(v)))
    if problems:
        print('\nNot high confidence:')
        for e in problems:
            print('  %s %s (%s): %s' % (e['footprint'], e['lcsc'], ','.join(e['refs']), e['confidence']))
    if args.markdown:
        print('\n| Footprint | LCSC | Part | Refs | Rot | Offset (mm) | Max err (mm) | Confidence | Notes |')
        print('|---|---|---|---|---|---|---|---|---|')
        for e in table:
            rot = '-' if e.get('rotation_correction_deg') is None else '%d' % e['rotation_correction_deg']
            off = '-' if e.get('origin_offset_mm') is None else '(%g, %g)' % tuple(e['origin_offset_mm'])
            print('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                e['footprint'], e['lcsc'], e['value'], ', '.join(e['refs']), rot, off,
                e.get('pad_match_max_err_mm', '-'), e['confidence'], e.get('notes', '').replace('|', '/')))
    print('\nwrote %s (%d entries)' % (args.output, len(table)))


if __name__ == '__main__':
    main()
