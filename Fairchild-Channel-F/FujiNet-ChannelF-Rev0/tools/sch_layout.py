"""How each sheet is drawn: placement and wiring, one function per sheet, and the root.

design.py owns the circuit; these functions only say where each part sits and how its pins are
joined (sch_draw.Sheet).  Parts are addressed by their design.py key (U_RP, C_IOV1, ...), never
by reference.  A sheet without a drawing function yet is drawn as a draft (sch_draft.py: every
pin labelled) -- electrically identical.  sch_draw.Sheet.check(), gen_sch.check_hierarchy() and
gen_sch.netlist_parity() prove the drawing is exactly design.py's netlist, so a wiring slip here
fails the build.

Every sheet is wired (Sheet.wired: each net one drawn piece, labels only name wires or leave the
sheet), signals flowing left to right from the cartridge edge: edge -> translators -> RP2040 and
the RP2040's own circuit on cart-rp, out to the ESP32-S3 (fujinet) and its USB-C (usb); power on
its own sheet.
"""
import os
import design as D
import sch_draft
import gen_sch
from sch_draw import Sheet, Pt, snap

DRAW = {}
PAPER = {'cart-rp': 'A2', 'fujinet': 'A3', 'usb': 'A3', 'power': 'A3'}
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


def top_supply(sh, pin, net, cap, side, fields='above'):
    """An upward supply pin: a riser to its rail symbol, its decoupling capacitor lying sideways on
    a tee halfway up (side -1 = left, +1 = right), its ground pointing away from the riser."""
    tee = (pin[0], snap(pin[1] - 5.08))
    e = (pin[0], snap(pin[1] - 10.16))
    sh.wire(pin, tee, e)
    sh.rail(e, net, 0)
    fit(sh, cap, 1, (snap(pin[0] + side * 5.08), tee[1]), {1: (-side, 0)}, fields=fields)
    sh.wire(tee, sh.P(cap, 1))
    sh.rail(sh.P(cap, 2), 'GND', 270 if side < 0 else 90)


def lvc_fields(d):
    """A translator's reference left of its body's empty top rows, its value under its B8 corner."""
    b = d['body']
    d['fields'] = [(b[0] - 1.27, b[1] + 1.27, 'right'), (b[2] + 1.27, b[3] + 1.778, 'left')]


