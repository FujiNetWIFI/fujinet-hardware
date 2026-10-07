"""How each sheet is drawn: placement and wiring, one function per sheet.

design.py owns the circuit; these functions only say where each part sits
and how its pins are joined (sch_draw.Sheet), left to right in signal-flow
order.  Parts are addressed by their design.py key (K['U_RP']), never by
reference, so adding a part never re-wires a sheet.  sch_draw.Sheet.check()
and gen_sch.netlist_parity() prove the drawing is exactly design.py's
netlist, so a wiring slip here fails the build.
"""
import design as D
import sch_draw
from sch_draw import Sheet, Pt as Pt_

DRAW = {}
K = D.KEY


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


def nc_unused(sh, ref, unit=1):
    for num, pt in sh.placed[(ref, unit)]['pins'].items():
        if sh.parts[ref].pins[num] is None:
            sh.nc(pt)


# =========================================================================
@sheet('edge-rp2354a')
def edge_rp2354a(sh):
    """The cartridge edge on the left, the RP2354A beside it, mirrored so its
    GPIO column faces the edge: A0-A12 and D0-D7 are 21 straight wires from
    finger to pin.  The RP's supplies and core regulator across the top; the
    clock, RUN / BOOTSEL, USB to the S3 and SWD leave on the right toward the
    ESP32-S3 sheet; the spare GPIOs (debug UART, LED, console 5 V sense) step
    out above and below the bus."""
    U, J = K['U_RP'], K['J_EDGE']
    X, Y = 228.6, 152.4
    sh.place(U, X, Y, mirror='y', ref_at=(X - 20.32, Y + 45.72, 'left'), val_at=(X - 20.32, Y + 48.26, 'left'))
    P = lambda n: sh.P(U, n)
    gp = lambda g: sh.P(U, D.RP_GPIO_PIN[g])
    xg = gp(2)[0]                                       # the GPIO column (pin ends), facing left
    # ---- the edge, level with GPIO2..22
    jx = X - 78.74
    sh.place(J, jx, 0)
    jy = gp(2)[1] - sh.N(J, 'CA0')[1]                    # A0 level with GPIO2
    sh.place(J, jx, jy, fields='left')
    sh.sup(sh.P(J, 23), 'CONS_5V')
    g1, g2 = sh.P(J, 12), sh.P(J, 24)
    sh.wire(g2, g2.go(2.54), g1.go(2.54), g1)
    sh.gnd(g1.go(2.54))
    for net in ['CA%d' % i for i in range(13)] + ['CD%d' % i for i in range(8)]:
        a, b = sh.N(J, net), sh.N(U, net)
        assert a[1] == b[1], (net, a, b)
        sh.wire(a, b)
        sh.label((a[0] + 2.54, a[1]), net)
    # the two bus names that make those local labels global (KiCad names a local
    # label after the member of a global bus label on the same sheet)
    bx, by = jx - 5.08, Y + 53.34
    sh.text((bx, by - 6.35), 'Bus names of the 21 edge wires', 1.27)
    for k, (name, shape) in enumerate((('CA[0..12]', 'input'), ('CD[0..7]', 'bidirectional'))):
        y = by + 5.08 * k
        sh.bus((bx, y), (bx + 7.62, y))
        sh.glabel(Pt_(bx + 7.62, y, 1, 0), name, 'R', shape)
    # ---- debug UART (GPIO0/1) up to two test pads, above the bus
    for g, x, tp, fl in ((0, xg - 5.08, 'TP_TX', 'left'), (1, xg - 15.24, 'TP_RX', 'left')):
        p = gp(g)
        sh.wire(p, (x, p[1]), (x, Y - 50.8))
        sh.place(K[tp], x, Y - 50.8, fields=fl)
    sh.name((xg - 5.08, Y - 45.72), 'RP_TX', 'R', 'R')
    sh.name((xg - 15.24, Y - 45.72), 'RP_RX', 'L', 'L')
    # ---- below the bus: the activity LED (GPIO25) and the console 5 V sense (GPIO27)
    p = gp(25)
    x = xg - 12.7
    rl, dl = K['R_LED'], K['D_LED']
    sh.place(rl, x, Y + 34.29, fields='left')
    sh.wire(p, (x, p[1]), sh.P(rl, 1))
    sh.place(dl, x, Y + 41.91, rot=90, fields='left')             # anode up, onto R_LED
    sh.gnd(sh.P(dl, 1), 2.54)
    sh.name((x, Y + 27.94), 'RP_LED', 'L', 'L')
    sh.name(sh.P(rl, 2), 'RP_LED_A', 'L', 'L')
    p = gp(27)
    sh.wire(p, (xg - 5.08, p[1]), (xg - 5.08, Y + 40.64))
    sh.glabel(Pt_(xg - 5.08, Y + 40.64, 0, 1), 'VSENSE', 'D', 'input')
    for g in (23, 24, 26, 28, 29):
        sh.nc(gp(g))
    # ---- supplies across the top: the +3V3_RP rail and its decoupling row (right),
    # the core regulator LX -> L -> DVDD and the DVDD decoupling (left)
    top = P(1)[1]                                       # pin ends of the top row
    ry = top - 15.24
    rail_pins = [P(n) for n in (49, 1, 54, 44, 53)]     # VREG_VIN IOVDD QSPI_IOVDD ADC_AVDD USB_OTP_VDD
    for q in rail_pins:
        sh.wire(q, (q[0], ry))
    av = P(46)                                          # VREG_AVDD: 33R off the rail, C_FILT to GND
    rf, cf = K['R_FILT'], K['C_FILT']
    sh.place(rf, av[0], ry + 3.81, fields='left')
    nd = (av[0], top - 5.08)
    cx = av[0] + 22.86
    sh.wire(sh.P(rf, 2), nd, av)
    sh.wire(nd, (cx, nd[1]))
    sh.place(cf, cx, nd[1] + 3.81, fields='right')
    sh.gnd(sh.P(cf, 2))
    sh.flag((cx, nd[1]), 'VREG_AVDD')
    sh.name((av[0] + 5.08, nd[1]), 'VREG_AVDD', 'D', 'R')
    caps = [K[k] for k in ('C_VIN', 'C_IOVDD1', 'C_IOVDD11', 'C_IOVDD20', 'C_IOVDD30', 'C_IOVDD38',
                           'C_IOVDD45', 'C_ADC', 'C_OTP', 'C_RPBULK')]
    xs = [av[0] + 43.18 + 11.43 * i for i in range(len(caps))]
    for c, x in zip(caps, xs):
        sh.place(c, x, ry + 3.81, fields='right')
        sh.gnd(sh.P(c, 2))
    sh.wire(*sorted({(q[0], ry) for q in rail_pins} | {(av[0], ry)} | {(x, ry) for x in xs}))
    sh.sup((rail_pins[0][0], ry), '+3V3_RP')
    # core regulator: LX up and left through the inductor, DVDD on to its caps;
    # FB and the DVDD pins join that node
    lx, fb, dv = P(48), P(50), P(6)
    ly = top - 25.4
    L = K['L_VREG']
    sh.place(L, lx[0] - 7.62, ly, rot=90, fields='below')         # pin 1 (DVDD) left, pin 2 (LX) right
    sh.wire(lx, (lx[0], ly), sh.P(L, 2))
    dcaps = [K[k] for k in ('C_VOUT', 'C_DVDD39', 'C_DVDD6', 'C_DVDD23')]
    node = (dv[0] - 10.16, ly)
    dx = [node[0] - 5.08 - 11.43 * i for i in range(4)]
    sh.wire(sh.P(L, 1), node, *[(x, ly) for x in dx])
    for c, x in zip(dcaps, dx):
        sh.place(c, x, ly + 3.81, fields='right')
        sh.gnd(sh.P(c, 2))
    sh.wire(dv, (dv[0], top - 5.08), (node[0], top - 5.08), node)
    sh.wire(fb, (fb[0], top - 2.54), (dv[0], top - 2.54))
    sh.flag((dx[-1], ly), 'DVDD')
    sh.name(node, 'DVDD', 'U', 'L')
    sh.name((lx[0], top - 12.7), 'RP_LX', 'L', 'L')
    # ground pins
    g, pg = P(61), P(47)
    sh.wire(pg, pg.go(2.54), g.go(2.54))
    sh.wire(g, g.go(2.54))
    sh.gnd(g.go(2.54))
    # ---- right side (the mirrored symbol's left column): toward the S3 sheet
    xr = P(26)[0]
    col = xr + 66.04                                     # global labels to the S3 sheet
    # RUN: pull-up, the RESET button through the BAT54C (also resets the S3), S3 IO4
    run = P(26)
    ry_ = run[1]
    pts = [(xr + 7.62, ry_), (xr + 12.7, ry_), (xr + 48.26, ry_)]
    sh.wire(run, *pts)
    sh.place(K['R_RUNPU'], pts[0][0], ry_ - 3.81, fields='left')
    sh.sup(sh.P(K['R_RUNPU'], 1), '+3V3_RP')
    D1 = K['D_RST']
    sh.place(D1, xr + 20.32, ry_ - 7.62, rot=180, mirror='y', fields='below')   # A1 left, A2 right, K up
    sh.wire(pts[1], sh.P(D1, 1))
    sh.wire(sh.P(D1, 2), (col, sh.P(D1, 2)[1]))
    sh.glabel((col, sh.P(D1, 2)[1]), 'S3_EN', 'R', 'bidirectional')
    k = sh.P(D1, 3)
    sw = K['SW_RESET']
    sh.place(sw, xr + 27.94, ry_ - 17.78, fields='above')
    sh.wire(k, (k[0], ry_ - 17.78), sh.P(sw, 1))
    sh.wire(sh.P(sw, 2), (xr + 38.1, ry_ - 17.78))
    sh.gnd((xr + 38.1, ry_ - 17.78))
    sh.name((k[0], ry_ - 15.24), 'RST_BTN', 'R', 'R')
    rc = K['R_RUNCTL']
    sh.place(rc, pts[2][0] + 3.81, ry_, rot=270, fields='above')     # pin 2 (RUN) left, pin 1 right
    sh.wire(pts[2], sh.P(rc, 2))
    sh.wire(sh.P(rc, 1), (col, ry_))
    sh.glabel((col, ry_), 'RUN_CTL', 'R', 'input')
    sh.name((xr + 2.54, ry_), 'RUN', 'D', 'R')
    # USB to the S3: 27R series pair
    for pin, r, net, rnet, d in ((51, 'R_USBM', 'USB_DM', 'RP_USB_DM', 'U'), (52, 'R_USBP', 'USB_DP', 'RP_USB_DP', 'D')):
        p = P(pin)
        rr = K[r]
        sh.place(rr, xr + 38.1, p[1], rot=270, fields='above' if pin == 51 else 'below')
        sh.wire(p, (xr + 15.24, p[1]), sh.P(rr, 2))
        sh.wire(sh.P(rr, 1), (col, p[1]))
        sh.glabel((col, p[1]), net, 'R', 'bidirectional')
        sh.name((xr + 15.24, p[1]), rnet, d, 'R')
    # QSPI_SS (BOOTSEL): button branch, pull-up, S3 IO5 branch
    ss = P(60)
    q = ss[1]
    pts = [(xr + 15.24, q), (xr + 43.18, q), (xr + 53.34, q)]
    sh.wire(ss, *pts)
    sh.name((xr + 2.54, q), 'QSPI_SS', 'U', 'R')
    rb, sw = K['R_SSBTN'], K['SW_BOOTSEL']
    sh.place(rb, pts[0][0], q + 3.81, fields='left')
    sh.place(sw, pts[0][0] + 10.16, q + 7.62, fields='below')
    sh.wire(sh.P(rb, 2), sh.P(sw, 1))
    sh.wire(sh.P(sw, 2), (xr + 33.02, q + 7.62))
    sh.gnd((xr + 33.02, q + 7.62))
    sh.name((pts[0][0] + 2.54, q + 7.62), 'BOOTSEL_BTN', 'D', 'L')
    sh.place(K['R_SSPU'], pts[1][0], q + 3.81, rot=180, fields='right')
    sh.sup(sh.P(K['R_SSPU'], 1), '+3V3_RP', rot=180)
    sc = K['R_SSCTL']
    sh.place(sc, pts[2][0] + 3.81, q, rot=270, fields='above')
    sh.wire(pts[2], sh.P(sc, 2))
    sh.wire(sh.P(sc, 1), (col, q))
    sh.glabel((col, q), 'BOOTSEL_CTL', 'R', 'input')
    for n in (55, 56, 57, 58, 59):
        sh.nc(P(n))
    # 12 MHz crystal: XIN straight to the crystal and its load cap, XOUT through the 1k
    xi, xo = P(21), P(22)
    Yc, rx, c1, c2 = K['Y_XTAL'], K['R_XOUT'], K['C_XIN'], K['C_XOUT']
    cx = xr + 30.48
    sh.place(Yc, cx, xi[1] + 3.81, rot=270, mirror='y', fields='left')   # XIN top, XOUT_Y bottom, GND right
    sh.wire(xi, sh.P(Yc, 1), (cx + 15.24, xi[1]))
    sh.place(c1, cx + 15.24, xi[1] + 3.81, fields='right')
    sh.gnd(sh.P(c1, 2))
    g2 = sh.P(Yc, 2)
    sh.wire(g2, (g2[0] + 2.54, g2[1]))
    sh.gnd((g2[0] + 2.54, g2[1]))
    sh.place(rx, xr + 10.16, xo[1], rot=90, fields='above')        # pin 1 (XOUT) left
    sh.wire(xo, sh.P(rx, 1))
    sh.wire(sh.P(rx, 2), (cx, xo[1]), sh.P(Yc, 3))
    sh.place(c2, cx, xo[1] + 3.81, fields='right')
    sh.wire((cx, xo[1]), sh.P(c2, 1))
    sh.gnd(sh.P(c2, 2))
    sh.name((xr + 5.08, xi[1]), 'XIN', 'U', 'R')
    sh.name((xr + 2.54, xo[1]), 'XOUT', 'D', 'R')
    sh.name((xr + 17.78, xo[1]), 'XOUT_Y', 'D', 'R')
    # SWD test pads (+ a GND pad beside them)
    for pin, tp, net, x, fl, d in ((24, 'TP_SWCLK', 'SWCLK', xr + 10.16, 'right', 'U'),
                                   (25, 'TP_SWDIO', 'SWDIO', xr + 20.32, 'below', 'D')):
        p = P(pin)
        sh.wire(p, (x, p[1]))
        sh.place(K[tp], x, p[1], rot=270, fields=fl)
        sh.name((xr + 2.54, p[1]), net, d, 'R')
    t = K['TP_GND']
    sh.place(t, xr + 40.64, P(25)[1], fields='right')
    sh.gnd(sh.P(t, 1))


