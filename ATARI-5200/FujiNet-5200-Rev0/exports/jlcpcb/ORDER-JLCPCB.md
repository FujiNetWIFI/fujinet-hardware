# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `FujiNet-5200-Rev0-gerbers.zip`: gerbers + Excellon drill. Its top silkscreen carries the
  order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order
  number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

## Before ordering (VERIFY)

1. **The tab.** Print `docs/tab-overlay-1to1.pdf` at 100 % (no fit-to-page) and check its 50 mm ruler.
   Lay a real Atari 5200 cartridge board on the fingers: pins 1-18 on the label side, pin 1 (D0) at
   the left seen from the label with the fingers down; the finger span, the tab width (47.8 mm) and
   the two short fingers (pins 18 / 36, the interlock) must match.
2. **The thickness.** The console connector takes 1.57 +/- 0.2 mm; 1.6 mm is ordered.
3. **Stock.** `python3 tools/audit/sourcing.py` (or read `docs/sourcing.md`, 2026-10-08): every line was in
   JLCPCB stock when this was written.
4. **The jumpers.** JP1 (interlock 18-36) and JP2 (edge 11 raw DC) are bridged copper: leave them.

## Board options (both fabs)

| Option | Value |
|---|---|
| Layers | 6 (stack: F.Cu, In1 GND, In2, In3, In4 power, B.Cu) |
| Size | 84.0 x 98.0 mm (a T: the 47.8 mm tab, 18.5 mm deep, under a 61 mm lower body and the 84 mm wide top) |
| Thickness | 1.6 mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold, **30-45 degree bevel** on the tab's insertion edge (the 47.8 mm bottom edge) only |
| Minimum track / clearance | 0.15 mm / 0.12 mm (the RP2354B's 0.4 mm pitch); smallest via 0.25 mm drill / 0.50 mm pad |
| Via in pad | the vias in the RP2354B's exposed pad: filled and capped |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | if asked for: on the left and right edges of the wide top only. Never on the tab or the lower body, and never on the top edge (USB-C, microSD, antenna) |

## Assembly

Top side only (B.Cu has no parts). 113 parts per board.  Not fitted (DNP, left off the BOM and the
CPL): J4, Q1, Q2, R24, R26 -- the firmware-controlled interlock switch and the RP's debug-UART header.

### JLCPCB specifics

1. Upload the zip; set the options above. JLCPCB fills and caps via-in-pad on 6 layers at no charge.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm).
   Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2354B, the S3 module, the logic, the regulators) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - U5 (RP2354B), U1 (ESP32-S3), U2 (CP2102N), J2 (USB-C), J3 (microSD), U7 (74HCT541,
     TSSOP-20), U8, U9 (74HCT08 / '14, SOIC-14), U11 (74LVC1G17, SOT-353), U4, U10 (AP63205 / AP63203,
     TSOT-23-6), U6 (AP2112K, SOT-23-5): pin 1 / orientation against the silkscreen.
   - D6 (WS2812B), D5, D9 (BAT54C), U3 (UMH3N), D4, D8 (SS34), D7 (red LED), D1, D2, D3 (ESD5Z): polarity.
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers. The fingers start 0.6 mm from the
   edge and pins 18 / 36 only 1.9 mm in, on purpose (the console's interlock makes last).
