# FujiNet-StudioII Rev0: floorplan and routing study

**Two passes.** The first (V1-V4 below) laid out the RP2354B cart alone, in FliP's 83.49 mm outline,
with the ESP32-S3 on a separate board joined by USB. The second (S1-S2, at the end) put the ESP32-S3,
its microSD and a USB-C bridge on the cart. The board grew 28 mm taller for them: the console's slot is
open above, and the user accepted a larger cart. The RP half's floorplan, its locked copper and its
routing lessons carry over from the first pass unchanged.

How the board in `FujiNet-StudioII-Rev0.kicad_pcb` came to be laid out as it is. Everything below is
generated: `tools/placement.py` (floorplan), `tools/gen_pcb.py` (outline, pre-routed copper, planes),
`tools/route_board.sh` (routing), with the numbers re-measured by `tools/audit/layout_checks.py`.

## Constraints the floorplan starts from

1. **The edge** (`tools/edge_geom.py`): FliP's multicart v5.1 board, 90.912 x 83.49 mm, the full width
   entering the console (no tab). The 22 contacts are on B.Cu, every part on F.Cu, as on an original
   cart. Seen from F.Cu with the edge south, pin 1 (D7) is east:

   ```
   west                                                                                       east
   22 CS  21 /MRD  20 MA7  19 TPA  18-16 MA6-4  15 +5V  14-11 MA3-0 | 10-8 D0-D2  7 GND  6 ROM DIS  5-1 D3-D7
   ```

2. **The RP2354B's pin order** (`s2_cart.h`, fixed): GPIO0-9 = MA0-7, TPA, /MRD; GPIO16-23 = D0-D7.
   Both groups run counter-clockwise round the QFN-80.
