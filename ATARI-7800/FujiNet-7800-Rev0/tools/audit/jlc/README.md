# JLCPCB CPL rotations and origin offsets (FujiNet-SMS Rev0)

JLCPCB places each part by the **EasyEDA footprint of its LCSC code**, not by our
KiCad footprint. When the two libraries draw the same package in different
orientations, or put the footprint origin in a different place, the CPL needs a
correction. This directory measures that correction for every
(footprint, LCSC) pair in `tools/design.py`. It compares the footprints pad by
pad and does not use regex tables or assumptions.

| File | What |
|---|---|
| `measure_rotations.py` | the measurement (Python 3 stdlib only) |
| `jlc_rotations.json` | generated table, same schema as `ATARI-2600/Fujiversal-Atari2600-Rev1/tools/audit/jlc/jlc_rotations.json` (plus a few extra diagnostic keys) |
| `easyeda_cache/<LCSC>.json` | raw EasyEDA API responses, so reruns are offline and reproducible |

## Rerun

```sh
python3 tools/audit/jlc/measure_rotations.py             # cache first, fetches only missing codes
python3 tools/audit/jlc/measure_rotations.py --offline   # cache only, never touches the network
python3 tools/audit/jlc/measure_rotations.py --refresh   # re-fetch every component
python3 tools/audit/jlc/measure_rotations.py --markdown  # also print the full table with all notes
```

The script reads `tools/design.py` at run time, so a new part or a changed
LCSC code is picked up automatically. A new code gets fetched, unless you pass
`--offline`. It prints a summary, the entries that are not high confidence,
and any footprint whose LCSC parts need different corrections.

Network notes. The endpoint is the one easyeda2kicad uses:
`https://easyeda.com/api/products/<LCSC>/components?version=6.4.19.5`. It sits
behind CloudFront, which returns **403 to non-browser User-Agents**, including
easyeda2kicad's own, so the script sends a browser UA. CloudFront also returns
403 after about 30 fast requests. The script backs off and retries, then
sleeps 2 s between fetches. A code with no EasyEDA component is cached as the
API's `{"success": false, "code": 404}` answer.

## What the table means

* `rotation_correction_deg` is added to the KiCad rotation in the CPL. Rotating
  the EasyEDA footprint counter-clockwise by this amount lands it on ours.
* `origin_offset_mm` is the position of the EasyEDA placement origin in **our
  footprint's frame** (KiCad local coordinates, +y down, mm, before the
  footprint's own rotation). JLC places by that origin, so the CPL position is
  our origin moved by this vector.
