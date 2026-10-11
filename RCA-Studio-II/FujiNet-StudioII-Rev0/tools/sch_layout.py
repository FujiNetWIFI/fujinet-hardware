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
PAPER = {'cart-bus': 'A3', 'rp-core': 'A3', 'fujinet': 'A3', 'usb': 'A3', 'power': 'A3'}
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
    with the row it feeds; D7-D0 straight across through the 74HCT541 (drawn mirrored, its Y row
    facing the edge, its A row the RP2354B's GPIO23-16: the channels reversed, A8 / Y8 = bit 0, so the
    board's '541 meets the fingers and the RP with no crossing); /MRD on its own row, rising into the '541's
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
    dj = pin_place(sh, J, 1, 1, (xE, row(ROW['D'])), fields='abovebelow')        # D7 on the top row
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
    du = pin_place(sh, U, 1, D.RP_GPIO_PIN[23], (xRP, row(ROW['D'])), fields='abovebelow')
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
            "PWR_OK: edge 15 (the console's 5 V, before the mux) through %s / %s into\n"
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
    crystal, SWD and RUN with its pull-up, the S3's RUN control and the RESET steering pair.  The USB
    pair, the S3's BOOTSEL / RUN controls and S3_EN leave on the right, to the fujinet sheet."""
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
            'Supplies (RP2350 datasheet 6.3.7): IOVDD, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and VREG_VIN on +3V3, the\n'
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
        xp = snap(a[0] + 5.08)                        # room for the +3V3_S3 text clear of the line
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
            'ESP32-S3-WROOM-1-N16R8: the FujiNet (fujiversal-studio2.h pin map), on +3V3_S3 (the buck).\n'
            'EN: 10k / 1 uF power-on delay.  The S3_RST button, the cart RESET\n'
            '(rp-core, through the BAT54C) and the USB bridge\'s auto-program pair\n'
            '(usb sheet) all pull it low; S3_BOOT and the same pair pull IO0.\n'
            'IO4 / IO5 drive the RP2354B\'s RUN and BOOTSEL (fujiversal-intv.h\'s\n'
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
    # ---- the bridge's supply: VDD and VREGIN on +3V3_S3, 4.7 uF bulk left, 100 nF right ---------
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
    """The power tree, left to right: USB's VBUS (top) and the console's 5 V (bottom) into the TPS2116
    power mux -- VBUS into VIN1 from above, with the 33k / 10k priority divider on PR1 and MODE on its own
    VBUS symbol; CONS_5V into VIN2 from below, with its bulk, bypass and pad -- and its output, +5V, out
    to the right: the RP2354B's LDO under the line, the S3's buck further right with its output, +3V3_S3,
    to its right.  The PWR_FLAGs of the rails only passive parts drive sit together, bottom left."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    M = 'U_MUX'
    x_m, y_m = 101.6, 99.06                            # VIN1's pin
    d = fit(sh, M, 3, (x_m, y_m), {3: L_, 2: R_, 1: D_}, fields='abovebelow')
    mb = d['body']
    d['fields'] = [(mb[0], mb[1] - 4.318, 'left'), (mb[0], mb[1] - 1.778, 'left')]
    P = lambda n: sh.P(M, n)
    sh.gnd(P(1))
    sh.nc(P(8))                                        # ST: not used
    # ---- VBUS: from the top line down into VIN1; the 1 uF, the pad, the priority divider ----------------
    y_v = snap(y_m - 20.32)
    v1 = P(3)
    x_r1 = snap(v1[0] - 2.54)
    x_n = snap(v1[0] - 12.7)                           # the PR1 node
    x_c1, x_tv = snap(x_n - 10.16), snap(x_n - 20.32)
    x0 = snap(x_tv - 15.24)
    sh.wire(v1, (x_r1, v1[1]), (x_r1, y_v))
    sh.rail((x0, y_v), 'VBUS', 0)
    rail_line(sh, (x0, y_v), [x_tv, x_c1, x_n, x_r1])
    tee_cap(sh, 'C_MUXV1', (x_c1, y_v))
    tee_tp(sh, 'TP_VBUS', (x_tv, y_v))
    pr = P(4)
    fit(sh, 'R_PRH', 1, (x_n, snap(y_v + 2.54)), {1: U_}, fields='right')
    sh.wire((x_n, y_v), sh.P('R_PRH', 1))
    sh.wire(sh.P('R_PRH', 2), (x_n, pr[1]), pr)
    sh.label((snap(pr[0] - 6.35), pr[1]), 'VBUS_PR', 'L')
    fit(sh, 'R_PRL', 1, (snap(x_n - 5.08), pr[1]), {1: R_}, fields='below')
    sh.wire((x_n, pr[1]), sh.P('R_PRL', 1))
    sh.rail(sh.P('R_PRL', 2), 'GND', 270)
    md = P(5)
    e = (snap(md[0] - 5.08), md[1])
    sh.wire(md, e)
    sh.rail(e, 'VBUS', 90)                             # MODE on VIN1: priority mode
    # ---- CONS_5V: from the bottom line up into VIN2; its bulk, bypass and pad -------------------------
    v2 = P(6)
    y_c = snap(y_m + 22.86)
    x_r2 = snap(v2[0] - 2.54)
    sh.wire(v2, (x_r2, v2[1]), (x_r2, y_c))
    xs = [snap(x0 + 10.16 * k) for k in range(1, 4)]
    sh.rail((x0, y_c), 'CONS_5V', 0)
    rail_line(sh, (x0, y_c), xs + [x_r2])
    tee_cap(sh, 'C_CONS', (xs[0], y_c))
    tee_cap(sh, 'C_CONSHF', (xs[1], y_c))
    tee_tp(sh, 'TP_CONS5V', (xs[2], y_c), up=False)
    # ---- +5V: the bulk, the pad, the LDO's riser, the buck's caps and its drop, along the output line -----
    o = P(2)
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
    sh.rail((xs[2], snap(lo[1] - 2.54)), '+3V3', 0)
    # ---- the S3's 3.3 V buck, under the line: +5V down into IN and EN; SW / BST / FB on its right ------
    d = fit(sh, 'U_BUCK', '3', (snap(x_bk + 5.08), snap(o[1] + 17.78)), {'3': L_, '5': R_, '4': D_}, fields='below')
    d['fields'] = [(d['body'][0], d['body'][1] - 1.778, 'left'), (d['body'][0] - 1.27, d['body'][3] + 1.778, 'right')]
    vin, en = sh.P('U_BUCK', 3), sh.P('U_BUCK', 2)
    sh.wire((x_bk, o[1]), (x_bk, vin[1]), (x_bk, en[1]), en)
    sh.wire((x_bk, vin[1]), vin)
    sh.gnd(sh.P('U_BUCK', 4))
    sw, bst, fb = sh.P('U_BUCK', 5), sh.P('U_BUCK', 6), sh.P('U_BUCK', 1)
    y_top = snap(sw[1] - 10.16)
    x_s, x_c = snap(sw[0] + 2.54), snap(sw[0] + 7.62)
    fit(sh, 'C_BST', 1, (x_c, y_top), {1: U_}, fields='right')
    sh.wire(sw, (x_s, sw[1]), (x_s, y_top), sh.P('C_BST', 1))
    sh.wire(bst, (x_c, bst[1]), sh.P('C_BST', 2))
    sh.label((x_s, snap(sw[1] - 1.27)), 'BUCK_SW', 'U')
    sh.label((snap(bst[0] + 1.27), bst[1]), 'BUCK_BST', 'R')
    sh.sup(fb, D.S3_RAIL, 2.54, rot=270)               # FB senses the output
    fit(sh, 'L_BUCK', 1, (snap(x_c + 7.62), y_top), {1: L_}, fields='above')
    sh.wire(sh.P('C_BST', 1), sh.P('L_BUCK', 1))
    bo = sh.P('L_BUCK', 2)
    xs = [snap(bo[0] + 7.62), snap(bo[0] + 17.78), snap(bo[0] + 27.94), snap(bo[0] + 38.1)]
    rail_line(sh, bo, xs)
    tee_cap(sh, 'C_BOUT1', (xs[0], y_top))
    tee_cap(sh, 'C_BOUT2', (xs[1], y_top))
    tee_tp(sh, 'TP_3V3S3', (xs[2], y_top), fields='right', up=False)
    sh.wire((xs[3], y_top), (xs[3], snap(y_top - 2.54)))
    sh.rail((xs[3], snap(y_top - 2.54)), D.S3_RAIL, 0)
    # ---- PWR_FLAGs: the rails driven only through passive parts --------------------------------
    y_f = snap(y_c + 30.48)
    for k_, net in enumerate(('GND', 'CONS_5V', 'VBUS', D.S3_RAIL)):
        x = snap(x0 + 25.4 * k_)
        sh.wire((x, y_f), (snap(x + 10.16), y_f))
        sh.flag((snap(x + 10.16), y_f), net)
        sh.rail((x, y_f), net, 0)
    sh.text((x0, snap(y_f - 12.7)), "PWR_FLAG: these rails reach their loads only through passive parts (the edge fingers, "
            "USB-C, the buck's inductor).", 1.27)
    r = lambda k: D.KEY[k]
    sh.text((x0, 25.4),
            "Power tree: +5V is the TPS2116 power mux's output (%s), USB first, the console's 5 V second.\n"
            '  VBUS     USB-C (usb sheet) -> VIN1, the priority input: MODE on VIN1, PR1 from %s 33k / %s 10k, so VBUS\n'
            "           above VREF x 4.3 (3.96-4.64 V) runs the cart and the console's 7805 supplies nothing.\n"
            "  CONS_5V  edge 15, the console's 7805 -> VIN2, whenever VBUS is absent.\n"
            '  37-60 mOhm either way: +5V sits within ~20 mV of its source, so the 74HCT glue stays inside 4.5-5.5 V\n'
            '  on either; reverse current blocking: neither source back-feeds the other.  ST is not used.\n'
            "+5V feeds the 74HCT541 / '32 / '1G02 / '14, the WS2812, %s AP2112K -> +3V3 (every RP2354B supply pin: it\n"
            'rises with +5V, so the 5 V-tolerant pads are never unpowered with 5 V on them) and %s AP63203 -> +3V3_S3\n'
            '(the ESP32-S3, the CP2102N and the microSD; WiFi bursts ~400 mA; it waits out UVLO, then soft-starts over\n'
            "4 ms).  Console 5 V headroom under WiFi bursts is unmeasured: bring-up step 2.  %s, %s, %s, %s and %s are\n"
            'bring-up pads.'
            % (r('U_MUX'), r('R_PRH'), r('R_PRL'), r('U_LDO'), r('U_BUCK'), r('TP_VBUS'), r('TP_CONS5V'),
               r('TP_5V'), r('TP_3V3'), r('TP_3V3S3')), 1.27)
    return sh


# =========================================================================
ROOT_NOTES = """FujiNet for the RCA Studio II, Rev0: an RP2354B cartridge on the CDP1802 bus + ESP32-S3.

