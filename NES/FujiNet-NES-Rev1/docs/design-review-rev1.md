# FujiNet-NES Rev1 Design Review

**Project:** FujiNet-NES-Rev1 (KiCad 10 project, root + 6 hierarchical sheets, 6-layer 1.2 mm board)
**Date:** 2026-10-19
**Analyzers:** kicad-happy 2.2.1, run `analysis/2026-10-18_2341`: `analyze_schematic.py`, `analyze_pcb.py --full --proximity`, `cross_analysis.py`, `analyze_emc.py`, `analyze_thermal.py`, `simulate_subcircuits.py` (ngspice), `analyze_gerbers.py`; Deep Review (`analysis/deep_review.json`, 22 findings, evidence gate 22/22 verified); `tools/check_nets.py` (415 netlist-vs-firmware checks); KiCad ERC and DRC at every severity.

## Overview

The Rev0 cartridge without its two SRAMs. Two RP2354Bs serve the console's two buses directly:

- **RP-A (U1)** serves the CPU bus. A PIO+DMA engine serves PRG from RAM (images up to 384K) or, for 512K, from the RP's in-package flash through the QMI address-translation windows. RP-A also serves the mailbox, loader and WRAM, runs every mapper and drives the MMC3 IRQ.
- **RP-B (U2)** serves the PPU bus: CHR, CHR-RAM and four-screen nametables from RAM, with CIRAM A10 and /CE from a PIO table. It has no firmware in flash; RP-A loads it over SWD at every boot.
- **The link:** 11 lines (LD0-7, LCLK, LFRM, LACK) carry mapper writes and CHR data from RP-A to RP-B.

The ESP32-S3, USB-C, microSD, buck, P-FET power entry, buttons and CIClone are Rev0's, in Rev0's places. Rev0's shell fits: `case/board-anchors.scad` is byte-identical.

## Previous Review Delta (Rev0 -> Rev1)