# =========================================================================
@sheet('cart-rp')
def cart_rp(sh):
    """The cartridge bus into the RP2040 and the RP2040's own circuit, left to right as the signals
    flow: the 22-contact edge on the left; the two SN74LVC4245A translators in a column, their A
    ports (5 V, the console) facing the edge and their B ports (3.3 V) facing the RP2040, whose left
    side takes the bus row for row -- each of the 15 bus lines, both halves of it, is a straight
    wire and not one line crosses another: D0-D7 through the data translator (its DIR from GPIO15
    on the top row, with its pull-up and scope pad), WRITE / ROMC0-4 / PHI through the control
    translator (DIR tied high: console -> RP only), /INTREQ under them through its open-drain FET
    from GPIO16, the activity LED on GPIO25.  Under the bus, the 2 MB QSPI flash wired pin for pin
    into the RP's left side with the BOOTSEL group standing on its /CS line, and the 12 MHz crystal.
    The six IOVDD along the RP's top and its core supplies along the bottom, each with its capacitor
    beside the pin; on its right GPIO17's scope pad, the unused GPIOs, SWD, the USB pair through 27R
    and RUN with its RESET steering -- out to the FujiNet half."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    J, U, UD, UC = 'J_EDGE', 'U_RP', 'U_DBUF', 'U_CBUF'
    row = lambda r: snap(50.8 + 2.54 * r)
    xU = 254.0                                     # the RP's left pin column
    xB = snap(xU - 50.8)                           # the translators' B pins
    xA = snap(xB - 30.48)                          # ... and A pins
    xJ = snap(xA - 38.1)                           # the edge's right-hand pins
    du = pin_place(sh, U, 1, D.RP_GPIO_PIN[15], (xU, row(0)), fields='abovebelow')
    for key, r in ((UD, 0), (UC, gen_sch.CTRL_ROW)):
        lvc_fields(pin_place(sh, key, 1, 2, (xB, row(r))))
    dj = pin_place(sh, J, 1, 3, (xJ, row(gen_sch.EDGE_FIRST)), fields='abovebelow')
    b = dj['body']
    dj['fields'] = [(b[0], b[1] - 6.35, 'left'), (b[0] - 1.27, b[3] - 1.27, 'right')]
    # ---- the bus: edge -> A port, B port -> GPIO, one straight wire each ---------------------------
    for key, chans in ((UD, D.DATA_CH), (UC, D.CTRL_CH)):
        for k, (cn, rn) in enumerate(chans, 1):
            a, bb = sh.P(key, D.A_PIN[k]), sh.P(key, D.B_PIN[k])
            if cn == 'CBUF_A8':                    # the control translator's spare A8: pulled low
                fit(sh, 'R_A8', 1, (snap(a[0] - 12.7), a[1]), {1: R_}, fields='below')
                sh.wire(a, sh.P('R_A8', 1))
                sh.label((snap(a[0] - 1.27), a[1]), cn, 'L')
                ground(sh, sh.P('R_A8', 2))
                sh.nc(bb)
                continue
            e, r = npin(sh, J, cn), npin(sh, U, rn, 1)
            assert e[1] == a[1] == bb[1] == r[1], (cn, e, a, bb, r)
            sh.wire(e, a)
            sh.label((snap(e[0] + 2.54), e[1]), cn)
            if rn in ('RP_WRITE', 'RP_PHI'):       # the scope pad: up off WRITE, down off PHI
                xt = snap(xB + 30.48)
                rail_line(sh, bb, [xt, r[0]])
                tee_tp(sh, 'TP_' + rn[3:], (xt, bb[1]), up=rn == 'RP_WRITE')
            else:
                sh.wire(bb, r)
            sh.label((snap(bb[0] + 2.54), bb[1]), rn)
    # ---- the data translator's DIR: GPIO15, straight across the top row, pull-up and scope pad ----
    dr, rr = sh.P(UD, 2), npin(sh, U, 'RP_DIR', 1)
    x_tp, x_pu = snap(xB + 25.4), snap(xB + 38.1)
    rail_line(sh, dr, [x_tp, x_pu, rr[0]])
    sh.label((snap(dr[0] + 2.54), dr[1]), 'RP_DIR')
    tee_tp(sh, 'TP_DIR', (x_tp, dr[1]))
    fit(sh, 'R_DIR', 2, (x_pu, snap(dr[1] - 2.54)), {2: D_}, fields='right')
    sh.wire((x_pu, dr[1]), sh.P('R_DIR', 2))
    sh.sup(sh.P('R_DIR', 1), '+3V3_RP')
    # the control translator's DIR: tied to its own VCCA (A -> B, always)
    sh.sup(sh.P(UC, 2), 'CONS_5V', 2.54)
    # ---- both translators' supplies: VCCA (console 5 V) and VCCB (the RP's 3.3 V) with their 100 nF,
    # /OE and GND to ground -------------------------------------------------------------------------
    for key, ca, cb in ((UD, 'C_DBUFA', 'C_DBUFB'), (UC, 'C_CBUFA', 'C_CBUFB')):
        top_supply(sh, sh.P(key, 1), 'CONS_5V', ca, -1)
        top_supply(sh, sh.P(key, 24), '+3V3_RP', cb, 1)
        sh.gnd(sh.P(key, 11))
        sh.gnd(sh.P(key, 22))
    # ---- /INTREQ: edge pin 5 down into the FET's drain; GPIO16 into its gate, the pull-down on a tee
    g = npin(sh, U, 'RP_INTREQ', 1)
    x_g = snap(xB + 20.32)
    fit(sh, 'Q_INT', 1, (x_g, g[1]), {1: R_, 3: U_}, fields='right')
    q = sh.placed[(D.KEY['Q_INT'], 1)]
    qb = q['body']
    q['fields'] = [(qb[0] - 1.27, qb[1] - 1.27, 'right'), (qb[0] - 1.27, qb[1] + 1.27, 'right')]
    dpin, ipin = sh.P('Q_INT', 3), npin(sh, J, 'INTREQ_N')
    assert ipin[1] < dpin[1]
    sh.wire(ipin, (dpin[0], ipin[1]), dpin)
    sh.label((snap(ipin[0] + 2.54), ipin[1]), 'INTREQ_N')
    x_pd = snap(x_g + 15.24)
    rail_line(sh, sh.P('Q_INT', 1), [x_pd, g[0]])
    sh.label((snap(g[0] - 2.54), g[1]), 'RP_INTREQ', 'L')
    fit(sh, 'R_INTPD', 1, (x_pd, snap(g[1] + 2.54)), {1: U_}, fields='right')
    sh.wire((x_pd, g[1]), sh.P('R_INTPD', 1))
    sh.gnd(sh.P('R_INTPD', 2))
    sh.gnd(sh.P('Q_INT', 2))
    # ---- the activity LED: GPIO25 -> 330R -> LED -> GND, along the foot -----------------------------
    led = npin(sh, U, 'RP_LED', 1)
    fit(sh, 'R_LED', 1, (snap(led[0] - 12.7), led[1]), {1: R_}, fields='above')
    sh.wire(led, sh.P('R_LED', 1))
    sh.label((snap(led[0] - 2.54), led[1]), 'RP_LED', 'L')
    r2 = sh.P('R_LED', 2)
    fit(sh, 'D_LED', 2, (snap(r2[0] - 10.16), led[1]), {2: R_}, fields='above')
    sh.wire(r2, sh.P('D_LED', 2))
    sh.label((snap(r2[0] - 1.27), led[1]), 'RP_LED_A', 'L')
    ground(sh, sh.P('D_LED', 1))
    # ---- GPIO17's scope pad, the spare GPIOs ----------------------------------------------------------
    p17 = npin(sh, U, 'RP_GP17', 1)
    fit(sh, 'TP_GP17', 1, (snap(p17[0] + 12.7), p17[1]), {1: L_}, fields='right')
    sh.wire(p17, sh.P('TP_GP17', 1))
    sh.label((snap(p17[0] + 2.54), p17[1]), 'RP_GP17')
    ncs(sh, U)
    # ---- the edge's supply, grounds and open contacts ---------------------------------------------------
    for pins_, net, dy in (((19, 20), 'CONS_5V', -2.54), ((1, 2), 'GND', 2.54)):
        a, c = sh.P(J, pins_[0]), sh.P(J, pins_[1])
        y = snap(a[1] + dy)
        m = (snap((a[0] + c[0]) / 2), y)
        sh.wire(a, (a[0], y), m)
        sh.wire(c, (c[0], y), m)
        sh.rail(m, net, 0)
    sh.nc(sh.P(J, 21))
    sh.nc(sh.P(J, 22))
    r = lambda k: D.KEY[k]
    sh.text((snap(xJ - 25.4), snap(row(0) - 50.8)),
            'The Fairchild Channel F Videocart edge, 22 contacts (channelf.se veswiki Pinouts): the F8 bus has NO address\n'
            'bus -- D0-D7, five ROMC lines, WRITE (one machine cycle per pulse) and PHI -- and no reset line (a console reset\n'
            'arrives as ROMC 08).  +12V (22) and NC (21) are left open.\n'
            '%s / %s SN74LVC4245A: A port on CONS_5V (TTL inputs, VIH 2.0 V; drives 5 V levels -- the F3850 data bus wants\n'
            'VIH 2.9 V, Table 7), B port on +3V3_RP (the RP2040 is not 5 V tolerant).  DIR high = A -> B = console -> cart.\n'
            '%s, data: DIR = GPIO15 (channelf_cart.h: 1 = console -> cart, 0 = cart drives D0-D7), %s holds it high through\n'
            'reset and boot against the pad pull-down.  %s, control: DIR tied high.  CONS_5V comes straight off the edge,\n'
            'ahead of the OR diode: with the console off both translators go high-Z (VCC isolation), so a USB-powered cart\n'
            'cannot back-power the console.  /INTREQ (GPIO16, never driven) is open drain through %s.'
            % (r('U_DBUF'), r('U_CBUF'), r('U_DBUF'), r('R_DIR'), r('U_CBUF'), r('Q_INT')), 1.27)
    # =================================================================================================
    # the RP2040's own circuit
    b = du['body']
    du['fields'] = [(b[2] - 12.7, b[1] - 1.778, 'left'), (b[2] + 1.27, b[3] + 1.778, 'left')]
    P = lambda n: sh.P(U, n)
    R3, DV = D.RP_RAIL, 'DVDD'
    # ---- the supply ring: every supply pin to its rail, its capacitor beside it -------------------
    for n in D.RP_IOVDD_PINS:
        supply_pin(sh, P(n), R3, 'C_IOV%d' % n)
    for n, net, cap in ((48, R3, 'C_USBV'), (43, R3, 'C_ADC'), (44, R3, 'C_VREGIN'), (45, DV, 'C_VREGOUT'),
                        (23, DV, 'C_DV23'), (50, DV, 'C_DV50')):
        supply_pin(sh, P(n), net, cap)
    sh.gnd(P(57), 2.54)                                # the exposed pad
    q = P(49)                                          # the IO rail's 10 uF bulk, top right
    xb = snap(b[2] + 35.56)
    fit(sh, 'C_IOBULK', 1, (xb, snap(q[1] - 7.62)), {1: U_}, fields='right')
    sh.sup(sh.P('C_IOBULK', 1), R3)
    sh.gnd(sh.P('C_IOBULK', 2))
    # ---- the flash, mirrored so its pins face the RP: six straight wires ----------------------------
    ss = P(56)
    x_L = ss[0]
    x_f = snap(x_L - 60.96)
    pin_place(sh, 'U_FLASH', 1, 1, (x_f, ss[1]), mirror='y', fields='abovebelow')
    fd = sh.placed[(D.KEY['U_FLASH'], 1)]
    fb = fd['body']
    fd['fields'] = [(fb[0] - 1.27, fb[1] + 1.27, 'right'), (fb[0] - 1.27, fb[3] - 1.27, 'right')]
    for n in (52, 53, 55, 54, 51):
        net = sh.parts[D.KEY[U]].pins[str(n)]
        a, c = npin(sh, 'U_FLASH', net), P(n)
        assert a[1] == c[1], (net, a, c)
        sh.wire(a, c)
        sh.label((snap(a[0] + 2.54), a[1]), net)
    supply_pin(sh, sh.P('U_FLASH', 8), R3, 'C_FLASH')
    sh.gnd(sh.P('U_FLASH', 4))
    # ---- QSPI_SS: flash /CS -- pull-up, BOOTSEL pad, BOOTSEL button, the S3's control -- RP ------------
    fc = sh.P('U_FLASH', 1)
    x_ss, x_tp, x_bs, x_ct = snap(x_L - 48.26), snap(x_L - 40.64), snap(x_L - 20.32), snap(x_L - 7.62)
    rail_line(sh, fc, [x_ss, x_tp, x_bs, x_ct, x_L])
    sh.label((snap(fc[0] + 2.54), fc[1]), 'QSPI_SS')
    fit(sh, 'R_SS', 2, (x_ss, snap(ss[1] - 2.54)), {2: D_}, fields='right')
    sh.wire((x_ss, ss[1]), sh.P('R_SS', 2))
    sh.sup(sh.P('R_SS', 1), R3)
    tee_tp(sh, 'TP_BOOTSEL', (x_tp, ss[1]))
    fit(sh, 'R_BSEL', 1, (x_bs, snap(ss[1] - 2.54)), {1: D_}, fields='right')
    sh.wire((x_bs, ss[1]), sh.P('R_BSEL', 1))
    bt = sh.P('R_BSEL', 2)
    y_b = snap(bt[1] - 5.08)
    fit(sh, 'SW_BOOTSEL', 1, (snap(x_bs - 5.08), y_b), {1: R_}, fields='above')
    sh.wire(bt, (x_bs, y_b), sh.P('SW_BOOTSEL', 1))
    sh.label((x_bs, snap(bt[1] - 1.27)), 'BOOTSEL_BTN', 'U')
    ground(sh, sh.P('SW_BOOTSEL', 2))
    fit(sh, 'R_BSELCTL', 2, (x_ct, snap(ss[1] - 2.54)), {2: D_}, fields='right')
    sh.wire((x_ct, ss[1]), sh.P('R_BSELCTL', 2))
    ct = sh.P('R_BSELCTL', 1)
    y_top = snap(ct[1] - 5.08)
    sh.wire(ct, (ct[0], y_top))
    sh.hlabel(Pt(ct[0], y_top, 0, -1), 'BOOTSEL_CTL', 'U', 'input')
    # ---- the crystal under the flash: XIN into its top, XOUT_Y out of its bottom through 1k -------------
    xi, xo = P(20), P(21)
    x_y = snap(x_L - 30.48)
    fit(sh, 'Y_RP', 1, (x_y, xi[1]), {1: U_, 3: D_, 2: L_}, fields='right')
    yd = sh.placed[(D.KEY['Y_RP'], 1)]
    yb = yd['body']
    yd['fields'] = [(yb[2] + 1.27, snap(xi[1] + 2.54), 'left'), (yb[2] + 1.27, snap(xi[1] + 5.08), 'left')]
    y3 = sh.P('Y_RP', 3)
    assert y3[1] == xo[1], (y3, xo)
    x_cx = snap(x_y - 15.24)
    sh.wire(xi, sh.P('Y_RP', 1), (x_cx, xi[1]))
    sh.label((snap(xi[0] - 2.54), xi[1]), 'XIN', 'L')
    tee_cap(sh, 'C_XIN', (x_cx, xi[1]), fields='left')
    ground(sh, sh.P('Y_RP', 2))
    x_co = snap(x_y + 5.08)
    fit(sh, 'R_XOUT', 1, (snap(x_L - 7.62), xo[1]), {1: R_}, fields='above')
    sh.wire(xo, sh.P('R_XOUT', 1))
    sh.label((snap(xo[0] - 1.27), xo[1]), 'XOUT', 'L')
    rail_line(sh, y3, [x_co, sh.P('R_XOUT', 2)[0]])
    sh.label((snap(x_co + 1.27), xo[1]), 'XOUT_Y')
    tee_cap(sh, 'C_XOUT', (x_co, xo[1]))
    ground(sh, P(19))                                  # TESTEN: low for normal operation
    # ---- the right: the USB pair through 27R to the S3, SWD to its pads -----------------------------
    x_r = snap(b[2] + 76.2)                            # the page's right-hand port column
    for n, rkey, net, inner, side in ((47, 'R_USBP', 'USB_DP', 'RP_USB_DP', 'above'),
                                      (46, 'R_USBM', 'USB_DM', 'RP_USB_DM', 'below')):
        p = P(n)
        fit(sh, rkey, 2, (snap(p[0] + 33.02), p[1]), {2: L_}, fields=side)
        sh.wire(p, sh.P(rkey, 2))
        sh.label((snap(p[0] + 2.54), p[1]), inner, 'R')
        sh.wire(sh.P(rkey, 1), (x_r, p[1]))
        sh.hlabel(Pt(x_r, p[1], 1, 0), net, 'R', 'bidirectional')
    for n, tp in ((24, 'TP_SWCLK'), (25, 'TP_SWDIO')):
        p = P(n)
        fit(sh, tp, 1, (snap(p[0] + 15.24), p[1]), {1: L_}, fields='right')
        sh.wire(p, sh.P(tp, 1))
        sh.label((snap(p[0] + 2.54), p[1]), sh.parts[D.KEY[U]].pins[str(n)], 'R')
    p = P(25)
    fit(sh, 'TP_GND', 1, (snap(p[0] + 15.24), snap(p[1] + 5.08)), {1: L_}, fields='right')
    ground(sh, sh.P('TP_GND', 1))
    # ---- RUN: pull-up, pad and the S3's RUN control on tees, then the RESET steering diode ------------
    run = P(26)
    x_pu, x_tr, x_rc = snap(run[0] + 7.62), snap(run[0] + 15.24), snap(run[0] + 22.86)
    x_d = snap(run[0] + 33.02)
    fit(sh, 'D_RST', 1, (x_d, run[1]), {1: L_, 2: R_, 3: D_}, fields='above')
    rail_line(sh, run, [x_pu, x_tr, x_rc, x_d])
    sh.label((snap(run[0] + 2.54), run[1]), 'RUN')
    fit(sh, 'R_RUN', 2, (x_pu, snap(run[1] - 2.54)), {2: D_}, fields='left')
    sh.wire((x_pu, run[1]), sh.P('R_RUN', 2))
    sh.sup(sh.P('R_RUN', 1), R3)
    tee_tp(sh, 'TP_RUN', (x_tr, run[1]), up=False)
    fit(sh, 'R_RUNCTL', 2, (x_rc, snap(run[1] - 2.54)), {2: D_}, fields='right')
    sh.wire((x_rc, run[1]), sh.P('R_RUNCTL', 2))
    rc = sh.P('R_RUNCTL', 1)
    y_rc = snap(rc[1] - 5.08)
    sh.wire(rc, (rc[0], y_rc), (x_r, y_rc))
    sh.hlabel(Pt(x_r, y_rc, 1, 0), 'RUN_CTL', 'R', 'input')
    en = sh.P('D_RST', 2)
    sh.wire(en, (x_r, run[1]))
    sh.hlabel(Pt(x_r, run[1], 1, 0), 'S3_EN', 'R', 'bidirectional')
    k = sh.P('D_RST', 3)
    fit(sh, 'SW_RESET', 1, (k[0], snap(k[1] + 7.62)), {1: U_}, fields='right')
    sh.wire(k, sh.P('SW_RESET', 1))
    sh.label((k[0], snap(k[1] + 1.27)), 'RST_BTN', 'D')
    sh.gnd(sh.P('SW_RESET', 2))
    sh.text((snap(x_f - 25.4), snap(b[3] + 45.72)),
            'Supplies (Hardware design with RP2040, 2.1): IOVDD x6, USB_VDD, ADC_AVDD and VREG_VIN on +3V3_RP, the\n'
            'AP2112K LDO; the on-chip regulator makes DVDD (1.1 V) at VREG_VOUT for both DVDD pins.  100 nF at every\n'
            'supply pin, 1 uF at VREG_VIN and at VREG_VOUT (2.1.3).  Crystal: ABM8-272-T3, 15 pF each side, 1k on XOUT\n'
            '(2.3).  Flash: W25Q16JV, 2 MB (fujichannelf.cmake), /CS pulled up (2.2).  USB: 27R at the chip (2.4); the\n'
            'S3 is the host.  RESET resets the RP2040 and the ESP32-S3 together (%s steers RST_BTN onto RUN and\n'
            "S3_EN) -- the way back to CONFIG after a booted Videocart.  Hold BOOTSEL while pressing RESET for the RP's\n"
            'USB boot ROM; the S3 does both itself: IO4 (RUN_CTL) low resets the RP, IO5 (BOOTSEL_CTL) low through that\n'
            'reset selects BOOTSEL.  First flash: SWD pads (the RP has no PC-facing USB).' % D.KEY['D_RST'], 1.27)
    return sh


# =========================================================================
@sheet('fujinet')
def fujinet(sh):
    """The ESP32-S3 and what hangs off it: the module's 3V3 decoupling above it; EN's power-on RC and
    the S3_RST button on the EN line above its left end, BOOT on IO0 left of it; the RP2040's RUN /
    BOOTSEL controls and USB pair in from the left (the cart-rp sheet); the UART out to the USB
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
    # ---- the RP2040's controls and USB, straight in from the left ------------------------------
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
            'ESP32-S3-WROOM-1-N16R8: the FujiNet (fujiversal-channelf.h pin map).\n'
            'EN: 10k / 1 uF power-on delay.  The S3_RST button, the cart RESET\n'
            '(cart-rp, through the BAT54C) and the USB bridge\'s auto-program pair\n'
            '(usb sheet) all pull it low; S3_BOOT and the same pair pull IO0.\n'
            'IO4 / IO5 drive the RP2040\'s RUN and BOOTSEL; IO19 / IO20, the\n'
            'S3\'s own USB, go to the RP\'s.\n'
            'microSD in SPI mode, 10k pull-ups on CS, DO, DAT1, DAT2 and CD.\n'
            'WS2812B-2020 on +5V: its data input (VIH 2.7 V) takes the S3\'s 3.3 V.\n'
            'The 23 spare GPIOs (right) are not connected.')
    return sh


