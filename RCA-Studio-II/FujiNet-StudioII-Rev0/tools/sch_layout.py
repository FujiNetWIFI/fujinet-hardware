"""How each sheet is drawn: placement and wiring, one function per sheet, and the root.

design.py owns the circuit; these functions only say where each part sits and how its pins are
joined (sch_draw.Sheet).  Parts are addressed by their design.py key (U_RP, C_IOV5, ...), never
by reference.  A sheet without a drawing function is drawn as a draft (sch_draft.py: every pin
labelled) -- electrically identical.  sch_draw.Sheet.check(), gen_sch.check_hierarchy() and
gen_sch.netlist_parity() prove the drawing is exactly design.py's netlist, so a wiring slip here
fails the build.

There is no board yet, so the sheets follow the signal, not a floorplan: the cartridge edge on the
left, the RP2354B on the right, every bus line one straight wire between them.
"""
import os
import design as D
import sch_draft
from sch_draw import Sheet, Pt, snap

DRAW = {}
PAPER = {'cart-bus': 'A3', 'rp-core': 'A3', 'power': 'A3'}
G = 2.54
# cart-bus rows (2.54 mm each, from D0): the edge symbol, the '541 and the RP's unit A are built on
# them (gen_sch.EDGE_RIGHT / RP_A_LEFT), so every bus line is a straight wire
ROW = {'D': 0, 'OE1': 9, 'OE2': 10, 'PWROK': 22, 'MRD': 27, 'NOR': 34, 'MA': 42}


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
@sheet('cart-bus')
def cart_bus(sh):
    """The cartridge bus, left to right from the slot: the edge on the left, every row of it level
    with the row it feeds; D0-D7 straight across through the 74HCT541 (drawn mirrored, its Y row
    facing the edge, its A row the RP2354B's GPIO16-23); /MRD on its own row, rising into the '541's
    /OE1, dropping into the CART CS NOR and running on through 330R to GPIO9; /DRIVE from GPIO24
    through an OR with PWR_OK_N into /OE2, /CLAIM from GPIO25 through the other OR into the NOR, each
    with its pull-up; PWR_OK_N one vertical line from the first OR to the second, the console-5 V
    sense's two Schmitt stages teed off it (the second into GPIO26); CART CS from the NOR back to
    the edge; MA0-MA7 and TPA straight across through their 330R to GPIO0-8.  The RP's right side:
    the debug header, the ADC divider, the LED, then the glue packages' supplies."""
    sh.wired = True
    # two crossings, both forced: /OE1 (/MRD, from the edge) sits between the '541's A pins and /OE2
    # (from the RP side), so the /MRD riser passes the /OE2 line; PWR_OK_N must reach both ORs, one
    # above the /MRD line (edge to GPIO9) and one below it, so it crosses that line once
    sh.crossing_budget = 2
    J, B, U, NOR = 'J_EDGE', 'U_BUF', 'U_RP', 'U_NOR'
    y0 = 50.8
    row = lambda k: snap(y0 + k * G)
    xE = 50.8
    dj = pin_place(sh, J, 1, 10, (xE, row(ROW['D'])), fields='abovebelow')
    jb = dj['body']
    dj['fields'][1] = (snap(jb[0] - 1.27), snap(jb[3] - 1.27), 'right')
    E = lambda net: npin(sh, J, net)
    # ---- the column plan: the '541, the /MRD riser, the ORs, PWR_OK_N, the RP ------------------------
    xY = snap(xE + 50.8)
    xA = snap(xY + 25.4)
    xm = snap(xA + 5.08)                               # the riser into /OE1
    xv = snap(xm + 45.72)                              # PWR_OK_N
    xRP = snap(xv + 55.88)
    # ---- D0-D7 straight across through the '541 ---------------------------------------------------
    db = pin_place(sh, B, 1, 18, (xY, row(ROW['D'])), mirror='y', fields='abovebelow')
    db['fields'][1] = (snap(db['body'][0] - 1.27), snap(db['body'][3] + 1.778), 'right')
    du = pin_place(sh, U, 1, D.RP_GPIO_PIN[16], (xRP, row(ROW['D'])), fields='abovebelow')
    ub = du['body']
    du['fields'][1] = (ub[0], snap(ub[3] + 1.778), 'left')
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
    oe1, oe2 = sh.P(B, 1), sh.P(B, 19)
    assert oe1[1] == row(ROW['OE1']) and oe2[1] == row(ROW['OE2']), (oe1, oe2)
    # ---- /OE2 = /DRIVE | PWR_OK_N: the first OR (drawn mirrored), its output over the riser to /OE2 --
    ia, oa = gate(sh, 'U_OR', 1, (snap(xm + 10.16), oe2[1]), mirror='y', fields='below')
    sh.wire(oa, oe2)
    sh.label((snap(oa[0] - 1.27), oe2[1]), 'OE2_N', 'L')
    r24 = npin(sh, U, 'DRIVE_N', 1)
    assert r24[1] == ia['DRIVE_N'][0][1]
    x_pd, x_tpd = snap(xv + 30.48), snap(xv + 40.64)
    rail_line(sh, r24, [x_tpd, x_pd, ia['DRIVE_N'][0][0]])
    sh.label((snap(r24[0] - 1.27), r24[1]), 'DRIVE_N', 'L')
    fit(sh, 'R_PUDRIVE', 2, (x_pd, snap(r24[1] + 2.54)), {2: U_}, fields='right')
    sh.wire((x_pd, r24[1]), sh.P('R_PUDRIVE', 2))
    sh.sup(sh.P('R_PUDRIVE', 1), '+5V', rot=180)
    tee_tp(sh, 'TP_DRIVE', (x_tpd, r24[1]), up=False)
    # ---- the NOR, near the edge under the /MRD line (drawn mirrored: output toward the edge) ---------
    yN = row(ROW['NOR'])
    x_no = snap(xE + 20.32)
    dn = pin_place(sh, NOR, 1, 4, (x_no, yN), mirror='y')
    nb = dn['body']
    dn['fields'] = [(snap(nb[0] - 1.27), snap(yN - 5.08), 'right'), (snap(nb[0] - 1.27), snap(yN - 2.54), 'right')]
    n1, n2 = sh.P(NOR, 1), sh.P(NOR, 2)
    assert (n1[1], n2[1]) == (row(ROW['NOR'] - 1), row(ROW['NOR'] + 1)), (n1, n2)
    sh.sup(sh.P(NOR, 5), '+5V')
    sh.gnd(sh.P(NOR, 3))
    # ---- CS_REQ_N = /CLAIM | PWR_OK_N: the second OR (mirrored), into the NOR's lower input ---------
    ib, ob = gate(sh, 'U_OR', 2, (snap(xv - 20.32), n2[1]), mirror='y', fields='below')
    sh.wire(ob, n2)
    sh.label((snap(n2[0] + 1.27), n2[1]), 'CS_REQ_N')
    r25 = npin(sh, U, 'CLAIM_N', 1)
    assert r25[1] == ib['CLAIM_N'][0][1]
    x_pc, x_tcl = snap(xv + 10.16), snap(xv + 22.86)
    rail_line(sh, r25, [x_tcl, x_pc, ib['CLAIM_N'][0][0]])
    sh.label((snap(r25[0] - 1.27), r25[1]), 'CLAIM_N', 'L')
    fit(sh, 'R_PUCLAIM', 2, (x_pc, snap(r25[1] - 2.54)), {2: D_}, fields='right')
    sh.wire((x_pc, r25[1]), sh.P('R_PUCLAIM', 2))
    sh.sup(sh.P('R_PUCLAIM', 1), '+5V')
    tee_tp(sh, 'TP_CLAIM', (x_tcl, r25[1]), up=False)
    # ---- PWR_OK: CONS_5V -> 22k / 100k -> '14 -> PWR_OK_N -> '14 -> GPIO26 ---------------------------
    yP = row(ROW['PWROK'])
    i1, o1 = gate(sh, 'U_INV', 1, (snap(xv - 2.54), snap(yP - 5.08)), fields='above')
    i2, o2 = gate(sh, 'U_INV', 2, (snap(xv + 17.78), yP), fields='above')
    p2 = i2['PWR_OK_N'][0]
    assert p2[0] == snap(xv + 2.54), p2
    # PWR_OK_N: one line from the first OR's lower input down to the second OR's upper input
    pa, pb = ia['PWR_OK_N'][0], ib['PWR_OK_N'][0]
    sh.wire(pa, (xv, pa[1]), (xv, o1[1]), (xv, yP), (xv, pb[1]), pb)
    sh.wire(o1, (xv, o1[1]))
    sh.wire((xv, yP), p2)
    sh.label((snap(pa[0] + 1.27), pa[1]), 'PWR_OK_N')
    vin = i1['VSENSE'][0]
    x_n = snap(vin[0] - 10.16)
    sh.wire((x_n, vin[1]), vin)
    sh.label((snap(x_n + 1.27), vin[1]), 'VSENSE')
    fit(sh, 'R_VSH', 2, (x_n, snap(vin[1] - 2.54)), {2: D_}, fields='right')
    sh.wire((x_n, vin[1]), sh.P('R_VSH', 2))
    sh.sup(sh.P('R_VSH', 1), 'CONS_5V')
    fit(sh, 'R_VSL', 1, (x_n, snap(vin[1] + 2.54)), {1: U_}, fields='right')
    sh.wire((x_n, vin[1]), sh.P('R_VSL', 1))
    sh.gnd(sh.P('R_VSL', 2))
    rpo = npin(sh, U, 'PWR_OK', 1)
    assert rpo[1] == yP
    x_tpp = snap(o2[0] + 7.62)
    rail_line(sh, o2, [x_tpp, rpo[0]])
    sh.label((snap(rpo[0] - 1.27), yP), 'PWR_OK', 'L')
    tee_tp(sh, 'TP_PWROK', (x_tpp, yP), up=False)
    # ---- /MRD: the edge -> the NOR, the '541's /OE1, 330R -> GPIO9 -----------------------------------
    yM = row(ROW['MRD'])
    em = E('MRD_N')
    assert em[1] == yM
    x_tp = snap(xE + 12.7)                             # the bring-up pads' column
    xd = snap(n1[0] + 5.08)                            # the drop into the NOR
    rgp9 = npin(sh, U, 'RP_MRD', 1)
    hres(sh, 'R_MRD', (snap(xRP - 20.32), yM))
    rail_line(sh, em, [x_tp, xd, xm, sh.P('R_MRD', 1)[0]])
    sh.label((snap(em[0] + 1.27), yM), 'MRD_N')
    tee_tp(sh, 'TP_MRD', (x_tp, yM), up=False)
    sh.wire((xd, yM), (xd, n1[1]), n1)
    sh.wire((xm, yM), (xm, oe1[1]), oe1)
    sh.label((snap(oe1[0] + 1.27), oe1[1]), 'MRD_N')
    sh.wire(sh.P('R_MRD', 2), rgp9)
    sh.label((snap(sh.P('R_MRD', 2)[0] + 1.27), yM), 'RP_MRD')
    # ---- CART CS: the NOR's output straight back to the edge ----------------------------------------
    ec = E('CART_CS')
    assert ec[1] == yN
    rail_line(sh, ec, [x_tp, x_no])
    sh.label((snap(ec[0] + 1.27), yN), 'CART_CS')
    tee_tp(sh, 'TP_CARTCS', (x_tp, yN), up=False)
    # ---- MA0-MA7, TPA: straight across through their 330R -----------------------------------------
    for i in range(9):
        net, rnet, key = ('MA%d' % i, 'RP_MA%d' % i, 'R_MA%d' % i) if i < 8 else ('TPA', 'RP_TPA', 'R_TPA')
        e, r = E(net), npin(sh, U, rnet, 1)
        assert e[1] == r[1] == row(ROW['MA'] + 2 * i), (net, e, r)
        hres(sh, key, (xA, e[1]))
        if net == 'TPA':
            rail_line(sh, e, [x_tp, sh.P(key, 1)[0]])
            tee_tp(sh, 'TP_TPA', (x_tp, e[1]), up=False)
        else:
            sh.wire(e, sh.P(key, 1))
        sh.wire(sh.P(key, 2), r)
        sh.label((snap(e[0] + 1.27), e[1]), net)
        sh.label((snap(sh.P(key, 2)[0] + 1.27), e[1]), rnet)
    fit(sh, 'TP_GNDBUS', 1, (snap(xE + 30.48), row(ROW['MA'] + 19)), {1: D_}, fields='right')
    sh.gnd(sh.P('TP_GNDBUS', 1))
    # ---- the edge's supply and grounds -------------------------------------------------------------
    sh.sup(sh.P(J, 15), 'CONS_5V')
    sh.gnd(sh.P(J, 6))
    sh.gnd(sh.P(J, 7))
    # ---- the RP's right side: debug header, ADC divider, LED; spare GPIOs top and bottom -----------
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
    led = npin(sh, U, 'RP_LED', 1)
    fit(sh, 'R_LED', 1, (snap(led[0] + 12.7), led[1]), {1: L_}, fields='above')
    sh.wire(led, sh.P('R_LED', 1))
    sh.label((snap(led[0] + 1.27), led[1]), 'RP_LED')
    fit(sh, 'D_LED', 2, (snap(sh.P('R_LED', 2)[0] + 12.7), led[1]), {2: L_}, fields='above')
    sh.wire(sh.P('R_LED', 2), sh.P('D_LED', 2))
    sh.label((snap(sh.P('R_LED', 2)[0] + 1.27), led[1]), 'RP_LED_A')
    ground(sh, sh.P('D_LED', 1))
    # ---- the glue packages' supplies and the 5V bulk, right of the RP; the spare gates at the foot ---
    xr0, ys0 = snap(led[0] + 7.62), row(ROW['MA'] + 6)
    for k, (key, unit) in enumerate((('U_INV', 7), ('U_OR', 5))):
        sh.place(key, snap(xr0 + 22.86 * k), ys0, unit=unit, fields='right')
        sh.sup(sh.P(key, 14), '+5V')
        sh.gnd(sh.P(key, 7))
    for k, cap in enumerate(('C_INV', 'C_OR', 'C_NOR', 'C_GLUEBULK')):
        x = snap(xr0 + 43.18 + 12.7 * k)
        fit(sh, cap, 1, (x, snap(ys0 - 3.81)), {1: U_}, fields='right')
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    yg = row(ROW['MA'] + 24)
    for k, (key, unit) in enumerate((('U_INV', 3), ('U_INV', 4), ('U_INV', 5), ('U_INV', 6), ('U_OR', 3),
                                     ('U_OR', 4))):
        ins, out = gate(sh, key, unit, (snap(xE + 25.4 + 22.86 * k), yg), fields='above')
        sh.nc(out)
        pins = sorted((q for lst in ins.values() for q in lst), key=lambda q: q[1])
        if len(pins) == 2:
            a_, b_ = pins
            jx = snap(a_[0] - 2.54)
            sh.wire(a_, (jx, a_[1]), (jx, b_[1]), b_)
            sh.wire((jx, b_[1]), (jx, snap(b_[1] + 2.54)))
            sh.rail((jx, snap(b_[1] + 2.54)), 'GND', 0)
        else:
            ground(sh, pins[0])
    r = lambda k: D.KEY[k]
    sh.text((snap(led[0] - 2.54), row(ROW['MA'] + 14)),
            "The glue (s2_cart.h): the '541 (%s) drives D0-D7 while /OE1 = /MRD and\n"
            '/OE2 = /DRIVE | /PWROK are both low (s2_glue_drive); CART CS = NOR(/MRD,\n'
            '/CLAIM | /PWROK) (%s, %s; s2_glue_cartcs) turns the console RAM off for a\n'
            'read the RP claims.  /MRD alone ends both.  With the console off (PWR_OK_N\n'
            'high) nothing is driven into it, whatever the RP, on USB, left on /DRIVE\n'
            'and /CLAIM.  5 V CMOS levels: the 1802 VIH is 3.5 V at 5 V.\n'
            '%s / %s 10k to +5V hold /DRIVE and /CLAIM high, the cart silent, while\n'
            'the RP is unpowered or booting (they beat its reset pull-down; RP2350-E9).\n'
            "PWR_OK: edge 15 (the console's 5 V, before the P-FET) through %s / %s into\n"
            "two '14 Schmitt stages; the first, PWR_OK_N, gates the two ORs.  Every\n"
            'console line reaches the RP through 330R; GPIO0-31 are 5 V tolerant\n'
            'whenever IOVDD is up.  ADC0 (GPIO40) reads edge 15 through %s / %s.\n'
            'Edge pin 6 (ROM DISABLE) is grounded, as on a stock cartridge.'
            % (r('U_BUF'), r('U_OR'), r('U_NOR'), r('R_PUDRIVE'), r('R_PUCLAIM'), r('R_VSH'), r('R_VSL'),
               r('R_ADCH'), r('R_ADCL')), 1.27)
    return sh