| Status | Item |
|---|---|
| Removed | 2 x AS6C4008-55TIN (0 JLC stock, $6.36 each), 74HCT595 / 253 / 14 / 20 / 00 / 32, RN1/RN2 pull-down packs, the POR RC |
| Added | RP-B: a second RP2354B (U2) with its own crystal (Y2), core inductor, AP2112K (U9) and decoupling |
| Changed | PWR_OK divider: 22k/100k (0.82 x CONS_5V) into a 5 V '14 -> 2.2k/3.3k (0.6 x CONS_5V) straight into both RPs (3.63 V fault-tolerant limit, erratum E9) |
| Changed | Status LED: KT-0603G green (VF 3.1 V) from the '595 -> KT-0603R red on RP-A GP27 through 330R |
| Changed | Bus gating when the console is off: the '253 / '595 tri-state logic -> the firmware's OEOVER overrides, gated by PWR_OK |
| Changed | Edge pin 58 (PPU /A13) left open: RP-B decodes PA13 itself. PA12 goes to both RPs (RP-A GP47 for the MMC3 filter) |
| Changed | CHR ceiling 512K -> 256K (MMC3's maximum; no Tier-1 mapper addresses more) |
| Fixed (firmware) | Latent Rev0 bug: /ROMSEL was sampled before it settles. Rev1 resamples it after T_ROMSEL. **Still open on Rev0's `nes-bringup` branch** |
| New (layout) | The edge buses and the link are drawn as locked copper by `gen_pcb.py` (routers could not escape two QFN-80s) |
| Open | AOTA-B201610S3R3 core inductor: 0 LCSC stock, now x2 (Rev0 needs it too) |

## Critical Findings

| Severity | Issue | Section |
|---|---|---|
| WARNING | 512K PRG from flash has thin timing margin on the bench (211-226 ns vs 230), and one MMC1 case regressed to 241 ns when the engine moved into the firmware | Timing |
| WARNING | RP-A must run at 266 MHz / 1.20 V (an overclock; Rev0 runs at 200 MHz) for 512K images | Timing |
| WARNING | AOTA core inductor (x2) at 0 stock: consign or substitute | Sourcing |

No CRITICAL issue remains in the schematic or the layout. All three warnings are bench, firmware or sourcing items, not CAD errors.

## Component Summary

| Type | Count |
|---|---|
| ICs | 9: 2 x RP2354B, ESP32-S3-WROOM-1-N16R8, CP2102N, UMH3N, AP63203, 2 x AP2112K, ATtiny13A (DNP) |
| Capacitors / resistors / arrays | 62 / 25 / 1 |
| Diodes / LEDs / FET | 5 / 2 / 1 |
| Connectors / switches / test points | 3 / 4 / 13 |
| Inductors / crystals | 3 / 2 |

130 parts in `design.py` (2 DNP: the CIClone and its capacitor), 133 footprints on the board including 3 fiducials. 134 schematic nets. MPN and LCSC coverage is 100 %. The JLC BOM and CPL have 114 rows each.

## Power Tree

```
edge 36 CONS_5V --[Q1 AO3401A, G = VBUS, R25 4.7k pull-down]--+
USB-C VBUS -----[D7 SS34]---------------------------------------+--> +5V --> WS2812B
                                                                     +--> U7 AP63203 buck --> +3V3: ESP32-S3, microSD, CP2102N
                                                                     +--> U8 AP2112K --> +3V3_RP:  RP-A IOVDD x8, QSPI/USB/ADC, VREG_VIN (+VREG_AVDD via 33R) -> DVDD
                                                                     +--> U9 AP2112K --> +3V3_RPB: RP-B, the same set -> DVDD_B
PWR_OK = 0.6 x CONS_5V (R 2.2k / 3.3k), sensed before Q1 --> RP-A GP26, RP-B GP24 and GP44 (ADC4)
```

Each RP's whole supply group sits on its own fast-start LDO off +5V. Its pads are 5 V-tolerant only while IOVDD is up, and the buck's 4 ms soft-start would leave them unpowered while the console already drives 5 V (Rev0's rule).

## Analyzer Verification

ERC: 0 violations at every severity. Netlist parity with `design.py`. `check_nets.py`: 415/415 against `nes_bus.h`, `nes_cart.h`, `nes_ppu.h` and `nes_link.h` on fujinet-firmware `simplify-nes`, the nesdev edge map and the edge footprint. It covers both GPIO maps, the mirrored link, the SWD/RUN wiring, each RP on its own LDO, and the PWR_OK ratio and source impedance. It was mutation-tested: moving a header pin or changing a divider value makes it fail.

Pinouts were checked against the manufacturers' PDFs (page and quote in `analysis/deep_review.json`): RP2354B (both instances, against `design.py` and the KiCad symbol), AP2112K, AP63203WU, AO3401A, CP2102N, UMH3N, ESP32-S3-WROOM-1, TF-015, ATtiny13A, BAT54C (package drawing only). The edge footprint was checked against the measured NES-EWROM-01 (`tools/audit/edge_orientation.py`).

## Deep Review (22 findings, all evidence-verified)

**Power**
- One AP2112K per RP, each holding that RP's whole supply group. About 0.10 W per LDO.
- Supply order: only VREG_VIN and VREG_AVDD must rise together, and both sit on the RP's own rail.
- Console entry through the P-FET: about 24 mV drop at 0.4 A, and USB never back-feeds the console. Unchanged from Rev0.

**I/O**
- **PWR_OK** is 0.6 x CONS_5V: 3.30 V at 5.5 V (under the 3.63 V an unpowered pad takes), 2.70 V at 4.5 V (over the 2.15 V VIH), source impedance 1.32k (under erratum E9's 8.2k).
- **Bus outputs** stay high-impedance until PWR_OK: RP-A's CD0-7 and RP-B's PD0-7 and CIRAM lines are held off by OEOVER.
  - Out of reset the pads are inputs with pull-downs, so nothing drives the bus before the firmware runs.
  - Firmware review item: set OEOVER before any output enable; a falling PWR_OK must drop the overrides within one interrupt.
- **RP2350 VIH** is 0.65 x IOVDD = 2.15 V against the NMOS 2A03/2C02 outputs. That margin is thin, but every CMOS cart has it; Rev1 now has it on both buses. Bring-up item.
- **LED:** a red KT-0603R (VF 1.8-2.4 V) at about 3 mA. The WS2812B stays on 5 V; its VIH of 2.7 V takes 3.3 V data.

**Oscillators:** both ABM8-272-T3 crystals (CL 10 pF) get 15 pF load caps, which gives 10.5 pF with stray capacitance.

**Mechanical:** the edge footprint matches NES-EWROM-01 with pin 1 east on F.Cu. `check_gerbers.py` checked the fab zip finger by finger.

**Sourcing (warning):**
- At LCSC on 2026-10-19, C42411119 (AOTA inductor, x2) shows 0 stock.
- Also at 0: C2913202 (the ESP32-S3 module), C21190 (1k) and C25819 (47k). C62684 (the buck inductor) is no longer listed.
- All of these lines are shared with Rev0. The two resistors are JLC Basic parts, which JLC stocks itself. Check JLC's stock at order time.

## Timing (Phase 0 bench, not a console)

The board only works if both RPs answer their bus fast enough. All of this was measured on a stock Pico 2 with an on-chip PIO loopback bench (`fujinet-firmware pico/nes/bench`, which links the firmware's own engine). Each run is 10^7 cycles, and every scenario had 0 errors.

| Path | Measured | Bar | Verdict |
|---|---|---|---|
| RP-A PRG from RAM (images up to 384K), M2 rise -> data | 143-177 ns | 150 (plan), 230 (console) | Misses the plan's own stretch bar; inside the console bar |
| RP-A PRG from flash via ATRANS (512K) | 211-214 ns | 230 | Pass, thin |
| The same, MMC1 SUROM half switch | 241 ns | 230 | **Over**: regression from the engine's move into the firmware (222 ns before); open |
| The same, under core0 memcpy stress | up to 241 ns | 230 | Information rows |
| RP-B /RD fall -> PD valid | 94 ns | 110 | Pass |
| RP-B CIRAM table | 30 ns | 40 | Pass |
| RP-B /RD rise -> PD released | 41 ns | 40 | Marginal |
| Link: mapper write -> RP-B slot updated | 551-566 ns, 0 errors in 10^7 frames | 1 us | Pass |

Not covered by the bench:
- the console's own /ROMSEL delay (up to about 33 ns after M2);
- NMOS signal levels;
- the board's own traces.

`bustest.nes` (not written yet) is meant to check a real console without instruments. RP-A at 266 MHz / 1.20 V is an overclock.

## Signal Analysis Review

- **Regulators:** U7 AP63203 (switching, +5V -> +3V3); U8 and U9 AP2112K (LDO, +5V -> +3V3_RP / +3V3_RPB); each RP's internal SMPS makes DVDD / DVDD_B at 1.1 V (RP-A at 1.20 V in firmware).
- **Dividers:**
  - VBUS_SNS (22k/47k) is simulated.
  - The PWR_OK divider is not, because kicad-happy treats PWR_OK as a rail. It is computed in the deep review and asserted by `check_nets.py`.
- **Simulation:** ngspice, 20 subcircuits, 20 pass: both crystal loads, one divider, one RC, three ESD devices, ten decoupling networks and three inrush models.
- **Differential pairs:** USB at Full Speed only (RP_USB, the S3's host pads, CP2102N).

## PCB Layout, Cross-Domain, EMC, Thermal, Gerbers

**Board:**
- `FujiNet-NES-Rev1.kicad_pcb`, generated by `tools/gen_pcb.py` and `tools/placement.py`.
- Locked copper drawn by `gen_pcb`: finger stubs, the link (`link_route`), both edge buses (`bus_route`) and RP-A's PA12 escape (`pa12_escape`).
- Routed by `tools/route_board.sh`: corner pre-routes, Freerouting 2.4.1, the A* finisher, tidy, GND stitching, the via check and saved fills.
- Three variants were run in parallel. The best one ("C", 8 passes, global strategy) left PA12 open. Its escape and a B.Cu run to RP-B's PA12 field via were added by hand, and the pipeline's tail and gates were re-run.
- Totals: 1239 track segments (4.78 m; Rev0 had 7.13 m) and 820 vias: 640 at 0.6/0.3, 178 at 0.5/0.25 (bus fields, under the RPs), 2 at 0.8/0.4. 473 of the vias are GND.

**Gates:**
- KiCad DRC at every severity on the **saved** fills: **0 violations, 0 unconnected, 0 schematic-parity issues**.
- ERC 0; `check_nets.py` 415/415.
- On the fab zip: `check_gerbers.py` 0 failures, `check_plane_shorts.py` 0.

### Analyzer runs (kicad-happy 2.2.1)

| Analyzer | Result |
|---|---|
| `analyze_pcb.py --full --proximity` | 87 findings (37 error, 21 warning, 29 info); routing complete, 0 unrouted nets |
| `cross_analysis.py` | 1 (RP-002) |
| `analyze_emc.py` | 61 (6 error, 39 warning, 16 info) |
| `analyze_thermal.py` | score 94/100; 2 warnings (TS-003), 17 info |
| `simulate_subcircuits.py` | 20/20 pass |
| `analyze_gerbers.py` | complete 6-layer set; 2 warnings |
| lifecycle audit | not run (no distributor API keys) |

### Layout findings and dispositions

Every high/error finding is listed below; warnings are grouped.

| Finding | Disposition |
|---|---|
| KO-001 x36: vias in `shell_post_*`, J1 in the tab keep-outs | False positive, as on Rev0. The analyzer tests a keep-out's bounding box, but the shell-post areas are circles, and KiCad's DRC, which tests the real shape, is clean. The fingers are allowed on the tab |
| PM-002 J2 0.2 mm from the edge | By design: the microSD and the USB-C sit at the edge, at Rev0's positions |
| DC-002 U6 has no decoupling | UMH3N is a transistor pair with no supply pin. False positive |
| DP-001 / DP-003 / DP-004 USB skew, layer changes, outer layer | Accepted: every USB endpoint is Full-Speed (83 ns bit time); the analyzer applies the High-Speed budget |
| RP-002 CIC_CLK "crosses a GND plane gap on F.Cu" | The gap is in the F.Cu pour; the reference plane for F.Cu is In1, which is solid GND. CIC_CLK is the console's 4 MHz lockout clock to the DNP CIClone. Accepted |
| RP-001 x20+ layer transitions without a stitching via (CA*, CD*, PA*, PD*, M2) | The bus nets go F -> In2 -> In3 -> the finger's face. In2 references In1 (GND); In3 references In4 (+3V3 planes), which closes to GND through the decoupling at each RP and the 4 mm stitching grid; the IOVDD caps' GND vias sit just below the bus fields. The buses run at 1.79 / 5.37 MHz. Accepted, as on Rev0 |
| CK-001 x10 clocks on outer layers | XIN/XOUT: short crystal runs. SWCLK / RPB_SWCLK: SWD, used only at boot. CIC_CLK: a finger. **LCLK: the link, on F.Cu by design (no vias)** |
| XT-001 LCLK/LD7 9 mm, LD pairs up to 55 mm at 0.4 mm pitch (F.Cu) | The link is nested arcs at 0.4 mm pitch, over In1 GND. RP-A changes LD only between LCLK edges, and RP-B's PIO (`nes_link_rx`) samples LD one instruction after it sees an edge through its input synchronisers, about 15 ns at 266 MHz. Near-end coupling from LCLK's own edge has settled by then. Bring-up: RP-B's frame-error and CRC counters in its SWD status block |
| (no analyzer row) In3 channel tracks run parallel | Adjacent tracks at 0.5 mm pitch (0.35 mm gap) overlap by up to 19 mm (CA11/CA12, PD3/PD4). These are bus lines sampled late in a 559 ns CPU cycle or a two-clock (372 ns) PPU fetch. Crosstalk settles in nanoseconds, but RP-A's PRG data path is the tight one (211-226 ns from M2 rise, see Timing). Accepted; `bustest.nes` covers it |
| CC-002 x20 0.15 mm tracks | The bus lanes and link by design (JLCPCB minimum 0.09 mm) |
| TS-003 U8/U9 Tj 96 C (the analyzer assumes 0.286 W each) | Not supported by the datasheets. Each RP's core runs from its own switcher, so the LDO sees only tens of mA. Even at a pessimistic 100 mA (RP-A overclocked): 1.7 V x 0.1 A x 184 C/W = +31 C. Keep the SOT-23-5s |
| BE-002 71 % edge ground, TE-001 12/207 nets on test points, CK-003 SD_SCK near J2 | As on Rev0: the stitching grid and an edge row are in place; the 13 test points are SWD and RUN for both RPs, both debug UARTs, M2, CIC_RST and GND; SD_SCK ends at the slot it clocks |
| NT-001 single-pin nets, RS-001 PWR_OK / VBUS_SNS, PU-001 U5 CHREN | False positives: bus-member labels, divider nodes, and a charger-detect output left open (suppressions in `.kicad-happy.json`) |
| SW-001 / EE-00x / CERT-001 / OR-001 / DFM-001 | Informational |

### Gerbers

- GR-002 "height varies by 16.7 mm across copper/edge layers": the copper stops short of the top edge under the ESP32-S3 antenna keep-out. Expected, as on Rev0.
- GR-004 "front paste 555 flashes vs 1411 copper": the rest are vias, fingers (no paste) and the exposed-pad via arrays. Expected.
- Fab notes for the order: 6 layers, 1.2 mm; ENIG or hard gold on the fingers with a 30-45 degree bevel; 0.6/0.3 mm vias plus 0.5/0.25 in the bus fields and under the RPs.

### Mechanical

The outline, fingers, notches and holes are Rev0's measured NES-EWROM-01 geometry. All case-anchor parts are unmoved, and `case/board-anchors.scad` is identical to Rev0's.

## Quality & Manufacturing

- **Assembly:**
  - All parts on the label side; 0603 passives.
  - Hard parts: two QFN-80s at 0.4 mm pitch, plus the QFN-28.
  - The two TSOP-32 SRAMs are gone.
- **Sourcing:** see the Deep Review. The JLC order drops seven extended-part lines.
- **Cost (LCSC, 2026-10-19):**

| | Rev0 | Rev1 | Saved |
|---|---|---|---|
| Qty 1 | $32.64 | $20.88 | $11.76 |
| 100-piece tier | $26.52 | $15.50 | $11.02 |

  Both totals leave out C62684, which LCSC no longer prices.
- **CPL:** rotations come from `tools/audit/jlc/jlc_rotations.json`, measured per (footprint, LCSC) pair. The red LED (C2286) was matched cathode to cathode. Still check JLC's placement preview before paying.

## Not Performed / Review Limits

- **No board has been built.** No firmware has run on a console.
- **Timing:** bench only (see Timing). The MMC1 512K regression, the RP-B release margin and the input-sync bypass are open firmware items.
- **Firmware, open:** the MAME device is updated but not rebuilt; `bustest.nes` is not written; four-screen is not tested in MAME.
- **Lifecycle audit:** not run (no API keys).
- **Impedance:** not controlled; the buses run at 1.79 / 5.37 MHz and USB is Full-Speed.
- **PWR_OK divider:** not simulated by the analyzer (computed instead; see above).

## Verdict (layout)

Ready to order as a first prototype once the open firmware timing item is understood. The board itself is complete:
- DRC 0 / 0 / 0 at every severity on the saved fills;
- ERC clean; `check_nets.py` 415/415;
- every analyzer finding is a documented false positive or an accepted trade-off.

The risk is in the timing, not the CAD. Fix the MMC1 512K regression on the bench before building boards. Plan the first console bring-up around `bustest.nes`.

**Layout notes worth keeping:**
- **Two QFN-80s' 0.4 mm south rows** could not be escaped by any router (three Freerouting variants, about 6 h each). Deterministic lanes into a two-row via field did it, with a constrained left-edge channel and per-finger column offsets to break constraint cycles.
- **Route each RP's supply pins as lanes too.** Its IOVDD caps then stand under their lane vias.
- **A pin boxed in by neighbouring SWD and IOVDD vias** (PA12) needs a locked escape before routing.