3. **A flow-through buffer cannot reverse a bus.** A bus that meets one part's pins in one rotational
   order and another's in the opposite order needs crossings, whatever the parts' rotations; the
   74HCT541's A and Y rows are mirror images, so it passes order straight through. The edge runs the
   data group D7..D0 but the address group MA0..MA7 (west to east), opposite senses, while the RP
   runs both the same way. So one group must cross itself once, whichever face the contacts are on.
   (The schematic-stage README said the '541 "absorbs" the reversal; it cannot.)

## Decisions

| Decision | Why |
|---|---|
| RP2354B at rotation 90, in the middle | GPIO0-9 face south-west over the address fingers, GPIO16-23 south-east over the data fingers; the core regulator and USB face west (toward the USB-C at the top-left edge), the crystal and SWD east |
| '541 at rotation 270 over the data fingers, channels reversed (A8/Y8 = bit 0, `design.py`) | fingers -> Y row and A row -> GPIO16-23 both planar: the data bus needs no crossing |
| The 10 address lines twisted once, in the parts-free band above the fingers (`gen_pcb.address_twist`) | the reversal the bus needs, where nothing else is: each line rises from its finger on B.Cu to a level of its own, crosses on F.Cu, and rises into its 330R. East-going lines (/MRD, MA7, TPA, MA6, MA5, MA4) rise the last stretch on F.Cu; west-going lines (MA2, MA1, MA0) on B.Cu with a via under the resistor; MA3, already under its resistor, rises straight. An all-F.Cu rise forms a cycle: /MRD's level spans MA0's column and MA0's spans /MRD's |
| The ten 330R in one row at 1.98 mm in GPIO order (MA0 .. /MRD west to east) | the row -> RP fan-in is planar; 1.98 mm puts every column 0.99 mm off the finger grid, so no via of the twist sits beside a foreign column |
| Raspberry Pi's regulator corner grafted onto the QFN-80 (`tools/rpi_graft.py`) | the RP2350 datasheet (6.3.8): "The most critical part of an RP2350 PCB layout is the core voltage regulator ... these guidelines must be strictly followed". The QFN-60 and QFN-80 share the regulator / USB / OTP / QSPI_IOVDD pin run at the same pitch from the same corner, so the reference's 0402 parts and copper move by (+1.0, -1.5) and land exactly; the 4.7 uF, 33R, 27R and one 100 nF became 0402 for it (as on Fujiversal-Atari2600 Rev1) |
| F.Cu +3V3 and DVDD rings under the package (`gen_pcb.rp_support`) | the reference's own scheme, sized for the QFN-80: every supply pin stubs inward, so no supply pin needs a via among the bus pins (IOVDD 5 sits between GP7 and GP8, IOVDD 76 beside GP0) |
| No top GND pour over the regulator corner (`gen_pcb.REG_CUT`) | datasheet 6.3.8.1: no extra copper under the inductor, the switching loops "only connect to main GND at one point" -- the graft's PGND pour meets main GND through its own two vias |
| The glue east of the '541, the power block west by finger 15 | the RP's control pins (GPIO24-27) face east; CONS_5V (finger 15) drops into a small In2 island straight up to the P-FET |
| USB-C top-left, RESET / BOOTSEL / LED / debug header along the top edge | outside the console, reachable through the shell |

## Routing variants

| Run | Change | Freerouting (16 passes) | KiCad open after import | After the finisher | DRC |
|---|---|---|---|---|---|
| V1 | the floorplan above; crystal pre-routed (A*), SWD drawn | 39 "unrouted" (plane joins included), plateau from pass 5 | 5 | 2 (the +3V3 ring cut into islands) | 2 starved thermals (the top GND pour over the regulator corner) |
| V2 | a Freerouting-only keep-out under the RP2354B (`route.rp_keepout`): V1's router dropped five signal vias (TPA, MA6, D0, D6, /DRIVE) into the ring band; no top GND pour over the regulator corner | 40 | 4 | 1 (RP_D2, walled in at the '541's A row) | 0 violations |
| V3 | the data fan RP -> '541 drawn and locked (`gen_pcb.data_rp_fan`: parallel 45-degree diagonals 0.6 mm apart in c = x - y); C_IOV15 0.4 mm west so GP16 drops beside it | 48 | 3 | 0 | **0 / 0 / 0** with parity |
| V4 | layout_checks on V3: DVDD 51's 100 nF hung on the south B.Cu link, 15 mm from its pin. DVDD 51's and IOVDD 50's 100 nF are now 0402 straight out of their pins (between the debug UART and GPIO40); only DVDD 32's stays on the link | 48 | 3 | 0 | **0 / 0 / 0** with parity (the board in this folder) |

After V4, two fixes on the routed copper, both now in the pipeline so `LAYOUT=1` reproduces them:

- **The top GND pour's hole over the regulator corner** had been saved as one self-intersecting
  outline, which left a triangle of the pour unfilled (seen on the render). `route.pour()` now adds
  `REG_CUT` as a real hole of the outline (`route.py --repour` redraws the pours on a routed board).
- **One 0.12 mm neck** Freerouting left on /MRD by the NOR (U3) was below JLCPCB's standard 0.127 mm
  track (kicad-happy DFM-001). `tidy_tracks.py` now widens any unlocked track under 0.127 mm to 0.2,
  else 0.15, else 0.127 mm where it clears; that one went to 0.2 mm, DRC still 0 / 0 / 0.

V4 in numbers: 592 track segments (1240 mm on F.Cu, 802 mm on B.Cu), 531 vias of which 420 GND
(343 stitching: a 4 mm grid and an edge row, 311, plus 32 beside signal vias). 27 signal vias have no
GND via within 1 mm, for want of a legal spot: the '541's two fan-in rows (8), the RP2354B's
south-west address fan, its debug pins and USB D- beside the regulator corner (8), the USB-C's CC and
D- joins (5), and six in the glue, the twist and by BOOTSEL.

Lessons from the runs:

- KiCad exports F.Cu pours to Specctra as conduction "planes", and Freerouting drops other nets' vias
  into them. A KiCad rule area under the package would flag the locked ring copper itself, so the
  keep-out is injected into the DSN only (`tools/route.py`).
- The A* pre-route takes nets one at a time: its first SWD diagonal walled in the other two. The SWD
  escape is now drawn as a ribbon (`gen_pcb.swd_escape`).

## Second pass: the ESP32-S3 on the cart (S1-S7)

### What changed

| Decision | Why |
|---|---|
| The outline: FliP's from the insertion edge to the top of his straight sides, then 28 mm taller (111.49 mm), rounded top corners (`edge_geom.EXT_H`, `CART_H`, `TOP_R`) | room for the S3 half without crowding the RP; the edge, the notches, the post holes and the parts-free band stay FliP's. The original shell no longer fits: `case/board-anchors.scad` describes a printed one |
| The ESP32-S3-WROOM-1 in the middle of the new top edge, its antenna flush (0.2 mm in) | Espressif: the antenna at the board's edge, no copper under it. The module footprint's zone (the antenna plus 15 mm each side) is a 48 x 6 mm keep-out on every layer along the edge |
| The USB-C, its USBLC6 and the CP2102N west of the keep-out; the microSD east of it | the microSD beside the S3's SPI pins (right column); the UART and IO0 cross under the module on B.Cu to the bridge |
| The S3's USB pins (left column, IO19 / IO20) straight above the RP's USB corner | the RP <-> S3 link is ~40 mm, vertical |
| The S3's AP63203 buck below the band, west of the button row; its input loop drawn on F.Cu (`gen_pcb.buck_loop`, FujiNet-ChannelF Rev0's) | the input capacitor at VIN / GND with no via (AP63203 layout guide); its output caps over a lobe of the +3V3_S3 island |
| The TPS2116 mux where the P-FET was, by finger 15, at rotation 270, its north row (PR1, VIN1, VOUT, GND) facing the +5V plane and its south row (MODE, VIN2, VOUT, ST) the CONS_5V island; VOUT 2 / 7 and MODE / VIN1 joined under the body (`gen_pcb.mux_link`) | the console's 5 V (the cart's main source) stays short; S1 left both VOUT pins open at the 0.5 mm pitch |
| In2: +5V everywhere, islands for +3V3 (the RP and its LDO), +3V3_S3 (the top band) and CONS_5V | +5V feeds both regulators, the glue and the WS2812 from one plane; each 3.3 V rail is local to its MCU |
| The four buttons in one row under the S3 (S3 EN, BOOTSEL, RESET, S3 BOOT); the WS2812 and the RP's LED beside them | pinholes in the printed shell's face |
| TP_DVDD's link drawn before Freerouting (`gen_pcb.tp_dvdd_link`) | S1 / S2: neither router nor finisher reached the pad through the regulator corner |
| The USB-C's chain in one order end to end: the receptacle's D+ U / D- vias, the USBLC6 at 90 (D- west, D+ east), the CP2102N at 270 (D- / D+ on its top row); the USBLC6 -> CP2102N stretch drawn (`gen_pcb.bridge_link`) | S3-S6: any other combination makes the pair cross itself, and even in order the routers do not thread D- between the QFN's VDD and D+ pins |

