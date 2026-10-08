"""Component placement for gen_pcb.py: design.py key -> (x, y, rot).  Board
body x 50..150, y 32 (top edge) .. 110 (tab base); fingers on the tab below,
insertion edge y = 125.  Top view (the component side, which faces the
label), y down, rotation CCW.

Fingers: pins 1/2 east (x 130.5) .. 49/50 west (69.5); even pins on F.Cu.
The console bus: D0-D7 x 102-115, A0-A7 x 92-100 (centre), A8-A11 / A13 /
A14 x 118-126 and the strobes /RD /WR /MREQ /CE x 115-131 (east), A12 /
A15 / /M1 / /IORQ / /WAIT / /RESET / CLK x 72-90 (west), +5V on 1 (east)
and 35 (west, x 87.3), GND 19-21 (x 105-108).

Regions:
  centre-south  RP2354B at (98, 86) rot 90: A4-A15 / D0-D3 (pins 1-20) face
                the fingers, D4-D7 and the strobes the south-east, the glue
                lines and SRAM bank lines the north, VREG / USB / QSPI the west;
                its decoupling ring and core-regulator corner are the NES Rev0
                arrangement (same package, same rotation, same circuit)
  east          the two SRAMs stacked (one bus, short hops between them), the
                five 74HCT packages in two rows under them
  south band    the D0-D7 100R packs over the data fingers, the console 5V
                P-FET (finger 1), the RP LDO, the /WAIT FET (finger 41)
  north-west    ESP32-S3, antenna flush with the top edge; its caps on the west edge
  north-middle  microSD (slot at the top edge), status LEDs below it
  north-east    USB-C (top edge), ESD, CP2102N + auto-program, the 3.3 V buck,
                the VBUS Schottky
  west edge     the four buttons (S3 EN, S3 BOOT, RESET, BOOTSEL)
The shell screws (gen_pcb.HOLES) keep 3 mm rings clear.
"""

RX, RY = 98.0, 86.0      # RP2354B centre
RING = 10.0              # decoupling ring radius (NES Rev0: 10, not 9 -- a second via column fits)


