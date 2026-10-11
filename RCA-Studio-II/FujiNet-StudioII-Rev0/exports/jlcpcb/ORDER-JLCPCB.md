# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `FujiNet-StudioII-Rev0-gerbers.zip`: gerbers + Excellon drill (plated and non-plated). Its top silkscreen carries
  the order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order
  number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

## Before ordering (VERIFY)

1. **The edge.** Print `docs/tab-overlay-1to1.pdf` at 100 % (no fit-to-page) and check its 50 mm
   ruler. Lay a real Studio II cartridge board on it, contacts up: the 22 contacts at 0.156"
   (3.96 mm), pin 1 (D7) at the LEFT seen from the contact side with the edge toward you, the
   90.9 mm width, the two 8.13 mm post holes and the side notches must match. The geometry is
   FliP's multicart v5.1 (built, runs in real consoles, fits original shells); nobody has
   measured an original cart for this board.  Above FliP's outline the board is taller (111.5 mm
   overall) for the ESP32-S3 half: it needs a printed shell (`case/board-anchors.scad`).
2. **The thickness.** 1.6 mm is ordered (FliP's boards: 1.57 mm). A 0.156" card-edge
   slot takes 1.57-1.6 mm.
3. **Stock.** `python3 tools/audit/sourcing.py` (or read `docs/sourcing.md`, 2026-10-11): every line
   was in JLCPCB stock when this was written. The core inductor (L1, AOTA-B201610S3R3) has the
   thinnest stock.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 power, B.Cu) |
| Size | 90.91 x 111.49 mm (no tab: the full width is the insertion edge) |
| Thickness | 1.6 mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 22 B.Cu fingers, **45 degree bevel** on the insertion edge (the 90.9 mm bottom edge) |
| Minimum track / clearance | 0.15 mm / 0.12 mm (the RP2354B's 0.4 mm pitch); smallest via 0.25 mm drill / 0.50 mm pad |
| Via in pad | the 3 x 3 vias in the RP2354B's exposed pad: epoxy filled and capped if offered for 4 layers, else plain (tented from B.Cu) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | if asked for: on the left and right edges only. Never on the insertion edge or the top edge (the ESP32-S3 antenna, USB-C, microSD) |

## Assembly

Top side only (B.Cu carries only the fingers and copper). 107 parts per board. Not fitted (DNP):
J2 (the debug UART header: fit it by hand for bring-up). The 17 test pads are bare copper.

### JLCPCB specifics

1. Upload the zip; set the options above. The two 8.13 mm holes for the shell posts are in the
   NPTH drill file, and the two side notches are in the Edge.Cuts layer.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2354B, the ESP32-S3 module, the logic, the regulators, the mux, the CP2102N, the crystal,
   the inductors, the USB-C, the microSD) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - U1 (RP2354B, QFN-80), U6 (ESP32-S3-WROOM-1: the antenna at the top edge), U2 (74HCT541,
     TSSOP-20), U4, U5 ('32 / '14, SOIC-14), U3 (74HCT1G02, SOT-23-5), U12 (AP2112K, SOT-23-5),
     U10 (TPS2116, SOT-583), U11 (AP63203, TSOT-23-6), U8 (CP2102N, QFN-28), U7 (USBLC6,
     SOT-23-6), U9 (UMH3N), D2 (BAT54C), J4 (USB-C), J3 (microSD: the card slot at the top
     edge), Y1 (crystal): pin 1 / orientation against the silkscreen.
   - D1 (red LED), D3 (WS2812B-2020): polarity / pin 1.
   - The regulator corner beside the RP2354B: L1 (AOTA 2016), C16, C19, C23, C24, R18, R25, R26 (0402, Raspberry Pi's minimal-design
     land pattern); C12, C22, the 0402 100 nF straight out of IOVDD 50 / DVDD 51.
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start 0.70 mm from
   the edge and run to 8.95 mm, 1.905 mm wide, on one face only (B.Cu), on purpose; no part
   sits closer than 23.5 mm to that edge.
