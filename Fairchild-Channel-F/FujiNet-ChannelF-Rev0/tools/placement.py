"""Component placement for gen_pcb.py: design.py key -> (x, y, rot), and the board frame the
floorplan owns (the original shell's boss holes, the In2 power islands).  KiCad frame: top view of
the component side (F.Cu, which faces UP in the console), y down, rotation CCW.  The insertion edge
is y = 150, the key slot x = 100; the 22 fingers are on B.Cu, west to east (tools/edge_geom.py):

  x  69.5  72.1   GND GND (1, 2)          x  74.6  77.1   D0 D1 (3, 4)       x  79.7  /INTREQ (5)
  x  82.2  84.8  87.3   ROMC0-2 (6-8)     x  89.8  D2 (9)   x  92.4  ROMC3 (10)   x  94.9  D3 (11)
     -- key slot, x 99.2-100.8, 12.58 deep --
  x 105.1  ROMC4 (12)   x 107.6  PHI (13)  x 110.2  D4 (14)  x 112.7  WRITE (15)
  x 115.2 117.8 120.3   D5 D6 D7 (16-18)  x 122.9 125.4  console +5V (19, 20)   x 127.9 NC  x 130.5 +12V

The board (gen_pcb.OUTLINE, edge_geom.py): the 68.3 mm tab, straight for 30 mm (no parts on it),
a 45-degree taper to the 77 mm body, 131.5 mm overall; four 5.6 mm holes on the original shell's
bosses.  The ESP32-S3's antenna, the USB-C and the microSD sit on the trailing (grip) edge, which
stays outside the console.

The co-design (docs/floorplan-study.md): the two SN74LVC4245A stand side by side over the bus
fingers at rotation 90 (A row south toward the fingers, B row north), the data one west, the
control one east; the RP2040 at rotation 90 straight north of them, its GP0-GP11 along its south
side and GP12-GP15 up its east side, so B row -> RP crosses nothing (design.py's CTRL_CH order).
The RP2040 macro (decoupling, core regulator copper, flash, crystal, USB series resistors) is the
routed atari2600-rev0 board's, drawn at rotation 90.
"""
import math, os

VARIANT = os.environ.get('PLACE_VARIANT', 'P1')

# ---- board frame ------------------------------------------------------------
XC, Y_EDGE = 100.0, 150.0


def rot_pt(x, y, a):
    """gen_pcb.rot_pt: KiCad's rotation (CCW on screen, y down)."""
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


# ---------------------------------------------------------------------------
# the RP2040 macro, relative to the RP centre, for the RP at rotation 90 (pins: south 1-14 W->E, east
# 15-28 S->N, north 29-42 E->W, west 43-56 N->S; 0.4 mm pitch, rows at 3.45 from the centre)
RP_MACRO = [
    # the north-west corner: DVDD leaves the ring's inner band diagonally between pins 42 and 43 (F.Cu,
    # gen_pcb.rp_dvdd_link) straight into the VREG_VOUT 1 uF and the two DVDD 100 nF in a row just outside
    # the package; VREG_VIN 44 + ADC_AVDD 43 (strapped) into their 1 uF west of them; IOVDD 42's 100 nF
    # north of it.  The USB pair runs west between this group and the west row, through its 27R
    ('C_IOV42', -2.6, -6.6, 90),
    ('C_VREGOUT', -4.9, -5.7, 90), ('C_DV50', -6.7, -5.7, 90), ('C_DV23', -8.5, -5.7, 90),
    ('C_VREGIN', -6.6, -3.3, 180),
    # the two 27R in line with the pair, close to the chip (design guide 2.4), staggered so their bodies clear
    ('R_USBM', -6.4, -1.7, 0), ('R_USBP', -9.6, -0.7, 0),
    # the west row (atari2600-rev0's DVDD row): USB_VDD 48 / IOVDD 49 (strapped, one via), ADC_AVDD and
    # the bulk on the +3V3_RP island; the flash south-west, its QSPI lines diagonal under the row
    ('C_ADC', -8.8, 1.8, 90), ('C_USBV', -10.6, 1.8, 90), ('C_IOV49', -12.4, 1.8, 90), ('C_IOBULK', -14.2, 1.8, 90),
    ('U_FLASH', -9.4, 9.6, 90), ('C_FLASH', -13.4, 6.2, 90),
    ('R_SS', -15.8, 12.6, 90), ('R_BSELCTL', -14.0, 12.6, 90), ('R_BSEL', -15.8, 16.0, 90),
    ('TP_BOOTSEL', -18.4, 12.6, 0),
    # the bus side (south): IOVDD 1 and 10 drop through locked vias in the ring's south band
    # (gen_pcb.rp_support); their 100 nF sit west of the data fan-in on the +3V3_RP island
    ('C_IOV1', -4.6, 5.7, 90), ('C_IOV10', -4.6, 8.9, 90),
    # north: IOVDD 33; the LED line leaves north from GP25 (pin 37)
    ('C_IOV33', 1.0, -6.6, 90),
    # east: XIN (20) runs straight out on F.Cu to the crystal; XOUT (21) drops through a via under the
    # package (gen_pcb.rp_support) and reaches its 1k on B.Cu; IOVDD 22's via 2 mm out between them and
    # SWCLK; SWD / RUN / GP16 / GP17 (24-28) escape east and turn north, DIR (18) east and south
    # outside the control lines (15-17), which come in from the south-east
    ('Y_RP', 9.0, -0.2, 0), ('C_XIN', 7.9, 3.1, 270), ('C_XOUT', 10.1, -3.5, 90), ('R_XOUT', 12.8, -1.05, 180),
    ('C_IOV22', 13.6, 2.2, 90),
    ('R_RUN', 9.4, -7.0, 0), ('R_RUNCTL', 9.4, -8.8, 0),
    # the escapes turn north with GP17 innermost, SWCLK outermost: their pads in the same order west to east
    ('TP_RUN', 14.0, -10.6, 0), ('TP_SWDIO', 16.6, -10.6, 0), ('TP_SWCLK', 19.2, -10.6, 0), ('TP_GND', 21.8, -10.6, 0),
    ('TP_GP17', 5.6, -12.4, 0),
]


