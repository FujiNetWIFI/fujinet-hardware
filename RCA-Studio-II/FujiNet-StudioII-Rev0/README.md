# FujiNet-StudioII Rev0

FujiNet for the RCA Studio II, on one cartridge. An RP2354B serves the CDP1802 bus in software. The
ESP32-S3 on the same board is the FujiNet (`fujiversal-studio2`) and the RP2354B's USB host. The
board also carries a microSD, a WS2812 status light, and a USB-C with a CP2102N bridge for flashing
and powering it.

**Status: board routed, JLCPCB package ready** (2026-10-11).
- **Board:** 4 layers, 90.9 x 111.5 mm, fully assembled by JLCPCB on the top side.
- **Outline:** FliP's proven Studio II multicart outline from the insertion edge up, then 28 mm taller
  for the S3 half. Because of that it needs a printed shell; the console's slot is open above.
- **Firmware:** the schematic implements `fujinet-firmware/pico/studio2/firmware/include/s2_cart.h`
  and the S3's `include/pinmap/fujiversal-studio2.h` as they stand.
  - Both firmwares run on it unchanged.
  - One pin-map addition lets the S3 re-flash the RP: see *Firmware follow-ups*.
- **Nothing has been built yet:** see **Before ordering**.

| Check (2026-10-11) | Result |
|---|---|
| Drawing checks (`gen_sch.py`) | every sheet wired; 2 crossings on `cart-bus` (see Glue), 1 on `usb` (the auto-program pair), 0 on `rp-core`, `fujinet`, `power` |
| Netlist parity, kicad-cli netlist vs `design.py`, names included | 97 / 97 nets |
| KiCad ERC, all severities | 0 errors, 0 warnings |
| `tools/check_nets.py`: the netlist against `s2_cart.h` and `fujiversal-studio2.h` | 364 checks, 0 failed, 1 warning (*Firmware follow-ups*). Covers the edge map, series R, pull-ups, senses, PWR_OK gating, the power mux and the buck, RP support, the RP <-> S3 USB link and RUN / BOOTSEL forcing, the S3's pins and strapping, the USB-C bridge, and the edge footprint. |
| `tools/check_glue.py`: the '541 enables and CART CS vs `s2_glue_drive()` / `s2_glue_cartcs()`, compiled | 16 / 16 joint input combinations, 0 mismatches. RP unpowered: 4 / 4 silent. Console off: 8 / 8 silent. |
| `tools/audit/edge_orientation.py`: the edge against FliP's board file, EJK's pinout and the original board | all checks pass |
| KiCad DRC + schematic parity, all severities (`route_board.sh`) | 0 violations, 0 unconnected, 0 parity issues, on the saved zone fills (`tools/fill_zones.py` refills them after the last copper change) |
| `tools/check_vias.py`: no via in a foreign SMD pad | 689 vias, 0 failures |
| `tools/audit/layout_checks.py`: the layout's datasheet claims, measured on the copper | 65 / 65 claims hold. Covers the regulator corner, the supply rings, decoupling, USB, crystal, exposed pads, the edge's copper, the S3's antenna keep-out, its decoupling, the buck's input loop. |
| `tools/audit/check_fab.py` (+ `check_gerbers.py`): BOM / CPL / drills / order-number spot / the gerbers | 10 / 10. `check_gerbers.py`: 0 failures, including check 9: no plated hole inside an inner-layer pour of another net |
| `tools/audit/margins.py`: levels, the mux on each source, PWR_OK, pull-ups, LDO, buck, S3 rail, WS2812, CP2102N, crystal, LED | all positive |
| JLCPCB CPL rotations (`tools/audit/jlc/`), measured pad by pad against each part's EasyEDA footprint | 42 / 42 pairs |
| JLCPCB stock, every assembled line (`docs/sourcing.md`) | 44 / 44 in stock for 5 boards. The RP2350 core inductor is down to 24. |
| kicad-happy review (`docs/design-review-rev0.md`) | Ready to order as a bring-up prototype; no blockers. SPICE 15 / 15. Deep review: 32 findings, 32 verified, 0 quarantined. Release gate: 10 pass, 2 waived (board-only parts, layer extents). Three warnings: the 7805 load with WiFi, the S3 pin map, L1 stock. |

