# UNADAPTED copy of Astrocade/rev0/tools: encodes that board (outline, QFN-60 graft,
# single-sided blade edge). Rework before the FujiNet-NES-Rev0 layout stage; do not run as-is.
"""Component placement for gen_pcb.py: ref -> (x, y, rot).  Board x 52..148,
y 30..88 (y=30 trailing edge, y=88 insertion edge / contact lands on B.Cu).

Regions (top view):
  north-west  ESP32-S3 module, antenna overhanging the trailing edge
  north-mid   microSD (slot at the trailing edge), SD pull-ups, WS2812 status
  north-east  USB-C (trailing edge), ESD, CP2102N + auto-program, VBUS OR diode
  east        top-face RESET / BOOTSEL buttons, RUN/BOOTSEL force transistors, test pads
  west        S3 EN/BOOT buttons, buck regulator + console-5V OR diode
  centre      RP2354A with its decoupling ring, crystal, core SMPS
  south       contact lands (B.Cu) and their plated escapes at y=70.6
"""


def do_placement(place):
    # ---------------- edge ----------------
    place('J1', 100, 88, 180)

    # ---------------- RP2354A ----------------
    # QFN-60 at rot 0: west side GP0-GP11 (address), south side GP12,/CCS,
    # D0-D4 + crystal/SWD/RUN, east side D5-D7 + LED/VSENSE, north side the
    # regulator/USB/QSPI pins.  The bus leaves west and south, so decoupling
    # sits north, east and at the corners, leaving escape channels open.
    rx, ry = 100, 55
    place('U1', rx, ry, 0)
    # north side: the regulator corner (L1, C10, C15, C16, R1) and the USB
    # series resistors R11/R12 + C8 are placed by the Raspberry Pi graft
    # (tools/rpi_core_graft.sexpr, relative to U1) -- not here.  QSPI_SS parts:
    place('R7', rx - 10.6, ry - 2.1, 0)      # S3 IO5 -> QSPI_SS
    place('R5', rx - 13.6, ry - 2.1, 0)      # QSPI_SS -> BOOTSEL button
    place('R4', rx - 7.6, ry - 2.1, 0)       # QSPI_SS pull-up
    place('C7', rx - 6.0, ry - 5.5, 0)       # QSPI_IOVDD extra
    # east columns
    place('C6', rx + 6.8, ry - 2.7, 0)       # IOVDD 45
    place('C9', rx + 10.0, ry - 2.7, 0)      # ADC_AVDD 44
    place('C14', 109.4, 45.2, 0)           # DVDD 39
    place('C5', 113.2, 50.6, 0)           # IOVDD 38
    # corners
    place('C1', rx - 6.0, ry - 3.8, 0)       # IOVDD 1 (NW)
    place('C12', 106.4, 46.8, 0)           # DVDD 6  (NE, next to the regulator's DVDD pour)
    place('C2', rx - 12.1, ry - 3.8, 0)      # IOVDD 11
    place('C11', rx - 15.1, ry - 3.8, 0)     # 3V3 bulk
    place('C3', rx - 9.1, ry - 3.8, 0)    # IOVDD 20 (NW cap row)
    place('C4', 113.2, 52.3, 0)           # IOVDD 30 (E cap row)
    place('C13', 106.4, 45.2, 0)           # DVDD 23
    # crystal south
    place('Y1', 93.0, 62.6, 180)          # crystal SW of the RP; XIN pad top-right
    place('C17', 95.6, 66.2, 90)           # XIN load
    place('C18', 90.4, 66.2, 90)           # XOUT_Y load
    place('R2', 97.8, 62.0, 270)          # XOUT series: pad 1 (XOUT) north, pad 2 (XOUT_Y) south
    # RUN, VSENSE, LED, /CCS
    place('R3', rx + 12.4, ry + 5.6, 90)     # RUN pull-up
    place('R6', rx + 14.2, ry + 5.6, 90)     # S3 IO4 -> RUN
    place('R9', 76.2, 63.6, 90)              # VSENSE divider, next to the +5V source
    place('R10', 78.0, 63.6, 90)
    place('R13', rx + 13.0, ry + 0.4, 0)     # LED
    place('R8', 87.6, 62.4, 90)           # /CCS pull-up
    place('D2', rx + 13.0, ry + 2.2, 180)
    # test pads (F.Cu)
    place('TP1', 134.0, 60.0, 0)
    place('TP2', 136.8, 60.0, 0)
    place('TP3', 139.6, 60.0, 0)
    place('TP4', 134.0, 63.0, 0)
    place('TP5', 136.8, 63.0, 0)

    # ---------------- east: top-face buttons ----------------
    place('SW1', 141, 43, 0)                 # top-face RESET
    place('D1', 133.8, 45.0, 0)              # BAT54C
    place('SW2', 141, 52, 0)                 # BOOTSEL

    # ---------------- north-west: ESP32-S3 ----------------
    place('U2', 68, 36.35, 0)
    place('C19', 56.3, 40.0, 90)
    place('C20', 56.3, 43.6, 90)
    place('R14', 56.3, 46.8, 90)
    place('C21', 56.3, 50.2, 90)
    place('SW3', 57.0, 57.0, 90)
    place('SW4', 57.0, 66.0, 90)

    # ---------------- north-mid: microSD + status LED ----------------
    place('J2', 88, 39.55, 180)
    place('RN1', 84.0, 48.6, 90)
    place('R15', 95.0, 47.0, 0)
    place('C22', 89.0, 47.9, 270)
    place('D3', 101.0, 44.5, 0)
    place('C23', 103.6, 44.5, 90)
    place('R16', 98.4, 44.5, 90)

    # ---------------- north-east: USB-C, ESD, CP2102N ----------------
    place('J3', 124, 35, 180)
    place('R17', 117.4, 37.5, 90)
    place('R18', 130.6, 37.5, 90)
    place('D4', 120.6, 43.0, 0)
    place('D5', 127.6, 43.0, 0)
    place('D6', 117.4, 41.6, 90)
    place('D8', 113.0, 40.0, 90)
    place('U3', 124.2, 48.8, 270)           # D+/D- face J3, RTS/DTR face U4
    place('C24', 119.8, 46.4, 90)
    place('C25', 118.0, 46.4, 90)
    place('R19', 118.8, 49.8, 0)
    place('R20', 118.8, 51.5, 0)
    place('R21', 118.8, 53.2, 0)
    place('U4', 130.4, 48.8, 0)

    # ---------------- west: power ----------------
    place('D7', 71.5, 67.0, 0)
    place('C26', 66.0, 69.0, 0)
    place('U5', 70.0, 57.5, 0)
    place('C27', 65.8, 55.4, 90)
    place('C28', 65.8, 59.4, 90)
    place('C29', 65.8, 63.4, 90)
    place('C30', 68.6, 61.2, 0)
    place('C31', 70.0, 54.6, 0)
    place('L2', 75.0, 57.5, 90)
    place('C32', 78.6, 55.6, 90)
    place('C33', 78.6, 59.6, 90)
