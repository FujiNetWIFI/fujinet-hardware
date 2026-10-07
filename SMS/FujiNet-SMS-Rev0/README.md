# FujiNet-SMS Rev0

All-in-one **Sega Master System / SMS2 FujiNet cartridge**: one board in the
50-pin cartridge slot carrying both halves of the FujiNet stack.

- **RP2354B** (RP2350B die + 2 MB flash, QFN-80, all 48 GPIO used) runs the
  `fujisms` cart firmware from `fujinet-firmware/pico/sms`. It sits on the
  5 V cart bus through its 5 V-tolerant pads (GPIO0-31), serves the mailbox
  arena and the loader itself, and drives SRAM A13-A19 from the live mapper's
  page table (GPIO41-47, the pads that are *not* 5 V tolerant).
- **2x AS6C4008-55** (512K x 8, TSOP-I-32) = 1 MB on the 5 V rail: console
  A0-A12 and D0-D7 direct, the RP's bank lines A13-A18, SRAM A19 picks the chip.
- **74HCT14 / 27 / 27 / 10 / 00** on 5 V: SRAM /OE, /WE and chip select from
  the console's address and strobes and four RP mode bits, plus PWR_OK.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-sms`** build of
  fujinet-firmware and is the USB *host* of the RP on IO19/IO20; it re-flashes
  the RP over PICOBOOT.
- **USB-C** (power + CP2102N UART with UMH3N auto-program), **microSD**,
  **WS2812B-2020** status LED, RESET / BOOTSEL / S3 EN / S3 BOOT buttons: the
  NES Rev0 FujiNet half.

**Status (2026-10-07): designed and routed, not built.** Nothing has run on a console.

- Schematic: ERC 0 errors / 0 warnings; `tools/check_nets.py` 437/437
  against the firmware headers; `tools/check_glue.py` 8192/8192 input
  combinations against the firmware's own glue functions.
- Board: 6 layers, 100 x 93 mm, routed; KiCad DRC at every severity: 0
  violations, 0 unconnected, 0 schematic-parity issues.
- Shell: an OpenSCAD clamshell on the original cartridge's base (`case/`).
- Audit: kicad-happy + manufacturer datasheets, `docs/design-review-rev0.md`.
  Part 1 is the schematic, Part 2 the layout.

