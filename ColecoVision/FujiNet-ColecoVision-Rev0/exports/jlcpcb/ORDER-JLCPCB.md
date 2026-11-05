# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `FujiNet-ColecoVision-Rev0-gerbers.zip`: gerbers + Excellon drill. Its bottom silkscreen carries the order-number text
  `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

## Before ordering (VERIFY)

1. **The edge.** `tools/audit/edge_orientation.py` passes: the pinout (MAME's ColecoVision slot table =
   the ADAM Technical Reference Manual's J1) and the footprint against two built, open carts
   (ThatOldNerd's Coleco-Game-Cart V4, Commodore-Bench's flash card): even pins on the component face,
   odd pins behind them, pin 1 / 2 at the left, 2.54 mm pitch.
2. **The shell.** The outline is the open carts' (40.0-40.6 mm wide, their notch positions); the 82.4 mm
   length is proven only in printed shells. Fit an original Coleco shell only after the checks in
   the README ("Original shell"); the printed shell (`case/`) is made for this board.
3. **Stock** (`python3 tools/audit/sourcing.py` re-reads it; `docs/sourcing.md`, 2026-11-05). The RP2350
   core inductor L1, AOTA-B201610S3R3-101-T (C42411119), swings between in stock and none (1 at
   JLCPCB on 2026-11-04). For a short line, buy it into your JLCPCB parts inventory first (Parts
   Manager, "Order parts", from LCSC) or consign it. Its alternate is TDK VLS201610HBX-3R3M-1 (C695624,
   same 2016 size; Raspberry Pi specifies the polarity-marked AOTA). The RP2354A / RP2354B were out of
   stock everywhere on 2026-11-04: this board uses the RP2350A (C42411118) + W25Q16JVUXIQ (C2843335).
4. **The thickness.** 1.6 mm is ordered: the slot (Sullins EBC15DRTH replacement) takes 1.57 +- 0.2 mm.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 +5V with +3V3 / +3V3_RP / DVDD / CONS_5V islands, B.Cu) |
| Size | 40.20 x 82.40 mm (the whole 40.2 mm bottom edge is the insertion edge) |
| Thickness | 1.6 mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 30 fingers (15 on each face, 2.54 mm pitch), **30 degree bevel** on the insertion edge |
| Minimum track / clearance | 0.15 mm / 0.12 mm (the RP2350A's 0.4 mm pitch); smallest via 0.25 mm drill / 0.50 mm pad (Raspberry Pi's QFN-60 land pattern) |
| Via in pad | the 3 x 3 vias in the RP2350A's exposed pad (Raspberry Pi's footprint) and the CP2102N's: plain, tented from B.Cu (no filling needed) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | the board is narrower than the 70 mm assembly minimum: let the fab add rails on the left and right edges only. Never on the insertion edge or the top edge (the USB-C, the microSD) |
| Outline | four side notches (the shell's ribs) and the chamfered finger corners: route them as drawn |

## Assembly

Top side only (B.Cu carries only the odd fingers and copper). 94 parts per board. Not fitted
(DNP): none. The 12 test pads are bare copper.

1. Upload the zip; set the options above.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2350A is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - U1 (RP2350A, QFN-60), U5 (W25Q16JV, USON-8), U4 (74LVC245A, TSSOP-20), U2 / U3
     (74LVC1G11 SOT-23-6 / 74LVC1G08 SOT-23-5), U6 (ESP32-S3-WROOM-1: the antenna at the west edge),
     U12 (AP2112K, SOT-23-5), U10 (TPS2116, SOT-583), U11 (AP63203, TSOT-23-6), U8 (CP2102N,
     QFN-28), U7 (USBLC6, SOT-23-6), U9 (UMH3N), D2 (BAT54C), J3 (USB-C, top edge),
     J2 (microSD: the card slot in the top edge), Y1 (crystal): pin 1 / orientation against the silkscreen.
   - D1 (red LED), D3 (WS2812B-2020): polarity / pin 1.
   - The regulator corner beside the RP2350A: L1 (AOTA 2016), C12, C14, C15, C16, R5, R12, R13 (0402, Raspberry Pi's
     minimal-design land pattern).
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start 0.50 mm from
   the edge (the +5V finger, 30, at 1.50 mm: it mates last) and run to 8.50 mm, 1.60 mm
   wide, on both faces, on purpose; no part sits closer than 15.0 mm to that edge.
