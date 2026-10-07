"""How each sheet is drawn: placement and wiring, one function per sheet.

design.py owns the circuit; these functions only say where each part sits
and how its pins are joined (sch_draw.Sheet), left to right in signal-flow
order.  sch_draw.Sheet.check() and gen_sch.netlist_parity() prove the drawing
is exactly design.py's netlist, so a wiring slip here fails the build.

The RP2354B core and the ESP32-S3 / USB-UART / power sheets are the NES / SMS
Rev0 drawings: those parts are declared in the same order as on those boards,
and the three FujiNet-side sheets are drawn under the NES references
(NES_FIRST) and renamed to this board's afterwards.
"""
import design as D
import sch_draw
from sch_draw import Sheet, Pt as Pt_

DRAW = {}

# sheets drawn by the NES Rev0 functions: first NES reference number per prefix
NES_FIRST = {
    'esp32s3-sd': {'U': 11, 'C': 32, 'R': 14, 'SW': 3, 'J': 2, 'RN': 3, 'D': 3},
    'usb-uart': {'J': 3, 'R': 17, 'D': 4, 'C': 37, 'U': 12},
    'power': {'Q': 1, 'D': 7, 'C': 41, 'U': 14, 'L': 2},
}


def sheet(stem, paper='A3'):
    def deco(f):
        DRAW[stem] = (f, paper)
        return f
    return deco


def draw(stem, syms, parts):
    f, paper = DRAW[stem]
    sh = Sheet(stem, syms, parts, paper)
    alias = {}
    if stem in NES_FIRST:
        first = {}
        for p in parts:
            first.setdefault(p.prefix, int(p.ref[len(p.prefix):]))
        for p in parts:
            k = int(p.ref[len(p.prefix):]) - first[p.prefix]
            alias['%s%d' % (p.prefix, NES_FIRST[stem][p.prefix] + k)] = p.ref
        sh.parts = {nes: sh.parts[ref] for nes, ref in alias.items()}
    f(sh)
    if alias:
        placed = {}
        for (r, u), d in sh.placed.items():
            d['ref'] = alias[r]
            placed[(alias[r], u)] = d
        sh.placed = placed
        sh.parts = {p.ref: p for p in parts}
    return sh


def gate(sh, ref, unit, x, y, fields='above'):
    """One gate unit, every input and the output on a label (rails as symbols;
    two inputs on one net joined and labelled once)."""
    d = sh.place(ref, x, y, unit=unit, fields=fields)
    p = sh.parts[ref]
    by_net = {}
    for num, pt in sorted(d['pins'].items(), key=lambda kv: kv[1][1]):
        if pt.dx < 0:
            by_net.setdefault(p.pins[num], []).append(pt)
        else:
            sh.tag(pt, p.pins[num], shape='output')
    for net, pts in by_net.items():
        if net == 'GND':
            for pt in pts:
                sh.gnd(pt, 2.54, rot=270)
        elif net == '+5V':
            for pt in pts:
                sh.sup(pt, '+5V', n=2.54, rot=90)
        elif len(pts) == 1:
            sh.tag(pts[0], net, shape='input')
        else:
            jx = pts[0][0] - 2.54
            for pt in pts:
                sh.wire(pt, (jx, pt[1]))
            sh.wire((jx, pts[0][1]), (jx, pts[-1][1]))
            my = (pts[0][1] + pts[-1][1]) / 2
            sh.wire((jx, my), (jx - 2.54, my))
            sh.glabel((jx - 2.54, my), net, 'L', 'input')
    return d




# =========================================================================
@sheet('edge')
def edge(sh):
    """The console edge on the left; everything it carries leaves on the right:
    address and data as buses, R/W, PHI2, /HALT, /IRQ as labels; edge pin 18
    takes the cart audio from the RP's PWM through the RC chain on this sheet."""
    J = 'J1'
    X, Y = 60.96, 147.32
    sh.place(J, X, Y, fields='abovebelow', ref_at=(X - 11.43, Y - 2.54, 'right'), val_at=(X - 11.43, Y, 'right'))
    col = 104.14                              # where every signal leaves the sheet
    bx = 91.44                                # the bus spines
    for nets, name, shape in ((['A%d' % i for i in range(16)], 'A[0..15]', 'output'),
                              (['D%d' % i for i in range(8)], 'D[0..7]', 'bidirectional')):
        top, bot = sh.bus_group([(sh.N(J, n), n) for n in nets], bx)
        sh.bus(top, (col, top[1]))
        sh.glabel((col, top[1]), name, 'R', shape)
    for net, shape in (('RW', 'output'), ('PHI2', 'output'), ('HALT_N', 'output'), ('IRQ_N', 'input')):
        p = sh.N(J, net)
        sh.wire(p, (col, p[1]))
        sh.glabel((col, p[1]), net, 'R', shape)
    # cart audio, below the edge: AUD_PWM -> 1.5k / 10n low-pass -> 10k level -> 1u DC block -> pin 18
    p = sh.N(J, 'EAUDIO')
    y = p[1] + 10.16
    sh.place('C22', 83.82, y, rot=270, fields='below')           # DC block
    sh.place('R13', 99.06, y, rot=270, fields='below')           # level
    sh.place('R12', 121.92, y, rot=270, fields='below')          # low-pass R
    sh.wire(p, (76.2, p[1]), (76.2, y), sh.P('C22', 2))
    sh.wire(sh.P('C22', 1), sh.P('R13', 2))
    node = (110.49, y)
    sh.wire(sh.P('R13', 1), node, sh.P('R12', 2))
    sh.place('C21', node[0], y + 3.81, fields='right')
    sh.gnd(sh.P('C21', 2))
    sh.tag(sh.P('R12', 1), 'AUD_PWM', n=5.08, shape='input')
    sh.name((76.2, p[1] + 5.08), 'EAUDIO', 'R', 'R')
    sh.name((91.44, y), 'AUD_LVL', 'U', 'R')
    sh.name((113.03, y), 'AUD_LP', 'U', 'R')
    # rails: +5V finger to the console rail, both GND fingers joined
    sh.sup(sh.P(J, '13'), 'CONS_5V')
    g = [sh.P(J, n) for n in ('14', '30')]
    sh.wire(g[0], g[0].go(2.54), g[1].go(2.54), g[1])
    sh.gnd(g[0].go(2.54))
    sh.text((30.48, 30.48), 'Atari 7800 32-pin cartridge edge, drawn by function (finger numbers on the pins).\n'
                            'Pins 1-16 face pins 32-17 (k over 33-k); 3-14 and 19-30 are the 2600 edge.  ASSUMED, verify\n'
                            'on a real cart PCB: pins 1-16 on the console-rear face, pin 1 at the LEFT seen from that face\n'
                            'with the fingers down.  No chip select, no reset: the glue decodes A15-A11 itself.')
    sh.text((30.48, 213.36), 'Cart audio: GPIO29 PWM (833 kHz carrier) -> 1.5k / 10n (fc 10.6 kHz) -> 10k -> 1u -> EAUDIO.\n'
                             'The 10k level is PROVISIONAL (match a POKEY cart on a real console); the 1u keeps the\n'
                             "console's audio node at its no-cart DC level.")


