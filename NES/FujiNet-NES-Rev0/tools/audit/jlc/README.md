# JLCPCB CPL rotations and origin offsets (FujiNet-NES Rev0)

JLCPCB places each part by the **EasyEDA footprint of its LCSC code**, not by our
KiCad footprint. When the two libraries draw the same package in different
orientations, or put the footprint origin in a different place, the CPL needs a
correction. This directory measures that correction for every
(footprint, LCSC) pair in `tools/design.py`, pad by pad, with no regex tables or
assumed conventions. The script and method are the ones FujiNet-StudioII Rev0,
FujiNet-ChannelF Rev0 and Fujiversal-Atari2600 Rev1 use.

| File | What |
|---|---|
| `measure_rotations.py` | the measurement (Python 3 stdlib only) |
| `jlc_rotations.json` | the generated table (44 entries), read by `tools/export.py` |
| `easyeda_cache/<LCSC>.json` | raw EasyEDA API responses, so reruns are offline and reproducible |

## Rerun

```sh
python3 tools/audit/jlc/measure_rotations.py             # cache first, fetches only missing codes
python3 tools/audit/jlc/measure_rotations.py --offline   # cache only, never touches the network
python3 tools/audit/jlc/measure_rotations.py --markdown  # also print the full table with all notes
```

The script reads `tools/design.py` and `FujiNet-NES.pretty/` at run time, so
a new part or a changed LCSC code is picked up automatically. The endpoint is
easyeda2kicad's (`https://easyeda.com/api/products/<LCSC>/components?version=6.4.19.5`).
It sits behind CloudFront, which refuses non-browser User-Agents and rate-limits
after about 30 fast requests, so the script sends a browser UA, backs off, and
sleeps 2 s between fetches. Of the 45 cached codes (42 parts plus the three
TSOP-32 proxies), 40 were copied from the sibling carts' caches; C1996, C282339,
C547509, C5985 and C40382 were fetched on 2026-10-13.

## What the table means

* `rotation_correction_deg` is added to the KiCad rotation in the CPL. Rotating
  the EasyEDA footprint counter-clockwise by this amount lands it on ours.
