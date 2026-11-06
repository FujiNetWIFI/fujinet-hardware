# 3D models bundled with Inty-FujiCard

`tools/set_models.py` points every footprint at `${KIPRJMOD}/3d/<file>`, so the board renders (`kicad-cli pcb render`, the 3D viewer) without KiCad's optional model package or the network.

| File | Source | Licence |
|---|---|---|
| `*.stpZ` (18 models) | the EasyEDA / LCSC models Yannick's footprints carry (each footprint's `JLC_3DModel` id, `easyeda_models.json`), fetched by `tools/fetch_models.py` from EasyEDA's model server, normalised (below) and gzipped (KiCad reads compressed STEP); placed with the offsets EasyEDA gives them | vendor models, redistributed with their solids moved, otherwise as supplied |
| `RP2354A_QFN-60_7x7.step` | Raspberry Pi RP2354A model via LCSC/EasyEDA C41378174, as FujiNet-ColecoVision / Arcadia Rev0 bundle it (Yannick's QFN-60 footprint carries no model id) | vendor model, redistributed as supplied |
| `LED_WS2812B-2020.wrl` | simple 2 x 2 mm stand-in for the SK6805-EC20 (no model id on its footprint), as the sister carts use | CERN-OHL-W-2.0 (FujiNet) |

**Normalised.** EasyEDA places a model by its solids' bounding box: the box's xy centre goes on the footprint's 3D origin, and its bottom on the board surface plus the node's z. KiCad's importer writes those offsets as if each model's own origin were that centre and bottom. `tools/fetch_models.py` therefore moves each model's solids (every 3D point except the representation's own placement, which KiCad's STEP reader applies on top) to put their vertex box centred at the origin with the lowest vertex at z = 0. Without it:
- the microSD socket's solids sat 29 mm off their origin and 6 mm under the board (only its pads showed);
- the SOD-523 diodes were wholly below the surface;
- the USB-C sank 2.6 mm;
- the 0402 / 0603 parts were half in the board.

No model: K1 (the edge fingers), the test pads and the holes need none.
