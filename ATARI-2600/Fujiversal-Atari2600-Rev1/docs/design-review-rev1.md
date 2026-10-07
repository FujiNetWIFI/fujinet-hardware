# Fujiversal-Atari2600 Rev1 Design Review

**Project:** Fujiversal-Atari2600-Rev1 (KiCad 10.0.6; root + 4 wired sheets; 4-layer PCB, routed)
**Date:** 2026-10-06
**Analyzers (kicad-happy 2.2.1, run `analysis/2026-10-06_1655`):** `analyze_schematic.py`, `simulate_subcircuits.py` (ngspice), `analyze_pcb.py --full --proximity`, `cross_analysis.py`, `analyze_emc.py`, `analyze_thermal.py`, `analyze_gerbers.py`, `lifecycle_audit.py` (LCSC only), Deep Review pass (`analysis/deep_review.json`, 19 findings, evidence gate 19/19 verified). Also `tools/check_nets.py` (290 netlist-vs-firmware checks), KiCad ERC (`--severity-all`) and DRC (`--schematic-parity`).
**Datasheets:** `datasheets/` (synced from LCSC for every MPN; `manifest.json` kept, PDFs gitignored). Page numbers below are those of the LCSC copies.

## Overview

All-in-one Atari 2600 FujiNet cartridge. An RP2354A (RP2350A + 2 MB flash in one QFN-60) sits directly on the 2600's cartridge port and serves the 4 K window, wired exactly as the fn-2600 firmware's `vcs_pins.h` expects (A0-A12 on GP2-14, D0-D7 on GP15-22, LED on GP25). An ESP32-S3-WROOM-1-N16R8 runs FujiNet (`fujiversal-atari2600`) and is the RP's USB host. USB-C (CP2102N + esptool auto-program) and microSD are the external ports. Power: console 5 V through a P-FET, ORed with USB VBUS through a Schottky; an AP63203 buck makes 3.3 V for the S3 side and an AP2112K LDO powers the whole RP.

## Previous Review Delta (Rev0, branch `atari2600-rev0` -> Rev1)

| Status | Item |
|---|---|
| Changed | RP2040 + W25Q16 + 3x 74LVC245A -> RP2354A wired straight to the edge (GPIO0-25 are 5 V-tolerant "Digital IO (FT)" with IOVDD at 3.3 V) |
| Fixed | Rev0's firmware never drove the '245 DIR pin (the cart could not drive the bus). There is no DIR on Rev1: the RP's output enable is the whole direction control |
| Fixed | RP pads must be powered before 5 V reaches them: the whole RP runs from a 20 us LDO on the 5 V rail instead of the buck |
| New | Console 5 V sense on GPIO27 (`main.c` flagged "power sense ... an item for the PCB") |
| Fixed | Console 5 V entered through a Schottky; now a P-FET (gate = VBUS), with a 4.7k gate pull-down against the Schottky's reverse leakage (found in this review) |
| Fixed | WS2812B-2020 ran from 3.3 V against a 3.7-5.3 V datasheet range; now on +5V |
| Fixed | The RP activity LED was a green 0603 (VF ~3.1 V) on a 3.3 V pin; now red through 680R (~2 mA) |
| Changed | ESP32-S3 antenna overhang (6.4 mm past the edge) -> flush with the edge over a copper-free band: JLC standard assembly (needed for gold fingers) adds edge rails, which an overhang collides with |
| Changed | microSD moved from the top edge to the right edge to keep metal away from the antenna |
| Changed | Label-per-pin schematic -> wired, left-to-right sheets; the 21 edge lines are straight wires finger -> GPIO |

## Critical Findings

