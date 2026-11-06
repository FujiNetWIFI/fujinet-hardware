#!/usr/bin/env python3
"""Gate: the board's fab outputs equal Yannick Erb's own (Original/Gerber_*.zip, EasyEDA 6.5.51).

Ours are plotted from Inty-FujiCard.kicad_pcb by kicad-cli exactly as tools/export.py plots them
(saved zone fills, never refilled; drill/place origin = the board's lower-left corner, which is
where EasyEDA puts (0, 0)), or read from a zip given on the command line.

  1. copper (F, B), solder mask (F, B), paste (F, B), outline: both sets rasterised (a small Gerber
     interpreter: FS 4.5 / 4.6, C / R / O / P apertures, aperture macros with primitives 1, 4, 5,
     20, 21 and arithmetic, G01 / G02 / G03 (G75), regions, LPD / LPC) at PX px/mm with pycairo,
     XOR-ed, then opened with a 3 x 3 cross (anything under ~50 um wide goes: arc flattening, an
     octagon against a rounded corner, a 0.2 um rounding).  Every blob left is a FAIL, with where
     it is and whose it is.
  2. silkscreen (F): the same, except that a blob inside a text's box is not a failure (KiCad's
     stroke font is not EasyEDA's); instead every text EasyEDA shows (the JSON's visible TEXT
     records) must have a KiCad text with the same string, its strokes centred within TEXT_POS mm
     of EasyEDA's, at the same angle, and no other text may be visible.  B.Silkscreen: EasyEDA plotted none, ours must be empty.
  3. drills: every hole (x, y, diameter, slot end) in his three Excellon files (the vias appear in
     two of them) is one of ours, within 0.01 mm, and no other.

Usage: python3 tools/audit/gerber_equiv.py [our-gerbers.zip]      exit 1 on any failure
"""
import io, json, math, os, re, subprocess, sys, tempfile, zipfile
import numpy as np
import cairo
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
NAME = 'Inty-FujiCard'
PCB = os.path.join(PRJ, NAME + '.kicad_pcb')
HIS = os.path.join(PRJ, 'Original', 'Gerber_PINTY-FUJI-CARD_PINTY-FUJI-CARD-PCB-v1.1_2026-11-04.zip')
JSON = os.path.join(PRJ, 'Original', 'PCB_PINTY-FUJI-CARD-PCB-v1.1_2026-11-04.json')
PX = 40                       # px / mm
WIN = (-2.0, -2.0, 61.0, 63.0)  # mm, gerber coordinates (y up); the board is 58.2 x 60.0
TEXT_POS = 0.05               # mm, a visible text's ink centre, EasyEDA's glyphs against KiCad's
fails = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        fails.append(msg)


# ---------------------------------------------------------------------------
# Gerber
def evaluate(expr, var):
    """An aperture-macro expression: numbers, $n, + - x X / and parentheses."""
    e = re.sub(r'\$(\d+)', lambda m: repr(var.get(int(m.group(1)), 0.0)), expr.strip())
    e = e.replace('x', '*').replace('X', '*')
    if not re.match(r'^[-+*/(). 0-9eE]*$', e):
        raise ValueError('macro expression %r' % expr)
    return float(eval(e, {'__builtins__': {}})) if e.strip() else 0.0


