"""How each sheet is drawn: placement and wiring, one function per sheet, and the root.

design.py owns the circuit; these functions only say where each part sits and how its pins are
joined (sch_draw.Sheet).  Parts are addressed by their design.py key (U_RP, C_IOV5, ...), never
by reference.  A sheet without a drawing function yet is drawn as a draft (sch_draft.py: every
pin labelled) -- electrically identical, so the board can be built from it.  sch_draw.Sheet.check(),
gen_sch.check_hierarchy() and gen_sch.netlist_parity() prove the drawing is exactly design.py's
netlist, so a wiring slip here fails the build.
"""
import os
import design as D
import sch_draft
from sch_draw import Sheet, Pt, snap

DRAW = {}
PAPER = {'cart-bus': 'A1', 'rp-core': 'A3', 'fujinet': 'A3', 'usb': 'A3', 'power': 'A3'}


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
    if os.environ.get('SCH_ALL_DRAFT'):
        return sch_draft.draft_root(syms, sheets)
    return root(Sheet('root', syms, [], 'A3'), sheets)


# =========================================================================
# helpers
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


def gate(sh, key, unit, x, y, fields='above'):
    """Place one gate unit; returns ({net: [input pins, top first]}, output pin)."""
    d = sh.place(key, x, y, unit=unit, fields=fields)
    part = D.BY_KEY[key]
    ins = {}
    for num, p in sorted(d['pins'].items(), key=lambda kv: kv[1][1]):
        if p.dx < 0:
            ins.setdefault(part.pins[num], []).append(p)
    out = next(p for p in d['pins'].values() if p.dx > 0)
    return ins, out


def tap_entry(sh, wire_pt, net, bus_x, up=True, label_at=None):
    """A bus entry off a point ON a wire the caller splits there: the 45-degree entry from
    wire_pt to the vertical bus at bus_x (wire_pt is 2.54 left or right of it)."""
    s = 1 if bus_x > wire_pt[0] else -1
    assert abs(bus_x - wire_pt[0] - s * 2.54) < 1e-6, (wire_pt, bus_x)
    dy = -2.54 if up else 2.54
    sh.entries.append(((wire_pt[0], wire_pt[1]), (s * 2.54, dy)))
    return (bus_x, snap(wire_pt[1] + dy))


# =========================================================================
A16 = ['A%d' % i for i in range(16)]
D8 = ['D%d' % i for i in range(8)]
SA = ['SA%d' % i for i in range(13, 20)]
AD_BUS = '{A[0..15] D[0..7]}'
SRAMC_BUS = '{SA[13..19] SA19_N SRAM_OE_N SRAM_WE_N}'
G = 2.54


