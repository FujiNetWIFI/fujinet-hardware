# Inty-FujiCard

FujiNet for the Intellivision, on one cartridge: Yannick Erb's production design (EasyEDA project PINTY-FUJI-CARD, PCB v1.1, 2026-11-04), converted to KiCad in the structure of the other console bring-ups.
- **RP2354A:** serves the CP1610's bus (`fujinet-firmware/pico/intellivision`, board `fujicard`). AD0-15, MSYNC, BDIR, BC1 and BC2 go straight from the edge to its GPIOs.
- **ESP32-S3:** the FujiNet (`fujiversal-intv`) and the RP's USB host, on the same board.
- **Also on the board:** a microSD, an SK6805 status LED, and a USB-C with a CP2102N bridge for flashing and power.

`Original/` holds Yannick's files exactly as he sent them: the EasyEDA PCB (JSON), an Altium ASCII export, his gerbers and drills, BOM and pick-and-place. Everything else is generated from them (`tools/`).

**Status (2026-11-05): converted, every gate passing. The copper, masks, paste, drills and silkscreen equal Yannick's gerbers; his BOM and placements are carried over unchanged.**
- **Board:** 2 layers, 58.2 x 60.0 mm, 1.6 mm. Yannick's layout, unchanged. His EasyEDA files had no schematic: the schematic here is drawn from the board's netlist.
- **Firmware:** the netlist matches `fujicard.h` and `fujiversal-intv.h` on every bus and S3 pin. The mismatches are listed under *Firmware*.
- **Before ordering:** see *Known limits / review*. The paste layers open the gold fingers, and three lines were out of stock on 2026-11-05.

