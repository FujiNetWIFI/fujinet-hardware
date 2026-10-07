"""How each sheet is drawn: placement and wiring, one function per sheet, and
the root's block diagram.

design.py owns the circuit; these functions only say where each part sits and
how its pins are joined (sch_draw.Sheet), left to right in signal-flow order:
the console's side on the left of every sheet, the PC / FujiNet side on the
right.  Parts are addressed by their design.py key (U_RP, C_IOV5, ...), never
by reference.  sch_draw.Sheet.check(), gen_sch.check_hierarchy() and
gen_sch.netlist_parity() prove the drawing is exactly design.py's netlist, so
a wiring slip here fails the build.
"""
import design as D
from sch_draw import Sheet, Pt, snap

DRAW = {}
A_BUS, D_BUS, SA_BUS = 'A[0..15]', 'D[0..7]', 'SA[13..19]'


class KSheet(Sheet):
    """A Sheet whose parts are addressed by design.py key (references also work)."""
    def place(self, ref, *a, **k):
        return Sheet.place(self, D.KEY.get(ref, ref), *a, **k)

    def N(self, ref, net):
        return Sheet.N(self, D.KEY.get(ref, ref), net)

    def P(self, ref, num, unit=None):
        return Sheet.P(self, D.KEY.get(ref, ref), num, unit)


def sheet(stem, paper='A3'):
    def deco(f):
        DRAW[stem] = (f, paper)
        return f
    return deco


def draw(stem, syms, parts):
    f, paper = DRAW[stem]
    sh = KSheet(stem, syms, parts, paper)
    f(sh)
    return sh


def ncs(sh, key, unit=1):
    """No-connect flags on every unused pin of a placed unit."""
    ref = D.KEY[key]
    for num, pt in sh.placed[(ref, unit)]['pins'].items():
        if sh.parts[ref].pins[num] is None:
            sh.nc(pt)


def cap_down(sh, key, x, y, net=None):
    """A capacitor hanging from (x, y) -- its pin 1 -- to a GND symbol."""
    sh.place(key, x, y + 3.81)
    sh.gnd(sh.P(key, 2))
    if net:
        sh.sup(sh.P(key, 1), net)
    return sh.P(key, 1)


# =========================================================================
@sheet('edge', 'A4')
def edge(sh):
    """The console's slot on the left; everything the console drives or reads
    leaves on the right: address and data as buses, the strobes, CLK and /RESET
    as single lines, /WAIT coming back from the RP sheet's 2N7002."""
    J = 'J_EDGE'
    sh.place(J, 60.96, 101.6, fields='abovebelow', val_at=(78.74, 156.21, 'left'))
    col = 111.76                              # the page edge every signal leaves through
    bx = 91.44                                # the bus spines
    for nets, name, shape in ((['A%d' % i for i in range(16)], A_BUS, 'output'),
                              (['D%d' % i for i in range(8)], D_BUS, 'bidirectional')):
        top, bot = sh.bus_group([(sh.N(J, n), n) for n in nets], bx)
        sh.bus(top, (col, top[1]))
        sh.hlabel(Pt(col, top[1]), name, 'R', shape)
    for net, shape in (('RD_N', 'output'), ('WR_N', 'output'), ('MREQ_N', 'output'), ('CE_N', 'output'),
                       ('IORQ_N', 'output'), ('M1_N', 'output'), ('RESET_N', 'output'), ('CLK', 'output'),
                       ('WAIT_N', 'input')):
        p = sh.N(J, net)
        sh.wire(p, (col, p[1]))
        sh.hlabel(Pt(col, p[1]), net, 'R', shape)
    # /CONT and /BUSREQ: a pad each, nothing fitted
    for net, tp in (('CONT_N', 'TP_CONT'), ('BUSREQ_N', 'TP_BUSREQ')):
        p = sh.N(J, net)
        sh.place(tp, 96.52, p[1], rot=270, fields='right')
        sh.wire(p, sh.P(tp, 1))
        sh.name((83.82, p[1]), net, 'U', 'R')
    # rails: both +5V fingers joined, the three GND fingers joined
    t = [sh.P(J, n) for n in ('1', '35')]
    sh.wire(t[0], t[0].go(2.54), t[1].go(2.54), t[1])
    sh.sup(t[0].go(2.54), 'CONS_5V')
    g = [sh.P(J, n) for n in ('19', '20', '21')]
    sh.wire(g[0], g[0].go(2.54), g[2].go(2.54), g[2])
    sh.wire(g[1], g[1].go(2.54))
    sh.gnd(g[0].go(2.54))
    ncs(sh, J)
    sh.text((25.4, 22.86), 'Sega Master System / SMS2 50-pin cartridge slot, drawn by function (finger numbers on the pins).\n'
                           'Even pins 2-50 on the component (label) side, which faces the console front; odd pins behind them;\n'
                           'pins 1/2 at the right seen from the front with the fingers down (tools/audit/edge_orientation.py).\n'
                           'Unused console outputs (left) stay open.  /CONT and /BUSREQ end on test pads only.')