# =========================================================================
@sheet('usb')
def usb(sh):
    """USB-C to the ESP32-S3, right to left (the receptacle on the page's right): VBUS up and along the top with its ESD diode, decoupling and the
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
    """The power tree, left to right: the console's 5V comes in on the left through its SS34 onto the
    +5V line; the RP2040's LDO hangs under the line beside that diode; the +5V bulk and the 3.3 V
    buck further right, the buck's output to its right; USB's VBUS comes in through its SS34 at the
    far right.  The PWR_FLAGs of the rails that only passive parts drive sit together, bottom left."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    y5 = 88.9
    x0 = 38.1
    # ---- the console side: CONS_5V, its HF bypass at the edge, the OR diode ----------------------
    sh.rail((x0, y5), 'CONS_5V', 0)
    x_d = 63.5
    fit(sh, 'D_CONS', 2, (x_d, y5), {2: L_, 1: R_}, fields='above')
    rail_line(sh, (x0, y5), [50.8, x_d])
    tee_cap(sh, 'C_CONSHF', (50.8, y5))
    k = sh.P('D_CONS', 1)
    # ---- the +5V line: the LDO's drop, the pad, the bulk, the buck's drop, on to USB's diode ------
    x_ldo = snap(k[0] + 7.62)
    x_tp = snap(x_ldo + 10.16)
    caps = [(snap(x_tp + 10.16 * (i + 1)), key) for i, key in enumerate(('C_BIN1', 'C_BIN2', 'C_5VBULK', 'C_BINHF'))]
    x_bk = snap(caps[-1][0] + 12.7)
    x_v = snap(x_bk + 101.6)                           # USB's SS34, by the receptacle
    x_r5 = snap(k[0] + 2.54)
    rail_line(sh, k, [x_r5, x_ldo, x_tp] + [c[0] for c in caps] + [x_bk, x_v])
    sh.wire((x_r5, y5), (x_r5, snap(y5 - 2.54)))
    sh.rail((x_r5, snap(y5 - 2.54)), '+5V', 0)
    tee_tp(sh, 'TP_5V', (x_tp, y5), fields='right')
    for xx, key in caps:
        tee_cap(sh, key, (xx, y5))
    # ---- the RP2040's LDO, under the line by the console diode: +5V down into VIN and EN ----------
    d = fit(sh, 'U_LDO', '1', (snap(x_ldo + 5.08), snap(y5 + 22.86)), {'1': L_, '5': R_}, fields='below')
    d['fields'] = [(d['body'][0], d['body'][1] - 1.778, 'left'), (d['body'][0] - 1.27, d['body'][3] + 1.778, 'right')]
    vin, en = sh.P('U_LDO', 1), sh.P('U_LDO', 3)
    t = (x_ldo, snap(y5 + 10.16))
    sh.wire((x_ldo, y5), t, (x_ldo, vin[1]), (x_ldo, en[1]), en)
    sh.wire((x_ldo, vin[1]), vin)
    sh.wire(t, (snap(x_ldo - 7.62), t[1]))
    tee_cap(sh, 'C_LDOIN', (snap(x_ldo - 7.62), t[1]), fields='left')
    sh.nc(sh.P('U_LDO', 4))
    sh.gnd(sh.P('U_LDO', 2))
    o = sh.P('U_LDO', 5)
    xs = [snap(o[0] + 7.62), snap(o[0] + 17.78), snap(o[0] + 27.94)]
    rail_line(sh, o, xs)
    tee_cap(sh, 'C_LDOOUT', (xs[0], o[1]))
    tee_tp(sh, 'TP_3V3RP', (xs[1], o[1]), fields='right', up=False)
    sh.wire((xs[2], o[1]), (xs[2], snap(o[1] - 2.54)))
    sh.rail((xs[2], snap(o[1] - 2.54)), '+3V3_RP', 0)
    # ---- the 3.3 V buck, under the line: +5V down into IN and EN; SW / BST / FB on its right ------
    d = fit(sh, 'U_BUCK', '3', (snap(x_bk + 5.08), snap(y5 + 17.78)), {'3': L_, '5': R_, '4': D_}, fields='below')
    d['fields'] = [(d['body'][0], d['body'][1] - 1.778, 'left'), (d['body'][0] - 1.27, d['body'][3] + 1.778, 'right')]
    vin, en = sh.P('U_BUCK', 3), sh.P('U_BUCK', 2)
    sh.wire((x_bk, y5), (x_bk, vin[1]), (x_bk, en[1]), en)
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
    sh.sup(fb, '+3V3', 2.54, rot=270)                  # FB senses the output
    fit(sh, 'L_BUCK', 1, (snap(x_c + 7.62), y_top), {1: L_}, fields='above')
    sh.wire(sh.P('C_BST', 1), sh.P('L_BUCK', 1))
    o = sh.P('L_BUCK', 2)
    xs = [snap(o[0] + 7.62), snap(o[0] + 17.78), snap(o[0] + 27.94), snap(o[0] + 38.1)]
    rail_line(sh, o, xs)
    tee_cap(sh, 'C_BOUT1', (xs[0], y_top))
    tee_cap(sh, 'C_BOUT2', (xs[1], y_top))
    tee_tp(sh, 'TP_3V3', (xs[2], y_top), fields='right', up=False)
    sh.wire((xs[3], y_top), (xs[3], snap(y_top - 2.54)))
    sh.rail((xs[3], snap(y_top - 2.54)), '+3V3', 0)
    # ---- USB: VBUS through its SS34 up onto the line, at the far right ---------------------------
    yd = snap(y5 + 33.02)
    fit(sh, 'D_VBUS', 1, (x_v, snap(yd - 7.62)), {1: U_, 2: D_}, fields='right')
    sh.wire((x_v, y5), sh.P('D_VBUS', 1))
    a = sh.P('D_VBUS', 2)
    sh.wire(a, (a[0], yd), (snap(a[0] + 15.24), yd))
    sh.rail((snap(a[0] + 15.24), yd), 'VBUS', 0)
    # ---- PWR_FLAGs: the rails driven only through passive parts --------------------------------
    for k_, net in enumerate(('GND', 'CONS_5V', '+5V', 'VBUS', '+3V3')):
        x = snap(x0 + 25.4 * k_)
        y = 175.26
        sh.wire((x, y), (snap(x + 10.16), y))
        sh.flag((snap(x + 10.16), y), net)
        sh.rail((x, y), net, 0)
    sh.text((x0, 160.02), "PWR_FLAG: these rails reach their loads only through passive parts (the edge pins, "
            "USB-C, the SS34s, the buck's inductor).", 1.27)
    r = lambda k: D.KEY[k]
    sh.text((x0, 30.48),
            'Power tree: +5V is the OR of two sources, so neither can back-feed the other.\n'
            "  CONS_5V  edge pins 19 / 20, the console's +5V, through %s SS34.\n"
            '  VBUS     USB-C, through %s SS34.\n'
            "SS34 VF ~0.35 V at the cart's ~0.4 A: +5V is 4.4-4.9 V.  The only 5 V logic is the two SN74LVC4245A A ports\n"
            '(cart-rp sheet), and they take CONS_5V itself, ahead of the diode: off with the console, so the translators\n'
            'isolate the bus whenever the console is off.\n'
            '%s AP2112K-3.3 LDO -> +3V3_RP: the RP2040 (IOVDD, USB_VDD, ADC_AVDD, VREG_VIN), its flash and both\n'
            "translators' B ports; in dropout it follows +5V up as the console rail rises.\n"
            '%s AP63203 3.3 V / 2 A buck -> +3V3: ESP32-S3 (WiFi bursts ~400 mA), CP2102N, microSD; it waits for UVLO,\n'
            'then soft-starts over 4 ms.  %s, %s and %s are bring-up test points.  Console +5V headroom under WiFi\n'
            'bursts is unmeasured: power the cart from USB-C if the console rail sags (bring-up checklist, README).'
            % (r('D_CONS'), r('D_VBUS'), r('U_LDO'), r('U_BUCK'), r('TP_5V'), r('TP_3V3'), r('TP_3V3RP')), 1.27)
    return sh