class Gerber:
    """Parsed into an ordered list of operations; render() draws them."""

    def __init__(self, text):
        self.ops, self.ap, self.am = [], {}, {}
        self.fmt = (4, 6)
        self.unit = 1.0
        x = y = 0.0
        cur, mode, region, pol = None, 'G01', None, 'D'
        contour = None
        for m in re.finditer(r'%([^%]*)%|([^%*]*)\*', text):
            if m.group(1) is not None:
                self.extended(m.group(1))
                pol = self.pol if hasattr(self, 'pol') else pol
                continue
            w = re.sub(r'\s', '', m.group(2))
            if not w or w.startswith('G04') or w in ('M02', 'M00', 'M01'):
                continue
            while True:
                g = re.match(r'^G0*(\d+)', w)
                if not g:
                    break
                w = w[g.end():]
                g = int(g.group(1))
                if g in (1, 2, 3):
                    mode = 'G0%d' % g
                elif g == 36:
                    region, contour = [], None
                elif g == 37:
                    if contour:
                        region.append(contour)
                    self.ops.append(('region', region, self.pol))
                    region, contour = None, None
                # G74 / G75 (KiCad and EasyEDA write G75), G70 / G71 / G90: nothing to draw
            if not w:
                continue
            if re.match(r'^D(\d+)$', w) and int(w[1:]) >= 10:
                cur = int(w[1:])
                continue
            mm = re.match(r'^(?:X([-+]?\d+))?(?:Y([-+]?\d+))?(?:I([-+]?\d+))?(?:J([-+]?\d+))?D0?([123])$', w)
            if not mm:
                if w:
                    raise ValueError('gerber word %r' % w)
                continue
            nx = self.coord(mm.group(1)) if mm.group(1) else x
            ny = self.coord(mm.group(2)) if mm.group(2) else y
            i = self.coord(mm.group(3)) if mm.group(3) else 0.0
            j = self.coord(mm.group(4)) if mm.group(4) else 0.0
            d = int(mm.group(5))
            if d == 2:
                if region is not None:
                    if contour:
                        region.append(contour)
                    contour = [(nx, ny)]
            elif d == 1:
                seg = ('L', x, y, nx, ny) if mode == 'G01' else ('A', x, y, nx, ny, x + i, y + j, mode == 'G03')
                if region is not None:
                    if contour is None:
                        contour = [(x, y)]
                    contour.append(seg)
                else:
                    self.ops.append(('stroke', cur, seg, self.pol))
            elif d == 3:
                self.ops.append(('flash', cur, nx, ny, self.pol))
            x, y = nx, ny

    pol = 'D'

    def coord(self, s):
        return int(s) / 10.0 ** self.fmt[1] * self.unit

    def extended(self, body):
        parts = [p.strip() for p in body.split('*') if p.strip()]
        if not parts:
            return
        h = parts[0]
        if h.startswith('FS'):
            m = re.match(r'FSLAX(\d)(\d)Y(\d)(\d)', h)
            self.fmt = (int(m.group(1)), int(m.group(2)))
        elif h.startswith('MO'):
            self.unit = 1.0 if h == 'MOMM' else 25.4
        elif h.startswith('LP'):
            self.pol = h[2]
        elif h.startswith('AM'):
            self.am[h[2:]] = parts[1:]
        elif h.startswith('AD'):
            m = re.match(r'ADD(\d+)([A-Za-z_][\w.$-]*)(?:,(.*))?$', h)
            args = [float(a) for a in m.group(3).split('X')] if m.group(3) else []
            self.ap[int(m.group(1))] = (m.group(2), args)
        # TF / TA / TO / TD / IP / OF / SR(1x1): attributes and defaults, no geometry

    # -- drawing ------------------------------------------------------------
    def render(self, ctx):
        for op in self.ops:
            dark = op[-1] == 'D'
            ctx.set_operator(cairo.OPERATOR_OVER if dark else cairo.OPERATOR_DEST_OUT)
            if op[0] == 'flash':
                self.flash(ctx, op[1], op[2], op[3])
            elif op[0] == 'stroke':
                self.stroke(ctx, op[1], op[2])
            else:
                for c in op[1]:
                    ctx.new_path()
                    ctx.move_to(*c[0])
                    for seg in c[1:]:
                        self.path_seg(ctx, seg)
                    ctx.close_path()
                    ctx.fill()

    @staticmethod
    def path_seg(ctx, seg):
        if seg[0] == 'L':
            ctx.line_to(seg[3], seg[4])
            return
        _, x0, y0, x1, y1, cx, cy, ccw = seg
        r = math.hypot(x0 - cx, y0 - cy)
        a0, a1 = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx)
        if (x0, y0) == (x1, y1):
            a1 = a0 + (2 * math.pi if ccw else -2 * math.pi)
        (ctx.arc if ccw else ctx.arc_negative)(cx, cy, r, a0, a1)

    def stroke(self, ctx, d, seg):
        kind, a = self.ap[d]
        if kind == 'C' or (kind == 'O' and abs(a[0] - a[1]) < 1e-6) or kind not in ('R', 'O'):
            w = a[0] if a else 0.0
            if w <= 0:
                w = 0.001
            ctx.set_line_width(w)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.new_path()
            ctx.move_to(seg[1], seg[2])
            self.path_seg(ctx, seg)
            ctx.stroke()
            return
        # a rectangle (or obround) dragged along a straight line: the hull of both end flashes
        if seg[0] != 'L':
            raise ValueError('arc drawn with a %s aperture' % kind)
        self.flash(ctx, d, seg[1], seg[2])
        self.flash(ctx, d, seg[3], seg[4])
        hw, hh = a[0] / 2, a[1] / 2
        pts = [(seg[1] + sx * hw, seg[2] + sy * hh) for sx in (-1, 1) for sy in (-1, 1)] + \
              [(seg[3] + sx * hw, seg[4] + sy * hh) for sx in (-1, 1) for sy in (-1, 1)]
        hull = convex_hull(pts)
        ctx.new_path()
        ctx.move_to(*hull[0])
        for p in hull[1:]:
            ctx.line_to(*p)
        ctx.close_path()
        ctx.fill()

    def flash(self, ctx, d, x, y):
        kind, a = self.ap[d]
        ctx.new_path()
        if kind == 'C':
            ctx.arc(x, y, a[0] / 2, 0, 2 * math.pi)
            ctx.fill()
        elif kind == 'R':
            ctx.rectangle(x - a[0] / 2, y - a[1] / 2, a[0], a[1])
            ctx.fill()
        elif kind == 'O':
            w, h = a[0], a[1]
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            if w >= h:
                ctx.set_line_width(h)
                ctx.move_to(x - (w - h) / 2, y)
                ctx.line_to(x + (w - h) / 2 + 1e-9, y)
            else:
                ctx.set_line_width(w)
                ctx.move_to(x, y - (h - w) / 2)
                ctx.line_to(x, y + (h - w) / 2 + 1e-9)
            ctx.stroke()
        elif kind == 'P':
            dia, n = a[0], int(a[1])
            rot = math.radians(a[2]) if len(a) > 2 else 0.0
            for k in range(n):
                t = rot + 2 * math.pi * k / n
                (ctx.move_to if k == 0 else ctx.line_to)(x + dia / 2 * math.cos(t), y + dia / 2 * math.sin(t))
            ctx.close_path()
            ctx.fill()
        else:
            self.macro(ctx, kind, a, x, y)

    def macro(self, ctx, name, args, x, y):
        var = {i + 1: v for i, v in enumerate(args)}
        op = ctx.get_operator()
        ctx.push_group()
        for line in self.am[name]:
            line = line.strip()
            if not line or line.startswith('0'):
                continue
            if line.startswith('$'):
                k, e = line.split('=', 1)
                var[int(k[1:])] = evaluate(e, var)
                continue
            f = [evaluate(v, var) for v in line.split(',')]
            code, exp = int(f[0]), f[1]
            ctx.set_operator(cairo.OPERATOR_OVER if exp else cairo.OPERATOR_DEST_OUT)
            ctx.new_path()

            def poly(pts, rot):
                c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
                for k, (px, py) in enumerate(pts):
                    rx, ry = px * c - py * s, px * s + py * c
                    (ctx.move_to if k == 0 else ctx.line_to)(x + rx, y + ry)
                ctx.close_path()
                ctx.fill()
            if code == 1:
                dia, cx, cy = f[2], f[3], f[4]
                rot = f[5] if len(f) > 5 else 0.0
                c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
                ctx.arc(x + cx * c - cy * s, y + cx * s + cy * c, dia / 2, 0, 2 * math.pi)
                ctx.fill()
            elif code == 20:
                w, x1, y1, x2, y2, rot = f[2:8]
                L = math.hypot(x2 - x1, y2 - y1) or 1e-9
                nx, ny = -(y2 - y1) / L * w / 2, (x2 - x1) / L * w / 2
                poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], rot)
            elif code == 21:
                w, h, cx, cy, rot = f[2:7]
                poly([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2),
                      (cx - w / 2, cy + h / 2)], rot)
            elif code == 4:
                n = int(f[2])
                pts = [(f[3 + 2 * k], f[4 + 2 * k]) for k in range(n + 1)]
                poly(pts, f[5 + 2 * n] if len(f) > 5 + 2 * n else 0.0)
            elif code == 5:
                n, cx, cy, dia = int(f[2]), f[3], f[4], f[5]
                rot = f[6] if len(f) > 6 else 0.0
                poly([(cx + dia / 2 * math.cos(2 * math.pi * k / n), cy + dia / 2 * math.sin(2 * math.pi * k / n))
                      for k in range(n)], rot)
            else:
                raise ValueError('macro primitive %d in %s' % (code, name))
        pat = ctx.pop_group()
        ctx.set_operator(op)
        ctx.set_source(pat)
        ctx.paint()
        ctx.set_source_rgba(0, 0, 0, 1)


