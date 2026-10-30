# FujiNet-O2 Rev0

FujiNet for the Magnavox Odyssey 2 / Philips Videopac, on one cartridge.
- **RP2354B:** serves the 8048's cartridge bus straight off the 5 V edge (`fujinet-firmware/pico/o2`).
- **ESP32-S3:** the FujiNet (`fujiversal-o2`) and the RP2354B's USB host, on the same board.
- **Also on the board:** a microSD, a WS2812 status light, and a USB-C with a CP2102N bridge for flashing and powering it.

**Status (2026-10-30): board routed on 4 layers, JLCPCB package generated, every gate passing. Nothing has been built yet.**
- **Board:** 4 layers, 63 x 85 mm, bwack's / PicoPAC's Videopac outline (the whole bottom edge carries 2 x 15 gold fingers). Fully assembled by JLCPCB on the top side.
- **Firmware:** the schematic implements the PicoPAC pin map of `pico/o2/firmware/picopac_cart.c` as it stands on fujinet-firmware master. The changes the RP2354B and the S3 still need are under *Firmware changes this board needs*.
- **Edge:** checked against Dan Boris's pinout and three built, working Videopac carts (`tools/audit/edge_orientation.py`); not provisional.

| Check (2026-10-30) | Result |
|---|---|
| Drawing checks (`gen_sch.py`) | every sheet wired; 0 crossings on `cart-bus`, `rp-core`, `fujinet`, `power`; 1 on `usb` (esptool's auto-program pair, as on Studio II) |
| Netlist parity: kicad-cli netlist vs `design.py`, names included | 110 / 110 nets |
| KiCad ERC, all severities (kicad-cli, and again through the KiCad MCP) | 0 errors, 0 warnings |
| `tools/check_nets.py`: the netlist vs `picopac_cart.c`, `CMakeLists.txt`, `fujiversal-o2.h` (fujinet-firmware `origin/master`) | 438 checks, 0 failed; 5 NOTE lines (the firmware changes below) |
| `tools/audit/edge_orientation.py`: footprint and netlist vs Boris, bwack's board, PicoPAC's board, wilco2009's board | all pass (`VERIFIED = True`) |
| `tools/audit/margins.py`: 8048 levels both ways through the 330R, pin B, VSENSE, the mux threshold, the cart's draw | 0 negative margins (tightest: 0.00 V, a 5.5 V console line against the RP's 5.5 V FT limit, at the 8048's own Vcc ceiling) |
| Routing | 100 % on 4 layers: Freerouting, then the A* finisher; 424 vias, 1047 tracks |
| KiCad DRC + schematic parity on the saved zone fills (kicad-cli, and again through the KiCad MCP) | 0 errors, 0 unconnected, 0 parity issues; 3 silk-over-edge warnings (the S3 module's outline at the flush top edge) |
| `tools/check_vias.py`: no via in a foreign SMD pad | 424 vias, 0 failures |
| `tools/audit/layout_checks.py`: the layout's claims measured on the copper | 62 / 62 (regulator corner, decoupling through the supply rings, USB pairs and skew, crystal, exposed pads, every finger to its resistor in at most 7 vias, the CONS_5V island, the S3 antenna keep-out, the buck loop) |
| `tools/audit/check_gerbers.py`: the zip itself | 0 failures: outline, notches and posts, both finger rows, masks, inner layers, and no plated hole inside an In1 / In2 pour of another net (440 holes) |
| `tools/audit/check_fab.py`: BOM / CPL / drills / order-number text / gerbers / the edge gate | all pass |
| JLCPCB CPL rotations (`tools/audit/jlc/`), measured against each LCSC part's EasyEDA footprint | 38 (footprint, LCSC) pairs, the RP2354B's QFN-80 at 81 / 81 pins; 4 medium-confidence (AOTA inductor, TS-1187A, BAT54C, USB-C), as on the sister carts: check them in JLC's preview |
| kicad-happy 2.2.1 (`tools/audit/run_sch_audit.sh`, `run_pcb_audit.sh`), triaged in `docs/design-review-rev0.md` | SPICE 15 / 15; 5 high-rule groups: 3 false positives (keep-out boxes, the microSD at the edge by design, UMH3N decoupling), 1 minor (a USB_DM layer change without a GND via), 1 accepted (B.Cu bus over In2 island edges) |

## Sheets

Drawn the way FujiNet-StudioII and FujiNet-Arcadia Rev0 are (their drawing toolkit, their rp-core / fujinet / usb / power sheets):
- **Wires only:** every connection on a sheet is a wire.
- **Rails:** rails are power symbols (`GND`, `CONS_5V`, `VBUS`, `+5V`, `+3V3`, `+3V3_RP`, `DVDD`).
- **Between sheets:** the sheets join only through hierarchical labels, wired on the root's block diagram.

KiCad names the nets `/cart-bus/CA0` (a net on one sheet), `/USB_DP` (joined on the root) and `GND` (a rail). The tools compare the last path element. `tools/gen_sch.py` checks each sheet's connectivity as it draws it, the hierarchy against `design.py`, and the written netlist against `design.py` pin for pin.

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | the block diagram: rp-core <-> fujinet (USB_DP / USB_DM, RUN_CTL, BOOTSEL_CTL, S3_EN), fujinet <-> usb (S3_TXD / S3_RXD, S3_EN, S3_IO0); notes |
| 2 | `cart-bus` | the 30-finger edge and the RP2354B's GPIO unit row for row: the 28 console lines in GPIO order, each one straight wire through its resistor; pin B's pull-down; the console-5V sense divider (GP40), activity LED (GP25), self-test (GP29) and debug UART (GP44 / 45) pads |
| 3 | `rp-core` | the RP2354B's core unit: a capacitor at every supply pin, Raspberry Pi's regulator corner, crystal, SWD, RUN / BOOTSEL / RESET (the BAT54C to S3 EN), the USB 27R pair out to the S3 |
| 4 | `fujinet` | ESP32-S3-WROOM-1-N16R8, its EN RC and buttons, microSD, WS2812 |
| 5 | `usb` | USB-C, USBLC6-2SC6, CP2102N, esptool's auto-program pair |
| 6 | `power` | TPS2116 power mux (USB first, console 5 V second), the S3's AP63203 buck, the RP's AP2112K LDO, rail test pads |

## Edge connector

The Videopac port is 30 contacts in two rows of 15: **1-15** on one face and **A-R** (no I, O or Q) on the other, each letter directly behind its number. Seen from the 1-15 face with the contacts down, pin 1 (and pin A behind it) is at the left.

| Pin | Signal | Board net | Pin | Signal | Board net |
|---|---|---|---|---|---|
| 1 | T0 (the 8048's test input: cart -> console) | 330R -> GP27 | A | /WR | 330R -> GP23 |
| 2-9 | DB0-DB7 | 330R -> GP14-21 | B | GND on a G7000; the video-mixer input on a Videopac+ | 1k -> GP28, 10k to GND |
| 10 | A10 | 330R -> GP10 | C | GND | GND |
| 11 | P14 (the write select) | 330R -> GP24 | D | +5V | CONS_5V -> TPS2116 VIN2 |
| 12 | P11 (bank) | 330R -> GP12 | E | the external-RAM enable | 330R -> GP26 |
| 13 | P10 (bank) | 330R -> GP13 | F | /PSEN (reads the cart) | 330R -> GP22 |
| 14 | A11 | 330R -> GP11 | G-M | A0-A5 | 330R -> GP0-5 |
| 15 | A9 | 330R -> GP9 | N, P, R | A7, A6, A8 | 330R -> GP7, GP6, GP8 |

**Sources:**
- **Pinout:** Dan Boris, *Odyssey 2 Technical Specs* v1.1, section 2.0 (atarihq.com/danb/files/o2doc.pdf).
- **N = A7, P = A6.** Boris and the nets of all three built boards below agree. The comment in MAME's `bus/odyssey2/slot.h` has them swapped; it is not used.
- **Three built, working carts**, read from their design files (numbers and names only, no file copied):
  - bwack's Videopac_USBCART (LGPL-3.0): the edge footprint as placed in its board, and its nets;
  - aotta's PicoPAC (no licence; dimensions only): the same footprint and outline, its own nets, and the GPIO map our firmware inherited;
  - wilco2009's Videopac-micro-SD-Cart v2.2 (GPL-3.0, Eagle): its edge element and signals.
- `tools/audit/edge_orientation.py` checks the footprint and the netlist against all four. It passes, so `tools/edge_geom.VERIFIED` is True and the package is not provisional.

**Geometry (`tools/edge_geom.py`), bwack's / PicoPAC's:**
- 15 fingers per face at 55 / 14 = 3.9286 mm, 2.0 mm wide, from 0.5 mm in (the bevel) to 8.0 mm, 1.6 mm board;
- pins 1-15 on F.Cu (the parts face), A-R on B.Cu;
- the 63 x 85 mm outline: the whole bottom edge is the contact edge, its corners chamfered 2.0 x 2.5 mm; two 1.5 mm side notches (32.5-40.0 mm up on the left, 30.5-38.0 mm on the right, seen from the parts face); two 5.0 mm shell-post holes at +-27 mm, 25 mm up;
- no part closer than 20 mm to the edge (bwack's lowest part reaches 19.8 mm), none within 4.5 mm of a post.

**Not measured on an original cart (not gates):**
- **The pitch.** Built carts use 3.9286 (bwack, PicoPAC), 3.937 (Soeren Gust) and 3.96 mm (wilco2009), and all of them play. Over 14 pitches the difference is 0.45 mm, inside a 2 mm finger.
- **Which face carries the label** on an original cart. In PicoPAC's photos the 1-15 face faces the player in a G7000. The silkscreen marks both faces.

## RP2354B pin map

Exactly the PicoPAC map in `pico/o2/firmware/picopac_cart.c` (`A0_PIN` .. `TD_PIN`). `tools/check_nets.py` reads it from fujinet-firmware `origin/master` and checks every pin.

| GPIO | Net | Goes to |
|---|---|---|
| 0-11 | RP_A0-11 | 330R -> A0-A11 |
| 12, 13 | RP_P11, RP_P10 | 330R -> pins 12, 13 (the bank lines) |
| 14-21 | RP_D0-7 | 330R -> DB0-DB7 (`D0_PIN 14`) |
| 22, 23, 24 | RP_PSEN, RP_WR, RP_P14 | 330R -> pins F, A, 11 |
| 25 | RP_LED | 680R, red LED (`LED_PIN`) |
| 26, 27 | RP_EXTRAM, RP_T0 | 330R -> pins E, 1 (`NOTCS_PIN`, `TD_PIN`) |
| 28 | RP_VPB | 1k -> pin B (this board's addition) |
| 29 | SELFTEST | test pad |
| 40 | VSENSE | console 5 V through 10k / 15k (3.0 V at 5 V), 100 nF; ADC0, not 5 V tolerant |
| 44, 45 | DBG_TX, DBG_RX | test pads, 3.3 V |
| the rest | -- | not connected |
| USB | RP_USB_DP / DM | 27R -> the ESP32-S3's USB host (IO20 / IO19), on the board |
| RUN, QSPI_SS | | 10k pull-ups; RESET / BOOTSEL buttons; 1k from S3 IO4 / IO5 |

**Why the RP2354B:** the O2 needs 27 bus lines. On the QFN-80, GPIO0-39 are 5 V tolerant (RP2350 datasheet Table 1674, "Digital IO (FT)", 5.5 V while IOVDD is 3.3 V) and the ADC pins are GPIO40-47. On the RP2354A's QFN-60 only GPIO0-25 are; PicoPAC's map puts pin E and T0 on GP26 / 27.

**The bus pins:**
- IOVDD comes from its own fast LDO off the cart's +5V, so it rises with the console's rail.
- There is no buffer. The firmware drives DB0-DB7 while /PSEN is low and releases them otherwise, as it does on PicoPAC today.
- The 330R bounds the current into a pad while IOVDD rises, in the overlap after /PSEN rises, and into a console that is off (`tools/audit/margins.py`).

**Pin B.** On a G7000 it is GND (Boris). On the Videopac+ G7400 it is an input: low shows the 8245's graphics everywhere (normal), high lets the EF9340 mask them; about 20 Videopac+ titles want it high (MAME `odyssey2.cpp`, `hash/videopac.xml`). Here it is pulled down by 10k and reaches GP28 through 1k, so the firmware can raise it for those titles. A console that grounds it sees 3.3 mA.

## ESP32-S3 pin map

`include/pinmap/fujiversal-o2.h` (SD 38-41, UART0 43/44, LED strip 48), plus what every on-cart S3 board adds:

| S3 pin | Net | Goes to |
|---|---|---|
| IO19 / IO20 | USB_DM / USB_DP | the RP2354B's USB through its 27R (the S3 is the host) |
| IO38 / 39 / 40 / 41 | SD_MOSI / SCK / MISO / CS | microSD (SPI), 10k pull-ups on CS, DO, DAT1, DAT2 |
| IO42 | SD_CD | card detect, 10k pull-up (low = card in) |
| IO48 | LED_STRIP | 330R -> WS2812B-2020 (on +5V; VIH 2.7 V takes 3.3 V data) |
| TXD0 / RXD0 | S3_TXD / S3_RXD | CP2102N |
| IO4 / IO5 | RUN_CTL / BOOTSEL_CTL | 1k -> RP RUN / QSPI_SS: the S3 can reset the RP into its USB boot ROM |
| EN / IO0 | S3_EN / S3_IO0 | EN RC (10k / 1 uF), the buttons, RESET (through the BAT54C), the auto-program pair |

## Power

| Rail | Source | Feeds |
|---|---|---|
| `CONS_5V` | edge pin D (the console's 5 V) | TPS2116 VIN2, the VSENSE divider |
| `VBUS` | USB-C (USBLC6, 1 uF + 100 nF) | TPS2116 VIN1 (priority), CP2102N VBUS sense |
| `+5V` | **TPS2116 mux**: VBUS above 3.96-4.64 V first (MODE on VIN1, PR1 33k / 10k), else the console | the buck, the RP LDO, the WS2812 |
| `+3V3` | AP63203 3.3 V / 2 A buck | ESP32-S3, CP2102N, microSD |
| `+3V3_RP` | AP2112K-3.3 LDO | every RP2354B supply pin (IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN, VREG_AVDD through 33R) |
| `DVDD` | RP2350 core SMPS (3.3 uH) | RP core, 1.1 V |

**Mux behaviour:**
- **No back-feed:** the mux blocks reverse current both ways. A cart on USB never powers a console that is off.
- **Switchover:** break-before-make (~8 us); +5V's bulk carries the cart through it.

**Load:**
- **Console without USB: ~145 mA average, ~370 mA peak** at 5 V (`margins.py`).
- The console's 5 V regulator and its spare current are not published (forum figures only: a 12 VAC / 600 mA adapter on the Odyssey 2, 9 V DC / 1.1 A on the G7000).
- **Prefer USB-C power during play.** Bring-up step 3 checks the console's regulator with the cart drawing from it.

## Layout

- **Stack (4 layers, JLC04161H-7628):**
  - F.Cu: signals and GND pour (pins 1-15);
  - In1: GND plane;
  - In2: +5V plane with a +3V3 island (the S3 band along the top, and a strip down the right edge to the buck), a +3V3_RP island under the RP and its LDO, and a CONS_5V island from the +5V finger (D) up under the mux;
  - B.Cu: signals and GND pour (pins A-R).
  - Inner planes stop above the finger field. The finger field is a rule area on both faces (fingers only).
- **Placement (`tools/placement.py`):**
  - **Top-right:** the ESP32-S3, its antenna flush with the top edge over a band that is copper-free on every layer: the module footprint's own keep-out, 24 mm each side.
  - **Top-left:** the USB-C on the top edge, the USBLC6 and the CP2102N east of it (the CP2102N's D+ / D- face the USBLC6's flow-through pins); the microSD on the left edge under it.
  - **Top-middle:** the S3's two buttons and the WS2812.
  - **Centre:** the RP2354B at 90 degrees, Studio II's macro round it (decoupling north, crystal east, QSPI / BOOTSEL west, the SWD and RUN pads north-east). Raspberry Pi's regulator corner sits west-north-west, turned with it.
  - **Under the RP:** the 28 series resistors in two blocks, each in its pins' GPIO order west to east: address GP0-13 south-west, data and control GP14-28 south-east.
  - **West:** RESET and BOOTSEL, the RP's LDO, the TPS2116 mux by the +5V finger's column, the console-5V caps and VSENSE.
  - **East:** the S3's buck under the module.
  - **Band above the fingers (y 110-119.5):** parts-free (the shell's bottom). It carries the bus.
- **The bus crossing.** Seen from the parts face, the fingers have the data group west (on F.Cu) and the address group east (on B.Cu). The RP2354B's counter-clockwise GPIO order has them the other way round, at any rotation. So the groups cross between the resistor blocks and the fingers, on the two finger layers. Each group keeps its own order, apart from N / P (A7 / A6). The control lines (/WR, B, E, /PSEN, T0 at the west end; P14) cross both groups. The block positions are the one of seven trial placements whose route keeps every finger-to-resistor path at 7 vias or fewer.
- **The RP2354B core (FujiNet-StudioII Rev0's):**
  - every supply pin stubs inward to an F.Cu +3V3_RP or DVDD ring under the package; the +3V3_RP ring drops to In2 at its corners;
  - Raspberry Pi's regulator corner is grafted at the RP (`tools/rpi_core_graft.sexpr`). The F.Cu GND pour stays out of that corner, as their layout asks;
  - Freerouting is kept out from under the package by a DSN-only keep-out (`route.rp_keepout`).
- **Deterministic copper:**
  - the +5V finger's neck via into In2's CONS_5V island;
  - the TPS2116's under-body joins (`gen_pcb.mux_link`);
  - the north-side decoupling links (`cap_links`) and TP_DVDD's link (`tp_dvdd_link`).
- **Rev0 compromises, measured by `layout_checks`:**
  - The south side of the RP is all bus, so IOVDD 5 / 15 and DVDD 10 reach their capacitors (north of the RP) through the rings under the package: 14-15 mm (limit 17; 14 for every other supply pin).
  - The USB pair to the S3 is 37-40 mm (skew 2.9 mm, 19 ps at full speed).

## Parts

Every part is JLCPCB-assemblable. `FujiNet-O2-Rev0-BOM.csv` has every line with its MPN, manufacturer and LCSC code. Run `python3 tools/audit/sourcing.py` on order day.

**Stock (2026-10-30, `docs/sourcing.md`; triage in `docs/design-review-rev0.md`):** 41 lines, about USD 13.84 of parts per board; one line is short at JLCPCB.
- **Y1 ABM8-272-T3 (C20625731), the RP2350's 12 MHz crystal:** JLCPCB 0, LCSC 57.
  - Buy them into the JLCPCB parts inventory first (Parts Manager, "Order parts", from LCSC), or consign.
  - It is Raspberry Pi's minimal-design part (CL 10 pF; the 15 pF loads are sized for it), so a substitute is a decision to make deliberately.
- The RP2354B (C39843328, JLCPCB 90) and the AOTA core inductor (C42411119, JLCPCB 644) were in stock that day; both were short for the Arcadia two days earlier, so re-check.

## Ordering

`exports/jlcpcb/ORDER-JLCPCB.md`, generated with the board's own numbers:
- 4 layers, 1.6 mm, ENIG, gold fingers with a 30-degree bevel;
- Standard PCBA, top side;
- `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`, whose rotations and origins are measured against each LCSC part's EasyEDA footprint (`tools/audit/jlc/`).

## Firmware changes this board needs (not made here)

The board needs these changes in a fujinet-firmware PR off master:
1. **A board file:** `pico/o2/firmware/boards/fujio2_rp2354.{cmake,h}` (`PICO_PLATFORM rp2350`, the QFN-80, 2 MB stacked flash, an RP2350 clock), replacing `PICO_BOARD myboard` (`boards/pico.h`, an RP2040) and `PICO_FLASH_SIZE_BYTES=16777216`. Model it on `fujicade_rp2354` / the Studio II board.
2. **No 15 MB flash filesystem.** PicoPAC's `flash_fs.c` / `msc_disk.c` (the USB drag-and-drop ROM store) cannot fit in 2 MB. The FujiNet build does not need it: images come over the mailbox. Leaving it out under `CONFIG_FUJINET` also removes the A8PicoCart-derived files whose licence `PROVENANCE.md` flags.
3. **A VSENSE (GP40) serve gate:** never drive DB0-DB7 or T0 while the console is off (the cart on USB).
4. **RP2350-E9:** turn the bus pins' pulls off (P10 / P11 / P14 are quasi-bidirectional, weak when high), and pick the DB0-DB7 drive strength. Today T0 (GP27) is unused and keeps the RP's default pull-down, as on PicoPAC; with the pulls off it floats like an empty slot's.
5. **Pin B:** GP28 low by default; raise it per title for the Videopac+ games that need it.
6. **`include/pinmap/fujiversal-o2.h`:** `PIN_RP2040_RUN` 4, `PIN_RP2040_BOOTSEL` 5, `PIN_CARD_DETECT` 42, the real board's pins in place of the Freenove ones, and the `pico_*` keys in `platformio-fujiversal-o2.ini`, so the S3 embeds the RP image and flashes it over PICOBOOT.

`tools/check_nets.py` prints a NOTE line for 1, 2, 5 and 6 until they are done.

## Known limits

- **No Voice passthrough.** The Voice reuses pins A, B, E, 1, 10 and 11 and passes only P10 / P11 through, so a cart behind it cannot use /WR, E, T0, A10 or P14. FujiNet's mailbox needs /WR and P14.
- **The original shell.** The outline fits bwack's / PicoPAC's shells, but the USB-C and the microSD sit on the board's top and left edges, inside an original shell: cut openings, or print a shell (not drawn yet; `case/board-anchors.scad` holds the positions).

## Bring-up checklist

1. **Rails, with no console:** USB-C only. Check +5V, +3V3 and +3V3_RP at the test pads, and DVDD at TP_DVDD. The RP enumerates to the S3, and the WS2812 lights.
2. **First flash of the RP:** SWD pads (SWCLK, SWDIO, GND) with a Raspberry Pi Debug Probe. After that the S3 re-flashes it over PICOBOOT (firmware change 6).
3. **The console's supply:** the cart in a console, no USB. Measure CONS_5V under WiFi load and feel the console's regulator; then add USB and check the mux hands over (TP_5V).
4. **The bus:** the `fujitest` client served by the RP shows the FujiNet's SSID on the TV (milestone 1 in `pico/o2/README.md`).
5. **Console off with USB on:** confirm DB0-DB7 and T0 stay released once firmware change 3 is in. Probe a data finger.

## Regenerating

You need KiCad 10 and Python 3 with numpy. For `LAYOUT=1` you also need Java and Freerouting 2.4.1 (`~/.local/share/freerouting/freerouting-2.4.1.jar`). `check_nets.py` reads fujinet-firmware from `$FUJINET_FIRMWARE` (default `~/Workspace/fujinet-firmware`) at `$FUJINET_FIRMWARE_REF` (default `origin/master`).

```sh
tools/build_all.sh                 # schematic, ERC, check_nets, BOM / PDF (keeps the routed board)
LAYOUT=1 tools/build_all.sh        # + place, route, DRC, the JLCPCB package and the fab gates
tools/audit/run_sch_audit.sh       # kicad-happy schematic stage (analysis/, gitignored)
tools/audit/run_pcb_audit.sh       # kicad-happy PCB stage
```

Everything is generated from `tools/design.py` (the circuit), `tools/sch_layout.py` (the drawing), `tools/placement.py` (the layout) and `tools/edge_geom.py` (the edge). Edit those, never the KiCad files.

## Provenance and licence

**CERN-OHL-W-2.0.**
- **This repository:**
  - the pipeline, the cart side (330R into the FT pads, VSENSE), the S3 half, the USB-C and the power mux come from FujiNet-Arcadia Rev0, and through it from Fujiversal-Atari2600 Rev1 and FujiNet-StudioII Rev0;
  - the RP2354B core, its supply rings and its drawing come from FujiNet-StudioII Rev0.
- **The regulator corner:** Raspberry Pi's RP2350 minimal design (MIT, `tools/RPI-MINIMAL-LICENSE.txt`), moved onto the QFN-80 by FujiNet-StudioII's `tools/rpi_graft.py`: its parts, its copper and the RPI_* footprints.
- **The edge:** Dan Boris's pinout; the geometry read from bwack's (LGPL-3.0), PicoPAC's (unlicensed) and wilco2009's (GPL-3.0) board files. Numbers and names only: no file from those projects is in this repository.
- **The pin map:** `fujinet-firmware` `pico/o2` (PicoPAC's, used with Andrea Ottaviani's permission; see its `PROVENANCE.md`) and `include/pinmap/fujiversal-o2.h`.
- **Symbols:** official KiCad libraries (CC-BY-SA 4.0 with exception); project symbols: the edge, the RP2354B in two units, the ESP32-S3-WROOM-1 by function, the microSD, the USB-C 16P by function.
- **3D models:** `3d/README.md`.
