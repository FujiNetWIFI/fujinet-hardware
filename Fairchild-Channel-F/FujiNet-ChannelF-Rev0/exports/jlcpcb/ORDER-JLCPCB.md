# Ordering at JLCPCB

Files in this folder, all from `tools/export.py`, checked by `tools/audit/check_fab.py` and
`tools/audit/check_gerbers.py`:

- `FujiNet-ChannelF-Rev0-gerbers.zip`: gerbers + Excellon drill (plated and non-plated). Its top silkscreen carries
  the order-number text `JLCJLCJLCJLC` in a clear spot: choose **"Specify a location"** for the order
  number.
- `BOM-JLCPCB.csv`: Comment, Designator, Footprint, LCSC Part #.
- `CPL-JLCPCB.csv`: positions and rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).

## Before ordering (VERIFY)

1. **The edge.** Print `docs/tab-overlay-1to1.pdf` at 100 % (no fit-to-page) and check its 50 mm
   ruler. Lay a real Videocart board on it, contacts up: the 22 contacts at 2.54 mm in two groups
   of 11, the key slot between pins 11 and 12, pin 1 (GND) at the RIGHT seen from the contact
   side with the edge toward you, the 68.3 mm tab and the hole pattern must match.
2. **The thickness.** The console slot is "slightly greater than the thickness" of a cartridge
   board (US 4,095,791); 1.6 mm is ordered, as aotta's PicoVideocart (proven on a console).
3. **Stock.** `python3 tools/audit/sourcing.py` (or read `docs/sourcing.md`, 2026-10-11): every line
   was in JLCPCB stock when this was written.

## Board options

| Option | Value |
|---|---|
| Layers | 4 (stack-up JLC04161H-7628: F.Cu, In1 GND, In2 power, B.Cu) |
| Size | 77.0 x 131.5 mm (the 68.3 mm tab, 30 mm long, under a 77 mm body) |
| Thickness | 1.6 mm |
| Surface finish | ENIG |
| Gold fingers | **Yes**, hard gold on the 22 B.Cu fingers, **30-45 degree bevel** on the tab's insertion edge (the 68.3 mm bottom edge) only |
| Minimum track / clearance | 0.15 mm / 0.12 mm (the RP2040's 0.4 mm pitch); smallest via 0.25 mm drill / 0.50 mm pad |
| Via in pad | the vias in the RP2040's and CP2102N's exposed pads: epoxy filled and capped if offered for 4 layers, else plain (tented from B.Cu) |
| Solder mask / silkscreen | any colour; white silk on green or black |
| Edge rails | if asked for: on the left and right edges of the body only. Never on the tab, the slot, or the grip edge (USB-C, microSD, antenna) |

## Assembly

Top side only (B.Cu carries only the fingers). 86 parts per board. Not fitted (DNP): none.

### JLCPCB specifics

1. Upload the zip; set the options above. The key slot (1.651 x 12.58 mm, round top) and
   its lead-in are in the Edge.Cuts layer, and so are the four 5.6 mm holes on the shell's bosses
   (also in the NPTH drill file).
2. **PCB Assembly: Standard** (Economic PCBA stops at 0.5 mm pitch; the RP2040 is 0.4 mm, and gold
   fingers need Standard). Assemble **top side**; 2 or 5 of the 5 boards.
3. Upload `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every line should match its LCSC part; the extended
   parts (the RP2040, the S3 module, the translators, the regulators) add JLC's per-part loading fee.
4. **Placement preview, before paying:**
   - U5 (RP2040, QFN-56), U1 (ESP32-S3), U3 (CP2102N, QFN-28), J2 (USB-C), J3 (microSD),
     U8, U9 (SN74LVC4245A, TSSOP-24), U6 (W25Q16JV, SOIC-8 208 mil), U4 (AP63203, TSOT-23-6),
     U7 (AP2112K, SOT-23-5), Q1 (2N7002), U2 (UMH3N): pin 1 / orientation against the silkscreen.
   - D1 (WS2812B), D2 (BAT54C), D7, D8 (SS34: the cathode bar toward +5V), D3 (green LED),
     D4, D5, D6 (ESD5Z): polarity.
5. DFM: JLCPCB's DFM viewer flags the bevel and the gold fingers, and the slot. The fingers start
   0.5 mm from the edge and run to 12.0 mm, on one face only (B.Cu), on purpose.