The schematic-only commit had the **edge connector's faces swapped**; it is
corrected here (below). Three circuit fixes came out of the audit:
- a 4.7k VBUS pull-down (the SS34's leakage lifted the P-FET's gate);
- the /WAIT gate pull-up 10k -> 4.7k (GPIO34's reset pull-down);
- 10 uF on the console's 5 V.

## Edge connector

50 pins, **2.54 mm pitch**, pin 2k-1 directly behind pin 2k.

- The **even pins (2-50) are on the component side**, which faces the label and the front of the console.
- **Pins 1/2 are at the right** seen from the front with the fingers down.

Sources:
- SMS Power's slot diagram;
- little-scale's 32K cart build;
- the component-side silkscreen of an original 171-5519 board (1200 dpi scan, "50 ... 2");
- raphnet's SMS4MBIT drawing;
- the barbeque and reidrac KiCad footprints.

All of them agree. `tools/audit/edge_orientation.py` records them and checks the footprint, and `check_nets.py` asserts the face split.

The pin list is Patrik's corrected physical order (The Hardware Book). SMS Power's table mislabels 31/33/35/37.

| | |
|---|---|
| Fingers | 1.75 x 8.75 mm, copper 0.75-9.5 mm from the edge. Original: 1.65-1.76 wide, ~1.2-10.1 mm; the open designs fall in the same range. |
| Tab | 65.8 mm wide (the original board is 66.0), 15 mm deep, 1 mm chamfers. The body widens to 100 mm above it. |
| Board | 1.6 mm (VERIFY: open designs use 1.6; no original measured). Hard gold, 30-45 degree bevel. |

| Pin | Signal | Net | Pin | Signal | Net |
|---|---|---|---|---|---|
| 1 | +5V | CONS_5V | 2 | /WR | WR_N |
| 3 | /MREQ | MREQ_N | 4 | /RD | RD_N |
| 5 | /M8-B | nc | 6 | A14 | A14 |
| 7 | A13 | A13 | 8 | A8 | A8 |
| 9 | A9 | A9 | 10 | A11 | A11 |
| 11 | /M0-7 | nc | 12 | A10 | A10 |
| 13 | /CE | CE_N | 14 | D7 | D7 |
| 15 | D6 | D6 | 16 | D5 | D5 |
| 17 | D4 | D4 | 18 | D3 | D3 |
| 19 | GND | GND | 20 | GND | GND |
| 21 | GND | GND | 22 | D2 | D2 |
| 23 | D1 | D1 | 24 | D0 | D0 |
| 25 | A0 | A0 | 26 | A1 | A1 |
| 27 | A2 | A2 | 28 | A3 | A3 |
| 29 | A4 | A4 | 30 | A5 | A5 |
| 31 | A6 | A6 | 32 | A7 | A7 |
| 33 | A12 | A12 | 34 | /CONT | CONT_N (TP1) |
| 35 | +5V | CONS_5V | 36 | A15 | A15 |
| 37 | /M1 | M1_N | 38 | /IORQ | IORQ_N |
| 39 | /RFSH | nc | 40 | /HALT | nc |
| 41 | /WAIT | WAIT_N | 42 | /INT | nc |
| 43 | KILLGA | nc | 44 | /BUSREQ | BUSREQ_N (TP2) |
| 45 | /BUSACK | nc | 46 | /RESET | RESET_N |
| 47 | CLK | CLK | 48 | /KBSEL | nc |
| 49 | /MC-F | nc | 50 | /NMI | nc |

/M8-B, /M0-7, /MC-F, /RFSH, /HALT, /INT, /NMI, /KBSEL, KILLGA and /BUSACK are
open. /CONT and /BUSREQ (inputs to the console) end on test pads TP1 / TP2
only, and nothing is fitted. /CONT is a general input the I/O chip reports on
the second controller port, not a boot or cart-detect line (the BIOS finds the
`TMR SEGA` header). Stock carts leave both open. /WAIT is driven only by the
2N7002; the console holds its pull-up.

## RP2354B pin map

Exactly `sms_cart.h`; `tools/check_nets.py` reads the header and checks the
netlist against it.

| GPIO | Net | Goes to |
|---|---|---|
| 0-15 | A0-A15 | edge and SRAM A0-A12; A12-A15 also the glue |
| 16-23 | RP_D0-7 | RN1/RN2 (4 x 100R) to D0-D7: edge, both SRAM DQ |
| 24-31 | RD_N WR_N MREQ_N CE_N IORQ_N RESET_N M1_N CLK | edge 4, 2, 3, 13, 38, 46, 37, 47; RD/WR/CE also the glue |
| 32 | PWR_OK | 74HCT14 output (console +5V sense), also the glue |
| 33 | RP_LED | 1k, red LED |
| 34 | WAIT_GATE | 2N7002 gate (4.7k pull-up to +3V3_RP); drain = edge 41 /WAIT |
| 35, 38, 39, 40 | MBOX, GAME, RAM_WE, LOAD | glue inputs |
| 36, 37 | DBG_TX, DBG_RX | J2 pins 1, 2 (pin 3 GND), DNP |
| 41-46 | SA13-SA18 | both SRAMs A13-A18 |
| 47 | SA19 | SRAM U2 /CE; '14 -> SA19_N -> SRAM U3 /CE |

GPIO40-47 are not 5 V tolerant. `check_nets.py` asserts their nets carry
nothing but input pins: glue and SRAM inputs on the 5 V rail, whose HCT
(VIH 2.0 V) and AS6C4008 (VIH 2.4 V at 4.5-5.5 V) thresholds the RP's
3.3 V outputs meet, with 0.22 V to spare at worst. QFN-80 pin numbers are
checked against `MCU_RaspberryPi:RP2354B` by `gen_sch.py`. The core (crystal,
SMPS, USB, RUN/BOOTSEL, SWD) is the NES Rev0 circuit.

## Glue

All 74HCT on +5V; the equations are `sms_glue_oe()` / `sms_glue_we()` in
`sms_cart.h`. RD, WR, CE = the console's strobes asserted; GAME, MBOX, RAM_WE,
LOAD active high from the RP; PWR_OK = console +5V present.

```
HIGH16 = A15 & A14     SLOT2 = A15 & !A14     WIN8 = SLOT2 & !A13     ARENA = SLOT2 & A13 & A12
/OE asserted = PWR_OK & GAME & RD & CE & !HIGH16 & !(MBOX & ARENA)
/WE asserted = PWR_OK & CE & (LOAD & RD & WIN8  |  RAM_WE & WR & SLOT2 & !(MBOX & ARENA))
U2 /CE = SA19          U3 /CE = !SA19
```

Five packages, all 19 gates used (the glue sheet draws them as a wired
network by logic depth):

| Net | Gate | Function |
|---|---|---|
| PWR_OK_N, PWR_OK | U4A, U4B ('14) | Schmitt of 0.82 x CONS_5V, twice |
| SA19_N, CE, A15_N, MBA | U4C-F ('14) | inversions (MBA = !MBA_N) |
| CEP_N | U8A ('00) | !(CE & PWR_OK) |
| MBA_N | U7A ('10) | !(MBOX & A13 & A12) |
| WIN8 | U6B ('27) | NOR(A15_N, A14, A13) |
| SLOT2_NM | U6C ('27) | NOR(A15_N, A14, MBA) = SLOT2 & !(MBOX & ARENA) |
| RD_CEP | U6A ('27) | NOR(RD_N, CEP_N) |
| LOADWIN_N | U8B ('00) | !(LOAD & WIN8) |
| RAMWIN_N | U7B ('10) | !(RAM_WE & SLOT2_NM) |
| SLOT2_NM_N, OE_ADDR | U8C, U8D ('00) | OE_ADDR = !A15 \| SLOT2_NM = !HIGH16 & !(MBOX & ARENA) |
| WE_LOAD, WE_RAM | U5A, U5B ('27) | NOR(RD_N, CEP_N, LOADWIN_N), NOR(WR_N, CEP_N, RAMWIN_N) |
| SRAM_WE_N | U5C ('27) | NOR(WE_LOAD, WE_RAM) |
| SRAM_OE_N | U7C ('10) | NAND(RD_CEP, GAME, OE_ADDR) |

`tools/check_glue.py` builds this network from the netlist, taking the gate
tables from the pin numbers rather than from `design.py`. It evaluates the
network for all 2^13 inputs and compares the result with `sms_cart.h`
compiled on the host and with the equations above. It also checks the
structure:
- /RD and /WR reach /WE through **two** gates (the write ends two NOR3 delays after the strobe does);
- /RD reaches /OE through two gates;
- /CE reaches /OE and /WE through four ('14, '00, '27, '27/'10).

Timing (Z80 at 3.58 MHz, T = 279 ns; `tools/audit/timing_margins.py`; PROVISIONAL until measured):
- **/CE is on the critical /OE path.** On SMS1/SMS2 the slot's /CE is /MREQ
  gated by the I/O chip's slot enable, so it falls together with /RD, not long
  before it. An M1 fetch samples data about 1.5 T after /RD falls. Against that
  are the four gates from /CE (121 ns worst case) plus the AS6C4008's 55 ns:
  +108 ns of margin, assuming the console decodes /CE in 40 ns (no published
  figure). Memory reads have +233 ns.
- **The bank lines are not static.** SA13-SA19, including SA19 as chip select,
  follow the live mapper: core1 puts the 1K page's bank on every address change.
  That leaves 359 ns for an M1 fetch (71 cycles at 200 MHz) and 483 ns for
  memory reads.
- **RAM_WE write.** /WE rises at most 52 ns after /WR (two '27s). The Z80 holds
  data at least 69.7 ns (+17.7 ns) and the address at least 89.7 ns (+37.7 ns).
- **LOAD copy.** The SRAM is written during a console *read* of $8000-$9FFF,
  with the RP driving D0-D7. The RP must keep driving until /WE rises, two '27
  delays after /RD does; the firmware's 150 ns drive gives +98 ns.

Firmware contract the glue needs:
- Set **LOAD** only while the console copies with plain data reads, never while
  it executes from $8000-$9FFF. In an opcode fetch the refresh address replaces
  A0-A15 as /RD rises.
- Keep **GAME = 0 while LOAD = 1**: together they assert /OE and /WE at once.

## Power

- **Sources:** the NES Rev0 arrangement. Console +5V (edge 1/35, `CONS_5V`)
  goes through an **AO3401A P-FET** whose gate is VBUS. Without USB the gate is
  held at 0 V by a 4.7k pull-down and the FET is fully on. With USB, only its
  body diode remains, so USB never back-feeds the console. USB VBUS comes in
  through an **SS34**. Both meet on **+5V**. The 4.7k is there because the
  SS34's reverse leakage (up to 20 mA hot) flows into VBUS. With only the 69k
  sense divider, 100 uA already turned the FET off (`tools/audit/spice_checks.py`).
- **+5V:** both SRAMs, the five 74HCT packages, the WS2812B, the AP63203 buck
  and the AP2112K LDO. **+3V3** (buck): ESP32-S3, microSD, CP2102N.
  **+3V3_RP** (LDO, tracks the 5 V rail): every RP2354B supply pin, so its
  pads are powered before the console's bus levels reach them.
- **Console budget:** the cart draws about 480 mA peak (the S3 transmitting,
  through the buck) and 180 mA on average from the console's 7805. There is
  10 uF + 100 nF at the fingers. Use a **1 A adaptor**: SMS2 adaptors were
  0.5 A in some regions. Measure the console rail under WiFi load at bring-up.
- **USB with the console on** (for flashing) turns the FET off: +5V =
  VBUS - VF(SS34) = 4.3-4.9 V, which can be under the 74HCTs' 4.5 V minimum.
  Use it for flashing, not for play.
- **PWR_OK** is sensed on `CONS_5V`, before the FET: 22k/100k (0.82 x) into a
  74HCT14 Schmitt (TTL thresholds, VT+ 1.2-1.9 V), inverted twice, to GPIO32
  and the glue. It is a console-present sense (rises at 2.3-2.6 V), not a
  brown-out detector. With USB in and the console off, /OE and /WE stay high,
  so nothing but the RP can drive the dead bus; its firmware keys off GPIO32
  and CLK.

## Flashing

As on NES Rev0:
- **S3:** over USB-C (CP2102N, esptool auto-program).
- **RP:** by the S3 over PICOBOOT: IO4 -> 1k -> RUN and IO5 -> 1k -> QSPI_SS, driven low to assert.
- **Manual BOOTSEL:** hold SW2 (BOOTSEL) while pressing SW1 (RESET).
- **SWD:** TP3 SWCLK / TP4 SWDIO, with TP5 GND and TP6 RUN.
- **RP debug UART:** J2 (DNP, 3-pin 2.54 mm header).

## Board

100 x 78 mm body on a 65.8 x 15 mm tab (93 mm overall), **1.6 mm, 6 layers**
(the NES Rev0 stack):

| Layer | Use |
|---|---|
| F.Cu | every part, the even fingers, signals + GND pour |
| In1 | GND plane |
| In2, In3 | signals |
| In4 | +3V3 plane in the north band; a +5V island over the south and up the east edge (console 5V, SRAMs, glue, LDO input, buck input); a +3V3_RP island under the RP2354B ring; a DVDD island under its core |
| B.Cu | the odd fingers, signals + GND pour (no parts) |

Placement (`tools/placement.py`, top view):
- **RP2354B** in the south centre, rotated so A4-A15 / D0-D3 face the fingers.
  Its decoupling ring, crystal, core regulator and USB / QSPI corner are the NES
  Rev0 arrangement: same package, rotation and circuit.
- **SRAMs:** side by side, upright, over the east fingers, with their data /
  A0-A3 ends toward the fingers.
- **Glue:** the five 74HCT packages north of the SRAMs.
- **D0-D7 100R packs** over the data fingers.
- **North band:** the ESP32-S3 (antenna flush with the top edge over its
  keep-out), the microSD and the USB-C / CP2102N / buck corner.
- **West edge:** the four buttons. The RP's activity LED and the WS2812 sit below the microSD.
- **Screw holes:** four M3, with a 3 mm part-free ring each.

Routing (`tools/route_board.sh`):
1. The RP2354B core corner, the crystal and SWD are routed first on the empty board, locked.
2. Freerouting runs.
3. A grid A* finisher (`tools/finish_route.py`) closes what Freerouting leaves.
4. Clean-up, GND stitching, then the DRC gate.

Netclasses:
- Default: 0.2 mm track / 0.15 mm clearance.
- Power: 0.5 mm.
- USB pairs: 0.25 mm.

The 0.4 mm-pitch RP pins' final links neck down to 0.15 / 0.12 mm (JLCPCB's
6-layer minimum is 0.09).

The routed board:
- 184 nets, all routed: Freerouting (10 passes) plus the finisher for the
  last 7 links;
- 1996 segments and 5266 mm of track;
- 756 vias, 284 of them GND stitching (a 4 mm grid, an edge guard row, and
  return vias beside the USB vias).

## Shell

`case/FujiNet-SMS-Shell.scad` (generated anchors in `case/board-anchors.scad`;
dimensions and sources in `case/case-spec.md`):
- **Outside:** 109.1 x 100.9 x 16.9 mm. It keeps the original cartridge's base
  (109.1 x 16.9, the board's component face 8.3 mm inside the label face, the
  contact edge 5.4 mm up inside an open connector mouth) and is 31.6 mm taller.
- **Front (label) half:** label recess, RESET with a printed plunger,
  BOOTSEL / S3 EN / S3 BOOT pin-holes, LED windows, the USB-C and microSD
  openings in the top wall.
- **Rear half:** a flat back plate.
- **Fasteners:** 4x M3x12 from the back.

The base dimensions marked VERIFY in `case-spec.md` come from a replica shell,
not a measured cartridge. Check them on SMS1, SMS2 and a Genesis + Power Base
Converter before printing more than one.

## Ordering (JLCPCB)

`tools/export.py` writes `exports/jlcpcb/`:
- the gerber + drill zip;
- `BOM-JLCPCB.csv`;
- `CPL-JLCPCB.csv`. Its rotations and origins are measured per part against the
  EasyEDA footprint of each LCSC code (`tools/audit/jlc/`).

Order with these options:
- 6 layers, 1.6 mm, ENIG;
- **gold fingers with a 30-45 degree bevel** (Standard PCBA, edge rails);
- epoxy-filled vias for the vias under the exposed pads.

Check the placement preview before paying, especially for **U2/U3**: EasyEDA
has no footprint for the AS6C4008-55TIN, so its rotation is the TSOP-I
convention and is marked low confidence.

## Regenerating

KiCad 10.0.6, Python 3 (+ numpy), a C compiler (for `check_glue.py`); for the
board also Java and Freerouting 2.4.1
(`~/.local/share/freerouting/freerouting-2.4.1.jar`).

```sh
tools/build_all.sh               # schematic, ERC, firmware checks, BOM / PDF
LAYOUT=1 tools/build_all.sh      # + board: placement, routing, DRC with schematic parity, CPL / gerbers / renders
tools/audit/run_sch_audit.sh     # kicad-happy schematic audit + deep review gate (docs/design-review-rev0.md Part 1)
tools/audit/run_pcb_audit.sh     # kicad-happy PCB / cross / EMC / thermal / gerber audit (Part 2)
openscad -D 'part="front"' -o front.stl case/FujiNet-SMS-Shell.scad   # also "rear", "plunger"
```

`check_*.py` read:
- `$FUJINET_FIRMWARE/pico/sms`. `build_all.sh` defaults to `~/Workspace/fn-sms`,
  the `add-sms` branch, when it exists.
- `$FUJINET_SMS_BOARD/include/pinmap/fujiversal-sms.h` (default
  `~/Workspace/fn-sms-board`). `fujiversal-sms.h` does not define
  `PIN_RP2040_RUN/BOOTSEL` yet, so `check_nets.py` falls back to
  `fujiversal-intv.h` (IO4/IO5) and says so.

Edit `tools/design.py` (circuit), `tools/sch_layout.py` (drawing) and
`tools/placement.py` (board), never the KiCad files.

- **Parts are addressed by key.** Every part has a design.py key (`U_RP`,
  `C_IOV5`, ...). The drawing and the placement use keys; references follow
  declaration order, sheet by sheet.
- **Hierarchy.** The sheets join through hierarchical labels, wired on the
  root's block diagram. KiCad names nets `/A0` (root), `/glue/VSENSE` (one
  sheet) or `GND` (power symbols). The tools compare the last path element.
  Every bus has one vector everywhere (`A[0..15]`, `D[0..7]`, `SA[13..19]`):
  KiCad joins buses of different vectors by position, not by member name.
- **Checks.** `sch_draw.py` lints connectivity and overlaps as each sheet is
  drawn. `gen_sch.check_hierarchy()` holds the labels and sheet pins to
  design.py. `gen_sch.netlist_parity()` holds KiCad's netlist to it.
- **Placement preview.** `tools/plot_placement.py` draws the placement with the
  ratsnest and prints its length and crossings.

## Parts and sourcing

- JLCPCB / LCSC stock on 2026-10-06: **AS6C4008-55TIN (C5569980), 74HCT27D,653
  (C5984) and 74HCT10D,653 (C547236) at 0**.
  - Consign the SRAMs.
  - TI's **CD74HCT27M96 (C2878706)** and **CD74HCT10M (C2863188)** are pin-identical
    alternates in single-digit stock. Every timing margin stays positive with them
    (`timing_margins.py --ti`).
  - Plain HC parts are not substitutes: the inputs need TTL thresholds.
  - The rest of the glue (SN74HCT14DR C6769, SN74HCT00DR C6764) is stocked.
- The '27 and '10 use the stock `74LS27` / `74LS10` symbols and the '14 the
  `74HC14` symbol, with the HCT part as the value and its datasheet linked.
- D0-D7 series resistors are two 4 x 100R arrays (`4D03WGJ0101T5E`, C25506).
- Activity LED is red (`KT-0603R`, C2286): GPIO33 drives it from 3.3 V.
- `2N7002` C8545; header `PZ254V-11-03P` C2937625 (DNP).
- Footprints are copies of the NES Rev0 project's (KiCad library geometry, the
  AOTA inductor from Raspberry Pi's RP2350 minimal design, MIT:
  `tools/RPI-MINIMAL-LICENSE.txt`), plus the generated edge and header. 3D
  models are in `3d/` (see `3d/README.md`).

## Bring-up checklist (not verifiable in CAD)

1. **Edge before ordering:** overlay a 1:1 print of `docs/layout-front.svg` on a
   real SMS cart board. Check: even fingers on the label side, pins 1/2 at the
   right, finger span, tab width, board thickness.
2. **Shell:** the VERIFY list in `case/case-spec.md` on each console model.
3. **Power-on:** /WAIT must be held by the 2N7002 from the first console cycle
   until the firmware drives GPIO34 low. GAME / MBOX / RAM_WE / LOAD rely on the
   pad pull-downs until the firmware drives them.
4. **PWR_OK** with USB in and the console off: SRAM /OE and /WE must stay high.
5. **Console 5 V headroom** under WiFi bursts on SMS1 and SMS2 (the 7805 feeds
   the SRAMs, glue, buck and LDO through the P-FET).
6. **Timing:** scope /MREQ -> /CE -> SRAM /OE on an M1 fetch from SRAM, and
   console D0-D7 against /WE on a RAM_WE write.
7. **LOAD copy:** verify a loaded image byte for byte.
8. **RP input levels** at /RD, /WR, /CE, CLK against VIH 2.0 V (the FT pads at
   IOVDD 3.3 V).

## Provenance and license

**CERN-OHL-W-2.0.** The RP2354B core, the ESP32-S3 / microSD / USB-UART /
power sheets and the generators are from `NES/FujiNet-NES-Rev0` in this
repository (itself from Astrocade Rev0, INTV Rev0 and the PiNTY CARD,
CERN-OHL-W-2.0); the key addressing, CPL method and shell structure from
`ATARI-2600/Fujiversal-Atari2600-Rev1`. Edge pinout: the corrected SMS / SMS2
slot list (Patrik's sequential order); edge geometry and orientation: the
sources above. Glue equations: `fujinet-firmware` `pico/sms` `sms_cart.h`.
Symbols and footprints: official KiCad libraries (CC-BY-SA 4.0 with
exception).

## Files

| Path | Contents |
|---|---|
| `FujiNet-SMS-Rev0.kicad_pro/.kicad_sch` | KiCad 10 project: the root block diagram plus `edge`, `rp2354b`, `sram`, `glue`, `esp32s3-sd`, `usb-uart`, `power` |
| `FujiNet-SMS-Rev0.kicad_pcb/.kicad_dru` | the 6-layer board and its custom rules |
| `FujiNet-SMS.kicad_sym`, `FujiNet-SMS.pretty/`, `3d/` | project symbol and footprint libraries, 3D models |
| `FujiNet-SMS-Rev0-BOM.csv` | grouped BOM (DNP flagged) |
| `exports/jlcpcb/` | gerbers + drill zip, JLCPCB BOM and CPL |
| `docs/` | schematic PDF, layout SVGs, board renders, `design-review-rev0.md` |
| `case/` | the shell (OpenSCAD), its board anchors and dimension dossier |
| `datasheets/manifest.json` | the datasheets the audit used (PDFs fetched, not committed) |
| `tools/` | generators, checks and the routing pipeline (see *Regenerating*); `tools/audit/` the audit scripts and the JLC rotation table |