# =========================================================================
@sheet('esp32s3-sd')
def esp32s3_sd(sh):
    """ESP32-S3 in the middle: EN / BOOT on the left (with the RP sheet's RESET and
    the USB bridge's auto-program lines coming in), UART / USB / SD / LED out on
    the right; the SD lines fan out to the socket and are named on the way."""
    U = K['U_S3']
    sh.place(U, 190.5, 149.86, fields='abovebelow', ref_at=(177.8, 120.65, 'left'),
             val_at=(167.64, 180.34, 'right'))
    # supply + decoupling above
    v = sh.P(U, 2)
    node = (v[0], 111.76)
    sh.wire(v, node, (200.66, node[1]), (213.36, node[1]))
    sh.sup(node, '+3V3')
    for c, x in ((K['C_S3'], 200.66), (K['C_S3BULK'], 213.36)):
        sh.place(c, x, node[1] + 3.81)
        sh.gnd(sh.P(c, 2))
    sh.gnd(sh.P(U, 1))
    # EN: pull-up, power-on delay, button; S3_EN also comes from RESET and the auto-program pair
    en = sh.P(U, 3)
    ey = 109.22
    sh.wire(en, (170.18, en[1]), (170.18, ey), (162.56, ey), (152.4, ey), (142.24, ey), (127.0, ey))
    sh.glabel((127.0, ey), 'S3_EN', 'L', 'bidirectional')
    sh.place(K['R_EN'], 162.56, ey - 3.81, fields='right')
    sh.sup(sh.P(K['R_EN'], 1), '+3V3')
    sh.place(K['C_EN'], 152.4, ey + 3.81, fields='right')
    sh.gnd(sh.P(K['C_EN'], 2))
    sh.place(K['SW_S3EN'], 142.24, ey + 5.08, rot=270, fields='left')
    sh.gnd(sh.P(K['SW_S3EN'], 2))
    # IO0 (BOOT): button + the auto-program transistor
    io0 = sh.P(U, 27)
    sh.wire(io0, (147.32, io0[1]), (137.16, io0[1]))
    sh.glabel((137.16, io0[1]), 'S3_IO0', 'L', 'bidirectional')
    sh.place(K['SW_S3BOOT'], 147.32, io0[1] + 5.08, rot=270, fields='left')
    sh.gnd(sh.P(K['SW_S3BOOT'], 2))
    # IO4 / IO5: RUN / BOOTSEL of the RP2354A
    sh.tag(sh.P(U, 4), 'RUN_CTL', shape='output')
    sh.tag(sh.P(U, 5), 'BOOTSEL_CTL', shape='output')
    # UART to the CP2102N, native USB to the RP
    sh.tag(sh.P(U, 37), 'S3_TXD', shape='output')
    sh.tag(sh.P(U, 36), 'S3_RXD', shape='input')
    sh.tag(sh.P(U, 13), 'USB_DM', shape='bidirectional')
    sh.tag(sh.P(U, 14), 'USB_DP', shape='bidirectional')
    nc_unused(sh, U)
    # microSD: SPI fans out from 2.54 to the socket's 5.08 and is named there
    J = K['J_SD']
    sh.place(J, 266.7, 160.02, fields='abovebelow', ref_at=(279.4, 186.69, 'left'),
             val_at=(279.4, 189.23, 'left'))
    for k, net in enumerate(('SD_MOSI', 'SD_SCK', 'SD_MISO', 'SD_CS', 'SD_CD')):
        a, b = sh.N(U, net), sh.N(J, net)
        x = 213.36 + (4 - k) * 2.54
        sh.wire(a, (x, a[1]), (x, b[1]), b)
        sh.name((209.55 if k == 0 else 228.6, b[1]), net, 'U', 'R')
    # pull-ups: DAT1 / DAT2 wired to the pack (DAT2 steps down to its pin), CS / MISO by label
    R = K['RN_SD']
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
    sh.place(K['R_CD'], 294.64, 177.8, fields='right')
    sh.sup(sh.P(K['R_CD'], 1), '+3V3')
    sh.tag(sh.P(K['R_CD'], 2), 'SD_CD', dirn='D')
    sh.sup(sh.N(J, '+3V3'), '+3V3', n=2.54, rot=90)
    sh.gnd(sh.P(J, 6), n=2.54, rot=270)
    shp = [sh.P(J, n) for n in (10, 11, 12, 13)]
    sh.wire(*shp)
    sh.wire(shp[0], (shp[0][0], shp[0][1] + 2.54))
    sh.gnd((shp[0][0], shp[0][1] + 2.54))
    sh.place(K['C_SD'], 284.48, 177.8)
    sh.sup(sh.P(K['C_SD'], 1), '+3V3')
    sh.gnd(sh.P(K['C_SD'], 2))
    # status LED: WS2812B on +5V, data straight from the S3 through 330R
    led = sh.P(U, 25)
    ly = 210.82
    sh.place(K['R_WS'], 218.44, ly, rot=90, fields='below')
    sh.wire(led, (210.82, led[1]), (210.82, ly), sh.P(K['R_WS'], 1))
    sh.name((210.82, 191.77), 'LED_STRIP', 'L', 'L')
    ws = K['D_WS']
    sh.place(ws, 243.84, ly, fields='right', ref_at=(251.46, ly - 1.27, 'left'), val_at=(251.46, ly + 1.27, 'left'))
    sh.wire(sh.P(K['R_WS'], 2), sh.P(ws, 3))
    sh.name((224.79, ly), 'WS_DIN', 'U', 'R')
    sh.sup(sh.P(ws, 4), '+5V')
    sh.gnd(sh.P(ws, 2))
    sh.nc(sh.P(ws, 1))
    sh.place(K['C_WS'], 279.4, ly)
    sh.sup(sh.P(K['C_WS'], 1), '+5V')
    sh.gnd(sh.P(K['C_WS'], 2))


