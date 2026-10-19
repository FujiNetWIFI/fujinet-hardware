"""How each sheet is drawn: placement and wiring, one function per sheet.

design.py owns the circuit; these functions only say where each part sits
and how its pins are joined (sch_draw.Sheet), left to right in signal-flow
order.  sch_draw.Sheet.check() and gen_sch.netlist_parity() prove the drawing
is exactly design.py's netlist, so a wiring slip here fails the build.
"""
import design as D
import sch_draw
from sch_draw import Sheet, Pt as Pt_

DRAW = {}


def sheet(stem, paper='A3'):
    def deco(f):
        DRAW[stem] = (f, paper)
        return f
    return deco


def draw(stem, syms, parts):
    f, paper = DRAW[stem]
    sh = Sheet(stem, syms, parts, paper)
    f(sh)
    return sh


# =========================================================================
@sheet('edge-cic')
def edge_cic(sh):
    """The console edge on the left; everything it carries leaves on the right:
    the CPU / PPU buses as buses, the strobes as labels, the CIC lines into the
    (DNP) CIClone."""
    J = 'J1'
    sh.place(J, 55.88, 152.4, fields='abovebelow', val_at=(71.12, 240.54, 'right'))
    col = 101.6                               # where every signal leaves the sheet
    bx = 88.9                                 # the bus spines
    for nets, name, shape in ((['CA%d' % i for i in range(15)], 'CA[0..14]', 'output'),
                              (['CD%d' % i for i in range(8)], 'CD[0..7]', 'bidirectional'),
                              (['PA%d' % i for i in range(14)], 'PA[0..13]', 'output'),
                              (['PD%d' % i for i in range(8)], 'PD[0..7]', 'bidirectional')):
        top, bot = sh.bus_group([(sh.N(J, n), n) for n in nets], bx)
        sh.bus(top, (col, top[1]))
        sh.glabel((col, top[1]), name, 'R', shape)
    for net, shape in (('M2', 'output'), ('RW', 'output'), ('ROMSEL_N', 'output'), ('IRQ_N', 'input'),
                       ('PPU_RD_N', 'output'), ('PPU_WR_N', 'output'),
                       ('CIRAM_A10', 'input'), ('CIRAM_CE_N', 'input')):
        p = sh.N(J, net)
        sh.wire(p, (col, p[1]))
        sh.glabel((col, p[1]), net, 'R', shape)
    # M2 test pad, on the free row above M2
    m2 = sh.N(J, 'M2')
    sh.place('TP7', 96.52, m2[1] - 2.54, rot=270, fields='above')
    sh.wire((93.98, m2[1]), (93.98, m2[1] - 2.54), sh.P('TP7', 1))
    # rails
    sh.sup(sh.N(J, 'CONS_5V'), 'CONS_5V')
    g1, g72 = sh.P(J, '1'), sh.P(J, '72')
    sh.wire(g72, g72.go(2.54), g1.go(2.54), g1)
    sh.gnd(g1.go(2.54))
    for num, pt in sh.placed[(J, 1)]['pins'].items():
        if sh.parts[J].pins[num] is None:
            sh.nc(pt)
    # CIClone: mirrored so its pins face the edge; the edge's CIC fingers sit 5.08
    # apart (net names on the way), the ATtiny's 2.54: each line steps up before it
    U = 'U3'
    tomb = sh.N(J, 'CIC_TOMB')
    sh.place(U, 177.8, tomb[1] - 7.62, mirror='y', fields='abovebelow')
    for k, net in enumerate(('CIC_TOMB', 'CIC_TOPAK', 'CIC_RST', 'CIC_CLK')):
        a, b = sh.N(J, net), sh.N(U, net)
        x = 132.08 + 2.54 * k
        sh.wire(a, (x, a[1]), (x, b[1]), b)
        sh.name((a[1] and (106.68, a[1])), net, 'U', 'R')
    sh.nc(sh.P(U, 3))                                   # PB4 (LED) unused
    rst = sh.P(U, 1)                                    # /RESET: programming pad only
    sh.place('TP13', rst[0] - 7.62, rst[1], rot=90, fields='above')
    sh.wire(rst, sh.P('TP13', 1))
    sh.name((rst[0] - 2.54, rst[1]), 'CIC_RESET_N', 'D', 'L')
    # its supply is the console's own 5 V (it resets with the console)
    vcc, gnd = sh.P(U, 8), sh.P(U, 4)
    sh.sup(vcc, 'CONS_5V')
    sh.gnd(gnd)
    sh.place('C41', vcc[0] + 25.4, vcc[1] + 10.16)
    sh.sup(sh.P('C41', 1), 'CONS_5V')
    sh.gnd(sh.P('C41', 2))
    # the console's 5 V, sensed: 2.2k / 3.3k = 0.6 x CONS_5V into both RPs
    sh.place('R11', 228.6, 63.5, fields='right')
    sh.place('R12', 228.6, 78.74, fields='right')
    sh.sup(sh.P('R11', 1), 'CONS_5V')
    sh.wire(sh.P('R11', 2), (228.6, 71.12), sh.P('R12', 1))
    sh.wire((228.6, 71.12), (243.84, 71.12))
    sh.glabel((243.84, 71.12), 'PWR_OK', 'R', 'output')
    sh.gnd(sh.P('R12', 2))
    sh.text((40.64, 33.02), 'NES 72-pin edge drawn by function (finger numbers on the pins). Pin 1 is at the RIGHT seen\n'
                            'from the label side with the fingers down (nesdev; NES-EWROM-01 geometry).\n'
                            'EXP0-9, SYSTEM CLK and PPU /A13 are not used. The CIClone (ATtiny13A) is DNP until its firmware exists.')


