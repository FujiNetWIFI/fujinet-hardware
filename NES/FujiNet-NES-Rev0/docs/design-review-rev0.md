# FujiNet-NES Rev0 Design Review

**Project:** FujiNet-NES-Rev0 (KiCad 10.0.6 project, root + 4 hierarchical sheets; PCB: see Part 2)
**Date:** 2026-10-01
**Analyzers:** kicad-happy 2.2.1 `analyze_schematic.py` (run `2026-10-01_2033`), `simulate_subcircuits.py` (ngspice), Deep Review pass (`analysis/deep_review.json`, 28 findings, evidence gate 28/28 verified), `tools/check_nets.py` (453 netlist-vs-firmware checks), KiCad ERC (`--severity-all`). PCB, cross-domain, EMC, thermal and gerber analyzers: Part 2, once the layout exists.

## Overview

All-in-one NES cartridge: an RP2354B (RP2350B + 2 MB flash, QFN-80, all 48 GPIO) sits directly on the console's 5 V CPU bus and serves the mailbox / loader / WRAM / reset vectors while two AS6C4008-55 SRAMs (PRG, CHR, 5 V) hold the game and are bank-switched from the RP's PIO tables. 74HCT glue (595 / 253 / 14 / 20 / 00 / 32) does the strobe decode on 5 V. An ESP32-S3-WROOM-1-N16R8 runs FujiNet and is the RP's USB host; USB-C (CP2102N) and microSD are the only external ports. Power is console 5 V through a P-FET, ORed with USB VBUS through a Schottky; an AP63203 buck makes 3.3 V and an AP2112K LDO makes the RP's I/O rail.

This review was done with the first Rev0 schematic (commit `1c9130d`) as the baseline and produced the second one; the delta table below lists what changed and why.

## Previous Review Delta (first Rev0 schematic -> this one)

| Status | Item |
|---|---|
| Fixed | Edge footprint mirrored (pin 1 was west; nesdev + two measured references put it east on the label side) |
| Fixed | Finger geometry guessed (1.6 x 9.5 mm, 0.5 mm in) -> measured NES-EWROM-01 (2.0 x 12 mm, ends 3.0 mm at +/-44.25, copper 1.0-13.0 mm in, front/back mask depths 6.5/11 mm) |
| Fixed | RP pads unpowered with 5 V on them at console power-on (buck soft-start 4 ms) -> the whole RP2354B (IOVDD group, VREG_VIN + VREG_AVDD) on a 20 us LDO |
| Fixed | 74HCT595 random from power-on with /OE grounded -> /OE = NAND(PWR_OK, POR), 100k pull-downs on all bits |
| Fixed | PRG /WE three gates behind the console's /ROMSEL decoder vs ~30 ns data hold -> NAND4 on M2 (74HCT20), one gate |
| Fixed | CIRAM /CE driven by a '32 into a dead console -> through the '253's second half, tri-stated by PWR_OK_N |
| Fixed | Console-sense divider 0.60 x CONS_5V could sit under a TI 74HCT14's VT+ (0.70 x VCC) -> 0.82 |
| Fixed | WS2812B-2020 on 3.3 V against a 3.7-5.3 V datasheet rating -> on +5V (VIH 2.7 V accepts the 3.3 V data) |
| Fixed | 74HCT rail one Schottky drop under console 5 V (4.5 V minimum) -> AO3401A P-FET, ~24 mV |
| Fixed | No VBUS decoupling at the USB-C -> 1 uF + 100 nF |
| New | CIClone (ATtiny13A, DNP) on the four CIC fingers so a stock NES-001 can run the cart once lockout firmware exists |
| Open | PRG write-data hold margin is +2 ns worst-case on a PROVISIONAL 30 ns 2A03 figure (bring-up scope item) |
| Open | AS6C4008 and every 74HCT253 out of JLCPCB stock (see Sourcing) |

## Critical Findings

| Severity | Issue | Section |
|---|---|---|
| WARNING | AS6C4008-55TIN (x2) and the 74HCT253 are not in JLCPCB stock; consign or second-source | Sourcing |
| WARNING | PRG write-data hold after /WE rises rests on nes_cart.h's PROVISIONAL 30 ns; worst-case margin +2 ns | Deep Review / timing |