| Severity | Issue | Disposition |
|---|---|---|
| WARNING (fixed) | SS34 reverse leakage could lift the P-FET gate (the VBUS net, pulled down only by the 69k CP2102N divider) and half-close the console 5 V switch | R19 4.7k VBUS-GND: gate stays under 2.2 V up to 500 uA leakage (Deep Review) |
| WARNING (accepted) | ESP32-S3 antenna side clearance is shorter than the footprint's 15 mm recommendation | Band under the antenna copper-free on all layers; nearest metal (USB-C) ~22 mm from the antenna centre; RSSI check on the bench |
| INFO | Firmware not yet ported: `fujivcs` is an RP2040 board (`PICO_PLATFORM rp2040`), and still writes DIR_PIN 26 | README "Firmware changes this board needs"; GPIO26 is deliberately unconnected so the write is harmless |

No CRITICAL issues. The schematic and the board are internally consistent (ERC 0, DRC 0, parity 0, check_nets 290/290) and every IC's usage was checked against its datasheet.

## Component Summary

| Type | Count |
|---|---|
| ICs | 7 (RP2354A, ESP32-S3-WROOM-1-N16R8, CP2102N, UMH3N, AP63203, AP2112K; WS2812B counted as LED) |
| Capacitors | 37 |
| Resistors / array | 21 / 1 |
| Diodes / LEDs / FET | 5 / 2 / 1 |
| Connectors | 3 (24-pin edge, microSD, USB-C) |
| Switches / test points / inductors / crystal | 4 / 5 / 2 / 1 |

88 schematic components (82 assembled; the edge and 5 test pads are copper only), 43 BOM lines, 0 DNP, 73 named nets, MPN and LCSC coverage 100 %.

## Power Tree

```
edge 23 CONS_5V --[Q1 AO3401A P-FET, G = VBUS, R19 4.7k pull-down]--+
              \--[R20/R21 100k/150k]--> VSENSE (GPIO27, 0.6 x CONS_5V) |
USB-C VBUS ------[D7 SS34]---------------------------------------------+--> +5V
                                                                         |-- U5 AP63203 buck 3.3 V/2 A --> +3V3: ESP32-S3, microSD, CP2102N
                                                                         |-- U6 AP2112K 3.3 V (20 us) ----> +3V3_RP: RP2354A IOVDD x6, QSPI_IOVDD,
                                                                         |                                   USB_OTP_VDD, ADC_AVDD, VREG_VIN,
                                                                         |                                   VREG_AVDD (33R/4.7 uF) -> core SMPS
                                                                         |                                   (3.3 uH AOTA) -> DVDD 1.1 V
                                                                         +-- D3 WS2812B-2020 (VDD 3.7-5.3 V)
```

Budget (estimates): +3V3 ~60 mA idle, ~350 mA during WiFi TX; +3V3_RP 16-40 mA (RP2350 datasheet Table 1693). Peak from the console's 7805 about 250-300 mA through the buck: a bench item (README checklist).

## Analyzer Verification

