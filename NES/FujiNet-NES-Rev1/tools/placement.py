"""Component placement for gen_pcb.py: ref -> (x, y, rot).  Board x 50..150,
y 30 (top edge) .. 125.5 (tab base); fingers on the tab below, insertion
edge y = 140.  Top view, y down, rotation CCW.

Pin 1 of the edge is EAST (label side), so the CPU bus fingers (2-15 front,
38-50 back: x 108.75..141.25) are on the east half and the PPU bus (21-33
front, 56-69 back: x 63.75..96.25) on the west half; the unused EXP fingers
(x 98.75..108.75) leave a free column between them.

Regions:
  south-east    RP-A (U1) at (120, 100) rot 90 over the CPU fingers: CPU A/D
                side faces them (south), M2/R/W//ROMSEL/IRQ/crystal/SWD east,
                the link + RP-B's SWD north, VREG/USB/QSPI west
  south-west    RP-B (U2) at (80, 100) rot 90 over the PPU fingers, the same
                drawing; the link leaves north, so the eleven link lines run
                as nested arcs over the gap (RP-B's LD pins are mirrored)
  the gap       both LDOs and the console-5V sense divider, above the EXP fingers
  west edge     console 5V P-FET and the CIClone at the +5V / CIC fingers
  north         ESP32-S3 (west), microSD (middle), USB-C + CP2102N + buck (east):
                Rev0's places, so the Rev0 shell still fits (case/board-anchors.scad)
  east edge     RESET / BOOTSEL buttons (Rev0's places)
Shell posts at (54.05, 92.2) / (145.95, 92.2) and the holes at (100, 72) /
(105.5, 62.5) are keep-clear (gen_pcb.KEEP_CLEAR).
"""
import design as D

RP_AT = {'rp_a': (120.0, 100.0), 'rp_b': (80.0, 100.0)}

# In4 +5V island (one polygon): the band south of y 86 -- the gap between the RPs, the
# P-FET and the LDO inputs -- and, north of it, the strip down the east edge for the
# buck input, the VBUS diode and the WS2812.  The RP islands (+3V3_RP, +3V3_RPB, RP +/-14)
# and the DVDD lobes win over it; everything else on In4 is +3V3.
ISLANDS_5V = [[(50.0, 86.0), (118.0, 86.0), (118.0, 64.0), (141.0, 64.0), (141.0, 48.0), (146.0, 48.0),
               (146.0, 86.0), (150.0, 86.0), (150.0, 125.5), (50.0, 125.5)]]

RING = 10.0

# The edge-bus via field (gen_pcb.bus_route), relative to the RP centre.  Every lane -- the west
# column's bus pins 77-80, the south row, the east column from 21 up to its last bus pin -- has a
# via in one of two rows, BUS_PITCH apart in boundary order: the south row's 0.4 mm pins spread
# about their middle, the columns' turn outward past their pad ends.
BUS_PITCH = 0.5
BUS_ROWS = (6.9, 7.8)       # the two via rows; lanes alternate
BUS_CAP_Y = 9.5             # an IOVDD lane's 100 nF: pad 1 0.12 mm clear of the neighbouring vias
BUS_CAP_GND = 11.1          # and its GND via, below pad 2
SOUTH = [k for k in range(1, 21) if k != 10]      # pin 10 (DVDD) goes inward


def bus_slot(num):
    """x of pin num's lane in the via field, from the RP centre."""
    k = int(num)
    if 77 <= k <= 80:
        return -5.7 - BUS_PITCH * (80 - k)
    if 21 <= k <= 40:
        return 5.7 + BUS_PITCH * (k - 21)
    # south: the least-squares spread of the pins to BUS_PITCH, in order.  The pins are evenly
    # spaced but for the DVDD gap, so it is one block: their mean offset
    px = [-3.8 + 0.4 * (q - 1) for q in SOUTH]
    t0 = sum(x - BUS_PITCH * i for i, x in enumerate(px)) / len(px)
    return round(t0 + BUS_PITCH * SOUTH.index(k), 4)


