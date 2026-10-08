"""Sega Master System cartridge edge and lower-board geometry: the one place these numbers live.

make_edge_fp.py (footprint), gen_pcb.py (outline, finger stubs, the SRAM0 fan-in),
check_nets.py and audit/edge_orientation.py (assertions), audit/check_gerbers.py (the fab
zips) and gen_pcb.write_case_anchors (shell) all import this.

Frame: x = 0 at the tab centre, y = distance IN from the insertion edge (mm, +y into the board).
Seen from F.Cu (the component side) with the fingers down, +x is right (east).

The edge (verified 2026-10-06, sources in audit/edge_orientation.py):
  * 25 positions at 2.54 mm per face; position k carries pin 2k-1 on B.Cu directly behind pin 2k
    on F.Cu;
  * the EVEN pins are on F.Cu, the component side, which faces the label and the console's
    front; pins 1 / 2 at the right (+x) seen from F.Cu with the fingers down;
  * the pin order is the JEDEC 32-pin memory pinout unrolled (A15 A12 A7..A0 D0-D2 GND D3-D7
    /CE A10 A11 A9 A8 A13 A14 west to east), so an AS6C4008 standing in the classic ROM spot
    takes A0-A12 and D0-D7 without one crossing (gen_pcb.sram0_fanin).
"""

PITCH = 2.54
N_POS = 25                       # finger positions per face


def pos_x(k):
    """Centre x of position k (1..25: pins 2k-1 / 2k), pins 1 / 2 east."""
    return round((N_POS - 1) * PITCH / 2 - (k - 1) * PITCH, 3)


def pin_pos(pin):
    return (pin + 1) // 2


def pin_x(pin):
    """Centre x of edge pin 1..50."""
    return pos_x(pin_pos(pin))


def pin_face(pin):
    return 'F' if pin % 2 == 0 else 'B'


# fingers: original 1.65-1.76 wide, raphnet 1.75, barbeque / reidrac 1.70; copper from about
# 0.5-1.25 to 9.5-10.1 above the edge on every source -> 0.75..9.5 here
FINGER_W = 1.75
LAND_Y0, LAND_Y1 = 0.75, 9.5     # copper, distance in from the insertion edge
MASK_Y1 = 10.0                   # one mask window per face, edge .. here

# the connector tab: the original board's full width (66.0 x 40.1 scan, raphnet 65.80,
# barbeque 65.8), 15 mm deep before the custom body widens (case/case-spec.md)
TAB_W = 65.8
TAB_D = 15.0                     # tab depth: insertion edge to the body's lower edge
BODY_W = 100.0                   # the custom body (shell inner width 105)
CH_TAB = 1.0                     # 45-degree chamfer on the tab's outer corners (insertion lead-in)

THICKNESS = 1.6                  # every open SMS cart design uses 1.6 (no original measured: VERIFY)
FINGER_EDGE_CLEAR = 0.5          # DRU: finger copper to Edge.Cuts (fingers start 0.75 in)

# finger field: each finger's stub leaves it here; no tracks / vias / pour on F/B below the
# body and no inner copper anywhere in the tab (gen_pcb)
STUB_TOP = TAB_D + 1.0           # stubs end 1 mm inside the body


assert pin_x(1) > 0 > pin_x(50) and pin_x(1) == pin_x(2)
assert abs(pin_x(1) - 30.48) < 1e-9 and abs(pin_x(49) + 30.48) < 1e-9
assert pin_face(2) == 'F' and pin_face(1) == 'B'
assert TAB_W / 2 - (abs(pin_x(1)) + FINGER_W / 2) > 1.0
assert MASK_Y1 > LAND_Y1 and STUB_TOP > LAND_Y1
