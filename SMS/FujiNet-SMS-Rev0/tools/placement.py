"""Component placement for gen_pcb.py: design.py key -> (x, y, rot), and the board frame the
floorplan owns (body height, shell-screw holes, the In4 +5V island).  KiCad frame: top view of
the component side (F.Cu, which faces the label), y down, rotation CCW.  The body is x 50..150,
y 110 - BODY_H (top edge) .. 110 (tab base); the fingers are on the tab below, insertion edge
y = 125.

Fingers (tools/edge_geom.py): pins 1/2 east (x 130.5) .. 49/50 west (69.5), even pins on F.Cu.
West to east the console bus is the JEDEC 32-pin memory pinout unrolled:
  x  72-85   CLK /RESET (/BUSREQ) /WAIT /M1 /IORQ          -> the RP2354B
  x  87-90   A15, A12 (+5V on 35)
  x  92-100  A7 A6 A5 A4 A3 A2 A1 A0
  x 102-115  D0 D1 D2 GND GND D3 D4 D5 D6 D7 /CE
  x 118-126  A10 A11 A9 A8 A13 A14
  x 128-131  /RD /MREQ /WR (+5V on 1)

The co-design (docs/floorplan-study.md): SRAM0 stands upright in the classic ROM spot, its
pin 17-32 end toward the fingers, and takes A0-A12 / D0-D7 / GND without one crossing
(gen_pcb.sram0_fanin); everything else -- the RP2354B, SRAM1, the glue -- taps the bus on
the inner layers.  PLACE_VARIANT selects a candidate floorplan (the study compares them);
the default is the one the board is built from.

The RP2354B and its ring (decoupling at every supply pin, the core-regulator corner, the
crystal, USB series resistors, QSPI / BOOTSEL, the RP LDO, the SWD pads) are one rigid macro,
drawn at rotation 90 (the NES / first SMS layout, proven routable) and turned as a whole for
any other RP rotation: gen_pcb.dvdd_island() turns with it.
"""
import math, os

VARIANT = os.environ.get('PLACE_VARIANT', 'P3')


