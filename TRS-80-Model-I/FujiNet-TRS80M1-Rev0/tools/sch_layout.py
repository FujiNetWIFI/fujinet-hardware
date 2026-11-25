"""How each sheet is drawn: placement and wiring, one function per sheet, and the root.

design.py owns the circuit; these functions only say where each part sits and how its pins are
joined (sch_draw.Sheet).  Parts are addressed by their design.py key (U_RP, C_IOV76, ...), never
by reference.  A sheet without a drawing function is drawn as a draft (sch_draft.py: every pin
labelled) -- electrically identical.  sch_draw.Sheet.check(), gen_sch.check_hierarchy() and
gen_sch.netlist_parity() prove the drawing is exactly design.py's netlist, so a wiring slip here
fails the build.

The sheets follow the signal: the cartridge edge on the left, the RP2354B on the right, every bus
line one straight wire between them through its resistor.  The rp-core, fujinet, usb and power
sheets are FujiNet-StudioII / Arcadia Rev0's drawings (the same parts and nets).
"""
import os
import design as D
import sch_draft
from sch_draw import Sheet, Pt, snap

DRAW = {}
PAPER = {'m1-bus': 'A2', 'rp-core': 'A3', 'fujinet': 'A3', 'usb': 'A3', 'power': 'A3'}
G = 2.54

# ---- m1-bus rows (2.54 mm each), one block per buffer group, every line on an even row so its
# pull-down / probe / pull-up can sit in the row beside it.  The header's units and the RP's GPIO units
# are built on these rows (gen_sch.header_symbol / rp_split_symbol), so every line is one straight wire
# from its header pin through its buffer to its GPIO.
R_AH, R_AL, R_D, R_DRIVE, R_G, R_STB, R_STA, R_OD = 0, 26, 52, 72, 82, 92, 108, 124
GROUPS = [  # (header unit, RP unit, first row, lines (header-side nets), buffer key)
    (1, 1, R_AH, D.ADDR_HI, 'U_AH'), (2, 2, R_AL, D.ADDR_LO, 'U_AL'), (3, 3, R_D, D.DATA, 'U_DB'),
    (4, 4, R_STB, D.STROBE_B, 'U_STB'), (5, 4, R_STA, D.STROBE_A, 'U_STA'), (6, 4, R_OD, ['M1_INT_N', 'M1_WAIT_N'], 'U_OD')]


def _every_other(items, n=None):
    out = []
    for it in items:
        out += [it, None]
    return out[:-1]


HDR_RIGHT = {hu: _every_other([D.EDGE_PIN[n] for n in lines]) for hu, ru, r0, lines, key in GROUPS}
HDR_BOTTOM = [8, None, 29, None, 37, None, None, 1, None, 3, None, 16, None, 23, None, 39]
_gp = lambda n: D.GPIO_OF[D.rp_of(n)]
RP_LEFT = {1: _every_other([_gp(n) for n in D.ADDR_HI]), 2: _every_other([_gp(n) for n in D.ADDR_LO])}
RP_LEFT[3] = _every_other([_gp(n) for n in D.DATA]) + [None] * (R_DRIVE - R_D - 15) + [D.GPIO_OF['DRIVE']]
_u4 = [None] * (R_OD - R_STB + 3)
for r0, lines in ((R_STB, D.STROBE_B), (R_STA, D.STROBE_A), (R_OD, ['M1_INT_N', 'M1_WAIT_N'])):
    for i, n in enumerate(lines):
        _u4[r0 - R_STB + 2 * i] = _gp(n)
RP_LEFT[4] = _u4
RP_LEFT[5] = [33, None, 34, None, 35]
SPARE_GPIOS = [g for g in D.RP_UNIT_GPIOS[5] if D.RP_GPIO_NET[g] is None]
RP_RIGHT = {5: [44, None, None, 45, None, None, 47, None, None] + SPARE_GPIOS}


class KSheet(Sheet):
    """A Sheet whose parts are addressed by design.py key (references also work)."""
    def place(self, ref, *a, **k):
        return Sheet.place(self, D.KEY.get(ref, ref), *a, **k)

    def N(self, ref, net):
        return Sheet.N(self, D.KEY.get(ref, ref), net)

    def P(self, ref, num, unit=None):
        return Sheet.P(self, D.KEY.get(ref, ref), num, unit)


def sheet(stem):
    def deco(f):
        DRAW[stem] = f
        return f
    return deco


def draw(stem, syms, parts, cross):
    sh = KSheet(stem, syms, parts, PAPER[stem])
    if stem in DRAW and not os.environ.get('SCH_ALL_DRAFT'):
        DRAW[stem](sh)
    else:
        sch_draft.draft(sh, cross)
    return sh


def draw_root(syms, sheets):
    if os.environ.get('SCH_ALL_DRAFT') or 'root' not in DRAW:
        return sch_draft.draft_root(syms, sheets)
    return DRAW['root'](Sheet('root', syms, [], 'A3'), sheets)


# =========================================================================
# helpers
L_, R_, U_, D_ = (-1, 0), (1, 0), (0, -1), (0, 1)


def pin_place(sh, key, unit, pad, xy, **kw):
    """Place a unit so that pin `pad` lands on xy (both on the grid)."""
    d = sh.place(key, 0, 0, unit=unit, **kw)
    p = d['pins'][str(pad)]
    return sh.place(key, snap(xy[0] - p[0]), snap(xy[1] - p[1]), unit=unit, **kw)


def npin(sh, key, net, unit=None):
    """The pin end of `key`'s pin on `net` (in `unit` if given)."""
    ref = D.KEY[key]
    for (r, u), d in sh.placed.items():
        if r == ref and (unit is None or u == unit):
            for num, pt in d['pins'].items():
                if d['part'].pins.get(num) == net:
                    return pt
    raise KeyError('%s: %s has no placed pin on %s' % (sh.stem, key, net))


def fit(sh, key, pad, xy, want, unit=1, **kw):
    """Place a unit with pin `pad` on xy, turned (mirrored if need be) so that every pin in
    `want` ({pad: (dx, dy)}) points out that way."""
    for mirror in (None, 'x', 'y'):
        for rot in (0, 90, 180, 270):
            d = pin_place(sh, key, unit, pad, xy, rot=rot, mirror=mirror, **kw)
            if all((d['pins'][str(k)].dx, d['pins'][str(k)].dy) == v for k, v in want.items()):
                return d
    raise ValueError('%s: no orientation of %s fits %s' % (sh.stem, key, want))


def ncs(sh, key, unit=1):
    """No-connect flags on every unused pin of a placed unit."""
    ref = D.KEY[key]
    for num, pt in sh.placed[(ref, unit)]['pins'].items():
        if sh.parts[ref].pins[num] is None:
            sh.nc(pt)


def ground(sh, pin, n=2.54):
    """A pin to GND: a short stub, then the symbol hanging below (sideways pins turn down)."""
    if (pin.dx, pin.dy) == (0, 1):
        return sh.gnd(pin, n)
    e = sh.stub(pin, n)
    sh.rail(e, 'GND', 0)
    return e


def tee_cap(sh, key, pt, fields='right'):
    """A capacitor hanging from a point ON a horizontal line (the caller splits the line there),
    its ground under it."""
    fit(sh, key, 1, (pt[0], snap(pt[1] + 2.54)), {1: U_}, fields=fields)
    sh.wire(pt, sh.P(key, 1))
    sh.gnd(sh.P(key, 2))


def tee_tp(sh, key, pt, fields='right', up=True):
    """A bring-up pad standing on (up) or hanging from (not up) a point of a horizontal line."""
    if up:
        fit(sh, key, 1, (pt[0], snap(pt[1] - 2.54)), {1: D_}, fields=fields)
    else:
        fit(sh, key, 1, (pt[0], snap(pt[1] + 2.54)), {1: U_}, fields=fields)
    sh.wire(pt, sh.P(key, 1))


def rail_line(sh, a, xs):
    """A horizontal line from a, split at every x in xs (so tees land on wire ends)."""
    pts = [a] + [(x, a[1]) for x in xs]
    for p, q in zip(pts, pts[1:]):
        sh.wire(p, q)
    return pts[-1]


