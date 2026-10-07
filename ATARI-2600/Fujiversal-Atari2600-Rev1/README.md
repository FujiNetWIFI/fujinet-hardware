# Fujiversal-Atari2600 Rev1

All-in-one **Atari 2600 FujiNet cartridge**, the RP2354A successor to the
RP2040 Rev0 (branch `atari2600-rev0`). It is the hardware for the 2600
bring-up in fujinet-firmware (branch `2600-experiment`, worktree
`~/Workspace/fn-2600`).

- **RP2354A** (RP2350A + 2 MB flash in one QFN-60) runs the cart firmware
  (`pico/atari-2600`, board `fujivcs`, ported to the RP2350 as listed below).
  The cartridge port goes **straight to the RP**: A0-A12 on GP2-GP14 and D0-D7
  on GP15-GP22, exactly as `include/vcs_pins.h`. RP2350 GPIO0-25 are
  "Digital IO (FT)": 5.5 V-tolerant while IOVDD is 3.3 V, and a 3.3 V high
  clears the 6507's TTL VIH (2.0 V). No '245 buffers and no direction pin:
  the firmware's per-access output enable is the only direction control.
- **ESP32-S3-WROOM-1-N16R8** runs the `fujiversal-atari2600` build of
  fujinet-firmware and is the RP's USB *host* (S3 IO19/IO20 -> 27R -> RP USB;
  the RP enumerates as CDC, VID 0xCafe). There is no UART between the chips.
- **USB-C**: power + CP2102N UART with UMH3N auto-program (flashes the S3).
- **microSD** (push-push, SPI on IO38-41, card-detect IO42), on the right edge.
- **WS2812B-2020** status LED (IO48, on +5V) and a red RP activity LED (GP25).
- **Buttons:** RESET (resets both chips: the way back to the browser),
  BOOTSEL (RP), S3 EN, S3 BOOT. The S3 can also force the RP into reset or
  BOOTSEL itself (IO4 -> RUN, IO5 -> QSPI_SS, active low through 1k).
- **Console 5 V sense** on GP27 (100k/150k, 3.0 V at 5 V): the firmware can
  tell a powered console from a USB-only cart.

4 layers, fully routed, DRC clean with schematic parity, JLCPCB fab +
assembly files in `exports/jlcpcb/`. Everything is generated from
`tools/design.py` (circuit), `tools/sch_layout.py` (schematic drawing) and
`tools/placement.py` (layout): edit those, never the KiCad files.

## Pin contract

| RP2354A | QFN-60 pin | Net | Firmware |
|---|---|---|---|
| GP2-GP14 | 4,5,7-10,12-18 | A0-A12 (CA0-CA12) | `ADDR_PIN 2`, `ADDR_BITS 13` |
| GP15-GP22 | 19, 27-29, 31-34 | D0-D7 (CD0-CD7) | `D0_PIN 15` |
| GP25 | 37 | RP_LED (680R, red LED) | `PICO_DEFAULT_LED_PIN` |
| GP27 | 41 | VSENSE (console 5 V x 0.6) | new: power sense |
| GP0 / GP1 | 2 / 3 | RP_TX / RP_RX (TP4 / TP5) | debug UART |
| GP26 | 40 | not connected | the RP2040 board's `DIR_PIN` (harmless if written) |
| GP23, 24, 28, 29 | | not connected | |
| USB DP/DM | 52 / 51 | 27R -> S3 IO20 / IO19 | CDC device |
| RUN / QSPI_SS | 26 / 60 | 10k pull-ups; 1k from S3 IO4 / IO5; RESET / BOOTSEL buttons | `PIN_RP2040_RUN` 4, `PIN_RP2040_BOOTSEL` 5 |
| SWCLK / SWDIO | 24 / 25 | TP1 / TP2 (TP3 GND) | first flash |

ESP32-S3 pins are exactly `include/pinmap/fujiversal-atari2600.h`: SD CS 41,
SCK 39, MISO 40, MOSI 38, CD 42 (10k pull-up), LED strip 48, UART0 43/44,
RUN 4, BOOTSEL 5, USB host 19/20. `tools/check_nets.py` checks all of this
against the firmware headers (290 checks).

## Edge connector

2x12 gold fingers at 2.54 mm pitch, 1.5 x 7.0 mm, starting 0.5 mm from the
edge; tab 32.4 mm with 45-degree shoulders (geometry and orientation from the
FujiPlusCart prototype gerbers, `../FujiPlusCart-Prototype`).

| Face | Fingers, left -> right (component face toward you) |
|---|---|
| **F.Cu** (components, console **rear**) | 13 D3, 14 D4, 15 D5, 16 D6, 17 D7, 18 A12, 19 A10, 20 A11, 21 A9, 22 A8, 23 +5V, 24 GND |
| **B.Cu** (label side, console **front**) | 12 GND, 11 D2, 10 D1, 9 D0, 8 A0, 7 A1, 6 A2, 5 A3, 4 A4, 3 A5, 2 A6, 1 A7 (pin 1 behind pin 24) |

