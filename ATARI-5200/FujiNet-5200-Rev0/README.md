# FujiNet-5200 Rev0

An all-in-one **Atari 5200 FujiNet cartridge**: one board in the 36-pin cartridge slot that
carries both halves of the FujiNet stack.

**The cart half: RP2354B** (RP2350B + 2 MB flash, QFN-80) at 200 MHz.

- Runs the `fuji5200` cart firmware from `fujinet-firmware/pico/atari-5200`.
- Reads A0-A13 and the two cart enables (/EN40, /EN80) straight off the console's 5 V bus,
  through its 5 V-tolerant pads (GPIO0-15), and follows them as a mask ROM would.
- Puts each byte on GPIO16-23, into a **74HCT541** whose outputs are the edge's D0-D7.
- A **74HCT08 + 74HCT14** opens the '541 only while all three hold: an enable is low, the console
  is powered (PWR_OK), and the RP says it is serving (BUF_EN).
- A **74LVC1G17** squares the 2-port console's diode-isolated PHI2.

**The FujiNet half: ESP32-S3-WROOM-1-N16R8**, running the `fujiversal-atari5200` build of
fujinet-firmware.

- It is the RP's USB host on IO19/IO20, and it re-flashes the RP over PICOBOOT.
- USB-C: power, plus a CP2102N UART with UMH3N auto-program.
- microSD, a WS2812B status LED, and RESET / BOOTSEL / S3 EN / S3 BOOT buttons.

**Power:** +5V is the OR of three sources:

- the console's 5 V, through a P-FET;
- USB VBUS;
- the universal consoles' raw adapter DC on edge pin 11, through a 5 V buck.

The console path switches off whenever either of the other two is present.

**Status (2026-10-09):** schematic regenerated and audited; board placed, routed and packaged for
JLCPCB and PCBWay. Not yet built. See *Before ordering* and *Bring-up*.

| Check | Result |
|---|---|
| ERC, all severities | 0 |
| `tools/check_nets.py`: netlist vs `a52_cart.h`, the CX5200 FSM edge map, the S3 pin map, FT-pad rules | 366 / 366 |
| `tools/check_glue.py`: the '541 enables vs `a52_glue_drive()`, every input | 16 / 16 |
| Netlist parity: drawn sheets vs `design.py`, names included | every net |
| Mirror check: each sheet's parts in board order | tau 1.00 on all five sheets |
| `tools/audit/edge_orientation.py` | OK |
| Deep review (kicad-happy evidence gate) | 30 / 30 findings verified against datasheet pages |
| kicad-happy SPICE + `tools/audit/spice_checks.py` | 21 / 21; PHI2, PWR_OK and console-gate decks pass |
| DRC with schematic parity, all severities | 0 violations, 0 unconnected, 0 parity issues |
| `tools/audit/check_fab.py` / `check_gerbers.py` | 14 / 14 / all pass |
| JLCPCB stock (`tools/audit/sourcing.py`) | 46 lines, 0 short for 5 boards; ~US$17 of parts per board |

## Sheets

The schematic is drawn the way the board is built. Every sheet is the board turned so that the
fingers face left (board south -> page left, north -> right, west -> top, east -> bottom), with
each part where it sits on the board. Signals flow left to right, from the cartridge slot to the
USB-C. `tools/sch_place.py` holds every sheet to the board's order.

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | the board outline with a block per sheet, the nine signals between sheets, notes |
| 2 | `cart-bus` | the 36-pin edge, 74HCT541, the '08 / '14 glue, the RP2354B's GPIOs, PHI2 buffer, interlock, PWR_OK and ADC senses, debug UART, scope pads |
| 3 | `rp-core` | RP2354B supplies and decoupling ring, core regulator, crystal, SWD, RUN / BOOTSEL, USB to the S3 |
| 4 | `fujinet` | ESP32-S3, microSD, WS2812B, S3 EN / BOOT |
| 5 | `usb` | USB-C, CP2102N, auto-program pair |
| 6 | `power` | the three-source +5V OR, the raw-DC buck, the 3.3 V buck, the RP's LDO |

## Edge connector

