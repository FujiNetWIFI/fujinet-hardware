"""Component placement for gen_pcb.py: design.py key -> (x, y, rot).  Board body x 63.8..136.2,
y Y0 (top edge) .. 133.5 (tab base); the 47 mm tab below with the fingers, insertion edge y = 150.
Top view of the component side (F.Cu, which faces the console's REAR), y down, rotation CCW.

Fingers (x = 100 + edge_geom.pin_x): F.Cu 1 R/W 78.4, 2 /HALT 81.0 | key | 3-7 D3-D7 86.0-96.2,
8 A12 98.7, 9 A10 101.3, 10 A11 103.8, 11 A9 106.4, 12 A8 108.9, 13 +5V 111.4, 14 GND 114.0 | key |
15 A13 119.1, 16 A14 121.6.  B.Cu behind: 32 PHI2, 31 /IRQ, 30 GND, 29-27 D2-D0 88.6-93.7, 26-19
A0-A7 96.2-114.0, 18 EAUDIO 119.1, 17 A15 121.6.  So: data west of centre, address centre to east,
A13-A15 and EAUDIO east, the strobes and /IRQ at the west end, +5V right of centre.

RP2354B at rot 90 (the NES / SMS ring): its south side (pins 1-20) carries D4-D7, A0-A12 west to
east; D0-D3 at its south-west corner (pins 77-80), A13-A15 at its south-east corner (21-23), R/W,
PHI2, /HALT, PWR_OK on its east side (25-28), the slot table (SA13-SA18, ROM_EN, RAM_EN, A8MASK)
along its north side.

Regions (the cart side as variant A of the 2026-10-07 sweep: 948 ratsnest crossings, 4065 mm; with the
SRAM east of the RP instead, as on SMS Rev0, 1103 / 4145 mm, dropped):
  lower body    the RP2354B over the address fingers, its decoupling ring and core-regulator
                corner as on NES / SMS Rev0; the SRAM upright over the data fingers, its DQ / A0-A3
                end toward them; the D0-D7 100R packs between; the console 5V P-FET by finger 13,
                the audio RC by finger 18, the /IRQ FET by finger 31
  middle band   the four 74HCT packages in a row, under the SRAM's and the RP's north sides
  upper body    ESP32-S3 top-left, antenna flush with the top edge; microSD and USB-C on the top
                edge, the two status LEDs between them; CP2102N, auto-program, buck down the east
                side; the four buttons down the west edge; the bring-up / SWD test pads in a block
                above the glue (outside the console's slot when the cart is in)
The shell screws (gen_pcb.HOLES) keep 3 mm rings clear.
"""
import os

RING = 10.0              # decoupling ring radius (NES Rev0: 10, not 9 -- a second via column fits)
RX, RY = 108.0, 112.0     # RP2354B centre
RX = float(os.environ.get('RP_X', RX))      # tuning knobs (tools/plot_placement.py compares the results)
RY = float(os.environ.get('RP_Y', RY))
GLUE = os.environ.get('GLUE_ORDER', 'INV,NAND2,CSEL,STROBE').split(',')
SRAM_XY = tuple(float(v) for v in os.environ.get('SRAM_XY', '76.0,112.0').split(','))


