#!/usr/bin/env python3
"""Generate the schematic (root block diagram + 4 sheets) from design.py.

design.py owns the parts and the pin->net map; tools/sch_layout.py owns the
drawing: where each symbol sits, which pins are joined by real wires, where
the notes go.  From those this script draws a conventional schematic:

  * rails (+5V, +3V3, +3V3_RP, CONS_5V, VBUS, DVDD, GND) as power symbols;
  * pins joined in sch_layout.WIRES as orthogonal wires (junction dots added
    wherever three or more ends meet);
  * nets that leave the sheet as hierarchical labels, wired on the root sheet
    between the sheet blocks (signal flow left to right);
  * every other net named once per wired group with a local label;
  * unconnected pins with no-connect flags.

Symbols come from tools/symcache.sexpr (stock KiCad symbols as flattened by
eeschema, see harvest_symbols.py) plus the project library, which this script
also (re)writes: FujiNet-Astrocade.kicad_sym.  check_sch_layout.py verifies
the drawing (netlist == design.py, nothing overlaps).

Usage: python3 tools/gen_sch.py      (writes into the project directory)
"""
import os, sys, uuid, copy, json, math, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
import design as D
import sch_layout as LAY

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
DATE = '2026-10-02'
NS = uuid.UUID('6f1c9a1e-3a52-4d7e-9b7d-0a57a0cade00')
PAPER = {'A3': (420.0, 297.0), 'A2': (594.0, 420.0)}

# rail -> power symbol lib id (the project clones take power:+3V3's arrow)
RAILS = {'GND': 'power:GND', '+3V3': 'power:+3V3', '+5V': 'power:+5V', 'VBUS': 'power:VBUS',
         '+3V3_RP': D.LIB + ':+3V3_RP', 'CONS_5V': D.LIB + ':CONS_5V', 'DVDD': D.LIB + ':DVDD'}
CUSTOM_RAILS = {'+3V3_RP': 'RP2354A 3.3V rail (AP2112K LDO)', 'CONS_5V': 'console +5V (edge land 25)',
                'DVDD': 'RP2350 1.1V core (on-chip SMPS)'}


def uid(*k):
    return Q(str(uuid.uuid5(NS, '/'.join(map(str, k)))))


def font(size=1.27):
    return ['effects', ['font', ['size', size, size]]]


def hidden():
    return ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]


