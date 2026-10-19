# FujiNet-NES Rev1

All-in-one **NES FujiNet cartridge** without SRAM: one board in a 72-pin Game
Pak shell, two RP2354Bs serving the console's two buses, an ESP32-S3 running
FujiNet. Same feature set as Rev0 (Tier-1 mappers 0, 1, 2, 3, 4, 7, 11, 30,
34, 66, 71, 206; 512K PRG; CHR-RAM; WRAM; mailbox; loader; MMC3 IRQ), plus
real four-screen nametables.

- **RP-A (U1, RP2354B)** sits on the CPU side of the 5 V cart bus through its
  5 V-tolerant pads (CPU A0-A14, D0-D7, M2, R/W, /ROMSEL, /IRQ, PPU A12 for the
  MMC3 scanline counter). It runs at 266 MHz and serves PRG itself with a
  PIO+DMA engine: from RAM for images up to 384K, from its in-package flash
  through the QMI address-translation windows for 512K. It also serves
  `$5000-$7FFF` (mailbox, loader, WRAM), runs every mapper, forwards each
  mapper write to RP-B, and loads RP-B's firmware into RP-B's RAM over SWD at
  every boot.
- **RP-B (U2, RP2354B)** sits on the PPU side (PPU A0-A13, D0-D7, /RD, /WR)
  and drives CIRAM A10 and /CE. It serves CHR, CHR-RAM and four-screen
  nametables from RAM; CIRAM A10//CE come from a PIO table indexed by
  PPU A10-A13. It has no firmware of its own in flash.
- **The link:** eight data lines LD0-LD7, LCLK (both edges), LFRM (frame) from
  RP-A, LACK back. 32-bit frames: raw mapper writes, the image header, CHR
  data, mode changes (`fujinet-firmware pico/nes/firmware/include/nes_link.h`).
  RP-B's LD pins are mirrored, so the bus is planar on the board.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-nes`** build of
  fujinet-firmware and is the USB *host* of RP-A (CDC, VID 0xCafe) on
  IO19/IO20; it re-flashes RP-A over PICOBOOT.
- **USB-C** (power + CP2102N UART with UMH3N auto-program), **microSD**
  (SPI on IO38-41, card-detect IO42), **WS2812B-2020** status LED,
  RESET / BOOTSEL / S3 EN / S3 BOOT buttons, a red status LED on RP-A.
- **CIClone** footprint (ATtiny13A, DNP) on the four CIC fingers.

**Against Rev0:** the two AS6C4008 SRAMs ($6.36 each, out of JLC stock), the
six 74HCT chips, two resistor packs and the power-on RC are gone; a second
RP2354B, its crystal, inductor, LDO and passives come in. The CHR ceiling
drops from 512K to 256K, which is MMC3's maximum; no supported mapper
addresses more.

| BOM at LCSC, 2026-10-19 | Rev0 | Rev1 | Saved |
|---|---|---|---|
| Lines | 43 | 36 | 7 |
| Parts cost, qty 1 | $32.64 | $20.88 | **$11.76** |
| Parts cost, 100-piece tier | $26.52 | $15.50 | **$11.02** |

Both totals leave out the buck inductor (C62684), which LCSC no longer
prices. The only part left to consign is the AOTA core inductor (Rev0 needs
it too), now two of them.

**Status (2026-10-19):** routed, DRC-clean, fab files exported; see *Status*.
**No board has been built.** The timing that makes this work was proven on a
stock Pico 2 with an on-chip bench (`fujinet-firmware pico/nes/bench`), not on
a console.

## Edge connector

72 pins, **2.50 mm pitch**, pins 1-36 on the label side, 37-72 behind them,
pin N over pin N+36 (nesdev *Cartridge connector*). Looking at the label side
with the fingers down, the fingers read **36 .. 1 from left to right: pin 1 is
at the right.** `NES_Cart_Edge_72` is Rev0's footprint (NES-EWROM-01 geometry:
fingers 2.0 x 12.0 mm, end fingers 3.0 mm, copper 1.0-13.0 mm in from the
bevelled edge, one mask window per face, 6.5 mm front / 11 mm back).

| Pin | Signal | Net | Pin | Signal | Net |
|---|---|---|---|---|---|
| 1 | GND | GND | 37 | SYSTEM CLK | nc |
| 2-13 | CPU A11..A0 | CA11..CA0 | 38 | M2 | M2 |
| 14 | CPU R/W | RW | 39-41 | CPU A12, A13, A14 | CA12-14 |
| 15 | /IRQ | IRQ_N | 42-49 | CPU D7..D0 | CD7..CD0 |
| 16-20 | EXP0-4 | nc | 50 | /ROMSEL | ROMSEL_N |
| 21 | PPU /RD | PPU_RD_N | 51-55 | EXP9-5 | nc |
| 22 | CIRAM A10 | CIRAM_A10 | 56 | PPU /WR | PPU_WR_N |
| 23-29 | PPU A6..A0 | PA6..PA0 | 57 | CIRAM /CE | CIRAM_CE_N |
| 30-33 | PPU D0-D3 | PD0-3 | 58 | PPU /A13 | **nc** (RP-B decodes PA13) |
| 34, 35 | CIC toPak, toMB | CIC_TOPAK, CIC_TOMB | 59-61 | PPU A7, A8, A9 | PA7-9 |
| 36 | +5V | CONS_5V | 62, 63 | PPU A11, **A10** | PA11, PA10 |
| | | | 64, 65 | PPU A12, A13 | PA12, PA13 |
| | | | 66-69 | PPU D7..D4 | PD7..PD4 |
| | | | 70, 71 | CIC +RST, CLK | CIC_RST, CIC_CLK |
| | | | 72 | GND | GND |