* Diagnostics:
  * `raw_angle_deg` is the pin-1 angle difference.
  * `pattern_rms_err_by_rotation_mm` is the pad-number fit at each rotation.
  * `geometric_rms_err_by_rotation_mm` is the fit when pad numbers are ignored.
    It shows when only the numbering separates two rotations.
  * The offset is computed three ways: `origin_offset_bbox_method_mm`,
    `origin_offset_padcentre_bbox_mm` and `origin_offset_lsq_mm`. The chosen
    value is `mech_origin_offset_mm` when the part has pegs, otherwise the
    bbox method.
  * Pin 1 and polarity: `pin1_*`, `easyeda_pin1_marker_*`,
    `easyeda_package_pin1_suffix` and `symbol_pin_names_agree` (EasyEDA symbol
    pin names against our KiCad symbol's, pad by pad).
  * `flags`, `proxy_results` and `dnp_refs`.

## Method

1. **EasyEDA footprint** (`packageDetail.dataStr`):
   * Units are 10 mil (0.254 mm) and **+y is down**, as in KiCad.
   * The placement origin is `head.x/y`.
   * `PAD` fields used: shape, x, y, w, h, layer, number, hole radius (also
     10 mil), polygon points and rotation. `PLATED=N` pads and `HOLE` shapes
     are NPTH.
   * A layer-101 `CIRCLE` is EasyEDA's pin-1 dot.
   * Pin names come from the symbol `P~` records.
2. **KiCad footprint**: a small s-expression parser reads `FujiNet-SMS.pretty`.
   * Rotated pads and custom-pad primitives are handled.
   * Unnumbered pads (paste windows) are ignored, and `np_thru_hole` pads are
     NPTH.
   * Pads that share a number are compared as one group by their copper-bbox
     centre: an EP with its thermal-via pads, USB-C `SH` tabs, a switch's
     bonded contacts.
   * The parser was checked against `pcbnew.FootprintLoad` for all 26
     footprints, and positions, NPTH and copper extents match exactly.
3. **Pad numbers**, applied in this order:
   1. Identity.
   2. EasyEDA merged numbers (`A1B12` maps to our `A1` + `B12`).
   3. **Diode and LED polarity by symbol pin name** (K/C against A). The pads
      are matched cathode to cathode, never by number.
   4. Leftover pads by nearest geometry, for example the USB-C shell tabs
      `1..4` to `SH`.

   If the numbers cannot describe the same pads (TL3342: EasyEDA `1,2,3,4`
   against our `1,1,2,2`), the whole part is matched by geometry and flagged.
4. **Rotation**: the one of 0/90/180/270 with the lowest RMS group error after
   centring both patterns on their bbox centres. This is the 2600 table's
   convention, and it reproduces that table's RMS values exactly.
5. **Offset**: the difference between the copper-bbox centres. When both
   footprints have NPTH pegs, the mechanical features (pegs + plated THT pads)
   are aligned instead, because the pegs locate the part physically. A
   least-squares pad fit is reported but not used, because it is biased on
   2+1 layouts (SOT-23 gives a spurious 0.07-0.10 mm). Components under
   0.02 mm are reported as 0.
6. **Sanity checks**:
   * the pin-1 angle difference must agree with the fitted rotation within 20 deg;
   * EasyEDA's pin-1 dot must be on its pad-1 side;
   * the package suffix (`-TL`/`-BL`/`-BR`) is recorded;
   * symbol pin names must agree, at least 70 % where both symbols name their
     pins.
7. **Confidence**:
   * `high`: every check passes and the maximum pad residual is 0.2 mm or less.
   * `medium`: residual between 0.2 and 0.35 mm, a mechanical and pad-bbox
     offset that disagree by more than 0.1 mm, or a geometry-only match.
   * `low`: a pad-number mismatch, a failed pin-1 or pin-name check, a
     rotation that is not clearly separated, a residual over 0.35 mm, or a
     proxy footprint.
   * The reason is written in brackets after the level.

For symmetric 2-terminal parts (R, C, L), 0 and 180 deg are physically
equivalent. The table uses the convention **EasyEDA pad 1 on our pad 1**, which
gives 0 for every passive here.

## How export.py should apply it

`tools/export.py` has no CPL step yet. Port the 2600 one
(`ATARI-2600/Fujiversal-Atari2600-Rev1/tools/export.py`, `cpl()`) with two
changes.

**1. Key the lookup by (footprint, LCSC), not by footprint.** The 2600 code
builds `JLC[footprint]`, so the last entry wins. Shared footprints agree on this
board (all three SOT-23 parts are 180, all four SOIC-14 parts are 270), but that
is a coincidence of the libraries. The script warns if they ever diverge.

```python
JLC = {(e['footprint'], e['lcsc']): (e['rotation_correction_deg'], tuple(e['origin_offset_mm']))
       for e in json.load(open(os.path.join(HERE, 'audit', 'jlc', 'jlc_rotations.json')))}
...
part = D.BY_REF[ref]
corr, (dx, dy) = JLC[(part.footprint.split(':')[1], part.lcsc)]
```

**2. Top side.** This is the 2600 formula. `kicad-cli pcb export pos` reports
PosX/PosY with Y up and Rot counter-clockwise; the footprint frame has +y down.

```python
t = math.radians(rot)
x = posx + dx * math.cos(t) + dy * math.sin(t)
y = posy + dx * math.sin(t) - dy * math.cos(t)
cpl_rot = (rot + corr) % 360
```

**Bottom side.** The 2600 export applies the top formula on both sides and
only labels the row `Bottom`. That is correct only for top-side parts. It was
checked with KiCad 10 (pcbnew + `kicad-cli pcb export pos` on a flipped
SOT-23): a B.Cu footprint maps local to board as **R(rot) · mirror-y**, and the
.pos file reports the stored `rot`. For a bottom-side part:

```python
x = posx + dx * math.cos(t) - dy * math.sin(t)     # dy negated: the footprint is mirrored
y = posy + dx * math.sin(t) + dy * math.cos(t)
kicad_rot_of_easyeda_fp = (rot - corr) % 360       # correction subtracts on a mirrored part
```

How JLC interprets a bottom-side rotation number relative to KiCad's is **not
verified here**. Check the bottom placement preview on the order page, or keep
JLC-assembled parts on the top side, as the 2600 board does. On this board,
every offset is (0, 0) except U9 (ESP32), J4 (USB-C) and J2 (header, DNP), so
the position part of the bottom caveat only matters if one of those ends up on
the bottom.

## Results (top side)

The full notes for every row are in `jlc_rotations.json`, or run with
`--markdown`. In the table, "err" is the largest pad-centre difference left
after the correction. It is a land-pattern difference, not a placement error.

| Footprint | LCSC | Part | Refs | Rot | Offset (mm) | err (mm) | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|
| QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm | C39843328 | RP2354B | U1 | **0** | (0, 0) | 0.042 | high | Pin 1 top-left in both (`-TL`). 81/81 symbol pin names agree. |
| QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm | C964632 | CP2102N | U10 | 0 | (0, 0) | 0.073 | high | Pin 1 top-left in both. 29/29 pin names agree. |
| TSOP-I-32_18.4x8mm_P0.5mm | **C5569980** | AS6C4008-55TIN | U2, U3 | 0 (proxy) | (0, 0) | 0.063 | **low** | **No EasyEDA component for C5569980**, see below. |
| SOIC-14_3.9x8.7mm_P1.27mm | C6769 / C5984 / C6764 | 74HCT14 / '27 / '00 | U4, U5, U6, U8 | **270** | (0, 0) | 0.144 | high | EasyEDA `-BL`: horizontal, pin 1 bottom-left. Ours: vertical, pin 1 top-left. |
| SOIC-14_3.9x8.7mm_P1.27mm | C547236 | 74HCT10 | U7 | **270** | (0, 0) | 0.259 | medium | Same as above (EasyEDA `SO-14...-BL`). Pad rows at ±2.734 against ±2.475: a symmetric land-pattern difference. |
| SOT-23 | C37704 | BAT54C | D1 | **180** | (0, 0) | 0.298 | medium | EasyEDA pin 1 bottom-right (`-BR`). Residual is the wider EasyEDA land pattern (symmetric). |
| SOT-23 | C8545 | 2N7002 | Q1 | **180** | (0, 0) | 0.062 | high | `-BR`. G/S/D names agree. |
| SOT-23 | C15127 | AO3401A | Q2 | **180** | (0, 0) | 0.212 | medium | `-BR`. Symmetric land-pattern residual. |
| SOT-363_SC-70-6 | C62892 | UMH3N | U11 | **180** | (0, 0) | 0.112 | high | `-BR`. E/B/C names agree. |
| SOT-23-5 | C51118 | AP2112K-3.3 | U13 | **270** | (0, 0) | 0.200 | high | `-BL` horizontal against our vertical. |
| TSOT-23-6 | C780769 | AP63203WU | U12 | **270** | (0, 0) | 0.062 | high | `-BL` horizontal against our vertical. |
| R_Array_Convex_4x0603 | C25506 / C29718 | 4x100R / 4x10k | RN1, RN2 / RN3 | **270** | (0, 0) | 0.100 | high | EasyEDA horizontal (pins 1-4 along the bottom). Ours vertical. |
| Crystal_SMD_3225-4Pin_3.2x2.5mm | C20625731 | 12MHz | Y1 | 0 | (0, 0) | 0.000 | high | Exact match. Pin 1 bottom-left in both. |
| ESP32-S3-WROOM-1 | C2913202 | ESP32-S3-WROOM-1-N16R8 | U9 | 0 | **(0, +3.62)** | 0.015 | high | Our origin is the module body centre. EasyEDA's is the pad-pattern centre, 3.62 mm toward the pin 15-26 edge. |
| USB_C_Receptacle_HRO_TYPE-C-31-M-12 | C165948 | TYPE-C-31-M-12 | J4 | 0 | **(0, -1.414)** | 0.165 | medium | Merged pads (`A1B12`...) and shell tabs 1-4 matched to `SH`. The mechanical offset (2 pegs + 4 tabs, within 0.022 mm) is used. The pad bbox would give (0, -1.585) and leave the pegs 0.19 mm off. |
| TF-SMD_TF-015 | C113206 | TF-015 | J3 | 0 | (0, 0) | 0.007 | high | Ours was generated from EasyEDA's. Pegs align. |
| PinHeader_1x03_P2.54mm_Vertical | C2937625 | PZ254V-11-03P (DNP) | J2 | **270** | **(0, +2.54)** | 0.000 | high | EasyEDA horizontal with the origin at pin 2. Ours vertical with the origin at pin 1. DNP, so export skips it. |
| LED_WS2812B-2020_PLCC4_2.0x2.0mm | C52917434 | WS2812B-2020-V6 | D3 | 0 | (0, 0) | 0.050 | high | Pin 1 (DO) top-left in both. 4/4 names agree. |
| LED_0603_1608Metric | C2286 | KT-0603R red | D2 | **0** | (0, 0) | 0.037 | high (cathode-matched) | **LED trap:** EasyEDA's symbol has pad 2 = K. Its doc layer has `-` at pad 2 and `+` at pad 1. Ours: pad 1 = K. Matched cathode to cathode, which gives 0. A pad-number match says 180 and would reverse D2. EasyEDA's layer-101 dot sits at pad 1, the **anode**, so that dot marks pin 1, not polarity. |
| D_SOD-523 | C82044 | ESD5Z5.0T1G | D4, D5, D6 | 0 | (0, 0) | 0.012 | high (cathode-matched) | EasyEDA pad 1 = C (cathode), same as ours. |
| D_SMA | C8678 | SS34 | D7 | 0 | (0, 0) | 0.200 | high (cathode-matched) | EasyEDA pad 1 = K, same as ours. Pads at ±2.2 against ±2.0. |
| SW_SPST_TL3342 | C2886898 | TL3342F160QG | SW1-SW4 | 0 | (0, 0) | 0.158 | medium | Numbers not comparable (EasyEDA 1-4, ours 1,1,2,2). Matched by geometry: EasyEDA {3,4} to our 1, {1,2} to our 2, which are the bonded rows in both. 0 and 180 are equivalent for an SPST switch. |
| RPI_L_AOTA-B201610S3R3 | C42411119 | 3.3uH | L1 | 0 | (0, 0) | 0.300 | medium | Pads ±1.0 against ±0.7. Symmetric. 0 and 180 are equivalent. |
| L_Sunlord_SWPA4030S | C62684 | 6.8uH | L2 | 0 | (0, 0) | 0.100 | high | 0 and 180 are equivalent. |
| C_0603_1608Metric | C14663, C19702, C19666, C1644, C15849 | 100nF, 10uF, 4.7uF, 15pF, 1uF | (all C 0603) | 0 | (0, 0) | 0.075 | high | 0 and 180 are equivalent, by convention pad 1 to pad 1. |
| C_0805_2012Metric | C45783 | 22uF | C29, C39-C41, C44, C45 | 0 | (0, 0) | 0.050 | high | Same. |
| R_0603_1608Metric | C23140, C21190, C25804, C25190, C31850, C25803, C23138, C23186, C25819, C23162 | 33R ... 100k | (all R 0603) | 0 | (0, 0) | 0.072 | high | Same. |

### Flags and open items

* **U2/U3, AS6C4008-55TIN, C5569980: not measurable.** LCSC lists it as
  `TSOPI-32` with stock 0. The EasyEDA API returns `404 Component not found`,
  and the Pro `searchByCodes` lookup is empty. C6125241 (the -TR version) and
  C7217846 (AS6C4008A) have no EasyEDA component either. JLC therefore has no
  library footprint to place it by. The EasyEDA library holds **two TSOP-I-32
  8x20 footprints 90 deg apart**:
  * `TSOPI-32_L18.4-W8.0-P0.50-LS20.0-TL` (C2944637, C6883917) gives **0**.
  * `TSOP-32_L8.0-W18.4-P0.50-LS20.0-BL` (C20481033) gives **270**.

  The table uses 0. That footprint's name matches LCSC's package naming, and on
  the proxy part 30 of 32 pin names agree with ours (pins 6 and 9 differ:
  A17/A18 against CE2/NC on the 128K part). Whatever JLC ends up using must be
  **confirmed in the placement preview / DFM** before paying. Also note the
  sourcing problem: with stock 0, JLC cannot assemble this part unless it is
  pre-ordered or consigned.
* **Medium** entries are all explained in the notes:
  * D1, Q2, U7 and L1 have symmetric land-pattern residuals over 0.2 mm, with
    no effect on rotation or offset.
  * The SW1-SW4 match is geometric.
  * J4 uses the mechanical offset.
* **D2:** use 0, never 180. See the LED trap above.

## Cross-check against the Fujiversal-Atari2600 Rev1 table

All **32 (footprint, LCSC) pairs shared with the 2600 table agree exactly** on
rotation and offset. The per-rotation RMS values are identical for 29 of the
32. ESP32, TF-015 and USB-C differ only in the wrong-rotation values, plus
0.050 against 0.042 at 0 deg for USB-C, because grouped pads (EP, shell tabs,
merged pads) are centred slightly differently. The shared pairs include:

* RP-side and S3-side passives, QFN-28, crystal, AOTA, TL3342, BAT54C, AO3401A,
  UMH3N, SOT-23-5, TSOT-23-6, R_Array C29718, ESP32 (0, +3.62),
  USB-C (0, -1.414), TF-015, WS2812, SOD-523, SMA, and the LED C2286 cathode
  match.

Pairs that are new for this board:

* Same footprint, new LCSC code: R 0603 C23140 / C25190, R_Array C25506
  (same EasyEDA package as C29718, 270), SOT-23 C8545 2N7002 (a different
  EasyEDA land pattern from BAT54C's, still 180).
* New footprints: QFN-80 (0), SOIC-14 x4 (270), the 1x03 header
  (270, (0, +2.54)), TSOP-I-32 (proxy).

---
Footprint and symbol data: EasyEDA / JLCEDA official library
(<https://easyeda.com>, <https://lceda.cn>), fetched through the public
component API and cached in `easyeda_cache/`.
