"""RCA Studio II cartridge edge and board-outline geometry: the one place these numbers live.

make_edge_fp.py (footprint), make_fp_extra.py (the shell-post hole), gen_pcb.py and placement.py
(outline, holes, finger stubs, keep-outs), check_nets.py and audit/edge_orientation.py (assertions
against the sources), audit/check_gerbers.py (the fab zip) and gen_pcb.write_case_anchors (shell)
import this.

Frame: x = 0 at the board centre, y = distance IN from the insertion edge (mm, +y into the board).
Seen from F.Cu (the parts side) with the fingers down, -x is left (west).

The source (audit/edge_orientation.py transcribes the numbers and re-checks them): FliP's (Philip
Marien's) RCA Studio II multicart v5.1, github.com/vodkaflip/RCA_Studio_II, Eagle 9.6.2 board file
and fab gerbers (2023-09-20).  It is built, runs in real consoles and fits original shells, and the
original game board's photos match its outline.  Read from it:
  * 22 contacts on ONE face (his Top copper; nothing on Bottom in the field), 0.156" (3.9624 mm)
    pitch, each 1.905 x 8.255 mm, 0.70-8.95 mm in from the edge, centred on the board;
  * seen from the contact face with the fingers down, pin 1 (D7) is at the LEFT -- his pad 1 is at
    local x -41.6 in his top view, the original board's component side reads "22 ... 1" left to
    right (cosmacvip.com Tester 1 photo), and his pads carry EJK's pinout (D7 on 1, A0 on 11);
  * no tab: the full 90.912 mm insertion edge enters; straight sides for 73.33 mm, then 12.12 x
    10.16 mm chamfers to the 83.49 mm top edge;
  * two 8.128 mm milled holes 68.58 mm in, for the original shell's posts; a 1.83 mm-radius
    half-round notch in each side 20.83 mm in;
  * 1.57 mm board (his job file).
This board puts the contacts on B.Cu and every part on F.Cu, as an original cart does (its chips on
the face away from the contacts, the shell's front half).  So everything FliP draws seen from his
contact face is MIRRORED here: seen from F.Cu, pin 1 is at the RIGHT (east, +x).  His two holes
and two notches sit ~0.24 mm off-centre in opposite directions (hand-placed): the holes keep his
positions, mirrored; both notches take the deeper of his two cuts, symmetric.

This board is FliP's outline from the insertion edge up to the top of his straight sides, then
taller by EXT_H with rounded top corners (CART_H, TOP_R): with the ESP32-S3 on the cart (antenna
flush with the top edge, the USB-C and the microSD beside it) it outgrows the original shell, and
the console's slot is open above, so nothing limits the height.  The edge, the notches, the two
post holes and the parts-free band are FliP's, unchanged.
"""

PITCH = 3.9624                  # 0.156" (FliP's pads: exactly 3.9624 apart)
N_PINS = 22
FACE = 'B'                      # the contact face: B.Cu; every part is on F.Cu


def pin_x(pin):
    """Centre x of edge pin 1..22 seen from F.Cu with the fingers down: pin 1 at the RIGHT (+x),
    the mirror of FliP's contact-face view (pin 1 at the left)."""
    assert 1 <= pin <= N_PINS
    return round(((N_PINS + 1) / 2 - pin) * PITCH, 4)


FINGER_W = 1.905                # FliP
LAND_Y0, LAND_Y1 = 0.70, 8.95   # finger copper, mm in from the insertion edge (FliP 0.6985-8.9535)
MASK_X = 0.1                    # each finger's own B.Mask opening: 0.1 mm a side (FliP 2.108 x 8.458) ...
MASK_Y1 = 9.05                  # ... from the edge to here

BOARD_W = 90.912                # FliP: the full width is the insertion edge (no tab)
BOARD_H = 83.49                 # FliP: insertion edge to his top edge (edge_orientation.py checks these
SIDE_H = 73.33                  #   three against his board file) -- straight sides up to here,
CH_TOP_W, CH_TOP_H = 12.117, 10.16   # then his top corners' chamfers (12.116 / 12.118 x 10.16)
EXT_H = 28.0                    # this board: taller than FliP's by this (the ESP32-S3 half above the RP)
CART_H = BOARD_H + EXT_H        # this board: insertion edge to its top edge (111.49)
TOP_R = 3.0                     # this board's top corners: rounded, r 3 mm
CH_EDGE = 0.8                   # 45-degree chamfer on the two insertion-edge corners (a lead-in;
                                # FliP's are square: 2.9 mm from the outer fingers either way)

HOLE_D = 8.128                  # the original shell's posts (FliP's milled 8.128 mm holes)
HOLES = ((35.804, 68.58), (-35.570, 68.58))   # (x, y in): FliP's (9.906 / 81.28 from his left
                                # edge, 0.254), seen from his contact face, mirrored
NOTCH_R = 1.8316                # FliP's side notches: milled circles r 1.8316 ...
NOTCH_INSET = 0.234             # ... centred this far inside the side (his deeper one; the other is 0.254 out)
NOTCH_Y = 20.828                # ... this far in

THICKNESS = 1.6                 # FliP 1.57 (his job file; a 0.156" card-edge slot takes 1.57-1.6)
FINGER_EDGE_CLEAR = 0.6         # DRU: finger copper to Edge.Cuts (0.70 by design)

# routing near the edge: nothing but the finger stubs below FIELD_TOP (the mask openings); tracks,
# vias and pour above it; no parts below PARTS_Y -- the board under the shell's lower lip enters the
# console (the original cart shows ~15 mm of board below its shell) and the notches clear the
# shell's rivets
FIELD_TOP = MASK_Y1 + 0.5       # 9.55
STUB_TOP = FIELD_TOP + 0.6      # every finger's locked stub ends here (10.15)
PLANE_Y = FIELD_TOP + 0.5       # In1 / In2 start here: no inner copper behind the fingers or the bevel
PARTS_Y = 23.5                  # no part courtyard closer to the insertion edge than this

# ---- FliP's numbers as read (his frame: x from his left edge, seen from his contact face) ----------
FLIP_PAD1_X = 4.1148            # his pad 1 centre (element P1 at 45.72, pad local -41.6052)
FLIP_OUTLINE_X = (0.254, 91.166)
FLIP_HOLES = ((9.906, 68.58), (81.28, 68.58))
FLIP_NOTCHES = ((0.0, 20.828), (90.932, 20.828))

assert abs(pin_x(1) - 10.5 * PITCH) < 1e-3 and abs(pin_x(1) + pin_x(22)) < 1e-9
assert all(abs(pin_x(n) - pin_x(n + 1) - PITCH) < 2e-4 for n in range(1, N_PINS))
assert BOARD_W / 2 - (pin_x(1) + FINGER_W / 2) > 2.0 + CH_EDGE      # 2.9 mm of board outside the outer fingers
assert MASK_Y1 > LAND_Y1 and STUB_TOP < PARTS_Y and NOTCH_Y + NOTCH_R < PARTS_Y
assert abs(sum(FLIP_OUTLINE_X) / 2 + (FLIP_HOLES[0][0] - sum(FLIP_OUTLINE_X) / 2) - FLIP_HOLES[0][0]) < 1e-9
assert abs(-(FLIP_HOLES[0][0] - sum(FLIP_OUTLINE_X) / 2) - HOLES[0][0]) < 1e-3
assert abs(-(FLIP_HOLES[1][0] - sum(FLIP_OUTLINE_X) / 2) - HOLES[1][0]) < 1e-3
assert abs(FLIP_OUTLINE_X[1] - FLIP_OUTLINE_X[0] - BOARD_W) < 1e-6
