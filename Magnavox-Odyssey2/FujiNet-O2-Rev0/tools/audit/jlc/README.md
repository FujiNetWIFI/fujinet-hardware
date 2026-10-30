# JLCPCB CPL rotations and origin offsets (FujiNet-O2 Rev0)

JLCPCB places each part by the **EasyEDA footprint of its LCSC code**, not by our
KiCad footprint. When the two libraries draw the same package in different
orientations, or put the footprint origin in a different place, the CPL needs a
correction. This directory measures that correction for every
(footprint, LCSC) pair in `tools/design.py`, pad by pad, with no regex tables or
assumed conventions. The script and method are the ones FujiNet-SMS Rev0 and
Fujiversal-Atari2600 Rev1 use.

| File | What |
|---|---|
| `measure_rotations.py` | the measurement (Python 3 stdlib only) |
| `jlc_rotations.json` | the generated table (38 entries), read by `tools/export.py` |
| `easyeda_cache/<LCSC>.json` | raw EasyEDA API responses, so reruns are offline and reproducible |

## Rerun

```sh
python3 tools/audit/jlc/measure_rotations.py             # cache first, fetches only missing codes
python3 tools/audit/jlc/measure_rotations.py --offline   # cache only, never touches the network
python3 tools/audit/jlc/measure_rotations.py --markdown  # also print the full table with all notes
```

The script reads `tools/design.py` and `FujiNet-O2.pretty/` at run time, so
a new part or a changed LCSC code is picked up automatically. The endpoint is
easyeda2kicad's (`https://easyeda.com/api/products/<LCSC>/components?version=6.4.19.5`);
it sits behind CloudFront, which refuses non-browser User-Agents and rate-limits
after about 30 fast requests, so the script sends a browser UA, backs off and
sleeps 2 s between fetches.

## What the table means

* `rotation_correction_deg` is added to the KiCad rotation in the CPL. Rotating
  the EasyEDA footprint counter-clockwise by this amount lands it on ours.
