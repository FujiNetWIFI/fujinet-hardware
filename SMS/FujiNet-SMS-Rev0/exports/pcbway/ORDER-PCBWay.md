# Ordering at PCBWay

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `FujiNet-SMS-Rev0-gerbers.zip`: gerbers + Excellon drill (no order-number text).
- `BOM-PCBWay.csv`: Line#, Qty, Designator, MPN, Manufacturer, Description, Package, Type, the
  LCSC code for reference, Notes.
- `Centroid-PCBWay.csv`: KiCad's own centres and rotations (PCBWay places by our footprints and
  the assembly drawing; never the JLC-corrected CPL).
- `Assembly-top.pdf`: references and pin-1 marks on the outline.

## Before ordering (VERIFY)

1. **The tab.** Print `docs/tab-overlay-1to1.pdf` at 100 % (no fit-to-page) and check its 50 mm ruler.
   Lay a real SMS cartridge board on the fingers: even fingers on the label side, pins 1/2 at the
   right, the finger span and the tab width must match.
2. **The thickness.** Measure a real cartridge board; 1.6 mm is assumed.
3. **Stock.** `python3 tools/audit/sourcing.py` (or read `docs/sourcing.md`, 2026-10-08): the SRAMs (U7, U10) and
   the Nexperia '27 / '10 (U8, U9, U13) were not in JLCPCB / LCSC stock.

## Board options (both fabs)

| Option | Value |
|---|---|
| Layers | 6 (stack: F.Cu, In1 GND, In2, In3, In4 power, B.Cu) |
| Size | 100 x 93 mm (body 100 x 78 on a 65.8 x 15 mm tab) |
| Thickness | 1.6 mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold, **30-45 degree bevel** on the tab's insertion edge (the 65.8 mm bottom edge) |
| Minimum track / clearance | 0.15 mm / 0.12 mm (the RP2354B's 0.4 mm pitch); vias 0.3 mm drill / 0.6 mm pad |
| Via in pad | the vias in the RP2354B's exposed pad: filled and capped |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | if asked for: on the left and right body edges only. Never on the tab, and never on the top edge (USB-C, microSD, antenna) |

## Assembly

Top side only (B.Cu has no parts). 109 parts per board.

### PCBWay specifics

1. PCB: the options above; ask for **hard gold fingers with bevel** and **resin-plugged, capped
   vias** under the RP2354B's exposed pad (note: "via-in-pad in U-EP, fill and cap").
2. Assembly: **turnkey**, top side, the quantity you need. PCBWay sources every line by MPN, so
   the SRAMs (U7, U10) and the '27 / '10 (U8, U9, U13) come from DigiKey / Mouser with the rest.
3. Upload `BOM-PCBWay.csv`, `Centroid-PCBWay.csv` and `Assembly-top.pdf`.
4. In the order notes: "Gold fingers: hard gold, 30-45 degree bevel on the 65.8 mm tab edge only.
   TSOP-I U7, U10: pin 1 at the silkscreen dot. Check polarity of D6, D5, U3, D1 against
   Assembly-top.pdf."
5. Approve PCBWay's engineering questions on the fingers (they end 0.75 mm from the edge on
   purpose) and the bevel.
