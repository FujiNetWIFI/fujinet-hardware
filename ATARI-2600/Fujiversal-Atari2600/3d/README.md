# 3D models

Bundled so the board renders without KiCad's optional 3D package.
`tools/set_models.py` points every footprint (library and board) at these
through `${KIPRJMOD}/3d/...`, and fails if a BOM part is left without one.

| File | Source |
|---|---|
| `QFN-56-*` (RP2040), `TSSOP-20-*` (74LVC245A), `SOIC-8_5.3x5.3mm-*` (W25Q16), `C_*`, `R_*`, `LED_0603*`, `D_*`, `SOT-*`, `TSOT-23-6`, `Crystal_*`, `L_Sunlord_*`, `QFN-28-*`, `ESP32-S3-WROOM-1`, `SW_SPST_TL3342`, `R_Array_*` | KiCad `kicad-packages3D` (CC-BY-SA 4.0 with the KiCad library exception) |
| `USB-C_HRO_TYPE-C-31-M-12.step` (C165948), `TF-015.step` (C113206) | LCSC/EasyEDA part models, fetched with easyeda2kicad; KiCad has no model for these parts |
| `LED_WS2812B-2020.wrl` | Simple 2.0 x 2.0 x 0.84 mm stand-in (no vendor model published) |

Not modelled by design: the gold fingers (they are board copper), the test
pads and the NPTH mounting holes.