def rp_macro(place, rx, ry, rot=90):
    rr = rot - 90
    place('U_RP', rx, ry, rot)
    for key, dx, dy, r in RP_MACRO:
        ox, oy = rot_pt(dx, dy, rr)
        place(key, rx + ox, ry + oy, (r + rr) % 360)


def p1(place, fid):
    """P1: the translators over the bus fingers, the RP2040 north of them with a long, gentle fan-in,
    the power column east, the FujiNet half (S3 west, microSD, USB-C east) along the grip edge, RESET
    and the LEDs between the S3 and the microSD."""
    rx, ry = 99.0, 90.0
    rp_macro(place, rx, ry, 90)
    # ---- the edge and the translators ----
    place('J_EDGE', XC, Y_EDGE, 0)
    place('U_DBUF', 97.5, 114.0, 90)
    place('C_DBUFA', 92.0, 117.0, 90)          # VCCA (pin 1, A row west end): pad 1 south
    place('C_DBUFB', 92.0, 110.6, 270)         # VCCB (24 / 23, B row west end): pad 1 north
    place('R_DIR', 92.0, 113.8, 90)            # DIR pull-up beside DIR (pin 2)
    place('TP_DIR', 89.4, 113.8, 0)
    place('U_CBUF', 108.5, 114.0, 90)
    place('C_CBUFA', 102.6, 117.0, 90)
    place('C_CBUFB', 102.6, 110.6, 270)
    place('R_A8', 113.6, 117.0, 90)            # spare A8 pull-down, at the A row's east end
    place('TP_WRITE', 113.0, 106.0, 0)
    place('TP_PHI', 115.6, 106.0, 0)
    # /INTREQ: the open-drain FET over finger 5, its gate line from GP16
    place('Q_INT', 80.0, 116.4, 0)
    place('R_INTPD', 84.0, 116.4, 90)
    # ---- power: console 5V in over fingers 19 / 20, the OR diodes, the buck and the RP's LDO ----
    place('D_CONS', 124.2, 115.4, 270)         # anode (CONS_5V) south toward the fingers
    place('C_CONSHF', 120.8, 117.0, 90)
    place('C_5VBULK', 127.0, 108.0, 90)
    place('U_LDO', 112.0, 99.0, 180)           # input east (+5V island), output west (+3V3_RP island)
    place('C_LDOIN', 115.6, 99.0, 90)
    place('C_LDOOUT', 110.0, 96.0, 0)
    place('TP_3V3RP', 108.4, 78.0, 0)
    # the buck's input loop closes on F.Cu: the 100 nF and both 22 uF stacked under VIN / GND, +5V and GND
    # each a locked 0.6 mm rail down the stack (gen_pcb.buck_loop); SW straight east to the inductor
    place('U_BUCK', 128.0, 68.4, 0)
    place('C_BINHF', 128.0, 70.9, 0)
    place('C_BIN1', 128.0, 73.0, 0)
    place('C_BIN2', 128.0, 75.4, 0)
    place('C_BST', 131.0, 66.6, 90)
    place('L_BUCK', 134.2, 67.0, 90)
    place('C_BOUT1', 132.0, 61.4, 90)
    place('C_BOUT2', 134.6, 61.4, 90)
    place('TP_3V3', 129.4, 61.4, 0)
    place('TP_5V', 122.6, 75.4, 0)
    # ---- the FujiNet half along the grip edge: S3 west (antenna flush), microSD, USB-C east ----
    place('U_S3', 81.5, 31.5, 0)
    place('C_S3', 70.6, 27.6, 90)
    place('C_S3BULK', 68.2, 26.8, 90)
    place('R_EN', 69.4, 41.6, 90)
    place('C_EN', 69.4, 45.0, 90)
    place('J_SD', 115.3, 28.5, 180)          # its west shell pad 1.4 mm clear of the antenna keep-out
    place('RN_SD', 106.0, 40.4, 90)
    place('R_SDCD', 108.6, 40.4, 90)
    place('C_SD', 111.0, 40.4, 90)
    place('J_USB', 131.0, 23.5, 180)
    # the USB-C's lines leave south through the 6 mm corridor between the microSD and the boss hole's
    # copper keep-out (H4): no parts in it (V7 left UBRG_DM open there); the ESD diodes, CC resistors and
    # VBUS capacitors sit in a row just below it, on the way to the CP2102N
    place('D_ESDP', 125.6, 41.8, 180)
    place('D_ESDM', 125.6, 43.4, 180)
    place('R_CC1', 122.6, 39.8, 0)
    place('R_CC2', 122.6, 41.6, 0)
    place('D_ESDV', 133.2, 41.0, 90)
    place('C_VBUS', 135.0, 41.0, 90)
    place('C_VBUSHF', 136.7, 41.0, 90)             # courtyard 1.07 mm inside the long side (rails)
    place('U_UART', 131.0, 46.0, 0)
    place('C_UART', 126.6, 47.6, 90)
    place('C_UARTBULK', 124.8, 47.6, 90)
    place('R_VBSH', 129.2, 51.4, 0)
    place('R_VBSL', 132.6, 51.4, 0)
    place('R_CPRST', 125.8, 51.4, 0)
    # the VBUS OR diode below the divider, VBUS pad north, +5V pad south toward the +5V island;
    # its courtyard 1.05 mm inside the body's long side (at 136.4 / 47.4 it was 0.35 mm: rails)
    place('D_VBUS', 135.7, 55.9, 90)
    place('U_AUTOPROG', 121.0, 46.0, 0)
    # RESET between the S3 and the microSD, the two LEDs under it: reachable / visible at the grip end
    place('SW_RESET', 99.0, 30.0, 0)
    place('D_RST', 96.0, 35.6, 0)
    place('D_WS', 95.4, 39.4, 0)
    place('C_WS', 98.2, 39.4, 90)
    place('R_WS', 93.4, 42.6, 90)
    place('D_LED', 101.6, 39.4, 180)
    place('R_LED', 101.6, 42.8, 90)
    # the other buttons under the S3 (pinholes in the shell)
    place('SW_S3EN', 72.0, 52.4, 0)
    place('SW_S3BOOT', 81.5, 52.4, 0)
    place('SW_BOOTSEL', 91.0, 52.4, 0)
    fid += [('FID1', 64.4, 60.0), ('FID2', 135.6, 84.0), ('FID3', 64.4, 100.0)]


