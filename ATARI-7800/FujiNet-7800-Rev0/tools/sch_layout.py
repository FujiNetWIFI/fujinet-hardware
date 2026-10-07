"""How each sheet is drawn: placement and wiring, one function per sheet, and the root's block
diagram.

design.py owns the circuit; these functions only say where each part sits and how its pins are
joined (sch_draw.Sheet), left to right in signal-flow order starting at the cartridge slot: the
console's side on the left of every sheet, the FujiNet / PC side on the right.  The root shows the
slot driving the RP2354B, the glue and the SRAM, the RP talking to the ESP32-S3, the S3 to the USB
bridge.  Parts are addressed by their design.py key (U_RP, C_IOV5, ...), never by reference.
sch_draw.Sheet.check(), gen_sch.check_hierarchy() and gen_sch.netlist_parity() prove the drawing
is exactly design.py's netlist, so a wiring slip here fails the build.
"""
import design as D
from sch_draw import Sheet, Pt, snap

DRAW = {}
A_BUS, D_BUS, SA_BUS = 'A[0..15]', 'D[0..7]', 'SA[13..18]'


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


def tap_tp(sh, key, pt, up=True, fields='right'):
    """A test pad on a T off the wire through pt (pad body above / below the line)."""
    x, y = pt
    ty = y - 5.08 if up else y + 5.08
    sh.place(key, x, ty, rot=0 if up else 180, fields=fields)
    sh.wire(sh.P(key, 1), (x, y))


# =========================================================================
@sheet('edge', 'A3')
def edge(sh):
    """The cartridge slot, drawn by function: everything the console drives leaves on the right,
    address and data as buses, R/W, PHI2 and /HALT as single lines (each with a bring-up pad);
    the two pins the cart drives back come in from the right through their own circuits: /IRQ
    from the RP's GPIO28 through the 2N7002, EAUDIO from its GPIO29 PWM through the RC."""
    J = 'J_EDGE'
    X, Y = 76.2, 127.0
    sh.place(J, X, Y, fields='abovebelow', val_at=(X - 12.7, Y + 72.39, 'left'))
    col = 241.3                               # the page edge every signal leaves through
    bx = 104.14                               # the bus spines
    for nets, name, shape in ((['A%d' % i for i in range(16)], A_BUS, 'output'),
                              (['D%d' % i for i in range(8)], D_BUS, 'bidirectional')):
        top, bot = sh.bus_group([(sh.N(J, n), n) for n in nets], bx)
        sh.bus(top, (col, top[1]))
        sh.hlabel(Pt(col, top[1]), name, 'R', shape)
    # R/W, PHI2, /HALT: straight out, a bring-up pad inline on each
    for k, (net, tp) in enumerate((('RW', 'TP_RW'), ('PHI2', 'TP_PHI2'))):
        p = sh.N(J, net)
        t = (134.62 + 12.7 * k, p[1])
        sh.place(tp, t[0], t[1], fields='right')
        sh.wire(p, t)
        sh.wire(t, (col, p[1]))
        sh.hlabel(Pt(col, p[1]), net, 'R', 'output')
    # /HALT through its 1k at the finger, the pad behind it
    p = sh.N(J, 'HALT_N')
    sh.place('R_HALT', 116.84, p[1], rot=90, fields='above')
    sh.wire(p, sh.N('R_HALT', 'HALT_N'))
    t = (160.02, p[1])
    sh.place('TP_HALT', t[0], t[1], fields='right')
    sh.wire(sh.N('R_HALT', 'HALT_RP'), t)
    sh.wire(t, (col, p[1]))
    sh.hlabel(Pt(col, p[1]), 'HALT_RP', 'R', 'output')
    sh.label((106.68, p[1]), 'HALT_N')
    # /IRQ: the 2N7002's drain on the pin, its gate from GPIO28 (10k down: released at power-on)
    p = sh.N(J, 'IRQ_N')
    sh.place('Q_IRQ', 182.88, p[1] + 10.16, mirror='y', fields='left')
    dr = sh.P('Q_IRQ', 3)
    sh.wire(p, (dr[0], p[1]), dr)
    sh.name((dr[0] - 30.48, p[1]), 'IRQ_N', 'U', 'R')
    gt = sh.P('Q_IRQ', 1)
    rx_ = gt[0] + 12.7
    sh.place('R_IRQ', rx_, gt[1] + 6.35, fields='right')
    sh.wire(gt, (rx_, gt[1]), (col, gt[1]))
    sh.wire(sh.P('R_IRQ', 1), (rx_, gt[1]))
    sh.gnd(sh.P('R_IRQ', 2))
    sh.gnd(sh.P('Q_IRQ', 2))
    sh.hlabel(Pt(col, gt[1]), 'IRQ_GATE', 'R', 'input')
    # EAUDIO: GPIO29 PWM -> 1.5k / 10n low-pass -> 10k level -> 1u DC block -> the pin
    p = sh.N(J, 'EAUDIO')
    x1 = 119.38
    ay = p[1] + 27.94
    tp = (x1, p[1] + 12.7)
    sh.place('TP_EAUDIO', tp[0], tp[1], rot=90, fields='left')
    sh.wire(p, (x1, p[1]), tp)
    sh.wire(tp, (x1, ay))
    chain = [('C_AUDDC', 'EAUDIO', 'AUD_LVL', x1 + 15.24), ('R_AUDLVL', 'AUD_LVL', 'AUD_LP', x1 + 38.1),
             ('R_AUDLP', 'AUD_LP', 'AUD_PWM', x1 + 76.2)]
    prev = (x1, ay)
    for key, a_, b_, x in chain:
        sh.place(key, x, ay, rot=270, fields='above')
        sh.wire(prev, sh.N(key, a_))
        prev = sh.N(key, b_)
        if b_ == 'AUD_LP':
            lp = (x + 19.05, ay)
            sh.wire(prev, lp)
            sh.place('C_AUDLP', lp[0], ay + 7.62, fields='right')
            sh.wire(lp, sh.N('C_AUDLP', 'AUD_LP'))
            sh.gnd(sh.P('C_AUDLP', 2))
            prev = lp
    sh.wire(prev, (col, ay))
    sh.hlabel(Pt(col, ay), 'AUD_PWM', 'R', 'input')
    sh.label((x1 + 5.08, ay), 'EAUDIO')
    sh.label((x1 + 22.86, ay), 'AUD_LVL')
    sh.label((x1 + 45.72, ay), 'AUD_LP')
    # rails: the +5V finger to the console rail (with its pad), the two GND fingers joined (with the
    # scope-ground pad)
    v = sh.P(J, '13')
    m = v.go(5.08)
    sh.wire(v, m)
    sh.place('TP_CONS5V', m[0], m[1], rot=270, fields='right')
    sh.wire(m, (m[0], m[1] - 5.08))
    sh.sup((m[0], m[1] - 5.08), 'CONS_5V')
    g = sorted((sh.P(J, n) for n in ('14', '30')), key=lambda q: q[0])
    a0, a1 = g[0].go(2.54), g[1].go(2.54)
    sh.wire(g[0], a0, a1, g[1])
    gm = (a0[0], a0[1] + 5.08)
    sh.wire(a0, gm)
    sh.place('TP_GNDBUS', gm[0], gm[1], rot=90, fields='left')
    sh.wire(gm, (gm[0], gm[1] + 2.54))
    sh.gnd((gm[0], gm[1] + 2.54))
    sh.text((40.64, 30.48),
            'Atari 7800 32-pin cartridge slot, drawn by function (finger numbers on the pins).  18 positions at 2.54 mm per face;\n'
            'positions 3 and 16 are key slots in the board for the console connector\'s plastic keys.  Pins 1-16 on F.Cu, the component\n'
            'side, which faces the console\'s REAR; pin 1 at the left seen from F.Cu, fingers down; pin k over pin 33-k on B.Cu\n'
            '(tools/edge_geom.py, tools/audit/edge_orientation.py).  No chip select and no reset on this edge: the glue decodes A15-A11.\n'
            'Cart audio: GPIO29 PWM (833 kHz carrier) -> 1.5k / 10n (fc 10.6 kHz) -> 10k level -> 1u -> EAUDIO; the console adds\n'
            '0.1u + 6.8k into its audio sum (C10, R5), as a POKEY cart\'s 1k pull-up + 12k does.  /IRQ: the 2N7002 pulls it low only\n'
            'while GPIO28 is high (the firmware never does); console pull-up R32 2.2k.  /HALT (MARIA\'s weak MOS output) through\n'
            '1k to the RP: observed only.  While the console\'s BIOS is mapped its U4 (74LS08) holds A15, A14, A12 low at this edge.')


