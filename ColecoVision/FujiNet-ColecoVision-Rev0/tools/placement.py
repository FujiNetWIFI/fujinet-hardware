"""Component placement for gen_pcb.py: key -> (x, y, rot), and the board frame the floorplan owns.
Board x 79.9..120.1, y 47.6..130 (y = 47.6 top edge, y = 130 insertion edge; tools/edge_geom.py); parts
only above the shell's bottom (courtyards at y < 130 - edge_geom.PARTS_Y = 115) and out of the side
notches.  Top view (F.Cu = the component face, even pins), y down, rotation CCW.  Parts are named by
their design.py key, so a reference change never moves a part.

Seen from the parts face the fingers run, west to east (x 82.2 .. 117.8, 2.54 mm):
  F.Cu  /C000, D3-D7, A11, A10, /8000, A14, /A000, A12, A9, A8, +5V
  B.Cu  D2, D1, D0, A0, A1, A2, GND, A3, A4, A13, A5, A6, A7, /E000, GND
so the data group is at the west end and the address group fills the middle and the east.

  top edge      USB-C (west of centre) and the microSD (east, its card slot in the top edge): both
                reach the shell's top wall
  under them    the CP2102N block between the USB-C and the module
  upper-west    the ESP32-S3 module turned 90 degrees, its antenna flush with the west edge over a
                strip that is copper-free on every layer (ANT_KEEP)
  upper-east    the S3 side's 3.3 V buck, the WS2812, the two S3 buttons
  lower body    the RP2350A at rot 90 (FujiNet-Arcadia Rev0's neighbourhood: decoupling north, crystal
                east, regulator corner west), the W25Q16 west of it; the four address arrays under it in
                GPIO order; the 74LVC245A in the south-west corner, straight over the data fingers (its
                B port's lines cross under the address lines to GP15-22); the select pull-ups and AND
                gates east of the arrays; the power mux by the +5V finger's column
  y 115 .. 130  parts-free: the shell's bottom and the fingers.
"""
import math
import edge_geom as EG

XC = 100.0
Y_EDGE = 130.0                       # insertion edge
X0, X1 = XC - EG.BOARD_W / 2, XC + EG.BOARD_W / 2
Y0 = Y_EDGE - EG.CART_H              # top edge
HOLES = [(XC + x, Y_EDGE - y, EG.HOLE_D) for x, y in EG.HOLES_REL]
RP = (99.4, 96.4, 90)                # RP2350A centre + rotation (gen_pcb turns the graft with it)
S3 = (X0 + 12.85, 73.6, 90)          # ESP32-S3 module: rot 90, the antenna (local -y) at the west edge
ANT_LATERAL = 15.0                   # the antenna keep-out's half-length along the edge (footprint: 24)