# =========================================================================
@sheet('rp-core')
def rp_core(sh):
    """The RP2354B's own circuit around its core unit (FujiNet-5200 Rev0's drawing): every supply pin
    with its 100 nF beside it; along the top the QSPI_SS strap and BOOTSEL, the USB pair and the
    core-regulator corner (VREG_LX -> 3.3 uH -> DVDD, VREG_AVDD through 33R); along the bottom the
    crystal, SWD and RUN with its pull-up and the RESET button.  The USB pair leaves on the right,
    to the receptacle on the power sheet."""
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
    sh.wire(ss, (ss[0], y_ss), (ss[0], y_bs))
    xs = snap(ss[0] - 5.08)
    sh.wire((ss[0], y_ss), (xs, y_ss))
    fit(sh, 'R_SS', 2, (xs, snap(y_ss - 2.54)), {2: D_}, fields='left')
    sh.wire((xs, y_ss), sh.P('R_SS', 2))
    sh.sup(sh.P('R_SS', 1), R3)
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
    # ---- RUN: down to its pad; the pull-up and the RESET button on a tee to the right ------------
    run = P(35)
    sh.label((run[0], snap(run[1] + 6.35)), 'RUN', 'U')
    y_r = snap(P(62)[1] + 33.02)
    y_end = snap(y1 + 17.78)
    sh.wire(run, (run[0], y_r), (run[0], y_end))
    fit(sh, 'TP_RUN', 1, (run[0], y_end), {1: U_}, fields='right')
    x_pu = snap(P(81)[0] + 10.16)
    fit(sh, 'SW_RESET', 1, (snap(x_pu + 12.7), y_r), {1: L_}, fields='above')
    sh.wire((run[0], y_r), (x_pu, y_r), sh.P('SW_RESET', 1))
    ground(sh, sh.P('SW_RESET', 2))
    fit(sh, 'R_RUN', 2, (x_pu, snap(y_r - 2.54)), {2: D_}, fields='right')
    sh.wire((x_pu, y_r), sh.P('R_RUN', 2))
    sh.sup(sh.P('R_RUN', 1), R3)
    sh.text((snap(P(5)[0] - 40.64), 25.4),
            'Supplies (RP2350 datasheet 6.3.7): IOVDD, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and VREG_VIN on +3V3, the\n'
            'AP2112K LDO that rises with +5V; the core regulator switches VREG_LX through 3.3 uH onto DVDD (VREG_FB senses\n'
            'it), its analog supply VREG_AVDD through 33R / 4.7 uF.  One 100 nF at every supply pin, drawn at the pin it serves.\n'
            "RESET pulls RUN low.  Hold BOOTSEL while pressing RESET for the RP's USB boot ROM.  The S3 board has no RUN /\n"
            'BOOTSEL wires to this cart: it can only ask running firmware for BOOTSEL over USB.  SWD and RUN on bring-up pads.\n'
            'QSPI_SD0-3 / SCLK unused: the 2 MB flash is in the package.')
    return sh


