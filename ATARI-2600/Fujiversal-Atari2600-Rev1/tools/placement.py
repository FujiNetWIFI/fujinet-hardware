"""Component placement for gen_pcb.py: key -> (x, y, rot).  Board x 72.8..127.2,
y 30..118 (y = 30 top edge, y = 118 insertion edge); parts only above the
shoulders and inside the shell (courtyards at y < 90.5).  Top view (F.Cu =
the face toward the console REAR), y down, rotation CCW.  Parts are named by
their design.py key, so a reference change never moves a part.

Regions:
  top-left      ESP32-S3 module, antenna flush with the top edge over a band
                that is copper-free on every layer; its bulk / EN parts in a
                row under it
  top-middle    WS2812 status LED + the RP LED (light pipes), CP2102N block,
                BOOTSEL button
  top-right     USB-C on the top edge, its CC / ESD parts
  right edge    microSD, slot facing east, contacts west toward the S3's SPI
  bottom-right  power: console-5V P-FET + sense by the +5V finger, VBUS
                Schottky, 3.3 V buck
  left column   S3 EN / S3 BOOT / RESET buttons (shell holes) + RESET steering
  centre-bottom RP2354A at rot 90: A0-A9 on its south side in the order of
                the B.Cu address fingers below; A10-A12, D0, the clock, SWD
                and RUN on its east side; D1-D7 at its north-east corner.
                The data lines run north-about and down the corridor west of
                the RP (x 82..90.5) to the data fingers, so the two buses never
                cross.  Raspberry Pi's regulator corner (gen_pcb graft) sits
                west of the RP, turned with it.
                Decoupling: +3V3_RP caps in a row north of the RP and in a
                column at its south-west; the DVDD caps beside them on a DVDD
                lobe of In2 (gen_pcb.DVDD_LOBE).
  band y 84..92 east of x 99, between the RP and the tab: free for the bus fan-out.
"""

RP = (103.5, 80.0, 90)          # RP2354A centre + rotation (gen_pcb turns the graft with it)

# In2 islands (absolute polygons).  +3V3_RP: the RP, its caps, the graft corner and the LDO.
RP_ISLAND = [(90.6, 69.6), (114.0, 69.6), (114.0, 86.0), (101.6, 86.0), (101.6, 90.4), (90.6, 90.4)]
# DVDD lobe, joined to gen_pcb's core island at the RP's south-west corner: under the
# DVDD cap column (pads east at x 98.8) -- clear of pin 1's fan-out via (x 100.7)
DVDD_LOBE = [(97.9, 81.9), (101.6, 81.9), (101.6, 83.1), (100.2, 83.1), (100.2, 89.2), (97.9, 89.2)]


