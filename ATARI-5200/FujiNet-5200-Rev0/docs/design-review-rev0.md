# FujiNet-5200 Rev0: design review

Two parts:

- **Part 1** is the schematic audit. It covers the first Rev0 schematic (the one this
  regeneration replaces), what the console's own documents say about the edge, and the circuit
  as rebuilt.
- **Part 2** is the layout, the fab packages and the PCB-stage audit.

Every number below comes from a script in this project and can be re-run:

| Script | What it checks |
|---|---|
| `tools/check_nets.py` | netlist vs firmware headers |
| `tools/check_glue.py` | the '541 enable vs `a52_glue_drive()` |
| `tools/audit/edge_orientation.py` | the edge footprint vs its sources |
| `tools/audit/spice_checks.py` | ngspice decks |
| `tools/audit/margins.py` | logic levels and power budgets |
| `tools/audit/timing_margins.py` | bus timing |
| `tools/audit/sourcing.py` | JLCPCB stock |
| `tools/audit/make_deep_review.py` | the datasheet-cited findings, through kicad-happy's evidence gate |

Run them all with `tools/audit/run_sch_audit.sh` and `tools/audit/run_pcb_audit.sh`.

## Part 1: schematic audit

### Sources

**The console.** Atari's CX5200 Field Service Manual, Rev 4 (July 1983), saved as
`datasheets/CX5200-FSM.pdf`. It has schematics of the three console boards and their parts lists:

- **CA018087**: the original 4-port.
- **CA020108**: the universal 4-port.
- **CA021374**: the 2-port.

The universal boards are the VCS-adaptor-ready ones.

**The edge geometry.** Four sources, cross-checked against each other:

- the Grand Idea Studio "Pixels Past" 5200 cart's rev B gerbers, traced from the fingers to the
  EPROM;
- tdididit's a52 Eagle library and flash cart;
- sanni's cartreader 5200 adapter, plus a photo of a cart seated in it;
- the Sullins connector that substitutes for Atari's C018081.

**The firmware contract.**

- fujinet-firmware `pico/atari-5200/firmware/include/a52_cart.h`, on branch add-5200.
- fn-5200-board `include/pinmap/fujiversal-atari5200.h`.

**The parts.** Manufacturer datasheets in `datasheets/`, one per BOM line.

### What the first Rev0 had wrong

| # | First Rev0 | What the console does | Now |
|---|---|---|---|
| 1 | Edge 24 to GND, 23 open | 23 is GND (shield) on every board. 24 is GND only on CA018087. On the universal boards it is **video in** through CR10, so grounding it shorts the VCS adaptor's video. | 23 GND, 24 open |
| 2 | Edge 11 "NC" | **Raw DC** from the adapter (9-13 V) on the universal boards. It is live ahead of the power switch, so it must never be grounded. | JP2 (bridged) -> 0.35 A PTC -> 2.2R -> AP63205 5 V buck -> SS34 onto +5V. While it is present, the console path turns off. |
| 3 | Edge 26 "+5 or +12 V", through an AP63205 | **+5 V from VR1** only, a 78M05 (0.5 A) on CA018087. VR1 also feeds the console RAM and controllers. The buck's 4 ms soft-start would have sat between the console bus and the RP2354B's IOVDD. The FT pads are 5 V-tolerant only while IOVDD is up. | CONS_5V -> AO3401A -> +5V; the RP's LDO rises with it |
| 4 | Edge 14 into GPIO25 through 1k | On the 2-port, PHI2 comes through **CR9, a 1N914 with its anode at pin 14**: the console can only pull it low, and only to ~1 V. The first Rev0 would have read neither level. | 4.7k pull-up to CONS_5V + 74LVC1G17 Schmitt at 5 V |
| 5 | Interlock switch: P-FET, S on 36, D on 18 | The stock jumper closes Q8 / Q6's base circuit at **~0.2 V, 34-61 mA**. A P-FET can never turn on at ground potential. | N-FET low side (2N7002, D = 36, S = 18), gate pulled to +5V, 2N7002 driver on GPIO28 with a 4.7k E9 pull-down; all DNP, JP1 bridged |
| 6 | Every finger the same length | Pins 18 / 36 are **short** on every stock and open board, so the interlock makes last and breaks first. | Copper from 1.9 mm (others 0.6 mm) |
| 7 | Edge dimensions "provisional" | Measured from the sources above | Tab 47.8 mm; fingers 1.78 mm, 0.6-7.0 mm; F.Cu = label face, pin 1 left |
| 8 | VSENSE_ADC 100k / 22k, for a 12 V pin 26 | Pin 26 is 5 V | 100k / 100k (0.5 x: 2.25-2.75 V for 4.5-5.5 V) |
| 9 | PWR_OK divider 47k / 100k | Pin 26 is 5 V | 22k / 100k (0.82 x), as SMS |
| 10 | README: "no 74HCT08 at JLCPCB" | jlcsearch's index misses it. JLCPCB's own API shows SN74HCT08DR C6767 in stock. | SN74HCT08DR |
| 11 | WS2812C-2020-V1 | 0 stock | WS2812B-2020-V6 (same package and pin order; VIH 2.7 V; 12 mA per channel) |

