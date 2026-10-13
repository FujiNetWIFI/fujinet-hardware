# 3D models bundled with FujiNet-SMS Rev0

`tools/set_models.py` points every footprint at `${KIPRJMOD}/3d/<file>`, so
the board renders (`kicad-cli pcb render`, the 3D viewer) without KiCad's
optional model package.

| File | Source | Licence |
|---|---|---|
| `C_*`, `R_*`, `LED_0603_*`, `D_SMA`, `D_SOD-523`, `SOT-23`, `SOT-23-5`, `SOT-363_SC-70-6`, `TSOT-23-6`, `Crystal_SMD_3225-*`, `L_Sunlord_SWPA4030S`, `QFN-28-*`, `TSOP-I-32_*`, `SOIC-14_*`, `ESP32-S3-WROOM-1`, `SW_SPST_TL3342` (.step) | KiCad `kicad-packages3D` (gitlab.com/kicad/libraries/kicad-packages3D, master, 2026-10-01) | CC-BY-SA 4.0 with the KiCad library exception |
| `RP2354B_QFN-80_10x10.step` | Raspberry Pi RP2354B model via LCSC/EasyEDA C39843328 (easyeda2kicad); KiCad has no QFN-80 0.4 mm model | vendor model, redistributed as supplied |
| `AOTA-B201610S3R3.step` | Abracon model via LCSC/EasyEDA (easyeda2kicad) | vendor model, redistributed as supplied |
| `TF-015.step` | SOFNG model via LCSC/EasyEDA C113206 | vendor model |
| `USB-C_HRO_TYPE-C-31-M-12.step` | HRO model via LCSC/EasyEDA C165948 | vendor model |
| `LED_WS2812B-2020.wrl` | simple stand-in (no vendor model published) | CERN-OHL-W-2.0 (this project) |

No model: `SMS_Cart_Edge_50`, `TestPoint_Pad_D1.5mm`, `MountingHole_*`, `Fiducial_*` and the
(DNP) `PinHeader_1x03` debug header.  Copied from `NES/FujiNet-NES-Rev0/3d/`.