No CRITICAL issues remain in the schematic. The two items above are sourcing and a bench measurement, not design errors.

## Component Summary

| Type | Count |
|---|---|
| ICs | 15 (RP2354B, 2 x AS6C4008, 74HCT595/253/14/20/00/32, ATtiny13A (DNP), ESP32-S3, CP2102N, UMH3N, AP63203, AP2112K) |
| Capacitors | 50 |
| Resistors / arrays | 21 / 3 |
| Diodes / LEDs / FET | 5 / 2 / 1 |
| Connectors | 3 (72-pin edge, microSD, USB-C) |
| Switches / test points / inductors / crystal | 4 / 7 / 2 / 1 |

114 components, 45 unique parts, 1 DNP, 148 schematic nets (212 with KiCad's unconnected-pin nets), 64 no-connects, 5 sheets. MPN and LCSC coverage 100 %.

## Power Tree

```
edge 36 CONS_5V --[Q1 AO3401A P-FET, G = VBUS]--+
                                                 +--> +5V --> AS6C4008 x2, 74HCT x6, WS2812, CIClone sense
USB-C VBUS -----[D7 SS34]------------------------+      |
                                                        +--> U14 AP63203 buck 3.3 V/2 A (6.8 uH, 3x22 uF in, 2x22 uF out)
                                                        |      +--> +3V3: ESP32-S3, microSD, CP2102N
                                                        +--> U15 AP2112K-3.3 LDO (20 us) --> +3V3_RP: RP IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD,
                                                                                             VREG_VIN (+ VREG_AVDD via 33R) --> RP core SMPS 1.1 V (3.3 uH) -> DVDD
PWR_OK = 74HCT14( 0.82 x CONS_5V )   sensed before the FET: USB-powered cart in a dead console disables every output toward it
```
Regulator Vout: AP63203WU-7 fixed 3.3 V (`vref_source: fixed_suffix`), AP2112K-3.3 fixed 3.3 V. Both datasheet-verified (pin tables, Deep Review).

## Analyzer Verification

Component count: analyzer 114 = `design.py` 114 (113 placed + the DNP CIClone capacitor counted) - match. ERC: 0 violations with every check enabled. `check_nets.py`: 453/453 against `nes_cart.h`, `fujiversal-nes.h` (branch `nes-bringup`), the nesdev edge map, the decode equations and the edge footprint file.

### Component Pinout Verification (manufacturer PDFs, not KiCad symbols)

| Ref | Part | Verified against | Status |
|---|---|---|---|
| U1 | RP2354B QFN-80 | RP2350 datasheet Figure 3, p.16 (PDF 17) | Verified (datasheet): all 80 pins |
| U2, U3 | AS6C4008-55TIN | Alliance datasheet "PIN CONFIGURATION" p.2 | Verified (datasheet): A17 = 6, A18 = 9, OE# = 32 |
| U4 | 74HCT595 | Nexperia pin description p.5 | Verified (datasheet) |
| U5 | 74HCT253 | Nexperia 74HC_HCT253 pin description p.3 | Verified (datasheet): S0 = MIR0, S1 = MIR1 |
| U6 | 74HCT14 | TI pin diagram p.3 | Verified (datasheet) |
| U7 | CD74HCT20 | TI pin order (1A 1B 1C 1D -> 1Y 6, 2A 2B 2C 2D -> 2Y 8) | Verified (symbol + TI standard); datasheet download blocked, see limits |
| U8, U9 | 74HCT00, 74HCT32 | standard quad-gate order, TI/Nexperia | Verified (symbol + standard) |
| U10 | ATtiny13A-SS | Microchip p.2 pinout | Verified (datasheet) |
| U11 | ESP32-S3-WROOM-1 | Espressif pin definitions p.11-12 | Verified (datasheet) + `gen_sch.py` symbol check |
| U12 | CP2102N QFN28 | Silicon Labs 5.1 pin definitions p.28 | Verified (datasheet): VREGIN = VDD = 3V3 (regulator bypass), VBUS = sense |
| U13 | UMH3N | ROHM inner circuit p.1 (Farnell copy) | Verified (datasheet): 1 E1 2 B1 3 C2 4 E2 5 B2 6 C1 |
| U14 | AP63203WU | Diodes pin descriptions p.2 | Verified (datasheet) |
| U15 | AP2112K-3.3 | Diodes pin descriptions p.4 | Verified (datasheet) |
| Q1 | AO3401A | AOS p.1 top view | Verified (datasheet): 1 G 2 S 3 D |
| D1 | BAT54C | Diodes p.1 polarity diagram | Verified (datasheet figure), medium confidence |
| D3 | WS2812B-2020 | Worldsemi pin function p.2 | Verified (datasheet): 1 DO 2 GND 3 DI 4 VDD |
| J2 | TF-015 | SOFNG pin definition p.2 | Verified (datasheet) |
| J1 | NES 72-pin edge | nesdev table + NES-EWROM-01 footprint | Verified (reference geometry, `tools/audit/edge_orientation.py`) |
| J3 | USB-C 16P | KiCad receptacle symbol vs HRO footprint pad names | Consistency only (pad names A1..B12 standard) |
| Y1, D2, D4-D7, passives | | ABM8 CL 10 pF, KT-0603G VF, ESD5Z, SS34 | Verified (datasheet) where it matters; 2-pin passives skipped |

### Pinout Ambiguity

None open: every transistor/diode/regulator in a multi-variant package has an MPN and was checked against that MPN's datasheet.

### Connector Pin Table (edge, as the firmware sees it)

Edge 1-36 on F.Cu (label side), 37-72 on B.Cu, pin N under pin N+36; pin 1 is at the right looking at the label side with the fingers down. Full table in README.md; `check_nets.py` checks all 72 against `nes_cart.h`.

### Net Tracing

+5V, +3V3, +3V3_RP, DVDD, VREG_AVDD, CONS_5V, VBUS, PWR_OK/PWR_OK_N and every SRAM strobe were traced by `check_nets.py` from a fresh `kicad-cli` netlist (not from `design.py`), including the IOVDD-rail check on all eight IOVDD pins plus QSPI_IOVDD / USB_OTP_VDD / ADC_AVDD and VREG_VIN on the buck rail.

## Deep Review (28 findings, all evidence-verified)

**Power / rails**
- The whole RP2354B on the AP2112K (RP2350: "GPIOs are 5 V-tolerant (powered) and 3.3 V-failsafe (unpowered)", "tolerate voltages up to 5.5 V, provided IOVDD is powered to 3.3 V"; AP2112K start-up 20 us vs AP63203 soft-start 4 ms). ~60 mA, ~100 mW in the SOT-23-5 (Tj about +25 C over ambient).
- Supply order: only VREG_VIN + VREG_AVDD must rise together (p.444) - both on +3V3_RP.
- Console entry P-FET: Rds(on) < 60 mOhm at Vgs -4.5 V -> ~24 mV at 0.4 A; 74HCT VCC minimum 4.5 V satisfied even on a weak console rail.

**5 V glue**
- '595: outputs Hi-Z ("outputs to assume a high-impedance OFF-state") for 71-171 ms after power-on (POR_RC 1 uF/100k through the HCT14 Schmitt, VT- 0.9-2.45 V) and whenever PWR_OK is low; 100k pull-downs define every bit meanwhile.
- '253 second half carries CIRAM /CE; both halves tri-state on PWR_OK_N.
- Console sense: TI SN74HCT14 VT+ max 3.13 V at 4.5 V (0.70 x VCC); divider 0.82 gives 3.69 V at 4.5 V.
- PRG strobes (`tools/audit/timing_margins.py`): /WE rises <= 28 ns after M2 falls (CD74HCT20) vs the PROVISIONAL 30 ns 2A03 hold: +2 ns; write pulse ~300 ns vs tWP 45; data setup ~228 ns vs tDW 25; read /CE 58 + tACE 55 = 113 ns vs 330 ns budget. The first draft's path was 110 ns (-80 ns).
- Firmware-visible behaviour is unchanged: same '595 bit order, same decode truth table; the README decode table on the firmware side should mention the gating.

**Interfaces**
- RP VIH = 0.65 x IOVDD = 2.15 V against NMOS console outputs: thin but conventional; HCT inputs (2.0 V) have more room. Bring-up scope item.
- WS2812B on +5V, data at 3.3 V >= VIH 2.7 V.
- Activity LED ~2.1 mA; crystal CL 10.5 pF vs 10 pF rated.

**Sourcing (warning)**: AS6C4008-55TIN (C5569980) 0, -55STIN 5, every 74HCT253 0 at JLCPCB on 2026-10-01; CD74HCT20M96 460. CY62148ELL-45ZSXIT (C2952831, 50 pcs, 5 V TSOP-32) is a candidate alternate only after its A17/A18 pins are checked.

## Signal Analysis Review

- **Regulators:** U14 AP63203 (switching, +5V -> +3V3, fixed), U15 AP2112K (LDO, +5V -> +3V3_RP, fixed), RP2350 internal SMPS (DVDD 1.1 V, 3.3 uH, FB = DVDD).
- **Dividers:** R10/R11 22k/100k VSENSE 0.820 (SPICE 2.70 V at 3.3 V test source; 4.10 V at 5 V); R19/R20 22k/47k VBUS_SNS 0.681 (3.41 V at 5 V, CP2102N VBUS pin).
- **RC:** R14/C33 10k/1 uF S3 EN delay 15.9 Hz (SPICE 15.88 Hz); POR_RC 100k/1 uF (cap to +5V; not pattern-matched as a filter, computed in `por_window.py`).
- **Crystal:** 12 MHz ABM8-272-T3, 2 x 15 pF, 1k series on XOUT, CL 10.5 pF (SPICE).
- **Protection:** ESD5Z5.0 on D+, D-, VBUS at the USB-C; CC 5.1k x2 (UFP). No ESD on the edge (console bus) or microSD (inside the shell) - accepted.
- **LEDs:** D2 green 1k from the '595 (2.1 mA); D3 WS2812B-2020 on +5V with 330R data series.
- **Transistors:** Q1 P-FET console switch; U13 dual pre-biased NPN auto-program (DevKitC-1 pattern, verified).
- **Differential pairs:** RP_USB_DP/DM (27R series, RP internal termination), USB_DP/DM to the S3 host pads, UBRG_DP/DM (CP2102N, ESD).
- **Simulation:** ngspice verified 15 subcircuits, 15 pass, 0 warn/fail/skip (two dividers, one RC, crystal load, three protection devices, six decoupling networks, two inrush models).

### Decoupling

| Rail | Caps | Notes |
|---|---|---|
| +3V3_RP | 11 x 100 nF (one per RP supply pin) + 4.7 uF VREG_VIN + 10 uF + 1 uF LDO out | PDN z_min 19 mOhm at 6.8 MHz (SPICE, first run) |
| +3V3 | 2 x 22 uF buck out, 22 uF + 100 nF S3, 10 uF SD, 4.7 uF + 100 nF CP2102N | |
| DVDD | 3 x 100 nF + 4.7 uF | core SMPS output |
| +5V | 3 x 22 uF, 100 nF buck in, 10 uF logic bulk, 100 nF per SRAM and per 74HCT (6), 100 nF WS2812, 1 uF LDO in | |
| VBUS / CONS_5V | 1 uF + 100 nF / 100 nF | |

## Power Analysis

- **Budget (analyzer estimate):** +3V3 ~250 mA typical (S3 240, CP2102N) with WiFi bursts to ~500 mA; +3V3_RP ~60 mA (RP I/O + core-regulator input); +5V: SRAMs 2 x 30 mA active, HCT, LED, plus the buck input (~0.35 A at WiFi peaks). Console-only: ~0.5 A peak from the NES 5 V rail (bring-up item: the NES 7805's headroom).
- **Sequencing:** no EN chains; buck EN = VIN, LDO EN = VIN; PWR_OK is the only gate and it is hardware.
- **Inrush:** 3 x 22 uF on +5V charged through the P-FET body diode / SS34 at console or cable insertion; buck output 2 x 22 uF with 4 ms soft-start.
- **Derating:** 22 uF 25 V X5R on 5 V, 10 uF 10 V on 3.3 V, 4.7 uF 16 V - fine. R19 47k 0603 "over-designed" (VD-004) - ignored, 0603 is the board's passive size.

## PCB Layout, Cross-Domain, EMC, Thermal, Gerbers (Part 2)

**Board:** `FujiNet-NES-Rev0.kicad_pcb`, generated by `tools/gen_pcb.py` + `tools/placement.py`, routed by the pipeline in `tools/build_all.sh` (locked pre-routes, Freerouting 2.4.1 x 8 passes, the A* finisher with cost-aware rip-up, DRC-gated tidy, GND stitching). Analyzer run `analysis/2026-10-04_0338`. 117 footprints (114 parts + 3 fiducials), all on the label side; 2084 track segments (7.13 m), 766 vias (0.6/0.3; 0.5/0.25 under the RP), 221 of them GND stitching; 6 layers, 1.2 mm.

**Gates:** KiCad DRC (`--refill-zones --schematic-parity --severity-error`): **0 errors, 0 unconnected, 0 schematic-parity issues**. Warnings: 199 solder-mask bridges (the fingers' shared mask window, by design), 78 silkscreen overlaps/silk-over-copper (reference designators on dense 0603 rows), 11 dangling track stubs (harmless router leftovers). ERC: 0. `tools/check_nets.py`: 453/453 against the firmware headers. Freerouting's own "unrouted" counter is inflated by zone-connected items; KiCad's unconnected count is the one quoted.

### Analyzer runs (kicad-happy 2.2.1)

| Analyzer | Run | Result |
|---|---|---|
| `analyze_pcb.py --full --proximity` | yes | 64 findings (31 error, 8 warning, 25 info); routing complete, 0 unrouted nets |
| `cross_analysis.py` | yes | 1 warning (PS-002, below) |
| `analyze_emc.py` | yes | 72 findings (6 error, 55 warning, 11 info) |
| `analyze_thermal.py` | yes | score 97/100; 1 warning (TS-003, below), 7 info |
| `simulate_subcircuits.py` (ngspice) | yes | re-run on the same schematic: crystal load, VSENSE, VBUS_SNS, POR RC as in Part 1 |
| `analyze_gerbers.py` on `exports/jlcpcb/FujiNet-NES-Rev0-gerbers.zip` | yes | complete 6-layer set (13 layers + PTH/NPTH drill), 100.1 x 110.1 mm from the job file; 2 warnings (below) |
| lifecycle audit | no | no distributor API keys (unchanged from Part 1) |

### Layout findings and dispositions

The PCB, cross-domain, EMC, thermal and gerber analyzers raised 147 findings between them. Everything rated high/error is listed; warnings that led to a change are listed; the rest are grouped.

| Finding | Disposition |
|---|---|
| VM-001 5 V / 3.3 V crossing x44, RS-001, PU-001 CHREN, DO-DET, CG-AUD J1, EP-AUD, IO-001/002 J1 | Same false positives as Part 1 (the direct 5 V bus is the design; J1 is the console's connector) |
| FD-001 no fiducials | **Fixed**: three 1 mm / 2 mm-mask fiducials (FID1-3, board-only footprints) at the body corners, outside the shell-post areas |
| KO-001 vias inside `shell_post_*` keep-outs x46 | False positive: the analyzer tests the keep-out's bounding box; the shell-post areas are circles and KiCad's DRC (which tests the real shape) is clean |
| VP-001 via in pad | **Fixed in the tools**: the finisher keeps vias 0.2 mm off its own pads, `stitch_gnd.py` keeps its grid off every pad. Left on the board: the thermal via arrays under the RP2354B and CP2102N exposed pads (intended) and two Freerouting vias in D7 pad 1 (+5V) and R15 pad 1 (+3V3) -- ask for filled/capped vias or accept a small solder-wicking risk on those two |
| TV-001 CP2102N exposed pad 4/9 vias | **Fixed in the tool**: `fanout.py` plans a 3x3 array; on the routed board only the vias DRC accepts are kept (9 of 9 on the final board: TV-001 now reports U12 adequate) |
| RP-001 no stitching via at layer transitions x20, BE-002 71 % edge ground | **Mitigated**: `tools/stitch_gnd.py` adds a 4 mm GND via grid plus a row 1.2 mm inside every body edge, each via kept only if DRC accepts it (221 vias on the final board; vias never in or against a pad) |
| J1 inside the tab keep-outs | By design: the finger pads are allowed on the tab; tracks, vias and pour are not |
| DP-001 USB_DP/USB_DM skew 10.4 mm (57 ps), DP-003 layer changes, DP-004 outer layers | Accepted: every USB endpoint on this board is Full-Speed (RP2350, ESP32-S3, CP2102N: 12 Mb/s, 83 ns bit time). The analyzer applies the High-Speed 25 ps budget; 57 ps is 0.07 % of a bit. Impedance is not controlled on this stack-up in any case (0.25 mm tracks) |
| GP-001 reference-plane coverage 77-86 % (PD0, PD2, PA13, CIRAM_*, SD_DAT2), PS-002 "GND plane has 3 islands" | Partly real: the "3 islands" are the three GND layers (In1 plane, F and B pours) counted separately, and In1 is one solid plane. Signals on In3/B.Cu reference In4, which is split into +3V3 / +5V / +3V3_RP / DVDD areas; their return path closes through the decoupling capacitors at every IC and the stitching vias. Accepted for a 1.8 MHz bus |
| TS-003 AP2112K Tj 96 C (0.286 W assumed), TP-001 MLCCs near it | Not supported by the datasheets: RP2350 draws 11.0 mA on VREG_VIN running CoreMark at 150 MHz and 14.7 mA in `hello_usb` (RP2350 datasheet Table 1446); its core regulator is a switcher, so the LDO never sees the core current. With the bus-driving IOVDD load this is tens of mA, not 170. At a pessimistic 150 mA: 0.26 W x 184 C/W (AP2112 datasheet, SOT-25) = +47 C. Keep the SOT-23-5 |
| DC-001 SRAM decoupling 6.4 mm from U2/U3 | Measured to the package centre; C22/C23 sit 1.3 mm from the VCC pin (pin 8) of each TSOP. False positive |
| DC-002 no decoupling near U13 | UMH3N is a transistor pair, no supply pin. False positive |
| PM-002 J2 0.2 mm from the edge, J3, U11 | microSD and USB-C are edge-mounted by design; the ESP32 antenna overhang is the module's keep-out |
| CC-002 0.15 mm segments on CD1, ROMSEL_N, SRAM_EN, UART_* | Freerouting neck-downs near fine-pitch pads; above JLCPCB's 0.09 mm minimum. Accepted |
| CK-001 CIC_CLK on an outer layer, CK-003 SD_SCK near J2 | CIC_CLK is the console's 4 MHz lockout clock on a finger (the CIClone is DNP); SD_SCK ends at the card slot it clocks |
| XT-001 CA5/CA6, CA4/CA5 parallel within 0.5 mm | 1.8 MHz address lines; accepted |
| TE-001 test points 6/208 nets | By design: SWCLK, SWDIO, GND, RUN, M2, SR_SPARE |
| SW-001 / EE-00x buck harmonics, CERT-001, WL-001, OR-001, DFM-001 (100 x 110 mm) | Informational |

### Gerbers

- GR-002 "height varies by 16.7 mm across copper/edge layers": the copper layers stop short of the top edge under the ESP32-S3 antenna keep-out while Edge.Cuts does not -- expected.
- GR-004 front paste 591 flashes vs 1395 copper pads (42 %): the difference is vias, fingers (no paste) and the exposed-pad via arrays -- expected.
- Fab notes for the order: 6 layers, 1.2 mm, ENIG or hard gold on the fingers with a 30-45 degree bevel; 0.6/0.3 mm vias (0.5/0.25 under the RP); request filled-and-capped vias if the two via-in-pad spots in the table above are a concern.

### Mechanical

Outline, finger geometry, notches and holes are the measured NES-EWROM-01 figures (Part 1). The shell (`case/FujiNet-NES-Shell.scad`) compiles in OpenSCAD 2025 with the generated `case/board-anchors.scad`; its Game Pak envelope and post positions are VERIFY items (`case/case-spec.md`).

## Quality & Manufacturing

- **Assembly:** 131 SMD placements, 0 THT; 2 hard (QFN-80 0.4 mm, QFN-28), 98 medium, 31 easy; 0603 passives; two TSOP-I-32 at 0.5 mm pitch. JLCPCB-assemblable except the consigned parts above.
- **Sourcing:** 100 % MPN + LCSC. Out of stock at JLC: AS6C4008-55TIN, 74HCT253D,653 / CD74HCT253M. The CIClone and its capacitor are DNP (excluded from the JLC BOM and CPL).
- **Test coverage:** SWCLK, SWDIO, GND, RUN, M2, SR_SPARE, CIC /RESET on pads; CIClone ISP reaches the fingers.
- **Lifecycle audit:** not performed (no distributor API keys); LCSC stock was queried manually.

## False Positives / Reviewer Overrides

| Finding | Count | Disposition |
|---|---|---|
| VM-001 5 V / 3.3 V domain crossing without level shifter | 44 | Intentional: RP2350 5 V-tolerant pads (now powered first by the LDO); 3.3 V outputs into 74HCT (VIH 2.0 V) and AS6C4008 (VIH 2.2 V) are in spec |
| RS-001 PWR_OK / PWR_OK_N / VBUS_SNS "no declared source" | 3 | Logic outputs and a divider node, not rails |
| PU-001 U12 CHREN missing pull-up | 1 | Charger-detect output, open as in the DevKitC-1 reference |
| DO-DET "missing decoupling on PWR_OK" | 4 | Same naming confusion |
| CG-AUD J1 35:1 signal-to-ground | 1 | Console-defined pinout |
| EP-AUD J1, J2 no ESD | 2 | Console bus / inside the shell |
| ERC-style "XIN has no driver" (analyzer) | 1 | Crystal; KiCad ERC is clean |
| Cross-domain SR_SCK/SR_RCK/SR_SER "needs level shifter" | 3 | 3.3 V into 74HCT595 (VIH 2.0 V) |

These are listed in `.kicad-happy.json` as suppressions (the schematic analyzer reports them regardless; the PCB/EMC/thermal analyzers honour the file).

## Not Performed / Review Limits

- PCB, cross-domain, EMC, thermal and gerber analyses: Part 2 above.
- Impedance control: none (JLCPCB 6-layer standard stack-up, 0.2-0.25 mm tracks); all buses are 1.8 MHz / 5.4 MHz NMOS levels, USB is Full-Speed.
- Lifecycle audit: no API keys.
- CD74HCT20 and 74HCT00/32 datasheets: TI's and Nexperia's servers refused the download; pin order taken from the KiCad symbols and the universal 74xx standard (low risk).
- BAT54C: verified from the package drawing, not a pin table.
- The 2A03 write-data hold (30 ns) is the firmware's PROVISIONAL figure; nothing in CAD can settle it.
- Structured datasheet extractions (`datasheets/extracted/`) were not produced; all pin-level claims above are direct PDF reads with page numbers in `analysis/deep_review.json`.

## Verdict (layout)

Ready to order as a first prototype. Routing is complete: KiCad DRC reports 0 errors, 0 unconnected items and 0 schematic-parity issues; ERC is clean; `check_nets.py` passes 453/453 against the firmware headers. No analyzer finding is an unresolved design error: each is fixed, a documented false positive, or an accepted trade-off in the table above. Open items are the Part 1 bench measurements, the two consigned parts, the shell VERIFY items, and the two via-in-pad spots (fab option).

Layout notes worth keeping for Rev1: the RP2354B's 0.4 mm-pitch pin rows were the routing bottleneck. Supply-pin fan-out vias placed at the escape-lane ends left no room for 3-4 signal pins between them (pins 25-28), so `fanout.FAR_VIA` moves those vias out. The final links were closed at 0.15 mm / 0.12 mm (`finish_route.py --neck`, within JLCPCB's 0.09 mm minimum). The CHR-side glue ('32, '253) had to leave the band between the west fingers and the CHR SRAM.

## Verdict (schematic)

Ready for layout. No critical or warning-level design errors remain; the two warnings are sourcing (consign the SRAMs and the mux) and a bench measurement (write-data hold) that the one-gate M2-qualified /WE already treats as well as discrete logic can.