The port carries no R/W, clock, chip select or reset: A12 is the only decode.

## Schematic

Root + four wired sheets, drawn left to right in signal-flow order
(`docs/Fujiversal-Atari2600-Rev1-schematic.pdf`):

1. **edge-rp2354a**: the edge connector on the left, the RP2354A beside it
   (mirrored so its GPIO column faces the edge): **A0-A12 and D0-D7 are 21
   straight wires from finger to pin**. Supplies and Raspberry Pi's core
   regulator across the top; clock, RUN/BOOTSEL, USB and SWD leave on the right.
2. **esp32s3-sd**: EN/BOOT in on the left; UART, USB, SD and LED out on the right.
3. **usb-uart**: USB-C -> ESD -> CP2102N -> UART + auto-program.
4. **power**: console 5 V (and its sense divider) and VBUS -> +5V -> buck and RP LDO.

Nets cross sheets only on global labels at the page edges; every pin is wired
or flagged no-connect. `gen_sch.py` lints each sheet (connectivity, overlaps)
and checks the written schematic's netlist (kicad-cli) against `design.py`
net by net.

## Power

- **Console 5 V** (finger 23) through an AO3401A P-FET (gate = VBUS): fully on
  without USB; with USB in, the gate is at VBUS and only the body diode is left,
  so USB never back-feeds the console. R19 (4.7k) holds the gate down against
  the SS34's reverse leakage. **USB VBUS** through an SS34. Both meet on **+5V**.
- **+3V3** (AP63203 buck, 2 A): ESP32-S3, microSD, CP2102N.
- **+3V3_RP** (AP2112K LDO, 20 us start-up, ~16-40 mA): every RP2354A supply
  pin, including the core regulator's VREG_VIN and VREG_AVDD (through 33R),
  which the datasheet asks to rise together. The pads are 5 V-tolerant only
  while IOVDD is powered; the LDO rises with the console rail, the buck's
  soft-start would not.
- **DVDD 1.1 V** from the RP's own regulator (3.3 uH AOTA, Raspberry Pi's
  minimal-design corner layout).
- **Budget (estimate):** ~60 mA idle and ~350 mA during WiFi TX on +3V3, about
  250-300 mA peak from the console's 7805. Measure on a 2600 Jr before relying
  on console-only power.

## Layout

- **Board:** 54.4 x 88 mm, 1.6 mm, Rev0's outline (same shell). Parts only
  above y 90.5 (the shell bottom, 25.5 mm above the contact edge).
- **Stack (4 layers):** F.Cu signals + GND pour / In1 GND plane / In2 +3V3
  plane with a +3V3_RP island under the RP and its decoupling and a DVDD island
  (+ lobe) under its core / B.Cu signals + GND pour. Inner planes stop 9 mm from
  the insertion edge; the finger strip is a rule area (fingers only).
- **Placement:** the RP2354A at rotation 90, so A0-A9 sit on its south side in
  the order of the B.Cu address fingers below it; the data lines (D1-D7 at its
  north-east corner) run north-about and down the west corridor to the data
  fingers, so the two buses never cross. The core-regulator corner is Raspberry
  Pi's own RP2350A minimal-design layout (MIT), grafted at the RP and turned with
  it. The ESP32-S3 sits top-left with its antenna flush with the top edge over a
  band that is copper-free on every layer; microSD on the right edge, USB-C on
  the top edge, power at the bottom right, buttons on the left edge.
- **Rules:** 0.2 mm / 0.15 mm default (0.5 mm power, 0.3 mm VBUS, 0.25 mm USB),
  0.6/0.3 mm vias (0.5/0.25 under the RP), 0.25 mm copper-to-edge, 0.125 mm
  annular, 0.12 mm clearance floor for the neck-downs at 0.4 mm pitch. JLCPCB
  multilayer minimums: 0.09 mm track/space, 0.25/0.15 mm via.
- **Shell:** `case/` (see `case/case-spec.md`), two options, both driven by
  `case/board-anchors.scad` (generated from the placement): a clamshell over
  the board's top with the tab bare (`Fujiversal-Atari2600-Shell.scad`), or a
  full-size cartridge re-modelled from norm8332's "Easy Print" 2600 shell
  (`Fujiversal-Atari2600-CartShell.scad`).

## Flashing

- **ESP32-S3:** USB-C (CP2102N, auto-program): `pio run -e fujiversal-atari2600 -t upload`.
- **RP2354A, first time:** the RP's USB goes only to the S3, so use the SWD
  pads (TP1 SWCLK, TP2 SWDIO, TP3 GND) with a Raspberry Pi Debug Probe:
  `openocd -f interface/cmsis-dap.cfg -f target/rp2350.cfg -c "adapter speed 5000; program fujivcs.elf verify reset exit"`.
