"""Component placement for gen_pcb.py: design.py key -> (x, y, rot), and the board frame the
floorplan owns (the upper body, shell-screw holes, the In4 +5V island).  KiCad frame: top view of
the component side (F.Cu, the label face), y down, rotation CCW.  The insertion edge is y = 150,
the tab centre x = 100; the fingers run west to east (tools/edge_geom.py):

  F.Cu  x  78.4-96.2  D0 .. D7               (positions 1-8)
        x  98.7 101.3 /EN80 /EN40            (9, 10)
        x 103.8       raw DC (edge 11)       (11)       GND 12 13 at 106.4 108.9
        x 111.4       PHI2 (14)              x 114-119  A6 A5 A2       x 121.6 CI1 (18, short)
  B.Cu  x  78.4       CI2 (36, short)        x 81-101   A11 A12 A10 A13 A9 . A8 . A7
        x 103.8       console 5 V (26)       GND 25 / 23 at 106.4 / 111.4
        x 114-121.6   A4 A3 A1 A0

The board is T-shaped (gen_pcb.OUTLINE): the 47.8 mm tab, the original cart board's 61 mm lower
body up to 38 mm from the edge (the console's prongs enter the shell beside it), then a 45-degree
step out to the upper body that carries the FujiNet half.

The co-design (docs/floorplan-study.md): the 74HCT541 stands over the D0-D7 fingers at rotation
270, its Y row in the fingers' order (design.py reverses its channels) and its A row facing the
RP2354B's GPIO16-23 corner in theirs, so the data path from the slot to the RP crosses nothing
(gen_pcb.buf_fanin draws the finger side, locked); the RP2354B at rotation 90 north of it, its bus
side (A4-A13, the enables, RP_D0-D4) facing the fingers; the glue, the PHI2 buffer and the power
entry in the lower body over the fingers that feed them; the FujiNet half along the top edge.

The RP2354B and its ring (decoupling at every supply pin, the core-regulator corner, the crystal,
USB series resistors, QSPI / BOOTSEL, the RP LDO, the SWD pads) are one rigid macro, drawn at
rotation 90 (the NES / SMS layout, proven routable) and turned as a whole for any other RP
rotation: gen_pcb.dvdd_island() turns with it.
"""
import math, os

VARIANT = os.environ.get('PLACE_VARIANT', 'P1')

# ---- board frame ------------------------------------------------------------
XC, Y_EDGE = 100.0, 150.0
UPPER_W = 84.0           # the upper body's width (the custom shell's inside is ~105)
BOARD_H = 98.0           # insertion edge to the top edge
LOWER_TOP = 38.0         # the 61 mm lower body runs this far from the edge (the shell's prong pockets end ~37)


