"""Component placement for gen_pcb.py: ref -> (x, y, rot).  Board x 72.8..127.2,
y 30..118 (y = 30 top edge, y = 118 insertion edge; parts only above y = 91.3,
the rest of the board goes into the slot).

Regions (top view = F.Cu = the face toward the console REAR):
  top-left     ESP32-S3 module, antenna overhanging the top edge
  top-middle   microSD (slot at the top edge), SD pull-ups, WS2812 status
  top-right    USB-C (top edge), ESD, CP2102N + auto-program
  right        power: OR diodes, AP63203 buck; RESET / BOOTSEL buttons
  left         S3 EN / BOOT buttons
  centre       RP2040 (rotated 90: A0-A9 on its south face, A10-A12 + D0-D2 +
               crystal on the east, D3-D7 on the north, USB/QSPI on the west)
  lower band   the three 74LVC245A: U5 data (west, over the data fingers),
               U3 A0-A7 (under the RP's south face, over the B.Cu A0-A7
               fingers), U4 A8-A12 (east, over the F.Cu A8-A12 fingers)
"""


def do_placement(place):
    # ---------------- edge ----------------
    place('J1', 100.0, 118.0, 0)

    # ---------------- RP2040 ----------------
    rx, ry = 106.0, 69.0
    place('U1', rx, ry, 90)
    # flash south-west: its top row (VCC, IO3, CLK, IO0) faces the RP's QSPI pins
    place('U2', 96.6, 78.6, 90)
    place('C1', 92.6, 75.2, 90)              # flash VCC
    # IOVDD decoupling (pins 1, 10, 22, 33, 42, 49)
    place('C2', 101.6, 74.4, 90)             # pin 1  (south-west corner)
    place('C3', 110.9, 75.6, 90)              # pin 10 (south, between A5/A6: plane via)
    place('C4', 111.6, 63.4, 90)             # pin 22 (east; kept out of the SWD/RUN escapes)
    place('C5', 104.2, 62.4, 0)              # pin 33 (north)
    place('C6', 100.8, 64.4, 90)             # pin 42 (north-west corner)
    place('C7', 97.2, 70.8, 90)              # pin 49 (west)
    place('C8', 99.0, 64.4, 90)              # USB_VDD
    place('C9', 95.4, 64.4, 90)              # ADC_AVDD
    place('C10', 97.2, 64.4, 90)             # VREG_VIN
    place('C11', 95.4, 70.8, 90)             # VREG_VOUT
    place('C12', 91.8, 70.8, 90)             # DVDD (with C11/C13; pin 23 is fed by the inner ring)
    place('C13', 93.6, 70.8, 90)             # DVDD (pin 50)
    place('C14', 93.6, 64.4, 90)             # 3V3 bulk
    # crystal east of the RP (XIN/XOUT mid east face)
    place('Y1', 115.4, 70.2, 90)
    place('C15', 119.2, 68.6, 90)             # XIN load
    place('C16', 119.2, 71.8, 90)             # XOUT_Y load
    place('R1', 112.6, 71.6, 90)             # XOUT series
    # RUN / BOOTSEL / S3 forcing
    place('R2', 115.0, 63.6, 0)              # RUN pull-up
    place('R5', 115.0, 65.4, 0)              # S3 IO4 -> RUN
    place('D1', 82.8, 67.0, 0)             # BAT54C (by RESET)
    place('R3', 90.2, 81.6, 90)              # QSPI_SS pull-up
    place('R4', 90.2, 85.0, 90)              # QSPI_SS -> BOOTSEL button
    place('R6', 92.0, 81.6, 90)              # S3 IO5 -> QSPI_SS
    place('SW1', 77.4, 80.2, 90)             # RESET (left column, next to BOOTSEL)
    place('SW2', 96.0, 87.6, 0)              # BOOTSEL
    # USB series: at the west end of the via-free USB lane (gen_pcb.VIA_KEEP)
    place('R7', 89.8, 64.4, 270)
    place('R8', 91.6, 64.4, 270)
    # LED + test pads
    place('R9', 101.2, 57.8, 0)
    place('D2', 104.2, 57.8, 180)
    place('TP1', 125.4, 68.0, 0)             # SWCLK
    place('TP2', 125.4, 71.0, 0)             # SWDIO
    place('TP3', 125.4, 74.0, 0)             # GND
    place('TP4', 122.4, 71.0, 0)             # RP_TX
    place('TP5', 122.4, 74.0, 0)             # RP_RX

    # ---------------- bus buffers ----------------
    place('U3', 106.0, 81.6, 90)             # A0-A7
    place('U4', 116.4, 79.6, 90)             # A8-A12
    place('U5', 84.6, 81.6, 90)              # D0-D7
    place('R10', 88.4, 76.4, 0)              # DIR pull-up
    place('C17', 101.2, 79.0, 90)             # U3 VCC
    place('C18', 111.4, 79.8, 90)             # U4 VCC
    place('C19', 84.6, 76.4, 0)              # U5 VCC
    place('C20', 110.6, 88.8, 0)             # edge 5V bulk

    # ---------------- top-left: ESP32-S3 ----------------
    place('U6', 83.6, 36.35, 0)
    place('C21', 77.4, 52.0, 0)              # S3 bulk
    place('C22', 81.2, 52.4, 0)
    place('R11', 84.4, 52.4, 0)              # EN pull-up
    place('C23', 87.6, 52.4, 0)              # EN delay
    place('SW3', 77.4, 62.6, 90)             # S3 EN
    place('SW4', 77.4, 71.4, 90)             # S3 BOOT

    # ---------------- top-middle: microSD + status LED ----------------
    place('J2', 102.2, 39.55, 180)
    place('RN1', 96.4, 50.2, 90)
    place('R12', 99.4, 50.2, 90)             # card-detect pull-up
    place('C24', 102.0, 50.2, 90)
    place('D3', 107.6, 50.6, 0)              # WS2812 status
    place('C25', 110.4, 50.6, 90)
    place('R13', 105.0, 50.6, 90)

    # ---------------- top-right: USB-C, ESD, CP2102N ----------------
    place('J3', 120.0, 35.0, 180)
    place('R14', 113.6, 37.0, 90)            # CC1
    place('R15', 126.0, 42.4, 90)            # CC2
    place('D4', 116.6, 42.6, 0)
    place('D5', 123.4, 42.6, 0)
    place('D6', 113.6, 41.8, 90)
    place('U7', 119.4, 48.4, 270)              # CP2102N: D+/D- (pins 4/5) face the USB-C
    place('C26', 114.6, 47.2, 90)
    place('C27', 114.6, 50.4, 90)
    place('R16', 117.8, 53.2, 0)             # VBUS sense
    place('R17', 121.2, 53.2, 0)
    place('R18', 112.8, 49.8, 90)            # /RST pull-up
    place('U8', 112.6, 46.2, 90)             # UMH3N auto-program

    # ---------------- right: power ----------------
    place('D8', 121.8, 56.0, 0)              # VBUS OR (near USB)
    place('D7', 123.8, 81.4, 90)             # console 5V OR (near edge pin 23)
    place('C28', 120.8, 84.6, 90)            # edge 5V HF
    place('U9', 121.2, 61.4, 0)              # AP63203
    place('C29', 125.2, 60.6, 90)            # buck in
    place('C30', 125.2, 64.6, 90)
    place('C31', 122.8, 64.8, 90)
    place('C32', 117.9, 61.4, 90)            # bootstrap
    place('L1', 114.8, 59.6, 90)
    place('C33', 110.8, 59.0, 90)            # buck out
    place('C34', 110.8, 55.4, 90)
