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
  NES Rev0 FujiNet half, unchanged.

**Status (2026-10-06): schematic only.** No layout, no board built, nothing has
run on a console. ERC 0 errors / 0 warnings; `tools/check_nets.py` 437/437
against the firmware headers; `tools/check_glue.py` 8192/8192 input
combinations against the firmware's own glue functions.

## Edge connector

50 pins, **2.54 mm pitch**, pin 2k-1 directly over pin 2k (odd pins on one
face, even on the other). The pin list is the corrected physical order from
Patrik's sequential list (SMS Power's table mislabels 31/33/35/37).

**ASSUMED, verify against a real cartridge PCB:** odd pins on the component
side (F.Cu), pin 1 at the **right** seen from that side with the fingers down.
**PROVISIONAL, not measured:** finger 1.78 x 8.0 mm, copper 0.5-8.5 mm from
the edge, tab 65.0 x 10.0 mm (`tools/make_edge_fp.py`). `check_nets.py`
asserts the face split, pitch and pin-1 end from the footprint file.

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
| 33 | A12 | A12 | 34 | /CONT | CONT_N (TP5) |
| 35 | +5V | CONS_5V | 36 | A15 | A15 |
| 37 | /M1 | M1_N | 38 | /IORQ | IORQ_N |
| 39 | /RFSH | nc | 40 | /HALT | nc |
| 41 | /WAIT | WAIT_N | 42 | /INT | nc |
| 43 | KILLGA | nc | 44 | /BUSREQ | BUSREQ_N (TP6) |
| 45 | /BUSACK | nc | 46 | /RESET | RESET_N |
| 47 | CLK | CLK | 48 | /KBSEL | nc |
| 49 | /MC-F | nc | 50 | /NMI | nc |

/M8-B, /M0-7, /MC-F, /RFSH, /HALT, /INT, /NMI, /KBSEL, KILLGA and /BUSACK are
open. /CONT and /BUSREQ (inputs to the console) end on test pads TP5 / TP6
only: nothing is fitted and no MCU pin sees them. /WAIT is driven only by the
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
| 34 | WAIT_GATE | 2N7002 gate (10k pull-up to +3V3_RP); drain = edge 41 /WAIT |
| 35, 38, 39, 40 | MBOX, GAME, RAM_WE, LOAD | glue inputs |
| 36, 37 | DBG_TX, DBG_RX | J2 pins 1, 2 (pin 3 GND), DNP |
| 41-46 | SA13-SA18 | both SRAMs A13-A18 |
| 47 | SA19 | SRAM U2 /CE; '14 -> SA19_N -> SRAM U3 /CE |

GPIO40-47 are not 5 V tolerant: `check_nets.py` asserts their nets carry
nothing but input pins (glue and SRAM inputs on the 5 V rail, HCT/CMOS
thresholds the 3.3 V levels meet). QFN-80 pin numbers are checked against
`MCU_RaspberryPi:RP2354B` by `gen_sch.py`. The core (crystal, SMPS, USB,
RUN/BOOTSEL, SWD) is the NES Rev0 circuit, same references.

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

Five packages, all 19 gates used:

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

