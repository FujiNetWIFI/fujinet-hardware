# FujiNet-StudioII Rev0: design review

**Project:** FujiNet-StudioII Rev0. KiCad 10; root + 5 wired sheets; a 4-layer PCB, 90.9 x 111.5 mm.
**Date:** 2026-10-11 (kicad-happy 2.2.1, analysis run `2026-10-11_1211`).
**Board:** the routed board in this folder: run S7 plus five fixes made after it (the antenna keep-out, the USBLC6 corner and its 100 nF, the USB-C at the edge, the saved zone fills) in `docs/floorplan-study.md` (the second pass,
with the ESP32-S3 on the cart).

Every number below comes from a script in this project and can be re-run:

| Script | What it checks |
|---|---|
| `tools/check_nets.py`, `tools/check_glue.py` | the netlist and the glue equations against the firmware: `s2_cart.h`, `s2_glue_*()`, `fujiversal-studio2.h` |
| `tools/audit/edge_orientation.py` | the edge footprint against FliP's board, EJK's pinout and the original board |
| `tools/audit/margins.py` | logic levels, the power mux on each source, PWR_OK, pull-ups, both regulators, the S3 rail, WS2812, CP2102N, crystal, LED |
| `tools/audit/layout_checks.py` | the layout's datasheet claims, measured on the copper |
| `tools/audit/check_fab.py`, `check_gerbers.py` | the JLCPCB package and its gerbers |
| `tools/audit/sourcing.py` | JLCPCB / LCSC stock and LCSC's lifecycle flag |
| `tools/audit/make_deep_review.py` | the datasheet-cited findings, through kicad-happy's evidence gate |

`tools/audit/run_sch_audit.sh` and `tools/audit/run_pcb_audit.sh` run the kicad-happy analyzers.

## Verdict

**Ready to order as a bring-up prototype at JLCPCB.** No blockers.

- KiCad DRC with schematic parity, all severities: **0 violations, 0 unconnected, 0 parity issues, on the saved zone fills (what the gerbers plot)**.
- **Schematic:**
  - ERC 0 at all severities;
  - netlist parity with `design.py`: 97 / 97 nets;
  - `check_nets.py`: 364 checks, 0 failed, 1 warning (a firmware pin-map follow-up, below);
  - `check_glue.py`: 16 / 16;
  - `edge_orientation.py`: all pass.
- `layout_checks.py`: 65 / 65 claims hold.
- **Fab package:** `check_fab.py` 10 / 10; `check_gerbers.py` 0 failures.
- **Stock:** all 44 assembled BOM lines are in JLCPCB stock for 5 boards.
- **Reproducible:** `LAYOUT=1 tools/build_all.sh` regenerates and re-routes the board from scratch with every
  gate above green (run S8 in `floorplan-study.md`).
- **Deep review:** 32 datasheet- or script-cited findings, 32 verified, 0 quarantined.
- **Pinouts:** every part's pinout checked against its datasheet, with no pin or pad numbering
  mismatch.

**This pass fixes the earlier review's open questions:**
- **The glue's supply.** The SS34 left the 74HCT glue at 4.3 V on USB. A TPS2116 power mux replaces
  the P-FET / SS34 OR, and +5V now stays at or above 4.72 V on either source.
- **USB ESD.** A 3.5 pF USBLC6-2SC6 replaces the 80 pF ESD5Z diodes.

Three **warnings** remain. None stops the board working:

| Severity | Issue | Where |
|---|---|---|
| WARNING | With no USB, the console's 7805 feeds the whole cart, the S3's WiFi included: ~140 mA average, ~470 mA peak. Its headroom is unmeasured. | [Power](#power) |
| WARNING | The S3 forces the RP's RUN / BOOTSEL on IO4 / IO5, but `fujiversal-studio2.h` does not declare those pins yet. | [Open questions](#open-questions) |
| WARNING | The RP2350 core inductor (L1, AOTA-B201610S3R3) had 24 left at JLCPCB and none at LCSC on 2026-10-11. | [Lifecycle](#lifecycle) |

Before ordering, do the README's *Before ordering* checks:
- the 1:1 edge overlay against a real cartridge;
- stock on the order day;
- the JLC placement preview;
- a printed shell for the taller board.

## Overview

The FujiNet for the RCA Studio II is one cartridge with two MCUs.

- **The RP2354B serves the CDP1802 bus in software.**
  - The console's address lines, TPA and /MRD reach GPIO0-9 through 330R.
  - A 74HCT541 drives D0-D7 at 5 V CMOS levels.
  - A 74HCT32 and a 74HCT1G02 gate the '541 and CART CS with PWR_OK, which comes from the console's
    5 V through a 74HCT14.
- **The ESP32-S3-WROOM-1-N16R8 is the FujiNet** (`fujiversal-studio2.h`).
  - It is the RP's USB host over an on-board USB link.
  - It carries a microSD (SPI) and a WS2812 status light.
  - A CP2102N on the USB-C flashes it and carries its console.
  - It drives the RP's RUN and BOOTSEL, so it can re-flash the RP.
- **Power.** A TPS2116 mux selects USB VBUS first and the console's 5 V second. Its output, +5V, feeds:
  - the glue;
  - the RP's AP2112K LDO (+3V3);
  - the S3 side's AP63203 buck (+3V3_S3);
  - the WS2812.
- **Board.** FliP's RCA Studio II multicart v5.1 outline from the insertion edge up.
  - The edge: 22 hard-gold fingers on B.Cu, two post holes, the side notches, a 23.5 mm parts-free
    band. Every part is on F.Cu.
  - Above that, the board is 28 mm taller for the S3 half.

## Previous review delta

The previous review covered the RP-only board, with the S3 on a separate board (run `2026-10-11_0912`).

| Run | What it covered |
|---|---|
| `2026-10-11_0832` | The RP-only schematic, revised for its board |
| `2026-10-11_0912` | The RP-only board (V4 in `floorplan-study.md`) |
| `2026-10-11_0957` | This schematic: the ESP32-S3 on the cart |
| `2026-10-11_1211` | This board |

**The circuit:**
- **New sheets.** `fujinet` holds the S3, microSD, WS2812, EN RC and buttons, ported from
  FujiNet-ChannelF Rev0. `usb` holds the USB-C, USBLC6, CP2102N and auto-program pair.
- **`rp-core`.** The S3's RUN / BOOTSEL controls (1k each) are added. RESET now resets both MCUs
  through a BAT54C, and the RP's USB goes to the S3 instead of a receptacle.
- **`power`.** The TPS2116 mux replaces the AO3401A + SS34 + 4.7k, and the AP63203 buck is added.
- **Unchanged:** the cart-bus sheet (the edge, glue, '541, pull-ups and PWR_OK).

**The board:**
- **Outline.** It is 28 mm taller, with rounded top corners in place of FliP's chamfers.
- **New top band.** The S3 sits along the new top edge with its antenna keep-out, beside the USB-C,
  the CP2102N and the microSD.
- **In2.** The base is now +5V, with +3V3 / +3V3_S3 / CONS_5V islands.
- **The RP half.** The core, the regulator graft, the rings, the twist and the fans are as in V4.
- **Routing.** The board was re-routed from scratch.

**The earlier review's findings:**
- **Fixed:** the USB-corner VCC warning (the mux) and the ESD capacitance (the USBLC6).
- **Still open:** the AOTA inductor's stock and TPA on real consoles.
- **New:** the 7805's load with WiFi, and the S3 pin-map follow-up.

## Component summary

| Type | Count |
|---|---|
| Capacitors | 46 |
| Resistors (+ 1 four-resistor network) | 36 + 1 |
| ICs / modules | 12: RP2354B, ESP32-S3-WROOM-1, SN74HCT541, SN74HCT32, SN74HCT14, 74HCT1G02, TPS2116, AP63203, AP2112K-3.3, CP2102N, USBLC6-2SC6, UMH3N |
| Diode / LEDs | 1 (BAT54C) / 2 (WS2812B-2020, red) |
| Switches | 4: TS-1187A for S3 EN, BOOTSEL, RESET, S3 BOOT |
| Connectors | 4: the Studio II edge, USB-C, microSD, the debug UART header J2 (not fitted) |
| Crystal, inductors | 12 MHz ABM8-272-T3; 3.3 uH AOTA (the RP core), 6.8 uH SWPA4030 (the buck) |
| Test pads | 17 (bare copper) |

- **Assembly:** JLCPCB places 107 parts.
  - J1 is the board's own edge, and J2 is not fitted (DNP).
  - The board also carries two 8.128 mm NPTH post holes and three fiducials.
- **Schematic:** 175 nets including unnamed ones (97 named), 358 wires, 78 no-connects.
- **Sourcing:** every part has an MPN, a manufacturer and an LCSC code.
  - Parts cost about USD 15.71 per board at the 5-board quantity, before assembly fees.
  - Details are in `docs/sourcing.md`.

## Power tree

```
USB-C VBUS ── USBLC6 ── TPS2116 VIN1 (priority: MODE = VIN1, PR1 = VBUS x 10k / 43k) ─┐
console 5 V (edge 15) = CONS_5V ── TPS2116 VIN2 ───────────────────────────────────────┴─ +5V (>= 4.72 V)
     ├─ 22k / 100k ─ VSENSE ─ 74HCT14 ─ PWR_OK_N, PWR_OK          ├─ 74HCT541, '32, '14, '1G02
     └─ 100k / 100k ─ VSENSE_ADC (GPIO40)                         ├─ WS2812B-2020
                                                                  ├─ AP2112K-3.3 (EN = +5V) ─ +3V3: every RP2354B supply pin
                                                                  │      └─ RP2354B core regulator, L1 3.3 uH ─ DVDD 1.1 V
                                                                  └─ AP63203 2 A buck, L2 6.8 uH ─ +3V3_S3: ESP32-S3, CP2102N, microSD
```

- Both regulators are fixed-output parts, so there are no feedback dividers to check.
- The analyzer found the AP2112K as an LDO and the AP63203 as a switching regulator (PR-DET).
- The mux's reverse-current blocking keeps either source from back-feeding the other.

## Analyzer verification

- **Component count.** The analyzer counts 126 schematic parts, and `cross_verify` matches all 126
  on the board.
  - Its orphans are the board-only holes H1 and H2 and the fiducials FID1-3.
  - Its one DNP note is J2.
- **Netlist.** The `kicad-cli` netlist equals `design.py` net for net, names included (97 / 97).
  KiCad DRC finds 0 schematic-parity issues.
- **Gerbers.** `analyze_gerbers` finds all 11 expected layers and both drill files (714 holes). Its two warnings are expected:
  - GR-002: the copper's extent is 9.8 mm short of the outline. In1 / In2 stop at the finger field, and nothing is in the antenna keep-out.
  - GR-004: 41 % of the copper flashes carry paste. Vias, the 17 test pads and the fingers take none.

  `check_gerbers.py` checks the zip itself against `edge_geom.py`. Its check 9 tests every plated hole against the plotted inner layers: none sits in a pour of another net.

### Pinouts against the datasheets

The symbol pin numbers, footprint pad numbers and nets were checked against the manufacturer's PDF
in `datasheets/`. This covers every part with more than two pins, and every polarized part.
**Verified (datasheet)** means the PDF's pin table or package drawing was read.

| Ref | Part | Package | Datasheet (page) | Status |
|---|---|---|---|---|
| U1 | RP2354B | QFN-80 | pinout figure p17, pin descriptions ch. 1; all 81 pads incl. EP = GND | Verified (datasheet) |
| U6 | ESP32-S3-WROOM-1-N16R8 | module | pin definitions p10-13: 1 GND, 2 3V3, 3 EN, 4 IO4, 5 IO5, 13 IO19, 14 IO20, 25 IO48, 27 IO0, 31-35 IO38-42, 36 RXD0, 37 TXD0, 40 / 41 GND | Verified (datasheet) |
| U2 | SN74HCT541PWR | TSSOP-20 | pin configuration p3 | Verified (datasheet) |
| U4, U5 | SN74HCT32DR, SN74HCT14DR | SOIC-14 | pin configuration p3 | Verified (datasheet) |
| U3 | 74HCT1G02GV,125 (Nexperia) | SOT-753 | pinning p2 | Verified (datasheet) |
| U10 | TPS2116DRLR | SOT-583 (DRL) | pin functions p3: 1 GND, 2 / 7 VOUT, 3 VIN1, 4 PR1, 5 MODE, 6 VIN2, 8 ST. `gen_sch.py` asserts the stock symbol against this table. | Verified (datasheet) |
| U11 | AP63203WU-7 | TSOT-23-6 | pin descriptions p2: 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST | Verified (datasheet) |
| U12 | AP2112K-3.3TRG1 | SOT-23-5 | pin descriptions p2: 1 VIN, 2 GND, 3 EN, 5 VOUT | Verified (datasheet) |
| U8 | CP2102N-A02-GQFN28R | QFN-28 | QFN28 pin table: 3 GND, 4 D+, 5 D-, 6 VDD, 7 VREGIN, 8 VBUS, 9 RSTb, 23 CTS, 24 RTS, 25 RXD, 26 TXD, 28 DTR, EP GND | Verified (datasheet) |
| U7 | USBLC6-2SC6 | SOT-23-6 | functional diagram p1: I/O1 = 1 / 6 and I/O2 = 3 / 4 (joined inside), 2 GND, 5 VBUS | Verified (datasheet) |
| U9 | UMH3N (JSCJ) | SOT-363 | equivalent circuit p1: 1 E1, 2 B1, 3 C2, 4 E2, 5 B2, 6 C1 | Verified (datasheet) |
| D2 | BAT54C,215 (Nexperia) | SOT-23 | pinning p2: 1 A1, 2 A2, 3 common cathode | Verified (datasheet) |
| D3 | WS2812B-2020-V6 | 2020 | pin table p2: 1 DOUT, 2 GND, 3 DIN, 4 VDD | Verified (datasheet) |
| D1 | KT-0603R | 0603 LED | package drawing p2 | Verified by function (the cathode to GND; the CPL matched cathode-to-cathode) |
| Y1 | ABM8-272-T3 | 3225 4-pad | p2: crystal between 1 and 3, 2 / 4 to GND | Verified (datasheet) |
| L1, L2 | AOTA-B201610S3R3, SWPA4030S6R8MT | 2016, 4030 | dimensions; non-polar | Verified (datasheet) |
| J3 | TF-015 (SOFNG) | microSD | pin definition: 1 DAT2, 2 CD/DAT3, 3 CMD, 4 VDD, 5 CLK, 6 VSS, 7 DAT0, 8 DAT1, 9 CD (closes to the shell with a card in) | Verified (datasheet) |
| J4 | TYPE-C-31-M-12 | 16P | drawing p1 | Verified (datasheet) |
| RN1 | 4D03WGJ0103T5E | 4 x 0603 | p4 | Verified (datasheet) |
| SW1-SW4 | TS-1187A-B-A-B | 4-pad SMD | p1: A-B and C-D joined inside, the switch between them; our pad 1 = A / B, pad 2 = C / D | Verified (datasheet) |
| J2 | PZ254V-11-03P | 1x03 2.54 mm | p1; DNP | Verified (datasheet) |
| J1 | the Studio II edge | 22 contacts | `edge_orientation.py` against FliP's board file and gerbers, EJK's pinout and the original board | Verified (three sources) |

**Datasheets.**
- All 41 MPNs have the BOM maker's own PDF in `datasheets/`; `manifest.json` lists each source.
- The file names are the MPN sanitized the way kicad-happy's gate looks them up (`74HCT1G02GV_125.pdf`,
  `BAT54C_215.pdf`). That clears the "partial" flags of the earlier review.

## Deep review

`tools/audit/make_deep_review.py` writes `analysis/deep_review.json`: 32 findings, each citing a datasheet page (quoted, and checked by kicad-happy's `deep_review_gate`) or a script result from this project. The gate verifies all 32 and quarantines none.

| Category | Findings | What they establish |
|---|---|---|
| power | 5 | The mux's output on either source and its priority, reverse blocking, both regulators' headroom; the 7805 load (warning) |
| layout | 6 | Raspberry Pi's regulator corner and its cut-outs, VREG_AVDD, the buck's input loop, the address twist and data fan-in, the plotted inner layers short nothing |
| mcu | 3 | The S3's supply, EN and strapping; the console into the RP's fault-tolerant pads; the RUN / BOOTSEL pin map (warning) |
| esd | 2 | The USBLC6's flow-through routing; the 100 nF ST draws at its VBUS pin, beside the package |
| level-shift, logic | 4 | The '541's CMOS levels into the 1802, no clamp current from the console's 5 V, PWR_OK, the /DRIVE / /CLAIM pull-ups |
| decoupling, thermal | 4 | Supply rings and straight-out capacitors; exposed-pad via grids (RP2354B, CP2102N) |
| usb, interface, led, clock, rf, connector | 8 | The 27R placement, pair lengths, the CP2102N's VBUS sense and RSTb, the WS2812 levels, the crystal load, the antenna keep-out, the edge and the firmware contract |

The two warnings (the 7805's load, the pin map) are in the verdict's table, with L1's stock.

## Signal analysis

- **SPICE** (`simulate_subcircuits.py` with `extract_parasitics.py`, ngspice): 15 / 15 subcircuits
  pass.
  - **The EN delay:** the S3's 10k / 1 uF at 15.9 Hz.
  - **Four dividers:**
    - PWR_OK's 22k / 100k at 0.82;
    - the ADC's 100k / 100k at 0.5;
    - the CP2102N's VBUS sense 22k / 47k (3.41 V at 5 V);
    - the mux's priority divider 33k / 10k (1.16 V at 5 V against VREF 0.92-1.08 V).
  - **The crystal** (CL 10.5 pF).
  - **Seven decoupling groups:** |Z| at 1 MHz 3-34 mOhm on the IC rails, 88 mOhm on VBUS.
  - **Both 3.3 V inrushes.**
- **Level translation (VM-001, 10).** False positives, as before. The RP_D0-7 / DRIVE_N / CLAIM_N
  nets are RP outputs into TTL-level HCT inputs (VIH 2.0 V). GPIO24 / 25 are fault-tolerant pads
  (5.5 V with IOVDD at 3.3 V), and IOVDD rises with +5V. The 74HCT parts are the level shifters, by
  design.
- **RS-001 (4):** PWR_OK / PWR_OK_N (logic outputs) and VBUS_PR / VBUS_SNS (divider nodes) are named
  like rails. None is a supply.
- **PU-001:** the CP2102N's CHREN is the battery-charger detection output, unused and left open as on
  Channel F. Waived in `.kicad-happy.json`.
- **LB-001 (8):** the inter-sheet signals (S3_EN, the UART, the USB pair, RUN / BOOTSEL_CTL) are
  hierarchical labels joined on the root. That is by design.
- **Protection (EP-AUD, 4):**
  - USB-C D+ / D- / VBUS are behind the USBLC6; CC1 / CC2 carry only the 5.1k Rd.
  - The edge has none, as on every Studio II cartridge: it is the console's own bus. The RP is behind
    330R, and the console sees only HCT inputs and outputs.
  - J2 (not fitted) is a 3.3 V bring-up UART.
- **The wireless module (WL-001 / CERT-001):** the ESP32-S3-WROOM-1 is a pre-certified module. Its
  antenna sits at the board edge with its keep-out empty (see [PCB layout](#pcb-layout)).
- **LED (LA-AUD):** 1.3 mA from GPIO27 through 1k. The WS2812's data runs through 330R from IO48.

## Power

- **Budget** (`margins.py`): ~140 mA average and ~470 mA peak on +5V.
  - The RP2354B draws ~45 mA and the glue ~4 mA.
  - At the peak, the S3 side draws 465 mA at 3.3 V through the buck: WiFi TX at 20.5 dBm, a microSD
    write and the CP2102N.
  - The WS2812 adds up to 36 mA.
- **The mux.** At its 60 mOhm maximum, the TPS2116 drops 28 mV at the peak.
  - +5V is >= 4.72 V on either source's low corner, inside the 74HCT range: margin 0.22 V.
  - VIN is <= 5.25 V on either source's high corner, under its 5.5 V.
  - USB's 4.75 V minimum always beats the 4.64 V priority threshold.
  - Switchover is break-before-make, ~8 us at 5 V; +5V's ~55 uF holds the cart through it.
- **The console's 7805 (warning).** With no USB, it supplies the whole cart: ~140 mA average and
  ~470 mA peak in WiFi bursts.
  - The Studio II's own load and its 7805's spare capacity are unmeasured.
  - Bring-up step 2 scopes CONS_5V under WiFi bursts. If it sags, run the cart from USB-C: the mux
    then takes nothing from the console.
- **Regulators.**
  - The AP2112K gets >= 4.72 V in (1.27 V of headroom at ~50 mA).
  - The AP63203 gets >= 4.72 V against its 3.8 V minimum, and its 2 A rating against the S3 side's
    465 mA peak (the module asks for a supply good for 0.5 A).
- **Thermal** (`analyze_thermal`): score 100 / 100.
  - The analyzer assessed only U12. It assumed 168 mA out of the AP2112K (Tj 96 °C, TS-003, waived). The LDO's real load is the RP2354B, the LED and the pull-ups: ~50 mA, so 85 mW. That gives Tj 41 °C at 25 °C ambient, 66 °C at 50 °C inside the shell (184 °C/W).
  - TP-001 (4, info): MLCCs within 10 mm of U12. Moot at the real dissipation.
  - The exposed pads: U1 has 11 GND vias, U6 12, U8 10 (TV-001).
- **Sequencing.**
  - The AP2112K's EN is on +5V, so the RP's IOVDD follows +5V up.
  - The buck waits out UVLO and a 4 ms soft start. The S3's EN delay (10k / 1 uF) then holds it in
    reset ~10 ms more.
  - PWR_OK gates both glue outputs: with the console off, nothing is driven into it (`check_glue.py`:
    8 / 8 silent).

## PCB layout

`docs/floorplan-study.md` has the floorplan, the decisions and the routing runs (V1-V4 for the RP
cart, S1-S7 for this board).

| | |
|---|---|
| Outline | FliP's multicart v5.1 from the insertion edge up: 90.912 mm wide, no tab, two 8.128 mm NPTH post holes 68.58 mm in, half-round notches (r 1.83 mm) 20.83 mm in. Then 28 mm taller: 111.49 mm overall, rounded top corners (r 3). |
| Stack-up | JLC04161H-7628, 1.6 mm. **F.Cu:** signals + GND pour, none over the regulator corner. **In1:** solid GND. **In2:** +5V with +3V3 (RP), +3V3_S3 (top band) and CONS_5V islands. **B.Cu:** fingers, signals, GND pour. |
| Parts-free band | 23.5 mm from the insertion edge: the finger stubs, the address twist, the data fan-in. In1 / In2 stop at the finger field. |
| The S3's antenna | The module flush with the top edge (0.2 mm in). Its footprint's keep-out (the antenna plus 15 mm each side, 48 x 6 mm on the board) is enforced as board rule areas and is empty on every layer: `layout_checks` 9. |
| Routing | Locked pre-routes first: the finger stubs, the address twist, the data fan-in, the regulator corner and rings, SWD, the crystal, the USB-C pad joins and the USBLC6 -> CP2102N stretch, the buck's input loop, the mux's under-body joins, TP_DVDD's link. Then Freerouting 2.4.1 (16 passes), the grid A* finisher, `drc_fix`, the neck pass, and `tidy_tracks` (necks widened to >= 0.127 mm). 838 segments: 1.78 m on F.Cu, 1.01 m on B.Cu, nothing routed on In1 / In2. |
| Vias | 689 through vias, tented both sides:
  - 664 at 0.6 / 0.3 mm, 9 power vias at 0.8 / 0.4, 16 at 0.5-0.6 / 0.25 (the USB-C's D- vias, the regulator corner).
  - By net: 540 GND (fan-out, a 4 mm stitching grid, an edge row 1.2 mm in, and GND vias beside signal vias), 72 signal, 77 supply.
  - 57 of the 72 signal vias have a GND via within 1 mm; the other 15 are triaged below (RP-001).
  - `check_vias`: none touches a foreign SMD pad. |
| Rules | Net-class clearance 0.15 mm, which the router used. The DRU floor is 0.12 mm, which the QFN-80's 0.4 mm pitch needs. The fingers keep >= 0.6 mm from the board edge. All within JLCPCB's 4-layer capability. |

**Layout notes.**
- **The S3 band.** The module is flush with the top edge. Its keep-out is enforced as board rule areas (`gen_pcb.antenna_keepout`): KiCad 10's DRC ignores a footprint's own keep-out once the project library is loaded.
- **The USB-C chain runs in one order end to end.** The receptacle's D+ U and D- vias feed the USBLC6 (rotation 90), then the CP2102N (rotation 270). The USBLC6's twin pins are joined straight under its body, and its VBUS drops through a via between the pad rows, to the 100 nF beside the package (5.3 mm; ST draws it at pin 5) (`gen_pcb.bridge_link`). The pair is 16.0 / 15.7 mm.
- **The USB-C sits where HRO's layout puts it.** The PCB edge is 5.79 mm in front of the pegs, so the shell face overhangs the edge by 0.46 mm and a plug's overmold clears the board. Its 3D model and the microSD's are placed by their measured origins (FujiNet-NES Rev0's fleet-wide fix).
- **The buck's input loop closes on F.Cu.** VIN and GND reach the 100 nF without a via, with the plane vias at the far end of the 22 uF stack (`layout_checks` 10). The CP2102N's exposed pad has 10 GND vias (11).
- **The RP half is V4's.** It keeps Raspberry Pi's regulator corner (grafted onto the QFN-80), the +3V3 supply rings, the 3 x 3 exposed-pad grid, the address twist and the data fan-in (`layout_checks` 1-8).
- **Five fixes after S7.** They cover the antenna keep-out, a 20 mm D+ loop at the USBLC6, the USBLC6's 100 nF moved to its VBUS pin, the USB-C set 1.35 mm inside the edge, and stale zone fills in the zip (427 GND vias inside the In2 power pours). They are described in `floorplan-study.md`; each is now in the generator and has its own gate.

### PCB / EMC findings, triaged

kicad-happy 2.2.1 applies `.kicad-happy.json`'s suppressions in the EMC and thermal analyzers only. The PCB analyzer's findings are triaged here. The EMC pre-compliance score is 55 / 100: a heuristic, with no critical findings.

| Rule (count) | Finding | Verdict |
|---|---|---|
| KO-001 (4, high) | H1 / H2 inside the post keep-outs; J1 inside the finger-field keep-outs | By design: the rule areas are drawn for exactly those parts. They forbid tracks, vias and pour, not the hole or the fingers. |
| DC-001 (fixed) | On run `2026-10-11_1144-2`, the nearest VBUS capacitor was 8.7 mm from U7 (USBLC6) | Fixed: ST's figure puts 100 nF at pin 5, so C_VBUSHF moved beside the package (5.3 mm of copper, `layout_checks` 7). Run `2026-10-11_1211` no longer reports it. |
| DC-002 (1, high) | No decoupling near U9 | False positive: the UMH3N is two transistors and has no supply pin. |
| PM-002 (1 high, 3 info) | J3 (microSD) 0.2 mm from the top edge; J4 (USB-C) over it; J1 at the edge | By design: the card and the plug enter from the top edge. JLCPCB places them; any rails go on the left and right edges only (ORDER doc). |
| RP-001 (1 high, 7 warning, 6 info) | Layer changes without a GND via within 1 mm | 15 of 72 signal vias. D1-D6 are the data fan-in's via row in the finger band (1.4-2.8 mm). UBRG_DM's three are under the receptacle's pads (3.4-4.3 mm). The rest (S3_IO0, S3_TXD, SD_DAT1/2, DRIVE_N, RP_MA1) are slow signals where `stitch_gnd` found no room. CONS_5V's are plane drops. A 1.76 MHz bus and full-speed USB: low risk. |
| GP-001 (10) | Bus lines 90-95 % over a reference plane | The uncovered 5-10 % is the finger field, where the inner layers must stay empty (gold fingers; `check_gerbers` 7). |
| PS-002 (1) | +3V3 in 10 islands, DBG_TX / RX crossing | The islands are the In2 RP island plus the F.Cu supply rings and graft pours of the same net. DBG_TX / RX is a 115200-baud bring-up UART. |
| CK-001 (5), CK-003 (1) | XIN / XOUT / XOUT_Y / SWCLK / SD_SCK on an outer layer; SD_SCK near J3 | All on F.Cu over In1's solid GND. XIN is 7.5 mm with no via, as in Raspberry Pi's layout. J3 is SD_SCK's own destination. |
| BE-002 (1) | GND pour on 71 % of the perimeter | The gaps are the finger field (bottom) and the antenna keep-out (top), both copper-free by design. |
| CC-002 (6), CC-DET (11) | 0.15 mm necks | At the 0.4-0.5 mm-pitch pins only; nothing below JLCPCB's 0.127 mm. Waived in the config. |
| SW-001 (3), EE-002 | Buck harmonics in the FM / VHF bands | The analyzer assumed 0.5 MHz; the AP63203 runs at 1.1 MHz. Its input loop closes on F.Cu with no via, and its output sits over the +3V3_S3 island. Pre-compliance only. |
| XT-001 (3) | RP_MA6 / 7 parallel 16 mm, RP_D3 / 4 and RP_D5 / 6 6 mm, at 0.5 mm | Same-direction bus lines, sampled after they settle on a 1.76 MHz bus. |
| TE-001 (1) | 12 / 171 nets have a test pad | 17 pads on the rails and key signals; the bus is reachable at the fingers. |
| IO-001 (3), IO-002, ES-002, EE-001, CP-002 (4), OR-001, DFM-001 | Info | The console-defined edge (2 GND contacts), USB-C behind the USBLC6, one GND via at U7's pin 2 plus In1 below it, cavity resonances from 641 MHz, no copper under the NPTH posts, mixed passive orientation, a board over 100 x 100 mm. |
| VM-001, RS-001, PU-001, LB-001, TS-003 | Schematic / thermal | See [Signal analysis](#signal-analysis) and [Power](#power). |

### Release-gate waivers

`fab_release_gate.py --strict`: 10 pass, 2 fail, both waived.

| Gate | Why it is waived |
|---|---|
| Component count: schematic 125 vs PCB 131 | The board carries 5 parts the schematic does not: H1 / H2 (the shell posts) and FID1-3. J2 is DNP in the schematic but has a footprint on the board (not fitted). `cross_verify` matches all 126 schematic parts. |
| Layer alignment: height varies by 9.8 mm | Not a registration error. In1 / In2 stop at the finger field, the antenna keep-out is copper-free, and the masks and paste cover only the parts. `check_gerbers.py` checks every position against `edge_geom.py`. |

## Manufacturing

| Gate | Result |
|---|---|
| `check_fab.py` | 10 / 10: parts = BOM = CPL; LCSC codes, MPNs and manufacturers on every line; a measured CPL rotation for every row; drills; the order-number spot |
| `check_gerbers.py` | **0 failures.** The 4-layer set; the sides above and below the notches; the notches and the top corners as arcs; 90.912 x 111.49 mm. 22 fingers at their pins' x, 1.905 mm wide, 0.70-8.95 mm in, with no copper between them. F.Cu and the inner layers are empty in the field; each finger has its own mask window. No paste, silk or drill hit in the field. Both post holes are in place. |
| JLC CPL | All 42 (footprint, LCSC) pairs measured pad by pad against their EasyEDA footprints. Four are medium confidence: the AOTA inductor and the BAT54C (land-size residuals), the TS-1187A (matched by geometry) and the USB-C (mechanical offset). The ESP32-S3's EasyEDA origin sits 3.62 mm off ours; the CPL corrects it. Check all of them in the placement preview. |
| Order | `exports/jlcpcb/ORDER-JLCPCB.md`: 4 layers, ENIG, hard-gold fingers with a 45° bevel on the insertion edge, Standard PCBA, top side, J2 not fitted. Rails, if asked for, on the left and right edges only: the top edge has the antenna, the USB-C and the microSD. |

## Lifecycle

- **kicad-happy's audit.** `lifecycle_audit.py --only lcsc` reports every MPN as "unknown". The LCSC
  source carries no lifecycle status for that script, by construction.
- **LCSC's flag.** `tools/audit/sourcing.py` reads LCSC's own product-cycle flag instead
  (`docs/sourcing.md`):
  - 43 of 44 lines are "normal" (active).
  - LCSC has no record of the buck inductor's code (SWPA4030S6R8MT, C62684). JLCPCB lists it with 16k
    in stock, as on Channel F.
- **Stock is the risk.** The RP2350 core inductor (AOTA-B201610S3R3-101-T, C42411119) had 24 at
  JLCPCB and 0 at LCSC. If it runs out, either:
  - consign it, or
  - fit a shielded 2016 3.3 uH on the same land, such as the TDK VLS201610HBX-3R3M-1 (C695624). That
    part is not qualified by Raspberry Pi.
- **No distributor status.** No DigiKey / Mouser / element14 keys are configured, so there is no
  distributor end-of-life status.

## Open questions

1. **The console's 7805 with WiFi** (warning). With no USB the cart draws ~470 mA peak from the
   console's 5 V. Bring-up step 2 measures it. If it sags, the cart runs from USB-C.
2. **The S3 pin map** (warning). `fujiversal-studio2.h` lacks `PIN_RP2040_RUN` / `PIN_RP2040_BOOTSEL`.
   - This board wires IO4 / IO5, as `fujiversal-intv.h` does.
   - With the two defines added, `fnPicoUpdater::forceBootselViaPins()` can re-flash a hung RP2354B.
   - Until then, use the buttons or the cooperative BOOTSEL request over USB.
3. **TPA on real consoles.** FliP's README says TPA is "crippled on most console cartridge ports".
   - FliP's v5 multicart stopped relying on it. This cart latches the high address byte on TPA (GPIO8),
     as `s2_cart.h` does.
   - Bring-up step 3 scopes the gated TPA's width, and the firmware's `S2_LO_DELAY_NS` may need tuning.
4. **L1 stock** (see [Lifecycle](#lifecycle)): re-check on the order day.

## Not performed / review limits

- **Distributor lifecycle status:** no API keys; LCSC's product-cycle flag stands in.
- **RF performance.** The S3 module is pre-certified, and its antenna placement follows Espressif's
  keep-out. Nothing is measured, and the printed shell's material near the antenna is the user's
  choice.
- **Signal and power integrity beyond kicad-happy's decks.**
  - The bus runs from a 1.76 MHz clock.
  - The USB links are full speed, at netclass width over the planes, not impedance-controlled.
- **Thermal analysis:** the analyzer assessed the regulators. `margins.py` covers the loads by hand.
- **The console side is not measured:**
  - the 7805's headroom (open question 1);
  - TPA's behaviour (open question 3);
  - the edge's fit, beyond FliP's built board (the 1:1 overlay is the one physical check).
- **Firmware:** `check_nets.py` and `check_glue.py` check the netlist and the glue against the
  firmware headers. The README's *Firmware follow-ups* lists the pin-map addition and two smaller
  items.

## What a Rev1 could improve

- **GND vias at the USB-C's D- join.** Move the receptacle's D- vias, or swap which line changes layer, so a GND via fits within 1 mm. Add a second GND via at U7's pin 2.
- **The console's 7805.** If bring-up shows CONS_5V sagging under WiFi bursts, add a current limit on VIN2 or a "WiFi needs USB" rule in firmware.
- **L1.** Qualify a second-source 2016 3.3 uH inductor before the AOTA runs out.
- **The pin map.** `PIN_RP2040_RUN` / `_BOOTSEL` in `fujiversal-studio2.h` (firmware, not the board).