# =========================================================================
@sheet('rp2354b')
def rp2354b(sh):
    """RP2354B mirrored, so its bus GPIOs face the cartridge on the left: the address bus, the
    data lines through the 100R packs, R/W, PHI2, /HALT, PWR_OK in; /IRQ and the audio PWM back
    to the slot; the slot table (SRAM A13-A18, ROM_EN, RAM_EN) to the glue and the SRAM.  On the
    right, toward the FujiNet half: A8MASK to the glue, the debug UART, RUN / RESET, USB to the
    S3, BOOTSEL, the crystal, SWD.  Supplies across the top."""
    U = 'U_RP'
    X, Y = 210.82, 152.4
    sh.place(U, X, Y, mirror='y', fields='left', ref_at=(X - 20.32, Y + 62.23, 'left'),
             val_at=(X - 20.32, Y + 64.77, 'left'))
    P = lambda n: sh.P(U, n)
    gp = lambda g: P(D.RP_GPIO_PIN[g])
    net = lambda g: D.RP_GPIO_NET[g]
    lcol, rcol = 129.54, 383.54               # where the nets leave the sheet
    # ---- cart side (left) ---------------------------------------------------
    # D0-D7: each GPIO straight into its 100R (the packs sit on the pin rows), the console
    # side onto the data bus
    rnx = 162.56
    pins_d = []
    for key, g0 in (('RN_D0', 0), ('RN_D4', 4)):
        y0 = gp(g0)[1]
        sh.place(key, rnx, y0 + 5.08, rot=270, mirror='y', fields='above' if g0 == 0 else 'below')
        for k in range(4):
            a = sh.P(key, k + 1)
            sh.wire(gp(g0 + k), a)
            sh.label((a[0] + 2.54, a[1]), net(g0 + k))
            pins_d.append((sh.P(key, 8 - k), 'D%d' % (g0 + k)))
    dbx = 147.32
    dtop, dbot = sh.bus_group(pins_d, dbx, True)
    sh.bus(dtop, (dbx, dtop[1] - 2.54), (lcol, dtop[1] - 2.54))
    sh.hlabel(Pt(lcol, dtop[1] - 2.54), D_BUS, 'L', 'bidirectional')
    # A0-A15 onto the address bus: its spine left of the pin row, leaving the sheet from the middle
    bx = 172.72
    top, bot = sh.bus_group([(gp(g), net(g)) for g in range(8, 24)], bx, True)
    my = snap((top[1] + bot[1]) / 2)
    sh.bus((bx, my), (lcol, my))
    sh.hlabel(Pt(lcol, my), A_BUS, 'L', 'input')
    # strobes in, PWR_OK in from the glue, /IRQ gate and the audio PWM out to the slot,
    # ROM_EN / RAM_EN out to the glue
    shapes = {24: 'input', 25: 'input', 26: 'input', 27: 'input', 28: 'output', 29: 'output',
              38: 'output', 39: 'output'}
    for g, shape in shapes.items():
        p = gp(g)
        sh.wire(p, (lcol, p[1]))
        sh.hlabel(Pt(lcol, p[1]), net(g), 'L', shape)
    # GPIO30: activity LED (1k, red) to GND, on its own row
    p = gp(30)
    sh.place('R_LED', 157.48, p[1], rot=270, fields='above')
    sh.wire(p, sh.P('R_LED', 1))
    sh.place('D_LED', 139.7, p[1], fields='above')
    sh.wire(sh.P('R_LED', 2), sh.P('D_LED', 2))
    sh.label((144.78, p[1]), 'RP_LED_A')
    sh.label((165.1, p[1]), 'RP_LED')
    sh.gnd(sh.P('D_LED', 1), 2.54, rot=270)
    sh.nc(gp(31))
    # GPIO32-37 (SRAM A13-A18) onto the slot bus, leaving the sheet from its middle
    sbx = 172.72
    top, bot = sh.bus_group([(gp(g), net(g)) for g in range(32, 38)], sbx, up=True)
    my = snap((top[1] + bot[1]) / 2)
    sh.bus((sbx, my), (lcol, my))
    sh.hlabel(Pt(lcol, my), SA_BUS, 'L', 'output')
    # ---- FujiNet side (right) -------------------------------------------------
    # GPIO40: A8MASK to the glue (not 5 V tolerant: drives the '14's CMOS input only)
    p = gp(40)
    sh.wire(p, (rcol, p[1]))
    sh.hlabel(Pt(rcol, p[1]), 'A8MASK', 'R', 'output')
    for g in (41, 42, 43, 46, 47):
        sh.nc(gp(g))
    # GPIO44/45: debug UART header (DNP), its pins on the GPIO rows
    p44, p45 = gp(44), gp(45)
    sh.place('J_DBG', p44[0] + 22.86, p44[1] + 2.54, fields='right')
    sh.wire(p44, sh.P('J_DBG', 1))
    sh.wire(p45, sh.P('J_DBG', 2))
    sh.label((p44[0] + 3.81, p44[1]), 'DBG_TX')
    sh.label((p45[0] + 3.81, p45[1]), 'DBG_RX')
    j3 = sh.P('J_DBG', 3)
    sh.wire(j3, (j3[0] - 2.54, j3[1]), (j3[0] - 2.54, j3[1] + 5.08))
    sh.gnd((j3[0] - 2.54, j3[1] + 5.08))
    # RUN: pull-up, test pad, RESET button through the BAT54C (which also resets the S3), the
    # S3's IO4 through 1k
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
    sh.text((X - 63.5, Y + 73.66),
            'fujinet-firmware pico/atari-7800 a78_cart.h: D0-D7 GPIO0-7 (through 100R), A0-A15 GPIO8-23, R/W 24, PHI2 25,\n'
            '/HALT 26 (observed only), PWR_OK 27, /IRQ gate 28, audio PWM 29, LED 30; a78map.h slot word on GPIO32-40 (PIO,\n'
            'indexed by A13-A15): SRAM A13-A18, ROM_EN, RAM_EN, A8MASK.  GPIO40-47 are not 5 V tolerant: A8MASK drives a\n'
            "74HCT14 input only, GPIO44/45 the 3.3 V debug header (DNP).  One 100 nF per IOVDD pin (key C_IOV<pin>: placed\n"
            'at that pin).  RP2350 datasheet 6.3.7: VREG_VIN and IOVDD on one 3.3 V supply (+3V3_RP, the LDO that rises with\n'
            'the console 5V), VREG_AVDD through 33R / 4.7 uF, 3.3 uH from VREG_LX to DVDD (= VREG_FB).')


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