* `origin_offset_mm` is the EasyEDA placement origin in **our footprint's frame**
  (KiCad local coordinates, +y down, mm, before the footprint's own rotation).
  JLC places by that origin, so the CPL position is our origin moved by it.
* "err" in the table is the largest pad-centre difference left after the
  correction. It is a land-pattern size difference, not a placement error.

## Method (short)

1. Both footprints are read pad by pad: EasyEDA in 10 mil units, +y down, origin
   at `head.x/y`; KiCad with an s-expression reader of `FujiNet-NES.pretty`.
   Pads that share a number (an exposed pad with its via pads, the USB-C `SH`
   tabs, a switch's bonded contacts) are compared as one group.
2. Pads are paired by number, then by EasyEDA's merged numbers (`A1B12` = our
   `A1` + `B12`), then **diodes and LEDs by symbol pin name, cathode to
   cathode**, then leftovers by geometry. A part whose numbers cannot describe
   the same pads is matched by geometry and flagged.
3. The rotation is the one of 0/90/180/270 with the lowest RMS error. The offset
   is the copper-bbox centre difference, or the peg alignment when both
   footprints have NPTH pegs.
4. Checks: the pin-1 angle must agree with the fitted rotation, EasyEDA's pin-1
   dot must be on its pad 1, and at least 70 % of the symbol pin names must
   agree. Confidence is:
   * `high`: all checks pass and the residual is 0.2 mm or less;
   * `medium`: a 0.2-0.35 mm residual, a geometry-only match, or an offset on
     which the two methods disagree by over 0.1 mm;
   * `low`: anything else.

For symmetric two-terminal parts (R, C, L), 0 and 180 deg are physically
equivalent. The table uses EasyEDA pad 1 on our pad 1, which gives 0 for every
passive here.

## How export.py applies it

`tools/export.py` `cpl()` keys the lookup by (footprint, LCSC), so two parts
that share a footprint can never take each other's correction. It stops if a
placed part has no measured entry.

Every assembled part is on the top side; the B.Cu cart-edge land is not
assembled, and the DNP parts (U10, C31) are skipped. `cpl()` refuses a
bottom-side part, because the corrections are measured for the top.

`kicad-cli pcb export pos` gives Y up and counter-clockwise rotation; the
footprint frame has +y down:

```python
t = math.radians(rot)
x = posx + dx * math.cos(t) + dy * math.sin(t)
y = posy + dx * math.sin(t) - dy * math.cos(t)
cpl_rot = (rot + corr) % 360
```

## Results (all top side)

| Footprint | LCSC | Part | Refs | Rot | Offset (mm) | err (mm) | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm | C39843328 | RP2354B | U1 | **0** | (0, 0) | 0.042 | high | Pin 1 top-left in both (`-TL`). 81/81 pin names agree. |
| ESP32-S3-WROOM-1 | C2913202 | ESP32-S3-WROOM-1-N16R8 | U11 | 0 | **(0, +3.62)** | 0.015 | high | Our origin is the module body centre. EasyEDA's is the pad-pattern centre, 3.62 mm toward the pin 15-26 edge. 39/41 pin names agree. |
| QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm | C964632 | CP2102N-A02-GQFN28 | U12 | **0** | (0, 0) | 0.073 | high | Pin 1 top-left in both. 29/29 pin names agree. |
| TSOP-I-32_18.4x8mm_P0.5mm | C5569980 | AS6C4008-55TIN | U2, U3 | **0** (proxy) | (0, 0) | 0.063 | **low** | **No EasyEDA component for C5569980**, as on FujiNet-SMS Rev0. Measured against the TSOPI-32 `-TL` footprint of C2944637 / C6883917 (0 degrees). The `-BL` footprint of C20481033 is drawn 90 degrees from it (it would give 270). 30/32 pin names agree on the proxy. JLC has no library data of its own for this part, and it is out of stock there, so it will be consigned. **Confirm in the preview / DFM.** |
| SOIC-16_3.9x9.9mm_P1.27mm | C282339 | 74HCT595 | U4 | 270 | (0, 0) | 0.261 | low (pin names) | EasyEDA `-BL`. Flagged only for naming: EasyEDA's Q0-Q7 / Q7S / DS / SHCP / STCP / MR# / OE# are our QA-QH / QH' / SER / SRCLK / RCLK / ~SRCLR / ~OE. **All 16 pins agree by function** (checked by hand). The residual is symmetric. |
| SOIC-16_3.9x9.9mm_P1.27mm | C547509 | 74HCT253 | U5 | 270 | (0, 0) | 0.497 | low (pin names) | EasyEDA `SO-16 ... LS6.2-BL`. Flagged only for naming: 1I0-1I3 / 2I0-2I3 / 1Y / 2Y / S0 / S1 / #1OE / #2OE are our I0a-I3a / I0b-I3b / Za / Zb / A0 / A1 / OEa / OEb. **All 16 pins agree by function** (checked by hand). EasyEDA's pad rows sit 0.497 mm farther out on each side, with zero error along the rows. |
| SOIC-14_3.9x8.7mm_P1.27mm | C6769 / C2878717 / C6764 / C5985 | 74HCT14 / '20 / '00 / '32 | U6, U7, U8, U9 | 270 | (0, 0) | 0.144 | high | EasyEDA `-BL`: horizontal, pin 1 bottom-left. Ours vertical, pin 1 top-left. |
| SOIC-8_3.9x4.9mm_P1.27mm | C40382 | ATtiny13A-SSU | U10 (DNP) | 270 | (0, 0) | 0.230 | medium | `-BL`. 8/8 pin names agree. Not fitted: export skips it. |
| TSOT-23-6 | C780769 | AP63203WU | U14 | **270** | (0, 0) | 0.062 | high | EasyEDA `-BL` horizontal, ours vertical. 6/6 pin names agree. |
| SOT-23-5 | C51118 | AP2112K-3.3 | U15 | **270** | (0, 0) | 0.200 | high | EasyEDA `-BL`. 5/5 pin names agree. |
| SOT-363_SC-70-6 | C62892 | UMH3N | U13 | 180 | (0, 0) | 0.112 | high | EasyEDA `-BR`. 6/6 pin names agree. |
| SOT-23 | C37704 | BAT54C | D1 | 180 | (0, 0) | 0.298 | medium | EasyEDA `-BR`. The residual comes from EasyEDA's wider land pattern, which is symmetric about the centre. |
| SOT-23 | C15127 | AO3401A | Q1 | 180 | (0, 0) | 0.212 | medium | `-BR`. G/S/D names agree. The residual is symmetric. |
| LED_0603_1608Metric | C12624 | green LED | D2 | 0 | (0, 0) | 0.039 | high (cathode-matched) | EasyEDA's pad 1 is K, as ours is, so there is no LED trap on this code. |
| D_SMA | C8678 | SS34 | D7 | **0** | (0, 0) | 0.200 | high (cathode-matched) | EasyEDA pad 1 = K, same as ours. The old table's +180 reversed the diode. |
| D_SOD-523 | C82044 | ESD5Z5.0T1G | D4, D5, D6 | 0 | (0, 0) | 0.012 | high (cathode-matched) | EasyEDA pad 1 = K, same as ours. |
| LED_WS2812B-2020_PLCC4_2.0x2.0mm | C52917434 | WS2812B-2020-V6 | D3 | **0** | (0, 0) | 0.050 | high | Pin 1 (DO) top-left in both. 4/4 names agree. |
| TF-SMD_TF-015 | C113206 | microSD | J2 | 0 | (0, 0) | 0.007 | high | Ours was generated from EasyEDA's. The pegs align. |
| USB_C_Receptacle_HRO_TYPE-C-31-M-12 | C165948 | USB-C | J3 | **0** | **(0, -1.414)** | 0.165 | medium | Merged pads (`A1B12`...) are split, and shell tabs 1-4 are matched to `SH`. The peg (mechanical) offset is used; the pad bbox would give (0, -1.585) and leave the pegs 0.19 mm off. |
| R_Array_Convex_4x0603 | C1996 / C29718 | 4x100k / 4x10k | RN1, RN2 / RN3 | 270 | (0, 0) | 0.100 | high | EasyEDA horizontal, ours vertical. |
| Crystal_SMD_3225-4Pin_3.2x2.5mm | C20625731 | 12 MHz | Y1 | 0 | (0, 0) | 0.000 | high | Exact match. |
| SW_SPST_TL3342 | C2886898 | TL3342F160QG | SW1-SW4 | 0 | (0, 0) | 0.158 | medium | The numbers are not comparable (EasyEDA 1-4, ours 1,1,2,2), so the pads are matched by geometry onto the bonded pairs. 0 and 180 are equivalent. |
| RPI_L_AOTA-B201610S3R3 | C42411119 | 3.3 uH | L1 | 0 | (0, 0) | 0.300 | medium | Pads at ±1.0 against ±0.7, symmetric. 0 and 180 are equivalent. |
| L_Sunlord_SWPA4030S | C62684 | 6.8 uH | L2 | 0 | (0, 0) | 0.100 | high | 0 and 180 are equivalent. |
| C_0603_1608Metric | C14663, C19702, C1644, C15849, C19666 | 100 nF, 10 uF, 15 pF, 1 uF, 4.7 uF | all C 0603 (C31 DNP) | 0 | (0, 0) | 0.075 | high | Pad 1 to pad 1. |
| C_0805_2012Metric | C45783 | 22 uF | C32, C42-C44, C47, C48 | 0 | (0, 0) | 0.050 | high | Pad 1 to pad 1. |
| R_0603_1608Metric | C23140, C21190, C25804, C25190, C31850, C25803, C23138, C23186, C25819, C23162 | 33R, 1k, 10k, 27R, 22k, 100k, 330R, 5.1k, 47k, 4.7k | all R 0603 | 0 | (0, 0) | 0.072 | high | Pad 1 to pad 1. |

Bold marks a correction the old `export.py` regex table got wrong. That table
also applied no origin offsets: U11 and J3 were placed by the KiCad origin.
The QFN-80's correction (0) differs from the old one (+270) because KiCad's
QFN-80 and EasyEDA's both have pin 1 top-left.

The low-confidence entries are U2/U3, where no EasyEDA footprint exists, and
U4/U5, where only the pin names differ and all 16 pins were checked by hand.
`export.py` prints these refs as a reminder. The medium entries are explained
in their rows. Cross-check: the 39 pairs this board shares with the other
carts' tables agree exactly on rotation and offset. C282339, C547509, C5985,
C1996 and C40382 are new to this board.

Still check **U11, J3, U1, U12, U4, U5, U2/U3 and D7** in JLCPCB's placement
preview before paying:

* U11 and J3, for their origin offsets;
* U1, U12, U4 and U5, for pin 1 (a QFN or SOIC looks the same when turned);
* U2/U3, because there is no EasyEDA footprint;
* D7, for the cathode band.

---
Footprint and symbol data: EasyEDA / JLCEDA official library
(<https://easyeda.com>, <https://lceda.cn>), fetched through the public
component API and cached in `easyeda_cache/`.