def convex_hull(pts):
    pts = sorted(set(pts))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def raster(text):
    x0, y0, x1, y1 = WIN
    W, H = int((x1 - x0) * PX), int((y1 - y0) * PX)
    surf = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
    ctx = cairo.Context(surf)
    ctx.set_matrix(cairo.Matrix(PX, 0, 0, -PX, -x0 * PX, y1 * PX))
    ctx.set_source_rgba(0, 0, 0, 1)
    Gerber(text).render(ctx)
    surf.flush()
    a = np.frombuffer(surf.get_data(), np.uint8).reshape(H, surf.get_stride())[:, :W]
    return a > 127


def px_to_mm(r, c):
    return WIN[0] + (c + 0.5) / PX, WIN[3] - (r + 0.5) / PX


def compare(name, ours, his, excuse=None, drilled=None):
    """XOR, opening, blobs.  excuse: a boolean mask of areas where a blob is not a failure;
    drilled: the holes, cleared on both sides first (the fab drills them out of every layer)."""
    a, b = raster(ours), raster(his)
    if drilled is not None:
        a, b = a & ~drilled, b & ~drilled
    if os.environ.get('GERBER_PNG'):
        from PIL import Image
        img = np.zeros(a.shape + (3,), np.uint8)
        img[a & b] = (200, 200, 200)
        img[a & ~b] = (255, 0, 0)
        img[b & ~a] = (0, 200, 0)
        Image.fromarray(img).save(os.path.join(os.environ['GERBER_PNG'], name.split()[0] + '.png'))
    x = a ^ b
    x = ndimage.binary_opening(x, structure=ndimage.generate_binary_structure(2, 1))
    lab, n = ndimage.label(x)
    blobs = []
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        m = lab[sl] == k
        if excuse is not None and excuse[sl][m].all():
            continue
        r0, r1, c0, c1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        xa, ya = px_to_mm(r1 - 1, c0)
        xb, yb = px_to_mm(r0, c1 - 1)
        who = 'ours only' if a[sl][m].sum() > b[sl][m].sum() else 'his only'
        blobs.append('(%.2f..%.2f, %.2f..%.2f) mm, %.3f mm2, %s' % (xa, xb, ya, yb, m.sum() / PX ** 2, who))
    check(not blobs, '%s: %s' % (name, 'identical to Yannick\'s (XOR opened at %d um: nothing left; %.1f / %.1f mm2 drawn)'
                                 % (round(2000 / PX), a.sum() / PX ** 2, b.sum() / PX ** 2) if not blobs else
                                 '%d differing areas: %s' % (len(blobs), '; '.join(blobs[:12]))))
    return a, b