* `origin_offset_mm` is the EasyEDA placement origin in **our footprint's frame**
  (KiCad local coordinates, +y down, mm, before the footprint's own rotation).
  JLC places by that origin, so the CPL position is our origin moved by it.
* "err" in the table is the largest pad-centre difference left after the
  correction: a land-pattern size difference, not a placement error.

## Method (short)

1. Both footprints are read pad by pad (EasyEDA: 10 mil units, +y down, origin
   at `head.x/y`; KiCad: an s-expression reader of `FujiNet-O2.pretty`).
   Pads that share a number (an exposed pad with its via pads, the USB-C `SH`
   tabs, a switch's bonded contacts) are compared as one group.
2. Pads are paired by number, then by EasyEDA's merged numbers (`A1B12` = our
   `A1` + `B12`), then **diodes and LEDs by symbol pin name, cathode to
   cathode**, then leftovers by geometry. A part whose numbers cannot describe
   the same pads is matched by geometry and flagged.
3. The rotation is the one of 0/90/180/270 with the lowest RMS error; the offset
   is the copper-bbox centre difference, or the peg alignment when both
   footprints have NPTH pegs.
4. Checks: the pin-1 angle agrees with the fitted rotation, EasyEDA's pin-1 dot
   is on its pad 1, the symbol pin names agree (at least 70 %). Confidence is
   `high` when all pass and the residual is 0.2 mm or less, `medium` for a
   0.2-0.35 mm residual, a geometry-only match or an offset the two methods
   disagree on by over 0.1 mm, `low` otherwise.

For symmetric two-terminal parts (R, C, L) 0 and 180 deg are physically
equivalent; the table uses EasyEDA pad 1 on our pad 1, which gives 0 for every
passive here.

## How export.py applies it

`tools/export.py` `cpl()` keys the lookup by (footprint, LCSC), so two parts that
share a footprint can never take each other's correction, and stops if a placed
part has no measured entry. Every assembled part is on the top side (the gold
fingers are the only B.Cu parts; `cpl()` refuses a bottom-side part, since the
corrections are measured for the top). `kicad-cli pcb export pos` gives Y up and
counter-clockwise rotation; the footprint frame has +y down:

```python
t = math.radians(rot)
x = posx + dx * math.cos(t) + dy * math.sin(t)
y = posy + dx * math.sin(t) - dy * math.cos(t)
cpl_rot = (rot + corr) % 360
```

## Results (all top side)

| Footprint | LCSC | Part | Refs | Rot | Offset (mm) | err (mm) | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm | C39843328 | RP2354B | U1 | 0 | (0, 0) | 0.042 | high | Pin 1 top-left in both (`-TL`). 81/81 pin names agree. |
| ESP32-S3-WROOM-1 | C2913202 | ESP32-S3-WROOM-1-N16R8 | U6 | 0 | **(0, +3.62)** | 0.015 | high | Our origin is the module body centre; EasyEDA's is the pad-pattern centre, 3.62 mm toward the pin 15-26 edge. 39/41 pin names agree. |
| QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm | C964632 | CP2102N-A02-GQFN28 | U8 | 0 | (0, 0) | 0.073 | high | Pin 1 top-left in both. 29/29 pin names agree. |
| TSSOP-20_4.4x6.5mm_P0.65mm | C436096 | 74HCT541 | U2 | **270** | (0, 0) | 0.008 | high | EasyEDA `-BL`. 20/20 names agree once our 0-based A0-A7 / Y0-Y7 are read as EasyEDA's 1-based A1-A8 / Y1-Y8. |
| SOIC-14_3.9x8.7mm_P1.27mm | C6781 / C6769 | 74HCT32 / 74HCT14 | U4 / U5 | **270** | (0, 0) | 0.144 | high | EasyEDA `-BL`: horizontal, pin 1 bottom-left. Ours vertical, pin 1 top-left. |
| SOT-583-8 | C3235557 | TPS2116 | U10 | **270** | (0, 0) | 0.100 | high | EasyEDA `-BL`. 8/8 pin names agree. |
| SOT-23-6 | C7519 | USBLC6-2SC6 | U7 | **270** | (0, 0) | 0.012 | high | EasyEDA `-BL`. |
| TSOT-23-6 | C780769 | AP63203WU | U11 | **270** | (0, 0) | 0.062 | high | EasyEDA `-BL`. 6/6 pin names agree. |
| SOT-23-5 | C12504 / C51118 | 74HCT1G02 / AP2112K-3.3 | U3 / U12 | **270** | (0, 0) | 0.195 / 0.200 | high | EasyEDA `-BL`. |
| SOT-363_SC-70-6 | C62892 | UMH3N | U9 | **180** | (0, 0) | 0.112 | high | EasyEDA `-BR`. E/B/C names agree. |
| SOT-23 | C37704 | BAT54C | D2 | **180** | (0, 0) | 0.298 | medium | EasyEDA `-BR`. The residual is EasyEDA's wider land pattern, symmetric about the centre. |
| LED_0603_1608Metric | C2286 | red LED | D1 | **0** | (0, 0) | 0.037 | high (cathode-matched) | **LED trap:** EasyEDA's pad 2 is K, ours pad 1. Matched cathode to cathode, which gives 0; a pad-number match would say 180 and reverse D1. EasyEDA's pin-1 dot is on its anode. |
| LED_WS2812B-2020_PLCC4_2.0x2.0mm | C52917434 | WS2812B-2020-V6 | D3 | 0 | (0, 0) | 0.050 | high | Pin 1 (DO) top-left in both. 4/4 names agree. |
| TF-SMD_TF-015 | C113206 | microSD | J3 | 0 | (0, 0) | 0.007 | high | Ours was generated from EasyEDA's. Pegs align. |
| USB_C_Receptacle_HRO_TYPE-C-31-M-12 | C165948 | USB-C | J4 | 0 | **(0, -1.414)** | 0.165 | medium | Merged pads (`A1B12`...) split; shell tabs 1-4 matched to `SH`. The peg (mechanical) offset is used; the pad bbox would give (0, -1.585) and leave the pegs 0.19 mm off. |
| PinHeader_1x03_P2.54mm_Vertical | C2937625 | debug header (DNP) | J2 | 270 | (0, +2.54) | 0.000 | high | Not fitted: export skips it. |
| R_Array_Convex_4x0603 | C29718 | 4x10k | RN1 | **270** | (0, 0) | 0.100 | high | EasyEDA horizontal, ours vertical. |
| Crystal_SMD_3225-4Pin_3.2x2.5mm | C20625731 | 12 MHz | Y1 | 0 | (0, 0) | 0.000 | high | Exact match. |
| SW_SPST_TS-1187A | C318884 | TS-1187A | SW1-SW4 | 0 | (0, 0) | 0.025 | medium | Numbers not comparable (EasyEDA 1-4, ours 1,1,2,2): matched by geometry onto the bonded pairs. 0 and 180 are equivalent. |
| RPI_L_AOTA-B201610S3R3 | C42411119 | 3.3 uH | L1 | 0 | (0, 0) | 0.300 | medium | Pads ±1.0 against ±0.7, symmetric. 0 and 180 are equivalent. |
| L_Sunlord_SWPA4030S | C62684 | 6.8 uH | L2 | 0 | (0, 0) | 0.100 | high | 0 and 180 are equivalent. |
| RPI_C0402 / RPI_C0402_wide / RPI_R0402 | C1525, C23733, C25105, C25100 | 100 nF, 4.7 uF, 33R, 27R | the regulator corner and the USB 27R | 0 | (0, 0) | ≤ 0.095 | high | Raspberry Pi's 0402 land patterns; pad 1 to pad 1. |
| C_0603_1608Metric | C14663, C19702, C1644, C15849, C19666 | 100 nF, 10 uF, 15 pF, 1 uF, 4.7 uF | all C 0603 | 0 | (0, 0) | 0.075 | high | Pad 1 to pad 1. |
| C_0805_2012Metric | C45783 | 22 uF | C27, C39, C40, C43, C44 | 0 | (0, 0) | 0.050 | high | Pad 1 to pad 1. |
| R_0603_1608Metric | C23138, C25804, C31850, C25803, C21190, C23186, C25819, C4216 | 330R, 10k, 22k, 100k, 1k, 5.1k, 47k, 33k | all R 0603 | 0 | (0, 0) | 0.072 | high | Pad 1 to pad 1. |

No entry is low confidence. The four medium ones are explained in their rows:
symmetric land-pattern residuals (D2, L1), a geometry match for a two-terminal
switch (SW1-SW4), and the USB-C's peg offset (J4). Still check **J4, U6 and D1**
in JLCPCB's placement preview before paying: J4 and U6 because of their origin
offsets, D1 because of the LED trap.

---
Footprint and symbol data: EasyEDA / JLCEDA official library
(<https://easyeda.com>, <https://lceda.cn>), fetched through the public
component API and cached in `easyeda_cache/`.
