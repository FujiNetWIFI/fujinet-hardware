# FujiNet-O2 Rev0: design review (2026-10-30)

**Runs:**
- `tools/audit/run_sch_audit.sh` and `tools/audit/run_pcb_audit.sh`: kicad-happy 2.2.1 (schematic, PCB, cross-check, EMC, thermal, SPICE and gerbers).
- `tools/audit/sourcing.py`.

**Output:** `analysis/` (gitignored) and `docs/sourcing.md`.

**Board status:** routed, every pipeline gate passing (README). SPICE: 15 / 15 subcircuits pass (dividers, RC filters, the crystal load).

## High-severity findings

| Rule | Count | Verdict |
|---|---|---|
| KO-001 "Keepout violation" | 7 | **False positive.** Six are parts inside their own rule areas: the edge's fingers in the finger field, the two post holes and the three fiducials in their clear circles. The seventh is a GND stitching via 2.1 mm from FID2's centre, outside its 1.6 mm clear circle but inside the circle's bounding box (the analyzer checks boxes). KiCad DRC checks the real shapes and passes. |
| GP-001 "Signal has significant reference plane gap" | 6 (+21 warnings) | **Accepted.** In2 is split into +5V / +3V3 / +3V3_RP / CONS_5V islands, and B.Cu bus tracks cross island edges in the band between the resistors and the fingers. The bus moves once per ~2.8 us 8048 machine cycle (/PSEN ~1 us), and In1 under F.Cu is solid GND. As on the sister carts. |
| PM-002 "J2 is 0.0 mm from board edge" | 2 | **By design.** The microSD card slot (J2) and the USB-C mouth (J3) sit at the left and top edges, so a shell opening reaches them. |
| DC-002 "No decoupling cap found near U5" | 1 | **False positive.** U5 is the UMH3N auto-program transistor pair, with no supply pin. (kicad-happy 2.2.1 applies `.kicad-happy.json` suppressions in its EMC and thermal analyzers only.) |
| RP-001 "Missing stitching via at layer transition: /USB_DM" | 1 | **Real, minor.** The RP <-> S3 USB pair (full speed, 12 Mbit/s) changes layer once without a GND via beside it. Its skew is 2.9 mm / 19 ps (`layout_checks` 6). The sister carts carry the same item. |

## Warnings worth a line

| Rule | Verdict |
|---|---|
| RP-001 x20 (bus layer changes without a GND via) | The band carries the address and data groups across each other on two layers. `stitch_gnd` put 124 GND vias on the board. Accepted for a ~1 us bus. |
| CC-002 x7 (0.15 mm signal necks) | `finish_route --neck` links between fine-pitch pins and the band's bus lines; 0.15 mm is above JLCPCB's 0.09 / 0.127 mm, and these are logic-level lines. |
| PS-002 "+3V3_RP plane split: 10 islands" | Measured on the saved fill: In2's +3V3_RP island fills as one 764 mm2 piece carrying all 20 of its vias (the RP's ring corners, its caps, the LDO). The two other +3V3_RP vias belong to routed tracks (the RUN pull-up). Not a split supply. |
| CK-001 / CK-003 SD_SCK on an outer layer near J2 | SPI to the microSD, a few MHz, short. Accepted (as on the sister carts). |
| TS-003 AP2112K Tj 96 C | The analyzer assumes 168 mA. The real load is the RP2354B (~45 mA), the LED and pull-ups: (5.0 - 3.3) V x 50 mA = 85 mW, so Tj is about 41 C (`margins.py`). |
| PU-001 CP2102N CHREN | Charger-detect output, unused, left open (as on the ESP32-S3-DevKitC-1). |
| SW-001 / SW-003 U7 buck harmonics and hot loop | AP63203 at 1.1 MHz. Its input caps sit 2.3 / 3.6 mm from VIN (`layout_checks` 9). The same pre-compliance item as on the sister carts. |
| RS-001 VBUS_PR has no declared source | The TPS2116 PR1 divider's midpoint; driven by the 33k / 10k divider from VBUS. |
| CG-AUD J1 28:1 signal-to-ground ratio | The console's edge has one GND contact (C), by the published pinout. |

## Rev0 compromises (measured by `layout_checks`)

- **The south side's supply pins** (IOVDD 5 and 15, DVDD 10) are boxed in by the bus: every RP2354B pin on the south side but these three is a bus line. They stub inward to the +3V3_RP / DVDD rings under the package (as every supply pin does), and their capacitors sit north of the RP, 14-15 mm away through the rings (limit 17 for these three, 14 for the rest).
- **The bus band.** The QFN's counter-clockwise GPIO order puts the address group west and the data group east at the RP. The fingers have them the other way round, so the two groups cross between the resistors and the fingers, on two layers. The worst finger-to-resistor path has 7 vias.
- **The block positions** come from seven trial placements around the first one. This is the one whose route has no bus line over 7 vias; the others left one or more lines at 9-13 vias, or one or two open.

## Sourcing (2026-10-30, `docs/sourcing.md`)

41 lines, about USD 13.84 of parts per board. One line is short at JLCPCB for 5 boards:
- **Y1 ABM8-272-T3 (C20625731), the RP2350's 12 MHz crystal:** JLCPCB 0, LCSC 57.
  - Buy them into the JLCPCB parts inventory (Parts Manager, "Order parts"), or consign.
  - It is Raspberry Pi's minimal-design part (CL 10 pF, the 15 pF loads and the 1k in XOUT are sized for it); a substitute is a decision to make deliberately.

The RP2354B (C39843328) and the AOTA core inductor (C42411119) were in stock that day (JLCPCB 90 and 644).
