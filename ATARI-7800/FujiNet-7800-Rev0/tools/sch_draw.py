"""Drawing toolkit for the wired sheets (sch_layout.py draws, gen_sch.py writes).

A Sheet collects placed symbols, wires, buses, labels, rail symbols and
no-connect flags in sheet coordinates (mm, y down), on the 1.27 mm grid.
Symbols are placed by reference designator; their pins are then addressed by
pad number, so the drawing scripts never repeat a coordinate from a symbol.

Connectivity is checked here before KiCad ever sees the file: finish()
unions every wire, pin, label and rail symbol by position exactly as eeschema
does (wire ends join wires and pins, a wire end on another wire's run makes a
T and gets a junction), then demands that each connected group holds pins of
exactly one design.py net and carries that net's name.  A pin lying on the
run of a wire it does not end on, a wire through a symbol body, overlapping
symbols or texts, and a dangling wire end are errors too.

Net names stay exactly design.py's: rails are power symbols whose Value is
the net (GND, +5V, +3V3, +3V3_RP, CONS_5V, VBUS); every other net is named by
global labels -- at the page edge where it enters or leaves the sheet, or one
tag on its wire when it lives on one sheet; bus members by a local label on
their entry wire under a global bus label.
"""
import math, os
from collections import defaultdict

from sexpr import find, findall, Q

G = 1.27


def snap(v):
    return round(round(v / G) * G, 4)


def font(size=1.27):
    return ['effects', ['font', ['size', size, size]]]


# ---------------------------------------------------------------------------
# symbol geometry (library coordinates, y up)
def lib_pins(sym):
    """[(unit, number, x, y, angle)], body style 1 only."""
    out = []
    for sub in findall(sym, 'symbol'):
        unit, style = (int(v) for v in sub[1].rsplit('_', 2)[-2:])
        if style > 1:
            continue
        for p in findall(sub, 'pin'):
            at = find(p, 'at')
            out.append((unit, str(find(p, 'number')[1]), float(at[1]), float(at[2]), int(float(at[3]))))
    return out


def lib_body(sym, unit):
    """Body outline box (graphics only, no pins) in library coordinates."""
    xs, ys = [], []

    def walk(e):
        for x in e:
            if isinstance(x, list) and x:
                if x[0] in ('xy', 'start', 'end', 'center', 'mid') and len(x) >= 3:
                    xs.append(float(x[1])); ys.append(float(x[2]))
                elif x[0] == 'circle':
                    c = find(x, 'center'); r = float(find(x, 'radius')[1])
                    xs.extend([float(c[1]) - r, float(c[1]) + r]); ys.extend([float(c[2]) - r, float(c[2]) + r])
                elif x[0] not in ('property', 'pin'):
                    walk(x)
    for sub in findall(sym, 'symbol'):
        u, style = (int(v) for v in sub[1].rsplit('_', 2)[-2:])
        if u in (0, unit) and style <= 1:
            walk(sub)
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))


def units_of(sym):
    us = sorted({u for u, *_ in lib_pins(sym) if u})
    return us or [1]