The edge pinout is taken from Atari's CX5200 Field Service Manual (Rev 4, 1983). It has
schematics of CA018087 (the original 4-port), CA020108 (the universal 4-port) and CA021374 (the
2-port).

The geometry is from Grand Idea Studio's Pixels Past gerbers, tdididit's a52 library, sanni's
cartreader adapter, and the Sullins connector datasheet. `tools/audit/edge_orientation.py`
checks the footprint against them.

| Pin | Signal | Net | Pin | Signal | Net |
|---|---|---|---|---|---|
| 1-8 | D0-D7 | '541 Y | 19, 20 | A0, A1 | GPIO0, 1 |
| 9 | /Enable $80-$BF | EN80_N | 21, 22 | A3, A4 | GPIO3, 4 |
| 10 | /Enable $40-$7F | EN40_N | 23 | GND (shield) | GND |
| 11 | raw DC (universal boards) | UNREG -> JP2 -> PTC -> buck | 24 | GND (CA018087) / video in (universal) | **open** |
| 12, 13 | GND | GND | 25 | GND | GND |
| 14 | GND (CA018087) / PHI2 (2-port, via CR9) | PHI2 -> 74LVC1G17 | 26 | +5 V from VR1 | CONS_5V |
| 15, 16, 17 | A6, A5, A2 | GPIO6, 5, 2 | 27, 29, 31 | A7, A8, A9 | GPIO7, 8, 9 |
| 18 | CI1, interlock (short finger) | ILK_A, JP1 | 28, 30 | NC, OSC (universal) | **open** |
| | | | 32-35 | A13, A10, A12, A11 | GPIO13, 10, 12, 11 |
| | | | 36 | CI2, interlock (short finger) | ILK_B, JP1 |

**Faces.** Pins 1-18 are on the label face, which is F.Cu, the component side. Pin 1 (D0) is at
the left when seen from that face with the fingers down. Pin 37-k sits behind pin k.

**Short fingers.** Pins 18 and 36 start 1.9 mm from the edge; the others start at 0.6 mm. They
make contact last and break first, as on every stock cart.

**No R/W, and the enables are not PHI2-qualified.** The enables are plain 74LS139 decodes of A14
/ A15. The cart answers reads only, and the '541 drives whenever an enable is low, exactly as a
stock ROM does.

**Never ground 11, 24, 28 or 30.**

- 11 is the adapter's raw DC on the universal boards, live even with the console switched off.
- 24 is the VCS adaptor's video input on the universal boards.
- 30 goes into the colour oscillator.

## RP2354B pin map

The pin map is exactly `a52_cart.h`. `tools/check_nets.py` reads every `*_PIN` define and fails
if the header names a pin this board does not wire, or the board wires one the header does not
name.

| GPIO | Net | Goes to |
|---|---|---|
| 0-13 | A0-A13 | the edge, directly |
| 14, 15 | EN40_N, EN80_N | edge 10, 9; also the 74HCT08 |
| 16-23 | RP_D0-7 | 74HCT541 A8..A1 (channels reversed; outputs only) |
| 24 | PWR_OK | 74HCT14 output (console 5 V sense) |
| 25 | PHI2_RP | 74LVC1G17 output (2-port only) |
| 26 | BUF_EN | the glue; R25 4.7k pull-down (RP2350-E9) |
| 27 | RP_LED | 1k, red LED |
| 28 | ILK | the DNP interlock switch's driver |
| 40 | VSENSE_ADC | ADC0: CONS_5V through 100k / 100k (0.5 x), 100 nF |
| 44, 45 | DBG_TX, DBG_RX | J4 (DNP), 3.3 V only |

- GPIO40-47 are not 5 V tolerant. `check_nets.py` asserts that only passives and the 3.3 V debug
  header reach them.
- The bus inputs have no pulls. The firmware turns the pad pulls off (RP2350 erratum E9).

## Glue

`a52_glue_drive()`: `drive = !(en40_n && en80_n) && pwrok && bufen`.

```
/OE1 = EN_ANY_N = /EN40 AND /EN80        74HCT08: either enable low
/OE2 = SERVE_N  = NOT(PWR_OK AND BUF_EN) 74HCT08 + 74HCT14: console powered and the RP serving
```

