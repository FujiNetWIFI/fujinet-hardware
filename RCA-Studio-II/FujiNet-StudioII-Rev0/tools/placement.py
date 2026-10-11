"""Component placement for gen_pcb.py: design.py key -> (x, y, rot), and the board frame the
floorplan owns (the shell-post holes, the In2 power islands).  KiCad frame: top view of the parts
side (F.Cu), y down, rotation CCW.  The insertion edge is y = 150, the board centre x = 100; the 22
fingers are on B.Cu (tools/edge_geom.py), seen from F.Cu pin 1 is east:

  x 141.6 137.6 133.7 129.7 125.8   D7 D6 D5 D4 D3 (1-5)     x 121.8 117.8   GND GND (6 ROM DIS, 7)
  x 113.9 109.9 105.9               D2 D1 D0 (8-10)          x 102.0  98.0  94.1  90.1   MA0-MA3 (11-14)
  x  86.1   CONS_5V (15)            x  82.2  78.2  74.2      MA4 MA5 MA6 (16-18)
  x  70.3   TPA (19)                x  66.3  MA7 (20)        x  62.4  /MRD (21)    x  58.4  CART CS (22)

The board (gen_pcb.OUTLINE, edge_geom.py): FliP's 90.912 mm-wide outline from the insertion edge up
(the full width enters the slot, two 8.128 mm post holes, two side notches), then 28 mm taller than
his board (edge_geom.CART_H, 111.49 mm) with rounded top corners for the ESP32-S3 half.  No part
closer than 23.5 mm to the insertion edge (edge_geom.PARTS_Y): the band below carries the finger
stubs, the address bus's locked two-layer twist and the data bus's fan-in to the '541.

The co-design (docs/floorplan-study.md):
  * the RP2354B at rotation 90 in the middle: GPIO0-9 (MA0-7, TPA, /MRD) at its south-west
    corner, GPIO16-23 (D0-D7) at its south-east corner, the core regulator and USB on its west
    side, the crystal and SWD on its east side;
  * the ten 330R in one row at 1.98 mm pitch south-west of it, in the RP's own GPIO order (MA0 ..
    MA7, TPA, /MRD west to east): the fingers run the other way (/MRD .. MA0), and a flow-through
    row cannot reverse a bus, so the band below twists the ten lines once (gen_pcb.address_twist);
  * the 74HCT541 at rotation 270 south-east of the RP over the data fingers, its channels taken in
    reverse (design.py): fingers -> Y row and A row -> GPIO16-23 both planar;
  * the glue ('32, '14, '1G02) east of the '541, under the RP's control pins (GPIO24-27);
  * the power mux (TPS2116) west by finger 15, on its CONS_5V island; the RP's LDO beside the RP;
  * the ESP32-S3 along the new top edge, its antenna flush and its 48 x 6 mm keep-out empty: the
    USB-C, its USBLC6 and the CP2102N west of the keep-out, the microSD east of it (beside the S3's
    SPI pins); the S3's buck below the band; the S3's USB pins face straight down at the RP's;
  * the four buttons (S3 EN, BOOTSEL, RESET, S3 BOOT) in a row under the S3, the LEDs beside it.
The RP2354B's ring (decoupling, crystal, BOOTSEL / QSPI_SS, SWD pads) is one rigid macro drawn at
rotation 90; Raspberry Pi's regulator corner (inductor, VREG_VIN / DVDD / AVDD capacitors, the 27R,
C_OTP) is placed by gen_pcb.graft_parts from tools/rpi_core_graft.sexpr.
"""
import math, os
import edge_geom as _EG0

VARIANT = os.environ.get('PLACE_VARIANT', 'P1')

# ---- board frame ------------------------------------------------------------
XC, Y_EDGE = 100.0, 150.0
RP_ROT = 90


