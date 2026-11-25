# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `FujiNet-TRS80M1-Rev0-gerbers.zip`: gerbers + Excellon drill. Its bottom silkscreen carries the order-number text
  `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

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

## Assembly

Top side only. 108 parts per board, one of them through-hole (J1, the box header). Not fitted
(DNP): none (J2, the logic-analyser header: solder a 2x20... a 2x10 pin header there only to
probe). The 11 test pads are bare copper.

1. Upload the zip; set the options above.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm), top side,
   **through-hole parts included** (the header is JLC's THT line: hand / selective soldering, a small
   extra fee). 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts add JLC's per-part loading fee.
4. **Placement preview, before paying:**
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
     minimal-design land pattern).
5. DFM: the box header's shroud stands 0.24 mm past the west edge on purpose (its mouth flush with the
   case wall).