@sheet('cart-bus')
def cart_bus(sh):
    """The cartridge bus, drawn as the board is built (the page is the board turned fingers-left):
    the edge on the left; SRAM0 straight across from it, wired pin to pin as its copper runs from
    the fingers into the ROM spot without one crossing; SRAM1 above it (board west); the
    RP2354B's GPIO unit on the right (board north), its rows level with the edge's so the control
    lines and strobes run straight across; the taps that change layers on the board -- SRAM1 and
    the RP on the console bus -- off one drawn bus, the SRAMs' bank lines and strobes off a second;
    the 74HCT glue along the bottom (board east), under the strobes that feed it."""
    sh.wired = True
    sh.crossing_budget = 75                         # the glue network and its feeds: logic depth forces them
    xJ, yA0 = 78.74, 175.26
    J = 'J_EDGE'
    dj = pin_place(sh, J, 1, [p for p, (n, _) in D.EDGE.items() if n == 'A0'][0], (xJ, yA0), fields='abovebelow')
    dj['fields'][1] = (dj['body'][0] - 2.54, dj['body'][3] - 1.27, 'right')   # the value clear of the GND pins
    row = lambda net: npin(sh, J, net)[1]
    # ---- SRAM0 in the ROM spot: straight across from the edge -------------------------------
    xS = xJ + 152.4
    pin_place(sh, 'U_SRAM0', 1, D.SRAM_PIN['A0'], (xS, yA0), fields='abovebelow')
    xb = xJ + 45.72                                    # the console bus, beside the edge
    for net in A16 + D8:
        a = npin(sh, J, net)
        e = (xb - G, a[1])
        sh.wire(a, e)
        sh.label((a[0] + 1.27, a[1]), net)
        tap_entry(sh, e, net, xb)
        if net not in ('A13', 'A14', 'A15'):
            sh.wire(e, npin(sh, 'U_SRAM0', net))
    # ---- SRAM1 above it (board west) ---------------------------------------------------------
    yS1 = snap(row('CLK') - 8 * G - 24 * G)
    pin_place(sh, 'U_SRAM1', 1, D.SRAM_PIN['A0'], (xS, yS1), fields='abovebelow')
    xs1 = xS - 12.7
    ytop = snap(yS1 - 12.7)
    s1 = [sh.entry(npin(sh, 'U_SRAM1', n), n, xs1, up=True) for n in A16[:13] + D8]
    # ---- the RP2354B GPIO unit, its rows level with the edge's ---------------------------------
    xU = snap(xS + 330.2)
    pin_place(sh, 'U_RP', 1, D.RP_GPIO_PIN[0], (xU, yA0), fields='abovebelow')
    xub = snap(xU - 50.8)
    for n in A16:
        sh.entry(npin(sh, 'U_RP', n, 1), n, xub, up=False)
    # D0-D7 through the 100R elements, inline between the bus and the RP's data pins
    for i, n in enumerate(D8):
        p = npin(sh, 'U_RP', 'RP_D%d' % i, 1)
        key, unit = ('RN_D0' if i < 4 else 'RN_D4'), i % 4 + 1
        d = pin_place(sh, key, unit, unit, (xU - 15.24, p[1]), rot=90, fields='above')
        # one ref / value per pack, in the free row above D0 (RN_D0) or below D7 (RN_D4)
        show = (i == 0) or (i == 7)
        if not show:
            d['hide_fields'] = ('Reference', 'Value')
        else:
            yf = d['body'][1] - 1.27 if i == 0 else d['body'][3] + 1.27
            d['fields'] = [(d['body'][0] - 6.35, yf, 'left'), (d['body'][0] + 0.0, yf, 'left')]
        sh.wire(sh.P(key, unit, unit), p)
        sh.label((sh.P(key, unit, unit)[0] + 1.27, p[1]), 'RP_D%d' % i)
        sh.entry(sh.P(key, 9 - unit, unit), n, xub, up=False)
    yd7 = npin(sh, 'U_RP', 'RP_D7', 1)[1]
    sh.bus((xb, row('D7') - G), (xb, ytop), (xub, ytop), (xub, yd7 + G))
    sh.bus((xs1, ytop), (xs1, max(p[1] for p in s1)))
    sh.label((xb + 1.27 + 0.0, ytop), AD_BUS)
    # control (west fingers) and strobes (east fingers): straight across, edge to RP
    for n in ('CLK', 'RESET_N', 'M1_N', 'IORQ_N', 'CE_N', 'RD_N', 'MREQ_N', 'WR_N'):
        a, b = npin(sh, J, n), npin(sh, 'U_RP', n, 1)
        assert a[1] == b[1], (n, a, b)
        sh.wire(a, b)
        sh.label((a[0] + 1.27, a[1]), n)
    # ---- the SRAM control bus: bank lines, chip selects, /OE /WE -------------------------------
    xsa = snap(xub - 20.32)
    sc = [sh.entry(npin(sh, 'U_RP', n, 1), n, xsa, up=True) for n in SA]
    for key, nets in (('U_SRAM1', SA[:6] + ['SA19_N', 'SRAM_OE_N', 'SRAM_WE_N']),
                      ('U_SRAM0', SA[:6] + ['SA19', 'SRAM_OE_N', 'SRAM_WE_N'])):
        sc += [sh.entry(npin(sh, key, n), n, xsa, up=False) for n in nets]
    glue_y0 = snap(max(p[1] for p in sc) + 12.7)       # the glue band's top
    gl = draw_glue(sh, xJ, xsa, glue_y0, row)
    sh.text((xJ - 60.96, glue_y0 + 195.58),
            'How to read this page: it is the board turned so the cartridge fingers face left (board\n'
            'south -> page left, north -> right, west -> top, east -> bottom), and every part sits where\n'
            'it is on the board.  A plain wire is a connection the copper makes on one layer: the edge\n'
            'straight into SRAM0, which stands in the classic ROM spot over the fingers (the SMS edge is\n'
            'the JEDEC 32-pin memory pinout unrolled, so not one of its 21 lines crosses another), the\n'
            'strobes straight across to the RP2354B, the glue.  The drawn buses carry what changes\n'
            'layers on the board: the console bus tapped by SRAM1 and the RP, and the SRAM control bus\n'
            '(bank lines SA13-SA19, chip selects, /OE, /WE) between the RP, the glue and both SRAMs.\n'
            'D0-D7 reach the RP through the 100R elements beside it.  /CONT and /BUSREQ end on pads.\n'
            'Bring-up pads: CE, OE, WE, PWR_OK (+ GND).  RP2350-E9 4.7k pull-downs on GAME, LOAD,\n'
            'RAM_WE, MBOX, SA19 (tools/check_nets.py asserts them).', 1.524)
    sh.bus((xsa, min(p[1] for p in sc)), (xsa, max([p[1] for p in sc] + gl)))
    sh.label((xsa, snap((min(p[1] for p in sc) + max(p[1] for p in sc)) / 2 + 1.27)), SRAMC_BUS, 'U')
    # ---- the edge's rails, unused outputs, the console inputs that end on pads -----------------
    t = [sh.P(J, n) for n in ('1', '35')]
    sh.wire(t[0], t[0].go(G), t[1].go(G), t[1])
    sh.sup(t[0].go(G), 'CONS_5V')
    g = [sh.P(J, n) for n in ('19', '20', '21')]
    sh.wire(g[0], g[0].go(G), g[2].go(G), g[2])
    sh.wire(g[1], g[1].go(G))
    sh.gnd(g[0].go(G))
    ncs(sh, J)
    for net, tp in (('CONT_N', 'TP_CONT'), ('BUSREQ_N', 'TP_BUSREQ')):
        a = npin(sh, J, net)
        pin_place(sh, tp, 1, 1, (a[0] + 15.24, a[1]), rot=270, fields='right')
        sh.wire(a, sh.P(tp, 1))
        sh.label((a[0] + 1.27, a[1]), net)
    # ---- /WAIT: the 2N7002 on the edge's /WAIT row (drain from the left, source to GND on the
    # right), its gate from GPIO34 over the top through the 4.7k pull-up's node -------------------
    w = npin(sh, J, 'WAIT_N')
    q = pin_place(sh, 'Q_WAIT', 1, 3, (w[0] + 30.48, w[1]), rot=270, mirror='y', fields='above')
    q['fields'] = [(q['body'][2] + 1.27, q['body'][1] - 2.54, 'left'), (q['body'][2] + 1.27, q['body'][1] - 0.0, 'left')]
    sh.wire(w, sh.P('Q_WAIT', 3))
    sh.label((w[0] + 1.27, w[1]), 'WAIT_N')
    sh.gnd(sh.P('Q_WAIT', 2), G, rot=90)
    gpin = sh.P('Q_WAIT', 1)
    gn = (gpin[0], snap(gpin[1] - 5.08))               # the gate node
    pin_place(sh, 'R_WAIT', 1, 2, (gn[0] - 7.62, gn[1]), rot=90, fields='above')
    if sh.P('R_WAIT', 2)[0] < sh.P('R_WAIT', 1)[0]:
        pin_place(sh, 'R_WAIT', 1, 2, (gn[0] - 7.62, gn[1]), rot=270, fields='above')
    sh.wire(gpin, gn, sh.P('R_WAIT', 2))
    sh.sup(sh.P('R_WAIT', 1), '+3V3_RP', rot=90)
    wg = npin(sh, 'U_RP', 'WAIT_GATE', 1)
    ygw = snap(ytop - 10.16)
    sh.wire(wg, (wg[0], ygw), (gn[0], ygw), gn)
    sh.label((gn[0] + 1.27, ygw), 'WAIT_GATE', 'R')
    # ---- LED and the debug UART header (board west -> page top), off the RP's top pins --------
    led = npin(sh, 'U_RP', 'RP_LED', 1)
    yl = snap(ygw - 7.62)
    pin_place(sh, 'R_LED', 1, 1, (xs1 - 20.32, yl), rot=270, fields='above')
    if sh.P('R_LED', 1)[0] < sh.P('R_LED', 2)[0]:
        pin_place(sh, 'R_LED', 1, 1, (xs1 - 20.32, yl), rot=90, fields='above')
    sh.wire(led, (led[0], yl), sh.P('R_LED', 1))
    sh.label((led[0], yl), 'RP_LED', 'L')
    pin_place(sh, 'D_LED', 1, 2, (sh.P('R_LED', 2)[0] - 15.24, yl), rot=0, fields='below')
    if sh.P('D_LED', 2)[0] < sh.P('D_LED', 1)[0]:
        pin_place(sh, 'D_LED', 1, 2, (sh.P('R_LED', 2)[0] - 15.24, yl), rot=180, fields='below')
    sh.wire(sh.P('R_LED', 2), sh.P('D_LED', 2))
    sh.label((sh.P('D_LED', 2)[0] + 1.27, yl), 'RP_LED_A')
    sh.gnd(sh.P('D_LED', 1), G, rot=270)
    dbg = [npin(sh, 'U_RP', n, 1) for n in ('DBG_TX', 'DBG_RX')]
    ydb = snap(yl - 10.16)
    pin_place(sh, 'J_DBG', 1, 1, (xs1 - 50.8, ydb), rot=0, mirror='y', fields='above')
    for k, (pt, n) in enumerate(zip(dbg, ('DBG_TX', 'DBG_RX'))):
        y = sh.P('J_DBG', k + 1)[1]
        sh.wire(pt, (pt[0], y), sh.P('J_DBG', k + 1))
        sh.label((pt[0], y), n, 'L')
    sh.gnd(sh.P('J_DBG', 3), G, rot=90)
    # ---- the SRAMs' supplies: each chip's 100 nF straight across VCC and VSS, the 10 uF beside --
    for key, cap in (('U_SRAM0', 'C_SRAM0'), ('U_SRAM1', 'C_SRAM1')):
        v, gnd = npin(sh, key, '+5V'), npin(sh, key, 'GND')
        pin_place(sh, cap, 1, 1, (v[0] + 7.62, v[1]), fields='right')
        mv, mg = (v[0] + 3.81, v[1]), (gnd[0] + 3.81, gnd[1])
        sh.wire(v, mv)
        sh.wire(mv, sh.P(cap, 1))
        sh.wire(gnd, mg)
        sh.wire(mg, sh.P(cap, 2))
        sh.sup(mv, '+5V')
        sh.gnd(mg)
    c0 = sh.P('C_SRAM0', 1)
    pin_place(sh, 'C_SRAMBULK', 1, 1, (c0[0] + 15.24, c0[1]), fields='right')
    sh.wire(c0, sh.P('C_SRAMBULK', 1))
    sh.wire(sh.P('C_SRAM0', 2), sh.P('C_SRAMBULK', 2))
    return sh