# ---------------------------------------------------------------------------
# Excellon
def excellon(text):
    """[(x, y, diameter, (x2, y2) or None)] in mm."""
    tools, holes, cur = {}, [], None
    dec = 3
    m = re.search(r'FILE_FORMAT=(\d):(\d)', text)
    if m:
        dec = int(m.group(2))
    body = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(';'):
            continue
        if line == '%' or line == 'M95':
            body = True
            continue
        t = re.match(r'^T(\d+)C([\d.]+)', line)
        if t:
            tools[int(t.group(1))] = float(t.group(2))
            continue
        t = re.match(r'^T(\d+)$', line)
        if t and body:
            cur = int(t.group(1))
            continue
        v = lambda s: float(s) if '.' in s else int(s) / 10.0 ** dec
        s = re.match(r'^X([-\d.]+)Y([-\d.]+)G85X([-\d.]+)Y([-\d.]+)$', line)
        if s:
            holes.append((v(s.group(1)), v(s.group(2)), tools[cur], (v(s.group(3)), v(s.group(4)))))
            continue
        h = re.match(r'^X([-\d.]+)Y([-\d.]+)$', line)
        if h:
            holes.append((v(h.group(1)), v(h.group(2)), tools[cur], None))
    return holes


def same_hole(p, q, tol=0.01):
    """The same round hole, or the same slot drawn from either end."""
    near = lambda a, b: abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol
    if abs(p[2] - q[2]) > tol or (p[3] is None) != (q[3] is None):
        return False
    if p[3] is None:
        return near(p, q)
    return (near(p, q) and near(p[3], q[3])) or (near(p, q[3]) and near(p[3], q))