- **PWR_OK.** CONS_5V goes through 22k / 100k into a 74HCT14 Schmitt and is inverted twice. It
  is high once the console rail passes 2.3-2.6 V.
- **BUF_EN.** A 4.7k pull-down keeps the '541 shut until the firmware drives GPIO26. That is
  under the 8.2k the RP2350-E9 latch needs.
- **PHI2 (2-port).** The console reaches pin 14 through CR9, a 1N914 with its anode at the pin,
  so it can only pull PHI2 low, to 0.94-1.09 V. R29 4.7k pulls the pin up to CONS_5V, and U11, a
  74LVC1G17 at 5 V, squares it: VT- min 1.32 V, +0.24 V of margin at the worst corner.

  The pull-up goes to CONS_5V and not +5V. With the console off and USB on, a pull-up to +5V
  would feed the console's LS125 through CR9.

## Power

**Q3, AO3401A: console 5 V -> +5V.** D = CONS_5V, S = +5V, gate = CONS_OFF.

- CONS_OFF = VBUS OR PRE5V, through D9 (BAT54C), with R23 100k to GND.
- The console path is fully on whenever the console alone powers the cart.
- R3 and R22, 4.7k each, keep the SS34s' reverse leakage off the OR. At 500 uA each, VGS is still
  -2.9 V.

**D4, SS34: USB VBUS -> +5V.**

**Edge 11 raw DC -> +5V.** The chain is:

1. JP2, a bridged jumper. Cut it to take nothing from pin 11.
2. F1, a 0.35 A / 30 V PTC.
3. R30, 2.2R, to limit inrush when the cart goes in with the adapter live.
4. U10, an AP63205 (5 V, 3.8-32 V in).
5. D8, an SS34.

On the universal consoles this takes the whole cart off VR1.

**+5V feeds:**

- the '541, '08, '14 and LVC1G17;
- the WS2812B;
- the AP2112K LDO (+3V3_RP, every RP2354B supply pin), which rises with +5V;
- the AP63203 buck (+3V3: S3, microSD, CP2102N).

**Budget:** ~470 mA at a WiFi TX burst, ~170 mA on average (`tools/audit/margins.py`).

**Warning: the original 4-port console (CA018087).** VR1 there is a **0.5 A 78M05** that also
feeds the console's RAM and controllers, and that board has no raw DC on pin 11. Without USB, a
WiFi burst can pull VR1 into current limit. On those consoles, run with USB-C plugged in for
WiFi. The universal consoles (CA020108, CA021374) feed the cart from the adapter instead.

## Interlock

Pins 18 and 36 are shorted by **JP1**, a bridged solder jumper, as a stock cartridge shorts them.
The stock jumper closes Q8 / Q6's base circuit (34-61 mA at ~0.2 V), which switches VR1 on.

Beside JP1, all DNP:

- **Q2**, a 2N7002 low-side switch: D on 36, S on 18, gate pulled to +5V by R26.
- **Q1**, a 2N7002 driver on GPIO28.
- **R24**, a 4.7k pull-down on GPIO28.

To let the firmware open the interlock (a console power cycle), cut JP1 and fit them. The cart
must then be powered from USB or the raw DC first, since VR1 is what that switch turns on.

## Board

**Outline.** T-shaped, 84 x 98 mm (`tools/placement.py`, `docs/floorplan-study.md`):

- the 47.8 mm tab;
- the original cart board's 61 mm lower body, up to 38 mm from the edge;
- a 45-degree step out to the 84 mm upper body that carries the FujiNet half.

It needs a custom shell. The stock 5200 shell holds a 61 x 89.5 mm board between ribs.
`case/board-anchors.scad` gives a shell design the outline, the three screws, the button
pinholes, the LEDs, the USB-C / microSD / antenna openings and a label recess.

**Stack-up.** 6 layers, 1.6 mm:

| Layer | Use |
|---|---|
| F.Cu | every part; fingers 1-18; signals and a GND pour |
| In1 | GND |
| In2, In3 | signals |
| In4 | power: +3V3 north; a +5V island south and east; +3V3_RP under the RP2354B ring; DVDD under its core |
| B.Cu | fingers 19-36; signals and a GND pour |

**Data path.** The 74HCT541 stands over the D0-D7 fingers, and its channels are taken in
reverse, so finger -> '541 -> RP GPIO16-23 crosses nothing on F.Cu.

## Fab packages

`tools/export.py` writes them, and `tools/audit/check_fab.py` / `check_gerbers.py` check them.

- `exports/jlcpcb/`: `ORDER-JLCPCB.md`, gerbers with an order-number spot, `BOM-JLCPCB.csv`, and
  `CPL-JLCPCB.csv` with rotations corrected to each LCSC part's EasyEDA footprint
  (`tools/audit/jlc/`, measured pad by pad).
- `exports/pcbway/`: `ORDER-PCBWay.md`, gerbers, `BOM-PCBWay.csv` (MPN / manufacturer),
  `Centroid-PCBWay.csv` (KiCad's own rotations), and `Assembly-top.pdf`.

Both need:

- 6 layers, 1.6 mm, ENIG;
- **hard gold fingers with a 30-45 degree bevel** on the 47.8 mm tab edge only;
- via-in-pad filled and capped under the RP2354B;
- top-side assembly.

## Before ordering

1. **The tab.** Print `docs/tab-overlay-1to1.pdf` at 100 % and check its 50 mm ruler. Lay a real
   5200 cartridge board on it:
   - pins 1-18 on the label side, pin 1 at the left;
   - the finger span, the 47.8 mm tab and the two short fingers must match.
2. **Thickness.** The console connector takes 1.57 +/- 0.2 mm. 1.6 mm is ordered.
3. **Stock.** Re-run `tools/audit/sourcing.py` on the order day.
4. **The preview.** In JLCPCB's placement preview, check:
   - pin 1 of the RP2354B, the '541 (TSSOP-20), the '08 / '14, the LVC1G17 (SOT-353), the
     regulators, the CP2102N, USB-C and the microSD;
   - the polarity of the diodes and the WS2812B.

## Bring-up

1. **Power, no console.**
   - USB-C only: +5V is 4.3-4.9 V at TP2, +3V3 at TP1, +3V3_RP at TP11, DVDD 1.1 V at TP3.
   - CONS_5V (TP17) and PRE5V (TP16) stay at 0 V.
2. **In a 2-port or universal 4-port, USB unplugged.**
   - With the adapter in, TP18 (raw DC after the PTC) reads 9-13 V and PRE5V 5.0 V.
   - The console path is off: CONS_5V carries only the console's own 5 V.
   - Cut JP2 and the cart runs from CONS_5V instead.
3. **In an original 4-port (CA018087), USB unplugged.** Measure CONS_5V at TP17 during WiFi TX.
   If VR1 sags, run WiFi on USB power, or cap the S3's TX power in firmware.
4. **Bus.** Scope /EN40, /EN80 (TP8 / TP9), /OE1 / /OE2 (TP10 / TP13), PWR_OK (TP14) and D0.
   Check:
   - the '541 opens only inside an enable;
   - D0 settles well before the end of the cycle (`timing_margins.py`: +234 ns budget).
5. **PHI2 (2-port).** At TP15 the pin sits at ~1 V low and ~4.8 V high. PHI2_RP (GPIO25) is a
   clean 0 / 5 V square.
6. **Power-on race.** Measure the RP's cold boot to a serving core1 against the 5200 BIOS's first
   cart read (scope BUF_EN against /EN80 at power-on). USB-C power before the console avoids the
   race.

## Flashing

- **The S3:** over USB-C (CP2102N, esptool auto-program).
- **The RP:**
  - by the S3 over PICOBOOT: IO4 -> 1k -> RUN, IO5 -> 1k -> QSPI_SS, low to assert;
  - by hand: hold BOOTSEL (SW2) and press RESET (SW1);
  - over SWD: TP4 SWCLK, TP5 SWDIO, TP6 GND, TP7 RUN.
- **The RP's debug UART:** J4 (DNP, 3-pin 2.54 mm, 3.3 V).

## Firmware follow-ups (not changed here)

- **fn-5200-board `fujiversal-atari5200.h`:**
  - add `PIN_RP2040_RUN` = IO4 and `PIN_RP2040_BOOTSEL` = IO5, which this board wires;
  - set `PIN_CARD_DETECT` to IO42 (the microSD card-detect, 10k pull-up).
- **`a52_cart.h`:** `VSENSE_PIN`'s comment says "12 V-safe divider". Pin 26 is 5 V and the
  divider is 0.5 x. Nothing reads the ADC yet. It could watch VR1 sag during WiFi.
- **`main.c`:** nothing initialises GPIO44/45 (J4).
- **S3:** cap the TX power when the cart runs from VR1 alone (an original 4-port without USB).

## Regenerating

You need KiCad 10.0.6, Python 3 with numpy, a C compiler (for `check_glue.py`), ngspice and
poppler for the audits, and Java with Freerouting 2.4.1 for the board.

```sh
tools/build_all.sh                 # footprints, sheets, ERC, check_nets / check_glue / edge, BOM, PDF, fab packages
LAYOUT=1 tools/build_all.sh        # ... and place, route (tools/route_board.sh) and DRC the board
tools/audit/run_sch_audit.sh       # kicad-happy schematic audit, SPICE, margins, timing, deep review
tools/audit/run_pcb_audit.sh       # kicad-happy PCB, cross, EMC, thermal, gerbers, release gate
```

`check_*.py` read two external sources:

- `$FUJINET_FIRMWARE/pico/atari-5200` (default `~/Workspace/fujinet-firmware`, branch
  `add-5200`);
- the S3 pin map from `$FUJINET_A52_BOARD/include/pinmap/fujiversal-atari5200.h` (default
  `~/Workspace/fn-5200-board`).

Never edit the KiCad files; edit these instead:

| File | What it holds |
|---|---|
| `tools/design.py` | the circuit |
| `tools/sch_layout.py` | the drawing |
| `tools/placement.py` | the floorplan |
| `tools/edge_geom.py` | the edge |

References are geographic and frozen in `tools/refs.lock`. Net names are frozen in
`tools/nets.lock`.

## Provenance and license

**CERN-OHL-W-2.0.**

- **This repository:** the RP2354B core, the FujiNet sheets, the power OR and the generators come
  from FujiNet-SMS Rev0 / FujiNet-7800 Rev0 in this repository, which descend from NES Rev0,
  Astrocade Rev0, INTV Rev0 and the PiNTY CARD.
- **Raspberry Pi:** the AOTA inductor footprint is from Raspberry Pi's RP2350 minimal design (MIT,
  `tools/RPI-MINIMAL-LICENSE.txt`).
