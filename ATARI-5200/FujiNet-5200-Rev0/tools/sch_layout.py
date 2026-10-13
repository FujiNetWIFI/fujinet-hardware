"""How each sheet is drawn: placement and wiring, one function per sheet, and the root.

design.py owns the circuit; these functions only say where each part sits and how its pins are
joined (sch_draw.Sheet).  Parts are addressed by their design.py key (U_RP, C_IOV5, ...), never
by reference.  A sheet without a drawing function yet is drawn as a draft (sch_draft.py: every
pin labelled) -- electrically identical, so the board can be built from it.  sch_draw.Sheet.check(),
gen_sch.check_hierarchy() and gen_sch.netlist_parity() prove the drawing is exactly design.py's
netlist, so a wiring slip here fails the build.

Every sheet is the board turned so the fingers face left (board south -> page left, north -> right,
west -> top, east -> bottom), each part where it sits on the board (tools/sch_place.py checks the
order), signals flowing left to right from the cartridge slot.
"""
import os
import design as D
import sch_draft
from sch_draw import Sheet, Pt, snap

DRAW = {}
PAPER = {'cart-bus': 'A3', 'rp-core': 'A3', 'fujinet': 'A3', 'usb': 'A3', 'power': 'A3'}
G = 2.54


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
    one) with its ground under it -- beside the pin it serves, as on the board."""
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


# =========================================================================
@sheet('cart-bus')
def cart_bus(sh):
    """The cartridge bus, drawn as the board is built (the page is the board turned fingers-left):
    the edge on the left, every row of it level with the row it feeds; D7-D0 straight across through
    the 74HCT541, which stands over the D fingers (its Y row meets them in their order, its A row the
    RP2354B's GPIO16-23 corner in theirs: not one data line crosses another, on the board or here);
    the glue band right of the '541 (board east of it), its outputs straight into the '541's two
    enables; /EN40 and /EN80 straight across to the RP; A0-A13 onto the address bus (they change
    layers on the board) and along under the RP into its bottom pins; PHI2 and its buffer at the
    edge's foot; the interlock top left (board west, by finger 36); the RP's debug header and ADC on
    its right (board north), its LED at the page's foot (board east)."""
    sh.wired = True
    sh.crossing_budget = 3        # the /EN80 tap over /EN40, the PWR_OK riser over both enables
    J, B, U = 'J_EDGE', 'U_BUF', 'U_RP'
    yD7 = 101.6
    row = lambda k: snap(yD7 + (k - 3) * G)          # the edge's right-side rows (gen_sch.EDGE_RIGHT)
    xJ = 66.04
    dj = pin_place(sh, J, 1, 8, (xJ, yD7), fields='abovebelow')
    dj['fields'][1] = (dj['body'][0] - 2.54, dj['body'][3] + 7.62, 'right')
    E = lambda net: npin(sh, J, net)
    # ---- D7-D0 straight across through the '541 (drawn mirrored: Y faces the edge, the A row the RP)
    xY = 101.6
    pin_place(sh, B, 1, 18, (xY, yD7), mirror='y', fields='abovebelow')
    xRP = 284.48                                      # the RP's left pin column
    pin_place(sh, U, 1, D.RP_GPIO_PIN[23], (xRP, yD7), fields='abovebelow')
    for i in range(8):
        e, y = E('D%d' % i), npin(sh, B, 'D%d' % i)
        assert e[1] == y[1], ('D%d' % i, e, y)
        sh.wire(e, y)
        sh.label((snap(e[0] + 1.27), e[1]), 'D%d' % i)
        a, r = npin(sh, B, 'RP_D%d' % i), npin(sh, U, 'RP_D%d' % i, 1)
        assert a[1] == r[1], ('RP_D%d' % i, a, r)
        sh.wire(a, r)
        sh.label((snap(a[0] + 1.27), a[1]), 'RP_D%d' % i)
    # the '541's supply: VCC up to +5V with its 100 nF on a tee, GND down
    v = sh.P(B, 20)
    t = (v[0], snap(v[1] - 5.08))
    sh.wire(v, t, (v[0], snap(v[1] - 7.62)))
    sh.sup((v[0], snap(v[1] - 7.62)), '+5V')
    fit(sh, 'C_BUF', 1, (snap(t[0] + 5.08), t[1]), {1: L_}, fields='above')
    sh.wire(t, sh.P('C_BUF', 1))
    sh.gnd(sh.P('C_BUF', 2), 2.54, rot=90)
    sh.gnd(sh.P(B, 10))
    # ---- the glue band (rows 11-14), right of the '541 -------------------------------------
    g1, g2 = sh.P(B, 1), sh.P(B, 19)                  # /OE1 = SERVE_N, /OE2 = EN_ANY_N (rows 12, 13)
    # /OE2 <- EN_ANY_N = /EN40 & /EN80: the '08 drawn mirrored, its output straight into /OE2
    ia, oa = gate(sh, 'U_AND', 1, (snap(g2[0] + 10.16), g2[1]), mirror='y', fields='below')
    sh.wire(oa, g2)
    sh.label((snap(g2[0] + 1.27), g2[1]), 'EN_ANY_N')
    # /OE1 <- SERVE_N = !SERVE: the '14 further right, its output up to row 11, over the '08, down into /OE1
    ic, oc = gate(sh, 'U_INV', 3, (snap(oa[0] + 45.72), g2[1]), mirror='y', fields='below')
    xj = snap(g1[0] + 2.54)
    yt = row(11)
    xo = snap(oc[0] - 2.54)
    sh.wire(oc, (xo, oc[1]), (xo, yt), (xj, yt), (xj, g1[1]), g1)
    sh.label((snap(xj + 1.27), yt), 'SERVE_N')
    # SERVE = BUF_EN & PWR_OK: the second '08 gate, its inputs from the RP's rows 12 / 14
    ib, ob = gate(sh, 'U_AND', 2, (snap(ic['SERVE'][0][0] + 7.62), g2[1]), mirror='y', fields='below')
    sh.wire(ob, ic['SERVE'][0])
    sh.label((snap(ic['SERVE'][0][0] + 1.27), g2[1]), 'SERVE')
    rbe, rpo = npin(sh, U, 'BUF_EN', 1), npin(sh, U, 'PWR_OK', 1)
    assert rbe[1] == ib['BUF_EN'][0][1] and rpo[1] == ib['PWR_OK'][0][1], (rbe, rpo, ib)
    # BUF_EN, with its RP2350-E9 pull-down laid along row 11 to a ground (named on that row)
    xpd = snap(ib['BUF_EN'][0][0] + 5.08)
    sh.wire(rbe, (xpd, rbe[1]), ib['BUF_EN'][0])
    sh.label((snap(rbe[0] - 1.27), rbe[1]), 'BUF_EN', 'L')
    d = fit(sh, 'R_PDBUF', 1, (xpd, yt), {1: L_}, fields='above')
    d['fields'] = [(snap(d['body'][2] + 12.7), yt, 'left'), (snap(d['body'][2] + 17.78), yt, 'left')]
    sh.wire((xpd, rbe[1]), (xpd, yt))
    sh.gnd(sh.P('R_PDBUF', 2), 2.54, rot=90)
    # the PWR_OK line: from the RP's row 14 into the '08's lower input; its riser comes up from the
    # '14 pair below the enables (and crosses them: the one place the glue cannot stay planar)
    xr = snap(xpd + 17.78)
    sh.wire(rpo, (xr, rpo[1]), ib['PWR_OK'][0])
    sh.label((snap(rpo[0] - 1.27), rpo[1]), 'PWR_OK', 'L')
    # ---- the enables: straight across to the RP; the '08's inputs off them (the /EN80 tap crosses /EN40)
    x40, x80 = snap(ia['EN40_N'][0][0] + 5.08), snap(ia['EN40_N'][0][0] + 2.54)
    xtp = snap(xJ + 20.32)
    for net, x, pin, tp in (('EN40_N', x40, ia['EN40_N'][0], 'TP_EN40'), ('EN80_N', x80, ia['EN80_N'][0], 'TP_EN80')):
        e, r = E(net), npin(sh, U, net, 1)
        assert e[1] == r[1], (net, e, r)
        sh.wire(e, (xtp, e[1]), (x, e[1]), r)
        sh.wire((x, e[1]), (x, pin[1]), pin)
        sh.label((snap(e[0] + 1.27), e[1]), net)
        tee_tp(sh, tp, (xtp, e[1]), up=(net == 'EN40_N'))
    tee_tp(sh, 'TP_OE2', (snap(g2[0] + 5.08), g2[1]), up=False, fields='left')
    tee_tp(sh, 'TP_OE1', (snap(xo - 7.62), yt), up=False, fields='left')
    # ---- PWR_OK: console 5V -> 22k / 100k -> two '14 Schmitt stages, below the enables --------------
    y14 = row(22)
    ib2, ob2 = gate(sh, 'U_INV', 2, (snap(xr - 7.62), y14), fields='below')
    ia2, oa2 = gate(sh, 'U_INV', 1, (snap(ib2['PWR_OK_N'][0][0] - 10.16), y14), fields='below')
    sh.wire(oa2, ib2['PWR_OK_N'][0])
    sh.label((snap(oa2[0] + 1.27), y14), 'PWR_OK_N')
    ytp = row(21)
    sh.wire(ob2, (xr, y14), (xr, ytp), (xr, rpo[1]))
    fit(sh, 'TP_PWROK', 1, (snap(xr + 2.54), ytp), {1: L_}, fields='right')
    sh.wire((xr, ytp), sh.P('TP_PWROK', 1))
    fit(sh, 'TP_GNDBUS', 1, (snap(xr + 20.32), snap(ytp + 2.54)), {1: D_}, fields='right')
    sh.gnd(sh.P('TP_GNDBUS', 1))
    nx = snap(ia2['VSENSE'][0][0] - 7.62)
    fit(sh, 'R_VSH', 2, (snap(nx - 2.54), y14), {2: R_}, fields='above')
    sh.wire(sh.P('R_VSH', 2), (nx, y14), ia2['VSENSE'][0])
    sh.sup(sh.P('R_VSH', 1), 'CONS_5V', 2.54, rot=90)
    fit(sh, 'R_VSL', 1, (nx, snap(y14 + 2.54)), {1: U_}, fields='right')
    sh.wire((nx, y14), sh.P('R_VSL', 1))
    sh.gnd(sh.P('R_VSL', 2))
    sh.label((snap(nx + 1.27), y14), 'VSENSE')
    # ---- A0-A13: onto the address bus beside the edge, along under the RP, up into its bottom pins --
    xb = snap(xJ + 25.4)
    bus_pts = [sh.entry(E('A%d' % i), 'A%d' % i, xb, up=True) for i in range(14)]
    yrb = row(27)
    rp_pts = []
    for i in range(14):
        n = 'A%d' % i
        p = npin(sh, U, n, 1)
        e = (p[0], snap(yrb - G))
        sh.wire(p, e)
        sh.entries.append((e, (G, G)))
        sh.label((p[0], snap(p[1] + 1.27)), n, 'D')
        rp_pts.append((snap(p[0] + G), yrb))
    sh.bus((xb, min(q[1] for q in bus_pts)), (xb, max(q[1] for q in bus_pts)))
    sh.bus((xb, yrb), (max(q[0] for q in rp_pts), yrb))
    sh.label((snap(xb + 12.7), yrb), 'A[0..13]')
    # ---- PHI2: the edge's foot, its pull-up from the console 5V, the Schmitt buffer, up into the RP --
    ph = E('PHI2')
    xpu, xtpp, xu = snap(xJ + 5.08), snap(xJ + 12.7), snap(xJ + 20.32)
    pin_place(sh, 'U_PHI2', 1, 2, (xu, ph[1]), fields='above')
    rail_line(sh, ph, [xpu, xtpp, xu])
    sh.label((snap(ph[0] + 1.27), ph[1]), 'PHI2')
    fit(sh, 'R_PHI2PU', 2, (xpu, snap(ph[1] + 2.54)), {2: U_}, fields='left')
    sh.wire((xpu, ph[1]), sh.P('R_PHI2PU', 2))
    sh.sup(sh.P('R_PHI2PU', 1), 'CONS_5V', rot=180)
    tee_tp(sh, 'TP_PHI2', (xtpp, ph[1]), up=False)
    ncs(sh, 'U_PHI2')
    sh.gnd(sh.P('U_PHI2', 3))
    vp = sh.P('U_PHI2', 5)
    tv = (vp[0], snap(vp[1] - 2.54))
    sh.wire(vp, tv, (vp[0], snap(vp[1] - 5.08)))
    sh.sup((vp[0], snap(vp[1] - 5.08)), '+5V')
    fit(sh, 'C_PHI2', 1, (snap(tv[0] - 7.62), snap(tv[1] + 2.54)), {1: U_}, fields='left')
    sh.wire(tv, (snap(tv[0] - 7.62), tv[1]), sh.P('C_PHI2', 1))
    sh.gnd(sh.P('C_PHI2', 2))
    o = sh.P('U_PHI2', 4)
    pr = npin(sh, U, 'PHI2_RP', 1)
    sh.wire(o, (pr[0], o[1]), pr)
    sh.label((snap(o[0] + 1.27), o[1]), 'PHI2_RP')
    # ---- the interlock, top left (finger 36 is the board's west end): CI1 and CI2 up two columns,
    # the bridged jumper between them, the DNP low-side N-FET above it, its driver from GPIO28 ---------
    ci1, ci2 = E('ILK_A'), E('ILK_B')
    xa, xbb = snap(xJ + 7.62), snap(xJ + 33.02)
    yq, yj = row(-8), row(-3)
    sh.wire(ci1, (xa, ci1[1]), (xa, yj), (xa, yq))
    sh.wire(ci2, (xbb, ci2[1]), (xbb, yj), (xbb, yq))
    sh.label((snap(ci1[0] + 1.27), ci1[1]), 'ILK_A')
    sh.label((snap(ci2[0] + 1.27), ci2[1]), 'ILK_B')
    pin_place(sh, 'JP_ILK', 1, 1, (snap(xa + 7.62), yj), fields='above')
    sh.wire((xa, yj), sh.P('JP_ILK', 1))
    sh.wire(sh.P('JP_ILK', 2), (xbb, yj))
    d = fit(sh, 'Q_ILK', 2, (snap(xa + 7.62), yq), {2: L_, 3: R_, 1: U_}, fields='right')
    d['fields'] = [(snap(d['body'][2] + 1.27), snap(yq + 3.81), 'left'), (snap(d['body'][2] + 1.27), snap(yq + 6.35), 'left')]
    sh.wire((xa, yq), sh.P('Q_ILK', 2))
    sh.wire(sh.P('Q_ILK', 3), (xbb, yq))
    gq = sh.P('Q_ILK', 1)
    yg = snap(gq[1] - 5.08)
    sh.wire(gq, (gq[0], yg))
    sh.label((gq[0], snap(gq[1] - 1.27)), 'ILK_G', 'U')
    fit(sh, 'R_ILKG', 2, (snap(gq[0] - 5.08), yg), {2: R_}, fields='above')
    sh.wire((gq[0], yg), sh.P('R_ILKG', 2))
    sh.sup(sh.P('R_ILKG', 1), '+5V', 2.54, rot=90)
    d = fit(sh, 'Q_ILKDRV', 3, (snap(gq[0] + 10.16), yg), {3: L_, 2: R_, 1: U_}, fields='right')
    d['fields'] = [(snap(d['body'][2] + 1.27), snap(yg + 3.81), 'left'), (snap(d['body'][2] + 1.27), snap(yg + 6.35), 'left')]
    sh.wire((gq[0], yg), sh.P('Q_ILKDRV', 3))
    e = sh.stub(sh.P('Q_ILKDRV', 2), 2.54)
    sh.rail(e, 'GND', 90)
    gd = sh.P('Q_ILKDRV', 1)
    ri = npin(sh, U, 'ILK', 1)
    ytopl = snap(gd[1] - 7.62)
    xpk = snap(gd[0] + 17.78)
    sh.wire(ri, (ri[0], ytopl), (xpk, ytopl), (gd[0], ytopl), gd)
    sh.label((snap(ri[0] - 1.27), ytopl), 'ILK', 'L')
    fit(sh, 'R_ILKPD', 1, (xpk, snap(ytopl + 2.54)), {1: U_}, fields='right')
    sh.wire((xpk, ytopl), sh.P('R_ILKPD', 1))
    sh.gnd(sh.P('R_ILKPD', 2))
    # ---- the edge's supplies, grounds, open pins -----------------------------------------------
    sh.sup(sh.P(J, 26), 'CONS_5V', 2.54)
    sh.port(sh.P(J, 11), 'UNREG', 5.08, 'U', 'input')
    gp = sorted((sh.P(J, n) for n in (12, 13, 23, 25)), key=lambda q: q[0])
    yg2 = snap(gp[0][1] + 2.54)
    for q in gp:
        sh.wire(q, (q[0], yg2))
    sh.wire((gp[0][0], yg2), (gp[-1][0], yg2))
    sh.rail((gp[0][0], yg2), 'GND', 0)
    ncs(sh, J)
    # ---- the RP's right side: the debug header, the ADC divider; its spare GPIOs (top) ------------
    ncs(sh, U, 1)
    dtx, drx = npin(sh, U, 'DBG_TX', 1), npin(sh, U, 'DBG_RX', 1)
    fit(sh, 'J_DBG', 1, (snap(dtx[0] + 25.4), dtx[1]), {1: L_}, fields='right')
    sh.wire(dtx, sh.P('J_DBG', 1))
    sh.wire(drx, sh.P('J_DBG', 2))
    sh.label((snap(dtx[0] + 1.27), dtx[1]), 'DBG_TX')
    sh.label((snap(drx[0] + 1.27), drx[1]), 'DBG_RX')
    ground(sh, sh.P('J_DBG', 3))
    ad = npin(sh, U, 'VSENSE_ADC', 1)
    xa1, xa2, xa3 = snap(ad[0] + 15.24), snap(ad[0] + 25.4), snap(ad[0] + 35.56)
    rail_line(sh, ad, [xa1, xa2, xa3])
    sh.label((snap(ad[0] + 1.27), ad[1]), 'VSENSE_ADC')
    fit(sh, 'R_ADCH', 2, (xa1, snap(ad[1] - 2.54)), {2: D_}, fields='right')
    sh.wire((xa1, ad[1]), sh.P('R_ADCH', 2))
    sh.sup(sh.P('R_ADCH', 1), 'CONS_5V')
    fit(sh, 'R_ADCL', 1, (xa2, snap(ad[1] + 2.54)), {1: U_}, fields='right')
    sh.wire((xa2, ad[1]), sh.P('R_ADCL', 1))
    sh.gnd(sh.P('R_ADCL', 2))
    fit(sh, 'C_ADCF', 1, (xa3, snap(ad[1] + 2.54)), {1: U_}, fields='right')
    sh.wire((xa3, ad[1]), sh.P('C_ADCF', 1))
    sh.gnd(sh.P('C_ADCF', 2))
    # ---- the LED: the board's east-most part on this sheet, so down to the page's foot ---------------
    led = npin(sh, U, 'RP_LED', 1)
    yl = snap(E('PHI2')[1] + 7.62)
    xl = snap(led[0] + 5.08)
    fit(sh, 'R_LED', 1, (snap(xl - 5.08), yl), {1: R_}, fields='above')
    sh.wire(led, (xl, led[1]), (xl, yl), sh.P('R_LED', 1))
    sh.label((snap(led[0] + 1.27), led[1]), 'RP_LED')
    fit(sh, 'D_LED', 2, (snap(sh.P('R_LED', 2)[0] - 10.16), yl), {2: R_}, fields='below')
    sh.wire(sh.P('R_LED', 2), sh.P('D_LED', 2))
    sh.label((snap(sh.P('R_LED', 2)[0] - 1.27), yl), 'RP_LED_A', 'L')
    ground(sh, sh.P('D_LED', 1))
    # ---- the glue packages' supplies, their unused gates (inputs on GND) and the 5V bulk ----------
    xs0, ys0 = snap(xb + 22.86), snap(yrb + 22.86)
    for k, (key, unit, cap) in enumerate((('U_AND', 5, 'C_AND'), ('U_INV', 7, 'C_INV'))):
        x = snap(xs0 + 30.48 * k)
        sh.place(key, x, ys0, unit=unit, fields='right')
        sh.sup(sh.P(key, 14), '+5V')
        sh.gnd(sh.P(key, 7))
        fit(sh, cap, 1, (snap(x + 12.7), snap(ys0 - 5.08)), {1: U_}, fields='right')
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    fit(sh, 'C_GLUEBULK', 1, (snap(xs0 + 60.96), snap(ys0 - 5.08)), {1: U_}, fields='right')
    sh.sup(sh.P('C_GLUEBULK', 1), '+5V')
    sh.gnd(sh.P('C_GLUEBULK', 2))
    xu0 = snap(xs0 + 88.9)
    for k, (key, unit) in enumerate((('U_AND', 3), ('U_AND', 4), ('U_INV', 4), ('U_INV', 5), ('U_INV', 6))):
        ins, out = gate(sh, key, unit, (snap(xu0 + 20.32 * k + 7.62), ys0), fields='above')
        sh.nc(out)
        pins = [q for lst in ins.values() for q in lst]
        if len(pins) == 2:
            a_, b_ = sorted(pins, key=lambda q: q[1])
            jx = snap(a_[0] - 2.54)
            sh.wire(a_, (jx, a_[1]), (jx, b_[1]), b_)
            sh.wire((jx, b_[1]), (jx, snap(b_[1] + 2.54)))
            sh.rail((jx, snap(b_[1] + 2.54)), 'GND', 0)
        else:
            ground(sh, pins[0])
    return sh


# =========================================================================
@sheet('rp-core')
def rp_core(sh):
    """The RP2354B's own circuit around its core unit, each side of the symbol the side of the
    package it is on the board (page = board turned fingers-left): every supply pin with its
    100 nF beside it -- the board's decoupling ring; along the top (the package's west side) the
    QSPI_SS strap, the USB pair and the core-regulator corner (VREG_LX -> 3.3 uH -> DVDD,
    VREG_AVDD through 33R); along the bottom (east) the crystal, SWD and RUN.  RESET and BOOTSEL
    sit north-west of the RP on the board (under the S3's south-west corner), so top right here,
    RESET above BOOTSEL as on the board, the RESET steering diode west of the RP, so above it.
    RUN reaches that diode round the south (left) of the RP; the S3's EN, the USB pair and the
    S3's RUN / BOOTSEL controls leave on the right, toward the FujiNet half."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    U = 'U_RP'
    sh.place(U, 210.82, 160.02, unit=2, fields='abovebelow')
    P = lambda n: sh.P(U, n, 2)
    R3, DV = D.RP_IO_RAIL, 'DVDD'
    ncs(sh, U, 2)                                      # the QSPI flash pins: no flash fitted
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
    # ---- the rows above the RP, top down: S3_EN out, RESET, RUN in, BOOTSEL, BOOTSEL_CTL, USB ----
    xr = snap(P(60)[0] + 63.5)                         # the page's right-hand port column
    y_en, y_rst, y_run, y_bs, y_ctl = 35.56, 45.72, 55.88, 68.58, 78.74
    # USB: the 27R pair, up over the regulator corner and right to the S3
    for n, rkey, net, inner, y in ((67, 'R_USBP', 'USB_DP', 'RP_USB_DP', snap(y_ctl + 5.08)),
                                   (66, 'R_USBM', 'USB_DM', 'RP_USB_DM', snap(y_ctl + 7.62))):
        p = P(n)
        fit(sh, rkey, 2, (p[0], snap(p[1] - 15.24)), {2: D_}, fields='left' if n == 67 else 'right')
        sh.wire(p, sh.P(rkey, 2))
        sh.label((p[0], snap(p[1] - 1.27)), inner, 'U')
        b = sh.P(rkey, 1)
        sh.wire(b, (b[0], y), (xr, y))
        sh.hlabel(Pt(xr, y, 1, 0), net, 'R', 'bidirectional')
    # QSPI_SS: up to the BOOTSEL row; the S3's BOOTSEL control on a tee right, the pull-up left
    ss = P(75)
    sh.label((ss[0], snap(ss[1] - 1.27)), 'QSPI_SS', 'U')
    fit(sh, 'R_BSELCTL', 2, (snap(ss[0] + 5.08), y_ctl), {2: L_}, fields='above')
    sh.wire(ss, (ss[0], y_ctl), (ss[0], snap(y_ctl - 5.08)), (ss[0], y_bs))
    sh.wire((ss[0], y_ctl), sh.P('R_BSELCTL', 2))
    sh.wire(sh.P('R_BSELCTL', 1), (xr, y_ctl))
    sh.hlabel(Pt(xr, y_ctl, 1, 0), 'BOOTSEL_CTL', 'R', 'input')
    xs, y_ss = snap(ss[0] - 5.08), snap(y_ctl - 5.08)
    sh.wire((ss[0], y_ss), (xs, y_ss))
    fit(sh, 'R_SS', 2, (xs, snap(y_ss - 2.54)), {2: D_}, fields='left')
    sh.wire((xs, y_ss), sh.P('R_SS', 2))
    sh.sup(sh.P('R_SS', 1), R3)
    fit(sh, 'R_BSEL', 1, (snap(ss[0] + 7.62), y_bs), {1: L_}, fields='above')
    sh.wire((ss[0], y_bs), sh.P('R_BSEL', 1))
    # the buttons, top right (north-west of the RP on the board), RESET above BOOTSEL; GND to the right
    x_sw = snap(xr - 33.02)
    fit(sh, 'SW_RESET', 1, (x_sw, y_rst), {1: L_}, fields='above')
    ground(sh, sh.P('SW_RESET', 2))
    fit(sh, 'SW_BOOTSEL', 1, (x_sw, y_bs), {1: L_}, fields='above')
    ground(sh, sh.P('SW_BOOTSEL', 2))
    sh.wire(sh.P('R_BSEL', 2), sh.P('SW_BOOTSEL', 1))
    sh.label((snap(sh.P('R_BSEL', 2)[0] + 2.54), y_bs), 'BOOTSEL_BTN', 'R')
    # the RESET steering diode above the RP: RST_BTN in from the right, S3_EN up and out, RUN below
    x_d = snap(P(66)[0] + 7.62)
    fit(sh, 'D_RST', 3, (snap(x_d + 5.08), y_rst), {3: R_, 2: U_, 1: D_}, fields='left')
    sh.wire(sh.P('D_RST', 3), sh.P('SW_RESET', 1))
    sh.label((snap(sh.P('D_RST', 3)[0] + 2.54), y_rst), 'RST_BTN', 'R')
    en = sh.P('D_RST', 2)
    sh.wire(en, (en[0], y_en), (xr, y_en))
    sh.hlabel(Pt(xr, y_en, 1, 0), 'S3_EN', 'R', 'bidirectional')
    r1 = sh.P('D_RST', 1)
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
    # ---- SWD and RUN: down and left under the crystal to the bring-up pads ----------------------
    y1 = snap(y_c + 22.86)
    rows = {'SWCLK': y1, 'SWDIO': snap(y1 + 5.08), 'RUN': snap(y1 + 17.78)}
    x_tp = snap(P(24)[0] - 5.08)
    for n, tp in (('SWCLK', 'TP_SWCLK'), ('SWDIO', 'TP_SWDIO')):
        p = sh.N(D.KEY[U], n)
        fit(sh, tp, 1, (x_tp, rows[n]), {1: R_}, fields='left')
        sh.wire(p, (p[0], rows[n]), sh.P(tp, 1))
        sh.label((p[0], snap(p[1] + 6.35)), n, 'U')
    yg = snap(rows['SWDIO'] + 5.08)
    fit(sh, 'TP_GND', 1, (x_tp, yg), {1: R_}, fields='left')
    ground(sh, sh.P('TP_GND', 1))
    run = P(35)
    x_run = snap(P(5)[0] - 40.64)                     # left of the left-side supply rails
    sh.label((run[0], snap(run[1] + 6.35)), 'RUN', 'U')
    sh.wire(run, (run[0], rows['RUN']), (x_run, rows['RUN']), (x_run, y_run), (r1[0], y_run), r1)
    fit(sh, 'TP_RUN', 1, (x_run, rows['RUN']), {1: U_}, fields='right')
    # the RUN pull-up and the S3's RUN control, on a tee to the right under the ground pins
    y_r = snap(P(62)[1] + 33.02)
    x_pu = snap(P(81)[0] + 10.16)
    fit(sh, 'R_RUNCTL', 2, (snap(x_pu + 12.7), y_r), {2: L_}, fields='above')
    sh.wire((run[0], y_r), sh.P('R_RUNCTL', 2))
    fit(sh, 'R_RUN', 2, (x_pu, snap(y_r - 2.54)), {2: D_}, fields='right')
    sh.wire((x_pu, y_r), sh.P('R_RUN', 2))
    sh.sup(sh.P('R_RUN', 1), R3)
    sh.wire(sh.P('R_RUNCTL', 1), (xr, y_r))
    sh.hlabel(Pt(xr, y_r, 1, 0), 'RUN_CTL', 'R', 'input')
    sh.text((snap(x_run - 2.54), 25.4),
            'Supplies (RP2350 datasheet 6.3.7): IOVDD, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and VREG_VIN on +3V3_RP, the\n'
            'AP2112K LDO that rises with +5V; the core regulator switches VREG_LX through 3.3 uH onto DVDD (VREG_FB senses\n'
            'it), its analog supply VREG_AVDD through 33R / 4.7 uF.  One 100 nF at every supply pin, drawn at the pin it serves.\n'
            'RESET resets the RP2354B and the ESP32-S3 together (D%s steers RST_BTN onto RUN and S3_EN).  Hold BOOTSEL while\n'
            "pressing RESET for the RP's USB boot ROM.  The S3 does both: IO4 (RUN_CTL) low resets the RP, IO5 (BOOTSEL_CTL)\n"
            'low through that reset selects BOOTSEL.  QSPI_SD0-3 / SCLK unused: the 2 MB flash is in the package.'
            % D.KEY['D_RST'][1:])
    return sh


# =========================================================================
@sheet('fujinet')
def fujinet(sh):
    """The ESP32-S3 and what hangs off it, where it sits on the board (page = board turned
    fingers-left): the module's 3V3 decoupling above it, EN's power-on RC and the S3_RST button on
    the EN line above its left end; BOOT on IO0 left of it (the buttons sit south-west of the
    module, in the strip under it); the RP2354B's RUN / BOOTSEL controls and USB pair in from the
    left; the UART out to the USB bridge on the right; the microSD east of the module, so below it
    here, its SPI lines stepping down into the socket with the pull-ups between them; the WS2812
    east of the RP by the board's east edge, so at the page's foot, bottom left."""
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
    # ---- 3V3 and its decoupling, bulk to the right as on the board -----------------------------
    v = P(2)
    yt = snap(v[1] - 15.24)
    sh.wire(v, (v[0], snap(v[1] - 22.86)))
    sh.sup((v[0], snap(v[1] - 22.86)), '+3V3')
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
    sh.sup(sh.P('R_EN', 1), '+3V3')
    fit(sh, 'C_EN', 1, (snap(en[0] - 15.24), snap(y_en + 2.54)), {1: U_}, fields='right')
    sh.wire((snap(en[0] - 15.24), y_en), sh.P('C_EN', 1))
    sh.gnd(sh.P('C_EN', 2))
    xs = snap(x - 40.64)
    fit(sh, 'SW_S3EN', 1, (xs, snap(y_en + 2.54)), {1: U_}, fields='right')
    sh.wire((xs, y_en), sh.P('SW_S3EN', 1))
    sh.gnd(sh.P('SW_S3EN', 2))
    # ---- IO0: S3_BOOT on a tee, then out left (esptool's auto-program pair drives it too) --------
    io0 = P(27)
    sh.wire(io0, (x_l, io0[1]))
    sh.hlabel(Pt(x_l, io0[1], -1, 0), 'S3_IO0', 'L', 'bidirectional')
    xb = snap(x - 58.42)
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
        xp = snap(a[0] + 3.81)
        pn = 2 if key == 'R_SDCD' else unit           # the pin on the line (RN unit k: pins k, 9 - k)
        fit(sh, key, pn, (xp, snap(b[1] - 2.54)), {pn: D_}, unit=unit, fields='right')
        sh.wire((xp, b[1]), sh.P(key, pn, unit))
        sh.sup(sh.P(key, 1 if key == 'R_SDCD' else 9 - unit, unit), '+3V3')
    for net, unit, xp in (('SD_DAT1', 3, snap(x + 40.64)), ('SD_DAT2', 4, snap(x + 33.02))):
        b = sh.N(D.KEY[J], net)
        fit(sh, 'RN_SD', unit, (xp, snap(b[1] - 2.54)), {unit: D_}, unit=unit, fields='right')
        sh.wire(b, (xp, b[1]), sh.P('RN_SD', unit, unit))
        sh.sup(sh.P('RN_SD', 9 - unit, unit), '+3V3')
        sh.label((snap(xp + 1.27 if unit == 3 else x_j - 12.7), b[1]), net, 'R')
    for u in (1, 2, 4):                                # the pack named once, on its DAT1 element
        sh.placed[(D.KEY['RN_SD'], u)]['hide_fields'] = ('Reference', 'Value')
    # the socket's supply with its 10 uF, its ground and the shell
    vdd, vss = sh.N(D.KEY[J], '+3V3'), sh.P(J, 6)
    e = (snap(vdd[0] - 10.16), vdd[1])
    sh.wire(vdd, (snap(vdd[0] - 7.62), vdd[1]), e)
    sh.sup(e, '+3V3', rot=90)
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
    y_l = snap((jb[1] + jb[3]) / 2 + 22.86)          # below the socket's middle: east of it on the board
    x_w = snap(x_l + 30.48)
    fit(sh, 'R_WS', 1, (snap(x_w + 17.78), y_l), {1: R_}, fields='above')
    sh.wire(led, (led[0], y_l), sh.P('R_WS', 1))
    sh.label((snap(led[0] - 1.27), y_l), 'LED_STRIP', 'L')
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
            'ESP32-S3-WROOM-1-N16R8: the FujiNet (fujiversal-atari5200.h pin map).\n'
            'EN: 10k / 1 uF power-on delay.  The S3_RST button, the cart RESET\n'
            '(rp-core, through the BAT54C) and the USB bridge\'s auto-program pair\n'
            '(usb sheet) all pull it low; S3_BOOT and the same pair pull IO0.\n'
            'IO4 / IO5 drive the RP2354B\'s RUN and BOOTSEL; IO19 / IO20, the\n'
            'S3\'s own USB, go to the RP\'s.\n'
            'microSD in SPI mode, 10k pull-ups on CS, DO, DAT1, DAT2 and CD.\n'
            'WS2812B-2020 on +5V: its data input (VIH 2.7 V) takes the S3\'s 3.3 V.\n'
            'The 23 spare GPIOs (right) are not connected.')
    return sh


# =========================================================================
@sheet('usb')
def usb(sh):
    """USB-C to the ESP32-S3, right to left as on the board (the receptacle's mouth is the board's
    north edge, the page's right): VBUS up and along the top with its ESD diode, decoupling and the
    bridge's VBUS-sense divider; CC1 / CC2 to their 5.1k; the D- / D+ pair, each with its ESD diode,
    into the CP2102N (drawn mirrored, USB side toward the receptacle); the bridge's UART out to the
    S3 on the left and its RTS / DTR into the esptool auto-program pair (UMH3N), whose collectors
    pull the S3's EN and IO0.  That pair is the page's one crossing: RTS and DTR leave the bridge
    side by side and each reaches the base of one transistor and the emitter of the other."""
    sh.wired = True
    sh.crossing_budget = 1
    U, J, Q = 'U_UART', 'J_USB', 'U_AUTOPROG'
    xc, yc = 165.1, 139.7
    d = fit(sh, U, '4', (snap(xc + 12.7), snap(yc - 10.16)), {'4': R_, '25': L_, '6': U_}, fields='abovebelow')
    d['fields'][1] = (d['body'][2] + 1.27, d['body'][3] + 1.778, 'left')
    P = lambda n: sh.P(U, n)
    ncs(sh, U)
    sh.gnd(P(3))
    x_l = snap(xc - 88.9)                              # the left-hand port column, to the S3
    # ---- the bridge's supply: VDD and VREGIN on +3V3, 4.7 uF bulk left, 100 nF right ------------
    vdd, vri = P(6), P(7)
    y_bar = snap(vdd[1] - 12.7)
    sh.wire(vdd, (vdd[0], y_bar))
    sh.wire(vri, (vri[0], y_bar))
    a, b = sorted(((vdd[0], y_bar), (vri[0], y_bar)))
    sh.wire(a, b)
    cu = fit(sh, 'C_UART', 1, (snap(b[0] + 7.62), y_bar), {1: U_}, fields='right')['pins']['1']
    sh.wire(b, cu)
    sh.sup(cu, '+3V3')
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
    sh.sup(sh.P('R_CPRST', 1), '+3V3')
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
    for key, xx in (('D_ESDV', snap(x_u - 25.4)), ('C_VBUS', snap(x_u - 38.1)), ('C_VBUSHF', snap(x_u - 50.8))):
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
    # D-: straight across; its ESD diode above it
    sh.wire(dm, JP('A7'))
    b7 = JP('B7')
    sh.wire(b7, (snap(b7[0] - 2.54), b7[1]), (snap(b7[0] - 2.54), y_m))
    fit(sh, 'D_ESDM', 1, (x_em, snap(y_m - 5.08)), {1: R_}, fields='above')
    sh.wire((x_em, y_m), sh.P('D_ESDM', 1))
    sh.rail(sh.P('D_ESDM', 2), 'GND', 270)
    sh.label((snap(dm[0] + 1.27), y_m), 'UBRG_DM', 'R')
    # D+: steps down under the receptacle's D- pair to its own; its ESD diode below it
    a6 = JP('A6')
    x_jp = snap(x_em + 5.08)
    sh.wire(dp, (x_jp, dp[1]), (x_jp, a6[1]), a6)
    b6 = JP('B6')
    sh.wire(b6, (snap(b6[0] - 2.54), b6[1]), (snap(b6[0] - 2.54), a6[1]))
    sh.label((snap(dp[0] + 1.27), dp[1]), 'UBRG_DP', 'R')
    x_ep = snap(x_jp + 5.08)
    fit(sh, 'D_ESDP', 1, (x_ep, snap(a6[1] + 2.54)), {1: U_}, fields='left')
    sh.wire((x_ep, a6[1]), sh.P('D_ESDP', 1))
    sh.gnd(sh.P('D_ESDP', 2))
    for n in ('A8', 'B8'):
        sh.nc(JP(n))
    sh.gnd(JP('A1'))
    sh.gnd(JP('SH'))
    return sh


# =========================================================================
@sheet('power')
def power(sh):
    """The power tree, left to right and top to bottom as on the board (page = board turned
    fingers-left): the console's 5V comes in at the edge (left) through the AO3401A onto the +5V
    line; the RP2354B's LDO stands above that line (west of the RP on the board); under the line
    the CONS_OFF OR (BAT54C) that turns the console path off, then the raw DC row from edge 11
    (jumper, PTC, 2.2R, the AP63205 5 V buck) whose output PRE5V reaches +5V through its SS34; the
    3.3 V buck further down and right (towards the USB corner) and USB's VBUS SS34 at the bottom
    right, by the receptacle.  The PWR_FLAGs of the rails that only passive parts drive sit
    together, bottom left."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    y5, y_off, y_pre = 99.06, 116.84, 157.48
    # ---- the console side: CONS_5V, its bulk at the edge, the P-FET ----------------------------
    x0, xq = 38.1, 88.9
    sh.rail((x0, y5), 'CONS_5V', 0)
    fit(sh, 'Q_CONS', 3, (xq, y5), {3: L_, 2: R_, 1: D_}, fields='above')
    rail_line(sh, (x0, y5), [50.8, 63.5, 76.2, xq])
    tee_cap(sh, 'C_CONS', (50.8, y5))
    tee_cap(sh, 'C_CONSHF', (63.5, y5))
    tee_tp(sh, 'TP_CONS5V', (76.2, y5))
    # ---- edge 11's raw DC: jumper, PTC, the pad, 2.2R, the input caps, the 5 V buck -------------
    xh = x0
    sh.hlabel(Pt(xh, y_pre, -1, 0), 'UNREG', 'L', 'input')
    fit(sh, 'JP_UNREG', 1, (snap(xh + 7.62), y_pre), {1: L_, 2: R_}, fields='above')
    sh.wire((xh, y_pre), sh.P('JP_UNREG', 1))
    fit(sh, 'F_UNREG', 1, (snap(sh.P('JP_UNREG', 2)[0] + 12.7), y_pre), {1: L_, 2: R_}, fields='above')
    sh.wire(sh.P('JP_UNREG', 2), sh.P('F_UNREG', 1))
    sh.label((snap(sh.P('JP_UNREG', 2)[0] + 1.27), y_pre), 'UNREG_J', 'R')
    f2 = sh.P('F_UNREG', 2)
    x_tu = snap(f2[0] + 12.7)
    fit(sh, 'R_UNREG', 1, (snap(x_tu + 7.62), y_pre), {1: L_, 2: R_}, fields='above')
    rail_line(sh, f2, [x_tu, sh.P('R_UNREG', 1)[0]])
    tee_tp(sh, 'TP_UNREG', (x_tu, y_pre), fields='right', up=False)
    sh.label((snap(f2[0] + 1.27), y_pre), 'UNREG_F', 'R')
    r2 = sh.P('R_UNREG', 2)
    x_fl = snap(r2[0] + 12.7)
    xc = [snap(r2[0] + 20.32), snap(r2[0] + 30.48), snap(r2[0] + 40.64)]
    x_in = snap(xc[2] + 12.7)
    rail_line(sh, r2, [x_fl] + xc + [x_in])
    for xx, key in zip(xc, ('C_PREIN1', 'C_PREIN2', 'C_PREINHF')):
        tee_cap(sh, key, (xx, y_pre))
    sh.wire((x_fl, y_pre), (x_fl, snap(y_pre - 2.54)))
    sh.flag((x_fl, snap(y_pre - 2.54)), 'PRE_VIN')
    sh.label((snap(r2[0] + 1.27), y_pre), 'PRE_VIN', 'R')
    d = fit(sh, 'U_PRE', '3', (snap(x_in + 2.54), y_pre), {'3': L_, '5': R_, '4': D_}, fields='above')
    vin, en = sh.P('U_PRE', 3), sh.P('U_PRE', 2)
    sh.wire((x_in, y_pre), vin)
    sh.wire((x_in, y_pre), (x_in, en[1]), en)
    sh.gnd(sh.P('U_PRE', 4))
    sw, bst, fb = sh.P('U_PRE', 5), sh.P('U_PRE', 6), sh.P('U_PRE', 1)
    y_p5 = snap(sw[1] - 17.78)                         # the PRE5V line, above the buck's switch side
    x_s, x_c = snap(sw[0] + 2.54), snap(sw[0] + 10.16)
    fit(sh, 'C_PREBST', 1, (x_c, y_p5), {1: U_}, fields='right')
    sh.wire(sw, (x_s, sw[1]), (x_s, y_p5), sh.P('C_PREBST', 1))
    sh.wire(bst, (x_c, bst[1]), sh.P('C_PREBST', 2))
    sh.label((x_s, snap(sw[1] - 1.27)), 'PRE_SW', 'U')
    sh.label((snap(bst[0] + 1.27), bst[1]), 'PRE_BST', 'R')
    fit(sh, 'L_PRE', 1, (snap(x_c + 5.08), y_p5), {1: L_}, fields='above')
    sh.wire(sh.P('C_PREBST', 1), sh.P('L_PRE', 1))
    o = sh.P('L_PRE', 2)
    x_fb = snap(o[0] + 5.08)
    xs = [x_fb, snap(x_fb + 10.16), snap(x_fb + 20.32), snap(x_fb + 30.48), snap(x_fb + 40.64),
          snap(x_fb + 50.8)]
    x_o3 = snap(xs[-1] + 5.08)                         # D_OFF pin 3 (the common cathode), PRE5V pin over xs + 10.16
    fit(sh, 'D_OFF', 3, (x_o3, y_off), {3: L_, 1: U_, 2: D_}, fields='right')
    x_off = sh.P('D_OFF', 2)[0]
    x_dp = snap(x_off + 7.62)                          # the SS34, anode on the line
    fit(sh, 'D_PRE', 2, (x_dp, y_p5), {2: L_, 1: R_}, fields='below')
    rail_line(sh, o, xs + [x_off, x_dp])
    sh.wire(fb, (x_fb, fb[1]), (x_fb, y_p5))           # FB senses the output
    sh.label((snap(fb[0] + 1.27), fb[1]), 'PRE5V', 'R')
    tee_cap(sh, 'C_PREOUT1', (xs[1], y_p5))
    tee_cap(sh, 'C_PREOUT2', (xs[2], y_p5))
    tee_cap(sh, 'R_PREPD', (xs[3], y_p5))
    tee_tp(sh, 'TP_PRE5V', (xs[4], y_p5), fields='right', up=False)
    sh.wire((xs[5], y_p5), (xs[5], snap(y_p5 - 2.54)))
    sh.flag((xs[5], snap(y_p5 - 2.54)), 'PRE5V')
    sh.wire(sh.P('D_OFF', 2), (x_off, y_p5))           # PRE5V present: the console path off
    # ---- CONS_OFF: the gate, down and right to the BAT54C OR; its 100k pull-down by the diode ----
    g = sh.P('Q_CONS', 1)
    x_opd = snap(x_o3 - 10.16)
    sh.wire(g, (g[0], y_off), (x_opd, y_off), sh.P('D_OFF', 3))
    tee_cap(sh, 'R_OFFPD', (x_opd, y_off), fields='left')
    sh.label((snap(g[0] + 2.54), y_off), 'CONS_OFF', 'R')
    sh.sup(sh.P('D_OFF', 1), 'VBUS')                   # USB present: the console path off
    # ---- the +5V line: the LDO riser, D_PRE's cathode, the pad, the bulk, the buck, USB ----------
    s = sh.P('Q_CONS', 2)
    x_ldo = snap(x_o3 - 22.86)
    k = sh.P('D_PRE', 1)
    x_k = snap(k[0] + 2.54)
    sh.wire(k, (x_k, k[1]), (x_k, y5))
    caps = ((snap(x_k + 10.16), 'C_5VBULK'), (snap(x_k + 20.32), 'C_BIN1'), (snap(x_k + 30.48), 'C_BIN2'),
            (snap(x_k + 40.64), 'C_BINHF'))
    x_tp = snap(x_k + 50.8)
    x_bk = snap(x_tp + 12.7)
    x_v = snap(x_bk + 22.86)
    rail_line(sh, s, [snap(s[0] + 12.7), x_ldo, x_k] + [c[0] for c in caps] + [x_tp, x_bk, x_v])
    sh.wire((snap(s[0] + 12.7), y5), (snap(s[0] + 12.7), snap(y5 - 2.54)))
    sh.rail((snap(s[0] + 12.7), snap(y5 - 2.54)), '+5V', 0)
    for xx, key in caps:
        tee_cap(sh, key, (xx, y5))
    tee_tp(sh, 'TP_5V', (x_tp, y5), fields='right')
    # ---- the RP2354B's LDO, above the line: +5V up its riser into VIN and EN ---------------------
    fit(sh, 'U_LDO', '1', (snap(x_ldo + 2.54), snap(y5 - 38.1)), {'1': L_, '5': R_}, fields='above')
    vin, en = sh.P('U_LDO', 1), sh.P('U_LDO', 3)
    tee = (x_ldo, snap(y5 - 20.32))
    sh.wire((x_ldo, y5), tee, (x_ldo, en[1]), (x_ldo, vin[1]), vin)
    sh.wire((x_ldo, en[1]), en)
    fit(sh, 'C_LDOIN', 1, (snap(x_ldo + 7.62), snap(tee[1] + 2.54)), {1: U_}, fields='right')
    sh.wire(tee, (snap(x_ldo + 7.62), tee[1]), sh.P('C_LDOIN', 1))
    sh.gnd(sh.P('C_LDOIN', 2))
    sh.nc(sh.P('U_LDO', 4))
    sh.gnd(sh.P('U_LDO', 2))
    o = sh.P('U_LDO', 5)
    xs = [snap(o[0] + 7.62), snap(o[0] + 17.78), snap(o[0] + 35.56)]
    rail_line(sh, o, xs)
    tee_cap(sh, 'C_LDOOUT', (xs[0], o[1]))
    tee_tp(sh, 'TP_3V3RP', (xs[1], o[1]))
    sh.rail((xs[2], o[1]), '+3V3_RP', 0)
    # ---- the 3.3 V buck, below the line (drawn mirrored: input right, switch side left) ---------
    yb = snap(y_p5 + 40.64)
    fit(sh, 'U_BUCK', '3', (snap(x_bk - 2.54), yb), {'3': R_, '5': L_, '4': D_}, fields='above')
    vin, en = sh.P('U_BUCK', 3), sh.P('U_BUCK', 2)
    sh.wire((x_bk, y5), (x_bk, vin[1]), (x_bk, en[1]), en)
    sh.wire((x_bk, vin[1]), vin)
    sh.gnd(sh.P('U_BUCK', 4))
    sw, bst, fb = sh.P('U_BUCK', 5), sh.P('U_BUCK', 6), sh.P('U_BUCK', 1)
    y_top = snap(sw[1] - 17.78)
    x_s, x_c = snap(sw[0] - 2.54), snap(sw[0] - 7.62)
    fit(sh, 'C_BST', 1, (x_c, y_top), {1: U_}, fields='left')
    sh.wire(sw, (x_s, sw[1]), (x_s, y_top), sh.P('C_BST', 1))
    sh.wire(bst, (x_c, bst[1]), sh.P('C_BST', 2))
    sh.label((x_s, snap(sw[1] - 1.27)), 'BUCK_SW', 'U')
    sh.label((x_c, snap(bst[1] - 1.27)), 'BUCK_BST', 'U')
    sh.sup(fb, '+3V3', 2.54, rot=90)                   # FB senses the output
    fit(sh, 'L_BUCK', 1, (snap(x_c - 5.08), y_top), {1: R_}, fields='above')
    sh.wire(sh.P('C_BST', 1), sh.P('L_BUCK', 1))
    o = sh.P('L_BUCK', 2)
    xs = [snap(o[0] - 7.62), snap(o[0] - 20.32), snap(o[0] - 33.02), snap(o[0] - 45.72)]
    rail_line(sh, o, xs)
    tee_cap(sh, 'C_BOUT1', (xs[0], y_top))
    tee_cap(sh, 'C_BOUT2', (xs[1], y_top))
    tee_tp(sh, 'TP_3V3', (xs[2], y_top))
    sh.rail((xs[3], y_top), '+3V3', 0)
    # ---- USB: VBUS through the SS34, at the bottom right by the receptacle -----------------------
    yd = snap(yb + 25.4)
    fit(sh, 'D_VBUS', 1, (x_v, snap(yd - 7.62)), {1: U_, 2: D_}, fields='right')
    sh.wire((x_v, y5), sh.P('D_VBUS', 1))
    a = sh.P('D_VBUS', 2)
    x_pd, x_vb = snap(a[0] + 7.62), snap(a[0] + 17.78)
    sh.wire(a, (a[0], yd))
    rail_line(sh, (a[0], yd), [x_pd, x_vb])
    tee_cap(sh, 'R_VBPD', (x_pd, yd))
    sh.rail((x_vb, yd), 'VBUS', 0)
    # ---- PWR_FLAGs: the rails driven only through passive parts --------------------------------
    for k_, net in enumerate(('GND', 'CONS_5V', '+5V', 'VBUS', '+3V3')):
        x = snap(x0 + 25.4 * k_)
        y = 243.84
        sh.wire((x, y), (snap(x + 10.16), y))
        sh.flag((snap(x + 10.16), y), net)
        sh.rail((x, y), net, 0)
    sh.text((x0, 228.6), 'PWR_FLAG: these rails reach their loads only through passive parts (the edge fingers, '
            "USB-C, the P-FET, the SS34s, the bucks' inductors).", 1.27)
    r = lambda k: D.KEY[k]
    sh.text((x0, 25.4),
            'Power tree: +5V is the OR of three sources.\n'
            "  CONS_5V  edge 26, the console's VR1 (a 78M05, 0.5 A, on the original CA018087 board, which also feeds the\n"
            '           console\'s RAM and controllers), through %s AO3401A (D = CONS_5V, S = +5V): on unless its gate CONS_OFF is\n'
            '           high; with the gate high only its body diode is left, which never passes anything back into the console.\n'
            '  VBUS     USB-C, through %s SS34.\n'
            "  PRE5V    edge 11, the adapter's raw DC (9-13 V; universal boards only, ahead of the power switch, so live whenever\n"
            '           the adapter is plugged in): %s bridged jumper (cut it to take nothing from pin 11), %s 0.35 A PTC, %s 2.2R\n'
            '           inrush limit, %s AP63205 5 V buck, %s SS34.  Never ground pin 11: on a universal console it is the adapter.\n'
            'CONS_OFF = VBUS OR PRE5V (%s BAT54C, %s 100k): either one turns the console path off, so with raw DC present the\n'
            'cart takes nothing from VR1.  %s / %s 4.7k hold the SS34s\' reverse leakage (0.5 mA at 25 C, 20 mA at 100 C) off\n'
            "the OR's inputs, so the console path stays on (tools/audit/spice_checks.py).  +5V feeds the 74HCT541 / '08 / '14,\n"
            'the PHI2 buffer, the WS2812, the AP2112K LDO -> +3V3_RP (every RP2354B supply pin: it rises with +5V, so the\n'
            "5V-tolerant pads are never unpowered with 5 V on them) and the AP63203 buck -> +3V3 (ESP32-S3, microSD, CP2102N).\n"
            '%s, %s, %s, %s, %s, %s and the rp-core DVDD pad are bring-up test points.'
            % (r('Q_CONS'), r('D_VBUS'), r('JP_UNREG'), r('F_UNREG'), r('R_UNREG'), r('U_PRE'), r('D_PRE'),
               r('D_OFF'), r('R_OFFPD'), r('R_VBPD'), r('R_PREPD'), r('TP_CONS5V'), r('TP_UNREG'),
               r('TP_PRE5V'), r('TP_5V'), r('TP_3V3'), r('TP_3V3RP')), 1.27)
    return sh


# =========================================================================
ROOT_NOTES = """FujiNet for the Atari 5200 SuperSystem, Rev0: RP2354B on the cart bus + ESP32-S3.

This page is the board seen from its component side (the label face), turned so that the edge
fingers face left (board south -> page left, north -> right, west -> top, east -> bottom), 2:1,
each sheet's block where its circuit sits.  Every sheet is drawn the same way: its parts where
they are on the board, every connection on it a wire, signals flowing left to right from the
console to the USB-C.

  cart-bus   the 36-pin edge, the 74HCT541 data buffer, the '08 / '14 enable glue, the RP2354B's
             48 GPIOs, the PHI2 Schmitt buffer, the interlock (18 / 36) jumper and its DNP switch,
             the PWR_OK and ADC senses of the console 5V, the debug UART, the bring-up pads
  rp-core    the RP2354B's supplies and decoupling ring, core regulator, crystal, SWD, RUN /
             BOOTSEL, USB to the S3
  fujinet    the ESP32-S3 (FujiNet), microSD, WS2812 status LED, S3 EN / BOOT
  usb        USB-C, the CP2102N bridge and esptool's auto-program pair
  power      +5V = console 5V (P-FET) OR edge 11 raw DC (5 V buck) OR USB VBUS, the 3.3 V
             buck (+3V3), the RP's LDO (+3V3_RP)

Between sheets: the nine signals wired here; the rails (GND, CONS_5V, VBUS, +5V, +3V3,
+3V3_RP, DVDD) by their power symbols.

The co-design (docs/floorplan-study.md): the 74HCT541 sits over the D0-D7 fingers, its channels
taken in reverse so that finger -> '541 -> RP2354B GPIO16-23 is planar on F.Cu (the fan-in is
drawn by tools/gen_pcb.py and locked before routing), the RP2354B straight north of it.

Stack-up: 1.6 mm, 6 layers.  F.Cu every part, pins 1-18 (the label face), signals + GND pour |
In1 GND plane | In2, In3 signals | In4 power: +3V3 north, a +5V island south and east, +3V3_RP
under the RP2354B ring, DVDD under its core | B.Cu pins 19-36, signals + GND pour.

Firmware contract (tools/check_nets.py, tools/check_glue.py check this netlist against it):
fujinet-firmware pico/atari-5200 a52_cart.h (A0-A13 GPIO0-13, /EN40 GPIO14, /EN80 GPIO15,
D0-D7 GPIO16-23, PWR_OK 24, PHI2 25, BUF_EN 26, LED 27, ILK 28, VSENSE ADC GPIO40, debug UART
GPIO44 / 45); glue a52_glue_drive(); ESP32-S3 pin map fujiversal-atari5200.h."""


def root(sh, sheets):
    """The board outline turned fingers-left at 2:1 (tools/gen_pcb.OUTLINE), a block per sheet at
    its region, the nine signals between sheets wired without a crossing: UNREG from the edge to
    the power block; the RP's controls and USB straight across to the S3; S3_EN, S3_IO0 and the
    UART down nested channels to the USB bridge, S3_EN tapped by the RP's RESET on the way."""
    import gen_pcb as GP
    px, py = 25.4, 25.4
    tf = lambda bx, by: (px + 2 * (GP.Y1 - by), py + 2 * (bx - GP.X0))
    pts = [tf(*p) for p in GP.OUTLINE]
    sh.poly(pts + pts[:1])
    b, i, o = 'bidirectional', 'input', 'output'
    cb = sh.block('cart-bus', 45.72, 58.42, 76.2, 93.98, right=[None] * 33 + [('UNREG', o)])
    pw = sh.block('power', 132.08, 142.24, 27.94, 45.72, left=[('UNREG', i)])
    rp = sh.block('rp-core', 132.08, 50.8, 27.94, 81.28,
                  right=[None, None, ('BOOTSEL_CTL', i), ('USB_DP', b), ('USB_DM', b), ('RUN_CTL', i)]
                  + [None] * 12 + [('S3_EN', b)])
    fj = sh.block('fujinet', 177.8, 30.48, 33.02, 99.06,
                  left=[None] * 10 + [('BOOTSEL_CTL', o), ('USB_DP', b), ('USB_DM', b), ('RUN_CTL', o)]
                  + [None] * 4 + [('S3_EN', b), ('S3_IO0', b), ('S3_TXD', o), ('S3_RXD', i)])
    us = sh.block('usb', 177.8, 152.4, 33.02, 35.56,
                  left=[('S3_RXD', o), ('S3_TXD', i), ('S3_IO0', b), ('S3_EN', b)])
    sh.wire(cb['UNREG'], pw['UNREG'])
    sh.label((snap(cb['UNREG'][0] + 1.27), cb['UNREG'][1]), 'UNREG')
    for n in ('BOOTSEL_CTL', 'USB_DP', 'USB_DM', 'RUN_CTL'):
        sh.wire(rp[n], fj[n])
        sh.label((snap(rp[n][0] + 1.27), rp[n][1]), n)
    for k, n in enumerate(('S3_EN', 'S3_IO0', 'S3_TXD', 'S3_RXD')):
        xc = snap(fj[n][0] - 10.16 + 2.54 * k)
        sh.wire(fj[n], (xc, fj[n][1]), (xc, us[n][1]), us[n])
        sh.label((xc, snap(us[n][1] - 1.27)), n, 'U')
    sh.wire(rp['S3_EN'], (snap(fj['S3_EN'][0] - 10.16), rp['S3_EN'][1]))
    sh.text((snap(px + 2.54), 104.14), 'edge\nfingers:\nthe\nconsole\nslot', 1.27)
    sh.text((233.68, 25.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh


DRAW['root'] = root