def ncs(sh, key, unit=1):
    """No-connect flags on every unused pin of a placed unit."""
    ref = D.KEY[key]
    for num, pt in sh.placed[(ref, unit)]['pins'].items():
        if sh.parts[ref].pins[num] is None:
            sh.nc(pt)


def draw_glue(sh, x_left, x_bus, y0, row):
    """The 5V glue as a wired network under the strobes that feed it, by logic depth left to right:
    the console 5V sense and the inversions; the address decode (the $8000-$9FFF load window, slot
    2 less the live mailbox arena); the window terms; the strobe stage that makes SRAM /WE and /OE
    and hands them to the SRAM control bus beside it.  /CE /RD /WR drop straight down from their
    strobe lines; A12-A15 come off the console bus run along the top of the band; the RP's mode
    bits come down from its bottom pins.  Package supplies with their 100 nF and the equations
    below.  Returns the y of every entry on the SRAM control bus."""
    xb = x_left + 45.72                                # the console bus spine
    c1, c2, c3, c4, c5, c6 = (snap(x_left + 96.52 + 55.88 * i) for i in range(6))
    ys = [snap(y0 + 48.26 + 22.86 * k) for k in range(7)]
    yA, yB, yC, yD, yE, yF, yG = ys
    bus_y = []
    rp = lambda n: npin(sh, 'U_RP', n, 1)
    # ---- the mode bits from the RP's bottom pins: each down to its own channel, then left ------
    # stacked so the left-most pin runs lowest: every corner where a line turns into its channel
    # is clear below, and the RP2350-E9 pull-down hangs straight down from it
    chan = {}
    order = sorted(('MBOX', 'GAME', 'RAM_WE', 'LOAD'), key=lambda n: -rp(n)[0])
    for k, n in enumerate(order):
        chan[n] = (rp(n), snap(y0 + 5.08 + 5.08 * k))
    chan['PWR_OK'] = (rp('PWR_OK'), None)
    # ---- A12-A15 off the console bus, run along the top of the band ---------------------------
    ya = snap(y0 + 35.56)
    sh.bus((xb, row('D7') - G), (xb, ya), (c5 - 5.08, ya))
    abus = lambda n, x: tap_entry(sh, (x, ya + G), n, x + G, up=False) if False else None

    def from_abus(n, pin, x):
        """A console address line: a 45-degree entry off the band's bus at x, straight down, then
        across into the pin."""
        sh.entries.append(((x, snap(ya + G)), (G, -G)))
        sh.wire((x, snap(ya + G)), (x, pin[1]), pin)
        sh.label((x, snap(ya + G + 1.27)), n, 'D')

    def link(a, b, jx):
        if a[1] == b[1]:
            return sh.wire(a, b)
        return sh.wire(a, (jx, a[1]), (jx, b[1]), b)

    def drop(n, pin, x):
        """A strobe dropped straight down from its line onto the pin's row, then across into it."""
        y = row(n)
        sh.wire((x, y), (x, pin[1]), pin)

    # ---- row A: console 5V sense, 22k / 100k into two Schmitt inverters -> PWR_OK ------------
    ia, oa = gate(sh, 'U_INV', 1, c1, yA)
    nx = snap(c1 - 40.64)
    pin_place(sh, 'R_VSH', 1, 2, (nx, yA - 2.54), fields='left')
    pin_place(sh, 'R_VSL', 1, 1, (nx, yA + 2.54), fields='left')
    sh.sup(sh.P('R_VSH', 1), 'CONS_5V')
    sh.gnd(sh.P('R_VSL', 2))
    sh.wire(sh.P('R_VSH', 2), (nx, yA), sh.P('R_VSL', 1))
    sh.wire((nx, yA), ia['VSENSE'][0])
    sh.label((nx + 2.54, yA), 'VSENSE')
    ib, ob = gate(sh, 'U_INV', 2, c2, yA)
    sh.wire(oa, ib['PWR_OK_N'][0])
    sh.label((oa[0] + 2.54, yA), 'PWR_OK_N')
    # ---- row B: CE = !/CE; CEP_N = !(CE & PWR_OK) ---------------------------------------------
    ic, oc = gate(sh, 'U_INV', 4, c1, yB)
    drop('CE_N', ic['CE_N'][0], c1 - 15.24)
    i8a, o8a = gate(sh, 'U_NAND2', 1, c3, yB)
    link(oc, i8a['CE'][0], c3 - 15.24)
    sh.label((oc[0] + 2.54, yB), 'CE')
    pok = (snap(c3 - 12.7), yA)
    sh.wire(ob, pok)
    link(pok, i8a['PWR_OK'][0], c3 - 12.7)
    p, _ = chan['PWR_OK']
    sh.wire(pok, (p[0], yA), p)                        # on to the RP's GPIO32
    sh.label((ob[0] + 2.54, yA), 'PWR_OK')
    # ---- row C: A15_N; WIN8 = A15 & !A14 & !A13; LOADWIN_N = !(LOAD & WIN8); WE_LOAD ----------
    i4e, o4e = gate(sh, 'U_INV', 5, c1, yC)
    from_abus('A15', i4e['A15'][0], c1 - 12.7)
    i6b, o6b = gate(sh, 'U_NORDEC', 2, c2, yC)
    sh.wire(o4e, i6b['A15_N'][0])
    from_abus('A14', i6b['A14'][0], c2 - 15.24)
    from_abus('A13', i6b['A13'][0], c2 - 12.7)
    sh.label((o4e[0] + 2.54, yC), 'A15_N')
    i8b, o8b = gate(sh, 'U_NAND2', 2, c3, yC)
    link(o6b, i8b['WIN8'][0], c3 - 17.78)
    sh.label((o6b[0] + 2.54, yC), 'WIN8')
    i5a, o5a = gate(sh, 'U_NORWE', 1, c4, yC)
    sh.wire(o8b, i5a['LOADWIN_N'][0])
    sh.label((o8b[0] + 2.54, yC), 'LOADWIN_N')
    # ---- row D: MBA_N = !(MBOX & A13 & A12); MBA; SLOT2_NM; RAMWIN_N; WE_RAM ------------------
    i7a, o7a = gate(sh, 'U_NAND3', 1, c1, yD)
    from_abus('A13', i7a['A13'][0], c1 - 17.78)
    from_abus('A12', i7a['A12'][0], c1 - 20.32)
    i4f, o4f = gate(sh, 'U_INV', 6, c2, yD)
    sh.wire(o7a, i4f['MBA_N'][0])
    sh.label((o7a[0] + 2.54, yD), 'MBA_N')
    i6c, o6c = gate(sh, 'U_NORDEC', 3, c3, yD)
    sh.wire(o4f, i6c['MBA'][0])
    sh.label((o4f[0] + 2.54, yD), 'MBA')
    from_abus('A14', i6c['A14'][0], c3 - 20.32)
    tap = (snap(c1 + 15.24), yC)                       # A15_N on down to SLOT2_NM
    gy = snap((yC + yD) / 2 + 1.27)
    sh.wire(tap, (tap[0], gy), (c3 - 15.24, gy), (c3 - 15.24, i6c['A15_N'][0][1]), i6c['A15_N'][0])
    i7b, o7b = gate(sh, 'U_NAND3', 2, c4, yD)
    sh.wire(o6c, i7b['SLOT2_NM'][0])
    sh.sup(i7b['+5V'][0], '+5V', 2.54, rot=90)
    sh.label((o6c[0] + 2.54, yD), 'SLOT2_NM')
    i5b, o5b = gate(sh, 'U_NORWE', 2, c5, yD)
    sh.wire(o7b, i5b['RAMWIN_N'][0])
    sh.label((o7b[0] + 2.54, yD), 'RAMWIN_N')
    drop('WR_N', i5b['WR_N'][0], c5 - 17.78)
    # ---- row E: SLOT2_NM_N; OE_ADDR = !A15 | SLOT2_NM ----------------------------------------
    i8c, o8c = gate(sh, 'U_NAND2', 3, c4, yE)
    s2 = i8c['SLOT2_NM']
    jx = snap(c4 - 17.78)
    sh.wire(s2[0], (jx, s2[0][1]), (jx, s2[1][1]), s2[1])
    sh.wire((jx, s2[0][1]), (jx, yD))                  # up to the SLOT2_NM line: a T on it
    i8d, o8d = gate(sh, 'U_NAND2', 4, c5, yE)
    link(o8c, i8d['SLOT2_NM_N'][0], c5 - 15.24)
    sh.label((o8c[0] + 2.54, yE), 'SLOT2_NM_N')
    from_abus('A15', i8d['A15'][0], c5 - 12.7)
    # ---- row F: RD_CEP = RD & CEP --------------------------------------------------------------
    i6a, o6a = gate(sh, 'U_NORDEC', 1, c4, yF)
    sh.gnd(i6a['GND'][0], 2.54, rot=270)
    # /RD down one trunk to both of its gates
    xr = snap(c4 - 22.86)
    sh.wire((xr, row('RD_N')), (xr, i6a['RD_N'][0][1]), i6a['RD_N'][0])
    sh.wire((xr, i5a['RD_N'][0][1]), i5a['RD_N'][0])
    # CEP_N down a trunk to the three strobe gates
    tx = snap(c4 - 25.4)
    sh.wire(o8a, (tx, yB))
    sh.label((o8a[0] + 2.54, yB), 'CEP_N')
    sh.wire((tx, yB), (tx, i6a['CEP_N'][0][1]), i6a['CEP_N'][0])
    sh.wire((tx, i5a['CEP_N'][0][1]), i5a['CEP_N'][0])
    g5 = snap((yC + yD) / 2 - 1.27)
    sh.wire((tx, g5), (c5 - 15.24, g5), (c5 - 15.24, i5b['CEP_N'][0][1]), i5b['CEP_N'][0])
    # ---- the strobe stage: SRAM /WE = NOR(WE_LOAD, WE_RAM); /OE = NAND(OE_ADDR, GAME, RD_CEP) --
    i5c, o5c = gate(sh, 'U_NORWE', 3, c6, snap((yC + yD) / 2))
    link(o5a, i5c['WE_LOAD'][0], c6 - 15.24)
    link(o5b, i5c['WE_RAM'][0], c6 - 12.7)
    sh.gnd(i5c['GND'][0], 2.54, rot=270)
    sh.label((o5a[0] + 2.54, yC), 'WE_LOAD')
    sh.label((o5b[0] + 2.54, yD), 'WE_RAM')
    i7c, o7c = gate(sh, 'U_NAND3', 3, c6, snap((yE + yF) / 2))
    link(o8d, i7c['OE_ADDR'][0], c6 - 20.32)
    link(o6a, i7c['RD_CEP'][0], c6 - 20.32)
    sh.label((o8d[0] + 2.54, yE), 'OE_ADDR')
    sh.label((o6a[0] + 2.54, yF), 'RD_CEP')
    for o, n in ((o5c, 'SRAM_WE_N'), (o7c, 'SRAM_OE_N')):
        bus_y.append(sh.entry(o, n, x_bus, up=True)[1])
    # ---- row G: the upper SRAM's chip select, next to the bus --------------------------------
    i4c, o4c = gate(sh, 'U_INV', 3, c6, yG)
    bus_y.append(sh.entry(o4c, 'SA19_N', x_bus, up=True)[1])
    a = i4c['SA19'][0]
    ys9 = snap(yG + 7.62)
    sh.wire(a, (a[0] - 5.08, a[1]), (a[0] - 5.08, ys9), (x_bus - G, ys9))
    sh.entries.append(((x_bus - G, ys9), (G, -G)))
    sh.label((a[0] - 3.81, ys9), 'SA19')
    bus_y.append(ys9 - G)
    # ---- the RP's mode bits: down from its bottom pins, along their channel, down to the gate ----
    pdkey = {'MBOX': 'R_PDMBOX', 'GAME': 'R_PDGAME', 'RAM_WE': 'R_PDRAMWE', 'LOAD': 'R_PDLOAD'}
    ypd = snap(y0 + 27.94)                             # under the channels, over the A12-A15 bus
    for n, pin, xin, side in (('MBOX', i7a['MBOX'][0], c1 - 22.86, -1), ('LOAD', i8b['LOAD'][0], c3 - 22.86, -1),
                              ('RAM_WE', i7b['RAM_WE'][0], c4 - 20.32, 1), ('GAME', i7c['GAME'][0], c6 - 17.78, 1)):
        p, cy = chan[n]
        sh.wire(p, (p[0], cy), (xin, cy), (xin, ypd), (xin, pin[1]), pin)
        sh.label((xin, cy), n, 'R')
        # the RP2350-E9 pull-down, off the line where it drops into the glue
        k = pdkey[n]
        pin_place(sh, k, 1, 1, (snap(xin + side * 5.08), ypd), rot=90 if side > 0 else 270, fields='above')
        if sh.P(k, 1)[0] * side > sh.P(k, 2)[0] * side:
            pin_place(sh, k, 1, 1, (snap(xin + side * 5.08), ypd), rot=270 if side > 0 else 90, fields='above')
        sh.wire((xin, ypd), sh.P(k, 1))
        sh.gnd(sh.P(k, 2), 0, rot=90 if side > 0 else 270)
    # SA19's pull-down off the corner of its line into the inverter
    pin_place(sh, 'R_PDSA19', 1, 1, (a[0] - 5.08, snap(ys9 + 2.54)), fields='left')
    sh.wire((a[0] - 5.08, ys9), sh.P('R_PDSA19', 1))
    sh.gnd(sh.P('R_PDSA19', 2), 2.54)
    # ---- scope pads: /CE, PWR_OK, SRAM /OE and /WE (the bring-up timing items), and a ground ----
    tpce = (c1 - 15.24, snap(row('WR_N') + 7.62))     # on /CE's drop, under the strobes
    pin_place(sh, 'TP_CE', 1, 1, (tpce[0] + 7.62, tpce[1]), rot=270, fields='right')
    sh.wire(tpce, sh.P('TP_CE', 1))
    tpp = (snap(c3 + 15.24), yA)
    pin_place(sh, 'TP_PWROK', 1, 1, (tpp[0], snap(yA - 5.08)), fields='right')
    sh.wire(tpp, sh.P('TP_PWROK', 1))
    for o, key in ((o5c, 'TP_WE'), (o7c, 'TP_OE')):
        t = (snap(o[0] + 7.62), o[1])
        pin_place(sh, key, 1, 1, (t[0], snap(o[1] - 5.08)), fields='right')
        sh.wire(t, sh.P(key, 1))
    g = (snap(o7c[0] + 15.24), snap(o7c[1] + 7.62))
    pin_place(sh, 'TP_GNDBUS', 1, 1, g, fields='right')
    sh.gnd(sh.P('TP_GNDBUS', 1))
    # ---- supplies: each package's power unit with its 100 nF ---------------------------------
    yp = snap(yG + 35.56)
    for i, (key, unit, cap) in enumerate((('U_INV', 7, 'C_INV'), ('U_NORWE', 4, 'C_NORWE'),
                                         ('U_NORDEC', 4, 'C_NORDEC'), ('U_NAND3', 4, 'C_NAND3'),
                                         ('U_NAND2', 5, 'C_NAND2'))):
        x = snap(c1 + 45.72 * i)
        sh.place(key, x, yp, unit=unit, fields='right')
        sh.sup(sh.P(key, 14), '+5V')
        sh.gnd(sh.P(key, 7))
        sh.place(cap, x + 22.86, yp)
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    sh.text((c1 + 233.68, yp - 5.08),
            "fujinet-firmware pico/sms sms_cart.h: sms_glue_oe(), sms_glue_we().  RD, WR, CE = the console's\n"
            '/RD, /WR, /CE asserted; GAME, MBOX, RAM_WE, LOAD = RP GPIO38, 35, 39, 40; PWR_OK = console +5V.\n'
            'CEP_N = !(CE & PWR_OK);   WIN8 = A15 & !A14 & !A13 (the $8000-$9FFF load window)\n'
            'MBA_N = !(MBOX & A13 & A12);   SLOT2_NM = A15 & !A14 & !(MBOX & A13 & A12)\n'
            'OE_ADDR = !A15 | SLOT2_NM;   WE_LOAD = RD & CEP & LOAD & WIN8;   WE_RAM = WR & CEP & RAM_WE & SLOT2_NM\n'
            'SRAM /WE = !(WE_LOAD | WE_RAM);   SRAM /OE = !(RD & CEP & GAME & OE_ADDR);   SRAM1 /CE = !SA19\n'
            "tools/check_glue.py evaluates this netlist against the firmware's C for every input combination.", 1.27)
    return bus_y


