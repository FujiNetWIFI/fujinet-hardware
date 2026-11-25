# FujiNet-TRS80M1 Rev0

FujiNet for the TRS-80 Model I, in place of the Expansion Interface, on one board in a printed case.
- **RP2354B:** serves the Model I's bus (`fujinet-firmware pico/trs80m1`): 32K of RAM, the EI's interrupt latch and
  heartbeat, its printer port, an FD1771 whose drives are FujiNet slots, the RS-232 board, and the FujiBus pipe at
  D0h.
- **ESP32-S3:** the FujiNet (`fujiversal-trs80m1`) and the RP's USB host.
- **Also on the board:** a microSD, a WS2812 status light, the DIP switches that force the RAM / EI / RS-232 off,
  and a USB-C with a CP2102N bridge, the card's only power.
- **The ribbon:** a 40-wire cable from the keyboard unit's expansion edge to a right-angle box header. Every line
  meets a 3.3 V LVC buffer right at the header:
  - the strobes go through Schmitt triggers;
  - D0-D7 are driven only while RD* or IN* is low, through 75R.

**Status (2026-11-25): board routed on 4 layers, JLCPCB and PCBWay packages generated, every gate passing, printed case
drawn. Nothing has been built yet.**
- **Fixed since PR #72:**
  - PR #72 wired header pin n to edge pin n, which no straight ribbon can give: Tandy numbers the edge as the mirror
    image of an IDC connector. The header now carries the edge pins swapped in pairs (*The expansion edge and the header*).
  - The 30 bus inputs are now pulled up to +3V3_RP instead of down.
  - Don't build PR #72's files.
- **Board:** 4 layers, 100 x 76 mm, an M3 hole in each corner. Assembled by JLCPCB or PCBWay, top side: 107 SMD
  parts and the through-hole box header.
- **Firmware:** the schematic implements `pico/trs80m1/firmware/include/m1_card.h`, as it stands in the bring-up's
  dev tree (`~/Workspace/fn-trs80m1`, not on fujinet-firmware master yet). The changes it still needs are under
  *Firmware changes this board needs*.
- **Header:** checked against four sources for the Model I's expansion edge (`tools/audit/header_pinout.py`).
- **Case:** `case/`, checked in OpenSCAD against every part. Not printed yet.