def holes_match(name, ours, his):
    his_u = []
    for h in his:
        if not any(same_hole(h, k) for k in his_u):
            his_u.append(h)
    left = list(ours)
    missing = []
    for h in his_u:
        k = next((i for i, o in enumerate(left) if same_hole(h, o)), None)
        if k is None:
            missing.append(h)
        else:
            left.pop(k)
    check(not missing and not left, '%s: %d holes, all Yannick\'s (%d in his files, %d after removing repeats)%s'
          % (name, len(ours), len(his), len(his_u), '' if not missing and not left else
             '; missing %s; extra %s' % (missing[:4], left[:4])))


# ---------------------------------------------------------------------------
def his_texts():
    """EasyEDA's visible top-silkscreen texts: (string, ink centre x, y, angle, ink box) in gerber
    coordinates (mm from the board's lower-left corner, y up); the ink box is the bounding box of
    EasyEDA's own glyph strokes (tools/easyeda.py)."""
    sys.path.insert(0, os.path.dirname(HERE))
    import easyeda
    g = lambda x, y: (x - easyeda.KI_ORIGIN[0], easyeda.KI_ORIGIN[1] - y)
    out = []
    for t in easyeda.texts():
        if t['shown'] and t['layer'] == '3':
            x0, y1 = g(t['ink'][0], t['ink'][1])
            x1, y0 = g(t['ink'][2], t['ink'][3])
            out.append((t['text'], (x0 + x1) / 2, (y0 + y1) / 2, t['angle'], (x0, y0, x1, y1)))
    return out