- **Afterwards:** the S3 puts the RP in BOOTSEL (mailbox doorbell, or IO5 low
  across an IO4 pulse) and writes it over PICOBOOT; by hand, hold BOOTSEL and
  press RESET.

## Firmware changes this board needs (not made here)

On fujinet-firmware `2600-experiment`:

1. An RP2350 board for the cart (e.g. `boards/fujivcs2354.cmake/.h`):
   `PICO_PLATFORM rp2350`, `boards/pico2.h`-style header, 2 MB flash (stacked).
2. `vcs_pins.h` / `main.c`: drop `DIR_PIN` (GP26 is unconnected here); keep the
   output-enable drive/release; give D0-D7 more than the 2 mA drive they had
   when they only faced a '245 (they now drive the console bus).
3. Turn the bus pins' pulls off (RP2350 erratum E9), and pick an RP2350 clock
   (the 250 MHz / 1.15 V RP2040 setting does not carry over as is).
4. Use GP27 (VSENSE) to idle the bus server while the console is off.
5. Enable the 1200-baud BOOTSEL reset (`pico_usb_reset` +
   `PICO_ENABLE_USB_RESET_VIA_BAUD_RATE=1`) for the S3's PICOBOOT path.
6. ESP side: `pico_*` keys + `CONFIG_USB_PICOBOOT_HOST_ENABLED` in
   `platformio-fujiversal-atari2600.ini`, and the missing
   `data/webui/config/fujiversal-atari2600.yaml`.

`tools/check_nets.py` prints NOTE lines for 1 and 2 until they are done.

## Ordering (JLCPCB)

- **PCB:** 4 layers, 1.6 mm, ENIG, **gold fingers: yes, bevel 30 degrees**,
  upload `exports/jlcpcb/Fujiversal-Atari2600-Rev1-gerbers.zip`.
- **Assembly:** Standard PCBA (gold fingers need it), top side only:
  `BOM-JLCPCB.csv` + `CPL-JLCPCB.csv` (82 parts). The board is narrower than
  JLC's 70 mm single-board minimum, so let JLC add the edge rails (not on the
  finger edge). Three fiducials are on the board.
- **CPL:** rotations and origins are corrected per footprint against the
  EasyEDA footprint of each LCSC part (`tools/audit/jlc/jlc_rotations.json`;
  ESP32-S3 origin +3.62 mm, USB-C -1.41 mm). Check pin-1 marks in JLC's
  placement preview anyway.
- **Via-in-pad:** the RP2354A and CP2102N exposed pads carry thermal vias.
  Choose epoxy-filled and capped vias if offered at a sensible price.
- **Stock (2026-10-06):** every part in JLC stock; 17 extended parts.

## Regenerating

KiCad 10.0.6, Python 3 (numpy), Java + Freerouting 2.4.1
(`~/.local/share/freerouting/freerouting-2.4.1.jar`), the firmware tree at
`~/Workspace/fn-2600` (or `$FUJINET_FIRMWARE`). `tools/build_all.sh` runs the
schematic stage; `LAYOUT=1 tools/build_all.sh` adds the board (about 12 minutes):

```sh
python3 tools/harvest_symbols.py   # stock KiCad symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py      # 2x12 finger footprint
python3 tools/make_fp_extra.py     # SOT-23-5, fiducial
python3 tools/gen_sch.py           # design.py + sch_layout.py -> root + 4 wired sheets; netlist parity
kicad-cli sch erc --severity-all --exit-code-violations Fujiversal-Atari2600-Rev1.kicad_sch -o /dev/null
python3 tools/check_nets.py        # netlist vs the fn-2600 firmware headers
python3 tools/gen_pcb.py           # outline, placement, RP regulator graft, plane islands, fan-out, rules
bash tools/route_board.sh          # Freerouting, A* finisher, tidy, GND stitching, 3D models, silk, DRC gate
python3 tools/export.py            # BOM, JLC BOM + CPL, gerbers, schematic PDF, SVGs, renders
```

## Audit (kicad-happy)

`docs/design-review-rev1.md` is the datasheet-backed review (schematic + PCB).
`analysis/` (gitignored) holds the analyzer runs and `analysis/deep_review.json`;
`tools/audit/` holds the computations it cites (`margins.py`), the deep-review
generator, the PCB audit runner and the JLC rotation table.
`.kicad-happy.json` records the intentional findings and why.