| Check (2026-11-25) | Result |
|---|---|
| Drawing checks (`gen_sch.py`) | every sheet wired. Crossings: 0 on `rp-core`, `fujinet`, `power`; 1 on `usb` (esptool's auto-program pair, as on the sibling carts); 1 on `m1-bus` (the OE gate's IN* tap past RD*: `docs/design-review-rev0.md` 3) |
| Netlist parity: kicad-cli netlist vs `design.py`, names included | 127 / 127 nets |
| KiCad ERC, all severities (kicad-cli and the KiCad MCP) | 0 errors, 0 warnings |
| `tools/audit/header_pinout.py`: the 40 edge pins against the Tech Ref 26-2103 p.91, the RetroStack rev G replica, the 26-1132 HD-adapter document and TRS-IO M1; the ribbon's pair swap against Fig. 22, the HD adapter's cable table and TRS-IO M1's pad numbers; the footprint against its EasyEDA original; pin 1 on the board | 0 failures (`tools/header_geom.VERIFIED = True`) |
| `tools/check_nets.py`: the netlist vs `m1_card.h`, `fujitrs80m1_rp2354b.h`, `fujiversal-trs80m1.h` | 461 checks, 0 failed; 4 NOTE lines (the firmware changes below) |
| `tools/audit/spice/ribbon.py` (ngspice): the ribbon both ways, 15 and 45 cm | strobes never ring through the Schmitt thresholds; the 75R data drive is clean to 45 cm |
| `tools/audit/margins.py`: levels, loads, contention, read timing (in step with the firmware's `test_timing.c`), power | 27 margins, 0 negative (tightest: +23 ns, a 3.55 MHz speed-up's typical read) |
| Routing | 100 % on 4 layers; 686 vias, 1678 tracks |
| KiCad DRC + schematic parity on the saved zone fills (kicad-cli, and again through the KiCad MCP) | 0 errors, 0 unconnected, 0 parity issues; 3 silk-over-edge warnings (the S3 module's outline at the flush east edge) |
| `tools/check_vias.py`: no via in a foreign SMD pad | 686 vias, 0 failures |
| `tools/audit/layout_checks.py`: the layout's claims measured on the copper | 69 / 69. Covers the regulator corner, decoupling (every bus buffer's within 6 mm), the USB pairs and their skew, the crystal, the exposed pads, the antenna band, the buck loop, and every header line to its buffer (42.5 mm and 2 vias at most) |
| `tools/audit/check_gerbers.py`: the zip itself | 0 failures: outline, the four M3 holes, the header's 40 drills with pads and mask both sides, no copper in the antenna band, nothing past the outline, no plated hole in an In1 / In2 pour of another net (762 holes) |
| `tools/audit/check_fab.py`: JLC and PCBWay BOM / CPL / centroid / drills / order-number text / gerbers / the header gate | all pass |
| JLCPCB CPL rotations (`tools/audit/jlc/`), measured against each LCSC part's EasyEDA footprint | 46 (footprint, LCSC) pairs. The RP2354B, the box header, the DIP switch and every logic part are high confidence. Medium: the 1G11, the AOTA and buck inductors, the TS-1187A, the BAT54C, the USB-C, the TLV62569. Check those in JLC's preview |
| kicad-happy 2.2.1 (`tools/audit/run_sch_audit.sh`, `run_pcb_audit.sh`), triaged in `docs/design-review-rev0.md` | 6 high groups: 4 false positives (keep-out circles, U12 decoupling, the LDO thermal estimate at 4x the real load, the header at the edge by design), 2 accepted (plane gaps beside the header's 40 holes, USB full-speed layer changes) |
| Printed case (`case/`, OpenSCAD) | `check` and `parts_check` empty, `parts_control` not |

## Sheets

Drawn with the FujiNet-StudioII / O2 / ColecoVision toolkit:
- **Wires only:** every connection on a sheet is a wire.
- **Rails:** rails are power symbols (`GND`, `VBUS`, `+5V`, `+3V3`, `+3V3_RP`, `DVDD`).
- **Between sheets:** the sheets join only through hierarchical labels, wired on the root's block diagram.

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | the block diagram: rp-core <-> fujinet (USB_DP / USB_DM, RUN_CTL, BOOTSEL_CTL, S3_EN), fujinet <-> usb (S3_TXD / S3_RXD, S3_EN, S3_IO0); notes |
| 2 | `m1-bus` (A2) | Left to right, one block per buffer group:<br>• the header (drawn in units by group) -> 100k pull-downs -> the buffer -> the RP2354B's GPIO unit for that group, every line one straight wire.<br>• A8-A15 and A0-A7: 74LVC245A, A -> B, always on.<br>• D0-D7: 75R, then the 74LVC245A turned round, DIR = DRIVE (GP28) and /OE from the 74LVC1G11 under it (DRIVE . RD* . IN*).<br>• RD* IN* INTAK* and SYSRES* OUT* WR*: two 74LVC3G17 Schmitt receivers.<br>• INT* WAIT*: the 74LVC2G07, pulled up on the RP side.<br>• The logic-analyser header, one unit per probed line.<br>• The DIP switches, LED and debug-UART pads |
| 3 | `rp-core` | the RP2354B's core unit: a capacitor at every supply pin, Raspberry Pi's regulator corner, crystal, SWD, RUN / BOOTSEL / RESET (the BAT54C to S3 EN), the USB 27R pair out to the S3 |
| 4 | `fujinet` | ESP32-S3-WROOM-1-N16R8, its EN RC and buttons, microSD, WS2812 |
| 5 | `usb` | USB-C, USBLC6-2SC6, CP2102N, esptool's auto-program pair |
| 6 | `power` | VBUS -> 1.1 A resettable fuse -> +5V; the RP's AP2112K LDO (+3V3_RP); the S3's TLV62569 buck (+3V3); rail test pads |

## The expansion edge and the header

40 contacts, two rows of 20 at 0.100", on a straight 40-wire IDC ribbon:
- **The Model I end:** a 40-way card-edge IDC connector (3M 3464-series or equivalent) on the keyboard unit's edge.
- **This board's end:** a 2x20 IDC socket on the box header.

**Tandy numbers the edge as the mirror image of that connector**, so the edge pins reach the header swapped in pairs:
header 1 = edge 2, header 2 = edge 1, header 3 = edge 4, and so on.
- Tech Ref Fig. 22, seen from the rear: odd pins on top, pin 1 at the **left**. Tandy's own EI floppy and printer
  edges have pin 1 at the top **right**.
- Buzbee / Fosdick: the expansion port "is configured opposite to other connectors on the expansion interface board".
  Plugged Tandy's way (stripe right, cable down), "the pin 1 stripe will actually connect to pin 39".
- TRS-IO M1 numbers its own edge pads the same way as this header (pad 1 SYSRES*, pad 2 RAS*).

Edge numbers are Tandy's:

| Header | Edge | Signal | Card | Header | Edge | Signal | Card |
|---|---|---|---|---|---|---|---|
| 1 | 2 | SYSRES* | 3G17 -> GP29 | 21 | 22 | D1 | 75R, '245 <-> GP17 |
| 2 | 1 | RAS* | open | 22 | 21 | INT* | GP30 -> 2G07 (OD) |
| 3 | 4 | A10 | '245 -> GP10 | 23 | 24 | D6 | 75R, '245 <-> GP22 |
| 4 | 3 | CAS* | open | 24 | 23 | TEST* | open (floats the buses) |
| 5 | 6 | A13 | '245 -> GP13 | 25 | 26 | D3 | 75R, '245 <-> GP19 |
| 6 | 5 | A12 | '245 -> GP12 | 26 | 25 | A0 | '245 -> GP0 |
| 7 | 8 | GND | GND | 27 | 28 | D5 | 75R, '245 <-> GP21 |
| 8 | 7 | A15 | '245 -> GP15 | 28 | 27 | A1 | '245 -> GP1 |
| 9 | 10 | A14 | '245 -> GP14 | 29 | 30 | D0 | 75R, '245 <-> GP16 |
| 10 | 9 | A11 | '245 -> GP11 | 30 | 29 | GND | GND |
| 11 | 12 | OUT* | 3G17 -> GP27 | 31 | 32 | D2 | 75R, '245 <-> GP18 |
| 12 | 11 | A8 | '245 -> GP8 | 32 | 31 | A4 | '245 -> GP4 |
| 13 | 14 | INTAK* | 3G17 -> GP32 | 33 | 34 | A3 | '245 -> GP3 |
| 14 | 13 | WR* | 3G17 -> GP24 | 34 | 33 | WAIT* | GP31 -> 2G07 (OD) |
| 15 | 16 | MUX | open | 35 | 36 | A7 | '245 -> GP7 |
| 16 | 15 | RD* | 3G17 -> GP25 | 36 | 35 | A5 | '245 -> GP5 |
| 17 | 18 | D4 | 75R, '245 <-> GP20 | 37 | 38 | A6 | '245 -> GP6 |
| 18 | 17 | A9 | '245 -> GP9 | 38 | 37 | GND | GND |
| 19 | 20 | D7 | 75R, '245 <-> GP23 | 39 | 40 | A2 | '245 -> GP2 |
| 20 | 19 | IN* | 3G17 -> GP26 | 40 | 39 | +5V / GND | **open** (+5V on boards A-E, GND on G) |

**Sources** (2026-11-24; `tools/audit/header_pinout.py` has them):
- the TRS-80 Technical Reference Handbook (Radio Shack 26-2103) p.91 table and Fig. 22;
- RetroStack's KiCad replica of the rev G keyboard-unit board (its edge netlist, and the part driving each pin);
- the Tandy 26-1132 hard-disk adapter document;
- TRS-IO M1 v1.4.

All four agree on every pin but 39, which Tandy's own text says Level II machines ground and the replicas show as +5V
on boards A-E. `header_pinout.py` also derives the pair swap from Fig. 22 and the connector, and checks it against
Buzbee / Fosdick's adapter table (the same map, plugged the other way up) and TRS-IO M1's pad numbers.

**What drives the edge** (the replica, and Tech Ref pp.15-18):
- A0-A15, RD*, WR*, IN*, OUT*, RAS*, CAS* and MUX come from 74LS367s ("one TTL load" each).
- SYSRES* comes from an LS02, INTAK* from an LS32.
- INT*, WAIT* and TEST* go straight to the Z80, each with a 4.7k pull-up.
- D0-D7 is the keyboard unit's internal data bus, driven by it except while the Z80 reads.
- The card puts one LVC input and a 100k pull-up to +3V3_RP on each line (`margins.py`). Unplugged, or with the Model I
  off, every line idles high: the strobes and SYSRES* inactive. With the Model I on and the card unpowered, the
  pull-ups back-feed its RP rail about 1 mA, too little to start anything.

**The header:** XFCN BH254R-40P (Ckmtw B-3000R40P-0110 fits the same holes), a right-angle shrouded 2x20.
- It lies along the west edge, its mouth flush with the board edge (0.24 mm past it), the key up.
- The odd pins are on its inboard row, **pin 1 (SYSRES*, edge pin 2) at the south end** by the PIN 1 / STRIPE arrow.

## The cable

**Buy or make** a straight 40-wire flat ribbon, **15 cm** (Tandy's EI cable was 6 in; no more than 30 cm):
- the Model I end: a 40-way 0.100" card-edge IDC connector (3M 3464-0000 or equivalent, for 1.4-1.8 mm boards);
- this board's end: a 2x20 IDC socket;
- both crimped with the red stripe (wire 1) at their pin-1 marks.

**On the Model I, the stripe goes at the left, seen from the rear** (the end of edge pins 1 and 2). The edge has no key slot.
- This is upside down from Tandy's own cables: the ribbon leaves the connector at the top. Wire 1 meets edge pin 2
  (bottom row), wire 2 edge pin 1.
- **Plugged Tandy's way round (stripe right), the card's grounds hold WAIT*, OUT* and A10 low.**
- To plug it Tandy's way round instead, crimp the socket end with its stripe at header pin 40, the north end.

**Before powering anything, with a meter and the Model I off:**
1. The cable alone: header pin 1 to the card-edge connector's contact at its stripe end, and header pin 40 to the
   contact at the far end on the other row. This shows the ribbon is straight.
2. With the connector on the keyboard unit: header pins 7, 30 and 38 to the Model I's ground. All three must ring.

To keep a real Expansion Interface too:
- Crimp a third connector (the EI's card-edge) onto the same ribbon.
- Plug it onto the EI the same way round as the Model I end: the stripe at the end of the EI edge's pins 1-2.
- Set the DIP switches to force off whatever the EI provides.

## RP2354B pin map

Exactly `m1_card.h`, plus INTAK* on GP32. `tools/check_nets.py` reads the dev tree and checks every pin.

| GPIO | Net | Goes to |
|---|---|---|
| 0-15 | RP_A0-A15 | the address 74LVC245As' B ports (`M1_PIN_A0` 0: `addr = pins & 0xFFFF`) |
| 16-23 | RP_D0-D7 | the data 74LVC245A's A port (`M1_PIN_D0` 16) |
| 24 / 25 / 26 / 27 | WR* / RD* / IN* / OUT* | the 74LVC3G17s (RD* on an odd pin: PWM-B counts it) |
| 28 | DRIVE | the data '245's DIR (1 = onto the bus) and the 74LVC1G11; 4.7k pull-down (RP2350-E9: under 8.2k) |
| 29 | SYSRES* | 74LVC3G17 |
| 30 / 31 | INT* / WAIT* | 74LVC2G07 inputs (low = assert), 10k pull-ups: released through reset |
| 32 | INTAK* | 74LVC3G17 (no firmware macro yet) |
| 33 / 34 / 35 | DIP_RAM / DIP_EI / DIP_RS232 | the DIP switches to GND (closed forces it off), 10k pull-ups (`M1_PIN_DIP0` 33) |
| 44 / 45 | DBG_TX / DBG_RX | test pads, UART, 3.3 V |
| 47 | RP_LED | 680R, red LED |
| QSPI | QSPI_SS | the flash is in the package; QSPI_SS is the BOOTSEL strap |
| USB | RP_USB_DP / DM | 27R -> the ESP32-S3's USB host (IO20 / IO19), on the board |
| RUN, QSPI_SS | | 10k pull-ups; RESET / BOOTSEL buttons; 1k from S3 IO4 / IO5 |

**The bus side.**
- **The data transceiver:** /OE is DRIVE . RD* . IN*, taken from the Schmitt receivers' outputs.
  - With DRIVE low it listens (the RP sees every write).
  - With DRIVE high it drives only while a read strobe is low, and lets go at the strobe's rising edge whatever core1 is doing.
- **The 75R on each data line:** it source-terminates the ribbon and limits the overlap current to ~31 mA when the
  keyboard unit takes the bus back.
- **Power and pulls:** every buffer runs at 3.3 V from the RP's LDO, so the RP never sees 5 V. LVC inputs are
  5 V-tolerant with Ioff, so a powered card never back-feeds a Model I that is off, and the reverse.

## ESP32-S3 pin map

`include/pinmap/fujiversal-trs80m1.h` (SD 38-41, UART0 43/44, LED strip 48), plus what every on-cart S3 board adds:

| S3 pin | Net | Goes to |
|---|---|---|
| IO19 / IO20 | USB_DM / USB_DP | the RP2354B's USB through its 27R (the S3 is the host) |
| IO38 / 39 / 40 / 41 | SD_MOSI / SCK / MISO / CS | microSD (SPI), 10k pull-ups on CS, DO, DAT1, DAT2 |
| IO42 | SD_CD | card detect, 10k pull-up (low = card in) |
| IO48 | LED_STRIP | 330R -> WS2812B-2020 (on +5V; VIH 2.7 V takes 3.3 V data) |
| TXD0 / RXD0 | S3_TXD / S3_RXD | CP2102N |
| IO4 / IO5 | RUN_CTL / BOOTSEL_CTL | 1k -> RP RUN / QSPI_SS: the S3 can reset the RP into its USB boot ROM |
| EN / IO0 | S3_EN / S3_IO0 | EN RC (10k / 1 uF), RESET (through the BAT54C), the S3 RST and BOOT buttons, the auto-program pair |

## Power

The Model I's edge carries no supply the card can use, so the card runs from its USB-C:
- pin 39 is +5V only on keyboard boards A-E;
- Tandy warns against loading it.

| Rail | Source | Feeds |
|---|---|---|
| `VBUS` | USB-C (USBLC6, 1 uF + 100 nF) | the fuse, the CP2102N's VBUS sense |
| `+5V` | VBUS through a 1.1 A hold / 2.2 A trip resettable fuse | the buck, the RP LDO, the WS2812 |
| `+3V3` | TLV62569 2 A buck, 3.33 V (100k / 22k), 2.2 uH | ESP32-S3, CP2102N, microSD |
| `+3V3_RP` | AP2112K-3.3 LDO | every RP2354B supply pin and all seven bus buffers |
| `DVDD` | RP2350 core SMPS (3.3 uH) | RP core, 1.1 V |

**Load:** ~0.53 A peak at 5 V in WiFi bursts (`margins.py`). Use a USB-C charger of 1 A or more. A PC's USB 2.0 port
(0.5 A) may sag during bursts.

## Layout

- **Stack (4 layers, JLC04161H-7628):**
  - F.Cu: signals + GND pour.
  - In1: GND.
  - In2: +5V, with a +3V3_RP island (the RP, its LDO and every bus buffer) and a +3V3 island (the east third: the S3, the CP2102N, the microSD).
  - B.Cu: signals + GND pour.
- **Placement (`tools/placement.py`):**
  - **West edge:** the box header, mouth outward.
  - **Bus column:** every buffer within ~15 mm of its header pins, in the header's order. The A0-A7 receiver north, the data transceiver with its 75R and pull-up arrays in the middle, the A8-A15 receiver south. The Schmitt receivers, the INT / WAIT driver and the OE gate east of them.
  - **Centre:** the RP2354B at rotation 0, its bus pins on its west and south sides, with FujiNet-StudioII / O2 Rev0's macro and Raspberry Pi's regulator corner turned with it.
  - **East edge:** the ESP32-S3, its antenna flush with the edge over a strip with no copper on any layer.
  - **North edge:** the USB-C and its ESD, fuse and CP2102N; the buck north-east.
  - **South edge:** the microSD, the DIP switches, RESET and BOOTSEL, and the unfitted logic-analyser header.
- **Deterministic copper:**
  - Raspberry Pi's regulator corner (`tools/rpi_core_graft.sexpr`);
  - the under-package +3V3_RP / DVDD rings (`gen_pcb.rp_support`);
  - the north-side capacitor links;
  - the core-rail pad's link.
- **Routing:** Freerouting, the grid finisher, clean-up, GND stitching, fills, DRC (`tools/route_board.sh`).
- **The board is not reproduced by `LAYOUT=1` alone.**
  - PR #72's board was the one of five isolated placement variants that closed every connection (`docs/design-review-rev0.md` 3).
  - The header fix (2026-11-25) re-routed only what it changed. `tools/reuse_copper.py` copied PR #72's copper, locked,
    for every net off the m1-bus sheet, VBUS, and the RP-side nets around the RP2354B's south pins. Freerouting and
    the finisher routed the rest: the header lines, the pull-ups and six RP-side address lines.
  - To repeat it: `git show 3278d76:TRS-80-Model-I/FujiNet-TRS80M1-Rev0/FujiNet-TRS80M1-Rev0.kicad_pcb > old.kicad_pcb`,
    then `LAYOUT=1 REUSE_FROM=old.kicad_pcb bash tools/build_all.sh`. Freerouting is deterministic for a given input,
    so the same input gives the same board.

## Parts

Every part is JLCPCB-assemblable. `FujiNet-TRS80M1-Rev0-BOM.csv` has every line with its MPN, manufacturer and LCSC
code. Run `python3 tools/audit/sourcing.py` on order day.

**Stock (2026-11-24, `docs/sourcing.md`):** 49 lines, none short at JLCPCB for 5 boards, about USD 14.75 of parts per
board.
- **The box header:** XFCN BH254R-40P (C48603651) had 603. The second source, Ckmtw B-3000R40P-0110 (C146628), had 248.
- **The buck:** the AP63203 the sibling carts use was at 0 again. This board uses the TLV62569DBVR (C141836, 461k).
- **The RP2354B** (C39843328, 10.5k) and the AOTA core inductor (C42411119, 8.7k) were in stock.

## Ordering

- **JLCPCB:** `exports/jlcpcb/ORDER-JLCPCB.md`.
  - Board: 4 layers, 1.6 mm, ENIG.
  - Assembly: Standard PCBA, top side, the box header as JLC's through-hole line.
  - Files: `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`, whose rotations and origins are measured against each LCSC part's EasyEDA footprint (`tools/audit/jlc/`).
- **PCBWay:** `exports/pcbway/ORDER-PCBWay.md`.
  - The same board options, turnkey assembly by MPN (`BOM-PCBWay.csv`, the header typed THT).
  - KiCad's own centroid (`Centroid-PCBWay.csv`) and `Assembly-top.pdf`.

## Printed case

`case/FujiNet-TRS80M1-Case.scad`, with `case/FujiNet-TRS80M1-Case.stl` (the tray, the lid and the RESET plunger,
laid out for printing) and the dimension dossier `case/case-spec.md`.
- **Size:** 105.2 x 81.2 x 18.7 mm.
- **Holding the board:** four M3 screws from below, through the tray's bosses and the board's holes, into the lid's.
- **Openings:** the header's mouth in the west wall, the USB-C north, the microSD south.
- **On the lid:** a RESET plunger, recessed pin-holes for BOOTSEL / S3 BOOT / S3 EN, a window over the DIP switches,
  LED windows, a label recess.
- **Checked in OpenSCAD:** the board, the plunger and every part's courtyard (to its height) clear both halves; a
  raised control does not. Fit one print before printing more.

## Firmware changes this board needs (not made here)

In the bring-up's PR series (`pico/trs80m1` is not on master yet):
1. `include/pinmap/fujiversal-trs80m1.h`: `PIN_RP2040_RUN` 4, `PIN_RP2040_BOOTSEL` 5, `PIN_CARD_DETECT` 42, and
   the `pico_*` keys in `platformio-fujiversal-trs80m1.ini`, so the S3 embeds the RP image and flashes it over
   PICOBOOT.
2. `pico/trs80m1/firmware/include/m1_card.h`: `M1_PIN_INTAK` 32, and drop "provisional until the board exists".
3. `pico/trs80m1/firmware/host_test/test_timing.c`: the 74LVC3G17 (5.4 ns), the 74LVC1G11 (4.1 ns) and the 75R
   ribbon edge in its constants (`tools/audit/margins.py` already models them).

`tools/check_nets.py` prints a NOTE line for each until it is done.

## Known limits

- **The cable is the user's to plug the right way round:** the Model I's edge has no key, and the right way is upside
  down from Tandy's own cables. See *The cable*.
- **Ribbon length:** the simulation is clean to 45 cm, but longer cables undershoot into the receivers' clamp
  diodes. Keep it to 15 cm.
- **Real-hardware timing:**
  - The read budget at the stock 1.774 MHz is met with 136 ns to spare.
  - Speed-up boards (2.66 / 3.55 MHz) are met only typically, as in the firmware.
  - The keyboard unit's data-buffer turnaround is modelled, not measured.
- **The DIP switches' ON side** follows the EasyEDA footprint's marks; check the delivered part.
- **Power:** USB-C only; a 0.5 A PC port may sag in WiFi bursts.

## Bring-up checklist

1. **Rails, with no Model I:** USB-C only. Check +5V, +3V3 and +3V3_RP at the test pads. The RP enumerates to the
   S3, and the WS2812 lights.
2. **First flash of the RP:** SWD pads (SWCLK, SWDIO, GND, south of the crystal) with a Raspberry Pi Debug Probe.
   After that the S3 re-flashes it over PICOBOOT (firmware change 1).
3. **The cable:** the meter checks under *The cable*, with everything off.
4. **The bus:** fit a 2x10 pin header in J2 (the logic-analyser header).
   - Its odd pins: RD*, WR*, IN*, OUT*, SYSRES*, INTAK*, DRIVE, /OE, INT, WAIT (the RP side of each buffer); every even pin is GND.
   - Power the Model I: CONFIG should boot from slot 1 (the `pico/trs80m1` milestones).
   - On a read, /OE must rise with RD* / IN*.