**/IRQ has no pull-up on the cart**: the console has one; RP-A drives the line
low or releases it. No bus line carries anything but the edge, the RPs and
test pads (`check_nets.py` checks it).

## Pin maps

Exactly the firmware headers on fujinet-firmware branch `simplify-nes`:
`nes_bus.h` + `nes_cart.h` (RP-A) and `nes_ppu.h` (RP-B). `tools/check_nets.py`
reads them and checks the netlist against them (415 checks); `gen_sch.py`
refuses to write a sheet if `design.py`'s pin table disagrees with KiCad's
`MCU_RaspberryPi:RP2354B` symbol.

| GPIO | RP-A (U1) | GPIO | RP-B (U2) |
|---|---|---|---|
| 0-12 | CA0-CA12 | 0-13 | PA0-PA13 |
| 13-20 | CD0-CD7 | 14-21 | PD0-PD7 |
| 21, 22, 23 | M2, RW, ROMSEL_N | 22, 23 | PPU_RD_N, PPU_WR_N |
| 24, 25 | CA13, CA14 | 24 | PWR_OK |
| 26 | PWR_OK | 25, 26 | CIRAM_A10, CIRAM_CE_N |
| 27 | LED (330R, red) | 27 | nc |
| 28, 29 | debug UART TX/RX (TP5, TP6) | 28, 29 | debug UART TX/RX (TP11, TP12) |
| 30, 31 | nc | 30-32 | nc |
| 32 | IRQ_N | 33, 34 | LFRM, LCLK (in) |
| 33 | LACK (in) | 35-42 | LD7..LD0 (in, mirrored) |
| 34-41 | LD0-LD7 | 43 | LACK (out) |
| 42, 43 | LCLK, LFRM | 44 | PWR_OK again, on ADC4 (console 5 V monitor) |
| 44, 45, 46 | RP-B's SWCLK, SWDIO, RUN | 45-47 | nc |
| 47 | PA12 (MMC3 A12 filter) | | |

RP-B's USB pins are unused and its QSPI_SS is only pulled up: it never boots
from its own flash.

## Power

- **Sources:** console +5V (edge 36, `CONS_5V`) through an **AO3401A
  P-FET** whose gate is VBUS (fully on with no cable; off with USB present,
  so USB never back-feeds the console), and USB VBUS through an SS34. Both
  meet on **+5V**. R25 (4.7k) holds the gate at 0 V with no cable (Rev0's
  2026-10-07 fix).
- **+5V** feeds the AP63203 buck, both AP2112K LDOs and the WS2812B.
- **+3V3** (AP63203): ESP32-S3, microSD, CP2102N.
- **+3V3_RP** (U8) and **+3V3_RPB** (U9), one AP2112K per RP: every supply
  pin of that RP -- IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and the core
  regulator's VREG_VIN, with VREG_AVDD through 33R. An RP2350's pads are 5 V
  tolerant only while IOVDD is powered; the LDOs track +5V as the console
  rail rises, where the buck's soft-start would leave the pads unpowered for
  milliseconds with the 2A03 already driving 5 V. One LDO would carry both
  (~95 mA, +34 C); two keep the RPs' rails apart and each next to its RP.
- **PWR_OK** = CONS_5V x 3.3k / (2.2k + 3.3k) = **0.6 x CONS_5V** into both
  RPs: 3.0 V from a 5.0 V console, 3.3 V at 5.5 V -- under the 3.63 V an
  RP2350 pad takes with its IOVDD off -- and 1.32k source impedance, inside
  RP2350 erratum E9's 8.2k. Sensed before the P-FET, so a USB-powered cart in
  an unpowered console keeps D0-D7, /IRQ, PD0-PD7 and CIRAM off the bus.
  RP-B also reads it on ADC4 (bring-up: console 5 V min/max).

## The two RPs on the board

- **Placement:** RP-A over the CPU fingers at (120, 100), RP-B over the PPU
  fingers at (80, 100), both rotated so their A/D rows face the fingers and
  their link rows face north. Each RP has Rev0's local circuit and drawing:
  the core inductor and DVDD caps west, the crystal block east. The 100 nF
  for IOVDD pins 5, 15 and 24 stand under those pins' bus-field vias (below).
  Both LDOs and the PWR_OK divider sit between the RPs, above the unused EXP
  fingers, each LDO's output cap on its own RP's island.
