"""Component placement for gen_pcb.py: key -> (x, y, rot), and the board frame the floorplan owns.
Board x 68.5..131.5, y 45..130 (y = 45 top edge, y = 130 insertion edge; tools/edge_geom.py); parts
only above the shell's bottom (courtyards at y < 130 - edge_geom.PARTS_Y = 110) and clear of the two
shell posts.  Top view (F.Cu = the 1..15 face), y down, rotation CCW.  Parts are named by their
design.py key, so a reference change never moves a part.

Seen from the parts face the fingers run, west to east:
  F.Cu  T0, D0 .. D7 (x 72.5 .. 103.9), A10, P14, P11, P10, A11, A9 (x 107.9 .. 127.5)
  B.Cu  /WR, B, GND, +5V, E, /PSEN (x 72.5 .. 92.1), A0 .. A5, A7, A6, A8 (x 96.1 .. 127.5)
and the RP2354B at rotation 90 has its bus pins round its south-west corner, south side and the
south half of its east side in GPIO order (GP0-3 up the west side's south end, GP4-20 west to east
along the south, GP21-27 up the east side; GP28 above RUN).  So each group keeps its order from
fingers to pins: the address group (fingers east, B.Cu) and the data group (fingers west, F.Cu)
only change sides, and the two finger faces put them on different layers.

  top-right     ESP32-S3 module, antenna flush with the top edge over a band that is copper-free
                on every layer (its footprint's keep-out: nothing at x > 97.5 above y 51.1)
  top-left      USB-C on the top edge, its ESD / CC / VBUS parts east of it; the CP2102N block
  left edge     microSD (slot west) under the USB-C, its pull-ups east of it
  top-middle    two of the buttons, the WS2812 and the RP's LED (between the bridge and the S3)
  centre        the RP2354B at rot 90 (Studio II's macro: decoupling north, crystal east, QSPI /
                BOOTSEL west, SWD pads north-east); Raspberry Pi's regulator corner (gen_pcb graft)
                west-north-west of it, turned with it
  under the RP  the 28 series resistors in two blocks, each in its pins' GPIO order west to east:
                address GP0-13 south-west, data and control GP14-28 south-east; pad 1 (the edge
                side) south, staggered rows at 1.27 mm
  west          the power mux by the +5V finger's column, the console-5V parts and VSENSE, the RP's
                LDO, two buttons
  east          the S3 side's 3.3 V buck under the module
  y 110 .. 119.5   parts-free (the shell's bottom to the finger necks): the buses' crossing band.
"""
import math
import edge_geom as EG

XC = 100.0
Y_EDGE = 130.0                       # insertion edge
X0, X1 = XC - EG.BOARD_W / 2, XC + EG.BOARD_W / 2
Y0 = Y_EDGE - EG.CART_H              # top edge
HOLES = [(XC + x, Y_EDGE - y, EG.HOLE_D) for x, y in EG.HOLES_REL]
RP = (100.0, 87.0, 90)               # RP2354B centre + rotation (gen_pcb turns the graft with it)
S3 = (121.5, Y0 + 12.85)             # ESP32-S3 module centre: the module's top flush with the top edge