def inp(sh, pin, net, x):
    """An input from another sheet: a wire left from the pin to x and its hierarchical label."""
    sh.wire(pin, (x, pin[1]))
    sh.hlabel(Pt(x, pin[1]), net, 'L', 'input')


@sheet('glue')
def glue(sh):
    """The 5V glue as a wired network, by logic depth left to right: the console 5V sense and the
    inversions; LOW_X and the A15 / A14 / A12 terms, each gated by PWR_OK; CSEL_P = PWR_OK &
    CARTSEL; the strobe stage that makes SRAM /OE and /WE.  The SRAM's A8 mask runs along the
    bottom.  Inputs enter on hierarchical labels on the left (the console's lines) and right (the
    RP's slot-table enables, with their pull-downs); outputs leave on the right."""
    c1, c2, c3, c4, c5 = (106.68 + 50.8 * i for i in range(5))
    lx = 63.5                                 # where the console's lines enter
    rx = c5 + 50.8                            # where the RP's lines enter and the outputs leave
    yA, yB, yC, yD, yE, yW, yO, yG = 45.72, 71.12, 88.9, 109.22, 127.0, 147.32, 165.1, 190.5

    def output(pt, net):
        sh.wire(pt, (rx, pt[1]))
        sh.hlabel(Pt(rx, pt[1]), net, 'R', 'output')

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
    pk = c3 - 17.78                           # the PWR_OK trunk, down to the three gates it qualifies
    sh.wire(ob, (pk, yA))
    output((pk, yA), 'PWR_OK')
    tap_tp(sh, 'TP_PWROK', (c4 + 12.7, yA))
    # ---- rows B, C: A15_P_N = !(A15 & PWR_OK), A14_P_N = !(A14 & PWR_OK)
    i15, o15 = gate(sh, 'U_NAND2', 2, c3, yB)
    i14, o14 = gate(sh, 'U_NAND2', 3, c3, yC)
    inp(sh, i15['A15'][0], 'A15', lx)
    inp(sh, i14['A14'][0], 'A14', lx)
    # ---- row D: A13_N; LOW_X = !(A13_N & A11) = A13 | !A11; LOW_P_N = !(A12 & LOW_X & PWR_OK)
    i13, o13 = gate(sh, 'U_INV', 3, c1, yD)
    inp(sh, i13['A13'][0], 'A13', lx)
    ilx, olx = gate(sh, 'U_NAND2', 1, c2, yD)
    sh.wire(o13, (c2 - 12.7, yD), (c2 - 12.7, ilx['A13_N'][0][1]), ilx['A13_N'][0])
    sh.label((o13[0] + 2.54, yD), 'A13_N')
    p = ilx['A11'][0]
    sh.wire(p, (c1 + 12.7, p[1]), (c1 + 12.7, yD + 10.16), (lx, yD + 10.16))
    sh.hlabel(Pt(lx, yD + 10.16), 'A11', 'L', 'input')
    ilp, olp = gate(sh, 'U_CSEL', 1, c3, yD + 2.54)
    link(sh, olx, ilp['LOW_X'][0], c3 - 12.7)
    sh.label((olx[0] + 2.54, yD), 'LOW_X')
    p = ilp['A12'][0]
    sh.wire(p, (c3 - 15.24, p[1]), (c3 - 15.24, yD - 11.43), (lx, yD - 11.43))
    sh.hlabel(Pt(lx, yD - 11.43), 'A12', 'L', 'input')
    sh.sup(ilp['+5V'][0], '+5V', 2.54, rot=90)
    # PWR_OK down the trunk into the three gates
    for p in (i15['PWR_OK'][0], i14['PWR_OK'][0], ilp['PWR_OK'][0]):
        sh.wire(p, (pk, p[1]))
    sh.wire((pk, yA), (pk, ilp['PWR_OK'][0][1]))
    # ---- column 4: CSEL_P = NAND(A15_P_N, A14_P_N, LOW_P_N) = PWR_OK & CARTSEL
    ics, ocs = gate(sh, 'U_CSEL', 2, c4, yC)
    link(sh, o15, ics['A15_P_N'][0], c4 - 15.24)
    link(sh, o14, ics['A14_P_N'][0], c4 - 12.7)
    link(sh, olp, ics['LOW_P_N'][0], c4 - 17.78)
    sh.sup(ics['+5V'][0], '+5V', 2.54, rot=90)
    sh.label((o15[0] + 2.54, yB), 'A15_P_N')
    sh.label((o14[0] + 2.54, yC), 'A14_P_N')
    sh.label((olp[0] + 1.27, olp[1]), 'LOW_P_N')
    # ---- the strobe stage: SRAM /OE = NAND(CSEL_P, RW, ROM_EN); /WE = NAND(CSEL_P, RW_N, PHI2, RAM_EN)
    ioe, ooe = gate(sh, 'U_STROBE', 1, c5, yE)
    iwe, owe = gate(sh, 'U_STROBE', 2, c5, yW)
    ct = c5 - 17.78                           # the CSEL_P trunk
    sh.wire(ocs, (ct, ocs[1]), (ct, iwe['CSEL_P'][0][1]))
    for p in (ioe['CSEL_P'][0], iwe['CSEL_P'][0]):
        sh.wire(p, (ct, p[1]))
    sh.label((ocs[0] + 2.54, ocs[1]), 'CSEL_P')
    tap_tp(sh, 'TP_CSEL', (ocs[0] + 12.7, ocs[1]))
    sh.sup(ioe['+5V'][0], '+5V', 2.54, rot=90)
    # R/W: straight to /OE, inverted for /WE; PHI2 to /WE (one gate from the strobe)
    irw, orw = gate(sh, 'U_INV', 4, c4, yE + 12.7)
    rw = ioe['RW'][0]
    sh.wire(rw, (c4 - 22.86, rw[1]), (c4 - 22.86, yE + 12.7), irw['RW'][0])
    sh.wire((c4 - 22.86, yE + 12.7), (lx, yE + 12.7))
    sh.hlabel(Pt(lx, yE + 12.7), 'RW', 'L', 'input')
    link(sh, orw, iwe['RW_N'][0], c5 - 22.86)
    sh.label((orw[0] + 1.27, orw[1]), 'RW_N')
    p = iwe['PHI2'][0]
    sh.wire(p, (c5 - 27.94, p[1]), (c5 - 27.94, yW + 12.7), (lx, yW + 12.7))
    sh.hlabel(Pt(lx, yW + 12.7), 'PHI2', 'L', 'input')
    # ROM_EN / RAM_EN from the RP (right), each with its pull-down, down into the strobe gates
    for pin, n, key, yy in ((ioe['ROM_EN'][0], 'ROM_EN', 'R_PDROM', yE - 12.7),
                            (iwe['RAM_EN'][0], 'RAM_EN', 'R_PDRAM', yW + 20.32)):
        jx = c5 - 10.16
        sh.wire(pin, (jx, pin[1]), (jx, yy), (rx - 12.7, yy))
        sh.wire((rx - 12.7, yy), (rx, yy))
        sh.hlabel(Pt(rx, yy), n, 'R', 'input')
        sh.place(key, rx - 12.7, yy + 6.35, fields='right')
        sh.wire(sh.P(key, 1), (rx - 12.7, yy))
        sh.gnd(sh.P(key, 2))
        sh.label((jx + 2.54, yy), n)
    output(ooe, 'SRAM_OE_N')
    output(owe, 'SRAM_WE_N')
    tap_tp(sh, 'TP_OE', (rx - 25.4, ooe[1]))
    tap_tp(sh, 'TP_WE', (rx - 25.4, owe[1]))
    # ---- row G: SRAM A8 = A8 & !A8MASK: A8MASK in from the RP (with its pull-down), inverted,
    # NANDed with A8, inverted again
    im, om = gate(sh, 'U_INV', 5, c3, yG)
    p = im['A8MASK'][0]
    sh.wire(p, (c3 - 15.24, p[1]), (c3 - 15.24, yG + 17.78), (rx - 12.7, yG + 17.78))
    sh.wire((rx - 12.7, yG + 17.78), (rx, yG + 17.78))
    sh.hlabel(Pt(rx, yG + 17.78), 'A8MASK', 'R', 'input')
    sh.place('R_PDA8M', rx - 12.7, yG + 24.13, fields='right')
    sh.wire(sh.P('R_PDA8M', 1), (rx - 12.7, yG + 17.78))
    sh.gnd(sh.P('R_PDA8M', 2))
    sh.label((c3 - 12.7, yG + 17.78), 'A8MASK')
    i8, o8 = gate(sh, 'U_NAND2', 4, c4, yG - 2.54)
    link(sh, om, i8['A8MASK_N'][0], c4 - 12.7)
    sh.label((om[0] + 1.27, om[1]), 'A8MASK_N')
    inp(sh, i8['A8'][0], 'A8', lx)
    isa, osa = gate(sh, 'U_INV', 6, c5, yG - 2.54)
    sh.wire(o8, isa['SA8_N'][0])
    sh.label((o8[0] + 2.54, o8[1]), 'SA8_N')
    output(osa, 'SA8')
    tap_tp(sh, 'TP_SA8', (rx - 25.4, osa[1]))
    # ---- supplies: each package's power unit with its 100 nF
    for i, (key, unit, cap) in enumerate((('U_INV', 7, 'C_INV'), ('U_NAND2', 5, 'C_NAND2'),
                                         ('U_CSEL', 3, 'C_CSEL'), ('U_STROBE', 3, 'C_STROBE'))):
        x, y = c1 - 25.4 + 38.1 * i, 228.6
        sh.place(key, x, y, unit=unit, fields='right')
        sh.sup(sh.P(key, 14), '+5V')
        sh.gnd(sh.P(key, 7))
        sh.place(cap, x + 17.78, y)
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    sh.text((lx, 251.46),
            "fujinet-firmware pico/atari-7800 a78_cart.h: a78_cartsel(), a78_glue_oe(), a78_glue_we(), a78_glue_a8().\n"
            'RW = 1 for a read; ROM_EN, RAM_EN, A8MASK = RP GPIO38, 39, 40 (the PIO slot table; 4.7k pull-downs hold\n'
            'them low until it runs, RP2350-E9); PWR_OK = console +5V present (0.82 x CONS_5V into the 74HCT14).\n'
            'CARTSEL = A15 | A14 | A12 & (A13 | !A11)   ($4000-$FFFF, $1000-$17FF, $3000-$3FFF)\n'
            'CSEL_P = PWR_OK & CARTSEL = NAND(!(A15 & PWR_OK), !(A14 & PWR_OK), !(A12 & LOW_X & PWR_OK))\n'
            'SRAM /OE = !(CSEL_P & RW & ROM_EN)   (no PHI2: MARIA DMA is not PHI2-aligned)\n'
            'SRAM /WE = !(CSEL_P & !RW & PHI2 & RAM_EN)   (PHI2 one gate from /WE);   SRAM A8 = A8 & !A8MASK\n'
            "tools/check_glue.py evaluates this netlist against the firmware's C for every input combination.", 1.27)