- **The link** is drawn by `gen_pcb.link_route` as locked F.Cu: eleven nested
  arcs from RP-B's north row to RP-A's, innermost (LFRM) first, across the
  empty band between the RPs, no vias. The eight lines between each RP's
  IOVDD 50 and IOVDD 41 fan-out vias neck to 0.15 mm at 0.33 mm pitch to pass
  them; those two pins' caps stand in the north-east corner, inside the
  innermost arc, and reach their pins through the island. (The grid router
  could not do this: it routed 8 of 11.)
- **Stack (6 layers, 1.2 mm):** F.Cu signals + GND pour / In1 GND plane / In2
  + In3 signals / In4 +3V3 plane, with a +5V island south of y 86 and down
  the east edge, a +3V3_RP / +3V3_RPB island under each RP's decoupling ring
  and a DVDD / DVDD_B island under each core / B.Cu signals + GND pour.
- **The edge buses** are drawn by `gen_pcb.bus_route` as locked copper; three
  Freerouting runs had each left 13-14 bus nets open (`BUS_ESCAPE` was not
  enough for two QFN-80s). Each pin from the west column's bus pins through
  the south row to the east column's last bus pin runs out on F.Cu at 45
  degrees to its own via in a two-row field (0.5 mm pitch). From there an In2
  vertical drops to a channel track, an In3 horizontal crosses to a column
  beside the net's finger, and a vertical on the finger's face runs into the
  finger stub. Tracks are assigned by a constrained left-edge pass; per-finger
  column offsets break constraint cycles. 19 tracks per RP, 0.15 mm.
- **PA12 into RP-A** (pin 58, between RP-B's SWD pins and two IOVDD pins) has
  a locked escape too (`gen_pcb.pa12_escape`): in under the pad row, out at
  the NW corner to a via. The router left it open in all three runs.
- Everything else -- outline, shell posts, finger stubs, the ESP32, microSD,
  USB-C, buck and buttons -- is where Rev0 has it, so **Rev0's shell fits**:
  `case/board-anchors.scad` is unchanged.

## Flashing

- **ESP32-S3:** USB-C (CP2102N, esptool auto-program),
  `pio run -e fujiversal-nes -t upload`. The build embeds RP-A's image.
- **RP-A:** flashed by the S3 over PICOBOOT -- mailbox BOOTSEL doorbell first,
  else IO5 holds QSPI_SS low across an IO4 pulse on RUN (1k links, no
  transistors). RP-A's image embeds RP-B's.
- **RP-B:** never flashed; RP-A loads it into RAM over SWD (GP44-46) at every
  boot and reads back a status block (`rpb_status_t`).
- **Manual fallback:** hold SW2 (BOOTSEL) and press SW1 (RESET).
- **Last resort / bring-up:** RP-A SWD on TP1 SWCLK / TP2 SWDIO / TP4 RUN,
  RP-B on TP8 / TP9 / TP10, GND on TP3; debug UARTs on TP5/TP6 (RP-A) and
  TP11/TP12 (RP-B).

## Regenerating

KiCad 10, Python 3 (numpy), Java + Freerouting 2.4.1
(`~/.local/share/freerouting/`). `tools/build_all.sh` runs the schematic stage
and the export; `LAYOUT=1 tools/build_all.sh` adds the board (`gen_pcb.py`, then
`route_board.sh`: corner pre-routes, Freerouting, the A* finisher, stitching,
`check_vias`, `fill_zones`, the DRC gate on the saved fills), then the fab-zip
gates (`check_plane_shorts`, `check_gerbers`). `check_nets.py` reads the
firmware headers from `$FUJINET_FIRMWARE` (default `~/Workspace/fujinet-firmware`,
branch `simplify-nes`).

Edit `tools/design.py` (circuit), `tools/sch_layout.py` (drawing) and
`tools/placement.py` (layout), never the KiCad files.

## Status

- **Schematic:** six wired sheets (edge, RP-A, RP-B, ESP32-S3, USB bridge,
  power), ERC 0, netlist parity with `design.py`, `check_nets.py` 415/415.
- **Board:** routed. 133 footprints, 1239 track segments (4.78 m), 820 vias.
  KiCad DRC at every severity on the saved fills: **0 violations, 0
  unconnected, 0 schematic-parity issues**. The PA12 escape and its B.Cu run
  were added to the best of three routing variants; `gen_pcb.py` carries the
  escape for a full rebuild.
- **Fab files:** `exports/jlcpcb/` (gerbers, BOM, CPL: 114 rows).
  `check_gerbers` 0 failures, `check_plane_shorts` 0, edge orientation OK.
- **Review:** `docs/design-review-rev1.md` (kicad-happy 2.2.1, deep review
  22/22 verified).
- **Not done:** no board built; firmware not run on a console; MAME device
  not rebuilt; `bustest.nes` not written.

## Provenance and license

**CERN-OHL-W-2.0.** Rev0 (this directory's sibling) adapted with its tools; see
Rev0's README for the sources of the edge geometry, the circuit blocks and the
footprints. `fill_zones.py`, `check_vias.py` and the fab-zip gates come from
FujiNet-5200 Rev0 in this repository.