def ring(place, rx, ry, ldo_xy):
    """The RP2354B and its NES / SMS Rev0 ring (same package, same rotation, same circuit)."""
    place('U_RP', rx, ry, 90)
    # south: D4-D7 / A0-A12; IOVDD 5 (x -2.2), DVDD 10 (-0.2), IOVDD 15 (+1.8)
    place('C_IOV5', rx - 2.2, ry + RING, 270)     # pad 1 toward the chip
    place('C_IOV15', rx + 1.8, ry + RING, 270)
    # east: the IOVDD 24/29 caps at the south-east corner, NOT in front of their pins
    # (in line they wall in R/W, PHI2, /HALT, PWR_OK, pins 25-28)
    place('C_IOV24', rx + 8.3, ry + 6.4, 0)
    place('C_IOV29', rx + 8.3, ry + 8.1, 0)
    # crystal block, planar: XIN (pin 30) straight into Y1's south-west pad, XOUT (pin 31)
    # into the 1k on its own lane, XOUT_Y over the crystal's GND pad to the north-east pad
    place('Y_RP', rx + RING + 4.0, ry, 0)
    place('C_XIN', rx + RING + 4.0, ry + 3.6, 270)
    place('C_XOUT', rx + RING + 7.0, ry - 2.6, 90)
    place('R_XOUT', rx + 9.0, ry - 0.7, 0)
    # north: IOVDD 41 (x +3.8), 50 (+0.2), 60 (-3.8), ADC_AVDD 59 (-3.4)
    place('C_IOV41', rx + 3.8, ry - RING, 90)
    place('C_IOV50', rx + 0.2, ry - RING, 90)
    place('C_IOV60', rx - 4.4, ry - RING, 90)
    place('C_ADC', rx - 2.4, ry - RING, 90)
    # west: VREG corner (61-65), USB 66/67, QSPI, IOVDD 76, D0-D3; the DVDD lobe of the
    # In4 island spans x rx-16..rx-3.6, y ry-5.6..ry-1.6
    place('L_RP', rx - 7.6, ry - 3.0, 0)        # pad 2 (LX) east toward pin 63
    place('C_DVBULK', rx - 11.0, ry - 2.6, 180)
    place('C_DV51', rx - 14.2, ry - 2.6, 180)
    place('C_DV10', rx - 8.6, ry - 4.8, 180)
    place('C_DV32', rx - 11.8, ry - 4.8, 180)
    place('C_VREGIN', rx - RING - 4.4, ry - 0.6, 180)
    place('R_AVDD', rx - 10.5, ry - 11.0, 0)
    place('C_AVDD', rx - 7.2, ry - 11.0, 0)
    # D- (pin 66) is the northern pin: its 27R sits north
    place('R_USBM', rx - RING - 0.6, ry - 0.6, 0)
    place('R_USBP', rx - RING - 0.6, ry + 1.1, 0)
    place('C_OTP', rx - RING - 0.6, ry + 2.8, 180)
    place('C_QSPI', rx - RING - 0.6, ry + 4.5, 180)
    place('R_SS', rx - RING - 0.6, ry + 6.2, 180)
    place('C_IOV76', rx - RING - 0.6, ry + 7.9, 180)
    place('R_BSELCTL', rx - RING - 4.4, ry + 1.1, 180)
    place('R_BSEL', rx - RING - 4.4, ry + 2.8, 180)
    place('C_IOBULK', rx - RING - 4.4, ry + 4.5, 180)
    # RP LDO: input on +5V, output on the +3V3_RP island (gen_pcb.rp_io_island covers it)
    lx, ly = ldo_xy
    place('U_LDO', lx, ly, 0)
    place('C_LDOIN', lx - 2.6, ly - 3.2, 90)
    place('C_LDOOUT', lx + 2.6, ly - 3.2, 90)
    # RUN pull-up and the S3's RUN line north-east of the RP, clear of the east-side escapes
    place('R_RUN', rx + 14.5, ry - 9.5, 0)
    place('R_RUNCTL', rx + 14.5, ry - 11.2, 0)


