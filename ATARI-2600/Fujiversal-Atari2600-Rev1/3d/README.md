# 3D models bundled with Fujiversal-Atari2600 Rev1

`tools/set_models.py` points every footprint at `${KIPRJMOD}/3d/<file>`, so
the board renders (`kicad-cli pcb render`, the 3D viewer) without KiCad's
optional model package.

| File | Source | Licence |
|---|---|---|
| `C_*`, `R_*` (0402 and 0603), `LED_0603_*`, `D_SMA`, `D_SOD-523`, `SOT-23`, `SOT-23-5`, `SOT-363_SC-70-6`, `TSOT-23-6`, `Crystal_SMD_3225-*`, `L_Sunlord_SWPA4030S`, `QFN-28-*`, `ESP32-S3-WROOM-1`, `SW_SPST_TL3342` (.step) | KiCad `kicad-packages3D` (gitlab.com/kicad/libraries/kicad-packages3D, master, 2026-10-01) | CC-BY-SA 4.0 with the KiCad library exception |
| `RP2354A_QFN-60_7x7.step` | Raspberry Pi RP2354A model via LCSC/EasyEDA C41378174 (easyeda2kicad), as bundled with Astrocade/rev0 | vendor model, redistributed as supplied |
| `AOTA-B201610S3R3.step` | Abracon model via LCSC/EasyEDA (easyeda2kicad) | vendor model, redistributed as supplied |
| `TF-015.step` | SOFNG model via LCSC/EasyEDA C113206 | vendor model |
| `USB-C_HRO_TYPE-C-31-M-12.step` | HRO model via LCSC/EasyEDA C165948 | vendor model |
| `LED_WS2812B-2020.wrl` | simple stand-in (no vendor model published) | CERN-OHL-W-2.0 (this project) |

No model: `Atari2600_Cart_Edge_24`, `TestPoint_Pad_D1.5mm`, `MountingHole_*` and
`Fiducial_*` need none.