def rot_pt(x, y, a):
    """gen_pcb.rot_pt: KiCad's rotation (CCW on screen, y down)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


# ---------------------------------------------------------------------------
# the RP2354B macro, relative to the RP centre, for the RP at rotation 90.  Pads (0.4 mm pitch, rows
# 4.95 from the centre): south 1-20 W->E (GP4-7, IOVDD 5, GP8-9, NC, DVDD 10, NC, IOVDD 15, GP16-20),
# east 21-40 S->N (GP21-23, IOVDD 24, GP24-27, IOVDD 29, XIN, XOUT, DVDD 32, SWCLK, SWDIO, RUN, NC),
# north 41-60 E->W (IOVDD 41, NC, GP40 ADC, IOVDD 50, DVDD 51, NC, DBG TX / RX, NC, ADC_AVDD, IOVDD 60),
# west 61-80 N->S (the regulator 61-65, USB 66 / 67, OTP 68, QSPI_IOVDD 69, NC, QSPI_SS 75, IOVDD 76,
# GP0-3).  Every supply pin also stubs inward to the +3V3 / DVDD rings under the package
# (gen_pcb.rp_support); the capacitors below sit straight out from their pins where the pin's
# neighbours leave the outside free, else beside the ring's plane vias.
RP_MACRO = [
    # south, between the address corner (x <= -1.4, leaving south-west) and the data corner (x >= 2.2,
    # leaving south-east): DVDD 10's and IOVDD 15's capacitors straight out (gen_pcb.cap_links), DVDD
    # 32's (east, boxed in by XOUT / SWCLK) below 10's on a B.Cu link from the DVDD ring
    # (gen_pcb.rp_support), IOVDD 5's (boxed in by GP7 / GP8: it reaches its ring inward) on the plane
    ('C_DV10', -0.2, 7.4, 270), ('C_IOV15', 1.4, 7.4, 270),       # 15's 0.4 west of its pin: GP16 drops beside it
    ('C_DV32', -0.2, 11.4, 270), ('C_IOV5', 3.8, 11.0, 270),
    # north: IOVDD 60, ADC_AVDD 59, DVDD 51, IOVDD 50, IOVDD 41 straight out (cap_links; 51's and 50's are
    # 0402 to fit between the debug UART (55 / 56) and GP40 (49), which jogs east to its 100 nF and divider)
    ('C_IOV60', -5.0, -7.4, 90), ('C_ADC', -3.3, -7.4, 90), ('C_DV51', -0.6, -7.0, 90), ('C_IOV50', 0.4, -7.0, 90),
    ('C_IOV41', 3.8, -7.4, 90),
    ('C_ADCF', 1.4, -10.4, 90), ('R_ADCL', 3.4, -10.4, 90), ('R_ADCH', -0.6, -10.4, 270),
    # east: IOVDD 24 / 29 (the control lines GP24-27 leave between them) reach their capacitors through
    # the ring and the plane; the two sit north-east beyond the SWD escape
    ('C_IOV24', 9.6, -4.6, 0), ('C_IOV29', 9.6, -6.2, 0),
    # crystal block: XIN (30) straight east into Y1's south-west pad; XOUT (31) east then up into the 1k
    # standing north of XIN's line; XOUT_Y over the crystal's north-west GND pad to its north-east pad;
    # the load caps on the far sides, so GPIO24-27 pass south of the block and SWD west of the 1k
    ('Y_RP', 13.5, -1.0, 0), ('C_XIN', 13.5, 1.6, 0), ('C_XOUT', 17.2, -1.85, 0), ('R_XOUT', 8.0, -1.8, 90),
    # west, south of the USB 27R (graft): QSPI_SS (75) out west to its pull-up and the BOOTSEL 1k;
    # IOVDD 76 reaches its capacitor through the ring; GP0-3 turn south at once
    ('C_QSPI', -11.6, 1.1, 0), ('R_SS', -11.6, 2.7, 0), ('R_BSEL', -11.6, 4.3, 180),
    ('C_IOV76', -11.6, 5.9, 0), ('C_IOBULK', -14.6, 1.9, 90),
    # SWD: SWCLK / SWDIO / RUN (33-35) leave east and turn north inside the 1k as a ribbon (gen_pcb.swd_escape),
    # to a row of pads north; the RUN pull-up beyond TP_RUN
    ('TP_RUN', 4.2, -13.6, 0), ('TP_SWDIO', 6.8, -13.6, 0), ('TP_SWCLK', 9.4, -13.6, 0), ('TP_GND', 12.0, -13.6, 0),
    ('R_RUN', 4.2, -16.5, 270),            # pad 2 (RUN) south toward TP_RUN, pad 1 (+3V3) north
    ('TP_DVDD', -9.4, -9.4, 0),
]


def rp_macro(place, rx, ry, rot=90):
    rr = rot - 90
    place('U_RP', rx, ry, rot)
    for key, dx, dy, r in RP_MACRO:
        ox, oy = rot_pt(dx, dy, rr)
        place(key, rx + ox, ry + oy, (r + rr) % 360)


# ---------------------------------------------------------------------------
RP_X, RP_Y = 104.0, 100.0
Y0 = Y_EDGE - _EG0.CART_H                              # the top edge (the ESP32-S3's antenna, USB-C, microSD)
S3_X = 100.0                                           # the ESP32-S3, antenna flush with the top edge
USB_X = 65.0                                           # the USB-C (power + S3 programming), west of the keep-out
SD_X = 134.4                                           # the microSD, east of the keep-out
BANK_X0, BANK_PITCH, BANK_Y = 84.0, 1.98, 124.9      # the 330R row: MA0 .. MA7, TPA, /MRD west to east
BANK = ['R_MA%d' % i for i in range(8)] + ['R_TPA', 'R_MRD']
BUF_XY = (113.5, 116.0)                                # the 74HCT541, rotation 270


def p1(place, fid):
    """P1: the RP2354B in the middle, the 330R row south-west and the '541 south-east of it over
    their fingers, the glue east, the power block west, the USB-C and the buttons along the top."""
    rp_macro(place, RP_X, RP_Y, RP_ROT)
    place('J_EDGE', XC, Y_EDGE, 0)
    # ---- the address row: pad 1 (the edge side) south, pad 2 (the RP side) north ----
    for i, k in enumerate(BANK):
        place(k, BANK_X0 + i * BANK_PITCH, BANK_Y, 90)
    # ---- the '541 over the data fingers: Y row south (D0..D7 west to east), A row north ----
    place('U_BUF', BUF_XY[0], BUF_XY[1], 270)
    place('C_BUF', BUF_XY[0] + 4.9, BUF_XY[1] + 1.6, 90)          # VCC (pin 20) is the south row's east end
    # ---- glue east of the '541: the '1G02 by its /OE1 corner, the '32 by its /OE2 corner with the
    # /DRIVE and /CLAIM pull-ups at its inputs, the '14 and the console-5 V sense further east ----
    place('U_NOR', 121.0, 113.6, 0)
    place('C_NOR', 121.0, 110.6, 0)
    place('U_OR', 127.0, 111.0, 0)
    place('C_OR', 131.6, 107.2, 90)
    place('R_PUDRIVE', 121.4, 106.6, 0)
    place('R_PUCLAIM', 121.4, 108.4, 0)
    place('U_INV', 137.6, 111.0, 0)
    place('C_INV', 140.4, 104.4, 0)
    place('C_GLUEBULK', 136.6, 104.4, 0)
    place('R_VSH', 132.4, 104.4, 0)
    place('R_VSL', 128.6, 104.4, 0)
    # ---- scope pads for the bus, in a row under the glue (south: clear of the shell's top opening) ----
    for i, k in enumerate(('TP_MRD', 'TP_TPA', 'TP_CARTCS', 'TP_DRIVE', 'TP_CLAIM', 'TP_PWROK', 'TP_GNDBUS')):
        place(k, 121.0 + i * 2.8, 122.8, 0)
    # ---- power block west, by finger 15: the TPS2116 mux on the CONS_5V island (VIN2 east, toward the
    # finger), VBUS (VIN1, west) from the USB-C at the top-left, its priority divider beside it ----
    # rotation 270: the north row (PR1, VIN1, VOUT, GND west to east) faces the +5V plane, the south row
    # (MODE, VIN2, VOUT, ST) the CONS_5V island; VOUT 2 / 7 and VIN1 3 / MODE 5 join under the body
    # (gen_pcb.mux_link)
    place('U_MUX', 76.0, 120.6, 270)
    place('C_CONS', 71.0, 123.8, 0)
    place('C_CONSHF', 80.4, 123.8, 0)
    place('C_MUXV1', 73.4, 115.6, 90)
    place('R_PRH', 70.4, 115.0, 0)
    place('R_PRL', 70.4, 116.8, 0)
    place('TP_CONS5V', 61.2, 121.4, 0)
    place('TP_VBUS', 61.2, 118.4, 0)
    place('TP_5V', 61.2, 111.0, 0)
    # ---- the RP2354B's LDO west of the RP, on the edge of its +3V3 island: inputs (1-3) south on the
    # +5V plane, output (5) north into the island ----
    place('U_LDO', 85.0, 110.4, 90)
    place('C_LDOIN', 85.0, 114.6, 0)
    place('C_LDOOUT', 85.0, 106.6, 0)
    place('TP_3V3', 81.2, 106.6, 0)
    # ---- the button row (pinholes in the shell): S3 EN, BOOTSEL, RESET, S3 BOOT; the RESET steering
    # pair under RESET; the RP's activity LED and the WS2812 status light under the S3 ----
    place('SW_S3EN', 94.0, 72.6, 0)
    place('SW_BOOTSEL', 104.0, 72.6, 0)
    place('SW_RESET', 114.0, 72.6, 0)
    place('SW_S3BOOT', 124.0, 72.6, 0)
    place('D_RST', 114.0, 77.8, 0)
    place('J_DBG', 103.5, 80.2, 270)             # pin 1 (TX) east: the RP's TX (55) is east of RX (56)
    place('D_WS', 106.0, 67.4, 0)
    place('C_WS', 109.0, 67.4, 90)
    place('R_WS', 103.0, 67.4, 90)
    place('D_LED', 131.2, 67.4, 180)
    place('R_LED', 131.2, 69.6, 180)
    # the S3's RUN / BOOTSEL controls at the RP's end: RUN_CTL beside the RUN pull-up, BOOTSEL_CTL beside
    # the BOOTSEL 1k on QSPI_SS
    place('R_RUNCTL', 110.2, 83.0, 270)
    place('R_BSELCTL', 89.2, 104.3, 0)
    # ---- the FujiNet half along the (new) top edge: the S3 in the middle, its antenna flush with the
    # edge and its 48 x 6 mm keep-out (the module footprint's zone) clear of everything; the USB-C and its
    # bridge west of the keep-out, the microSD east of it ----
    sy = Y0 + 12.97                               # the antenna 0.2 mm inside the edge (courtyard 0.1)
    place('U_S3', S3_X, sy, 0)
    place('C_S3', S3_X - 11.8, sy - 4.0, 0)       # at 3V3 (pin 2), west
    place('C_S3BULK', S3_X - 14.8, sy - 3.4, 90)
    place('R_EN', S3_X - 11.8, sy - 2.2, 0)       # EN (pin 3)
    place('C_EN', S3_X - 11.8, sy - 0.4, 0)
    # the USB-C (power + S3 programming): the ESD array under its contacts, CC 5.1k on either side,
    # the 1 uF at its VBUS pads, the 100 nF at the USBLC6's VBUS pin (ST's layout figure: CBUS at
    # pin 5; gen_pcb.bridge_link joins them); the CP2102N and its auto-program pair below
    ux = USB_X
    # HRO's recommended layout: the PCB edge 5.79 mm in front of the locating pegs (fp y +3.19), so the
    # shell face (fp y +3.65) overhangs the edge by 0.46 mm and a plug's overmold clears the board; at
    # Y0 + 5.0 the face sat 1.35 mm inside (the fleet-wide fix of FujiNet-NES Rev0, 63ccf57)
    place('J_USB', ux, Y0 + 3.19, 180)
    place('U_ESD', ux, Y0 + 13.2, 90)            # D- (I/O1) west, D+ (I/O2) east: as the CP2102N's top row
    place('R_CC1', ux + 3.6, Y0 + 12.0, 90)
    place('R_CC2', ux - 3.6, Y0 + 12.0, 90)
    place('C_VBUS', ux - 7.4, Y0 + 9.0, 90)
    place('C_VBUSHF', ux + 2.6, Y0 + 15.49, 270)  # east of the USBLC6, south of R_CC1, north of the CP2102N; pad 1 (VBUS) north
    place('U_UART', ux, Y0 + 20.6, 270)          # USB pins (D- 5, D+ 4) on the top row, the UART / RTS / DTR east
    place('C_UART', ux - 3.4, Y0 + 16.7, 180)      # at VDD / VREGIN (6 / 7, top row west), pad 1 east
    place('C_UARTBULK', ux - 3.4, Y0 + 14.9, 180)
    place('R_CPRST', ux - 5.6, Y0 + 22.6, 90)     # RSTb (9, west column)
    place('R_VBSH', ux - 5.4, Y0 + 19.0, 90)
    place('R_VBSL', ux - 7.2, Y0 + 19.0, 90)
    place('U_AUTOPROG', ux + 6.4, Y0 + 21.6, 0)   # RTS / DTR (east column)
    # the S3 side's 3.3 V buck below the band, west of the button row: its input loop on F.Cu down the
    # capacitor stack (gen_pcb.buck_loop, +5V plane), its output north into the +3V3_S3 island
    bx, by = 80.0, 72.0
    place('U_BUCK', bx, by, 0)
    place('C_BINHF', bx, by + 2.5, 0)
    place('C_BIN', bx, by + 4.6, 0)
    place('C_5VBULK', bx, by + 7.0, 0)
    place('C_BST', bx + 3.0, by - 1.8, 90)
    place('L_BUCK', bx + 6.2, by - 1.4, 90)
    place('C_BOUT1', bx + 4.0, by - 7.0, 90)
    place('C_BOUT2', bx + 6.6, by - 7.0, 90)
    place('TP_3V3S3', bx + 1.2, by - 7.0, 0)
    # the microSD east of the keep-out, its card slot at the top edge; pull-ups and its 10 uF below
    place('J_SD', SD_X, Y0 + 10.0, 180)
    place('RN_SD', SD_X - 7.4, Y0 + 20.6, 90)
    place('R_SDCD', SD_X - 4.6, Y0 + 20.6, 90)
    place('C_SD', SD_X - 2.0, Y0 + 20.6, 90)
    fid += [('FID1', 58.6, 92.0), ('FID2', 141.4, 120.0), ('FID3', 141.4, 64.0)]


VARIANTS = {'P1': p1}

# board frame owned by the floorplan (gen_pcb reads these): the shell posts (edge_geom)
import edge_geom as _EG
HOLES = [(XC + x, Y_EDGE - y, _EG.HOLE_D) for x, y in _EG.HOLES]
HOLE_KEEP = 5.6          # no parts within this radius of a hole centre (FliP's keep-out: 5.1-6.1)
HOLE_CU = _EG.HOLE_D / 2 + 0.6   # no copper within this radius
# In2: +3V3 everywhere but these islands (absolute), highest priority first
# In2 is +5V (the mux's output) but for these islands, highest priority first (gen_pcb.ISLANDS)
CONS5V_POLY = [(58.0, 119.4), (88.6, 119.4), (88.6, 141.0), (83.6, 141.0), (83.6, 126.0), (58.0, 126.0)]
RP3V3_POLY = [(82.0, 81.0), (124.0, 81.0), (124.0, 103.5), (119.6, 103.5), (119.6, 113.6), (89.0, 113.6),
              (89.0, 108.6), (82.0, 108.6)]                     # the RP2354B, its ring and its LDO's output
S3_POLY = [(54.0, Y0 - 1.0), (146.0, Y0 - 1.0), (146.0, 66.0), (90.0, 66.0), (90.0, 68.4), (82.4, 68.4), (82.4, 66.0),
           (54.0, 66.0)]   # the S3, its bridge, the microSD; a lobe under the buck's output capacitors
LABEL = ((100.0, 104.0), (44.0, 30.0))    # shell label recess: centre (board x, y), size (w, h), clear of the openings
TITLE_XY = (74.0, 96.0)
JLC_ORDER = ((128.0, 92.0), 1.0)          # centre, text height (mm): clear of parts and silk


def do_placement(place, fiducials):
    placed = set()

    def pl(key, *a):
        placed.add(key)
        place(key, *a)
    VARIANTS[VARIANT](pl, fiducials)
    if os.environ.get('PARK'):           # study only: park parts a variant does not place yet
        import design as D
        x, y = 60.0, 90.0
        for p in D.PARTS:
            if p.key not in placed:
                place(p.key, x, y, 0)
                x += 3.6
                if x > 140:
                    x, y = 60.0, y + 2.6
