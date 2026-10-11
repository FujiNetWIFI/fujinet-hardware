# 3D models bundled with FujiNet-ChannelF Rev0

`tools/set_models.py` points every footprint at `${KIPRJMOD}/3d/<file>`, so the board renders
(`kicad-cli pcb render`, the 3D viewer) without KiCad's optional model package. The models are for
the renders and the shell design only; the fab never sees them.

| File | Source | Licence |
|---|---|---|
| `C_*`, `R_*`, `LED_0603_*`, `D_SMA`, `D_SOD-523`, `SOT-23`, `SOT-23-5`, `SOT-363_SC-70-6`, `TSOT-23-6`, `Crystal_SMD_3225-*`, `L_Sunlord_SWPA4030S`, `QFN-28-*`, `ESP32-S3-WROOM-1`, `SW_SPST_TL3342` (.step) | KiCad `kicad-packages3D`, copied from `ATARI-5200/FujiNet-5200-Rev0/3d/` | CC-BY-SA 4.0 with the KiCad library exception |
| `QFN-56-1EP_7x7mm_*`, `SOIC-8_5.3x5.3mm_*` (.step) | KiCad `kicad-packages3D`, copied from the `atari2600-rev0` branch (`ATARI-2600/Fujiversal-Atari2600/3d/`) | CC-BY-SA 4.0 with the KiCad library exception |
| `TSSOP-24_4.4x7.8mm_P0.65mm.step` | KiCad `kicad-packages3D` (gitlab.com/kicad/libraries/kicad-packages3D, master, fetched 2026-10-10) | CC-BY-SA 4.0 with the KiCad library exception |
| `TF-015.step` | SOFNG model via LCSC/EasyEDA C113206 | vendor model |
| `USB-C_HRO_TYPE-C-31-M-12.step` | HRO model via LCSC/EasyEDA C165948 | vendor model |
| `LED_WS2812B-2020.wrl` | simple stand-in (no vendor model published) | CERN-OHL-W-2.0 (this project) |

No model: `ChannelF_Videocart_Edge_22` (board copper), `TestPoint_Pad_D1.5mm`, `MountingHole_*`,
`Fiducial_*`.
