# FujiNet-NES Rev0

All-in-one **NES FujiNet cartridge**: one board in a 72-pin Game Pak shell
carrying both halves of the FujiNet stack.

- **RP2354B** (RP2350B die + 2 MB flash, QFN-80, all 48 GPIO used) runs the
  `fujines` cart firmware from `fujinet-firmware/pico/nes` (branch
  `nes-bringup`). It sits on the 5 V cart bus directly through its
  5 V-tolerant pads, serves `$5000-$7FFF` (mailbox, loader ROM, WRAM) and the
  power-on reset vectors itself, watches every CPU write for mapper
  registers, and drives the two SRAMs' bank lines from PIO lookup tables.
- **2x AS6C4008-55** (512K x 8, TSOP-I-32) are the PRG and CHR memories the
  console addresses itself, on the 5 V rail so their outputs drive the 5 V bus.
- **74HCT595 / 253 / 14 / 20 / 00 / 32** on 5 V: the slow control bits, the
  CIRAM A10 mirroring mux, the console-power gate and the SRAM strobe decode.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-nes`** build of
  fujinet-firmware and is the USB *host* of the RP (CDC, VID 0xCafe) on
  IO19/IO20; it re-flashes the RP over PICOBOOT.
- **USB-C** (power + CP2102N UART with UMH3N auto-program), **microSD**
  (SPI on IO38-41, card-detect IO42), **WS2812B-2020** status LED,
  RESET / BOOTSEL / S3 EN / S3 BOOT buttons.
- **CIClone** footprint (ATtiny13A, DNP) on the four CIC fingers, so a stock
  NES-001 can run the cart once lockout firmware exists.

**Status (2026-10-01):** schematic audited against the manufacturer
datasheets and redone (`docs/design-review-rev0.md`); 6-layer 1.2 mm layout
generated on the measured NES-EWROM-01 outline -- see *Status* below for
the routing / DRC / export state. **No board has been built**, nothing has
run on a console.

## Edge connector

72 pins, **2.50 mm pitch** (not 0.1 in), pins 1-36 on the label side of the
board, 37-72 on the back, pin N over pin N+36 (nesdev wiki, *Cartridge
connector*). Looking at the label side with the fingers down, the fingers
read **36 .. 1 from left to right: pin 1 is at the right.** The project
footprint `NES_Cart_Edge_72` follows the NES-EWROM-01 board measured on the
nesdev *NES cartridge dimensions* page: fingers 2.0 x 12.0 mm (the four end
fingers 3.0 mm wide at +/-44.25 mm), copper 1.0-13.0 mm in from the bevelled
edge, one solder-mask window per face (the lower 6.5 mm on the label side,
11 mm on the back) exactly as Nintendo's boards have. `tools/check_nets.py`
asserts the orientation from the footprint file and
`tools/audit/edge_orientation.py` compares it with the reference pads.

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
| 34, 35 | CIC toPak, toMB | CIC_TOPAK, CIC_TOMB | 59-61 | PPU A7, A8, A9 | PA7-9 |
| 36 | +5V | CONS_5V | 62, 63 | PPU A11, **A10** | PA11, PA10 |
| | | | 64, 65 | PPU A12, A13 | PA12, PA13 |
| | | | 66-69 | PPU D7..D4 | PD7..PD4 |
| | | | 70, 71 | CIC +RST, CLK | CIC_RST, CIC_CLK |
| | | | 72 | GND | GND |

EXP0-9 and SYSTEM CLK are open. **/IRQ has no pull-up on the cart**: the
console has a 10k pull-up (nesdev), the firmware drives the line low or
releases it.

## RP2354B pin map

Exactly `nes_cart.h`; `tools/check_nets.py` reads the header and checks the
netlist against it (453 checks, including the decode gate by gate).

| GPIO | Net | Goes to |
|---|---|---|
| 0-12 | CA0-CA12 | edge CPU A0-A12 and PRG SRAM A0-A12 |
| 13-20 | CD0-CD7 | edge CPU D0-D7 and PRG SRAM DQ0-7 |
| 21 | M2 | edge 38, the '20 (PRG /WE), test pad |
| 22 | RW | edge 14, '14 and '00 inputs |
| 23 | ROMSEL_N | edge 50, '14 input |
| 24, 25 | CA13, CA14 | edge 40, 41 (PIO1's PRG index) |
| 26-28 | PA10, PA11, PA12 | edge 63, 62, 64 (PIO0's CHR index); PA10/PA11 also '253 1I0/1I1 |
| 29, 30, 31 | SR_SER, SR_SCK, SR_RCK | 74HCT595 DS, SHCP, STCP |
| 32 | IRQ_N | edge 15, direct |
| 33-38 | PRG_A13-PRG_A18 | PRG SRAM A13-A18 (PIO1 table) |
| 39-47 | CHR_A10-CHR_A18 | CHR SRAM A10-A18 (PIO0 table) |

QFN-80 pin numbers were read against the RP2350 datasheet's pinout figure
and KiCad's `MCU_RaspberryPi:RP2354B` symbol; `gen_sch.py` refuses to write
a sheet if `design.py`'s table disagrees with the symbol.

'595 bits, Q0 first: `SRAM_EN`, `PRG_WE_EN`, `CHR_WE_EN`, `MIR0`, `MIR1`,
`FOURSCREEN`, `LED` (1k, green 0603), `SR_SPARE` (test pad). Every bit has a
100k pull-down and the register's **/OE is gated**: outputs float (so the
bits read 0) for ~70-170 ms after the 5 V rail comes up and whenever the
console is off, so the undefined power-on contents of the '595 can never
enable an SRAM before the RP has loaded it.

## Decode

All 74HCT, on the +5V rail. `ROMSEL = !ROMSEL_N`, `RW_N = !RW`.

```
VSENSE        = CONS_5V * 100k/(22k+100k) = 0.82 x CONS_5V   (TI 74HCT14 VT+ reaches 0.70 x VCC)
PWR_OK_N      = !VSENSE          PWR_OK = !PWR_OK_N          both on the '14 (Schmitt)
POR           = !POR_RC          POR_RC: 1 uF to +5V, 100k to GND (starts high, decays)
'595 /OE      = NAND(PWR_OK, POR)
PRG /CE       = NAND(ROMSEL, SRAM_EN)                       '20 (4-input, spare inputs high)
PRG /OE       = NAND(R/W, PWR_OK)                           '00
PRG /WE       = NAND(M2, ROMSEL, RW_N, PRG_WE_EN)            '20: one gate after M2 falls
CHR /CE       = PPU A13
CHR /OE       = PPU /RD | PWR_OK_N                          '32
CHR /WE       = PPU /WR | !CHR_WE_EN                        '32
CIRAM A10     = '253 half a { PPU A10, PPU A11, 0, 1 }[MIR1:MIR0], /OE = PWR_OK_N
CIRAM /CE     = '253 half b ( PPU /A13 | FOURSCREEN ), /OE = PWR_OK_N
```

Gate budget: '14 6 of 6, '20 2 of 2, '00 2 of 4, '32 3 of 4, '253 both
halves; every unused input is grounded. The truth table the firmware sees is
the one in `pico/nes/README.md`; the differences are in *how* the lines are
driven: `CIRAM /CE` tri-states with the console off instead of being a '32
output into a dead console, the PRG write strobe ends on M2 rather than on
the console's /ROMSEL decoder (`tools/audit/timing_margins.py`: 28 ns
worst-case after M2 falls against the 2A03's PROVISIONAL 30 ns data hold;
the first draft was 110 ns), and `FOURSCREEN` is a '595 bit with a pull-down.

### Timing budget (NTSC, nesdev and the AS6C4008-55 datasheet)

| Path | Budget | Spent |
|---|---|---|
| CPU read of PRG SRAM: /ROMSEL low to data valid | 330 ns | '14 + '20 (58 ns worst) + tACE 55 ns = 113 ns |
| CPU write to PRG SRAM (loader copy): data hold after /WE rises | tDH 0 ns | /WE rises <= 28 ns after M2 falls; 2A03 holds ~30 ns (PROVISIONAL) |
| write pulse / data setup | tWP 45 / tDW 25 ns | ~300 ns / ~228 ns |
| PPU fetch: PPU A10-A12 change to CHR data | 372 ns (2 dots) | PIO table ~45 ns + tACE 55 ns; /OE one '32 after /RD |
| Mirroring: PPU A10 to CIRAM A10 | same PPU access | '253 ~20 ns |
| CIRAM /CE from PPU /A13 | same | '32 + '253 ~40 ns |

## Power

- **Sources:** console +5V (edge 36, `CONS_5V`) through an **AO3401A
  P-FET** whose gate is VBUS: with no cable it is fully on (~24 mV at
  0.4 A), with USB present it is off and only its body diode remains,
  pointing into the cart, so USB never back-feeds the console. USB VBUS
  comes in through an SS34. Both meet on **+5V**.
- **+5V** feeds the two SRAMs, the six 74HCT packages (VCC minimum 4.5 V,
  which the Schottky drop of the first draft left no margin for), the
  WS2812B (datasheet VDD 3.7-5.3 V), the AP63203 buck and the AP2112K LDO.
- **+3V3** (AP63203, 2 A, 4 ms soft-start): ESP32-S3, microSD, CP2102N.
- **+3V3_RP** (AP2112K, 20 us start-up, ~60 mA): every RP2354B supply pin:
  IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, and the core-regulator input
  VREG_VIN with VREG_AVDD through 33R (the datasheet asks for those two to
  rise together). The RP2350's pads are 5 V-tolerant *only while IOVDD is
  powered*; on console-only power the buck's soft-start would leave them
  unpowered for ms with the 2A03's outputs already at 5 V. The LDO tracks the
  console rail as it rises instead. (Keeping VREG_VIN on the buck would also
  have left pin 64 boxed in between LX and FB with no via spot at 0.4 mm
  pitch; on the island it joins through a stub under the package.)
- **PWR_OK** is sensed on `CONS_5V`, before the FET, so a USB-powered cart in
  an unpowered console keeps both SRAM /OE high, the '595 off and the '253
  released. Because the SRAMs and logic stay on USB power, a loaded game
  survives a console power cycle while the cable is in.

## Flashing

- **ESP32-S3:** USB-C (CP2102N, esptool auto-program),
  `pio run -e fujiversal-nes -t upload`. The build embeds the RP image.
- **RP2354B:** flashed by the S3 over PICOBOOT at boot -- mailbox BOOTSEL
  doorbell first, else IO5 holds QSPI_SS low across an IO4 pulse on RUN
  (1k links, both 3.3 V, no transistors: `forceBootselViaPins()` drives
  low to assert). `fujiversal-nes.h` does not define `PIN_RP2040_RUN/BOOTSEL`
  yet; the board follows the IO4/IO5 contract and `check_nets.py` says so
  when it falls back to the INTV header.
- **Manual fallback:** hold SW2 (BOOTSEL) and press SW1 (RESET); in BOOTSEL
  the RP enumerates to the S3, not a PC.
- **Last resort:** test pads TP1 SWCLK, TP2 SWDIO, TP3 GND, TP4 RUN.
- **CIClone:** the ATtiny's ISP lines are the CIC fingers (34 MISO/PB1,
  35 MOSI/PB0, 70 SCK/PB2) plus TP7 (/RESET) and the +5V/GND fingers.

## Layout

- **Outline:** the NES-EWROM-01 board (nesdev, measured to 0.05 mm):
  100 x 95.5 mm body, 93.5 x 14.5 mm connector tab, Nintendo's side notches,
  the 5 mm and 3 mm shell-post holes, keep-clear areas at the shell-post pads.
  1.2 mm thick (what the 72-pin connector was made for).
- **Stack (6 layers):** F.Cu signals + GND pour / In1 GND plane / In2 + In3
  signals / In4 +3V3 plane with a +5V island under the SRAM-and-HCT regions,
  a +3V3_RP island under the RP's decoupling ring and a DVDD island under its
  core / B.Cu signals + GND pour. The RP's four DVDD pins, VREG_VIN and
  VREG_PGND reach their planes through stubs and vias under the package
  (the DVDD island reaches 4.3 mm from the package centre so the pins'
  inward vias land on it; a notch west of the core leaves the VREG_VIN via
  on the +3V3_RP island). The crystal block is planar: XIN runs straight
  into the crystal's south-west pad and down to its load cap, XOUT loops
  over the crystal through the 1 k series resistor to the north-east pad
  and its load cap east of it. The tab carries fingers only; every finger
  has a locked stub into the body and the tab is a track/via keep-out on
  every layer.
- **Placement (label side only):** the RP sits 25 mm above the tab, rotated
  so the CPU bus faces the fingers (pin 1 east puts the CPU bus on the east
  half, the PPU bus on the west), the PRG SRAM north-east, the CHR SRAM
  north-west, the glue in the band between the RP and the tab, the ESP32 at
  the north-west with its antenna at the top edge, microSD and USB-C on the
  top edge, buck at the north-east, buttons on the east and west edges away
  from the shell posts. The RP's decoupling ring sits 10 mm from the package
  centre: each supply pin's fan-out via lands at the end of its 1.2 mm escape
  lane, and the extra millimetre leaves a second via column for the signal
  pins between those stubs (at 9 mm five of them could not escape at all).
  `tools/placement.py` has every coordinate.
- **Rules:** 0.2 mm tracks / 0.15 mm clearance (0.5 mm for power), 0.6/0.3 mm
  vias (0.5/0.25 under the RP), 0.25 mm copper-to-edge, annular 0.125 mm --
  all above JLCPCB's 6-layer minimums (0.09 / 0.09 / 0.25 / 0.15 / 0.2). The DRC
  floor for signal clearance is 0.12 mm: the last links at the RP's 0.4 mm-pitch
  pins are routed at 0.15 mm / 0.12 mm (`finish_route.py --neck`).
  No mask-dam check: the fab opens the mask as one window across the
  0.4 mm-pitch QFN pins and the finger field.
- **Shell:** `case/case-spec.md` (dimension dossier with VERIFY items) and
  `case/FujiNet-NES-Shell.scad`, a printable Game Pak envelope with the
  USB-C / microSD wells, button and LED holes; `case/board-anchors.scad` is
  generated from the placement.

## Regenerating

KiCad 10.0.6, Python 3 (numpy), Java + Freerouting 2.4.1
(`~/.local/share/freerouting/`). `tools/build_all.sh` runs the schematic
stage; `LAYOUT=1 tools/build_all.sh` adds the board:

```sh
python3 tools/harvest_symbols.py   # stock KiCad symbols -> tools/symcache.sexpr (flattens "extends")
python3 tools/make_edge_fp.py      # FujiNet-NES.pretty/NES_Cart_Edge_72.kicad_mod (measured geometry)
python3 tools/make_fp_extra.py     # SOT-23-5, SOIC-8
python3 tools/gen_sch.py           # design.py -> root + 4 sheets, FujiNet-NES.kicad_sym, .kicad_pro sheet list
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-NES-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py        # netlist vs fujinet-firmware headers ($FUJINET_FIRMWARE, default ~/Workspace/fn-nes)
python3 tools/gen_pcb.py           # outline, placement, plane islands, finger stubs, RP support copper, fan-out
python3 tools/finish_route.py --nets=CA13,CA14,PA11,PA10,PA12,<PPU bus>,CIC_*,CONS_5V # pre-routes Freerouting never reached (unlocked)
python3 tools/finish_route.py --nets=RP_LX,DVDD,VREG_AVDD,XIN,XOUT,XOUT_Y,SWDIO,SWCLK,CD3,SR_SER,SR_SCK,SR_RCK --lock   # RP corner, crystal, SWD, hard links
python3 tools/route.py --passes 8  # Freerouting, then the outer GND pours
python3 tools/drc_fix.py           # drop router copper that breaks DRC (the finisher redoes it)
python3 tools/finish_route.py      # A* for whatever Freerouting left open (transactional rip-up), twice with drc_fix between
python3 tools/finish_route.py --neck   # the last links at 0.15 mm (as Freerouting necks down; board min 0.1, JLC 0.09)
python3 tools/tidy_tracks.py       # router crumbs, DRC-gated
python3 tools/stitch_gnd.py        # GND stitching grid + edge guard row (every via DRC-filtered)
python3 tools/set_models.py        # 3d/ models into the library and the board
kicad-cli pcb drc --refill-zones --schematic-parity --severity-error --exit-code-violations FujiNet-NES-Rev0.kicad_pcb -o /dev/null
python3 tools/export.py            # BOM, exports/jlcpcb/{BOM,CPL,gerbers}, docs/ PDF + renders
```

Edit `tools/design.py` (circuit) and `tools/placement.py` (layout), never
the KiCad files.

## Audit (kicad-happy)

`docs/design-review-rev0.md` is the datasheet-backed review; it lists what
the first schematic got wrong and what changed. `analysis/` (gitignored)
holds the analyzer runs and `analysis/deep_review.json`; `tools/audit/`
holds the computations the review cites and the generator for the
deep-review file. `.kicad-happy.json` documents the analyzer findings that
are intentional (the 5 V bus crossings, the console-defined connector).
Datasheets go in `datasheets/` (gitignored PDFs; `manifest.json` kept):

```sh
python3 <kicad-happy>/skills/lcsc/scripts/sync_datasheets_lcsc.py FujiNet-NES-Rev0.kicad_sch --output datasheets
python3 <kicad-happy>/skills/kicad/scripts/analyze_schematic.py FujiNet-NES-Rev0.kicad_sch --analysis-dir analysis/
python3 <kicad-happy>/skills/spice/scripts/simulate_subcircuits.py --analysis-dir analysis/
python3 tools/audit/make_deep_review.py && python3 <kicad-happy>/skills/kicad/review/scripts/deep_review_gate.py analysis/deep_review.json --analysis-dir analysis/ --datasheets-dir datasheets --project-dir .
```

## Status

Rev0 is **schematic- and layout-complete, not yet built**.

- Schematic: audited with kicad-happy against manufacturer datasheets and redone
  (`docs/design-review-rev0.md`, Part 1). ERC clean; `tools/check_nets.py` 453/453
  against the firmware headers on fujinet-firmware `nes-bringup`.
- Layout: 6 layers, 1.2 mm, 100 x 110 mm (NES-EWROM-01 outline), all parts on the
  label side. KiCad DRC with schematic parity: 0 errors, 0 unconnected, 0 parity
  issues. 766 vias (221 GND stitching), 3 fiducials. Reviewed with the kicad-happy
  PCB/EMC/thermal/gerber analyzers (`docs/design-review-rev0.md`, Part 2).
- Fab outputs: `exports/jlcpcb/` (gerbers, BOM, CPL; the CIClone is DNP), renders in
  `docs/`. Order 6-layer, 1.2 mm, gold fingers with a bevel.
- Before ordering: consign or substitute the AS6C4008 SRAMs and the 74HCT253 (out of
  JLC stock); decide on filled vias for the two via-in-pad spots (review, Part 2).
- On the bench: the Part 1 measurements (2A03 write-data hold, console 5 V headroom,
  power-on window); shell fit (`case/case-spec.md` VERIFY items).
- Firmware follow-ups (fujinet-firmware, not this repo): RUN/BOOTSEL pin defines in
  `fujiversal-nes.h`, the new glue-logic decode in `pico/nes/README.md`, CIClone
  firmware.

## Parts and sourcing

- `AS6C4008-55TIN` (C5569980) and every 74HCT253 were out of JLCPCB stock on
  2026-10-01: consign them or source from a second distributor. The sTSOP
  `-55STIN` (C1349756) has the same pinout and a shorter body (different
  footprint). CY62148ELL-45ZSXIT (C2952831) is a 5 V TSOP-32 candidate only
  after its A17/A18 pins are checked against its own datasheet.
- `CD74HCT20M96` (C2878717) is the 4-input NAND; `74HCT20D` is pin-compatible.
- `RP2354B` C39843328; `AP2112K-3.3TRG1` C51118; `AO3401A` C15127 (basic
  part); `ATTINY13A-SSUR` C40382 (DNP); 4x100k array `4D03WGJ0104T5E` C1996.
- The AS6C4008 TSOP-I pin order is the JEDEC rotated one, **not** the DIP
  order, and pins 6/9 (A17/A18) differ from ISSI's TSOP part; the symbol
  follows the Alliance datasheet (verified, review table).
- Symbols: `MCU_RaspberryPi:RP2354B`, `74xx:74HCT00`, `74xx:74HCT595`,
  `Regulator_Linear:AP2112K-3.3`, `Transistor_FET:AO3401A`,
  `MCU_Microchip_ATtiny:ATtiny13A-SS` are stock; the 74HCT14/20/32/253 use
  the `74HC14`, `74LS20`, `74LS32`, `74LS253` symbols with the HCT part as
  the value. `NES_Cart_Edge_72`, `AS6C4008-55TIN` and `MicroSD_TF015` are
  drawn by `gen_sch.py` into `FujiNet-NES.kicad_sym`.
- Footprints: copies of the KiCad libraries in `FujiNet-NES.pretty/` (plus
  `SOT-23-5` and `SOIC-8` written by `make_fp_extra.py` to the same
  geometry), the TF-015 (EasyEDA) and the AOTA inductor (Raspberry Pi, MIT).
  3D models: `3d/README.md`.

## Bring-up checklist (not verifiable in CAD)

1. **Finger geometry** in a real front-loader and top-loader: insertion
   force, contact wipe within the 1.0-13.0 mm copper, no shadowing by the shell.
2. **Power-on:** scope IOVDD (+3V3_RP) against CONS_5V while the console
   comes up; scope `SR_OE_N` and `SRAM_EN` against the 2A03's first cycles
   (the '595 must stay off until the RP has loaded it).
3. **PWR_OK** with the console off and USB on: no SRAM or '253 output may
   drive the bus; CIRAM /CE and CIRAM A10 must float.
4. **Write-data hold:** CPU D0-D7 against PRG /WE on a loader copy (the
   PROVISIONAL 30 ns in `nes_cart.h`); verify the copied image byte for byte.
5. **M2-relative timing** of a mailbox read (RP serves within 350 ns).
6. **MMC3 A12 filter and /IRQ latency** with a status-bar game.
7. **Console 5 V headroom** under WiFi bursts: SRAMs, HCT and the buck all
   draw from the NES's 7805 through the P-FET.
8. **Hardware BOOTSEL forcing** (IO5 low across an IO4 pulse) before trusting
   PICOBOOT reflash; microSD card-detect polarity on IO42.
9. **RP input levels** at M2 / R/W / PPU A10-A12 against the 0.65 x IOVDD
   threshold (NMOS console outputs).

## Provenance and license

**CERN-OHL-W-2.0.** Circuit blocks adapted from `Astrocade/rev0` and
`INTV/FujiNet-INTV-Rev0` in this repository (themselves from the PiNTY
CARD, CERN-OHL-W-2.0) and the ESP32-S3-DevKitC-1 reference design, then
audited and changed as `docs/design-review-rev0.md` records. Edge pinout:
nesdev wiki *Cartridge connector*. Edge and outline geometry: nesdev *NES
cartridge dimensions* (NES-EWROM-01, Gumball2415's measurements, TAPR OHL --
dimensions only, no files copied), cross-checked against nesos-dev's
nes-dev-cart (GPL, orientation only). Memory architecture: the EverDrive N8
as described on nesdev; nothing is copied from it. CIClone pin map: the
common ATtiny13A NES CIC clone. Symbols and footprints: official KiCad
libraries (CC-BY-SA 4.0 with exception); the AOTA inductor footprint from
Raspberry Pi's RP2350A minimal design (MIT, `tools/RPI-MINIMAL-LICENSE.txt`);
TF-015 from LCSC/EasyEDA C113206.

## Files

| Path | Contents |
|---|---|
| `FujiNet-NES-Rev0.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` | KiCad 10 project: root sheet plus `cart-rp2354b`, `esp32s3-sd`, `usb-uart`, `power`; the board; the custom rules |
| `FujiNet-NES.kicad_sym`, `FujiNet-NES.pretty/`, `3d/` | project symbol, footprint and 3D-model libraries (the only libraries the files need) |
| `FujiNet-NES-Rev0-BOM.csv`, `exports/jlcpcb/` | grouped BOM (DNP flagged); JLCPCB BOM, CPL and gerbers |
| `docs/` | schematic PDF, layout SVGs/renders, `design-review-rev0.md` |
| `case/` | shell dossier, OpenSCAD shell, generated anchors |
| `tools/` | generators and checks (see *Regenerating*); `tools/audit/` the review computations |
| `.kicad-happy.json` | kicad-happy project config and documented suppressions |
