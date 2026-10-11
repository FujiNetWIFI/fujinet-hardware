# FujiNet-ChannelF Rev0: floorplan study

How the board was laid out, and why. `tools/placement.py` holds the floorplan, `tools/gen_pcb.py`
builds the board from it (outline, planes, locked support copper, plane fan-out) and
`tools/route_board.sh` routes it. Board frame: KiCad top view of F.Cu, the insertion edge at
y = 150, the key slot at x = 100.

## Fixed constraints

**The edge** (`tools/edge_geom.py`, checked by `tools/audit/edge_orientation.py` against aotta's
PicoVideocart fab gerbers, timtashpulatov/fart's footprint, US 4,095,791 and the veswiki photo):

- All 22 contacts are on **one face, the one that is down in the console**: the console's spring
  contacts push up from below. This board puts them on **B.Cu** and every part on F.Cu, which faces
  up (toward the label).
- 2.54 mm pitch: pins 1-11, a 4-pitch gap with the key slot, pins 12-22. Seen from F.Cu with the
  edge at the south, pin 1 (GND) is at the west.
- Fingers 1.8 mm wide, copper 0.5-12.0 mm from the edge (aotta 0.55-10.3, fart 1.0-13.0), one
  B.Mask window to 12.5 mm. F.Cu over the finger field stays bare.
- Key slot 1.651 x 12.58 mm with a round top and a 6.1 mm lead-in (aotta, proven on a console).

| Finger x (mm) | Pins |
|---|---|
| 69.5, 72.1 | GND (1, 2) |
| 74.6, 77.1 | D0, D1 (3, 4) |
| 79.7 | /INTREQ (5) |
| 82.2, 84.8, 87.3 | ROMC0-2 (6-8) |
| 89.8, 92.4, 94.9 | D2, ROMC3, D3 (9-11) |
| 99.2-100.8 | key slot |
| 105.1, 107.6, 110.2, 112.7 | ROMC4, PHI, D4, WRITE (12-15) |
| 115.2, 117.8, 120.3 | D5, D6, D7 (16-18) |
| 122.9, 125.4 | console +5 V (19, 20) |
| 127.9, 130.5 | spare (21), +12 V (22): bare, nothing within 1 mm |

**The shell.** The board keeps the outline aotta proved in an original Videocart shell, so it fits
both an unmodified shell and the custom printed one (102 x 140 x 19 mm outside):

- a 68.3 mm tab, straight for 30 mm, then a 45-degree taper to a 77 mm body; 131.5 mm overall;
- four 5.6 mm holes on the original shell's bosses, 67 mm apart, 37.5 and 116.1 mm from the edge,
  with no parts within 4.8 mm of a hole centre and no copper within 3.4 mm;
- **no parts on the straight tab** (30 mm): the console connector's reach and the spring door's
  swing over the top face are not documented anywhere. The floor is 15 mm if a console is
  measured.

`case/board-anchors.scad` gives the shell what it needs: the outline, the slot, the holes, the
RESET button, the pinhole buttons, the two LEDs, the USB-C, microSD and antenna positions, and a
label recess.

**The grip end.** The trailing edge stays outside the console, so the ESP32-S3's antenna (flush,
over the module's own 48 x 6 mm keep-out), the microSD and the USB-C sit on it, with RESET and
the two LEDs just inside, between the S3 and the microSD.

## The data path decides the south half

The console reads the cart through 15 bus lines that come off the fingers interleaved (D0 D1 /INT
R0 R1 R2 D2 R3 D3 | R4 PHI D4 WR D5 D6 D7). They have to reach the RP2040's GP0-GP14, in that
order, through two SN74LVC4245A.

- **Both translators stand side by side over the fingers at rotation 90**: the A row (5 V, the
  console) south toward the fingers, the B row (3.3 V) north toward the RP. The data one is west,
  the control one east, because the RP's data pins (GP0-7) come before its control pins (GP8-14)
  going round its south-east corner.
- **The RP2040 sits straight north of them at rotation 90.** Its south side carries IOVDD, GP0-7,
  IOVDD, GP8-11 west to east; GP12-15 go up its east side. With `design.py`'s `CTRL_CH` order
  (ROMC0-4, WRITE, PHI, spare A8), the B row meets the RP in the RP's own order, so **B row -> RP
  crosses nothing**. The fingers' R4 / PHI / WRITE order costs one swap, out on the tab where
  there is room for both layers.
- **The finger side:** the data lines run on F.Cu, the control lines on B.Cu, crossing under each
  other in the 17 mm between the finger field and the translators. The A-side lines are 20-35 mm
  long, which is harmless at the F8's 1.79 MHz.
- **The bus-side supplies drop inward.** IOVDD 1 and 10 sit among the bus pins. Each gets a locked
  stub and a 0.5 mm via inward, into the ring's free band between the pads and the exposed pad,
  onto the +3V3_RP island (`gen_pcb.rp_support`). No plane via stands in the fan-in.

## The RP2040 macro

The ring is the routed `atari2600-rev0` board's (same package, rotation and core-regulator
copper):

