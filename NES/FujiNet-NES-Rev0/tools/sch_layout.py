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
                       ('PA13_N', 'output'), ('PPU_RD_N', 'output'), ('PPU_WR_N', 'output'),
                       ('CIRAM_A10', 'input'), ('CIRAM_CE_N', 'input')):
        p = sh.N(J, net)
        sh.wire(p, (col, p[1]))
        sh.glabel((col, p[1]), net, 'R', shape)
    # M2 test pad, on the free row above M2
    m2 = sh.N(J, 'M2')
    sh.place('TP5', 96.52, m2[1] - 2.54, rot=270, fields='above')
    sh.wire((93.98, m2[1]), (93.98, m2[1] - 2.54), sh.P('TP5', 1))
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
    U = 'U10'
    tomb = sh.N(J, 'CIC_TOMB')
    sh.place(U, 177.8, tomb[1] - 7.62, mirror='y', fields='abovebelow')
    for k, net in enumerate(('CIC_TOMB', 'CIC_TOPAK', 'CIC_RST', 'CIC_CLK')):
        a, b = sh.N(J, net), sh.N(U, net)
        x = 132.08 + 2.54 * k
        sh.wire(a, (x, a[1]), (x, b[1]), b)
        sh.name((a[1] and (106.68, a[1])), net, 'U', 'R')
    sh.nc(sh.P(U, 3))                                   # PB4 (LED) unused
    rst = sh.P(U, 1)                                    # /RESET: programming pad only
    sh.place('TP7', rst[0] - 7.62, rst[1], rot=90, fields='above')
    sh.wire(rst, sh.P('TP7', 1))
    sh.name((rst[0] - 2.54, rst[1]), 'CIC_RESET_N', 'D', 'L')
    # its supply is the console's own 5 V (it resets with the console)
    vcc, gnd = sh.P(U, 8), sh.P(U, 4)
    sh.sup(vcc, 'CONS_5V')
    sh.gnd(gnd)
    sh.place('C31', vcc[0] + 25.4, vcc[1] + 10.16)
    sh.sup(sh.P('C31', 1), 'CONS_5V')
    sh.gnd(sh.P('C31', 2))
    sh.text((40.64, 33.02), 'NES 72-pin edge drawn by function (finger numbers on the pins). Pin 1 is at the RIGHT seen\n'
                            'from the label side with the fingers down (nesdev; NES-EWROM-01 geometry).\n'
                            'EXP0-9 and SYSTEM CLK are not used. The CIClone (ATtiny13A) is DNP until its firmware exists.')


