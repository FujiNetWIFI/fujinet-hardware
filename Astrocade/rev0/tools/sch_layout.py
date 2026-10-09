"""How each sheet is drawn: placement and wiring, one function per sheet, and the root.

design.py owns the circuit; these functions only say where each part sits and how its pins are
joined (sch_draw.Sheet).  Parts are addressed by their design.py key (U_RP, C_IOV1, ...), never
by reference.  A sheet without a drawing function yet is drawn as a draft (sch_draft.py: every
pin labelled) -- electrically identical, so the board can be built from it.  sch_draw.Sheet.check(),
gen_sch.check_hierarchy() and gen_sch.netlist_parity() prove the drawing is exactly design.py's
netlist, so a wiring slip here fails the build.

Every sheet is the board turned so the edge faces left (board south -> page left, north -> right,
west -> top, east -> bottom), each part where it sits on the board (tools/sch_place.py checks the
order), signals flowing left to right from the cartridge slot to the USB-C.
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


# =========================================================================
@sheet('cart-bus')
def cart_bus(sh):
    """The cartridge bus, drawn as the board is built (the page is the board turned edge-left): the
    26-land edge on the left, every console signal straight across the page into the RP2354A's GPIO
    unit, whose left side takes them in the edge symbol's order (/CCS, A0-A12, D0-D7: no buffer, no
    level shifter, the RP's 5 V-tolerant pads on the bus) -- not one line crosses another; /CCS's
    pull-up above its line; VSENSE, the console 5V divided down for GPIO26, above the RP (west of it
    on the board); the self-test and debug pads and the activity LED below it (east)."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    J, U = 'J_EDGE', 'U_RP'
    y0 = 101.6                                     # the /CCS row
    xJ, xU = 76.2, 203.2                           # the edge's pin column, the RP's left pin column
    dj = pin_place(sh, J, 1, 21, (xJ, y0), fields='abovebelow')
    dj['fields'][1] = (dj['body'][0] - 1.27, dj['body'][3] - 1.27, 'right')
    du = pin_place(sh, U, 1, D.RP_GPIO_PIN[13], (xU, y0), fields='abovebelow')
    du['fields'][0] = (du['body'][2] - 7.62, du['body'][1] - 1.778, 'left')
    du['fields'][1] = (du['body'][2] + 1.27, du['body'][3] + 1.778, 'left')
    nets = ['CCS_N'] + ['CA%d' % i for i in range(13)] + ['CD%d' % i for i in range(8)]
    for net in nets:
        e, r = npin(sh, J, net), npin(sh, U, net, 1)
        assert e[1] == r[1], (net, e, r)
        sh.wire(e, r)
        sh.label((snap(e[0] + 2.54), e[1]), net)
    # /CCS: 10k to +3V3_RP (idle high with no console), standing on its line
    xc = snap(xJ + 38.1)
    fit(sh, 'R_CCS', 2, (xc, snap(y0 - 2.54)), {2: D_}, fields='right')
    sh.wire((xc, y0), sh.P('R_CCS', 2))
    sh.sup(sh.P('R_CCS', 1), '+3V3_RP')
    # the edge's supply and grounds
    sh.sup(sh.P(J, 25), 'CONS_5V', 2.54)
    gp = sorted((sh.P(J, n) for n in (1, 13, 26)), key=lambda q: q[0])
    yg = snap(gp[0][1] + 2.54)
    for q in gp:
        sh.wire(q, (q[0], yg))
    sh.wire((gp[0][0], yg), (gp[-1][0], yg))
    sh.rail((gp[1][0], yg), 'GND', 0)
    # ---- VSENSE: CONS_5V -> 10k -> GPIO26 -> 15k -> GND, above the RP (west of it on the board) ----
    vs = npin(sh, U, 'VSENSE', 1)
    yn = snap(vs[1] - 15.24)
    x1, x2 = snap(vs[0] - 25.4), snap(vs[0] - 12.7)
    sh.wire(vs, (vs[0], yn), (x2, yn), (x1, yn))
    sh.label((vs[0], snap(vs[1] - 1.27)), 'VSENSE', 'U')
    fit(sh, 'R_VSH', 2, (x1, snap(yn - 2.54)), {2: D_}, fields='left')
    sh.wire((x1, yn), sh.P('R_VSH', 2))
    sh.sup(sh.P('R_VSH', 1), 'CONS_5V')
    fit(sh, 'R_VSL', 1, (x2, snap(yn + 2.54)), {1: U_}, fields='right')
    sh.wire((x2, yn), sh.P('R_VSL', 1))
    sh.gnd(sh.P('R_VSL', 2))
    # ---- below the RP (east on the board): SELFTEST pad, the activity LED, the debug TX pad ----------
    for net, tp, side in (('SELFTEST', 'TP_SELFTEST', 'left'), ('RP_DBG_TX', 'TP_DBGTX', 'right')):
        p = npin(sh, U, net, 1)
        fit(sh, tp, 1, (p[0], snap(p[1] + 15.24)), {1: U_}, fields=side)
        sh.wire(p, sh.P(tp, 1))
        sh.label((p[0], snap(p[1] + 1.27)), net, 'D')
    led = npin(sh, U, 'RP_LED', 1)
    fit(sh, 'R_LED', 1, (led[0], snap(led[1] + 10.16)), {1: U_}, fields='right')
    sh.wire(led, sh.P('R_LED', 1))
    sh.label((led[0], snap(led[1] + 1.27)), 'RP_LED', 'D')
    r2 = sh.P('R_LED', 2)
    fit(sh, 'D_LED', 2, (r2[0], snap(r2[1] + 12.7)), {2: U_}, fields='right')
    sh.wire(r2, sh.P('D_LED', 2))
    sh.label((r2[0], snap(r2[1] + 1.27)), 'RP_LED_A', 'D')
    sh.gnd(sh.P('D_LED', 1), 2.54)
    ncs(sh, U, 1)
    xt = snap(xJ - 12.7)
    sh.text((xt, 25.4),
            'The Bally Astrocade cassette port: 26 contact lands on the PCB underside (the console blade presses up),\n'
            "Tilton 1-26.  No buffers: the RP2354A's fault-tolerant pads take 5.5 V while IOVDD is up, and +3V3_RP (power\n"
            'sheet, an LDO) rises with the console rail.  A0-A12 = GPIO0-12, /CCS (the pre-decoded enable) = GPIO13,\n'
            'D0-D7 = GPIO14-21 (astrocade_cart.h).  The console only ever reads the cart: the firmware drives D0-D7 only\n'
            'while /CCS is low AND VSENSE is high, so a USB-powered cart never drives a dead console.\n'
            'VSENSE: CONS_5V x 0.6 (3.0 V; 3.15 V at 5.25 V).  GPIO26 is an ADC pad, not 5 V tolerant.  10k / 15k: a\n'
            '6 kOhm pull, low enough that RP2350-E9 (A2 silicon) cannot hold VSENSE high in a switched-off console.', 1.27)
    return sh