# =========================================================================
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


def fit(sh, key, pad, xy, want, unit=1, **kw):
    """Place a unit with pin `pad` on xy, turned (mirrored if need be) so that every pin in
    `want` ({pad: (dx, dy)}) points out that way."""
    for mirror in (None, 'x', 'y'):
        for rot in (0, 90, 180, 270):
            d = pin_place(sh, key, unit, pad, xy, rot=rot, mirror=mirror, **kw)
            if all((d['pins'][str(k)].dx, d['pins'][str(k)].dy) == v for k, v in want.items()):
                return d
    raise ValueError('%s: no orientation of %s fits %s' % (sh.stem, key, want))


L_, R_, U_, D_ = (-1, 0), (1, 0), (0, -1), (0, 1)


def ground(sh, pin, n=2.54):
    """A pin to GND: a short stub, then the symbol hanging below (sideways pins turn down)."""
    if (pin.dx, pin.dy) == (0, 1):
        return sh.gnd(pin, n)
    e = sh.stub(pin, n)
    sh.rail(e, 'GND', 0)
    return e


@sheet('rp-core')
def rp_core(sh):
    """The RP2354B's own circuit around its core unit, each side of the symbol the side of the
    package it is on the board (page = board turned fingers-left): every supply pin with its
    100 nF beside it -- the board's decoupling ring; along the top (the package's west side) the
    QSPI_SS strap, the USB pair and the core-regulator corner (VREG_LX -> 3.3 uH -> DVDD,
    VREG_AVDD through 33R); along the bottom (east) the crystal, SWD and RUN.  BOOTSEL and RESET
    sit west of the RP on the board, so top left here, with the RESET steering diode below RESET.
    RUN reaches that diode round the south (left) of the RP, as its track does; the S3's EN, the
    USB pair and the S3's RUN / BOOTSEL controls leave on the right, toward the FujiNet half."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    U = 'U_RP'
    sh.place(U, 210.82, 152.4, unit=2, fields='abovebelow')
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
    # ---- USB: the 27R pair, up over the regulator corner and right to the S3 -------------------
    xr = snap(P(60)[0] + 63.5)                         # the page's right-hand port column
    for n, rkey, net, inner, y in ((67, 'R_USBP', 'USB_DP', 'RP_USB_DP', 78.74),
                                   (66, 'R_USBM', 'USB_DM', 'RP_USB_DM', 81.28)):
        p = P(n)
        fit(sh, rkey, 2, (p[0], snap(p[1] - 15.24)), {2: D_}, fields='left' if n == 67 else 'right')
        sh.wire(p, sh.P(rkey, 2))
        sh.label((p[0], snap(p[1] - 1.27)), inner, 'U')
        b = sh.P(rkey, 1)
        sh.wire(b, (b[0], y), (xr, y))
        sh.hlabel(Pt(xr, y, 1, 0), net, 'R', 'bidirectional')
    # ---- QSPI_SS: the 10k pull-up, the BOOTSEL button through 1k, the S3's BOOTSEL control ------
    ss = P(75)
    yb, yt = 81.28, 73.66                              # the button row; the column's top
    sh.label((ss[0], snap(ss[1] - 1.27)), 'QSPI_SS', 'U')
    fit(sh, 'R_BSELCTL', 2, (snap(ss[0] + 5.08), yt), {2: L_}, fields='above')
    sh.wire(ss, (ss[0], yt), sh.P('R_BSELCTL', 2))
    e = sh.wire(sh.P('R_BSELCTL', 1), (xr, yt))
    sh.hlabel(Pt(xr, yt, 1, 0), 'BOOTSEL_CTL', 'R', 'input')
    fit(sh, 'R_BSEL', 1, (snap(ss[0] - 12.7), yb), {1: R_}, fields='above')
    sh.wire((ss[0], yb), sh.P('R_BSEL', 1))
    xs = snap(ss[0] - 5.08)                            # the pull-up, off the row
    fit(sh, 'R_SS', 2, (xs, snap(yb - 2.54)), {2: D_}, fields='left')
    sh.wire((xs, yb), sh.P('R_SS', 2))
    sh.sup(sh.P('R_SS', 1), R3)
    # ---- the buttons (top left, as on the board) and the RESET steering diode below RESET -------
    y_sw, x_run, y_top = 45.72, 88.9, 33.02
    fit(sh, 'SW_BOOTSEL', 2, (101.6, y_sw), {2: L_}, fields='above')     # pin 2 is the GND side
    gb, bb = sh.P('SW_BOOTSEL', 2), sh.P('SW_BOOTSEL', 1)
    ground(sh, gb)
    rb = sh.P('R_BSEL', 2)
    sh.wire(bb, (bb[0], rb[1]), rb)
    sh.label((snap(bb[0] + 2.54), rb[1]), 'BOOTSEL_BTN', 'R')
    fit(sh, 'SW_RESET', 2, (121.92, y_sw), {2: L_}, fields='above')
    swr = sh.P('SW_RESET', 2), sh.P('SW_RESET', 1)
    ground(sh, swr[0])
    x_d = snap(swr[1][0] + 20.32)                     # the diode a step below RESET: east of it on the board
    fit(sh, 'D_RST', 3, (snap(x_d - 5.08), snap(y_sw + 5.08)), {3: L_, 1: U_}, fields='right')
    sh.wire(swr[1], (snap(x_d - 10.16), y_sw), (snap(x_d - 10.16), snap(y_sw + 5.08)), sh.P('D_RST', 3))
    sh.label((snap(swr[1][0] + 1.27), y_sw), 'RST_BTN', 'R')
    en = sh.P('D_RST', 2)
    y_e = 60.96
    sh.wire(en, (en[0], y_e), (xr, y_e))
    sh.hlabel(Pt(xr, y_e, 1, 0), 'S3_EN', 'R', 'bidirectional')
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
    sh.label((run[0], snap(run[1] + 6.35)), 'RUN', 'U')
    sh.wire(run, (run[0], rows['RUN']), (x_run, rows['RUN']), (x_run, y_top))
    fit(sh, 'TP_RUN', 1, (x_run, rows['RUN']), {1: U_}, fields='right')
    r1 = sh.P('D_RST', 1)
    sh.wire((x_run, y_top), (r1[0], y_top), r1)
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
    sh.text((snap(x_d + 27.94), snap(y_top - 2.54)),
            'Supplies (RP2350 datasheet 6.3.7): IOVDD, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and VREG_VIN on +3V3_RP, the LDO that\n'
            'rises with the console 5V; the core regulator switches VREG_LX through 3.3 uH onto DVDD (VREG_FB senses it), its\n'
            'analog supply VREG_AVDD through 33R / 4.7 uF.  One 100 nF at every supply pin, drawn at the pin it serves.\n'
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
    the EN line above its left end; BOOT on IO0 and the WS2812 out to the left (the board's west
    edge, under the shell's pinholes); the RP2354B's RUN / BOOTSEL controls and USB pair in from the
    left; the UART out to the USB bridge on the right; the microSD east of the module, so below it
    here, its SPI lines stepping down into the socket with the pull-ups between them."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    U = 'U_S3'
    d = sh.place(U, 190.5, 127.0, fields='abovebelow')
    b = d['body']                                      # the value under the body, clear of its pins
    d['fields'][1] = (b[0] - 1.27, b[3] + 1.778, 'right')
    P = lambda n: sh.P(U, n)
    ncs(sh, U)
    x = 190.5
    y_l = P(25)[1]                                     # the LED row: the module's top-left pin
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
    y_en = snap(y_l - 22.86)
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
    # ---- the status LED: IO48 -> 330R -> WS2812C DIN, on +5V -------------------------------------
    led = P(25)
    fit(sh, 'R_WS', 1, (snap(x - 71.12), y_l), {1: R_}, fields='above')
    sh.wire(led, sh.P('R_WS', 1))
    sh.label((snap(led[0] - 2.54), y_l), 'LED_STRIP', 'L')
    d = fit(sh, 'D_WS', 3, (snap(x - 88.9), y_l), {3: R_, 4: U_}, fields='right')
    b = d['body']                                      # its long value under the data line
    d['fields'] = [(b[2] + 1.27, y_l + 3.81, 'left'), (b[2] + 1.27, y_l + 6.35, 'left')]
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
    b = d['body']
    d['fields'][1] = (b[2] + 1.27, b[3] - 1.27, 'left')
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
    sh.text((snap(x - 119.38), snap(y_b + 5.08)),
            'ESP32-S3-WROOM-1-N16R8: the FujiNet (fujiversal-sms.h pin map).\n'
            'EN: 10k / 1 uF power-on delay.  The S3_RST button, the cart RESET\n'
            '(rp-core, through the BAT54C) and the USB bridge\'s auto-program pair\n'
            '(usb sheet) all pull it low; S3_BOOT and the same pair pull IO0.\n'
            'IO4 / IO5 drive the RP2354B\'s RUN and BOOTSEL (as on the NES board);\n'
            'IO19 / IO20, the S3\'s own USB, go to the RP\'s.\n'
            'microSD in SPI mode, 10k pull-ups on CS, DO, DAT1, DAT2 and CD.\n'
            'WS2812C on +5V: its data input (VIH 2.7 V) takes the S3\'s 3.3 V.\n'
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
def tee_cap(sh, key, pt, fields='right'):
    """A capacitor hanging from a point ON a horizontal rail line (the caller splits the line
    there), its ground under it."""
    fit(sh, key, 1, (pt[0], snap(pt[1] + 2.54)), {1: U_}, fields=fields)
    sh.wire(pt, sh.P(key, 1))
    sh.gnd(sh.P(key, 2))


def tee_tp(sh, key, pt, fields='right'):
    """A bring-up pad standing on a point of a horizontal line."""
    fit(sh, key, 1, (pt[0], snap(pt[1] - 2.54)), {1: D_}, fields=fields)
    sh.wire(pt, sh.P(key, 1))


def rail_line(sh, a, xs):
    """A horizontal line from a, split at every x in xs (so tees land on wire ends)."""
    pts = [a] + [(x, a[1]) for x in xs]
    for p, q in zip(pts, pts[1:]):
        sh.wire(p, q)
    return pts[-1]


@sheet('power')
def power(sh):
    """The power tree along one +5V line, left to right as on the board (page = board turned
    fingers-left): the console's 5V comes in at the edge (left) through the AO3401A, whose gate is
    VBUS; USB's VBUS comes in at the receptacle (right) through the SS34.  Off the +5V line: the
    RP2354B's LDO above it (its +3V3_RP feeds every RP supply pin), the 3.3 V buck below it (its
    +3V3 runs back left: the S3, microSD and USB bridge), the bulk and the bring-up pads at their
    nodes.  The PWR_FLAGs of the rails that only passive parts drive sit together, bottom left."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    y5 = 139.7
    # ---- the console side: CONS_5V, its bulk at the edge, the P-FET ----------------------------
    x0, xq = 38.1, 88.9
    sh.rail((x0, y5), 'CONS_5V', 0)
    fit(sh, 'Q_CONS', 3, (xq, y5), {3: L_, 2: R_, 1: D_}, fields='above')
    rail_line(sh, (x0, y5), [50.8, 63.5, 76.2, xq])
    tee_cap(sh, 'C_CONS', (50.8, y5))
    tee_cap(sh, 'C_CONSHF', (63.5, y5))
    tee_tp(sh, 'TP_CONS5V', (76.2, y5))
    sh.sup(sh.P('Q_CONS', 1), 'VBUS', 2.54, rot=180)  # gate = VBUS: USB in turns the FET off
    # ---- the +5V line: the pad, the LDO riser, the buck drop, input and bulk caps, the SS34 -----
    s = sh.P('Q_CONS', 2)
    x_tp, x_5v, x_ldo, x_bk = 101.6, 111.76, 121.92, 233.68
    caps = ((246.38, 'C_BINHF'), (259.08, 'C_BIN2'), (271.78, 'C_BIN1'), (284.48, 'C_5VBULK'))
    x_k = 297.18
    yd = snap(y5 + 5.08)                               # the SS34 a step down: east of the P-FET on the board
    fit(sh, 'D_VBUS', 1, (x_k, yd), {1: L_}, fields='above')
    rail_line(sh, s, [x_tp, x_5v, x_ldo, x_bk] + [c[0] for c in caps] + [snap(x_k - 5.08)])
    sh.wire((snap(x_k - 5.08), y5), (snap(x_k - 5.08), yd), (x_k, yd))
    tee_tp(sh, 'TP_5V', (x_tp, y5), fields='right')
    sh.wire((x_5v, y5), (x_5v, snap(y5 - 2.54)))
    sh.rail((x_5v, snap(y5 - 2.54)), '+5V', 0)
    for xx, key in caps:
        tee_cap(sh, key, (xx, y5))
    # USB: VBUS from the receptacle, the 4.7k that holds the FET gate against the SS34's leakage
    a = sh.P('D_VBUS', 2)
    x_pd, x_v = snap(a[0] + 10.16), snap(a[0] + 22.86)
    rail_line(sh, a, [x_pd, x_v])
    tee_cap(sh, 'R_VBPD', (x_pd, yd))
    sh.rail((x_v, yd), 'VBUS', 0)
    # ---- the RP2354B's LDO, above the line: +5V up its riser into VIN and EN ---------------------
    fit(sh, 'U_LDO', '1', (snap(x_ldo + 2.54), snap(y5 - 35.56)), {'1': L_, '5': R_}, fields='above')
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
    # ---- the buck, below the line (drawn mirrored: input right, switch side left, as on the board)
    yb = snap(y5 + 38.1)
    fit(sh, 'U_BUCK', '3', (snap(x_bk - 2.54), snap(yb - 2.54)), {'3': R_, '5': L_, '4': D_}, fields='above')
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
    # ---- PWR_FLAGs: the rails driven only through passive parts --------------------------------
    for k, net in enumerate(('GND', 'CONS_5V', '+5V', 'VBUS', '+3V3')):
        x = snap(x0 + 25.4 * k)
        y = snap(y5 + 66.04)
        sh.wire((x, y), (snap(x + 10.16), y))
        sh.flag((snap(x + 10.16), y), net)
        sh.rail((x, y), net, 0)
    sh.text((x0, snap(y5 + 58.42)), 'PWR_FLAG: these rails reach their loads only through passive parts '
            "(the edge fingers, USB-C, the P-FET, the SS34, the buck's inductor).", 1.27)
    r = lambda k: D.KEY[k]
    sh.text((x0, snap(y5 - 78.74)),
            "Power tree.  CONS_5V is the console's 7805 through the edge fingers: about 480 mA peak (the S3 transmitting through the buck),\n"
            '180 mA average.  %s AO3401A (D = CONS_5V, S = +5V, G = VBUS) is fully on without USB, so the 74HCT glue sees VCC >= 4.5 V\n'
            '(a Schottky drop here would leave no margin); with USB in, its gate goes high and only its body diode conducts, so nothing\n'
            'back-feeds the console.  %s SS34 puts USB VBUS onto +5V.  It is reverse-biased whenever the console powers the cart, and its\n'
            'leakage (0.5 mA at 25 C, 20 mA at 100 C) flows into VBUS, the FET gate: %s 4.7k holds VGS at -2.8 V up to 500 uA\n'
            '(tools/audit/spice_checks.py).  +5V feeds the 5V glue and both SRAMs (cart-bus), the AP2112K LDO -> +3V3_RP (every RP2354B\n'
            'supply pin: it rises with the console rail, so the 5V-tolerant pads are never unpowered with 5V on them) and the AP63203\n'
            'buck -> +3V3 (ESP32-S3, microSD, CP2102N).  %s, %s, %s, %s and the rp-core DVDD pad are bring-up test points.'
            % (r('Q_CONS'), r('D_VBUS'), r('R_VBPD'), r('TP_CONS5V'), r('TP_5V'), r('TP_3V3'), r('TP_3V3RP')), 1.27)
    return sh



