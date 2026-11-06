# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/gerber_equiv.py`:

- `Inty-FujiCard-gerbers.zip`: gerbers + Excellon drill, equal to Yannick Erb's own set. Its bottom
  silkscreen carries the order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a
  location"** for the order number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part # (Yannick's LCSC codes).
- `CPL-JLCPCB.csv`: positions and rotations, equal to Yannick's own pick-and-place file (his
  footprints are LCSC's, so no correction applies).

## Before ordering (VERIFY)

1. **The options Yannick has not stated.** His EasyEDA files give the copper, the masks, the paste,
   the silkscreen and the drills, not the order options: the finish, the gold fingers and the bevel
   below are the house recommendation for a cartridge edge. Confirm them with Yannick Erb.
2. **The paste on the gold fingers.** His paste layers open every finger (22 on F.Paste, 22 on
   B.Paste), and so do these gerbers (they equal his). A stencil cut from them prints solder paste on
   the top fingers. Ask the fab to leave the fingers out of the stencil (or confirm with Yannick how
   his boards were built).
3. **Spacing below the fab's standard figures** (Yannick's own EasyEDA rule is 0.1016 mm): six spots
   at 0.107-0.121 mm in the RP2354A's and the CP2102N's fan-out, and 156 vias of which the small
   ones are 0.254 mm drill / 0.457 mm pad (a 0.1015 mm ring). See README "Design rules".
4. **Stock** (`python3 tools/audit/sourcing.py`; `docs/sourcing.md`, 2026-11-05).

## Board options

| Option | Value |
|---|---|
| Layers | 2 |
| Size | 58.2 x 60.0 mm (the whole 58.2 mm bottom edge is the insertion edge) |
| Thickness | 1.6 mm |
| Surface finish | ENIG (recommended; not stated by Yannick) |
| Gold fingers | hard gold on the 44 fingers (22 on each face, 2.54 mm pitch), 30 degree bevel on the insertion edge (recommended; not stated by Yannick) |
| Minimum track / clearance | 0.203 mm / 0.107 mm (six spots; 0.127 mm everywhere else) |
| Smallest via | 0.254 mm drill / 0.457 mm pad |
| Solder mask / silkscreen | any colour; white silk |

## Assembly

Top side only (B.Cu carries the odd fingers and copper). 70 parts per board on 31 BOM lines.
The 5 test pads are bare copper; the edge and the two holes are not parts.

1. Upload the zip; set the options above.
2. **PCB Assembly: Standard** (the RP2354A is 0.4 mm pitch, and gold fingers need Standard). Top side.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part.
4. **Stencil / paste:** see "The paste on the gold fingers" above.
5. **Placement preview, before paying:**
   - U1 (RP2354A, QFN-60 0.4 mm), U3 (CP2102N, QFN-28), U7 (ESP32-S3-WROOM-1: the antenna overhangs the
     top edge), U2 (AP63203, TSOT-26), Q1 / Q3 / Q4 (BC847BT, SOT-523), Q2 (UMH3N, SOT-363), U5 (crystal),
     U8 (microSD, top-right), J1 (USB-C, top-left): pin 1 / orientation against the silkscreen.
   - D1 / D2 (SS34), D3-D5 (ESD5Z), C29 (electrolytic), D6 (SK6805-EC20): polarity / pin 1.
