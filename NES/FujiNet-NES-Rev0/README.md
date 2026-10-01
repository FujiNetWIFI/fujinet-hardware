# FujiNet-NES Rev0

All-in-one **NES FujiNet cartridge**, built the same way as
`Astrocade/rev0` and `INTV/FujiNet-INTV-Rev0`: one board in a 72-pin cart
shell carrying both halves of the FujiNet stack.

- **RP2354B** (RP2350B die + 2 MB flash, QFN-80, all 48 GPIO used) runs the
  `fujines` cart firmware from `fujinet-firmware/pico/nes`. It sits on the
  5 V cart bus directly through its 5 V-tolerant pads, **no level shifters**,
  serves `$5000-$7FFF` (mailbox, loader ROM, WRAM) and the power-on reset
  vectors itself, watches every CPU write for mapper registers, and drives
  the two SRAMs' bank lines from PIO lookup tables.
- **2x AS6C4008-55** (512K x 8, TSOP-I-32) are the PRG and CHR memories the
  console addresses itself, powered from the 5 V rail so their outputs drive
  the 5 V bus.
- **74HCT595 / 74HCT253 / 74HCT14 / 74HCT00 / 74HCT32** on 5 V: the slow
  control bits, the CIRAM A10 mirroring mux, the console-power gate and the
  SRAM chip-select decode below.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-nes`** build of
  fujinet-firmware and is the USB *host* of the RP (CDC, VID 0xCafe) on
  IO19/IO20; it re-flashes the RP over PICOBOOT.
- **USB-C** (power + CP2102N UART with UMH3N auto-program), **microSD**
  (SPI on IO38-41, card-detect IO42), **WS2812B-2020-V6** status LED,
  RESET / BOOTSEL / S3 EN / S3 BOOT buttons -- the Astrocade Rev0 circuits
  unchanged.

**Status: schematic only.** Everything here is generated from
`tools/design.py` (see *Regenerating*). No layout exists, **no board has been
built**, and nothing has run on a console.

## Edge connector

72 pins, **2.50 mm pitch** (not 0.1 in), pins 1-36 on the label side of the
board, 37-72 on the back, pin N over pin N+36 (nesdev wiki, *Cartridge
connector*). The project footprint `NES_Cart_Edge_72` puts 1-36 on F.Cu,
37-72 on B.Cu, 1.6 x 9.5 mm fingers -- finger size and the exact position
of the fingers relative to the shell are VERIFY items for the first board.

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
| 30-33 | PPU D0-D3 | PD0-3 | 58 | PPU /A13 | PA13_N |
| 34, 35 | CIC toPak, toMB | nc | 59-61 | PPU A7, A8, A9 | PA7-9 |
| 36 | +5V | CONS_5V | 62, 63 | PPU A11, **A10** | PA11, PA10 |
| | | | 64, 65 | PPU A12, A13 | PA12, PA13 |
| | | | 66-69 | PPU D7..D4 | PD7..PD4 |
| | | | 70, 71 | CIC +RST, CLK | nc |
| | | | 72 | GND | GND |

The EXP pins, SYSTEM CLK and the four CIC pins are left open: the 10NES
lockout is an external CIClone later. **/IRQ has no pull-up on the cart**:
the firmware drives it low or releases it and the console holds the line
high; a cart pull-up would only add a second source on a wired-OR line.

## RP2354B pin map

Exactly `nes_cart.h`; `tools/check_nets.py` reads the header and checks the
netlist against it (418 checks).

| GPIO | Net | Goes to |
|---|---|---|
| 0-12 | CA0-CA12 | edge CPU A0-A12 and PRG SRAM A0-A12 |
| 13-20 | CD0-CD7 | edge CPU D0-D7 and PRG SRAM DQ0-7 |
| 21 | M2 | edge 38 (+ test pad) |
| 22 | RW | edge 14, '00 and '32 inputs |
| 23 | ROMSEL_N | edge 50, '14 input |
| 24, 25 | CA13, CA14 | edge 40, 41 (PIO1's PRG index) |
| 26-28 | PA10, PA11, PA12 | edge 63, 62, 64 (PIO0's CHR index); PA10/PA11 also '253 I0/I1 |
| 29, 30, 31 | SR_SER, SR_SCK, SR_RCK | 74HCT595 SER, SRCLK, RCLK |
| 32 | IRQ_N | edge 15, direct |
| 33-38 | PRG_A13-PRG_A18 | PRG SRAM A13-A18 (PIO1 table) |
| 39-47 | CHR_A10-CHR_A18 | CHR SRAM A10-A18 (PIO0 table) |

QFN-80 pin numbers come from KiCad's `MCU_RaspberryPi:RP2350B` symbol
(GPIO0-3 on pins 77-80, GPIO4 on pin 1); `gen_sch.py` refuses to write a
sheet if `design.py`'s table disagrees with the symbol.

'595 bits, Q0 (QA) first: `SRAM_EN`, `PRG_WE_EN`, `CHR_WE_EN`, `MIR0`,
`MIR1`, `FOURSCREEN`, `LED` (1k, green 0603), `SR_SPARE` (test pad). /OE is
tied low and /SRCLR high, so the bits are **undefined from power-on until
the RP loads the register** (a few ms); a VERIFY item below.

## Decode

All 74HCT, on the +5V rail. `ROMSEL = !ROMSEL_N`.

```
PWR_OK_N      = !VSENSE          VSENSE = CONS_5V * 150k/(100k+150k) = 3.0 V, into a '14
PWR_OK        = !PWR_OK_N
PRG /CE       = NAND(ROMSEL, SRAM_EN)
PRG /OE       = NAND(R/W, PWR_OK)
PRG /WE       = NAND(ROMSEL, PRG_WE_EN) | R/W        == !(!ROMSEL & !R/W & PRG_WE_EN)
CHR /CE       = PPU A13
CHR /OE       = PPU /RD | PWR_OK_N                   == !(!/RD & PWR_OK)
CHR /WE       = PPU /WR | !CHR_WE_EN
CIRAM A10     = 74HCT253 { PPU A10, PPU A11, 0, 1 }[MIR1:MIR0], /OE = PWR_OK_N
CIRAM /CE     = PPU /A13 | (FOURSCREEN & PWR_OK)
```

Gate budget: '14 5 of 6, '00 4 of 4, '32 4 of 4, '253 one half; every unused
input is grounded.

The one departure from `pico/nes/README.md`: `CIRAM /CE` ORs in
`FOURSCREEN & PWR_OK`, not `FOURSCREEN` alone. With the console off and the
cart alive on USB the '595 still holds whatever a four-screen game left in
it, and a plain OR would drive 5 V into the dead console's CIRAM /CE input --
the thing PWR_OK exists to prevent. While the console is powered the two
are identical.

### Timing budget (NTSC, from nesdev and the datasheets)

| Path | Budget | Spent |
|---|---|---|
| CPU read of PRG SRAM: /ROMSEL low to data valid | M2 high 350 ns, data needed at M2 fall | '14 (~15 ns) + '00 (~15 ns) + SRAM tACE 55 ns = ~85 ns |
| CPU write to PRG SRAM (loader copy) | same | '14 + '00 + '32 = ~45 ns to /WE, data held to M2 fall |
| PPU fetch: PPU A10-A12 change to CHR data | 372 ns (2 dots) per access | PIO table ~45 ns + SRAM 55 ns = ~100 ns; /OE via '32 ~15 ns after /RD |
| Mirroring: PPU A10 to CIRAM A10 | same PPU access | '253 ~20 ns |
| CIRAM /CE from PPU /A13 | same | '32 ~15 ns |
| Mailbox / WRAM / vectors served by the RP | 350 ns | the family's core1 loop; the hardware adds nothing |

HCT propagation figures are 5 V, 50 pF typicals; nothing is within a factor
of three of its budget. Remaining risk is the RP side (sampling M2, the
`nes_cart.h` PROVISIONAL note), not the glue.

## Power

- **Sources:** console +5V (edge 36, net `CONS_5V`) and USB VBUS, each
  through an SS34 into **+5V** (diode-OR, no back-feed into the console).
- **+5V** feeds the two SRAMs, the five 74HCT packages and the AP63203
  3.3 V/2 A buck (6.8 uH, 3x22 uF in, 2x22 uF out). Without USB the whole
  5 V domain runs at console 5 V minus one Schottky drop (~4.5 V), inside
  the HCT and AS6C4008 ranges.
- **+3V3** feeds the RP2354B (own SMPS: 3.3 uH to DVDD, 33 R + 4.7 uF on
  VREG_AVDD, 100 nF on each of the eight IOVDD pins), the ESP32-S3, microSD,
  CP2102N and WS2812.
- **PWR_OK** is sensed on `CONS_5V`, before the diode, so a USB-powered cart
  in an unpowered console keeps both SRAM /OE high and the '253 released.
  Because the SRAMs and logic stay on USB power, a loaded game survives a
  console power cycle while the cable is in.

Net names differ from the Astrocade board on purpose: there `+5V` was the
edge rail and `VIN` the OR node; here `+5V` is the OR node, because it is a
real supply rail for seven chips.

## Flashing

- **ESP32-S3:** USB-C (CP2102N, esptool auto-program),
  `pio run -e fujiversal-nes -t upload`. The build embeds the RP image.
- **RP2354B:** flashed by the S3 over PICOBOOT at boot -- mailbox BOOTSEL
  doorbell first, else IO5 holds QSPI_SS low across an IO4 pulse on RUN
  (1k links, same 3.3 V rail, no transistors: `forceBootselViaPins()` drives
  low to assert).
- **Manual fallback:** hold SW2 (BOOTSEL) and press SW1 (RESET); in BOOTSEL
  the RP enumerates to the S3, not a PC.
- **Last resort:** test pads TP1 SWCLK, TP2 SWDIO, TP3 GND, TP4 RUN.

`include/pinmap/fujiversal-nes.h` does not yet define
`PIN_RP2040_RUN/BOOTSEL`; the board follows the fujiversal-intv/astrocade
contract (IO4/IO5) and `check_nets.py` says so when it falls back to that
header.

## Regenerating

KiCad 10.0.6 and Python 3. `tools/build_all.sh` runs the schematic stage:

```sh
python3 tools/harvest_symbols.py   # stock KiCad symbols -> tools/symcache.sexpr (flattens "extends")
python3 tools/make_edge_fp.py      # FujiNet-NES.pretty/NES_Cart_Edge_72.kicad_mod
python3 tools/gen_sch.py           # design.py -> root + 4 sheets, FujiNet-NES.kicad_sym, .kicad_pro sheet list
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-NES-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py        # netlist vs fujinet-firmware headers, gate by gate
python3 tools/export.py            # BOM, exports/jlcpcb/BOM-JLCPCB.csv, docs/*-schematic.pdf
```

**Done for Rev0 (2026-09-30):** all of the above. ERC with `--severity-all`:
0 violations. `check_nets.py`: 418 of 418. BOM: 93 placed parts, every
line with an MPN and an LCSC code.

**Not done:** `gen_pcb.py`, `placement.py`, `fanout.py`, `finish_route.py`,
`route.py`, `tidy_tracks.py`, `set_models.py`, `rpi_graft.py` are verbatim
copies from `Astrocade/rev0/tools`, marked UNADAPTED at the top. They
encode the Astrocade outline, the single-sided blade edge and the QFN-60
regulator graft, and must be reworked for the QFN-80, the two-sided 72-pin
edge and a 5 V plane before any layout. No gerbers, CPL, DRC, 3D models or
shell exist. `export.py` adds CPL/gerbers/renders by itself once a
`.kicad_pcb` is present.

**Parts and sourcing notes:**

- `AS6C4008-55TIN` is LCSC C5569980 (extended part, 0 in JLC stock when
  checked; the sTSOP `-55STIN` C1349756 has the same pinout and a shorter
  body). Its TSOP-I pin order is the JEDEC rotated one, **not** the DIP
  order, and pins 6/9 (A17/A18) differ from ISSI's TSOP part; the symbol
  follows the Alliance datasheet.
- `74HCT253D,653` C547509: every 74HCT253 at JLC was out of stock when
  checked. CD74HCT253M (C1547301) is pin-compatible.
- `RP2354B` C39843328. The QFN-80 footprint is KiCad's stock
  `QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm`; the regulator-corner passives are
  plain 0603 here (the Astrocade board used Raspberry Pi's 0402 layout
  graft, which exists only for the QFN-60).
- Symbols: `MCU_RaspberryPi:RP2354B`, `74xx:74HCT00`, `74xx:74HCT595` are
  stock. The stock library has no 74HCT14/32/253, so those use the
  `74HC14`, `74LS32` and `74LS253` symbols with the HCT part as the value.
  `NES_Cart_Edge_72`, `AS6C4008-55TIN` and `MicroSD_TF015` are drawn by
  `gen_sch.py` into `FujiNet-NES.kicad_sym`.
- Footprints are copies of the KiCad libraries in `FujiNet-NES.pretty/`,
  plus the TF-015 (EasyEDA) and the AOTA inductor (Raspberry Pi, MIT).

## Bring-up checklist (not verifiable in CAD)

1. **Finger geometry** against a real NES board and a front-loader
   connector: pitch 2.50 mm, finger width/length, pin 1 side.
2. **Power-on race:** the '595 is random until the RP loads it. Scope
   `SRAM_EN`/`PRG_WE_EN` against the 2A03's first write cycles; if the CPU
   writes to `$8000+` before the RP is up, the PRG SRAM can take a stray
   write.
3. **PWR_OK** with the console off and USB on: no SRAM or '253 output may
   drive the bus; CIRAM /CE must stay low.
4. **Floating HCT inputs** in the same state (PPU /A13, /RD, /WR, R/W,
   /ROMSEL come from a dead console); add 100k pull-downs if they oscillate.
5. **M2-relative timing** of a mailbox read and of write-data hold after M2
   falls (`nes_cart.h` PROVISIONAL).
6. **MMC3 A12 filter and /IRQ latency** with a status-bar game.
7. **Console 5 V headroom** under WiFi bursts: the SRAMs and HCT now sit on
   the same OR node as the buck.
8. **Hardware BOOTSEL forcing** (IO5 low across an IO4 pulse) before trusting
   PICOBOOT reflash; microSD card-detect polarity on IO42.

## Provenance and license

**CERN-OHL-W-2.0.** Circuit blocks adapted from `Astrocade/rev0` and
`INTV/FujiNet-INTV-Rev0` in this repository (themselves from the PiNTY
CARD, CERN-OHL-W-2.0) and the ESP32-S3-DevKitC-1 reference design. Edge
pinout: nesdev wiki *Cartridge connector*. Memory architecture: the
EverDrive N8 as described on nesdev; nothing is copied from it. Symbols and
footprints: official KiCad libraries (CC-BY-SA 4.0 with exception); the
AOTA inductor footprint from Raspberry Pi's RP2350A minimal design (MIT,
`tools/RPI-MINIMAL-LICENSE.txt`); TF-015 from LCSC/EasyEDA C113206.

## Files

| Path | Contents |
|---|---|
| `FujiNet-NES-Rev0.kicad_pro/.kicad_sch` | KiCad 10 project: root sheet plus `cart-rp2354b`, `esp32s3-sd`, `usb-uart`, `power` |
| `FujiNet-NES.kicad_sym`, `FujiNet-NES.pretty/` | project symbol and footprint libraries (the only libraries the sheets need) |
| `FujiNet-NES-Rev0-BOM.csv`, `exports/jlcpcb/BOM-JLCPCB.csv` | grouped BOM with MPN and LCSC code on every line |
| `docs/FujiNet-NES-Rev0-schematic.pdf` | the five sheets |
| `tools/` | generators and checks (see *Regenerating*) |
