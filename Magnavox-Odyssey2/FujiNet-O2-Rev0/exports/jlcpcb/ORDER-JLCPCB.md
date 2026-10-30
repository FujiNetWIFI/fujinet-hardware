# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `FujiNet-O2-Rev0-gerbers.zip`: gerbers + Excellon drill. Its top silkscreen carries the order-number text
  `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

## Before ordering (VERIFY)

1. **The edge.** `tools/audit/edge_orientation.py` passes: the pinout (Dan Boris's O2 Tech Specs) and
   the footprint against three built Videopac carts (bwack's USBCART, PicoPAC, wilco2009's microSD
   cart): pins 1-15 on the parts face, A-R behind them, 3.9286 mm pitch. Not measured on an
   original cart: its exact pitch (built carts use 3.93-3.96 mm; all play) and its label face.
2. **Stock** (`python3 tools/audit/sourcing.py` re-reads it; `docs/sourcing.md`, 2026-10-30). On 2026-10-30
   the crystal Y1, ABM8-272-T3 (C20625731), was short at JLCPCB (0; LCSC 57). The RP2354B (C39843328)
   and the RP2350 core inductor L1, AOTA-B201610S3R3-101-T (C42411119), swing between in stock and
   none. For a short line, buy it into your JLCPCB parts inventory first (Parts Manager, "Order
   parts", from LCSC) or consign it. The inductor's alternate is TDK VLS201610HBX-3R3M-1 (C695624, same
   2016 size; Raspberry Pi specifies the polarity-marked AOTA); the crystal is Raspberry Pi's
   minimal-design part (CL 10 pF), so substitute it deliberately.
3. **The thickness.** 1.6 mm is ordered: the Videopac slot takes the 1.6 mm bwack / PicoPAC boards.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 +5V with +3V3 / +3V3_RP / CONS_5V islands, B.Cu) |
| Size | 63.00 x 85.00 mm (the whole 63 mm bottom edge is the insertion edge) |
| Thickness | 1.6 mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 30 fingers (15 on each face, 3.9286 mm pitch), **30 degree bevel** on the insertion edge |
| Minimum track / clearance | 0.15 mm / 0.12 mm (the RP2354B's 0.4 mm pitch); smallest via 0.25 mm drill / 0.50 mm pad |
| Via in pad | the 3 x 3 vias in the RP2354B's exposed pad and the CP2102N's: epoxy filled and capped if offered for 4 layers, else plain (tented from B.Cu) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | the board is narrower than JLC's 70 mm single-board minimum: let JLC add rails on the left and right edges only. Never on the insertion edge or the top edge (the ESP32-S3 antenna, the USB-C) |
| Holes | two 5.0 mm non-plated holes (the shell posts), and the two side notches: route them as drawn |

## Assembly

Top side only (B.Cu carries only the A-R fingers and copper). 113 parts per board. Not fitted
(DNP): none. The 13 test pads are bare copper.

1. Upload the zip; set the options above.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2354B, the ESP32-S3 module, the regulators, the mux, the CP2102N, the crystal, the
   inductors, the USB-C, the microSD) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - U1 (RP2354B, QFN-80), U2 (ESP32-S3-WROOM-1: the antenna at the top edge), U8 (AP2112K,
     SOT-23-5), U6 (TPS2116, SOT-583), U7 (AP63203, TSOT-23-6), U4 (CP2102N, QFN-28),
     U3 (USBLC6, SOT-23-6), U5 (UMH3N), D2 (BAT54C), J3 (USB-C), J2 (microSD: the
     card slot at the left edge), Y1 (crystal): pin 1 / orientation against the silkscreen.
   - D1 (red LED), D3 (WS2812B-2020): polarity / pin 1.
   - The regulator corner beside the RP2354B: L1 (AOTA 2016), C11, C14, C18, C19, R33, R40, R41 (0402, Raspberry Pi's
     minimal-design land pattern).
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start 0.50 mm from
   the edge and run to 8.00 mm, 2.00 mm wide, on both faces, on purpose; no part sits
   closer than 20.0 mm to that edge.
