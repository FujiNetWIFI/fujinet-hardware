# FujiNet-Astrocade cartridge shell: dimension dossier

The Bally Astrocade "Videocade" is a **closed cassette-style box**, not an exposed-finger cart.
The console's connector is a **blade**: a single-row wafer of 26 spring contacts. It enters a slot
in the cart's leading face, under the board, and its springs press **up** against gold lands on
the board's **underside**. The cart lies flat, label up, in an open-top well. Only its leading
section goes under the console's mouth. EJECT pops it back out.

`FujiNet-Astrocade-Shell.scad` is the shell. `part` selects the output:

| `part` | What it gives |
|---|---|
| `bottom` | The bottom half |
| `top` | The top half, turned roof-down for printing by a rotation, never a mirror |
| `plunger` | The RESET plunger |
| `assembled` | The assembly |
| `check` | Renders **empty** only when nothing touches what it must not |

The `check` view covers:
- the board, against both halves;
- 92 top-side part boxes, against both halves;
- the plunger, against the roof and against every part;
- the blade's room, against both halves.

`tools/build_all.sh` runs it, after it regenerates:
- `board-anchors.scad` (buttons, LEDs, ports, holes and the board frame), with `tools/gen_pcb.case_anchors()`;
- `board-parts.scad` (every top-side part's body box and datasheet height), with `tools/case_parts.py`.

## Sources

| Source | What it gives |
|---|---|
| Lance F. Squire (Komb), *Cart shell for the Bally/Astrocade video game system*, Thingiverse thing:173532, 2013, **CC BY 3.0** ("Working cart shell for home brew Bally/Astrocade games") | The stock envelope, slot, blade-stop rib and board plane. These were measured from its two STLs. No code was taken. |
| AtariAge topic 278465, discgolfer72, 2018-05 | An original cart calipers **12.27 mm** thick, and the printed Komb shell 11.98. The poster refined the shell and fitted it to an UltiMulti cart. |
| Jay Tilton pinout (ballyalley `bally_technical_info_(cartridge_port).htm`); MCM Design DWG 1 | 1x26 contacts at 0.100", pin 1 on the left (top view, inserting away from you). Pin 1 GND, 2-9 A7..A0, 10-12 D0-D2, 13 GND, 14-18 D3-D7, 19 A11, 20 A10, 21 /CCS, 22 A12, 23 A9, 24 A8, 25 +5V, 26 GND. |
| sakman55 cart-reader adapter (26 pads, 2.500" span, centred) | The land span is 63.5 mm, centred on the cart's width. |

## Komb's shell, measured

Komb's shell is two 6.0 mm halves, 100 x 63 mm, with 1.29 mm walls. The heights below are given
above the assembled cart's bottom face.

| Feature | Measured | Used here |
|---|---|---|
| Width | 100.0 | `cart_w` 100.0 |
| Thickness | 12.0 (2 x 6.0) | `lead_h` 12.0, the leading 18 mm |
| Blade slot | 74.7 wide, from the floor (1.32) to 7.77 | `slot_w` 74.7, `floor_t` 1.3 to `slot_z1` 7.77 |
| Blade-channel side guides | \|x\| 37.35 .. 38.65, from the leading wall to the rib | the same |
| Blade-stop rib, under the board | front face 12.86 from the leading face, 1.29 thick, top at 7.1 | `stop_y` 12.86. Its top is the board's underside, 7.65. |
| Clamp shelf, over the board | from the leading wall to 18.27 in, underside at 9.25 | a solid section from the leading wall to `lead_d` 18, down to the board's top, 9.25 |
| Board pocket | 7.1 .. 9.25 (2.15) | The 1.6 mm board is clamped with its top at 9.25 (`z_b` 7.65). That is where the blade's springs push a floating 1.6 mm board in Komb's shell. |
| Leading wall | 1.29 | `lead_wall` 1.3. The board's leading edge is 0.3 behind it, 1.6 mm from the face. |

The lands run from 2.6 to 16.6 mm in from the leading face. The blade can reach at most 12.86 mm,
the rib. The lands' plated escapes are 19.0 mm in, behind the rib, so the blade cannot touch them.

## The FujiNet shell

| Item | Value | Why |
|---|---|---|
| Leading section | 100 x 12.0, 0 .. 18 mm deep | Komb. No top-side part is within 19.3 mm of the face. |
| Chamfer | 45 degrees, 18 .. 21.5 mm | SW3 and D7 (SMA, 2.45 mm) start about 20 mm in. |
| Rear body | 15.5 mm tall, 1.5 mm roof | The USB-C (3.31) and the ESP32-S3 module (3.3) stand on the board top at 9.25. |
| Trailing face | 61.2 mm from the leading face | The board edge is 59.6 mm in; 0.3 mm clearance and a 1.3 mm wall follow. |
| USB-C | 9.8 x 4.0 opening, plus a 12.8 x 7.0 x 0.8 overmold counterbore | The receptacle's face is 0.5 mm past the board edge, so a plug seats with 0.3 mm to spare. |
| microSD | 14 x 2.2 slot, and a finger dish over the card's end | The push-push card is reached through the dish. |
| Antenna hood | Behind the trailing face, x = U2 +/- 0.4, out to **67.65 mm** | The ESP32-S3 antenna overhangs the board edge by 6.45 mm. The hood keeps plastic, not air, around it. |
| Side walls | 1.5 mm, inner cavity square | The 96 mm board has 0.5 mm per side. |
| Screws | 4x M3 from the bottom, through the board, into 2.6 mm pilots in the top half | **M3x10 at the front holes** (the shell is 12 mm there, about 2 mm of thread) and **M3x12 at the rear** (about 4 mm) |
| RESET | A printed plunger in a guide, cap 0.6 mm proud | At rest the stem is 0.15 mm above the SKQGABE010's stem, and the switch travels 0.25 mm. |
| BOOTSEL, S3 EN, S3 BOOT | 2.2 mm pinholes | They take a paperclip. The switch stems are 4.75 mm below the face. |
| LEDs | 3.0 mm window over D3 (WS2812B), 2.0 mm window over D1 | |
| Label recess | 35 x 32 x 0.4 mm, left of centre | It clears the buttons, the LED windows and the microSD dish. |

Print the bottom half floor-down, the top half roof-down and the plunger cap-down. Resin (JLC3DP)
or FDM works, with no supports. All three exports are 2-manifold.

## Still to VERIFY on a console

1. **Mouth depth.** The shell is 12.0 mm thick only for its leading 18 mm, and the chamfer rises
   behind that. If the console's mouth covers more than 18 mm of the cart, the chamfer meets it.
   Komb's whole shell is 12 mm thick, so it never tested this.
2. **Well length.** The cart is 61.2 mm deep, and 67.65 mm at the antenna hood (stock is about
   63). The well behind the mouth must take the hood.
3. **Well rim.** The 15.5 mm rear body and the trailing-face USB-C / microSD must clear the
   well's rim and side clearance.
4. **Contact force.** The board is clamped 0.55 mm higher than the floor of Komb's board pocket.
   That is where the blade lifts a floating board. Check that the springs wipe the lands with
   real force, and look at the lands after a few insertions.
5. **Width.** 100.0 mm is Komb's value. An original was estimated at 102 +/- 2 from photos. Komb's
   shell works in a console.
