# 3D models bundled with FujiNet-StudioII Rev0

`tools/set_models.py` points every footprint at `${KIPRJMOD}/3d/<file>`, so the board renders
(`kicad-cli pcb render`, the 3D viewer) without KiCad's optional model package.  The models are for
the renders and the shell design only; the fab never sees them.

| File | Source | Licence |
|---|---|---|
| `C_*` / `R_*` (0402, 0603), `LED_0603_*`, `SOT-23`, `SOT-23-5`, `SOIC-14_*`, `TSSOP-20_*`, `Crystal_SMD_3225-*`, `SW_SPST_TL3342` (.step) | KiCad `kicad-packages3D`, copied from `ATARI-5200/FujiNet-5200-Rev0/3d/` and (the 0402 bodies) `ATARI-2600/Fujiversal-Atari2600-Rev1/3d/` | CC-BY-SA 4.0 with the KiCad library exception |
| `C_0805_*`, `R_Array_Convex_4x0603`, `SOT-363_SC-70-6`, `TSOT-23-6`, `L_Sunlord_SWPA4030S`, `QFN-28-1EP_5x5mm_*`, `ESP32-S3-WROOM-1` (.step) | KiCad `kicad-packages3D`, copied from `Fairchild-Channel-F/FujiNet-ChannelF-Rev0/3d/` | CC-BY-SA 4.0 with the KiCad library exception |
| `SOT-583-8.step`, `SOT-23-6.step` | KiCad `kicad-packages3D` (gitlab.com/kicad/libraries/kicad-packages3D, master, fetched 2026-10-11) | CC-BY-SA 4.0 with the KiCad library exception |
| `RP2354B_QFN-80_10x10.step` | Raspberry Pi RP2354B model via LCSC/EasyEDA C39843328 (easyeda2kicad); KiCad has no QFN-80 0.4 mm model | vendor model, redistributed as supplied |
| `AOTA-B201610S3R3.step` | Abracon model via LCSC/EasyEDA (easyeda2kicad) | vendor model, redistributed as supplied |
| `USB-C_HRO_TYPE-C-31-M-12.step` | HRO model via LCSC/EasyEDA C165948 | vendor model, redistributed as supplied |
| `TF-015.step` | SOFNG model via LCSC/EasyEDA C113206 (from FujiNet-ChannelF Rev0) | vendor model, redistributed as supplied |
| `LED_WS2812B-2020.wrl` | simple stand-in (no vendor model published; from FujiNet-ChannelF Rev0) | CERN-OHL-W-2.0 (this project) |

The TS-1187A buttons render with the TL3342's model (5.2 x 5.2 x 1.5 mm against 5.1 x 5.1 x 1.5): no
model is published for it.  No model: `StudioII_Cart_Edge_22`, `TestPoint_Pad_D1.5mm`,
`MountingHole_*`, `Fiducial_*` and the (DNP) `PinHeader_1x03` debug header.