# =========================================================================
def rp_core(sh, U, r, rail, n):
    """One RP2354B in the middle (Rev0's drawing, both RPs): its rail's decoupling
    row and the core regulator (LX -> inductor -> DVDD) across the top, the
    crystal and the SWD pads on the left.  r: this RP's refs (caps[13], dcaps[4],
    r_avdd, c_avdd, l, y, c_xin, c_xout, r_x, tp_swclk, tp_swdio); n: its local
    net names (design.NAMES_A / NAMES_B)."""
    X, Y = 215.9, 160.02
    sh.place(U, X, Y, fields='left', ref_at=(X - 27.94, Y + 63.5, 'left'), val_at=(X - 27.94, Y + 66.04, 'left'))
    P = lambda k: sh.P(U, k)
    # ---- the rail: every IO supply pin up to it, the decoupling row on it
    ry = 81.28
    for k in (68, 59, 69, 50, 64):                    # USB_OTP_VDD ADC_AVDD QSPI_IOVDD IOVDD VREG_VIN
        sh.wire(P(k), (P(k)[0], ry))
    caps = r['caps']                                  # 8x IOVDD, QSPI, OTP, ADC, 10u bulk, 4.7u VREG_VIN
    xs = [187.96 - 12.7 * (len(caps) - 1 - i) for i in range(len(caps))]
    for c, x in zip(caps, xs):
        sh.place(c, x, ry + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.wire(*sorted({(x, ry) for x in xs} | {(P(k)[0], ry) for k in (61, 68, 59, 69, 50, 64)}))
    sh.sup((xs[0], ry), rail)
    # VREG_AVDD: 33R off the rail, 4.7u to GND
    av = P(61)
    sh.place(r['r_avdd'], av[0], ry + 7.62 + 3.81, fields='left')
    sh.wire((av[0], ry), sh.P(r['r_avdd'], 1))
    node = (av[0], 101.6)
    sh.wire(sh.P(r['r_avdd'], 2), node, av)
    sh.place(r['c_avdd'], 172.72, node[1] + 3.81, fields='left')
    sh.wire(node, sh.P(r['c_avdd'], 1))
    sh.gnd(sh.P(r['c_avdd'], 2))
    sh.flag(sh.P(r['c_avdd'], 1), n['VREG_AVDD'])
    sh.name((190.5, node[1]), n['VREG_AVDD'], 'D', 'L')
    # core SMPS: LX up and over to the inductor, DVDD back down to FB and the DVDD pins
    lx, fb, dv = P(63), P(65), P(10)
    ly = 86.36
    sh.place(r['l'], 231.14, ly, rot=270, fields='below')
    sh.wire(lx, (lx[0], ly), sh.P(r['l'], 2))
    sh.name((lx[0], ly), n['RP_LX'], 'U', 'R')
    dx = [241.3 + 12.7 * i for i in range(4)]
    sh.wire(sh.P(r['l'], 1), (236.22, ly), *[(x, ly) for x in dx])
    for c, x in zip(r['dcaps'], dx):
        sh.place(c, x, ly + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.flag((dx[-1], ly), n['DVDD'])
    sh.wire(dv, (dv[0], 96.52), (236.22, 96.52), (236.22, ly))
    sh.wire(fb, (fb[0], 99.06), (dv[0], 99.06))
    sh.name((238.76, ly), n['DVDD'], 'U', 'R')
    # ground pins
    g, pg = P(81), P(62)
    sh.wire(pg, pg.go(2.54), g.go(2.54))
    sh.wire(g, g.go(2.54))
    sh.gnd(g.go(2.54))
    for k in (71, 72, 74, 73, 70):                    # QSPI: the flash in the package
        sh.nc(P(k))
    # ---- 12 MHz crystal: XIN straight to the crystal, XOUT through the 1k
    xi, xo = P(30), P(31)
    sh.place(r['y'], 160.02, xi[1] + 3.81, rot=270, fields='right')
    sh.wire(xi, sh.P(r['y'], 1))
    sh.place(r['c_xin'], 137.16, xi[1] + 3.81, fields='left')
    sh.wire(sh.P(r['y'], 1), sh.P(r['c_xin'], 1))
    sh.gnd(sh.P(r['c_xin'], 2))
    sh.gnd(sh.P(r['y'], 2))
    sh.place(r['r_x'], 175.26, xo[1], rot=270, fields='above')
    sh.wire(xo, sh.P(r['r_x'], 1))
    sh.wire(sh.P(r['r_x'], 2), (162.56, xo[1]), (160.02, xo[1]), (147.32, xo[1]))
    sh.wire(sh.P(r['y'], 3), (160.02, xo[1]))
    sh.place(r['c_xout'], 147.32, xo[1] + 3.81, fields='left')
    sh.gnd(sh.P(r['c_xout'], 2))
    sh.name((180.34, xi[1]), n['XIN'], 'U', 'L')
    sh.name((182.88, xo[1]), n['XOUT'], 'D', 'R')
    sh.name((162.56, xo[1]), n['XOUT_Y'], 'D', 'L')
    # ---- SWD test pads
    sc, sd = P(33), P(34)
    sh.place(r['tp_swclk'], 170.18, sc[1], rot=90, fields='above')
    sh.place(r['tp_swdio'], 160.02, sd[1], rot=90, fields='below')
    sh.wire(sc, sh.P(r['tp_swclk'], 1)); sh.wire(sd, sh.P(r['tp_swdio'], 1))
    return P


def rp_refs(base_c, r_avdd, r_x, l, y, tps):
    caps = ['C%d' % (base_c + i) for i in range(13)]
    return {'caps': caps, 'dcaps': ['C%d' % (base_c + 13 + i) for i in range(4)],
            'r_avdd': r_avdd, 'c_avdd': 'C%d' % (base_c + 17), 'l': l, 'y': y,
            'c_xin': 'C%d' % (base_c + 18), 'c_xout': 'C%d' % (base_c + 19), 'r_x': r_x,
            'tp_swclk': tps[0], 'tp_swdio': tps[1]}


def gpio_out(sh, U, gpio_net, groups, singles, col, lcol):
    """The bus side of an RP: groups = [(gpios, bus label, shape, up)] onto buses at
    x 256.54, singles = [(gpio, shape)] straight out; GPIO40-47 sit on the
    symbol's LEFT side and go to lcol."""
    gp = lambda g: sh.P(U, D.RP_GPIO_PIN[g])
    for gs, name, shape, up in groups:
        top, bot = sh.bus_group([(gp(g), gpio_net[g]) for g in gs], 256.54, up)
        end = top if up else bot
        sh.bus(end, (col, end[1]))
        sh.glabel((col, end[1]), name, 'R', shape)
    for g, shape in singles:
        p = gp(g)
        if gpio_net[g] is None:
            sh.nc(p)
        elif g >= 40:
            sh.wire(p, (lcol, p[1]))
            sh.glabel((lcol, p[1]), gpio_net[g], 'L', shape)
        else:
            sh.wire(p, (col, p[1]))
            sh.glabel((col, p[1]), gpio_net[g], 'R', shape)
    return gp


@sheet('rp-cpu')
def rp_cpu(sh):
    """RP-A (U1) in the middle: the CPU bus, the link to RP-B and RP-B's SWD on
    the right and the left; clock, reset / BOOTSEL, USB to the S3 and SWD pads
    on the left; the +3V3_RP decoupling row and the core regulator across the top."""
    U = 'U1'
    P = rp_core(sh, U, rp_refs(1, 'R1', 'R2', 'L1', 'Y1', ('TP1', 'TP2')), '+3V3_RP', D.NAMES_A)
    col, lcol = 279.4, 119.38
    gpn = D.RP_A_GPIO_NET
    gp = gpio_out(sh, U, gpn,
                  [(range(0, 13), 'CA[0..14]', 'input', True), (range(13, 21), 'CD[0..7]', 'bidirectional', True),
                   (range(34, 40), 'LD[0..7]', 'output', False)],
                  [(21, 'input'), (22, 'input'), (23, 'input'), (24, 'input'), (25, 'input'), (26, 'input'),
                   (30, 'passive'), (31, 'passive'), (32, 'output'), (33, 'input'),
                   (40, 'output'), (41, 'output'), (42, 'output'), (43, 'output'), (44, 'output'),
                   (45, 'bidirectional'), (46, 'output'), (47, 'input')], col, lcol)
    # status LED (GP27) and the debug UART pads (GP28/29): named off the pins,
    # drawn right of the bus labels
    for g in (27, 28, 29):
        p = gp(g)
        sh.wire(p, (251.46, p[1]))
        sh.glabel((251.46, p[1]), gpn[g], 'R', 'output' if g != 29 else 'input')
    rx = 307.34
    sh.glabel((rx, 180.34), 'LED', 'L', 'input')
    sh.place('R10', rx + 7.62, 180.34, rot=90, fields='above')
    sh.place('D2', rx + 20.32, 180.34, rot=180, fields='above')
    sh.wire((rx, 180.34), sh.P('R10', 1))
    sh.wire(sh.P('R10', 2), sh.P('D2', 2))
    sh.name((rx + 13.97, 180.34), 'LED_A', 'D', 'R')
    sh.gnd(sh.P('D2', 1), 2.54)
    for y, net, tp in ((193.04, 'DBG_A_TX', 'TP5'), (200.66, 'DBG_A_RX', 'TP6')):
        sh.glabel((rx, y), net, 'L', 'input' if tp == 'TP5' else 'output')
        sh.place(tp, rx + 7.62, y, rot=270, fields='right')
        sh.wire((rx, y), sh.P(tp, 1))
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
    # ---- USB to the S3 (RP-A = device): 27R series pair
    dm, dp = P(66), P(67)
    sh.place('R9', 160.02, dm[1], rot=90, fields='above')
    sh.place('R8', 152.4, dp[1], rot=90, fields='below')
    sh.wire(dm, sh.P('R9', 2)); sh.wire(dp, sh.P('R8', 2))
    sh.name((182.88, dm[1]), 'RP_USB_DM', 'U', 'L')
    sh.name((180.34, dp[1]), 'RP_USB_DP', 'D', 'L')
    for rr, net in (('R9', 'USB_DM'), ('R8', 'USB_DP')):
        p = sh.P(rr, 1)
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
    sh.name((185.42, P(33)[1]), 'SWCLK', 'U', 'L')
    sh.name((182.88, P(34)[1]), 'SWDIO', 'D', 'L')
    # ground test pad
    sh.place('TP3', 205.74, 228.6, fields='left')
    sh.gnd(sh.P('TP3', 1))


@sheet('rp-ppu')
def rp_ppu(sh):
    """RP-B (U2) in the middle: the PPU bus, the CIRAM lines and the link on the
    right and the left; its RUN, SWCLK and SWDIO come from RP-A; its USB is
    unused; the +3V3_RPB decoupling row and the core regulator across the top."""
    U = 'U2'
    P = rp_core(sh, U, rp_refs(21, 'R13', 'R14', 'L2', 'Y2', ('TP8', 'TP9')), '+3V3_RPB', D.NAMES_B)
    col, lcol = 279.4, 119.38
    gpn = D.RP_B_GPIO_NET
    gp = gpio_out(sh, U, gpn,
                  [(range(0, 14), 'PA[0..13]', 'input', True), (range(14, 22), 'PD[0..7]', 'bidirectional', True),
                   (range(35, 40), 'LD[0..7]', 'input', False)],
                  [(22, 'input'), (23, 'input'), (24, 'input'), (25, 'output'), (26, 'output'),
                   (27, 'passive'), (30, 'passive'), (31, 'passive'), (32, 'passive'), (33, 'input'), (34, 'input'),
                   (40, 'input'), (41, 'input'), (42, 'input'), (43, 'output'), (44, 'input'),
                   (45, 'passive'), (46, 'passive'), (47, 'passive')], col, lcol)
    # debug UART pads (GP28/29), as on RP-A
    for g in (28, 29):
        p = gp(g)
        sh.wire(p, (251.46, p[1]))
        sh.glabel((251.46, p[1]), gpn[g], 'R', 'output' if g == 28 else 'input')
    rx = 307.34
    for y, net, tp in ((193.04, 'DBG_B_TX', 'TP11'), (200.66, 'DBG_B_RX', 'TP12')):
        sh.glabel((rx, y), net, 'L', 'input' if tp == 'TP11' else 'output')
        sh.place(tp, rx + 7.62, y, rot=270, fields='right')
        sh.wire((rx, y), sh.P(tp, 1))
    # ---- RUN: RP-A drives it (GP46); pull-up and a test pad here
    run = P(35)
    a = (185.42, run[1]); b = (175.26, run[1])
    sh.wire(run, a, b, (lcol, run[1]))
    sh.glabel((lcol, run[1]), 'RPB_RUN', 'L', 'input')
    sh.place('R15', a[0], a[1] - 3.81, fields='left')
    sh.sup(sh.P('R15', 1), '+3V3_RPB')
    sh.wire(b, (b[0], b[1] - 2.54))
    sh.place('TP10', b[0], b[1] - 2.54, fields='left')
    # ---- SWD from RP-A (GP44/45)
    sh.name((185.42, P(33)[1]), 'RPB_SWCLK', 'U', 'L')
    sh.name((182.88, P(34)[1]), 'RPB_SWDIO', 'D', 'L')
    # ---- USB unused
    sh.nc(P(66)); sh.nc(P(67))
    # ---- QSPI_SS: pulled up, never driven (RP-B never boots its flash)
    ss = P(75)
    sh.wire(ss, (185.42, ss[1]), (142.24 + 3.81, ss[1]))
    sh.place('R16', 142.24, ss[1], rot=90, fields='below')
    sh.sup(sh.P('R16', 1), '+3V3_RPB')
    sh.name((185.42, ss[1]), 'QSPI_SS_B', 'D', 'L')


# =========================================================================
@sheet('esp32s3-sd')
def esp32s3_sd(sh):
    """ESP32-S3 in the middle: EN / BOOT on the left (with the RP sheet's RESET and
    the USB bridge's auto-program lines coming in), UART / USB / SD / LED out on
    the right; the SD lines fan out to the socket and are named on the way."""
    U = 'U4'
    sh.place(U, 190.5, 149.86, fields='abovebelow', ref_at=(177.8, 120.65, 'left'),
             val_at=(167.64, 180.34, 'right'))
    # supply + decoupling above
    v = sh.P(U, 2)
    node = (v[0], 111.76)
    sh.wire(v, node, (200.66, node[1]), (213.36, node[1]))
    sh.sup(node, '+3V3')
    for c, x in (('C43', 200.66), ('C42', 213.36)):
        sh.place(c, x, node[1] + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.gnd(sh.P(U, 1))
    # EN: pull-up, power-on delay, button; S3_EN also comes from RESET and the auto-program pair
    en = sh.P(U, 3)
    ey = 109.22
    sh.wire(en, (170.18, en[1]), (170.18, ey), (162.56, ey), (152.4, ey), (142.24, ey), (127.0, ey))
    sh.glabel((127.0, ey), 'S3_EN', 'L', 'bidirectional')
    sh.place('R17', 162.56, ey - 3.81, fields='right')
    sh.sup(sh.P('R17', 1), '+3V3')
    sh.place('C44', 152.4, ey + 3.81, fields='right')
    sh.gnd(sh.P('C44', 2))
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
    R = 'RN1'
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
    sh.place('R18', 294.64, 177.8, fields='right')
    sh.sup(sh.P('R18', 1), '+3V3')
    sh.tag(sh.P('R18', 2), 'SD_CD', dirn='D')
    sh.sup(sh.N(J, '+3V3'), '+3V3', n=2.54, rot=90)
    sh.gnd(sh.P(J, 6), n=2.54, rot=270)
    shp = [sh.P(J, n) for n in (10, 11, 12, 13)]
    sh.wire(*shp)
    sh.wire(shp[0], (shp[0][0], shp[0][1] + 2.54))
    sh.gnd((shp[0][0], shp[0][1] + 2.54))
    sh.place('C45', 284.48, 177.8)
    sh.sup(sh.P('C45', 1), '+3V3')
    sh.gnd(sh.P('C45', 2))
    # status LED: WS2812B on +5V, data straight from the S3 through 330R
    led = sh.P(U, 25)
    ly = 210.82
    sh.place('R19', 218.44, ly, rot=90, fields='below')
    sh.wire(led, (210.82, led[1]), (210.82, ly), sh.P('R19', 1))
    sh.name((210.82, 191.77), 'LED_STRIP', 'L', 'L')
    sh.place('D3', 243.84, ly, fields='right')
    sh.wire(sh.P('R19', 2), sh.P('D3', 3))
    sh.name((224.79, ly), 'WS_DIN', 'U', 'R')
    sh.sup(sh.P('D3', 4), '+5V')
    sh.gnd(sh.P('D3', 2))
    sh.nc(sh.P('D3', 1))
    sh.place('C46', 271.78, ly)
    sh.sup(sh.P('C46', 1), '+5V')
    sh.gnd(sh.P('C46', 2))


# =========================================================================
@sheet('usb-uart')
def usb_uart(sh):
    """USB-C on the left; VBUS up onto its rail (ESD, decoupling, the bridge's
    VBUS sense), CC pull-downs, the data pair through its ESD diodes into the
    CP2102N; the bridge's UART and the esptool auto-program pair on the right."""
    J, U = 'J3', 'U5'
    sh.place(J, 50.8, 149.86, fields='abovebelow')
    # VBUS rail: ESD, decoupling, the sense divider
    vb = sh.P(J, 'A4')
    ry = 116.84
    xs = [96.52, 109.22, 121.92]
    sh.wire(vb, (71.12, vb[1]), (71.12, ry), *[(x, ry) for x in xs], (134.62, ry))
    sh.sup((71.12, ry), 'VBUS')
    for ref, x in zip(('D6', 'C47', 'C48'), xs):
        sh.place(ref, x, ry + 3.81, rot=270 if ref == 'D6' else 0, fields='left' if ref == 'D6' else 'right')
        sh.gnd(sh.P(ref, 2))
    # CC pull-downs (Rd), up to ground in the space under the VBUS rail
    for pin, r, x, d in (('A5', 'R20', 78.74, 'U'), ('B5', 'R21', 88.9, 'D')):
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
    sh.place('R22', 134.62, ry + 3.81, fields='right')
    sh.place('R23', 130.81, sns[1], rot=270, fields='above')
    sh.wire(sh.P('R22', 2), (134.62, sns[1]), sns)
    sh.gnd(sh.P('R23', 2), rot=270)
    sh.name((175.26, sns[1]), 'VBUS_SNS', 'U', 'L')
    # supply, reset pull-up
    vd, vr = sh.P(U, 6), sh.P(U, 7)
    top = 116.84
    sh.wire(vr, (vr[0], top))
    sh.wire(vd, (vd[0], top), (198.12, top), (210.82, top))
    sh.wire((vr[0], top), (vd[0], top))
    sh.sup((vr[0], top), '+3V3')
    for c, x in (('C49', 198.12), ('C50', 210.82)):
        sh.place(c, x, top + 3.81)
        sh.gnd(sh.P(c, 2))
    rst = sh.P(U, 9)
    sh.place('R24', 172.72, rst[1] - 3.81, fields='left')
    sh.wire(rst, (172.72, rst[1]), (167.64, rst[1]))
    sh.sup(sh.P('R24', 1), '+3V3')
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
    Q = 'U6'
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
    Schottky meet on +5V; +5V feeds the 3.3 V buck (S3, bridge, SD) and each RP's
    own fast LDO (+3V3_RP, +3V3_RPB)."""
    y5, yv = 88.9, 116.84
    # console 5V -> P-FET (gate = VBUS: on without USB) -> +5V
    sh.place('Q1', 60.96, y5 + 2.54, rot=90, fields='above')
    d, s, g = sh.P('Q1', 3), sh.P('Q1', 2), sh.P('Q1', 1)
    sh.wire((25.4, y5), (40.64, y5), (48.26, y5), d)
    sh.sup((25.4, y5), 'CONS_5V')
    sh.flag((48.26, y5), 'CONS_5V')
    sh.place('C51', 40.64, y5 + 3.81, fields='right')
    sh.gnd(sh.P('C51', 2))
    sh.wire(sh.P('C51', 2), (33.02, sh.P('C51', 2)[1]))
    sh.flag((33.02, sh.P('C51', 2)[1]), 'GND')
    # USB VBUS -> gate, and through the SS34 onto +5V
    sh.place('D7', 76.2, yv, rot=180, fields='below')
    sh.wire((25.4, yv), (35.56, yv), (45.72, yv), (g[0], yv), sh.P('D7', 2))
    sh.wire((g[0], yv), g)
    sh.sup((25.4, yv), 'VBUS')
    sh.flag((45.72, yv), 'VBUS')
    # the gate's pull-down against the SS34's reverse leakage
    sh.place('R25', 35.56, yv + 3.81, fields='right')
    sh.gnd(sh.P('R25', 2))
    k = sh.P('D7', 1)
    sh.wire(k, (86.36, yv), (86.36, y5))
    # +5V: bulk + the buck's input caps, a branch down to the RP LDO
    caps = [('C52', 96.52), ('C53', 106.68), ('C54', 116.84), ('C55', 127.0)]
    sh.wire(s, (86.36, y5), *[(x, y5) for _, x in caps], (134.62, y5), (139.7, y5), (147.32, y5))
    sh.sup((86.36, y5), '+5V')
    sh.flag((139.7, y5), '+5V')
    for c, x in caps:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # 3.3 V buck
    B = 'U7'
    sh.place(B, 160.02, y5 + 2.54, fields='abovebelow', ref_at=(149.86, 82.55, 'left'), val_at=(147.32, 97.79, 'right'))
    sh.wire((147.32, y5), sh.P(B, 3))
    sh.wire(sh.P(B, 2), (147.32, sh.P(B, 2)[1]), (147.32, y5))
    sh.gnd(sh.P(B, 4))
    sw, bst, fb = sh.P(B, 5), sh.P(B, 6), sh.P(B, 1)
    sh.place('C56', 182.88, y5 + 3.81, fields='right')
    sh.place('L3', 193.04, y5, rot=90, fields='above')
    sh.wire(sw, (182.88, y5), sh.P('L3', 1))
    sh.wire(bst, (175.26, bst[1]), (175.26, 99.06), (182.88, 99.06), sh.P('C56', 2))
    sh.name((177.8, 99.06), 'BUCK_BST', 'D', 'R')
    sh.name((173.99, y5), 'BUCK_SW', 'U', 'R')
    out = [('C57', 207.01), ('C58', 217.17)]
    sh.wire(sh.P('L3', 2), (201.93, y5), *[(x, y5) for _, x in out])
    sh.wire(fb, (172.72, fb[1]), (172.72, 106.68), (201.93, 106.68), (201.93, y5))
    sh.sup((201.93, y5), '+3V3')
    sh.flag((217.17, y5), '+3V3')
    for c, x in out:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # the RP LDOs: +5V -> AP2112K -> +3V3_RP (RP-A) and +3V3_RPB (RP-B), each RP's
    # IOVDD up with the console rail
    vx = 134.62
    for i, (L, cin, cout, rail) in enumerate((('U8', 'C59', 'C60', '+3V3_RP'), ('U9', 'C61', 'C62', '+3V3_RPB'))):
        yy = 142.24 + 30.48 * i
        sh.place(L, 152.4, yy, fields='abovebelow', ref_at=(144.78, yy - 10.16, 'left'), val_at=(144.78, yy - 7.62, 'left'))
        vin, en, vo = sh.P(L, 1), sh.P(L, 3), sh.P(L, 5)
        sh.wire((vx, vin[1]), (137.16, vin[1]), (142.24, vin[1]), vin)
        sh.wire(en, (142.24, en[1]), (142.24, vin[1]))
        sh.place(cin, 137.16, vin[1] + 3.81, fields='left')
        sh.gnd(sh.P(cin, 2))
        sh.gnd(sh.P(L, 2))
        sh.nc(sh.P(L, 4))
        sh.wire(vo, (167.64, vo[1]), (172.72, vo[1]))
        sh.place(cout, 167.64, vo[1] + 3.81)
        sh.gnd(sh.P(cout, 2))
        sh.sup((172.72, vo[1]), rail)
    sh.wire((vx, y5), (vx, sh.P('U8', 1)[1]), (vx, sh.P('U9', 1)[1]))


