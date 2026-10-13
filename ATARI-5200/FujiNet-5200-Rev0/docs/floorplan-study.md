# FujiNet-5200 Rev0: floorplan study

How the board was laid out, and why. The board and the schematic were designed together: the
schematic sheets are drawn in the board's own geometry (fingers to the left), so a part's place on
a sheet tells you where it sits on the board. `tools/placement.py` holds the floorplan,
`tools/gen_pcb.py` builds the board from it, and `tools/route_board.sh` routes it.

## Fixed constraints

**The edge** (`tools/edge_geom.py`, checked by `tools/audit/edge_orientation.py`):

- 18 positions at 2.54 mm per face.
- Pins 1-18 are on the label face, which is F.Cu, the component side. Pin 1 (D0) is at the
  left. Pin 37-k sits behind pin k.
- Pins 18 and 36 (the interlock) are short fingers. Their copper starts 1.9 mm from the edge, so
  they make contact last.
- The tab is 47.8 mm wide and runs straight for 18.5 mm. Nothing but the finger stubs is allowed
  within 8.5 mm of the edge (the console connector reaches 7.5 mm in).

**Where the signals land** (seen from F.Cu, fingers down):

| Face | x (mm) | Pins |
|---|---|---|
| F.Cu | 78.4-96.2 | D0..D7 (1-8) |
| F.Cu | 98.7 / 101.3 | /EN80, /EN40 (9, 10) |
| F.Cu | 103.8 | raw DC (11) |
| F.Cu | 106.4 / 108.9 | GND (12, 13) |
| F.Cu | 111.4 | PHI2 (14) |
| F.Cu | 114-119 | A6 A5 A2 |
| F.Cu | 121.6 | CI1 (18) |
| B.Cu | 78.4 | CI2 (36) |
| B.Cu | 81-101 | A11 A12 A10 A13 A9 . A8 . A7 |
| B.Cu | 103.8 | console 5 V (26) |
| B.Cu | 106.4 / 111.4 | GND (25 / 23) |
| B.Cu | 114-121.6 | A4 A3 A1 A0 |

**The shell.** A stock 5200 cartridge board is 61 x 89.5 mm. It fits between the shell's ribs
(|x| 26.75-30 mm) and carries one screw 38.7 mm up the centre line. The FujiNet half does not fit
that envelope: the ESP32-S3 module alone is 18 x 25.5 mm and needs its antenna at an edge, and
USB-C and the microSD need to exit the top. So the board is T-shaped and goes in a custom shell
whose inside is about 105 mm wide:

- the 47.8 mm tab;
- the original board's 61 mm lower body, up to 38 mm from the edge (the console's dust-cover
  prongs enter the shell beside it);
- a 45-degree step out to an 84 mm wide upper body, 98 mm from the edge to the top.

`case/board-anchors.scad` gives the shell what it needs: the outline, the three screw holes (the
original centre screw and the two step corners), the button pinholes, the LEDs, the USB-C,
microSD and antenna positions, and a label recess.

## The data path decides the lower body

The console reads the cart by putting an address on A0-A13 and pulling an enable low. The byte
has to come back on D0-D7 through the 74HCT541. These are the densest nets on the board, and they
come off the fingers in a fixed order. The plan was to make that path planar before placing
anything else:

- **The '541 sits over the D0-D7 fingers**, at rotation 270. Its Y row faces the fingers in their
  order. Its channels are taken in reverse (`design.py`: A8/Y8 carries bit 0). As a result its A
  row faces the RP2354B's GPIO16-23 corner in that corner's order. Finger -> '541 -> RP crosses
  nothing on F.Cu. `gen_pcb.buf_fanin` draws the finger side, and the board locks it before
  routing.
- **The RP2354B sits straight north of it**, at rotation 90. Its bus side (A4-A13, the enables,
  RP_D0-RP_D4) faces the fingers. The RP and its ring (a 100 nF at every supply pin, the
  core-regulator corner, the crystal, the USB series resistors, QSPI/BOOTSEL, the RP LDO and the
  SWD pads) are one rigid macro. It is the same one the NES and SMS boards use, which is known to
  route.
- **The RP's bus pins get their own escape.** The south row is 0.4 mm pitch. Its middle stretch
  (pins 6-9 and 11-14: A8-A13, /EN40, /EN80) is boxed in by the IOVDD 5 / 15 stubs and DVDD 10.
  `gen_pcb.rp_support` gives each of these pins a locked stub and a 0.5 mm via before routing:
  - pins 6, 8, 12 and 14 go inward, to vias 4.0 mm from the centre beside the DVDD via;
  - pins 7 / 11 and 9 / 13 go outward, to two staggered rows at 5.95 and 6.75 mm.

  Without it, Freerouting's own fan-out walled in A10 and A13 (variants V1-V3 below), and the
  finisher cannot reach under the package to free them.