def supply_pin(sh, pin, net, cap=None, fields=None):
    """A supply pin wired straight out to its rail symbol, its decoupling capacitor on a tee
    beside it, hanging down from a short stub (to the right of a vertical pin, below a horizontal
    one) with its ground under it -- beside the pin it serves."""
    o = (pin.dx, pin.dy)
    out, t = {(0, -1): (22.86, 15.24), (0, 1): (22.86, 7.62), (1, 0): (22.86, 7.62), (-1, 0): (22.86, 7.62)}[o]
    end = (snap(pin[0] + o[0] * out), snap(pin[1] + o[1] * out))
    sh.wire(pin, end)
    if net == 'GND':
        sh.rail(end, 'GND', {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[o])
    else:
        sh.rail(end, net, {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[o])
    if not cap:
        return end
    tee = (snap(pin[0] + o[0] * t), snap(pin[1] + o[1] * t))
    st = (tee[0] + 5.08, tee[1]) if o[1] != 0 else (tee[0], tee[1] + 2.54)
    sh.wire(tee, st)
    pin_place(sh, cap, 1, 1, st, fields=fields or ('left' if o == (-1, 0) else 'right'))
    sh.gnd(sh.P(cap, 2))
    return end


def gate(sh, key, unit, out_xy, mirror=None, fields='above'):
    """Place one gate unit with its output pin end on out_xy; returns ({net: [input pins, top first]},
    output pin)."""
    d = pin_place(sh, key, unit, _out_pad(key, unit), out_xy, mirror=mirror, fields=fields)
    part = D.BY_KEY[key]
    ins = {}
    out = None
    for num, p in sorted(d['pins'].items(), key=lambda kv: kv[1][1]):
        if num == _out_pad(key, unit):
            out = p
        else:
            ins.setdefault(part.pins[num], []).append(p)
    return ins, out


def _out_pad(key, unit):
    v = D.BY_KEY[key].value
    return str(D.GATE_PINS[v][unit - 1][1])


def hres(sh, key, xy):
    """A horizontal resistor, pin 1 on xy facing left, its reference and value side by side above
    it (a ladder of these 2 x 2.54 apart keeps every name clear of the neighbouring lines)."""
    d = fit(sh, key, 1, xy, {1: L_})
    cx = (sh.P(key, 1)[0] + sh.P(key, 2)[0]) / 2
    y = snap(xy[1] - 2.54)
    d['fields'] = [(round(cx - 0.635, 3), y, 'right'), (round(cx + 0.635, 3), y, 'left')]
    return d


# =========================================================================
def hres_u(sh, key, unit, xy):
    """hres() for one resistor of a 4-resistor array (unit u = pins u and 9-u), pin u on xy facing left."""
    d = fit(sh, key, unit, xy, {unit: L_}, unit=unit)
    cx = (sh.P(key, unit, unit)[0] + sh.P(key, 9 - unit, unit)[0]) / 2
    y = snap(xy[1] - 2.54)
    d['fields'] = [(round(cx - 0.635, 3), y, 'right'), (round(cx + 0.635, 3), y, 'left')]
    return d


def side_res(sh, key, unit, pt, rail, up=False, show=False):
    """A resistor of an array hanging off a horizontal line at pt, drawn horizontally in the row beside
    it (below, or above with up): a 2.54 stub from the line, the resistor running right, its far end on a
    rail symbol pointing right.  Fields hidden unless show (then right of the rail symbol)."""
    y = snap(pt[1] + (-G if up else G))
    sh.wire(pt, (pt[0], y))
    d = fit(sh, key, unit, (pt[0], y), {unit: L_}, unit=unit)
    far = sh.P(key, 9 - unit, unit)
    sh.rail(far, rail, 90 if rail == 'GND' else 270)
    if show == 'left':                   # the array's name left of its first resistor, in its row
        near = sh.P(key, unit, unit)
        d['fields'] = [(snap(near[0] - 8.89), y, 'right'), (snap(near[0] - 1.27), y, 'right')]
    elif show:
        off = 8.89 if rail == 'GND' else 13.97
        d['fields'] = [(snap(far[0] + off), y, 'left'), (snap(far[0] + off + 7.62), y, 'left')]
    else:
        d['hide_fields'] = ('Reference', 'Value')
    return d


def side_r(sh, key, pt, rail, up=True):
    """side_res() for a single resistor (pin 2 on the line), its fields beyond the rail symbol."""
    y = snap(pt[1] + (-G if up else G))
    sh.wire(pt, (pt[0], y))
    d = fit(sh, key, 2, (pt[0], y), {2: L_})
    far = sh.P(key, 1)
    sh.rail(far, rail, 90 if rail == 'GND' else 270)
    d['fields'] = [(snap(far[0] + 13.97), y, 'left'), (snap(far[0] + 19.05), y, 'left')]
    return d


def side_probe(sh, unit, pt, show=False):
    """One unit of the logic-analyser header in the row under a line, tapped at pt; its ground right."""
    y = snap(pt[1] + G)
    sh.wire(pt, (pt[0], y))
    d = pin_place(sh, 'J_LA', unit, 2 * unit - 1, (pt[0], y), fields='above')
    sh.rail(sh.P('J_LA', 2 * unit, unit), 'GND', 90)
    if show:
        b = d['body']
        d['fields'] = [(snap(b[2] + 10.16), y, 'left'), (snap(b[2] + 15.24), y, 'left')]
    else:
        d['hide_fields'] = ('Reference', 'Value')
    return d


def foot_supply(sh, pin, cap, side=1):
    """A logic part's VCC pin (pointing down) to +3V3_RP: a stub down, the rail symbol beside it, its
    100 nF on a tee further along (side +1 = right)."""
    y = snap(pin[1] + 2 * G)
    xr, xc = snap(pin[0] + side * 2 * G), snap(pin[0] + side * 4 * G)
    sh.wire(pin, (pin[0], y), (xr, y), (xc, y))
    sh.wire((xr, y), (xr, snap(y - G)))
    sh.rail((xr, snap(y - G)), D.RP_RAIL, 0)
    fit(sh, cap, 1, (xc, snap(y + G)), {1: U_}, fields='right' if side > 0 else 'left')
    sh.wire((xc, y), sh.P(cap, 1))
    sh.gnd(sh.P(cap, 2))


PROBE_UNIT = {n: i + 1 for i, n in enumerate(D.LA)}


@sheet('m1-bus')
def m1_bus(sh):
    """The Model I's bus from the ribbon header to the RP2354B, left to right, one block per buffer group:
    each line one straight wire from its header pin (the header drawn in units by group) through its
    100k pull-down (the row under it) into its buffer, and from the buffer on to its GPIO (the RP's
    GPIO units built on the same rows).  A8-A15 and A0-A7: 74LVC245A, A -> B, always on.  D0-D7: 47R
    series, the 74LVC245A turned round (B, the bus, on the left), DIR = DRIVE and /OE from the
    74LVC1G11 under it (DRIVE . RD* . IN*).  RD* IN* INTAK* and SYSRES* OUT* WR*: two 74LVC3G17
    Schmitt receivers.  INT* WAIT*: the 74LVC2G07 turned round (the RP drives them), pulled up on the
    RP side.  The logic-analyser header taps the buffered strobes and controls, one unit per line.
    One crossing: IN* reaches the gate past RD* (both strobes feed it from below; DRIVE from above)."""
    sh.wired = True
    sh.crossing_budget = 1
    U, J = 'U_RP', 'J_M1'
    y0 = 30.48
    row = lambda r: snap(y0 + r * G)
    x_h = 50.8                                   # the header units' pin ends
    x_r = snap(x_h + 5 * G)                      # data series resistor, pin 1
    x_pd = snap(x_h + 12 * G)                    # pull-down tees
    x_bi = snap(x_h + 20 * G)                    # every buffer's bus-side pin ends
    x_rp = snap(x_bi + 50 * G)                   # the RP units' left pin ends
    hp = lambda n: sh.N(D.KEY[J], n)
    pd_unit = {}                                 # header-side (pulled) net -> (array key, unit)
    for key in ('RN_AH1', 'RN_AH2', 'RN_AL1', 'RN_AL2', 'RN_D1', 'RN_D2', 'RN_STA', 'RN_STB'):
        for u in range(1, 5):
            n = D.BY_KEY[key].pins[str(u)]
            if n:
                pd_unit[n] = (key, u)
    shown = set()
    for hu, ru, r0, lines, key in GROUPS:
        y1 = row(r0)
        first = D.EDGE_PIN[lines[0]]
        dj = pin_place(sh, J, hu, first, (x_h, y1), fields='abovebelow')
        jb = dj['body']
        dj['fields'] = [(jb[0], snap(jb[1] - 1.27), 'left'), (jb[0], snap(jb[3] + 2.54), 'left')]
        if hu > 1:
            dj['hide_fields'] = ('Value',)
        du = pin_place(sh, U, ru, D.RP_GPIO_PIN[_gp(lines[0])], (x_rp, y1), fields='abovebelow') \
            if (ru, r0) != (4, R_STA) and (ru, r0) != (4, R_OD) else None
        if du:
            ub = du['body']
            du['fields'] = [(ub[0], snap(ub[1] - 1.27), 'left'), (ub[0], snap(ub[3] + 2.54), 'left')]
            if ru > 1:
                du['hide_fields'] = ('Value',)
        # the buffer, its bus-side pins at x_bi (turned round for the data and the INT / WAIT drivers)
        part = D.BY_KEY[key]
        bus_pin = next(num for num, n in part.pins.items() if n in (lines[0], D.ds_of(lines[0])))
        db = pin_place(sh, key, 1, bus_pin, (x_bi, y1), fields='abovebelow')
        bb = db['body']
        if key.startswith('U_A') or key == 'U_DB':
            db['fields'] = [(bb[0], snap(bb[1] - 1.27), 'left'), (bb[2], snap(bb[1] - 1.27), 'right')]
        else:                                     # the narrow boxes: reference above, value right of the foot
            db['fields'] = [(bb[0], snap(bb[1] - 1.27), 'left'), (snap(bb[2] + 1.27), snap(bb[3] + 1.27), 'left')]
        for i, n in enumerate(lines):
            y = row(r0 + 2 * i)
            h = hp(n)
            assert h[1] == y, (n, h, y)
            rpn = D.rp_of(n)
            g = sh.N(D.KEY[U], rpn)
            assert g[1] == y, (rpn, g, y)
            if key == 'U_DB':                     # header -> 47R -> pull-down tee -> '245 B
                ds = D.ds_of(n)
                rk, ru_ = next((k, u) for k in ('RS_D1', 'RS_D2') for u in range(1, 5)
                               if D.BY_KEY[k].pins[str(u)] == n)
                hres_u(sh, rk, ru_, (x_r, y))
                if ru_ != 1:
                    sh.placed[(D.KEY[rk], ru_)]['hide_fields'] = ('Reference', 'Value')
                sh.wire(h, sh.P(rk, ru_, ru_))
                sh.label((snap(h[0] + 1.27), y), n, 'R')
                a = sh.P(rk, 9 - ru_, ru_)
                bpin = sh.N(D.KEY[key], ds)
                sh.wire(a, (x_pd, y), bpin)
                sh.label((snap(a[0] + 1.27), y), ds, 'R')
                pk, pu = pd_unit[ds]
            else:
                bpin = sh.N(D.KEY[key], n)
                sh.wire(h, (x_pd, y), bpin)
                sh.label((snap(h[0] + 1.27), y), n, 'R')
                pk, pu = pd_unit.get(n, (None, None))
            assert bpin[1] == y, (n, bpin, y)
            if pk:
                side_res(sh, pk, pu, (x_pd, y), 'GND', show='left' if pk not in shown else False)
                shown.add(pk)
            # the RP side: buffer -> GPIO
            o = sh.N(D.KEY[key], rpn)
            assert o[1] == y, (rpn, o, y)
            sh.wire(o, g)
            sh.label((snap(o[0] + 1.27), y), rpn, 'R')
        # the buffer's foot
        foot(sh, key)
    # ---- the data buffer's DIR and /OE, the gate -----------------------------------------------------
    dir_ = sh.P('U_DB', 1)
    oe = sh.P('U_DB', 19)
    yd, yg = row(R_DRIVE), row(R_G)
    gd = sh.N(D.KEY[U], 'DRIVE')
    assert gd[1] == yd, (gd, yd)
    x_gout = snap(oe[0] + 10 * G)
    ins, out = gate(sh, 'U_OE', 1, (x_gout, yg), mirror='y', fields='above')
    gd_ = sh.placed[(D.KEY['U_OE'], 1)]
    gb = gd_['body']
    gd_['fields'] = [(snap(gb[2] + 1.27), snap(gb[1] + 1.27), 'left'), (snap(gb[2] + 1.27), snap(gb[1] + 3.81), 'left')]
    x_in = sh.N(D.KEY['U_OE'], 'DRIVE')[0]
    x_t2, x_t1 = snap(x_in + 2 * G), snap(x_in + 4 * G)
    x_p, x_pp = snap(x_in + 8 * G), snap(x_in + 11 * G)
    sh.wire(dir_, (dir_[0], yd), (x_in, yd), (x_p, yd), (x_pp, yd), gd)
    sh.label((snap(x_pp + 2.54), yd), 'DRIVE', 'R')
    sh.wire((x_in, yd), sh.N(D.KEY['U_OE'], 'DRIVE'))
    fit(sh, 'R_DRIVE', 1, (x_p, snap(yd + 2 * G)), {1: U_}, fields='right')
    sh.wire((x_p, yd), sh.P('R_DRIVE', 1))
    sh.gnd(sh.P('R_DRIVE', 2))
    side_probe(sh, PROBE_UNIT['DRIVE'], (x_pp, yd), show=True)
    x_po = snap(oe[0] + 3 * G)
    sh.wire(oe, (oe[0], yg), (x_po, yg), out)
    sh.label((snap(oe[0] + 1.27), yg), 'BUF_OE_N', 'R')
    side_probe(sh, PROBE_UNIT['BUF_OE_N'], (x_po, yg))
    rd_in, in_in = sh.N(D.KEY['U_OE'], 'RP_RD_N'), sh.N(D.KEY['U_OE'], 'RP_IN_N')
    y_rd, y_in = sh.N(D.KEY[U], 'RP_RD_N')[1], sh.N(D.KEY[U], 'RP_IN_N')[1]
    sh.wire(rd_in, (x_t1, rd_in[1]), (x_t1, y_rd))
    sh.wire(in_in, (x_t2, in_in[1]), (x_t2, y_in))
    vg = npin(sh, 'U_OE', D.RP_RAIL)
    sh.wire(vg, (vg[0], snap(vg[1] - G)))
    sh.rail((vg[0], snap(vg[1] - G)), D.RP_RAIL, 0)
    tc = (snap(vg[0] - 2 * G), snap(vg[1] - G))
    sh.wire((vg[0], tc[1]), tc)
    fit(sh, 'C_OE', 1, tc, {1: R_}, fields='above')
    sh.gnd(sh.P('C_OE', 2), 0, rot=270)
    sh.gnd(npin(sh, 'U_OE', 'GND'))
    # ---- the RP side's taps: the probes on the strobes and INT / WAIT, the drivers' pull-ups --------------
    x_pr = snap(x_rp - 12 * G)
    for n in ('RP_RD_N', 'RP_IN_N', 'RP_INTAK_N', 'RP_SYSRES_N', 'RP_OUT_N', 'RP_WR_N', 'RP_INT_N', 'RP_WAIT_N'):
        p = sh.N(D.KEY[U], n)
        side_probe(sh, PROBE_UNIT[n], (x_pr, p[1]))
    x_pu = snap(x_bi + 9 * G)
    for n, k in (('RP_INT_N', 'R_INTPU'), ('RP_WAIT_N', 'R_WAITPU')):
        side_r(sh, k, (x_pu, sh.N(D.KEY[U], n)[1]), D.RP_RAIL)
    # the spare resistors of the two strobe arrays: open on the line side, under their group
    for key, r0 in (('RN_STB', R_STB + 6), ('RN_STA', R_STA + 6)):
        y = row(r0)
        d = fit(sh, key, 4, (x_pd, y), {4: L_}, unit=4)
        d['hide_fields'] = ('Reference', 'Value')
        sh.nc(sh.P(key, 4, 4))
        sh.rail(sh.P(key, 5, 4), 'GND', 90)
    # the header's grounds and open pins (unit 7), the RP's unit 5: DIP switches, LED, debug UART, spares
    x5 = snap(x_rp + 62 * G)
    dj = pin_place(sh, J, 7, 8, (snap(x5 - 30 * G), row(R_AH + 6)), fields='abovebelow')
    for p in (8, 29, 37):
        sh.gnd(sh.P(J, p, 7))
    for p in (1, 3, 16, 23, 39):
        sh.nc(sh.P(J, p, 7))
    dip_rp(sh, x5, row(R_AL))
    bus_buffer_bulk(sh, x_h, row(R_OD + 10))
    sh.text((snap(x5 - 34 * G), row(R_D)),
            'The TRS-80 Model I expansion edge (Level II; Tech Ref 26-2103 p.91) on a 40-wire IDC ribbon, header pin n = edge pin n.\n'
            'Grounds 8, 29, 37.  Pin 39 is +5V on keyboard boards A-E and GND on G: open.  RAS* CAS* MUX (the EI\'s DRAM timing) and\n'
            'TEST* (it floats the keyboard unit\'s buses) are open.  Every line meets one LVC buffer at the header (3.3 V, 5 V-tolerant\n'
            'inputs, Ioff) and a 100k pull-down (defined with the ribbon unplugged; to GND, so neither side back-feeds the other).\n'
            'The strobes, SYSRES* and INTAK* through 74LVC3G17 Schmitt triggers.  D0-D7 IS the keyboard unit\'s data bus: the card\n'
            'drives it only while RD* or IN* is low (OE* = DRIVE . RD* . IN*), through 47R.  GPIO map: m1_card.h (pico/trs80m1).', 1.27)
    ncs(sh, U, 5)
    return sh


def foot(sh, key):
    """VCC / GND / DIR / OE of a placed buffer (every foot has VCC leftmost: its 100 nF goes left)."""
    if key in ('U_AH', 'U_AL'):
        sh.sup(sh.P(key, 1), D.RP_RAIL, G, rot=180)       # DIR high: A -> B
        sh.gnd(sh.P(key, 19))                              # /OE low: always on
        sh.gnd(sh.P(key, 10))
        foot_supply(sh, sh.P(key, 20), 'C_' + key[2:], side=-1)
    elif key == 'U_DB':
        sh.gnd(sh.P(key, 10))
        foot_supply(sh, sh.P(key, 20), 'C_DB', side=-1)
    else:
        part = D.BY_KEY[key]
        vcc = next(num for num, n in part.pins.items() if n == D.RP_RAIL)
        gnd = next(num for num, n in part.pins.items() if n == 'GND')
        sh.gnd(sh.P(key, gnd))
        foot_supply(sh, sh.P(key, vcc), 'C_' + key[2:], side=-1)


def dip_rp(sh, x5, y5):
    """RP unit 5: the DIP switches into GP33-35 (pulled up), the LED, the debug-UART pads, the spares."""
    U = 'U_RP'
    pin_place(sh, U, 5, D.RP_GPIO_PIN[33], (x5, y5), fields='abovebelow')
    d = sh.placed[(D.KEY[U], 5)]
    ub = d['body']
    d['fields'] = [(ub[0], snap(ub[1] - 1.27), 'left'), (ub[0], snap(ub[3] + 2.54), 'left')]
    d['hide_fields'] = ('Value',)
    nets = ['DIP_RAM', 'DIP_EI', 'DIP_RS232']
    gps = [sh.N(D.KEY[U], n) for n in nets]
    # the switch (pins 1-3 toward the RP, 2.54 apart); each line jogs onto its GPIO row (5.08 apart), the
    # lower ones first, then takes its pull-up in the row above it
    x_sw = snap(x5 - 34 * G)
    sw = pin_place(sh, 'SW_DIP', 1, 1, (x_sw, y5), mirror='y', fields='abovebelow')
    sb = sw['body']
    sw['fields'] = [(sb[0], snap(sb[1] - 1.27), 'left'), (sb[0], snap(sb[3] + 2.54), 'left')]
    assert sh.P('SW_DIP', 1)[1] < sh.P('SW_DIP', 3)[1]
    for i, n in enumerate(nets):
        a = sh.P('SW_DIP', i + 1)
        if i:
            xj = snap(x_sw + (8 - 2 * i) * G)
            sh.wire(a, (xj, a[1]), (xj, gps[i][1]), gps[i])
        else:
            sh.wire(a, gps[i])
        sh.label((snap(a[0] + 1.27), a[1]), n, 'R')
        side_res(sh, 'RN_DIP', i + 1, (snap(x5 - 22 * G), gps[i][1]), D.RP_RAIL, up=True, show=i == 0)
    for p in (4, 5, 6):
        sh.gnd(sh.P('SW_DIP', p), G, rot=270)
    d = fit(sh, 'RN_DIP', 4, (snap(x5 - 22 * G), snap(gps[2][1] + 3 * G)), {4: L_}, unit=4)
    d['hide_fields'] = ('Reference', 'Value')
    sh.nc(sh.P('RN_DIP', 4, 4))
    sh.rail(sh.P('RN_DIP', 5, 4), D.RP_RAIL, 270)
    gp = lambda g: sh.P(U, D.RP_GPIO_PIN[g], 5)
    for g, tp, net in ((44, 'TP_DBGTX', 'DBG_TX'), (45, 'TP_DBGRX', 'DBG_RX')):
        p = gp(g)
        fit(sh, tp, 1, (snap(p[0] + 15.24), p[1]), {1: L_}, fields='right')
        sh.wire(p, sh.P(tp, 1))
        sh.label((snap(p[0] + 1.27), p[1]), net, 'R')
    p = gp(47)                                     # GP47 -> 680R -> red LED -> GND
    hres(sh, 'R_LED', (snap(p[0] + 12.7), p[1]))
    sh.wire(p, sh.P('R_LED', 1))
    sh.label((snap(p[0] + 1.27), p[1]), 'RP_LED', 'R')
    fit(sh, 'D_LED', 2, (snap(sh.P('R_LED', 2)[0] + 10.16), p[1]), {2: L_}, fields='above')
    sh.wire(sh.P('R_LED', 2), sh.P('D_LED', 2))
    sh.label((snap(sh.P('R_LED', 2)[0] + 1.27), p[1]), 'RP_LED_A', 'R')
    ground(sh, sh.P('D_LED', 1))


def bus_buffer_bulk(sh, x, y):
    """The bus buffers' 10 uF on +3V3_RP, under the drawing."""
    sh.rail((x, y), D.RP_RAIL, 0)
    sh.wire((x, y), (snap(x + 3 * G), y))
    fit(sh, 'C_BUFBULK', 1, (snap(x + 3 * G), snap(y + G)), {1: U_}, fields='right')
    sh.wire((snap(x + 3 * G), y), sh.P('C_BUFBULK', 1))
    sh.gnd(sh.P('C_BUFBULK', 2))


# =========================================================================
@sheet('rp-core')
def rp_core(sh):
    """The RP2354B's own circuit around its core unit (FujiNet-StudioII Rev0's drawing): every supply pin
    with its 100 nF beside it; along the top the QSPI_SS strap and BOOTSEL, the USB pair and the
    core-regulator corner (VREG_LX -> 3.3 uH -> DVDD, VREG_AVDD through 33R); along the bottom the
    crystal, SWD and RUN with its pull-up, the S3's RUN control and the RESET steering pair.  The USB
    pair, the S3's BOOTSEL / RUN controls and S3_EN leave on the right, to the fujinet sheet."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    U = 'U_RP'
    sh.place(U, 210.82, 160.02, unit=D.RP_CORE_UNIT, fields='abovebelow')
    P = lambda n: sh.P(U, n, D.RP_CORE_UNIT)
    R3, DV = D.RP_IO_RAIL, 'DVDD'
    ncs(sh, U, D.RP_CORE_UNIT)                         # the QSPI flash pins: no flash fitted
    # ---- the decoupling ring: every supply pin to its rail, its cap beside it ------------------
    for n, cap in ((76, 'C_IOV76'), (69, 'C_QSPI'), (68, 'C_OTP'), (64, 'C_VREGIN')):
        supply_pin(sh, P(n), R3, cap)
    for n, cap in ((41, 'C_IOV41'), (50, 'C_IOV50'), (59, 'C_ADC'), (60, 'C_IOV60'), (24, 'C_IOV24'),
                   (29, 'C_IOV29'), (5, 'C_IOV5'), (15, 'C_IOV15')):
        supply_pin(sh, P(n), R3, cap)
    for n, cap in ((51, 'C_DV51'), (32, 'C_DV32'), (10, 'C_DV10')):
        supply_pin(sh, P(n), DV, cap)
    supply_pin(sh, P(65), DV)                          # VREG_FB senses DVDD
    for n in (62, 81):
        supply_pin(sh, P(n), 'GND')
    i76 = P(76)                                        # the IO rail's bulk, on IOVDD 76's run
    t = (i76[0], snap(i76[1] - 20.32))
    fit(sh, 'C_IOBULK', 1, (snap(t[0] - 5.08), t[1]), {1: U_}, fields='left')
    sh.wire(t, sh.P('C_IOBULK', 1))
    sh.gnd(sh.P('C_IOBULK', 2))
    # ---- the core regulator: VREG_LX -> 3.3 uH -> DVDD; VREG_AVDD through 33R from the IO rail ---
    lx = P(63)
    fit(sh, 'L_RP', 2, (lx[0], snap(lx[1] - 10.16)), {2: D_}, fields='right')
    sh.wire(lx, sh.P('L_RP', 2))
    sh.label((lx[0], snap(lx[1] - 1.27)), 'RP_LX', 'U')
    sh.sup(sh.P('L_RP', 1), DV)
    av = P(61)
    tee = (av[0], snap(av[1] - 12.7))
    fit(sh, 'R_AVDD', 2, tee, {2: D_}, fields='right')
    sh.wire(av, tee)
    sh.label((av[0], snap(av[1] - 1.27)), 'VREG_AVDD', 'U')
    sh.sup(sh.P('R_AVDD', 1), R3)
    st = (snap(tee[0] + 12.7), tee[1])
    sh.wire(tee, st)
    fit(sh, 'C_AVDD', 1, st, {1: U_}, fields='right')
    sh.gnd(sh.P('C_AVDD', 2))
    sh.flag(st, 'VREG_AVDD')
    # DVDD's bulk, its bring-up pad and its PWR_FLAG (the regulator drives it through the inductor)
    xd, yd = snap(st[0] + 15.24), snap(tee[1] - 5.08)
    sh.rail((xd, yd), DV, 0)
    e = sh.wire((xd, yd), (snap(xd + 12.7), yd))
    fit(sh, 'C_DVBULK', 1, (xd, yd), {1: U_}, fields='right')
    sh.gnd(sh.P('C_DVBULK', 2))
    fit(sh, 'TP_DVDD', 1, e, {1: U_}, fields='right')
    sh.flag(e, DV)
    # ---- above the RP: BOOTSEL on QSPI_SS, then the USB pair out to the power sheet ---------------
    xr = snap(P(60)[0] + 63.5)                         # the page's right-hand port column
    y_bs, y_ss, y_usb = 68.58, 73.66, 83.82
    for n, rkey, net, inner, y in ((67, 'R_USBP', 'USB_DP', 'RP_USB_DP', y_usb),
                                   (66, 'R_USBM', 'USB_DM', 'RP_USB_DM', snap(y_usb + 2.54))):
        p = P(n)
        fit(sh, rkey, 2, (p[0], snap(p[1] - 15.24)), {2: D_}, fields='left' if n == 67 else 'right')
        sh.wire(p, sh.P(rkey, 2))
        sh.label((p[0], snap(p[1] - 1.27)), inner, 'U')
        b = sh.P(rkey, 1)
        sh.wire(b, (b[0], y), (xr, y))
        sh.hlabel(Pt(xr, y, 1, 0), net, 'R', 'bidirectional')
    # QSPI_SS: up to the BOOTSEL row, the pull-up on a tee to the left
    ss = P(75)
    sh.label((ss[0], snap(ss[1] - 1.27)), 'QSPI_SS', 'U')
    sh.wire(ss, (ss[0], snap(y_ss + 5.08)), (ss[0], y_ss), (ss[0], y_bs))
    xs = snap(ss[0] - 5.08)
    sh.wire((ss[0], y_ss), (xs, y_ss))
    fit(sh, 'R_SS', 2, (xs, snap(y_ss - 2.54)), {2: D_}, fields='left')
    sh.wire((xs, y_ss), sh.P('R_SS', 2))
    sh.sup(sh.P('R_SS', 1), R3)
    y_ct = snap(y_ss + 5.08)                           # the S3's BOOTSEL control: a tee, out right
    xc = snap(ss[0] + 7.62)
    sh.wire((ss[0], y_ct), (xc, y_ct))
    fit(sh, 'R_BSELCTL', 2, (snap(xc + 2.54), y_ct), {2: L_}, fields='below')
    sh.wire((xc, y_ct), sh.P('R_BSELCTL', 2))
    sh.wire(sh.P('R_BSELCTL', 1), (xr, y_ct))
    sh.hlabel(Pt(xr, y_ct, 1, 0), 'BOOTSEL_CTL', 'R', 'input')
    fit(sh, 'R_BSEL', 1, (snap(ss[0] + 7.62), y_bs), {1: L_}, fields='above')
    sh.wire((ss[0], y_bs), sh.P('R_BSEL', 1))
    fit(sh, 'SW_BOOTSEL', 1, (snap(sh.P('R_BSEL', 2)[0] + 22.86), y_bs), {1: L_}, fields='above')
    ground(sh, sh.P('SW_BOOTSEL', 2))
    sh.wire(sh.P('R_BSEL', 2), sh.P('SW_BOOTSEL', 1))
    sh.label((snap(sh.P('R_BSEL', 2)[0] + 2.54), y_bs), 'BOOTSEL_BTN', 'R')
    # ---- the crystal: XIN straight into it, XOUT through 1k, both 15 pF to GND -------------------
    xi, xo = P(30), P(31)
    fit(sh, 'R_XOUT', 1, (xo[0], snap(xo[1] + 7.62)), {1: U_}, fields='right')
    sh.wire(xo, sh.P('R_XOUT', 1))
    sh.label((xo[0], snap(xo[1] + 6.35)), 'XOUT', 'U')
    y_c = snap(sh.P('R_XOUT', 2)[1] + 10.16)
    fit(sh, 'Y_RP', 1, (snap(xi[0] + 2.54), y_c), {1: L_, 3: R_}, fields='above')
    sh.gnd(sh.P('Y_RP', 2))
    for col, ykey, cap in ((xi, 1, 'C_XIN'), (sh.P('R_XOUT', 2), 3, 'C_XOUT')):
        fit(sh, cap, 1, (col[0], snap(y_c + 5.08)), {1: U_}, fields='left' if cap == 'C_XIN' else 'right')
        sh.wire(col, sh.P(cap, 1))
        sh.wire((col[0], y_c), sh.P('Y_RP', ykey))
        sh.gnd(sh.P(cap, 2))
    sh.label((xi[0], snap(xi[1] + 6.35)), 'XIN', 'U')
    sh.label((xo[0], snap(y_c - 1.27)), 'XOUT_Y', 'U')
    # ---- SWD: down and left under the crystal to the bring-up pads -------------------------------
    y1 = snap(y_c + 22.86)
    rows = {'SWCLK': y1, 'SWDIO': snap(y1 + 5.08)}
    x_tp = snap(P(24)[0] - 5.08)
    for n, tp in (('SWCLK', 'TP_SWCLK'), ('SWDIO', 'TP_SWDIO')):
        p = sh.N(D.KEY[U], n)
        fit(sh, tp, 1, (x_tp, rows[n]), {1: R_}, fields='left')
        sh.wire(p, (p[0], rows[n]), sh.P(tp, 1))
        sh.label((p[0], snap(p[1] + 6.35)), n, 'U')
    yg = snap(rows['SWDIO'] + 5.08)
    fit(sh, 'TP_GND', 1, (x_tp, yg), {1: R_}, fields='left')
    ground(sh, sh.P('TP_GND', 1))
    # ---- RUN: down to its pad; the pull-up, the S3's RUN control and the RESET steering pair -------
    run = P(35)
    sh.label((run[0], snap(run[1] + 6.35)), 'RUN', 'U')
    y_r = snap(P(62)[1] + 33.02)
    y_end = snap(y1 + 17.78)
    sh.wire(run, (run[0], y_r), (run[0], y_end))
    fit(sh, 'TP_RUN', 1, (run[0], y_end), {1: U_}, fields='right')
    x_pu = snap(P(81)[0] + 10.16)
    x_rc, x_d = snap(x_pu + 10.16), snap(x_pu + 25.4)
    fit(sh, 'D_RST', 1, (x_d, y_r), {1: L_, 2: R_, 3: D_}, fields='above')
    rail_line(sh, (run[0], y_r), [x_pu, x_rc, x_d])
    fit(sh, 'R_RUN', 2, (x_pu, snap(y_r - 2.54)), {2: D_}, fields='left')
    sh.wire((x_pu, y_r), sh.P('R_RUN', 2))
    sh.sup(sh.P('R_RUN', 1), R3)
    fit(sh, 'R_RUNCTL', 2, (x_rc, snap(y_r - 2.54)), {2: D_}, fields='right')
    sh.wire((x_rc, y_r), sh.P('R_RUNCTL', 2))
    rc = sh.P('R_RUNCTL', 1)
    y_rc = snap(rc[1] - 5.08)
    sh.wire(rc, (rc[0], y_rc), (xr, y_rc))
    sh.hlabel(Pt(xr, y_rc, 1, 0), 'RUN_CTL', 'R', 'input')
    en = sh.P('D_RST', 2)
    sh.wire(en, (xr, en[1]))
    sh.hlabel(Pt(xr, en[1], 1, 0), 'S3_EN', 'R', 'bidirectional')
    k = sh.P('D_RST', 3)
    fit(sh, 'SW_RESET', 1, (k[0], snap(k[1] + 7.62)), {1: U_}, fields='right')
    sh.wire(k, sh.P('SW_RESET', 1))
    sh.label((k[0], snap(k[1] + 1.27)), 'RST_BTN', 'D')
    sh.gnd(sh.P('SW_RESET', 2))
    sh.text((snap(P(5)[0] - 40.64), 25.4),
            'Supplies (RP2350 datasheet 6.3.7): IOVDD, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and VREG_VIN on +3V3_RP, the\n'
            'AP2112K LDO that rises with +5V; the core regulator switches VREG_LX through 3.3 uH onto DVDD (VREG_FB senses\n'
            'it), its analog supply VREG_AVDD through 33R / 4.7 uF.  One 100 nF at every supply pin, drawn at the pin it serves.\n'
            "RESET resets the RP2354B and the ESP32-S3 together (%s steers RST_BTN onto RUN and S3_EN): the way back to\n"
            "the FujiNet's CONFIG.  Hold BOOTSEL while pressing RESET for the RP's USB boot ROM; the S3 does both itself: IO4\n"
            '(RUN_CTL) low resets the RP, IO5 (BOOTSEL_CTL) low through that reset selects BOOTSEL.  USB: 27R at the RP, the S3\n'
            'is the host.  SWD and RUN on bring-up pads.  QSPI_SD0-3 / SCLK unused: the 2 MB flash is in the package.'
            % D.KEY['D_RST'])
    return sh


# =========================================================================
@sheet('fujinet')
def fujinet(sh):
    """The ESP32-S3 and what hangs off it: the module's 3V3 decoupling above it; EN's power-on RC and
    the S3_RST button on the EN line above its left end, BOOT on IO0 left of it; the RP2354B's RUN /
    BOOTSEL controls and USB pair in from the left (the rp-core sheet); the UART out to the USB
    bridge on the right; the microSD below it, its SPI lines stepping down into the socket with the
    pull-ups between them; the WS2812 at the page's foot."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    U = 'U_S3'
    d = sh.place(U, 190.5, 116.84, fields='abovebelow')
    b = d['body']                                      # the value under the body, clear of its pins
    d['fields'][1] = (b[0] - 1.27, b[3] + 1.778, 'right')
    P = lambda n: sh.P(U, n)
    ncs(sh, U)
    x = 190.5
    y_t = b[1]                                         # the body's top edge
    # ---- 3V3 and its decoupling, bulk to the right -----------------------------------------------
    v = P(2)
    yt = snap(v[1] - 15.24)
    sh.wire(v, (v[0], snap(v[1] - 22.86)))
    sh.sup((v[0], snap(v[1] - 22.86)), D.S3_RAIL)
    c1 = fit(sh, 'C_S3', 1, (snap(v[0] + 7.62), yt), {1: U_}, fields='right')['pins']['1']
    c2 = fit(sh, 'C_S3BULK', 1, (snap(v[0] + 20.32), yt), {1: U_}, fields='right')['pins']['1']
    sh.wire((v[0], yt), c1)
    sh.wire(c1, c2)
    for c in ('C_S3', 'C_S3BULK'):
        sh.gnd(sh.P(c, 2))
    # ---- EN: up to its line; the 10k pull-up, the 1 uF delay, S3_RST, then out left -------------
    en = P(3)
    y_en = snap(y_t - 20.32)
    x_l = snap(x - 121.92)                             # the page's left-hand port column
    sh.wire(en, (en[0], y_en), (x_l, y_en))
    sh.hlabel(Pt(x_l, y_en, -1, 0), 'S3_EN', 'L', 'bidirectional')
    fit(sh, 'R_EN', 2, (snap(en[0] - 7.62), snap(y_en - 2.54)), {2: D_}, fields='right')
    sh.wire((snap(en[0] - 7.62), y_en), sh.P('R_EN', 2))
    sh.sup(sh.P('R_EN', 1), D.S3_RAIL)
    fit(sh, 'C_EN', 1, (snap(en[0] - 15.24), snap(y_en + 2.54)), {1: U_}, fields='right')
    sh.wire((snap(en[0] - 15.24), y_en), sh.P('C_EN', 1))
    sh.gnd(sh.P('C_EN', 2))
    xs = snap(x - 76.2)
    fit(sh, 'SW_S3EN', 1, (xs, snap(y_en + 2.54)), {1: U_}, fields='right')
    sh.wire((xs, y_en), sh.P('SW_S3EN', 1))
    sh.gnd(sh.P('SW_S3EN', 2))
    # ---- IO0: S3_BOOT on a tee, then out left (esptool's auto-program pair drives it too) --------
    io0 = P(27)
    sh.wire(io0, (x_l, io0[1]))
    sh.hlabel(Pt(x_l, io0[1], -1, 0), 'S3_IO0', 'L', 'bidirectional')
    xb = snap(x - 88.9)
    fit(sh, 'SW_S3BOOT', 1, (xb, snap(io0[1] + 2.54)), {1: U_}, fields='right')
    sh.wire((xb, io0[1]), sh.P('SW_S3BOOT', 1))
    sh.gnd(sh.P('SW_S3BOOT', 2))
    # ---- the RP2354B's controls and USB, straight in from the left -----------------------------
    for n, net, shape in ((4, 'RUN_CTL', 'output'), (5, 'BOOTSEL_CTL', 'output'),
                          (14, 'USB_DP', 'bidirectional'), (13, 'USB_DM', 'bidirectional')):
        p = P(n)
        sh.wire(p, (x_l, p[1]))
        sh.hlabel(Pt(x_l, p[1], -1, 0), net, 'L', shape)
    # ---- the UART to the CP2102N, out right ----------------------------------------------------
    x_r = snap(x + 88.9)
    for n, net, shape in ((37, 'S3_TXD', 'output'), (36, 'S3_RXD', 'input')):
        p = P(n)
        sh.wire(p, (x_r, p[1]))
        sh.hlabel(Pt(x_r, p[1], 1, 0), net, 'R', shape)
    sh.gnd(P(1))
    # ---- the microSD: the SPI lines step down and right into the socket --------------------------
    y_b = P(31)[1]
    x_j = snap(x + 53.34)
    J = 'J_SD'
    d = sh.place(J, 0, 0, fields='abovebelow')
    dy = snap(y_b + 10.16 - d['pins']['8'][1])
    dx = snap(x_j - d['pins']['8'][0])
    d = sh.place(J, dx, dy, fields='abovebelow')
    jb = d['body']
    d['fields'][1] = (jb[2] + 1.27, jb[3] - 1.27, 'left')
    for net in ('SD_MOSI', 'SD_SCK', 'SD_MISO', 'SD_CS', 'SD_CD'):
        a, b = sh.N(D.KEY[U], net), sh.N(D.KEY[J], net)
        sh.wire(a, (a[0], b[1]), b)
        sh.label((snap(x_j - 12.7), b[1]), net, 'R')
    # pull-ups: CD, CS and MISO each in the gap right of its line, DAT1 / DAT2 off the socket's pins
    for net, key, unit in (('SD_CD', 'R_SDCD', 1), ('SD_CS', 'RN_SD', 1), ('SD_MISO', 'RN_SD', 2)):
        a, b = sh.N(D.KEY[U], net), sh.N(D.KEY[J], net)
        xp = snap(a[0] + 5.08)                        # room for the +3V3 text clear of the line
        pn = 2 if key == 'R_SDCD' else unit           # the pin on the line (RN unit k: pins k, 9 - k)
        fit(sh, key, pn, (xp, snap(b[1] - 2.54)), {pn: D_}, unit=unit, fields='right')
        sh.wire((xp, b[1]), sh.P(key, pn, unit))
        sh.sup(sh.P(key, 1 if key == 'R_SDCD' else 9 - unit, unit), D.S3_RAIL)
    for net, unit, xp in (('SD_DAT1', 3, snap(x + 40.64)), ('SD_DAT2', 4, snap(x + 33.02))):
        b = sh.N(D.KEY[J], net)
        fit(sh, 'RN_SD', unit, (xp, snap(b[1] - 2.54)), {unit: D_}, unit=unit, fields='right')
        sh.wire(b, (xp, b[1]), sh.P('RN_SD', unit, unit))
        sh.sup(sh.P('RN_SD', 9 - unit, unit), D.S3_RAIL)
        sh.label((snap(xp + 1.27 if unit == 3 else x_j - 12.7), b[1]), net, 'R')
    for u in (1, 2, 4):                                # the pack named once, on its DAT1 element
        sh.placed[(D.KEY['RN_SD'], u)]['hide_fields'] = ('Reference', 'Value')
    # the socket's supply with its 10 uF, its ground and the shell
    vdd, vss = sh.N(D.KEY[J], D.S3_RAIL), sh.P(J, 6)
    e = (snap(vdd[0] - 10.16), vdd[1])
    sh.wire(vdd, (snap(vdd[0] - 7.62), vdd[1]), e)
    sh.sup(e, D.S3_RAIL, rot=90)
    fit(sh, 'C_SD', 1, (snap(vdd[0] - 7.62), snap(vdd[1] + 5.08)), {1: U_}, fields='left')
    sh.wire((snap(vdd[0] - 7.62), vdd[1]), sh.P('C_SD', 1))
    sh.gnd(sh.P('C_SD', 2))
    ground(sh, vss)
    shp = sorted((sh.P(J, n) for n in (10, 11, 12, 13)), key=lambda p: p[0])
    for a, b in zip(shp, shp[1:]):
        sh.wire(a, b)
    sh.gnd(shp[0], 2.54)
    # ---- the status LED: IO48 -> 330R -> WS2812B DIN, on +5V, down at the page's foot ------------
    led = P(25)
    y_l = snap((jb[1] + jb[3]) / 2 + 22.86)          # below the socket's middle
    x_w = snap(x - 58.42)                             # east of the module, between it and its buttons
    fit(sh, 'R_WS', 1, (snap(x_w + 22.86), y_l), {1: R_}, fields='above')
    sh.wire(led, (led[0], y_l), sh.P('R_WS', 1))
    sh.label((led[0], snap(led[1] + 1.27)), 'LED_STRIP', 'D')
    d = fit(sh, 'D_WS', 3, (x_w, y_l), {3: R_, 4: U_}, fields='right')
    wb = d['body']                                     # its long value under the data line
    d['fields'] = [(wb[2] + 1.27, y_l + 3.81, 'left'), (wb[2] + 1.27, y_l + 6.35, 'left')]
    sh.wire(sh.P('R_WS', 2), sh.P('D_WS', 3))
    sh.label((snap(sh.P('R_WS', 2)[0] - 1.27), y_l), 'WS_DIN', 'L')
    sh.nc(sh.P('D_WS', 1))
    sh.gnd(sh.P('D_WS', 2))
    vd = sh.P('D_WS', 4)
    t5 = (vd[0], snap(vd[1] - 5.08))
    sh.wire(vd, t5, (vd[0], snap(vd[1] - 7.62)))
    sh.sup((vd[0], snap(vd[1] - 7.62)), '+5V')
    fit(sh, 'C_WS', 1, (snap(vd[0] - 12.7), snap(t5[1] + 2.54)), {1: U_}, fields='left')
    sh.wire(t5, (snap(vd[0] - 12.7), t5[1]), sh.P('C_WS', 1))
    sh.gnd(sh.P('C_WS', 2))
    sh.text((snap(x_l - 2.54), 30.48),
            'ESP32-S3-WROOM-1-N16R8: the FujiNet (fujiversal-o2.h pin map), on +3V3 (the buck).\n'
            'EN: 10k / 1 uF power-on delay.  The S3_RST button, the cart RESET\n'
            '(rp-core, through the BAT54C) and the USB bridge\'s auto-program pair\n'
            '(usb sheet) all pull it low; S3_BOOT and the same pair pull IO0.\n'
            'IO4 / IO5 drive the RP2354B\'s RUN and BOOTSEL (every on-cart S3\'s\n'
            'pins); IO19 / IO20, the S3\'s own USB, host the RP\'s.\n'
            'microSD in SPI mode, 10k pull-ups on CS, DO, DAT1, DAT2 and CD.\n'
            'WS2812B-2020 on +5V: its data input (VIH 2.7 V) takes the S3\'s 3.3 V.\n'
            'The 23 spare GPIOs (right) are not connected.')
    return sh


# =========================================================================
@sheet('usb')
def usb(sh):
    """USB-C to the ESP32-S3, right to left (the receptacle on the page's right): VBUS up and along the
    top with its decoupling and the bridge's VBUS-sense divider; CC1 / CC2 to their 5.1k; the D- / D+
    pair through the USBLC6-2SC6 (flow-through: each line in two pieces, joined inside the package,
    its VBUS clamp up to the VBUS line) into the CP2102N (drawn mirrored, USB side toward the receptacle); the bridge's UART out to the
    S3 on the left and its RTS / DTR into the esptool auto-program pair (UMH3N), whose collectors
    pull the S3's EN and IO0.  That pair is the page's one crossing: RTS and DTR leave the bridge
    side by side and each reaches the base of one transistor and the emitter of the other."""
    sh.wired = True
    sh.crossing_budget = 1
    sh.through = {D.KEY['U_ESD']}                     # USBLC6: I/O1 = pins 1 / 6, I/O2 = 3 / 4 inside
    U, J, Q = 'U_UART', 'J_USB', 'U_AUTOPROG'
    xc, yc = 165.1, 139.7
    d = fit(sh, U, '4', (snap(xc + 12.7), snap(yc - 10.16)), {'4': R_, '25': L_, '6': U_}, fields='abovebelow')
    d['fields'][1] = (d['body'][2] + 1.27, d['body'][3] + 1.778, 'left')
    P = lambda n: sh.P(U, n)
    ncs(sh, U)
    sh.gnd(P(3))
    x_l = snap(xc - 88.9)                              # the left-hand port column, to the S3
    # ---- the bridge's supply: VDD and VREGIN on +3V3, 4.7 uF bulk left, 100 nF right ---------
    vdd, vri = P(6), P(7)
    y_bar = snap(vdd[1] - 12.7)
    sh.wire(vdd, (vdd[0], y_bar))
    sh.wire(vri, (vri[0], y_bar))
    a, b = sorted(((vdd[0], y_bar), (vri[0], y_bar)))
    sh.wire(a, b)
    cu = fit(sh, 'C_UART', 1, (snap(b[0] + 7.62), y_bar), {1: U_}, fields='right')['pins']['1']
    sh.wire(b, cu)
    sh.sup(cu, D.S3_RAIL)
    cb = fit(sh, 'C_UARTBULK', 1, (snap(a[0] - 7.62), y_bar), {1: U_}, fields='left')['pins']['1']
    sh.wire(a, cb)
    for c in ('C_UART', 'C_UARTBULK'):
        sh.gnd(sh.P(c, 2))
    # ---- the UART, out left to the S3 -------------------------------------------------------------
    for n, net, shape in (('26', 'S3_RXD', 'output'), ('25', 'S3_TXD', 'input')):
        p = P(n)
        sh.wire(p, (x_l, p[1]))
        sh.hlabel(Pt(x_l, p[1], -1, 0), net, 'L', shape)
    e = sh.stub(P('23'), 2.54)                         # /CTS held asserted
    sh.rail(e, 'GND', 270)
    # ---- RTS / DTR into the auto-program pair: Q1 (DTR base) pulls EN, Q2 (RTS base) pulls IO0 ---
    rts, dtr = P('24'), P('28')
    x_j2, x_j1 = snap(rts[0] - 12.7), snap(rts[0] - 20.32)
    y_q2 = snap(rts[1] + 15.24)
    y_q1 = snap(y_q2 + 17.78)
    x_q2b = snap(x_j1 - 12.7)

    def q_fields(d):                                   # ref / value right of the body, under the base line
        b = d['body']
        d['fields'] = [(b[2] + 1.27, d['y'] + 3.81, 'left'), (b[2] + 1.27, d['y'] + 6.35, 'left')]
    q_fields(fit(sh, Q, '5', (x_q2b, y_q2), {'5': R_, '3': U_}, unit=2))
    sh.wire(rts, (x_j1, rts[1]), (x_j1, y_q2), (x_q2b, y_q2))
    sh.label((snap(rts[0] - 2.54), rts[1]), 'UART_RTS', 'L')
    e2 = sh.P(Q, '4', 2)
    x_q1b = snap(e2[0] - 7.62)
    q_fields(fit(sh, Q, '2', (x_q1b, y_q1), {'2': R_, '6': U_}, unit=1))
    sh.wire(dtr, (x_j2, dtr[1]), (x_j2, y_q1), (x_q1b, y_q1))
    sh.label((snap(dtr[0] - 2.54), dtr[1]), 'UART_DTR', 'L')
    sh.wire(e2, (e2[0], y_q1))
    c2 = sh.P(Q, '3', 2)
    y_io = snap(c2[1] - 2.54)
    sh.wire(c2, (c2[0], y_io), (x_l, y_io))
    sh.hlabel(Pt(x_l, y_io, -1, 0), 'S3_IO0', 'L', 'bidirectional')
    c1 = sh.P(Q, '6', 1)
    y_en = snap(y_q2 + 5.08)
    sh.wire(c1, (c1[0], y_en), (x_l, y_en))
    sh.hlabel(Pt(x_l, y_en, -1, 0), 'S3_EN', 'L', 'bidirectional')
    e1 = sh.P(Q, '1', 1)
    x_t = snap(x_q2b + 7.62)
    y_low = snap(e1[1] + 5.08)
    sh.wire(e1, (e1[0], y_low), (x_t, y_low), (x_t, y_q2))
    sh.text((snap(x_l + 2.54), snap(y_low + 7.62)),
            "esptool's auto-program pair, as on the ESP32-S3-DevKitC-1:\n"
            'DTR low with RTS high pulls EN low; RTS low with DTR high pulls\n'
            'IO0 low; both high or both low leave the S3 alone.', 1.27)
    # ---- the USB side: reset pull-up, VBUS sense, the pair to the receptacle ---------------------
    rst = P('9')
    x_rst = snap(rst[0] + 12.7)
    fit(sh, 'R_CPRST', 2, (x_rst, snap(rst[1] - 2.54)), {2: D_}, fields='right')
    sh.wire(rst, (x_rst, rst[1]), sh.P('R_CPRST', 2))
    sh.sup(sh.P('R_CPRST', 1), D.S3_RAIL)
    sh.label((snap(rst[0] + 1.27), rst[1]), 'CP_RST', 'R')
    dm, dp, sns = P('5'), P('4'), P('8')
    y_m = dm[1]
    x_n = snap(dm[0] + 25.4)
    x_em = snap(x_n + 38.1)
    x_u = snap(x_em + 22.86)
    d = fit(sh, J, 'A7', (x_u, y_m), {'A7': L_}, fields='abovebelow')
    d['fields'][1] = (d['body'][2] + 1.27, d['body'][3] - 1.27, 'left')
    JP = lambda n: sh.P(J, n)
    # VBUS: up from the receptacle and along the top, its shunts hanging from it
    v = JP('A4')
    y_v = snap(y_m - 33.02)
    sh.wire(v, (v[0], y_v), (x_n, y_v))
    sh.rail((v[0], y_v), 'VBUS', 0)
    for key, xx in (('C_VBUS', snap(x_u - 38.1)), ('C_VBUSHF', snap(x_u - 50.8))):
        fit(sh, key, 1, (xx, snap(y_v + 2.54)), {1: U_}, fields='right')
        sh.wire((xx, y_v), sh.P(key, 1))
        sh.gnd(sh.P(key, 2))
    # the sense divider: 22k from VBUS down to the node, 47k from it to GND
    node = (x_n, sns[1])
    fit(sh, 'R_VBSH', 1, (x_n, snap(y_v + 2.54)), {1: U_}, fields='left')
    sh.wire((x_n, y_v), sh.P('R_VBSH', 1))
    sh.wire(sh.P('R_VBSH', 2), node)
    sh.wire(sns, node)
    sh.label((snap(sns[0] + 1.27), sns[1]), 'VBUS_SNS', 'R')
    fit(sh, 'R_VBSL', 1, (snap(x_n + 5.08), sns[1]), {1: L_}, fields='above')
    sh.wire(node, sh.P('R_VBSL', 1))
    e = sh.P('R_VBSL', 2)
    sh.rail(e, 'GND', 90)
    # CC1 / CC2: 5.1k to GND right at the receptacle
    for pin, key in (('A5', 'R_CC1'), ('B5', 'R_CC2')):
        p = JP(pin)
        fit(sh, key, 1, (snap(p[0] - 7.62), p[1]), {1: R_}, fields='above')
        sh.wire(p, sh.P(key, 1))
        sh.rail(sh.P(key, 2), 'GND', 270)
        sh.label((snap(p[0] - 6.35), p[1]), sh.parts[D.KEY[key]].pins['1'], 'R')
    # D- and D+ through the USBLC6-2SC6 (I/O1 pins 1 -> 6 carries D-, I/O2 pins 3 -> 4 D+): each line
    # is two drawn pieces joined inside the package, both labelled; its VBUS clamp rises to the VBUS line
    x_e = snap(x_n + 30.48)                           # its VBUS riser clear of the 1 uF's fields
    fit(sh, 'U_ESD', 1, (x_e, y_m), {1: L_, 6: R_, 5: U_}, fields='below')
    ed = sh.placed[(D.KEY['U_ESD'], 1)]
    eb = ed['body']
    ed['fields'] = [(eb[2] + 1.27, eb[1] - 1.27, 'left'), (eb[2] + 1.27, eb[3] + 3.81, 'left')]
    E = lambda n: sh.P('U_ESD', n)
    sh.wire(dm, E(1))
    sh.label((snap(dm[0] + 1.27), y_m), 'UBRG_DM', 'R')
    sh.wire(E(6), JP('A7'))
    sh.label((snap(E(6)[0] + 1.27), y_m), 'UBRG_DM', 'R')
    b7 = JP('B7')
    sh.wire(b7, (snap(b7[0] - 2.54), b7[1]), (snap(b7[0] - 2.54), y_m))
    p3 = E(3)
    if dp[1] == p3[1]:
        sh.wire(dp, p3)
    else:
        x_s = snap(x_e - 5.08)
        sh.wire(dp, (x_s, dp[1]), (x_s, p3[1]), p3)
    sh.label((snap(dp[0] + 1.27), dp[1]), 'UBRG_DP', 'R')
    a6 = JP('A6')
    p4 = E(4)
    x_jp = snap(p4[0] + 5.08)
    sh.wire(p4, (x_jp, p4[1]), (x_jp, a6[1]), a6)
    sh.label((snap(p4[0] + 1.27), p4[1]), 'UBRG_DP', 'R')
    b6 = JP('B6')
    sh.wire(b6, (snap(b6[0] - 2.54), b6[1]), (snap(b6[0] - 2.54), a6[1]))
    ev = E(5)
    sh.wire(ev, (ev[0], y_v))
    sh.gnd(E(2))
    for n in ('A8', 'B8'):
        sh.nc(JP(n))
    sh.gnd(JP('A1'))
    sh.gnd(JP('SH'))
    return sh


# =========================================================================
@sheet('power')
def power(sh):
    """The power tree, left to right: USB's VBUS through the 1.1 A resettable fuse onto +5V; along +5V
    its bulk and pad, the RP2354B's LDO under the line (+3V3_RP: the RP and the bus buffers), then the
    S3's TLV62569 buck, its 2.2 uH out to +3V3 with the 100k / 22k feedback divider under it.  The
    PWR_FLAGs of the rails only passive parts drive sit together, bottom left."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    x0, y_o = 50.8, 99.06
    # ---- VBUS -> fuse -> +5V ------------------------------------------------------------------------
    x_tv = snap(x0 + 10.16)
    x_f = snap(x0 + 20.32)
    sh.rail((x0, y_o), 'VBUS', 0)
    rail_line(sh, (x0, y_o), [x_tv, x_f])
    tee_tp(sh, 'TP_VBUS', (x_tv, y_o))
    fit(sh, 'F_VBUS', 1, (x_f, y_o), {1: L_}, fields='above')
    o = sh.P('F_VBUS', 2)
    x_sym, x_cb, x_tp5 = snap(o[0] + 7.62), snap(o[0] + 15.24), snap(o[0] + 25.4)
    x_ldo = snap(o[0] + 35.56)
    x_ci, x_ch = snap(x_ldo + 45.72), snap(x_ldo + 55.88)
    x_bk = snap(x_ch + 12.7)
    rail_line(sh, o, [x_sym, x_cb, x_tp5, x_ldo, x_ci, x_ch, x_bk])
    sh.wire((x_sym, o[1]), (x_sym, snap(o[1] - 2.54)))
    sh.rail((x_sym, snap(o[1] - 2.54)), '+5V', 0)
    tee_cap(sh, 'C_5VBULK', (x_cb, o[1]))
    tee_tp(sh, 'TP_5V', (x_tp5, o[1]))
    tee_cap(sh, 'C_BIN', (x_ci, o[1]))
    tee_cap(sh, 'C_BINHF', (x_ch, o[1]))
    # ---- the RP2354B's LDO under the line: +5V down into VIN and EN -----------------------------------
    d = fit(sh, 'U_LDO', '1', (snap(x_ldo + 5.08), snap(o[1] + 22.86)), {'1': L_, '5': R_}, fields='below')
    d['fields'] = [(d['body'][0], d['body'][1] - 1.778, 'left'), (d['body'][0] - 1.27, d['body'][3] + 1.778, 'right')]
    vin, en = sh.P('U_LDO', 1), sh.P('U_LDO', 3)
    t = (x_ldo, snap(o[1] + 10.16))
    sh.wire((x_ldo, o[1]), t, (x_ldo, vin[1]), (x_ldo, en[1]), en)
    sh.wire((x_ldo, vin[1]), vin)
    sh.wire(t, (snap(x_ldo - 7.62), t[1]))
    tee_cap(sh, 'C_LDOIN', (snap(x_ldo - 7.62), t[1]), fields='left')
    sh.nc(sh.P('U_LDO', 4))
    sh.gnd(sh.P('U_LDO', 2))
    lo = sh.P('U_LDO', 5)
    xs = [snap(lo[0] + 7.62), snap(lo[0] + 17.78), snap(lo[0] + 27.94)]
    rail_line(sh, lo, xs)
    tee_cap(sh, 'C_LDOOUT', (xs[0], lo[1]))
    tee_tp(sh, 'TP_3V3', (xs[1], lo[1]), fields='right', up=False)
    sh.wire((xs[2], lo[1]), (xs[2], snap(lo[1] - 2.54)))
    sh.rail((xs[2], snap(lo[1] - 2.54)), D.RP_RAIL, 0)
    # ---- the S3's 3.3 V buck, under the line: +5V down into VIN and EN; SW out to the inductor ---------
    d = fit(sh, 'U_BUCK', '4', (snap(x_bk + 5.08), snap(o[1] + 17.78)), {'4': L_, '3': R_, '2': D_}, fields='below')
    d['fields'] = [(d['body'][0], d['body'][1] - 1.778, 'left'), (d['body'][0] - 1.27, d['body'][3] + 1.778, 'right')]
    vin, en = sh.P('U_BUCK', 4), sh.P('U_BUCK', 1)
    sh.wire((x_bk, o[1]), (x_bk, vin[1]), (x_bk, en[1]), en)
    sh.wire((x_bk, vin[1]), vin)
    sh.gnd(sh.P('U_BUCK', 2))
    sw, fb = sh.P('U_BUCK', 3), sh.P('U_BUCK', 5)
    fit(sh, 'L_BUCK', 1, (snap(sw[0] + 12.7), sw[1]), {1: L_}, fields='above')
    sh.wire(sw, sh.P('L_BUCK', 1))
    sh.label((snap(sw[0] + 1.27), sw[1]), 'BUCK_SW', 'R')
    bo = sh.P('L_BUCK', 2)
    x_fh = snap(bo[0] + 7.62)
    xs = [x_fh, snap(bo[0] + 17.78), snap(bo[0] + 27.94), snap(bo[0] + 38.1), snap(bo[0] + 48.26)]
    rail_line(sh, bo, xs)
    # the feedback divider hanging from +3V3: R1 100k down to BUCK_FB, R2 22k on to GND; FB's own wire
    # comes in under the inductor
    fit(sh, 'R_FBH', 1, (x_fh, snap(bo[1] + 5.08)), {1: U_}, fields='right')
    sh.wire((x_fh, bo[1]), sh.P('R_FBH', 1))
    nfb = sh.P('R_FBH', 2)
    fit(sh, 'R_FBL', 1, (x_fh, snap(nfb[1] + 5.08)), {1: U_}, fields='right')
    sh.wire(nfb, sh.P('R_FBL', 1))
    sh.gnd(sh.P('R_FBL', 2))
    xq = snap(fb[0] + 2.54)
    sh.wire(fb, (xq, fb[1]), (xq, nfb[1]), nfb)
    sh.label((snap(xq + 1.27), nfb[1]), 'BUCK_FB', 'R')
    tee_cap(sh, 'C_BOUT1', (xs[1], bo[1]))
    tee_cap(sh, 'C_BOUT2', (xs[2], bo[1]))
    tee_tp(sh, 'TP_3V3S3', (xs[3], bo[1]), fields='right', up=False)
    sh.wire((xs[4], bo[1]), (xs[4], snap(bo[1] - 2.54)))
    sh.rail((xs[4], snap(bo[1] - 2.54)), D.S3_RAIL, 0)
    # ---- PWR_FLAGs: the rails driven only through passive parts --------------------------------
    y_f = snap(y_o + 53.34)
    for k_, net in enumerate(('GND', 'VBUS', '+5V', D.S3_RAIL)):
        x = snap(x0 + 25.4 * k_)
        sh.wire((x, y_f), (snap(x + 10.16), y_f))
        sh.flag((snap(x + 10.16), y_f), net)
        sh.rail((x, y_f), net, 0)
    sh.text((x0, snap(y_f - 12.7)), "PWR_FLAG: these rails reach their loads only through passive parts (USB-C, the fuse, "
            "the buck's inductor).", 1.27)
    r = lambda k: D.KEY[k]
    sh.text((x0, 25.4),
            "Power tree: the Model I's edge carries no supply the card can use (pin 39 is +5V only on keyboard boards A-E,\n"
            "and Tandy warns against loading it), so the card runs from its USB-C alone.\n"
            '  VBUS -> %s, 1.1 A hold / 2.2 A trip resettable fuse -> +5V: the WS2812, the two regulators.\n'
            '  %s AP2112K -> +3V3_RP: every RP2354B supply pin and every bus buffer (they come up together, fast).\n'
            '  %s TLV62569 (2 A buck, 2.5-5.5 V in, 1.5 MHz) -> +3V3: the ESP32-S3, the CP2102N and the microSD;\n'
            '  VOUT = 0.6 V x (1 + %s 100k / %s 22k) = 3.33 V; 2.2 uH and 2 x 22 uF (datasheet Table 4).\n'
            '%s, %s, %s and %s are bring-up pads.'
            % (r('F_VBUS'), r('U_LDO'), r('U_BUCK'), r('R_FBH'), r('R_FBL'), r('TP_VBUS'), r('TP_5V'),
               r('TP_3V3'), r('TP_3V3S3')), 1.27)
    return sh


# =========================================================================
ROOT_NOTES = """FujiNet for the TRS-80 Model I, Rev0: an RP2354B card in place of the Expansion Interface,
on a 40-wire ribbon from the keyboard unit's expansion edge, + ESP32-S3.

The card serves the Model I's cycles in software (fujinet-firmware pico/trs80m1): 32K of RAM at
8000h-FFFFh, the EI's interrupt latch, drive select, printer and FD1771 at 37E0h-37EFh, the RS-232 board
at E8h-EBh and the FujiBus pipe at D0h-D3h.  Every line meets an LVC buffer at the header: the
strobes Schmitt-triggered, D0-D7 driven only while RD* or IN* is low (OE* = DRIVE . RD* . IN*).

  m1-bus     the 2x20 ribbon header, 100k pull-downs, the five buffers (2 x 74LVC245A address, a
             74LVC245A for data through 47R, 2 x 74LVC3G17 strobes, 74LVC2G07 INT* / WAIT*), the OE gate,
             the RP2354B's GPIOs, the DIP switches, LED, debug-UART pads, the logic-analyser header
  rp-core    the RP2354B's supplies and decoupling, core regulator, crystal, SWD, RUN / BOOTSEL /
             RESET, its USB out to the S3
  fujinet    the ESP32-S3 (the FujiNet, the RP's USB host), microSD, WS2812 status light
  usb        USB-C (the card's only power), the USBLC6 ESD array, the CP2102N bridge and esptool's
             auto-program pair
  power      VBUS -> 1.1 A fuse -> +5V, the RP's LDO (+3V3_RP), the S3's buck (+3V3)

Rails (GND, VBUS, +5V, +3V3, +3V3_RP, DVDD) join by their power symbols.

Firmware contract (tools/check_nets.py checks this netlist against it): pico/trs80m1 m1_card.h (A0-A15
GPIO0-15, D0-D7 GPIO16-23, WR* 24, RD* 25, IN* 26, OUT* 27, DRIVE 28, SYSRES* 29, INT* 30, WAIT* 31,
DIPs 33-35, debug UART 44 / 45, LED 47); this board adds INTAK* on GPIO32.  The S3: fujiversal-trs80m1.h
(SD 38-41, UART0 43 / 44, WS2812 48, USB host 19 / 20) + RUN / BOOTSEL on IO4 / IO5 and SD card detect
on IO42 (README: firmware changes)."""


def root(sh, sheets):
    """The block diagram in signal-flow order: m1-bus (the header, buffers and the RP's GPIOs) and rp-core on
    the left, then the FujiNet half -- fujinet with usb under it -- on the right, power above; the
    nine signals between sheets wired without a crossing: the RP's controls and USB straight across
    to the S3; S3_EN, S3_IO0 and the UART down nested channels to the USB bridge, S3_EN tapped by
    the RP's RESET on the way."""
    b, i, o = 'bidirectional', 'input', 'output'
    sh.block('power', 30.48, 33.02, 63.5, 20.32)
    sh.block('m1-bus', 30.48, 172.72, 63.5, 20.32)
    rp = sh.block('rp-core', 30.48, 76.2, 63.5, 81.28,
                  right=[('USB_DP', b), ('USB_DM', b), ('RUN_CTL', i), ('BOOTSEL_CTL', i)] + [None] * 14 +
                  [('S3_EN', b)])
    fj = sh.block('fujinet', 132.08, 33.02, 30.48, 99.06,
                  left=[None] * 17 + [('USB_DP', b), ('USB_DM', b), ('RUN_CTL', o), ('BOOTSEL_CTL', o)]
                  + [None] * 10 + [('S3_EN', b), ('S3_IO0', b), ('S3_TXD', o), ('S3_RXD', i)])
    us = sh.block('usb', 132.08, 152.4, 30.48, 35.56,
                  left=[('S3_RXD', o), ('S3_TXD', i), ('S3_IO0', b), ('S3_EN', b)])
    for n in ('USB_DP', 'USB_DM', 'RUN_CTL', 'BOOTSEL_CTL'):
        assert rp[n][1] == fj[n][1], (n, rp[n], fj[n])
        sh.wire(rp[n], fj[n])
        sh.label((snap(rp[n][0] + 1.27), rp[n][1]), n)
    for k, n in enumerate(('S3_EN', 'S3_IO0', 'S3_TXD', 'S3_RXD')):
        xc = snap(fj[n][0] - 10.16 + 2.54 * k)
        sh.wire(fj[n], (xc, fj[n][1]), (xc, us[n][1]), us[n])
        sh.label((xc, snap(us[n][1] - 1.27)), n, 'U')
    sh.wire(rp['S3_EN'], (snap(fj['S3_EN'][0] - 10.16), rp['S3_EN'][1]))
    sh.text((30.48, 203.2), 'the Model I expansion edge (the ribbon header) is on m1-bus', 1.27)
    sh.text((187.96, 25.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh


DRAW['root'] = root