# =========================================================================
@sheet('sram', 'A4')
def sram(sh):
    """The AS6C4008 on the 5V rail: the console's address lines, the glue's SRAM A8 and strobes
    and the RP's slot lines in from the left; data straight onto the console's data bus."""
    lcol, rcol = 50.8, 203.2
    U = 'U_SRAM'
    X, Y = 127.0, 104.14
    sh.place(U, X, Y, fields='abovebelow', val_at=(X + 11.43, Y + 31.75, 'left'))
    top, _ = sh.bus_group([(sh.N(U, 'A%d' % i), 'A%d' % i) for i in list(range(8)) + list(range(9, 13))],
                          101.6, up=True)
    sh.bus(top, (lcol, top[1]))
    sh.hlabel(Pt(lcol, top[1]), A_BUS, 'L', 'input')
    p = sh.N(U, 'SA8')
    sh.wire(p, (lcol, p[1]))
    sh.hlabel(Pt(lcol, p[1]), 'SA8', 'L', 'input')
    stop, _ = sh.bus_group([(sh.N(U, 'SA%d' % i), 'SA%d' % i) for i in range(13, 19)], 93.98, up=True)
    sh.bus(stop, (lcol, stop[1]))
    sh.hlabel(Pt(lcol, stop[1]), SA_BUS, 'L', 'input')
    for n in ('SRAM_OE_N', 'SRAM_WE_N'):
        p = sh.N(U, n)
        sh.wire(p, (lcol, p[1]))
        sh.hlabel(Pt(lcol, p[1]), n, 'L', 'input')
    ce = sh.P(U, D.SRAM_PIN['CE#'])
    sh.wire(ce, (ce[0] - 5.08, ce[1]))
    sh.gnd((ce[0] - 5.08, ce[1]), rot=270)
    top, _ = sh.bus_group([(sh.N(U, 'D%d' % i), 'D%d' % i) for i in range(8)], 152.4, up=True)
    sh.bus(top, (rcol, top[1]))
    sh.hlabel(Pt(rcol, top[1]), D_BUS, 'R', 'bidirectional')
    sh.sup(sh.P(U, D.SRAM_PIN['VCC']), '+5V')
    sh.gnd(sh.P(U, D.SRAM_PIN['VSS']))
    for i, c in enumerate(('C_SRAM', 'C_SRAMBULK')):
        sh.place(c, X + 38.1 + 12.7 * i, Y + 15.24)
        sh.sup(sh.P(c, 1), '+5V')
        sh.gnd(sh.P(c, 2))
    sh.text((50.8, 162.56), 'A0-A7, A9-A12 and D0-D7 are the console\'s; SRAM A8 = A8 & !A8MASK (glue sheet); A13-A18 are the\n'
                            "RP's slot lines (GPIO32-37): the 8K page for the slot A13-A15 selects.  /CE is tied active:\n"
                            '/OE and /WE alone decide when the SRAM answers.')