- **Edge facts:** Atari CX5200 Field Service Manual; Pixels Past rev B gerbers; tdididit a52
  library; sanni cartreader.
- **Glue and pin map:** `fujinet-firmware` `pico/atari-5200` `a52_cart.h`.
- **Symbols:** official KiCad libraries (CC-BY-SA 4.0 with exception), except the project's own
  (the 5200 edge, the RP2354B and ESP32-S3 functional units, the USB-C 16P, the TF-015 microSD).

## Files

| Path | Contents |
|---|---|
| `FujiNet-5200-Rev0.kicad_pro/.kicad_sch/.kicad_pcb` | KiCad 10 project: root + `cart-bus`, `rp-core`, `fujinet`, `usb`, `power`; the routed board |
| `FujiNet-5200.kicad_sym`, `FujiNet-5200.pretty/`, `3d/` | project symbols, footprints, 3D models |
| `FujiNet-5200-Rev0-BOM.csv` | grouped BOM (MPN, manufacturer, LCSC; DNP flagged) |
| `exports/jlcpcb/`, `exports/pcbway/` | the fab packages |
| `docs/` | schematic PDF, layout SVGs, renders, tab overlay, design review, floorplan study, sourcing |
| `case/board-anchors.scad` | the board's outline and openings, for a shell |
| `tools/` | generators, routing pipeline, checks, audits |