def rot_pt(x, y, a):
    """gen_pcb.rot_pt: KiCad's rotation (CCW on screen, y down)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


# ---------------------------------------------------------------------------
# the RP2354B macro, relative to the RP centre, for the RP at rotation 90
RING = 10.0              # decoupling ring radius (NES Rev0: 10, not 9 -- a second via column fits)
RP_MACRO = [
    # south (rot 90: A4-A15 / D0-D3): IOVDD 5 (x -2.2), DVDD 10 (-0.2), IOVDD 15 (+1.8)
    ('C_IOV5', -2.2, RING, 270), ('C_IOV15', 1.8, RING, 270),
    # east: the IOVDD 24/29 caps at the south-east corner, NOT in front of their pins
    # (in line they wall in the strobes, pins 25-28)
    ('C_IOV24', 8.3, 6.4, 0), ('C_IOV29', 8.3, 8.1, 0),
    # crystal block, planar: XIN (pin 30) straight into Y1's south-west pad, XOUT (pin 31) into
    # the 1k on its own lane, XOUT_Y over the crystal's GND pad to the north-east pad
    ('Y_RP', RING + 4.0, 0.0, 0), ('C_XIN', RING + 4.0, 3.6, 270), ('C_XOUT', RING + 7.0, -2.6, 90),
    ('R_XOUT', 9.0, -0.7, 0),
    # north: IOVDD 41 (x +3.8), 50 (+0.2), 60 (-3.8), ADC_AVDD 59 (-3.4)
    ('C_IOV41', 3.8, -RING, 90), ('C_IOV50', 0.2, -RING, 90), ('C_IOV60', -4.4, -RING, 90),
    ('C_ADC', -2.4, -RING, 90),
    # west: VREG corner (61-65), USB 66/67, QSPI, IOVDD 76, A0-A3; the DVDD lobe of the In4
    # island spans x -16..-3.6, y -5.6..-1.6
    ('L_RP', -7.6, -3.0, 0), ('C_DVBULK', -11.0, -2.6, 180), ('C_DV51', -14.2, -2.6, 180),
    ('C_DV10', -8.6, -4.8, 180), ('C_DV32', -11.8, -4.8, 180), ('C_VREGIN', -RING - 4.4, -0.6, 180),
    ('R_AVDD', -10.5, -11.0, 0), ('C_AVDD', -7.2, -11.0, 0),
    # D- (pin 66) is the northern pin: its 27R sits north
    ('R_USBM', -RING - 0.6, -0.6, 0), ('R_USBP', -RING - 0.6, 1.1, 0), ('C_OTP', -RING - 0.6, 2.8, 180),
    ('C_QSPI', -RING - 0.6, 4.5, 180), ('R_SS', -RING - 0.6, 6.2, 180), ('C_IOV76', -RING - 0.6, 7.9, 180),
    ('R_BSELCTL', -RING - 4.4, 1.1, 180), ('R_BSEL', -RING - 4.4, 2.8, 180),
    ('C_IOBULK', -RING - 4.4, 4.5, 180),
    # RP LDO just south-west of the ring: input on +5V, output on the +3V3_RP island
    ('U_LDO', -13.5, 13.5, 0), ('C_LDOIN', -16.0, 10.5, 180), ('C_LDOOUT', -9.2, 11.0, 180),
    # RUN pull-up and the S3's RUN line north-east, clear of the strobes' escape (/IORQ /RESET
    # /M1 CLK, pins 36-39): with the two resistors in front of them /IORQ stayed open (first
    # SMS layout, 2026-10-07).  SWD pads south-east: the pads are south of their pins, so the
    # southern pin (SWCLK, 33) takes the western pad and SWDIO (34) / RUN (35) the ones east
    ('R_RUN', 14.5, -9.5, 0), ('R_RUNCTL', 14.5, -11.2, 0),
    ('TP_SWCLK', 9.0, 10.5, 0), ('TP_SWDIO', 11.6, 10.5, 0), ('TP_GND', 14.2, 10.5, 0), ('TP_RUN', 16.8, 10.5, 0),
]


def rp_macro(place, rx, ry, rot=90):
    rr = rot - 90
    place('U_RP', rx, ry, rot)
    for key, dx, dy, r in RP_MACRO:
        ox, oy = rot_pt(dx, dy, rr)
        place(key, rx + ox, ry + oy, (r + rr) % 360)


# ---------------------------------------------------------------------------
# the SRAM in the ROM spot (gen_pcb.sram0_fanin draws its fan-in): AS6C4008 TSOP-I at
# rotation 270, pin 17-32 end south over finger positions 6..14
ROM_X = 107.62           # its centre x: the middle of A3 (position 14, x 97.46) .. A10 (6, 117.78)
ROM_Y = 90.5             # its centre y: the pin 17-32 row ends at y 100.98, 7.7 mm of fan-in to the stubs


# ---------------------------------------------------------------------------
def p1(place, fid):
    """P1: SRAM0 in the ROM spot, SRAM1 stacked north of it (same orientation), the RP2354B west
    over the control fingers (/M1 /IORQ /WAIT /RESET CLK) at rotation 90 (A4-A15 / D0-D4 south,
    strobes east, bank lines and glue lines north, USB / QSPI west toward the S3), the glue
    east over /RD /WR /MREQ /CE / A13 / A14, the FujiNet half along the top edge."""
    rx, ry = 76.0, 79.0
    rp_macro(place, rx, ry, 90)
    # ---- edge, console side ----
    place('J_EDGE', 100.0, 125.0, 0)
    place('TP_CONT', 89.84, 106.6, 0)          # finger 34
    place('TP_BUSREQ', 77.14, 106.6, 0)        # finger 44
    place('Q_WAIT', 80.6, 103.0, 0)            # finger 41 (x 79.68, B.Cu): the 2N7002 drain
    place('R_WAIT', 84.2, 103.0, 90)
    # D0-D7 100R packs between the RP's data corner (D0-D4 south-east, D5-D7 east) and the bus
    place('RN_D0', 83.0, 95.5, 0)
    place('RN_D4', 87.0, 95.5, 0)
    # ---- the SRAMs ----
    place('U_SRAM0', ROM_X, ROM_Y, 270)
    place('C_SRAM0', 115.0, 81.0, 90)          # beside the north end (VCC pin 8 via the +5V island)
    place('U_SRAM1', ROM_X, 63.6, 270)
    place('C_SRAM1', 115.0, 54.0, 90)
    place('C_SRAMBULK', 115.0, 58.0, 90)
    # ---- glue: two rows over the east fingers ----
    glue = [('U_INV', 122.0, 96.0), ('U_NORDEC', 131.0, 96.0), ('U_NAND2', 140.0, 93.0),
            ('U_NAND3', 122.0, 83.0), ('U_NORWE', 131.0, 83.0)]
    gcap = {'U_INV': 'C_INV', 'U_NORWE': 'C_NORWE', 'U_NORDEC': 'C_NORDEC', 'U_NAND3': 'C_NAND3',
            'U_NAND2': 'C_NAND2'}
    for k, x, y in glue:
        place(k, x, y, 0)
        place(gcap[k], x, y - 5.9, 0)
    place('R_VSH', 118.0, 102.5, 0)            # console 5V sense divider into the '14
    place('R_VSL', 121.5, 102.5, 0)
    # ---- console 5V switch by finger 1 (x 130.5) ----
    place('Q_CONS', 136.0, 104.0, 0)
    place('C_CONS', 140.0, 101.5, 0)
    place('C_CONSHF', 140.0, 104.0, 0)
    # ---- the FujiNet half along the top edge ----
    fuji_top(place, fid)


def fuji_top(place, fid):
    """The ESP32-S3 top-left (antenna flush with the top edge), the microSD beside it, the four
    buttons in a block at the top centre, USB-C / CP2102N / buck top-right, the two LEDs."""
    place('U_S3', 66.0, 45.0, 0)               # antenna end at the top edge (y 32.15)
    place('C_S3BULK', 53.5, 41.0, 90)          # west edge column, below the antenna band (y 38.25)
    place('C_S3', 53.5, 44.5, 90)
    place('R_EN', 53.5, 48.0, 90)
    place('C_EN', 53.5, 51.5, 90)
    place('J_SD', 88.0, 42.0, 180)             # slot at the top edge, east of the antenna keep-out
    place('RN_SD', 80.5, 52.5, 90)
    place('R_SDCD', 95.0, 51.0, 90)
    place('C_SD', 92.0, 51.0, 90)
    # buttons: RESET / BOOTSEL over the S3 EN / BOOT, all four behind pinholes / a plunger
    place('SW_RESET', 102.0, 36.6, 0)
    place('SW_BOOTSEL', 110.6, 36.6, 0)
    place('SW_S3EN', 102.0, 44.4, 0)
    place('SW_S3BOOT', 110.6, 44.4, 0)
    place('D_RST', 99.0, 49.5, 0)              # RESET steering by its button
    # status LEDs west of SRAM1, on the +5V island (WS2812)
    place('D_WS', 96.0, 70.0, 0)
    place('R_WS', 96.0, 67.0, 0)
    place('C_WS', 96.0, 73.0, 0)
    place('D_LED', 96.0, 61.0, 0)
    place('R_LED', 96.0, 63.6, 0)
    place('J_DBG', 92.0, 58.0, 90)             # debug header (DNP)
    # USB-C, CP2102N, the 3.3 V buck, the VBUS Schottky
    place('J_USB', 124.0, 37.0, 180)
    place('R_CC1', 116.5, 38.0, 90)
    place('R_CC2', 131.5, 38.0, 90)
    place('D_ESDV', 116.5, 42.5, 90)
    place('D_ESDP', 121.0, 45.0, 0)
    place('D_ESDM', 127.0, 45.0, 0)
    place('C_VBUS', 133.5, 42.5, 90)
    place('C_VBUSHF', 135.5, 42.5, 90)
    place('R_VBPD', 138.0, 39.0, 90)           # VBUS / P-FET gate pull-down
    place('D_VBUS', 143.5, 39.0, 90)           # SS34 VBUS -> +5V
    place('U_UART', 124.0, 52.0, 270)
    place('C_UART', 118.5, 50.0, 90)
    place('C_UARTBULK', 118.5, 53.5, 90)
    place('R_VBSH', 118.5, 56.5, 0)
    place('R_VBSL', 122.0, 56.5, 0)
    place('R_CPRST', 129.5, 48.5, 90)
    place('U_AUTOPROG', 130.5, 53.0, 0)
    place('U_BUCK', 142.0, 52.0, 180)
    place('C_BIN1', 147.0, 48.0, 90)
    place('C_BIN2', 147.0, 51.5, 90)
    place('C_BINHF', 147.0, 55.0, 90)
    place('C_5VBULK', 143.5, 45.0, 0)
    place('C_BST', 142.0, 48.5, 0)
    place('L_BUCK', 137.0, 55.5, 0)
    place('C_BOUT1', 133.0, 58.5, 90)
    place('C_BOUT2', 130.5, 58.5, 90)
    fid += [('FID1', 148.0, 70.0), ('FID2', 52.5, 99.5), ('FID3', 147.0, 85.0)]


def p2(place, fid):
    """P2: as P1, but the glue between the RP2354B and the SRAMs (north of the RP, west of SRAM1):
    its mode bits come straight off the RP's north side, its /OE /WE / chip select go straight
    east into both SRAMs, PWR_OK back to the RP's north-east corner; the strobes from the east
    fingers run west to the RP and the glue together.  Buttons, LEDs and the debug header take
    the east side."""
    rx, ry = 76.0, 81.5
    rp_macro(place, rx, ry, 90)
    place('J_EDGE', 100.0, 125.0, 0)
    place('TP_CONT', 89.84, 106.6, 0)
    place('TP_BUSREQ', 77.14, 106.6, 0)
    place('Q_WAIT', 80.6, 103.0, 0)
    place('R_WAIT', 84.2, 103.0, 90)
    place('RN_D0', 83.0, 95.5, 0)
    place('RN_D4', 87.0, 95.5, 0)
    place('U_SRAM0', ROM_X, ROM_Y, 270)
    place('C_SRAM0', 115.0, 81.0, 90)
    place('U_SRAM1', ROM_X, 63.6, 270)
    place('C_SRAM1', 115.0, 54.0, 90)
    place('C_SRAMBULK', 115.0, 58.0, 90)
    glue = [('U_NAND3', 88.5, 55.1), ('U_NORWE', 98.5, 55.1), ('U_NORDEC', 88.5, 64.5),
            ('U_NAND2', 98.5, 64.5), ('U_INV', 98.5, 73.9)]
    gcap = {'U_INV': 'C_INV', 'U_NORWE': 'C_NORWE', 'U_NORDEC': 'C_NORDEC', 'U_NAND3': 'C_NAND3',
            'U_NAND2': 'C_NAND2'}
    for k, x, y in glue:
        place(k, x, y, 0)
    place('C_NAND3', 93.5, 53.0, 90)          # one cap per package in the gap between the columns
    place('C_NORWE', 93.5, 57.0, 90)
    place('C_NORDEC', 93.5, 62.4, 90)
    place('C_NAND2', 93.5, 66.4, 90)
    place('C_INV', 93.5, 71.8, 90)
    place('R_VSH', 82.5, 52.5, 90)
    place('R_VSL', 82.5, 56.0, 90)
    place('Q_CONS', 136.0, 104.0, 0)
    place('C_CONS', 140.0, 101.5, 0)
    place('C_CONSHF', 140.0, 104.0, 0)
    fuji_top2(place, fid)


def fuji_top2(place, fid):
    """P2's FujiNet half: the ESP32-S3 top-left, microSD beside it, USB-C / CP2102N / buck
    top-right; buttons, LEDs and the debug header in the free east band."""
    place('U_S3', 66.0, 45.0, 0)
    place('C_S3BULK', 53.5, 41.0, 90)
    place('C_S3', 53.5, 44.5, 90)
    place('R_EN', 53.5, 48.0, 90)
    place('C_EN', 53.5, 51.5, 90)
    place('J_SD', 88.0, 42.0, 180)
    place('RN_SD', 99.5, 44.0, 0)
    place('R_SDCD', 99.5, 40.0, 90)
    place('C_SD', 102.5, 40.0, 90)
    place('SW_S3EN', 124.0, 66.0, 0)
    place('SW_S3BOOT', 124.0, 74.0, 0)
    place('SW_RESET', 133.5, 66.0, 0)
    place('SW_BOOTSEL', 133.5, 74.0, 0)
    place('D_RST', 129.0, 80.5, 0)
    place('D_WS', 124.0, 87.0, 0)
    place('R_WS', 124.0, 84.0, 0)
    place('C_WS', 127.5, 87.0, 90)
    place('D_LED', 133.0, 87.0, 0)
    place('R_LED', 133.0, 84.0, 0)
    place('J_DBG', 140.0, 82.0, 0)
    place('J_USB', 124.0, 37.0, 180)
    place('R_CC1', 116.5, 38.0, 90)
    place('R_CC2', 131.5, 38.0, 90)
    place('D_ESDV', 116.5, 42.5, 90)
    place('D_ESDP', 121.0, 45.0, 0)
    place('D_ESDM', 127.0, 45.0, 0)
    place('C_VBUS', 133.5, 42.5, 90)
    place('C_VBUSHF', 135.5, 42.5, 90)
    place('R_VBPD', 138.0, 39.0, 90)
    place('D_VBUS', 143.5, 39.0, 90)
    place('U_UART', 124.0, 52.0, 270)
    place('C_UART', 118.5, 50.0, 90)
    place('C_UARTBULK', 118.5, 53.5, 90)
    place('R_VBSH', 118.5, 56.5, 0)
    place('R_VBSL', 122.0, 56.5, 0)
    place('R_CPRST', 129.5, 48.5, 90)
    place('U_AUTOPROG', 130.5, 53.0, 0)
    place('U_BUCK', 142.0, 52.0, 180)
    place('C_BIN1', 147.0, 48.0, 90)
    place('C_BIN2', 147.0, 51.5, 90)
    place('C_BINHF', 147.0, 55.0, 90)
    place('C_5VBULK', 143.5, 45.0, 0)
    place('C_BST', 142.0, 48.5, 0)
    place('L_BUCK', 137.0, 55.5, 0)
    place('C_BOUT1', 133.0, 58.5, 90)
    place('C_BOUT2', 130.5, 58.5, 90)
    fid += [('FID1', 148.0, 70.0), ('FID2', 52.5, 99.5), ('FID3', 147.0, 92.0)]


def p0(place, fid):
    """P0: the first SMS layout (RP2354B centre-south over the fingers, the SRAMs side by side
    east, glue north of them), with today's parts: the baseline the others are scored against."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('placement_v1', os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'placement_v1.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.do_placement(place, fid)