# =========================================================================
@sheet('rp2354b')
def rp2354b(sh):
    """RP2354B mirrored, so its 40 bus GPIOs face the console on the left: the
    address bus, the data lines through the 100R packs, the strobes, /WAIT
    through the 2N7002, PWR_OK and the glue's mode bits.  On the right, toward
    the FujiNet half: RUN / RESET, USB to the S3, BOOTSEL, the crystal, SWD,
    LOAD and the SRAM bank lines.  Supplies across the top: the +3V3_RP rail
    with one 100 nF per IOVDD pin, the core regulator (LX -> 3.3 uH -> DVDD)."""
    U = 'U_RP'
    X, Y = 210.82, 152.4
    sh.place(U, X, Y, mirror='y', fields='left', ref_at=(X - 20.32, Y + 62.23, 'left'),
             val_at=(X - 20.32, Y + 64.77, 'left'))
    P = lambda n: sh.P(U, n)
    gp = lambda g: P(D.RP_GPIO_PIN[g])
    net = lambda g: D.RP_GPIO_NET[g]
    lcol, rcol = 139.7, 383.54               # where the nets leave the sheet
    # ---- cart side (left) ---------------------------------------------------
    # A0-A15 onto the address bus
    bx = 172.72
    top, _ = sh.bus_group([(gp(g), net(g)) for g in range(16)], bx, True)
    sh.bus(top, (lcol, top[1]))
    sh.hlabel(Pt(lcol, top[1]), A_BUS, 'L', 'input')
    # D0-D7: each GPIO straight into its 100R (the packs sit on the pin rows),
    # the console side onto the data bus
    rnx = 162.56
    pins_d = []
    for key, g0 in (('RN_D0', 16), ('RN_D4', 20)):
        y0 = gp(g0)[1]
        sh.place(key, rnx, y0 + 5.08, rot=270, mirror='y', fields='above' if g0 == 16 else 'below')
        for k in range(4):
            a = sh.P(key, k + 1)
            sh.wire(gp(g0 + k), a)
            sh.label((a[0] + 2.54, a[1]), net(g0 + k))
            pins_d.append((sh.P(key, 8 - k), 'D%d' % (g0 - 16 + k)))
    dbx = 149.86
    dtop, dbot = sh.bus_group(pins_d, dbx, True)
    sh.bus(dtop, (dbx, dtop[1] - 2.54), (lcol, dtop[1] - 2.54))
    sh.hlabel(Pt(lcol, dtop[1] - 2.54), D_BUS, 'L', 'bidirectional')
    # strobes and clock in, PWR_OK in from the glue, the glue's mode bits out
    shapes = {24: 'input', 25: 'input', 26: 'input', 27: 'input', 28: 'input', 29: 'input', 30: 'input',
              31: 'input', 32: 'input', 35: 'output', 38: 'output', 39: 'output'}
    for g, shape in shapes.items():
        p = gp(g)
        sh.wire(p, (lcol, p[1]))
        sh.hlabel(Pt(lcol, p[1]), net(g), 'L', shape)
    # GPIO33: activity LED (1k, red) to GND, on its own row past the label column
    p = gp(33)
    sh.place('R_LED', 119.38, p[1], rot=270, fields='above')
    sh.wire(p, sh.P('R_LED', 1))
    sh.place('D_LED', 99.06, p[1], fields='above')
    sh.wire(sh.P('R_LED', 2), sh.P('D_LED', 2))
    sh.label((104.14, p[1]), 'RP_LED_A')
    sh.label((124.46, p[1]), 'RP_LED')
    sh.gnd(sh.P('D_LED', 1), 2.54, rot=270)
    # GPIO34: /WAIT -- the 2N7002, gate pulled up: the Z80 waits from power-on
    p = gp(34)
    qx = 66.04
    sh.place('Q_WAIT', qx, p[1], mirror='y', fields='left')
    gte = sh.P('Q_WAIT', 1)
    sh.wire(p, gte)
    sh.place('R_WAIT', 81.28, p[1] - 6.35, fields='right')
    sh.wire(sh.P('R_WAIT', 2), (81.28, p[1]))
    sh.sup(sh.P('R_WAIT', 1), '+3V3_RP')
    sh.label((106.68, p[1]), 'WAIT_GATE')
    sh.gnd(sh.P('Q_WAIT', 2))
    d = sh.P('Q_WAIT', 3)
    sh.wire(d, (d[0], d[1] - 5.08), (d[0] - 10.16, d[1] - 5.08))
    sh.hlabel(Pt(d[0] - 10.16, d[1] - 5.08), 'WAIT_N', 'L', 'output')
    # GPIO36/37: debug UART header (DNP), its pins on the GPIO rows
    p36, p37 = gp(36), gp(37)
    sh.place('J_DBG', 114.3, p36[1] + 2.54, mirror='y', fields='left')
    sh.wire(p36, sh.P('J_DBG', 1))
    sh.wire(p37, sh.P('J_DBG', 2))
    sh.label((148.59, p36[1]), 'DBG_TX')
    sh.label((148.59, p37[1]), 'DBG_RX')
    j3 = sh.P('J_DBG', 3)
    sh.wire(j3, (j3[0] + 2.54, j3[1]), (j3[0] + 2.54, j3[1] + 5.08))
    sh.gnd((j3[0] + 2.54, j3[1] + 5.08))
    # ---- FujiNet side (right) -------------------------------------------------
    # RUN: pull-up, test pad, RESET button through the BAT54C (which also resets
    # the S3), the S3's IO4 through 1k
    run = P(35)
    ry_ = run[1]
    xa, xb, xd = run[0] + 10.16, run[0] + 20.32, run[0] + 33.02
    sh.place('R_RUN', xa, ry_ - 6.35, fields='right')
    sh.wire(sh.P('R_RUN', 2), (xa, ry_))
    sh.sup(sh.P('R_RUN', 1), '+3V3_RP')
    sh.place('TP_RUN', xb, ry_ - 2.54, fields='right')
    sh.wire((xb, ry_), (xb, ry_ - 2.54))
    sh.place('D_RST', xd, ry_ - 7.62, rot=90, fields='right')
    dk = sh.P('D_RST', 3)
    sh.place('SW_RESET', dk[0] + 15.24, dk[1], fields='above')
    sh.wire(dk, sh.P('SW_RESET', 1))
    sh.gnd(sh.P('SW_RESET', 2), 2.54, rot=90)
    sh.label((dk[0] + 1.27, dk[1]), 'RST_BTN')
    e = sh.P('D_RST', 2)
    sh.wire(e, (e[0], e[1] - 2.54), (rcol, e[1] - 2.54))
    sh.hlabel(Pt(rcol, e[1] - 2.54), 'S3_EN', 'R', 'bidirectional')
    sh.place('R_RUNCTL', xd + 30.48, ry_, rot=270, fields='above')
    sh.wire(run, (xa, ry_), (xb, ry_), sh.P('D_RST', 1), sh.P('R_RUNCTL', 2))
    p = sh.P('R_RUNCTL', 1)
    sh.wire(p, (rcol, p[1]))
    sh.hlabel(Pt(rcol, p[1]), 'RUN_CTL', 'R', 'input')
    sh.label((run[0] + 3.81, ry_), 'RUN')
    # USB to the S3 (the RP is the device): 27R series
    for pin, key, n in ((66, 'R_USBM', 'USB_DM'), (67, 'R_USBP', 'USB_DP')):
        p = P(pin)
        sh.place(key, p[0] + 25.4, p[1], rot=270, fields='above' if pin == 66 else 'below')
        sh.wire(p, sh.P(key, 2))
        q = sh.P(key, 1)
        sh.wire(q, (rcol, q[1]))
        sh.hlabel(Pt(rcol, q[1]), n, 'R', 'bidirectional')
        sh.label((p[0] + 3.81, p[1]), 'RP_' + n)
    # QSPI_SS (BOOTSEL): the button branch, the S3 IO5 branch, the pull-up at the end
    ss = P(75)
    q = ss[1]
    x1, x2 = ss[0] + 10.16, ss[0] + 25.4
    sh.place('R_BSEL', x1, q + 3.81, fields='left')
    sh.place('SW_BOOTSEL', x1 + 20.32, q + 17.78, fields='above')
    sh.wire(sh.P('R_BSEL', 2), (x1, q + 17.78), sh.P('SW_BOOTSEL', 1))
    sh.gnd(sh.P('SW_BOOTSEL', 2), 2.54, rot=90)
    sh.label((x1 + 1.27, q + 17.78), 'BOOTSEL_BTN')
    sh.place('R_BSELCTL', x2, q + 3.81, rot=180, fields='right')
    p = sh.P('R_BSELCTL', 1)
    sh.wire(p, (p[0], p[1] + 2.54), (rcol, p[1] + 2.54))
    sh.hlabel(Pt(rcol, p[1] + 2.54), 'BOOTSEL_CTL', 'R', 'input')
    sh.place('R_SS', x2 + 15.24, q, rot=270, fields='above')
    sh.wire(ss, (x1, q), (x2, q), sh.P('R_SS', 2))
    sh.sup(sh.P('R_SS', 1), '+3V3_RP', rot=270)
    sh.label((ss[0] + 3.81, q), 'QSPI_SS')
    for n in (71, 72, 74, 73, 70):
        sh.nc(P(n))
    # 12 MHz crystal: XIN straight to it, XOUT through the 1k; load caps to the right
    xi, xo = P(30), P(31)
    cx = xi[0] + 25.4
    sh.place('Y_RP', cx, (xi[1] + xo[1]) / 2, rot=270, mirror='y', fields='left')
    y1, y3 = sh.P('Y_RP', 1), sh.P('Y_RP', 3)
    sh.wire(xi, (cx, xi[1]), y1)
    sh.place('R_XOUT', xo[0] + 15.24, xo[1], rot=90, fields='below')
    sh.wire(xo, sh.P('R_XOUT', 1))
    sh.wire(sh.P('R_XOUT', 2), (cx, xo[1]), y3)
    sh.gnd(sh.P('Y_RP', 2), 2.54, rot=90)
    for key, row in (('C_XIN', xi[1]), ('C_XOUT', xo[1])):
        sh.place(key, cx + 27.94, row, rot=90, fields='above' if key == 'C_XIN' else 'below')
        sh.wire((cx, row), sh.P(key, 1))
        sh.gnd(sh.P(key, 2), 2.54, rot=90)
    sh.label((xi[0] + 3.81, xi[1]), 'XIN')
    sh.label((xo[0] + 3.81, xo[1]), 'XOUT')
    sh.label((cx + 3.81, xo[1]), 'XOUT_Y')
    # SWD test pads
    for pin, key, f in ((33, 'TP_SWCLK', 'above'), (34, 'TP_SWDIO', 'below')):
        p = P(pin)
        sh.place(key, p[0] + 17.78, p[1], rot=270, fields=f)
        sh.wire(p, sh.P(key, 1))
        sh.label((p[0] + 3.81, p[1]), D.BY_KEY[key].pins['1'])
    # GPIO40 LOAD to the glue, GPIO41-47 (SRAM A13-A19) onto the bank bus
    p = gp(40)
    sh.wire(p, (rcol, p[1]))
    sh.hlabel(Pt(rcol, p[1]), 'LOAD', 'R', 'output')
    sbx = p[0] + 33.02
    _, bot = sh.bus_group([(gp(g), net(g)) for g in range(41, 48)], sbx, up=False)
    sh.bus(bot, (sbx, bot[1] + 2.54), (rcol, bot[1] + 2.54))
    sh.hlabel(Pt(rcol, bot[1] + 2.54), SA_BUS, 'R', 'output')
    # ---- supplies (top) -------------------------------------------------------
    ry = Y - 78.74                       # the +3V3_RP rail
    io = [P(n) for n in (64, 50, 69, 59, 68)]    # VREG_VIN IOVDD QSPI_IOVDD ADC_AVDD USB_OTP_VDD
    for p in io:
        sh.wire(p, (p[0], ry))
    caps = ['C_IOV%d' % n for n in D.RP_IOVDD_PINS] + ['C_QSPI', 'C_OTP', 'C_ADC', 'C_IOBULK', 'C_VREGIN']
    av = P(61)
    rx = av[0]                           # the VREG_AVDD filter hangs straight over its pin
    xs = [rx + 22.86 + 11.43 * i for i in range(len(caps))]
    for key, x in zip(caps, xs):
        sh.place(key, x, ry + 3.81, fields='right')
        sh.gnd(sh.P(key, 2))
    end = xs[-1] + 7.62
    sh.wire(*sorted({(x, ry) for x in xs} | {(p[0], ry) for p in io} | {(rx, ry), (end, ry)}))
    sh.sup((end, ry), '+3V3_RP')
    # VREG_AVDD: 33R off the rail, 4.7u to GND
    sh.place('R_AVDD', rx, ry + 6.35, fields='right')
    sh.wire((rx, ry), sh.P('R_AVDD', 1))
    node = sh.P('R_AVDD', 2)
    sh.wire(node, av)
    sh.place('C_AVDD', rx + 7.62, node[1] + 3.81, fields='right')
    sh.wire(node, (rx + 7.62, node[1]), (rx + 12.7, node[1]))
    sh.gnd(sh.P('C_AVDD', 2))
    sh.flag((rx + 12.7, node[1]), 'VREG_AVDD')
    sh.label((rx, node[1] + 1.27), 'VREG_AVDD', 'D')
    # core SMPS: LX -> L -> DVDD; FB and the three DVDD pins on that node, its caps to the left
    lx, fb, dv = P(63), P(65), P(10)
    ly = ry + 7.62
    sh.place('L_RP', lx[0] - 7.62, ly, rot=90, fields='above')
    sh.wire(lx, (lx[0], ly), sh.P('L_RP', 2))
    dvx = [lx[0] - 25.4 - 11.43 * i for i in range(4)]
    sh.wire(sh.P('L_RP', 1), *[(x, ly) for x in dvx], (dvx[-1] - 7.62, ly))
    for key, x in zip(('C_DV10', 'C_DV32', 'C_DV51', 'C_DVBULK'), dvx):
        sh.place(key, x, ly + 3.81, fields='right')
        sh.gnd(sh.P(key, 2))
    jy = ly + 12.7
    jx = lx[0] - 15.24
    sh.wire(fb, (fb[0], jy), (jx, jy), (jx, ly))
    sh.wire(dv, (dv[0], jy))
    fx = (dvx[0] + dvx[1]) / 2
    sh.wire((fx, ly), (fx, ly - 2.54))
    sh.flag((fx, ly - 2.54), 'DVDD')
    sh.sup((dvx[-1] - 7.62, ly), 'DVDD')
    sh.label((lx[0], ly + 5.08), 'RP_LX', 'U')
    # ground: GND + the regulator's PGND, the GND test pad
    g, pg = P(81), P(62)
    sh.wire(pg, pg.go(2.54), g.go(2.54))
    sh.wire(g, g.go(2.54))
    sh.gnd(g.go(2.54))
    sh.place('TP_GND', g[0] + 12.7, g[1] + 2.54, fields='right')
    sh.wire(g.go(2.54), (g[0] + 12.7, g[1] + 2.54))
    sh.text((X - 63.5, Y + 73.66), 'One 100 nF per IOVDD pin (key C_IOV<pin>: placed at that pin).  RP2350 datasheet 6.3.7: VREG_VIN and IOVDD\n'
                                    'on one 3.3 V supply (+3V3_RP, the LDO that rises with the console 5V), VREG_AVDD through 33R / 4.7 uF,\n'
                                    '3.3 uH from VREG_LX to DVDD (= VREG_FB).  GPIO33 activity LED; console /WAIT held low by the 2N7002\n'
                                    'from power-on until the firmware drives GPIO34 low; debug UART header (DNP): 1 TX GPIO36, 2 RX GPIO37.')