VARIANTS = {'P1': p1}

# board frame owned by the floorplan (gen_pcb reads these): the original shell's bosses (edge_geom)
import edge_geom as _EG
HOLES = [(XC + sx * _EG.HOLE_DX, Y_EDGE - hy, _EG.HOLE_D) for hy in _EG.HOLE_Y for sx in (-1, 1)]
HOLE_KEEP = 4.8          # no parts within this radius of a hole centre (the boss and its base)
HOLE_CU = 3.4            # no copper within this radius
# In2 power islands (absolute), highest priority first; the rest of In2 is +3V3 (the S3 half)
CONS5V_POLY = [(84.0, 114.6), (130.0, 114.6), (130.0, 140.0), (84.0, 140.0)]      # the translators' A halves + D_CONS
RP_POLY = [(76.0, 76.0), (112.0, 76.0), (112.0, 114.6), (76.0, 114.6)]            # RP, flash, the B halves
FIVE_V_POLY = [(112.0, 64.6), (139.0, 64.6), (139.0, 114.6), (112.0, 114.6)]      # the power column
LABEL = ((100.0, 75.0), (34.0, 22.0))     # shell label recess: centre (board x, y), size (w, h)
TITLE_XY = (82.0, 66.0)
JLC_ORDER = ((86.0, 72.0), 1.0)          # centre, text height (mm): clear of parts and silk
RP_ROT = 90


def do_placement(place, fiducials):
    placed = set()

    def pl(key, *a):
        placed.add(key)
        place(key, *a)
    VARIANTS[VARIANT](pl, fiducials)
    if os.environ.get('PARK'):           # study only: park parts a variant does not place yet
        import design as D
        x, y = 64.0, 60.0
        for p in D.PARTS:
            if p.key not in placed:
                place(p.key, x, y, 0)
                x += 3.6
                if x > 136:
                    x, y = 64.0, y + 2.6