def place_rp(place, who, rx, ry):
    """The RP2354B and its local circuit (design.rp2354b), Rev0's drawing for both:
    refs in design order -- 8 IOVDD caps, QSPI, OTP, ADC, 10 uF, 4.7 uF VREG_VIN;
    3 DVDD + 4.7 uF core; 33R + 4.7 uF VREG_AVDD; L; Y; 2 x 15 pF; 1k."""
    U = D.ROLE_REF['rp_' + who]
    c0 = {'a': 1, 'b': 21}[who]
    C = lambda i: 'C%d' % (c0 + i)            # C(0..19)
    r_avdd, r_x = {'a': ('R1', 'R2'), 'b': ('R13', 'R14')}[who]
    L, Y = D.ROLE_REF['l_' + who], D.ROLE_REF['y_' + who]
    place(U, rx, ry, 90)
    # south: A/D pins; IOVDD 5 (x -2.2), DVDD 10 (-0.2), IOVDD 15 (+1.8).  gen_pcb.bus_route runs
    # every south pin out to the bus via field; an IOVDD lane ends at its via (the In4 island) and
    # its 100 nF stands right below it, in the lane's otherwise empty column, pad 1 toward the via
    place(C(0), rx + bus_slot(5), ry + BUS_CAP_Y, 270)     # IOVDD 5
    place(C(1), rx + bus_slot(15), ry + BUS_CAP_Y, 270)    # IOVDD 15
    # east: IOVDD 24 sits among the bus lanes (ROMSEL 23 / CA13 25), so its cap goes the same way;
    # IOVDD 29's stands east of the lanes, on the island
    place(C(2), rx + bus_slot(24), ry + BUS_CAP_Y, 270)    # IOVDD 24
    place(C(3), rx + 10.3, ry + 4.6, 270)                  # IOVDD 29 (y +0.6)
    # crystal block, planar: XIN (pin 30, southern lane) straight into Y's south-west pad and
    # its load cap below; XOUT (pin 31) straight into the 1k on the lane, XOUT_Y over Y's
    # north-west GND pad to the north-east pad
    place(Y, rx + RING + 4.0, ry, 0)
    place(C(18), rx + RING + 4.0, ry + 3.6, 270)   # XIN load
    place(C(19), rx + RING + 7.0, ry - 2.6, 90)    # XOUT_Y load
    place(r_x, rx + 9.0, ry - 0.7, 0)              # XOUT -> XOUT_Y
    # north: IOVDD 41 (x +3.8), 50 (+0.2), 60 (-3.8), ADC_AVDD 59 (-3.4).  The link leaves the
    # north row between x -1.4 and +3.4 (gen_pcb.link_route), so the IOVDD 41 / 50 caps stand
    # in the north-east corner, inside the innermost link arc, and reach their pins through the
    # island; the ADC_AVDD cap moves north-west, out of the way of RP-A's RP-B SWD / PA12 escapes
    place(C(4), rx + 4.5, ry - 9.6, 90)       # IOVDD 41
    place(C(5), rx + 6.0, ry - 9.6, 90)       # IOVDD 50
    place(C(6), rx - 4.4, ry - RING, 90)      # IOVDD 60
    place(C(10), rx - 6.2, ry - 7.8, 90)      # ADC_AVDD 59
    # west: VREG corner (61-65), USB 66/67, QSPI, IOVDD 76, A0-3; the DVDD lobe of the
    # In4 island spans x rx-16..rx-3.6, y ry-5.6..ry-1.6
    place(L, rx - 7.6, ry - 3.0, 0)           # core inductor: pad 2 (LX) east toward pin 63
    place(C(16), rx - 11.0, ry - 2.6, 180)    # core 4.7 uF
    place(C(15), rx - 14.2, ry - 2.6, 180)    # DVDD 100 nF x3 in the lobe
    place(C(13), rx - 8.6, ry - 4.8, 180)
    place(C(14), rx - 11.8, ry - 4.8, 180)
    place(C(12), rx - RING - 4.4, ry - 0.6, 180)  # VREG_VIN 4.7 uF on the RP island
    place(r_avdd, rx - 10.5, ry - 11.0, 0)    # 33R rail -> VREG_AVDD
    place(C(17), rx - 7.2, ry - 11.0, 0)      # VREG_AVDD 4.7 uF
    place(C(9), rx - RING - 0.6, ry + 2.8, 180)   # USB_OTP_VDD (pin 68)
    place(C(8), rx - RING - 0.6, ry + 4.5, 180)   # QSPI_IOVDD (pin 69)
    place(C(7), rx - RING - 0.6, ry + 7.9, 180)   # IOVDD 76
    place(C(11), rx - RING - 4.4, ry + 4.5, 180)  # IO rail bulk 10 uF


