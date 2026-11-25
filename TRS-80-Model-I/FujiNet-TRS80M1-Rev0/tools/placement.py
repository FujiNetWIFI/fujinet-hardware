"""Component placement for gen_pcb.py: key -> (x, y, rot), and the board frame the floorplan owns.
Board x 50..150, y 40..116 (tools/header_geom.py: 100 x 76 mm, an M3 hole in each corner).  Top view
(F.Cu, every part), y down, rotation CCW.  Parts are named by their design.py key, so a reference change
never moves a part.

  west edge     the 2x20 right-angle box header, its mouth flush with the edge, pin 1 at its south end;
                its odd pins on the inboard row
  bus column    every buffer within ~15 mm of its header pins, in the header's order north to south:
                the A0-A7 receiver (header pins 25-40) north, the data transceiver (18-32) with its 47R
                and pull-up arrays in the middle, the A8-A15 receiver (4-17) south; the two Schmitt
                receivers and the INT / WAIT driver beside them, the OE gate by the data buffer's /OE
  centre        the RP2354B at rotation 0 -- its bus pins on its west and south sides, toward the buffers
                (FujiNet-StudioII / O2 Rev0's macro, turned with it: decoupling east, crystal south, the
                QSPI / BOOTSEL corner north, Raspberry Pi's regulator corner north-east)
  east edge     the ESP32-S3 at rotation 270, its antenna flush with the east edge over a strip that is
                copper-free on every layer (its footprint's keep-out, +-24 mm along the edge)
  north edge    USB-C, its ESD / CC / fuse, the CP2102N block; the S3's buck east of them
  south edge    microSD (slot south) under the S3, the DIP switches, the (unfitted) logic-analyser header
"""
import math
import header_geom as HG

X0, Y0 = 50.0, 40.0
X1, Y1 = X0 + HG.BOARD_W, Y0 + HG.BOARD_H
XC, YC = (X0 + X1) / 2, (Y0 + Y1) / 2
HOLES = [(X0 + HG.HOLE_IN, Y0 + HG.HOLE_IN, HG.HOLE_D), (X1 - HG.HOLE_IN, Y0 + HG.HOLE_IN, HG.HOLE_D),
         (X0 + HG.HOLE_IN, Y1 - HG.HOLE_IN, HG.HOLE_D), (X1 - HG.HOLE_IN, Y1 - HG.HOLE_IN, HG.HOLE_D)]
HDR = (X0 + HG.HDR_MOUTH - HG.HDR_OVERHANG, YC, HG.HDR_ROT)   # the header: its mouth on the west edge
RP = (104.0, 77.0, 0)                # RP2354B centre + rotation (gen_pcb turns the graft with it)
S3 = (X1 - 12.85, 80.0, 270)         # ESP32-S3 module centre: its antenna end flush with the east edge


