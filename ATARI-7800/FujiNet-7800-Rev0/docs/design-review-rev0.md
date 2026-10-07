# FujiNet-7800 Rev0 Design Review

**Project:** FujiNet-7800-Rev0 (KiCad 10.0.6, root + 7 hierarchical sheets, generated from `tools/design.py`)
**Date:** 2026-10-07
**Baseline:** the schematic-only Rev0 on branch `a7800-rev0` (`803e9e2`, `9f60722`), audited and then redrawn. The changes below are **applied** in `tools/design.py` and the redrawn schematic; references are renumbered from the cartridge slot outward (keys in parentheses).
**Firmware contract:** fujinet-firmware `add-atari7800` `03b925719` (`pico/atari-7800`: `a78_cart.h`, `a78map.h`); S3 pin map fn-7800-board `a4d40118d` (`fujiversal-atari7800.h`).
**Analyzers:** kicad-happy 2.2.1:
- `analyze_schematic`, `simulate_subcircuits` (ngspice: 19 / 19 pass), `summarize_findings`;
- the Deep Review pass: `analysis/deep_review.json`, 17 findings, evidence gate 17 / 17 verified, 0 quarantined;
- LCSC stock by code.

Also run: KiCad ERC (`--severity-all`: 0 errors, 0 warnings) and the project's own checks:
- `tools/check_nets.py` 383 / 383;
- `tools/check_glue.py` 4096 / 4096;
- `tools/audit/edge_orientation.py`;
- `tools/audit/{margins,timing_margins,spice_checks}.py`.

# Part 1 — schematic audit

## Scope

An all-in-one Atari 7800 cartridge:
- **RP2354B** (QFN-80): sits on the console's 5 V bus through its 5 V-tolerant pads. It serves the boot block, the mailbox and POKEY, and drives the SRAM's page lines from a PIO slot table indexed by A13-A15.
- **AS6C4008-55** (512K, TSOP-I) on the 5 V rail.
- **Four 74HCT packages** ('14, '00, '20, '20): decode CARTSEL and make SRAM /OE, /WE and A8.
- **2N7002** on /IRQ, and a **PWM RC** into the edge's EXT AUDIO pin.
- **The FujiNet half** is NES / SMS Rev0's circuit: ESP32-S3-WROOM-1-N16R8, CP2102N + UMH3N auto-program, USB-C, microSD, WS2812, AO3401A / SS34 power OR, AP63203 buck, AP2112K LDO.

## Verification basis

| Item | Basis |
|---|---|
| Datasheets | `datasheets/` has 50+ PDFs; each new file was opened and checked to be the named part.<br>• Shared parts are copied from SMS Rev0, whose audit replaced two mis-fetched files.<br>• New: TI CD74HCT20 (SCHS417, English; LCSC served the Chinese edition), 0603WAF1501T5E, 0603B103K500NT, XKB TS-1187A, Worldsemi WS2812C-2020-V1, SK6805-EC20 (rejected alternate).<br>• Console references: the Atari 7800 schematics C025231-001 Rev A (NTSC) and C070354 (PAL), the GCC1702B MARIA specification, the 7800 Software Guide, POKEY cart schematics C026461 / C301105, the standard cart C024926, and the Synertek SY6500 sheet (the 2 MHz table stands in for SALLY, which has no datasheet). |
| Firmware contract | Every one of the 48 RP GPIOs and all four glue equations match `a78_cart.h` / `a78map.h`. Both checks run against those headers: `check_nets.py` and `check_glue.py` (`a78_cart.h` compiled on the host; 2^22 address sweep, then the 4096 input combinations). |
| Edge connector | `tools/audit/edge_orientation.py` checks the footprint against Otaku-flash (KiCad), tdididit a78-flashcartplus (Eagle), the a78-devcart gerbers, karri's measurements, Wierer's photos of an Atari C024926 board, and this repository's working FujiPlusCart prototype gerbers (faces and power fingers). |
| Computations | `tools/audit/margins.py`, `timing_margins.py` (static timing over the `design.py` gate network, worst and typical), `spice_checks.py` (ngspice decks). |