def p3(place, fid):
    """P3 (the board): SRAM0 in the ROM spot; the RP2354B straight north of it at rotation 90, its
    A4-A15 / D0-D4 side facing SRAM0's north end, so the bus taps run straight up under SRAM0 on
    the inner layers; SRAM1 upright west of SRAM0; the glue east over /RD /WR /MREQ /CE / A13 /
    A14; the FujiNet half along the top edge; buttons, LEDs and the debug header down the west
    side, where the shell's face carries their pinholes and windows (the label east of them)."""
    rx, ry = 104.0, 63.5
    rp_macro(place, rx, ry, 90)
    place('TP_DVDD', 87.6, 57.6, 0)            # the core rail, by the VREG corner
    # ---- edge, console side ----
    place('J_EDGE', 100.0, 125.0, 0)
    place('TP_CONT', 89.84, 106.6, 0)          # finger 34
    place('TP_BUSREQ', 77.14, 106.6, 0)        # finger 44
    place('Q_WAIT', 80.6, 104.2, 0)            # finger 41 (x 79.68, B.Cu): the 2N7002 drain
    place('R_WAIT', 84.2, 104.2, 90)
    # D0-D7 100R packs by the RP's data corner (D0-D4 south-east, D5-D7 east), RP side west
    place('RN_D0', 124.5, 66.5, 180)
    place('RN_D4', 124.5, 70.9, 180)
    # ---- the SRAMs ----
    place('U_SRAM0', ROM_X, ROM_Y, 270)
    place('C_SRAM0', 116.2, 84.0, 90)          # east of the wrap columns, its VCC pin via the +5V island
    place('U_SRAM1', 82.8, 86.4, 270)
    place('C_SRAM1', 76.5, 76.5, 90)
    place('C_SRAMBULK', 76.5, 80.0, 90)
    # ---- glue: two rows over the east fingers ----
    glue = [('U_INV', 124.0, 97.0), ('U_NORDEC', 133.0, 97.0), ('U_NAND2', 142.0, 94.5),
            ('U_NAND3', 124.0, 84.0), ('U_NORWE', 133.0, 84.0)]
    gcap = {'U_INV': 'C_INV', 'U_NORWE': 'C_NORWE', 'U_NORDEC': 'C_NORDEC', 'U_NAND3': 'C_NAND3',
            'U_NAND2': 'C_NAND2'}
    for k, x, y in glue:
        place(k, x, y, 0)
        place(gcap[k], x, y - 5.9, 0)
    place('R_VSH', 121.6, 104.6, 90)           # console 5V sense divider into the '14
    place('R_VSL', 123.4, 104.6, 90)
    # RP2350-E9 pull-downs on the glue's mode inputs and the chip select, between the RP and the glue
    for i, k in enumerate(('R_PDSA19', 'R_PDMBOX', 'R_PDGAME', 'R_PDRAMWE', 'R_PDLOAD')):
        place(k, 127.0 + 3.4 * i, 75.8, 0)
    # scope pads for the bring-up timing items, with a ground, between SRAM0's east wrap and the glue
    for i, k in enumerate(('TP_CE', 'TP_OE', 'TP_WE', 'TP_PWROK', 'TP_GNDBUS')):
        place(k, 117.2, 88.0 + 3.0 * i, 0)
    # ---- console 5V switch by finger 1 (x 130.5) ----
    place('Q_CONS', 139.0, 104.3, 0)
    place('C_CONS', 143.0, 100.2, 0)
    place('C_CONSHF', 139.5, 100.2, 0)
    place('TP_CONS5V', 148.0, 98.0, 0)
    # ---- FujiNet half: S3 top-left, microSD beside it, USB-C / CP2102N / buck top-right ----
    place('U_S3', 66.0, 45.0, 0)
    place('C_S3BULK', 53.5, 41.0, 90)
    place('C_S3', 53.5, 44.5, 90)
    place('R_EN', 53.5, 48.0, 90)
    place('C_EN', 53.5, 51.5, 90)
    place('J_SD', 100.0, 42.0, 180)          # east of the S3 antenna keep-out (x <= 90)
    place('RN_SD', 111.0, 45.6, 90)
    place('R_SDCD', 113.8, 45.6, 90)
    place('C_SD', 116.6, 45.6, 90)
    # buttons, LEDs, the debug header: down the west side
    place('SW_S3EN', 58.0, 70.5, 0)
    place('SW_S3BOOT', 58.0, 78.5, 0)
    place('SW_RESET', 66.5, 70.5, 0)
    place('SW_BOOTSEL', 66.5, 78.5, 0)
    place('D_RST', 72.5, 66.5, 0)
    place('D_WS', 58.0, 88.0, 0)
    place('R_WS', 58.0, 85.0, 0)
    place('C_WS', 61.5, 88.0, 90)
    place('D_LED', 66.0, 88.0, 0)
    place('R_LED', 66.0, 85.0, 0)
    place('J_DBG', 70.0, 96.0, 90)
    place('J_USB', 128.0, 37.0, 180)
    place('R_CC1', 120.5, 38.0, 90)
    place('R_CC2', 135.5, 38.0, 90)
    place('D_ESDV', 120.5, 42.5, 90)
    place('D_ESDP', 125.0, 45.0, 0)
    place('D_ESDM', 131.0, 45.0, 0)
    place('C_VBUS', 137.0, 42.5, 90)
    place('C_VBUSHF', 139.0, 42.5, 90)
    place('R_VBPD', 141.0, 39.0, 90)
    place('D_VBUS', 145.5, 39.0, 90)
    place('U_UART', 130.0, 53.0, 270)
    place('C_UART', 124.5, 51.0, 90)
    place('C_UARTBULK', 124.5, 54.5, 90)
    place('R_VBSH', 124.5, 57.5, 0)
    place('R_VBSL', 128.0, 57.5, 0)
    place('R_CPRST', 135.5, 49.5, 90)
    place('U_AUTOPROG', 136.5, 54.0, 0)
    place('U_BUCK', 143.0, 56.0, 180)
    place('C_BIN1', 147.5, 49.0, 90)
    place('C_BIN2', 147.5, 52.5, 90)
    place('C_BINHF', 147.5, 56.0, 90)
    place('C_5VBULK', 144.5, 46.5, 0)
    place('TP_5V', 62.0, 96.5, 0)            # on the +5V island, by the debug header
    place('C_BST', 143.0, 52.5, 0)
    place('L_BUCK', 139.0, 60.0, 0)
    place('C_BOUT1', 134.5, 60.5, 90)
    place('C_BOUT2', 132.0, 60.5, 90)
    place('TP_3V3', 129.5, 61.0, 0)
    place('TP_3V3RP', 90.5, 80.8, 0)          # by the RP LDO's output
    fid += [('FID1', 148.0, 70.0), ('FID2', 52.5, 99.5), ('FID3', 147.0, 85.0)]