- the VREG_VOUT -> DVDD link runs inside the pin ring (`rp_dvdd_link`, locked F.Cu), with a via in
  the band that takes DVDD on B.Cu to the 1 uF + 2 x 100 nF west of the QSPI lines;
- the USB pair is drawn, not searched (`rp_usb_link`): it leaves 0.4 mm apart, which a greedy
  router cannot split;
- USB_VDD 48 and IOVDD 49 are strapped, with one via 1.15 mm out;
- the flash sits south-west at rotation 90, its QSPI lines diagonal under the DVDD row;
- the north-west supply row (IOVDD 42, USB_VDD, VREG_VIN, ADC_AVDD, bulk) stands over the USB pair.

The east side is ChannelF's own, because the control lines arrive there from the south-east:

- XIN leaves on F.Cu straight to the crystal;
- XOUT drops through a locked via under the package to its 1k on B.Cu;
- IOVDD 22's via sits 2 mm out between them and SWCLK;
- SWD, RUN, GP16 and GP17 escape east and turn north to their pads;
- DIR leaves east, outside the control lines, and crosses to the data translator on B.Cu.

## Power

- The console's 5 V enters on fingers 19 / 20 through 0.8 mm stubs and vias into an In2 CONS_5V
  island under the translators' A halves. The SS34 that ORs it into +5V sits right over the
  fingers.
- +5V has its own In2 island down the east side, carrying the AP63203 buck (its hot loop on F.Cu
  over the solid In1 GND) and the AP2112K for the RP. The LDO stands on the island boundary: input
  in the +5V island, output in the +3V3_RP island.
- The buck's output and inductor reach north into the +3V3 region that feeds the S3 half.

## Stack-up and rules

JLC04161H-7628, 1.6 mm: F.Cu signal / In1 GND / In2 power islands / B.Cu signal.

| Class | Track | Clearance | Via |
|---|---|---|---|
| Default | 0.2 | 0.15 | 0.6 / 0.3 |
| PWR | 0.5 | 0.15 | 0.8 / 0.4 |
| VBUS | 0.3 | 0.15 | 0.6 / 0.3 |
| USB | 0.25 | 0.15 | 0.6 / 0.3 |

The DRU allows 0.12 mm for the last links at the RP's 0.4 mm pitch (the finisher's `--neck`),
joins the QFN, translator and regulator grounds to the pours solidly, and lets the fingers sit
0.4 mm from the edge.

## Routing

`tools/route_board.sh` takes the placed board through four stages:

1. A short locked pre-route on the empty board: XIN and XOUT_Y, by the grid finisher.
2. Freerouting 2.4.1, 16 passes.
3. The grid A* finisher, three times. It honours every rule area, including the S3 antenna
   keep-out inside the module footprint. Its last pass necks down to 0.15 mm / 0.12 mm at the
   RP's pins.
4. Clean-up: `drc_fix` removes router copper that breaks DRC (clearance, shorts, dangling, items in
   rule areas), then tidy, `fix_via_pairs`, GND stitching (a 4 mm grid, a 1.2 mm edge row, and a
   GND via within 1 mm of every signal via that has room for one), `check_vias`, 3D models,
   silkscreen, and the DRC gate.

Freerouting alone always left 19-21 links. Most of them are the bus between the fingers and the
translators, which the finisher closes. Its "violations" count is its own bookkeeping: KiCad's DRC
on its output found nothing for `drc_fix` to remove.