## Sheets

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | block diagram, notes. The RP <-> S3 USB pair, RUN / BOOTSEL controls, S3_EN, S3_IO0 and the UART are wired here. |
| 2 | `cart-bus` | 22-pin edge, 330R into GPIO0-9, 74HCT541, CART CS NOR, the PWR_OK-gating ORs, /DRIVE and /CLAIM pull-ups, PWR_OK, ADC sense, LED, debug UART, scope pads |
| 3 | `rp-core` | RP2354B supplies and decoupling, core regulator, crystal, SWD, RUN / BOOTSEL (buttons and the S3's controls), RESET (both MCUs), USB 27R |
| 4 | `fujinet` | ESP32-S3-WROOM-1-N16R8, its EN RC and buttons, microSD, WS2812 |
| 5 | `usb` | USB-C, USBLC6-2SC6, CP2102N, esptool's auto-program pair |
| 6 | `power` | TPS2116 power mux (USB first, console 5 V second), the S3's AP63203 buck, the RP's AP2112K LDO |

Each bus line is one straight wire from the edge to the RP. The edge symbol, the '541 and the RP's
GPIO unit are built on the same rows: D7 is on the top row, and the '541 takes its channels reversed
for the board.

## Edge connector

| Pin | Signal | Net | Pin | Signal | Net |
|---|---|---|---|---|---|
| 1-5 | D7-D3 | '541 Y | 12-14 | MA1-MA3 | 330R -> GPIO1-3 |
| 6 | ROM DISABLE | GND (removes the built-in games, as a cart does) | 15 | +5 V (console 7805) | CONS_5V |
| 7 | GND | GND | 16-18 | MA4-MA6 | 330R -> GPIO4-6 |
| 8-10 | D2-D0 | '541 Y | 19 | TPA (gated by /MRD in the console) | 330R -> GPIO8 |
| 11 | MA0 | 330R -> GPIO0 | 20 | MA7 | 330R -> GPIO7 |
| | | | 21 | /MRD | '541 /OE1, NOR, 330R -> GPIO9 |
| | | | 22 | CART CS (cart output, high = console RAM off) | NOR output |

The pinout is EJK's console schematic. FliP's multicart board carries the same signals on the same
pads, and `tools/audit/edge_orientation.py` compares them pad by pad. There is no write strobe,
clock or reset on the edge.

**The geometry is FliP's** (Philip Marien's RCA Studio II multicart v5.1, github.com/vodkaflip/
RCA_Studio_II). It was read from his Eagle board file and fab gerbers into `tools/edge_geom.py`. The
board is built, runs in real consoles and fits original shells, and photos of an original game
board match its outline.

- **22 contacts on one face, B.Cu**, at 0.156" (3.9624 mm):
  - 1.905 mm wide, with copper 0.70-8.95 mm from the edge;
  - each in its own mask opening;
  - hard gold with a 45-degree bevel.
  The console's CN1 is a 2x22 connector whose lettered row is unconnected (EJK).
- **Pin 1 (D7) is at the left seen from the contact face**, so at the right seen from the parts
  (F.Cu). The contacts face the back of the console, the parts its front, as on an original cart.
- **No tab:** the full 90.912 mm bottom edge enters the slot. Up to the top of FliP's straight sides
  the board is his:
  - two 8.128 mm holes 68.58 mm in, where the original shell's posts go;
  - a half-round notch in each side 20.83 mm in.
- **Above that the board grows 28 mm** (111.49 mm overall, rounded top corners) for the ESP32-S3
  half, so it needs a printed shell.
