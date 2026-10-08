# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py`:

- `FujiNet-SMS-Rev0-gerbers.zip`: gerbers + Excellon drill. Its top silkscreen carries the
  order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order
  number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).
- `consigned.csv`: the lines JLCPCB does not stock, with quantities for 5 boards.

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

### JLCPCB specifics

1. Upload the zip; set the options above. JLCPCB fills and caps via-in-pad on 6 layers at no charge.
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2354B is 0.4 mm).
   Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`.
4. For the SRAMs (U7, U10) and the '27 / '10 (U8, U9, U13), pick one:
   - **consign** them (buy from DigiKey / Mouser per `consigned.csv`, ship to JLCPCB, and select
     them as your own parts), or
   - **Global Sourcing** on the BOM page (JLCPCB buys them; check lead time and fee), or
   - for the gates only, the TI alternates CD74HCT27M96 (C2878706) / CD74HCT10M (C2863188) if
     their stock covers the build (pin-identical; `tools/audit/timing_margins.py --ti`).
5. **Placement preview, before paying:**
   - U7, U10 (AS6C4008, TSOP-I): EasyEDA has no footprint for it, so its rotation follows the TSOP-I
     convention and is marked low confidence. Pin 1 is the dot / bold mark on the silkscreen;
     the part's pin 1 must sit there.
   - U4 (RP2354B), U1 (ESP32-S3), U2 (CP2102N), J2 (USB-C), J3 (microSD): pin 1 / orientation
     against the silkscreen.
   - D6 (WS2812C), D5 (BAT54C), U3 (UMH3N), D1 (SS34): polarity.
6. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers; the fingers end 0.75 mm
   from the edge on purpose.
