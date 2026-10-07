# FujiNet-7800 Rev0

All-in-one **Atari 7800 FujiNet cartridge**: one board in the 32-pin cartridge slot that carries
both halves of the FujiNet stack.

- **RP2354B** (RP2350B die + 2 MB flash, QFN-80) at 200 MHz.
  - Runs the `fuji7800` cart firmware from `fujinet-firmware/pico/atari-7800`.
  - Sits on the console's 5 V bus through its 5 V-tolerant pads (GPIO0-31), with no buffers.
  - Serves the boot block, the mailbox arena and POKEY itself.
  - Drives the SRAM's page lines A13-A18, plus ROM_EN, RAM_EN and A8MASK (GPIO32-40), from a PIO
    slot table indexed by A13-A15.
- **AS6C4008-55** (512K x 8, TSOP-I-32) on the 5 V rail.
  - Console A0-A7, A9-A12 and D0-D7 connect directly.
  - SRAM A8 = A8 & !A8MASK; /CE is tied active.
- **74HCT14 / 00 / 20 / 20** on 5 V make CARTSEL from A15-A11, SRAM /OE and /WE from it, R/W,
  PHI2, the slot bits and PWR_OK, and the SRAM A8 mask.
- **Cart audio:** GPIO29 PWM through an RC into edge pin 18 (EXT AUDIO). It matches a POKEY cart's
  level.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-atari7800`** build of fujinet-firmware. It is
  the USB *host* of the RP on IO19/IO20 and re-flashes the RP over PICOBOOT.
- **The NES / SMS Rev0 FujiNet half** (its buttons and status LED re-sourced; see *Parts and
  sourcing*): USB-C (power + CP2102N UART with UMH3N auto-program), microSD, WS2812C-2020 status
  LED, and RESET / BOOTSEL / S3 EN / S3 BOOT buttons.

**Status (2026-10-07): designed and routed, not built.** Nothing has run on a console yet.

| Check | Result |
|---|---|
| ERC (all severities) | 0 errors, 0 warnings |
| `tools/check_nets.py` (netlist vs `a78_cart.h`, `a78map.h`, the S3 pin map) | 383 / 383 |
| `tools/check_glue.py` (glue netlist vs the firmware's C, every input) | 4096 / 4096 |
| `tools/audit/edge_orientation.py` (edge vs six sources) | PASS |
| kicad-happy schematic audit + deep review gate | 17 / 17 verified ([docs/design-review-rev0.md](docs/design-review-rev0.md), Part 1) |
| Board | 6 layers, 72.4 x 115 mm, all 117 nets routed; DRC 0 / 0 / 0 at every severity with schematic parity; `check_vias.py` and `check_gerbers.py` clean |
| kicad-happy layout audit | every finding triaged (design review, Part 2): EMC risk score 61, thermal 97, cross-analysis 0 |
| Shell | `case/FujiNet-7800-Shell.scad`, 80 x 125 x 20 mm |

## Edge connector

32 fingers on **18 positions at 2.54 mm** per face. **Positions 3 and 16 are key slots** cut into
the board for the console connector's two plastic keys: 2 fingers | slot | 12 fingers | slot | 2
fingers. Pins 3-14 and 19-30 are the 2600's 24-pin edge in the middle.

**Faces (verified):**
- Pins 1-16 are on **F.Cu**, the component side, which faces the **console's rear**. That is also
  the side a 7800 label faces: "hold the cartridge so the name on the label faces away from you".
- Pin 1 is at the left seen from F.Cu with the fingers down.
- Pins 32-17 are on B.Cu, pin k directly behind pin 33-k.

**Geometry** (`tools/edge_geom.py`, the only place these numbers live):
- 47.0 x 16.5 mm tab;
- fingers 1.5 x 7.0 mm from 0.5 mm in;
- slots 2.4 x 10 mm centred on +-16.51 mm, 0.59 mm from the fingers;
- 1.6 mm board.

`tools/audit/edge_orientation.py` checks the footprint against:
- Otaku-flash (KiCad), tdididit's a78-flashcartplus (Eagle) and a78-devcart (gerbers);
- karri's measurements of a real cart;
- Wierer's photos of an Atari C024926 board;
- this repository's working FujiPlusCart prototype gerbers, for the faces and power fingers.

The schematic-only Rev0 had 16 contiguous positions and was wrong; see the review, Part 1, finding 1.

| Pin | Signal | Net | Pin | Signal | Net |
|---|---|---|---|---|---|
| 1 | R/W | RW | 32 | PHI2 | PHI2 |
| 2 | /HALT | HALT_N (10k to the RP) | 31 | /IRQ | IRQ_N (2N7002) |
| 3-7 | D3-D7 | D3-D7 | 30 | GND | GND |
| 8 | A12 | A12 | 29-27 | D2-D0 | D2-D0 |
| 9 | A10 | A10 | 26-19 | A0-A7 | A0-A7 |
| 10 | A11 | A11 | 18 | EXT AUDIO | EAUDIO (audio RC) |
| 11 | A9 | A9 | 17 | A15 | A15 |
| 12 | A8 | A8 | | | |
| 13 | +5V | CONS_5V | | | |
| 14 | GND | GND | | | |
| 15 | A13 | A13 | | | |
| 16 | A14 | A14 | | | |

There is no chip select and no reset on this edge. ("The console's U4", "C10", "R5", "R32" are
designators on Atari's console schematic C025231, not this board's.)
- **The glue decodes A15-A11 itself.** While the console's BIOS is mapped, the console's U4
  (74LS08) holds **A15, A14 and A12 low at the edge** (ANDed with the BIOS-disable bit).
  - CARTSEL is therefore 0, and the cart never fights the BIOS ROM.
  - The cart also never sees the BIOS's own fetches, which matters to the firmware; see
    *Firmware follow-ups*.
- **/HALT** is MARIA's weak MOS output, observed only, through a 10k at the finger.
- **/IRQ** has the console's 2.2k pull-up; the 2N7002 is fitted but never asserted.
- **EXT AUDIO** reaches the console's audio sum through its 0.1 uF + 6.8k.

## RP2354B pin map

Exactly `a78_cart.h` (and `a78map.h` for the slot word); `tools/check_nets.py` reads both.

| GPIO | Net | Goes to |
|---|---|---|
| 0-7 | RP_D0-7 | RN1/RN2 (4 x 100R) to D0-D7: edge, SRAM DQ |
| 8-23 | A0-A15 | edge and SRAM A0-A7, A9-A12; A8, A11-A15 also the glue; A13-A15 index the PIO table |
| 24, 25 | RW, PHI2 | edge 1, 32; also the glue |
| 26 | HALT_RP | edge 2 through R1 10k, observed only |
| 27 | PWR_OK | 74HCT14 output (console +5V sense), also the glue |
| 28 | IRQ_GATE | 2N7002 gate (10k pull-down); drain = edge 31 /IRQ; never asserted |
| 29 | AUD_PWM | audio RC to edge 18 |
| 30 | RP_LED | 1k, red LED |
| 32-37 | SA13-SA18 | SRAM A13-A18 (slot word bits 0-5) |
| 38, 39, 40 | ROM_EN, RAM_EN, A8MASK | glue inputs (slot word bits 6, 7, 8), 4.7k pull-downs (RP2350-E9) |
| 44, 45 | DBG_TX, DBG_RX | J2 pins 1, 2 (pin 3 GND), DNP, 3.3 V only |
| 31, 41-43, 46, 47 | - | unconnected (not in `a78_cart.h`) |

GPIO40-47 are not 5 V tolerant. `check_nets.py` asserts that their nets carry nothing but input
pins (A8MASK into the '14), their pull-down, or the 3.3 V debug header, so nothing on them can
drive 5 V back. It also asserts that every slot-table output drives only input pins, and that the
three enables have a pull-down of 8.2k or less. The core (crystal, SMPS, USB, RUN/BOOTSEL) is the NES / SMS Rev0 circuit.

## Glue

All four packages are 74HCT on +5V. The equations are `a78_cartsel()`, `a78_glue_oe()`,
`a78_glue_we()` and `a78_glue_a8()` in `a78_cart.h`:
- RW = 1 for a read;
- ROM_EN, RAM_EN and A8MASK are active high, from the slot table;
- PWR_OK = console +5V present.

```
CARTSEL   = A15 + A14 + A12·(A13 + !A11)              $4000-$FFFF, $1000-$17FF, $3000-$3FFF
SRAM /OE  = !(PWR_OK · RW · ROM_EN · CARTSEL)        no PHI2: MARIA DMA is not PHI2-aligned
SRAM /WE  = !(PWR_OK · !RW · PHI2 · RAM_EN · CARTSEL)
SRAM A8   = A8 · !A8MASK
SRAM /CE  = active (GND)
```

The glue sheet draws this as a left-to-right gate-depth diagram:
- U2 ('14): the Schmitt PWR_OK sense and the A13 / R/W / A8MASK / SA8 inversions;
- U3 ('00): LOW_X = A13 | !A11, the A15 / A14 terms gated by PWR_OK, and the SRAM A8 mask NAND;
- U4 ('20): CSEL_P = PWR_OK & CARTSEL;
- U5 ('20): the strobes.

`tools/check_glue.py` builds the network from the netlist and compares it with `a78_cart.h`
compiled on the host, for all 2^12 inputs. It also checks the gate depths: PHI2 one gate from /WE,
R/W one from /OE.

Timing (`tools/audit/timing_margins.py`; review Part 1, findings 6-7, 11):
- 6502 reads of the SRAM have 134 ns of margin at the worst-case gate delays.
- MARIA's graphics reads have at least 60 ns.
- Display-list reads have 39-64 ns, with two exceptions:
  - right after a slot change that toggles A8MASK (the mram board): -41 ns worst case, +23 typical;
  - from the high-score ranges ($1000-$17FF, $3000-$3FFF), whose decode passes the 5-gate A13
    path: -16 ns worst case, +74 typical.
- /WE releases 35 ns worst case after PHI2 falls, against the 6502's 30 ns hold: -5 ns at
  85 C / 50 pF, +19 ns typical.

All three corners are negative only with every delay at its datasheet maximum; they are bring-up
measurements.

## Cart audio

GPIO29 (PWM6B) carries an 833 kHz carrier that `fuji_audio.c` updates at the 31.4 kHz POKEY sample
rate. The path:
1. a 1.5k / 10n low-pass (fc 10.6 kHz);
2. a 10k level resistor;
3. a 1u DC block;
4. edge 18 EAUDIO;
5. the console's C10 0.1 uF + R5 6.8k into its audio sum.

At full PWM swing this delivers within +-0.7 dB of a real POKEY cart (C026461 / C301105: 1k
pull-up, 12k series) up to 5 kHz (ngspice, `tools/audit/spice_checks.py`).

## Power

- **Console 5V** (edge 13, `CONS_5V`) goes through an **AO3401A P-FET** whose gate is VBUS. It is
  fully on without USB; with USB in only its body diode remains, so USB never back-feeds the
  console. R28 4.7k holds the gate down against the SS34's reverse leakage.
- **USB VBUS** goes through an **SS34**. Both sources meet on **+5V**.
- **+5V** feeds the SRAM, the glue, the WS2812C, the AP63203 buck and the AP2112K LDO.
- **+3V3** (buck) feeds the ESP32-S3, the microSD and the CP2102N.
- **+3V3_RP** (LDO, which tracks the 5 V rail) feeds the RP2354B's IOVDD, VREG and ADC supply
  pins (its core regulator makes DVDD), so its pads are powered before the console's bus levels
  reach them.
- **Budget:** the cart peaks at about 474 mA from the console (S3 WiFi TX through the buck) and
  averages about 180 mA, on top of the console's own ~0.35-0.5 A, from a 9 V 1 A adapter through
  the 7805. **For WiFi-heavy use, power the cart from USB-C:** it then takes nothing from the
  console's 5 V but the 41 uA of the PWR_OK divider. USB power before switching the console on also wins the power-on race on PAL consoles
  (see *Bring-up*).
- **PWR_OK** is sensed on `CONS_5V`, before the FET: 22k / 100k (0.82 x) into a 74HCT14 Schmitt,
  inverted twice, to GPIO27 and the glue. With USB in and the console off, SRAM /OE and /WE stay
  high.

## Flashing

As on NES / SMS Rev0:
- **The S3:** over USB-C (CP2102N, esptool auto-program).
- **The RP:** by the S3 over PICOBOOT (IO4 -> 1k -> RUN, IO5 -> 1k -> QSPI_SS, low to assert).
- **Manual BOOTSEL:** hold SW2 and press SW1.
- **SWD:** TP7 SWCLK / TP8 SWDIO (TP9 GND, TP10 RUN) in the bring-up pad block.
- **RP debug UART:** J2 (DNP, 3-pin 2.54 mm header, 3.3 V).

## Board

## Board

72.4 x 98.5 mm body on the 47.0 x 16.5 mm tab with its two key slots (115 mm overall),
**1.6 mm, 6 layers** (the NES / SMS Rev0 stack):

| Layer | Use |
|---|---|
| F.Cu | every part, pins 1-16, signals + GND pour |
| In1 | GND plane, solid under the body |
| In2, In3 | signals |
| In4 | +3V3 plane north of y 84 (the FujiNet half); a +5V island south of it and up the east edge (console 5V, SRAM, glue, LDO and buck inputs); a +3V3_RP island under the RP2354B ring; a DVDD island under its core |
| B.Cu | pins 17-32, signals + GND pour (no parts) |

The tab carries the fingers and nothing else. Each finger has a locked stub into the body; no
tracks, vias or pour sit in the finger rows, and there is no inner copper anywhere in the tab, so
the bevel never exposes a plane.

Placement (`tools/placement.py`, top view, the edge at the bottom):
- **RP2354B** low in the body over the address fingers. Its decoupling ring, crystal, core
  regulator and USB / QSPI corner are the NES / SMS Rev0 arrangement.
- **SRAM** upright west of it, its DQ / A0-A3 end toward the data fingers.
- **D0-D7 100R packs** between the RP's south-west corner and the data fingers, their RP side
  toward the RP. The first three routes, with the packs the other way round, each left RP_D5
  open (review, Part 2).
- **Along the tab:** the console-5V P-FET by finger 13 with its sense divider beside it, the audio RC by
  finger 18, the /IRQ FET and the /HALT 10k by fingers 31 / 2.
- **Middle band:** the four 74HCT packages, the E9 pull-downs, and above them the 18-pad
  bring-up / SWD block.
- **Upper body:** the ESP32-S3 top-left (antenna flush with the top edge over its keep-out),
  microSD and USB-C on the top edge, the CP2102N and buck down the east side, the four buttons
  down the west edge.
- **Screw holes:** four M3 holes for the shell, each with a 3 mm part-free ring.

Routing (`tools/route_board.sh`):
1. The RP2354B core corner and the crystal are routed first on the empty board, and locked.
2. Freerouting runs 12 passes with its hybrid strategy.
3. A grid A* finisher (`tools/finish_route.py`) closes the last links (5 on this board).
4. Clean-up, GND stitching, `check_vias.py`, then the DRC gate.

Netclasses:
- Default: 0.2 mm track / 0.15 mm clearance.
- Power: 0.5 mm.
- VBUS: 0.3 mm.
- USB: 0.25 mm.

The 0.4 mm-pitch RP pins' last links neck down to 0.15 / 0.12 mm; JLCPCB's 6-layer minimum is
0.09.

The routed board:
- 117 nets, all routed;
- 1682 segments and 5074 mm of track;
- 686 vias, 362 of them GND (249 stitching, edge guard and USB return vias).

## Ordering

`tools/export.py` writes both fab packages from the same gerbers.

**JLCPCB (`exports/jlcpcb/`):**
- the gerber + drill zip;
- `BOM-JLCPCB.csv` (LCSC Part #);
- `CPL-JLCPCB.csv`. Its rotations and origins are measured per part against the EasyEDA footprint
  of each LCSC code (`tools/audit/jlc/`).

Options:
- 6 layers, 1.6 mm, ENIG;
- **gold fingers with a 30-45 degree bevel** (the two key slots stay as milled notches in the
  bevelled edge);
- **Standard PCBA:** Economic PCBA stops at 0.5 mm pitch, and the RP2354B is 0.4 mm.
- **Edge rails,** if JLCPCB asks for them: on the left and right body edges only. Never on the tab,
  and never on the top edge, where the USB-C, microSD and antenna sit.
- epoxy-filled vias for the vias under the exposed pads.

**The AS6C4008-55TIN is 0 at JLCPCB / LCSC: consign it.** Check U6 in the placement preview
before paying: EasyEDA has no footprint for it, so its rotation follows the TSOP-I convention and
is marked low confidence.

**PCBWay (`exports/pcbway/`):**
- the same gerber zip;
- `BOM-PCBWay.csv` (Line#, Qty, Designator, MPN, Manufacturer, Description, Package, Type, LCSC
  code for reference, Notes; the AS6C4008's sourcing note is in Notes);
- `Centroid-PCBWay.csv` (KiCad's own rotations, unmodified);
- `Assembly-top.pdf` (references and pin-1 marks).

Turnkey assembly lets PCBWay source the AS6C4008 from DigiKey / Mouser. PCB options are as for
JLCPCB.

**Before ordering either:**
1. Fit the tab. Print `docs/layout-front.svg` at 1:1, or order a cheap 2-layer coupon of the tab.
   Check that the key slots take the console's keys and every finger meets its contact, on a real
   7800.
2. Measure a real cartridge's thickness.
3. Check U6's pin 1 in the assembler's preview.

## Shell

`case/FujiNet-7800-Shell.scad` (anchors generated into `case/board-anchors.scad`; dimensions,
sources and the VERIFY list in `case/case-spec.md`):
- **Outside:** 80 x 125 x 20 mm, a 7800 cartridge's base grown taller for the board.
- **Label half:** over the component side, facing the console's rear like a 7800 label. Label
  recess, RESET with a printed plunger, pin-holes for BOOTSEL / S3 EN / S3 BOOT, LED windows.
- **Back half:** a flat plate toward the player.
- **Openings:** USB-C and microSD in the top wall.
- **Fasteners:** 4x M3x12.

`part="check"` proves the board clears both halves.

## Bring-up checklist (not verifiable in CAD)

1. **Edge:** the 1:1 / coupon fit above, on NTSC and (if available) PAL 7800s.
2. **Power-on race:** measure the RP's cold-boot time to a serving PIO. The PAL BIOS reads the
   cart about 22-62 ms after +5V; the NTSC BIOS about 0.27-0.31 s. With USB-C power connected before
   the console is switched on, the race does not exist.
3. **/WE hold:** scope PHI2, A0 and SRAM /WE on a RAM_EN write (-5 ns worst-case datasheet corner,
   +19 ns typical).
4. **MARIA display lists:** run an mram-board title (A8MASK slot changes: -41 ns worst case, +23
   typical) and a title that keeps display lists in the high-score ranges (-16 / +74).
5. **Power-on states:** /IRQ is released by its gate pull-down, and ROM_EN / RAM_EN / A8MASK are
   held low by their 4.7k pull-downs until the PIO table runs.
6. **PWR_OK** with USB in and the console off: SRAM /OE and /WE must stay high.
7. **Audio:** EAUDIO level against a POKEY cart (simulated within +-0.7 dB).
8. **Console 5 V** under WiFi bursts without USB.
9. **2600 mode:** if the BIOS ever falls back to it (open bus at the check), TIA / RIOT decode on
   A12 = 0 alone. Confirm the firmware stays off the bus (PHI2 runs continuously at 1.19 MHz
   there).

## Firmware follow-ups (fujinet-firmware, not changed here)

- **PAL detection cannot work on hardware.** `a78_cart.c` detects PAL from reads at $C000-$EFFF
  while the BIOS runs, but the console gates A15 / A14 / A12 low at the edge while its BIOS is
  mapped. Detect PAL by PHI2 frequency instead (1.773 vs 1.790 MHz, on the PWM edge counter), and
  model the gating in `emu/fujinet.cpp`.
- **Boot speed:** a minimal RAM-resident first stage that serves the boot block within about 10 ms
  of power.
- **S3 pin map:** fn-7800-board `fujiversal-atari7800.h` lacks `PIN_RP2040_RUN` (IO4) and
  `PIN_RP2040_BOOTSEL` (IO5), and sets `PIN_CARD_DETECT` to NC. The board wires IO4, IO5 and the
  microSD card-detect on IO42, as NES / SMS Rev0 do.
- **Debug UART:** the firmware never initialises GPIO44/45 (J2).

## Regenerating

KiCad 10.0.6, Python 3 (+ numpy, PIL), a C compiler (for `check_glue.py`), ngspice and pdftotext
for the audit; for the board also Java and Freerouting 2.4.1
(`~/.local/share/freerouting/freerouting-2.4.1.jar`).

```sh
tools/build_all.sh               # schematic, ERC, firmware checks, edge audit, BOM / PDF; with a board present
                                 #   also both fab packages, layout views, renders and check_gerbers.py