def rot_pt(x, y, a):
    """gen_pcb.rot_pt: KiCad's rotation (CCW on screen, y down)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


# the antenna keep-out on the board (all layers): from the module's antenna boundary (local y -6.75)
# to the west edge, ANT_LATERAL either side of its centre line
ANT_KEEP = (X0, S3[1] - ANT_LATERAL, S3[0] - 6.75, S3[1] + ANT_LATERAL)
KEEPOUTS = [ANT_KEEP]

# In2 islands (absolute polygons; the base of In2 is +5V).
# +3V3 (the buck: the S3, the CP2102N, the microSD): the upper body, down to the module's foot
# and a tongue under the module's foot for its decoupling and EN pull-up (C_S3, C_S3BULK, R_EN)
S3_ISLAND = [(X0, Y0), (X1, Y0), (X1, 84.0), (92.0, 84.0), (92.0, 87.8), (86.2, 87.8), (86.2, 84.0), (X0, 84.0)]
# +3V3_RP: the lower body -- the RP, its caps and flash, the '245, the AND pair, the pull-ups, the LDO's
# output -- less a +5V pocket at the LDO's input (west) and one round the mux and the WS2812 (east)
RP_ISLAND = [(92.2, 84.4), (106.8, 84.4), (106.8, 91.0), (111.0, 91.0), (111.0, 100.4), (116.6, 100.4),
             (116.6, 114.6), (X0, 114.6), (X0, 94.2), (87.4, 94.2), (87.4, 88.0), (92.2, 88.0)]
# DVDD lobe, joined to gen_pcb's core island at the RP's south-west corner: under the DVDD cap column
# (FujiNet-Arcadia Rev0's lobe, RP-relative: west of the corner pin's IOVDD via spot)
DVDD_LOBE = [(RP[0] + x, RP[1] + y) for x, y in
             [(-5.6, 1.9), (-1.9, 1.9), (-1.9, 3.1), (-3.0, 3.1), (-3.0, 9.2), (-5.6, 9.2)]]
# no vias of any net across the lobe's neck into the core island (a QSPI via there cut the lobe off)
DVDD_NECK_KEEP = [(RP[0] + x, RP[1] + y) for x, y in [(-4.6, 1.7), (-2.0, 1.7), (-2.0, 3.3), (-4.6, 3.3)]]
# CONS_5V: from the +5V finger's neck via (gen_pcb.finger_gnd_vias) up the east edge to the mux's
# south row and the console-side caps (no router track for the console's 5 V)
# (the block under the mux's south row takes VIN2's via; the +5V bulk cap and test pad stay off it)
CONS5V_ISLAND = [(113.6, 98.6), (116.4, 98.6), (116.4, 100.6), (X1 - 0.6, 100.6), (X1 - 0.6, 119.4),
                 (116.4, 119.4), (116.4, 101.8), (113.6, 101.8)]

# FujiNet-Arcadia Rev0's RP2350A neighbourhood, relative to the RP centre (rot 90): IOVDD / ADC caps
# north, crystal east, the QSPI_SS pull-up, RP bulk and the W25Q16 west (the flash where Raspberry
# Pi's minimal design has it, turned with the RP), the DVDD / IOVDD caps south-west (0402, a channel
# left between them and the flash for its back-row QSPI lines)
RP_NEAR = [
    ('C_IOVDD45', -6.6, -7.4, 90), ('C_ADC', -4.8, -7.4, 90), ('C_IOVDD38', -3.0, -7.4, 90),
    ('C_IOVDD30', -1.2, -7.4, 90), ('C_RPBULK', -11.9, -2.4, 90), ('R_SSPU', -11.3, 1.3, 90),
    ('C_DVDD6', -4.8, 5.2, 180), ('C_DVDD39', -4.8, 7.0, 180), ('C_DVDD23', -4.8, 8.8, 180),
    ('C_IOVDD1', -6.6, 5.2, 0), ('C_IOVDD11', -6.6, 7.0, 0), ('C_IOVDD20', -6.6, 8.8, 0),
    ('R_XOUT', 6.1, 0.2, 0), ('Y_XTAL', 9.9, 0.8, 0), ('C_XIN', 9.9, 3.6, 180), ('C_XOUT', 11.1, -2.6, 90),
    ('R_RUNPU', 6.0, -3.6, 0),
    ('U_FLASH', -10.8, 5.0, 90), ('C_FLASH', -10.6, 9.0, 90),
]
GRAFT_KEYS = ('L_VREG', 'C_VOUT', 'C_VIN', 'C_FILT', 'R_FILT', 'R_USBP', 'R_USBM', 'C_OTP')


def do_placement(place):
    place('J_EDGE', XC, Y_EDGE, 0)

    # ---------------- RP2350A ----------------
    rx, ry, rr = RP
    place('U_RP', rx, ry, rr)
    for k, dx, dy, r in RP_NEAR:
        place(k, rx + dx, ry + dy, r)
    # address arrays under it, GPIO order west to east, at rot 90: inputs (pads 1-4) south toward the
    # fingers, outputs north toward GP0-14
    for i, k in enumerate(('RN_A0', 'RN_A4', 'RN_A8', 'RN_A12')):
        place(k, 94.0 + 3.8 * i, 110.6, 90)
    # the data buffer straight over the data fingers (D0-D7 are the edge's west end) at rot 90: A row
    # (south) to the fingers, B row (north) to GP15-22; DIR / VCC at its west end, by the notch
    place('U_BUF', 87.6, 111.0, 90)
    place('C_BUF', 82.7, 106.0, 90)
    place('R_DIR', 82.7, 109.8, 90)
    # selects: pull-ups east of the arrays (inputs south), the AND pair east of them; the bring-up pads
    # and the console-side caps beside the gates, the CONS_5V caps and pad on the island's strip
    place('RN_SEL', 109.4, 110.6, 90)
    place('U_AND2', 109.0, 105.6, 0)
    place('U_AND3', 114.0, 110.4, 0)
    place('C_AND2', 109.0, 102.4, 0)
    place('C_AND3', 114.0, 113.4, 0)

    # ---------------- the band between the module and the RP ----------------
    place('D_LED', 101.6, 85.0, 0)
    place('R_LED', 101.6, 86.8, 0)
    place('C_VS', 104.8, 85.0, 0)
    place('R_VSL', 104.8, 86.8, 0)
    place('R_VSH', 104.6, 88.6, 0)
    place('D_RST', 108.6, 85.4, 0)
    place('D_WS', 112.4, 85.4, 0)
    place('R_WS', 115.6, 85.4, 0)
    place('C_WS', 118.6, 85.4, 90)
    place('TP_GP23', 101.6, 89.6, 0)
    place('TP_RUN', 107.4, 89.6, 0)
    place('TP_SWDIO', 110.0, 89.6, 0)
    place('TP_SWCLK', 112.6, 89.6, 0)
    place('TP_GND', 115.2, 89.6, 0)

    # ---------------- top: USB-C, microSD ----------------
    # HRO's recommended layout puts the PCB edge 5.79 mm in front of the locating pegs: origin =
    # top edge + 3.2 at rot 180, the face 0.46 mm past the edge (Studio II's reference, PR #61)
    place('J_USB', 91.8, Y0 + 3.2, 180)
    place('J_SD', X1 - 8.75, Y0 + 9.8, 180)        # card slot north, in the top edge
    place('R_CC1', 81.4, 50.4, 90)
    place('R_CC2', 83.4, 50.4, 90)
    place('C_VBUS', 81.4, 54.2, 90)
    place('C_VBUSHF', 83.4, 54.2, 90)
    place('U_AUTOPROG', 99.8, 49.4, 90)
    place('R_CPRST', 99.8, 53.4, 90)
    place('U_ESD', 92.0, 58.9, 90)              # south row DM / DP straight to U_UART's pins 5 / 4
    place('R_VBSH', 88.0, 58.0, 90)
    place('R_VBSL', 88.0, 61.6, 90)
    place('C_UART', 93.6, 62.9, 180)               # at VDD / VREGIN (pins 6 / 7), south of the D+ / D- entry
    place('C_UARTBULK', 90.6, 62.9, 0)
    place('U_UART', 99.4, 60.6, 0)

    # ---------------- ESP32-S3 ----------------
    place('U_S3', S3[0], S3[1], S3[2])
    place('C_S3', 88.0, 85.0, 0)
    place('C_S3BULK', 88.0, 86.8, 0)
    place('R_EN', 91.6, 85.0, 0)
    place('C_EN', 91.6, 86.7, 0)
    place('R_RUNCTL', 95.0, 85.0, 0)
    place('R_SSCTL', 98.4, 85.0, 0)

    # ---------------- upper-east: microSD passives, the buck, RESET and S3 BOOT ----------------
    place('RN_SD', 108.2, 66.2, 90)
    place('R_SDCD', 107.2, 70.6, 90)
    place('C_SD', 107.2, 74.2, 90)
    place('C_BST', 111.8, 65.0, 0)
    place('U_BUCK', 113.2, 68.0, 0)
    place('L_BUCK', 117.6, 68.2, 0)
    place('C_BIN', 110.0, 70.6, 90)
    place('C_BINHF', 110.0, 74.2, 90)
    place('C_BOUT2', 113.6, 72.0, 0)
    place('C_BOUT1', 117.6, 72.0, 0)
    place('TP_3V3S3', 113.4, 74.6, 0)
    place('SW_S3BOOT', 111.0, 79.6, 90)
    place('SW_RESET', 116.8, 79.6, 90)

    # ---------------- lower-west: BOOTSEL, the RP's LDO ----------------
    place('SW_BOOTSEL', 84.4, 100.0, 90)
    place('R_SSBTN', 86.0, 105.4, 0)
    place('U_LDO', 87.4, 90.4, 0)
    place('C_LDOIN', 84.4, 90.6, 90)
    place('C_LDOOUT', 90.6, 90.4, 90)
    place('TP_3V3', 112.4, 106.4, 0)
    place('TP_SELFTEST', 115.0, 103.2, 0)
    place('TP_DBGTX', 112.4, 103.2, 0)

    # ---------------- power: the mux by the +5V finger ----------------
    # the TPS2116 at rot 270: its north row PR1 / VIN1 / VOUT / GND, its south row MODE / VIN2 / VOUT
    # / ST on the CONS_5V island (gen_pcb.mux_link draws the joins)
    place('U_MUX', 114.8, 96.6, 270)
    place('R_PRH', 112.2, 95.0, 90)
    place('R_PRL', 112.2, 98.4, 90)
    place('C_MUXV1', 117.2, 95.0, 90)
    place('C_5VBULK', 117.6, 98.6, 270)
    place('TP_VBUS', 115.4, 92.2, 0)
    place('TP_5V', 112.6, 92.2, 0)
    place('C_CONSHF', 117.0, 109.0, 90)
    place('C_CONS', 117.0, 105.6, 90)
    place('TP_CONS5V', 117.6, 102.2, 0)


# routed first (tools/finish_route.py --nets, locked), in this order, before Freerouting: Freerouting
# never enters a finger's neck, and the edge nets need the room more than anything else does
PRE_ROUTE = ['/usb/UBRG_DP', '/usb/UBRG_DM'] + ['/cart-bus/' + n for n in (
    'CD2 CD1 CD3 CD0 CD4 CD5 CD6 CD7 SELC000_N CA8 CA0 CA1 CA2 CA11 CA10 CA3 CA4 SEL8000_N CA14 CA13 '
    'SELA000_N CA5 CA12 CA6 CA9 CA7 SELE000_N').split()]     # data west to east, then A8 (the longest run), then the rest

# then Freerouting on these alone, locked (tools/fr_subset.py): the W25Q16's QSPI, whose corner west of
# the RP the full run otherwise crosses with B.Cu through-traffic (one line walled out in most runs)
FR_FIRST = ['/rp-core/QSPI_%s' % n for n in ('SS', 'SCLK', 'SD0', 'SD1', 'SD2', 'SD3')]

# centre, text height (mm), side: JLCPCB's order number -- on the back, under the module (the parts face
# has no 12 x 1.6 mm spot clear of pads and courtyards; the back has no parts)
JLC_ORDER = ((100.0, 80.0), 1.0, 'B')
FIDUCIALS = [('FID1', 81.6, 113.4), ('FID2', 118.4, 113.6), ('FID3', 82.0, 57.2)]
