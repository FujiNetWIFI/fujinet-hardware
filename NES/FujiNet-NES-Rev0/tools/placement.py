"""Component placement for gen_pcb.py: ref -> (x, y, rot).  Board x 50..150,
y 30 (top edge) .. 125.5 (tab base); fingers on the tab below, insertion
edge y = 140.  Top view, y down, rotation CCW.

Pin 1 of the edge is EAST (label side), so the CPU bus fingers (2-15 front,
38-50 back) are on the east half and the PPU bus (21-33 front, 56-69 back)
on the west half.

Regions:
  south-centre  RP2354B at (112, 100) rot 90: CPU A/D side faces the fingers
                (south), M2/R/W//ROMSEL/SR side east, bank lines north,
                VREG/USB/QSPI side west; decoupling ring on the +3V3_RP island
  north-east of the RP  PRG SRAM; north-west  CHR SRAM
  south band    the 74HCT glue between the RP and the tab (CHR side west,
                PRG strobes east), '595 + pull-downs east of the RP
  south-west    console 5V P-FET, sense divider, CIClone at the CIC fingers
  north-west    ESP32-S3 (antenna at the top edge), its EN/BOOT buttons on the west edge
  north-middle  microSD (slot at the top edge)
  north-east    USB-C (top edge), ESD, CP2102N + auto-program, buck, VBUS diode
  east edge     RESET / BOOTSEL buttons, test pads, status LED
Shell posts at (54.05, 92.2) / (145.95, 92.2) and the holes at (100, 72) /
(105.5, 62.5) are keep-clear (gen_pcb.KEEP_CLEAR).
"""

# In4 +5V islands (polygons); the +3V3_RP island (RP +/-12) and the DVDD
# lobe win over them, everything else on In4 is +3V3.  Keep the buck output
# caps and the VREG_VIN cap out of these; keep every 74HCT, SRAM, the P-FET,
# the LDO input, the WS2812 and the '595 inside.
ISLANDS_5V = [[(55.0, 60.0), (95.0, 60.0), (95.0, 104.0), (101.0, 104.0), (101.0, 124.0), (55.0, 124.0)],
              [(118.0, 64.0), (141.0, 64.0), (141.0, 48.0), (146.0, 48.0), (146.0, 124.0), (118.0, 124.0)]]