def do_placement(place, fiducials):
    # ---------------- edge ----------------
    place('J_EDGE', 100.0, 150.0, 0)

    # ---------------- cart side: the RP over the address fingers, the SRAM west of it ----------------
    rx, ry = RX, RY
    ring(place, rx, ry, (rx - 13.5, ry + 13.5))
    # SRAM upright, pins 17-32 (A0-A3, DQ0-7, A10, /OE) south toward the data fingers
    sx, sy = SRAM_XY
    place('U_SRAM', sx, sy, 270)
    place('C_SRAM', sx, sy - 12.5, 0)        # by VCC (pin 8, north end)
    place('C_SRAMBULK', 79.5, 97.5, 0)
    # D0-D7 100R packs between the RP's south-west corner and the data fingers, rotated so their
    # RP side (pins 1-4) faces east toward GPIO0-7 and their D side west toward the SRAM and the
    # fingers.  At rotation 0 RP_D4-D7 had to wrap round RN_D4 into the 1.7 mm channel RN_D0's
    # D0-D3 also need, and every route left RP_D5 open (design review Part 2, Routing).
    place('RN_D0', 85.5, 126.5, 180)       # 1 mm west of the 86.5 first tried: room for a via column
    place('RN_D4', 90.0, 126.5, 180)

    # console 5V P-FET by finger 13 (x 111.4), its bulk beside it
    place('Q_CONS', 111.0, 128.8, 270)
    place('C_CONS', 114.6, 128.8, 90)
    place('C_CONSHF', 116.4, 128.8, 90)
    # cart audio by finger 18 (x 119.1): PWM low-pass, level, DC block
    place('R_AUDLP', 128.0, 129.0, 90)
    place('C_AUDLP', 126.2, 129.0, 90)
    place('R_AUDLVL', 124.4, 129.0, 90)
    place('C_AUDDC', 122.6, 129.0, 90)
    # /HALT's 10k right at finger 2 (x 81.0): the console sees only the stub to it
    place('R_HALT', 83.5, 130.8, 90)
    # /IRQ FET by finger 31 (x 81.0), its gate pull-down beside it
    place('Q_IRQ', 80.5, 128.6, 270)
    place('R_IRQ', 77.0, 128.6, 90)
    # console 5V sense divider by finger 13 too (VSENSE runs to the '14)
    place('R_VSH', 118.5, 128.8, 90)
    place('R_VSL', 120.3, 128.8, 90)

    # ---------------- middle band: the glue ----------------
    gy = 92.0
    for i, (k, c) in enumerate(('U_' + g, 'C_' + g) for g in GLUE):
        x = 75.0 + 10.5 * i
        place(k, x, gy, 0)
        place(c, x + 4.9, gy - 6.0, 90)
    place('R_PDROM', 112.5, 92.5, 90)
    place('R_PDRAM', 114.3, 92.5, 90)
    place('R_PDA8M', 116.1, 92.5, 90)

    # ---------------- upper body: the FujiNet half ----------------
    from gen_pcb import Y0, X0, X1
    place('U_S3', 75.7, Y0 + 13.0, 0)        # antenna end at the top edge; 3 mm in for the west pads' fan-out
    place('C_S3BULK', 87.2, Y0 + 12.0, 90)  # east of the module, below the antenna band
    place('C_S3', 89.2, Y0 + 12.0, 90)
    place('R_EN', 87.2, Y0 + 16.0, 90)
    place('C_EN', 89.2, Y0 + 16.0, 90)
    # microSD and USB-C on the top edge, east of the antenna keep-out (x <= 99.7)
    place('J_SD', 109.3, Y0 + 10.0, 180)
    place('RN_SD', 104.0, Y0 + 20.0, 90)
    place('R_SDCD', 109.0, Y0 + 19.5, 90)
    place('C_SD', 111.0, Y0 + 19.5, 90)
    place('J_USB', 127.4, Y0 + 5.0, 180)
    # status LEDs between the microSD and the USB-C, at the top edge (a shell window)
    place('D_WS', 120.0, Y0 + 2.5, 0)
    place('R_WS', 120.0, Y0 + 6.0, 90)
    place('C_WS', 120.0, Y0 + 9.0, 0)
    place('D_LED', 120.0, Y0 + 12.0, 90)
    place('R_LED', 120.0, Y0 + 15.5, 90)
    # USB-C support, the CP2102N and the auto-program pair down the east side
    place('R_CC1', 122.4, Y0 + 12.0, 90)
    place('R_CC2', 133.0, Y0 + 12.0, 90)
    place('D_ESDP', 124.6, Y0 + 12.0, 90)
    place('D_ESDM', 129.4, Y0 + 12.0, 90)
    place('D_ESDV', 123.0, Y0 + 15.5, 0)
    place('C_VBUS', 127.0, Y0 + 15.5, 0)
    place('C_VBUSHF', 131.0, Y0 + 15.5, 0)
    place('R_VBPD', 133.8, Y0 + 19.0, 90)     # VBUS / P-FET gate pull-down
    place('D_VBUS', 133.0, Y0 + 24.5, 90)     # SS34 VBUS -> +5V
    place('U_UART', 125.0, Y0 + 24.0, 270)
    place('C_UART', 119.5, Y0 + 21.0, 90)
    place('C_UARTBULK', 119.5, Y0 + 24.0, 90)
    place('R_VBSH', 119.5, Y0 + 27.5, 0)
    place('R_VBSL', 119.5, Y0 + 29.3, 0)
    place('R_CPRST', 129.5, Y0 + 19.5, 90)
    place('U_AUTOPROG', 125.5, Y0 + 30.5, 0)
    # 3.3 V buck below them, its input on the +5V strip up the east edge
    place('U_BUCK', 128.5, Y0 + 39.0, 180)
    place('C_BIN1', 133.5, Y0 + 35.0, 90)
    place('C_BIN2', 133.5, Y0 + 38.5, 90)
    place('C_BINHF', 133.5, Y0 + 42.0, 90)
    place('C_5VBULK', 133.5, Y0 + 46.0, 90)
    place('C_BST', 128.5, Y0 + 35.0, 0)
    place('L_BUCK', 123.0, Y0 + 39.0, 0)
    place('C_BOUT1', 119.0, Y0 + 36.0, 90)
    place('C_BOUT2', 119.0, Y0 + 39.5, 90)
    # buttons down the west edge, under the module
    place('SW_S3EN', 68.6, Y0 + 30.0, 0)
    place('SW_S3BOOT', 68.6, Y0 + 36.2, 0)
    place('SW_RESET', 68.6, Y0 + 42.4, 0)
    place('SW_BOOTSEL', 68.6, Y0 + 48.6, 0)
    place('D_RST', 74.5, Y0 + 42.4, 0)
    # bring-up / SWD test pads: one block right above the glue row (short stubs off PHI2, R/W and
    # the strobes, which pass the glue; 68-71 mm above the edge, outside the console's slot), two rows
    tps = ['TP_PHI2', 'TP_RW', 'TP_HALT', 'TP_EAUDIO', 'TP_CONS5V', 'TP_GNDBUS', 'TP_CSEL', 'TP_OE', 'TP_WE',
           'TP_SA8', 'TP_PWROK', 'TP_5V', 'TP_3V3', 'TP_3V3RP', 'TP_SWCLK', 'TP_SWDIO', 'TP_GND', 'TP_RUN']
    for i, k in enumerate(tps):
        place(k, 81.0 + 2.6 * (i % 9), 79.0 + 2.6 * (i // 9), 0)
    place('J_DBG', 106.0, Y0 + 33.0, 90)     # debug UART header (DNP)

    fiducials += [('FID1', X1 - 2.0, Y0 + 50.0), ('FID2', X0 + 2.0, Y0 + 55.0), ('FID3', X0 + 3.0, 118.0)]