- **1.6 mm thick** (FliP's boards are 1.57 mm).
- **No part closer than 23.5 mm to the edge.** That band holds the finger stubs, the address bus's
  twist and the data bus's fan-in, and it enters the console under the shell.
- **FliP's holes and notches** sit ~0.24 mm off-centre in opposite directions (hand-placed). The
  holes keep his positions, mirrored because he drew from the contact face. Both notches take his
  deeper cut.

## RP2354B pin map

Exactly `s2_cart.h`. `check_nets.py` reads every `*_PIN` and fails if the header names a pin this
board does not wire, or the board wires one the header does not name.

| GPIO | Net | Goes to |
|---|---|---|
| 0-7 | RP_MA0-7 | 330R -> edge MA0-MA7 |
| 8 | RP_TPA | 330R -> edge 19 |
| 9 | RP_MRD | 330R -> edge 21 |
| 16-23 | RP_D0-7 | 74HCT541 A8-A1, channels reversed (A8 / Y8 = bit 0: the board's data bus is then planar) (outputs only) |
| 24 | DRIVE_N | 74HCT32 -> '541 /OE2; R11 10k to +5V |
| 25 | CLAIM_N | 74HCT32 -> NOR; R12 10k to +5V |
| 26 | PWR_OK | 74HCT14, two stages from the console 5 V; the first stage (PWR_OK_N) gates the ORs |
| 27 | RP_LED | 1k, red LED |
| 40 | VSENSE_ADC | ADC0: edge 15 through 100k / 100k (0.5 x), 100 nF |
| 44, 45 | DBG_TX, DBG_RX | J2 (DNP), 3.3 V only |
| USB | RP_USB_DP / DM | 27R -> the ESP32-S3's USB host (IO20 / IO19), on the board |
| RUN, QSPI_SS | RUN, QSPI_SS | the buttons, and the S3's IO4 / IO5 through 1k |

- The console's lines reach the RP through 330R. That limits the current into a 5 V-tolerant pad
  while IOVDD is still rising, and costs under 2 ns.
- GPIO40-47 are not 5 V tolerant. `check_nets.py` asserts only passives and the debug header reach
  them.
- No bus pin has a pull: the firmware turns the pad pulls off (RP2350-E9).

## ESP32-S3 pin map

Exactly `fujiversal-studio2.h`. `check_nets.py` reads it and checks every pin.

| S3 pin | Net | Goes to |
|---|---|---|
| IO19 / IO20 | USB_DM / USB_DP | the RP2354B's USB through its 27R (the S3 is the host) |
| IO38 / IO39 / IO40 / IO41 | SD_MOSI / SD_SCK / SD_MISO / SD_CS | microSD (SPI mode), 10k pull-ups on CS, DO, DAT1, DAT2 |
| IO42 | SD_CD | card detect, 10k pull-up (low = card in) |
| IO48 | LED_STRIP | 330R -> WS2812B-2020 (on +5V; VIH 2.7 V takes 3.3 V data) |
| TXD0 / RXD0 (IO43 / 44) | S3_TXD / S3_RXD | CP2102N (flashing and the S3's console over the USB-C) |
| IO4 / IO5 | RUN_CTL / BOOTSEL_CTL | 1k -> RP RUN / QSPI_SS: the S3 can reset the RP into its USB boot ROM |
| EN | S3_EN | 10k / 1 uF power-on delay; S3_RST button, the cart RESET (through the BAT54C), the auto-program pair |
| IO0 | S3_IO0 | S3_BOOT button, the auto-program pair |
| IO3, IO45, IO46 | -- | strapping pins, unloaded |

The N16R8 module's octal PSRAM takes IO35-37, and its flash takes IO26-32. Neither is used.

## Glue

```
'541 drives D0-D7  = !/MRD & !/DRIVE & PWR_OK                    (s2_glue_drive)
                     /OE1 = /MRD          /OE2 = /DRIVE | PWR_OK_N     74HCT32
CART CS            = NOR(/MRD, /CLAIM) & PWR_OK                  (s2_glue_cartcs)
                   = NOR(/MRD, /CLAIM | PWR_OK_N)                    74HCT32 + 74HCT1G02
```

- /MRD alone ends a read in hardware, for both outputs. It is the '541's /OE1 with no gate between
  them, and one gate from CART CS.
- **The console's power gates both outputs.** With the console off, PWR_OK_N (the first '14 stage)
  is high, so nothing is driven into it: not D0-D7, not CART CS.
  - This holds whatever the RP, running from USB, has left on /DRIVE and /CLAIM.
  - The gates run on +5V, the cart's own muxed rail, so they work with the console off.
- No 74HCT27 (triple 3-input NOR) is stocked at JLCPCB, so the 3-input NOR is a '32 OR into the
  '1G02. The '32's other gate makes /OE2.
- The '541, '32 and NOR run on +5V, so D0-D7 and CART CS are 5 V CMOS levels; the 1802's VIH is
  3.5 V at 5 V. Their TTL inputs take the RP's 3.3 V.
- R11 / R12 hold /DRIVE and /CLAIM high, keeping the cart silent while the RP is unpowered or
  booting. 10k beats the RP2350's reset pull-down. `check_glue.py` checks this and the console-off
  case.
- `cart-bus` has two crossings, both forced:
  - the /MRD riser crosses /OE2, because /OE1 = /MRD sits between the '541's A pins and /OE2;
  - PWR_OK_N crosses the /MRD line once, because it reaches one OR above that line and one below.

## Power

- **U10, TPS2116 power mux: +5V.** VIN1 is the USB-C's VBUS, VIN2 the console's 5 V (CONS_5V, edge 15).
  - **Priority:** MODE is tied to VIN1, and PR1 comes from a 33k / 10k divider. VBUS above
    3.96-4.64 V (always, for a USB source) runs the cart, and the console's 7805 then supplies
    nothing. Otherwise the console does.
  - **Drop:** 37-60 mOhm either way. +5V sits within ~30 mV of its source at the cart's peak, so the
    74HCT glue stays inside its 4.5-5.5 V on either source (`tools/audit/margins.py`: >= 4.72 V).
  - **Reverse-current blocking:** neither source back-feeds the other. Switchover is
    break-before-make (~8 us), and +5V's 50 uF carries the cart through it.
- **+5V feeds:**
  - the '541, '32, '1G02 and '14;
  - the WS2812;
  - U12, an AP2112K, giving +3V3: every RP2354B supply pin. It rises with +5V, so the 5 V-tolerant
    pads are never unpowered with 5 V on them;
  - U11, an AP63203 2 A buck, giving +3V3_S3: the ESP32-S3, the CP2102N and the microSD.
- **Load:** ~140 mA average with the S3 on WiFi, ~470 mA peak (`margins.py`).
  - With USB-C connected, all of it comes from USB.
  - With no USB, all of it comes from the console's 7805. Its headroom is unmeasured: bring-up step 2.
- **USB-C:**
  - a UFP (5.1k Rd on CC1 / CC2), behind a USBLC6-2SC6 (3.5 pF per line);
  - its D+ / D- go to the CP2102N, which flashes the S3 and carries its console;
  - the RP's USB is the S3's (on the board), not the receptacle's.

## Parts

Every part is JLCPCB-assemblable. The stock below is from JLCPCB's parts library on 2026-10-11
(`docs/sourcing.md`, `tools/audit/sourcing.py`). `FujiNet-StudioII-Rev0-BOM.csv` has every line with
MPN, manufacturer and LCSC code.

| Part | LCSC | JLC stock | Note |
|---|---|---|---|
| RP2354B | C39843328 | 3640 | extended |
| ESP32-S3-WROOM-1-N16R8 | C2913202 | 34k | extended; the FujiNet module (16 MB flash, 8 MB PSRAM) |
| SN74HCT541PWR | C436096 | 25k | extended |
| 74HCT1G02GV,125 (Nexperia, SOT-753) | C12504 | 2.9k | extended. Fallback: SN74AHCT1G02DBVR, C163710, same SOT-23-5 land (A / B swapped, which a NOR does not care about) |
| SN74HCT14DR, SN74HCT32DR | C6769, C6781 | 36k, 3.0k | extended |
| TPS2116DRLR (power mux) | C3235557 | 75k | extended |
| AP63203WU-7 (S3 buck) + SWPA4030S6R8MT 6.8 uH | C780769, C62684 | 12k, 16k | extended (LCSC has no record of the inductor's code; JLCPCB lists it) |
| AP2112K-3.3TRG1 (RP LDO) | C51118 | 29k | extended |
| CP2102N-A02-GQFN28R, UMH3N, USBLC6-2SC6 | C964632, C62892, C7519 | 36k, 54k, 35k | extended |
| TF-015 microSD, TYPE-C-31-M-12 USB-C | C113206, C165948 | 22k, 408k | extended |
| WS2812B-2020-V6, BAT54C,215 | C52917434, C37704 | 987k, 275k | extended |
| ABM8-272-T3 12 MHz | C20625731 | 9.3k | extended |
| **AOTA-B201610S3R3-101-T** 3.3 uH | C42411119 | **24** (LCSC 0) | The RP2350 core inductor Raspberry Pi qualifies; very low stock. If it runs out, consign it, or try a shielded 2016 3.3 uH such as TDK VLS201610HBX-3R3M-1 (C695624) on the same land, unqualified. |
| Raspberry Pi's 0402 corner parts | C23733, C1525, C25105, C25100 | 2.1M, 24.5M, 1.7M, 38k | basic, basic, basic, extended |

Re-check stock on the order day. Parts cost ~USD 15.71 per board (LCSC, 5-board quantities), before
assembly fees.

## The board

The board is generated, not hand-drawn:
- `tools/gen_pcb.py` builds it from `tools/design.py`, `tools/placement.py` and `tools/edge_geom.py`;
- `tools/route_board.sh` routes it.

The reasoning, the variants and their numbers are in `docs/floorplan-study.md`; the audit is in
`docs/design-review-rev0.md`.

| Layer | Use |
|---|---|
| F.Cu | every part, signals, GND pour (not over the RP2350's regulator corner) |
| In1 | solid GND (stops at the finger field) |
| In2 | +5V (the mux's output), with islands: +3V3 under the RP2354B and its LDO, +3V3_S3 under the S3 band, CONS_5V from finger 15 to the mux |
| B.Cu | the 22 fingers, signals, GND pour |

- **Fab:** JLC04161H-7628 (1.6 mm), ENIG, hard-gold bevelled fingers.
- **Tracks:** minimum 0.15 mm (Raspberry Pi's corner, the USB-C's contact joins). Clearance has a
  0.12 mm floor (0.15 mm net classes).
- **Vias:** 0.6 / 0.3 mm (0.5 / 0.25 at the RP's rings and the USB-C, 0.6 / 0.25 in Raspberry Pi's
  corner, 0.8 / 0.4 for power).

**Floorplan.**
- **The bottom is the RP cart.** The RP2354B sits in the middle at rotation 90:
  - GPIO0-9 face south-west over the address fingers, GPIO16-23 south-east over the data fingers;
  - the core regulator and USB face west, the crystal and SWD east.
- **The bus side:** the '541 stands over the data fingers, the glue east of it, and the power mux west
  by finger 15.
- **Along the new top edge sits the S3 half.**
  - The ESP32-S3 in the middle, its antenna flush with the edge, and its 48 x 6 mm keep-out empty on
    every layer (the module footprint's zone: the antenna plus Espressif's 15 mm). KiCad 10's DRC
    ignores a footprint's own keep-out once the project library is loaded, so the board carries it
    again as board rule areas (`gen_pcb.antenna_keepout`).
  - The USB-C, its USBLC6 and the CP2102N west of the keep-out, in one order end to end. The USBLC6
    is flow-through: its twin pins are joined straight under its body, and its VBUS drops through a
    via between the pad rows to the 100 nF beside it (`gen_pcb.bridge_link`).
  - The USB-C sits where HRO's layout puts it: the edge 5.79 mm in front of its pegs. Its shell face
    overhangs the edge by 0.46 mm, so a plug's overmold clears the board.
  - The microSD east of it, beside the S3's SPI pins, its card slot at the edge.
- **In between:** the S3's buck, and the four buttons in a row (S3 EN, BOOTSEL, RESET, S3 BOOT).
- **Direct link:** the S3's USB pins face straight down at the RP's.

**The buses.** A flow-through buffer cannot reverse a bus. The edge runs D7..D0 but MA0..MA7, while
the RP runs both groups the same way, so one group must cross itself once, whichever face the
contacts are on.
- **Data: planar.** The '541 takes its channels reversed (A8 / Y8 = bit 0, `design.py`; the same
  nets, the firmware untouched).
  - Fingers -> Y row on B.Cu lanes to staggered vias under the '541 (`data_fanin`).
  - A row -> GPIO16-23 as parallel 45-degree diagonals (`data_rp_fan`).
  - Both are locked.
- **Address: one twist** in the parts-free band (`address_twist`).
  - Each of the 10 lines rises from its finger on B.Cu to a level of its own, crosses on F.Cu, and
    rises into its 330R. The 330R row then fans into the RP planar.
  - Vias: east-going lines rise the last stretch on F.Cu (one via), west-going ones on B.Cu (three
    vias), and MA3 goes straight up (one via).

**The RP2354B core.**
- **Raspberry Pi's regulator corner**, grafted from their RP2350 minimal design (MIT;
  `tools/rpi_graft.py`, `tools/rpi_core_graft.sexpr`).
  - The QFN-60 and QFN-80 share the AVDD / PGND / LX / VIN / FB / USB / OTP / QSPI_IOVDD pin run at
    the same pitch from the same corner. So the reference's 0402 parts and copper move by
    (+1.0, -1.5) mm and land exactly.
  - The datasheet (6.3.8): "the most critical part of an RP2350 PCB layout is the core voltage
    regulator ... these guidelines must be strictly followed".
- **No top-layer GND pour over that corner:** nothing but pads under the inductor, and the PGND pour
  meets main GND through its own two vias only (datasheet 6.3.8.1).
- **Supply rings under the package**, after the reference: a DVDD ring round the exposed pad and a
  +3V3 ring round that, on F.Cu.
  - Every supply pin stubs inward to its ring, so no supply pin needs a via among the bus pins.
  - The +3V3 ring drops to its In2 island at its four corners; the DVDD ring reaches the regulator's
    output over a B.Cu link.

**Mechanics.** `case/board-anchors.scad` (generated) gives a printed shell what it needs:
- the outline with its notches, and the post holes;
- the parts-free band and the tallest part;
- the antenna's clear zone, the USB-C and the microSD at the top edge;
- the four buttons, the two LEDs and the debug header;
- a label recess.

## Before ordering

1. **The edge.** Print `docs/tab-overlay-1to1.pdf` at 100 % and check its 50 mm ruler. Then lay a
   real Studio II cartridge board on it, contacts up.
   - The 22 contacts, pin 1 at the left, the width, the post holes and the notches must line up.
   - The geometry is FliP's; nobody has measured an original for this board.
2. **The thickness.** 1.6 mm is ordered (FliP's boards: 1.57).
3. **Stock**: run `python3 tools/audit/sourcing.py`.
   - The RP2350 core inductor (AOTA-B201610S3R3, L1) had 24 left at JLCPCB on 2026-10-11, and none
     at LCSC. Five boards need five.
4. **The order.** Order exactly as `exports/jlcpcb/ORDER-JLCPCB.md` says, and check the placement
   preview.
   - 4 layers, ENIG, gold fingers with bevel, Standard PCBA top side.
   - Rails, if any, on the long sides only.
5. **The shell.** The board is 111.5 mm tall, so an original shell does not fit. Print one from
   `case/board-anchors.scad`.
6. **The review's open questions** (`docs/design-review-rev0.md`).

## Firmware follow-ups (not changed here)

- **The S3's RUN / BOOTSEL pins.** `fujiversal-studio2.h` declares no `PIN_RP2040_RUN` /
  `PIN_RP2040_BOOTSEL`. This board wires them to IO4 / IO5, as `fujiversal-intv.h` does.
  - With `#define PIN_RP2040_RUN GPIO_NUM_4` and `#define PIN_RP2040_BOOTSEL GPIO_NUM_5`,
    `fnPicoUpdater::forceBootselViaPins()` can re-flash the RP2354B even when its firmware is hung.
  - Until then, use the buttons, or the cooperative BOOTSEL request over USB.
- **Unused RP pins.** Nothing initialises GPIO44 / 45 (J2), and nothing reads VSENSE (GPIO40).
  VSENSE could watch the console's 7805.
- **A stale comment.** `s2_cart.h` says `DRIVE_PIN` is "the '541's /OE2". It now reaches /OE2
  through the 74HCT32, gated by PWR_OK_N.

## Bring-up

1. **USB-C only, no console.**
   - +5V at TP15: 4.75-5.25 V, within ~30 mV of VBUS at TP14.
   - +3V3 at TP16 and +3V3_S3 at TP17; DVDD 1.1 V at TP12.
   - CONS_5V (TP13) and PWR_OK (TP6) stay at 0 V.
   - The CP2102N enumerates on the PC. Flash the S3 with esptool over it: auto-program, or hold
     S3_BOOT (SW4) and press S3_RST (SW3).
2. **In the console, no USB.**
   - CONS_5V (TP13) and +5V (TP15) within ~30 mV of each other.
   - Scope CONS_5V while the S3 joins WiFi (TX bursts, up to ~470 mA for the cart). If the console's
     7805 sags, run the cart from USB-C: the mux then takes nothing from the console.
3. **Bus.** Scope /MRD (TP1), TPA (TP2), CART CS (TP3), /DRIVE (TP4), /CLAIM (TP5) and D0:
   - the gated-TPA width and the low-byte settle time (`S2_LO_DELAY_NS`);
   - CART CS against the console RAM's release before the '541 drives;
   - whether non-memory execute cycles assert /MRD.
4. **Power-on race.** The BIOS reaches `$0400` about 50 ms after power-on. Scope /DRIVE against the
   first TPA with the cart on the console alone.
5. **Power-off on USB.** Switch the console off with USB-C connected. As PWR_OK (TP6) falls:
   - /OE2 ('541 pin 19) must go high;
   - CART CS (TP3) must go low;
   - D0 must float.

**Flashing the RP2354B:**
- from the S3 (USB host: the FujiNet firmware's PICOBOOT / UF2 path, and the IO4 / IO5 forcing once
  the pin map declares it);
- or hold BOOTSEL (SW1) and press RESET (SW2);
- or SWD on TP8 SWCLK, TP9 SWDIO, TP10 GND, TP11 RUN.

RESET resets both MCUs: the way back to the FujiNet's CONFIG screen.

## Regenerating

You need:
- KiCad 10;
- Python 3 (+ numpy, Pillow);
- a C compiler (`check_glue.py` compiles the firmware's glue);
- for the board, Java and Freerouting 2.4.1 (`~/.local/share/freerouting/freerouting-2.4.1.jar`).

```sh
tools/build_all.sh              # schematic, checks, the routed board kept as it is (re-synced, DRC), the package
LAYOUT=1 tools/build_all.sh     # ... and the board regenerated and re-routed from scratch (~25 min)
```

It runs, in order:

1. `harvest_symbols.py`, `make_edge_fp.py`, `make_fp_extra.py`, `audit/edge_orientation.py`;
2. `gen_sch.py`: drawing checks, hierarchy, netlist parity with `design.py`, `nets.lock`;
3. KiCad ERC at all severities;
4. `check_nets.py`, then `check_glue.py`;
5. the board:
   - with `LAYOUT=1`, `gen_pcb.py`: placement, the graft, the rings, the twist and fans, the buck
     loop, the planes, the plane fan-out, `case/board-anchors.scad`;
   - then `route_board.sh`: the crystal pre-route, Freerouting with a keep-out under the RP, the A*
     finisher, tidy, GND stitching, `check_vias`, 3D models, silkscreen, `fill_zones.py`, DRC with
     schematic parity;
   - without `LAYOUT=1`, only `sync_pcb_sheets.py`, `fill_zones.py` and the DRC.
   - The gerbers are plotted from the zone fills saved in the board, and GND stitching adds its vias
     after the last fill. So `fill_zones.py` refills and saves, and the DRC runs on the saved fills
     (not `--refill-zones`, which checks fresh fills in memory only).
6. `check_vias.py`, `audit/layout_checks.py`;
7. `export.py`: BOM, JLCPCB BOM and CPL, gerbers, `ORDER-JLCPCB.md`, the schematic PDF, the assembly
   drawing, layout SVGs, renders;
8. `tab_overlay.py`, `audit/check_fab.py` (+ `check_gerbers.py`, whose check 9 tests every plated
   hole against the plotted inner layers).

**Other entry points:**
- The kicad-happy audit: `tools/audit/run_sch_audit.sh`, `tools/audit/run_pcb_audit.sh`,
  `tools/audit/make_deep_review.py` (writes to `analysis/`, gitignored except its manifest).
- The JLC rotations: `tools/audit/jlc/measure_rotations.py`.
- The stock: `tools/audit/sourcing.py`.

**Firmware sources:**
- `check_*.py` read `$FUJINET_FIRMWARE/pico/studio2` (default `~/Workspace/fujinet-firmware`).
- `check_nets.py` also reads the S3's pin map from
  `$FUJINET_S2_BOARD/include/pinmap/fujiversal-studio2.h` (default `~/Workspace/fn-studio2-board`).
  It is required: the S3's pins are this board's contract.

**What to edit.** Never edit the KiCad files. Edit instead:
- `tools/design.py`: the circuit;
- `tools/sch_layout.py`: the drawing;
- `tools/edge_geom.py`: the edge and the outline;
- `tools/placement.py`: the floorplan;
- `tools/gen_pcb.py`: the pre-routed copper.

References are frozen in `tools/refs.lock`, net names in `tools/nets.lock`.

## Provenance and license

**CERN-OHL-W-2.0.**

- **This repository:**
  - the RP2354B core circuit, the '541 data path, the PWR_OK and ADC senses and the generators come
    from FujiNet-5200 Rev0;
  - the ESP32-S3 half (S3, microSD, WS2812, CP2102N, auto-program pair, buck, RESET steering) and
    the board pipeline (placement, Freerouting round trip, finisher, stitching, fab gates, JLC
    rotations) come from FujiNet-ChannelF Rev0;
  - the TPS2116 power mux and the USBLC6 are new here.
- **The regulator corner:** Raspberry Pi's RP2350 minimal design (MIT,
  `tools/RPI-MINIMAL-LICENSE.txt`): its parts, its copper and the RPI_* footprints.
- **The edge:**
  - the pinout is from EJK's console schematic;
  - the geometry is from FliP's multicart v5.1 (github.com/vodkaflip/RCA_Studio_II, "(cc) FliP"):
    numbers read from his board file, no file copied;
  - other sources: MAME `rca/studio2.cpp` and the CDP1802A datasheet.
- **Glue and pin maps:** `fujinet-firmware` `pico/studio2` `s2_cart.h`; `include/pinmap/
  fujiversal-studio2.h` and `fujiversal-intv.h`.
- **Symbols:** official KiCad libraries (CC-BY-SA 4.0 with exception).
  - The 74HCT1G02 uses the 74LVC1G02 symbol and the 74HCT14 the 74HC14's (same pinouts).
  - Project symbols: the edge, the RP2354B in two units, the ESP32-S3-WROOM-1 by function, the
    microSD, and the USB-C 16P by function.
- **Footprints:**
  - KiCad's official library: SOT-583-8, SOT-23-6, and the others through the sibling boards;
  - Raspberry Pi's: RPI_*;
  - generated: the edge, the TS-1187A, the post hole.
- **3D models:** `3d/README.md`.

## Files

| Path | Contents |
|---|---|
| `FujiNet-StudioII-Rev0.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` | KiCad 10 project (root + `cart-bus`, `rp-core`, `fujinet`, `usb`, `power`), the board and its rules |
| `FujiNet-StudioII.kicad_sym`, `FujiNet-StudioII.pretty/`, `3d/` | project symbols, footprints and 3D models |
| `FujiNet-StudioII-Rev0-BOM.csv` | grouped BOM (MPN, manufacturer, LCSC; DNP flagged) |
| `exports/jlcpcb/` | gerbers + drills zip, `BOM-JLCPCB.csv`, `CPL-JLCPCB.csv`, `ORDER-JLCPCB.md` |
| `docs/FujiNet-StudioII-Rev0-schematic.pdf` | the schematic |
| `docs/assembly-top.pdf`, `layout-front.svg`, `layout-back.svg`, `board-top.png`, `board-bottom.png` | the board |
| `docs/tab-overlay-1to1.pdf` | the edge at 1:1, to check against a real cartridge |
| `docs/floorplan-study.md`, `docs/design-review-rev0.md`, `docs/sourcing.md` | the layout's reasoning, the audit, the stock |
| `case/board-anchors.scad` | the board's outline, holes and openings for a printed shell |
| `datasheets/manifest.json` | the parts' datasheets (the PDFs are gitignored: re-fetch by the manifest) |