# =========================================================================
@sheet('sram')
def sram(sh):
    """Two AS6C4008s on the 5V rail: the console's address bus and the RP's bank
    lines in from the left with the glue's strobes, data out on the right
    (straight onto the console's data bus)."""
    lcol, rcol = 139.7, 266.7
    for U, Y, ce, caps in (('U_SRAM0', 88.9, 'SA19', ('C_SRAM0', 'C_SRAMBULK')), ('U_SRAM1', 182.88, 'SA19_N', ('C_SRAM1',))):
        X = 203.2
        sh.place(U, X, Y, fields='abovebelow', val_at=(X + 11.43, Y + 31.75, 'left'))
        top, _ = sh.bus_group([(sh.N(U, 'A%d' % i), 'A%d' % i) for i in range(13)], 177.8, up=True)
        sh.bus(top, (lcol, top[1]))
        sh.hlabel(Pt(lcol, top[1]), A_BUS, 'L', 'input')
        sa = [(sh.N(U, 'SA%d' % i), 'SA%d' % i) for i in range(13, 19)]
        if ce == 'SA19':
            sa.append((sh.N(U, 'SA19'), 'SA19'))
        stop, _ = sh.bus_group(sa, 170.18, up=True)
        sh.bus(stop, (lcol, stop[1]))
        sh.hlabel(Pt(lcol, stop[1]), SA_BUS, 'L', 'input')
        nets = ('SRAM_OE_N', 'SRAM_WE_N') if ce == 'SA19' else ('SA19_N', 'SRAM_OE_N', 'SRAM_WE_N')
        for n in nets:
            p = sh.N(U, n)
            sh.wire(p, (lcol, p[1]))
            sh.hlabel(Pt(lcol, p[1]), n, 'L', 'input')
        top, _ = sh.bus_group([(sh.N(U, 'D%d' % i), 'D%d' % i) for i in range(8)], 228.6, up=True)
        sh.bus(top, (rcol, top[1]))
        sh.hlabel(Pt(rcol, top[1]), D_BUS, 'R', 'bidirectional')
        sh.sup(sh.N(U, '+5V'), '+5V')
        sh.gnd(sh.N(U, 'GND'))
        for i, c in enumerate(caps):
            sh.place(c, X + 38.1 + 12.7 * i, Y + 15.24)
            sh.sup(sh.P(c, 1), '+5V')
            sh.gnd(sh.P(c, 2))
    sh.text((139.7, 236.22), 'SRAM A19 (GPIO47) picks the chip: the lower 512K\'s /CE is SA19 itself, the upper one\'s !SA19 (glue sheet).\n'
                             'A0-A12 and D0-D7 are the console\'s; A13-A18 the RP\'s bank lines (GPIO41-46).')