def do_placement(place):
    # ---------------- edge ----------------
    place('J1', 100, 140, 0)

    # ---------------- RP2354B ----------------
    rx, ry = 112.0, 100.0
    place('U1', rx, ry, 90)
    # south: CA4-12 / CD0-7 pins; IOVDD 5 (x -2.2), DVDD 10 (-0.2), IOVDD 15 (+1.8)
    # decoupling ring RING from the centre.  A supply pin's fan-out via sits at the end
    # of its 1.2 mm escape lane (6.9 mm out, fanout.py); the ring's pads start 1.5 mm
    # beyond that, which leaves a second via column for the signal pins between a
    # fan-out stub and a routed neighbour (at 9.0 mm there was none: every such pin
    # was left open by the routers).
    RING = 10.0
    place('C1', rx - 2.2, ry + RING, 270)     # IOVDD 5   (pad 1 toward the chip)
    place('C2', rx + 1.8, ry + RING, 270)     # IOVDD 15
    # east: M2 / R/W / ROMSEL / CA13-14 / PA10-12 / XIN XOUT / SWD / RUN / SR / IRQ
    # the east column's two IOVDD caps sit at the south-east corner, NOT in front of their
    # pins: they reach the pins through the +3V3_RP island, and in line they walled in PA10/
    # PA11 (pins 27/28); the RUN resistors moved east of the test pads for the same reason
    # (they blocked SWCLK/SWDIO, pins 33/34)
    place('C3', rx + 8.3, ry + 6.4, 0)        # IOVDD 24 (y +2.6), south-east corner
    place('C4', rx + 8.3, ry + 8.1, 0)        # IOVDD 29 (y +0.6), south-east corner
    place('R3', 137.5, 93.2, 0)               # RUN pull-up, by TP4 (RUN)
    place('R6', 137.5, 91.5, 0)               # S3 IO4 -> RUN
    # crystal block, planar: XIN (pin 30, the southern lane) runs straight into Y1's
    # south-west pad and on to its load cap below; XOUT (pin 31, the northern lane)
    # runs straight into R2, which sits on that lane between the RP and the crystal,
    # and XOUT_Y continues over the crystal's north-west GND pad to the north-east pad.
    # (R2 north of the crystal made XOUT climb diagonally across the escape lanes of
    # pins 32-35 and walled SWCLK/SWDIO off from their test pads.)
    place('Y1', rx + RING + 4.0, ry - 0.0, 0)   # crystal: pad 1 XIN south-west, pad 3 XOUT_Y north-east
    place('C19', rx + RING + 4.0, ry + 3.6, 270)  # XIN load, below pad 1
    place('C20', rx + RING + 7.0, ry - 2.6, 90)   # XOUT_Y load, north-east of pad 3 (pad 1 south, toward it)
    place('R2', rx + 9.0, ry - 0.7, 0)        # XOUT -> XOUT_Y, on the XOUT lane (pin 31 at y -0.2)
    # north: bank lines; IOVDD 41 (x +3.8), 50 (+0.2), 60 (-3.8), ADC_AVDD 59 (-3.4)
    place('C5', rx + 3.8, ry - RING, 90)      # IOVDD 41
    place('C6', rx + 0.2, ry - RING, 90)      # IOVDD 50
    place('C7', rx - 4.4, ry - RING, 90)      # IOVDD 60
    place('C11', rx - 2.4, ry - RING, 90)     # ADC_AVDD 59
    # west: VREG corner (61-65 at y -3.8..-2.2), USB 66/67, QSPI, IOVDD 76, CA0-3
    # the DVDD lobe of the In4 island spans x rx-16..rx-3.6, y ry-5.6..ry-1.6
    place('L1', rx - 7.6, ry - 3.0, 0)        # core inductor: pad 2 (LX) east toward pin 63
    place('C17', rx - 11.0, ry - 2.6, 180)    # core 4.7 uF (DVDD pad east)
    place('C16', rx - 14.2, ry - 2.6, 180)    # DVDD 100 nF x3 in the DVDD lobe
    place('C14', rx - 8.6, ry - 4.8, 180)
    place('C15', rx - 11.8, ry - 4.8, 180)
    place('C13', rx - RING - 4.4, ry - 0.6, 180)  # VREG_VIN 4.7 uF on the RP island (pin 64 reaches it through In4)
    place('R1', rx - 10.5, ry - 11.0, 0)      # 33R +3V3 -> VREG_AVDD
    place('C18', rx - 7.2, ry - 11.0, 0)      # VREG_AVDD 4.7 uF
    # design.py: R8 = USB_DP series, R9 = USB_DM series.  D- (pin 66) is the northern pin, so
    # R9 sits north (the other way round the pair has to cross)
    place('R9', rx - RING - 0.6, ry - 0.6, 0)     # USB_DM series (pin 66 y -1.8)
    place('R8', rx - RING - 0.6, ry + 1.1, 0)     # USB_DP series (pin 67 y -1.4)
    place('C10', rx - RING - 0.6, ry + 2.8, 180)  # USB_OTP_VDD (pin 68)
    place('C9', rx - RING - 0.6, ry + 4.5, 180)   # QSPI_IOVDD (pin 69)
    place('R4', rx - RING - 0.6, ry + 6.2, 180)   # QSPI_SS pull-up (+3V3_RP pad east)
    place('C8', rx - RING - 0.6, ry + 7.9, 180)   # IOVDD 76
    place('R7', rx - RING - 4.4, ry + 1.1, 180)   # S3 IO5 -> QSPI_SS
    place('R5', rx - RING - 4.4, ry + 2.8, 180)   # QSPI_SS -> BOOTSEL button
    place('C12', rx - RING - 4.4, ry + 4.5, 180)  # RP IO rail bulk 10 uF
    # RP I/O LDO just south-west of the RP: input cap on the +5V island, output cap on the RP island
    place('U15', 98.5, 113.5, 0)
    place('C49', 96.0, 110.5, 180)            # LDO in (+5V pad east -> island (95..101, 104..124))
    place('C50', 102.8, 111.0, 180)           # LDO out (+3V3_RP pad east -> RP island)
    # test pads east of the RP, north of the '595
    # SWDIO (TP2, pin 34) leaves the RP north of SWCLK (TP1, pin 33): its pad comes first, west,
    # so the two escapes do not cross
    for i, tp in enumerate(('TP2', 'TP1', 'TP3', 'TP4', 'TP5', 'TP6')):
        place(tp, 121.5 + 2.5 * i, 92.0, 0)

    # ---------------- SRAMs ----------------
    place('U2', 130.0, 84.0, 0)               # PRG: CPU A0-12 / D0-7 + GP33-38
    place('C22', 123.8, 77.6, 90)             # PRG VCC (pin 8) decoupling
    place('U3', 82.0, 84.0, 0)                # CHR: PPU A0-9 / D0-7 + GP39-47
    place('C23', 75.8, 77.6, 90)
    place('C24', 96.0, 106.0, 0)              # 5V logic bulk

    # ---------------- 74HCT glue ----------------
    place('U4', 134.0, 101.0, 0)              # '595 east of the RP (SER/SRCLK/RCLK on the RP's east side)
    place('C25', 134.0, 108.6, 0)
    place('RN1', 140.6, 98.5, 90)             # pull-downs
    place('RN2', 140.6, 103.0, 90)
    place('R13', 137.5, 108.4, 0)             # LED
    place('D2', 137.5, 110.6, 0)
    # CHR-side glue: the '32 and the '253 stand in a column on the far west, beside the CHR
    # SRAM's west end and OUT of the band the PPU bus crosses from the west fingers to the CHR
    # SRAM (in that band they left 5-8 links unroutable in every build); the '14 (mostly
    # CPU-side signals) stays in the south band, as do the PRG-side '20 and '00
    place('U5', 61.5, 84.5, 0)                # '253: CIRAM A10 / CIRAM /CE
    place('U9', 61.5, 96.5, 0)                # '32: CHR /OE /WE, CIRAM /CE pre-gate
    place('C26', 66.5, 84.5, 90)
    place('C30', 66.5, 96.5, 90)
    place('U6', 92.0, 116.0, 0)               # '14
    place('U7', 125.0, 116.0, 0)              # '20: PRG /WE (M2), /CE
    place('U8', 133.0, 116.0, 0)              # '00: PRG /OE, '595 /OE
    for ref, x in (('C27', 92.0), ('C28', 125.0), ('C29', 133.0)):
        place(ref, x, 122.6, 0)
    place('C21', 97.5, 108.5, 0)              # POR_RC 1 uF to +5V (on the +5V island, near the '14)
    place('R12', 99.6, 110.5, 0)              # POR_RC 100k

    # ---------------- south-west: console 5V, sense, CIClone ----------------
    place('Q1', 59.0, 119.5, 0)               # P-FET at the +5V finger (36, x 55.75)
    place('C41', 63.0, 119.5, 0)              # CONS_5V bypass
    place('R10', 66.2, 122.6, 0)              # sense divider
    place('R11', 69.4, 122.6, 0)
    place('U10', 58.5, 110.0, 0)              # CIClone (DNP) at the CIC fingers (34/35, 70/71: x 58.75..61.25)
    place('C31', 63.6, 110.0, 90)
    place('TP7', 64.5, 106.0, 0)

    # ---------------- north-west: ESP32-S3 ----------------
    place('U11', 66.0, 43.0, 0)               # antenna end at the top edge (y 30.15)
    place('C32', 53.5, 38.5, 90)              # 22 uF bulk by the 3V3 pad (west edge)
    place('C33', 53.5, 42.0, 90)
    place('R14', 53.5, 45.2, 90)
    place('C34', 53.5, 48.4, 90)
    place('SW3', 56.5, 62.0, 0)               # S3 EN
    place('SW4', 56.5, 72.0, 0)               # S3 BOOT

    # ---------------- north-middle: microSD ----------------
    place('J2', 100.0, 40.0, 180)             # slot at the top edge, east of the ESP32 antenna keep-out (x <= 90)
    place('RN3', 89.0, 49.5, 90)
    place('R15', 111.2, 48.5, 90)
    place('C35', 111.2, 45.0, 90)

    # ---------------- north-east: USB-C, CP2102N, buck ----------------
    place('J3', 125.0, 35.0, 180)
    place('R17', 118.0, 37.5, 90)             # CC1 Rd
    place('R18', 132.0, 37.5, 90)             # CC2 Rd
    place('D4', 121.5, 43.5, 0)               # ESD D+
    place('D5', 128.5, 43.5, 0)               # ESD D-
    place('D6', 115.5, 40.5, 90)              # ESD VBUS
    place('C37', 134.5, 42.5, 90)             # VBUS 1 uF
    place('C38', 136.5, 42.5, 90)             # VBUS 100 nF
    place('U12', 125.0, 50.0, 270)            # CP2102N: D+/D- face J3
    place('C39', 120.0, 48.0, 90)
    place('C40', 120.0, 51.0, 90)
    place('R19', 119.5, 54.5, 0)              # VBUS sense divider
    place('R20', 119.5, 56.0, 0)
    place('R21', 131.5, 46.5, 90)             # /RST pull-up
    place('U13', 131.0, 50.5, 0)              # UMH3N
    place('U14', 139.5, 56.0, 180)            # buck: VIN/EN/FB east toward the input caps on the +5V strip
    place('C42', 144.0, 53.0, 90)             # buck in 22 uF x2 (+5V strip x 141..146)
    place('C43', 144.0, 56.5, 90)
    place('C45', 144.0, 60.2, 90)             # buck in 100 nF
    place('C46', 138.0, 51.5, 0)              # bootstrap
    place('L2', 134.0, 56.0, 0)               # inductor: SW east, +3V3 west
    place('C47', 129.5, 54.0, 90)             # buck out 22 uF x2 (+3V3 plane)
    place('C48', 129.5, 58.0, 90)
    place('D7', 140.0, 66.0, 0)               # SS34 VBUS -> +5V (island)
    place('C44', 144.6, 67.0, 90)             # +5V bulk
    place('D3', 121.0, 66.0, 0)               # WS2812 status LED (light pipe)
    place('R16', 117.5, 66.0, 0)
    place('C36', 124.5, 66.0, 0)

    # ---------------- east edge: buttons ----------------
    place('SW1', 143.5, 72.0, 0)              # RESET
    place('D1', 137.0, 72.0, 0)               # BAT54C
    place('SW2', 144.5, 112.0, 0)             # BOOTSEL
