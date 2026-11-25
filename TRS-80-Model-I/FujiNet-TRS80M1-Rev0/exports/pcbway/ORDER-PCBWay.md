# Ordering at PCBWay

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `FujiNet-TRS80M1-Rev0-gerbers.zip`: gerbers + Excellon drill (no order-number text).
- `BOM-PCBWay.csv`: Line#, Qty, Designator, MPN, Manufacturer, Description, Package, Type (SMD / THT),
  the LCSC code for reference, Notes.
- `Centroid-PCBWay.csv`: KiCad's own centres and rotations (PCBWay places by our footprints and
  the assembly drawing; never the JLC-corrected CPL).
- `Assembly-top.pdf`: references and pin-1 marks on the outline.

## Before ordering (VERIFY)

1. **The header.** `tools/audit/header_pinout.py` passes: every header pin against the Model I's
   expansion edge (four sources), the footprint against the part's EasyEDA footprint, pin 1 at the
   south end. The cable is the user's to plug the right way round (README "The cable").
2. **Stock** (`python3 tools/audit/sourcing.py` re-reads it; `docs/sourcing.md`, 2026-11-24). The RP2350
   core inductor L1, AOTA-B201610S3R3-101-T (C42411119), swings between in stock and none; its
   alternate is TDK VLS201610HBX-3R3M-1 (C695624; Raspberry Pi specifies the polarity-marked AOTA).
   The box header J1, XFCN BH254R-40P (C48603651), had ~600 at JLCPCB on 2026-11-24; Ckmtw
   B-3000R40P-0110 (C146628) fits the same holes.
3. **The case.** `case/` holds a printed case made for this board; print one before printing more.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 +5V with +3V3 / +3V3_RP islands, B.Cu) |
| Size | 100.00 x 76.00 mm, rounded corners, four 3.2 mm NPTH (M3) |
| Thickness | 1.6 mm |
| Surface finish | ENIG (the RP2354B's 0.4 mm-pitch QFN wants a flat finish) |
| Gold fingers | no |
| Minimum track / clearance | 0.15 mm / 0.12 mm (the RP2354B's 0.4 mm pitch); smallest via 0.25 mm drill / 0.50 mm pad (Raspberry Pi's regulator corner) |
| Via in pad | the 3 x 3 vias in the RP2354B's and the CP2102N's exposed pads: plain, tented from B.Cu (no filling needed) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | none needed (100 x 76 mm); if the fab adds them, never on the west edge: the box header's mouth stands 0.24 mm past it |

### PCBWay specifics

1. PCB: the options above.
2. Assembly: **turnkey**, top side, SMD + one THT part, the quantity you need. PCBWay sources every line
   by MPN.
3. Upload `BOM-PCBWay.csv`, `Centroid-PCBWay.csv` and `Assembly-top.pdf`.
4. In the order notes: "J1 is a right-angle shrouded 2x20 header, mouth outward over the west
   edge, pin 1 at the south end. Check the orientation of the ICs and the polarity of the LEDs
   against Assembly-top.pdf:
   - U1 (RP2354B, QFN-80), U2, U3, U4 (74LVC245A, TSSOP-20), U6, U7 (74LVC3G17, SSOP-8 / DCT),
     U8 (74LVC2G07, SOT-363), U5 (74LVC1G11, SOT-23-6), U9 (ESP32-S3-WROOM-1: the antenna at the
     east edge), U14 (AP2112K, SOT-23-5), U13 (TLV62569, SOT-23-5), U11 (CP2102N, QFN-28),
     U10 (USBLC6, SOT-23-6), U12 (UMH3N), D2 (BAT54C), J4 (USB-C, north edge), J3
     (microSD: the card slot in the south edge), SW1 (DIP switch: ON toward the RP), Y1 (crystal): pin 1 /
     orientation against the silkscreen.
   - J1, the right-angle box header (through-hole): its mouth OUTWARD, flush with the west edge, the
     key notch up; pin 1 (the square pad) at the south end, by the PIN 1 / STRIPE arrow.
   - D1 (red LED), D3 (WS2812B-2020): polarity / pin 1.
   - The regulator corner beside the RP2354B: L1 (AOTA 2016), C18, C21, C25, C26, R5, R12, R13 (0402, Raspberry Pi's
     minimal-design land pattern)."
