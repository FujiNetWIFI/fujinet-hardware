# JLCPCB CPL rotations and origin offsets (FujiNet-Astrocade Rev0)

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
| `jlc_rotations.json` | the generated table (36 entries), read by `tools/export.py` |
| `easyeda_cache/<LCSC>.json` | raw EasyEDA API responses, so reruns are offline and reproducible |

## Rerun

```sh
python3 tools/audit/jlc/measure_rotations.py             # cache first, fetches only missing codes
python3 tools/audit/jlc/measure_rotations.py --offline   # cache only, never touches the network
python3 tools/audit/jlc/measure_rotations.py --markdown  # also print the full table with all notes
```

The script reads `tools/design.py` and `FujiNet-Astrocade.pretty/` at run time, so
a new part or a changed LCSC code is picked up automatically. The endpoint is
easyeda2kicad's (`https://easyeda.com/api/products/<LCSC>/components?version=6.4.19.5`).
It sits behind CloudFront, which refuses non-browser User-Agents and rate-limits
after about 30 fast requests, so the script sends a browser UA, backs off, and
sleeps 2 s between fetches. Of the 35 cached codes, 33 were copied from the
sibling carts' caches; C41378174 (RP2354A) and C22809 (15k) were fetched on
2026-10-13.

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
   at `head.x/y`; KiCad with an s-expression reader of `FujiNet-Astrocade.pretty`.
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
assembled. `cpl()` refuses a bottom-side part, because the corrections are
measured for the top.

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
| RPI_RP2350A_QFN60 | C41378174 | RP2354A | U1 | **0** | (0, 0) | 0.125 | high | Pin 1 top-left in both (`-TL`). 61/61 pin names agree. Same as the Fujiversal-Atari2600 Rev1 table. |
| ESP32-S3-WROOM-1 | C2913202 | ESP32-S3-WROOM-1-N16R8 | U2 | 0 | **(0, +3.62)** | 0.015 | high | Our origin is the module body centre. EasyEDA's is the pad-pattern centre, 3.62 mm toward the pin 15-26 edge. 39/41 pin names agree. |
| QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm | C964632 | CP2102N-A02-GQFN28 | U3 | **0** | (0, 0) | 0.073 | high | Pin 1 top-left in both. 29/29 pin names agree. |
| TSOT-23-6 | C780769 | AP63203WU | U5 | **270** | (0, 0) | 0.062 | high | EasyEDA `-BL` horizontal, ours vertical. 6/6 pin names agree. |
| SOT-23-5 | C51118 | AP2112K-3.3 | U6 | **270** | (0, 0) | 0.200 | high | EasyEDA `-BL`. 5/5 pin names agree. |
| SOT-363_SC-70-6 | C62892 | UMH3N | U4 | 180 | (0, 0) | 0.112 | high | EasyEDA `-BR`. 6/6 pin names agree. |
| SOT-23 | C37704 | BAT54C | D2 | 180 | (0, 0) | 0.298 | medium | EasyEDA `-BR`. The residual comes from EasyEDA's wider land pattern, which is symmetric about the centre. |
| LED_0603_1608Metric | C12624 | green LED | D1 | 0 | (0, 0) | 0.039 | high (cathode-matched) | EasyEDA's pad 1 is K, as ours is, so there is no LED trap on this code. |
| D_SMA | C8678 | SS34 | D7, D8 | **0** | (0, 0) | 0.200 | high (cathode-matched) | EasyEDA pad 1 = K, same as ours. The old table's +180 reversed both diodes. |
| D_SOD-523 | C82044 | ESD5Z5.0T1G | D4, D5, D6 | 0 | (0, 0) | 0.012 | high (cathode-matched) | EasyEDA pad 1 = K, same as ours. |
| LED_WS2812B-2020_PLCC4_2.0x2.0mm | C52917434 | WS2812B-2020-V6 | D3 | **0** | (0, 0) | 0.050 | high | Pin 1 (DO) top-left in both. 4/4 names agree. |
| TF-SMD_TF-015 | C113206 | microSD | J2 | 0 | (0, 0) | 0.007 | high | Ours was generated from EasyEDA's. The pegs align. |
| USB_C_Receptacle_HRO_TYPE-C-31-M-12 | C165948 | USB-C | J3 | **0** | **(0, -1.414)** | 0.165 | medium | Merged pads (`A1B12`...) are split, and shell tabs 1-4 are matched to `SH`. The peg (mechanical) offset is used; the pad bbox would give (0, -1.585) and leave the pegs 0.19 mm off. |
| R_Array_Convex_4x0603 | C29718 | 4x10k | RN1 | 270 | (0, 0) | 0.100 | high | EasyEDA horizontal, ours vertical. |
| Crystal_SMD_3225-4Pin_3.2x2.5mm | C20625731 | 12 MHz | Y1 | 0 | (0, 0) | 0.000 | high | Exact match. |
| SW_SPST_TL3342 | C2886898 | TL3342F160QG | SW1-SW4 | 0 | (0, 0) | 0.158 | medium | The numbers are not comparable (EasyEDA 1-4, ours 1,1,2,2), so the pads are matched by geometry onto the bonded pairs. 0 and 180 are equivalent. |
| RPI_L_AOTA-B201610S3R3 | C42411119 | 3.3 uH | L1 | 0 | (0, 0) | 0.300 | medium | Pads at ±1.0 against ±0.7, symmetric. 0 and 180 are equivalent. |
| L_Sunlord_SWPA4030S | C62684 | 6.8 uH | L2 | 0 | (0, 0) | 0.100 | high | 0 and 180 are equivalent. |
| RPI_C0402 / RPI_C0402_wide / RPI_R0402 | C1525, C23733, C25105, C25100 | 100 nF, 4.7 uF, 33R, 27R | the regulator corner and the USB 27R | 0 | (0, 0) | ≤ 0.095 | high | Raspberry Pi's 0402 land patterns. Pad 1 to pad 1. |
| C_0603_1608Metric | C14663, C19702, C1644, C15849, C19666 | 100 nF, 10 uF, 15 pF, 1 uF, 4.7 uF | all C 0603 | 0 | (0, 0) | 0.075 | high | Pad 1 to pad 1. |
| C_0805_2012Metric | C45783 | 22 uF | C19, C29-C31, C34, C35 | 0 | (0, 0) | 0.050 | high | Pad 1 to pad 1. |
| R_0603_1608Metric | C21190, C25804, C22809, C23138, C23186, C31850, C25819 | 1k, 10k, 15k, 330R, 5.1k, 22k, 47k | all R 0603 | 0 | (0, 0) | 0.072 | high | Pad 1 to pad 1. |

Bold marks a correction the old `export.py` regex table got wrong. That table
also applied no origin offsets: U2 and J3 were placed by the KiCad origin.

No entry is low confidence. The four medium ones are explained in their rows:
symmetric land-pattern residuals (D2, L1), a geometry match for a two-terminal
switch (SW1-SW4), and the USB-C's peg offset (J3). Cross-check: the 35 pairs
this board shares with the 2600 Rev1, SMS, 7800, ChannelF and Studio II tables
agree exactly on rotation and offset. C22809 is new to this board.

Still check **U2, J3, U1, U3 and D7/D8** in JLCPCB's placement preview before
paying:

* U2 and J3, for their origin offsets;
* U1 and U3, for pin 1 (a QFN looks the same at every rotation);
* D7 and D8, for the cathode band.

---
Footprint and symbol data: EasyEDA / JLCEDA official library
(<https://easyeda.com>, <https://lceda.cn>), fetched through the public
component API and cached in `easyeda_cache/`.