# =========================================================================
@sheet('rp2354b')
def rp2354b(sh):
    """RP2354B in the middle: the cart bus leaves on the right (buses toward the
    edge and the SRAMs, strobes to the glue); clock, reset / BOOTSEL, USB to the
    S3 and SWD on the left; the +3V3_RP decoupling row and the core regulator
    (LX -> inductor -> DVDD) across the top."""
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
    # ---- cart side (right): buses toward the edge / SRAMs, strobes and '595 lines out
    col, bx = 279.4, 256.54
    gp = lambda g: sh.P(U, D.RP_GPIO_PIN[g])
    net_of = lambda g: D.RP_GPIO_NET[g]
    for gs, name, shape, up in ((range(0, 13), 'CA[0..14]', 'input', True), (range(13, 21), 'CD[0..7]', 'bidirectional', True),
                                (range(33, 39), 'PRG_A[13..18]', 'output', False)):
        top, bot = sh.bus_group([(gp(g), net_of(g)) for g in gs], bx, up)
        end = top if up else bot
        sh.bus(end, (col, end[1]))
        sh.glabel((col, end[1]), name, 'R', shape)
    for g, shape in ((21, 'input'), (22, 'input'), (23, 'input'), (24, 'input'), (25, 'input'),
                     (26, 'input'), (27, 'input'), (28, 'input'), (29, 'output'), (30, 'output'),
                     (31, 'output'), (32, 'output')):
        p = gp(g)
        sh.wire(p, (col, p[1]))
        sh.glabel((col, p[1]), net_of(g), 'R', shape)
    p = gp(39)                                         # CHR_A10: under the PRG bus
    sh.wire(p, (248.92, p[1]), (248.92, p[1] + 7.62), (col, p[1] + 7.62))
    sh.glabel((col, p[1] + 7.62), net_of(39), 'R', 'output')
    # CHR bank lines leave on the left (the symbol puts GPIO40-47 there)
    lcol = 119.38
    top, bot = sh.bus_group([(gp(g), net_of(g)) for g in range(40, 48)], 177.8, up=False)
    sh.bus(bot, (lcol, bot[1]))
    sh.glabel((lcol, bot[1]), 'CHR_A[11..18]', 'L', 'output')
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
    """Two AS6C4008s on the 5V rail: address buses and strobes in from the left,
    data out to the right (straight onto the console's buses)."""
    lcol, rcol = 139.7, 254.0
    for U, Y, abus, bbus, bank, data, dbus, strobes, cap, bulk in (
            ('U2', 82.55, ['CA%d' % i for i in range(13)], 'CA[0..14]',
             ('PRG_A[13..18]', ['PRG_A%d' % i for i in range(13, 19)]),
             ['CD%d' % i for i in range(8)], 'CD[0..7]', ('PRG_CE_N', 'PRG_OE_N', 'PRG_WE_N'), 'C22', 'C24'),
            ('U3', 193.04, ['PA%d' % i for i in range(10)], 'PA[0..13]',
             ('CHR_A[10..18]', ['CHR_A%d' % i for i in range(10, 19)]),
             ['PD%d' % i for i in range(8)], 'PD[0..7]', ('PA13', 'CHR_OE_N', 'CHR_WE_N'), 'C23', None)):
        X = 203.2
        sh.place(U, X, Y, fields='abovebelow', val_at=(X + 11.43, Y + 27.94, 'left'))
        top, _ = sh.bus_group([(sh.N(U, n), n) for n in abus], 177.8, up=True)
        sh.bus(top, (lcol, top[1]))
        sh.glabel((lcol, top[1]), abus and abus_name(abus), 'L', 'input')
        _, bot = sh.bus_group([(sh.N(U, n), n) for n in bank[1]], 177.8, up=False)
        sh.bus(bot, (lcol, bot[1]))
        sh.glabel((lcol, bot[1]), bank[0], 'L', 'input')
        for n in strobes:
            p = sh.N(U, n)
            sh.wire(p, (lcol, p[1]))
            sh.glabel((lcol, p[1]), n, 'L', 'input')
        top, _ = sh.bus_group([(sh.N(U, n), n) for n in data], 228.6, up=True)
        sh.bus(top, (rcol, top[1]))
        sh.glabel((rcol, top[1]), dbus, 'R', 'bidirectional')
        sh.sup(sh.N(U, '+5V'), '+5V')
        sh.gnd(sh.N(U, 'GND'))
        for i, c in enumerate([cap] + ([bulk] if bulk else [])):
            sh.place(c, X + 25.4 + 12.7 * i, Y + 12.7)
            sh.sup(sh.P(c, 1), '+5V')
            sh.gnd(sh.P(c, 2))


def abus_name(nets):
    return {'CA0': 'CA[0..14]', 'PA0': 'PA[0..13]'}[nets[0]]