VARIANTS = {'P0': p0, 'P1': p1, 'P2': p2, 'P3': p3}

# board frame owned by the floorplan (gen_pcb reads these)
BODY_H = 78.0            # body height: top edge at y = 110 - BODY_H
HOLES = [(54.0, 32.0, 3.2), (146.0, 32.0, 3.2), (54.0, -5.5, 3.2), (146.0, -5.5, 3.2)]   # x, dy (>= 0 from the
#                          top edge, < 0 from the tab base), diameter
PLANE_SPLIT_Y = 60.0     # In4: +3V3 north of this, +5V south (FIVE_V_POLY, when set, replaces it)
FIVE_V_NOTCH_X = 139.5   # the +5V island also runs up the east edge east of this
# In4 +5V island (absolute; the +3V3_RP / DVDD islands win over it): the cart side, the column
# over SRAM1, the strip up the east edge under the buck input and the VBUS diode
FIVE_V_POLY = [(50.0, 66.0), (92.0, 66.0), (92.0, 50.0), (117.0, 50.0), (117.0, 60.0), (139.5, 60.0),
               (139.5, 34.0), (150.0, 34.0), (150.0, 110.0), (50.0, 110.0)]
LABEL = ((118.0, 90.0), (50.0, 30.0))     # shell label recess: centre (board x, y), size (w, h)
# F.Silkscreen texts, in spots clear of pads, courtyards and other silk on the routed P3 board
# (found by rasterising it, 2026-10-08): the title centred above the edge; JLCPCB's order number
# (export.py adds it to the JLC zip only; tools/audit/check_fab.py re-checks the spot)
TITLE_XY = (104.25, 103.75)
JLC_ORDER = ((134.0, 65.4), 1.0)           # centre, text height (mm)
RP_ROT = 90
SRAM0_FANIN = VARIANT in ('P1', 'P2', 'P3')     # gen_pcb.sram0_fanin: the ROM-spot SRAM's locked fan-in
if VARIANT == 'P0':
    FIVE_V_POLY = None