```sh
python3 <kicad-happy>/skills/lcsc/scripts/sync_datasheets_lcsc.py Fujiversal-Atari2600-Rev1.kicad_sch
python3 <kicad-happy>/skills/kicad/scripts/analyze_schematic.py Fujiversal-Atari2600-Rev1.kicad_sch --analysis-dir analysis/
bash tools/audit/run_pcb_audit.sh  # PCB, cross, EMC, thermal, SPICE, gerbers, summary
python3 tools/audit/make_deep_review.py && python3 <kicad-happy>/skills/kicad/review/scripts/deep_review_gate.py analysis/deep_review.json --analysis-dir analysis/
```

## Status

Rev1, generated 2026-10-06. **Not built or tested on hardware.**

| Check | Result |
|---|---|
| Schematic lint + netlist parity | 73 nets match `design.py` |
| ERC (`--severity-all`) | 0 violations |
| `tools/check_nets.py` | 290 / 290 (NOTE: firmware not yet ported to the RP2350) |
| DRC (`--refill-zones --schematic-parity`) | 0 errors, 0 unconnected, 0 parity; 4 warnings (the ESP32 module's silkscreen meets the top edge it sits flush with) |
| Routing | 100 %, 342 vias (120 GND stitching) |
| kicad-happy | schematic 0 errors; SPICE 16/16 pass; DFM (JLC standard tier) 0 violations; Deep Review 19/19 verified; dispositions in the review |
| Shell | clamshell: both halves render 2-manifold in OpenSCAD; cart shell: front, rear and holder render 2-manifold, the board/part interference check is empty, outside faces match norm8332's STLs within 0.3 mm |
| LCSC / JLC | every part in stock |

## Bring-up checklist (not verifiable in CAD)

1. **Fit** in a real 2600 (heavy sixer, 4-switch, Jr, 7800): fingers seat, shell clears the slot surround.
   For the cart shell, measure an original cart's edge recess first (`edge_recess`, see `case/case-spec.md`).
2. **Console 5 V** at finger 23 under WiFi bursts, especially on a Jr.
3. **Power-up:** scope +3V3_RP against CONS_5V at console power-on (IOVDD must lead the bus).
4. **Bus timing:** address -> data at the edge against the 6507 read window
   (~500 ns budget); D0-D7 must be released before the address changes.
5. **Back-power:** USB-C only, console off: the console must stay dead.
6. **RESET** returns to the browser; **BOOTSEL + RESET** enumerates the RP (VID 0x2E8A) on the S3.
7. **VSENSE** reads high with the console on, low on USB only.
8. **microSD card-detect** polarity on IO42, then set `PIN_CARD_DETECT`.
9. **WiFi RSSI** inside the shell (antenna flush with the edge, reduced side clearance).
10. **JLC placement preview:** pin-1 marks on every IC, LED and diode.

## Provenance and license

**CERN-OHL-W-2.0.**

- RP2350 core-regulator corner (parts placement and copper): Raspberry Pi
  RP2350A minimal design (`RPI-RP2350A-MINIMAL_R4-S1`, MIT, `tools/RPI-MINIMAL-LICENSE.txt`),
  the layout the RP2350 datasheet (6.3.8) says to follow.
- Edge geometry and orientation: the FujiPlusCart prototype in this repository
  (via Rev0's `make_edge_fp.py`).
- Generator pipeline: `NES/FujiNet-NES-Rev0/tools` (schematic drawing, routing
  tools), with Rev0's 2600 outline and checks.
- Cartridge shell (`case/Fujiversal-Atari2600-CartShell.scad`): re-modelled
  from "Atari 2600 Cartridge Shell - Easy Print" by norm8332
  (https://www.thingiverse.com/thing:1790785, Creative Commons Attribution);
  changes listed in the file header and `case/case-spec.md`.
- Symbols and footprints: official KiCad libraries (CC-BY-SA 4.0 with
  exception), Raspberry Pi's RP2350A footprint, the TF-015 footprint from
  LCSC/EasyEDA; 3D models listed in `3d/README.md`.

## Files

| Path | Contents |
|---|---|
| `Fujiversal-Atari2600-Rev1.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` | KiCad 10 project: root + `edge-rp2354a`, `esp32s3-sd`, `usb-uart`, `power` |
| `Fujiversal-Atari2600.kicad_sym`, `Fujiversal-Atari2600.pretty/`, `3d/` | project libraries and models |
| `Fujiversal-Atari2600-Rev1-BOM.csv` | grouped BOM, MPN + LCSC on every line |
| `exports/jlcpcb/` | gerbers zip, `BOM-JLCPCB.csv`, `CPL-JLCPCB.csv` |
| `docs/` | schematic PDF, layout SVGs, 3D renders, `design-review-rev1.md` |
| `case/` | OpenSCAD shells (clamshell + full-size cart), generated anchors, `case-spec.md` |
| `datasheets/manifest.json` | datasheet sources (PDFs gitignored) |
| `tools/` | the generator pipeline; `tools/audit/` the review tooling |