def esc(t):
    """Text for a KiCad string: sexpr.dump skips quote-escaping once a backslash is present."""
    return Q(t.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n'))


def r2(v):
    return round(v, 2)


# ---------------------------------------------------------------------------
# project-library symbols
def box_symbol(name, ref, value, footprint, desc, left, right=(), bottom=(), top=(), w=15.24):
    """left/right/bottom/top: lists of (number, name, etype).  2.54 pitch."""
    n = max(len(left), len(right), 1)
    h = (n + 1) * 2.54
    y0 = round(((n - 1) * 2.54 / 2) / 1.27) * 1.27
    top_y = y0 + 2.54
    bot_y = round((top_y - h) / 1.27) * 1.27
    half = w / 2
    body = ['symbol', Q(name + '_0_1'),
            ['rectangle', ['start', -half, top_y], ['end', half, bot_y],
             ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]]
    pins = ['symbol', Q(name + '_1_1')]

    def pin(num, nm, et, x, y, ang):
        pins.append(['pin', et, 'line', ['at', x, y, ang], ['length', 2.54],
                     ['name', Q(nm), font()], ['number', Q(str(num)), font()]])
    for i, (num, nm, et) in enumerate(left):
        pin(num, nm, et, -half - 2.54, y0 - i * 2.54, 0)
    for i, (num, nm, et) in enumerate(right):
        pin(num, nm, et, half + 2.54, y0 - i * 2.54, 180)
    for i, (num, nm, et) in enumerate(bottom):
        x = -((len(bottom) - 1) * 2.54) / 2 + i * 2.54
        pin(num, nm, et, round(x / 1.27) * 1.27, bot_y - 2.54, 90)
    for i, (num, nm, et) in enumerate(top):
        x = -((len(top) - 1) * 2.54) / 2 + i * 2.54
        pin(num, nm, et, round(x / 1.27) * 1.27, top_y + 2.54, 270)
    return ['symbol', Q(name), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
            ['in_bom', 'yes'], ['on_board', 'yes'],
            ['property', Q('Reference'), Q(ref), ['at', 0, top_y + 1.27, 0], font()],
            ['property', Q('Value'), Q(value), ['at', 0, bot_y - 5.08, 0], font()],
            ['property', Q('Footprint'), Q(footprint), ['at', 0, 0, 0], hidden()],
            ['property', Q('Datasheet'), Q(''), ['at', 0, 0, 0], hidden()],
            ['property', Q('Description'), Q(desc), ['at', 0, 0, 0], hidden()],
            body, pins]


def rail_symbol(base, name, desc):
    """A global power symbol for `name`, drawn like stock `base` (power:+3V3)."""
    s = copy.deepcopy(base)
    s[1] = Q(name)
    for e in s:
        if isinstance(e, list) and e and e[0] == 'property':
            if e[1] == 'Value':
                e[2] = Q(name)
            elif e[1] == 'Description':
                e[2] = Q('Power symbol creates a global label with name "%s": %s' % (name, desc))
    base_name = str(base[1]).split(':', 1)[1]
    for sub in findall(s, 'symbol'):
        sub[1] = Q(name + str(sub[1])[len(base_name):])
    return s


def project_symbols(stock):
    old = stock['FujiNet-Astrocade:Astrocade_Cart_Edge_26']
    edge = copy.deepcopy(old)
    edge[1] = Q('Astrocade_Cart_Edge_26')
    for s in findall(edge, 'symbol'):
        s[1] = Q(s[1].replace('FujiNet-Astrocade:', ''))
    sd = box_symbol('MicroSD_TF015', 'J', 'microSD', D.FP('TF-SMD_TF-015'),
                    'microSD push-push socket, SOFNG TF-015 (LCSC C113206); CD closes to the shell with a card in',
                    left=[(1, 'DAT2', 'bidirectional'), (2, 'DAT3/CS', 'bidirectional'),
                          (3, 'CMD/DI', 'input'), (4, 'VDD', 'power_in'), (5, 'CLK', 'input'),
                          (6, 'VSS', 'power_in'), (7, 'DAT0/DO', 'bidirectional'),
                          (8, 'DAT1', 'bidirectional'), (9, 'CD', 'passive')],
                    bottom=[(10, 'SH', 'passive'), (11, 'SH', 'passive'),
                            (12, 'SH', 'passive'), (13, 'SH', 'passive')], w=17.78)
    rails = [rail_symbol(stock['power:+3V3'], n, d) for n, d in CUSTOM_RAILS.items()]
    lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('fujinet_gen')],
           ['generator_version', Q('1.0')], edge, sd] + rails
    open(os.path.join(PRJ, D.LIB + '.kicad_sym'), 'w').write(dump(lib) + '\n')
    cache = {}
    for s in [edge, sd] + rails:
        c = copy.deepcopy(s)
        c[1] = Q(D.LIB + ':' + s[1])
        cache[c[1]] = c
    return cache


def load_symbols():
    t = parse(open(os.path.join(HERE, 'symcache.sexpr')).read())
    syms = {s[1]: s for s in t[1:]}
    syms.update(project_symbols(syms))
    return syms


# ---------------------------------------------------------------------------
# symbol geometry
def sym_pins(sym):
    """[(unit, number, x, y, angle)] in library coordinates (y up); body style 1 only."""
    out = []
    for sub in findall(sym, 'symbol'):
        unit, style = (int(v) for v in sub[1].rsplit('_', 2)[-2:])
        if style > 1:
            continue
        for p in findall(sub, 'pin'):
            at = find(p, 'at')
            out.append((unit, str(find(p, 'number')[1]), float(at[1]), float(at[2]), int(float(at[3]))))
    return out


def pin_names(sym):
    out = {}
    for sub in findall(sym, 'symbol'):
        for p in findall(sub, 'pin'):
            out[str(find(p, 'number')[1])] = str(find(p, 'name')[1])
    return out


def body_box(sym, unit):
    """Graphic extents of the body (pins excluded), library coordinates."""
    xs, ys = [], []

    def walk(e):
        for x in e:
            if isinstance(x, list) and x:
                if x[0] in ('xy', 'start', 'end', 'center', 'mid') and len(x) >= 3:
                    xs.append(float(x[1])); ys.append(float(x[2]))
                elif x[0] == 'circle':
                    c, r = find(x, 'center'), float(find(x, 'radius')[1])
                    xs.extend([float(c[1]) - r, float(c[1]) + r]); ys.extend([float(c[2]) - r, float(c[2]) + r])
                elif x[0] not in ('property', 'pin'):
                    walk(x)
    for sub in findall(sym, 'symbol'):
        u, style = (int(v) for v in sub[1].rsplit('_', 2)[-2:])
        if u in (0, unit) and style <= 1:
            walk(sub)
    if not xs:
        return (-1.27, -1.27, 1.27, 1.27)
    return (min(xs), min(ys), max(xs), max(ys))