| Check (2026-11-05) | Result |
|---|---|
| `tools/audit/gerber_equiv.py`: our PCBWay zip against Yannick's gerber zip, rasterised at 40 px/mm and XOR-ed | F.Cu, B.Cu, F/B.Mask, F/B.Paste, outline: identical (nothing left after a 50 um opening); silkscreen graphics identical, all 42 visible texts centred within 0.05 mm of his; 160 plated and 6 unplated holes, all his |
| `tools/board_netlist.py --check`: `tools/design.py` against the board's own netlist | 76 nets, 78 parts, every unconnected pad NC; Yannick's net names kept |
| Drawing checks (`gen_sch.py`) and netlist parity (kicad-cli netlist against `design.py`, names included) | every sheet wired; 0 crossings on 4 sheets, 1 on `usb` (esptool's auto-program pair); 76 / 76 nets |
| KiCad ERC, all severities | 0 errors, 0 warnings |
| `tools/check_nets.py`: the netlist against `fujicard.h`, `pintycard.h`, `fujiversal-intv.h` (fujinet-firmware `origin/master`) | 72 checks, 0 failed; 8 NOTE lines (*Firmware*) |
| `tools/sync_board.py`: schematic -> board, names and fields only | copper hash unchanged |
| `tools/audit/check_drc.py`: KiCad DRC + schematic parity on the saved fills (kicad-cli; again through the KiCad MCP) | 0 errors, 0 unconnected, 0 parity issues; 101 warnings, all from Yannick's footprints (*Design rules*) |
| `tools/audit/check_fab.py`: the JLCPCB / PCBWay packages against his BOM and pick-and-place | BOM = his 31 lines / 70 parts with his LCSC codes and MPNs; CPL = his placements (worst 0.005 mm, every rotation); the zips |

## What the conversion changed

KiCad 10.0.8's EasyEDA importer (`pcbnew.PCB_IO_MGR.EASYEDA`) reads the JSON. `tools/convert.py` keeps what it gets right and fixes what it gets wrong. Each fix is proven against Yannick's gerbers:
1. **The GND pours' holes.** EasyEDA stores each pour's fill with its clearance holes, and the importer drops the holes. As imported, the B.Cu pour covered 31 signal tracks (230 mm2 of copper that is not on his board), and the F.Cu pour filled 129 clearances. The fills are rebuilt from the JSON.
2. **Paste and silkscreen drawn inside footprints.** The importer drops these shapes: 142 paste openings and 13 silkscreen marks (polarity bars, pin-1 dots). Their pads carry EasyEDA's "no paste of its own" value (-393.7 x 10 mil, imported as a -100 mm margin). They are restored; those 138 pads have no F.Paste of their own.
3. **Text.** The importer shows every value and reference; the JSON hides all values and 40 references, and its visibility flags are applied. KiCad anchors each text where EasyEDA's starts, so every text sat 0.2-1.4 mm off; each is moved so its strokes are centred on EasyEDA's. The font is KiCad's.
4. **3D models.** The importer offsets each EasyEDA model as if its origin were its solids' box centre and bottom. EasyEDA places them by that box, and several are not centred on their origin: the microSD socket sat 29 mm away and under the board. `tools/fetch_models.py` normalises each model (`3d/README.md`).
5. **Solid regions** (the 386 teardrops and copper shapes) become filled copper polygons with their nets, not zones, so no refill can redraw them. Two that EasyEDA drew twice are kept once.
6. **Housekeeping:**
   - KiCad's own layer names.
   - The 23 footprints go into `Inty-FujiCard.pretty`.
   - The designators KiCad cannot annotate are numbered (table below).
   - The 3D models are bundled.
   - The crystal's no-fill keep-out is 10 um smaller: EasyEDA's pour touched it.
   - UUIDs are fixed, so a rerun diffs clean.

**Never refill the zones.** The two GND pours are EasyEDA's own fills. A refill (B in pcbnew, `--refill-zones`, `--check-zones`) replaces them with KiCad's. `tools/audit/gerber_equiv.py` would then report the difference.

| Yannick's | Here | | Yannick's | Here |
|---|---|---|---|---|
| BOOT | SW1 | | GND (test pad) | TP1 |
| RESET | SW2 | | TX | TP2 |
| RP-BOOT | SW3 | | RX | TP3 |
| RP-RUN | SW4 | | SWD | TP4 |
| LED | D6 | | SWCLK | TP5 |
| USB | J1 | | Hole_gge2670 / 2700 | H1 / H2 |

The silkscreen still reads BOOT, RESET, RP-BOOT, RP-RUN, LED, USB, GND, TX, RX, SWD and SWCLK: each label is kept as board text, grouped with its part. Every other designator is his.

## Sheets

Drawn with the FujiNet-ColecoVision / O2 / Arcadia toolkit:
- **Wires only:** every connection on a sheet is a wire.
- **Rails:** rails are power symbols (`GND`, `VSYS`, `VBUS`, `VIN`, `3V3`, `1V1`).
- **Between sheets:** sheets join only through hierarchical labels, wired on the root's block diagram.

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | the block diagram: rp-core <-> fujinet (USB_DP / USB_DM, RUN_CTL, BOOTSEL_CTL), fujinet <-> usb (S3_TXD / S3_RXD, S3_EN, S3_IO0); notes |
| 2 | `cart-bus` | the 44-finger edge and the RP2354A's GPIO unit row for row; the console reset (GP20, R13, Q1), the ECS audio (GP28, R5), the TX / RX pads |
| 3 | `rp-core` | the RP2354A's core unit: its supply capacitors, core regulator (L1, R6 / C19), crystal, USB 27R pair, QSPI_SS / RP-BOOT / Q3, RUN / RP-RUN / Q4, SWD pads |
| 4 | `fujinet` | ESP32-S3-WROOM-1-N16R8, EN RC and RESET, BOOT, microSD with the YC158 pull-ups, SK6805 |
| 5 | `usb` | USB-C, ESD5Z diodes, CP2102N, esptool's auto-program pair (UMH3N) |
| 6 | `power` | the SS34 diode-OR (VSYS, VBUS -> VIN), the AP63203 buck (3V3), PWR_FLAGs, the holes |

## Edge connector

44 contacts in two rows of 22 at 2.54 mm. Yannick's footprint numbers them A1-A22 on the component face and B1-B22 behind, left to right, seen from the component face with the contacts down. Finger A(k) is INTV pin 46 - 2k, and B(k) is pin 45 - 2k: even pins in front, odd behind.

| Pin | Finger | Signal | Goes to | Pin | Finger | Signal | Goes to |
|---|---|---|---|---|---|---|---|
| 1 | B22 | GND | GND | 2 | A22 | NC | - |
| 3 | B21 | /MSYNC | GP21 | 4 | A21 | NC | - |
| 5 | B20 | D7 | GP7 | 6 | A20 | EXT_AUDIO | R5 from GP28 |
| 7 | B19 | D8 | GP8 | 8 | A19 | GND | GND |
| 9 | B18 | D6 | GP6 | 10 | A18 | GND | GND |
| 11 | B17 | D9 | GP9 | 12 | A17 | /RESET | Q1 (GP20 via R13) |
| 13 | B16 | D5 | GP5 | 14 | A16 | NC | - |
| 15 | B15 | D10 | GP10 | 16 | A15 | NC | - |
| 17 | B14 | D4 | GP4 | 18 | A14 | NC | - |
| 19 | B13 | D11 | GP11 | 20 | A13 | GND | GND |
| 21 | B12 | D3 | GP3 | 22 | A12 | GND | GND |
| 23 | B11 | D12 | GP12 | 24 | A11 | GND | GND |
| 25 | B10 | D13 | GP13 | 26 | A10 | GND | GND |
| 27 | B9 | D2 | GP2 | 28 | A9 | GND | GND |
| 29 | B8 | D14 | GP14 | 30 | A8 | NC | - |
| 31 | B7 | D1 | GP1 | 32 | A7 | PASS_A | joined to pin 42 |
| 33 | B6 | D0 | GP0 | 34 | A6 | PASS_B | joined to pin 40 |
| 35 | B5 | D15 | GP15 | 36 | A5 | PASS_C | joined to pin 38 |
| 37 | B4 | BDIR | GP22 | 38 | A4 | PASS_C | joined to pin 36 |
| 39 | B3 | BC2 | GP27 | 40 | A3 | PASS_B | joined to pin 34 |
| 41 | B2 | BC1 | GP26 | 42 | A2 | PASS_A | joined to pin 32 |
| 43 | B1 | +5V | VSYS -> D1 | 44 | A1 | GND | GND |

The pinout is the attic FujiNet-INTV-Rev0's edge, traced from the PiNTY CARD's gerbers. The firmware's bus map agrees on every finger (`tools/check_nets.py` keeps its own copy of both).

## RP2354A pin map

| GPIO | Net | Goes to |
|---|---|---|
| 0-15 | GPIO00-15 | the edge's D0-D15 (`MI_AD0_PIN` 0), straight |
| 16 / 17 | GPIO16 / 17 | test pads TP2 (silk TX) / TP3 (silk RX) |
| 18, 19, 23, 24, 25, 29 | - | not connected |
| 20 | GPIO20 | R13 -> Q1: high pulls the console's /RESET (pin 12) low (`MI_RST_PIN`) |
| 21 / 22 | GPIO21 / 22 | MSYNC / BDIR, straight |
| 26 / 27 | GPIO26 / 27 | BC1 / BC2, straight |
| 28 | PWM | R5 1k -> EXT_AUDIO (pin 6, the ECS audio; `pintycard.h` `MI_AUDIO_PIN`) |
| QSPI | QSPI_SS | the BOOTSEL strap (R12 10k up; RP-BOOT / Q3 through R11 1k); the flash is in the package, the other QSPI pins are not connected |
| USB | USB_D+ / USB_D- | 27R -> the ESP32-S3's IO20 / IO19 (the S3 is the host) |
| RUN | RUN | R14 10k up; RP-RUN (SW4); Q4 |

## ESP32-S3 pin map

`include/pinmap/fujiversal-intv.h`:

| S3 pin | Net | Goes to |
|---|---|---|
| IO19 / IO20 | USB_DM / USB_DP | the RP2354A's USB through its 27R |
| IO38 / 39 / 40 / 41 | SD_MOSI / SCK / MISO / CS | microSD (SPI); 10k pull-ups (RN1) on CS, DO, DI, DAT1, DAT2; card detect not connected |
| IO48 | LED_STRIP | 330R -> SK6805-EC20 (on 3V3) |
| TXD0 / RXD0 | S3_TXD / S3_RXD | CP2102N RXD / TXD |
| IO4 / IO5 | RUN_CTL / BOOTSEL_CTL | 1k -> Q4 / Q3: high pulls the RP's RUN / QSPI_SS low |
| EN / IO0 | S3_EN / S3_IO0 | 10k / 1 uF and RESET (SW2); BOOT (SW1), 100 nF, 10k up; the auto-program pair |

## Power

| Rail | Source | Feeds |
|---|---|---|
| `VSYS` | edge pin 43, the console's +5V | D1 (SS34) -> VIN |
| `VBUS` | USB-C | D2 (SS34) -> VIN; the CP2102N's VBUS sense (22.1k / 47.5k) |
| `VIN` | the higher of the two, less a Schottky drop | C29 100 uF, C25 10 uF; the AP63203 |
| `3V3` | AP63203, 3.3 V / 2 A buck (4.7 uH) | everything: the RP2354A (IOVDD, VREG_VIN, ADC, USB, QSPI), the ESP32-S3, the CP2102N, the microSD, the SK6805 |
| `1V1` | the RP2354A's core regulator (L1 3.3 uH) | the RP's DVDD |

Neither source can back-feed the other: a cart on USB never powers a console that is off.

## Design rules

The Board Setup minimums (`tools/rules.json`) are the lowest values Yannick's copper needs. `Inty-FujiCard.kicad_dru` holds everything else to JLCPCB's standard 1-2 layer figures (0.127 mm space, 0.45 / 0.2 mm via, 0.125 mm ring, 0.3 mm to the edge). The measured exceptions:
- **Spacing:** 6 spots at 0.107-0.121 mm, in the RP2354A's and the CP2102N's fan-out (QFNs at 0.4 / 0.5 mm pitch). His EasyEDA rule there is 0.1016 mm.
- **Vias:** 151 are 0.457 / 0.254 mm, a 0.1015 mm ring (EasyEDA's 18 / 10 mil). The other 5 are 0.62 / 0.31 mm.
- **Hole clearance:** the USB-C's own pads sit 0.171-0.213 mm from its locating pegs (the connector's footprint). One B.Cu track (GPIO09) passes 0.243 mm from GPIO08's via.
- **Edge clearance:** the two GND pours stop 0.259 mm from the outline's centre line.
- **Placement:** C9, C10, C13 and C19 are inside the RP2354A's courtyard, and R3 overlaps L1's (EasyEDA courtyards).
- **Pad 23:** the CP2102N's GND pad 23 reaches the pour by one spoke.

The 101 DRC warnings are all his footprints' (`tools/audit/check_drc.py` fails on any other):
- 47 `lib_footprint_mismatch`: EasyEDA placed each instance with its own 0.1-0.2 um rounding and fab-text angle; the library holds the first.
- 39 `silk_overlap`: polarity bars and pin-1 dots over the parts' own outlines.
- 10 `silk_edge_clearance`: the USB-C, the S3 and the microSD outlines at the board edge.
- 4 `silk_over_copper`: the USB-C outline over its shell legs.
- 1 `track_dangling`: a zero-length 3V3 dot on B.Cu, which is in his gerbers too.

## Parts

Every part is Yannick's, with his LCSC code (`Inty-FujiCard-BOM.csv` has MPN, manufacturer and LCSC for every line). Run `python3 tools/audit/sourcing.py` on order day.

**Stock (2026-11-05, `docs/sourcing.md`):** 31 lines, about USD 11.59 of parts per board. Three lines are short at JLCPCB:
- **U1 RP2354A** (C41378174): JLCPCB 0, LCSC 0.
- **U2 AP63203WU-7** (C780769): JLCPCB 0, LCSC 0.
- **RN1 YC158TJR-0710KL** (C309679): JLCPCB 1, LCSC 0.

Consign them, use JLC Global Sourcing, or order from PCBWay, which sources by MPN. **C29** (Lelon VE-101M1ATR-0505, C134722) is marked `stop_product` at LCSC, with 408 left at JLCPCB. Any substitute is Yannick's call.

## Ordering

- **JLCPCB:** `exports/jlcpcb/ORDER-JLCPCB.md`. `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv` equal his files: his footprints are LCSC's own, so no rotation table applies. The zip carries the order-number text on the back silkscreen.
- **PCBWay:** `exports/pcbway/ORDER-PCBWay.md`, turnkey by MPN (`BOM-PCBWay.csv`), `Centroid-PCBWay.csv`, `Assembly-top.pdf`.

Yannick's files give no order options. The finish, hard-gold fingers and bevel in the ORDER files are the house recommendation for a cartridge edge: confirm them with him.

## Firmware (not changed here)

`tools/check_nets.py` reports these as NOTE lines:
1. **`fujicard.h` names pins this board does not connect:**
   - `MI_LED_PIN` 25 (no RP LED here).
   - `MI_DBG_UART_TX_PIN` 24: the TX / RX pads are GP16 / GP17.
   - `FUJI_SELFTEST_TRIGGER_PIN` 23.
   
   Its comment says "No PCB pin map is committed yet": this board is one.
2. **RUN / BOOTSEL polarity.** The S3 reaches the RP's RUN and QSPI_SS through NPNs (Q4, Q3), so IO4 / IO5 must be driven **high** to assert. `fnPicoUpdater::forceBootselViaPins()` drives them low (for a direct 1k link), so that recovery path does nothing on this board. The normal path, the USB mailbox doorbell, is unaffected.
3. **ECS audio.** GP28 is wired to EXT_AUDIO as `pintycard.h` has it (`MI_AUDIO_PIN` 28). `fujicard.h` defines no audio pin, and `fujicard.cmake` has `CONFIG_ECS_AUDIO` off.

## Known limits / review

- **Paste on the gold fingers.** His F.Paste and B.Paste open all 44 fingers, and our gerbers equal his. Ask the fab to keep the fingers out of the stencil, or confirm with Yannick how his boards were built.
- **BC1 / BC2 on GP26 / GP27.** These are the RP2350's ADC pins, not 5 V tolerant (GP0-25 are). They meet the console's lines directly, as on the PiNTY CARD.
- **Fab limits.** The spacing and via-ring exceptions above are below JLCPCB's standard 2-layer figures. Check the quote's DFM report.
- **The ESP32-S3 overhangs** the board's top edge by about 6.2 mm (the antenna). The shell must allow for it.
- **Designators.** U5 is the crystal: Yannick's designator, kept.

## Bring-up checklist

1. **Rails, with no console:** USB-C only. Check 3V3 (C4 / C22) and 1V1 (C17). The SK6805 lights.
2. **First flash of the RP:** SWD on TP4 (SWDIO), TP5 (SWCLK) and TP1 (GND), with a Raspberry Pi Debug Probe. Or hold RP-BOOT while pressing RP-RUN for the USB boot ROM; its USB reaches only the S3.
3. **The S3:** flash over the USB-C. The CP2102N and the auto-program pair drive EN and IO0.
4. **In a console, no USB:** measure VIN and 3V3 under WiFi load, then CONFIG on the TV.
5. **Console off with USB on:** confirm D1 blocks: VSYS stays at 0 V.

## Regenerating

You need KiCad 10 and Python 3 with numpy, scipy and pycairo. `check_nets.py` reads fujinet-firmware from `$FUJINET_FIRMWARE` (default `~/Workspace/fujinet-firmware`) at `$FUJINET_FIRMWARE_REF` (default `origin/master`).

```sh
tools/build_all.sh                 # schematic, ERC, check_nets, sync, DRC, exports, the fab gates (keeps the board)
CONVERT=1 tools/build_all.sh       # first re-converts Original/PCB_*.json (tools/convert.py) and its netlist
python3 tools/fetch_models.py      # re-fetch the EasyEDA 3D models into 3d/ (network)
python3 tools/audit/sourcing.py    # stock at JLCPCB and LCSC -> docs/sourcing.md (network)
```

Each source file has one job:
- `tools/convert.py`: the board and footprints, from `Original/`.
- `tools/design.py`: the circuit as written out.
- `tools/sch_layout.py`: the drawing.

Edit those, never the KiCad files.

## Provenance and licence

- **The design:** Yannick Erb, PINTY-FUJI-CARD v1.1 (EasyEDA, 2026-11-04). It grows out of his PiNTY CARD (with gtortone), which is CERN-OHL-W-2.0. **His files state no licence for this board: confirm one with him before publishing it.**
- **The conversion:**
  - `tools/`; the drawing toolkit and the serializer from FujiNet-ColecoVision / O2 / Arcadia Rev0.
  - `tools/gen_sch.py`'s RP2354A core unit and S3 symbol from FujiNet-ColecoVision Rev0.
  - The edge pinout from the attic FujiNet-INTV-Rev0.
- **The pin maps:** `fujinet-firmware` `pico/intellivision` and `include/pinmap/fujiversal-intv.h`.
- **Symbols:**
  - Official KiCad libraries (CC-BY-SA 4.0 with exception).
  - Project symbols for the edge, the RP2354A in two units, the ESP32-S3 by function, Yannick's USB-C, microSD, YC158 array and SK6805-EC20, each numbered as his footprints are.
- **Footprints:** Yannick's (LCSC / EasyEDA), as on the board.
- **3D models:** `3d/README.md`.
