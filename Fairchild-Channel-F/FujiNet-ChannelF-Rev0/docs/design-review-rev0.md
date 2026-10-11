# FujiNet-ChannelF Rev0: design review

**Project:** FujiNet-ChannelF Rev0 (KiCad 10; root + 4 wired sheets; 4-layer PCB, 77 x 131.5 mm)
**Date:** 2026-10-11 (kicad-happy 2.2.1, analysis run `2026-10-11_0328`)
**Board:** the routed board in this folder: `LAYOUT=1 tools/build_all.sh` run of 2026-10-11, V10 in
`docs/floorplan-study.md`

Every number below comes from a script in this project and can be re-run:

| Script | What it checks |
|---|---|
| `tools/check_nets.py` | netlist vs the firmware headers |
| `tools/audit/edge_orientation.py` | the edge footprint vs its four sources |
| `tools/audit/margins.py` | logic levels, power budget, regulators, crystal, LED, buck ripple |
| `tools/audit/layout_checks.py` | the layout's datasheet claims, measured on the copper |
| `tools/audit/check_fab.py`, `check_gerbers.py` | the JLCPCB package and its gerbers |
| `tools/audit/sourcing.py` | JLCPCB / LCSC stock and LCSC lifecycle flag |
| `tools/audit/make_deep_review.py` | the datasheet-cited findings, through kicad-happy's evidence gate |

`tools/audit/run_sch_audit.sh` and `tools/audit/run_pcb_audit.sh` run the kicad-happy analyzers.

## Verdict

**Ready to order as a bring-up prototype at JLCPCB.** No blockers.

- KiCad DRC with schematic parity, all severities: **0 violations, 0 unconnected, 0 parity
  issues**.
- ERC 0 at all severities; netlist parity with `design.py` (87 nets); `check_nets.py` 204 checks,
  0 failed.
- The fab package passes `check_fab.py` (10 / 10) and `check_gerbers.py`.
- Every one of the 38 BOM lines is in JLCPCB stock for 5 boards. 37 are "normal" (active) at LCSC;
  LCSC has no record for the inductor's code, which JLCPCB lists.
- The deep review: 24 / 24 findings verified against their datasheets or the copper, 0
  quarantined.
- All 99 parts' pinouts checked against their datasheets: no pin or pad numbering mismatch.

Two **warnings** need a decision; neither stops the board working:

| Severity | Issue | Where |
|---|---|---|
| WARNING | The console's 7805 feeds the cart's ~405 mA Wi-Fi peak as well as the console. Its headroom is unknown. | [Power](#power) |
| WARNING | Two circuit choices differ from the CP2102N datasheet's own diagram: the 80 pF ESD5Z on USB D+ / D-, and a 10k RSTb pull-up instead of 1k. Both left as drawn: changing a value or a part is the user's call. | [Open questions](#open-questions) |

Before ordering, do the three checks in the README's *Before ordering*: the 1:1 tab overlay
against a real Videocart, stock on the order day, and the JLC placement preview.

## Overview

An RP2040 Videocart serves the Fairchild F8 bus through two SN74LVC4245A translators. On the
same board, an ESP32-S3-WROOM-1 is the FujiNet and the RP2040's USB host, with a microSD and a
CP2102N USB-C bridge for flashing it.

- **Power:** the console's 5 V and USB VBUS are diode-ORed (SS34) into +5V.
  - an AP63203 buck makes +3V3 for the S3 side;
  - an AP2112K LDO makes +3V3_RP for the RP2040, its flash and the translators' B ports;
  - the translators' A ports sit on the console's 5 V (CONS_5V) directly.
- **Board:** the outline of aotta's PicoVideocart, which fits a real console and an original
  Videocart shell:
  - a 68.3 mm tab, then a 77 mm body;
  - 22 hard-gold fingers on B.Cu;
  - every part on F.Cu.

## Previous review delta

| Run | What it covered |
|---|---|
| `2026-10-09_0952` | The schematic of PR #54 (no board) |
| `2026-10-11_0254` | The first routed board (V9) |
| `2026-10-11_0328` | This board (V10) |

- **Schematic, 2026-10-09 → now.** Comparing the BOMs by value, footprint and MPN finds them
  identical: 99 parts. The only difference is that J1, the edge, now has its footprint.
  - `diff_analysis.py` reports 94 "changes". Nearly all of them are the geographic
    re-annotation, which moved most references.
  - The control translator's channel order changed (`CTRL_CH`). That is net-level only: A_k / B_k
    pairs are interchangeable, and the RP2040 GPIO numbers the firmware fixes are unchanged.
  - The analyzer's warnings are the same two (PU-001, RS-001; triaged below).
- **PCB, V9 → V10.** This review's own findings were fixed:
  - **PM-002.** The SS34 (D7), a fiducial (FID2) and a 100 nF (C6) were 0.35 / 0.25 / 0.97 mm
    from the body's long sides, where JLCPCB's rails would join. All three are now at least
    1 mm in.
  - **RP-001.** Before V10, the stitching only put GND vias beside the USB vias. Now every signal
    via gets one within 1 mm where there is room: 61 more GND vias. Warning-level RP-001 went from
    19 to 3; 8 nets cleared and 10 dropped to info.
  - **Two new RP-001 errors.** Freerouting moved SWCLK's layer change under the RP2040, where no
    stitching via may go. XOUT's is the locked via inside the RP2040's pin ring (both triaged
    below). The EMC score moved 43 → 40 through these two and C14's DC-003 (the buck's bootstrap
    capacitor).
  - **The board was re-routed from scratch**, not patched. The full `LAYOUT=1` build ran green
    end to end, which also confirms the pipeline reproduces the board.

## Component summary

| Type | Count |
|---|---|
| Capacitors | 39 |
| Resistors (+ 1 four-resistor network) | 20 + 1 |
| ICs / modules | 9 (RP2040, 2x SN74LVC4245A, W25Q16JV, ESP32-S3-WROOM-1, CP2102N, AP63203, AP2112K, UMH3N) |
| Diodes / LEDs | 6 / 2 (WS2812B, green indicator) |
| Switches | 4 (TL3342: RESET, S3 EN, S3 BOOT, BOOTSEL) |
| Connectors | 3 (the Videocart edge, USB-C, microSD) |
| Transistor, crystal, inductor | 1 each (2N7002, 12 MHz, 6.8 uH) |
| Test pads | 12 (bare copper) |

- **Assembly:** 86 parts are placed by JLCPCB. J1 is the board's own edge. The board also carries
  four 5.6 mm NPTH holes and three fiducials.
- **Schematic:** 144 nets, 310 wires, 57 no-connects.
- **Sourcing:** every part has an MPN, a manufacturer and an LCSC code (`check_fab` 2 / 3). See
  `docs/sourcing.md`. The parts cost is about US$18.66 per board at the 5-board quantity, before
  assembly fees.

## Power tree

```
console 5 V (edge 19/20) = CONS_5V ─┬─ SN74LVC4245A x2 VCCA (A ports, the console side)
                                    └─ SS34 (D8) ─┐
USB-C VBUS ── ESD5Z ── SS34 (D7) ─────────────────┴─ +5V (4.3-4.9 V)
                                                   ├─ AP63203 buck, fixed 3.3 V, 1.1 MHz ─ +3V3: ESP32-S3, microSD, CP2102N
                                                   ├─ AP2112K-3.3 LDO ─ +3V3_RP: RP2040, W25Q16, translators' VCCB
                                                   │                     └─ RP2040 core regulator ─ DVDD (1.1 V)
                                                   └─ WS2812B
```

Both regulators are fixed-output parts: no feedback divider to check. The analyzer's power
regulator detection found both (U4 switching, U7 LDO).

## Analyzer verification

- **Component count.** The analyzer counts 99 schematic parts; the netlist exported by
  `kicad-cli` has 99. `cross_verify` matches all 99 on the board. Its 7 "orphans" are the
  board-only holes H1-H4 and fiducials FID1-3.
- **Netlist.** The `kicad-cli` netlist equals `design.py` part for part and pad for pad (0
  differences), and every symbol in the schematic is identical to its library copy. KiCad DRC
  finds 0 schematic-parity issues.
- **Gerbers.** `analyze_gerbers` finds all expected layers; `check_gerbers.py` checks the geometry
  layer by layer (table under [Manufacturing](#manufacturing)). Excellon hits: 782 = 758 vias +
  16 plated pads + 8 unplated.

### Pinouts against the datasheets

The symbol pin numbers, footprint pad numbers and nets of every part with more than two pins, and
of every polarized part, were checked against the manufacturer's PDF in `datasheets/`.
**Verified (datasheet)** means the PDF's pin table or package drawing was read.

| Ref | Part | Package | Datasheet (page) | Status |
|---|---|---|---|---|
| U5 | RP2040 | QFN-56 | pin list p613-615, package p609-612; all 57 pins incl. EP = GND | Verified (datasheet) |
| U8, U9 | SN74LVC4245APWR | TSSOP-24 | pin functions p3, PW0024A p23 | Verified (datasheet) |
| U6 | W25Q16JVSSIQ | SOIC-8 208 mil | pin configuration p6 | Verified (datasheet) |
| Y1 | ABM8-272-T3 | 3225 4-pad | outline p2 (crystal between 1 and 3) | Verified (datasheet) |
| U1 | ESP32-S3-WROOM-1-N16R8 | module | pin table p11-12, layout p10 / p45 | Verified (datasheet) |
| U3 | CP2102N-A02-GQFN28R | QFN-28 | pin table p27-28, land pattern p35 | Verified (datasheet) |
| U4 | AP63203WU-7 | TSOT-26 | pin table p1-2 | Verified (datasheet) |
| U7 | AP2112K-3.3TRG1 | SOT-23-5 | pin table p1-2 | Verified (datasheet) |
| U2 | UMH3N | SOT-363 | equivalent circuit p1 | Verified (datasheet) |
| D2 | BAT54C,215 (Nexperia) | SOT-23 | pinning p1: 1 A1, 2 A2, 3 common cathode | Verified (datasheet) |
| D7, D8 | SS34 (MDD) | SMA / DO-214AC | case and polarity p1: band = cathode = pad 1 | Verified (datasheet) |
| D4-D6 | ESD5Z5.0T1G | SOD-523 | pin 1 cathode p1 / p5 | Verified (datasheet) |
| Q1 | 2N7002 | SOT-23 | 1 G, 2 S, 3 D p1 | Verified (datasheet) |
| D1 | WS2812B-2020 | 2020 | pin table p2 | Verified (datasheet; the PDF is revision V1.3 and does not name the -V6 suffix) |
| D3 | KT-0603G | 0603 LED | p2: ① anode, ② cathode. KiCad pad 1 is the cathode | Verified by function (see below) |
| J2 | TYPE-C-31-M-12 | 16P | pin table and layout p1 | Verified (datasheet) |
| J3 | TF-015 | microSD | pin definition p2, CD closes to the shell with a card in | Verified (datasheet) |
| SW1-SW4 | TL3342F160QG | 4-pad tact | schematic and land pattern p1 | Verified (datasheet) |
| RN1 | 4D03WGJ0103T5E | 4x0603 | p4 | Verified (datasheet) |
| J1 | the Videocart edge | 22 fingers | `edge_orientation.py` against aotta, fart, US 4,095,791 and the veswiki photo | Verified (four sources) |

Notes:

- **Wrong-maker datasheets replaced.** The SS34 and BAT54C PDFs in `datasheets/` were another
  maker's: Vishay's SS34 in **SMC**, and Diodes Inc's BAT54C. They are now the BOM's own: MDD's
  SS34 (SMA, as the footprint) and Nexperia's BAT54C, both fetched from LCSC.
- **The green LED** numbers its anode 1, where KiCad's pad 1 is the cathode. The netlist is right
  by function (cathode to GND). The JLC CPL rotation was measured cathode-to-cathode by pin name,
  not by pad number (`tools/audit/jlc/`).

## Deep review

`analysis/deep_review.json`: 24 findings, every one with a datasheet quote and page or a script
result. `deep_review_gate.py` verified all 24, quarantined none.

**The console bus**

| Finding | Evidence |
|---|---|
| Cart → console: the A port drives the F3850's DB inputs (VIH 2.9 V) at 4.3 V. That is 1.4 V of margin, 0.8 V at 24 mA. A 3.3 V driver would have 0.4 V. | F3850 p23; SN74LVC4245A p6; `margins.py` |
| Console → cart: the F3850's 3.9 / 4.4 V outputs into the A port's TTL VIH 2.0 V; the B port's 2.8 V into the RP2040's VIH 2.0 V | F3850 p23; SN74LVC4245A p5, p7 |
| DIR is held high through RP reset by 4.7k against the 50-80k pad pull-down: 2.74 V | SN74LVC4245A p1; RP2040 p615 |
| VCCA is on CONS_5V, ahead of the OR diode. Ioff isolates the A port with the console off, so USB cannot back-power the console. | SN74LVC4245A p1; `check_nets.py` |
| /INTREQ is an open drain (2N7002 from GP16, 100k pull-down) | F3850 p23; 2N7002 p2 |
| No RP2040 pin touches a 5 V or edge net | RP2040 p615; `check_nets.py` |

**The edge**

| Finding | Evidence |
|---|---|
| The fingers' face, order, pitch, slot and pin-1 side match aotta's console-proven board and fart's footprint | `edge_orientation.py` |
| Fingers 21 (spare) and 22 (+12 V) are bare. The gerbers show no other copper within 1 mm and no inner-plane copper in the field. | `check_gerbers.py` 3 / 4 / 7 |

**The RP2040 and its layout**

| Finding | Evidence |
|---|---|
| VREG_VOUT 1 uF at 5.3 mm of copper from pin 45, no via; the two DVDD 100 nF at 7.1 / 8.9 mm | Hardware design with RP2040 p9; `layout_checks` 1 |
| VREG_VIN 1 uF at 3.0 mm; USB_VDD and IOVDD 49 share one via and capacitor (Raspberry Pi's own minimal design) | p9; `layout_checks` 2 |
| The 27R sit 2.3 / 5.5 mm of copper from pins 46 / 47 | p12; `layout_checks` 3 |
| Crystal: 2 x 15 pF + stray = 9.5-12.5 pF for CL 10 pF; XIN is 4.4 mm | ABM8 p1; p11; `margins.py`, `layout_checks` 5 |
| Exposed pads: 9 GND vias in the RP2040's, 9 in the CP2102N's | `layout_checks` 6 |

**Power**

| Finding | Evidence |
|---|---|
| +5V from the console is at least 4.30 V. That is above the AP63203's 3.8 V minimum input and the AP2112K's 3.3 V + 0.25 V dropout, and 5.25 V is under the AP2112K's 6 V. | SS34 p1; AP63203 p1; AP2112K p1, p3 |
| **WARNING:** the +5V peak is ~405 mA from the console's 7805, which also runs the console | ESP32-S3-WROOM-1 p28; `margins.py` |
| The AP63203's input loop closes on F.Cu: 1.6 mm from each pin to the 100 nF, no via, 7.0 mm around (3.8 mm of it inside the parts) | AP63203 p15; `layout_checks` 4 |
| The 6.8 uH inductor is not Table 2's 3.9 uH. That table assumes 12 V in and a 2 A load. At 5 V in, the ripple is 0.15 A, 41 % of the S3 side's peak (the datasheet asks 30-50 %), and 6.8 uH is inside its 2.2-10 uH range. | AP63203 p13; `margins.py` |
| AP2112K dissipation ~66 mW worst case | AP2112K p1 |

**The FujiNet half**

| Finding | Evidence |
|---|---|
| The antenna keep-out is empty on every layer | WROOM-1 p46; `layout_checks` 8 |
| The 3V3 pin's 100 nF and 22 uF sit 2.3 / 4.6 mm from it, as in the datasheet's peripheral schematic | WROOM-1 p41; `layout_checks` 9 |
| S3 EN: a 10k / 1 uF RC, as recommended | WROOM-1 p41 |
| WS2812B on +5V (3.7-5.3 V); the green LED at 1.8 mA | WS2812B p3; KT-0603G p3 |
| CP2102N VBUS sense: 22k / 47k gives 3.4 V | CP2102N p8 |
| USB pair skew 0.5 / 1.3 / 3.2 mm (UBRG / S3 / RP), under 20 ps against 4-20 ns full-speed edges | `layout_checks` 7 |

## Signal analysis

- **SPICE** (`simulate_subcircuits.py` with `extract_parasitics.py`, ngspice): 15 / 15 subcircuits
  pass: dividers, RC filters, decoupling.
- **Level shifters:** both '4245s detected, with their supply domains (CONS_5V A / +3V3_RP B).
- **Crystal:** 12 MHz, load capacitance as above.
- **RC filter R1 / C7 at 15.9 Hz:** the S3 EN delay (10k / 1 uF).
- **Protection:** ESD5Z on D+, D- and VBUS at the USB-C (see [Open questions](#open-questions)).
  The edge has no ESD part: no Videocart carries one, and every edge line meets a '4245 A port
  or the 2N7002.

## Power

- **Budget** (`margins.py`):
  - +5V peak ~405 mA;
  - the S3 side's 0.36 A comes through the buck;
  - the RP side's 40 mA comes through the LDO.
- **Thermal** (`analyze_thermal`): score 100, 0.22 W on the whole board. The hottest part is the
  AP2112K, at an estimated 81 °C. That figure is a heuristic: `margins.py`'s worst case is
  66 mW, +12 °C over ambient at the SOT-23-5's θJA of 184 °C/W (AP2112K p3).
- **Sequencing:** no enables or power-good chains. The AP63203's EN is tied to VIN, and the LDO's
  EN to +5V.

## PCB layout

`docs/floorplan-study.md` has the floorplan, the variants and the routing record.

| | |
|---|---|
| Outline | 77 x 131.5 mm. The 68.3 mm tab is straight for 30 mm with no parts, under a 45° taper. Four 5.6 mm NPTH holes on the original shell's bosses. |
| Stack-up | JLC04161H-7628, 1.6 mm: F.Cu signal + GND pour / In1 GND / In2 power islands (+3V3, +3V3_RP, +5V, CONS_5V) / B.Cu signal + GND pour |
| Routing | 768 segments, 1504 mm on F.Cu and 982 mm on B.Cu. Tracks 0.2 mm, with 54 segments necked to 0.15 mm at the 0.4 mm-pitch QFNs. Power 0.5-0.8 mm. |
| Vias | 758. 741 are 0.6 / 0.3, 11 are 0.8 / 0.4 (power), and 6 are 0.5 / 0.25 (the USB-C's D- join). 588 are GND: 488 of them stitching (a 4 mm grid, a 1.2 mm edge row, and 61 beside signal vias). `check_vias`: none in a foreign pad. |
| Rules | Clearance 0.15 mm, 0.12 mm at the QFN pins (DRU). Within JLCPCB's 4-layer capability (0.09 mm track / space, 0.25 / 0.15 mm via). |

**Edge clearance.**

- **Every part but the edge-mounted ones is at least 1 mm inside the body's long sides:** D7 /
  FID2 / C6 were moved in V10.
- **The microSD (J3) is 0.2 mm from the grip edge,** the USB-C 0.85 mm and the S3 antenna flush.
  All three are by design: the card, the plug and the antenna face out of the grip end. No rail
  goes on that edge.

### PCB / EMC findings, triaged

| Finding (rule) | Count | Triage |
|---|---|---|
| KO-001 keep-out "violations" | 6 | Deliberate rule areas. Each shell-boss keep-out contains its own hole H1-H4. The tab keep-outs allow the edge's fingers and forbid everything else. |
| RP-001 no GND via within 1 mm of a layer change (error) | 4 | UBRG_DM: the USB-C's two D- pads joined through vias right under the connector, no room (as on the SMS and 7800 boards). QSPI_SCLK: one via under the RP2040, the other in the dense flash corner where `stitch_gnd` found no legal spot; its B.Cu run is referenced to the In2 +3V3_RP island that both chips sit on and decouple. XOUT: the locked via in the RP2040's pin ring. SWCLK: under the RP2040, a debug line. |
| RP-001 (warning / info) | 3 / 15 | CONS_5V is a supply. The rest are bus and SD lines that `stitch_gnd` could give no room. In1 is solid GND under F.Cu across the whole body. |
| DC-002 no decoupling near U2 | 1 | U2 is the UMH3N transistor pair: no supply pin |
| DC-003 C14 far from a via | 1 | C14 is the AP63203's bootstrap capacitor, SW to BST: it has no via by nature |
| GP-001 partial reference-plane gap | 10 | The bus lines and CONS_5V cross the finger field, plane-free by design (no inner copper may enter the console's connector). 89-95 % covered. |
| CC-002 0.15 mm signals | 7 | Neck-downs at the 0.4 mm-pitch QFNs, carrying logic currents |
| CK-001 clock on an outer layer | 6 | A 4-layer board has only outer signal layers. XIN / XOUT are millimetres long; F.Cu is over solid In1. |
| CK-003 SD_SCK near J3 | 1 | It is J3's own clock |
| BE-002 edge ground pour incomplete | 1 | The tab and the antenna keep-out are pour-free by design |
| PM-002 J3 0.2 mm from the edge | 1 | Edge-mounted at the grip end, by design |
| XT-001 RP_D3 / RP_D4 parallel 18 mm | 1 | Translator B port → RP2040, sampled long after the edges settle at the F8's 1.79 MHz |
| SW-001 buck harmonics | 3 | Heuristic. 1.1 MHz with frequency spread spectrum; input loop on F.Cu, 7 mm around. |
| TE-001 test-point coverage 6 % | 1 | Bring-up pads on the bus control lines, DIR, SWD, RUN and the rails: deliberate for a prototype |
| CP-002 no copper under H1-H4 | 5 | NPTH holes with copper-free rings |
| GR-004 paste on 35 % of copper flashes | 1 | The 758 vias, 22 fingers, 12 test pads and 3 fiducials carry no paste |
| DFM-001 over 100 x 100 mm | 1 | The Videocart shell sets the size |

The EMC score is 40 / 100 with no critical findings. It counts the three worst findings of each
rule, so the RP-001 and KO-001 entries above dominate it.

### Release-gate waivers

`fab_release_gate --strict`: 10 pass, 2 fail, both waived:

| Gate item | Why it is waived |
|---|---|
| Component count: schematic 99, PCB 106 | The PCB adds seven board-only footprints: H1-H4 (the shell bosses) and FID1-3. KiCad's schematic parity finds 0 issues, and `cross_verify` matches all 99. |
| Layer alignment: heights differ by 13.8 mm | Deliberate. In1, In2 and F.Cu stop at the finger field: no inner or top copper enters the console's connector. The paste layers stop above the 30 mm tab. |

## Manufacturing

| Gate | Result |
|---|---|
| `check_fab.py` | 10 / 10: parts = BOM = CPL (86); LCSC codes, MPNs and manufacturers on every line; CPL rotations measured for every row; drill count; the order-number spot |
| `check_gerbers.py` | 4-layer set; tab, body and slot sides; the slot's round top; 22 fingers at their pins' x, 1.8 mm wide, 0.5-12.0 mm in; nothing between the fingers or within 1 mm of 21 / 22; F.Cu, In1 and In2 empty in the field; mask window; no paste, silk or drill hit in the field; the four boss holes |
| JLC CPL | Every (footprint, LCSC) pair measured pad by pad against its EasyEDA footprint. Three are medium confidence: TL3342, BAT54C, USB-C. Check them in the placement preview. |
| Order | `exports/jlcpcb/ORDER-JLCPCB.md`: 4 layers, ENIG, hard-gold fingers with a 30-45° bevel on the tab edge only, Standard PCBA, top side. Rails, if JLCPCB asks for them, go on the body's long sides only. |

## Lifecycle

`lifecycle_audit.py --only lcsc` reports all 35 MPNs as "unknown". The LCSC source carries no
lifecycle status for that script, by construction.

`tools/audit/sourcing.py` reads LCSC's own product-cycle flag instead (`docs/sourcing.md`):

- 37 of 38 lines are "normal" (active).
- LCSC has no record for the inductor's code (C62684, Sunlord SWPA4030S6R8MT). JLCPCB lists it,
  with 16k in stock.

No DigiKey / Mouser / element14 keys are configured, so there is no distributor end-of-life
status.

## Open questions

These two would change the circuit, so they are left for the user.

1. **USB D+ / D- protection (D4, D6).** The ESD5Z5.0T1G is a general-purpose TVS: 80 pF maximum
   at 0 V. The CP2102N datasheet's connection diagrams show "SP0503BAHTG or equivalent USB ESD"
   (p7-9). The ESD5Z is the same choice as the SMS, 7800 and 5200 boards.
   - Full speed tolerates the extra capacitance, but it eats into the rise-time margin.
   - A low-capacitance array would be a footprint change and a re-route.
   - The USB-C is only for flashing and the S3's console.
2. **CP2102N RSTb pull-up (R_CPRST).** It is 10k. The datasheet says "In all cases, a 1 kΩ
   pull-up on the RSTb pin is recommended" (p5). 1k is already on the BOM (0603WAF1001T5E), so it
   is a value change only, with no layout change.

## Not performed / review limits

- **Distributor lifecycle status:** no API keys; LCSC's product-cycle flag stands in (above).
- **Signal integrity and power integrity beyond kicad-happy's decks.** The bus runs at 1.79 MHz.
  The USB pairs are full speed, routed at netclass width over In1, not impedance-controlled.
  Controlled impedance is not ordered.
- **Thermal analysis:** the analyzer assessed one component (the AP2112K). `margins.py` covers
  the LDO by hand. The other parts dissipate milliwatts.
- **The console side is not measured:** the 7805's headroom with the cart's Wi-Fi peak; the
  connector's reach and door swing (hence the parts-free tab); the slot's thickness tolerance
  (1.6 mm, as aotta's board).
- **Firmware:** `check_nets.py` checks the netlist against the firmware headers. Its one warning
  is the pin map's missing `PIN_RP2040_RUN` / `_BOOTSEL` (README, open item 1).

## What a Rev1 could improve

- A low-capacitance USB ESD array, if open question 1 is not taken up in Rev0.
- QSPI_SCLK on F.Cu only, with no layer change, now that the board's routing is known.
- The tab's 30 mm parts-free length could shrink to 15 mm once a console's connector is measured.

## Post-review change (2026-10-11): the fab zip re-plotted from refilled zones

The gerbers are plotted from the zone fills saved in the board file. `stitch_gnd.py` adds its GND vias to
the file after the last fill, so the saved inner pours still covered them. The committed zip put
**476 plated holes inside an inner-layer pour of another net**: GND vias inside the power planes.
A board made from it would have had GND shorted to the planes. The DRC gate checked fresh fills in memory
(`--refill-zones`), so it passed. Found on FujiNet-StudioII Rev0.

- `tools/fill_zones.py` refills and saves the board; the DRC gate now runs on the saved fills
  (identical results to before).
- `tools/export.py` plots with `--check-zones`.
- `tools/audit/check_plane_shorts.py` checks each zip: every plated hole takes its net from the copper flashed
  at it (KiCad's X2 attributes), and no inner pour of another net may contain it. Now: 0.
- Re-exported: only the copper layers' pours changed (In2 and the outer pours; drills unchanged). Outside the zone fills the board is unchanged.