The enables are pure 74LS139 decodes of A14 / A15, and that decoder's enable input is grounded,
so they are not qualified by PHI2. There is no R/W on the edge. The '541 therefore also drives
during CPU writes to $4000-$BFFF, exactly as a stock ROM does with /CE = /OE = the enable.

### The circuit as rebuilt (`tools/design.py`)

**Cart bus.** Edge -> 74HCT541 -> console. It works like a mask ROM:

- The RP2354B follows A0-A13 and the two enables on GPIO0-15, its 5 V-tolerant pads, and puts
  the byte on GPIO16-23.
- The 74HCT541 drives D0-D7 only while all three hold:
  - an enable is low (74HCT08: /OE1 = /EN40 AND /EN80);
  - the console is powered (PWR_OK, through the 74HCT14);
  - the RP is serving (BUF_EN, GPIO26, with a 4.7k pull-down).

  This is `a52_glue_drive()`, checked for all 16 input combinations.
- The '541's channels are taken in reverse, so the data path is planar on the board.

**Power.** +5V is the OR of three sources:

- the console's 5 V through a P-FET that CONS_OFF turns off;
- USB VBUS through an SS34;
- the edge's raw DC through the AP63205 and an SS34.

CONS_OFF = VBUS OR PRE5V, through a BAT54C. +5V feeds:

- the '541, the '08, the '14 and the LVC1G17;
- the WS2812B;
- the AP2112K LDO, which makes +3V3_RP for every RP2354B supply pin;
- the AP63203 buck, which makes +3V3 for the S3, the microSD and the CP2102N.

**The FujiNet half** is the SMS / 7800 / NES circuit, unchanged:

- ESP32-S3-WROOM-1-N16R8 (fujiversal-atari5200), the USB host of the RP on IO19/20, and the
  RP's RUN / BOOTSEL on IO4 / IO5;
- microSD;
- USB-C with a CP2102N and the UMH3N auto-program pair;
- the buttons.

### Checks

| Check | Result |
|---|---|
| ERC, all severities | 0 |
| `check_nets.py` (netlist vs `a52_cart.h`, the FSM edge map, the S3 pin map, FT-pad rules) | 366 / 366 |
| `check_glue.py` | 16 / 16, 5 unused gates tied off |
| `gen_sch` netlist parity (drawn sheets vs `design.py`, names included) | every net |
| Mirror check (each sheet's major parts in board order) | tau 1.00 / 1.00 on all five sheets |
| `edge_orientation.py` | OK |
| kicad-happy `analyze_schematic` | 154 components, 178 nets, 84 detector findings (triaged below) |
| kicad-happy SPICE (`simulate_subcircuits`) | 21 / 21 pass |
| Deep review (`make_deep_review.py` through `deep_review_gate.py`) | 30 findings, 30 verified against the datasheet pages, 0 quarantined |

### Numbers worth knowing

**PHI2** (`spice_checks.py` 3):

- The 2-port's low reaches the cart at 0.94-1.09 V. The LVC1G17's VT- min is 1.32 V, which
  leaves +0.24 V at the worst corner.
- The high is 4.2-4.8 V.
- The edge passes VT+ max within 57 ns at 25 pF, against a 279 ns half period.
- The pull-up goes to CONS_5V, not +5V. With the console off and USB on, a pull-up to +5V would
  forward-bias CR9 into the unpowered LS125.

**PWR_OK** (`spice_checks.py` 1):

- The divider gives 3.69 V at a 4.5 V console rail, against the HCT14's VT+ max of 1.9 V.
- PWR_OK is high once the rail passes 2.3-2.6 V, and drops below 0.6-1.7 V.

**The console path** (`spice_checks.py` 2):

- 500 uA of leakage from each SS34 still leaves VGS at -2.9 V (RDS(on) specified at -2.5 V).
- After a USB unplug, VGS passes -2.5 V in 3.1 ms. Until then the body diode carries the console.
- With raw DC running the cart, the console still supplies part of the load through the body
  diode only at the tolerance corner: up to 85 mA with VR1 at 5.25 V and PRE5V at 4.95 V.

**Bus timing** (`timing_margins.py`):

- The byte reaches D0-D7 125 ns after the address reaches the edge. That is the LS244 plus the
  RP following the address (65 ns, PROVISIONAL: firmware) plus the '541 at 150 pF.
- The enable path takes 118 ns.
- At 1.79 MHz with 2 MHz-grade 6502 timing the margin is +234 ns. With 1 MHz-grade figures it is
  +34 ns.

**Levels** (`margins.py`):

| Path | Margin |
|---|---|
| RP -> HCT | +0.62 V |
| Console NMOS / LS -> RP FT pads | +0.40 / +0.70 V |
| '541 -> console bus | VOH 3.84 V at -6 mA |
| BUF_EN, 4.7k E9 pull-down | 0.56 V worst, under VIL 0.8 V |

### Warning: the console's VR1 budget

The cart draws:

- ~470 mA at a WiFi TX burst: S3 TX 355 mA and the microSD through the buck, plus the RP, the
  logic and the WS2812B at full white;
- ~170 mA on average.

On CA018087, VR1 is a **0.5 A 78M05** that also feeds the console RAM and controllers. There is
no raw DC on that board's pin 11. So without USB, a burst can pull VR1 into current limit.

- On the universal boards the edge raw DC takes the whole cart and the console path opens.
- With USB plugged in, USB carries the cart.

**Mitigation, in the README:**

- On an original 4-port, run WiFi with USB power.
- Firmware should cap the S3's TX power when the cart runs from VR1.
- At bring-up, measure CONS_5V at TP17 during TX.

### Other findings, triaged

| Finding (rule) | Count | Triage |
|---|---|---|
| VM-001 voltage-domain crossings | 12 | Deliberate. RP 3.3 V outputs go into 74HCT inputs (VIH 2.0 V): RP_D0-7, BUF_EN. 5 V signals go into RP FT pads, which are 5.5 V-tolerant with IOVDD up: /EN40, /EN80, PHI2_RP. The analyzer does not see the console's A0-A13 as a 5 V domain; those are FT pads too. |
| RS-001 nets with no source | 3 | PWR_OK and PWR_OK_N are 74HCT14 outputs. VBUS_SNS is a divider node. None is a rail. |
| PU-001 CP2102N CHREN | 1 | Charger-detect output, open as on the ESP32-S3-DevKitC-1 |
| LB-001 multiple hierarchical labels | 9 | The analyzer counts the sheet-pin labels at both ends of a cross-sheet net |
| EP-AUD ESD coverage | 4 | J1 is the cart edge. No 5200 cart carries ESD parts, and the RP2350 FT pads have enhanced ESD protection. J3 is the microSD, inside the shell. J4 is the DNP debug header. USB-C has ESD5Z on D+, D- and VBUS. |
| VD-004 "over-designed" 0603 | 2 | 0603 is the board's passive size |
| PS-001 no PG pin | 1 | The AP63203 has none |
| DO-DET, DC-DET, PR-DET, TR-DET, VD-DET, ... | 40+ | Detections, not findings |

## Part 2: layout, fab packages and the PCB audit

### Verdict

**Ready to order as a bring-up prototype, at JLCPCB or PCBWay.**

- The board is fully routed: DRC finds 0 violations, 0 unconnected and 0 schematic-parity issues
  at every severity.
- Both fab packages pass `check_fab.py` and `check_gerbers.py`.
- Every BOM line is in JLCPCB stock.

**No blockers.** One warning carries over from Part 1: the original 4-port's VR1 budget during
WiFi bursts. It needs USB power or a TX cap; it does not need a board change.

Open before ordering:

- lay a real cart on the 1:1 tab overlay;
- check the placement preview;
- re-run sourcing on the order day.

### The board

`docs/floorplan-study.md` has the floorplan and the routing record.

- **Outline:** 84 x 98 mm, T-shaped. The 47.8 mm tab has hard-gold fingers with a 30-45 degree
  bevel; pins 18 / 36 are short.
- **Stack:** 6 layers, 1.6 mm, ENIG.
- **Data path:** finger -> 74HCT541 -> RP2354B GPIO16-23 is locked and planar on F.Cu.
- **RP2354B bus pins:** A8-A13, /EN40 and /EN80 have a locked alternate inward / outward escape
  (`gen_pcb.BUS_ESCAPE`). Without it, Freerouting walled A10 and A13 in, in every one of six
  variants.
- **Routing:** 1183 segments and 594 vias. Signals use F.Cu, In2, In3 and B.Cu; In1 is GND and
  In4 carries the power islands. The tracks are 0.2 mm (0.15 mm at 8 RP neck-downs). There are
  358 GND vias, 230 of them stitching.
- **Fab rules:** the smallest via is 0.25 / 0.50 mm, inside JLCPCB's and PCBWay's standard 6-layer
  capability.

| Gate | Result |
|---|---|
| `kicad-cli pcb drc --schematic-parity --severity-all` | 0 / 0 / 0 |
| `tools/check_vias.py` | 594 vias, none in a foreign pad |
| `tools/audit/check_fab.py` | 14 / 14 |
| `tools/audit/check_gerbers.py` | Checks: zips identical but the silkscreen; 18 fingers per face at their pins' x; 18 / 36 from 1.9 mm; mask windows; no inner copper or drill hits in the finger field; no paste on the tab |
| JLC CPL | Every one of the 45 (footprint, LCSC) pairs measured pad by pad against its EasyEDA footprint (`tools/audit/jlc/`); all high confidence except five medium entries with symmetric land-pattern residuals |
| kicad-happy `fab_release_gate --strict` | 10 pass, 2 fail (both waived below) |

### Analyses run

- `analyze_schematic`
- `analyze_pcb --full --proximity`
- `cross_analysis`: 0 findings
- `cross_verify`: 139 / 139 components matched. The six "orphans" are the board-only fiducials
  and mounting holes. The DNP parts are placed but not fitted.
- `analyze_emc`: score 38.5, no critical findings
- `analyze_thermal`: score 100
- `simulate_subcircuits`: 21 / 21
- `analyze_gerbers`
- the deep review: 30 / 30 verified
- `fab_release_gate --strict`
- the project's own checks in Part 1

**Not run:**

- **The lifecycle / obsolescence audit.** No distributor API keys are configured.
  `tools/audit/sourcing.py` read JLCPCB's and LCSC's stock instead, so this is a gap for
  end-of-life status only.
- **SI / PI simulation beyond the kicad-happy decks.** It is not needed at 1.79 MHz bus speed,
  but the USB pair is routed to netclass width, not impedance-controlled.

**Prior run.** The analysis of the first Rev0 schematic (run `2026-10-08_2150`) and of this one
show the same detector classes: VM-001 x 11 / 12, RS-001 x 3, PU-001 x 1. None of Part 1's five
edge errors is visible to an analyzer. They came from the console's own schematics, which is
why Part 1 checked them against the FSM.

### Release-gate waivers

| Gate item | Why it is waived |
|---|---|
| Component count: schematic 130, PCB 145 | The PCB adds six board-only footprints: FID1-3 and H1-3, the shell screws. The analyzer's placeable count also leaves out the five DNP parts and folds multi-unit symbols. KiCad's own schematic parity finds 0 issues. |
| Layer alignment: heights differ by 10 mm | Deliberate. The inner planes stop 8.5 mm short of the insertion edge, so nothing but the fingers enters the connector, and there is no paste on the tab. |

### PCB findings, triaged

| Finding (rule) | Count | Triage |
|---|---|---|
| KO-001 keepout "violations" | 5 | Deliberate rule areas. The screw keep-outs contain their own holes H1-H3. The tab keep-outs allow the fingers' pads and forbid everything else. |
| DC-002 no decoupling near U1 / U3 | 2 | U3 (UMH3N) has no supply pin. U1 is the ESP32-S3 module: its 3V3 pin is 3.4 mm from the board's west edge, so C3 / C4 (22 uF + 100 nF) sit on its east side and reach it through the In4 +3V3 plane. The module carries its own decoupling. |
| GP-001 reference-plane gaps | 4 | D6 (75 % over 21.6 mm) is the finger stub through the plane-free finger field, by design. SD_SCK / SD_MOSI (83-86 %) and A12 cross the In4 +3V3 / +5V split on In3 / B.Cu: an EMC note for a 20-40 MHz SPI clock on a cart inside a shell. |
| RP-001 no stitching via at a layer change | 19 | stitch_gnd placed 230 GND vias. Three USB-pair vias had no room for a neighbour (as on the SMS and 7800 boards). In1 is a solid GND plane next to every signal layer. |
| PM-002 parts near the edge | 4 | By design: the microSD (J3) and USB-C open on the top edge; the S3 antenna is flush with it over its keep-out; SW1 / SW3 sit at the west edge under the shell's pinholes. FID2 was moved 4 mm in after this audit flagged it at 0.75 mm. |
| CK-001 crystal on F.Cu | 3 | The RP2350 minimal-design arrangement: 12 MHz, pre-routed and locked, millimetres long |
| CC-002 0.15 mm signals | 3 | Neck-downs at the RP's 0.4 mm pitch, carrying logic currents |
| SW-001 buck harmonics | 2 | Heuristic. AP63203 / AP63205 at 1.1 MHz with spread spectrum (+-6 %); both are compact, with input caps at the pins. |
| DC-003 C43 far from a via | 1 | C43 is the AP63205's bootstrap capacitor, SW to BST. It has no via by nature. |
| GP-005 two ground domains | 1 | There is one GND net. The second "domain" is unnamed (`?`) in the analyzer's output. |
| BE-002 edge ground pour 80 % | 1 | The tab and the antenna keep-out are deliberately pour-free |
| TS-003 / TP-001 AP2112K Tj 96 C | 1 / 5 | Heuristic that books the whole board's dissipation on the LDO. `margins.py`: 51-102 mW, +13-26 C. The thermal analyzer scores 100. |
| GR-004 paste on 45 % of pads | 1 | Fingers, test pads, fiducials and the bridged jumpers carry no paste |
| TE-001 test-point coverage 7 % | 1 | Bring-up pads are on every rail and source and on the bus control nets. That is deliberate for a prototype. |

### What a Rev1 could improve

- A dedicated 100 nF at the ESP32-S3's 3V3 pin. It would mean moving the module off the west
  edge.
- Route the SD clock on In2 (referenced to In1 GND) end to end.
- Should the 2-port adapter turn out softer than 9 V under load, an 0805 2.2R on the raw-DC path.
- Should the VR1 budget bite on CA018087 in practice, a firmware TX-power cap (Part 1).