def units_of(sym):
    us = sorted({u for u, *_ in sym_pins(sym) if u})
    return us or [1]


def xf(px, py, rot, mirror):
    """library point -> sheet offset (y down) for a symbol at angle rot / mirror."""
    if mirror == 'y':
        px = -px
    elif mirror == 'x':
        py = -py
    a = math.radians(rot)
    rx = px * math.cos(a) - py * math.sin(a)
    ry = px * math.sin(a) + py * math.cos(a)
    return r2(rx), r2(-ry)


DIRS = {(1, 0): 'R', (-1, 0): 'L', (0, -1): 'U', (0, 1): 'D'}
STEP = {'R': (1, 0), 'L': (-1, 0), 'U': (0, -1), 'D': (0, 1)}


def outward(ang, rot, mirror):
    """Pin 'at' angle points from the tip into the body; outward is the opposite."""
    a = math.radians(ang + 180)
    dx, dy = xf(math.cos(a), math.sin(a), rot, mirror)
    return DIRS[(int(round(dx)), int(round(dy)))]


def verify_pin_tables(syms):
    """design.py's hand-written pin numbers against the symbols they index."""
    names = pin_names(syms['MCU_RaspberryPi:RP2354A'])
    for g, pin in D.RP_GPIO_PIN.items():
        nm = names.get(str(pin), '')
        if not re.match(r'GPIO%d(/|$)' % g, nm):
            raise SystemExit('RP_GPIO_PIN: GPIO%d -> pin %d, but the symbol calls that pin %r' % (g, pin, nm))
    for pin in D.RP_IOVDD_PINS:
        if names.get(str(pin)) != 'IOVDD':
            raise SystemExit('RP_IOVDD_PINS: pin %d is %r' % (pin, names.get(str(pin))))
    for pin in D.RP_DVDD_PINS:
        if names.get(str(pin)) != 'DVDD':
            raise SystemExit('RP_DVDD_PINS: pin %d is %r' % (pin, names.get(str(pin))))
    names = pin_names(syms['RF_Module:ESP32-S3-WROOM-1'])
    for fn, pad in D.S3_PAD.items():
        for p in (pad if isinstance(pad, list) else [pad]):
            nm = names[str(p)]
            if nm != fn and not (fn == 'IO19' and nm == 'USB_D-') and not (fn == 'IO20' and nm == 'USB_D+'):
                raise SystemExit('S3_PAD: %s -> pad %d, but the symbol calls it %r' % (fn, p, nm))


# ---------------------------------------------------------------------------
def sheet_nets():
    """net -> set of sheets it has pins on."""
    out = {}
    for p in D.PARTS:
        for n in p.pins.values():
            if n:
                out.setdefault(n, set()).add(p.sheet)
    return out


def hier_nets(stem):
    sn = sheet_nets()
    return sorted(n for n, s in sn.items() if stem in s and len(s) > 1 and n not in RAILS)


