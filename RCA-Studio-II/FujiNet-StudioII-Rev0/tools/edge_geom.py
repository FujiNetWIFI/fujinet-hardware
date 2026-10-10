"""RCA Studio II cartridge edge geometry: the one place these numbers live.

make_edge_fp.py (footprint) and check_nets.py (assertions) import this.

Frame: x = 0 at the tab centre, y = distance IN from the insertion edge (mm, +y into the board).
Seen from F.Cu (the component side) with the fingers down, -x is left.

What is known (the bring-up plan's sources: EJK's Studio II schematic, Paul Robson's notes, the FliP
multicart; MAME rca/studio2.cpp): 22 contacts at 0.156" (3.96 mm); the console's CN1 is a 2x22
connector, and the lettered row appears unconnected, so a cart carries its 22 contacts on one face.

PROVISIONAL, every number below except the pitch and the count, until a real cartridge is measured:
which face carries the contacts, which end is pin 1, the finger width and length, the tab width
and depth, the board thickness.
"""

PITCH = 3.96                     # 0.156"
N_PINS = 22


def pin_x(pin):
    """Centre x of edge pin 1..22, pin 1 at the left seen from F.Cu (PROVISIONAL)."""
    return round((pin - (N_PINS + 1) / 2) * PITCH, 3)


FACE = 'F'                       # contacts on F.Cu, the component side (PROVISIONAL)
FINGER_W = 2.5                   # 1.46 mm between fingers (PROVISIONAL)
LAND_Y0, LAND_Y1 = 0.6, 8.5      # copper, distance in from the insertion edge (PROVISIONAL)
MASK_Y1 = 9.0                    # one mask window over the finger field
TAB_W = 88.9                     # 3.5": the finger span (85.7 mm) plus 1.6 mm a side (PROVISIONAL)
TAB_D = 12.0                     # straight part of the tab (PROVISIONAL)
CH_TAB = 0.8                     # 45-degree lead-in chamfer on the tab's outer corners
THICKNESS = 1.6                  # (PROVISIONAL)

assert pin_x(1) < 0 < pin_x(22) and abs(pin_x(1) + pin_x(22)) < 1e-9
assert abs(pin_x(22) - pin_x(1) - 21 * PITCH) < 1e-9
assert TAB_W / 2 - (abs(pin_x(1)) + FINGER_W / 2) > 1.0
assert MASK_Y1 > LAND_Y1 and TAB_D > MASK_Y1