# =========================================================================
@sheet('power')
def power(sh):
    """The power tree left to right: the console's 5 V comes in from the edge (left) through the
    AO3401A onto the +5V line; the RP2354B's LDO stands above that line; the P-FET's gate is VBUS,
    on a line below it that also carries the VBUS SS34 up into +5V.  The USB-C receptacle sits
    bottom right: VBUS up and along the top with its ESD diode and decoupling, CC1 / CC2 to their
    5.1k, the D- / D+ pair with their ESD diodes out to the left, to the RP2354B on rp-core.  The
    PWR_FLAGs of the rails only passive parts drive sit together, bottom left."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    y5 = 99.06
    x0, xq = 38.1, 88.9
    # ---- the console side: CONS_5V, its bulk at the edge, the P-FET ----------------------------
    sh.rail((x0, y5), 'CONS_5V', 0)
    fit(sh, 'Q_CONS', 3, (xq, y5), {3: L_, 2: R_, 1: D_}, fields='above')
    rail_line(sh, (x0, y5), [50.8, 63.5, 76.2, xq])
    tee_cap(sh, 'C_CONS', (50.8, y5))
    tee_cap(sh, 'C_CONSHF', (63.5, y5))
    tee_tp(sh, 'TP_CONS5V', (76.2, y5))
    # ---- the +5V line: the rail symbol, the LDO riser, the bulk, the pad, the VBUS diode ---------
    s = sh.P('Q_CONS', 2)
    x_sym, x_ldo = snap(s[0] + 7.62), snap(s[0] + 20.32)
    x_cb, x_tp5, x_dv = snap(s[0] + 48.26), snap(s[0] + 58.42), snap(s[0] + 71.12)
    rail_line(sh, s, [x_sym, x_ldo, x_cb, x_tp5, x_dv])
    sh.wire((x_sym, y5), (x_sym, snap(y5 - 2.54)))
    sh.rail((x_sym, snap(y5 - 2.54)), '+5V', 0)
    tee_cap(sh, 'C_5VBULK', (x_cb, y5))
    tee_tp(sh, 'TP_5V', (x_tp5, y5))
    fit(sh, 'D_VBUS', 1, (x_dv, snap(y5 + 5.08)), {1: U_, 2: D_}, fields='right')
    sh.wire((x_dv, y5), sh.P('D_VBUS', 1))
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
    tee_tp(sh, 'TP_3V3', (xs[1], o[1]))
    sh.rail((xs[2], o[1]), '+3V3', 0)
    # ---- VBUS: the P-FET's gate down to its line; the pull-down, the pad, the SS34's anode ---------
    y_vb = snap(y5 + 25.4)
    g = sh.P('Q_CONS', 1)
    a = sh.P('D_VBUS', 2)
    x_pd, x_tv, x_vs = snap(g[0] + 15.24), snap(g[0] + 27.94), snap(g[0] + 40.64)
    sh.wire(g, (g[0], y_vb))
    rail_line(sh, (g[0], y_vb), [x_pd, x_tv, x_vs, a[0]])
    sh.wire((a[0], y_vb), a)
    tee_cap(sh, 'R_VBPD', (x_pd, y_vb))
    tee_tp(sh, 'TP_VBUS', (x_tv, y_vb), up=False)
    sh.wire((x_vs, y_vb), (x_vs, snap(y_vb - 2.54)))
    sh.rail((x_vs, snap(y_vb - 2.54)), 'VBUS', 0)
    # ---- the USB-C receptacle, bottom right ---------------------------------------------------------
    J = 'J_USB'
    x_u, y_m = snap(x_dv + 76.2), snap(y_vb + 45.72)
    d = fit(sh, J, 'A7', (x_u, y_m), {'A7': L_}, fields='abovebelow')
    d['fields'][1] = (d['body'][2] + 1.27, d['body'][3] - 1.27, 'left')
    JP = lambda n: sh.P(J, n)
    x_em = snap(x_u - 22.86)
    x_l = snap(x_em - 30.48)                           # the D+ / D- ports, out to rp-core
    # VBUS: up from the receptacle and along the top, its shunts hanging from it
    v = JP('A4')
    y_v = snap(y_m - 33.02)
    xs = [snap(x_u - 25.4), snap(x_u - 38.1), snap(x_u - 50.8)]
    sh.wire(v, (v[0], y_v))
    rail_line(sh, (v[0], y_v), xs)
    sh.rail((v[0], y_v), 'VBUS', 0)
    for key, xx in zip(('D_ESDV', 'C_VBUS', 'C_VBUSHF'), xs):
        fit(sh, key, 1, (xx, snap(y_v + 2.54)), {1: U_}, fields='right')
        sh.wire((xx, y_v), sh.P(key, 1))
        sh.gnd(sh.P(key, 2))
    # CC1 / CC2: 5.1k to GND right at the receptacle
    for pin, key in (('A5', 'R_CC1'), ('B5', 'R_CC2')):
        p = JP(pin)
        fit(sh, key, 1, (snap(p[0] - 7.62), p[1]), {1: R_}, fields='above')
        sh.wire(p, sh.P(key, 1))
        sh.rail(sh.P(key, 2), 'GND', 270)
        sh.label((snap(p[0] - 6.35), p[1]), sh.parts[D.KEY[key]].pins['1'], 'R')
    # D-: straight across from the port; its ESD diode above it
    sh.wire((x_l, y_m), JP('A7'))
    sh.hlabel(Pt(x_l, y_m, -1, 0), 'USB_DM', 'L', 'bidirectional')
    b7 = JP('B7')
    sh.wire(b7, (snap(b7[0] - 2.54), b7[1]), (snap(b7[0] - 2.54), y_m))
    fit(sh, 'D_ESDM', 1, (x_em, snap(y_m - 5.08)), {1: R_}, fields='above')
    sh.wire((x_em, y_m), sh.P('D_ESDM', 1))
    sh.rail(sh.P('D_ESDM', 2), 'GND', 270)
    # D+: straight across from the port to A6; its ESD diode below it
    a6 = JP('A6')
    sh.wire((x_l, a6[1]), a6)
    sh.hlabel(Pt(x_l, a6[1], -1, 0), 'USB_DP', 'L', 'bidirectional')
    b6 = JP('B6')
    sh.wire(b6, (snap(b6[0] - 2.54), b6[1]), (snap(b6[0] - 2.54), a6[1]))
    x_ep = snap(x_em + 5.08)
    fit(sh, 'D_ESDP', 1, (x_ep, snap(a6[1] + 2.54)), {1: U_}, fields='left')
    sh.wire((x_ep, a6[1]), sh.P('D_ESDP', 1))
    sh.gnd(sh.P('D_ESDP', 2))
    for n in ('A8', 'B8'):
        sh.nc(JP(n))
    sh.gnd(JP('A1'))
    sh.gnd(JP('SH'))
    # ---- PWR_FLAGs: the rails driven only through passive parts --------------------------------
    y_f = snap(y_vb + 45.72)
    for k_, net in enumerate(('GND', 'CONS_5V', '+5V', 'VBUS')):
        x = snap(x0 + 25.4 * k_)
        sh.wire((x, y_f), (snap(x + 10.16), y_f))
        sh.flag((snap(x + 10.16), y_f), net)
        sh.rail((x, y_f), net, 0)
    sh.text((x0, snap(y_f - 15.24)), 'PWR_FLAG: these rails reach their loads only through passive parts (the edge fingers, '
            'USB-C, the P-FET, the SS34).', 1.27)
    r = lambda k: D.KEY[k]
    sh.text((x0, 25.4),
            "Power tree: +5V is the OR of the console's 5 V and USB VBUS (FujiNet-NES Rev0's circuit).\n"
            "  CONS_5V  edge 15, the console's 7805, through %s AO3401A (D = CONS_5V, S = +5V, G = VBUS): fully on (~30 mV)\n"
            '           with no USB; off with VBUS present, when only its body diode is left, which never passes anything\n'
            '           back into the console.\n'
            '  VBUS     the ESP32-S3 board (fujiversal-studio2, the USB host, on its own supply), through %s SS34: with it\n'
            "           connected the cart takes nothing from the console's 7805.  %s 4.7k holds VBUS (the P-FET's gate)\n"
            "           low with no cable and against the SS34's reverse leakage.\n"
            "+5V feeds the 74HCT541 / '32 / '1G02 / '14 and %s AP2112K -> +3V3 (every RP2354B supply pin: it rises with +5V, so the\n"
            "5 V-tolerant pads are never unpowered with 5 V on them).  The cart draws ~50 mA; nothing else is on this board.\n"
            'USB-C: the RP2354B native USB to the S3 board (UFP, 5.1k Rd); ESD on D+, D- and VBUS.  %s, %s, %s and %s are\n'
            'bring-up pads.'
            % (r('Q_CONS'), r('D_VBUS'), r('R_VBPD'), r('U_LDO'), r('TP_CONS5V'), r('TP_VBUS'), r('TP_5V'),
               r('TP_3V3')), 1.27)
    return sh


# =========================================================================
ROOT_NOTES = """FujiNet for the RCA Studio II, Rev0: an RP2354B cartridge on the CDP1802 bus.

