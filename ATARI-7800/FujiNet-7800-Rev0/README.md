# FujiNet-7800 Rev0

All-in-one **Atari 7800 FujiNet cartridge**: one board in the 32-pin cartridge
slot carrying both halves of the FujiNet stack.

- **RP2354B** (RP2350B die + 2 MB flash, QFN-80) at 200 MHz runs the
  `fuji7800` cart firmware from `fujinet-firmware/pico/atari-7800`. It sits on
  the console's 5 V bus through its 5 V-tolerant pads (GPIO0-31) with no
  buffers, serves the boot block, the mailbox arena and POKEY itself, and
  drives the SRAM's page lines A13-A18 plus ROM_EN, RAM_EN and A8MASK from a
  PIO slot table indexed by A13-A15 (GPIO32-40).
- **AS6C4008-55** (512K x 8, TSOP-I-32) on the 5 V rail: console A0-A7,
  A9-A12 and D0-D7 direct, SRAM A8 = A8 & !A8MASK, /CE tied active.
- **74HCT14 / 00 / 20 / 20** on 5 V: CARTSEL from A15-A11, SRAM /OE and /WE
  from it, R/W, PHI2, the slot bits and PWR_OK; the SRAM A8 mask.
- **Cart audio:** GPIO29 PWM through an RC low-pass into edge pin 18.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-atari7800`** build of
  fujinet-firmware and is the USB *host* of the RP on IO19/IO20; it re-flashes
  the RP over PICOBOOT.
- **USB-C** (power + CP2102N UART with UMH3N auto-program), **microSD**,
  **WS2812B-2020** status LED, RESET / BOOTSEL / S3 EN / S3 BOOT buttons: the
  NES / SMS Rev0 FujiNet half, unchanged.

**Status (2026-10-06): schematic only.** No layout, no board built, nothing has
run on a console. ERC 0 errors / 0 warnings; `tools/check_nets.py` 379/379
against the firmware headers; `tools/check_glue.py` 4096/4096 input
combinations against the firmware's own glue functions.

## Edge connector

32 pins, **2.54 mm pitch**, 16 per face, pin k directly over pin 33-k. Pins
3-14 and 19-30 are the 2600's 24-pin edge in the middle; the 7800 adds two
positions at each end of each face.

Pin list: Dan Boris, [Atari 7800 cartridge](https://atarihq.com/danb/7800cart/a7800cart.shtml);
[hardwarebook.info](http://www.hardwarebook.info/Atari_7800_Cartridge) and
[allpinouts](https://allpinouts.org/pinouts/connectors/cartridges_expansions/atari-7800-cartridge/)
give the same 32 signals. None of the three gives faces or dimensions.

**ASSUMED, verify against a real 7800 cart PCB:** pins 1-16 on F.Cu, the face
toward the console's **rear**, pin 1 at the **left** seen from that face with
the fingers down; pins 32-17 on B.Cu (label side), pin 32 behind pin 1. This
extends the 2600 Rev1 footprint in this repository (orientation taken from the
working FujiPlusCart prototype), whose F.Cu fingers 13-24 are 7800 pins 3-14.
**PROVISIONAL, not measured:** fingers 1.5 x 7.0 mm from 0.5 mm in (the 2600
prototype's lands), tab 42.6 x 10.0 mm (`tools/make_edge_fp.py`).
`check_nets.py` asserts the face split, pitch and pin-1 end from the footprint
file.

| Pin | Signal | Net | Pin | Signal | Net |
|---|---|---|---|---|---|
| 1 | R/W | RW | 32 | PHI2 | PHI2 |
| 2 | /HALT | HALT_N | 31 | /IRQ | IRQ_N (2N7002) |
| 3 | D3 | D3 | 30 | GND | GND |
| 4 | D4 | D4 | 29 | D2 | D2 |
| 5 | D5 | D5 | 28 | D1 | D1 |
| 6 | D6 | D6 | 27 | D0 | D0 |
| 7 | D7 | D7 | 26 | A0 | A0 |
| 8 | A12 | A12 | 25 | A1 | A1 |
| 9 | A10 | A10 | 24 | A2 | A2 |
| 10 | A11 | A11 | 23 | A3 | A3 |
| 11 | A9 | A9 | 22 | A4 | A4 |
| 12 | A8 | A8 | 21 | A5 | A5 |
| 13 | +5V | CONS_5V | 20 | A6 | A6 |
| 14 | GND | GND | 19 | A7 | A7 |
| 15 | A13 | A13 | 18 | EAUDIO | EAUDIO (audio RC) |
| 16 | A14 | A14 | 17 | A15 | A15 |

Every pin is used. There is no chip select and no reset on this edge: the glue
decodes the cart's ranges from A15-A11 itself.

## RP2354B pin map

Exactly `a78_cart.h` (and `a78map.h` for the slot word); `tools/check_nets.py`
reads both and checks the netlist against them.

| GPIO | Net | Goes to |
|---|---|---|
| 0-7 | RP_D0-7 | RN1/RN2 (4 x 100R) to D0-D7: edge, SRAM DQ |
| 8-23 | A0-A15 | edge and SRAM A0-A7, A9-A12; A8, A11-A15 also the glue; A13-A15 index the PIO table |
| 24, 25 | RW, PHI2 | edge 1, 32; also the glue |
| 26 | HALT_N | edge 2, observed only |
| 27 | PWR_OK | 74HCT14 output (console +5V sense), also the glue |
| 28 | IRQ_GATE | 2N7002 gate (10k pull-down); drain = edge 31 /IRQ; never asserted |
| 29 | AUD_PWM | audio RC to edge 18 |
| 30 | RP_LED | 1k, red LED |
| 32-37 | SA13-SA18 | SRAM A13-A18 (slot word bits 0-5) |
| 38, 39, 40 | ROM_EN, RAM_EN, A8MASK | glue inputs (slot word bits 6, 7, 8) |
| 44, 45 | DBG_TX, DBG_RX | J2 pins 1, 2 (pin 3 GND), DNP, 3.3 V only |
| 31, 41-43, 46, 47 | - | unconnected (not in `a78_cart.h`) |

GPIO40-47 are not 5 V tolerant: `check_nets.py` asserts their nets carry
nothing but 5 V-rail inputs (A8MASK into the '14) or the 3.3 V debug header,
and that every slot-table output (GPIO32-40) drives only CMOS inputs. QFN-80
pin numbers are checked against `MCU_RaspberryPi:RP2354B` by `gen_sch.py`.
The core (crystal, SMPS, USB, RUN/BOOTSEL, SWD) is the NES / SMS Rev0 circuit,
same references.

## Glue

All 74HCT on +5V; the equations are `a78_cartsel()`, `a78_glue_oe()`,
`a78_glue_we()` and `a78_glue_a8()` in `a78_cart.h`. RW = 1 for a read; ROM_EN,
RAM_EN, A8MASK active high from the slot table; PWR_OK = console +5V present.

```
CARTSEL   = A15 + A14 + !A15·!A14·!A13·A12·!A11 ($1000-$17FF) + !A15·!A14·A13·A12 ($3000-$3FFF)
          = A15 + A14 + A12·(A13 + !A11)