# =========================================================================
@sheet('esp32s3-sd', 'A4')
def esp32s3_sd(sh):
    """The ESP32-S3: reset / boot and its two RP control lines on the left; the UART to the USB
    bridge and native USB to the RP on the right, then the microSD socket (SPI fanned out to the
    socket's pin order) and the status LED."""
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
    # status LED: WS2812C on +5V, data straight from the S3 through 330R
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
    """USB-C on the left; VBUS up onto its rail (ESD, decoupling, the bridge's VBUS sense), CC
    pull-downs, the data pair through its ESD diodes into the CP2102N; the bridge's UART and the
    esptool auto-program pair on the right."""
    J, U = 'J_USB', 'U_UART'
    rcol = 284.48
    sh.place(J, 50.8, 149.86, fields='abovebelow', val_at=(39.37, 172.72, 'right'))
    vb = sh.P(J, 'A4')
    ry = 116.84
    xs = [96.52, 109.22, 121.92]
    sh.wire(vb, (71.12, vb[1]), (71.12, ry), *[(x, ry) for x in xs], (134.62, ry))
    sh.sup((71.12, ry), 'VBUS')
    for key, x in zip(('D_ESDV', 'C_VBUS', 'C_VBUSHF'), xs):
        sh.place(key, x, ry + 3.81, rot=270 if key == 'D_ESDV' else 0, fields='left' if key == 'D_ESDV' else 'right')
        sh.gnd(sh.P(key, 2))
    for pin, key, x, f in (('A5', 'R_CC1', 83.82, 'above'), ('B5', 'R_CC2', 96.52, 'below')):
        p = sh.P(J, pin)
        sh.place(key, x, p[1], rot=90, fields=f)
        sh.wire(p, sh.P(key, 1))
        sh.gnd(sh.P(key, 2), 2.54, rot=90)
        sh.label((p[0] + 2.54, p[1]), pin.replace('A5', 'CC1').replace('B5', 'CC2'))
    dm = [sh.P(J, 'A7'), sh.P(J, 'B7')]
    dp = [sh.P(J, 'A6'), sh.P(J, 'B6')]
    for a, b in (dm, dp):
        sh.wire(a, (68.58, a[1]), (68.58, b[1]), b)
    sh.place(U, 190.5, 160.02, fields='abovebelow', val_at=(204.47, 196.85, 'left'))
    cdm, cdp = sh.P(U, 5), sh.P(U, 4)
    sh.wire((68.58, dm[0][1]), (114.3, dm[0][1]), cdm)
    sh.wire((68.58, dp[0][1]), (99.06, dp[0][1]), (167.64, dp[0][1]), (167.64, cdp[1]), cdp)
    sh.place('D_ESDM', 114.3, dm[0][1] - 3.81, rot=90, fields='right')
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
    sns = sh.P(U, 8)
    sh.place('R_VBSH', 134.62, ry + 3.81, fields='right')
    sh.place('R_VBSL', 144.78, sns[1] - 3.81, rot=180, fields='right')
    sh.wire(sh.P('R_VBSH', 2), (134.62, sns[1]), sh.P('R_VBSL', 1), sns)
    sh.gnd(sh.P('R_VBSL', 2), rot=180)
    sh.label((149.86, sns[1]), 'VBUS_SNS')
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
    for pad, n, shape in ((26, 'S3_RXD', 'output'), (25, 'S3_TXD', 'input')):
        p = sh.P(U, pad)
        sh.wire(p, (rcol, p[1]))
        sh.hlabel(Pt(rcol, p[1]), n, 'R', shape)
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
    """Left to right: the console's 5 V (from the slot's pin 13) through the P-FET and USB VBUS
    through the Schottky meet on +5V; +5V feeds the 3.3 V buck (S3, bridge, SD) and the RP's own
    fast LDO (+3V3_RP).  Bring-up pads on each rail."""
    y5, yv = 88.9, 116.84
    sh.place('Q_CONS', 60.96, y5 + 2.54, rot=90, fields='above')
    d, s_, g = sh.P('Q_CONS', 3), sh.P('Q_CONS', 2), sh.P('Q_CONS', 1)
    sh.wire((20.32, y5), (33.02, y5), (40.64, y5), (50.8, y5), d)
    sh.sup((20.32, y5), 'CONS_5V')
    sh.flag((50.8, y5), 'CONS_5V')
    sh.place('C_CONS', 33.02, y5 + 3.81, fields='left')
    sh.gnd(sh.P('C_CONS', 2))
    sh.place('C_CONSHF', 40.64, y5 + 3.81, fields='right')
    sh.gnd(sh.P('C_CONSHF', 2))
    sh.wire((20.32, 137.16), (30.48, 137.16))
    sh.gnd((20.32, 137.16))
    sh.flag((30.48, 137.16), 'GND')
    sh.place('D_VBUS', 76.2, yv, rot=180, fields='below')
    sh.wire((25.4, yv), (35.56, yv), (45.72, yv), (g[0], yv), sh.P('D_VBUS', 2))
    sh.wire((g[0], yv), g)
    sh.sup((25.4, yv), 'VBUS')
    sh.flag((45.72, yv), 'VBUS')
    sh.place('R_VBPD', 35.56, yv + 3.81, fields='left')
    sh.gnd(sh.P('R_VBPD', 2))
    k = sh.P('D_VBUS', 1)
    sh.wire(k, (86.36, yv), (86.36, y5))
    caps = [('C_BIN1', 96.52), ('C_BIN2', 106.68), ('C_5VBULK', 116.84), ('C_BINHF', 127.0)]
    sh.wire(s_, (86.36, y5), *[(x, y5) for _, x in caps], (134.62, y5), (139.7, y5), (147.32, y5))
    sh.sup((86.36, y5), '+5V')
    sh.flag((139.7, y5), '+5V')
    for c, x in caps:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    tap_tp(sh, 'TP_5V', (91.44, y5))
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
    sh.wire(sh.P('L_BUCK', 2), (201.93, y5), *[(x, y5) for _, x in out], (229.87, y5))
    sh.wire(fb, (172.72, fb[1]), (172.72, 106.68), (201.93, 106.68), (201.93, y5))
    sh.sup((201.93, y5), '+3V3')
    sh.flag((229.87, y5), '+3V3')
    for c, x in out:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    tap_tp(sh, 'TP_3V3', (222.25, y5))
    L = 'U_LDO'
    sh.place(L, 152.4, 142.24, fields='abovebelow', ref_at=(144.78, 132.08, 'left'), val_at=(144.78, 134.62, 'left'))
    vin, en, vo = sh.P(L, 1), sh.P(L, 3), sh.P(L, 5)
    sh.wire((134.62, y5), (134.62, vin[1]), (137.16, vin[1]), (142.24, vin[1]), vin)
    sh.wire(en, (142.24, en[1]), (142.24, vin[1]))
    sh.place('C_LDOIN', 137.16, vin[1] + 3.81, fields='left')
    sh.gnd(sh.P('C_LDOIN', 2))
    sh.gnd(sh.P(L, 2))
    sh.nc(sh.P(L, 4))
    sh.wire(vo, (167.64, vo[1]), (172.72, vo[1]), (182.88, vo[1]))
    sh.place('C_LDOOUT', 167.64, vo[1] + 3.81)
    sh.gnd(sh.P('C_LDOOUT', 2))
    sh.sup((172.72, vo[1]), '+3V3_RP')
    sh.place('TP_3V3RP', 182.88, vo[1] - 5.08, fields='right')
    sh.wire(sh.P('TP_3V3RP', 1), (182.88, vo[1]))
    sh.text((20.32, 162.56),
            'Console 5V (slot pin 13, CONS_5V) through the AO3401A (gate = VBUS: fully on without USB, body diode only with\n'
            'USB, so nothing back-feeds the console); USB VBUS through the SS34; R_VBPD 4.7k holds the gate low against the\n'
            "SS34's reverse leakage.  +5V: SRAM, glue, WS2812, buck, RP LDO.  +3V3 (buck): S3, microSD, CP2102N.  +3V3_RP\n"
            '(LDO, rises with the 5V rail): every RP2354B supply pin, so its 5V-tolerant pads are powered before the bus is.')