## Findings

| # | Severity | Finding | Evidence | Resolution |
|---|---|---|---|---|
| 1 | **CRITICAL** | **The edge footprint was wrong.** The 7800 edge has 18 positions at 2.54 mm; positions 3 and 16 are slots for the console connector's two plastic keys. The schematic-only footprint had 16 contiguous positions, so pins 1, 2, 15, 16 (and 32, 31, 18, 17 behind them) sat one pitch inward, on the key positions. It had no slots and a 42.6 mm tab (sources: 45.85-47.6). | `edge_orientation.py`, sources [1]-[6] in its header | **Fixed.** `tools/edge_geom.py`: 47.0 mm tab, slots centred on +-16.51 mm, 2.4 x 10 mm (0.59 mm to the neighbouring fingers), fingers 1.5 x 7.0 mm from 0.5 mm. Faces verified: pins 1-16 on F.Cu (component side, facing the console's rear). `check_nets.py` asserts the 5.08 mm steps. |
| 2 | WARNING | **RP2350-E9** (stepping A2): an input-enabled pad in the undefined region floats to about 2.2 V, above the 74HCT VIH of 2.0 V, and the internal pull-down cannot pull it down. ROM_EN high before the PIO runs would let the SRAM answer during the BIOS's check. | RP2350 DS p.1367-1368: "8.2 kOhm or less" | **Applied:** R17 / R18 / R19 4.7k on ROM_EN / RAM_EN / A8MASK (0.7 mA each while high). `check_nets.py` asserts them. |
| 3 | WARNING | **/HALT is MARIA's weak NMOS output** ("One MOS load", 30 ns into 25 pF). The cart's ~17 pF (RP pin, the trace to its east side, a bring-up pad) slows J1-2's rise to ~40 ns, and a 1k series resistor makes it worse (49 ns). | MARIA p.8; ngspice | **Applied:** R1 **10k** at the finger. J1-2 rises in 23.5 ns; the RP sees the edge ~80 ns later. That is fine: the firmware only observes /HALT. |
| 4 | WARNING | **Console 5 V budget.** The cart peaks at ~474 mA (S3 TX 355 mA through the buck) on top of the console's own ~0.35-0.5 A, from a 9 V 1 A adapter through the 7805 (no fuse). That is ~0.8-1.0 A at peaks and ~0.53-0.68 A average. An official POKEY cart draws <= ~0.2 A. | ESP32-S3 DS p.28; C025231; `margins.py` | **Applied:** C38 10 uF at the finger, as SMS Rev0. README: power the cart from USB-C for WiFi-heavy use; that takes the cart entirely off the console. Firmware option: cap S3 TX power. Bench: measure the rail. |
| 5 | WARNING | **Sourcing** (JLCPCB 2026-10-07):<br>• TL3342F160QG had 5 in stock -> **TS-1187A-B-A-B** (basic, 1.68M; footprint drawn from XKB's drawing, matches EasyEDA to 0.025 mm).<br>• WS2812B-2020-V6 had 5 -> **WS2812C-2020-V1** (377k; same pins, VDD 3.7-5.3 V, VIH 2.7 V; land identical).<br>• AS6C4008-55TIN: 0 at JLCPCB and LCSC. | WS2812C p.3; `measure_rotations.py` | **Applied** in `design.py`. Order: consign the AS6C4008 at JLCPCB, or use PCBWay turnkey (`exports/pcbway`). |
| 6 | WARNING | **/WE hold.** /WE rises one CD74HCT20 delay after PHI2 falls: 35 ns max at 4.5 V / 50 pF / 85 C. The 6502 guarantees 30 ns of address and data hold (SY6502A 2 MHz proxy). Margin is **-5 ns** at that corner, +2 ns at 25 C max, and **+19 ns** typical (+49 against the typical 60 ns hold). tWR = tDH = 0 on the AS6C4008. | CD74HCT20 p.5; AS6C4008 p.4; `timing_margins.py` | No change for Rev0. The real load is ~15 pF at 5 V, and 7800 RAM carts gate /WE the same way through LS gates. **Bring-up:** scope PHI2, A0 and SRAM /WE on a RAM write. Rev1 option: a single-gate AHCT NAND for the last /WE stage. |
| 7 | WARNING | **MARIA display-list reads after an A8MASK change.** A display-list read from cart SRAM immediately after a slot change that toggles A8MASK (mram board only) has data at 225 ns worst case, against MARIA's ~184 ns window. That is **-41 ns** worst, +23 ns typical. Same slot: +64 ns. A slot change without the toggle: +39 ns. HSC A13 path: -16 / +74. Graphics windows (285 ns) are met in every case (>= +60). | MARIA p.14 ("display lists ... must be in fast (RAM) memory"), p.27-28; `timing_margins.py` | No change: the glue is the firmware's equation, and display lists normally live in console RAM. **Bring-up:** run an mram title. Rev1 option: the PIO drives A8MASK_N, saving a gate. |
| 8 | WARNING | **Power-on race.** The PAL BIOS reads the cart ~22-62 ms after +5V (no self-test; reset RC R48 470k / C54 0.1 uF); NTSC reads it at ~0.27-0.31 s. The RP must already be serving the boot block. Bootrom, XOSC and copy_to_ram of the 69 KB image take tens of ms (**measure**). On an open bus the PAL BIOS falls back to its built-in Asteroids or 2600 mode, and the NTSC BIOS to 2600 mode, locked until a power cycle. No hardware hold-off exists: no reset on the edge, and /HALT is enabled only after the BIOS's second INPTCTRL write. | C025231; BIOS disassembly; `margins.py` | Firmware: a minimal RAM-resident first stage. Users: plug USB-C power in before switching the console on (the RP is then already running; PWR_OK gates the bus). README bring-up item. |
| 9 | WARNING (firmware) | **The console gates A15, A14 and A12 at the edge** while its BIOS is mapped (U4 74LS08 with EXT). The cart never sees the PAL BIOS at $C000-$EFFF, so the firmware's PAL detection (`a78_cart.c`, reads at $C000-$EFFF in boot mode) cannot fire on hardware, and MAME does not model the gating. The same gating is why a 7800 cart never fights the BIOS ROM: CARTSEL is 0 throughout. | C025231 (J1-8/16/17 = U4 outputs); Software Guide | **No board change.** fujinet-firmware: detect PAL by PHI2 frequency (1.773 vs 1.790 MHz on the PWM edge counter); add the gating to `emu/fujinet.cpp`. |
| 10 | INFO | **R/W during MARIA DMA:** SALLY releases it; MARIA's 3-6k pad pull-up (plus R60 4.7k on NTSC) holds it high. /WE cannot fire during DMA, and /OE needs no PHI2 term. No HALT term is needed in /WE. | MARIA p.7 | None. |
| 11 | INFO | **6502 reads of the cart SRAM:** +134 ns worst case. Read-to-write turnaround frees the bus 99 ns before the 6502 drives data. | `timing_margins.py` | None. |
| 12 | INFO | **/IRQ:** the 2N7002 pulls the console's R32 2.2k to 0.08-0.17 V. The 10k gate pull-down holds it released from power-on. | 2N7002 p.2; ngspice | None. |
| 13 | INFO | **Cart audio** into EXT AUDIO (console C10 0.1 uF + R5 6.8k into its audio sum) is within +-0.7 dB of a real POKEY cart (1k pull-up, 12k series) up to 5 kHz. The 10k level, marked provisional in the schematic-only Rev0, is confirmed. Pin 18 floats in DC between the two DC blocks, which is harmless. | ngspice; C026461 / C301105 | None. |
| 14 | INFO | **PWR_OK** is guaranteed high above 2.3 V of console supply and low below 0.6 V. +1.79 V over VT+max at 4.5 V. | SN74HCT14 p.5; ngspice | None. |
| 15 | INFO | **P-FET gate with R28 4.7k:** VGS is -2.80 V even at 500 uA of SS34 leakage; it recovers 1.8 ms after a USB unplug. | SS34 / AO3401A p.2; ngspice | None (the 9f60722 fix). |
| 16 | INFO | **Levels:** RP VOH 2.62 V min into 74HCT +0.62 V, into the SRAM's SA lines +0.22 V (+0.85 V into CMOS). Console NMOS VOH 2.4 V into the FT pads +0.40 V. The FT pads see 5 V only while +3V3_RP is up (the LDO on +5V). | RP2350 p.1337; AS6C4008 p.4 | None. |
| 17 | INFO | **Console decode:** nothing in the console answers $1000-$17FF or $3000-$3FFF in 7800 mode, so the HSC ranges in CARTSEL are free. In 2600 mode, TIA / RIOT decode on A12 = 0 alone; the firmware must stay off the bus there. | MARIA p.12 memory map | Firmware note. |

## design.py changes (applied 2026-10-07)

| Change | Parts |
|---|---|
| Edge geometry | `tools/edge_geom.py`, `make_edge_fp.py`; board outline slots in `gen_pcb.py` |
| E9 pull-downs | R17 / R18 / R19 4.7k (`R_PDROM`, `R_PDRAM`, `R_PDA8M`), on the glue sheet |
| /HALT isolation | R1 10k (`R_HALT`) at J1-2. GPIO26's net is now `HALT_RP`. |
| Console 5 V bulk | C38 10 uF (`C_CONS`) |
| Bring-up pads | 18 pads in one block above the glue row, 68-71 mm above the edge: PHI2, R/W, /HALT, EAUDIO, CONS_5V, GND, CSEL, /OE, /WE, SA8, PWR_OK, +5V, +3V3, +3V3_RP, SWCLK, SWDIO, GND, RUN |
| Sourcing | TS-1187A-B-A-B buttons (new footprint `SW_SPST_TS-1187A`); WS2812C-2020-V1; manufacturer fields for PCBWay |

## Analyzer findings and false positives

| Rule | Count | Disposition |
|---|---|---|
| VM-001 5 V / 3.3 V crossing | 27 | False positive. These are console 5 V outputs into the RP's FT pads (A0-A15, R/W, PHI2) and the RP's 3.3 V outputs into HCT / SRAM inputs (SA13-18, ROM_EN, RAM_EN, A8MASK); finding 16 covers both. D0-D7 reach the RP through 100R, so the analyzer does not list them. |
| RS-001 PWR_OK, PWR_OK_N, VBUS_SNS | 3 | Logic outputs and a divider node, not rails. |
| PU-001 CP2102N CHREN | 1 | Charger-detect output, left open as in the DevKitC-1. |
| EP-AUD J1, J2, J3; J4 partial | 4 | J1 is the console bus, J2 the DNP debug header, J3 the microSD inside the shell; J4's CC lines carry the 5.1k Rd only. |
| CG-AUD J1 14:1 | 1 | Console-defined pinout. |
| LB-001 | 19 | Hierarchical labels, one per sheet on each cross-sheet net (as SMS Rev0). |
| VD-004 R25 / R28 | 2 | 0603 is the board's passive size. |
| PS-001, CERT-001, WL-001, LC-007 | 4 | Informational: no PG pin on the AP63203; pre-certified module; lifecycle not queried. |

## Not performed / limits

- **SALLY timing:** SALLY has no datasheet. The Synertek SY6500 2 MHz table stands in for it (image-only PDF; read on p.6).
- **MARIA's DMA window from address to data** (~184 ns) is inferred from its 165 ns CS access time and the address timing (GCC1702B p.27-28).
- **Console power draw:** the console's own draw is an estimate; no measured figure exists.
- **RP boot time:** the RP's cold-boot time to a serving PIO is unmeasured; it is the deciding number for finding 8.
- **Console schematic scans:** the C025231 / C070354 schematics are scans. Findings 9-10 cite the drawing by designator and carry a computation instead of a text quote.
- **Lifecycle:** no lifecycle audit (no distributor keys). Stock was queried per LCSC code instead (finding 5).

## Verdict (schematic)

The edge footprint (finding 1) was the one board-killer, and it is fixed, with an automated check against six sources. Three real circuit issues are fixed with one resistor or cap each: E9, /HALT loading and the 5 V bulk. Two parts were nearly out of stock and are replaced. Two timing corners (/WE hold, mram display lists) are negative only at the datasheet's 85 C / 50 pF corner; they become bring-up measurements, not changes. The power-on race and PAL detection are firmware items. With the changes applied: ERC 0, `check_nets.py` 383 / 383, `check_glue.py` 4096 / 4096, deep-review gate 17 / 17.

Re-run: `tools/audit/run_sch_audit.sh`.

# Part 2 — layout

**Board:** `FujiNet-7800-Rev0.kicad_pcb`, generated by `tools/gen_pcb.py` (placement `tools/placement.py`) and routed by `tools/route_board.sh`.
**Analyzers (layout run):** kicad-happy 2.2.1:
- `analyze_pcb --full --proximity`, `cross_analysis`, `analyze_emc`, `analyze_thermal`;
- `simulate_subcircuits`, `analyze_gerbers` on the exported zip;
- `summarize_findings`.

Also run: KiCad DRC (`--severity-all --refill-zones --schematic-parity`), `tools/check_vias.py`, and the new `tools/audit/check_gerbers.py` on both fab zips.

## Edge connector (from the fab files)

Part 1 fixed the footprint; this checks what the fab receives. `tools/audit/check_gerbers.py` reads both zips and asserts:
- **Same files:** the JLCPCB and PCBWay zips are byte-identical.
- **Edge.Cuts:** the 47.0 mm tab and the 72.4 mm body. Each key-slot wall sits at x = 100 +- 16.51 +- 1.2 and runs from 10 mm in to the edge.
- **Fingers:** 16 flashes of the 1.5 x 7.0 mm finger aperture per copper face, each at its pin's x, 0.5-7.5 mm in. Pins 1-16 are on F.Cu, 32-17 on B.Cu.
- **Between the fingers:** no outer copper in the finger field except within each finger's own width.
- **Mask:** every finger lies inside a mask opening.
- **Tab:** no inner-layer copper, drill hit or paste below the body's lower edge (y 133.5). No silkscreen ink in the fingers' mask window: the pin numbers 1 / 16 / 17 / 32 and J1 sit on mask 0.7 mm above it.

It found one thing on the way, a parser lesson rather than a board fault. KiCad's `--subtract-soldermask` writes the finger window into the silkscreen gerbers as a clear-polarity (`%LPC%`) region, which a polarity-blind reader takes for ink over the fingers.

## Stack-up, rules, placement

| Item | Value |
|---|---|
| Outline | 72.4 x 98.5 mm body (x 63.8-136.2, y 35-133.5) on the 47.0 x 16.5 mm tab with two 2.4 x 10 mm key slots: 72.4 x 115 mm overall, 1.6 mm. 2 mm chamfers on the top corners, 1 mm at the shoulders and the tab's insertion corners. 4 x M3 holes; 3 fiducials. |
| Layers | F.Cu: parts, pins 1-16, signals + GND pour. In1: GND, solid under the body. In2 / In3: signals. In4: +3V3 north of y 84, a +5V island south of it and up the east edge, a +3V3_RP island (RP +-14 mm) and the DVDD island under the RP core. B.Cu: pins 17-32, signals + GND pour, no parts. |
| Tab | Fingers only. Each finger has a locked stub into the body; no tracks, vias or pour on F/B in the finger rows, and no inner copper anywhere in the tab, so the bevel never exposes a plane. |
| Rules | Default 0.2 mm track / 0.15 mm clearance; PWR (+5V, CONS_5V, BUCK_SW, +3V3) 0.5 mm with 0.8 / 0.4 vias; VBUS 0.3 mm; USB 0.25 mm. A 0.12 mm clearance floor (`.kicad_dru`) for the last links at the RP's 0.4 mm-pitch pins (JLCPCB 6-layer minimum 0.09). Fingers 0.5 mm from the edge and 0.59 mm from the slots (`finger_edge` rule 0.4). GND solid under the QFNs, the SRAM and the regulators. |
| Parts | 128 parts, 135 footprints with the holes and fiducials, all on F.Cu. 108 are placed by the assembler; J1, H1-H4, 3 fiducials, 18 test pads and the DNP J2 are not. `gen_pcb.check_parts_inside()` checks the outline polygon, the hole rings and courtyard overlaps. |
| Placement | **Lower body:** the RP2354B at (108, 112) over the address fingers, with the NES / SMS ring. **West:** the SRAM upright at (76, 112), its DQ / A0-A3 end toward the data fingers. **Between them:** the D0-D7 100R packs, now with their RP side toward the RP (below). **Along the tab:** the console-5V P-FET by finger 13, the audio RC by finger 18, the /IRQ FET and the /HALT 10k by fingers 31 / 2. **Middle band:** the four 74HCT packages and the E9 pull-downs. **Above them:** the bring-up / SWD pad block. **Upper body:** the ESP32-S3 top-left (antenna flush with the top edge), microSD and USB-C on the top edge, the buttons down the west edge. Ratsnest 4065 mm with 948 crossings (`tools/plot_placement.py`). The SMS-like alternative, with the SRAM east of the RP, gave 4145 mm and 1103, and was dropped. |

## Routing

1. The RP's core-regulator corner and the crystal are routed first on the empty board by the A* finisher, and locked (6 nets).
2. Freerouting 2.4.1 runs 12 passes with its hybrid strategy. It leaves 40 connections, most of them closed by the planes; KiCad then counts 5 open links.
3. `drc_fix` and the A* finisher close those 5: /RW, +5V, /edge/HALT_N, QSPI_SS and /edge/IRQ_N.
4. Then `tidy_tracks`; GND stitching (436 candidates on a 4 mm grid, an edge guard row and return vias beside the USB vias; DRC kept 249); `check_vias`; 3D models and silkscreen; the DRC gate.

**RN packs (the lesson of this board).** The first three routes (A with 10 passes; A with 16; A with Freerouting's hybrid strategy) each left exactly one link open: RP_D5 between RN2 and U1. The packs were placed with their RP side (pins 1-4) facing west, away from the RP. RP_D4-D7 therefore had to wrap round RN2 into the 1.7 mm channel between RN1's D side and RN2's RP side, which RN1's D0-D3 also need. The finisher's transactional rip-up could not close it: RP_D5 alone routes, but then six other nets cannot come back.
- **The fix is placement:** both packs turn 180 degrees, so their RP side faces the RP's south-west corner and their D side the SRAM and the fingers. That gives 948 ratsnest crossings instead of 974, and 4065 mm instead of 4088.
- **Results:** two more routes. With the packs at 86.5 / 90.0 and 10 passes, RP_D6 stayed open. With RN1 1 mm further west (85.5) and 12 hybrid passes, everything closed; that is the committed board.
- **Reproducibility:** `placement.py` now holds that placement (a fresh `gen_pcb.py` gives identical footprint positions), and `route_board.sh` defaults to 12 hybrid passes.

| Route | Placement | Freerouting | Left after the finisher |
|---|---|---|---|
| v1 | RN packs at 0 deg | 10 passes | RP_D5 |
| v2 | RN packs at 0 deg | 16 passes | RP_D5 |
| v3 | RN packs at 0 deg | 10 passes, hybrid | RP_D5 |
| v1 + `--force=RP_D5` | | | 4 links (the ripped nets could not all come back) |
| v4 | 180 deg, RN1 at 86.5 | 10 passes | RP_D6 |
| **v5** | **180 deg, RN1 at 85.5** | **12 passes, hybrid** | **none** |

A false gate failure was also fixed: `check_vias.py` tested every pad as its bounding box, so a via 0.21 mm clear of a round 1.5 mm test pad (TP2) was reported as touching it. Circular pads are now tested as circles.

| Result | Value |
|---|---|
| DRC (all severities, zones refilled, schematic parity) | 0 violations, 0 unconnected, 0 parity issues |
| `check_vias.py` | 686 vias against the SMD pads of other nets, 0 failures |
| Nets | 117, all routed (analyzer `routing_complete`) |
| Copper | 1682 segments, 5074 mm of track (F.Cu 1320, In2 2207, In3 1086, B.Cu 462), 39 zones |
| Vias | 686: 362 GND (249 of them stitching, edge guard or USB return), the rest signal and plane fan-out |
| Exports | `exports/jlcpcb/`: gerbers + drill zip, BOM, CPL; `exports/pcbway/`: the same zip, MPN BOM, centroid, assembly drawing. 108 refs in every BOM and placement file; `check_gerbers.py` 0 failures |

## Analyzer findings (layout run) and triage

Run: `analysis/2026-10-07_1445` (213 findings in 63 groups; the `dr:` rows are Part 1's deep review, carried in the same run). EMC risk score 61.0; thermal score 97; cross-analysis 0.

| Rule | Count | Disposition |
|---|---|---|
| VM-001 5 V / 3.3 V crossing | 27 (schematic) | As Part 1, finding 16: the FT pads and HCT inputs. The schematic analyzer ignores the suppression. |
| KO-001 H1-H4, J1 inside keep-outs | 6 | Deliberate rule areas. The screw keep-outs exist for the holes. The tab keep-outs (`tab_fingers_only_F`, `tab_no_pour_F`, and their B / inner twins) allow pads, i.e. the fingers. |
| DC-002 no decoupling near U9 | 1 | The UMH3N is a pair of pre-biased transistors with no supply pin. |
| PM-002 J3 0.2 mm from the edge | 1 (+ J1, J4, U7 info; FID1 warning) | By design: the microSD mouth faces the shell's top-wall slot, as do the USB-C and the S3 antenna. The outline is milled, not V-scored. FID1 / FID2 sit 2 mm in from the long edges; with edge rails, JLCPCB places its own fiducials on them. |
| RP-001 layer change without a GND via within 1 mm | 1 high (/USB_DP) + 20 warning + 1 info | /USB_DP has two such vias. (93.6, 110.7) changes F.Cu <-> In2, and both layers take their return from In1 GND. (67.7, 60.2), beside the S3's pad row, changes F.Cu <-> In3, so the reference moves from In1 GND to the In4 +3V3 plane: it returns through the S3's decoupling, ~2.4 mm away. The new second-ring pass in `stitch_gnd.py` offered 8-14 legal spots at 0.75 / 0.85 mm around these and the other USB vias, and DRC rejected every one against the neighbouring tracks. The RP-side vias lie in the DVDD-island exclusion, as on SMS. This is acceptable for 12 Mb/s full-speed USB; /USB_DP has the lowest per-net EMC score, 88. The 20 warnings are console-bus and control nets at 1.79 MHz or slower through the RP fan-out. |
| GP-001 partial reference-plane gap | 7 | Accepted. /D4 84 %, /D1 87 %, /D2 89 % and /D5 94 % are data-finger stubs: about 5 mm of each crosses the tab, which has no inner copper. /IRQ_GATE 92 %, /A2 93 % and /A8MASK_N 88 % cross In4 island boundaries on In3. All are 1.79 MHz bus or static nets. |
| CC-002 narrow signal 0.15 mm | 4 | `finish_route --neck` last links into fine-pitch pins; logic currents. |
| CK-001 crystal on an outer layer | 3 | The 12 MHz crystal is pre-routed on F.Cu over In1 GND, millimetres from the RP: the NES / SMS layout. |
| CK-003 SD_SCK near J3 | 1 | It is J3's own clock. |
| RS-001 PWR_OK, PWR_OK_N, VBUS_SNS | 3 | Logic nets, as Part 1. |
| BE-002 ground pour on 65 % of the perimeter | 1 | The missing part is the tab (fingers, no pour) and the antenna keep-out on the top edge. By design. |
| IO-001 / IO-002 J1 filtering, ground pins | 2 info | Console-defined connector: two GND pins, as on every 7800 cart. |
| XT-001 /A10 and /A11 parallel ~7 mm | 1 info | 1.79 MHz bus; accepted. |
| TS-003 / TP-001 U11 Tj 96 °C | 1 + 5 | False positive, as on SMS and the 2600 Rev1. The heuristic puts the whole board's 0.286 W into the AP2112K. The LDO carries the RP only: 51-102 mW at 30-60 mA (`margins.py`), a 13-26 °C rise. |
| SW-001 / EE-001 / EE-002 buck harmonics, cavity resonance | 5 | Informational estimates; no pre-compliance scan was done. The S3 is a certified module; the buck is the NES / SMS layout. |
| TE-001 test points 13/167 nets | 1 | The bring-up block covers the console strobes, the glue outputs, the rails, SWD and RUN; the bus is probed at the fingers, the RP UART at J2. |
| GR-002 height varies 18.7 mm; GR-004 paste 43 % | 2 | Inner copper stops at the tab, as it must; the fingers, holes, test pads and vias carry no paste. `check_gerbers.py` checks both properly. |
| CP-002 no copper under H1-H4, J1, J2 | 6 info | The keep-outs and the tab. |
| OR-001 31 passives not at 90° | 1 info | The decoupling ring follows the RP's pins; the CPL carries measured rotations. |
| DFM-001 board over 100 x 100 mm | 1 info | 72.4 x 115 mm; a price note only. |
| TV-001 thermal vias | 3 info | U1 10 / 9, U7 12 / 9, U8 9 / 9: adequate. |
| PU-001, EP-AUD, CG-AUD, VD-004, PS-001, CERT-001, WL-001, LC-007, LB-001 | as Part 1 | As Part 1. |
| Cross-analysis | 0 | Schematic and board agree. |

## Not performed / limits (layout)

- **No field solver or SI/PI simulation.** GP-001, RP-001 and XT-001 were judged by hand against signal speed: a 1.79 MHz bus, 12 Mb/s USB.
- **No EMC pre-compliance scan:** the analyzer's emission numbers are heuristics.
- **The mechanical items are not measured:** board thickness, the console slot's clearance around the 72.4 mm body, the tab depth and the shell mouth. Each is a VERIFY in `case/case-spec.md`; the 1:1 tab fit and the thickness gate the order.
- **U6's JLCPCB rotation** (AS6C4008, no EasyEDA footprint) follows the TSOP-I convention. Confirm it in the placement preview.
- **No impedance-controlled stack-up:** USB is full-speed over short runs.

## Verdict (layout)

The board is routed and DRC-clean at every severity, with schematic parity, and the fab files pass the gerber gate on both faces of the edge. One placement fix came out of routing: the D0-D7 packs now face the RP. Every analyzer finding is triaged above, and none calls for a further layout change.

Before ordering:
1. Fit the tab. Print `docs/layout-front.svg` at 1:1, or order a 2-layer coupon, and try it in a real 7800: the key slots, every finger on its contact, and nothing in the console touching the 72.4 mm body. Also measure a real cart's thickness.
2. Check U6 (TSOP-I pin 1) in the assembler's placement preview.
3. Consign the AS6C4008-55TIN at JLCPCB, or order PCBWay turnkey.
4. Order options: 6 layers, 1.6 mm, ENIG + hard-gold fingers with a 30-45 degree bevel, epoxy-filled vias (vias sit in the RP, CP2102N and S3 thermal pads). For JLCPCB: Standard PCBA; if rails are needed, on the left and right body edges only, never on the tab or the top edge (USB-C, microSD, antenna).

Re-run: `tools/audit/run_pcb_audit.sh` (after `tools/export.py`).
