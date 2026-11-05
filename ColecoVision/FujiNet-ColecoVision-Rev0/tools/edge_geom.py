"""The ColecoVision cartridge edge and board outline -- the single source of the cart's mechanical
numbers.  make_edge_fp.py, gen_pcb.py, placement.py and the audits import it.

Sources (2026-11-04):
  * 30 contacts, two rows of 15 at 2.54 mm, pin 2k-1 directly behind pin 2k: MAME
    src/devices/bus/coleco/cartridge/exp.h (its pin table is design.EDGE) = the Coleco ADAM Technical
    Reference Manual's cartridge connector J1 (CS1*-CS4* = /8000 /A000 /C000 /E000).
  * Three built, open carts, whose design files give the edge as it actually plugs in:
      - ThatOldNerd, Coleco-Game-Cart V4 (GPL-3.0), Coleco Cart V4.brd: a 40.0 x 56.5 board; fingers
        1.27 x 8.89 mm at 2.54 mm from 0.42 mm, even pins on the top copper with pin 2 at the left,
        odd pins on the bottom behind them; notches 2.0 mm deep at 19.6-26.0 on both sides and
        34.0-40.5 (pin-1 side) / 36.5-43.0 (pin-30 side); two 3.4 mm holes 50.5 mm up, 5.5 mm in from
        the pin-1 side and 6.0 mm from the other; 0.5 mm x 45 degree corner chamfers.
      - Commodore-Bench, ColecoVision Reprogrammable Flash Card (MIT), KiCAD/Coleco-Card3.kicad_pcb, and
        aotta's PiCOLECO (GPL-3.0) on the same footprint: 40.64 x 82.4, fingers 1.75 x 7.0 from the edge
        (the +5V finger 5.75 long, starting 1.3 mm in: it mates last), notches 0.97 deep at 20.0-25.75
        / 34.5-40.1 / 37.0-42.6, no holes.
      - Joe Grand, "Pixels Past" ColecoVision cart rev B ("fits standard housing"): 40.13 x 58.67,
        fingers 1.27 x 7.62 from 0.5 mm, notches 1.27 deep at 20.1-25.7 / 34.5-40.1 / 37.1-42.7.
    They agree on the pinout and its orientation, the pitch and the notch positions; this board takes
    the widest notch spans (ThatOldNerd's), a width between Joe Grand's and Commodore-Bench's, and
    Commodore-Bench's 82.4 mm length (so the USB-C and the microSD reach the shell's top wall).
  * The replacement slot (Sullins EBC15DRTH) takes 0.062" +- 0.008" boards: 1.6 mm.
  * Insertion depth / shell bottom: not published.  ThatOldNerd's lowest pads (a DIP-28) sit 15 mm
    above the edge, Commodore-Bench's lowest parts 17 mm: PARTS_Y = 15.
VERIFIED: tools/audit/edge_orientation.py checks the footprint and the netlist against MAME's table and
the three carts' footprints and nets; it passes, so the edge is not provisional.  Unmeasured (not gates;
README "Original shell"): the interior of an original shell -- its length to the top wall, whether it has
posts above the notches (ThatOldNerd's board has holes 50.5 mm up), and which face carries the label.
"""

VERIFIED = True

# ---- contacts --------------------------------------------------------------------------------
N_PER_FACE = 15
ROW_F = [str(i) for i in range(2, 31, 2)]            # F.Cu, the component face: 2 .. 30
ROW_B = [str(i) for i in range(1, 30, 2)]            # B.Cu, each directly behind its even pin: 1 .. 29
PINS = ROW_F + ROW_B
PITCH = 2.54
# Seen from the parts side (F.Cu) with the edge at the bottom, pin 2 (and pin 1 behind it) is at the left
PIN1_LEFT = True
LAND_W = 1.6               # finger width (built carts 1.27 .. 1.75)
LAND_Y0 = 0.5              # finger starts this far from the insertion edge (room for the bevel)
LAND_Y0_LATE = {'30': 1.5}  # ... the +5V finger further in, so it mates last (Commodore-Bench's 1.3)
LAND_Y1 = 8.5              # ... and ends here (built carts 7.0 .. 9.3)
NECK_W = 0.5               # each finger continues as a masked neck ...
NECK_Y1 = 11.0             # ... to here, above the finger field, where the routers pick it up
FIELD_TOP = 9.5            # finger field: no tracks / vias / pour on F.Cu or B.Cu below this
PLANE_Y = 10.5             # inner planes stop this far from the insertion edge
THICKNESS = 1.6

# ---- outline (y up from the insertion edge, x from the centre, seen from F.Cu) -----------------
BOARD_W = 40.2
CART_H = 82.4              # insertion edge to top edge
CHAMF_X, CHAMF_Y = 0.8, 0.8   # the two bottom corners
TOP_R = 1.0                # top corners rounded
NOTCH_D = 2.0              # side notches, 2.0 mm deep (from .. to above the edge):
NOTCHES_L = [(19.6, 26.0), (34.0, 40.5)]   # left side, the pin-1 side (seen from F.Cu)
NOTCHES_R = [(19.6, 26.0), (36.5, 43.0)]   # right side, the pin-30 side
PARTS_Y = 15.0             # no part courtyard closer than this to the insertion edge
HOLE_D = 3.4
# No holes.  ThatOldNerd's 56.5 mm board has two 3.4 mm holes 50.5 mm up (-14.5 / +14.0 from the centre),
# but Joe Grand's 58.7 mm board, which "fits standard housing", has none across the same spot, so they
# are not the original shell's posts for certain -- and on this board that spot is the ESP32-S3 module.
# README "Original shell": check an original's interior before cutting one.
HOLES_REL = []             # NPTH centres (x from centre, y above the edge): shell posts
POST_KEEP = 3.5            # no part within this radius of a hole centre (a post's boss)


def finger_x(pin):
    """Finger centre x (footprint frame, + = right seen from the parts side) for an edge pin."""
    col = (ROW_F if pin in ROW_F else ROW_B).index(pin)     # 0..14 along the row, from the pin-1 end
    x = (col - (N_PER_FACE - 1) / 2) * PITCH
    return round(x if PIN1_LEFT else -x, 4)


def finger_layer(pin):
    """Even pins on the component face (F.Cu), odd pins behind them (B.Cu)."""
    return 'F.Cu' if pin in ROW_F else 'B.Cu'


def land_y0(pin):
    return LAND_Y0_LATE.get(str(pin), LAND_Y0)
