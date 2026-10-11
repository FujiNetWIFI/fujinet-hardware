"""Fairchild Channel F Videocart edge and board-outline geometry: the one place these numbers live.

make_edge_fp.py (footprint), gen_pcb.py and placement.py (outline, holes, finger stubs, keep-outs),
audit/edge_orientation.py (assertions against the sources), audit/check_gerbers.py (the fab zip)
and gen_pcb.write_case_anchors (shell) import this.

Frame: x = 0 at the key slot (the tab centre), y = distance IN from the insertion edge (mm, +y
into the board).  Seen from F.Cu (the component side, which faces UP in the console) with the
fingers down, -x is left (west).

The edge (sources and their numbers in audit/edge_orientation.py, read 2026-10-10):
  * all 22 contacts are on ONE face, the face that is DOWN in the console: the console's spring
    contacts push up from below (US 4,095,791: contacts "formed in parallel along the bottom
    surface"; the veswiki Pinouts photo; both open designs carry copper on one face).  This board
    puts them on B.Cu and every part on F.Cu, facing up;
  * 2.54 mm pitch: pins 1-11, a gap of 4 pitches (10.16 mm) holding the key slot, pins 12-22;
    pin 1 to pin 22 spans 60.96 mm (timtashpulatov/fart Cart_Conn exactly; aotta/PicoVideocart
    ~2.565 hand-placed, 10.156 gap);
  * seen from the parts side with the fingers down, pin 1 (GND) is at the LEFT and pin 22 (+12V)
    at the right (fart: B.Cu fingers, J5 numbering; aotta: F.Cu fingers with its pad n = J5 pin
    23-n, mirrored onto B.Cu it agrees);
  * key slot centred between pins 11 and 12: aotta (works on a console) 1.651 wide, 12.58 deep,
    with a 6.1 mm lead-in over the first 1.66 mm;
  * the tab 68.3 wide (aotta 68.37, fart 68.58), straight for 30 mm (aotta), a 45-degree taper
    out to the 77 mm body; 131.5 mm overall; four 5.6 mm holes 67 mm apart, 37.5 / 116.1 mm in
    from the edge -- the original shell's bosses (aotta's Edge.Cuts circles; it fits an original
    shell).
"""

PITCH = 2.54
N_PINS = 22
GAP = 4                           # pitches between pins 11 and 12 (the key slot sits in the middle)


def pin_index(pin):
    """Position index on the 2.54 mm grid: pins 1-11 -> 0-10, pins 12-22 -> 14-24."""
    assert 1 <= pin <= N_PINS
    return pin - 1 if pin <= 11 else pin - 1 + GAP - 1


def pin_x(pin):
    """Centre x of edge pin 1..22, 0 at the key slot (the midpoint of pins 11 and 12)."""
    return round((pin_index(pin) - (10 + 10 + GAP) / 2) * PITCH, 3)


FINGER_W = 1.8                    # between fart's 1.524 and aotta's 1.9: 0.74 mm between fingers
LAND_Y0, LAND_Y1 = 0.5, 12.0      # finger copper, distance in from the insertion edge (aotta 0.55-~10.5,
                                  # fart 0.99-12.99; ZX-80's rev 2A "height doubled" after short fingers)
MASK_Y1 = 12.5                    # one B.Mask window over the finger field, edge .. here

SLOT_W = 1.651                    # the key slot (aotta, proven on a console)
SLOT_D = 12.58                    # edge to the top of the slot (round top, r = SLOT_W / 2)
LEADIN_W = 6.1                    # the slot's V lead-in: this wide at the edge ...
LEADIN_D = 1.66                   # ... narrowing to SLOT_W this far in

TAB_W = 68.3                      # straight tab (aotta 68.26-68.37, fart 68.58)
TAB_D = 30.0                      # straight part of the tab (aotta 30.0): no parts on it
BODY_W = 77.0                     # the body (aotta 77.0)
TAPER = (BODY_W - TAB_W) / 2      # 45-degree taper from the tab out to the body
BODY_Y0 = TAB_D + TAPER           # the body reaches its full width here
BOARD_H = 131.5                   # insertion edge to the trailing (grip-end) edge (aotta 131.525)
CH_TAB = 1.5                      # 45-degree chamfer on the tab's two leading corners
CH_TOP = 2.0                      # 45-degree chamfer on the grip-end corners

# the original shell's bosses (aotta's Edge.Cuts circles, 2.8 mm radius): x from the centre, y in
HOLE_D = 5.6
HOLE_DX = 33.5                    # 67.0 apart
HOLE_Y = (37.525, 116.1)

THICKNESS = 1.6                   # the console slot is "slightly greater than the thickness" (patent); aotta 1.6
FINGER_EDGE_CLEAR = 0.4           # DRU: finger copper to Edge.Cuts (the lead-in passes 1.1 mm from pins 11/12)

# routing on the tab: nothing but the finger stubs below FIELD_TOP (the mask window, the slot),
# tracks / vias / pour above it; no parts anywhere on the straight tab (KEEP_D): the console
# connector's reach and the shell door's swing over the top face are not documented
FIELD_TOP = MASK_Y1 + 1.0
STUB_TOP = FIELD_TOP + 0.5        # every finger's locked stub ends here
KEEP_D = TAB_D                    # no parts this close to the edge (15 mm floor if a console is measured)

NC_PINS = (21, 22)                # 21 spare, 22 +12 V: fingers, but no stub and no copper near them

assert pin_x(1) < 0 < pin_x(22)
assert abs(pin_x(1) + 30.48) < 1e-9 and abs(pin_x(22) - 30.48) < 1e-9
assert abs(pin_x(11) + 5.08) < 1e-9 and abs(pin_x(12) - 5.08) < 1e-9 and abs(pin_x(12) - pin_x(11) - GAP * PITCH) < 1e-9
assert TAB_W / 2 - (abs(pin_x(1)) + FINGER_W / 2) > 2.5
assert LEADIN_W / 2 < pin_x(12) - FINGER_W / 2 - 1.0          # the lead-in clears fingers 11 / 12
assert MASK_Y1 > LAND_Y1 and FIELD_TOP > SLOT_D and STUB_TOP < TAB_D
assert abs(TAPER - 4.35) < 1e-9 and BOARD_H > HOLE_Y[1] + HOLE_D