# =========================================================================
ROOT_NOTES = """FujiNet for the Sega Master System / SMS2, Rev0 v2: RP2354B on the cart bus + ESP32-S3.

This page is the board seen from its component side, turned so that the edge fingers face left
(board south -> page left, north -> right, west -> top, east -> bottom), 2:1, each sheet's block
where its circuit sits.  Every sheet is drawn the same way: its parts where they are on the board,
every connection on it a wire, signals flowing left to right from the console to the USB-C.

  cart-bus   the 50-pin edge, the 1 MB SRAM (512K in the ROM spot, 512K beside it), the 74HCT
             glue, the RP2354B's 48 GPIOs, /WAIT, the bring-up pads
  rp-core    the RP2354B's supplies and decoupling ring, core regulator, crystal, SWD, RUN /
             BOOTSEL, USB to the S3
  fujinet    the ESP32-S3 (FujiNet), microSD, WS2812 status LED, S3 EN / BOOT
  usb        USB-C, the CP2102N bridge and esptool's auto-program pair
  power      CONS_5V / VBUS OR onto +5V, the 3.3 V buck (+3V3), the RP's LDO (+3V3_RP)

Between sheets: the nine signals wired here; the rails (GND, CONS_5V, VBUS, +5V, +3V3,
+3V3_RP, DVDD) by their power symbols.

The co-design (docs/floorplan-study.md): the SMS edge is the JEDEC 32-pin memory pinout unrolled,
so SRAM0 stands upright in the classic ROM spot and takes A0-A12, D0-D7 and GND from the fingers
without a crossing (its fan-in is drawn by tools/gen_pcb.py and locked before routing).

Stack-up: 1.6 mm, 6 layers.  F.Cu every part, even fingers, signals + GND pour | In1 GND plane |
In2, In3 signals | In4 power: +3V3 north, a +5V island south and east, +3V3_RP under the RP2354B
ring, DVDD under its core | B.Cu odd fingers, signals + GND pour.

Firmware contract (tools/check_nets.py, tools/check_glue.py check this netlist against it):
RP2354B pin map fujinet-firmware pico/sms sms_cart.h (A0-A15 GPIO0-15, D0-D7 GPIO16-23, strobes
GPIO24-31); glue equations sms_glue_oe() / sms_glue_we(); ESP32-S3 pin map fujiversal-sms.h."""


