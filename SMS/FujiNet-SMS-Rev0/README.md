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
  **WS2812C-2020** status LED, RESET / BOOTSEL / S3 EN / S3 BOOT buttons: the
  NES Rev0 FujiNet half.

**Status (2026-10-08): Rev0 v2 designed, routed and packaged for JLCPCB and PCBWay, not built.**
Nothing has run on a console.

- Schematic: ERC 0 at every severity; `tools/check_nets.py` 442/442 against
  the firmware headers; `tools/check_glue.py` 8192/8192 input combinations
  against the firmware's own glue functions; every sheet mirrors the board
  (below).
- Board: 6 layers, 100 x 93 mm, routed; KiCad DRC at every severity: 0
  violations, 0 unconnected, 0 schematic-parity issues; `check_vias.py` clean.
- Fab: `exports/jlcpcb/` and `exports/pcbway/`, checked by `tools/audit/check_fab.py`
  and `check_gerbers.py`; build-day stock in `docs/sourcing.md`.
- Shell: an OpenSCAD clamshell on the original cartridge's base (`case/`).
- Audit: kicad-happy + manufacturer datasheets, `docs/design-review-rev0.md`.

### What v2 changed (2026-10-08)

The first routed layout (branch `sms-rev0-layout`, 8213d1d) placed parts the
usual way and drew the schematic separately. v2 designs them together:

- **The board was laid out fresh from the edge** (`docs/floorplan-study.md`).
  The SMS edge is the JEDEC 32-pin memory pinout unrolled, so SRAM0 stands
  upright in the classic ROM spot and takes A0-A12, D0-D7 and GND straight from
  the fingers with no crossing. That fan-in is generated and locked before
  routing. The RP2354B sits straight north of it, SRAM1 west, the glue east
  over the strobes, the FujiNet half along the top edge.
- **The schematic was redrawn to mirror the board.** Every sheet is the board
  turned so the fingers face left, with its parts where they sit and every
  connection a wire. Details under *Schematic*.
- **RP2350-E9:** 4.7k pull-downs on GAME, LOAD, RAM_WE, MBOX and SA19, so a pad
  left as an input cannot latch at ~2.2 V and enable /OE, /WE or both SRAMs.
- **Bring-up pads** on every rail (CONS_5V, +5V, +3V3, +3V3_RP, DVDD) and on
  /CE, SRAM /OE, SRAM /WE and PWR_OK, with scope GNDs.
- **Stock swaps:** TS-1187A buttons (the TL3342 had 5 in stock) and the
  WS2812C-2020 (the WS2812B-2020 had 5).
- **Geographic references:** numbered by where each part sits, top to bottom
  and left to right (`tools/annotate.py`, `tools/refs.lock`). J1 stays the edge.
  Every reference below is v2's; the first layout's differ.
- **PCBWay package** next to JLCPCB's; JLC's gerbers carry the order-number box.