def rot_pt(x, y, a):
    """gen_pcb.rot_pt: KiCad's rotation (CCW on screen, y down)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


# In2 islands (absolute polygons; the base of In2 is +5V).
# +3V3_RP: the RP, its ring's corner vias, its caps, the graft corner and the LDO
RP_ISLAND = [(83.0, 72.0), (118.0, 72.0), (118.0, 95.0), (83.0, 95.0)]
# +3V3 (the buck: S3, CP2102N, microSD): the top band, and a strip down the right edge to the buck
S3_ISLAND = [(X0, Y0), (X1, Y0), (X1, 96.0), (119.0, 96.0), (119.0, 71.0), (X0, 71.0)]
# CONS_5V: from the +5V finger's neck via (gen_pcb.finger_gnd_vias) up under the mux, its
# console-side caps and the VSENSE divider (no router track for the console's 5 V)
CONS5V_ISLAND = [(X0 + 2.0, 89.0), (82.5, 89.0), (82.5, 112.0), (84.6, 112.0), (84.6, 121.0), (X0 + 2.0, 121.0)]

# The RP2354B macro (FujiNet-StudioII Rev0's), relative to the RP centre, for the RP at rotation 90.
# Pads (0.4 mm pitch, rows 4.95 from the centre): south 1-20 W->E (GP4-7, IOVDD 5, GP8-11, DVDD 10,
# GP12-15, IOVDD 15, GP16-20: all bus), east 21-40 S->N (GP21-23, IOVDD 24, GP24-27, IOVDD 29, XIN,
# XOUT, DVDD 32, SWCLK, SWDIO, RUN, GP28-32), north 41-60 E->W (IOVDD 41, GP33-39, GP40 VSENSE,
# IOVDD 50, DVDD 51, GP41-43, GP44 / 45 debug UART, GP46-47, ADC_AVDD, IOVDD 60), west 61-80 N->S
# (the regulator 61-65, USB 66 / 67, OTP 68, QSPI_IOVDD 69, QSPI 70-74, QSPI_SS 75, IOVDD 76,
# GP0-3).  Every supply pin stubs inward to the +3V3_RP / DVDD rings under the package
# (gen_pcb.rp_support), so the south side's three (5, 10, 15), boxed in by the bus, need nothing
# outside: their capacitors sit north with the others, on the rings' copper and the plane.
RP_MACRO = [
    # north: IOVDD 60, ADC_AVDD 59, DVDD 51, IOVDD 50, IOVDD 41 straight out (gen_pcb.cap_links; 51's
    # and 50's are 0402 to fit between GP45 (56) and GP40 (49)); the south side's DVDD 10 / IOVDD 5 /
    # IOVDD 15 capacitors one row further out
    ('C_IOV60', -5.0, -7.4, 90), ('C_ADC', -3.3, -7.4, 90), ('C_DV51', -0.6, -7.0, 90), ('C_IOV50', 0.4, -7.0, 90),
    ('C_IOV41', 3.8, -7.4, 90),
    ('C_DV10', -1.6, -10.0, 90), ('C_IOV5', 2.2, -10.4, 90), ('C_IOV15', 4.0, -10.4, 90),
    # east: IOVDD 24 / 29 reach their capacitors through the ring and the plane; DVDD 32's beside them
    ('C_IOV24', 9.6, -4.6, 0), ('C_IOV29', 9.6, -6.2, 0), ('C_DV32', 9.6, -7.8, 0),
    # crystal block: XIN (30) straight east into Y1's south-west pad; XOUT (31) east then up into the
    # 1k standing north of XIN's line; the load caps on the far sides
    ('Y_RP', 13.5, -1.0, 0), ('C_XIN', 13.5, 1.6, 0), ('C_XOUT', 17.2, -1.85, 0), ('R_XOUT', 8.0, -1.8, 90),
    # west, south of the USB 27R (graft): QSPI_SS (75) out west to its pull-up and the BOOTSEL 1k;
    # IOVDD 76 reaches its capacitor through the ring
    ('C_QSPI', -11.6, 1.1, 0), ('R_SS', -11.6, 2.7, 0), ('R_BSEL', -11.6, 4.3, 180),
    ('C_IOV76', -11.6, -0.5, 0), ('C_IOBULK', -14.6, 1.9, 90),
    # SWD / RUN pads north-east, the RUN pull-up beyond TP_RUN
    ('TP_RUN', 4.2, -13.6, 0), ('TP_SWDIO', 6.8, -13.6, 0), ('TP_SWCLK', 9.4, -13.6, 0), ('TP_GND', 12.0, -13.6, 0),
    ('R_RUN', 4.2, -16.5, 270),            # pad 2 (RUN) south toward TP_RUN, pad 1 (+3V3_RP) north
    ('TP_DVDD', -9.4, -9.4, 0),
]


def rp_macro(place, rx, ry, rot=90):
    rr = rot - 90
    place('U_RP', rx, ry, rot)
    for key, dx, dy, r in RP_MACRO:
        ox, oy = rot_pt(dx, dy, rr)
        place(key, rx + ox, ry + oy, (r + rr) % 360)


# the series resistors (design.BUS order = GPIO order): two blocks of staggered pairs, pad 1 south
import design as _D
ADDR_BLOCK = [k for k in ('R_' + rn[3:] for cn, rn, g, rv in _D.BUS if g <= 13)]
DATA_BLOCK = [k for k in ('R_' + rn[3:] for cn, rn, g, rv in _D.BUS if g >= 14)]
R_PITCH = 1.27
R_ROWS = (106.4, 102.9)              # lower (even index) / upper row centres
# (the blocks' x: of seven trial placements round these, this one routes with no bus line over 7 vias)


def do_placement(place):
    # ---------------- edge ----------------
    place('J_EDGE', XC, Y_EDGE, 0)

    # ---------------- RP2354B ----------------
    rx, ry, rr = RP
    rp_macro(place, rx, ry, rr)
    # graft parts (L_RP C_VREGIN C_DVBULK C_AVDD R_AVDD R_USBP R_USBM C_OTP) are placed by
    # gen_pcb.graft_parts() from tools/rpi_core_graft.sexpr, relative to U_RP

    # ---------------- the 28 series resistors ----------------
    for i, k in enumerate(ADDR_BLOCK):            # GP0 .. GP13, west to east, centred under GP4-13
        place(k, 80.3 + R_PITCH * i, R_ROWS[i % 2], 90)
    for i, k in enumerate(DATA_BLOCK):            # GP14 .. GP28, west to east
        place(k, 103.1 + R_PITCH * i, R_ROWS[i % 2], 90)
    place('R_VPBPD', 121.4, 98.8, 0)              # pin B's pull-down beside its 1k (the block's east end)

    # the RP's LED and the bring-up pads
    place('D_LED', 116.2, 92.2, 0)
    place('R_LED', 116.2, 94.0, 0)
    place('TP_SELFTEST', 116.0, 77.0, 0)
    place('TP_DBGTX', 95.8, 73.6, 0)
    place('TP_DBGRX', 93.2, 73.6, 0)

    # ---------------- top-right: ESP32-S3 ----------------
    place('U_S3', S3[0], S3[1], 0)                # antenna (local y < -6.75) flush with the top edge
    place('C_S3', 109.2, 56.0, 90)                # its 100 nF at the 3V3 pin (2), west of the module
    place('C_S3BULK', 109.2, 60.0, 90)
    place('R_EN', 109.2, 64.2, 90)
    place('C_EN', 109.2, 67.6, 90)

    # ---------------- top-left: USB-C, its ESD and Rd, the CP2102N ----------------
    # HRO's recommended layout puts the PCB edge 5.79 mm in front of the locating pegs: origin =
    # top edge + 3.2 at rot 180, the face 0.46 mm past the edge (Studio II's reference, PR #61)
    place('J_USB', 76.0, Y0 + 3.2, 180)
    place('R_CC1', 83.4, 47.6, 90)
    place('R_CC2', 85.2, 47.6, 90)
    place('U_ESD', 84.4, 52.4, 90)
    place('C_VBUS', 87.6, 52.6, 90)
    place('C_VBUSHF', 89.4, 52.6, 90)
    place('U_UART', 91.0, 57.6, 0)                # D+/D- (pins 4/5, west side) facing the USBLC6's flow-through pins
    place('C_UART', 86.6, 59.4, 90)               # at VDD / VREGIN (pins 6 / 7, west side)
    place('C_UARTBULK', 86.6, 62.8, 90)
    place('R_CPRST', 95.8, 61.6, 90)
    place('R_VBSH', 91.2, 47.8, 90)
    place('R_VBSL', 93.0, 47.8, 90)
    place('U_AUTOPROG', 96.2, 56.4, 90)

    # ---------------- top-middle: two buttons, the WS2812 ----------------
    place('SW_S3EN', 103.6, 56.6, 90)
    place('SW_S3BOOT', 103.6, 65.0, 90)
    place('D_WS', 98.8, 66.6, 0)
    place('R_WS', 98.8, 69.2, 0)
    place('C_WS', 95.8, 66.6, 90)

    # ---------------- left edge: microSD ----------------
    place('J_SD', X0 + 9.8, 63.6, 270)            # slot west, face 0.5 mm inside the edge (TF-015 drawing)
    place('RN_SD', 86.6, 68.4, 0)
    place('R_SDCD', 86.8, 72.2, 0)
    place('C_SD', 90.4, 69.4, 90)

    # ---------------- west: buttons, the RP's LDO, the power mux ----------------
    place('SW_RESET', 73.4, 79.2, 0)
    place('SW_BOOTSEL', 73.4, 85.6, 0)
    place('D_RST', 80.6, 76.2, 0)
    place('R_RUNCTL', 80.4, 79.6, 90)
    place('R_BSELCTL', 80.2, 83.6, 90)
    place('U_LDO', 85.0, 77.0, 90)
    place('C_LDOIN', 87.6, 75.2, 90)
    place('C_LDOOUT', 87.6, 79.0, 90)
    place('TP_3V3', 84.2, 81.4, 0)
    # the TPS2116 at rot 270: its north row PR1 / VIN1 / VOUT / GND faces the VBUS side and VOUT's +5V
    # via (gen_pcb.mux_link, just above the CONS_5V island); its south row MODE / VIN2 / VOUT / ST
    # sits on the island, VIN2's via straight down into it
    place('U_MUX', 78.0, 90.6, 270)
    place('C_MUXV1', 75.6, 90.6, 90)
    place('R_PRH', 73.6, 92.2, 90)
    place('R_PRL', 71.8, 92.2, 90)
    place('C_5VBULK', 81.6, 87.6, 90)
    place('TP_5V', 82.4, 90.6, 0)
    place('TP_VBUS', 81.6, 93.0, 0)
    place('C_CONS', 74.0, 95.2, 0)
    place('C_CONSHF', 74.0, 97.0, 0)
    place('TP_CONS5V', 78.4, 95.2, 0)
    place('R_VSH', 78.6, 97.6, 0)
    place('R_VSL', 78.6, 99.4, 0)
    place('C_VS', 78.6, 101.2, 0)

    # ---------------- east: the S3 side's 3.3 V buck under the module ----------------
    place('U_BUCK', 124.0, 78.6, 0)
    place('C_BST', 124.0, 75.8, 0)
    place('L_BUCK', 128.8, 78.8, 0)
    place('C_BIN', 120.6, 78.4, 90)
    place('C_BINHF', 121.0, 82.0, 0)
    place('C_BOUT1', 128.8, 83.2, 0)
    place('C_BOUT2', 125.0, 83.2, 0)
    place('TP_3V3S3', 128.6, 86.4, 0)


JLC_ORDER = ((119.0, 73.4), 1.0)          # centre, text height (mm): JLCPCB's order number, clear of parts (under the S3)
FIDUCIALS = [('FID1', 71.6, 74.6), ('FID2', 128.4, 89.8), ('FID3', 98.6, 61.0)]