SRAM /OE  = !(PWR_OK · RW · ROM_EN · CARTSEL)        no PHI2: MARIA DMA is not PHI2-aligned
SRAM /WE  = !(PWR_OK · !RW · PHI2 · RAM_EN · CARTSEL)
SRAM A8   = A8 · !A8MASK
SRAM /CE  = active (GND)
```

Four packages, all 14 gates used; PWR_OK is folded into CARTSEL so both
strobes share one term:

| Net | Gate | Function |
|---|---|---|
| PWR_OK_N, PWR_OK | U3A, U3B ('14) | Schmitt of 0.82 x CONS_5V, twice |
| A13_N, RW_N, A8MASK_N | U3C-E ('14) | inversions |
| LOW_X | U4A ('00) | NAND(A13_N, A11) = A13 + !A11 |
| A15_P_N, A14_P_N | U4B, U4C ('00) | !(A15 · PWR_OK), !(A14 · PWR_OK) |
| SA8_N, SA8 | U4D ('00), U3F ('14) | A8 · !A8MASK, to SRAM A8 |
| LOW_P_N | U5A ('20) | !(A12 · LOW_X · PWR_OK) |
| CSEL_P | U5B ('20) | NAND(A15_P_N, A14_P_N, LOW_P_N) = PWR_OK · CARTSEL |
| SRAM_OE_N | U6A ('20) | NAND(CSEL_P, RW, ROM_EN) |
| SRAM_WE_N | U6B ('20) | NAND(CSEL_P, RW_N, PHI2, RAM_EN) |

`tools/check_glue.py` builds this network from the netlist (gate tables from
the pin numbers, not from `design.py`) and compares it, for all 2^12 inputs,
with `a78_cart.h` compiled on the host and with the equations above. The
harness first sweeps the firmware functions over every address (2^22
address and input combinations) to prove they read no address bit but A8 and
A11-A15, so the 4096 rows are the whole truth table. It also checks the
structure: PHI2 is exactly **one** gate from /WE (the write ends one '20 delay
after PHI2 falls), R/W one gate from /OE and two from /WE, A8 two gates from
SRAM A8. Address to /OE: A15, A14, A12 three gates, A11 four, A13 five.

Timing (6502C at 1.79 MHz, T = 559 ns; MARIA DMA reads in 280 ns (DL) and
420 ns (graphics) windows; PROVISIONAL until measured): a slot change is
about 55 ns through the PIO table plus the AS6C4008's 55 ns; the game ranges
($4000-$FFFF) reach /OE through three gates plus the SRAM's /OE access time.
The five-gate A13 path only decodes the HSC ranges ($1000-$3FFF).

## Cart audio

GPIO29 (PWM6B; an 833 kHz carrier that `fuji_audio.c` updates at the 31.4 kHz
POKEY sample rate) -> 1.5k / 10n low-pass (fc 10.6 kHz) -> 10k level resistor
-> 1u DC block -> edge 18 EAUDIO. The block leaves the console's audio node at
its no-cart DC level. **PROVISIONAL:** the 10k level (match a real POKEY cart's
level on the console).

## Power

- **Sources:** the NES / SMS Rev0 arrangement. Console +5V (edge 13,
  `CONS_5V`) through an **AO3401A P-FET** whose gate is VBUS (fully on without
  USB; with USB only its body diode remains, so USB never back-feeds the
  console); USB VBUS through an **SS34**. Both meet on **+5V**. A Schottky on
  the console side would leave the 74HCT parts at or under their 4.5 V VCC
  minimum (why NES Rev0 moved to the FET).
- **+5V:** the SRAM, the four 74HCT packages, the WS2812B, the AP63203 buck and
  the AP2112K LDO. **+3V3** (buck): ESP32-S3, microSD, CP2102N. **+3V3_RP**
  (LDO, tracks the 5 V rail): every RP2354B supply pin, so its pads are powered
  before the console's bus levels reach them.
- **PWR_OK** is sensed on `CONS_5V`, before the FET: 22k/100k (0.82 x) into a
  74HCT14 Schmitt, inverted twice, to GPIO27 and the glue. It is a
  console-present sense, not a brown-out detector. With USB in and the console
  off, SRAM /OE and /WE stay high, so nothing but the RP (whose firmware keys
  off GPIO27) and the AC-coupled audio pin can reach the dead bus.

## Flashing

As NES / SMS Rev0: the S3 over USB-C (CP2102N, esptool auto-program); the RP by
the S3 over PICOBOOT (IO4 -> 1k -> RUN, IO5 -> 1k -> QSPI_SS, low to assert);
manual BOOTSEL with SW2 + SW1; SWD on TP1/TP2 (TP3 GND, TP4 RUN). RP debug
UART on J2 (DNP, 3-pin 2.54 mm header, 3.3 V).

## Regenerating

KiCad 10.0.6, Python 3, a C compiler (for `check_glue.py`). `tools/build_all.sh`
runs everything below:

```sh
python3 tools/harvest_symbols.py   # stock symbols (via the NES Rev0 cache) -> tools/symcache.sexpr
python3 tools/make_edge_fp.py      # FujiNet-7800.pretty/Atari7800_Cart_Edge_32.kicad_mod (PROVISIONAL geometry)
python3 tools/make_fp_extra.py     # 1x03 pin header
python3 tools/gen_sch.py           # design.py + sch_layout.py -> root + 7 drawn sheets, FujiNet-7800.kicad_sym, .kicad_pro sheet list
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-7800-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py        # netlist vs a78_cart.h, a78map.h + the S3 pinmap
python3 tools/check_glue.py        # glue vs a78_glue_oe/_we/_a8, every input
python3 tools/export.py            # BOM, docs/ schematic PDF
```

`check_*.py` read `$FUJINET_FIRMWARE/pico/atari-7800` (default
`~/Workspace/fujinet-firmware`) and the S3 pinmap from
`$FUJINET_A78_BOARD/include/pinmap/fujiversal-atari7800.h` (default
`~/Workspace/fn-7800-board`), falling back to the SMS board's
`$FUJINET_SMS_BOARD/include/pinmap/fujiversal-sms.h` (default
`~/Workspace/fn-sms-board`), whose S3 contract this board copies. Neither
pinmap defines `PIN_RP2040_RUN/BOOTSEL` yet: `check_nets.py` falls back to
`fujiversal-intv.h` (IO4/IO5) and says so. Both leave `PIN_CARD_DETECT` NC;
the board wires card-detect to IO42 with a pull-up, as NES / SMS Rev0 do.

Edit `tools/design.py` (circuit) and `tools/sch_layout.py` (drawing), never the
KiCad files. The FujiNet-side sheets are drawn by the NES Rev0 functions under
that board's references and renamed (`sch_layout.NES_FIRST`).

ERC suppressions come from the NES project file: `single_global_label` (a net
named on one sheet only), `same_local_global_label` (bus members are local
labels, the same nets leave other sheets on global labels), `four_way_junction`,
`footprint_filter`, `simulation_model_issue`.

## Parts and sourcing

- JLCPCB / LCSC stock on 2026-10-06: **AS6C4008-55TIN (C5569980) at 0**, and
  the SOP-32 (-55SIN, C1350086) and TSOP-II (-55ZIN, C1350078) variants at 0
  too: consign it or buy it from DigiKey / Mouser. All three glue types are
  stocked: SN74HCT14DR (C6769), SN74HCT00DR (C6764; 74HCT00D,653 C282337 as a
  second source), CD74HCT20M96 (C2878717; 74HCT20D is pin-compatible). The
  glue deliberately avoids the '10 and '27 that SMS Rev0 could not source.
- The '20 uses the stock `74LS20` symbol and the '14 the `74HC14` symbol, with
  the HCT part as the value and its datasheet linked.
- D0-D7 series resistors are two 4 x 100R arrays (`4D03WGJ0101T5E`, C25506).
- Audio: 1.5k `0603WAF1501T5E` (C22843), 10n `0603B103K500NT` (C57112),
  10k, 1u as elsewhere on the board.
- Activity LED is red (`KT-0603R`, C2286): GPIO30 drives it from 3.3 V.
- `2N7002` C8545; header `PZ254V-11-03P` C2937625 (DNP).
- Footprints are copies of the SMS / NES Rev0 projects' (KiCad library
  geometry, the AOTA inductor from Raspberry Pi's RP2350 minimal design, MIT:
  `tools/RPI-MINIMAL-LICENSE.txt`), plus the generated edge and header. Their
  3D-model paths point at a `3d/` folder this project does not have yet.

## Bring-up checklist (not verifiable in CAD)

1. **Edge:** which face carries pins 1-16, which end pin 1 is at, finger size,
   tab width/depth and board thickness, on a real 7800 cart PCB; fix
   `make_edge_fp.py` before any layout.
2. **Write hold:** /WE rises one '20 delay after PHI2 falls; the 6502's
   address and data hold after PHI2 falls is of the same order. Scope SRAM
   address and data against /WE on a RAM_EN write.
3. **R/W during MARIA DMA:** /OE needs R/W high while MARIA, not the CPU, owns
   the bus; confirm the console holds it high with the 6502 halted.
4. **Slot changes:** ROM_EN / RAM_EN / A8MASK follow A13-A15 about 55 ns late;
   check SRAM /OE against the RP's own drive when the address moves between an
   SRAM slot and an RP-served one (boot block, POKEY); the 100R packs limit any
   overlap.
5. **Power-on:** /IRQ released by the gate pull-down until the firmware drives
   GPIO28 low; ROM_EN / RAM_EN / A8MASK rely on the pad pull-downs until the
   PIO table runs (all slots off at init).
6. **PWR_OK** with USB in and the console off: SRAM /OE and /WE must stay high.
7. **Audio:** EAUDIO level against a POKEY cart.
8. **Console 5 V headroom** under WiFi bursts (the console's regulator feeds the
   SRAM, glue, buck and LDO through the P-FET).
9. **RP input levels** at R/W, PHI2 and the address lines against the
   0.65 x IOVDD threshold.

## Provenance and license

**CERN-OHL-W-2.0.** The RP2354B core, the ESP32-S3 / microSD / USB-UART /
power sheets and the generators are from `SMS/FujiNet-SMS-Rev0` and
`NES/FujiNet-NES-Rev0` in this repository (themselves from Astrocade Rev0,
INTV Rev0 and the PiNTY CARD, CERN-OHL-W-2.0). Edge pinout: Dan Boris's 7800
cartridge page, cross-checked as above. Glue equations and pin map:
`fujinet-firmware` `pico/atari-7800` `a78_cart.h`, `a78map.h`. Symbols and
footprints: official KiCad libraries (CC-BY-SA 4.0 with exception).

## Files

| Path | Contents |
|---|---|
| `FujiNet-7800-Rev0.kicad_pro/.kicad_sch` | KiCad 10 project: root sheet plus `edge`, `rp2354b`, `sram`, `glue`, `esp32s3-sd`, `usb-uart`, `power` |
| `FujiNet-7800.kicad_sym`, `FujiNet-7800.pretty/` | project symbol and footprint libraries (the only libraries the files need) |
| `FujiNet-7800-Rev0-BOM.csv` | grouped BOM (DNP flagged) |
| `docs/FujiNet-7800-Rev0-schematic.pdf` | schematic PDF |
| `tools/` | generators and checks (see *Regenerating*) |