def root(sh, sheets):
    """The board outline turned fingers-left at 2:1 (tools/gen_pcb.OUTLINE), a block per sheet at
    its region, the nine signals between rp-core, fujinet and usb wired without a crossing: the
    RP's controls and USB straight across to the S3; S3_EN, S3_IO0 and the UART down nested
    channels to the USB bridge, S3_EN tapped by the RP's RESET on the way."""
    import gen_pcb as GP
    px, py = 25.4, 25.4
    tf = lambda bx, by: (px + 2 * (GP.Y1 - by), py + 2 * (bx - GP.X0))
    pts = [tf(*p) for p in GP.OUTLINE]
    sh.poly(pts + pts[:1])
    b, i, o = 'bidirectional', 'input', 'output'
    sh.block('cart-bus', 63.5, 71.12, 53.34, 119.38)
    sh.block('power', 124.46, 180.34, 35.56, 33.02)
    rp = sh.block('rp-core', 124.46, 50.8, 35.56, 116.84,
                  right=[None, None, ('BOOTSEL_CTL', i), ('USB_DP', b), ('USB_DM', b), ('RUN_CTL', i)]
                  + [None] * 12 + [('S3_EN', b)])
    fj = sh.block('fujinet', 177.8, 30.48, 27.94, 88.9,
                  left=[None] * 10 + [('BOOTSEL_CTL', o), ('USB_DP', b), ('USB_DM', b), ('RUN_CTL', o)]
                  + [None] * 4 + [('S3_EN', b), ('S3_IO0', b), ('S3_TXD', o), ('S3_RXD', i)])
    us = sh.block('usb', 177.8, 160.02, 27.94, 53.34,
                  left=[('S3_RXD', o), ('S3_TXD', i), ('S3_IO0', b), ('S3_EN', b)])
    for n in ('BOOTSEL_CTL', 'USB_DP', 'USB_DM', 'RUN_CTL'):
        sh.wire(rp[n], fj[n])
        sh.label((snap(rp[n][0] + 1.27), rp[n][1]), n)
    for k, n in enumerate(('S3_EN', 'S3_IO0', 'S3_TXD', 'S3_RXD')):
        xc = snap(fj[n][0] - 10.16 + 2.54 * k)
        sh.wire(fj[n], (xc, fj[n][1]), (xc, us[n][1]), us[n])
        sh.label((xc, snap(us[n][1] - 1.27)), n, 'U')
    sh.wire(rp['S3_EN'], (snap(fj['S3_EN'][0] - 10.16), rp['S3_EN'][1]))
    sh.text((snap(px + 2.54), 121.92), 'edge\nfingers:\nthe\nconsole\nslot', 1.27)
    sh.text((233.68, 25.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh
