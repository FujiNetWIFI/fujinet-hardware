"""The board's mechanical numbers and the ribbon header's frame -- the single source for placement.py,
gen_pcb.py, the case and the audits.

The card is a free-standing board (in a printed case, case/), not a cartridge: a 100 x 76 mm rectangle,
rounded corners, an M3 hole in each corner.  The TRS-80 Model I's expansion edge reaches it on a
40-wire IDC ribbon: a 3M 3464-series (or equivalent) 40-way 0.100" card-edge IDC on the keyboard unit's
edge, a 2x20 IDC socket on this board's right-angle box header.  A straight ribbon puts edge pin n on
header pin n.

The header (XFCN BH254R-40P, tools/make_fp_m1.py) lies along the west edge, its mouth flush with the
board edge, turned 270 deg: the odd pins on its inboard row, the even pins on the row by the mouth,
pin 1 at the SOUTH end.  Seen from the mouth, with the key up, pin 1 is on the left.

VERIFIED: tools/audit/header_pinout.py checks the netlist on every header pin against the edge pinout
(four independent sources) and this footprint's numbering against its EasyEDA original; it passes.  The
cable's orientation on the unkeyed Model I edge is the user's: README "The cable".
"""

VERIFIED = True

BOARD_W = 100.0
BOARD_H = 76.0
CORNER_R = 2.0
THICKNESS = 1.6

HOLE_D = 3.2               # M3 clearance, NPTH
HOLE_IN = 4.0              # hole centres this far in from both edges at each corner
HOLE_KEEP = 3.6            # no part within this radius of a hole centre (the case's boss / screw head)

# the header, in its own footprint frame (tools/make_fp_m1.py): pads at x +-24.13 (pin 1 at +24.13),
# rows at y -1.27 (odd) / +1.27 (even), the shroud from y +3.43 to its mouth at y +12.24
HDR_ROT = 270
HDR_MOUTH = 12.24          # footprint y of the mouth
HDR_OVERHANG = 0.24        # the mouth stands this far past the board edge (0 = flush)
HDR_H = 8.9                # the shroud's height above the board (right-angle 2x20 box headers: 8.85-9.0)
HDR_HALF_LEN = 29.3        # half the shroud's length (footprint x)
PITCH = 2.54
