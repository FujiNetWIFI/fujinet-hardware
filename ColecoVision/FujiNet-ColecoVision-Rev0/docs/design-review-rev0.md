# FujiNet-ColecoVision Rev0: design review (2026-11-05)

**Runs:**
- `tools/audit/run_sch_audit.sh` and `tools/audit/run_pcb_audit.sh`: kicad-happy 2.2.1 (schematic, PCB, cross-check, EMC, thermal, SPICE and gerbers).
- `tools/audit/sourcing.py`.

**Output:** `analysis/` (gitignored) and `docs/sourcing.md`.

**Board status:** routed, every pipeline gate passing (README). SPICE: 14 / 14 subcircuits pass (dividers, RC filters, the crystal load).

## High-severity findings

| Rule | Count | Verdict |
|---|---|---|
| GP-001 "Signal has major reference plane gap" | 5 (+8 warnings) | **Accepted.** In2 is split into +5V / +3V3 / +3V3_RP / DVDD / CONS_5V islands, and B.Cu tracks cross island edges. The Z80 bus moves once per ~280 ns cycle, and In1 under F.Cu is solid GND. As on the sister carts. |
| KO-001 "Keepout violation" | 4 | **False positive.** The fiducials sit in their own clear circles, the fingers in the finger field. KiCad DRC checks the real shapes and passes. |
| PM-002 "FID2 is 0.45 mm from board edge" | 4 | **By design.** FID2 is in the bottom-right corner (its copper 1.2 mm from the edge). The USB-C (J3) and the microSD (J2) sit at the top edge so a shell opening reaches them, and the fingers are the edge. |
| RP-001 "Missing stitching via at layer transition: /usb/UBRG_*" | 3 | **Real, minor.** The bridge's full-speed pair (12 Mbit/s) changes layer at the receptacle's drawn D- join (`gen_pcb.usbc_link`) without a GND via beside it. As on the sister carts. |
| RP-002 "/rp-core/RP_USB_DP crosses +3V3_RP plane gap" | 2 | **Accepted.** The RP <-> S3 full-speed pair crosses from the +3V3_RP island to the +3V3 island; In1 (GND) is solid under both. |
| DC-001 "Decoupling cap too far from U7" | 1 | **Real, minor.** The USBLC6's VBUS (pin 5) is 9 mm from the receptacle's 100 nF (C_VBUSHF). Its VBUS pin is the clamp's reference; the receptacle-side caps are where VBUS enters. |
| DC-002 "No decoupling cap found near U9" | 1 | **False positive.** U9 is the UMH3N auto-program pair, with no supply pin. |
| PS-002 "+3V3_RP plane split: 2 islands" | 1 | **Not a split.** Measured on the saved fill: In2's +3V3_RP island fills as one 746 mm² piece, and KiCad's DRC finds no unconnected item. |

## Warnings worth a line

| Rule | Verdict |
|---|---|
| RP-001 x16 (signal layer changes without a GND via) | The bus crosses itself on two layers (the QFN's GPIO order puts address before data; the fingers have data first). `stitch_gnd` put 65 GND vias on the board. |
| CC-002 x6 (0.15 mm signal necks) | Grid-router links between 0.4 mm-pitch pins, and RP_A1's hand-placed line between RP_A0 and RP_A2 (see below). JLCPCB's minimum is 0.09 mm. |
| CK-001 / CK-003 SD_SCK on an outer layer near J2 | SPI to the microSD, a few MHz, short. As on the sister carts. |
| TS-003 AP2112K Tj 97 C | The analyzer assumes 168 mA. The real load is the RP2350A (~40 mA), the W25Q16, the bus logic and the LED: about 80 mW, Tj about 45 C (`margins.py`). |
| PU-001 CP2102N CHREN | Charger-detect output, unused, left open (as on the ESP32-S3-DevKitC-1). |
| SW-001 / SW-003 AP63203 harmonics and hot loop | 1.1 MHz buck. Its 22 uF input capacitor is 3.3 mm from VIN, the 100 nF 6.4 mm (`layout_checks` 2, 9). A pre-compliance item, as on the sister carts. |
| RS-001 VBUS_PR has no declared source | The TPS2116 PR1 divider's midpoint, driven by the 33k / 10k divider from VBUS. |

## Rev0 compromises (measured by `layout_checks`)

- **The bus crossing.** The QFN's counter-clockwise GPIO order puts the address group before the data group, while the fingers have the data group first, at any rotation of the RP. The 74LVC245A sits over the data fingers, so its A side is short, and its B side (GP15-22) crosses the address fan between the arrays and the RP and wraps the RP's north-east corner. The worst finger-to-part path has 4 vias.
- **The W25Q16's back row.** QSPI_SD2 and QSPI_SS go round the flash's far row: 22 and 24 mm against SCLK's 9.5 mm, about 90 ps of spread at a flash clock of 75 MHz or less.
- **Two decoupling distances.** The W25Q16's 100 nF is 6.3 mm from its VCC pin and the CP2102N's 6.2 mm, both ends on their supply island; the buck's 100 nF is 6.4 mm from VIN (its 22 uF at 3.3 mm).
- **RP_A1 by hand.** No router run joined it: Freerouting laid RP_A0 and RP_A2 0.37 mm apart. RP_A2's diagonal starts 0.6 mm lower and RP_A1 runs between them at 0.15 mm.

## Routing (what worked)

- **The edge first.** Freerouting never enters a finger's neck, so every edge net used to fall to the grid finisher, after Freerouting had filled the band. `placement.PRE_ROUTE` routes the 27 edge nets and the USB pair first with the grid router, locked.
- **The QSPI next.** In the full run, B.Cu through-traffic walls one QSPI line out of the flash corner. `tools/fr_subset.py` routes the six alone first.
- **Twenty-odd placement variants.** Isolated parallel variants (rsync + TMPDIR each) of the gate, array, buffer and crystal positions. This board is the one whose finisher left one link (RP_A1, above).

## Sourcing (2026-11-05, `docs/sourcing.md`)

45 lines, about USD 15.38 of parts per board. Two lines are short at JLCPCB for 5 boards:
- **U11 AP63203WU-7 (C780769), the S3's 3.3 V buck:** JLCPCB 0, LCSC 0 (79 on 2026-11-04). Consign it, use JLC Global Sourcing, or order from PCBWay (turnkey by MPN).
- **L1 AOTA-B201610S3R3-101-T (C42411119), the RP2350's core inductor:** JLCPCB 1, LCSC 0. The TDK VLS201610HBX-3R3M-1 (C695624, JLCPCB 343) has the same footprint, but Raspberry Pi specifies the polarity-marked AOTA; using it instead is a deliberate decision.

The RP2350A (C42411118, 3481) and the W25Q16JVUXIQ (C2843335, 2877) were in stock.