class Sheet:
    def __init__(self, stem, spec, syms, root_uuid, sheet_uuid):
        self.stem, self.spec, self.syms = stem, spec, syms
        self.root_uuid, self.sheet_uuid = root_uuid, sheet_uuid
        self.items, self.used = [], {}
        self.parts = {p.ref: p for p in D.PARTS if p.sheet == stem}
        self.tips = {}          # 'REF.pin' -> (x, y, dir)
        self.segs = []          # wire segments ((x1,y1),(x2,y2))
        self.anchors = []       # points where power symbols / labels attach
        self.npwr = 0
        self.hier = set(hier_nets(stem))
        self.boxes = []         # (ref, x0, y0, x1, y1) of placed bodies, for check_sch_layout
        self.dx, self.dy = spec.get('shift', (0, 0))   # moves the whole drawing (all absolute coordinates)

    def use(self, lib_id):
        self.used[lib_id] = self.syms[lib_id]
        return self.syms[lib_id]

    # -- symbols ------------------------------------------------------------
    def place_part(self, p, x, y, rot=0, mirror=None, fields=None):
        sym = self.use(p.lib_id)
        for u in units_of(sym):
            ux, uy = x, y
            if isinstance(self.spec['place'][p.ref], dict):
                ux, uy = self.spec['place'][p.ref]['units'].get(u, (x, y))
                ux, uy = r2(ux + self.dx), r2(uy + self.dy)
            self._instance(p, sym, u, ux, uy, rot, mirror, fields)

    def _instance(self, p, sym, u, x, y, rot, mirror, fields):
        path = '/%s/%s' % (self.root_uuid, self.sheet_uuid)
        bx0, by0, bx1, by1 = body_box(sym, u)
        cs = [xf(a, b, rot, mirror) for a in (bx0, bx1) for b in (by0, by1)]
        L, R = x + min(c[0] for c in cs), x + max(c[0] for c in cs)
        T, B = y + min(c[1] for c in cs), y + max(c[1] for c in cs)
        self.boxes.append((p.ref, r2(L), r2(T), r2(R), r2(B)))
        pins = [(n, px, py, a) for (uu, n, px, py, a) in sym_pins(sym) if uu in (0, u)]
        dirs = {outward(a, rot, mirror) for (n, px, py, a) in pins}
        # Reference / Value placement
        fx = (fields or {}).get(p.ref)
        if fx:                                                # relative to the symbol origin
            (rx, ry, rj), (vx, vy, vj) = fx
            rx, ry, vx, vy = x + rx, y + ry, x + vx, y + vy
        elif len(pins) <= 2 and dirs <= {'U', 'D'}:         # upright 2-pin passive: fields to the right
            rx, ry, rj = R + 1.27, y - 1.27, 'left'
            vx, vy, vj = R + 1.27, y + 1.27, 'left'
        elif len(pins) <= 3 and dirs <= {'L', 'R'}:           # horizontal 2/3-pin: fields above
            rx, ry, rj = (L + R) / 2, T - 3.81, None
            vx, vy, vj = (L + R) / 2, T - 1.27, None
        else:                                                 # ICs: above the top-left corner
            rx, ry, rj = L, T - 3.81, 'left'
            vx, vy, vj = L, T - 1.27, 'left'
            if 'U' in dirs:
                ry, vy = T - 8.89, T - 6.35
        just = lambda j: (['justify', j] if j else None)
        eff = lambda j: [x for x in ['effects', ['font', ['size', 1.27, 1.27]], just(j)] if x]
        fa = (-rot) % 360 % 180      # KiCad adds the symbol's rotation to its fields': keep them horizontal
        e = ['symbol', ['lib_id', Q(p.lib_id)], ['at', x, y, rot]]
        if mirror:
            e.append(['mirror', mirror])
        e += [['unit', u], ['exclude_from_sim', 'no'], ['in_bom', 'yes' if p.bom else 'no'],
              ['on_board', 'yes'], ['dnp', 'yes' if p.dnp else 'no'], ['uuid', uid(self.stem, p.ref, u)],
              ['property', Q('Reference'), Q(p.ref), ['at', r2(rx), r2(ry), fa], eff(rj)],
              ['property', Q('Value'), Q(p.value), ['at', r2(vx), r2(vy), fa], eff(vj)],
              ['property', Q('Footprint'), Q(p.footprint), ['at', x, y, 0], hidden()],
              ['property', Q('Datasheet'), Q(self._datasheet(sym)), ['at', x, y, 0], hidden()],
              ['property', Q('Description'), Q(p.desc), ['at', x, y, 0], hidden()]]
        for k, v in (('MPN', p.mpn), ('LCSC', p.lcsc)):
            if v:
                e.append(['property', Q(k), Q(v), ['at', x, y, 0], hidden()])
        for (n, px, py, a) in pins:
            e.append(['pin', Q(n), ['uuid', uid(self.stem, p.ref, u, 'pin', n)]])
        e.append(['instances', ['project', Q(D.PROJECT), ['path', Q(path), ['reference', Q(p.ref)], ['unit', u]]]])
        self.items.append(e)
        for (n, px, py, a) in pins:
            if n not in p.pins:
                raise SystemExit('%s pin %s not assigned in design.py' % (p.ref, n))
            dx, dy = xf(px, py, rot, mirror)
            key = '%s.%s' % (p.ref, n)
            tip = (r2(x + dx), r2(y + dy), outward(a, rot, mirror))
            if key in self.tips and self.tips[key][:2] != tip[:2]:
                continue
            self.tips[key] = tip

    @staticmethod
    def _datasheet(sym):
        for pr in findall(sym, 'property'):
            if pr[1] == 'Datasheet':
                return pr[2]
        return ''

    # -- connections --------------------------------------------------------
    def wire(self, a, b):
        if a == b:
            return
        self.segs.append((a, b))
        self.items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                           ['stroke', ['width', 0], ['type', 'default']], ['uuid', uid(self.stem, 'w', a, b)]])

    def power(self, net, x, y, d):
        """Rail symbol attached at (x, y), its graphic pointing in direction d."""
        lib_id = RAILS[net]
        sym = self.use(lib_id)
        up = net != 'GND'                 # stock graphics: rails point up, GND down
        rot = ({'U': 0, 'D': 180, 'L': 90, 'R': 270} if up else {'D': 0, 'U': 180, 'R': 90, 'L': 270})[d]
        self.npwr += 1
        ref = '#PWR%03d' % self.npwr
        vy = {'U': -3.81, 'D': 3.81}.get(d, 0)
        vx = {'L': -2.54, 'R': 2.54}.get(d, 0)
        vj = {'L': 'right', 'R': 'left'}.get(d)
        eff = ['effects', ['font', ['size', 1.27, 1.27]]] + ([['justify', vj]] if vj else [])
        path = '/%s/%s' % (self.root_uuid, self.sheet_uuid)
        self.items.append(['symbol', ['lib_id', Q(lib_id)], ['at', x, y, rot], ['unit', 1],
                           ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'], ['dnp', 'no'],
                           ['uuid', uid(self.stem, ref)],
                           ['property', Q('Reference'), Q(ref), ['at', x, y, 0], hidden()],
                           ['property', Q('Value'), Q(net), ['at', r2(x + vx), r2(y + vy), (-rot) % 360 % 180], eff],
                           ['property', Q('Footprint'), Q(''), ['at', x, y, 0], hidden()],
                           ['property', Q('Datasheet'), Q(''), ['at', x, y, 0], hidden()],
                           ['property', Q('Description'), Q(''), ['at', x, y, 0], hidden()],
                           ['pin', Q('1'), ['uuid', uid(self.stem, ref, 'pin')]],
                           ['instances', ['project', Q(D.PROJECT), ['path', Q(path), ['reference', Q(ref)], ['unit', 1]]]]])
        self.anchors.append((x, y))

    def flag(self, net, x, y):
        """PWR_FLAG + rail symbol sharing one point (flag on the opposite side)."""
        self.power(net, x, y, 'D' if net == 'GND' else 'U')
        self.pwr_flag(x, y, 0 if net == 'GND' else 180)

    def pwr_flag(self, x, y, rot=0):
        self.use('power:PWR_FLAG')
        self.npwr += 1
        ref = '#FLG%03d' % self.npwr
        path = '/%s/%s' % (self.root_uuid, self.sheet_uuid)
        vy = -3.81 if rot == 0 else 3.81
        self.items.append(['symbol', ['lib_id', Q('power:PWR_FLAG')], ['at', x, y, rot], ['unit', 1],
                           ['exclude_from_sim', 'no'], ['in_bom', 'no'], ['on_board', 'no'], ['dnp', 'no'],
                           ['uuid', uid(self.stem, ref)],
                           ['property', Q('Reference'), Q(ref), ['at', x, y, 0], hidden()],
                           ['property', Q('Value'), Q('PWR_FLAG'), ['at', x + 1.27, r2(y + vy), 0],
                            ['effects', ['font', ['size', 1.0, 1.0]], ['justify', 'left']]],
                           ['property', Q('Footprint'), Q(''), ['at', x, y, 0], hidden()],
                           ['property', Q('Datasheet'), Q(''), ['at', x, y, 0], hidden()],
                           ['property', Q('Description'), Q(''), ['at', x, y, 0], hidden()],
                           ['pin', Q('1'), ['uuid', uid(self.stem, ref, 'pin')]],
                           ['instances', ['project', Q(D.PROJECT), ['path', Q(path), ['reference', Q(ref)], ['unit', 1]]]]])

    def label(self, net, x, y, d):
        """Name `net` at (x, y); text runs in direction d (away from the pin)."""
        self.anchors.append((x, y))
        if net in self.hier:
            shape = LAY.HIER_SHAPE.get((self.stem, net), 'bidirectional')
            ang = {'R': 0, 'U': 90, 'L': 180, 'D': 270}[d]
            j = 'left' if d in ('R', 'U') else 'right'
            self.items.append(['hierarchical_label', Q(net), ['shape', shape], ['at', x, y, ang],
                               ['effects', ['font', ['size', 1.27, 1.27]], ['justify', j]],
                               ['uuid', uid(self.stem, 'hl', net, x, y)]])
        else:
            ang = {'R': 0, 'U': 90, 'L': 180, 'D': 270}[d]
            j = 'left' if d in ('R', 'U') else 'right'
            self.items.append(['label', Q(net), ['at', x, y, ang],
                               ['effects', ['font', ['size', 1.27, 1.27]], ['justify', j, 'bottom']],
                               ['uuid', uid(self.stem, 'lb', net, x, y)]])

    def text(self, x, y, s, size=1.524):
        self.items.append(['text', esc(s), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                           ['effects', ['font', ['size', size, size]], ['justify', 'left', 'top']],
                           ['uuid', uid(self.stem, 'txt', x, y)]])

    def junctions(self):
        pts = {}
        for a, b in self.segs:
            for p in (a, b):
                pts[p] = pts.get(p, 0) + 1
        for (x, y, d) in self.tips.values():
            if (x, y) in pts:
                pts[(x, y)] += 1
        for p in list(pts):
            for a, b in self.segs:
                if p in (a, b):
                    continue
                if a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]) or \
                   a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0]):
                    pts[p] += 2
        for p, n in sorted(pts.items()):
            if n >= 3:
                self.items.append(['junction', ['at', p[0], p[1]], ['diameter', 0], ['color', 0, 0, 0, 0],
                                   ['uuid', uid(self.stem, 'j', p)]])

    # -- the sheet ------------------------------------------------------------
    def point(self, e):
        """A polyline entry: 'REF.pin' (its tip), (x, y), or ('REF.pin', dx, dy)."""
        if isinstance(e, str):
            if e not in self.tips:
                raise SystemExit('%s: %s is not a pin here' % (self.stem, e))
            return self.tips[e][:2]
        if len(e) == 3:
            t = self.point(e[0])
            return (r2(t[0] + e[1]), r2(t[1] + e[2]))
        return (r2(e[0] + self.dx), r2(e[1] + self.dy))

    def polyline(self, pl):
        pts, vfirst = [], False
        for e in pl:
            if e == '|':
                vfirst = True
                continue
            p = self.point(e)
            if pts and pts[-1][0] != p[0] and pts[-1][1] != p[1]:
                q = pts[-1]
                pts.append((q[0], p[1]) if vfirst else (p[0], q[1]))
            vfirst = False
            pts.append(p)
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)

    @staticmethod
    def on_seg(p, s):
        (a, b) = s
        if a[0] == b[0] == p[0]:
            return min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
        if a[1] == b[1] == p[1]:
            return min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        return False

    def groups(self):
        """Connected pin groups, from geometry: wires touching pins/each other, coincident tips."""
        keys = list(self.tips)
        n = len(keys) + len(self.segs)
        parent = list(range(n))

        def find_(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def join(i, j):
            parent[find_(i)] = find_(j)
        at = {}
        for i, k in enumerate(keys):
            p = self.tips[k][:2]
            if p in at:
                join(i, at[p])
            at[p] = i
        ends = {p for s in self.segs for p in s}
        for si, s in enumerate(self.segs):
            j = len(keys) + si
            for i, k in enumerate(keys):
                p = self.tips[k][:2]
                if self.on_seg(p, s):
                    if p not in ends:   # KiCad joins a pin to a wire only at an end or a junction
                        raise SystemExit('%s: pin %s sits in the middle of wire %s' % (self.stem, k, s))
                    join(i, j)
            for sj, t in enumerate(self.segs[:si]):
                if any(self.on_seg(p, t) for p in s) or any(self.on_seg(p, s) for p in t):
                    join(j, len(keys) + sj)
        out, segs = {}, {}
        for i, k in enumerate(keys):
            out.setdefault(find_(i), []).append(k)
        for si, s in enumerate(self.segs):
            r = find_(len(keys) + si)
            if r not in out:
                raise SystemExit('%s: wire %s touches no pin' % (self.stem, s))
            segs.setdefault(r, []).append(s)
        return [(v, segs.get(r, [])) for r, v in out.items()]

    def build(self):
        spec = self.spec
        missing = set(self.parts) - set(spec['place'])
        if missing:
            raise SystemExit('%s: no placement for %s' % (self.stem, ', '.join(sorted(missing))))
        for ref, pl in spec['place'].items():
            if isinstance(pl, dict):
                x, y = pl['units'][1]
                rot, mirror = pl.get('rot', 0), pl.get('mirror')
            else:
                x, y, rot, mirror = (tuple(pl) + (0, None))[:4]
            self.place_part(self.parts[ref], r2(x + self.dx), r2(y + self.dy), rot, mirror, spec.get('fields'))
        for pl in spec.get('wires', []):
            self.polyline(pl)
        spec_pts = [self.point(lb[1]) for lb in spec.get('labels', [])] + \
                   [self.point(r[1]) for r in spec.get('rails', [])]
        anchor = spec.get('anchor', {})       # 'REF.pin' -> direction ('U','D','L','R') or 'none'
        stub = spec.get('stub', {})           # 'REF.pin' -> (length, direction): a lead before the symbol/label
        for keys, gsegs in self.groups():
            nets = {self.net_of(k) for k in keys}
            if len(nets) > 1:
                raise SystemExit('%s: %s are drawn connected but carry nets %s' % (self.stem, keys, nets))
            net = nets.pop()
            if net is None:
                for k in keys:
                    x, y, d = self.tips[k]
                    self.items.append(['no_connect', ['at', x, y], ['uuid', uid(self.stem, 'nc', k)]])
                continue
            chosen = [k for k in keys if k in anchor]
            if not chosen:
                if any(any(self.on_seg(p, sg) for sg in gsegs) or p in [self.tips[k][:2] for k in keys]
                       for p in spec_pts):
                    continue                  # named on its wire by a 'labels' / 'rails' entry
                chosen = [keys[0]]
            for k in chosen:
                if anchor.get(k) == 'none':
                    continue
                x, y, d = self.tips[k]
                d = anchor.get(k, d)
                if k in stub:
                    ln, sd = stub[k]
                    sx, sy = STEP[sd]
                    nx, ny = r2(x + sx * ln), r2(y + sy * ln)
                    self.wire((x, y), (nx, ny))
                    x, y = nx, ny
                    if k not in anchor:
                        d = sd
                if net in RAILS:
                    self.power(net, x, y, d)
                else:
                    self.label(net, x, y, d)
        ends = {q for sg in self.segs for q in sg}
        for pt in [r[1] for r in spec.get('rails', [])] + list(spec.get('pwr_flags', [])):
            if self.point(pt) not in ends:
                raise SystemExit('%s: rail/flag at %s is not on a wire end or junction' % (self.stem, pt))
        for net, pt, d in spec.get('rails', []):   # rail symbols on wire points
            p = self.point(pt)
            self.power(net, p[0], p[1], d)
        for pt in spec.get('pwr_flags', []):        # PWR_FLAG on a wire point (graphic up)
            p = self.point(pt)
            self.pwr_flag(p[0], p[1])
        for lb in spec.get('labels', []):      # extra names on wires: (net, point, dir)
            p = self.point(lb[1])
            self.label(lb[0], p[0], p[1], lb[2])
        for (net, x, y) in spec.get('flags', []):
            self.flag(net, r2(x + self.dx), r2(y + self.dy))
        for t in spec.get('text', []):
            self.text(r2(t[0] + self.dx), r2(t[1] + self.dy), *t[2:])
        self.junctions()
        return self.document()

    def net_of(self, key):
        ref, pin = key.split('.', 1)
        return self.parts[ref].pins.get(pin)

    def document(self):
        stem = self.stem
        title = [t for s, t, pg in D.SHEETS if s == stem][0]
        tb = ['title_block', ['title', Q('FujiNet Astrocade Rev0 - ' + title)], ['date', Q(DATE)],
              ['rev', Q('0')], ['company', Q('FujiNet')],
              ['comment', 1, Q('Generated by tools/gen_sch.py from tools/design.py + tools/sch_layout.py - edit those, not this file')],
              ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-INTV-Rev0 / PiNTY CARD)')],
              ['comment', 3, Q('Rev0 audit 2026-10-02: kicad-happy + manufacturer datasheets; see docs/design-review-rev0.md')]]
        lib_symbols = ['lib_symbols'] + [self.used[k] for k in sorted(self.used)]
        return ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
                ['generator_version', Q('9.0')], ['uuid', Q(self.sheet_uuid)],
                ['paper', Q(self.spec.get('paper', 'A3'))], tb, lib_symbols] + self.items + [['embedded_fonts', 'no']]