# =========================================================================
ROOT_NOTES = """FujiNet for the Fairchild Channel F, Rev0: an RP2040 Videocart on the F8 bus + ESP32-S3.

Signals flow left to right, from the console's cartridge slot to the network, and
every connection between the sheets is a wire on this page:

  cart-rp    the 22-contact edge -> two SN74LVC4245A (5 V console / 3.3 V RP) -> the
             RP2040 (one symbol): D0-D7, ROMC0-4, WRITE, PHI, DIR; /INTREQ's open-drain
             FET; the activity LED; scope pads on DIR, WRITE, PHI, GP17; and the RP2040's
             own circuit: supplies and decoupling, 1.1 V core regulator, 2 MB QSPI flash,
             12 MHz crystal, SWD, RUN / BOOTSEL / RESET, USB out to the S3
  fujinet    the ESP32-S3 (FujiNet, the RP's USB host), microSD, WS2812 status LED
  usb        USB-C, the CP2102N bridge and esptool's auto-program pair
  power      +5V = console 5V OR USB VBUS (SS34s), the 3.3 V buck (+3V3), the RP's
             LDO (+3V3_RP)

Rails (GND, CONS_5V, VBUS, +5V, +3V3, +3V3_RP, DVDD) join by their power symbols.

Firmware contract (tools/check_nets.py checks this netlist against it):
fujinet-firmware pico/channelf channelf_cart.h (D0-D7 GPIO0-7, ROMC0-4 GPIO8-12,
WRITE GPIO13, PHI GPIO14, DIR GPIO15, /INTREQ GPIO16), boards/pico.h (LED GPIO25),
and the ESP32-S3 pin map fujiversal-channelf.h -- the RP2040 firmware runs unchanged.

Not verifiable in CAD (bring-up checklist, README): the WRITE edge and write-data
timing (PROVISIONAL in channelf_cart.c: scope pads), console 5 V headroom under
WiFi bursts, the Videocart edge's geometry (to be measured from a real cart)."""


def root(sh, sheets):
    """The block diagram in signal-flow order: cart-rp (the edge and the RP2040) on the left, then
    the FujiNet half -- fujinet with usb under it -- on the right, power above; the nine signals
    between sheets wired without a crossing: the RP's controls and USB straight across to the S3;
    S3_EN, S3_IO0 and the UART down nested channels to the USB bridge, S3_EN tapped by the RP's
    RESET on the way."""
    b, i, o = 'bidirectional', 'input', 'output'
    sh.block('power', 30.48, 33.02, 63.5, 20.32)
    rp = sh.block('cart-rp', 30.48, 76.2, 63.5, 81.28,
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
    sh.text((30.48, 162.56), 'the console cartridge slot\n(the edge) is on cart-rp', 1.27)
    sh.text((187.96, 25.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh


DRAW['root'] = root
