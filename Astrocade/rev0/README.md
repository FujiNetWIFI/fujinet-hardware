# FujiNet-Astrocade Rev0

All-in-one **Bally Astrocade FujiNet cartridge**: one board in an Astrocade
cassette shell carrying both halves of the Astrocade FujiNet stack.

- **RP2354A** (RP2350A die + 2 MB flash in the package, QFN-60) runs the
  `fujicade` cart firmware from `fujinet-firmware/pico/astrocade`, board
  **`fujicade_rp2354`**. It serves the 8K cart window and the FujiNet
  mailbox straight off the 5 V bus through its 5 V-tolerant pads, with **no
  level shifters**. The pads tolerate 5 V only while IOVDD is powered, so the
  whole RP runs from its own fast LDO (see *Power*).
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-astrocade`** build of
  fujinet-firmware. The two chips link **on the board over native USB**: the
  S3 is the USB *host* (IO19/IO20) and the RP a CDC device (VID 0xCafe).
  The S3 embeds the RP image and re-flashes it over PICOBOOT whenever it
  changes (`build_pico.py`).
- **USB-C** carries power plus a CP2102N UART with UMH3N auto-program
  (ESP32-S3-DevKitC-1 style) for flashing the S3.
- **microSD** (push-push, SPI on S3 IO38-41). Card detect on IO42 reads
  **low with a card in** (TF-015 drawing: the CD switch closes to the shell).
- **WS2812B-2020** status LED under a light pipe, on **+5V**: its datasheet
  rates VDD 3.7-5.3 V. VIH min is 2.7 V, so the S3's 3.3 V data drives it
  without a level shifter.
- **Buttons:** top-face **RESET** (SW4, resets the RP and the S3), **BOOTSEL**
  pinhole (SW1), S3 **EN/BOOT** (SW2/SW3, board-level).

This revision was audited with kicad-happy and the manufacturer datasheets,
and then redone. The schematic, board and fabrication files are all generated
from `tools/` (see *Regenerating*). The audit is
[`docs/design-review-rev0.md`](docs/design-review-rev0.md).

## Schematic

The schematic is drawn the way the later carts' (2600 Rev1, 7800, SMS, 5200) are:
- **every sheet is the board turned edge-left**: board south -> page left, north -> right, west -> top, east -> bottom;
- each part sits where it is on the board, and `tools/sch_place.py` checks the order;
- **every connection on a sheet is a wire**, flowing left to right from the console to the USB-C.

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | The board outline at 2:1 with each sheet's block over its region; the nine signals between sheets wired; notes |
| 2 | `cart-bus` | The 26-land edge **straight into the RP2354A's GPIO unit**: 22 parallel wires (/CCS, A0-A12, D0-D7), no buffers; /CCS pull-up, the VSENSE divider, activity LED, SELFTEST / DBG_TX pads |
| 3 | `rp-core` | The RP2354A's core unit: every supply pin with its capacitor, the core regulator corner, crystal, SWD, RUN / BOOTSEL / RESET, the USB pair to the S3 |
| 4 | `fujinet` | ESP32-S3, EN / BOOT, microSD, WS2812 status LED |
| 5 | `usb` | USB-C, ESD, CP2102N, esptool's auto-program pair |
| 6 | `power` | Console 5 V / USB VBUS diode-OR, 3.3 V buck, RP LDO |

Rails are power symbols (`CONS_5V`, `VBUS`, `+5V`, `+3V3`, `+3V3_RP`, `DVDD`, `GND`). Sheets join only through hierarchical labels, wired on the root. KiCad names the nets:
- `/cart-bus/CA0` for a net local to its sheet;
- `/S3_EN` for a net joined on the root;
- `GND` for a rail.

The names are frozen in `tools/nets.lock` because the routed board carries them. References are frozen in `tools/refs.lock`.

## Edge port

The cassette edge carries **A0-A12, D0-D7, one pre-decoded active-low
Enable (/CCS), +5V and 3x GND**. There is no /RD, /WR, clock or reset, and
the console only ever *reads* the cart. The RP pin map is exactly
`astrocade_cart.h`:

| RP2354A | Net | Edge (Tilton 1-26) |
|---|---|---|
| GP0-GP12 | CA0-CA12 | A0 9, A1 8, A2 7, A3 6, A4 5, A5 4, A6 3, A7 2, A8 24, A9 23, A10 20, A11 19, A12 22 |
| GP13 | CCS_N (10k pull-up to +3V3_RP) | 21 |
| GP14-GP21 | CD0-CD7 | D0 10, D1 11, D2 12, D3 14, D4 15, D5 16, D6 17, D7 18 |
| GP26 | VSENSE: edge +5V (CONS_5V) through 10k/15k (3.0 V; 6 kOhm, below RP2350-E9's 8.2 kOhm) | 25 |
| GP22 / GP27 | SELFTEST / DBG_TX test pads | - |
| GP25 | green activity LED (330R) | - |

`tools/audit/edge_orientation.py` checks the generated board: land 1 is
**east** in KiCad top view, on B.Cu. That matches Tilton's "looking at the
cart slot, pins 1 to 26 left to right" with the cart inserted label-up.

**The unbuffered bus is safe because the firmware gates it.** The core1 loop
serves a read only while `(pins & SERVE_MASK) == SERVE_WANT`: /CCS low
**and** VSENSE high (`FUJICADE_VSENSE_PIN`). VSENSE is sensed on the console
side of the OR diode. So a cart on USB power in an **unpowered** console
never drives D0-D7 into it, and the loop lets go if the console loses power
mid-cycle. The bus pads' pull-downs are disabled (`FUJICADE_BUS_NO_PULLS`,
RP2350-E9).

The S3 pins follow `include/pinmap/fujiversal-astrocade.h`:

| S3 | Function |
|---|---|
| IO38/39/40/41 | SD MOSI / SCK / MISO / CS |
| IO42 | SD card detect (10k pull-up, low = card present) |
| IO48 | WS2812 (330R) |
| IO4 / IO5 | `PIN_RP2040_RUN` / `PIN_RP2040_BOOTSEL`, 1k each to RP RUN / QSPI_SS |
| IO19 / IO20 | USB D- / D+ to the RP (27R series) |
| TXD0 / RXD0 | CP2102N |

**Why RUN/BOOTSEL are direct 1k links.** `fnPicoUpdater::forceBootselViaPins()`
drives these pins **low** to assert and leaves them as inputs when idle. An
NPN driver (as on INTV Rev0) would invert that. Both chips run at 3.3 V
(`+3V3` and `+3V3_RP`), so a series resistor is the whole interface.

## Power

| Rail | Source | Feeds |
|---|---|---|
| `CONS_5V` | edge land 25 | OR diode, VSENSE divider |
| `VBUS` | USB-C (1 uF + 100 nF, ESD) | OR diode, CP2102N VBUS sense |
| `+5V` | SS34 diode-OR of CONS_5V and VBUS | buck, RP LDO, WS2812 |
| `+3V3` | AP63203 3.3 V / 2 A buck (6.8 uH) | ESP32-S3, CP2102N, microSD |
| `+3V3_RP` | **AP2112K-3.3 LDO** | every RP2354A supply: IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN, VREG_AVDD (33R / 4.7 uF) |
| `DVDD` | RP2350 core SMPS (3.3 uH AOTA) | RP core, 1.1 V |

- **Why the RP has its own LDO.** The RP2350 datasheet says the GPIOs tolerate
  5.5 V "provided IOVDD is powered to 3.3 V" (p.1332). The first Rev0 fed IOVDD
  from the buck. The buck stays off until its UVLO, then soft-starts over
  4 ms, which left the pads unpowered while the console drove the bus. The
  AP2112K sits in dropout while the console rail rises, so +3V3_RP follows it.
  Following 1 V/ms into the rail's 21 uF needs 21 mA, under the 50 mA
  fold-back limit. A hot-plug step would take up to 1.4 ms, but hot-plugging
  isn't supported. Bring-up item 2 scopes it.
- **Supply order.** VREG_VIN and VREG_AVDD must rise together (p.402), and both
  are on the LDO.
- **Headroom.** At a 4.75 V console rail, +5V is at least 4.37 V after the
  diode. That clears the buck (3.8 V), the LDO (3.55 V) and the WS2812
  (3.7 V). There is no 5 V logic on the board. Numbers in
  `tools/audit/por_window.py`.

## Mechanics: a cassette, not a finger cart

A Videocade is a closed cassette-style box lying label-up in an **open-top
well**. The console's 26-contact **blade** (0.100" pitch, about 74 mm wide
and 3.6-3.8 mm thick, reaching about 17-18 mm in) enters a slot in the
leading face. It presses **up** against gold lands on the **PCB underside**.

The sourced dossier is `case/case-spec.md`, and the parametric shell is
`case/FujiNet-Astrocade-Shell.scad`. Its openings come from
`case/board-anchors.scad`, which is generated from the placement.

**Board:**

| | |
|---|---|
| Outline | 96 x 58 x 1.6 mm (x 52..148, y 30..88), 4x M3 NPTH for the shell posts |
| Contact lands | 26 x (1.7 x 14 mm) on **B.Cu only**, 2.54 mm pitch, 63.5 mm span, centred; land 1 is **east** in top view |
| Blade strip | B.Cu rule area over the south 16.5 mm (y >= 71.5): no tracks, vias or pour where the blade wipes |
| Land escapes | Each land's footprint carries a 0.5 mm neck under solder mask to a 0.3/0.6 mm plated hole **17.4 mm** in from the edge, beyond the blade's reach |
| Stack-up | **6 layers, 1.6 mm** (JLC06161H-2116 class): F.Cu signals + GND pour / In1.Cu **GND plane** / In2.Cu + In3.Cu signals / In4.Cu **power plane**: +3V3, a +3V3_RP island under the RP2354A region, a DVDD island under its core / B.Cu signals + GND pour (outside the blade strip). 4 layers was tried first and did not close (see *Status*) |
| Trailing edge (y=30) | USB-C, microSD slot, and the ESP32-S3 antenna overhanging about 6.4 mm (shell antenna window) |
| Top face | SW4 RESET, SW1 BOOTSEL pinhole, D3 WS2812 light pipe |
| Assembly | 3 fiducials (FID1-3, 1 mm copper / 2 mm mask), all SMD parts on the top side |

## Flashing

- **ESP32-S3:** plug in the USB-C port (CP2102N, esptool auto-program) and run
  `pio run -e fujiversal-astrocade -t upload`. The build also compiles the
  RP firmware (`pico_src = pico/astrocade/firmware`,
  `pico_board = fujicade_rp2354`) and embeds it.
- **RP2354A:** flashed by the S3 at boot, over PICOBOOT. It tries the
  cooperative mailbox BOOTSEL doorbell first, else hardware forcing (IO5
  holds QSPI_SS low across an IO4 pulse on RUN). The image is capped below
  the flash store at 0x180000 (`pico_flash_limit`).
- **Manual fallback:** hold SW1 (BOOTSEL) and press SW4 (RESET). In BOOTSEL
  the RP enumerates to the **S3**, not a PC.
- **Test pads:**
  - SWD: TP1 SWCLK, TP2 SWDIO, TP3 GND.
  - TP4 SELFTEST, TP5 DBG_TX, TP6 RUN, TP7 BOOTSEL.
  - Rails: TP8 +5V, TP9 +3V3, TP10 +3V3_RP.
  - Probe /CCS at R8 and DVDD at C15.

## Regenerating

KiCad 10, Python 3 with numpy; for `LAYOUT=1` also Java 21+ and Freerouting 2.4.1 at
`~/.local/share/freerouting/freerouting-2.4.1.jar`. `check_nets.py` reads the
firmware from `$FUJINET_FIRMWARE`. Its default is the worktree
`~/Workspace/fn-astrocade` on fujinet-firmware branch `astrocade-rp2354-board`.

`tools/build_all.sh` runs the whole chain. By default it keeps the routed board and only re-links it to the regenerated schematic. `LAYOUT=1` re-places and re-routes the board from scratch: Freerouting is deterministic, but any change to its inputs gives a different board.

| Step | Script | What it does |
|---|---|---|
| Schematic | `gen_sch.py` | `design.py` (parts, nets) + `sch_layout.py` (the drawing, through `sch_draw.py`) -> root + 5 sheets. Every sheet is connectivity-checked as drawn (one wired piece per net, no 4-way junctions, no overlaps), mirror-checked against the placement (`sch_place.py`), and the written schematic is checked against `design.py` pin for pin through kicad-cli's netlist and `tools/nets.lock` |
| | KiCad ERC | `--severity-all`, must report 0 |
| | `check_nets.py` | The netlist against the firmware headers (independent of `design.py`) |
| Board, default | `sync_pcb_nets.py`, `sync_pcb_sheets.py`, `gen_pcb.configure_project()` | The routed board gets the schematic's net names and sheet links; the copper is untouched (self-checked) |
| | `check_vias.py`, `audit/edge_orientation.py`, KiCad DRC `--schematic-parity` | Must report 0 errors |
| Board, `LAYOUT=1` | `gen_pcb.py` | Placement, the RPi regulator-corner graft, plane fan-out, zones, fiducials |
| | `finish_route.py --nets=XIN,XOUT,XOUT_Y,VBUS --lock` | Pre-routes the crystal and VBUS (the bus is left to Freerouting) |
| | `route.py` | Freerouting |
| | `drc_fix.py`, `finish_route.py` | Clean up router errors, then close whatever is still open (A* with rip-up) |
| | `tidy_tracks.py`, `stitch_gnd.py` | Tidy the tracks, add GND stitching (never in a pad) |
| | `stitch_transitions.py`, `check_vias.py` | GND return vias at USB / crystal / SWCLK layer changes; a gate that no via touches another net's pad (KiCad's DRC re-nets such vias) |
| | KiCad DRC `--schematic-parity` | Must report 0 errors |
| Outputs | `export.py` | BOM, JLC BOM/CPL, gerbers, PDF, renders |

**Audit** (`tools/audit/`):

| Script | Purpose |
|---|---|
| `por_window.py` | Power-path numbers |
| `timing_margins.py` | Z80 read budget |
| `edge_orientation.py` | Land 1 east on B.Cu |
| `make_deep_review.py` | Datasheet-cited findings, for kicad-happy's evidence gate |
| `e9_vsense.py`, `dvdd_far_pin.py`, `vbus_leakage.py` | The numbers behind design-review Part 3 findings 1-3 |
| `stock_check.py` | JLC / LCSC stock for every assembled line (network) |
| `run_pcb_audit.sh` | All kicad-happy analyzers, the deep-review gate and the fab release gate (writes `analysis/`, gitignored) |

`datasheets/manifest.json` lists the datasheet for every MPN. The PDFs are gitignored; they were copied from the sibling carts' `datasheets/`.

**The RP2350 regulator corner is Raspberry Pi's.** Pins 46-50 (VREG_AVDD,
PGND, LX, VREG_VIN, FB) sit side by side at 0.4 mm pitch next to USB_DM/DP.
The board uses Raspberry Pi's own layout for that corner, from the RP2350A
minimal design (MIT, `tools/RPI-MINIMAL-LICENSE.txt`):

- the QFN-60 footprint with its thermal vias;
- the AOTA inductor, the 0402 VREG_VIN/DVDD caps, the AVDD RC and the USB 27R pair;
- the small LX and 1V1 pours.

Its 3.3 V net is this board's `+3V3_RP`. A `.kicad_dru` rule allows the
reference's 0.12 mm clearance on DVDD / RP_LX / VREG_AVDD only.

**Why the board is written as text.** pcbnew's SWIG bindings misbehave under
Python 3.14, so boards are written as S-expressions and pcbnew is used only
for DSN/SES and zone fills.

## Status

Rev0 redo, generated 2026-10-02 from a clean `tools/build_all.sh` run. The schematic was redrawn wired on 2026-10-09, with the same netlist and the same routed board (design review Part 3). The 6-layer layout is **100 % routed** and the fabrication outputs are exported. The board has **not been built or tested** on hardware.

| Check | Result |
|---|---|
| ERC (`--severity-all`) | 0 violations |
| `gen_sch.py` | Every sheet wired and mirroring the board (tau 1.00); netlist parity 74 / 74 nets with `design.py`; `nets.lock` unchanged |
| `check_nets.py` | 182 / 182 against the firmware headers (branch `astrocade-rp2354-board`), the Tilton edge map and the power tree |
| DRC (`--refill-zones --schematic-parity`) | **0 errors, 0 unconnected, 0 parity.** 77 warnings: silkscreen cosmetics (silk over pads is clipped by the mask in the gerbers; the ESP32 / microSD / USB-C silk runs off the trailing edge where those parts overhang) and 1 copper sliver |
| `check_vias.py` | 382 vias, none touching a pad of another net |
| kicad-happy | Schematic + SPICE 16/16 pass; Deep Review 25/25 evidence-verified (Part 3 adds two datasheet deviations to decide: VSENSE vs RP2350-E9, DVDD decoupling); PCB / EMC / thermal (score 97) / gerbers dispositioned in `docs/design-review-rev0.md` |
| Firmware | `fujicade_rp2354` (fujinet-firmware `astrocade-rp2354-board`) is unchanged by the redo: same pin map, same RUN/BOOTSEL contract |
| Shell | Both halves render in OpenSCAD with the generated anchors (the existing non-manifold warning remains) |

**Layer count.** 4 layers was tried first:
- F.Cu / In1 GND / In2 power / B.Cu, with B.Cu forbidden under the console blade.
- After Freerouting, 7 links were left open around the RP2354A's 0.4 mm QFN.
- The A* finisher only traded one open net for another (7, then 12) and never converged.

The 6-layer stack closes completely.

**Fab (JLCPCB):**
- **Board:** 6-layer, 1.6 mm, ENIG (the contact lands want gold; hard gold optional), no edge bevel.
- **Process:** epoxy-filled and capped vias, which JLC includes on 6-layer boards; the QFN exposed-pad thermal vias are via-in-pad.
- **Limits used:**
  - track: 0.15 mm minimum
  - clearance: 0.15 mm, and 0.12 mm only in the Raspberry Pi regulator corner
  - drill: 0.25 mm minimum
  - vias: 0.45 / 0.25 mm (0.1 mm ring), on the USB-C pad ties and a few router vias. That is within JLC's multilayer minimum of 0.25 / 0.15 mm.
- **Upload files:** `exports/jlcpcb/`: `FujiNet-Astrocade-Rev0-gerbers.zip`, `BOM-JLCPCB.csv`, `CPL-JLCPCB.csv`. 82 placed parts, every one with an LCSC code, all in JLC stock on 2026-10-02. Lands, test pads, mounting holes and fiducials are not assembled.

## Bring-up checklist (not verifiable in CAD)

1. **Caliper pass** on a real Videocade and console: every VERIFY item in
   `case/case-spec.md`. That includes the blade reach against the escape
   holes 17.4 mm in; they need at least about 1 mm margin past the blade tip.
2. **Power-up:** scope +3V3_RP, CONS_5V and CA0 at a console cold start.
   +3V3_RP must follow the console rail as it rises (AP2112K in dropout).
3. **VSENSE gate:** the cart must stay silent on USB power with the console
   off, including while the console is being switched off, and serve with it
   on. Log the RP2354A stepping (`rp2350_chip_version()`): erratum E9 is why
   the divider is 10k/15k (design review Part 3, finding 1).
4. **Read timing:** /CCS to D0-D7 valid against the Z80 read cycle, about
   590 ns available for an M1 fetch (`timing_margins.py`). The console's
   decode delay is assumed, not published.
5. **Console 5 V headroom** under WiFi bursts (about 400 mA peak on +3V3).
6. **Hardware BOOTSEL forcing** (IO5 low across an IO4 pulse) before trusting
   the PICOBOOT reflash.
7. **JLC CPL rotations:** check the placement preview, especially the QFN-60,
   QFN-28, SOT-23(-5/-6), SOT-363, USB-C and SMA diodes. The table is in
   `tools/export.py`.
8. **WiFi RSSI** in the shell. The antenna overhangs the trailing edge, and
   the microSD shell is about 2 mm from it.
9. **TL3342 RESET actuator** height against the roof (printed plunger, see
   `case/case-spec.md`).
10. **DVDD under load:** scope DVDD (at C15) with WiFi and the bus busy. None
    of the DVDD pins has a capacitor close to it; the datasheet wants 4.7 uF at
    pin 23 (design review Part 3, finding 2, a Rev1 change).

**Rev1 / ordering notes** (design review Part 3):
- 4.7 uF beside RP2354A DVDD pin 23 and 100 nF beside pins 6 and 39 (finding 2);
- a 4.7k VBUS pull-down against SS34 reverse leakage faking a CP2102N USB
  attach (finding 3);
- a red KT-0603R + 680R activity LED: the green KT-0603G can be dim at 330R
  (finding 4);
- the AOTA-B201610S3R3 core inductor: 291 left at JLC on 2026-10-09; order soon
  or name a pin-compatible 2016 3.3 uH alternate (finding 5).

## Provenance and license

**CERN-OHL-W-2.0.**

- **Circuit blocks:** adapted from `FujiNet-INTV-Rev0` in this repository
  (itself an adaptation of the PiNTY CARD, CERN-OHL-W-2.0) and the
  ESP32-S3-DevKitC-1 v1.1 reference design.
- **Edge pinout:** Jay Tilton (ballyalley.com
  `bally_technical_info_(cartridge_port).htm`), cross-checked against MCM
  Design's modified cassette cartridge drawing.
- **Blade and physical data:** sakman55's Astrocade cartreader adapter
  (github.com/sanni/cartreader discussion #354).
- **RP2350 regulator corner:** Raspberry Pi RP2350A minimal design
  (`RPI-RP2350A-MINIMAL_R4-S1`, MIT, Copyright Raspberry Pi Ltd; license in
  `tools/RPI-MINIMAL-LICENSE.txt`).
- **Symbols and footprints:** official KiCad libraries (CC-BY-SA 4.0 with
  exception). The TF-015 footprint is from LCSC/EasyEDA C113206 via
  easyeda2kicad. The land footprint is original.

## Files

| Path | Contents |
|---|---|
| `FujiNet-Astrocade-Rev0.kicad_pro/.kicad_sch/.kicad_pcb` | KiCad 10 project: root plus `cart-bus`, `rp-core`, `fujinet`, `usb`, `power` sheets. It uses only the project libraries `FujiNet-Astrocade.kicad_sym`, `FujiNet-Astrocade.pretty/` and `3d/` |
| `FujiNet-Astrocade-Rev0-BOM.csv` | Grouped BOM, with an MPN and LCSC code on every line |
| `exports/jlcpcb/` | `BOM-JLCPCB.csv`, `CPL-JLCPCB.csv`, `FujiNet-Astrocade-Rev0-gerbers.zip` |
| `docs/` | Schematic PDF, design review, layout SVGs, 3D renders |
| `tools/` | Generators and checks (see *Regenerating*) |
| `case/` | Dimension dossier, parametric shell, generated anchors |