The three circuit fixes from the first audit stay:
- a 4.7k VBUS pull-down (the SS34's leakage lifted the P-FET's gate);
- the /WAIT gate pull-up 4.7k (GPIO34's reset pull-down);
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
| 33 | A12 | A12 | 34 | /CONT | CONT_N (TP16) |
| 35 | +5V | CONS_5V | 36 | A15 | A15 |
| 37 | /M1 | M1_N | 38 | /IORQ | IORQ_N |
| 39 | /RFSH | nc | 40 | /HALT | nc |
| 41 | /WAIT | WAIT_N | 42 | /INT | nc |
| 43 | KILLGA | nc | 44 | /BUSREQ | BUSREQ_N (TP15) |
| 45 | /BUSACK | nc | 46 | /RESET | RESET_N |
| 47 | CLK | CLK | 48 | /KBSEL | nc |
| 49 | /MC-F | nc | 50 | /NMI | nc |

/M8-B, /M0-7, /MC-F, /RFSH, /HALT, /INT, /NMI, /KBSEL, KILLGA and /BUSACK are
open. /CONT and /BUSREQ (inputs to the console) end on test pads TP16 / TP15
only, and nothing is fitted. /CONT is a general input the I/O chip reports on
the second controller port, not a boot or cart-detect line (the BIOS finds the
`TMR SEGA` header). Stock carts leave both open. /WAIT is driven only by the
2N7002 (Q1); the console holds its pull-up.

## RP2354B pin map

Exactly `sms_cart.h`; `tools/check_nets.py` reads the header and checks the
netlist against it.

| GPIO | Net | Goes to |
|---|---|---|
| 0-15 | A0-A15 | edge and SRAM A0-A12; A12-A15 also the glue |
| 16-23 | RP_D0-7 | RN2 / RN3 (4 x 100R) to D0-D7: edge, both SRAM DQ |
| 24-31 | RD_N WR_N MREQ_N CE_N IORQ_N RESET_N M1_N CLK | edge 4, 2, 3, 13, 38, 46, 37, 47; RD/WR/CE also the glue |
| 32 | PWR_OK | 74HCT14 output (console +5V sense), also the glue |
| 33 | RP_LED | R24 1k, red LED D7 |
| 34 | WAIT_GATE | Q1 2N7002 gate (R25 4.7k pull-up to +3V3_RP); drain = edge 41 /WAIT |
| 35, 38, 39, 40 | MBOX, GAME, RAM_WE, LOAD | glue inputs; 4.7k RP2350-E9 pull-downs |
| 36, 37 | DBG_TX, DBG_RX | J4 pins 1, 2 (pin 3 GND), DNP |
| 41-46 | SA13-SA18 | both SRAMs A13-A18 |
| 47 | SA19 | SRAM0 U10 /CE (4.7k E9 pull-down); U12C -> SA19_N -> SRAM1 U7 /CE |

GPIO40-47 are not 5 V tolerant. `check_nets.py` asserts their nets carry
nothing but input pins: glue and SRAM inputs on the 5 V rail, whose HCT
(VIH 2.0 V) and AS6C4008 (VIH 2.4 V at 4.5-5.5 V) thresholds the RP's
3.3 V outputs meet, with 0.22 V to spare at worst. QFN-80 pin numbers are
checked against `MCU_RaspberryPi:RP2354B` by `gen_sch.py`. The core (crystal,
SMPS, USB, RUN/BOOTSEL, SWD) is the NES Rev0 circuit.

**RP2350-E9** (the A2 stepping; fixed in A3/A4, but the stepping a buyer gets
is not guaranteed): a Bank 0 pad set as an input, with its output off and its
voltage between VIL and VIH, sources ~120 uA and sits near 2.2 V. A pull of
8.2k or less to GND overcomes it (datasheet p.1366-1367). R18-R22 (4.7k) hold
SA19, MBOX, GAME, RAM_WE and LOAD at 0.56 V or less against it
(`tools/audit/margins.py`), and cost 0.7 mA each while the RP drives them high.

## Glue

All 74HCT on +5V; the equations are `sms_glue_oe()` / `sms_glue_we()` in
`sms_cart.h`. RD, WR, CE = the console's strobes asserted; GAME, MBOX, RAM_WE,
LOAD active high from the RP; PWR_OK = console +5V present.

```
HIGH16 = A15 & A14     SLOT2 = A15 & !A14     WIN8 = SLOT2 & !A13     ARENA = SLOT2 & A13 & A12
/OE asserted = PWR_OK & GAME & RD & CE & !HIGH16 & !(MBOX & ARENA)
/WE asserted = PWR_OK & CE & (LOAD & RD & WIN8  |  RAM_WE & WR & SLOT2 & !(MBOX & ARENA))
U10 /CE = SA19          U7 /CE = !SA19
```

Five packages, all 19 gates used (the cart-bus sheet draws them as a wired
network by logic depth, under the strobes that feed them):

| Net | Gate | Function |
|---|---|---|
| PWR_OK_N, PWR_OK | U12A, U12B ('14) | Schmitt of 0.82 x CONS_5V, twice |
| SA19_N, CE, A15_N, MBA | U12C-F ('14) | inversions (MBA = !MBA_N) |
| CEP_N | U11A ('00) | !(CE & PWR_OK) |
| MBA_N | U8A ('10) | !(MBOX & A13 & A12) |
| WIN8 | U13B ('27) | NOR(A15_N, A14, A13) |
| SLOT2_NM | U13C ('27) | NOR(A15_N, A14, MBA) = SLOT2 & !(MBOX & ARENA) |
| RD_CEP | U13A ('27) | NOR(RD_N, CEP_N) |
| LOADWIN_N | U11B ('00) | !(LOAD & WIN8) |
| RAMWIN_N | U8B ('10) | !(RAM_WE & SLOT2_NM) |
| SLOT2_NM_N, OE_ADDR | U11C, U11D ('00) | OE_ADDR = !A15 \| SLOT2_NM = !HIGH16 & !(MBOX & ARENA) |
| WE_LOAD, WE_RAM | U9A, U9B ('27) | NOR(RD_N, CEP_N, LOADWIN_N), NOR(WR_N, CEP_N, RAMWIN_N) |
| SRAM_WE_N | U9C ('27) | NOR(WE_LOAD, WE_RAM) |
| SRAM_OE_N | U8C ('10) | NAND(RD_CEP, GAME, OE_ADDR) |

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

With the TI alternates (CD74HCT27M96 / CD74HCT10M, `timing_margins.py --ti`)
every margin stays positive: +105 ns on the M1 fetch, +11.7 ns write-data hold.

Firmware contract the glue needs:
- Set **LOAD** only while the console copies with plain data reads, never while
  it executes from $8000-$9FFF. In an opcode fetch the refresh address replaces
  A0-A15 as /RD rises.
- Keep **GAME = 0 while LOAD = 1**: together they assert /OE and /WE at once.

## Power

- **Sources:** the NES Rev0 arrangement. Console +5V (edge 1/35, `CONS_5V`)
  goes through **Q2, an AO3401A P-FET** whose gate is VBUS. Without USB the
  gate is held at 0 V by R3 (4.7k) and the FET is fully on. With USB, only its
  body diode remains, so USB never back-feeds the console. USB VBUS comes in
  through **D1, an SS34**. Both meet on **+5V**. R3 is there because the
  SS34's reverse leakage (up to 20 mA hot) flows into VBUS. With only the 69k
  sense divider, 100 uA already turned the FET off (`tools/audit/spice_checks.py`).
- **+5V:** both SRAMs, the five 74HCT packages, the WS2812C, the AP63203 buck
  (U5) and the AP2112K LDO (U6). **+3V3** (buck): ESP32-S3, microSD, CP2102N.
  **+3V3_RP** (LDO, tracks the 5 V rail): every RP2354B supply pin, so its
  pads are powered before the console's bus levels reach them.
- **Console budget:** the cart draws about 460 mA peak (the S3 transmitting,
  through the buck) and 185 mA on average from the console's 7805. There is
  10 uF + 100 nF at the fingers. Use a **1 A adaptor**: SMS2 adaptors were
  0.5 A in some regions. Measure the console rail under WiFi load at bring-up.
- **USB with the console on** (for flashing) turns the FET off: +5V =
  VBUS - VF(SS34) = 4.3-4.9 V, which can be under the 74HCTs' 4.5 V minimum.
  Use it for flashing, not for play.
- **PWR_OK** is sensed on `CONS_5V`, before the FET: R26 / R27, 22k / 100k
  (0.82 x), into a 74HCT14 Schmitt (TTL thresholds, VT+ 1.2-1.9 V), inverted
  twice, to GPIO32 and the glue. It is a console-present sense (rises at
  2.3-2.6 V), not a brown-out detector. With USB in and the console off, /OE
  and /WE stay high, so nothing but the RP can drive the dead bus; its firmware
  keys off GPIO32 and CLK.

## Flashing

As on NES Rev0:
- **S3:** over USB-C (CP2102N, esptool auto-program).
- **RP:** by the S3 over PICOBOOT: IO4 -> 1k -> RUN and IO5 -> 1k -> QSPI_SS, driven low to assert.
- **Manual BOOTSEL:** hold SW4 (BOOTSEL) while pressing SW2 (RESET).
- **SWD:** TP3 SWCLK / TP4 SWDIO, with TP5 GND and TP6 RUN.
- **RP debug UART:** J4 (DNP, 3-pin 2.54 mm header).
- **S3:** SW1 is its EN (reset), SW3 its BOOT (IO0).

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

Floorplan (`tools/placement.py`, variant P3, chosen by trial routing in
`docs/floorplan-study.md`; top view, fingers down):
- **SRAM0 (U10)** upright in the ROM spot over the fingers, its pin 17-32 end
  down: A0-A12, D0-D7 and GND reach it from the fingers without a crossing. The
  fan-in (`gen_pcb.sram0_fanin()`) is drawn and locked before routing.
- **RP2354B (U4)** straight north of SRAM0, its A/D side facing it, with the
  NES Rev0 decoupling ring, crystal, core regulator and USB / QSPI corner (same
  package, rotation and circuit). The D0-D7 100R packs RN2 / RN3 sit at its data pins.
- **SRAM1 (U7)** west of SRAM0; **the glue** east, over the strobes that feed it
  (/RD /WR /MREQ /CE and A13/A14), next to the RP's strobe side.
- **North band:** the ESP32-S3 (antenna top-left over its keep-out), the
  microSD and the USB-C / CP2102N / buck corner.
- **West edge:** the four buttons, the LEDs and the debug header, under the
  shell's pinholes and windows; the scope and rail pads beside them.
- **Screw holes:** four M3, with a 3 mm part-free ring each.

Routing (`tools/route_board.sh`):
1. The SRAM0 fan-in, the RP2354B core corner, the crystal and SWD are drawn or
   routed first on the empty board, and locked.
2. Freerouting runs (12 passes, its default greedy strategy; the best of six variants).
3. A grid A* finisher (`tools/finish_route.py`) closes what Freerouting leaves.
4. Clean-up, GND stitching, `check_vias.py`, then the DRC gate.

Netclasses:
- Default: 0.2 mm track / 0.15 mm clearance.
- Power: 0.5 mm.
- USB pairs: 0.25 mm.

The 0.4 mm-pitch RP pins' final links neck down to 0.15 / 0.12 mm (JLCPCB's
6-layer minimum is 0.09).

The routed board:
- 126 nets, all routed: Freerouting plus the finisher for the last 2 links
  (A12 and QSPI_SS);
- 1951 segments and 6055 mm of track (F.Cu 1109, In2 391, In3 353, B.Cu 98
  segments; In4 carries only the power planes);
- 743 vias, 390 of them GND, 271 of those stitching (a 4 mm grid, an edge guard row, and
  return vias beside the USB vias).

## Schematic

Six sheets: the root, `cart-bus` (A1) and `rp-core`, `fujinet`, `usb`,
`power` (A3), one per board region. **Every sheet is the board turned so the
fingers face left** (board south -> page left, north -> right, west -> top,
east -> bottom). Each part is placed where it sits on the board, and every
connection on a sheet is a wire. Signals flow left to right, from the console
to the USB-C.

- **Root:** the board outline at 2:1, turned the same way, with each sheet's
  block at its region and the nine signals between sheets wired.
- **cart-bus:** the edge on the left; A0-A12 / D0-D7 straight across to SRAM0
  in its ROM spot, then SRAM1 and the RP's GPIO unit; the RN elements inline
  on D0-D7; the glue as a gate network under the strobes; /WAIT, the LED and
  the E9 pull-downs where they sit.
- **rp-core:** the RP2354B's core unit with each supply pin's 100 nF at the
  pin (the board's ring), the regulator corner, crystal, SWD and the RUN /
  BOOTSEL / RESET network.
- **fujinet:** the ESP32-S3 (a functional symbol), its EN RC and buttons, the
  WS2812C, and the microSD's SPI lines stepping into the socket with the
  pull-ups between them.
- **usb:** the USB-C (a functional symbol) facing the CP2102N, and the
  esptool auto-program pair. This page has one crossing, and it cannot be
  avoided: RTS and DTR leave the bridge side by side, and each feeds the base
  of one transistor and the emitter of the other.
- **power:** the CONS_5V / VBUS OR on one +5V line, the LDO above it, the buck
  below it.

Symbols are functional: pins grouped by what they connect to, the stock KiCad
pin names and numbers kept (`gen_sch.verify_pin_tables` checks the RP2354B,
ESP32-S3 and USB-C symbols against the stock ones).

`gen_sch.py` gates the drawing:
- connectivity and overlap lint for every sheet;
- every net a single wired piece per sheet;
- a crossing budget per sheet: cart-bus 75 (the glue network and its feeds),
  usb 1, the rest 0;
- the **mirror check** (`tools/sch_place.py`): on each sheet the major parts
  (ICs, connectors, transistors, switches, the crystal, the LEDs) are in their
  board order across and down the page, Kendall tau >= 0.85 per axis (every
  sheet is at 1.00 / 1.00);
- netlist parity with `design.py`, and the net names equal `tools/nets.lock`,
  the names the board carries.

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

## Ordering

`tools/export.py` writes both packages; `tools/audit/check_fab.py` checks them
against the board (designators, CPL positions and rotations, drills, the gerber
gate). Step-by-step instructions are in the packages:

- **JLCPCB:** `exports/jlcpcb/ORDER-JLCPCB.md`, with the gerber zip (its
  silkscreen carries the order-number box), `BOM-JLCPCB.csv`,
  `CPL-JLCPCB.csv` (rotations and origins measured per part against EasyEDA,
  `tools/audit/jlc/`) and `consigned.csv`.
- **PCBWay:** `exports/pcbway/ORDER-PCBWay.md`, with the gerber zip,
  `BOM-PCBWay.csv` (MPN and manufacturer per line), `Centroid-PCBWay.csv`
  (KiCad's own rotations) and `Assembly-top.pdf`.

Both need: 6 layers, 1.6 mm, ENIG, **gold fingers with a 30-45 degree bevel**,
filled vias for the vias in the RP2354B's exposed pad, and assembly on the top
side. JLCPCB needs **Standard PCBA** (the RP2354B is 0.4 mm pitch).

Three lines are not in JLCPCB's stock (`docs/sourcing.md`): the AS6C4008-55TIN
SRAMs and the Nexperia 74HCT27D / 74HCT10D. Consign them, use JLC's Global
Sourcing, or order PCBWay turnkey.

**Before ordering either (VERIFY):**
1. **The tab.** Print `docs/tab-overlay-1to1.pdf` at 100 %, check its 50 mm
   ruler, and lay a real SMS cartridge board on the fingers: even fingers on
   the label side, pins 1/2 at the right, finger span and tab width.
2. **The thickness:** measure a real cartridge board (1.6 mm assumed).
3. **The TSOPs' pin 1** in the assembler's placement preview: EasyEDA has no
   footprint for the AS6C4008-55TIN, so its CPL rotation is the TSOP-I
   convention and is marked low confidence. The board's silkscreen marks pin 1
   boldly.

## Regenerating

KiCad 10.0.6, Python 3 (+ numpy), a C compiler (for `check_glue.py`); for the
board also Java and Freerouting 2.4.1
(`~/.local/share/freerouting/freerouting-2.4.1.jar`).

```sh
export FUJINET_FIRMWARE=~/Workspace/fn-sms FUJINET_SMS_BOARD=~/Workspace/fn-sms-board
tools/build_all.sh               # schematic, ERC, firmware checks, BOM / PDF, fab packages
LAYOUT=1 tools/build_all.sh      # + board: placement, routing, DRC with schematic parity, CPL / gerbers / renders
tools/audit/run_sch_audit.sh     # kicad-happy schematic audit + deep review gate
tools/audit/run_pcb_audit.sh     # kicad-happy PCB / cross / EMC / thermal / gerber audit + fab release gate
python3 tools/audit/check_fab.py # the two fab packages against the board
python3 tools/audit/sourcing.py  # build-day stock -> docs/sourcing.md (needs the network)
python3 tools/tab_overlay.py     # docs/tab-overlay-1to1.pdf
openscad -D 'part="front"' -o front.stl case/FujiNet-SMS-Shell.scad   # also "rear", "plunger"
```

Firmware heads checked: `~/Workspace/fn-sms` (`add-sms`, 10f055b87) and
`~/Workspace/fn-sms-board` (302d4950d). `check_*.py` read:
- `$FUJINET_FIRMWARE/pico/sms`. `build_all.sh` defaults to `~/Workspace/fn-sms`,
  the `add-sms` branch, when it exists.
- `$FUJINET_SMS_BOARD/include/pinmap/fujiversal-sms.h` (default
  `~/Workspace/fn-sms-board`). `fujiversal-sms.h` does not define
  `PIN_RP2040_RUN/BOOTSEL` yet, so `check_nets.py` falls back to
  `fujiversal-intv.h` (IO4/IO5) and says so.

Edit `tools/design.py` (circuit), `tools/sch_layout.py` (drawing) and
`tools/placement.py` (board), never the KiCad files.

- **Parts are addressed by key.** Every part has a design.py key (`U_RP`,
  `C_IOV5`, ...). The drawing, the placement and the audits use keys;
  references come from `tools/refs.lock` (geographic, `tools/annotate.py`).
- **Hierarchy.** The sheets join through hierarchical labels, wired on the
  root. KiCad names nets `/USB_DP` (root), `/cart-bus/A0` (one sheet) or `GND`
  (power symbols); `tools/nets.lock` freezes them.
- **Checks.** `sch_draw.py` lints connectivity, overlaps and crossings as each
  sheet is drawn; `sch_place.py` holds each sheet to the board;
  `gen_sch.check_hierarchy()` holds the labels and sheet pins to design.py;
  `gen_sch.netlist_parity()` holds KiCad's netlist to it.
- **Placement preview.** `tools/plot_placement.py` draws the placement with the
  ratsnest and prints its length and crossings.

## Parts and sourcing

`docs/sourcing.md` has every line's stock at JLCPCB and LCSC on 2026-10-08,
the quantities for 2 and 5 boards and a parts cost (about USD 29 per board).

- **Not at JLCPCB / LCSC:** AS6C4008-55TIN (C5569980), 74HCT27D,653 (C5984),
  74HCT10D,653 (C547236). All three are at DigiKey / Mouser.
  - TI's **CD74HCT27M96 (C2878706)** and **CD74HCT10M (C2863188)** are
    pin-identical alternates in single-digit stock. Every timing margin stays
    positive with them (`timing_margins.py --ti`).
  - Plain HC parts are not substitutes: the inputs need TTL thresholds.
  - The rest of the glue (SN74HCT14DR C6769, SN74HCT00DR C6764) is stocked.
- **Buttons:** TS-1187A-B-A-B (C318884, JLC basic), as on FujiNet-7800 Rev0.
- **Status LED:** WS2812C-2020-V1 (C2976072): the WS2812B-2020's package, land
  and pins, 5 mA per channel.
- The '27 and '10 use the stock `74LS27` / `74LS10` symbols and the '14 the
  `74HC14` symbol, with the HCT part as the value and its datasheet linked.
- D0-D7 series resistors are two 4 x 100R arrays (`4D03WGJ0101T5E`, C25506).
- Activity LED is red (`KT-0603R`, C2286): GPIO33 drives it from 3.3 V.
- `2N7002` C8545; header `PZ254V-11-03P` C2937625 (DNP).
- Footprints are copies of the NES Rev0 project's (KiCad library geometry, the
  AOTA inductor from Raspberry Pi's RP2350 minimal design, MIT:
  `tools/RPI-MINIMAL-LICENSE.txt`), plus the generated edge and header and the
  7800's TS-1187A. 3D models are in `3d/` (see `3d/README.md`).

## Bring-up checklist (not verifiable in CAD)

1. **Edge before ordering:** the tab overlay above, and the board thickness.
2. **Shell:** the VERIFY list in `case/case-spec.md` on each console model.
3. **Rails before the console:** on USB alone, check +5V (TP11), +3V3 (TP2),
   +3V3_RP (TP7) and DVDD (TP1, ~1.1 V); CONS_5V (TP14) stays at 0 V.
4. **Power-on:** /WAIT must be held by Q1 from the first console cycle until
   the firmware drives GPIO34 low. GAME / MBOX / RAM_WE / LOAD / SA19 sit on
   their 4.7k pull-downs until the firmware drives them.
5. **PWR_OK** (TP12) with USB in and the console off: SRAM /OE (TP9) and /WE
   (TP10) must stay high.
6. **Console 5 V headroom** under WiFi bursts on SMS1 and SMS2 (TP14; the
   7805 feeds the SRAMs, glue, buck and LDO through Q2).
7. **Timing:** scope /CE (TP8) -> SRAM /OE (TP9) on an M1 fetch from SRAM, and
   console D0-D7 against /WE (TP10) on a RAM_WE write; TP13 is the scope GND
   beside them. Then re-tune the PROVISIONAL timings in `sms_cart.c`.
8. **LOAD copy:** verify a loaded image byte for byte.
9. **RP input levels** at /RD, /WR, /CE, CLK against VIH 2.0 V (the FT pads at
   IOVDD 3.3 V).

## Firmware follow-ups (fujinet-firmware; not changed here)

- `fujiversal-sms.h` has no `PIN_RP2040_RUN` / `PIN_RP2040_BOOTSEL`, and
  there is no `pico_usb_reset` path: the S3 cannot yet force BOOTSEL on a
  running RP through IO4 / IO5, though the board wires both.
- IO42 (microSD card detect) and the RP's debug UART (GPIO36/37, J4) are
  wired but unused.
- WiFi TX power is not capped; a cap would ease the console's 5 V budget.

## Provenance and license

**CERN-OHL-W-2.0.** The RP2354B core, the ESP32-S3 / microSD / USB-UART /
power circuits and the generators are from `NES/FujiNet-NES-Rev0` in this
repository (itself from Astrocade Rev0, INTV Rev0 and the PiNTY CARD,
CERN-OHL-W-2.0); the key addressing, CPL method and shell structure from
`ATARI-2600/Fujiversal-Atari2600-Rev1`; the PCBWay package, manufacturer data
and fab checks from `ATARI-7800/FujiNet-7800-Rev0`. Edge pinout: the corrected
SMS / SMS2 slot list (Patrik's sequential order); edge geometry and
orientation: the sources above. Glue equations: `fujinet-firmware` `pico/sms`
`sms_cart.h`. Symbols and footprints: official KiCad libraries (CC-BY-SA 4.0
with exception).

## Files

| Path | Contents |
|---|---|
| `FujiNet-SMS-Rev0.kicad_pro/.kicad_sch` | KiCad 10 project: the root plus `cart-bus`, `rp-core`, `fujinet`, `usb`, `power` |
| `FujiNet-SMS-Rev0.kicad_pcb/.kicad_dru` | the 6-layer board and its custom rules |
| `FujiNet-SMS.kicad_sym`, `FujiNet-SMS.pretty/`, `3d/` | project symbol and footprint libraries, 3D models |
| `FujiNet-SMS-Rev0-BOM.csv` | grouped BOM (DNP flagged) |
| `exports/jlcpcb/`, `exports/pcbway/` | the two fab packages and their order instructions |
| `docs/` | schematic PDF, layout SVGs, board renders, tab overlay, `design-review-rev0.md`, `floorplan-study.md`, `sourcing.md` |
| `case/` | the shell (OpenSCAD), its board anchors and dimension dossier |
| `datasheets/manifest.json` | the datasheets the audit used (PDFs fetched, not committed) |
| `tools/` | generators, checks and the routing pipeline (see *Regenerating*); `tools/audit/` the audit, fab and sourcing scripts and the JLC rotation table |