# =========================================================================
@sheet('usb-uart')
def usb_uart(sh):
    """USB-C on the left; VBUS up onto its rail (ESD, decoupling, the bridge's
    VBUS sense), CC pull-downs, the data pair through its ESD diodes into the
    CP2102N; the bridge's UART and the esptool auto-program pair on the right."""
    J, U = K['J_USB'], K['U_UART']
    sh.place(J, 50.8, 149.86, fields='abovebelow')
    # VBUS rail: ESD, decoupling, the sense divider
    vb = sh.P(J, 'A4')
    ry = 116.84
    xs = [96.52, 109.22, 121.92]
    sh.wire(vb, (71.12, vb[1]), (71.12, ry), *[(x, ry) for x in xs], (134.62, ry))
    sh.sup((71.12, ry), 'VBUS')
    for ref, x in zip((K['D_ESDV'], K['C_VBUS'], K['C_VBUSHF']), xs):
        dio = ref == K['D_ESDV']
        sh.place(ref, x, ry + 3.81, rot=270 if dio else 0, fields='left' if dio else 'right')
        sh.gnd(sh.P(ref, 2))
    # CC pull-downs (Rd), up to ground in the space under the VBUS rail
    for pin, r, x in (('A5', K['R_CC1'], 78.74), ('B5', K['R_CC2'], 88.9)):
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
    sh.place(K['D_ESDM'], 106.68, dm[0][1] - 3.81, rot=90, fields='left')     # cathode on the line
    sh.gnd(sh.P(K['D_ESDM'], 2), rot=180)
    sh.place(K['D_ESDP'], 99.06, dp[0][1] + 3.81, rot=270, fields='right')
    sh.gnd(sh.P(K['D_ESDP'], 2))
    sh.name((116.84, dm[0][1]), 'UBRG_DM', 'D', 'R')
    sh.name((116.84, dp[0][1]), 'UBRG_DP', 'D', 'R')
    for p in (sh.P(J, 'A8'), sh.P(J, 'B8')):
        sh.nc(p)
    g1, g2 = sh.P(J, 'A1'), sh.P(J, 'SH')
    sh.wire(g2, (g2[0], g2[1] + 2.54), (g1[0], g1[1] + 2.54), g1)
    sh.gnd((g1[0], g1[1] + 2.54))
    # VBUS sense divider into the bridge's VBUS pin (self-powered bridge)
    sns = sh.P(U, 8)
    sh.place(K['R_VBH'], 134.62, ry + 3.81, fields='right')
    sh.place(K['R_VBL'], 130.81, sns[1], rot=270, fields='above')
    sh.wire(sh.P(K['R_VBH'], 2), (134.62, sns[1]), sns)
    sh.gnd(sh.P(K['R_VBL'], 2), rot=270)
    sh.name((175.26, sns[1]), 'VBUS_SNS', 'U', 'L')
    # supply, reset pull-up
    vd, vr = sh.P(U, 6), sh.P(U, 7)
    top = 116.84
    sh.wire(vr, (vr[0], top))
    sh.wire(vd, (vd[0], top), (198.12, top), (210.82, top))
    sh.wire((vr[0], top), (vd[0], top))
    sh.sup((vr[0], top), '+3V3')
    for c, x in ((K['C_CP'], 198.12), (K['C_CPBULK'], 210.82)):
        sh.place(c, x, top + 3.81)
        sh.gnd(sh.P(c, 2))
    rst = sh.P(U, 9)
    sh.place(K['R_CPRST'], 172.72, rst[1] - 3.81, fields='left')
    sh.wire(rst, (172.72, rst[1]), (167.64, rst[1]))
    sh.sup(sh.P(K['R_CPRST'], 1), '+3V3')
    sh.glabel((167.64, rst[1]), 'CP_RST', 'L')
    sh.gnd(sh.P(U, 3))
    sh.gnd(sh.P(U, 23), 2.54, rot=90)                      # /CTS tied low
    nc_unused(sh, U)
    # UART to the S3
    sh.tag(sh.P(U, 26), 'S3_RXD', shape='output')
    sh.tag(sh.P(U, 25), 'S3_TXD', shape='input')
    # esptool auto-program: DTR/RTS cross-coupled into EN / IO0 (DevKitC-1)
    rts, dtr = sh.P(U, 24), sh.P(U, 28)
    Q = K['Q_AUTO']
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
    """Left to right: the console's 5 V (sensed for the RP on the way in) through
    the P-FET and USB VBUS through the Schottky meet on +5V; +5V feeds the 3.3 V
    buck (S3, bridge, SD) and the RP's own fast LDO (+3V3_RP)."""
    y5, yv = 88.9, 116.84
    # console 5V -> P-FET (gate = VBUS: on without USB) -> +5V
    Q = K['Q_CONS']
    sh.place(Q, 68.58, y5 + 2.54, rot=90, fields='above')
    d, s, g = sh.P(Q, 3), sh.P(Q, 2), sh.P(Q, 1)
    xc = [33.02, 43.18, 53.34]
    sh.wire((25.4, y5), *[(x, y5) for x in xc], (58.42, y5), d)
    sh.sup((25.4, y5), 'CONS_5V')
    sh.flag((58.42, y5), 'CONS_5V')
    for c, x in ((K['C_CONS'], 33.02), (K['C_CONSHF'], 43.18)):
        sh.place(c, x, y5 + 3.81, fields='right')
        sh.gnd(sh.P(c, 2))
    gq = sh.P(K['C_CONS'], 2)
    sh.wire(gq, (gq[0] - 5.08, gq[1]))
    sh.flag((gq[0] - 5.08, gq[1]), 'GND')
    # console 5 V sense for the RP (GPIO27): 0.6 x CONS_5V, filtered
    vh, vl, vc = K['R_VSH'], K['R_VSL'], K['C_VS']
    sh.place(vh, 53.34, y5 - 7.62 - 3.81, rot=180, fields='left')   # pin 1 (CONS_5V) down
    sh.wire((53.34, y5), sh.P(vh, 1))
    nd = sh.P(vh, 2)
    vy = nd[1] - 2.54
    sh.wire(nd, (nd[0], vy), (63.5, vy), (73.66, vy), (83.82, vy))
    sh.place(vl, 63.5, vy + 3.81, fields='right')
    sh.gnd(sh.P(vl, 2))
    sh.place(vc, 73.66, vy + 3.81, fields='right')
    sh.gnd(sh.P(vc, 2))
    sh.glabel((83.82, vy), 'VSENSE', 'R', 'output')
    # USB VBUS -> gate, and through the SS34 onto +5V
    Dv = K['D_VBUS']
    sh.place(Dv, 83.82, yv, rot=180, fields='below')
    sh.wire((25.4, yv), (35.56, yv), (45.72, yv), (g[0], yv), sh.P(Dv, 2))
    sh.wire((g[0], yv), g)
    sh.sup((25.4, yv), 'VBUS')
    sh.flag((45.72, yv), 'VBUS')
    pd = K['R_VBPD']
    sh.place(pd, 35.56, yv + 3.81, fields='right')
    sh.gnd(sh.P(pd, 2))
    k = sh.P(Dv, 1)
    sh.wire(k, (93.98, yv), (93.98, y5))
    # +5V: the buck's input caps, a branch down to the RP LDO
    caps = [(K['C_BIN1'], 104.14), (K['C_BIN2'], 114.3), (K['C_BINHF'], 124.46)]
    sh.wire(s, (93.98, y5), *[(x, y5) for _, x in caps], (134.62, y5), (139.7, y5), (147.32, y5))
    sh.sup((93.98, y5), '+5V')
    sh.flag((139.7, y5), '+5V')
    for c, x in caps:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # 3.3 V buck
    B = K['U_BUCK']
    sh.place(B, 160.02, y5 + 2.54, fields='abovebelow', ref_at=(149.86, 82.55, 'left'), val_at=(147.32, 97.79, 'right'))
    sh.wire((147.32, y5), sh.P(B, 3))
    sh.wire(sh.P(B, 2), (147.32, sh.P(B, 2)[1]), (147.32, y5))
    sh.gnd(sh.P(B, 4))
    sw, bst, fb = sh.P(B, 5), sh.P(B, 6), sh.P(B, 1)
    cb, lb = K['C_BST'], K['L_BUCK']
    sh.place(cb, 182.88, y5 + 3.81, fields='right')
    sh.place(lb, 193.04, y5, rot=90, fields='above')
    sh.wire(sw, (182.88, y5), sh.P(lb, 1))
    sh.wire(bst, (175.26, bst[1]), (175.26, 99.06), (182.88, 99.06), sh.P(cb, 2))
    sh.name((177.8, 99.06), 'BUCK_BST', 'D', 'R')
    sh.name((173.99, y5), 'BUCK_SW', 'U', 'R')
    out = [(K['C_BOUT1'], 207.01), (K['C_BOUT2'], 217.17)]
    sh.wire(sh.P(lb, 2), (201.93, y5), *[(x, y5) for _, x in out])
    sh.wire(fb, (172.72, fb[1]), (172.72, 106.68), (201.93, 106.68), (201.93, y5))
    sh.sup((201.93, y5), '+3V3')
    sh.flag((217.17, y5), '+3V3')
    for c, x in out:
        sh.place(c, x, y5 + 3.81)
        sh.gnd(sh.P(c, 2))
    # RP LDO: +5V -> AP2112K -> +3V3_RP (IOVDD up with the console rail)
    L = K['U_LDO']
    sh.place(L, 152.4, 142.24, fields='abovebelow', ref_at=(144.78, 132.08, 'left'), val_at=(144.78, 134.62, 'left'))
    vin, en, vo = sh.P(L, 1), sh.P(L, 3), sh.P(L, 5)
    sh.wire((134.62, y5), (134.62, vin[1]), (137.16, vin[1]), (142.24, vin[1]), vin)
    sh.wire(en, (142.24, en[1]), (142.24, vin[1]))
    ci = K['C_LDOIN']
    sh.place(ci, 137.16, vin[1] + 3.81, fields='left')
    sh.gnd(sh.P(ci, 2))
    sh.gnd(sh.P(L, 2))
    sh.nc(sh.P(L, 4))
    co = K['C_LDOOUT']
    sh.wire(vo, (167.64, vo[1]), (172.72, vo[1]))
    sh.place(co, 167.64, vo[1] + 3.81)
    sh.gnd(sh.P(co, 2))
    sh.sup((172.72, vo[1]), '+3V3_RP')