# =========================================================================
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


def link(sh, a, b, jx):
    """Output a -> input b: right to x = jx, along to b's row, into b."""
    if a[1] == b[1]:
        return sh.wire(a, b)
    return sh.wire(a, (jx, a[1]), (jx, b[1]), b)


def inp(sh, pin, net, n=7.62):
    """An input from another sheet: a short stub left of the pin and its hierarchical label."""
    e = (pin[0] - n, pin[1])
    sh.wire(pin, e)
    sh.hlabel(Pt(e[0], e[1]), net, 'L', 'input')


@sheet('glue')
def glue(sh):
    """The 5V glue as a wired network, by logic depth left to right: the console
    5V sense and the inversions; the address decode (the $8000-$9FFF load window,
    slot 2 less the live mailbox arena); the window terms; the strobe stage that
    makes SRAM /WE and /OE.  Inputs from the other sheets enter on hierarchical
    labels at the gate that first takes them; outputs leave on the right."""
    c1, c2, c3, c4, c5, c6 = (101.6 + 50.8 * i for i in range(6))
    yA, yB, yC, yD, yE, yF, yG = 38.1, 60.96, 86.36, 111.76, 137.16, 160.02, 182.88
    out_x = c6 + 38.1
    lab = {}

    def output(pin_or_pt, net, y=None):
        y = pin_or_pt[1] if y is None else y
        if y != pin_or_pt[1]:
            sh.wire(pin_or_pt, (out_x - 12.7, pin_or_pt[1]), (out_x - 12.7, y), (out_x, y))
        else:
            sh.wire(pin_or_pt, (out_x, y))
        sh.hlabel(Pt(out_x, y), net, 'R', 'output')

    # ---- row A: console 5V sense, 22k / 100k into two Schmitt inverters -> PWR_OK
    ia, oa = gate(sh, 'U_INV', 1, c1, yA)
    nx = c1 - 25.4
    sh.place('R_VSH', nx, yA - 6.35, fields='left')
    sh.place('R_VSL', nx, yA + 6.35, fields='left')
    sh.sup(sh.P('R_VSH', 1), 'CONS_5V')
    sh.gnd(sh.P('R_VSL', 2))
    sh.wire(sh.P('R_VSH', 2), (nx, yA), sh.P('R_VSL', 1))
    sh.wire((nx, yA), ia['VSENSE'][0])
    sh.label((nx + 2.54, yA), 'VSENSE')
    ib, ob = gate(sh, 'U_INV', 2, c2, yA)
    sh.wire(oa, ib['PWR_OK_N'][0])
    sh.label((oa[0] + 2.54, yA), 'PWR_OK_N')
    # ---- row B: CE = !/CE; CEP_N = !(CE & PWR_OK)
    ic, oc = gate(sh, 'U_INV', 4, c1, yB)
    inp(sh, ic['CE_N'][0], 'CE_N')
    i8a, o8a = gate(sh, 'U_NAND2', 1, c3, yB)
    link(sh, oc, i8a['CE'][0], c3 - 15.24)
    sh.label((oc[0] + 2.54, yB), 'CE')
    pok = (c3 - 12.7, yA)
    sh.wire(ob, pok)
    link(sh, pok, i8a['PWR_OK'][0], c3 - 12.7)
    output(pok, 'PWR_OK')
    # ---- row C: A15_N; WIN8 = A15 & !A14 & !A13; LOADWIN_N = !(LOAD & WIN8); WE_LOAD
    i4e, o4e = gate(sh, 'U_INV', 5, c1, yC)
    inp(sh, i4e['A15'][0], 'A15')
    i6b, o6b = gate(sh, 'U_NORDEC', 2, c2, yC)
    sh.wire(o4e, i6b['A15_N'][0])
    inp(sh, i6b['A14'][0], 'A14', 5.08)
    inp(sh, i6b['A13'][0], 'A13', 5.08)
    sh.label((o4e[0] + 2.54, yC), 'A15_N')
    i8b, o8b = gate(sh, 'U_NAND2', 2, c3, yC)
    link(sh, o6b, i8b['WIN8'][0], c3 - 15.24)
    inp(sh, i8b['LOAD'][0], 'LOAD', 5.08)
    sh.label((o6b[0] + 2.54, yC), 'WIN8')
    i5a, o5a = gate(sh, 'U_NORWE', 1, c4, yC)
    sh.wire(o8b, i5a['LOADWIN_N'][0])
    inp(sh, i5a['RD_N'][0], 'RD_N', 5.08)
    sh.label((o8b[0] + 2.54, yC), 'LOADWIN_N')
    # ---- row D: MBA_N = !(MBOX & A13 & A12); MBA; SLOT2_NM; RAMWIN_N; WE_RAM
    i7a, o7a = gate(sh, 'U_NAND3', 1, c1, yD)
    for n in ('MBOX', 'A13', 'A12'):
        inp(sh, i7a[n][0], n, 5.08)
    i4f, o4f = gate(sh, 'U_INV', 6, c2, yD)
    sh.wire(o7a, i4f['MBA_N'][0])
    sh.label((o7a[0] + 2.54, yD), 'MBA_N')
    i6c, o6c = gate(sh, 'U_NORDEC', 3, c3, yD)
    sh.wire(o4f, i6c['MBA'][0])
    sh.label((o4f[0] + 2.54, yD), 'MBA')
    inp(sh, i6c['A14'][0], 'A14', 5.08)
    # A15_N down from row C, through the gap between the rows
    tap = (c1 + 17.78, yC)
    gy = (yC + yD) / 2 + 1.27
    sh.wire(tap, (tap[0], gy), (c3 - 12.7, gy), (c3 - 12.7, i6c['A15_N'][0][1]), i6c['A15_N'][0])
    i7b, o7b = gate(sh, 'U_NAND3', 2, c4, yD)
    sh.wire(o6c, i7b['SLOT2_NM'][0])
    inp(sh, i7b['RAM_WE'][0], 'RAM_WE', 5.08)
    sh.sup(i7b['+5V'][0], '+5V', 2.54, rot=90)
    sh.label((o6c[0] + 2.54, yD), 'SLOT2_NM')
    i5b, o5b = gate(sh, 'U_NORWE', 2, c5, yD)
    sh.wire(o7b, i5b['RAMWIN_N'][0])
    inp(sh, i5b['WR_N'][0], 'WR_N', 5.08)
    sh.label((o7b[0] + 2.54, yD), 'RAMWIN_N')
    # ---- row E: SLOT2_NM_N; OE_ADDR = !A15 | SLOT2_NM
    i8c, o8c = gate(sh, 'U_NAND2', 3, c4, yE)
    s2 = i8c['SLOT2_NM']
    jx = c4 - 20.32
    sh.wire(s2[0], (jx, s2[0][1]), (jx, s2[1][1]), s2[1])
    sh.wire((jx, s2[0][1]), (jx, yD))          # up to the SLOT2_NM line (a T on it)
    i8d, o8d = gate(sh, 'U_NAND2', 4, c5, yE)
    link(sh, o8c, i8d['SLOT2_NM_N'][0], c5 - 15.24)
    inp(sh, i8d['A15'][0], 'A15', 5.08)
    sh.label((o8c[0] + 2.54, yE), 'SLOT2_NM_N')
    # ---- row F: RD_CEP = RD & CEP
    i6a, o6a = gate(sh, 'U_NORDEC', 1, c4, yF)
    inp(sh, i6a['RD_N'][0], 'RD_N', 5.08)
    sh.gnd(i6a['GND'][0], 2.54, rot=270)
    # ---- CEP_N: down a trunk to the three strobe gates
    tx = c4 - 27.94
    sh.wire(o8a, (tx, yB))
    sh.label((o8a[0] + 2.54, yB), 'CEP_N')
    taps = [i5a['CEP_N'][0], i6a['CEP_N'][0]]
    sh.wire((tx, yB), (tx, taps[1][1]))
    for t in taps:
        sh.wire((tx, t[1]), t)
    g5 = (yC + yD) / 2 - 1.27
    sh.wire((tx, g5), (c5 - 15.24, g5), (c5 - 15.24, i5b['CEP_N'][0][1]), i5b['CEP_N'][0])
    # ---- the strobe stage: SRAM /WE = NOR(WE_LOAD, WE_RAM); SRAM /OE = NAND(OE_ADDR, GAME, RD_CEP)
    i5c, o5c = gate(sh, 'U_NORWE', 3, c6, (yC + yD) / 2)
    link(sh, o5a, i5c['WE_LOAD'][0], c6 - 15.24)
    link(sh, o5b, i5c['WE_RAM'][0], c6 - 12.7)
    sh.gnd(i5c['GND'][0], 2.54, rot=270)
    sh.label((o5a[0] + 2.54, yC), 'WE_LOAD')
    sh.label((o5b[0] + 2.54, yD), 'WE_RAM')
    output(o5c, 'SRAM_WE_N')
    i7c, o7c = gate(sh, 'U_NAND3', 3, c6, (yE + yF) / 2)
    link(sh, o8d, i7c['OE_ADDR'][0], c6 - 20.32)
    link(sh, o6a, i7c['RD_CEP'][0], c6 - 20.32)
    inp(sh, i7c['GAME'][0], 'GAME', 5.08)
    sh.label((o8d[0] + 2.54, yE), 'OE_ADDR')
    sh.label((o6a[0] + 2.54, yF), 'RD_CEP')
    output(o7c, 'SRAM_OE_N')
    # ---- row G: the upper SRAM's chip select
    i4c, o4c = gate(sh, 'U_INV', 3, c1, yG)
    inp(sh, i4c['SA19'][0], 'SA19')
    output(o4c, 'SA19_N')
    # ---- supplies: each package's power unit with its 100 nF
    for i, (key, unit, cap) in enumerate((('U_INV', 7, 'C_INV'), ('U_NORWE', 4, 'C_NORWE'), ('U_NORDEC', 4, 'C_NORDEC'),
                                         ('U_NAND3', 4, 'C_NAND3'), ('U_NAND2', 5, 'C_NAND2'))):
        x, y = c1 - 25.4 + 38.1 * i, 223.52
        sh.place(key, x, y, unit=unit, fields='right')
        sh.sup(sh.P(key, 14), '+5V')
        sh.gnd(sh.P(key, 7))
        sh.place(cap, x + 17.78, y)
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    sh.text((c5 - 33.02, 208.28),
            "fujinet-firmware pico/sms sms_cart.h: sms_glue_oe(), sms_glue_we().  RD, WR, CE = the console's\n"
            '/RD, /WR, /CE asserted; GAME, MBOX, RAM_WE, LOAD = RP GPIO38, 35, 39, 40; PWR_OK = console +5V present.\n'
            'CEP_N = !(CE & PWR_OK);   WIN8 = A15 & !A14 & !A13 (the $8000-$9FFF load window)\n'
            'MBA_N = !(MBOX & A13 & A12);   SLOT2_NM = A15 & !A14 & !(MBOX & A13 & A12)\n'
            'OE_ADDR = !A15 | SLOT2_NM;   WE_LOAD = RD & CEP & LOAD & WIN8;   WE_RAM = WR & CEP & RAM_WE & SLOT2_NM\n'
            'SRAM /WE = !(WE_LOAD | WE_RAM): /RD and /WR are two gates from /WE\n'
            'SRAM /OE = !(RD & CEP & GAME & OE_ADDR);   upper SRAM /CE = !SA19, lower = SA19\n'
            "tools/check_glue.py evaluates this netlist against the firmware's C for every input combination.", 1.27)