# =========================================================================
@sheet('rp-core')
def rp_core(sh):
    """The RP2354A's own circuit around its core unit, each group on the side of the symbol its parts
    take on the board (page = board turned edge-left): every supply pin with its 100 nF beside it --
    the board's decoupling ring; the 12 MHz crystal top left (south-west of the RP on the board); SWD
    to its pads on the left; the core-regulator corner (VREG_LX -> 3.3 uH -> DVDD, VREG_AVDD through
    33R) and the USB pair to the S3 on the right; under the RP (east of it on the board) the RESET
    and BOOTSEL buttons: RUN with its pull-up, the S3's RUN control and the RESET steering diode,
    QSPI_SS with its pull-up, the BOOTSEL button and the S3's BOOTSEL control.  The S3's EN, RUN /
    BOOTSEL controls and the USB pair leave on the right, toward the FujiNet half."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    U = 'U_RP'
    d = sh.place(U, 203.2, 132.08, unit=2, fields='abovebelow')
    b = d['body']
    d['fields'] = [(b[0], b[1] - 1.778, 'left'), (b[0], b[3] + 1.778, 'left')]
    P = lambda n: sh.P(U, n, 2)
    R3, DV = D.RP_RAIL, 'DVDD'
    ncs(sh, U, 2)                                      # the QSPI flash pins: the flash is in the package
    # ---- the decoupling ring: every supply pin to its rail, its cap beside it ------------------
    for n, net, cap in ((11, R3, 'C_IOV11'), (6, DV, 'C_DV6'), (1, R3, 'C_IOV1'),
                        (20, R3, 'C_IOV20'), (23, DV, 'C_DV23'), (30, R3, 'C_IOV30'),
                        (38, R3, 'C_IOV38'), (39, DV, 'C_DV39'), (44, R3, 'C_ADC'), (45, R3, 'C_IOV45'),
                        (54, R3, 'C_QSPI'), (53, R3, 'C_OTP'), (49, R3, 'C_VREGIN')):
        supply_pin(sh, P(n), net, cap)
    supply_pin(sh, P(50), DV)                          # VREG_FB senses DVDD
    supply_pin(sh, P(47), 'GND')                       # VREG_PGND
    sh.gnd(P(61), 2.54)                                # the exposed pad
    q = P(53)                                          # the IO rail's 10 uF bulk, top right
    xb = snap(q[0] + 20.32)
    fit(sh, 'C_IOBULK', 1, (xb, snap(q[1] - 12.7)), {1: U_}, fields='right')
    sh.sup(sh.P('C_IOBULK', 1), R3)
    sh.gnd(sh.P('C_IOBULK', 2))
    # ---- the crystal, top left: XIN straight up into it, XOUT through 1k, 15 pF on each side ------
    xi, xo = P(21), P(22)
    fit(sh, 'R_XOUT', 1, (xo[0], snap(xo[1] - 7.62)), {1: D_}, fields='right')
    sh.wire(xo, sh.P('R_XOUT', 1))
    sh.label((xo[0], snap(xo[1] - 1.27)), 'XOUT', 'U')
    r2 = sh.P('R_XOUT', 2)
    y_c = snap(r2[1] - 12.7)
    fit(sh, 'Y_RP', 1, (xi[0], y_c), {1: L_, 3: R_}, fields='above')
    sh.wire(xi, (xi[0], y_c))
    sh.wire(r2, (r2[0], y_c))
    sh.label((xi[0], snap(xi[1] - 1.27)), 'XIN', 'U')
    sh.label((r2[0], snap(r2[1] - 1.27)), 'XOUT_Y', 'U')
    sh.gnd(sh.P('Y_RP', 2))
    for x0, cap, side in ((snap(xi[0] - 7.62), 'C_XIN', 'left'), (snap(r2[0] + 7.62), 'C_XOUT', 'right')):
        sh.wire((xi[0] if cap == 'C_XIN' else r2[0], y_c), (x0, y_c))
        tee_cap(sh, cap, (x0, y_c), fields=side)
    # ---- SWD: out left to the bring-up pads, the GND pad under them ------------------------------
    for n, tp in ((24, 'TP_SWCLK'), (25, 'TP_SWDIO')):
        p = P(n)
        fit(sh, tp, 1, (snap(p[0] - 25.4), p[1]), {1: R_}, fields='left')
        sh.wire(p, sh.P(tp, 1))
        sh.label((snap(p[0] - 2.54), p[1]), sh.parts[D.KEY[U]].pins[str(n)], 'L')
    p = P(25)
    fit(sh, 'TP_GND', 1, (snap(p[0] - 25.4), snap(p[1] + 5.08)), {1: R_}, fields='left')
    ground(sh, sh.P('TP_GND', 1))
    # ---- the right: the USB pair through 27R to the S3, the core-regulator corner ---------------
    x_r = snap(b[2] + 50.8)                            # the page's right-hand port column
    for n, rkey, net, inner, side in ((52, 'R_USBP', 'USB_DP', 'RP_USB_DP', 'above'),
                                      (51, 'R_USBM', 'USB_DM', 'RP_USB_DM', 'below')):
        p = P(n)
        fit(sh, rkey, 2, (snap(p[0] + 27.94), p[1]), {2: L_}, fields=side)
        sh.wire(p, sh.P(rkey, 2))
        sh.label((snap(p[0] + 2.54), p[1]), inner, 'R')
        sh.wire(sh.P(rkey, 1), (x_r, p[1]))
        sh.hlabel(Pt(x_r, p[1], 1, 0), net, 'R', 'bidirectional')
    lx = P(48)                                         # VREG_LX -> 3.3 uH -> DVDD, its 4.7 uF bulk and flag
    fit(sh, 'L_RP', 2, (snap(lx[0] + 10.16), lx[1]), {2: L_}, fields='above')
    sh.wire(lx, sh.P('L_RP', 2))
    sh.label((snap(lx[0] + 1.27), lx[1]), 'RP_LX', 'R')
    o = sh.P('L_RP', 1)
    xs = [snap(o[0] + 5.08), snap(o[0] + 12.7), snap(o[0] + 17.78)]
    rail_line(sh, o, xs)
    tee_cap(sh, 'C_DVBULK', (xs[0], o[1]))
    sh.wire((xs[1], o[1]), (xs[1], snap(o[1] - 2.54)))
    sh.flag((xs[1], snap(o[1] - 2.54)), DV)
    sh.rail((xs[2], o[1]), DV, 270)
    av = P(46)                                         # VREG_AVDD <- 33R <- +3V3_RP, 4.7 uF, its flag
    xa = [snap(av[0] + 7.62), snap(av[0] + 15.24)]
    rail_line(sh, av, xa)
    sh.label((snap(av[0] + 1.27), av[1]), 'VREG_AVDD', 'R')
    tee_cap(sh, 'C_AVDD', (xa[0], av[1]))
    fit(sh, 'R_AVDD', 2, (snap(xa[1] + 5.08), av[1]), {2: L_}, fields='below')
    sh.wire((xa[1], av[1]), sh.P('R_AVDD', 2))
    sh.wire((xa[1], av[1]), (xa[1], snap(av[1] - 2.54)))
    sh.flag((xa[1], snap(av[1] - 2.54)), 'VREG_AVDD')
    sh.sup(sh.P('R_AVDD', 1), R3, 2.54, rot=270)
    # ---- under the RP: RUN, the RESET steering diode and button; QSPI_SS and BOOTSEL -------------
    run, ss = P(26), P(60)
    y_pu = snap(run[1] + 20.32)                        # RUN's pull-up, on a tee off its riser
    y_rc = snap(run[1] + 27.94)                        # the S3's RUN control
    y_run = snap(run[1] + 38.1)                        # RUN into the steering diode
    y_bs = snap(y_run + 10.16)                         # the BOOTSEL row
    y_ctl = snap(y_run + 33.02)                        # the S3's BOOTSEL control, under everything
    sh.wire(run, (run[0], y_run))
    sh.label((run[0], snap(run[1] + 1.27)), 'RUN', 'D')
    sh.wire((run[0], y_pu), (snap(run[0] + 5.08), y_pu))
    fit(sh, 'R_RUN', 2, (snap(run[0] + 5.08), snap(y_pu - 2.54)), {2: D_}, fields='right')
    sh.wire((snap(run[0] + 5.08), y_pu), sh.P('R_RUN', 2))
    sh.sup(sh.P('R_RUN', 1), R3)
    fit(sh, 'R_RUNCTL', 2, (snap(run[0] + 12.7), y_rc), {2: L_}, fields='above')
    sh.wire((run[0], y_rc), sh.P('R_RUNCTL', 2))
    sh.wire(sh.P('R_RUNCTL', 1), (x_r, y_rc))
    sh.hlabel(Pt(x_r, y_rc, 1, 0), 'RUN_CTL', 'R', 'input')
    x_d = snap(run[0] + 25.4)
    fit(sh, 'D_RST', 1, (x_d, y_run), {1: L_, 2: R_, 3: D_}, fields='above')
    x_tp6 = snap(run[0] + 10.16)
    rail_line(sh, (run[0], y_run), [x_tp6, x_d])
    tee_tp(sh, 'TP_RUN', (x_tp6, y_run), up=False)
    en = sh.P('D_RST', 2)
    sh.wire(en, (x_r, y_run))
    sh.hlabel(Pt(x_r, y_run, 1, 0), 'S3_EN', 'R', 'bidirectional')
    k = sh.P('D_RST', 3)
    fit(sh, 'SW_RESET', 1, (k[0], snap(k[1] + 7.62)), {1: U_}, fields='right')
    sh.wire(k, sh.P('SW_RESET', 1))
    sh.label((k[0], snap(k[1] + 1.27)), 'RST_BTN', 'D')
    sh.gnd(sh.P('SW_RESET', 2))
    sh.wire(ss, (ss[0], y_bs), (ss[0], y_ctl))
    sh.label((ss[0], snap(ss[1] + 1.27)), 'QSPI_SS', 'D')
    x_pu, x_tp7 = snap(ss[0] - 7.62), snap(ss[0] - 15.24)
    fit(sh, 'R_BSEL', 1, (snap(ss[0] - 22.86), y_bs), {1: R_}, fields='above')
    rail_line(sh, (ss[0], y_bs), [x_pu, x_tp7, sh.P('R_BSEL', 1)[0]])
    fit(sh, 'R_SS', 2, (x_pu, snap(y_bs - 2.54)), {2: D_}, fields='right')
    sh.wire((x_pu, y_bs), sh.P('R_SS', 2))
    sh.sup(sh.P('R_SS', 1), R3)
    tee_tp(sh, 'TP_BOOTSEL', (x_tp7, y_bs), up=False)
    bp = sh.P('R_BSEL', 2)
    fit(sh, 'SW_BOOTSEL', 1, (snap(bp[0] - 12.7), y_bs), {1: R_}, fields='above')
    sh.wire(bp, sh.P('SW_BOOTSEL', 1))
    sh.label((snap(bp[0] - 1.27), y_bs), 'BOOTSEL_BTN', 'L')
    ground(sh, sh.P('SW_BOOTSEL', 2))
    fit(sh, 'R_BSELCTL', 2, (snap(ss[0] + 12.7), y_ctl), {2: L_}, fields='above')
    sh.wire((ss[0], y_ctl), sh.P('R_BSELCTL', 2))
    sh.wire(sh.P('R_BSELCTL', 1), (x_r, y_ctl))
    sh.hlabel(Pt(x_r, y_ctl, 1, 0), 'BOOTSEL_CTL', 'R', 'input')
    sh.text((snap(b[0] - 50.8), snap(y_c - 33.02)),
            'Supplies (RP2350 datasheet 6.3.7): IOVDD, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and VREG_VIN on +3V3_RP, the\n'
            'AP2112K LDO that rises with +5V; the core regulator switches VREG_LX through 3.3 uH onto DVDD (VREG_FB\n'
            'senses it), its analog supply VREG_AVDD through 33R / 4.7 uF.  One 100 nF at every supply pin, drawn at\n'
            'the pin it serves (on the board they reach it through the In4 +3V3_RP island and DVDD pour); the\n'
            'regulator corner is the Raspberry Pi RP2350A minimal design\'s.\n'
            'RESET resets the RP2354A and the ESP32-S3 together (%s steers RST_BTN onto RUN and S3_EN).  Hold\n'
            "BOOTSEL while pressing RESET for the RP's USB boot ROM.  The S3 does both: IO4 (RUN_CTL) low resets the\n"
            'RP, IO5 (BOOTSEL_CTL) low through that reset selects BOOTSEL.  QSPI_SD0-3 / SCLK unused: the 2 MB flash\n'
            'is in the package.' % D.KEY['D_RST'], 1.27)
    return sh


# =========================================================================
@sheet('fujinet')
def fujinet(sh):
    """The ESP32-S3 and what hangs off it, where it sits on the board (page = board turned edge-left):
    the module's 3V3 decoupling above it; EN's power-on RC and the S3_RST button on the EN line above
    its left end, BOOT on IO0 left of it (the two buttons sit south-west of the module on the board);
    the RP2354A's RUN / BOOTSEL controls and USB pair in from the left; the UART out to the USB bridge
    on the right; the microSD east of the module, so below it here, its SPI lines stepping down into
    the socket with the pull-ups between them; the WS2812 east of the module and the socket, at the
    page's foot."""
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
    # ---- the RP2354A's controls and USB, straight in from the left -----------------------------
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
            'ESP32-S3-WROOM-1-N16R8: the FujiNet (fujiversal-astrocade.h pin map).\n'
            'EN: 10k / 1 uF power-on delay.  The S3_RST button, the cart RESET\n'
            '(rp-core, through the BAT54C) and the USB bridge\'s auto-program pair\n'
            '(usb sheet) all pull it low; S3_BOOT and the same pair pull IO0.\n'
            'IO4 / IO5 drive the RP2354A\'s RUN and BOOTSEL; IO19 / IO20, the\n'
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
    """The power tree, left to right as on the board (page = board turned edge-left): the console's
    5V comes in on the left through its SS34 onto the +5V line; the RP2354A's LDO hangs under the
    line beside that diode (west of the RP on the board); the +5V bulk and the 3.3 V buck further
    right, the buck's output to its right; USB's VBUS comes in through its SS34 at the far right, by
    the receptacle.  The PWR_FLAGs of the rails that only passive parts drive sit together, bottom
    left."""
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
    # ---- the RP2354A's LDO, under the line by the console diode: +5V down into VIN and EN ---------
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
    sh.text((x0, 160.02), "PWR_FLAG: these rails reach their loads only through passive parts (the edge land, "
            "USB-C, the SS34s, the buck's inductor).", 1.27)
    r = lambda k: D.KEY[k]
    sh.text((x0, 30.48),
            'Power tree: +5V is the OR of two sources, so neither can back-feed the other.\n'
            "  CONS_5V  edge land 25, the console's +5V, through %s SS34.\n"
            '  VBUS     USB-C, through %s SS34.\n'
            "SS34 VF ~0.35 V at the cart's ~0.4 A: +5V is 4.4-4.9 V; there is no 5 V logic on this board.\n"
            '%s AP2112K-3.3 LDO -> +3V3_RP: the WHOLE RP2354A (IOVDD, QSPI / USB / ADC supplies, VREG_VIN, VREG_AVDD).\n'
            'In dropout it follows +5V as the console rail rises (1 V/ms into ~21 uF = 21 mA, under its 50 mA fold-back\n'
            'limit), so the 5 V-tolerant pads are never unpowered with the console bus driving them (RP2350 datasheet:\n'
            "the FT pads take 5.5 V 'provided IOVDD is powered to 3.3 V').\n"
            '%s AP63203 3.3 V / 2 A buck -> +3V3: ESP32-S3 (WiFi bursts ~400 mA), CP2102N, microSD; it waits for UVLO,\n'
            'then soft-starts over 4 ms.  %s, %s and %s are bring-up test points.'
            % (r('D_CONS'), r('D_VBUS'), r('U_LDO'), r('U_BUCK'), r('TP_5V'), r('TP_3V3'), r('TP_3V3RP')), 1.27)
    return sh


# =========================================================================
ROOT_NOTES = """FujiNet for the Bally Astrocade, Rev0: RP2354A on the cart bus + ESP32-S3.

This page is the board seen from its component side, turned so that the edge (the 26
contact lands) faces left (board south -> page left, north -> right, west -> top, east ->
bottom), 2:1, each sheet's block where its circuit sits.  Every sheet is drawn the same
way: its parts where they are on the board, every connection on it a wire, signals
flowing left to right from the console to the USB-C.

  cart-bus   the 26-land edge straight into the RP2354A's GPIOs (no buffers: its
             5 V-tolerant pads), /CCS pull-up, the VSENSE divider, the activity LED,
             the self-test and debug pads
  rp-core    the RP2354A's supplies and decoupling ring, core regulator, crystal, SWD,
             RUN / BOOTSEL / RESET, USB to the S3
  fujinet    the ESP32-S3 (FujiNet), microSD, WS2812 status LED, S3 EN / BOOT
  usb        USB-C, the CP2102N bridge and esptool's auto-program pair
  power      +5V = console 5V OR USB VBUS (SS34s), the 3.3 V buck (+3V3), the RP's
             LDO (+3V3_RP)

Between sheets: the nine signals wired here; the rails (GND, CONS_5V, VBUS, +5V, +3V3,
+3V3_RP, DVDD) by their power symbols.

Stack-up: 1.6 mm, 6 layers.  F.Cu every part | In1 GND plane | In2, In3 signals | In4
power: +3V3, a +3V3_RP island under the RP2354A, DVDD under its core | B.Cu the contact
lands (the console blade wipes the south 16.5 mm of the underside).

Firmware contract (tools/check_nets.py checks this netlist against it): fujinet-firmware
pico/astrocade astrocade_cart.h (A0-A12 GPIO0-12, /CCS GPIO13, D0-D7 GPIO14-21) and
fujicade_rp2354.h (VSENSE GPIO26); ESP32-S3 pin map fujiversal-astrocade.h.

Not verifiable in CAD (bring-up checklist, README): the console cold start (+3V3_RP vs
CA* / CCS_N rise), /CCS-to-data timing against the Z80 read cycle, console 5 V headroom
under WiFi bursts, blade reach vs the land escape holes."""


def root(sh, sheets):
    """The board outline turned edge-left at 2:1 (tools/gen_pcb.OUTLINE), a block per sheet at its
    region, the nine signals between sheets wired without a crossing: the RP's controls and USB
    straight across to the S3; S3_EN, S3_IO0 and the UART down nested channels to the USB bridge,
    S3_EN tapped by the RP's RESET on the way."""
    import gen_pcb as GP
    px, py = 25.4, 25.4
    tf = lambda bx, by: (px + 2 * (GP.Y1 - by), py + 2 * (bx - GP.X0))
    pts = [tf(*p) for p in GP.OUTLINE]
    sh.poly(pts + pts[:1])
    b, i, o = 'bidirectional', 'input', 'output'
    sh.block('cart-bus', 30.48, 45.72, 30.48, 152.4)
    sh.block('power', 68.58, 33.02, 27.94, 25.4)
    rp = sh.block('rp-core', 68.58, 76.2, 27.94, 81.28,
                  right=[('USB_DP', b), ('USB_DM', b), ('RUN_CTL', i), ('BOOTSEL_CTL', i)] + [None] * 14 +
                  [('S3_EN', b)])
    fj = sh.block('fujinet', 111.76, 33.02, 25.4, 99.06,
                  left=[None] * 17 + [('USB_DP', b), ('USB_DM', b), ('RUN_CTL', o), ('BOOTSEL_CTL', o)]
                  + [None] * 10 + [('S3_EN', b), ('S3_IO0', b), ('S3_TXD', o), ('S3_RXD', i)])
    us = sh.block('usb', 111.76, 152.4, 25.4, 35.56,
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
    sh.text((snap(px + 1.27), 30.48), 'edge\nlands:\nthe\nconsole\nslot', 1.27)
    sh.text((172.72, 25.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh


DRAW['root'] = root
