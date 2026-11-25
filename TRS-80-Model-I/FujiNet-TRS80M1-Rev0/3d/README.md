# 3D models bundled with FujiNet-TRS80M1 Rev0

`tools/set_models.py` points every footprint at `${KIPRJMOD}/3d/<file>`, so
the board renders (`kicad-cli pcb render`, the 3D viewer) without KiCad's
optional model package.

| File | Source | Licence |
|---|---|---|
| `C_*`, `R_*` (0402 and 0603), `LED_0603_*`, `SOT-23`, `SOT-23-5`, `SOT-23-6`, `SOT-363_SC-70-6`, `Crystal_SMD_3225-*`, `L_Sunlord_SWPA4030S`, `QFN-28-*`, `ESP32-S3-WROOM-1`, `SW_SPST_TL3342`, `R_Array_Convex_4x0603`, `TSSOP-20_4.4x6.5mm_P0.65mm` (.step) | KiCad `kicad-packages3D` (gitlab.com/kicad/libraries/kicad-packages3D), as bundled with FujiNet-O2 / ColecoVision Rev0 | CC-BY-SA 4.0 with the KiCad library exception |
| `SSOP-8_2.95x2.8mm_P0.65mm`, `IDC-Header_2x20_P2.54mm_Horizontal`, `PinHeader_2x10_P2.54mm_Vertical`, `Fuse_1206_3216Metric`, `SW_DIP_SPSTx03_Slide_6.7x9.18mm_W8.61mm_P2.54mm_LowProfile` (.step) | KiCad `kicad-packages3D`, tag 9.0.0 (fetched 2026-11-24). The IDC header and the DIP switch are KiCad's generic models, turned onto the EasyEDA-derived footprints (`tools/make_fp_m1.py`) | CC-BY-SA 4.0 with the KiCad library exception |
| `RP2354B_QFN-80_10x10.step` | Raspberry Pi RP2354B model via LCSC/EasyEDA C39843328 (easyeda2kicad), as bundled with FujiNet-StudioII Rev0 | vendor model, redistributed as supplied |
| `AOTA-B201610S3R3.step` | Abracon model via LCSC/EasyEDA (easyeda2kicad) | vendor model, redistributed as supplied |
| `TF-015.step` | SOFNG model via LCSC/EasyEDA C113206 | vendor model |
| `USB-C_HRO_TYPE-C-31-M-12.step` | HRO model via LCSC/EasyEDA C165948 | vendor model |
| `LED_WS2812B-2020.wrl` | simple stand-in (no vendor model published) | CERN-OHL-W-2.0 (this project) |

No model: `TestPoint_Pad_D1.5mm`, `MountingHole_*` and `Fiducial_*` need none.