- **The glue goes over the fingers that feed it.**
  - The 74HCT08 sits over the enables (fingers 9 and 10), under the central screw. Next to it is
    the 74HCT14 with the PWR_OK divider.
  - The PHI2 pull-up and the 74LVC1G17 sit right over finger 14.
- **Power enters where its fingers are.**
  - The console-5V P-FET and its bulk sit over finger 26.
  - The raw-DC jumper sits over finger 11. The PTC, the 2.2R and the AP63205 pre-buck fill the
    lower body's east part. Its SS34 and the CONS_OFF OR sit at the step.
  - The interlock jumper sits where CI2 (36) and CI1 (18) meet, at the west end. Its DNP switch
    sits beside it.
- **Scope pads** for /EN40, /EN80, /OE1, /OE2, PWR_OK, PHI2 and GND sit in the lower body's west
  part, away from the tab.

## The FujiNet half along the top

- **ESP32-S3**, top-left. The antenna is flush with the top edge and has a copper keep-out on
  every layer.
- **microSD** east of the antenna's keep-out. Its slot opens at the top edge.
- **USB-C, the CP2102N and the 3.3 V buck** in the top-right corner. VBUS and its SS34 run down
  the east edge to the +5V island.
- **Buttons** in the west strip under the S3: RESET and BOOTSEL above S3 EN and S3 BOOT. These
  are pinholes in the shell's face.
- **The WS2812 and the RP's LED** east of the RP.

## Stack-up and planes

6 layers, 1.6 mm:

| Layer | Use |
|---|---|
| F.Cu | every part; fingers 1-18; signals and a GND pour |
| In1 | GND plane |
| In2, In3 | signals |
| In4 | power: +3V3 north of y 91; a +5V island south of it and up the east edge; a +3V3_RP island under the RP ring; a DVDD island under its core |
| B.Cu | fingers 19-36; signals and a GND pour |

The planes stop 8.5 mm short of the insertion edge.

## Routing

`tools/route_board.sh` routes the board in stages:

1. It pre-routes the RP core corner (VREG_LX, DVDD, VREG_AVDD, the crystal, SWD) and locks it.
2. Freerouting 2.4.1 routes the rest.
3. A grid A* finisher closes what Freerouting leaves, with rip-up. A last pass necks signals down
   to 0.15 mm at fine-pitch pins.
4. It tidies the tracks, stitches GND, checks the vias, adds 3D models, fixes the silkscreen, and
   runs the DRC gate (all severities, with schematic parity).

Eleven variants ran from the same placement. Freerouting's own "unrouted" count (41-45)
includes connections that KiCad makes through the zones, so the variants were compared by
KiCad's count after import.

| Variant | Before Freerouting | Freerouting | KiCad unconnected | Outcome |
|---|---|---|---|---|
| V1 | core corner | 12 passes, greedy | 22 | stopped |
| V2 | core corner | 12 passes, hybrid | 4 | finisher closed 2; **A10, A13 walled in** |
| V3 | core corner | 20 passes, hybrid | 4 | the same two |
| V2b, V3b | V2 / V3 as routed | second round, 6 passes, hybrid | 2 | the same two |
| V4 | core corner | 12 passes, global | 21 | stopped |
| V5 | core corner | 16 passes, hybrid | 22 | stopped |
| V7 | + A10, A13 routed and locked | 12 passes, hybrid | 4 | A7 and A12 walled in instead |
| V8 | + A8-A13 routed and locked (A8 found no path) | 12 passes, hybrid | 15 | stopped |
| V9 | core corner + **bus escape** | 12 passes, hybrid | n/a | stopped once V10 passed |
| **V10** | core corner + **bus escape** | 12 passes, greedy | **1** (QSPI_SS) | **kept**: finisher closed it; DRC 0 / 0 / 0 with schematic parity |

V6 (20 passes, greedy, without the escape) was stopped before it finished.

The finisher could not free A10 / A13 even when it was allowed into the via ring under the RP
(`FINISH_UNDER=2.4`), because Freerouting had already spent every escape slot around them. The fix
belongs before routing, in the floorplan's own locked copper, which is where it now lives
(`gen_pcb.BUS_ESCAPE`).

The kept board, V10:

| Item | Value |
|---|---|
| Tracks | 1183 segments: F.Cu 1450 mm, In2 1087 mm, In3 808 mm, B.Cu 175 mm |
| Track widths | 0.15 mm (8 neck-downs at the RP) to 0.6 mm |
| Vias | 594: 573 at 0.6 / 0.3, 14 at 0.5 / 0.25 (DVDD and bus escapes), 7 at 0.8 / 0.4 |
| GND vias | 358, including 230 stitching |
| `check_vias` | 0 vias in a foreign pad |
| DRC with schematic parity, all severities | 0 violations, 0 unconnected, 0 parity issues |

FID2 was moved 4 mm in from the east edge after routing; DRC was re-run.
