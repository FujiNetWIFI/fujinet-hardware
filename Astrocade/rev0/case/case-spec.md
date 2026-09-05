# FujiNet-Astrocade cartridge case — dimension dossier

The Bally Astrocade "Videocade" cartridge is a **closed cassette-style box**,
not an exposed-finger cart. The console's cassette connector is a **blade**:
a single-row wafer carrying 26 spring contacts that enters a slot in the
cartridge's leading face and presses **upward** against gold lands on the
**underside** of the cartridge PCB. The cartridge lies flat, label up, in an
open-top well on the console; only the leading ~20 mm enters the console's
mouth. EJECT pops it back out.

## Interface facts (sourced)

| Item | Value | Source |
|---|---|---|
| Contacts | 1×26, 0.100" (2.54 mm) pitch, single side | Jay Tilton pinout (ballyalley); MCM Design DWG 1; sakman55 cartreader adapter ("26 pin (1x26) 0.100" spacing") |
| Contact span | 63.5 mm centers, **centered on cart width** | adapter gerbers (26 pads, 2.500" span, centered); photo of cart on adapter (centered ±0.5 mm) |
| Pinout | 1 GND, 2–9 A7…A0, 10–12 D0–D2, 13 GND, 14–18 D3–D7, 19 A11, 20 A10, 21 /CCS, 22 A12, 23 A9, 24 A8, 25 +5V, 26 GND | ballyalley `bally_technical_info_(cartridge_port).htm`; MCM DWG 1 (0-indexed, identical) |
| Orientation | Top view (label up), insertion direction away from you: contact 1 on the **left** | derived twice: adapter photo labels + Tilton "looking at the cart slot, 1..26 left to right"; both agree |
| Blade width | ≈74 mm (connector cut to 74 mm fits the cart slot) | sakman55 build notes |
| Blade thickness | 3.6–3.8 mm total works ("1.2 mm PCB + two ~1.2 mm spacers, +2.4 to +2.6 mm") | sakman55 build notes |
| Blade reach | ~17–18 mm into the cart | scaled from adapter FRONT photo (PCB = 100.45 mm known width) |
| Cart footprint | ≈102 × 65 mm (±2) — essentially compact-cassette-sized, a hair larger | photogrammetry: cart on adapter photo, adapter PCB = 100.45 mm ruler |
| Cart thickness | ≈12.5 mm (cassette-like) | est. from MCM shell photos; **VERIFY** |
| Shell construction | two halves, 4 corner screws, label recess on top | MCM Design photos |

## What the console constrains — and what it doesn't

- The **mouth** constrains only the leading ~20 mm: that section must stay at
  original thickness (~12.5 mm) and present the blade slot at the correct
  height above the cart bottom.
- The **well is open-topped**: the rear body can be taller than an original
  cart. The Rev0 shell uses 17 mm so the trailing-edge USB-C and microSD sit
  above the well rim. **VERIFY** the rim height and the well's trailing-side
  clearance on a real console.
- The cart's **top face is fully exposed** when inserted → the RESET button
  (SW1), BOOTSEL pinhole (SW2) and WS2812 light pipe act through the top face.

## PCB ↔ shell mapping

PCB is 96 × 58 × 1.6 mm (`FujiNet-Astrocade-Rev0.kicad_pcb`, frame
x 52..148 / y 30..88). Cart X = board_x − 100; cart Y = (88 − board_y) + 2.
Contact lands: 26 × (1.7 × 14 mm) on B.Cu, land row centered, land 1 at
board x = 131.75 (cart top view: left, insertion away). PCB underside sits
4.0 mm above the inner floor (blade + spring room); the top shell's clamp
ribs back the PCB above the contact zone. Four M3 posts at board
(55,33)(145,33)(55,84)(145,84) = cart (∓45, 57)/(∓45, 6).

## Open items before printing/ordering

1. Caliper a real Videocade: width, depth, thickness, slot width/height and
   its offset from the cart bottom, screw locations of the mouth.
2. Console: mouth interior depth/stop, well rim height, well trailing-side
   clearance (the ESP32 antenna window tip sits ~1.4 mm proud).
3. TL3342 actuator height: with the PCB top at 8.8 mm and the roof underside
   at 15.4 mm, the stock 1.6 mm-actuator TL3342 needs a **printed plunger**
   in the 4.5 mm RESET hole (or fit the tall-actuator TL3342 variant).
4. Blade spring compression: pcb_seat_z (4.0 mm) sets land height; tune so
   the springs wipe with real force after measuring an original cart's PCB
   height above its slot floor.

`FujiNet-Astrocade-Shell.scad` is parametric over all of the above
(`part = "bottom" | "top" | "assembly"`).