def do_placement(place, fiducials):
    rx, ry = RX, RY
    # ---------------- edge ----------------
    place('J_EDGE', 100.0, 125.0, 0)
    place('TP_CONT', 89.5, 107.3, 0)          # finger 34 (x 89.84)
    place('TP_BUSREQ', 76.5, 107.0, 0)        # finger 44 (x 77.14)

    # ---------------- RP2354B: the NES Rev0 ring ----------------
    place('U_RP', rx, ry, 90)
    # south: A4-A15 / D0-D3; IOVDD 5 (x -2.2), DVDD 10 (-0.2), IOVDD 15 (+1.8)
    place('C_IOV5', rx - 2.2, ry + RING, 270)     # pad 1 toward the chip
    place('C_IOV15', rx + 1.8, ry + RING, 270)
    # east: the IOVDD 24/29 caps at the south-east corner, NOT in front of their pins
    # (in line they wall in the strobes, pins 25-28)
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
    # west: VREG corner (61-65), USB 66/67, QSPI, IOVDD 76, A0-A3; the DVDD lobe of the
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
    # RP LDO just south-west of the ring: input on +5V, output on the +3V3_RP island
    place('U_LDO', rx - 13.5, ry + 13.5, 0)
    place('C_LDOIN', rx - 16.0, ry + 10.5, 180)
    place('C_LDOOUT', rx - 9.2, ry + 11.0, 180)
    # RUN pull-up and the S3's RUN line north-east of the RP, clear of the strobes' escape:
    # /IORQ /RESET /M1 CLK (pins 36-39, y -2.2..-3.4) leave east and turn north for the west
    # fingers; with the two resistors in front of them (rx + 10, ry - 6) /IORQ stayed open
    # (variant run 2026-10-07).  SWD pads south-east: the pads are south of their pins, so the
    # southern pin (SWCLK, 33) takes the western pad and SWDIO (34) / RUN (35) the ones east of it
    place('R_RUN', rx + 14.5, ry - 9.5, 0)
    place('R_RUNCTL', rx + 14.5, ry - 11.2, 0)
    for i, k in enumerate(('TP_SWCLK', 'TP_SWDIO', 'TP_GND', 'TP_RUN')):
        place(k, 107.0 + 2.6 * i, 96.5, 0)
    # D0-D7 100R packs over the data fingers (x 102-115)
    place('RN_D0', 102.5, 101.5, 0)
    place('RN_D4', 109.5, 101.5, 0)
    # /WAIT FET at finger 41 (x 79.68), its gate pull-up beside it
    place('Q_WAIT', 81.0, 103.5, 0)
    place('R_WAIT', 84.5, 104.0, 90)
    # debug header (DNP) west of the VREG corner
    place('J_DBG', 74.5, 76.0, 90)
    # status LEDs below the microSD
    place('D_LED', 106.0, 66.5, 0)
    place('R_LED', 103.0, 66.5, 0)

    # ---------------- SRAMs + glue (variants while choosing) ----------------
    import os
    v = os.environ.get('PLACE_VARIANT', 'C')
    if v == 'A':      # SRAMs stacked north-east, glue rows under them
        sram = [('U_SRAM0', 132.0, 66.0, 0), ('U_SRAM1', 132.0, 78.0, 0)]
        caps = [('C_SRAM0', 124.0, 72.0, 0), ('C_SRAM1', 124.0, 84.0, 0), ('C_SRAMBULK', 140.5, 72.0, 0)]
        glue = [('U_NAND3', 121.0, 92.0), ('U_NORWE', 130.5, 92.0), ('U_INV', 140.0, 92.0),
                ('U_NORDEC', 121.0, 104.0), ('U_NAND2', 130.5, 104.0)]
    else:             # SRAMs over the east fingers, glue rows above them
        r = {'B': 180, 'D': 0}.get(v, 180)
        if v == 'C':  # side by side, upright: data / A0-A3 end toward the fingers
            sram = [('U_SRAM0', 125.0, 96.5, 270), ('U_SRAM1', 137.0, 96.5, 270)]
            caps = [('C_SRAM0', 131.0, 90.0, 90), ('C_SRAM1', 143.0, 90.0, 90), ('C_SRAMBULK', 131.0, 101.0, 90)]
        else:
            sram = [('U_SRAM0', 131.5, 91.0, r), ('U_SRAM1', 131.5, 103.0, r)]
            caps = [('C_SRAM0', 123.5, 97.0, 0), ('C_SRAM1', 139.5, 97.0, 0), ('C_SRAMBULK', 131.5, 97.0, 0)]
        glue = [('U_NAND3', 120.0, 67.0), ('U_NORWE', 129.0, 67.0), ('U_INV', 138.0, 67.0),
                ('U_NORDEC', 120.0, 79.0), ('U_NAND2', 129.0, 79.0)]
    for k, x, y, rr in sram:
        place(k, x, y, rr)
    for k, x, y, rr in caps:
        place(k, x, y, rr)
    gcap = {'U_NAND3': 'C_NAND3', 'U_NORWE': 'C_NORWE', 'U_INV': 'C_INV', 'U_NORDEC': 'C_NORDEC',
            'U_NAND2': 'C_NAND2'}
    for k, x, y in glue:
        place(k, x, y, 0)
        place(gcap[k], x, y - 5.7, 0)
    gx = {k: (x, y) for k, x, y in glue}
    place('R_VSH', gx['U_INV'][0] - 2.0, gx['U_INV'][1] + 6.3, 0)    # console 5V sense divider into the '14
    place('R_VSL', gx['U_INV'][0] + 1.5, gx['U_INV'][1] + 6.3, 0)

    # ---------------- console 5V: P-FET by finger 35 (x 87.3), next to the RP LDO ----------------
    if v == 'A':
        place('Q_CONS', 138.5, 104.0, 0)
        place('C_CONS', 138.5, 107.8, 0)
        place('C_CONSHF', 135.5, 107.8, 0)
    else:
        place('Q_CONS', 93.0, 104.0, 0)
        place('C_CONS', 96.5, 104.5, 90)
        place('C_CONSHF', 98.5, 104.5, 90)

    # ---------------- north-west: ESP32-S3 ----------------
    place('U_S3', 66.0, 45.0, 0)              # antenna end at the top edge (y 32.15)
    place('C_S3BULK', 53.5, 41.0, 90)         # west edge column, below the antenna band (y 38.25)
    place('C_S3', 53.5, 44.5, 90)
    place('R_EN', 53.5, 48.0, 90)
    place('C_EN', 53.5, 51.5, 90)
    # west edge: the buttons
    place('SW_S3EN', 55.5, 71.0, 0)
    place('SW_S3BOOT', 55.5, 79.0, 0)
    place('SW_RESET', 55.5, 87.0, 0)
    place('SW_BOOTSEL', 55.5, 95.0, 0)
    place('D_RST', 62.5, 87.0, 0)             # RESET steering by its button

    # ---------------- north-middle: microSD ----------------
    place('J_SD', 100.0, 42.0, 180)           # slot at the top edge, east of the antenna keep-out (x <= 90)
    place('RN_SD', 88.5, 51.5, 90)
    place('R_SDCD', 111.5, 50.5, 90)
    place('C_SD', 111.5, 47.0, 90)
    place('D_WS', 111.5, 62.5, 0)             # WS2812 status LED (on the +5V island)
    place('R_WS', 108.5, 62.5, 0)
    place('C_WS', 114.5, 62.5, 90)

    # ---------------- north-east: USB-C, CP2102N, buck ----------------
    place('J_USB', 126.0, 37.0, 180)
    place('R_CC1', 118.5, 38.0, 90)
    place('R_CC2', 133.5, 38.0, 90)
    place('D_ESDV', 117.5, 42.5, 90)
    place('D_ESDP', 123.0, 45.0, 0)
    place('D_ESDM', 129.0, 45.0, 0)
    place('C_VBUS', 135.5, 42.5, 90)
    place('C_VBUSHF', 137.5, 42.5, 90)
    place('R_VBPD', 140.0, 39.0, 90)          # VBUS / P-FET gate pull-down
    place('D_VBUS', 143.5, 39.0, 90)          # SS34 VBUS -> +5V
    place('U_UART', 126.0, 52.5, 270)
    place('C_UART', 120.5, 50.5, 90)
    place('C_UARTBULK', 120.5, 53.5, 90)
    place('R_VBSH', 120.5, 56.5, 0)
    place('R_VBSL', 120.5, 58.2, 0)
    place('R_CPRST', 131.5, 48.5, 90)
    place('U_AUTOPROG', 132.5, 53.0, 0)
    place('U_BUCK', 141.5, 55.0, 180)
    place('C_BIN1', 146.5, 51.0, 90)
    place('C_BIN2', 146.5, 54.5, 90)
    place('C_BINHF', 146.5, 58.0, 90)
    place('C_5VBULK', 143.5, 47.5, 0)
    place('C_BST', 141.5, 51.0, 0)
    place('L_BUCK', 136.5, 58.0, 0)
    place('C_BOUT1', 131.5, 58.5, 90)
    place('C_BOUT2', 129.0, 58.5, 90)

    fiducials += [('FID1', 147.5, 37.0), ('FID2', 52.5, 100.0), ('FID3', 147.0, 80.0)]