# =========================================================================
def draw_root(syms):
    """The block diagram, read from the cartridge slot outward: the slot on the left; what it
    drives -- the RP2354B bus controller, the glue that decodes it, the SRAM that answers it;
    then the ESP32-S3 and the USB bridge toward the PC; power below."""
    sh = KSheet('root', syms, [], 'A3')
    i, o, b = 'input', 'output', 'bidirectional'
    edge_pins = [('HALT_RP', o), ('IRQ_GATE', i), ('AUD_PWM', i), None, ('RW', o), ('PHI2', o), None,
                 (D_BUS, b), (A_BUS, o)]
    flip = {i: o, o: i, b: b}
    Y0 = 45.72
    ep = sh.block('edge', 30.48, Y0, 33.02, 30.48, right=edge_pins)
    rp = sh.block('rp2354b', 124.46, Y0, 50.8, 40.64,
                  left=[(e[0], flip[e[1]]) if e else None for e in edge_pins],
                  right=[('S3_EN', b), ('RUN_CTL', i), ('BOOTSEL_CTL', i), ('USB_DM', b), ('USB_DP', b), None,
                         (SA_BUS, o), None, ('PWR_OK', i), ('ROM_EN', o), ('RAM_EN', o), ('A8MASK', o)])
    es = sh.block('esp32s3-sd', 254.0, Y0, 50.8, 30.48,
                  left=[('S3_EN', b), ('RUN_CTL', o), ('BOOTSEL_CTL', o), ('USB_DM', b), ('USB_DP', b)],
                  right=[None, ('S3_TXD', o), ('S3_RXD', i), ('S3_IO0', b)])
    us = sh.block('usb-uart', 350.52, Y0, 45.72, 30.48,
                  left=[('S3_EN', o), ('S3_TXD', i), ('S3_RXD', o), ('S3_IO0', o)])
    YG = 116.84
    gl = sh.block('glue', 124.46, YG, 50.8, 40.64,
                  left=[('RW', i), ('PHI2', i), None, ('A8', i), ('A11', i), ('A12', i), ('A13', i), ('A14', i),
                        ('A15', i)],
                  right=[('A8MASK', i), ('RAM_EN', i), ('ROM_EN', i), ('PWR_OK', o), None,
                         ('SA8', o), ('SRAM_OE_N', o), ('SRAM_WE_N', o)])
    sr = sh.block('sram', 254.0, YG, 50.8, 40.64,
                  left=[(SA_BUS, i), None, None, None, None, ('SA8', i), ('SRAM_OE_N', i), ('SRAM_WE_N', i), None,
                        (A_BUS, i), (D_BUS, b)])
    sh.block('power', 350.52, YG, 45.72, 25.4)
    # slot -> RP: every console line straight across (buses for A and D); /IRQ and audio back
    for e in edge_pins:
        if e:
            n = e[0]
            (sh.bus if '[' in n else sh.wire)(ep[n], rp[n])
            sh.label((ep[n][0] + 3.81, ep[n][1]), n)
    # A and D also down to the SRAM under the glue; A8, A11-A15 off the A bus into the glue
    ax, dx = 91.44, 86.36
    ya, yd = 170.18, 172.72
    sh.bus((ax, ep[A_BUS][1]), (ax, ya), (231.14, ya), (231.14, sr[A_BUS][1]), sr[A_BUS])
    sh.bus((dx, ep[D_BUS][1]), (dx, yd), (236.22, yd), (236.22, sr[D_BUS][1]), sr[D_BUS])
    for n in ('A8', 'A11', 'A12', 'A13', 'A14', 'A15'):
        p = gl[n]
        sh.entries.append(((ax + 2.54, p[1]), (-2.54, -2.54)))
        sh.wire((ax + 2.54, p[1]), p)
        sh.label((ax + 5.08, p[1]), n)
    # R/W and PHI2 also down into the glue
    for n, x in (('RW', 111.76), ('PHI2', 106.68)):
        sh.wire((x, ep[n][1]), (x, gl[n][1]), gl[n])
    # RP -> S3: USB, RUN / BOOTSEL, S3_EN (S3_EN on to the USB bridge's auto-program pair)
    for n in ('S3_EN', 'RUN_CTL', 'BOOTSEL_CTL', 'USB_DM', 'USB_DP'):
        sh.wire(rp[n], es[n])
        sh.label((rp[n][0] + 3.81, rp[n][1]), n)
    t = (rp['S3_EN'][0] + 22.86, rp['S3_EN'][1])
    top = Y0 - 7.62
    sh.wire(t, (t[0], top), (335.28, top), (335.28, us['S3_EN'][1]), us['S3_EN'])
    for n in ('S3_TXD', 'S3_RXD', 'S3_IO0'):
        sh.wire(es[n], us[n])
        sh.label((es[n][0] + 3.81, es[n][1]), n)
    # RP <-> glue: nested C's down the corridor right of the RP / glue column
    for k, n in enumerate(('A8MASK', 'RAM_EN', 'ROM_EN', 'PWR_OK')):
        x = 185.42 + 2.54 * k
        sh.wire(rp[n], (x, rp[n][1]), (x, gl[n][1]), gl[n])
        sh.label((rp[n][0] + 1.27, rp[n][1]), n)
    # the slot bus: RP -> SRAM
    sx = 205.74
    sh.bus(rp[SA_BUS], (sx, rp[SA_BUS][1]), (sx, sr[SA_BUS][1]), sr[SA_BUS])
    sh.label((rp[SA_BUS][0] + 3.81, rp[SA_BUS][1]), SA_BUS)
    # glue -> SRAM: A8 and the strobes
    for n in ('SA8', 'SRAM_OE_N', 'SRAM_WE_N'):
        sh.wire(gl[n], sr[n])
        sh.label((gl[n][0] + 3.81, gl[n][1]), n)
    sh.text((30.48, 190.5), NOTES, 1.524)
    return sh


NOTES = """FujiNet for the Atari 7800 - Rev0 (RP2354B).  Read from the cartridge slot outward: the console's 32-pin slot ->
the RP2354B on the 5V cart bus (boot block, mailbox, POKEY, and the PIO slot table) with the 512K SRAM it pages and
the 74HCT glue that decodes the console's address for it -> ESP32-S3 (FujiNet, WiFi, microSD) -> USB-C / CP2102N.
Power (rails only): console 5V via a P-FET and USB VBUS via an SS34 meet on +5V; +3V3 buck (S3, SD, bridge);
+3V3_RP LDO (every RP2354B supply pin, rises with the console's 5V).
RP pin map: fujinet-firmware pico/atari-7800 a78_cart.h + a78map.h; S3 pin map: fujiversal-atari7800.h; glue:
a78_cartsel / a78_glue_oe / _we / _a8 (tools/check_nets.py and tools/check_glue.py hold the netlist to them).
Edge: 18 positions with key slots at 3 and 16; pins 1-16 on the component side, facing the console's rear."""