The cart serves the console's reads in software (fujinet-firmware pico/studio2): every read is one
TPA pulse, the high address byte on MA0-7 as TPA falls, the low byte a few hundred ns later.  The
edge has no write strobe, clock or reset: the console reaches the cart only through the address of
a read.  CART CS turns the console RAM off for the pages the cart claims, the 1861's raster too.

  cart-bus   the 22-pin edge, 330R into the RP2354B's GPIOs, the 74HCT541 data buffer, the CART CS
             NOR, the two ORs that gate /OE2 and CART CS with the console's power, the /DRIVE and
             /CLAIM pull-ups, PWR_OK and the ADC sense of the console 5 V, the debug UART, the LED,
             the bring-up pads
  rp-core    the RP2354B's supplies and decoupling, core regulator, crystal, SWD, RUN / BOOTSEL
  power      +5V = console 5 V (P-FET) OR USB VBUS (SS34), the RP's LDO (+3V3), the USB-C receptacle

The ESP32-S3 (the FujiNet, fujiversal-studio2) is a separate board with its own supply, joined to
this one by USB alone.

Between sheets: USB_DP / USB_DM, wired here; the rails (GND, CONS_5V, VBUS, +5V, +3V3, DVDD) by
their power symbols.

Firmware contract (tools/check_nets.py, tools/check_glue.py check this netlist against it):
fujinet-firmware pico/studio2 s2_cart.h (MA0-7 GPIO0-7, TPA 8, /MRD 9, D0-D7 GPIO16-23, /DRIVE 24,
/CLAIM 25, PWR_OK 26, LED 27, VSENSE ADC GPIO40, debug UART GPIO44 / 45); glue s2_glue_drive(),
s2_glue_cartcs(), both gated by PWR_OK: nothing is driven into a console that is off.

Status: schematic only.  The edge geometry is PROVISIONAL (tools/edge_geom.py)."""


def root(sh, sheets):
    """A block per sheet in signal-flow order, the two signals between sheets wired straight."""
    b = 'bidirectional'
    sh.block('cart-bus', 45.72, 50.8, 50.8, 60.96)
    rp = sh.block('rp-core', 127.0, 50.8, 40.64, 30.48, right=[('USB_DP', b), ('USB_DM', b)])
    pw = sh.block('power', 203.2, 50.8, 40.64, 30.48, left=[('USB_DP', b), ('USB_DM', b)])
    for n in ('USB_DP', 'USB_DM'):
        assert rp[n][1] == pw[n][1], (n, rp[n], pw[n])
        sh.wire(rp[n], pw[n])
        sh.label((snap(rp[n][0] + 2.54), rp[n][1]), n)
    sh.text((45.72, 127.0), 'the console cartridge slot (the edge) is on cart-bus;\n'
                            'the ESP32-S3 board plugs into the USB-C on power', 1.27)
    sh.text((45.72, 152.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh


DRAW['root'] = root
