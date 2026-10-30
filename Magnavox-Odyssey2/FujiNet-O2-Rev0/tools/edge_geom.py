"""The Magnavox Odyssey 2 / Philips Videopac cartridge edge and board outline -- the single source of
the cart's mechanical numbers.  make_edge_fp.py, gen_pcb.py, placement.py and the audits import it.

Sources (2026-10-30):
  * 30 contacts, two rows of 15: "Top Row: A B C D E F G H J K L M N P R / Bottom Row: 1 .. 15 (Note
    that letters I, O, and Q are not used)": Dan Boris, "Odyssey 2 Technical Specs" v1.1 section 2.0
    (https://atarihq.com/danb/files/o2doc.pdf).  Its pin list is design.EDGE.
  * Three built, working Videopac carts, whose design files give the edge as it actually plugs in:
      - bwack, Videopac_USBCART (LGPL-3.0), KiCad/videopac-usbcart-kicad5.kicad_pcb: the footprint
        INSIDE the board (its library file videopac-edgecon.kicad_mod differs: pin 7 at -3.81 and
        F..K reversed -- not used).  Pads 1..15 on F.Cu at x = -27.5 .. +27.5 step 3.9286 (55 / 14),
        A..R on B.Cu at the same x (A behind 1), each 2.0 x 8.0 mm from the board edge; two 5.0 mm
        NPTH at (+-27, -25); outline 63 x 85 with the side notches and bottom chamfers below.
      - aotta, PicoPAC: the same outline and footprint as bwack's (dimensions only: no licence).
      - wilco2009, Videopac-micro-SD-Cart v2.2 (GPL-3.0): 3.96 mm pitch, 2.6 x 10.16 mm fingers
        from 0.45 mm, 62.2 mm wide; Soeren Gust's G7000RAM: 3.937 mm (0.155").
    Every one of them plays in a console, so a pitch anywhere in 3.9286 .. 3.96 and a 2.0 mm finger
    make contact; this board takes bwack's / PicoPAC's numbers, the most-built outline.
  * Which way round: in PicoPAC's photos in a G7000 the 1..15 row faces the player, pin 1 at the left
    seen from the front.  The board follows bwack's frame: F.Cu (the parts) = the 1..15 face, so the
    asymmetric side notches and the holes are bwack's exactly.
  * Insertion depth / shell bottom: not published.  bwack's lowest part courtyard (U2, a TQFP-64 at
    28.16 mm) reaches 19.8 mm above the edge, and his shell posts are at 25 mm: PARTS_Y = 20.
VERIFIED: tools/audit/edge_orientation.py checks the footprint and the netlist against Boris's list,
bwack's in-board footprint and nets, wilco's netlist and PicoPAC's GPIO wiring; it passes, so the
edge is not provisional.  Unmeasured (not gates): the exact pitch of an original cart, and which face
of an original cart carries its label.
"""

VERIFIED = True

# ---- contacts --------------------------------------------------------------------------------
N_PER_FACE = 15
ROW_F = [str(i) for i in range(1, 16)]               # F.Cu, the parts face (toward the player)
ROW_B = list('ABCDEFGHJKLMNPR')                      # B.Cu, each directly behind its 1..15 pin
PINS = ROW_F + ROW_B
PITCH = 55.0 / 14          # 3.9286: bwack / PicoPAC, pins 1 and 15 at -27.5 / +27.5
# Seen from the parts side (F.Cu) with the edge at the bottom, pin 1 (and A behind it) is at the left
PIN1_LEFT = True
LAND_W = 2.0               # finger width (bwack / PicoPAC)
LAND_Y0 = 0.5              # finger starts this far from the insertion edge (room for the bevel; wilco 0.45)
LAND_Y1 = 8.0              # ... and ends here (bwack / PicoPAC 8.0)
NECK_W = 0.5               # each finger continues as a masked neck ...
NECK_Y1 = 10.5             # ... to here, above the finger field, where the routers pick it up
FIELD_TOP = 9.0            # finger field: no tracks / vias / pour on F.Cu or B.Cu below this
PLANE_Y = 10.0             # inner planes stop this far from the insertion edge
THICKNESS = 1.6            # bwack / PicoPAC; the EDAC 305 sockets cartridge readers use take 1.57

# ---- outline: bwack's / PicoPAC's 63 x 85 (y up from the insertion edge, x from the centre,
# seen from F.Cu) ----------------------------------------------------------------------------
BOARD_W = 63.0
CART_H = 85.0              # insertion edge to top edge
CHAMF_X, CHAMF_Y = 2.0, 2.5   # the two bottom corners
TOP_R = 1.0                # top corners rounded (bwack's are square: a radius only removes material)
NOTCH_D = 1.5              # side notches, 1.5 mm deep:
NOTCH_L = (32.5, 40.0)     #   left side (seen from F.Cu), from .. to above the edge
NOTCH_R = (30.5, 38.0)     #   right side
PARTS_Y = 20.0             # no part courtyard closer than this to the insertion edge
HOLE_D = 5.0
HOLES_REL = [(-27.0, 25.0), (27.0, 25.0)]   # NPTH centres (x from centre, y above the edge): shell posts
POST_KEEP = 4.5            # no part within this radius of a hole centre (the shell's post boss)


def finger_x(pin):
    """Finger centre x (footprint frame, + = right seen from the parts side) for an edge pin."""
    col = (ROW_F if pin in ROW_F else ROW_B).index(pin)     # 0..14 along the row, from the pin-1 end
    x = (col - (N_PER_FACE - 1) / 2) * PITCH
    return round(x if PIN1_LEFT else -x, 4)


def finger_layer(pin):
    """1..15 on the parts side (F.Cu), A..R behind them (B.Cu)."""
    return 'F.Cu' if pin in ROW_F else 'B.Cu'