### Component count
Schematic analyzer: 88 components, 126 nets (73 named + KiCad's unconnected-pin nets), 53 no-connects. Board: 95 footprints = 88 + 4 mounting holes + 3 fiducials. Matches `design.py`.

### Pinout verification (datasheet, not library symbol)

| Ref | Part | Check | Source | Result |
|---|---|---|---|---|
| U1 | RP2354A | every GPIO -> QFN-60 pin | RP2350 DS Table 1427 (p.1331-1333) | GP0-29 = pins 2-5, 7-10, 12-19, 27-29, 31-37, 40-43: match |
| U1 | RP2354A | supply pins | DS Figure 2 (p.16), Table 1432 (p.1335) | IOVDD 1/11/20/30/38/45, DVDD 6/23/39, VREG 46-50, USB 51/52, OTP 53, QSPI 54-60, GND 61: match. Table 1432 omits pin 1 and lists 54 (erratum); the board ties all of them to +3V3_RP |
| U1 | RP2354A | XIN/XOUT/SWD/RUN | DS Tables 1429/1430 (p.1333) | 21/22, 24/25, 26: match |
| U2 | ESP32-S3-WROOM-1 | IO19/20 = USB D-/D+, TXD0/RXD0, IO38-42, IO48 | DS pin table (p.11-12) | match |
| U3 | CP2102N | D+/D- 4/5, VDD 6, VREGIN 7, VBUS 8, /RST 9, RXD 25, TXD 26, RTS 24, DTR 28 | DS (p.8-9 connection diagrams) | match (unchanged from the audited NES/Astrocade block) |
| Q1 | AO3401A | SOT-23 G 1, S 2, D 3; body diode D -> S | DS p.1-2 | match |
| D1 | BAT54C | common cathode 3, anodes 1/2 | DS package drawing | match |
| D3 | WS2812B-2020 | 1 DO, 2 GND, 3 DI, 4 VDD | DS p.2 "PIN Function" | match |
| U5 / U6 | AP63203 / AP2112K | TSOT-23-6 / SOT-23-5 pin tables | DS p.3 / p.2 | match |
| J1 | 2600 edge | 24-pin map, face orientation | FujiPlusCart prototype gerbers (Rev0) | match (`check_nets.py` carries an independent copy) |

### Net tracing
`tools/check_nets.py` (independent of `design.py`) reads `vcs_pins.h`, `fujivcs.cmake/.h` and `fujiversal-atari2600.h` from `~/Workspace/fn-2600` and checks 290 items: every edge pin -> its GPIO directly, every bus GPIO 5 V-tolerant, DIR_PIN unconnected, every RP supply pin on +3V3_RP, VREG_AVDD through 33R, LX -> 3.3 uH -> DVDD, the VSENSE divider levels, USB 27R pair, RUN/BOOTSEL forcing (1k from IO4/IO5) and pull-ups, crystal, SD/UART/LED pins. A mutated header (D0_PIN 16, SD CS 42) fails 9 checks.

## Deep Review (19 findings, all verified by `deep_review_gate.py`)

| Category | Finding |
|---|---|
| io | Bus straight to GPIO2-22, all FT (5.5 V with IOVDD 3.3 V; DS p.14, p.1332, p.1336) |
| power | Whole RP on the 20 us AP2112K so IOVDD tracks the console 5 V; FT limit 3.63 V unpowered / 4.2 V at 2.5 V / 5.5 V at 3.3 V |
| power | VREG_VIN + VREG_AVDD together on the LDO rail (DS p.402, Figure 19 p.408); RC filter, AOTA inductor (p.412-413) |
| power | DVDD 100 nF on pins 39/6, 4.7 uF on the far pin 23 (p.401), on an In2 DVDD island + lobe |
| pinout | Table 1432 IOVDD erratum (see above) |
| io | VSENSE 100k/150k: 3.15 V at 5.25 V (GPIO27 is an ADC pin, not FT), 2.70 V at 4.5 V |
| usb | 27R series on the RP USB (p.1333) |
| power (WARNING, fixed) | SS34 leakage vs P-FET gate; 4.7k added |
| led | WS2812B on +5V, VIH 2.7 V accepts 3.3 V data (p.3) |
| led | RP LED red, 2.1 mA |
| usb | CP2102N VBUS sense 3.41 V (VIH 2.7 V, max VIO + 2.5 V; p.8) |
| mcu | ESP32-S3 EN RC 10k/1 uF (p.41) |
| oscillator | ABM8-272-T3 CL 10 pF: 15 pF loads -> 10.5 pF (also SPICE) |
| power | AP63203 VIN 3.8-32 V vs +5V 4.3-5.0 V; AP2112K EN up to 6.0 V |
| rf (WARNING, accepted) | Antenna at the edge, copper-free band, reduced side clearance |
| thermal | LDO 27-68 mW, Tj 32-42 C (analyzer's 95 C assumed 165 mA) |
| usb | FS USB pair skew 6.5 / 5.7 mm = ~40 ps vs 4-20 ns edges |
| emc | B.Cu bus references a split In2; 1.19 MHz bus, accepted for a prototype |

Computations: `tools/audit/margins.py`. Generator: `tools/audit/make_deep_review.py`.

## Signal Analysis Review

- **Regulators:** U5 AP63203 (switching, 3.3 V fixed), U6 AP2112K-3.3 (LDO). Both outputs named correctly; inputs on +5V.
- **Dividers:** R16/R17 VBUS sense (0.681), R20/R21 VSENSE (0.600): SPICE matches to 0.0 %.
- **RC:** R11/C20 ESP EN delay 15.9 Hz (tau 10 ms): SPICE 0.27 % off.
- **Crystal:** Y1 12 MHz, 10.5 pF load vs CL 10 pF: pass.
- **Protection:** D4-D6 ESD5Z on UBRG_DP/DM/VBUS at the USB-C.
- **LEDs:** D2 resistor-limited 2.1 mA; D3 WS2812 single-pixel chain.
- **Simulation:** 16 subcircuits, 16 pass (dividers, RC, crystal, decoupling impedance, inrush).
- **Decoupling:** every RP supply pin has 100 nF (USB_OTP/QSPI_IOVDD share one, as Raspberry Pi's minimal design does), 10 uF bulk on +3V3_RP, 4.7 uF VREG_VIN/VOUT/AVDD per Figure 19; S3 22 uF + 100 nF; CP2102N 4.7 uF + 100 nF.

## PCB Layout (Part 2)

### Analyzer runs
| Analyzer | Result |
|---|---|
| KiCad DRC (`--refill-zones --schematic-parity`) | 0 errors, 0 unconnected, 0 parity; 4 warnings (the ESP32 module's own silkscreen outline meets the top edge it sits flush with; clipped by the fab) |
| `analyze_pcb.py` | routing complete; 95 footprints, 342 vias (120 GND stitching), 4 copper layers; DFM tier "standard", 0 violations (min track 0.15, min space 0.152, min drill 0.25, min annular 0.125) |
| `cross_analysis.py` | 2 findings (USB_DP 0.7 mm / USB_DM 1.6 mm from the left edge, where the S3 module's USB pads are) |
| `analyze_emc.py` | 67 findings (8 high, 51 warning); per-net scores 71.5 (USB_DM) to 100 |
| `analyze_thermal.py` | score 97/100; one heuristic warning (LDO, false: see Deep Review) |
| `analyze_gerbers.py` | complete layer set (4 Cu, masks, paste, silk, Edge.Cuts, PTH + NPTH drill); 2 warnings, both by design |

### Layout findings and dispositions
| Rule | Finding | Disposition |
|---|---|---|
| KO-001 | J1 inside the finger-strip rule area | False positive: the rule area allows pads; the fingers belong there |
| PM-002 | J2 at the edge; R15, C34/C35, L2, SW1/3/4 0.47-0.9 mm from the edge | Edge connectors by design; the rest is fine for fab (copper-to-edge 0.25 mm) and JLC adds assembly rails |
| DC-002 | No cap near U4 / U2 | U4 (UMH3N) has no supply pin. U2: the module's 3V3 pad is at the board edge under the antenna band, so its 22 uF + 100 nF sit 15 mm away on the +3V3 plane (the module carries its own decoupling) |
| DP-001/003/004 | USB pair skew, layer changes, outer layer | Full-speed USB only (12 Mb/s): ~40 ps skew, see Deep Review |
| NR-001 | USB_DP 0.7 mm from the edge | The S3's USB pads are on its edge-side column; FS USB, accepted |
| GP-001 / RP-001 | Bus nets cross plane gaps / change layers without a nearby stitch | Tab plane setback (by design) and In2 island edges; 1.19 MHz bus. 120 GND stitching vias tie the pours |
| CK-001/003, XT-001 | SD_SCK, XIN/XOUT, SWCLK on outer layers; close SD spacing | 20 MHz SPI / 12 MHz crystal over a solid GND plane (In1 under F.Cu); accepted |
| BE-002 | Incomplete ground pour at the edges | The antenna band and the tab are copper-free by design |
| ML-001 | L2 near sensitive parts | SWPA4030S is magnetically shielded; 14 mm from the nearest flagged part |
| TS-003 | LDO Tj 95 C | False (heuristic 165 mA load); 42 C at 40 mA |
| GR-002 | Layer extents differ by 9.3 mm | Inner planes stop 9 mm from the bevelled edge; fingers are outer-layer only |
| GR-004 | Paste flashes 48 % of copper flashes | Vias, NPTH and the gold fingers carry no paste |

### Gerbers
`exports/jlcpcb/Fujiversal-Atari2600-Rev1-gerbers.zip`: F/In1/In2/B copper, masks, paste, silk, Edge.Cuts, PTH and NPTH Excellon, drill maps, job file. Drill tools: 0.25 / 0.3 / 0.4 mm vias, 0.6 mm USB-C shell, NPTH 0.65 / 1.0 mm (USB-C / microSD pegs), 3.2 mm (shell screws).

### Mechanical
Rev0's proven outline (54.4 x 88 mm, 32.4 mm tab, 45-degree shoulders) and finger geometry (2x12, 2.54 mm, 1.5 x 7 mm, 0.5 mm from the edge, F.Cu = pins 13-24 toward the console rear). Every courtyard ends above y 90.5 (the shell's bottom face, 25.5 mm above the contact edge). The shell (`case/`) renders as two manifold halves; the microSD slot moved to its right wall.

## Quality and Manufacturing

- **JLCPCB:** 4 layers, 1.6 mm, ENIG + gold fingers, 30-degree bevel. Gold fingers need Standard PCBA, which needs edge rails and fiducials (3 on the board). Rules are above JLC's multilayer minimums (0.09 mm track/space, 0.15 mm drill, 0.25 mm via).
- **Via-in-pad:** the RP2354A exposed pad carries Raspberry Pi's 9 thermal vias and the CP2102N exposed pad a 3 x 3 array: order epoxy-filled and capped vias if offered, else expect some solder wicking (GND/thermal only).
- **CPL:** rotations and origins measured against the EasyEDA footprint of every LCSC part (`tools/audit/jlc/jlc_rotations.json`), cathode-checked for LEDs and diodes. Still review JLC's placement preview.
- **Sourcing (JLC stock 2026-10-06):** all 39 LCSC codes in stock; 22 basic, 17 extended (ESP32-S3, RP2354A, CP2102N, AP63203, AP2112K, UMH3N, BAT54C, ESD5Z, WS2812B, TF-015, USB-C, TL3342, ABM8, AOTA, SWPA4030S, 0402 27R). Thinnest: AOTA-B201610S3R3 (908), TL3342F160QG (1,786).

## False Positives / Reviewer Overrides
Recorded in `.kicad-happy.json` with reasons: PU-001 (CP2102N CHREN), RS-001 (VBUS_SNS divider node), KO-001 (fingers in their own rule area), DC-002 (U4 has no supply), PM-002 (edge connectors), EP-AUD (console bus, microSD inside the shell), CG-AUD (Atari's pinout).

## Not Performed / Review Limits
- **Lifecycle audit:** run against LCSC only, which reports no lifecycle status ("unknown" by construction); no DigiKey/Mouser/element14 API keys in this environment.
- **Datasheet extraction cache:** not built; the Deep Review read the PDFs directly (quotes located with `tools/audit/find_quote_page.py`).
- **Firmware:** this board needs an RP2350 port of `fujivcs` (README); not built or run here.
- **Hardware:** nothing has been built. Bus timing, antenna performance and console power headroom are bench items.

## Verdict
**Ready to order as a prototype from JLCPCB** (fab + assembly), with the bring-up checklist in the README. Schematic: complete and verified against the datasheets and the fn-2600 firmware headers. Layout: 100 % routed, DRC clean with schematic parity, DFM clean against JLC's standard tier, fabrication files complete.