elif VARIANT == 'P3':
    # the cart side south of y 66, the RP (its own island) and SRAM0's north end; the S3 / microSD
    # band on +3V3; the strip up the east edge under the buck input
    FIVE_V_POLY = [(50.0, 62.0), (86.0, 62.0), (86.0, 78.0), (120.0, 78.0), (120.0, 66.0), (141.5, 66.0),
                   (141.5, 34.0), (150.0, 34.0), (150.0, 110.0), (50.0, 110.0)]
elif VARIANT == 'P2':
    # the glue (x 84-102, y 48-78) and SRAM1 on +5V; the S3 / microSD / USB bridge band on +3V3
    FIVE_V_POLY = [(50.0, 66.0), (80.0, 66.0), (80.0, 47.0), (117.0, 47.0), (117.0, 60.0), (139.5, 60.0),
                   (139.5, 34.0), (150.0, 34.0), (150.0, 110.0), (50.0, 110.0)]


def do_placement(place, fiducials):
    placed = set()

    def pl(key, *a):
        placed.add(key)
        place(key, *a)
    VARIANTS[VARIANT](pl, fiducials)
    if os.environ.get('PARK'):           # study only: park parts a variant does not place yet
        import design as D
        x, y = 119.0, 66.0
        for p in D.PARTS:
            if p.key not in placed:
                place(p.key, x, y, 0)
                x += 3.6
                if x > 141:
                    x, y = 119.0, y + 2.6