LAYOUT=1 tools/build_all.sh      # + regenerate the board first: placement, routing, DRC with schematic parity
tools/audit/run_sch_audit.sh     # kicad-happy schematic audit + deep review gate (review Part 1)
tools/audit/run_pcb_audit.sh     # kicad-happy PCB / cross / EMC / thermal / gerber audit (Part 2)
openscad -D 'part="label"' -o label.stl case/FujiNet-7800-Shell.scad   # also "back", "plunger", "check"
```

`check_*.py` read:
- `$FUJINET_FIRMWARE/pico/atari-7800` (default `~/Workspace/fujinet-firmware`, branch
  `add-atari7800`);
- the S3 pin map from `$FUJINET_A78_BOARD/include/pinmap/fujiversal-atari7800.h` (default
  `~/Workspace/fn-7800-board`);
- while that header lacks `PIN_RP2040_RUN` / `PIN_RP2040_BOOTSEL`, those two from the SMS
  board's `$FUJINET_SMS_BOARD/include/pinmap/fujiversal-intv.h` (default `~/Workspace/fn-sms-board`),
  the contract this board copies.

Edit `tools/design.py` (circuit), `tools/sch_layout.py` (drawing), `tools/placement.py` (board)
and `tools/edge_geom.py` (edge), never the KiCad files.
- **Keys.** Parts are addressed by key; references follow declaration order, sheet by sheet from
  the slot.
- **Hierarchy.** The sheets join through hierarchical labels, wired on the root's block diagram.
- **Buses.** Every bus has one vector everywhere (`A[0..15]`, `D[0..7]`, `SA[13..18]`).
- **Checks.** `sch_draw.py` lints each sheet. `gen_sch.check_hierarchy()` and
  `gen_sch.netlist_parity()` hold the drawing to design.py. `tools/plot_placement.py` previews a
  placement with its ratsnest length and crossings.

## Parts and sourcing (2026-10-07)

- **AS6C4008-55TIN (C5569980):** 0 at JLCPCB and LCSC. Consign it, or use PCBWay turnkey.
- **Glue, all stocked:** SN74HCT14DR (C6769), SN74HCT00DR (C6764), CD74HCT20M96 (C2878717).
- **Buttons:** TS-1187A-B-A-B (C318884, JLC basic). The NES / SMS TL3342 had 5 in stock.
- **Status LED:** WS2812C-2020-V1 (C2976072). The WS2812B-2020-V6 had 5; the land and pins are the
  same.
- **Footprints** are copies of the SMS / NES Rev0 projects' (KiCad library geometry; the AOTA
  inductor is from Raspberry Pi's RP2350 minimal design, MIT: `tools/RPI-MINIMAL-LICENSE.txt`),
  plus the generated edge, header and TS-1187A. 3D models are in `3d/`; the TS-1187A (5.1 x 5.1 x
  1.5 mm) borrows the TL3342's model (5.2 x 5.2 x 1.5 mm), as no model exists for it.

## Provenance and license

**CERN-OHL-W-2.0.**
- **Sources:** the RP2354B core, the FujiNet sheets and the generators are from `SMS/FujiNet-SMS-Rev0`
  and `NES/FujiNet-NES-Rev0` in this repository (themselves from Astrocade Rev0, INTV Rev0 and the
  PiNTY CARD, CERN-OHL-W-2.0).
- **Edge:** pinout from Dan Boris's 7800 cartridge page; geometry from the sources listed in
  `tools/audit/edge_orientation.py`.
- **Console facts:** the Atari 7800 schematics C025231 / C070354, the GCC1702B MARIA
  specification and the 7800 Software Guide.
- **Glue and pin map:** `fujinet-firmware` `pico/atari-7800` `a78_cart.h`, `a78map.h`.
- **Symbols and footprints:** official KiCad libraries (CC-BY-SA 4.0 with exception), except the
  project's own symbols (AS6C4008, the 7800 edge, the TF-015 microSD) and footprints (the edge, the
  1x03 header, the TS-1187A; the AOTA inductor from Raspberry Pi's RP2350 minimal design, MIT).

## Files

| Path | Contents |
|---|---|
| `FujiNet-7800-Rev0.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` | KiCad 10 project: root block diagram + `edge`, `rp2354b`, `glue`, `sram`, `esp32s3-sd`, `usb-uart`, `power`; the routed board |
| `FujiNet-7800.kicad_sym`, `FujiNet-7800.pretty/`, `3d/` | project symbol, footprint and model libraries |
| `FujiNet-7800-Rev0-BOM.csv` | grouped BOM (MPN, manufacturer, LCSC; DNP flagged) |
| `exports/jlcpcb/`, `exports/pcbway/` | fab packages |
| `docs/` | schematic PDF, layout SVGs, renders, `design-review-rev0.md` |
| `case/` | the shell |
| `tools/` | generators and checks; `tools/audit/` the audit scripts |
