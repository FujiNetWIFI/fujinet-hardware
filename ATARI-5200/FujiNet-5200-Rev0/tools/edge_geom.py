"""Atari 5200 cartridge edge and lower-board geometry: the one place these numbers live.

make_edge_fp.py (footprint), gen_pcb.py (outline, finger stubs), check_nets.py and
audit/edge_orientation.py (assertions), audit/check_gerbers.py (the fab zips) and
gen_pcb.write_case_anchors (shell) import this.

Frame: x = 0 at the tab centre, y = distance IN from the insertion edge (mm, +y into the board).
Seen from F.Cu (the component side, the label face) with the fingers down, -x is left (west).

The edge (sources in audit/edge_orientation.py, measured 2026-10-08):
  * 18 positions at 2.54 mm per face; pins 1-18 on the LABEL face, pin 1 (D0) at the far left
    seen from it with the fingers down; pin 37-k on the back face directly behind pin k (pin 19,
    A0, behind pin 18; pin 36 behind pin 1).  Joe Grand's Pixels Past 5200 32K rev B gerbers
    (traced to the EPROM), tdididit's a52 Eagle library and flash cart, sanni's cartreader
    5200.ino pin diagram and the photo of a Galaxian cart in its adapter all agree;
  * pins 18 and 36 (CI1 / CI2, the interlock) are SHORT fingers: their copper starts ~1.27 mm
    further from the edge than the others (Pixels Past 1.905 vs 0.635, tdididit 1.8415 vs
    0.5715), so the console's regulator VR1 is switched on last as the cart goes in and off first
    as it comes out;
  * fingers 1.524 (tdididit) to 1.905 (Pixels Past) wide, copper from 0.57-0.64 to 6.99-7.05 mm
    in; the tab 47.625 (tdididit) / 48.006 (Pixels Past) wide, straight for 17.8-18.5 mm; the
    console connector's opening (Sullins / TE substitutes for Atari C018081) is 48.26 mm, 7.5 mm
    deep, for a 1.57 +/- 0.2 mm board.
"""

PITCH = 2.54
N_POS = 18                       # finger positions per face
N_PINS = 2 * N_POS


def pos_x(p):
    """Centre x of position p (1..18), position 1 at the left seen from F.Cu."""
    return round((p - (N_POS + 1) / 2) * PITCH, 3)


def pin_pos(pin):
    return pin if pin <= N_POS else N_PINS + 1 - pin


def pin_x(pin):
    """Centre x of edge pin 1..36."""
    return pos_x(pin_pos(pin))


def pin_face(pin):
    return 'F' if pin <= N_POS else 'B'


SHORT = (18, 36)                 # the interlock pair: last-make, first-break
FINGER_W = 1.78                  # 0.070": between tdididit's 1.524 and Pixels Past's 1.905
LAND_Y0, LAND_Y1 = 0.6, 7.0      # copper, distance in from the insertion edge (covers 0.635-6.985)
LAND_Y0_SHORT = 1.9              # pins 18 / 36 (Pixels Past 1.905, tdididit 1.8415)
MASK_Y1 = 7.5                    # one mask window per face, edge .. here (Pixels Past 6.553 tall)

# the tab: straight, then 45-ish degree shoulders out to the lower body (Pixels Past rev B: 48.006
# straight to 18.542, then to 60.96 at 25.4)
TAB_W = 47.8                     # inside 47.625..48.006 of the open designs; slot 48.26
TAB_D = 18.5                     # straight part of the tab
SHOULDER_Y = 25.4                # the lower body reaches its full width here
LOWER_W = 60.96                  # the original cart board's width (the shell's prong slots at |x| >= 30.75)
CH_TAB = 0.8                     # 45-degree lead-in chamfer on the tab's outer corners

THICKNESS = 1.6                  # the connector takes 1.57 +/- 0.2; the SIO2 shell clamps 1.6
FINGER_EDGE_CLEAR = 0.5          # DRU: finger copper to Edge.Cuts (fingers start 0.6 in)

# routing on the tab: nothing but the finger stubs below FIELD_TOP (the mask window and the
# connector's 7.5 mm), tracks and vias allowed above it; no parts anywhere on the tab
FIELD_TOP = MASK_Y1 + 1.0
STUB_TOP = FIELD_TOP + 0.5       # every finger's locked stub ends here

assert pin_x(1) < 0 < pin_x(18) and pin_x(1) == pin_x(36) and pin_x(18) == pin_x(19)
assert abs(pin_x(1) + 21.59) < 1e-9 and abs(pin_x(18) - 21.59) < 1e-9
assert pin_face(1) == 'F' and pin_face(19) == 'B'
assert TAB_W / 2 - (abs(pin_x(1)) + FINGER_W / 2) > 1.0
assert MASK_Y1 > LAND_Y1 and FIELD_TOP > MASK_Y1 and STUB_TOP < TAB_D