The cart serves the console's reads in software (fujinet-firmware pico/studio2): every read is one
TPA pulse, the high address byte on MA0-7 as TPA falls, the low byte a few hundred ns later.  The
edge has no write strobe, clock or reset: the console reaches the cart only through the address of
a read.  CART CS turns the console RAM off for the pages the cart claims, the 1861's raster too.

  cart-bus   the 22-pin edge, 330R into the RP2354B's GPIOs, the 74HCT541 data buffer, the CART CS
             NOR, the two ORs that gate /OE2 and CART CS with the console's power, the /DRIVE and
             /CLAIM pull-ups, PWR_OK and the ADC sense of the console 5 V, the debug UART, the LED,
             the bring-up pads
  rp-core    the RP2354B's supplies and decoupling, core regulator, crystal, SWD, RUN / BOOTSEL /
             RESET, its USB out to the S3
  fujinet    the ESP32-S3 (the FujiNet, the RP's USB host), microSD, WS2812 status light
  usb        USB-C, the USBLC6 ESD array, the CP2102N bridge and esptool's auto-program pair
  power      +5V = the TPS2116 mux (USB VBUS first, console 5 V second), the RP's LDO (+3V3), the
             S3's buck (+3V3_S3)

Rails (GND, CONS_5V, VBUS, +5V, +3V3, +3V3_S3, DVDD) join by their power symbols.

Firmware contract (tools/check_nets.py, tools/check_glue.py check this netlist against it):
fujinet-firmware pico/studio2 s2_cart.h (MA0-7 GPIO0-7, TPA 8, /MRD 9, D0-D7 GPIO16-23, /DRIVE 24,
/CLAIM 25, PWR_OK 26, LED 27, VSENSE ADC GPIO40, debug UART GPIO44 / 45); glue s2_glue_drive(),
s2_glue_cartcs(), both gated by PWR_OK: nothing is driven into a console that is off.  The S3:
fujiversal-studio2.h (SD 38-41, UART0 43 / 44, WS2812 48, USB host 19 / 20); RUN / BOOTSEL forcing
on IO4 / IO5 (fujiversal-intv.h's pins)."""


def root(sh, sheets):
    """The block diagram in signal-flow order: cart-bus (the edge and the RP's GPIOs) and rp-core on
    the left, then the FujiNet half -- fujinet with usb under it -- on the right, power above; the
    nine signals between sheets wired without a crossing: the RP's controls and USB straight across
    to the S3; S3_EN, S3_IO0 and the UART down nested channels to the USB bridge, S3_EN tapped by
    the RP's RESET on the way."""
    b, i, o = 'bidirectional', 'input', 'output'
    sh.block('power', 30.48, 33.02, 63.5, 20.32)
    sh.block('cart-bus', 30.48, 172.72, 63.5, 20.32)
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
    sh.text((30.48, 203.2), 'the console cartridge slot (the edge) is on cart-bus', 1.27)
    sh.text((187.96, 25.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh


DRAW['root'] = root