`tools/check_glue.py` builds this network from the netlist (gate tables from
the pin numbers, not from `design.py`), evaluates it for all 2^13 inputs and
compares with `sms_cart.h` compiled on the host and with the equations above.
It also checks the structure: /RD and /WR reach /WE through **two** gates (the
write ends two NOR3 delays after the strobe does), /RD reaches /OE through two;
/CE reaches /OE and /WE through four ('14, '00, '27, '27/'10), which only
delays the start of a cycle /CE has opened long before the strobe.

Timing (Z80 at 3.58 MHz, T = 279 ns; PROVISIONAL until measured): an M1
fetch samples data about 1.5 T after /RD falls (other reads 2 T), against two
to four gate delays plus the AS6C4008's 55 ns; the chips' /CE is static (SA19).
The LOAD path writes the SRAM during a console *read* of $8000-$9FFF, with the
RP driving D0-D7: the RP must keep driving until /WE rises, two '27 delays
after /RD does.

## Power

- **Sources:** the NES Rev0 arrangement. Console +5V (edge 1/35, `CONS_5V`)
  through an **AO3401A P-FET** whose gate is VBUS (fully on without USB; with
  USB only its body diode remains, so USB never back-feeds the console); USB
  VBUS through an **SS34**. Both meet on **+5V**. A Schottky on the console
  side leaves the 74HCT parts at or under their 4.5 V VCC minimum (why NES
  Rev0 moved to the FET).
- **+5V:** both SRAMs, the five 74HCT packages, the WS2812B, the AP63203 buck
  and the AP2112K LDO. **+3V3** (buck): ESP32-S3, microSD, CP2102N.
  **+3V3_RP** (LDO, tracks the 5 V rail): every RP2354B supply pin, so its
  pads are powered before the console's bus levels reach them.
- **PWR_OK** is sensed on `CONS_5V`, before the FET: 22k/100k (0.82 x) into a
  74HCT14 Schmitt, inverted twice, to GPIO32 and the glue. It is a
  console-present sense (HCT thresholds trip at a few volts), not a brown-out
  detector. With USB in and the console off, /OE and /WE stay high, so nothing
  but the RP (whose firmware keys off GPIO32 and CLK) can drive the dead bus.

## Flashing

As NES Rev0: the S3 over USB-C (CP2102N, esptool auto-program); the RP by the
S3 over PICOBOOT (IO4 -> 1k -> RUN, IO5 -> 1k -> QSPI_SS, low to assert);
manual BOOTSEL with SW2 + SW1; SWD on TP1/TP2 (TP3 GND, TP4 RUN). RP debug
UART on J2 (DNP, 3-pin 2.54 mm header).

## Regenerating

KiCad 10.0.6, Python 3, a C compiler (for `check_glue.py`). `tools/build_all.sh`
runs everything below:

```sh
python3 tools/harvest_symbols.py   # stock symbols (via the NES Rev0 cache) -> tools/symcache.sexpr
python3 tools/make_edge_fp.py      # FujiNet-SMS.pretty/SMS_Cart_Edge_50.kicad_mod (PROVISIONAL geometry)
python3 tools/make_fp_extra.py     # 1x03 pin header
python3 tools/gen_sch.py           # design.py + sch_layout.py -> root + 7 drawn sheets, FujiNet-SMS.kicad_sym, .kicad_pro sheet list
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-SMS-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py        # netlist vs sms_cart.h + fujiversal-sms.h
python3 tools/check_glue.py        # glue vs sms_glue_oe/_we, every input
python3 tools/export.py            # BOM, docs/ schematic PDF
```

`check_*.py` read `$FUJINET_FIRMWARE/pico/sms` (default
`~/Workspace/fujinet-firmware`) and `$FUJINET_SMS_BOARD/include/pinmap/fujiversal-sms.h`
(default `~/Workspace/fn-sms-board`). `fujiversal-sms.h` does not define
`PIN_RP2040_RUN/BOOTSEL` yet: `check_nets.py` falls back to `fujiversal-intv.h`
(IO4/IO5) and says so. It also leaves `PIN_CARD_DETECT` NC; the board wires
card-detect to IO42 with a pull-up, as NES Rev0 does.

Edit `tools/design.py` (circuit) and `tools/sch_layout.py` (drawing), never the
KiCad files. The FujiNet-side sheets are drawn by the NES Rev0 functions under
that board's references and renamed (`sch_layout.NES_FIRST`).

ERC suppressions come from the NES project file: `single_global_label` (a net
named on one sheet only), `same_local_global_label` (bus members are local
labels, the same nets leave other sheets on global labels), `four_way_junction`,
`footprint_filter`, `simulation_model_issue`.

## Parts and sourcing

- JLCPCB stock on 2026-10-06: **AS6C4008-55TIN (C5569980), 74HCT27D,653 (C5984)
  and 74HCT10D,653 (C547236) at 0**: consign them or use a second distributor.
  CD74HCT27M96 (C2878706) and CD74HCT10M (C2863188) are TI equivalents in
  single-digit stock. The rest of the glue (SN74HCT14DR C6769, SN74HCT00DR
  C6764) is stocked.
- The '27 and '10 use the stock `74LS27` / `74LS10` symbols and the '14 the
  `74HC14` symbol, with the HCT part as the value and its datasheet linked.
- D0-D7 series resistors are two 4 x 100R arrays (`4D03WGJ0101T5E`, C25506).
- Activity LED is red (`KT-0603R`, C2286): GPIO33 drives it from 3.3 V, too
  low for the NES board's 3 V green part.
- `2N7002` C8545; header `PZ254V-11-03P` C2937625 (DNP).
- Footprints are copies of the NES Rev0 project's (KiCad library geometry,
  the AOTA inductor from Raspberry Pi's RP2350 minimal design, MIT:
  `tools/RPI-MINIMAL-LICENSE.txt`), plus the generated edge and header. Their
  3D-model paths point at a `3d/` folder this project does not have yet.

## Bring-up checklist (not verifiable in CAD)

1. **Edge:** which face carries the odd pins, which end pin 1 is at, finger
   size, tab width/depth and board thickness, on a real SMS cart PCB; fix
   `make_edge_fp.py` before any layout.
2. **Write-data hold:** console D0-D7 against SRAM /WE on a RAM_WE write; /WE
   rises two '27 delays after /WR.
3. **LOAD copy:** the RP's data must outlast /WE (two '27 delays after /RD);
   verify a loaded image byte for byte.
4. **Power-on:** /WAIT held by the 2N7002 from the first console cycle until
   the firmware drives GPIO34 low (the 10k pull-up works against the RP2350's
   reset pull-down on GPIO34); GAME / MBOX / RAM_WE / LOAD rely on the pad
   pull-downs until the firmware drives them.
5. **PWR_OK** with USB in and the console off: SRAM /OE and /WE must stay high.
6. **Console 5 V headroom** under WiFi bursts (the console's regulator feeds
   SRAMs, glue, buck and LDO through the P-FET).
7. **RP input levels** at /RD, /WR, /CE, CLK against the 0.65 x IOVDD threshold.

## Provenance and license

**CERN-OHL-W-2.0.** The RP2354B core, the ESP32-S3 / microSD / USB-UART /
power sheets and the generators are from `NES/FujiNet-NES-Rev0` in this
repository (itself from Astrocade Rev0, INTV Rev0 and the PiNTY CARD,
CERN-OHL-W-2.0). Edge pinout: the corrected SMS / SMS2 slot list (Patrik's
sequential order). Glue equations: `fujinet-firmware` `pico/sms` `sms_cart.h`.
Symbols and footprints: official KiCad libraries (CC-BY-SA 4.0 with exception).

## Files

| Path | Contents |
|---|---|
| `FujiNet-SMS-Rev0.kicad_pro/.kicad_sch` | KiCad 10 project: root sheet plus `edge`, `rp2354b`, `sram`, `glue`, `esp32s3-sd`, `usb-uart`, `power` |
| `FujiNet-SMS.kicad_sym`, `FujiNet-SMS.pretty/` | project symbol and footprint libraries (the only libraries the files need) |
| `FujiNet-SMS-Rev0-BOM.csv` | grouped BOM (DNP flagged) |
| `docs/FujiNet-SMS-Rev0-schematic.pdf` | schematic PDF |
| `tools/` | generators and checks (see *Regenerating*) |