# =========================================================================
@sheet('rp2354b')
def rp2354b(sh):
    """RP2354B in the middle: the cart bus leaves on the right (data through the
    100R packs, address bus, control lines and the slot table on labels / a bus),
    A8MASK and the debug UART on the left; clock, reset / BOOTSEL, USB to the S3
    and SWD on the left; the +3V3_RP decoupling row and the core regulator
    (LX -> inductor -> DVDD) across the top -- the NES Rev0 drawing of the core."""
    U = 'U1'
    X, Y = 215.9, 160.02
    sh.place(U, X, Y, fields='left', ref_at=(X - 27.94, Y + 63.5, 'left'), val_at=(X - 27.94, Y + 66.04, 'left'))
    P = lambda n: sh.P(U, n)
    # ---- +3V3_RP: every IO supply pin up to one rail, the decoupling row on it
    ry = 81.28
    for n in (68, 59, 69, 50, 64):                    # USB_OTP_VDD ADC_AVDD QSPI_IOVDD IOVDD VREG_VIN
        sh.wire(P(n), (P(n)[0], ry))
    caps = ['C%d' % i for i in range(1, 14)]          # 8x IOVDD, QSPI, OTP, ADC, 10u bulk, 4.7u VREG_VIN
    xs = [187.96 - 12.7 * (len(caps) - 1 - i) for i in range(len(caps))]
    for c, x in zip(caps, xs):
        sh.place(c, x, ry + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.wire(*sorted({(x, ry) for x in xs} | {(P(n)[0], ry) for n in (61, 68, 59, 69, 50, 64)}))
    sh.sup((xs[0], ry), '+3V3_RP')
    # VREG_AVDD: 33R off the rail, 4.7u to GND
    av = P(61)
    sh.place('R1', av[0], ry + 7.62 + 3.81, fields='left')
    sh.wire((av[0], ry), sh.P('R1', 1))
    node = (av[0], 101.6)
    sh.wire(sh.P('R1', 2), node, av)
    sh.place('C18', 172.72, node[1] + 3.81, fields='left')
    sh.wire(node, sh.P('C18', 1))
    sh.gnd(sh.P('C18', 2))
    sh.flag(sh.P('C18', 1), 'VREG_AVDD')
    sh.name((190.5, node[1]), 'VREG_AVDD', 'D', 'L')
    # core SMPS: LX up and over to the inductor, DVDD back down to FB and the DVDD pins
    lx, fb, dv = P(63), P(65), P(10)
    ly = 86.36
    sh.place('L1', 231.14, ly, rot=270, fields='below')
    sh.wire(lx, (lx[0], ly), sh.P('L1', 2))
    sh.name((lx[0], ly), 'RP_LX', 'U', 'R')
    dcaps = ['C14', 'C15', 'C16', 'C17']
    dx = [241.3 + 12.7 * i for i in range(4)]
    sh.wire(sh.P('L1', 1), (236.22, ly), *[(x, ly) for x in dx])
    for c, x in zip(dcaps, dx):
        sh.place(c, x, ly + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.flag((dx[-1], ly), 'DVDD')
    sh.wire(dv, (dv[0], 96.52), (236.22, 96.52), (236.22, ly))
    sh.wire(fb, (fb[0], 99.06), (dv[0], 99.06))
    sh.name((238.76, ly), 'DVDD', 'U', 'R')
    # ground pins
    g, pg = P(81), P(62)
    sh.wire(pg, pg.go(2.54), g.go(2.54))
    sh.wire(g, g.go(2.54))
    sh.gnd(g.go(2.54))
    # ---- cart side (right): GPIO0-7 onto RP_D[0..7] (the 100R packs lower right),
    # the address bus, the control lines on labels, the slot table out on SA[13..18]
    col, bx = 279.4, 256.54
    lcol = 119.38
    gp = lambda g: sh.P(U, D.RP_GPIO_PIN[g])
    net_of = lambda g: D.RP_GPIO_NET[g]
    rbx = 251.46
    top, _ = sh.bus_group([(gp(g), net_of(g)) for g in range(8)], rbx, True)
    sh.bus(top, (rbx, top[1] - 5.08), (rbx + 7.62, top[1] - 5.08))
    sh.glabel((rbx + 7.62, top[1] - 5.08), 'RP_D[0..7]', 'R', 'bidirectional')
    top, _ = sh.bus_group([(gp(g), net_of(g)) for g in range(8, 24)], bx, True)
    sh.bus(top, (col, top[1]))
    sh.glabel((col, top[1]), 'A[0..15]', 'R', 'input')
    for g, shape in ((24, 'input'), (25, 'input'), (26, 'input'), (27, 'input'), (28, 'output'),
                     (29, 'output'), (30, 'output'), (38, 'output'), (39, 'output')):
        sh.tag(gp(g), net_of(g), shape=shape)
    sh.nc(gp(31))
    top, _ = sh.bus_group([(gp(g), net_of(g)) for g in range(32, 38)], bx, True)
    sh.bus(top, (col, top[1]))
    sh.glabel((col, top[1]), 'SA[13..18]', 'R', 'output')
    # the 100R packs: RP_D[0..7] in on the left, the console's D[0..7] out on the right
    rnx, lbx, dbx = 284.48, 271.78, 297.18
    pins_l, pins_r = [], []
    for ref, y0, g0 in (('RN1', 223.52, 0), ('RN2', 241.3, 4)):
        sh.place(ref, rnx, y0, rot=270, fields='above')
        for k in range(4):
            pins_l.append((sh.P(ref, k + 1), net_of(g0 + k)))
            pins_r.append((sh.P(ref, 8 - k), 'D%d' % (g0 + k)))
    ltop, _ = sh.bus_group(pins_l, lbx, True)
    sh.bus(ltop, (lbx, ltop[1] - 2.54))
    sh.glabel((lbx, ltop[1] - 2.54), 'RP_D[0..7]', 'U', 'bidirectional')
    dtop, _ = sh.bus_group(pins_r, dbx, True)
    sh.bus(dtop, (dbx, dtop[1] - 2.54), (dbx + 7.62, dtop[1] - 2.54))
    sh.glabel((dbx + 7.62, dtop[1] - 2.54), 'D[0..7]', 'R', 'bidirectional')
    # left: A8MASK (the slot table's ninth bit), the 3.3 V debug UART; GPIO41-43, 46, 47 unused
    sh.tag(gp(40), net_of(40), shape='output')
    sh.tag(gp(44), net_of(44), shape='output')
    sh.tag(gp(45), net_of(45), shape='input')
    for g in (41, 42, 43, 46, 47):
        sh.nc(gp(g))
    # ---- activity LED, /IRQ pull-down, debug UART header (lower left, on labels)
    ly = 248.92
    sh.place('R10', 134.62, ly, rot=90, fields='above')
    sh.place('D2', 147.32, ly, rot=180, fields='below')
    sh.tag(sh.P('R10', 1), 'RP_LED', shape='input')
    sh.wire(sh.P('R10', 2), sh.P('D2', 2))
    sh.name((140.97, ly), 'RP_LED_A', 'U', 'R', n=3.81)
    sh.gnd(sh.P('D2', 1), 2.54, rot=90)
    q = 'Q1'
    sh.place(q, 200.66, ly, fields='right')
    g = sh.P(q, 1)
    sh.wire(g, (190.5, g[1]), (182.88, g[1]))
    sh.glabel((182.88, g[1]), 'IRQ_GATE', 'L', 'input')
    sh.place('R11', 190.5, g[1] + 3.81, fields='left')
    sh.gnd(sh.P('R11', 2))
    sh.gnd(sh.P(q, 2))
    d = sh.P(q, 3)
    sh.wire(d, (d[0], d[1] - 2.54), (213.36, d[1] - 2.54))
    sh.glabel((213.36, d[1] - 2.54), 'IRQ_N', 'R', 'output')
    J = 'J2'
    sh.place(J, 241.3, ly, mirror='y', fields='left')
    sh.tag(sh.P(J, 1), 'DBG_TX', shape='input')
    sh.tag(sh.P(J, 2), 'DBG_RX', shape='output')
    sh.gnd(sh.P(J, 3), 2.54, rot=90)
    sh.text((127.0, 264.16), 'Activity LED (GPIO30).  Console /IRQ: the 2N7002 pulls it low only while GPIO28 is high,\n'
                            'which the firmware never does; the 10k holds the gate low from power-on.\n'
                            'RP debug UART J2 (DNP, 3.3 V only): 1 TX GPIO44, 2 RX GPIO45, 3 GND.')
    # ---- RUN: pull-up, test pad, RESET button through the BAT54C (also resets the S3), S3 IO4
    run = P(35)
    a = (185.42, run[1]); b = (175.26, run[1]); c = (154.94, run[1]); d = (139.7, run[1])
    sh.wire(run, a, b, (c[0] + 7.62, c[1]), c)
    sh.place('R3', a[0], a[1] - 3.81, fields='left')
    sh.sup(sh.P('R3', 1), '+3V3_RP')
    sh.wire(b, (b[0], b[1] - 2.54))
    sh.place('TP4', b[0], b[1] - 2.54, fields='left')
    sh.place('D1', 147.32, 111.76, rot=180, fields='below')
    sh.wire(c, sh.P('D1', 1))
    sh.place('R6', d[0] - 3.81, d[1], rot=90, fields='above')
    sh.wire(c, sh.P('R6', 2))
    sh.tag(sh.P('R6', 1), 'RUN_CTL', n=sh.P('R6', 1)[0] - lcol, shape='input')
    sh.name((c[0] + 7.62, c[1]), 'RUN', 'D', 'R')
    sh.wire(sh.P('D1', 2), (lcol, sh.P('D1', 2)[1]))
    sh.glabel((lcol, sh.P('D1', 2)[1]), 'S3_EN', 'L', 'bidirectional')
    k = sh.P('D1', 3)
    sh.place('SW1', k[0] - 5.08, 101.6, mirror='y', fields='above')
    sh.wire(k, (k[0], 101.6), sh.P('SW1', 1))
    sh.gnd(sh.P('SW1', 2))
    sh.name((k[0], 104.14), 'RST_BTN', 'R', 'R')
    # ---- USB to the S3 (RP = device): 27R series pair
    dm, dp = P(66), P(67)
    sh.place('R9', 160.02, dm[1], rot=90, fields='above')
    sh.place('R8', 152.4, dp[1], rot=90, fields='below')
    sh.wire(dm, sh.P('R9', 2)); sh.wire(dp, sh.P('R8', 2))
    sh.name((182.88, dm[1]), 'RP_USB_DM', 'U', 'L')
    sh.name((180.34, dp[1]), 'RP_USB_DP', 'D', 'L')
    for r, net in (('R9', 'USB_DM'), ('R8', 'USB_DP')):
        p = sh.P(r, 1)
        sh.wire(p, (lcol, p[1]))
        sh.glabel((lcol, p[1]), net, 'L', 'bidirectional')
    # ---- QSPI_SS (BOOTSEL): button branch, S3 IO5 branch, pull-up at the end of the row
    ss = P(75)
    q = ss[1]
    sh.wire(ss, (185.42, q), (170.18, q), (152.4, q), (146.05, q))
    sh.place('R5', 170.18, q + 3.81, fields='left')
    sh.place('SW2', 162.56, q + 7.62, mirror='y', fields='below')
    sh.wire(sh.P('R5', 2), (168.91, q + 7.62), sh.P('SW2', 1))
    sh.gnd(sh.P('SW2', 2), 2.54)
    sh.name((168.91, q + 7.62), 'BOOTSEL_BTN', 'D', 'R')
    sh.place('R7', 152.4, q + 3.81, rot=180, fields='left')
    p = sh.P('R7', 1)
    sh.wire((152.4, q), sh.P('R7', 2))
    sh.wire(p, (p[0], p[1] + 2.54))
    sh.tag(Pt_(p[0], p[1] + 2.54, -1, 0), 'BOOTSEL_CTL', n=p[0] - lcol, shape='input')
    sh.place('R4', 142.24, q, rot=90, fields='below')
    sh.sup(sh.P('R4', 1), '+3V3_RP')
    sh.name((185.42, q), 'QSPI_SS', 'D', 'L')
    for n in (71, 72, 74, 73, 70):
        sh.nc(P(n))
    # ---- 12 MHz crystal: XIN straight to the crystal, XOUT through the 1k
    xi, xo = P(30), P(31)
    sh.place('Y1', 160.02, xi[1] + 3.81, rot=270, fields='right')
    sh.wire(xi, sh.P('Y1', 1))
    sh.place('C19', 137.16, xi[1] + 3.81, fields='left')
    sh.wire(sh.P('Y1', 1), sh.P('C19', 1))
    sh.gnd(sh.P('C19', 2))
    sh.gnd(sh.P('Y1', 2))
    sh.place('R2', 175.26, xo[1], rot=270, fields='above')
    sh.wire(xo, sh.P('R2', 1))
    sh.wire(sh.P('R2', 2), (162.56, xo[1]), (160.02, xo[1]), (147.32, xo[1]))
    sh.wire(sh.P('Y1', 3), (160.02, xo[1]))
    sh.place('C20', 147.32, xo[1] + 3.81, fields='left')
    sh.gnd(sh.P('C20', 2))
    sh.name((180.34, xi[1]), 'XIN', 'U', 'L')
    sh.name((182.88, xo[1]), 'XOUT', 'D', 'R')
    sh.name((162.56, xo[1]), 'XOUT_Y', 'D', 'L')
    # ---- SWD test pads
    sc, sd = P(33), P(34)
    sh.place('TP1', 170.18, sc[1], rot=90, fields='above')
    sh.place('TP2', 160.02, sd[1], rot=90, fields='below')
    sh.wire(sc, sh.P('TP1', 1)); sh.wire(sd, sh.P('TP2', 1))
    sh.name((185.42, sc[1]), 'SWCLK', 'U', 'L')
    sh.name((182.88, sd[1]), 'SWDIO', 'D', 'L')
    # ground test pad
    sh.place('TP3', 205.74, 228.6, fields='left')
    sh.gnd(sh.P('TP3', 1))



# =========================================================================
@sheet('sram')
def sram(sh):
    """One AS6C4008 on the 5V rail: the console's address bus, the glue's A8
    and the slot lines in from the left, /CE tied active, /OE and /WE from the
    glue; data out to the right (straight onto the console's data bus)."""
    lcol, rcol = 139.7, 254.0
    U, X, Y = 'U2', 203.2, 137.16
    sh.place(U, X, Y, fields='abovebelow', val_at=(X + 11.43, Y + 27.94, 'left'))
    console = [i for i in range(13) if i != 8]
    top, _ = sh.bus_group([(sh.N(U, 'A%d' % i), 'A%d' % i) for i in console], 175.26, up=True)
    sh.bus(top, (lcol, top[1]))
    sh.glabel((lcol, top[1]), 'A[0..15]', 'L', 'input')
    sh.tag(sh.N(U, 'SA8'), 'SA8', n=7.62, shape='input')
    _, bot = sh.bus_group([(sh.N(U, 'SA%d' % i), 'SA%d' % i) for i in range(13, 19)], 175.26, up=False)
    sh.bus(bot, (lcol, bot[1]))
    sh.glabel((lcol, bot[1]), 'SA[13..18]', 'L', 'input')
    sh.gnd(sh.P(U, D.SRAM_PIN['CE#']), 2.54, rot=270)
    for n in ('SRAM_OE_N', 'SRAM_WE_N'):
        p = sh.N(U, n)
        sh.wire(p, (lcol, p[1]))
        sh.glabel((lcol, p[1]), n, 'L', 'input')
    top, _ = sh.bus_group([(sh.N(U, 'D%d' % i), 'D%d' % i) for i in range(8)], 228.6, up=True)
    sh.bus(top, (rcol, top[1]))
    sh.glabel((rcol, top[1]), 'D[0..7]', 'R', 'bidirectional')
    sh.sup(sh.P(U, D.SRAM_PIN['VCC']), '+5V')
    sh.gnd(sh.P(U, D.SRAM_PIN['VSS']))
    for i, c in enumerate(('C23', 'C24')):
        sh.place(c, X + 25.4 + 12.7 * i, Y + 12.7)
        sh.sup(sh.P(c, 1), '+5V')
        sh.gnd(sh.P(c, 2))
    sh.text((139.7, 200.66), "A0-A7, A9-A12 and D0-D7 are the console's; SRAM A8 = A8 & !A8MASK (glue sheet);\n"
                             "A13-A18 are the RP's slot lines (GPIO32-37), the 8K page for the slot A13-A15 selects.\n"
                             '/CE is tied active: /OE and /WE alone decide when the SRAM answers.')


# =========================================================================
@sheet('glue')
def glue(sh):
    """The 5V glue, by logic level left to right: the console sense and the
    inversions; the address terms; LOW_P_N and SRAM A8; CSEL_P; the strobe
    stage that makes /OE and /WE.  Every gate is on labels; the equations are
    on the sheet."""
    # ---- console 5V sense: 22k/100k -> '14 -> PWR_OK_N -> '14 -> PWR_OK
    sh.place('R14', 20.32, 36.83, fields='left')
    sh.place('R15', 20.32, 44.45, fields='left')
    sh.sup(sh.P('R14', 1), 'CONS_5V')
    sh.gnd(sh.P('R15', 2))
    sh.place('U3', 43.18, 40.64, unit=1, fields='above')
    sh.place('U3', 63.5, 40.64, unit=2, fields='below')
    sh.wire(sh.P('R15', 1), (24.13, 40.64), sh.P('U3', 1))
    sh.name((24.13, 40.64), 'VSENSE', 'U', 'R')
    sh.wire(sh.P('U3', 2), (53.34, 40.64), sh.P('U3', 3))
    sh.wire((53.34, 40.64), (53.34, 30.48), (60.96, 30.48))
    sh.glabel((60.96, 30.48), 'PWR_OK_N', 'R')
    pok = sh.P('U3', 4)
    sh.wire(pok, (81.28, pok[1]))
    sh.glabel((81.28, pok[1]), 'PWR_OK', 'R', 'output')
    # ---- level 0: A13, R/W, A8MASK inversions
    for i, unit in enumerate((3, 4, 5)):
        gate(sh, 'U3', unit, 50.8, 66.04 + 22.86 * i)
    # ---- level 1: LOW_X, A15 & PWR_OK, A14 & PWR_OK, the A8 mask
    for i, unit in enumerate((1, 2, 3, 4)):
        gate(sh, 'U4', unit, 121.92, 40.64 + 22.86 * i)
    # ---- level 2: LOW_P_N; SRAM A8
    gate(sh, 'U5', 1, 190.5, 40.64)
    gate(sh, 'U3', 6, 190.5, 109.22)
    # ---- level 3: CSEL_P = PWR_OK & CARTSEL
    gate(sh, 'U5', 2, 259.08, 40.64)
    # ---- level 4: the strobe stage
    gate(sh, 'U6', 1, 327.66, 40.64)
    gate(sh, 'U6', 2, 327.66, 66.04)
    # ---- supplies: each package's power unit with its 100n
    for i, (ref, unit, cap) in enumerate((('U3', 7, 'C25'), ('U4', 5, 'C26'), ('U5', 3, 'C27'),
                                         ('U6', 3, 'C28'))):
        x, y = 205.74 + 45.72 * (i % 2), 160.02 + 35.56 * (i // 2)
        sh.place(ref, x, y, unit=unit, fields='right')
        sh.sup(sh.P(ref, 14), '+5V')
        sh.gnd(sh.P(ref, 7))
        sh.place(cap, x + 20.32, y)
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    sh.text((25.4, 160.02),
            "fujinet-firmware pico/atari-7800 a78_cart.h: a78_cartsel(), a78_glue_oe(), a78_glue_we(),\n"
            'a78_glue_a8().  RW = 1 for a read; ROM_EN, RAM_EN, A8MASK = RP GPIO38, 39, 40 (the PIO slot\n'
            'table); PWR_OK = console +5V present.\n\n'
            'CARTSEL = A15 | A14 | !A15 & !A14 & !A13 & A12 & !A11 | !A15 & !A14 & A13 & A12\n'
            '        = A15 | A14 | A12 & (A13 | !A11)\n'
            'LOW_X = A13 | !A11 = NAND(A13_N, A11)  [U3C, U4A]\n'
            'A15_P_N = !(A15 & PWR_OK), A14_P_N = !(A14 & PWR_OK)  [U4B, U4C]\n'
            'LOW_P_N = !(A12 & LOW_X & PWR_OK)  [U5A]\n'
            'CSEL_P = NAND(A15_P_N, A14_P_N, LOW_P_N) = PWR_OK & CARTSEL  [U5B]\n'
            'SRAM /OE = !(CSEL_P & RW & ROM_EN)  [U6A]: no PHI2, MARIA DMA is not PHI2-aligned\n'
            'SRAM /WE = !(CSEL_P & !RW & PHI2 & RAM_EN)  [U3D, U6B]: PHI2 is one gate from /WE\n'
            'SRAM A8 = A8 & !A8MASK  [U3E, U4D, U3F]\n\n'
            "tools/check_glue.py evaluates this netlist against the firmware's own C functions\n"
            'for every input combination.', 1.27)


# =========================================================================
@sheet('esp32s3-sd')
def esp32s3_sd(sh):
    """ESP32-S3 in the middle: EN / BOOT on the left (with the RP sheet's RESET and
    the USB bridge's auto-program lines coming in), UART / USB / SD / LED out on
    the right; the SD lines fan out to the socket and are named on the way."""
    U = 'U11'
    sh.place(U, 190.5, 149.86, fields='abovebelow', ref_at=(177.8, 120.65, 'left'),
             val_at=(167.64, 180.34, 'right'))
    # supply + decoupling above
    v = sh.P(U, 2)
    node = (v[0], 111.76)
    sh.wire(v, node, (200.66, node[1]), (213.36, node[1]))
    sh.sup(node, '+3V3')
    for c, x in (('C33', 200.66), ('C32', 213.36)):
        sh.place(c, x, node[1] + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.gnd(sh.P(U, 1))
    # EN: pull-up, power-on delay, button; S3_EN also comes from RESET and the auto-program pair
    en = sh.P(U, 3)
    ey = 109.22
    sh.wire(en, (170.18, en[1]), (170.18, ey), (162.56, ey), (152.4, ey), (142.24, ey), (127.0, ey))
    sh.glabel((127.0, ey), 'S3_EN', 'L', 'bidirectional')
    sh.place('R14', 162.56, ey - 3.81, fields='right')
    sh.sup(sh.P('R14', 1), '+3V3')
    sh.place('C34', 152.4, ey + 3.81, fields='right')
    sh.gnd(sh.P('C34', 2))
    sh.place('SW3', 142.24, ey + 5.08, rot=270, fields='left')
    sh.gnd(sh.P('SW3', 2))
    # IO0 (BOOT): button + the auto-program transistor
    io0 = sh.P(U, 27)
    sh.wire(io0, (147.32, io0[1]), (137.16, io0[1]))
    sh.glabel((137.16, io0[1]), 'S3_IO0', 'L', 'bidirectional')
    sh.place('SW4', 147.32, io0[1] + 5.08, rot=270, fields='left')
    sh.gnd(sh.P('SW4', 2))
    # IO4 / IO5: RUN / BOOTSEL of the RP2354B
    sh.tag(sh.P(U, 4), 'RUN_CTL', shape='output')
    sh.tag(sh.P(U, 5), 'BOOTSEL_CTL', shape='output')
    # UART to the CP2102N, native USB to the RP
    sh.tag(sh.P(U, 37), 'S3_TXD', shape='output')
    sh.tag(sh.P(U, 36), 'S3_RXD', shape='input')
    sh.tag(sh.P(U, 13), 'USB_DM', shape='bidirectional')
    sh.tag(sh.P(U, 14), 'USB_DP', shape='bidirectional')
    for num, pt in sh.placed[(U, 1)]['pins'].items():
        if sh.parts[U].pins[num] is None:
            sh.nc(pt)
    # microSD: SPI fans out from 2.54 to the socket's 5.08 and is named there
    J = 'J2'
    sh.place(J, 266.7, 160.02, fields='abovebelow', ref_at=(279.4, 186.69, 'left'),
             val_at=(279.4, 189.23, 'left'))
    for k, net in enumerate(('SD_MOSI', 'SD_SCK', 'SD_MISO', 'SD_CS', 'SD_CD')):
        a, b = sh.N(U, net), sh.N(J, net)
        x = 213.36 + (4 - k) * 2.54
        sh.wire(a, (x, a[1]), (x, b[1]), b)
        sh.name((209.55 if k == 0 else 228.6, b[1]), net, 'U', 'R')
    # pull-ups: DAT1 / DAT2 wired to the pack (DAT2 steps down to its pin), CS / MISO by label
    R = 'RN3'
    sh.place(R, 233.68, sh.N(J, 'SD_DAT1')[1], rot=90, mirror='x', fields='above')
    sh.wire(sh.N(R, 'SD_DAT1'), sh.N(J, 'SD_DAT1'))
    p, q = sh.N(R, 'SD_DAT2'), sh.N(J, 'SD_DAT2')
    sh.wire(p, (241.3, p[1]), (241.3, q[1]), q)
    sh.name((243.84, sh.N(J, 'SD_DAT1')[1]), 'SD_DAT1', 'D', 'R')
    sh.name((243.84, q[1]), 'SD_DAT2', 'D', 'R')
    for net in ('SD_CS', 'SD_MISO'):
        sh.tag(sh.N(R, net), net)
    g = [sh.P(R, n) for n in (5, 6, 7, 8)]
    ys = sorted(p[1] for p in g)
    gx = g[0][0] - 2.54
    for p in g:
        sh.wire(p, (gx, p[1]))
    sh.wire(*[(gx, y) for y in ys])
    sh.sup((gx, ys[0]), '+3V3')
    sh.place('R15', 294.64, 177.8, fields='right')
    sh.sup(sh.P('R15', 1), '+3V3')
    sh.tag(sh.P('R15', 2), 'SD_CD', dirn='D')
    sh.sup(sh.N(J, '+3V3'), '+3V3', n=2.54, rot=90)
    sh.gnd(sh.P(J, 6), n=2.54, rot=270)
    shp = [sh.P(J, n) for n in (10, 11, 12, 13)]
    sh.wire(*shp)
    sh.wire(shp[0], (shp[0][0], shp[0][1] + 2.54))
    sh.gnd((shp[0][0], shp[0][1] + 2.54))
    sh.place('C35', 284.48, 177.8)
    sh.sup(sh.P('C35', 1), '+3V3')
    sh.gnd(sh.P('C35', 2))
    # status LED: WS2812B on +5V, data straight from the S3 through 330R
    led = sh.P(U, 25)
    ly = 210.82
    sh.place('R16', 218.44, ly, rot=90, fields='below')
    sh.wire(led, (210.82, led[1]), (210.82, ly), sh.P('R16', 1))
    sh.name((210.82, 191.77), 'LED_STRIP', 'L', 'L')
    sh.place('D3', 243.84, ly, fields='right')
    sh.wire(sh.P('R16', 2), sh.P('D3', 3))
    sh.name((224.79, ly), 'WS_DIN', 'U', 'R')
    sh.sup(sh.P('D3', 4), '+5V')
    sh.gnd(sh.P('D3', 2))
    sh.nc(sh.P('D3', 1))
    sh.place('C36', 271.78, ly)
    sh.sup(sh.P('C36', 1), '+5V')
    sh.gnd(sh.P('C36', 2))


# =========================================================================
@sheet('usb-uart')
def usb_uart(sh):
    """USB-C on the left; VBUS up onto its rail (ESD, decoupling, the bridge's
    VBUS sense), CC pull-downs, the data pair through its ESD diodes into the
    CP2102N; the bridge's UART and the esptool auto-program pair on the right."""
    J, U = 'J3', 'U12'
    sh.place(J, 50.8, 149.86, fields='abovebelow')
    # VBUS rail: ESD, decoupling, the sense divider
    vb = sh.P(J, 'A4')
    ry = 116.84
    xs = [96.52, 109.22, 121.92]
    sh.wire(vb, (71.12, vb[1]), (71.12, ry), *[(x, ry) for x in xs], (134.62, ry))
    sh.sup((71.12, ry), 'VBUS')
    for ref, x in zip(('D6', 'C37', 'C38'), xs):
        sh.place(ref, x, ry + 3.81, rot=270 if ref == 'D6' else 0, fields='left' if ref == 'D6' else 'right')
        sh.gnd(sh.P(ref, 2))
    # CC pull-downs (Rd), up to ground in the space under the VBUS rail
    for pin, r, x, d in (('A5', 'R17', 78.74, 'U'), ('B5', 'R18', 88.9, 'D')):
        p = sh.P(J, pin)
        sh.place(r, x, p[1] - 3.81, rot=180, fields='right')
        sh.wire(p, sh.P(r, 1))
        sh.gnd(sh.P(r, 2), rot=180)
    sh.name((73.66, sh.P(J, 'A5')[1]), 'CC1', 'U', 'L')
    sh.name((76.2, sh.P(J, 'B5')[1]), 'CC2', 'D', 'R')
    # data pair: both receptacle rows joined, ESD to GND, into the bridge
    dm = [sh.P(J, 'A7'), sh.P(J, 'B7')]
    dp = [sh.P(J, 'A6'), sh.P(J, 'B6')]
    for a, b in (dm, dp):
        sh.wire(a, (68.58, a[1]), (68.58, b[1]), b)
    sh.place(U, 190.5, 160.02, fields='abovebelow', val_at=(204.47, 196.85, 'left'))
    cdm, cdp = sh.P(U, 5), sh.P(U, 4)
    sh.wire((68.58, dm[0][1]), (106.68, dm[0][1]), cdm)
    sh.wire((68.58, dp[0][1]), (99.06, dp[0][1]), (167.64, dp[0][1]), (167.64, cdp[1]), cdp)
    sh.place('D5', 106.68, dm[0][1] - 3.81, rot=90, fields='left')     # cathode on the line
    sh.gnd(sh.P('D5', 2), rot=180)
    sh.place('D4', 99.06, dp[0][1] + 3.81, rot=270, fields='right')
    sh.gnd(sh.P('D4', 2))
    sh.name((116.84, dm[0][1]), 'UBRG_DM', 'D', 'R')
    sh.name((116.84, dp[0][1]), 'UBRG_DP', 'D', 'R')
    for p in (sh.P(J, 'A8'), sh.P(J, 'B8')):
        sh.nc(p)
    g1, g2 = sh.P(J, 'A1'), sh.P(J, 'SH')
    sh.wire(g2, (g2[0], g2[1] + 2.54), (g1[0], g1[1] + 2.54), g1)
    sh.gnd((g1[0], g1[1] + 2.54))
    # VBUS sense divider into the bridge's VBUS pin (self-powered bridge)
    sns = sh.P(U, 8)
    sh.place('R19', 134.62, ry + 3.81, fields='right')
    sh.place('R20', 130.81, sns[1], rot=270, fields='above')
    sh.wire(sh.P('R19', 2), (134.62, sns[1]), sns)
    sh.gnd(sh.P('R20', 2), rot=270)
    sh.name((175.26, sns[1]), 'VBUS_SNS', 'U', 'L')
    # supply, reset pull-up
    vd, vr = sh.P(U, 6), sh.P(U, 7)
    top = 116.84
    sh.wire(vr, (vr[0], top))
    sh.wire(vd, (vd[0], top), (198.12, top), (210.82, top))
    sh.wire((vr[0], top), (vd[0], top))
    sh.sup((vr[0], top), '+3V3')
    for c, x in (('C39', 198.12), ('C40', 210.82)):
        sh.place(c, x, top + 3.81)
        sh.gnd(sh.P(c, 2))
    rst = sh.P(U, 9)
    sh.place('R21', 172.72, rst[1] - 3.81, fields='left')
    sh.wire(rst, (172.72, rst[1]), (167.64, rst[1]))
    sh.sup(sh.P('R21', 1), '+3V3')
    sh.glabel((167.64, rst[1]), 'CP_RST', 'L')
    sh.gnd(sh.P(U, 3))
    sh.gnd(sh.P(U, 23), 2.54, rot=90)                      # /CTS tied low
    for num, pt in sh.placed[(U, 1)]['pins'].items():
        if sh.parts[U].pins[num] is None:
            sh.nc(pt)
    # UART to the S3
    sh.tag(sh.P(U, 26), 'S3_RXD', shape='output')
    sh.tag(sh.P(U, 25), 'S3_TXD', shape='input')
    # esptool auto-program: DTR/RTS cross-coupled into EN / IO0 (DevKitC-1)
    rts, dtr = sh.P(U, 24), sh.P(U, 28)
    Q = 'U13'
    sh.place(Q, 248.92, 149.86, unit=1, fields='right')
    sh.place(Q, 248.92, 172.72, unit=2, fields='right')
    b1, e1, c1 = sh.P(Q, 2), sh.P(Q, 1), sh.P(Q, 6)
    b2, e2, c2 = sh.P(Q, 5), sh.P(Q, 4), sh.P(Q, 3)
    sh.wire(rts, (231.14, rts[1]), (231.14, e1[1] + 5.08), (231.14, b2[1]), b2)
    sh.wire((231.14, e1[1] + 5.08), (e1[0], e1[1] + 5.08), e1)
    sh.wire(dtr, (226.06, dtr[1]), (226.06, b1[1]), b1)
    sh.wire((226.06, b1[1]), (226.06, e2[1] + 5.08), (e2[0], e2[1] + 5.08), e2)
    sh.name((220.98, rts[1]), 'UART_RTS', 'U', 'R')
    sh.name((220.98, dtr[1]), 'UART_DTR', 'U', 'L')
    for c, net in ((c1, 'S3_EN'), (c2, 'S3_IO0')):
        sh.wire(c, (c[0], c[1] - 2.54), (264.16, c[1] - 2.54))
        sh.glabel((264.16, c[1] - 2.54), net, 'R', 'output')


# =========================================================================
@sheet('power')
def power(sh):
    """Left to right: the console's 5 V through the P-FET and USB VBUS through the
    Schottky meet on +5V; +5V feeds the 3.3 V buck (S3, bridge, SD) and the RP's
    own fast LDO (+3V3_RP)."""
    y5, yv = 88.9, 116.84
    # console 5V -> P-FET (gate = VBUS: on without USB) -> +5V
    sh.place('Q1', 60.96, y5 + 2.54, rot=90, fields='above')
    d, s, g = sh.P('Q1', 3), sh.P('Q1', 2), sh.P('Q1', 1)
    sh.wire((25.4, y5), (40.64, y5), (48.26, y5), d)
    sh.sup((25.4, y5), 'CONS_5V')
    sh.flag((48.26, y5), 'CONS_5V')
    sh.place('C41', 40.64, y5 + 3.81, fields='right')
    sh.gnd(sh.P('C41', 2))
    sh.wire(sh.P('C41', 2), (33.02, sh.P('C41', 2)[1]))
    sh.flag((33.02, sh.P('C41', 2)[1]), 'GND')
    # USB VBUS -> gate, and through the SS34 onto +5V
    sh.place('D7', 76.2, yv, rot=180, fields='below')
    sh.wire((25.4, yv), (45.72, yv), (g[0], yv), sh.P('D7', 2))
    sh.wire((g[0], yv), g)
    sh.sup((25.4, yv), 'VBUS')
    sh.flag((45.72, yv), 'VBUS')
    k = sh.P('D7', 1)
    sh.wire(k, (86.36, yv), (86.36, y5))
    # +5V: bulk + the buck's input caps, a branch down to the RP LDO
    caps = [('C42', 96.52), ('C43', 106.68), ('C44', 116.84), ('C45', 127.0)]
    sh.wire(s, (86.36, y5), *[(x, y5) for _, x in caps], (134.62, y5), (139.7, y5), (147.32, y5))
    sh.sup((86.36, y5), '+5V')
    sh.flag((139.7, y5), '+5V')
    for c, x in caps:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # 3.3 V buck
    B = 'U14'
    sh.place(B, 160.02, y5 + 2.54, fields='abovebelow', ref_at=(149.86, 82.55, 'left'), val_at=(147.32, 97.79, 'right'))
    sh.wire((147.32, y5), sh.P(B, 3))
    sh.wire(sh.P(B, 2), (147.32, sh.P(B, 2)[1]), (147.32, y5))
    sh.gnd(sh.P(B, 4))
    sw, bst, fb = sh.P(B, 5), sh.P(B, 6), sh.P(B, 1)
    sh.place('C46', 182.88, y5 + 3.81, fields='right')
    sh.place('L2', 193.04, y5, rot=90, fields='above')
    sh.wire(sw, (182.88, y5), sh.P('L2', 1))
    sh.wire(bst, (175.26, bst[1]), (175.26, 99.06), (182.88, 99.06), sh.P('C46', 2))
    sh.name((177.8, 99.06), 'BUCK_BST', 'D', 'R')
    sh.name((173.99, y5), 'BUCK_SW', 'U', 'R')
    out = [('C47', 207.01), ('C48', 217.17)]
    sh.wire(sh.P('L2', 2), (201.93, y5), *[(x, y5) for _, x in out])
    sh.wire(fb, (172.72, fb[1]), (172.72, 106.68), (201.93, 106.68), (201.93, y5))
    sh.sup((201.93, y5), '+3V3')
    sh.flag((217.17, y5), '+3V3')
    for c, x in out:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # RP LDO: +5V -> AP2112K -> +3V3_RP (IOVDD up with the console rail)
    L = 'U15'
    sh.place(L, 152.4, 142.24, fields='abovebelow', ref_at=(144.78, 132.08, 'left'), val_at=(144.78, 134.62, 'left'))
    vin, en, vo = sh.P(L, 1), sh.P(L, 3), sh.P(L, 5)
    sh.wire((134.62, y5), (134.62, vin[1]), (137.16, vin[1]), (142.24, vin[1]), vin)
    sh.wire(en, (142.24, en[1]), (142.24, vin[1]))
    sh.place('C49', 137.16, vin[1] + 3.81, fields='left')
    sh.gnd(sh.P('C49', 2))
    sh.gnd(sh.P(L, 2))
    sh.nc(sh.P(L, 4))
    sh.wire(vo, (167.64, vo[1]), (172.72, vo[1]))
    sh.place('C50', 167.64, vo[1] + 3.81)
    sh.gnd(sh.P('C50', 2))
    sh.sup((172.72, vo[1]), '+3V3_RP')
