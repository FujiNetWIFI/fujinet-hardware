# FujiNet-Astrocade Rev0 Design Review

**Project:** FujiNet-Astrocade-Rev0 (KiCad 10, generated from `tools/design.py` + `tools/sch_layout.py`; since Part 3 a root board map + 5 wired sheets)
**Date:** 2026-10-02 (Parts 1, 2); 2026-10-09 (Part 3: the wired redraw and a re-audit, at the end)
**Baseline:** commit `12ffcc1` (the first Rev0: RP2354A + ESP32-S3, 6-layer, autorouted, never audited against datasheets)
**Analyzers:** kicad-happy 2.2.1:
- `analyze_schematic.py`
- `simulate_subcircuits.py` (ngspice, 16/16 pass)
- the Deep Review pass: `analysis/deep_review.json`, 19 findings, evidence gate 19/19 verified
- the PCB / cross-domain / EMC / thermal / gerber analyzers (Part 2)

Project checks:
- `tools/check_nets.py`: 182 netlist-vs-firmware checks
- `tools/check_sch_layout.py`: 373 pins, drawn netlist == design.py (replaced in Part 3 by `gen_sch.py`'s netlist parity + `tools/nets.lock`)
- KiCad ERC (`--severity-all`)

## Overview

All-in-one Astrocade cassette cartridge:
- An **RP2354A** (RP2350A + 2 MB flash, QFN-60) sits directly on the console's 5 V bus and serves the 8K cart window and the FujiNet mailbox.
- An **ESP32-S3-WROOM-1-N16R8** runs FujiNet and is the RP's USB host.
- **USB-C** (CP2102N) and **microSD** are the external ports.
- Power is the console's +5V, diode-ORed with USB VBUS. An AP63203 buck makes +3V3; an AP2112K LDO makes the RP's own +3V3_RP.

## Previous Review Delta (baseline -> this revision)

| Status | Item |
|---|---|
| **Fixed** | **RP pads unpowered while the console drives 5 V on them.** IOVDD came from the buck: 4 ms soft-start after UVLO, while the RP2350 FT pads take 5.5 V only "provided IOVDD is powered to 3.3 V" (DS p.1332). Every RP supply pin is now on +3V3_RP from an AP2112K. In dropout it tracks the console rail as that rail rises. |
| **Fixed** | **WS2812B-2020-V6 on +3V3**, against a datasheet VDD of 3.7-5.3 V (the "3.3 V-rated V6" claim was wrong). Now on +5V; VIH 2.7 V still takes the 3.3 V data. |
| **Fixed** | **No VBUS decoupling** at the USB-C (kicad-happy UC-001): 1 uF + 100 nF added. |
| **Fixed** | **RP activity LED at ~0.45 mA** (1k from 3.3 V into a 2.85 V green LED): 330R. |
| **Fixed** | **CP2102N exposed pad had 4 of the 9 recommended thermal vias** (TV-001): `fanout.py` plans a 3x3 array (Part 2). |
| **Fixed** | **No fiducials** (FD-001, high): FID1-3. |
| **Fixed** | **microSD card-detect polarity** was an open bring-up item. The TF-015 drawing has the CD switch closing to the shell with a card in: SD_CD low = card present. |
| **Fixed** | **Schematic unreadable**: shelf-packed symbols, a global label on every pin, no wires. It is redrawn: block-diagram root with hierarchical pins, power symbols, wired clusters, design notes. |
| **New** | **Test pads**: TP6 RUN, TP7 BOOTSEL, and the three rails (TP8 +5V, TP9 +3V3, TP10 +3V3_RP). |
| **New** | The tooling checks `design.py` pin numbers against the symbols on every build (RP2354A, ESP32-S3). It also checks the drawn netlist against `design.py`, pin for pin. |
| Kept | Topology: RP directly on the bus, no level shifters, firmware-gated by /CCS and VSENSE (user decision, re-justified below). |
| Kept | SS34 diode-OR. There is no 5 V logic, so the ~0.38 V drop is harmless (headroom below); no P-FET. |
| Open | **Read timing:** the console decoder's /CCS delay is unpublished; the ~590 ns M1 budget assumes 100 ns (bring-up scope item). |

## Critical Findings

None open. Every finding that needed a design change was fixed (above). The remaining items need a bench: console power-up ramp, /CCS timing, blade reach. They are on the README bring-up checklist.

## Component Summary

93 components:
- 6 ICs: RP2354A, ESP32-S3, CP2102N, UMH3N, AP63203, AP2112K
- 37 capacitors, 21 resistors + 1 array
- 8 diodes/LEDs, 2 inductors, 1 crystal
- 3 connectors: Astrocade edge, microSD, USB-C
- 4 switches, 10 test pads

There are 40 unique BOM lines, 74 design nets and 52 no-connects. MPN and LCSC coverage is 100 % on placed parts. JLCPCB stock was checked 2026-10-02 for every LCSC code; all are in stock:
- RP2354A C41378174: 6,980
- ESP32-S3-WROOM-1-N16R8 C2913202: 28,205
- AP2112K-3.3TRG1 C51118: 38,648
- AOTA-B201610S3R3 C42411119: 3,308
- TL3342F160QG C2886898: 1,892

## Power Tree

```
edge 25 CONS_5V --[D7 SS34]--+
                             +--> +5V --> U5 AP63203 buck 3.3 V/2 A (6.8 uH, 3x22 uF in, 2x22 uF out) --> +3V3: ESP32-S3, CP2102N, microSD
USB-C VBUS ----[D8 SS34]-----+        |
 (1 uF + 100 nF, ESD5Z)               +--> U6 AP2112K-3.3 --> +3V3_RP: RP IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD,
                                      |                                 VREG_VIN, VREG_AVDD (33R/4.7 uF) --> RP core SMPS --> DVDD 1.1 V
                                      +--> D3 WS2812B-2020
VSENSE = 0.6 x CONS_5V (sensed before the OR diode) -> RP GP26: the firmware serves the bus only with the console powered
```

Headroom (`tools/audit/por_window.py`): at a 4.75 V console rail, +5V is 4.37 V. The margins are 0.57 V to the buck's 3.8 V VIN minimum, 0.82 V to the LDO's 3.55 V, and 0.67 V to the WS2812's 3.7 V.

LDO start-up: +3V3_RP carries 21.3 uF, and the AP2112K's short-current limit is 50 mA (fold-back, at VOUT = 0). So a hot-plug step would take up to 1.4 ms. On a normal console power-up the rail ramps on a millisecond scale: following 1 V/ms needs 21 mA, so +3V3_RP tracks CONS_5V minus the diode drop. That is the property the FT pads need. It is a bring-up scope item (checklist 2).

## Analyzer Verification

- **Netlist.** `check_sch_layout.py` exports the netlist with kicad-cli. All 373 `design.py` pins sit on the named net (52 NC pins unconnected).
- **ERC.** 0 violations with `--severity-all`.
- **Firmware.** `check_nets.py`: 182/182 against `astrocade_cart.h`, `fujicade_rp2354.h` and `fujiversal-astrocade.h` (fujinet-firmware branch `astrocade-rp2354-board`), plus the Tilton edge map. It also checks the RP rail, the LDO, the OR diodes, the buck and the WS2812 supply.

### Component Pinout Verification (manufacturer PDFs)

| Ref | Part | Verified against | Status |
|---|---|---|---|
| U1 | RP2354A QFN-60 | RP2350 datasheet pin tables; `gen_sch.verify_pin_tables()` on every build | Verified |
| U2 | ESP32-S3-WROOM-1 | Espressif pin definitions p.11-12 | Verified |
| U3 | CP2102N QFN28 | Silicon Labs pin definitions p.28 (VREGIN = VDD = +3V3, VBUS = sense) | Verified |
| U4 | UMH3N | JCET p.1 (two DTC143T), inner-circuit figure | Verified, medium (figure, not text) |
| U5 | AP63203WU | Diodes pin descriptions p.2 | Verified |
| U6 | AP2112K-3.3 | Diodes pin descriptions p.4 | Verified |
| D2 | BAT54C | SOT-23 diagram p.1 (common cathode pin 3) | Verified, medium |
| D3 | WS2812B-2020-V6 | Worldsemi p.3 (1 DO 2 GND 3 DI 4 VDD; VDD 3.7-5.3 V) | Verified |
| J2 | TF-015 | SOFNG drawing p.1 (pins 1-8, CD switch table) | Verified |
| J1 | Astrocade 26-contact edge | Tilton table (ballyalley) + `tools/audit/edge_orientation.py` on the generated board | Verified |
| Y1, passives | ABM8-272-T3 (CL 10 pF), KT-0603G (VF), SS34, ESD5Z5.0 | LCSC datasheets | Verified where it matters |

## Deep Review (19 findings, all evidence-verified)

- **Power:** the LDO rail and its ramp behaviour; supply order (VREG_VIN with VREG_AVDD, p.402); diode-OR headroom.
- **I/O:**
  - WS2812 supply.
  - VSENSE: 2.85-3.30 V for a 4.75-5.5 V console rail on the plain ADC pad GP26; reads high down to 3.6 V.
  - /CCS pull-up: about 0.3 mA into a dead console; the firmware gate keeps D0-D7 off it.
  - Card-detect polarity.
- **Timing:** Z80 at 1.79 MHz. The RP must drive D0-D7 within about 588 ns of /CCS for an M1 fetch, 867 ns for a read (about 88 RP clocks at 150 MHz). The console decoder delay is assumed (`tools/audit/timing_margins.py`).
- **Pinouts and mechanics:** as in the table above; land 1 east on B.Cu.

## Signal Analysis Review

- **Regulators:**
  - U5 AP63203: switching, +5V to +3V3, fixed.
  - U6 AP2112K: LDO, +5V to +3V3_RP, fixed.
  - The RP2350 core SMPS (3.3 uH) makes DVDD.
- **Dividers** (SPICE):
  - R9/R10 VSENSE: 0.600.
  - R19/R20 VBUS_SNS: 0.681 (3.41 V at 5 V into the CP2102N VBUS pin).
- **RC:** R14/C21, S3 EN delay, 15.9 Hz (SPICE 15.88 Hz).
- **Crystal:** 12 MHz ABM8-272-T3, 2 x 15 pF, 1k series on XOUT; CL 10.5 pF against 10 pF rated.
- **Protection:**
  - ESD5Z5.0 on D+, D- and VBUS at the USB-C; CC 5.1k x2 (UFP).
  - No ESD on the console edge: no Videocade has any, and the RP2350 FT pads carry enhanced ESD protection (DS p.1332).
  - The microSD sits inside the shell.
- **SPICE:** 16/16 pass:
  - 2 dividers, 1 RC, the crystal load, 3 protection devices
  - 7 decoupling networks: +3V3_RP z_min 4.4 mOhm, DVDD 5.4 mOhm
  - 2 inrush models

### Decoupling

| Rail | Caps |
|---|---|
| +3V3_RP | 9 x 100 nF (one per supply pin) + 4.7 uF VREG_VIN + 10 uF bulk + 1 uF LDO out |
| DVDD | 3 x 100 nF + 4.7 uF (regulator corner, Raspberry Pi layout) |
| VREG_AVDD | 33R + 4.7 uF |
| +3V3 | 2 x 22 uF buck out, 22 uF + 100 nF S3, 10 uF microSD, 4.7 uF + 100 nF CP2102N |
| +5V | 3 x 22 uF + 100 nF buck in, 1 uF LDO in, 100 nF WS2812 |
| VBUS / CONS_5V | 1 uF + 100 nF / 100 nF |

## False Positives / Reviewer Overrides (`.kicad-happy.json`)

| Finding | Disposition |
|---|---|
| VM-001 5 V / 3.3 V crossing | Intentional. The RP2350 FT pads take 5.5 V with IOVDD powered, and IOVDD is the tracking LDO rail. The console only reads the cart; the RP's 3.3 V outputs meet the Z80's TTL VIH. |
| RS-001 VBUS_SNS "no source" | A divider node into the CP2102N VBUS sense pin |
| PU-001 U3 CHREN | Charger-detect output, left open as in the DevKitC-1 |
| LB-001 x9 "multiple labels" | A hierarchical label and its sheet pin: how the root block diagram wires the sheets (x8 since Part 3; the analyzer names those nets by sheet uuid, `/2207b269-.../S3_EN`, where KiCad's netlist says `/S3_EN`) |
| CG-AUD J1, EP-AUD J1/J2 | Console-defined pinout (3 GND); no ESD on a console bus; microSD inside the shell |

## Not Performed / Review Limits

- **Lifecycle audit:** no distributor API keys. JLC stock was queried directly.
- **Impedance control:** none. USB is Full-Speed on every endpoint (RP2350, ESP32-S3, CP2102N: 12 Mb/s), and the bus runs at 1.79 MHz.
- **Bench-only items** (README checklist):
  - console power-up ramp vs +3V3_RP
  - /CCS-to-data timing with the real decoder
  - blade reach vs the escape holes
  - console 5 V headroom under WiFi bursts

## PCB Layout, Cross-Domain, EMC, Thermal, Gerbers (Part 2)

**Board.** `FujiNet-Astrocade-Rev0.kicad_pcb` is generated by `tools/gen_pcb.py` + `tools/placement.py` and routed by `tools/build_all.sh`:
- crystal + VBUS pre-routed and locked
- Freerouting 2.4.1, 25 passes x 2 rounds
- `drc_fix`, then the A* finisher with rip-up
- DRC-gated tidy, GND stitching, return vias at USB/crystal/SWCLK layer changes where DRC allows
- `check_vias.py`

It has 833 track segments (2.14 m) and 382 vias:
- 368 at 0.6/0.3
- 8 at 0.45/0.25: the USB-C pad ties and some router vias
- 3 at 0.5/0.25: under the RP
- 3 at 0.8/0.4: power

**Gates.**
- KiCad DRC (`--refill-zones --schematic-parity`): **0 errors, 0 unconnected, 0 parity**. 76 warnings remain: silkscreen cosmetics plus 1 copper sliver.
- `check_vias.py`: 0 vias touching a pad of another net.
- `check_nets.py`: 182/182.

### Stack-up: 4 layers tried first (user request), 6 layers used

The 4-layer board was F.Cu / In1 GND / In2 power (+3V3 with the +3V3_RP and DVDD islands) / B.Cu. B.Cu is forbidden over the south 16.5 mm, where the console blade wipes.

| Attempt | Freerouting result (KiCad unconnected) | After the A* finisher |
|---|---|---|
| 4 L, bus pre-routed with A* | 13 | 12, not converging |
| 4 L, Freerouting only | 7 | 12 after 55 min of rip-up, stopped |
| 6 L, Freerouting only | 6 | 4 (RP2354A pins CA7/CA8/CD1/CD4) |
| 6 L, +3V3_RP moved out of the PWR net class, USB-C ties locked | **1** | **0** |

Two findings along the way changed the tooling. Neither was a placement problem.

- **Pre-routing the bus pin by pin walls in the 0.4 mm QFN.** A* tracks laid one pin at a time left every other bus net with no path, on 4 and on 6 layers alike. The bus is now left to Freerouting.
- **A net-class clearance on a supply that touches a 0.4 mm-pitch IC is a routing hazard.**
  - Putting `+3V3_RP` in the PWR class (0.2 mm clearance, 0.5 mm track) made every IOVDD pin and its fan-out stub demand 0.2 mm from the neighbouring signal pins. Four bus pins were boxed in.
  - The RP rail carries about 60 mA, so it is back in Default.

### Analyzer runs (kicad-happy 2.2.1)

| Analyzer | Result |
|---|---|
| `analyze_pcb.py --full --proximity` | dispositioned below |
| `cross_analysis.py` | 2 findings (PS-002 info) |
| `analyze_emc.py` | 37 findings (8 error-class, all dispositioned below) |
| `analyze_thermal.py` | score 97/100, board dissipation 0.28 W; 1 warning (TS-003, below) |
| `simulate_subcircuits.py` | 16/16 pass |
| `analyze_gerbers.py` (exported zip) | 0 errors; GR-002, GR-004 (below) |
| lifecycle audit | not run (no distributor API keys) |

### Layout findings and dispositions

| Finding | Disposition |
|---|---|
| FD-001 no fiducials (baseline, high) | **Fixed.** FID1-3 sit in three corners, each with a 1.6 mm copper/track keep-out ring so the mask opening never meets the GND pour. |
| TV-001 CP2102N EP 4/9 vias (baseline) | **Fixed.** 3x3 thermal array (`fanout.EP_ARRAYS`). Via-in-pad is acceptable because JLC 6-layer boards are epoxy-filled and capped. |
| VP-001 via in pad (C13, C7, R4, SW2-4, R18, D6, C19, R10, C9, C4) | **Fixed, and the cause is in the tooling.** `stitch_gnd` dropped GND grid vias into pads, because KiCad's DRC accepts a same-net via in a pad. Worse, on load KiCad *re-nets* a via that sits inside a pad of another net: a GND via in a +3V3_RP pad becomes a +3V3_RP via and passes DRC. `stitch_gnd` now keeps 0.5 mm off every SMD pad, and the new `tools/check_vias.py` gates the board-file nets. |
| UBRG_DP / UBRG_DM unroutable at the USB-C | **Fixed.** The receptacle's interleaved pads (B6 A7 A6 B7, 0.5 mm) are joined by locked copper (`gen_pcb.usb_c_ties`): D+ loops on F.Cu, D- drops through two staggered 0.45/0.25 vias to B.Cu. |
| Starved thermal on J1 GND land 13 (DRC) | **Fixed.** The blade rule area clips the B.Cu pour around the escape hole; `.kicad_dru` `j1_gnd_spokes` accepts one spoke there (the lands are fed through their plated holes). |
| RP-001 missing GND via within 1.0 mm of a layer change (USB_DP/DM, UBRG_DP/DM, XOUT, SWCLK; plus about 20 slow nets) | **Partly mitigated, accepted.** `tools/stitch_transitions.py` adds GND return vias where DRC allows. Of the 18 signal vias on those nets, 7 have a GND via within 1.0 mm, 13 within 2.0 mm, and the worst is 4.3 mm away; the dense USB-C and QFN areas leave no legal spot closer. Every USB link here is Full-Speed (RP2350, ESP32-S3 host, CP2102N: 12 Mb/s), XOUT is a 12 MHz crystal drive, SWCLK is debug-only, and the bus runs at 1.79 MHz. Worth an EMC pre-scan if the cart is ever certified. |
| GP-001 XIN 94 % reference coverage over 14.7 mm | Accepted. The XIN run joins the RP pin, the crystal and its load cap on F.Cu over the In1 GND plane; the 6 % is the crystal pad / via area. The regulator-corner copper is Raspberry Pi's. |
| DC-002 no decoupling near U4 (high) | False positive: UMH3N is a transistor pair with no supply pin. |
| KO-001 FID1-3 inside a keep-out (high) | False positive: the keep-out rings exist *for* the fiducials (pads allowed, pour and tracks not). |
| PM-002 J2 courtyard 0.25 mm over the edge (high) | By design: the microSD slot exits the trailing edge, and the shell has the opening (`case/board-anchors.scad`). |
| DFM-001/002 0.1 mm annular ring | Accepted. The 0.45/0.25 vias are within JLCPCB's multilayer minimum (0.25 mm via / 0.15 mm drill). The rest of the board uses 0.6/0.3 (0.15 mm ring). |
| CC-002 0.15 mm neck-downs (CA0 etc.) | Freerouting neck-downs at the QFN-60 / QFN-28 pins; JLC multilayer minimum is 0.09 mm. |
| CK-001 XIN/XOUT on an outer layer, CK-003 SD_SCK near J2 | The crystal is a few mm from its pins over the GND plane; SD_SCK ends at the slot it clocks. |
| DC-001 S3 decoupling "moderately far" | C19/C20 sit beside the module's 3V3 pad column; the module carries its own decoupling. |
| TS-003 U6 AP2112K "Tj 96 C", TP-001 MLCCs near it | Analyzer's assumed load. With about 60 mA x (4.62 - 3.3) V = 79 mW at ~250 C/W, the rise is about +20 C (`tools/audit/por_window.py`). |
| SW-001 buck harmonics, CERT-001, WL-001 | Informational (AP63203 at 1.1 MHz; pre-certified ESP32-S3 module). |
| GR-002 "height varies 18 mm" across copper layers | The inner signal layers simply carry less copper than the outlined layers. Not a registration problem: all layers share one origin. |
| GR-004 paste 46 % of copper flashes | Copper flashes include 382 vias and the unpasted lands / test pads. |
| PS-002 +3V3_RP / VBUS "2 islands" | Fill fragments around vias, joined through vias; DRC reports 0 unconnected. |
| TE-001 test points 6 % of nets | By design: SWD, SELFTEST, DBG_TX, RUN, BOOTSEL and the three rails. |

### Gerbers and fab package

`exports/jlcpcb/FujiNet-Astrocade-Rev0-gerbers.zip` contains:
- F/In1/In2/In3/In4/B copper
- mask, paste and silk
- Edge.Cuts
- PTH and NPTH Excellon files with maps

`BOM-JLCPCB.csv` and `CPL-JLCPCB.csv` cover the 82 placed parts. Each carries an LCSC code, all in stock on 2026-10-02. The JLC rotation corrections are in `tools/export.py` and must be checked in JLC's placement preview (README bring-up item 7).

### Mechanical

- **Outline and holes:** unchanged (96 x 58 mm, 4x M3).
- **Contact lands:** checked by `tools/audit/edge_orientation.py`.
- **Shell:** `case/FujiNet-Astrocade-Shell.scad` compiles in OpenSCAD with the regenerated `case/board-anchors.scad`; its existing non-manifold warning remains.

## Verdict

**Ready to order as a Rev0 prototype from JLCPCB** (6-layer, 1.6 mm, ENIG), with these gates:
- ERC 0
- DRC 0 / 0 / 0
- the 373-pin drawn-netlist check
- 182 firmware-contract checks
- the via-in-pad gate
- 19/19 evidence-verified datasheet findings

What CAD cannot settle is the README bring-up checklist:
- the console power-up ramp vs +3V3_RP
- /CCS-to-data timing with the real decoder
- blade reach vs the land escape holes
- 5 V headroom under WiFi bursts
- the JLC CPL rotation preview


## Part 3 (2026-10-09): the schematic redrawn wired, and a re-audit

**Scope.** The Part 1 schematic was readable but disconnected:
- every edge land and every RP2354A GPIO ended in a local label (65 on the cart sheet, each bus net labelled twice);
- the 15 RP decoupling capacitors stood in a row 84 mm above U1, each on its own power symbol;
- the root was a plain block diagram.

The later carts (2600 Rev1, 7800, SMS, 5200) are drawn by the SMS-lineage tools, and the schematic is now drawn the same way:
- `tools/sch_draw.py`, `sch_draft.py`, `sch_place.py` and `netlist.py` are ported from FujiNet-5200 Rev0;
- `tools/sch_layout.py` hand-draws each sheet.

**Unchanged:** the routed board, its copper and every part.
**Baseline:** master `1de56c1`.

### What changed

| | Part 1 / 2 | Part 3 |
|---|---|---|
| Sheets | `cart` (edge + the whole RP), `esp32`, `usb`, `power` | `cart-bus`, `rp-core`, `fujinet`, `usb`, `power`, one per board region, console side first; the RESET button and its BAT54C moved from `esp32` to `rp-core`, beside the RP's BOOTSEL as on the board |
| RP2354A | the stock symbol | `RP2354A_Split`: unit A = the 30 GPIOs (cart-bus), unit B = supplies / regulator / crystal / SWD / RUN / USB / QSPI (rp-core); pin names checked against the stock symbol on every build |
| The cart bus | labels on both ends | 22 straight wires, edge land -> GPIO, in the edge symbol's order (/CCS, A0-A12, D0-D7); not one crossing |
| Decoupling | a row of caps on power symbols | every supply pin wired out to its rail with its own cap beside it (the cap's role as `design.py` and `placement.py` record it) |
| Root | block diagram | the board outline turned edge-left at 2:1, each sheet's block over its region, the nine inter-sheet signals wired without a crossing |
| Every sheet | | the board turned edge-left (south -> left, north -> right, west -> top, east -> bottom); signals left to right from the console to the USB-C |
| References | declaration order | `tools/refs.lock` (key -> reference), seeded from the routed board: silk, BOM and CPL are unchanged |

Sheet-local nets now carry the new sheet names, and nets joined on the root are `/NET`:
- `/cart/CA0` became `/cart-bus/CA0`;
- `/cart/XIN` became `/rp-core/XIN`;
- `/esp32/S3_EN` became `/S3_EN`.

On the routed board, the renames were made by these tools:
- `tools/sync_pcb_nets.py` (new) renames the nets on the board itself. It maps every name by its last path element and refuses unless the map is one-to-one. Its self-check: with names cut to that element, the board text is unchanged.
- `tools/sync_pcb_sheets.py` re-points the footprint sheet links.
- `gen_pcb.configure_project()` rewrites the net-class patterns and the `.kicad_dru` rules.

`build_all.sh` now leaves the routed board in place by default (`LAYOUT=0`, as on the 5200). Before, a plain run re-placed and re-routed the board.

### Gates (all pass)

| Gate | Result |
|---|---|
| `gen_sch.py`: `Sheet.check` on every sheet | every connection a wire, each net one wired piece, no 4-way junctions, nothing overlapping; crossings: 0 on cart-bus, rp-core, fujinet and power; 1 on usb (the esptool auto-program pair: RTS and DTR leave the bridge side by side, as on the 5200) |
| board-mirror (`sch_place.py`) | Kendall tau 1.00 across and down on all five sheets |
| netlist parity | 74 / 74 nets, pin for pin, against `design.py` (kicad-cli netlist); the names frozen in `tools/nets.lock` (178) |
| `design.py` vs the Part 2 file | every reference: the same value, footprint, MPN, LCSC code, description and pin -> net map |
| KiCad ERC `--severity-all` | 0 |
| `check_nets.py` (firmware branch `astrocade-rp2354-board`, worktree `~/Workspace/fn-astrocade`) | 182 / 182 |
| the board after the re-link vs before | identical, apart from net names and the footprints' sheet links (`sync_pcb_nets` self-check, and a separate normalised diff) |
| KiCad DRC `--schematic-parity --severity-all --refill-zones` | 0 errors, 0 unconnected, 0 parity; 77 warnings, the same list at the same coordinates as the unchanged board gives under KiCad 10.0.7 (Part 2 counted 76 under 10.0.6): silkscreen, 1 copper sliver, 1 dangling via |
| `check_vias.py`, `edge_orientation.py` | 0 failures; land 1 east on B.Cu |
| fab package | `BOM-JLCPCB.csv`, `CPL-JLCPCB.csv` and the project BOM byte-identical; the 18 gerber / drill files identical but for KiCad 10.0.7's header, the date and the net-name attributes |

### Re-audit (kicad-happy 2.2.1, runs `analysis/2026-10-09_0752`, and `2026-10-09_0805-2` after the R9 / R10 change)

| Analyzer | Result |
|---|---|
| `analyze_schematic.py` | 53 findings, 0 error / 2 warning (PU-001 U3 CHREN, RS-001 VBUS_SNS: as Part 1) |
| `analyze_pcb.py --full --proximity` | 47 findings: the Part 2 set, same dispositions |
| `cross_analysis.py`, `cross_verify.py` | PS-002 x2 (info); cross_verify's 7 "orphans" are FID1-3 and H1-4 (board-only), its diff-pair / decoupling misses are naming artifacts (it looks for the short name on the board) |
| `analyze_emc.py` | 37 findings, risk score 35.5: identical to Part 2 (the copper did not change) |
| `analyze_thermal.py` | 97 / 100, 0.28 W; TS-003 U6 as Part 2 |
| `simulate_subcircuits.py` (ngspice) | 16 / 16 pass (VSENSE and VBUS_SNS dividers, EN RC, crystal, decoupling, inrush) |
| `analyze_gerbers.py` | GR-002, GR-004 as Part 2 |
| `fab_release_gate.py --strict` | 5 fails, all known: advanced DFM tier (0.1 mm via ring, JLC multilayer accepts it), no revision on the silkscreen (the board text reads "FujiNet Astrocade Rev0"; the gate wants a title-block rev), 93 vs 100 parts (FID1-3, H1-4), gerber layer extents (GR-002), the TS-003 thermal warning |
| lifecycle (`lifecycle_audit.py --only lcsc`) | no lifecycle status from LCSC (by construction); stock checked instead (`tools/audit/stock_check.py`) |
| Deep review (`tools/audit/make_deep_review.py` + `deep_review_gate.py`) | **25 / 25 verified**, 0 quarantined: the 19 Part 1 findings (citation pages updated to the current RP2350 datasheet revision) and 6 new ones |

**Datasheets.** `datasheets/` now holds all 36 MPNs (manifest.json), copied from the sibling carts. The PDFs are gitignored. The RP2354A's file is the 1380-page RP2350 datasheet. Two gaps remain:
- the Samsung MLCC files (CL05/CL10/CL21) are RoHS declarations, not datasheets, so capacitor DC-bias derating is not datasheet-backed;
- the Sunlord SWPA4030 PDF is a scan.

### New findings (Part 3)

The later carts' audits were compared with this board, item by item. Five new findings follow; the sixth new deep-review entry records the redraw's gates (above). None of the five is a short or a wrong pin. The first two deviate from the RP2350 datasheet.

| # | Severity | Finding | Evidence | Fix | Board impact |
|---|---|---|---|---|---|
| 1 | **warning** (if the RP2354A is A2 silicon); **fixed 2026-10-09** | **RP2350-E9 can hold VSENSE high in a switched-off console.** The serve gate is /CCS low AND VSENSE (GPIO26) high. The firmware configures VSENSE as a plain input, input enabled and no pulls (`main.c`). On an A2 die, a pad between VIL and VIH sources ~120 uA and holds near 2.2 V; only a pull of 8.2 k or less overcomes it. The 100k / 150k divider is a 60 k pull, so a USB-powered cart in a console being switched off can leave the gate open and drive D0-D7 into the dead bus whenever /CCS reads low. | RP2350 DS p.1367-1369 (E9; "Fixed by RP2350 A3"); `tools/audit/e9_vsense.py`: 60 k holds ~2.2 V > VIH 2.15 V; 10k / 15k = 6 k holds ~0.7 V | **Done (user decision):** R9 / R10 are 10k / 15k, the same 0.6 ratio, drawing 0.2 mA from CONS_5V. Before the LDO starts, GP26 can take up to ~0.1 mA through its clamp (`e9_vsense.py`), and +3V3_RP tracks the ramp. | value change only (R9, R10: same 0603 lands): the BOM changes, the CPL and copper do not |
| 2 | **warning** | **DVDD has no capacitor close to any pin.** The datasheet wants 100 nF at the two DVDD pins nearest the core regulator and 4.7 uF at the furthest. Here all three DVDD 100 nF sit by the regulator and reach the pins through the In4 DVDD island; the furthest pin (23) is 9.1 mm from the nearest DVDD cap. The 2600 Rev1 (same QFN-60) has 4.7 uF at pin 23. | RP2350 DS p.441 ("The DVDD pin furthest from the regulator should be decoupled with a 4.7uF capacitor close to the pin"); `tools/audit/dvdd_far_pin.py` | 4.7 uF (C13 -> CL10A475KO8NNNC) beside pin 23, 100 nF beside pins 6 and 39 | re-placement on the QFN's crowded south side + re-route |
| 3 | info | **USB OR diode leakage can fake a USB attach.** With the console powering the cart and no cable, the SS34's reverse leakage lifts VBUS, which is held only by the CP2102N's 22k / 47k divider. 57 uA reaches the CP2102N's VBUS threshold (VIO - 0.6 V), plausible only on a hot board. No gate rides on VBUS here, so the symptom is the CP2102N's D+ pull-up switching on with no host. | SS34 DS p.2 (0.5 mA at 25 C / 20 mA at 100 C, at 40 V); CP2102N DS p.8; `tools/audit/vbus_leakage.py` | 4.7k VBUS pull-down, as on the 2600 Rev1 / SMS / 7800 / 5200 | new 0603 + re-route (Rev1) |
| 4 | info | **The activity LED can be dim.** KT-0603G VF is 2.6-3.1 V at 5 mA, so 330R from 3.3 V gives 0.6-2.1 mA. The later carts use a red KT-0603R at 680R-1k. | KT-0603G DS p.3; `por_window.py` | red KT-0603R + 680R | value / part change only |
| 5 | info | **Stock.** The AOTA 3.3 uH core-regulator inductor (the Raspberry Pi minimal design's part) is down to 291 at JLC and 5 at LCSC, from 3,308 on 2026-10-02. Every other line is in stock: TL3342 1,650 (4 per board), RP2354A 15,866, WS2812B-2020-V6 1,011,237. | `tools/audit/stock_check.py`, `analysis/sourcing/2026-10-09.json` | order soon, or name a pin-compatible 2016 3.3 uH alternate | none now |

Compared with the later carts, items checked and **not** applicable:
- **The P-FET on the console 5V** (siblings): there is no 5 V logic here, and the SS34 drop leaves 4.37 V at a 4.75 V console rail.
- **The siblings' 4.7k E9 pull-downs:** they guard glue and SRAM enables this board does not have; the bus pads' pulls are off in firmware.
- **WS2812C:** the 5200 went back to the WS2812B-2020-V6 on 2026-10-08, and the V6 is the stocked part.
- **TS-1187A switches:** the TL3342 is still in stock.

One sibling item stays a bring-up check rather than a change: **the console 5V has only 100 nF at the edge**; every sibling has 10 uF + 100 nF. The +5V side already carries 66 uF behind the OR diode; README bring-up item 5 (console 5 V headroom under WiFi bursts) measures what the console rail sees.

### Verdict (Part 3)

**The redraw is complete and electrically neutral.** It is the same netlist pin for pin, the same copper and the same fab package. The board is as orderable as Part 2 said.

The user's decisions on the new findings (2026-10-09):

| # | Decision | Applied |
|---|---|---|
| 1 VSENSE vs E9 | change R9 / R10 to 10k / 15k | yes. `design.py` value change. `sync_pcb_sheets.py` gave R9 / R10 the new Value / MPN / LCSC fields, and the copper is unchanged. Checks: DRC parity 0, `check_nets` 182 / 182, SPICE divider pass. JLC BOM: R9 joins the 10k line (C25804); R10 is a new 15k line (0603WAF1502T5E, C22809, JLC basic) |
| 2 DVDD decoupling | Rev1, plus a bring-up check (README item 10) | no board change |
| 3 VBUS pull-down, 4 LED, 5 inductor stock | Rev1 / ordering notes (README) | no board change |
