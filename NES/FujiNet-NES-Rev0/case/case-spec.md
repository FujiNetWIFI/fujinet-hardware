# FujiNet-NES Rev0 shell: dimension dossier

Everything the shell depends on, with its source.  Items marked VERIFY were
not measured on a real part and must be checked before printing in anger.

## The board (generated: `case/board-anchors.scad`)

| Item | Value | Source |
|---|---|---|
| Body | 100.0 x 95.5 mm (KiCad x 50..150, y 30..125.5), 1.2 mm thick | NES-EWROM-01 measured outline (nesdev "NES cartridge dimensions") |
| Connector tab | 93.5 x 14.5 mm below the body (y 125.5..140), fingers 1.0-13.0 mm from the edge | same |
| Side notches | left: 5.0 mm deep for 23..25.5 mm above the tab base, 1.5 mm deep for 17..23; right: 5.0 mm for 25.5..28, 1.5 mm for 19.5..25.5 | same |
| Shell-post holes | 5.0 mm at (100, 72) = 53.5 mm above the tab base on the centre line; 3.0 mm at (105.5, 62.5) | same |
| Shell-post pads (no parts) | 3 mm radius at (54.05, 92.2) and (145.95, 92.2); 6.5 mm around the 5 mm hole; 4 mm around the 3 mm hole | NES-EWROM-01 courtyard marks |
| USB-C | centre x 125, face at the top edge (y 30), 9 x 3.3 mm opening; the plug body needs ~12 x 7 mm clearance outside | placement.py |
| microSD (push-push) | centre x 100, slot at the top edge; card protrudes ~2 mm, 12 x 2.5 mm opening | placement.py / TF-015 drawing |
| ESP32 antenna | centre x 66 at the top edge; no metal within 15 mm, keep plastic thin there | Espressif module guidelines |
| Buttons (top face) | RESET (143.5, 72), BOOTSEL (144.5, 112), S3 EN (56.5, 62), S3 BOOT (56.5, 72); TL3342 5.2 mm square, 1.5 mm stem | placement.py |
| Status LED | WS2812B-2020 at (121, 66), light pipe 2-3 mm | placement.py |
| Tallest parts, label side | ESP32 module 3.1 mm, USB-C 3.2, microSD 1.85, buttons 1.6, SRAM 1.2, QFN 0.9 | datasheets |
| Back side | fingers only; everything is on the label side | placement.py |

## The original Game Pak (VERIFY: taken from published figures, not measured)

| Item | Value |
|---|---|
| Outer envelope | 120 x 133 x 19.5 mm (width x height x thickness), label side flat, back side with the grip ridges |
| Connector opening | bottom face, ~96 x 7 mm, the fingers ~10 mm inside the shell |
| PCB seat | board 1.2 mm in rails ~3 mm from the front face; the tab centred on the opening |
| Screws | five on the back (early) or three (late shells); posts pass beside the board at the notches and through the 5 mm hole |
| Label recess | 55 x 97 mm (nesdev), top 7 mm folded over the top face |

The shell in `FujiNet-NES-Shell.scad` is a printable envelope of those
numbers with the openings the board needs; it is not a replica of Nintendo's
internal ribs.  A stock shell (original or reproduction) fits the board as
well, once the USB-C / microSD / button / LED openings are cut: their
positions are in `board-anchors.scad` in board coordinates.

## VERIFY before relying on it

1. Outer envelope and wall thickness against a real Game Pak.
2. Finger exposure: the console's connector contacts touch the fingers
   ~4-9 mm from the edge; the shell's bottom opening must not shadow them.
3. The USB-C and microSD wells reach ~20 mm down from the top face to the
   board edge; check a cable plug and a card can be inserted.
4. Button stem height vs the front wall thickness (1.5 mm stems: wall <= 1.2 mm
   over the switches, or print pushers).
5. Front-loader insertion: nothing may protrude from the label face beyond
   the original shell's thickness, or the tray will not latch.
