"""Atari 7800 cartridge edge and lower-board geometry: the one place these numbers live.

make_edge_fp.py (footprint), gen_pcb.py (outline, key slots, finger stubs), check_nets.py and
audit/edge_orientation.py (assertions), gen_pcb.write_case_anchors (shell) all import this.

Frame: x = 0 at the tab centre, y = distance IN from the insertion edge (mm, +y into the board).
Seen from F.Cu (the component side) with the fingers down, -x is left.

The edge (verified 2026-10-07, sources in audit/edge_orientation.py):
  * 18 positions at 2.54 mm; positions 3 and 16 carry no finger but a SLOT in the board for the
    plastic keys in the console's connector: 2 fingers | slot | 12 fingers (the 2600's 24-pin edge)
    | slot | 2 fingers on each face.
  * pins 1-16 on F.Cu = the component side, which faces the console's REAR; pin 1 at the left
    (-x); pin k on F.Cu directly over pin 33-k on B.Cu.  (Avoid "label side": sources disagree
    on the word, not on the copper.)
"""

PITCH = 2.54
N_POS = 18                       # finger positions per face, incl. the two key positions
KEY_POS = (3, 16)                # positions with a slot instead of a finger


def pos_x(p):
    """Centre x of position p (1..18), position 1 at the left seen from F.Cu."""
    return round((p - (N_POS + 1) / 2) * PITCH, 3)


# finger position of pin k (1..16 on F.Cu; 33-k on B.Cu sits behind it)
FINGER_POS = [p for p in range(1, N_POS + 1) if p not in KEY_POS]
assert len(FINGER_POS) == 16


def pin_x(pin):
    """Centre x of edge pin 1..32."""
    k = pin if pin <= 16 else 33 - pin
    return pos_x(FINGER_POS[k - 1])


def pin_face(pin):
    return 'F' if pin <= 16 else 'B'


# fingers: the working FujiPlusCart prototype's 1.5 mm width (its gerbers: 1.5 x 6.5 mm,
# 0.58-7.08 mm in), lengthened to 0.5-7.5 mm so the copper covers every source's span
FINGER_W = 1.5
LAND_Y0, LAND_Y1 = 0.5, 7.5      # copper, distance in from the insertion edge
MASK_Y1 = LAND_Y1 + 0.5          # one mask window per face, edge .. here

# key slots: centred on the key positions (+-16.51), 2.4 mm wide (karri's measured cut),
# 10 mm deep (Otaku 9.7, tdididit 8.89); 0.59 mm to the neighbouring fingers on both sides
SLOT_W, SLOT_D = 2.4, 10.0
SLOT_X = [pos_x(p) for p in KEY_POS]          # (-16.51, +16.51)

# lower board profile (the stock 7800 "T-bar" board, tdididit a78-flashcartplus):
#   47.0 wide from the edge to 33.0 mm in, 41.3 wide (the stock neck, its rib notches dropped:
#   our shell is printed) to 49.5 mm in, then the 72.4 mm body.
TAB_W = 47.0
TAB_TOP = 33.0                   # y where the tab width ends
NECK_W = 41.3
NECK_TOP = 49.5                  # y where the body starts (stock T-bar transition)
BODY_W = 72.4                    # stock T-bar body width
CH_TAB = 1.0                     # 45-degree chamfer on the tab's outer corners (insertion lead-in)

THICKNESS = 1.6                  # real carts measured 1.5 (karri); 1.6 FR4 fits (Dissy614, karri)
FINGER_EDGE_CLEAR = 0.4          # DRU: finger copper to Edge.Cuts (fingers start 0.5 in)

# finger field: stubs leave each finger to here; no tracks/vias/pour on F/B below this line and
# no inner copper anywhere in the tab (gen_pcb)
FIELD_TOP = SLOT_D + 2.0         # 12 mm in: above the slot ends with room for the stub-end vias


def slot_clearance():
    """Smallest copper gap between a key slot and its neighbouring fingers (mm)."""
    gaps = []
    for sx in SLOT_X:
        for pin in range(1, 17):
            x = pin_x(pin)
            gaps.append(abs(x - sx) - FINGER_W / 2 - SLOT_W / 2)
    return min(gaps)


assert pin_x(1) < 0 < pin_x(16) and pin_x(1) == pin_x(32)
assert abs(pin_x(3) + pin_x(14)) < 1e-9, '2600 block centred'
assert slot_clearance() > 0.55
assert SLOT_D > LAND_Y1 and FIELD_TOP > SLOT_D
assert TAB_W / 2 - (abs(pin_x(1)) + FINGER_W / 2) > 1.0