def rot_pt(x, y, a):
    """gen_pcb.rot_pt: KiCad's rotation (CCW on screen, y down)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


# ---------------------------------------------------------------------------
# the RP2354B macro, relative to the RP centre, for the RP at rotation 90 (FujiNet-SMS Rev0 v2)
RING = 10.0              # decoupling ring radius (NES Rev0: 10, not 9 -- a second via column fits)
RP_MACRO = [
    # south (rot 90: A4-A13, the enables, RP_D0-D4): IOVDD 5 (x -2.2), DVDD 10 (-0.2), IOVDD 15 (+1.8)
    ('C_IOV5', -2.2, RING, 270), ('C_IOV15', 1.8, RING, 270),
    # east: the IOVDD 24/29 caps at the south-east corner, NOT in front of their pins
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
    # RUN pull-up and the S3's RUN line north-east; SWD pads south-east: the pads are south of
    # their pins, so the southern pin (SWCLK, 33) takes the western pad and SWDIO (34) / RUN (35)
    # the ones east
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
# the '541 over the D0-D7 fingers (gen_pcb.buf_fanin draws its fan-in): rotation 270, Y row south
BUF_X = 87.3             # the middle of D3 (x 86.03) and D4 (88.57)
BUF_Y = 121.0


def p1(place, fid):
    """P1: the '541 over the D fingers, the RP2354B straight north of it (its GPIO16-23 corner over
    the '541's A row), the glue east of the '541 over the enables, the console 5V switch and the raw
    DC input over fingers 26 / 11, the raw DC buck in the lower body's east part, the interlock
    jumper and the scope pads in its west part; the FujiNet half along the top edge (the S3
    top-left, the microSD, the USB-C / CP2102N / buck corner top-right), the buttons and LEDs in
    the west strip under the S3."""
    rx, ry = 90.0, 95.0
    rp_macro(place, rx, ry, 90)
    place('TP_DVDD', 72.8, 93.2, 0)            # the core rail, by the VREG corner
    # ---- edge, console side: the data path ----
    place('J_EDGE', XC, Y_EDGE, 0)
    place('U_BUF', BUF_X, BUF_Y, 270)
    place('C_BUF', BUF_X + 6.2, BUF_Y + 3.0, 90)
    # the glue over the enables (fingers 9 / 10, x 98.7 / 101.3), under the central screw
    place('U_AND', 100.0, 121.0, 90)
    place('C_AND', 100.0, 115.6, 0)
    place('R_PDBUF', 94.6, 117.0, 90)          # BUF_EN E9 pull-down
    place('U_INV', 111.0, 121.0, 90)
    place('C_INV', 106.6, 115.6, 0)
    place('C_GLUEBULK', 111.0, 115.6, 0)
    place('R_VSH', 107.0, 127.4, 90)           # console 5V sense divider into the '14
    place('R_VSL', 108.8, 127.4, 90)
    # PHI2 (finger 14, x 111.43): pull-up and Schmitt buffer right over it
    place('U_PHI2', 112.8, 127.4, 0)
    place('C_PHI2', 116.0, 127.4, 90)
    place('R_PHI2PU', 110.4, 130.0, 0)
    # the console 5V switch over finger 26 (x 103.8, B.Cu), the raw DC jumper over finger 11 (F.Cu)
    place('Q_CONS', 100.4, 127.8, 0)
    place('C_CONS', 96.4, 127.2, 90)
    place('C_CONSHF', 94.4, 127.2, 90)
    place('JP_UNREG', 104.4, 128.8, 90)
    place('TP_CONS5V', 92.2, 129.2, 0)
    # the raw DC buck in the lower body's east part, its output diode and the console path's gate OR
    place('F_UNREG', 120.4, 129.0, 0)
    place('R_UNREG', 120.4, 126.4, 0)
    place('C_PREIN1', 117.4, 121.8, 90)
    place('C_PREIN2', 119.8, 121.8, 90)
    place('C_PREINHF', 122.2, 122.2, 90)
    place('U_PRE', 120.4, 117.2, 0)
    place('C_PREBST', 120.4, 113.4, 0)
    place('L_PRE', 126.6, 113.4, 0)
    place('C_PREOUT1', 125.8, 118.6, 90)
    place('C_PREOUT2', 128.2, 118.6, 90)
    place('TP_UNREG', 125.2, 125.4, 0)
    place('TP_PRE5V', 125.2, 122.6, 0)
    place('D_PRE', 121.0, 107.4, 0)
    place('R_PREPD', 126.6, 107.4, 90)
    place('D_OFF', 110.0, 108.0, 0)
    place('R_OFFPD', 113.6, 108.0, 90)
    # the interlock: CI2 (finger 36, x 78.4, B.Cu) and CI1 (finger 18, x 121.6) meet at JP_ILK
    place('JP_ILK', 78.4, 129.2, 0)
    place('Q_ILK', 73.6, 124.4, 0)
    place('R_ILKG', 77.6, 124.6, 90)
    place('Q_ILKDRV', 73.6, 119.8, 0)
    place('R_ILKPD', 77.6, 120.0, 90)
    # scope pads for the bus items, with a ground, in the lower body's west part
    for i, k in enumerate(('TP_EN40', 'TP_EN80', 'TP_OE1', 'TP_OE2', 'TP_PWROK', 'TP_PHI2')):
        place(k, 72.4 + 2.8 * (i % 3), 113.4 + 2.8 * (i // 3), 0)
    place('TP_GNDBUS', 80.8, 113.4, 0)
    # ADC divider by the RP's GPIO40 (north side)
    place('R_ADCH', 96.4, 82.6, 0)
    place('R_ADCL', 99.8, 82.6, 0)
    place('C_ADCF', 99.8, 80.4, 0)
    # the RP's debug header (DNP) by its GPIO44 / 45 (north-west)
    place('J_DBG', 88.0, 80.4, 90)
    # ---- FujiNet half: S3 top-left, microSD beside it, USB-C / CP2102N / buck top-right ----
    place('U_S3', 70.4, 65.0, 0)              # antenna end at the top edge (y 52)
    place('C_S3BULK', 83.0, 70.0, 90)
    place('C_S3', 83.0, 73.5, 90)
    place('R_EN', 83.0, 77.0, 90)
    place('C_EN', 85.6, 77.0, 90)
    place('J_SD', 104.4, 62.0, 180)           # slot at the top edge, east of the antenna keep-out (x <= 94)
    place('RN_SD', 97.0, 73.4, 90)
    place('R_SDCD', 100.0, 73.4, 90)
    place('C_SD', 103.0, 73.4, 90)
    # HRO's recommended layout puts the PCB edge 5.79 mm in front of the locating pegs
    # (fp y -2.6 -> edge at fp y +3.19): the face (fp y +3.65) overhangs the top edge by
    # 0.45 mm, so the plug's overmold clears the board edge (at y 57 it sat 1.35 mm inside)
    place('J_USB', 129.0, 55.2, 180)
    place('R_CC1', 121.5, 58.0, 90)
    place('R_CC2', 136.5, 58.0, 90)
    place('D_ESDV', 121.5, 62.5, 90)
    place('D_ESDP', 126.0, 65.0, 0)
    place('D_ESDM', 132.0, 65.0, 0)
    place('C_VBUS', 138.0, 62.5, 90)
    place('C_VBUSHF', 140.0, 62.5, 90)
    place('R_VBPD', 140.0, 66.5, 90)
    place('D_VBUS', 137.0, 72.0, 90)
    place('U_UART', 126.0, 73.0, 270)
    place('C_UART', 120.5, 71.0, 90)
    place('C_UARTBULK', 120.5, 74.5, 90)
    place('R_VBSH', 120.5, 78.0, 0)
    place('R_VBSL', 124.0, 78.0, 0)
    place('R_CPRST', 131.5, 69.5, 90)
    place('U_AUTOPROG', 132.0, 76.5, 0)
    place('U_BUCK', 129.0, 85.5, 180)
    place('C_BIN1', 134.5, 82.0, 90)
    place('C_BIN2', 137.0, 82.0, 90)
    place('C_BINHF', 139.5, 82.0, 90)
    place('C_5VBULK', 134.5, 89.0, 0)
    place('C_BST', 129.0, 82.0, 0)
    place('L_BUCK', 123.0, 87.5, 0)
    place('C_BOUT1', 117.5, 85.5, 90)
    place('C_BOUT2', 115.0, 85.5, 90)
    place('TP_3V3', 112.5, 85.5, 0)
    place('TP_5V', 139.5, 89.0, 0)
    place('TP_3V3RP', 80.6, 110.2, 0)
    # buttons and LEDs in the west strip under the S3 (the shell's face carries their pinholes and
    # windows): RP RESET / BOOTSEL over S3 EN / BOOT, the two LEDs under them
    place('SW_RESET', 62.4, 81.4, 0)
    place('SW_BOOTSEL', 70.4, 81.4, 0)
    place('SW_S3EN', 62.4, 87.8, 0)
    place('SW_S3BOOT', 70.4, 87.8, 0)
    place('D_RST', 66.4, 93.2, 0)
    place('D_WS', 113.0, 95.0, 0)
    place('C_WS', 116.0, 95.0, 90)
    place('R_WS', 118.2, 95.0, 90)
    place('D_LED', 121.4, 95.0, 0)
    place('R_LED', 124.6, 95.0, 90)
    fid += [('FID1', 115.0, 78.0), ('FID2', 136.0, 77.0), ('FID3', 82.0, 116.0)]


VARIANTS = {'P1': p1}

# board frame owned by the floorplan (gen_pcb reads these)
# the shell screws: the two corners of the upper body's step, and the original cart board's single
# screw (38.735 mm up the centre line: Pixels Past rev B, tdididit; the SIO2 shell's boss)
HOLES = [(63.0, 99.0, 3.2), (137.0, 99.0, 3.2), (100.0, 150.0 - 38.735, 3.2)]   # x, y (absolute), diameter
# In4: +3V3 north of the split, +5V south (FIVE_V_POLY, when set, replaces it); islands win over both
PLANE_SPLIT_Y = 91.0
# In4 +5V island (absolute; the +3V3_RP / DVDD islands win over it): everything south of y 91 (the
# cart side, the LDO input, the LEDs), and the strip up the east edge under the 3.3 V buck's input,
# the +5V bulk and the VBUS diode
FIVE_V_POLY = [(40.0, 91.0), (126.0, 91.0), (126.0, 78.0), (133.0, 78.0), (133.0, 66.0), (160.0, 66.0),
               (160.0, 160.0), (40.0, 160.0)]
LABEL = ((100.0, 72.0), (30.0, 20.0))     # shell label recess: centre (board x, y), size (w, h)
TITLE_XY = (100.0, 135.5)
JLC_ORDER = ((116.0, 100.0), 1.0)          # centre, text height (mm): clear of parts and silk, 1 mm+ inside the outline
RP_ROT = 90


def do_placement(place, fiducials):
    placed = set()

    def pl(key, *a):
        placed.add(key)
        place(key, *a)
    VARIANTS[VARIANT](pl, fiducials)
    if os.environ.get('PARK'):           # study only: park parts a variant does not place yet
        import design as D
        x, y = 62.0, 120.0
        for p in D.PARTS:
            if p.key not in placed:
                place(p.key, x, y, 0)
                x += 3.6
                if x > 140:
                    x, y = 62.0, y + 2.6