# =========================================================================
@sheet('glue')
def glue(sh):
    """The 5V glue, left to right: console sense -> PWR_OK and the '595's /OE gate;
    the '595's eight control bits drop to their gates in nested channels (no
    crossings: the gates are stacked in the bits' own order); the console's
    strobes come in on labels at the gates that use them; strobes and the CIRAM
    lines leave on the right.  PWR_OK / PWR_OK_N fan out to five gates and the
    pull-down packs sit on the '595 bits: both by label."""
    # ---- console 5V sense: 22k/100k -> '14 -> PWR_OK_N -> '14 -> PWR_OK
    sh.place('R10', 20.32, 36.83, fields='left')
    sh.place('R11', 20.32, 44.45, fields='left')
    sh.sup(sh.P('R10', 1), 'CONS_5V')
    sh.gnd(sh.P('R11', 2))
    sh.place('U6', 43.18, 40.64, unit=1, fields='above')
    sh.place('U6', 63.5, 40.64, unit=2, fields='below')
    sh.wire(sh.P('R11', 1), (24.13, 40.64), sh.P('U6', 1))
    sh.name((24.13, 40.64), 'VSENSE', 'U', 'R')
    sh.wire(sh.P('U6', 2), (53.34, 40.64), sh.P('U6', 3))
    sh.wire((53.34, 40.64), (53.34, 30.48), (60.96, 30.48))
    sh.glabel((60.96, 30.48), 'PWR_OK_N', 'R')
    pok = sh.P('U6', 4)
    sh.wire(pok, (76.2, pok[1]), (88.9, pok[1]))
    sh.glabel((88.9, pok[1]), 'PWR_OK', 'R')
    # ---- power-on hold-off: RC from +5V, '14 Schmitt -> POR
    sh.place('C21', 33.02, 57.15, rot=180, fields='left')
    sh.place('R12', 33.02, 64.77, fields='left')
    sh.sup(sh.P('C21', 2), '+5V')
    sh.gnd(sh.P('R12', 2))
    sh.place('U6', 55.88, 60.96, unit=6, fields='below')
    sh.wire(sh.P('C21', 1), (38.1, 60.96), sh.P('U6', 13))
    sh.name((38.1, 60.96), 'POR_RC', 'D', 'R')
    # ---- '595 /OE = NAND(PWR_OK, POR)
    sh.place('U8', 86.36, 55.88, unit=2, fields='above')
    sh.wire((76.2, pok[1]), (76.2, sh.P('U8', 4)[1]), sh.P('U8', 4))
    por = sh.P('U6', 12)
    sh.wire(por, (68.58, por[1]), (73.66, por[1]), (73.66, sh.P('U8', 5)[1]), sh.P('U8', 5))
    sh.name((68.58, por[1]), 'POR', 'D', 'R')
    # ---- '595: RP's SPI-ish lines in on labels, /OE from the gate
    U = 'U4'
    sh.place(U, 124.46, 88.9, fields='abovebelow', val_at=(113.03, 102.87, 'right'))
    for net in ('SR_SER', 'SR_SCK', 'SR_RCK'):
        sh.tag(sh.N(U, net), net, shape='input')
    sh.sup(sh.P(U, 10), '+5V', n=2.54, rot=90)          # /SRCLR
    oe = sh.P(U, 13)
    sh.wire(sh.P('U8', 6), (96.52, sh.P('U8', 6)[1]), (96.52, oe[1]), oe)
    sh.name((96.52, 68.58), 'SR_OE_N', 'R', 'R')
    sh.sup(sh.P(U, 16), '+5V')
    sh.gnd(sh.P(U, 8))
    sh.nc(sh.P(U, 9))
    # ---- the gates, stacked in the '595 bits' order
    xg = 215.9
    sh.place('U7', xg, 106.68, unit=1, mirror='x', fields='above')    # PRG /WE = NAND4(M2, ROMSEL, !R/W, PRG_WE_EN)
    sh.place('U7', xg, 124.46, unit=2, fields='below')                # PRG /CE = NAND(ROMSEL, SRAM_EN)
    sh.place('U8', xg, 144.78, unit=1, fields='above')                # PRG /OE = NAND(R/W, PWR_OK)
    sh.place('U9', xg, 160.02, unit=1, fields='above')                # CHR /OE = /RD | PWR_OK_N
    sh.place('U9', xg, 175.26, unit=2, fields='above')                # CHR /WE = /WR | CHR_WE_EN_N
    sh.place('U9', 198.12, 210.82, unit=4, fields='below')                # CIRAM /CE pre-gate = /A13 | FOURSCREEN
    sh.place('U5', 254.0, 205.74, fields='abovebelow', val_at=(265.43, 224.79, 'left'))
    rcol = 279.4
    for ref, pin, net in (('U7', 6, 'PRG_WE_N'), ('U7', 8, 'PRG_CE_N'), ('U8', 3, 'PRG_OE_N'),
                          ('U9', 3, 'CHR_OE_N'), ('U9', 6, 'CHR_WE_N'), ('U5', 7, 'CIRAM_A10'), ('U5', 9, 'CIRAM_CE_N')):
        p = sh.P(ref, pin)
        sh.wire(p, (rcol, p[1]))
        sh.glabel((rcol, p[1]), net, 'R', 'output')
    # the '595 bits: QA..QH right, then down at x[k] to their consumer rows
    order = ['SRAM_EN', 'PRG_WE_EN', 'CHR_WE_EN', 'MIR0', 'MIR1', 'FOURSCREEN', 'SR_LED', 'SR_SPARE']
    cx = {n: 162.56 - 2.54 * i for i, n in enumerate(order)}
    dest = {'SRAM_EN': sh.P('U7', 10), 'PRG_WE_EN': sh.P('U7', 5),
            'MIR0': sh.P('U5', 14), 'MIR1': sh.P('U5', 2), 'FOURSCREEN': sh.P('U9', 13)}
    sh.place('U6', 193.04, 177.8, unit=4, fields='below')            # CHR_WE_EN -> CHR_WE_EN_N
    dest['CHR_WE_EN'] = sh.P('U6', 9)
    sh.wire(sh.P('U6', 8), sh.P('U9', 5))
    sh.name((203.2, 177.8), 'CHR_WE_EN_N', 'D', 'R')
    sh.place('R13', 179.07, 241.3, rot=90, fields='above')
    sh.place('D2', 190.5, 241.3, rot=180, fields='below')
    dest['SR_LED'] = sh.P('R13', 1)
    sh.wire(sh.P('R13', 2), sh.P('D2', 2))
    sh.gnd(sh.P('D2', 1), 2.54)
    sh.name((184.15, 241.3), 'SR_LED_A', 'U', 'R', n=3.81)
    sh.place('TP6', 175.26, 248.92, rot=270, fields='right')
    dest['SR_SPARE'] = sh.P('TP6', 1)
    for n in order:
        q, t = sh.N(U, n), dest[n]
        sh.wire(q, (cx[n], q[1]), (cx[n], t[1]), t)
    # each bit's name: on its channel below the channels to its right, else on its tap
    for n, at, d in (('SRAM_EN', (139.7, sh.N(U, 'SRAM_EN')[1]), 'U'), ('PRG_WE_EN', (165.1, sh.P('U7', 5)[1]), 'D'),
                     ('CHR_WE_EN', (cx['CHR_WE_EN'], 149.86), 'R'), ('MIR0', (cx['MIR0'], 182.88), 'R'),
                     ('MIR1', (157.48, sh.P('U5', 2)[1]), 'D'), ('FOURSCREEN', (cx['FOURSCREEN'], 203.2), 'R'),
                     ('SR_LED', (cx['SR_LED'], 233.68), 'R'), ('SR_SPARE', (cx['SR_SPARE'], 246.38), 'R')):
        sh.name(at, n, d, 'R')
    # ---- the console's strobes, in on labels at their gates
    sh.place('U6', 193.04, 95.25, unit=5, fields='above')             # R/W -> RW_N
    sh.place('U6', 193.04, 116.84, unit=3, fields='below')            # /ROMSEL -> ROMSEL
    sh.tag(sh.P('U6', 11), 'RW', shape='input')
    sh.wire(sh.P('U6', 10), (203.2, 95.25), (203.2, sh.P('U7', 4)[1]), sh.P('U7', 4))
    sh.name((203.2, 97.79), 'RW_N', 'R', 'R')
    sh.tag(sh.P('U6', 5), 'ROMSEL_N', shape='input')
    rs = sh.P('U6', 6)
    sh.wire(rs, (205.74, rs[1]), (205.74, sh.P('U7', 2)[1]), sh.P('U7', 2))
    sh.wire((205.74, rs[1]), (205.74, sh.P('U7', 9)[1]), sh.P('U7', 9))
    sh.name((205.74, 114.3), 'ROMSEL', 'R', 'R')
    sh.tag(sh.P('U7', 1), 'M2', n=5.08, shape='input')
    for ref, pin, net, shape in ( ('U8', 1, 'RW', 'input'), ('U8', 2, 'PWR_OK', 'passive'),
                                 ('U9', 1, 'PPU_RD_N', 'input'), ('U9', 2, 'PWR_OK_N', 'passive'),
                                 ('U9', 4, 'PPU_WR_N', 'input'), ('U9', 12, 'PA13_N', 'input'),
                                 ('U5', 6, 'PA10', 'input'), ('U5', 5, 'PA11', 'input'),
                                 ('U5', 1, 'PWR_OK_N', 'passive'), ('U5', 15, 'PWR_OK_N', 'passive')):
        sh.tag(sh.P(ref, pin), net, shape=shape)
    sh.gnd(sh.P('U5', 4), 2.54, rot=270)
    sh.sup(sh.P('U5', 3), '+5V', n=2.54, rot=90)
    # PRG /CE's two spare inputs high
    a, b = sh.P('U7', 12), sh.P('U7', 13)
    sh.wire(a, (205.74, a[1]), (205.74, b[1]), b)
    sh.sup((205.74, b[1]), '+5V', rot=90)
    # CIRAM /CE: the pre-gate into all four inputs of the '253's half b
    o = sh.P('U9', 11)
    jx = 236.22
    sh.wire(o, (jx, o[1]), (jx, sh.P('U5', 10)[1]))
    for n in (10, 11, 12, 13):
        p = sh.P('U5', n)
        sh.wire((jx, p[1]), p)
    sh.wire((jx, sh.P('U5', 10)[1]), (jx, sh.P('U5', 13)[1]))
    sh.name((208.28, o[1]), 'CIRAM_CE_PRE', 'D', 'R')
    sh.sup(sh.P('U5', 16), '+5V')
    sh.gnd(sh.P('U5', 8))
    # ---- supplies: the gate packages' power units, every package's 100n, spare gates
    for i, (ref, unit, cap) in enumerate((('U6', 7, 'C27'), ('U7', 3, 'C28'), ('U8', 5, 'C29'), ('U9', 5, 'C30'))):
        x, y = 27.94 + 40.64 * (i % 2), 147.32 + 35.56 * (i // 2)
        sh.place(ref, x, y, unit=unit, fields='right')
        sh.sup(sh.P(ref, 14), '+5V')
        sh.gnd(sh.P(ref, 7))
        sh.place(cap, x + 20.32, y)
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    for i, cap in enumerate(('C25', 'C26')):                 # the '595's and the '253's
        sh.place(cap, 27.94 + 20.32 * i, 213.36)
        sh.sup(sh.P(cap, 1), '+5V')
        sh.gnd(sh.P(cap, 2))
    sh.text((60.96, 210.82), "C25: '595\nC26: '253", 1.27)
    for i, (ref, unit, a, b, y) in enumerate((('U8', 3, 9, 10, 8), ('U8', 4, 12, 13, 11), ('U9', 3, 9, 10, 8))):
        sh.place(ref, 119.38, 152.4 + 20.32 * i, unit=unit, fields='above')
        pa, pb = sh.P(ref, a), sh.P(ref, b)
        sh.wire(pa, (pa[0] - 2.54, pa[1]), (pb[0] - 2.54, pb[1]), pb)
        sh.gnd((pb[0] - 2.54, pb[1]))
        sh.nc(sh.P(ref, y))
    # ---- the '595 bits' 100k pull-downs (hold them low while /OE is high)
    for ref, x in (('RN1', 50.8), ('RN2', 101.6)):
        sh.place(ref, x, 246.38, rot=270, fields='above')
        for n in (1, 2, 3, 4):
            p = sh.P(ref, n)
            sh.tag(p, sh.parts[ref].pins[str(n)])
        g = [sh.P(ref, n) for n in (5, 6, 7, 8)]
        ys = sorted(p[1] for p in g)
        gx = g[0][0] + 2.54
        for p in g:
            sh.wire(p, (gx, p[1]))
        sh.wire(*[(gx, y) for y in ys])
        sh.gnd((gx, ys[-1]))
    sh.text((27.94, 231.14), "100k pull-downs: the '595 bits read low while its /OE is high", 1.27)



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