# =========================================================================
@sheet('esp32s3-sd', 'A4')
def esp32s3_sd(sh):
    """The ESP32-S3: reset / boot and its two RP control lines on the left; the
    UART to the USB bridge and native USB to the RP on the right, then the
    microSD socket (SPI fanned out to the socket's pin order) and the status LED."""
    U = 'U_S3'
    X, Y = 190.5, 149.86
    sh.place(U, X, Y, fields='abovebelow', ref_at=(X - 12.7, Y - 29.21, 'left'), val_at=(X - 22.86, Y + 29.21, 'right'))
    lcol, rcol = 124.46, 297.18
    # supply + decoupling above
    v = sh.P(U, 2)
    node = (v[0], Y - 38.1)
    sh.wire(v, node, (X + 10.16, node[1]), (X + 22.86, node[1]))
    sh.sup(node, '+3V3')
    for c, x in (('C_S3', X + 10.16), ('C_S3BULK', X + 22.86)):
        sh.place(c, x, node[1] + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.gnd(sh.P(U, 1))
    # EN: pull-up, power-on delay, button; S3_EN also from RESET and the auto-program pair
    en = sh.P(U, 3)
    ey = en[1] - 17.78
    sh.wire(en, (X - 20.32, en[1]), (X - 20.32, ey), (X - 27.94, ey), (X - 38.1, ey), (X - 48.26, ey), (lcol, ey))
    sh.hlabel(Pt(lcol, ey), 'S3_EN', 'L', 'bidirectional')
    sh.place('R_EN', X - 27.94, ey - 3.81, fields='right')
    sh.sup(sh.P('R_EN', 1), '+3V3')
    sh.place('C_EN', X - 38.1, ey + 3.81, fields='right')
    sh.gnd(sh.P('C_EN', 2))
    sh.place('SW_S3EN', X - 48.26, ey + 5.08, rot=270, fields='left')
    sh.gnd(sh.P('SW_S3EN', 2))
    # IO0 (BOOT): button + the auto-program transistor
    io0 = sh.P(U, 27)
    sh.wire(io0, (X - 43.18, io0[1]), (lcol, io0[1]))
    sh.hlabel(Pt(lcol, io0[1]), 'S3_IO0', 'L', 'bidirectional')
    sh.place('SW_S3BOOT', X - 43.18, io0[1] + 5.08, rot=270, fields='left')
    sh.gnd(sh.P('SW_S3BOOT', 2))
    # IO4 / IO5: RUN / BOOTSEL of the RP2354B
    sh.port(sh.P(U, 4), 'RUN_CTL', 5.08, shape='output')
    sh.port(sh.P(U, 5), 'BOOTSEL_CTL', 5.08, shape='output')
    # UART to the CP2102N, native USB to the RP
    for pad, n, shape in ((37, 'S3_TXD', 'output'), (36, 'S3_RXD', 'input'), (13, 'USB_DM', 'bidirectional'),
                          (14, 'USB_DP', 'bidirectional')):
        p = sh.P(U, pad)
        sh.wire(p, (rcol, p[1]))
        sh.hlabel(Pt(rcol, p[1]), n, 'R', shape)
    ncs(sh, U)
    # microSD: SPI fans out from 2.54 to the socket's 5.08 and is named there
    J = 'J_SD'
    sh.place(J, X + 76.2, Y + 20.32, fields='abovebelow', ref_at=(X + 88.9, Y + 46.99, 'left'),
             val_at=(X + 88.9, Y + 49.53, 'left'))
    for k, n in enumerate(('SD_MOSI', 'SD_SCK', 'SD_MISO', 'SD_CS', 'SD_CD')):
        a, b = sh.N(U, n), sh.N(J, n)
        x = X + 22.86 + (4 - k) * 2.54
        sh.wire(a, (x, a[1]), (x, b[1]), b)
        sh.label((X + 38.1, b[1]), n)
    # pull-ups: DAT1 / DAT2 wired to the pack (DAT2 steps down to its pin), CS / MISO by label
    R = 'RN_SD'
    sh.place(R, X + 43.18, sh.N(J, 'SD_DAT1')[1], rot=90, mirror='x', fields='above')
    sh.wire(sh.N(R, 'SD_DAT1'), sh.N(J, 'SD_DAT1'))
    p, q = sh.N(R, 'SD_DAT2'), sh.N(J, 'SD_DAT2')
    sh.wire(p, (X + 50.8, p[1]), (X + 50.8, q[1]), q)
    sh.label((X + 53.34, sh.N(J, 'SD_DAT1')[1]), 'SD_DAT1')
    sh.label((X + 53.34, q[1]), 'SD_DAT2')
    for n in ('SD_CS', 'SD_MISO'):
        e = sh.stub(sh.N(R, n), 2.54)
        sh.label(e, n, 'R')
    g = [sh.P(R, n) for n in (5, 6, 7, 8)]
    ys = sorted(p[1] for p in g)
    gx = g[0][0] - 2.54
    for p in g:
        sh.wire(p, (gx, p[1]))
    sh.wire(*[(gx, y) for y in ys])
    sh.sup((gx, ys[0]), '+3V3')
    sh.place('R_SDCD', X + 104.14, Y + 38.1, fields='right')
    sh.sup(sh.P('R_SDCD', 1), '+3V3')
    e = sh.stub(sh.P('R_SDCD', 2))
    sh.label(e, 'SD_CD', 'D')
    sh.sup(sh.N(J, '+3V3'), '+3V3', n=2.54, rot=90)
    sh.gnd(sh.P(J, 6), n=2.54, rot=270)
    shp = [sh.P(J, n) for n in (10, 11, 12, 13)]
    sh.wire(*shp)
    sh.wire(shp[0], (shp[0][0], shp[0][1] + 2.54))
    sh.gnd((shp[0][0], shp[0][1] + 2.54))
    sh.place('C_SD', X + 93.98, Y + 38.1)
    sh.sup(sh.P('C_SD', 1), '+3V3')
    sh.gnd(sh.P('C_SD', 2))
    # status LED: WS2812B on +5V, data straight from the S3 through 330R
    led = sh.P(U, 25)
    ly = Y + 60.96
    sh.place('R_WS', X + 27.94, ly, rot=90, fields='below')
    sh.wire(led, (X + 20.32, led[1]), (X + 20.32, ly), sh.P('R_WS', 1))
    sh.label((X + 20.32, ly - 7.62), 'LED_STRIP', 'U')
    sh.place('D_WS', X + 53.34, ly, fields='right')
    sh.wire(sh.P('R_WS', 2), sh.P('D_WS', 3))
    sh.label((X + 34.29, ly), 'WS_DIN')
    sh.sup(sh.P('D_WS', 4), '+5V')
    sh.gnd(sh.P('D_WS', 2))
    sh.nc(sh.P('D_WS', 1))
    sh.place('C_WS', X + 81.28, ly)
    sh.sup(sh.P('C_WS', 1), '+5V')
    sh.gnd(sh.P('C_WS', 2))


# =========================================================================
@sheet('usb-uart', 'A4')
def usb_uart(sh):
    """USB-C on the left; VBUS up onto its rail (ESD, decoupling, the bridge's
    VBUS sense), CC pull-downs, the data pair through its ESD diodes into the
    CP2102N; the bridge's UART and the esptool auto-program pair on the right."""
    J, U = 'J_USB', 'U_UART'
    rcol = 284.48
    sh.place(J, 50.8, 149.86, fields='abovebelow', val_at=(39.37, 172.72, 'right'))
    # VBUS rail: ESD, decoupling, the sense divider
    vb = sh.P(J, 'A4')
    ry = 116.84
    xs = [96.52, 109.22, 121.92]
    sh.wire(vb, (71.12, vb[1]), (71.12, ry), *[(x, ry) for x in xs], (134.62, ry))
    sh.sup((71.12, ry), 'VBUS')
    for key, x in zip(('D_ESDV', 'C_VBUS', 'C_VBUSHF'), xs):
        sh.place(key, x, ry + 3.81, rot=270 if key == 'D_ESDV' else 0, fields='left' if key == 'D_ESDV' else 'right')
        sh.gnd(sh.P(key, 2))
    # CC pull-downs (Rd): inline, staggered, ground at the end
    for pin, key, x, f in (('A5', 'R_CC1', 83.82, 'above'), ('B5', 'R_CC2', 96.52, 'below')):
        p = sh.P(J, pin)
        sh.place(key, x, p[1], rot=90, fields=f)
        sh.wire(p, sh.P(key, 1))
        sh.gnd(sh.P(key, 2), 2.54, rot=90)
        sh.label((p[0] + 2.54, p[1]), pin.replace('A5', 'CC1').replace('B5', 'CC2'))
    # data pair: both receptacle rows joined, ESD to GND, into the bridge
    dm = [sh.P(J, 'A7'), sh.P(J, 'B7')]
    dp = [sh.P(J, 'A6'), sh.P(J, 'B6')]
    for a, b in (dm, dp):
        sh.wire(a, (68.58, a[1]), (68.58, b[1]), b)
    sh.place(U, 190.5, 160.02, fields='abovebelow', val_at=(204.47, 196.85, 'left'))
    cdm, cdp = sh.P(U, 5), sh.P(U, 4)
    sh.wire((68.58, dm[0][1]), (114.3, dm[0][1]), cdm)
    sh.wire((68.58, dp[0][1]), (99.06, dp[0][1]), (167.64, dp[0][1]), (167.64, cdp[1]), cdp)
    sh.place('D_ESDM', 114.3, dm[0][1] - 3.81, rot=90, fields='right')    # cathode on the line
    sh.gnd(sh.P('D_ESDM', 2), rot=180)
    sh.place('D_ESDP', 99.06, dp[0][1] + 3.81, rot=270, fields='right')
    sh.gnd(sh.P('D_ESDP', 2))
    sh.label((139.7, dm[0][1]), 'UBRG_DM')
    sh.label((139.7, dp[0][1]), 'UBRG_DP')
    for p in (sh.P(J, 'A8'), sh.P(J, 'B8')):
        sh.nc(p)
    g1, g2 = sh.P(J, 'A1'), sh.P(J, 'SH')
    sh.wire(g2, (g2[0], g2[1] + 2.54), (g1[0], g1[1] + 2.54), g1)
    sh.gnd((g1[0], g1[1] + 2.54))
    # VBUS sense divider into the bridge's VBUS pin (self-powered bridge)
    sns = sh.P(U, 8)
    sh.place('R_VBSH', 134.62, ry + 3.81, fields='right')
    sh.place('R_VBSL', 144.78, sns[1] - 3.81, rot=180, fields='right')
    sh.wire(sh.P('R_VBSH', 2), (134.62, sns[1]), sh.P('R_VBSL', 1), sns)
    sh.gnd(sh.P('R_VBSL', 2), rot=180)
    sh.label((149.86, sns[1]), 'VBUS_SNS')
    # supply, reset pull-up
    vd, vr = sh.P(U, 6), sh.P(U, 7)
    top = 116.84
    sh.wire(vr, (vr[0], top))
    sh.wire(vd, (vd[0], top), (198.12, top), (210.82, top))
    sh.wire((vr[0], top), (vd[0], top))
    sh.sup((vr[0], top), '+3V3')
    for c, x in (('C_UART', 198.12), ('C_UARTBULK', 210.82)):
        sh.place(c, x, top + 3.81)
        sh.gnd(sh.P(c, 2))
    rst = sh.P(U, 9)
    sh.place('R_CPRST', 165.1, rst[1] - 3.81, fields='left')
    sh.wire(rst, (165.1, rst[1]))
    sh.sup(sh.P('R_CPRST', 1), '+3V3')
    sh.label((166.37, rst[1]), 'CP_RST')
    sh.gnd(sh.P(U, 3))
    sh.gnd(sh.P(U, 23), 2.54, rot=90)                      # /CTS tied low
    ncs(sh, U)
    # UART to the S3 (the bridge's RXD is the S3's TXD)
    for pad, n, shape in ((26, 'S3_RXD', 'output'), (25, 'S3_TXD', 'input')):
        p = sh.P(U, pad)
        sh.wire(p, (rcol, p[1]))
        sh.hlabel(Pt(rcol, p[1]), n, 'R', shape)
    # esptool auto-program: DTR/RTS cross-coupled into EN / IO0 (DevKitC-1)
    rts, dtr = sh.P(U, 24), sh.P(U, 28)
    Q = 'U_AUTOPROG'
    sh.place(Q, 248.92, 149.86, unit=1, fields='right')
    sh.place(Q, 248.92, 172.72, unit=2, fields='right')
    b1, e1, c1 = sh.P(Q, 2), sh.P(Q, 1), sh.P(Q, 6)
    b2, e2, c2 = sh.P(Q, 5), sh.P(Q, 4), sh.P(Q, 3)
    sh.wire(rts, (231.14, rts[1]), (231.14, e1[1] + 5.08), (231.14, b2[1]), b2)
    sh.wire((231.14, e1[1] + 5.08), (e1[0], e1[1] + 5.08), e1)
    sh.wire(dtr, (226.06, dtr[1]), (226.06, b1[1]), b1)
    sh.wire((226.06, b1[1]), (226.06, e2[1] + 5.08), (e2[0], e2[1] + 5.08), e2)
    sh.label((215.9, rts[1]), 'UART_RTS')
    sh.label((215.9, dtr[1]), 'UART_DTR')
    for c, n in ((c1, 'S3_EN'), (c2, 'S3_IO0')):
        sh.wire(c, (c[0], c[1] - 2.54), (rcol, c[1] - 2.54))
        sh.hlabel(Pt(rcol, c[1] - 2.54), n, 'R', 'output')


# =========================================================================
@sheet('power', 'A4')
def power(sh):
    """Left to right: the console's 5 V through the P-FET and USB VBUS through the
    Schottky meet on +5V; +5V feeds the 3.3 V buck (S3, bridge, SD) and the RP's
    own fast LDO (+3V3_RP)."""
    y5, yv = 88.9, 116.84
    # console 5V -> P-FET (gate = VBUS: on without USB) -> +5V
    sh.place('Q_CONS', 60.96, y5 + 2.54, rot=90, fields='above')
    d, s_, g = sh.P('Q_CONS', 3), sh.P('Q_CONS', 2), sh.P('Q_CONS', 1)
    sh.wire((20.32, y5), (33.02, y5), (40.64, y5), (50.8, y5), d)
    sh.sup((20.32, y5), 'CONS_5V')
    sh.flag((50.8, y5), 'CONS_5V')
    sh.place('C_CONS', 33.02, y5 + 3.81, fields='left')
    sh.gnd(sh.P('C_CONS', 2))
    sh.place('C_CONSHF', 40.64, y5 + 3.81, fields='right')
    sh.gnd(sh.P('C_CONSHF', 2))
    # GND's PWR_FLAG (every ground pin on this board is passive or power input)
    sh.wire((20.32, 137.16), (30.48, 137.16))
    sh.gnd((20.32, 137.16))
    sh.flag((30.48, 137.16), 'GND')
    # USB VBUS -> gate (held low by 4.7k without USB), and through the SS34 onto +5V
    sh.place('D_VBUS', 76.2, yv, rot=180, fields='below')
    sh.wire((25.4, yv), (35.56, yv), (45.72, yv), (g[0], yv), sh.P('D_VBUS', 2))
    sh.wire((g[0], yv), g)
    sh.sup((25.4, yv), 'VBUS')
    sh.flag((45.72, yv), 'VBUS')
    sh.place('R_VBPD', 35.56, yv + 3.81, fields='left')
    sh.gnd(sh.P('R_VBPD', 2))
    k = sh.P('D_VBUS', 1)
    sh.wire(k, (86.36, yv), (86.36, y5))
    # +5V: bulk + the buck's input caps, a branch down to the RP LDO
    caps = [('C_BIN1', 96.52), ('C_BIN2', 106.68), ('C_5VBULK', 116.84), ('C_BINHF', 127.0)]
    sh.wire(s_, (86.36, y5), *[(x, y5) for _, x in caps], (134.62, y5), (139.7, y5), (147.32, y5))
    sh.sup((86.36, y5), '+5V')
    sh.flag((139.7, y5), '+5V')
    for c, x in caps:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # 3.3 V buck
    B = 'U_BUCK'
    sh.place(B, 160.02, y5 + 2.54, fields='abovebelow', ref_at=(149.86, 82.55, 'left'), val_at=(147.32, 97.79, 'right'))
    sh.wire((147.32, y5), sh.P(B, 3))
    sh.wire(sh.P(B, 2), (147.32, sh.P(B, 2)[1]), (147.32, y5))
    sh.gnd(sh.P(B, 4))
    sw, bst, fb = sh.P(B, 5), sh.P(B, 6), sh.P(B, 1)
    sh.place('C_BST', 182.88, y5 + 3.81, fields='right')
    sh.place('L_BUCK', 193.04, y5, rot=90, fields='above')
    sh.wire(sw, (182.88, y5), sh.P('L_BUCK', 1))
    sh.wire(bst, (175.26, bst[1]), (175.26, 99.06), (182.88, 99.06), sh.P('C_BST', 2))
    sh.name((177.8, 99.06), 'BUCK_BST', 'D', 'R')
    sh.name((173.99, y5), 'BUCK_SW', 'U', 'R')
    out = [('C_BOUT1', 207.01), ('C_BOUT2', 217.17)]
    sh.wire(sh.P('L_BUCK', 2), (201.93, y5), *[(x, y5) for _, x in out])
    sh.wire(fb, (172.72, fb[1]), (172.72, 106.68), (201.93, 106.68), (201.93, y5))
    sh.sup((201.93, y5), '+3V3')
    sh.flag((217.17, y5), '+3V3')
    for c, x in out:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # RP LDO: +5V -> AP2112K -> +3V3_RP (IOVDD up with the console rail)
    L = 'U_LDO'
    sh.place(L, 152.4, 142.24, fields='abovebelow', ref_at=(144.78, 132.08, 'left'), val_at=(144.78, 134.62, 'left'))
    vin, en, vo = sh.P(L, 1), sh.P(L, 3), sh.P(L, 5)
    sh.wire((134.62, y5), (134.62, vin[1]), (137.16, vin[1]), (142.24, vin[1]), vin)
    sh.wire(en, (142.24, en[1]), (142.24, vin[1]))
    sh.place('C_LDOIN', 137.16, vin[1] + 3.81, fields='left')
    sh.gnd(sh.P('C_LDOIN', 2))
    sh.gnd(sh.P(L, 2))
    sh.nc(sh.P(L, 4))
    sh.wire(vo, (167.64, vo[1]), (172.72, vo[1]))
    sh.place('C_LDOOUT', 167.64, vo[1] + 3.81)
    sh.gnd(sh.P('C_LDOOUT', 2))
    sh.sup((172.72, vo[1]), '+3V3_RP')


# =========================================================================
def draw_root(syms):
    """The block diagram: the console's slot on the left, the RP2354B bus
    controller, the SRAM and its glue under it, the ESP32-S3 and the USB bridge
    toward the PC on the right; power (rails only) bottom right."""
    sh = KSheet('root', syms, [], 'A3')
    i, o, b = 'input', 'output', 'bidirectional'
    strobes = [('MREQ_N', o), ('IORQ_N', o), ('M1_N', o), ('RESET_N', o), ('CLK', o), ('WAIT_N', i),
               ('RD_N', o), ('WR_N', o), ('CE_N', o), (D_BUS, b), (A_BUS, o)]
    flip = {i: o, o: i, b: b}
    Y0 = 45.72
    ep = sh.block('edge', 30.48, Y0, 38.1, 35.56, right=strobes)
    rp = sh.block('rp2354b', 139.7, Y0, 50.8, 40.64,
                  left=[(n, flip[s]) for n, s in strobes],
                  right=[('S3_EN', b), ('RUN_CTL', i), ('BOOTSEL_CTL', i), ('USB_DM', b), ('USB_DP', b), None,
                         ('PWR_OK', i), ('MBOX', o), ('GAME', o), ('RAM_WE', o), ('LOAD', o), None, (SA_BUS, o)])
    es = sh.block('esp32s3-sd', 246.38, Y0, 50.8, 30.48,
                  left=[('S3_EN', b), ('RUN_CTL', o), ('BOOTSEL_CTL', o), ('USB_DM', b), ('USB_DP', b)],
                  right=[None, ('S3_TXD', o), ('S3_RXD', i), ('S3_IO0', b)])
    us = sh.block('usb-uart', 345.44, Y0, 45.72, 30.48,
                  left=[('S3_EN', o), ('S3_TXD', i), ('S3_RXD', o), ('S3_IO0', o)])
    YG = 116.84
    gl = sh.block('glue', 139.7, YG, 50.8, 33.02,
                  left=[('RD_N', i), ('WR_N', i), ('CE_N', i), ('A12', i), ('A13', i), ('A14', i), ('A15', i)],
                  right=[('LOAD', i), ('RAM_WE', i), ('GAME', i), ('MBOX', i), ('PWR_OK', o), ('SA19', i), None,
                         ('SA19_N', o), ('SRAM_OE_N', o), ('SRAM_WE_N', o)])
    sr = sh.block('sram', 246.38, YG, 50.8, 40.64,
                  left=[None] * 6 + [(SA_BUS, i), ('SA19_N', i), ('SRAM_OE_N', i), ('SRAM_WE_N', i), None,
                                     (A_BUS, i), (D_BUS, b)])
    sh.block('power', 345.44, YG, 45.72, 25.4)
    # edge -> RP: every console line straight across (buses for A and D)
    for n, _ in strobes:
        a, c = ep[n], rp[n]
        (sh.bus if '[' in n else sh.wire)(a, c)
        sh.label((a[0] + 3.81, a[1]), n)
    # A and D also down to the SRAM, under the glue; A12-A15 off the A bus into the glue
    ax, dx = 101.6, 96.52
    ya, yd = 162.56, 165.1
    sh.bus((ax, ep[A_BUS][1]), (ax, ya), (223.52, ya), (223.52, sr[A_BUS][1]), sr[A_BUS])
    sh.bus((dx, ep[D_BUS][1]), (dx, yd), (228.6, yd), (228.6, sr[D_BUS][1]), sr[D_BUS])
    for n in ('A12', 'A13', 'A14', 'A15'):
        p = gl[n]
        sh.entries.append(((ax + 2.54, p[1]), (-2.54, -2.54)))
        sh.wire((ax + 2.54, p[1]), p)
        sh.label((ax + 5.08, p[1]), n)
    # RD, WR, CE also down into the glue
    for n, x in (('RD_N', 121.92), ('WR_N', 116.84), ('CE_N', 111.76)):
        sh.wire((x, ep[n][1]), (x, gl[n][1]), gl[n])
    # RP -> S3: USB, RUN / BOOTSEL, S3_EN (S3_EN on to the USB bridge's auto-program pair)
    for n in ('S3_EN', 'RUN_CTL', 'BOOTSEL_CTL', 'USB_DM', 'USB_DP'):
        sh.wire(rp[n], es[n])
        sh.label((rp[n][0] + 3.81, rp[n][1]), n)
    t = (rp['S3_EN'][0] + 22.86, rp['S3_EN'][1])
    top = Y0 - 7.62
    sh.wire(t, (t[0], top), (330.2, top), (330.2, us['S3_EN'][1]), us['S3_EN'])
    for n in ('S3_TXD', 'S3_RXD', 'S3_IO0'):
        sh.wire(es[n], us[n])
        sh.label((es[n][0] + 3.81, es[n][1]), n)
    # RP -> glue: nested C's down the corridor right of the RP / glue column
    for k, n in enumerate(('LOAD', 'RAM_WE', 'GAME', 'MBOX', 'PWR_OK')):
        x = 200.66 + 2.54 * k
        sh.wire(rp[n], (x, rp[n][1]), (x, gl[n][1]), gl[n])
        sh.label((rp[n][0] + 1.27, rp[n][1]), n)
    # the SRAM bank bus: RP -> SRAM, SA19 off it into the glue
    sx = 215.9
    sh.bus(rp[SA_BUS], (sx, rp[SA_BUS][1]), (sx, sr[SA_BUS][1]), sr[SA_BUS])
    sh.label((rp[SA_BUS][0] + 3.81, rp[SA_BUS][1]), SA_BUS)
    p = gl['SA19']
    sh.entries.append(((sx - 2.54, p[1]), (2.54, -2.54)))
    sh.wire(p, (sx - 2.54, p[1]))
    sh.label((p[0] + 2.54, p[1]), 'SA19')
    # glue -> SRAM: chip select and strobes
    for n in ('SA19_N', 'SRAM_OE_N', 'SRAM_WE_N'):
        sh.wire(gl[n], sr[n])
        sh.label((gl[n][0] + 3.81, gl[n][1]), n)
    # what each block is
    for b in sh.blocks:
        pass
    sh.text((30.48, 190.5), NOTES, 1.524)
    return sh


NOTES = """FujiNet for the Sega Master System / SMS2 - Rev0 (RP2354B).  Signal flow left to right: the console's
cartridge slot -> the RP2354B on the 5V cart bus (+ 1 MB SRAM and its 74HCT glue) -> ESP32-S3 (FujiNet, WiFi,
microSD) -> USB-C / CP2102N.  Power (rails only): console 5V via a P-FET and USB VBUS via an SS34 meet on +5V;
+3V3 buck (S3, SD, bridge); +3V3_RP LDO (every RP2354B supply pin, rises with the console's 5V).
RP pin map: fujinet-firmware pico/sms sms_cart.h; S3 pin map: fujiversal-sms.h; glue: sms_glue_oe / _we
(tools/check_nets.py and tools/check_glue.py hold the netlist to them)."""
