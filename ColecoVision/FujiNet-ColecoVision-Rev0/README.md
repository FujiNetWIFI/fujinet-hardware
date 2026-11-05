# FujiNet-ColecoVision Rev0

FujiNet for the ColecoVision (and the ADAM's cartridge slot), on one cartridge.
- **RP2350A + W25Q16:** serves the Z80's cartridge bus (`fujinet-firmware/pico/coleco`): A0-A14 straight off the 5 V edge, D0-D7 through a 74LVC245A whose /OE is the AND of the four cart selects.
- **ESP32-S3:** the FujiNet (`fujiversal-coleco`) and the RP's USB host, on the same board.
- **Also on the board:** a microSD, a WS2812 status light, and a USB-C with a CP2102N bridge for flashing and powering it.

**Status (2026-11-05): board routed on 4 layers, JLCPCB and PCBWay packages generated, every gate passing. Nothing has been built yet.**
- **Board:** 4 layers, 40.2 x 82.4 mm, the ColecoVision cart outline (the whole bottom edge carries 2 x 15 gold fingers), four side notches for the shell's ribs. Assembled by JLCPCB or PCBWay, top side only.
- **Firmware:** the schematic implements `pico/coleco/firmware/include/coleco_cart.h` as it stands on fujinet-firmware master. The board file and S3 pin map it still needs are under *Firmware changes this board needs*.
- **Edge:** checked against MAME's slot table and two built, open carts (`tools/audit/edge_orientation.py`); not provisional.
- **Shell:** fits a printed shell (`case/`). An original Coleco shell is unverified: see *Original shell*.

| Check (2026-11-05) | Result |
|---|---|
| Drawing checks (`gen_sch.py`) | every sheet wired; 0 crossings on `cart-bus`, `rp-core`, `fujinet`, `power`; 1 on `usb` (esptool's auto-program pair, as on Studio II and the O2) |
| Netlist parity: kicad-cli netlist vs `design.py`, names included | 112 / 112 nets |
| KiCad ERC, all severities | 0 errors, 0 warnings |
| `tools/check_nets.py`: the netlist vs `coleco_cart.h`, `fujiversal-coleco.h` (fujinet-firmware `origin/master`) | 390 checks, 0 failed; 3 NOTE lines (the firmware changes below) |
| `tools/audit/edge_orientation.py`: footprint and netlist vs MAME's slot table, ThatOldNerd's and Commodore-Bench's boards | all pass (`VERIFIED = True`) |
| `tools/audit/margins.py`: Z80 / LS138 levels against the 330R, the LVC parts and the RP, the select-to-buffer timing, VSENSE, the mux threshold, the cart's draw | 0 negative margins (tightest: +0.11 V, the mux's VBUS threshold under a 4.75 V USB source) |
| Routing | 100 % on 4 layers (see *Layout*); 390 vias, 1136 tracks |
| KiCad DRC + schematic parity on the saved zone fills (kicad-cli, and again through the KiCad MCP) | 0 errors, 0 unconnected, 0 parity issues; 3 silk-over-edge warnings (the S3 module's outline at the flush west edge) |
| `tools/check_vias.py`: no via in a foreign SMD pad | 378 vias, 0 failures |
| `tools/audit/layout_checks.py`: the layout's claims measured on the copper | 56 / 56 (regulator corner, decoupling, USB pairs and skew, crystal, QSPI, exposed pads, every finger to its part in at most 4 vias, the CONS_5V island, the S3 antenna strip, the buck loop) |
| `tools/audit/check_gerbers.py`: the zip itself | 0 failures: outline and notches, both finger rows, masks, inner layers, no plated hole inside an In1 / In2 pour of another net (403 holes) |
| `tools/audit/check_fab.py`: JLC and PCBWay BOM / CPL / centroid / drills / order-number text / gerbers / the edge gate | all pass |
| JLCPCB CPL rotations (`tools/audit/jlc/`), measured against each LCSC part's EasyEDA footprint | 43 (footprint, LCSC) pairs, the RP2350A's QFN-60 high-confidence; 6 medium (the two AND gates, AOTA inductor, TS-1187A, BAT54C, USB-C): check them in JLC's preview |
| kicad-happy 2.2.1 (`tools/audit/run_sch_audit.sh`, `run_pcb_audit.sh`), triaged in `docs/design-review-rev0.md` | SPICE 14 / 14; 8 high-rule groups: 3 false positives or by design (keep-out boxes, the fiducial and connectors at the edge, UMH3N decoupling), 1 not a split (+3V3_RP fills as one piece), 3 accepted or minor (bus over In2 island edges, USB layer changes, the USB pair across islands), 1 minor (the USBLC6's VBUS cap 9 mm away) |
| Printed shell (`case/`, OpenSCAD) | `check` and `parts_check` empty, `parts_control` 86 volumes |

## Sheets

Drawn with the FujiNet-StudioII / Arcadia / O2 toolkit:
- **Wires only:** every connection on a sheet is a wire.
- **Rails:** rails are power symbols (`GND`, `CONS_5V`, `VBUS`, `+5V`, `+3V3`, `+3V3_RP`, `DVDD`).
- **Between sheets:** the sheets join only through hierarchical labels, wired on the root's block diagram.

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | the block diagram: rp-core <-> fujinet (USB_DP / USB_DM, RUN_CTL, BOOTSEL_CTL, S3_EN), fujinet <-> usb (S3_TXD / S3_RXD, S3_EN, S3_IO0); notes |
| 2 | `cart-bus` | the 30-finger edge and the RP2350A's GPIO unit row for row: A0-A14 straight through the four 330R arrays; D0-D7 straight through the 74LVC245A; DIR (GP27) from the buffer's foot with its pull-up; the four selects, pulled up, into the 74LVC1G11 + 74LVC1G08, whose /CE rises into the buffer's /OE and runs on to GP26; the console-5V sense (GP28), the activity LED (GP25), the bring-up pads (GP23, GP24, GP29) |
| 3 | `rp-core` | the RP2350A's core unit: a capacitor at every supply pin, Raspberry Pi's regulator corner, the W25Q16 standing over the QSPI pins, crystal, SWD, RUN / BOOTSEL / RESET (the BAT54C to S3 EN), the USB 27R pair out to the S3 |
| 4 | `fujinet` | ESP32-S3-WROOM-1-N16R8, its EN RC and BOOT button, microSD, WS2812 |
| 5 | `usb` | USB-C, USBLC6-2SC6, CP2102N, esptool's auto-program pair |
| 6 | `power` | TPS2116 power mux (USB first, console 5 V second), the S3's AP63203 buck, the RP's AP2112K LDO, rail test pads |

## Edge connector

30 contacts in two rows of 15 at 2.54 mm. The **even pins** are on the component face, the **odd pins** behind them (pin 1 behind pin 2). Seen from the component face with the contacts down, pins 1 / 2 are at the left.

| Pin | Signal | Board net | Pin | Signal | Board net |
|---|---|---|---|---|---|
| 1, 3, 5 | D2, D1, D0 | '245 A2, A1, A0 | 2 | /C000 | 10k up; 74LVC1G11 |
| 7, 9, 11 | A0, A1, A2 | 330R -> GP0-2 | 4-12 | D3-D7 | '245 A3-A7 |
| 13 | SHLD (ADAM: RF ground) | GND | 14, 16 | A11, A10 | 330R -> GP11, GP10 |
| 15, 17 | A3, A4 | 330R -> GP3, GP4 | 18 | /8000 | 10k up; 74LVC1G11 |
| 19 | A13 | 330R -> GP13 | 20 | A14 | 330R -> GP14 |
| 21-25 | A5, A6, A7 | 330R -> GP5-7 | 22 | /A000 | 10k up; 74LVC1G11 |
| 27 | /E000 | 10k up; 74LVC1G08 | 24, 26, 28 | A12, A9, A8 | 330R -> GP12, GP9, GP8 |
| 29 | GND | GND | 30 | +5V | CONS_5V -> TPS2116 VIN2 (this finger starts 1.5 mm in: it mates last) |

No /RD, /WR, A15, clock or reset reach the cart. The selects come from the console's '138, enabled by /MREQ and RFSH: a write selects as a read does, refresh never.

**Sources:**
- **Pinout:** MAME `src/devices/bus/coleco/cartridge/exp.h`, the same as the Coleco ADAM Technical Reference Manual's J1 (CS1*-CS4* = /8000 /A000 /C000 /E000).
- **Two built, open carts**, read from their design files (numbers and names only, no file copied): ThatOldNerd's Coleco-Game-Cart V4 (GPL-3.0, Eagle) and Commodore-Bench's ColecoVision Reprogrammable Flash Card (MIT, KiCad; aotta's PiCOLECO uses the same footprint). Joe Grand's "Pixels Past" cart ("fits standard housing") for the width and the notches.
- `tools/audit/edge_orientation.py` checks the footprint and the netlist against all of them (and a local MAME tree when there is one). It passes, so `tools/edge_geom.VERIFIED` is True.

**Geometry (`tools/edge_geom.py`):**
- 15 fingers per face at 2.54 mm, 1.6 mm wide, from 0.5 mm in (the bevel) to 8.5 mm; the +5V finger from 1.5 mm (Commodore-Bench's practice: GND mates first); 1.6 mm board (the slot takes 1.57 +- 0.2 mm);
- the 40.2 x 82.4 mm outline: built carts are 40.0-40.64 wide; Commodore-Bench's / PiCOLECO's length, so the USB-C and the microSD reach the shell's top wall;
- four 2.0 mm side notches at the widest published spans (ThatOldNerd's): 19.6-26.0 mm up on both sides, 34.0-40.5 (pin-1 side) and 36.5-43.0 (pin-30 side);
- no part closer than 15 mm to the edge (ThatOldNerd's lowest pads sit at 15, Commodore-Bench's lowest parts at 17).

## RP2350A pin map

Exactly `coleco_cart.h`. `tools/check_nets.py` reads it from fujinet-firmware `origin/master` and checks every pin.

| GPIO | Net | Goes to |
|---|---|---|
| 0-14 | RP_A0-14 | 330R -> A0-A14 (`ADDR_MASK` 0x7FFF; 5 V-tolerant pads) |
| 15-22 | RP_D0-7 | the 74LVC245A's B port (`D0_PIN` 15) |
| 23 | GP23 | test pad (spare) |
| 24 | DBG_TX | test pad, UART1 TX, 3.3 V |
| 25 | RP_LED | 680R, red LED (`PICO_DEFAULT_LED_PIN`) |
| 26 | CART_CE_N | the AND of /8000 /A000 /C000 /E000 (`CE_PIN`), also the '245's /OE |
| 27 | BUF_DIR | the '245's DIR, 1 = console -> cart (`DIR_PIN`), 10k pull-up |
| 28 | VSENSE | console 5 V through 10k / 15k (3.0 V at 5 V), 100 nF (`PWR_PIN`, read as a digital input) |
| 29 | SELFTEST | test pad |
| QSPI | QSPI_SS / SCLK / SD0-3 | W25Q16JV (2 MB), its /CS the BOOTSEL strap |
| USB | RP_USB_DP / DM | 27R -> the ESP32-S3's USB host (IO20 / IO19), on the board |
| RUN, QSPI_SS | | 10k pull-ups; RESET / BOOTSEL buttons; 1k from S3 IO4 / IO5 |

**The bus side.** core1 drives GP15-22 off the bare address on every cycle, RAM and BIOS cycles included (`coleco_cart.c`), so the data buffer's /OE must be the hardware select: the 74LVC1G11 + 74LVC1G08 AND the four selects (no 74LVC21 is stocked at JLCPCB). The '245 and the gates run at 3.3 V with 5 V-tolerant inputs (`coleco_cart.h` asks for an LVC part, not HCT). DIR's pull-up keeps the buffer facing the RP while the RP is in reset, and the firmware holds it there while the console is off (its unpowered '138 reads as every select low). `tools/audit/margins.py` has the levels and the timing (the gates and the buffer's enable add under 30 ns against the ~285 ns the firmware has after /CE falls).

**Why the RP2350A + W25Q16:** on 2026-11-04 the RP2354A (C41378174) and RP2354B (C39843328), the stacked-flash parts the sister carts use, were out of stock at JLCPCB and LCSC; the RP2350A (C42411118) and the W25Q16JVUXIQ (C2843335) were in stock. The QFN-60's GPIO0-25 are 5 V tolerant; GP26-28 (/CE, DIR, PWR) only ever see 3.3 V. The RP2350's 520 KB SRAM lifts the firmware's 128K image cap (an RP2040 limit).

## ESP32-S3 pin map

`include/pinmap/fujiversal-coleco.h` (SD 38-41, UART0 43/44, LED strip 48), plus what every on-cart S3 board adds:

| S3 pin | Net | Goes to |
|---|---|---|
| IO19 / IO20 | USB_DM / USB_DP | the RP2350A's USB through its 27R (the S3 is the host) |
| IO38 / 39 / 40 / 41 | SD_MOSI / SCK / MISO / CS | microSD (SPI), 10k pull-ups on CS, DO, DAT1, DAT2 |
| IO42 | SD_CD | card detect, 10k pull-up (low = card in) |
| IO48 | LED_STRIP | 330R -> WS2812B-2020 (on +5V; VIH 2.7 V takes 3.3 V data) |
| TXD0 / RXD0 | S3_TXD / S3_RXD | CP2102N |
| IO4 / IO5 | RUN_CTL / BOOTSEL_CTL | 1k -> RP RUN / QSPI_SS: the S3 can reset the RP into its USB boot ROM |
| EN / IO0 | S3_EN / S3_IO0 | EN RC (10k / 1 uF), RESET (through the BAT54C), the BOOT button, the auto-program pair |

There is no separate S3 EN button (the sister carts have one): RESET pulls EN low through the BAT54C, and the 40 mm board has no room for a fourth switch.

## Power

| Rail | Source | Feeds |
|---|---|---|
| `CONS_5V` | edge pin 30 (the console's 5 V) | TPS2116 VIN2, the VSENSE divider |
| `VBUS` | USB-C (USBLC6, 1 uF + 100 nF) | TPS2116 VIN1 (priority), CP2102N VBUS sense |
| `+5V` | **TPS2116 mux**: VBUS above 3.96-4.64 V first (MODE on VIN1, PR1 33k / 10k), else the console | the buck, the RP LDO, the WS2812 |
| `+3V3` | AP63203 3.3 V / 2 A buck | ESP32-S3, CP2102N, microSD |
| `+3V3_RP` | AP2112K-3.3 LDO | every RP2350A supply pin, the W25Q16, the 74LVC245A and the AND gates |
| `DVDD` | RP2350 core SMPS (3.3 uH) | RP core, 1.1 V |

**Load:** without USB, ~145 mA average and ~370 mA in WiFi bursts at 5 V (`margins.py`). The ADAM's Technical Reference Manual rates its cart slot at "typical available current 0.2A"; the ColecoVision's figure is not published. **Prefer USB-C power during play.** The mux blocks reverse current both ways: a cart on USB never powers a console that is off.

## Layout

- **Stack (4 layers, JLC04161H-7628):** F.Cu signals + GND pour (even fingers); In1 GND; In2 +5V with a +3V3 island (the upper half: module, CP2102N, microSD, buck output, and a tongue under the module's foot for its decoupling), a +3V3_RP island (the lower half: RP, flash, bus logic, LDO output), a DVDD island under the RP's core, and a CONS_5V strip from the +5V finger up the east edge to the mux; B.Cu signals + GND pour (odd fingers). Inner planes stop above the finger field; the finger field is a rule area on both faces.
- **Placement (`tools/placement.py`):**
  - **Top edge:** the USB-C (west of centre) and the microSD (east), both reaching the shell's top wall; the CP2102N block between the USB-C and the module.
  - **Upper body:** the ESP32-S3 turned 90 degrees, its antenna flush with the west edge over a strip that is copper-free on every layer, 15 mm either side of the module's centre line (the footprint's own keep-out is 24 mm: narrowed here, the board is 40 mm wide); east of it the buck, RESET and S3 BOOT, the WS2812.
  - **Lower body:** the RP2350A at 90 degrees in FujiNet-Arcadia Rev0's neighbourhood (decoupling north, crystal east, Raspberry Pi's regulator corner west, turned with it), the W25Q16 west of it where Raspberry Pi's minimal design has its flash; the four address arrays under it in GPIO order, inputs toward the fingers; the 74LVC245A in the south-west corner, straight over the data fingers (the edge's D0-D7 are its west end; GP15-22's lines cross under the address lines); the select pull-ups and the AND pair east of the arrays, with the bring-up pads; the mux by the +5V finger's column; BOOTSEL on the west edge.
  - **Band above the fingers (y 115-120.5):** parts-free (the shell's bottom). It carries the buses.
- **Deterministic copper:** Raspberry Pi's regulator corner (`tools/rpi_core_graft.sexpr`) and the under-package +3V3_RP bar / DVDD vias (`gen_pcb.rp_ring`, FujiNet-Arcadia Rev0's); the finger neck vias (the +5V finger's into the CONS_5V island, 1.6 mm above the GND finger's behind it); the TPS2116's under-body joins (`gen_pcb.mux_link`); the CP2102N's VDD / VREGIN join (`gen_pcb.uart_link`), clear of D-'s entry.
- **Routing order** (`tools/route_board.sh`):
  1. the 27 edge nets and the USB pair, with the grid router, locked (`placement.PRE_ROUTE`): Freerouting never enters a finger's neck;
  2. the W25Q16's six QSPI lines alone in Freerouting, locked (`placement.FR_FIRST`, `tools/fr_subset.py`): in the full run, B.Cu through-traffic crosses the flash corner and walls one of them out;
  3. Freerouting, then the grid router for what it leaves.

**Rev0 compromises** (measured; `docs/design-review-rev0.md`):
- **QSPI_SD2 / QSPI_SS** go round the W25Q16's far row: 22 and 24 mm against SCLK's 9.5 mm (about 90 ps).
- **Decoupling:** the W25Q16's 100 nF is 6.3 mm from VCC, the CP2102N's 6.2 mm; the buck's 100 nF 6.4 mm from VIN (its 22 uF at 3.3 mm).
- **RP_A1** is laid by hand between RP_A0 and RP_A2 (0.15 mm): no router run joined it.
- **The board is not reproduced by `LAYOUT=1`.** Routing results vary run to run; this board came from about twenty isolated placement variants (rsync + TMPDIR each), the one that came closest, plus RP_A1. `LAYOUT=1` regenerates and routes a new board, which may leave a link open.

## Parts

Every part is JLCPCB-assemblable. `FujiNet-ColecoVision-Rev0-BOM.csv` has every line with its MPN, manufacturer and LCSC code. Run `python3 tools/audit/sourcing.py` on order day.

**Stock (2026-11-05, `docs/sourcing.md`; triage in `docs/design-review-rev0.md`):** 45 lines, about USD 15.38 of parts per board; two lines are short at JLCPCB.
- **U11 AP63203WU-7 (C780769), the S3's 3.3 V buck:** JLCPCB 0, LCSC 0 (79 a day earlier). Consign it, use JLC Global Sourcing, or order from PCBWay, which sources by MPN.
- **L1 AOTA-B201610S3R3-101-T (C42411119), the RP2350's core inductor:** JLCPCB 1, LCSC 0. The TDK VLS201610HBX-3R3M-1 (C695624, JLCPCB 343) fits the footprint, but Raspberry Pi specifies the polarity-marked AOTA: a deliberate decision.
- The RP2350A (C42411118, JLCPCB 3481) and the W25Q16JVUXIQ (C2843335, 2877) were in stock.

## Ordering

- **JLCPCB:** `exports/jlcpcb/ORDER-JLCPCB.md`: 4 layers, 1.6 mm, ENIG, gold fingers with a 30-degree bevel; Standard PCBA, top side (Economic PCBA stops at 0.5 mm pitch and takes no gold fingers); `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`, whose rotations and origins are measured against each LCSC part's EasyEDA footprint (`tools/audit/jlc/`).
- **PCBWay:** `exports/pcbway/ORDER-PCBWay.md`: the same board options, turnkey assembly by MPN (`BOM-PCBWay.csv`), KiCad's own centroid (`Centroid-PCBWay.csv`) and `Assembly-top.pdf`.

## Printed shell

`case/FujiNet-ColecoVision-Shell.scad`, with `case/FujiNet-ColecoVision-Shell.stl` (both halves and the RESET plunger, laid out for printing) and the dimension dossier `case/case-spec.md`.
- **Size:** 82 x 97 x 19 mm, a reproduction shell's outside (PiCOLECO's, measured only). The skirt below the fingers is open for the console's connector.
- **Holding the board:** a ledge under B.Cu, keys through the four side notches, ribs on F.Cu; four M2.5 screws through bosses beside the board.
- **Openings:** the USB-C and the microSD in the top wall; a RESET plunger, pin-holes for BOOTSEL and S3 BOOT, LED windows; label recesses on both faces.
- **Checked in OpenSCAD:** the board, the plunger and every part's courtyard (to its height) clear both halves; a raised control does not.
- **Estimated, not measured:** how far the console's connector reaches into the skirt, and its body's size. Fit one print before printing more.

## Original shell

The outline (width, notches) is the built carts', so an original Coleco shell's ribs should take the board. Not verified:
- **The length.** 82.4 mm is proven only in printed shells (PiCOLECO's). Joe Grand's 58.7 mm board "fits standard housing"; an AtariAge thread on new shells says longer boards need holes for the shell's extrusions.
- **Posts.** ThatOldNerd's 56.5 mm board has two 3.4 mm holes 50.5 mm up (5.5 / 6.0 mm in from the sides); Joe Grand's board has none across that spot. This board has none: the ESP32-S3 module sits there.
- **The label face** (the component face, by sparkletron's manual).
- **The openings:** an original's top wall is closed; cut it for the USB-C and the microSD (`case/case-spec.md`, *An original shell*).

## Firmware changes this board needs (not made here)

A fujinet-firmware PR off master:
1. **A board file:** `pico/coleco/firmware/boards/fujicoleco_rp2350a.{cmake,h}` (`PICO_PLATFORM rp2350`, the RP2350A with a 2 MB W25Q16 on QSPI (W25Q080-compatible boot2, as a Pico 2), `PICO_DEFAULT_LED_PIN 25`, an RP2350 clock), beside the stock-Pico `fujicoleco`. The pin map is unchanged.
2. **A bigger image store** on the RP2350 (`FUJI_STORE_RAM_SIZE`: 520 KB of SRAM lifts the 128K cap), with `checksram` still passing.
3. **RP2350-E9:** the bus pins' pulls off.
4. **`include/pinmap/fujiversal-coleco.h`:** `PIN_RP2040_RUN` 4, `PIN_RP2040_BOOTSEL` 5, `PIN_CARD_DETECT` 42, and the `pico_*` keys in `platformio-fujiversal-coleco.ini`, so the S3 embeds the RP image and flashes it over PICOBOOT.

`tools/check_nets.py` prints a NOTE line for 1 and 4 until they are done.

## Known limits

- **The ESP32-S3 antenna** has 6 mm of copper-free board either side of the module (15 mm from its centre line), not Espressif's 15 mm either side: the board is 40 mm wide. Check WiFi range at bring-up.
- **Console power.** WiFi bursts exceed the ADAM slot's 0.2 A typical rating; use USB-C power where possible.
- **The original shell** (see above).

## Bring-up checklist

1. **Rails, with no console:** USB-C only. Check +5V, +3V3 and +3V3_RP at the test pads. The RP enumerates to the S3, and the WS2812 lights.
2. **First flash of the RP:** SWD pads (SWCLK, SWDIO, GND) with a Raspberry Pi Debug Probe. After that the S3 re-flashes it over PICOBOOT (firmware change 4).
3. **The console's supply:** the cart in a console, no USB. Measure CONS_5V under WiFi load and feel the console's regulator; then add USB and check the mux hands over (TP_5V).
4. **The bus:** CONFIG on the TV (the `pico/coleco` milestones). Probe /CE (the GP26 test point is the '245's /OE) against a select finger.
5. **Console off with USB on:** confirm the '245 stays facing the RP (DIR high) and nothing drives the data fingers.

## Regenerating

You need KiCad 10 and Python 3 with numpy. For `LAYOUT=1` you also need Java and Freerouting 2.4.1 (`~/.local/share/freerouting/freerouting-2.4.1.jar`). `check_nets.py` reads fujinet-firmware from `$FUJINET_FIRMWARE` (default `~/Workspace/fujinet-firmware`) at `$FUJINET_FIRMWARE_REF` (default `origin/master`). OpenSCAD 2021 for the shell.

```sh
tools/build_all.sh                 # schematic, ERC, check_nets, BOM / PDF (keeps the routed board)
LAYOUT=1 tools/build_all.sh        # + place, route, DRC, the JLCPCB / PCBWay packages and the fab gates
tools/audit/run_sch_audit.sh       # kicad-happy schematic stage (analysis/, gitignored)
tools/audit/run_pcb_audit.sh       # kicad-happy PCB stage
```

Everything is generated from `tools/design.py` (the circuit), `tools/sch_layout.py` (the drawing), `tools/placement.py` (the layout) and `tools/edge_geom.py` (the edge). Edit those, never the KiCad files.

## Provenance and licence

**CERN-OHL-W-2.0.**
- **This repository:** the pipeline, the S3 half, the USB-C and the power mux come from FujiNet-O2 / Arcadia / StudioII Rev0; the RP2350A core, its neighbourhood and its drawing from FujiNet-Arcadia Rev0 (and through it Fujiversal-Atari2600 Rev1).
- **The regulator corner:** Raspberry Pi's RP2350 minimal design (MIT, `tools/RPI-MINIMAL-LICENSE.txt`): its parts, its copper and the RPI_* footprints.
- **The edge:** MAME's slot table (BSD-3-Clause) and the ADAM TRM; the geometry (width, notches, fingers) read from ThatOldNerd's (GPL-3.0), Commodore-Bench's (MIT) and Joe Grand's board files. Numbers and names only: no file from those projects is in this repository.
- **The shell's outside:** aotta's PiCOLECO shell (GPL-3.0) and sparkletron's (MIT), measured only.
- **The pin map:** `fujinet-firmware` `pico/coleco` and `include/pinmap/fujiversal-coleco.h`.
- **Symbols:** official KiCad libraries (CC-BY-SA 4.0 with exception); project symbols: the edge, the RP2350A in two units, the 74LVC245A and the W25Q16JV by function, the ESP32-S3-WROOM-1 by function, the microSD, the USB-C 16P by function.
- **Footprints:** KiCad's (Winbond USON-8 from kicad-footprints), Raspberry Pi's, and the generated edge.
- **3D models:** `3d/README.md`.