def our_texts():
    """KiCad's visible F.Silkscreen texts (board texts, footprint texts and fields): (string, ink
    centre x, y, angle, ink box) in gerber coordinates (aux origin, y up); the ink box is the
    bounding box of KiCad's stroked glyphs."""
    import pcbnew
    b = pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(PCB, None)
    ox, oy = b.GetDesignSettings().GetAuxOrigin().x / 1e6, b.GetDesignSettings().GetAuxOrigin().y / 1e6
    out = []
    items = [d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT']
    for f in b.GetFootprints():
        items += [t for t in f.GraphicalItems() if t.GetClass() == 'PCB_TEXT']
        items += [fl for fl in f.GetFields()]
    for t in items:
        if t.GetLayer() != pcbnew.F_SilkS or not t.IsVisible():
            continue
        bb = t.GetEffectiveTextShape().BBox()
        x0, x1 = bb.GetX() / 1e6 - ox, (bb.GetX() + bb.GetWidth()) / 1e6 - ox
        y0, y1 = oy - (bb.GetY() + bb.GetHeight()) / 1e6, oy - bb.GetY() / 1e6
        out.append((t.GetShownText(False), (x0 + x1) / 2, (y0 + y1) / 2, t.GetDrawRotation().AsDegrees() % 360,
                    (x0, y0, x1, y1)))
    return out


def hole_mask(holes):
    """Every drilled hole (round or slot) as a raster, slightly shrunk (a ring left by a mask
    opening a few um larger than the hole still shows)."""
    x0, y0, x1, y1 = WIN
    W, H = int((x1 - x0) * PX), int((y1 - y0) * PX)
    surf = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
    ctx = cairo.Context(surf)
    ctx.set_matrix(cairo.Matrix(PX, 0, 0, -PX, -x0 * PX, y1 * PX))
    ctx.set_source_rgba(0, 0, 0, 1)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for x, y, d, end in holes:
        d = max(d - 0.05, 0.01)
        ctx.new_path()
        if end is None:
            ctx.arc(x, y, d / 2, 0, 2 * math.pi)
            ctx.fill()
        else:
            ctx.set_line_width(d)
            ctx.move_to(x, y)
            ctx.line_to(*end)
            ctx.stroke()
    surf.flush()
    return np.frombuffer(surf.get_data(), np.uint8).reshape(H, surf.get_stride())[:, :W] > 127


def text_mask(boxes, grow=0.3):
    x0, y0, x1, y1 = WIN
    W, H = int((x1 - x0) * PX), int((y1 - y0) * PX)
    m = np.zeros((H, W), bool)
    for bx0, by0, bx1, by1 in boxes:
        c0, c1 = int((bx0 - grow - x0) * PX), int((bx1 + grow - x0) * PX) + 1
        r0, r1 = int((y1 - by1 - grow) * PX), int((y1 - by0 + grow) * PX) + 1
        m[max(r0, 0):r1, max(c0, 0):c1] = True
    return m


def main():
    tmp = tempfile.mkdtemp(prefix='inty-gerber-equiv-')
    if len(sys.argv) > 1:
        z = zipfile.ZipFile(sys.argv[1])
        ours = {n: z.read(n).decode() for n in z.namelist()}
        src = os.path.relpath(sys.argv[1], PRJ)
    else:
        subprocess.run(['kicad-cli', 'pcb', 'export', 'gerbers', '-o', tmp + '/', '-l',
                        'F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts',
                        '--use-drill-file-origin', PCB], check=True, capture_output=True)
        subprocess.run(['kicad-cli', 'pcb', 'export', 'drill', '-o', tmp + '/', '--format', 'excellon',
                        '--drill-origin', 'plot', '--excellon-units', 'mm', '--excellon-separate-th', PCB],
                       check=True, capture_output=True)
        ours = {n: open(os.path.join(tmp, n)).read() for n in os.listdir(tmp)}
        src = 'a fresh kicad-cli plot of %s.kicad_pcb' % NAME
    z = zipfile.ZipFile(HIS)
    his = {n: z.read(n).decode() for n in z.namelist()}
    # a layer by its name, whichever extension (Protel's .gtl ..., or KiCad's .gbr)
    mine = lambda suffix: next(v for k, v in ours.items()
                               if 'drl_map' not in k and re.search(re.escape(suffix.rsplit('.', 1)[0]) + r'\.', k))
    print('ours: %s; Yannick\'s: %s' % (src, os.path.relpath(HIS, PRJ)))
    pth = excellon(mine('-PTH.drl'))
    npth = excellon(mine('-NPTH.drl'))
    drilled = hole_mask(pth + npth)
    for nm, a, b in (('F.Cu', '-F_Cu.gtl', 'Gerber_TopLayer.GTL'), ('B.Cu', '-B_Cu.gbl', 'Gerber_BottomLayer.GBL'),
                     ('F.Mask', '-F_Mask.gts', 'Gerber_TopSolderMaskLayer.GTS'),
                     ('B.Mask', '-B_Mask.gbs', 'Gerber_BottomSolderMaskLayer.GBS'),
                     ('F.Paste', '-F_Paste.gtp', 'Gerber_TopPasteMaskLayer.GTP'),
                     ('B.Paste', '-B_Paste.gbp', 'Gerber_BottomPasteMaskLayer.GBP'),
                     ('Edge.Cuts', '-Edge_Cuts.gm1', 'Gerber_BoardOutlineLayer.GKO')):
        compare(nm, mine(a), his[b], drilled=drilled)
    # silkscreen
    ht, ot = his_texts(), our_texts()
    excuse = text_mask([t[4] for t in ht] + [t[4] for t in ot])
    compare('F.Silkscreen (outside text boxes)', mine('-F_Silkscreen.gto'), his['Gerber_TopSilkscreenLayer.GTO'], excuse,
            drilled=drilled)
    unmatched = []
    pool = list(ot)
    for s, x, y, ang, _ in ht:
        k = next((i for i, o in enumerate(pool) if o[0] == s and math.hypot(o[1] - x, o[2] - y) <= TEXT_POS and
                  abs((o[3] - ang + 180) % 360 - 180) < 0.5), None)
        if k is None:
            near = sorted(pool, key=lambda o: math.hypot(o[1] - x, o[2] - y))[:1]
            unmatched.append('%r at (%.2f, %.2f) %g deg (nearest ours: %s)' % (s, x, y, ang,
                             ['%r (%.2f, %.2f) %g' % o[:4] for o in near]))
        else:
            pool.pop(k)
    check(not unmatched, 'F.Silkscreen texts: %d of Yannick\'s %d visible texts have a KiCad text with the same '
          'string within %.2f mm, same angle%s' % (len(ht) - len(unmatched), len(ht), TEXT_POS,
                                                   '' if not unmatched else ': ' + '; '.join(unmatched[:8])))
    check(not pool, 'F.Silkscreen texts: no KiCad text Yannick\'s silkscreen lacks%s' %
          ('' if not pool else ': %s' % ['%r (%.2f, %.2f)' % o[:3] for o in pool][:8]))
    bsilk = raster(mine('-B_Silkscreen.gbo'))
    check(not bsilk.any(), 'B.Silkscreen: empty, as Yannick\'s set (it has no bottom silkscreen file)')
    # drills
    holes_match('PTH', pth, excellon(his['Drill_PTH_Through.DRL']) + excellon(his['Drill_PTH_Through_Via.DRL']))
    holes_match('NPTH', npth, excellon(his['Drill_NPTH_Through.DRL']))
    print('%d failures' % len(fails))
    sys.stdout.flush()
    os._exit(1 if fails else 0)


if __name__ == '__main__':
    main()