def rot_pt(x, y, a):
    """gen_pcb.rot_pt: KiCad's rotation (CCW on screen, y down)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


def hdr_pin(n):
    """Board position of header pin n (tools/make_fp_m1.py: pin 2k+1 at (24.13 - 2.54k, -1.27), 2k+2 at
    (24.13 - 2.54k, +1.27) in the footprint)."""
    k = (n - 1) // 2
    lx, ly = 24.13 - HG.PITCH * k, (-1.27 if n % 2 else 1.27)
    dx, dy = rot_pt(lx, ly, HDR[2])
    return HDR[0] + dx, HDR[1] + dy


# In2 islands (absolute polygons; the base of In2 is +5V).
# +3V3_RP: the RP, its ring's corner vias, its caps, the graft corner, the LDO, and every bus buffer
RP_ISLAND = [(65.5, 46.0), (118.0, 46.0), (118.0, 112.0), (65.5, 112.0)]
# +3V3 (the buck: S3, CP2102N, microSD): the north-east and the S3's column down to the microSD
S3_ISLAND = [(118.5, Y0), (X1, Y0), (X1, Y1), (118.5, Y1)]

# The RP2354B macro (FujiNet-StudioII / O2 Rev0's), relative to the RP centre, for the RP at rotation 90;
# rp_macro() turns it with the RP.  At rotation 0 (this board): west 1-20 N->S (GP4-7, IOVDD 5, GP8-11,
# DVDD 10, GP12-15, IOVDD 15, GP16-20: all bus), south 21-40 W->E (GP21-23, IOVDD 24, GP24-27, IOVDD 29,
# XIN, XOUT, DVDD 32, SWCLK, SWDIO, RUN, GP28-32), east 41-60 S->N (IOVDD 41, GP33-35 DIPs, GP36-39,
# GP40, IOVDD 50, DVDD 51, GP41-43, GP44 / 45 debug UART, GP46, GP47 LED, ADC_AVDD, IOVDD 60), north
# 61-80 E->W (the regulator 61-65, USB 66 / 67, OTP 68, QSPI_IOVDD 69, QSPI 70-74, QSPI_SS 75,
# IOVDD 76, GP0-3).  Every supply pin stubs inward to the +3V3_RP / DVDD rings under the package
# (gen_pcb.rp_support).
RP_MACRO = [
    ('C_IOV60', -5.0, -7.4, 90), ('C_ADC', -3.3, -7.4, 90), ('C_DV51', -0.6, -7.0, 90), ('C_IOV50', 0.4, -7.0, 90),
    ('C_IOV41', 3.8, -7.4, 90),
    ('C_DV10', -1.6, -10.0, 90), ('C_IOV5', 2.2, -10.4, 90), ('C_IOV15', 4.0, -10.4, 90),
    ('C_IOV24', 9.6, -4.6, 0), ('C_IOV29', 9.6, -6.2, 0), ('C_DV32', 9.6, -7.8, 0),
    ('Y_RP', 13.5, -1.0, 0), ('C_XIN', 13.5, 1.6, 0), ('C_XOUT', 17.2, -1.85, 0), ('R_XOUT', 8.0, -1.8, 90),
    ('C_QSPI', -11.6, 1.1, 0), ('R_SS', -11.6, 2.7, 0), ('R_BSEL', -11.6, 4.3, 180),
    ('C_IOV76', -11.6, -0.5, 0), ('C_IOBULK', -14.6, 1.9, 90),
    ('TP_RUN', 4.2, -13.6, 0), ('TP_SWDIO', 6.8, -13.6, 0), ('TP_SWCLK', 9.4, -13.6, 0), ('TP_GND', 12.0, -13.6, 0),
    ('R_RUN', 4.2, -16.5, 270),
    ('TP_DVDD', -9.4, -9.4, 0),
]


def rp_macro(place, rx, ry, rot=90):
    rr = rot - 90
    place('U_RP', rx, ry, rot)
    for key, dx, dy, r in RP_MACRO:
        ox, oy = rot_pt(dx, dy, rr)
        place(key, rx + ox, ry + oy, (r + rr) % 360)


def do_placement(place):
    # ---------------- the header ----------------
    place('J_M1', *HDR)

    # ---------------- RP2354B ----------------
    rx, ry, rr = RP
    rp_macro(place, rx, ry, rr)
    # the core rail's pad north of the macro's spot: its B.Cu link (gen_pcb.tp_dvdd_link) then clears
    # the regulator corner's GND vias
    place('TP_DVDD', 113.4, 66.9, 0)
    # SWD / RUN pads in a row south of the crystal (the macro's spot east of it walls SWCLK in between the
    # DIP lines and the debug UART: the 2026-11-24 placement variants)
    place('TP_RUN', 110.2, 93.6, 0)
    place('TP_SWDIO', 112.8, 93.6, 0)
    place('TP_SWCLK', 115.4, 93.6, 0)
    place('TP_GND', 118.0, 93.6, 0)
    # graft parts (L_RP C_VREGIN C_DVBULK C_AVDD R_AVDD R_USBP R_USBM C_OTP) are placed by
    # gen_pcb.graft_parts() from tools/rpi_core_graft.sexpr, relative to U_RP

    # ---------------- the bus column: arrays at x 68-71, buffers at x 76 ----------------
    # A0-A7 receiver, north (its header pins 25-40 span y 53.9-71.7); A side west, pin 2 (A2) north
    place('U_AL', 77.4, 60.4, 0)
    place('RN_AL1', 71.4, 58.4, 0)
    place('RN_AL2', 71.4, 62.4, 0)
    place('C_AL', 77.4, 55.4, 0)
    # the data transceiver, middle (18-32: y 64.0-81.8), turned round: B (the bus) west, pin 18 (D4) south
    place('U_DB', 78.0, 73.4, 180)
    place('RS_D1', 68.0, 75.4, 180)
    place('RS_D2', 68.0, 71.4, 180)
    place('RN_D1', 71.4, 75.4, 180)
    place('RN_D2', 71.4, 71.4, 180)
    place('C_DB', 75.6, 78.4, 0)               # at VCC (pin 20: south-west, the part turned round)
    place('U_OE', 84.6, 71.0, 0)
    place('C_OE', 84.6, 68.0, 0)
    place('R_DRIVE', 84.6, 76.0, 90)
    # A8-A15 receiver, south (4-17: y 81.8-99.6); A side west, pin 2 (A9) north
    place('U_AH', 77.4, 90.4, 0)
    place('RN_AH1', 71.4, 88.4, 0)
    place('RN_AH2', 71.4, 92.4, 0)
    place('C_AH', 77.4, 85.4, 0)
    # the Schmitt receivers: RD* IN* INTAK* (15, 19, 14) and SYSRES* OUT* WR* (2, 12, 13); INT* / WAIT*
    place('U_STB', 85.4, 83.6, 0)
    place('RN_STB', 85.4, 87.8, 90)
    place('C_STB', 85.4, 80.6, 0)
    place('U_STA', 77.4, 100.4, 0)
    place('RN_STA', 71.4, 100.4, 0)
    place('C_STA', 77.4, 96.6, 0)
    place('U_OD', 85.4, 64.2, 0)
    place('C_OD', 85.4, 61.8, 0)
    place('R_INTPU', 89.0, 63.2, 90)
    place('R_WAITPU', 89.0, 66.2, 90)
    place('C_BUFBULK', 82.6, 94.0, 90)

    # the logic-analyser header (not fitted), along the south edge
    place('J_LA', 67.6, 112.4, 90)

    # ---------------- RP side: DIP switches, the LED, debug-UART pads ----------------
    place('SW_DIP', 112.0, 104.6, 0)
    place('RN_DIP', 112.0, 96.6, 90)
    place('D_LED', 119.6, 72.6, 0)
    place('R_LED', 119.6, 74.4, 0)
    place('TP_DBGTX', 122.2, 76.4, 0)
    place('TP_DBGRX', 122.2, 79.0, 0)

    # ---------------- RP buttons, RUN / BOOTSEL from the S3, the LDO ----------------
    place('SW_RESET', 93.4, 104.6, 0)
    place('SW_BOOTSEL', 101.6, 104.6, 0)
    place('D_RST', 96.4, 97.4, 0)
    place('R_RUNCTL', 120.6, 86.2, 90)
    place('R_BSELCTL', 96.6, 60.4, 90)
    place('U_LDO', 90.6, 52.4, 0)
    place('C_LDOIN', 87.4, 52.4, 90)
    place('C_LDOOUT', 93.8, 52.4, 90)
    place('TP_3V3', 90.6, 56.4, 0)

    # ---------------- east: ESP32-S3 ----------------
    place('U_S3', *S3)                            # antenna (local y < -6.75) flush with the east edge
    place('C_S3', 142.4, 67.6, 90)
    place('C_S3BULK', 140.4, 67.6, 90)
    place('R_EN', 136.0, 67.6, 90)
    place('C_EN', 134.2, 67.6, 90)
    place('SW_S3EN', 127.0, 62.6, 0)
    place('SW_S3BOOT', 135.2, 62.6, 0)
    place('D_WS', 141.2, 59.4, 0)
    place('R_WS', 141.2, 61.6, 0)
    place('C_WS', 141.2, 57.4, 0)

    # ---------------- south-east: microSD under the S3 ----------------
    place('J_SD', 133.0, Y1 - 9.8, 0)             # slot south, face 0.5 mm inside the edge (TF-015 drawing)
    place('RN_SD', 121.2, 102.0, 90)
    place('R_SDCD', 119.8, 107.6, 90)
    place('C_SD', 121.2, 97.6, 90)

    # ---------------- north edge: USB-C, its ESD and Rd, the fuse, the CP2102N ----------------
    # HRO's recommended layout puts the PCB edge 5.79 mm in front of the locating pegs: origin =
    # edge + 3.2 at rot 180, the face 0.46 mm past the edge (Studio II's reference, PR #61)
    place('J_USB', 106.0, Y0 + 3.2, 180)
    place('R_CC1', 99.6, 47.6, 90)
    place('R_CC2', 112.4, 47.6, 90)
    place('U_ESD', 106.0, 51.4, 0)
    place('C_VBUS', 101.4, 51.4, 90)
    place('C_VBUSHF', 99.6, 51.4, 90)
    place('F_VBUS', 103.4, 55.0, 0)
    place('TP_VBUS', 99.0, 55.0, 0)
    place('U_UART', 113.6, 55.0, 0)
    place('C_UART', 109.4, 55.0, 90)
    place('C_UARTBULK', 109.4, 58.4, 90)
    place('R_CPRST', 117.6, 59.4, 90)
    place('R_VBSH', 115.6, 47.6, 90)
    place('R_VBSL', 117.4, 47.6, 90)
    place('U_AUTOPROG', 119.6, 55.0, 90)

    # ---------------- north-east: the S3's buck, +5V bulk ----------------
    place('C_5VBULK', 124.6, 45.0, 90)
    place('TP_5V', 121.6, 45.0, 0)
    place('U_BUCK', 129.0, 47.4, 0)
    place('C_BIN', 126.2, 50.4, 90)
    place('C_BINHF', 128.0, 51.0, 90)
    place('L_BUCK', 134.2, 47.4, 0)
    place('R_FBH', 131.0, 51.6, 90)
    place('R_FBL', 132.8, 51.6, 90)
    place('C_BOUT1', 138.6, 46.0, 90)
    place('C_BOUT2', 140.6, 46.0, 90)
    place('TP_3V3S3', 138.0, 50.6, 0)


    # layout experiments: PLACEMENT_OVERRIDES='{"KEY": [x, y, rot], ...}' moves parts after the table above
    import json, os
    for key, (x, y, r) in json.loads(os.environ.get('PLACEMENT_OVERRIDES', '{}')).items():
        place(key, x, y, r)


JLC_ORDER = ((131.0, 93.2), 1.0, 'B')     # centre, text height (mm), side: JLCPCB's order number, on B.Silk between the S3 and the microSD
FIDUCIALS = [('FID1', 58.0, 112.0), ('FID2', 128.0, 56.4), ('FID3', 92.0, 44.0)]