### Routing runs

| Run | Change | Freerouting (16 passes) | KiCad open after import | After the finisher | DRC |
|---|---|---|---|---|---|
| S1 | the floorplan above | 57 "unrouted" (plane joins included) | 9 | 3 (the mux's two VOUT pins; TP_DVDD) | 2 dangling +3V3_S3 vias (the buck's output caps off the island) |
| S2 | the mux at rotation 270 with its under-body joins; the +3V3_S3 lobe; TP_DVDD pre-routed by the grid finisher | stopped: the finisher's pre-route left TP_DVDD open (it finds no way through the regulator corner's locked copper) | | | |
| S3 | TP_DVDD's link drawn (`gen_pcb.tp_dvdd_link`: a via south of the pad, B.Cu to the graft's DVDD via) | 52 | 4 | 0 | 5 clearance squeezes (0.075-0.11 mm) and one doubled via, all on the USB-C's D+ / D- between the receptacle and the USBLC6. layout_checks: the CP2102N's 100 nF 8.1 mm from VDD; the USB-C pair's skew 29 mm (the pair crossed itself) |
| S4 | the USBLC6 at rotation 270 (D+ west, D- east, under the receptacle's D+ U and D- vias) | stopped: the CP2102N's capacitors moved first | | | |
| S5 | the CP2102N's 100 nF / 4.7 uF at its VDD pins | 51 | 4 | 1: UBRG_DM ("no path") -- the CP2102N's west column takes D+ above D-, so D- had to cross D+ | 0 violations |
| S6 | the CP2102N at rotation 270 (D- / D+ on its top row, in the USBLC6's order; UART / RTS / DTR east, toward the S3 and the auto-program pair); the USBLC6 back at 90; a last drc_fix + finisher pass after the neck pass (`route_board.sh`) | 52 | 4 | 1: UBRG_DM again, now its last 4 mm (USBLC6 -> CP2102N): at the QFN's 0.5 mm pitch D- has to pass between VDD (6) and D+ (4) and no router threads it | 0 violations |
| S7 | that last stretch of both lines drawn (`gen_pcb.bridge_link`: D- drops past the USBLC6's GND pad, 45 degrees onto pad 5's column; D+ straight down, 45 degrees onto pad 4) | 52 | 4 | 0 | 0 violations, 0 unconnected, 0 parity issues; `check_vias` 0; `layout_checks` all pass |
| S8 | a check, not the board: `LAYOUT=1 tools/build_all.sh` from scratch with the final generator (every post-S7 fix below in `placement.py` / `gen_pcb.py` / the gates), in a scratch copy | 53 | 4 | 0 | 0 violations, 0 unconnected, 0 parity issues on the saved fills; `layout_checks` all pass (USBLC6 joins, its 100 nF 5.3 mm from pin 5, the pair 15.0 / 14.5 mm); `check_fab` 10 / 10 with the gerber short check; 704 vias |

### After S7: five fixes the gates had missed

The routed board is S7 with these corrections. Each one is now in the generator or the gates, so a fresh
`LAYOUT=1` run produces it, and the gate that should have caught it now does.

1. **The antenna keep-out was not enforced.** KiCad 10's DRC ignores a footprint's own keep-out zone once
   the project's footprint library is loaded. Without the library, the same board reports "items not
   allowed (keepout area of U6)"; with it, nothing. Two GND stitching vias sat inside the antenna area.
   - `gen_pcb.antenna_keepout()` now adds the area as board rule areas, on every copper layer.
   - The two vias were dropped. `layout_checks` 9 checks the area on the copper.
2. **A 20 mm D+ loop at the USBLC6.** The USBLC6 is flow-through: pins 4 and 3 are one line inside the
   package, but the router saw two pads to join. VBUS left pin 5 through the gap between pins 4 and 3,
   so Freerouting reached pin 3 by a loop round the USB-C receptacle.
   - `gen_pcb.bridge_link` now draws both twin-pin joins straight under the body, with VBUS dropping
     through a via between the pad rows.
   - The routed board was patched to match, VBUS joining the receptacle's on B.Cu.
   - `layout_checks` 7 checks the joins and that no USB line's copper has a loop. The 25 mm skew limit
     had let the loop pass.
   - **A further fix** came out of this one. With the loop gone, there was room for the 100 nF VBUS
     capacitor where ST's layout figure draws it, at the USBLC6's pin 5. It was ~9 mm away beside the
     receptacle (kicad-happy DC-001). It now sits east of the package, 5.3 mm of copper from pin 5
     (`placement.py`, `bridge_link`, `layout_checks` 7). The 1 uF stays at the receptacle.
3. **The USB-C sat 1.35 mm inside the top edge.** It had been placed with its origin 5.0 mm in, as on
   every board that shares the HRO footprint. HRO's layout puts the edge 5.79 mm in front of the pegs,
   so the shell face overhangs it by 0.46 mm; set back, a plug's overmold meets the board edge before
   the plug mates. This is FujiNet-NES Rev0's fix (63ccf57), applied here.
   - J4 moved 1.81 mm toward the edge (`placement.py`: `Y0 + 3.19`). Ten F.Cu stubs join the new pad
     centres to the untouched routing.
   - The footprint drops its front silk (past the edge) and marks HRO's edge on Dwgs.User.
   - The USB-C and microSD 3D models now sit on their measured origins (`set_models.py`).
   - `gen_pcb.check_parts_inside` allows the USB-C's courtyard past the top edge.
4. **The zip plotted stale zone fills.** `stitch_gnd.py` adds vias to the file after the last fill, and
   the gerbers are plotted from the saved fills, so 427 GND vias sat inside the In2 power pours. DRC ran
   with `--refill-zones`, which checks fresh fills in memory, and passed.
   - `tools/fill_zones.py` now refills and saves after the last copper change.
   - The DRC gate runs on the saved fills.
   - The gerber export passes `--check-zones`.
   - `check_gerbers.py` check 9 tests every plated hole against the plotted inner layers.