# ---------------------------------------------------------------------------
def build_root(root_uuid, sheet_uuids):
    R = LAY.ROOT
    items = []
    pin_at = {}
    for stem, title, page in D.SHEETS:
        x, y, w, h = R['blocks'][stem]
        nets = set(hier_nets(stem))
        sides = R['pins'].get(stem, {})
        placed = set()
        e = ['sheet', ['at', x, y], ['size', w, h], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
             ['on_board', 'yes'], ['dnp', 'no'], ['fields_autoplaced', 'yes'],
             ['stroke', ['width', 0.1524], ['type', 'solid']], ['fill', ['color', 0, 0, 0, 0.0]],
             ['uuid', Q(sheet_uuids[stem])],
             ['property', Q('Sheetname'), Q(LAY.ROOT['names'][stem]), ['at', x, r2(y - 0.7), 0],
              ['effects', ['font', ['size', 1.524, 1.524]], ['justify', 'left', 'bottom']]],
             ['property', Q('Sheetfile'), Q(stem + '.kicad_sch'), ['at', x, r2(y + h + 0.6), 0],
              ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]]]
        for side, lst in sides.items():
            for net, py in lst:
                if net not in nets:
                    raise SystemExit('root: %s has no hierarchical net %s' % (stem, net))
                px = x if side == 'L' else x + w
                shape = LAY.HIER_SHAPE.get((stem, net), 'bidirectional')
                e.append(['pin', Q(net), shape, ['at', px, py, 180 if side == 'L' else 0],
                          ['uuid', uid('rootpin', stem, net)],
                          ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left' if side == 'L' else 'right']]])
                pin_at[(stem, net)] = (px, py)
                placed.add(net)
        if nets - placed:
            raise SystemExit('root: %s pins not placed: %s' % (stem, ', '.join(sorted(nets - placed))))
        e.append(['instances', ['project', Q(D.PROJECT), ['path', Q('/' + root_uuid), ['page', Q(str(page))]]]])
        items.append(e)
        items.append(['text', esc('%s  (page %d)' % (title, page)), ['exclude_from_sim', 'no'],
                      ['at', r2(x + 2.54), r2(y + 3.81), 0],
                      ['effects', ['font', ['size', 1.524, 1.524], 'bold'], ['justify', 'left', 'top']],
                      ['uuid', uid('roottitle', stem)]])
    for (a, b, net, via) in R['wires']:
        pts = [pin_at[(a, net)]] + [tuple(v) for v in via] + [pin_at[(b, net)]]
        for p, q in zip(pts, pts[1:]):
            items.append(['wire', ['pts', ['xy', p[0], p[1]], ['xy', q[0], q[1]]],
                          ['stroke', ['width', 0], ['type', 'default']], ['uuid', uid('rootw', net, p, q)]])
    for (x, y, s, size) in R['text']:
        items.append(['text', esc(s), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                      ['effects', ['font', ['size', size, size]], ['justify', 'left', 'top']],
                      ['uuid', uid('roottext', x, y)]])
    return ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
            ['generator_version', Q('9.0')], ['uuid', Q(root_uuid)], ['paper', Q('A3')],
            ['title_block', ['title', Q('FujiNet Astrocade Rev0')], ['date', Q(DATE)], ['rev', Q('0')],
             ['company', Q('FujiNet')],
             ['comment', 1, Q('Generated by tools/gen_sch.py from tools/design.py + tools/sch_layout.py')],
             ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-INTV-Rev0 / PiNTY CARD)')],
             ['comment', 3, Q('Rev0 audit 2026-10-02: kicad-happy + manufacturer datasheets; see docs/design-review-rev0.md')]],
            ['lib_symbols']] + items + [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]],
                                        ['embedded_fonts', 'no']]