| Variant | What changed | Result |
|---|---|---|
| V1 | XIN, XOUT, XOUT_Y, SWCLK, SWDIO and DVDD pre-routed; XOUT through an in-ring via | XOUT and SWDIO open, 4 errors. Fixes below. |
| V2 | XOUT drawn on B.Cu; SWD pads reordered | Stopped after the pre-route: routed first, SWCLK's diagonal still walled SWDIO in |
| V3 | SWDIO pre-routed before SWCLK | RUN, the next escape in, walled in the same way: 1 open, plus a GND track in the antenna keep-out |
| V4 | The RP's east-side escapes left to Freerouting; microSD 1 mm east; `drc_fix` / `fix_silk` cover keep-outs and the board edge | **DRC 0 / 0 / 0.** But the buck's input loop closed through the planes, and the VREG_VOUT 1 uF sat 11.9 mm of copper from pin 45 |
| V5 | The buck's input loop drawn on F.Cu | Superseded before it finished |
| V6 | The DVDD capacitors on the ring's corner, no via in the path | Superseded before it finished |
| V7 | The two 27R in line with the pair, close to the chip; VREG_VIN 1 uF re-seated | UBRG_DM open: the USB-C's D- could not get out between its own pads and the ESD / CC parts behind it |
| V8 | The USB corridor behind the USB-C cleared of parts (the ESD diodes and CC resistors moved aside) | UBRG_DP open instead, the same squeeze |
| V9 | `gen_pcb.usbc_link` draws the connector's pair: D+ on F.Cu straight under the pads, the two D- pads (A7 / B7) joined through 0.5 / 0.25 mm vias on B.Cu; `fix_via_pairs` collapses a VBUS via pair closer than the hole rule | **DRC 0 / 0 / 0**, every layout check passes |
| V10 | The kicad-happy review: the SS34 (VBUS OR diode) and a fiducial were 0.35 / 0.25 mm from the body's long sides, where JLCPCB's rails would join. Both moved in (D7 under the CP2102N's divider, VBUS pad north, +5V pad south); `stitch_gnd` gives every signal via a GND via within 1 mm where there is room | the board shipped (below) |

The V1 fixes:

- the IOVDD 1 stub: along the pad axis first. Its straight diagonal passed 0.098 mm from pin 2.
- the 0.8 mm CONS_5V finger stubs start deeper in the finger. Their round ends reached 0.1 mm into
  the finger keep-out.
- the finisher now reads footprint rule areas (the S3 antenna).
- the RUN / SWDIO / SWCLK / GND pads are ordered by the escapes' own west-to-east order.

**What the variants taught:**

- **Escapes that turn together must be routed together.** Pre-routing them one at a time with a
  greedy router walls in the next one: SWDIO in V2, RUN in V3. Freerouting places all five
  north-turning escapes on the RP's east side at once.
- **Measure what the datasheet asks for, not just DRC.** V4 passed DRC with every link closed, yet:
  - the AP63203's input loop ran pad -> via -> In2 -> via -> capacitor and back through In1;
  - the RP2040's VREG_VOUT capacitor was 11.9 mm of copper (with two vias) from its pin;
  - the 27R sat 15 mm from the RP.

  `tools/audit/layout_checks.py` now measures each of these on the copper, and fails the build if
  one regresses.

## The board shipped (V10)

Built by `LAYOUT=1 tools/build_all.sh` from the floorplan above, from scratch:

- Freerouting left 19 links, as in every variant, all of them the bus between the fingers and
  the translators.
- The finisher closed 17 at once, and D5 / D6 on its neck-down pass.

| | |
|---|---|
| KiCad DRC, schematic parity, all severities | 0 violations, 0 unconnected, 0 parity issues |
| `tools/audit/layout_checks.py` | all 9 pass (below) |
| Tracks | 768 segments: 1504 mm on F.Cu, 982 mm on B.Cu; 0.2 mm signals, 54 segments necked to 0.15 mm at the QFNs |
| Vias | 758. 588 are GND: 427 from the stitching grid and edge row, 61 beside signal vias, the rest plane and exposed-pad vias. |
| Signal vias with no GND via within 1 mm | 30 of 93 (no room, or under the RP2040) |

What `layout_checks.py` measures on this copper:

| Claim | Measured |
|---|---|
| VREG_VOUT 1 uF / the two DVDD 100 nF from pin 45 | 5.3 / 7.1 / 8.9 mm, no via |
| VREG_VIN 1 uF from pin 44 | 3.0 mm |
| 27R from pins 46 / 47 | 2.3 / 5.5 mm |
| AP63203 VIN and GND to the 100 nF | 1.6 mm each on F.Cu, no via; 7.0 mm around the loop |
| XIN to the crystal | 4.4 mm |
| Exposed-pad vias | 9 in the RP2040's, 9 in the CP2102N's |
| USB skew (UBRG / S3 / RP) | 0.5 / 1.3 / 3.2 mm |
| S3 antenna keep-out | empty on every layer |
| S3 3V3 pin to its 100 nF / 22 uF | 2.3 / 4.6 mm |