def do_placement(place):
    # ---------------- edge ----------------
    place('J_EDGE', 100.0, 118.0, 0)

    # ---------------- RP2354A ----------------
    rx, ry, rr = RP
    place('U_RP', rx, ry, rr)
    # graft parts (L_VREG C_VOUT C_VIN C_FILT R_FILT R_USBP R_USBM C_OTP) are placed by
    # gen_pcb.graft_parts() from tools/rpi_core_graft.sexpr, relative to U_RP
    # north row (pins at y 76.55): IOVDD 45 (x 100.7), ADC 44 (101.1), IOVDD 38 (103.5);
    # GPIO25 (103.9) and the data pins (105.1-106.3) escape north beside it
    for i, k in enumerate(('C_IOVDD45', 'C_ADC', 'C_IOVDD38', 'C_IOVDD30')):
        place(k, 96.9 + 1.8 * i, 72.6, 90)
    place('C_RPBULK', 91.6, 77.6, 90)
    # south-west: DVDD caps (pad 1 = DVDD east, on the DVDD lobe) and +3V3_RP caps
    for i, k in enumerate(('C_DVDD6', 'C_DVDD39', 'C_DVDD23')):
        place(k, 98.0, 84.6 + 1.8 * i, 180)
    for i, k in enumerate(('C_IOVDD1', 'C_IOVDD11', 'C_IOVDD20')):
        place(k, 94.6, 84.6 + 1.8 * i, 180)
    # QSPI_SS (west side, pin 60): the pull-up on the island; the S3 / button series
    # resistors by the BOOTSEL button
    place('R_SSPU', 91.6, 81.8, 90)
    # debug UART pads (GPIO0/1, the south side's west end)
    place('TP_TX', 91.7, 86.4, 0)
    place('TP_RX', 91.7, 89.0, 0)
    # east side (pins at x 106.95): crystal on the XIN/XOUT lanes (y 80.8 / 80.4)
    place('R_XOUT', 109.6, 80.2, 0)          # on the XOUT lane
    place('Y_XTAL', 113.4, 80.8, 0)          # pad 1 XIN south-west, pad 3 XOUT_Y north-east
    place('C_XIN', 113.4, 83.6, 180)         # below pad 1
    place('C_XOUT', 114.6, 77.4, 90)         # beside pad 3
    # RUN (y 78.8) pull-up; SWD pads (SWCLK 79.6, SWDIO 79.2) north-east of the crystal
    place('R_RUNPU', 109.2, 76.0, 0)
    place('TP_SWDIO', 110.2, 73.4, 0)
    place('TP_SWCLK', 112.8, 73.4, 0)
    place('TP_GND', 115.4, 73.4, 0)
    # RP LDO on the island, north-west of the RP
    place('U_LDO', 92.4, 72.0, 0)
    place('C_LDOIN', 92.4, 75.0, 180)
    place('C_LDOOUT', 95.4, 70.0, 90)

    # ---------------- top-left: ESP32-S3 ----------------
    place('U_S3', 83.3, 42.85, 0)            # antenna (local y < -6.75) flush with the top edge
    place('C_S3BULK', 81.2, 58.2, 0)
    place('C_S3', 84.4, 58.2, 0)
    place('R_EN', 87.6, 58.2, 0)
    place('C_EN', 90.8, 58.2, 0)
    # left column buttons (shell holes): S3 EN, S3 BOOT, RESET (+ its steering diode)
    place('SW_S3EN', 77.6, 66.8, 0)
    place('SW_S3BOOT', 77.6, 73.2, 0)
    place('SW_RESET', 77.6, 79.6, 0)
    place('D_RST', 82.0, 84.6, 0)
    place('R_RUNCTL', 78.4, 84.6, 0)         # S3 IO4 -> RUN, on RUN's way to the RESET diode

    # ---------------- top-middle: LEDs, CP2102N, BOOTSEL ----------------
    place('D_WS', 99.4, 40.6, 0)
    place('R_WS', 99.4, 43.4, 0)
    place('C_WS', 102.4, 40.6, 90)
    place('R_LED', 99.4, 46.0, 0)
    place('D_LED', 99.4, 48.4, 180)          # RP activity LED beside the WS2812 (second light pipe)
    place('U_UART', 107.4, 44.8, 270)        # D+/D- (pins 4/5) face the USB-C
    place('C_CP', 103.0, 43.6, 90)
    place('C_CPBULK', 103.0, 47.4, 90)
    place('R_CPRST', 105.4, 49.8, 0)
    place('R_VBH', 108.8, 49.8, 90)
    place('R_VBL', 108.8, 53.2, 90)
    place('Q_AUTO', 105.4, 52.6, 0)
    place('SW_BOOTSEL', 99.6, 54.4, 0)
    place('R_SSBTN', 105.6, 55.6, 0)
    place('R_SSCTL', 105.6, 57.4, 0)

    # ---------------- top-right: USB-C ----------------
    place('J_USB', 121.0, 34.2, 180)         # opening on the top edge
    place('R_CC1', 114.2, 36.2, 90)
    place('R_CC2', 126.0, 41.8, 90)
    place('D_ESDP', 117.4, 41.2, 0)
    place('D_ESDM', 120.4, 41.2, 0)
    place('D_ESDV', 123.4, 41.2, 0)
    place('C_VBUS', 114.2, 40.4, 90)
    place('C_VBUSHF', 112.4, 40.4, 90)

    # ---------------- right edge: microSD ----------------
    place('J_SD', 117.4, 52.6, 90)           # slot east, contacts west (x 112.3)
    place('RN_SD', 109.0, 57.6, 0)
    place('R_CD', 109.2, 60.6, 0)
    place('C_SD', 113.0, 63.0, 0)

    # ---------------- bottom-right: power ----------------
    place('Q_CONS', 114.8, 88.6, 0)          # console 5V switch by the +5V finger (x 111.43)
    place('C_CONS', 118.4, 89.0, 0)
    place('C_CONSHF', 118.4, 87.4, 0)
    place('R_VBPD', 114.8, 85.8, 0)
    place('R_VSH', 121.8, 87.4, 90)
    place('R_VSL', 123.6, 84.2, 90)
    place('C_VS', 121.8, 83.6, 90)
    place('D_VBUS', 118.6, 66.6, 90)         # VBUS (top) -> +5V, down the right side
    place('U_BUCK', 120.0, 76.6, 0)
    place('C_BST', 123.4, 76.6, 90)
    place('L_BUCK', 124.0, 71.6, 0)
    place('C_BIN1', 119.0, 72.8, 0)
    place('C_BIN2', 119.0, 80.0, 0)
    place('C_BINHF', 116.4, 76.6, 90)
    place('C_BOUT1', 125.6, 76.6, 90)
    place('C_BOUT2', 124.8, 80.4, 0)