def do_placement(place):
    # ---------------- edge ----------------
    place('J1', 100, 140, 0)

    # ---------------- RP-A (U1) ----------------
    rx, ry = RP_AT['rp_a']
    place_rp(place, 'a', rx, ry)
    # design.py: R8 = USB_DP series, R9 = USB_DM series.  D- (pin 66) is the northern pin
    place('R9', rx - RING - 0.6, ry - 0.6, 0)     # USB_DM series (pin 66 y -1.8)
    place('R8', rx - RING - 0.6, ry + 1.1, 0)     # USB_DP series (pin 67 y -1.4)
    place('R4', rx - RING - 0.6, ry + 6.2, 180)   # QSPI_SS pull-up
    place('R7', rx - RING - 4.4, ry + 1.1, 180)   # S3 IO5 -> QSPI_SS
    place('R5', rx - RING - 4.4, ry + 2.8, 180)   # QSPI_SS -> BOOTSEL button
    # test pads north-east, east of the corner caps, in the east side's pin order (RX -2.6 ..
    # SWCLK -1.0 turn north west to east), then M2 (pin 21, the southern end, the outermost run)
    for i, tp in enumerate(('TP6', 'TP5', 'TP4', 'TP2', 'TP1', 'TP7')):
        place(tp, rx + 8.0 + 2.5 * i, 91.5, 0)     # TP7 at x 140.5: clear of the shell post (145.95, r 3)
    place('TP3', rx + 21.5, ry - 0.5, 0)           # GND, below the RUN resistors
    place('R3', rx + 21.5, 95.2, 0)               # RUN pull-up, east of the pads
    place('R6', rx + 21.5, 96.9, 0)               # S3 IO4 -> RUN
    place('R10', rx + 19.5, ry + 3.4, 0)          # status LED (GP27, pin 28 at y +1.0)
    place('D2', rx + 19.5, ry + 5.2, 0)

    # ---------------- RP-B (U2) ----------------
    rx, ry = RP_AT['rp_b']
    place_rp(place, 'b', rx, ry)
    place('R16', rx - RING - 0.6, ry + 6.2, 180)  # QSPI_SS_B pull-up (R4's place on RP-A)
    for i, tp in enumerate(('TP12', 'TP11', 'TP10', 'TP9', 'TP8')):
        place(tp, rx + 8.0 + 2.5 * i, 91.5, 0)    # east side's order, as on RP-A
    place('R15', rx + 20.2, 94.0, 90)             # RPB_RUN pull-up, at the RP-A end

    # ---------------- the gap: LDOs, console-5V sense ----------------
    # each LDO's output cap stands on its own RP's island, its input cap on the +5V band; all north
    # of the bus channels (gen_pcb.bus_route, from y 111.6), which reach x 97 (RP-B) and 110 (RP-A)
    place('U9', 96.4, 108.5, 180)                 # RP-B LDO: VOUT west
    place('C62', 92.6, 108.5, 0)                  # +3V3_RPB out (RP-B island, x <= 94)
    place('C61', 96.4, 104.9, 0)                  # +5V in
    place('U8', 101.8, 108.5, 0)                  # RP-A LDO: VOUT east
    place('C60', 105.8, 108.5, 180)               # +3V3_RP out (RP-A island, x >= 106)
    place('C59', 101.8, 104.9, 0)                 # +5V in
    place('R11', 99.1, 116.5, 90)                 # CONS_5V -> PWR_OK, 2.2k
    place('R12', 99.1, 119.6, 90)                 # PWR_OK -> GND, 3.3k

    # ---------------- west edge: console 5V, CIClone ----------------
    place('Q1', 59.0, 119.5, 0)                   # P-FET at the +5V finger (36, x 55.75)
    place('C51', 61.4, 117.0, 90)                 # CONS_5V bypass (west of RP-B's bus channel, x >= 62.7)
    place('U3', 58.5, 110.0, 0)                   # CIClone (DNP) at the CIC fingers (x 58.75 / 61.25)
    place('C41', 62.6, 105.0, 90)
    place('TP13', 58.5, 104.6, 0)                 # CIC /RESET

    # ---------------- north-west: ESP32-S3 (Rev0) ----------------
    place('U4', 66.0, 43.0, 0)                    # antenna end at the top edge (y 30.15)
    place('C42', 53.5, 38.5, 90)                  # 22 uF bulk by the 3V3 pad (west edge)
    place('C43', 53.5, 42.0, 90)
    place('R17', 53.5, 45.2, 90)
    place('C44', 53.5, 48.4, 90)
    place('SW3', 56.5, 62.0, 0)                   # S3 EN
    place('SW4', 56.5, 72.0, 0)                   # S3 BOOT

    # ---------------- north-middle: microSD (Rev0) ----------------
    place('J2', 100.0, 40.0, 180)                 # slot at the top edge
    place('RN1', 89.0, 49.5, 90)
    place('R18', 111.2, 48.5, 90)
    place('C45', 111.2, 45.0, 90)

    # ---------------- north-east: USB-C, CP2102N, buck (Rev0) ----------------
    place('J3', 125.0, 33.2, 180)                 # face overhangs the top edge by 0.45 mm (HRO layout)
    place('R20', 118.0, 37.5, 90)                 # CC1 Rd
    place('R21', 132.0, 37.5, 90)                 # CC2 Rd
    place('D4', 121.5, 43.5, 0)                   # ESD D+
    place('D5', 128.5, 43.5, 0)                   # ESD D-
    place('D6', 115.5, 40.5, 90)                  # ESD VBUS
    place('C47', 134.5, 42.5, 90)                 # VBUS 1 uF
    place('C48', 136.5, 42.5, 90)                 # VBUS 100 nF
    place('U5', 125.0, 50.0, 270)                 # CP2102N: D+/D- face J3
    place('C49', 120.0, 48.0, 90)
    place('C50', 120.0, 51.0, 90)
    place('R22', 119.5, 54.5, 0)                  # VBUS sense divider
    place('R23', 119.5, 56.0, 0)
    place('R24', 131.5, 46.5, 90)                 # /RST pull-up
    place('U6', 131.0, 50.5, 0)                   # UMH3N
    place('U7', 139.5, 56.0, 180)                 # buck: VIN/EN/FB east toward the input caps on the +5V strip
    place('C52', 144.0, 53.0, 90)                 # buck in 22 uF x2 (+5V strip x 141..146)
    place('C53', 144.0, 56.5, 90)
    place('C55', 144.0, 60.2, 90)                 # buck in 100 nF
    place('C56', 138.0, 51.5, 0)                  # bootstrap
    place('L3', 134.0, 56.0, 0)                   # inductor: SW east, +3V3 west
    place('C57', 129.5, 54.0, 90)                 # buck out 22 uF x2 (+3V3 plane)
    place('C58', 129.5, 58.0, 90)
    place('D7', 140.0, 66.0, 0)                   # SS34 VBUS -> +5V (island)
    place('R25', 141.45, 59.6, 0)                 # VBUS (P-FET gate) pull-down
    place('C54', 144.6, 67.0, 90)                 # +5V bulk
    place('D3', 121.0, 66.0, 0)                   # WS2812 status LED (light pipe)
    place('R19', 117.5, 66.0, 0)
    place('C46', 124.5, 66.0, 0)

    # ---------------- east edge: buttons (Rev0) ----------------
    place('SW1', 143.5, 72.0, 0)                  # RESET
    place('D1', 137.0, 72.0, 0)                   # BAT54C
    place('SW2', 144.5, 112.0, 0)                 # BOOTSEL