def write_project(root_uuid, sheet_uuids):
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    pro['meta']['filename'] = D.PROJECT + '.kicad_pro'
    pro['sheets'] = [[root_uuid, 'Root']] + [[sheet_uuids[s[0]], s[0]] for s in D.SHEETS]
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')


def main():
    syms = load_symbols()
    verify_pin_tables(syms)
    root_uuid = str(uid('root'))
    sheet_uuids = {s[0]: str(uid('sheet', s[0])) for s in D.SHEETS}
    geo = {}
    for stem, title, page in D.SHEETS:
        sh = Sheet(stem, LAY.SHEETS[stem], syms, root_uuid, sheet_uuids[stem])
        sch = sh.build()
        open(os.path.join(PRJ, stem + '.kicad_sch'), 'w').write(dump(sch) + '\n')
        geo[stem] = {'boxes': sh.boxes, 'segs': sh.segs, 'tips': sh.tips, 'paper': LAY.SHEETS[stem].get('paper', 'A3')}
    open(os.path.join(PRJ, D.PROJECT + '.kicad_sch'), 'w').write(dump(build_root(root_uuid, sheet_uuids)) + '\n')
    write_project(root_uuid, sheet_uuids)
    json.dump(geo, open(os.path.join(HERE, '.sch_geometry.json'), 'w'))
    print('schematic written')


if __name__ == '__main__':
    main()