def xform(rot, mirror):
    """lib (x, y-up) -> sheet offset (y-down), KiCad order: rotate, then mirror."""
    def f(x, y):
        a, b = x, -y
        for _ in range((rot // 90) % 4):
            a, b = b, -a
        if mirror == 'y':
            a = -a
        elif mirror == 'x':
            b = -b
        return a, b
    return f


class Pt(tuple):
    """A pin end: (x, y) plus the outward direction (dx, dy)."""
    def __new__(cls, x, y, dx=0, dy=0, owner=None):
        t = tuple.__new__(cls, (snap(x), snap(y)))
        t.dx, t.dy, t.owner = dx, dy, owner
        return t

    def go(self, n):
        """The point n mm further out along the pin direction."""
        return (snap(self[0] + self.dx * n), snap(self[1] + self.dy * n))


def text_box(x, y, s, size, justify, vertical=False):
    w = 0.9 * size * len(s) + 0.3
    h = size * 1.2
    if justify == 'left':
        x0, x1 = x, x + w
    elif justify == 'right':
        x0, x1 = x - w, x
    else:
        x0, x1 = x - w / 2, x + w / 2
    box = (x0, y - h / 2, x1, y + h / 2)
    if vertical:   # rotate about (x, y)
        box = (x - h / 2, y - (x1 - x), x + h / 2, y - (x0 - x))
    return box


def overlap(a, b, gap=0.0):
    return a[0] < b[2] - gap and b[0] < a[2] - gap and a[1] < b[3] - gap and b[1] < a[3] - gap


# ---------------------------------------------------------------------------
class Sheet:
    RAILS = {'GND': 'power:GND', '+5V': 'power:+5V', '+3V3': 'power:+3V3', '+3V3_RP': 'power:+3V3',
             'CONS_5V': 'power:+5V', 'VBUS': 'power:VBUS'}

    def __init__(self, stem, syms, parts, paper='A3'):
        self.stem, self.syms, self.paper = stem, syms, paper
        self.size = {'A4': (297, 210), 'A3': (420, 297), 'A2': (594, 420), 'A1': (841, 594)}[paper]
        self.parts = {p.ref: p for p in parts}
        self.placed = {}           # (ref, unit) -> dict
        self.wires, self.buses, self.entries = [], [], []
        self.labels = []           # (kind, net, x, y, angle, shape)
        self.rails = []            # (net, x, y, rot)
        self.flags = []            # (net, x, y)
        self.ncs, self.texts = [], []
        self.errors = []
        self.lint = True           # geometry lint (overlaps); connectivity is always checked

    # -- symbols ------------------------------------------------------------
    def place(self, ref, x, y, unit=1, rot=0, mirror=None, fields='auto', ref_at=None, val_at=None):
        p = self.parts[ref]
        sym = self.syms[p.lib_id]
        x, y = snap(x), snap(y)
        f = xform(rot, mirror)
        pins = {}
        for (u, num, px, py, ang) in lib_pins(sym):
            if u not in (0, unit):
                continue
            ox, oy = f(px, py)
            ix, iy = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[ang]
            dx, dy = f(-ix, -iy)  # outward, sheet frame (f folds in the lib y-up flip)
            pins[num] = Pt(x + ox, y + oy, dx, dy, (ref, unit, num))
        bx0, by0, bx1, by1 = lib_body(sym, unit)
        c = [f(bx0, by0), f(bx1, by1)]
        body = (x + min(c[0][0], c[1][0]), y + min(c[0][1], c[1][1]),
                x + max(c[0][0], c[1][0]), y + max(c[0][1], c[1][1]))
        d = dict(ref=ref, unit=unit, x=x, y=y, rot=rot, mirror=mirror, pins=pins, body=body, part=p)
        d['fields'] = self._fields(d, fields, ref_at, val_at)
        self.placed[(ref, unit)] = d
        return d

    def _fields(self, d, mode, ref_at, val_at):
        """Reference / Value text positions (absolute) + justification."""
        x0, y0, x1, y1 = d['body']
        ref, val = d['ref'], d['part'].value
        if mode == 'auto':        # two-pin parts beside themselves when vertical, above when horizontal
            dirs = {(p.dx, p.dy) for p in d['pins'].values()}
            mode = 'right' if dirs <= {(0, 1), (0, -1)} else 'above'
        cx, cy = round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)
        if mode == 'right':
            r = (x1 + 1.27, cy - 1.27, 'left'); v = (x1 + 1.27, cy + 1.27, 'left')
        elif mode == 'left':
            r = (x0 - 1.27, cy - 1.27, 'right'); v = (x0 - 1.27, cy + 1.27, 'right')
        elif mode == 'below':
            r = (cx, y1 + 1.778, None); v = (cx, y1 + 4.318, None)
        elif mode == 'above':
            r = (cx, y0 - 4.318, None); v = (cx, y0 - 1.778, None)
        elif mode == 'abovebelow':   # ICs: ref over the top edge, value under the bottom edge
            r = (x0, y0 - 1.778, 'left'); v = (x0, y1 + 1.778, 'left')
        else:
            raise ValueError(mode)
        if ref_at:
            r = ref_at
        if val_at:
            v = val_at
        return [r, v]

    def N(self, ref, net):
        """Pin end of ref's (first) pin on net."""
        for (r, u), d in self.placed.items():
            if r == ref:
                for num, pt in d['pins'].items():
                    if d['part'].pins.get(num) == net:
                        return pt
        raise KeyError('%s: no %s pin on %s placed' % (self.stem, ref, net))

    def P(self, ref, num, unit=None):
        """Pin end of ref's pad num (searching the placed units)."""
        num = str(num)
        for (r, u), d in self.placed.items():
            if r == ref and (unit is None or u == unit) and num in d['pins']:
                return d['pins'][num]
        raise KeyError('%s: %s pin %s not placed' % (self.stem, ref, num))

    # -- wires --------------------------------------------------------------
    def wire(self, *pts):
        pts = [(snap(p[0]), snap(p[1])) for p in pts]
        for a, b in zip(pts, pts[1:]):
            if a == b:
                continue
            if a[0] != b[0] and a[1] != b[1]:
                raise ValueError('%s: diagonal wire %s -> %s' % (self.stem, a, b))
            self.wires.append((a, b))
        return pts[-1]

    def hv(self, a, b):
        """a -> b, horizontal first."""
        return self.wire(a, (b[0], a[1]), b)

    def vh(self, a, b):
        return self.wire(a, (a[0], b[1]), b)

    def zx(self, a, b, x):
        """a -> b through a vertical run at x."""
        return self.wire(a, (x, a[1]), (x, b[1]), b)

    def zy(self, a, b, y):
        return self.wire(a, (a[0], y), (b[0], y), b)

    def stub(self, pin, n=2.54):
        e = pin.go(n)
        self.wire(pin, e)
        return Pt(e[0], e[1], pin.dx, pin.dy)

    # -- names ----------------------------------------------------------------
    def glabel(self, pt, net, dirn=None, shape='passive'):
        """Global label at pt, its body pointing away along dirn ('L','R','U','D');
        pt may be a pin (direction from the pin)."""
        if dirn is None:
            dirn = {(-1, 0): 'L', (1, 0): 'R', (0, -1): 'U', (0, 1): 'D'}[(pt.dx, pt.dy)]
        ang = {'R': 0, 'U': 90, 'L': 180, 'D': 270}[dirn]
        self.labels.append(('global_label', net, snap(pt[0]), snap(pt[1]), ang, shape))

    def tag(self, pin, net, n=2.54, dirn=None, shape='passive'):
        """Wire stub out of a pin + global label."""
        e = self.stub(pin, n) if n else pin
        self.glabel(e, net, dirn, shape)
        return e

    def name(self, pt, net, dirn='U', flag='R', n=2.54):
        """Name a net drawn on one sheet: a short stub off its wire at pt and a
        global label on the stub (a local label would rename the net /sheet/...)."""
        dx, dy = {'U': (0, -1), 'D': (0, 1), 'L': (-1, 0), 'R': (1, 0)}[dirn]
        e = self.wire(pt, (pt[0] + dx * n, pt[1] + dy * n))
        self.glabel(e, net, flag)
        return e

    def label(self, pt, net, dirn='R'):
        ang = {'R': 0, 'U': 90, 'L': 180, 'D': 270}[dirn]
        self.labels.append(('label', net, snap(pt[0]), snap(pt[1]), ang, None))

    def rail(self, pt, net, rot=0):
        """Power symbol (GND points down, supplies up); its pin sits at pt."""
        self.rails.append((net, snap(pt[0]), snap(pt[1]), rot))

    def gnd(self, pin, n=0, rot=0):
        e = self.stub(pin, n) if n else pin
        self.rail(e, 'GND', rot)
        return e

    def sup(self, pin, net, n=0, rot=0):
        """Supply symbol at a pin (after an n mm stub); rot 90 points it left,
        180 down, 270 right -- for pins that do not face up."""
        e = self.stub(pin, n) if n else pin
        self.rail(e, net, rot)
        return e

    def flag(self, pt, net):
        self.flags.append((net, snap(pt[0]), snap(pt[1])))

    def nc(self, pin):
        self.ncs.append((snap(pin[0]), snap(pin[1])))

    def text(self, pt, s, size=1.27, justify='left'):
        self.texts.append((s, snap(pt[0]), snap(pt[1]), size, justify))

    # -- buses ----------------------------------------------------------------
    def bus(self, *pts):
        pts = [(snap(p[0]), snap(p[1])) for p in pts]
        for a, b in zip(pts, pts[1:]):
            if a[0] != b[0] and a[1] != b[1]:
                raise ValueError('diagonal bus')
            self.buses.append((a, b))

    def entry(self, pin, net, bus_x, up=True):
        """Pin -> horizontal wire -> 45 deg entry onto a vertical bus at bus_x; the
        member's local label sits on the wire next to the pin.  Returns the bus point."""
        s = 1 if bus_x > pin[0] else -1
        ex = snap(bus_x - s * 2.54)
        self.wire(pin, (ex, pin[1]))
        dy = -2.54 if up else 2.54
        self.entries.append(((ex, pin[1]), (s * 2.54, dy)))
        self.label((snap(pin[0] + s * 1.27), pin[1]), net, 'R' if s > 0 else 'L')
        return (bus_x, snap(pin[1] + dy))

    def bus_group(self, pins_nets, bus_x, up=True):
        """Entries for every (pin, net) onto one vertical bus; returns (top, bottom) bus points."""
        pts = [self.entry(p, n, bus_x, up) for p, n in pins_nets]
        ys = [p[1] for p in pts]
        self.bus((bus_x, min(ys)), (bus_x, max(ys)))
        return (bus_x, min(ys)), (bus_x, max(ys))

    def boxes(self):
        """(what, box) for every body, field, label, rail symbol and text."""
        boxes = []
        for d in self.placed.values():
            boxes.append(('body ' + d['ref'], d['body']))
            for (fx, fy, j), s in zip(d['fields'], (d['ref'], d['part'].value)):
                boxes.append(('field %s %s' % (d['ref'], s), text_box(fx, fy, s, 1.27, j)))
        for kind, net, x, y, ang, shape in self.labels:
            w = 0.9 * 1.27 * len(net) + (2.5 if kind == 'global_label' else 0.6)
            h = 1.6
            if ang == 0:
                bx = (x, y - h / 2, x + w, y + h / 2)
            elif ang == 180:
                bx = (x - w, y - h / 2, x, y + h / 2)
            elif ang == 90:
                bx = (x - h / 2, y - w, x + h / 2, y)
            else:
                bx = (x - h / 2, y, x + h / 2, y + w)
            if kind == 'label':
                bx = (bx[0], bx[1] - 0.6, bx[2], bx[3] - 0.6) if ang in (0, 180) else bx
            boxes.append(('%s %s' % (kind, net), bx))
        for net, x, y, rot in self.rails:
            ux, uy = (0, 1) if net == 'GND' else (0, -1)
            for _ in range(rot // 90):
                ux, uy = uy, -ux
            w = 0.9 * 1.27 * len(net)
            tx, ty = x + ux * (3.3 + w / 2), y + uy * 3.81
            boxes.append(('rail %s' % net, (min(x, x + ux * 2.54) - (1.0 if ux == 0 else 0), min(y, y + uy * 2.54) - (1.0 if uy == 0 else 0),
                                            max(x, x + ux * 2.54) + (1.0 if ux == 0 else 0), max(y, y + uy * 2.54) + (1.0 if uy == 0 else 0))))
            boxes.append(('rail text %s' % net, (tx - w / 2, ty - 0.8, tx + w / 2, ty + 0.8)))
        for s, x, y, size, j in self.texts:
            for i, line in enumerate(s.split('\n')):
                boxes.append(('text', text_box(x, y + i * size * 1.6, line, size, j)))
        return boxes

    def translate(self, dx, dy):
        """Move the whole drawing (dx, dy multiples of 2.54 keep every grid)."""
        mv = lambda p: (snap(p[0] + dx), snap(p[1] + dy))
        for d in self.placed.values():
            d['x'], d['y'] = snap(d['x'] + dx), snap(d['y'] + dy)
            d['pins'] = {n: Pt(p[0] + dx, p[1] + dy, p.dx, p.dy, p.owner) for n, p in d['pins'].items()}
            x0, y0, x1, y1 = d['body']
            d['body'] = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
            d['fields'] = [(fx + dx, fy + dy, j) for fx, fy, j in d['fields']]
        self.wires = [(mv(a), mv(b)) for a, b in self.wires]
        self.buses = [(mv(a), mv(b)) for a, b in self.buses]
        self.entries = [(mv(p), s) for p, s in self.entries]
        self.labels = [(k, n) + mv((x, y)) + (a, s) for k, n, x, y, a, s in self.labels]
        self.rails = [(n,) + mv((x, y)) + (r,) for n, x, y, r in self.rails]
        self.flags = [(n,) + mv((x, y)) for n, x, y in self.flags]
        self.ncs = [mv(p) for p in self.ncs]
        self.texts = [(s,) + mv((x, y)) + (z, j) for s, x, y, z, j in self.texts]

    def center(self):
        """Centre the drawing in the frame, clear of the title block."""
        bx = [b for _, b in self.boxes()] + [(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
                                             for a, b in self.wires + self.buses]
        x0, y0 = min(b[0] for b in bx), min(b[1] for b in bx)
        x1, y1 = max(b[2] for b in bx), max(b[3] for b in bx)
        W, H = self.size
        g = 2.54
        dx = round(((W / 2) - (x0 + x1) / 2) / g) * g
        dy = round(((15 + H - 45) / 2 - (y0 + y1) / 2) / g) * g
        if y0 + dy < 15:
            dy = math.ceil((15 - y0) / g) * g
        self.translate(dx, dy)

    # ======================================================================
    def check(self):
        """Union-find connectivity + geometry lint; raises on any error."""
        err = self.errors
        par = {}

        def F(a):
            while par.setdefault(a, a) != a:
                par[a] = par[par[a]]
                a = par[a]
            return a

        def U(a, b):
            par[F(a)] = F(b)
        pin_at = defaultdict(list)       # point -> [(ref, num, net)]
        for d in self.placed.values():
            for num, pt in d['pins'].items():
                pin_at[tuple(pt)].append((d['ref'], num, d['part'].pins.get(num)))
        # wire ends, and the points that lie on a run
        ends = defaultdict(int)
        for a, b in self.wires:
            ends[a] += 1; ends[b] += 1
            U(a, b)
        pts = set(pin_at) | set(ends) | {(l[2], l[3]) for l in self.labels} | \
            {(r[1], r[2]) for r in self.rails} | {(f[1], f[2]) for f in self.flags}
        for e in self.entries:
            pts.add(e[0])
        juncs = set()

        def on_run(p, a, b):
            if a[0] == b[0] == p[0]:
                return min(a[1], b[1]) < p[1] < max(a[1], b[1])
            if a[1] == b[1] == p[1]:
                return min(a[0], b[0]) < p[0] < max(a[0], b[0])
            return False
        for a, b in self.wires:
            for p in pts:
                if on_run(p, a, b):
                    if p in ends or p in {(l[2], l[3]) for l in self.labels} or \
                            p in {(r[1], r[2]) for r in self.rails}:
                        U(p, a)
                        if p in ends:
                            juncs.add(p)
                    if p in pin_at:
                        err.append('pin %s on the run of wire %s-%s' % (pin_at[p], a, b))
        for p, n in ends.items():
            k = n + len(pin_at.get(p, []))
            if k >= 3:
                juncs.add(p)
            if n == 1 and p not in pin_at and p not in juncs and \
                    p not in {(l[2], l[3]) for l in self.labels} and p not in {(r[1], r[2]) for r in self.rails} and \
                    p not in {e[0] for e in self.entries} and p not in {f[1:] for f in self.flags}:
                err.append('dangling wire end at %s' % (p,))
        self.junctions = sorted(juncs)
        # groups
        names = defaultdict(set)
        for kind, net, x, y, ang, shape in self.labels:
            names[F((x, y))].add(net)
        for net, x, y, rot in self.rails:
            names[F((x, y))].add(net)
        for net, x, y in self.flags:
            names[F((x, y))].add(net)
        members = defaultdict(list)
        for p, lst in pin_at.items():
            for ref, num, net in lst:
                members[F(p)].append((ref, num, net))
        ncset = set(self.ncs)
        for g in set(members) | set(names):
            nets = {n for (_, _, n) in members.get(g, [])}
            nm = names.get(g, set())
            if None in nets:
                for ref, num, net in members[g]:
                    if net is None and (len(members[g]) > 1 or nm or g not in {F(c) for c in ncset}):
                        if not (g in {F(c) for c in ncset} and len({(r, n) for r, n, _ in members[g]}) == 1):
                            err.append('NC pin %s %s is connected/unflagged (%s)' % (ref, num, nm or ''))
                nets.discard(None)
            if len(nets) > 1:
                err.append('short: %s join %s' % (sorted(nets), sorted(members[g])[:6]))
            if len(nm) > 1:
                err.append('two names on one net: %s' % sorted(nm))
            if nets and nm and nets != nm:
                err.append('net %s named %s' % (sorted(nets), sorted(nm)))
            if nets and not nm:
                err.append('unnamed group %s: %s' % (sorted(nets), sorted(members[g])[:6]))
        # every design pin on this sheet placed and reached
        for d in self.placed.values():
            for num, pt in d['pins'].items():
                net = d['part'].pins.get(num)
                g = F(tuple(pt))
                if net is None:
                    if tuple(pt) not in ncset and len(pin_at[tuple(pt)]) == 1:
                        err.append('%s pin %s: NC without a flag' % (d['ref'], num))
                elif g not in names:
                    err.append('%s pin %s (%s) floats' % (d['ref'], num, net))
        for ref, p in self.parts.items():
            sym = self.syms[p.lib_id]
            for u in units_of(sym):
                if (ref, u) not in self.placed:
                    err.append('%s unit %d not placed' % (ref, u))
        # wires through bodies
        for d in self.placed.values():
            x0, y0, x1, y1 = d['body']
            own = {tuple(p) for p in d['pins'].values()}
            for a, b in self.wires:
                if a in own or b in own:      # a pin's own stub may start inside the drawing
                    continue
                if a[0] == b[0] and x0 + 0.01 < a[0] < x1 - 0.01 and \
                        max(min(a[1], b[1]), y0) < min(max(a[1], b[1]), y1) - 0.01:
                    err.append('wire %s-%s through %s' % (a, b, d['ref']))
                if a[1] == b[1] and y0 + 0.01 < a[1] < y1 - 0.01 and \
                        max(min(a[0], b[0]), x0) < min(max(a[0], b[0]), x1) - 0.01:
                    err.append('wire %s-%s through %s' % (a, b, d['ref']))
        boxes = self.boxes()
        for i in range(len(boxes) if self.lint else 0):
            for k in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[k]
                if overlap(a[1], b[1], 0.05):
                    # a symbol's own fields may sit inside its bounding box (gates)
                    if a[0].startswith('body') and b[0].startswith('field ' + a[0][5:] + ' '):
                        continue
                    if b[0].startswith('body') and a[0].startswith('field ' + b[0][5:] + ' '):
                        continue
                    err.append('overlap: %s / %s' % (a[0], b[0]))
        W, H = self.size
        for name, b in boxes:
            if b[0] < 10 or b[1] < 10 or b[2] > W - 10 or b[3] > H - 40 and b[2] > W - 180:
                err.append('off the page / under the title block: %s %s' % (name, b))
        if err:
            msg = '%s:\n  %s' % (self.stem, '\n  '.join(err[:60]))
            if os.environ.get('SCH_DRAFT'):     # layout work: report, write anyway
                print(msg)
            else:
                raise SystemExit(msg)
