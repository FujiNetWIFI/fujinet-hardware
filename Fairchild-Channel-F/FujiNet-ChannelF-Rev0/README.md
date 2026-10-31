# FujiNet-ChannelF Rev0

FujiNet for the Fairchild Channel F: an RP2040 Videocart that serves the F8 bus, plus an ESP32-S3
(the FujiNet, the RP2040's USB host), on one cartridge.

**Status (2026-10-11): laid out, routed and packaged for JLCPCB. Not yet built.** The RP2040
firmware (`fujichannelf` in `fujinet-firmware/pico/channelf/`) runs unchanged. Read *Before
ordering* first.

| | |
|---|---|
| Board | 4 layers, 1.6 mm, 77 x 131.5 mm: the outline of aotta's PicoVideocart, which fits a real console and an original Videocart shell |
| Edge | 22 hard-gold fingers on the bottom face (B.Cu), 2.54 mm, key slot between pins 11 and 12 |
| Parts | 99 in the schematic: 86 placed by JLCPCB on the top face, 12 bare-copper test pads, and the edge itself |
| Fab package | `exports/jlcpcb/`: gerbers + drill, BOM, CPL with measured rotations, `ORDER-JLCPCB.md` |
| Shell | `case/board-anchors.scad`: everything a printed shell needs from the board |

See `docs/floorplan-study.md` for how the board was laid out, and `docs/design-review-rev0.md`
for the kicad-happy design review.

| Sheet | Contents |
|---|---|
| root | Block diagram. Every connection between sheets is a drawn wire. |
| `cart-rp` (A2) | 22-contact edge → 2x SN74LVC4245A → RP2040 (one symbol), plus the RP2040's own circuit: supplies, 2 MB QSPI flash, 12 MHz crystal, SWD, RUN / BOOTSEL / RESET, USB to the S3 |
| `fujinet` | ESP32-S3-WROOM-1-N16R8, microSD, WS2812B status LED, S3 EN / BOOT buttons |
| `usb` | USB-C, CP2102N bridge and esptool auto-program pair (UMH3N) for flashing the S3 |
| `power` | Console 5 V and USB VBUS diode-ORed into +5V; AP63203 buck to +3V3 (S3 side); AP2112K LDO to +3V3_RP (RP side) |

Every sheet is fully wired: each net is one drawn piece, and labels only name wires or leave the
sheet. Two sheets have one wire crossing each. On `cart-rp`, WRITE's scope pad drops past PHI's
line. On `usb`, it is the auto-program pair, as on the Astrocade. The control
translator's channels follow the board's order (see *The board*).

## Firmware contract

`tools/check_nets.py` checks this against the firmware itself; it does not read `design.py`.

| Signal | Edge pin | RP2040 | Source |
|---|---|---|---|
| D0-D7 | 3, 4, 9, 11, 14, 16, 17, 18 | GPIO0-7, through U8 | `channelf_cart.h` `D0_PIN` |
| ROMC0-4 | 6, 7, 8, 10, 12 | GPIO8-12, through U9 | `ROMC0_PIN` |
| WRITE / PHI | 15 / 13 | GPIO13 / GPIO14, through U9 | `WRITE_PIN`, `PHI_PIN` |
| DIR | n/a | GPIO15 → U8 DIR (1 = console → cart, 0 = cart drives) | `DIR_PIN`, `channelf_cart.c` |
| /INTREQ | 5 | GPIO16 → Q1 (2N7002) open drain (never driven) | `INTREQ_PIN` |
| LED | n/a | GPIO25 | stock `boards/pico.h` |
| +5V / GND / NC / +12V | 19-20 / 1-2 / 21 / 22 | +12V and NC left open | |

The edge pinout comes from Fairchild's FVE100 schematic (J5) and the
[channelf.se veswiki Pinouts](https://channelf.se/veswiki/index.php?title=Pinouts) page.

S3 pins follow `include/pinmap/fujiversal-channelf.h` on the `fujiversal-channelf-board` branch:

- microSD: IO38-41, card detect on IO42
- WS2812: IO48
- UART0: 43 / 44
- USB host to the RP: IO19 / IO20

RP2040 RUN and BOOTSEL are driven from S3 IO4 and IO5, the same pins as on the Astrocade board.
**That pinmap does not declare `PIN_RP2040_RUN` / `PIN_RP2040_BOOTSEL` yet**; `check_nets.py`
reports it as a warning.

## Why two SN74LVC4245A

- **The F3850's data bus needs VIH 2.9 V minimum** (F3850 data sheet, Table 7). A 3.3 V driver
  has almost no margin, whether a bare RP pin or a 74LVC245A at 3.3 V. The RP2040 is also not
  5 V tolerant (VPIN max = IOVDD + 0.5 V).
- **The '4245A's A port runs at 5 V with TTL inputs** (VIH 2.0 V).
  - The console's outputs give 3.9 V on DB / ROMC and 4.4 V on WRITE / PHI.
  - The A port drives at least 4.3 V back onto the bus at VCCA 4.5 V: 1.4 V above the F3850's
    2.9 V.
- **DIR high = A → B.** With A on the console side, that is the firmware's own polarity: no
  inverter, no firmware change.
- **DIR and /OE are TTL inputs referenced to VCCA**, so the RP's 3.3 V drives them correctly.
- **R18, 4.7k to +3V3_RP, holds U8's DIR high** through RP reset and boot. Without it, the
  RP2040's 50-80 kΩ pad pull-down would read 0, and the cart would drive the bus while the BIOS
  runs.
- **VCCA is CONS_5V, taken straight off edge pins 19 / 20, ahead of the OR diode.** With the
  console off, VCCA drops below 100 mV and both translators go high-Z (TI SCAS375K §7.5, plus
  Ioff). A USB-powered cart therefore cannot back-power the console through the bus. The
  firmware's DIR = 1 idle is the second line of defence.
- **U9 carries the control lines, console → RP only**: DIR is tied to VCCA and /OE to GND. Its
  channels run ROMC0-4, WRITE, PHI. Its spare A8 is held low through R20, 10k (SCAS375K 5.4
  note 1), and B8 is left open.

`tools/audit/margins.py` computes every one of these margins.

## The Videocart edge

All 22 contacts are on **one face, the one that is down in the console**: the console's spring
contacts push up from below.

- This board puts them on **B.Cu** and every part on F.Cu, which faces up (toward the label).
- Pitch 2.54 mm: pins 1-11, a 4-pitch gap holding the key slot, pins 12-22.
- Seen from the parts side with the edge toward you, pin 1 (GND) is on the left. Seen from the
  contact side, it is on the right.

| | |
|---|---|
| Fingers | 1.8 mm wide, copper 0.5-12.0 mm from the edge, hard gold, 30-45° bevel |
| Key slot | 1.651 x 12.58 mm, round top, 6.1 mm lead-in (aotta's, proven on a console) |
| Tab | 68.3 mm wide, straight for 30 mm: no parts on it |
| Body | 77 mm after a 45° taper; 131.5 mm overall; four 5.6 mm holes on the original shell's bosses |
| Pins 21 / 22 | Spare and +12 V: bare fingers, nothing within 1 mm |

Sources, transcribed and checked by `tools/audit/edge_orientation.py`:

- Andrea Ottaviani's aotta/PicoVideocart (GPL-3.0), its fab gerbers: the outline, the key slot,
  the shell holes, the thickness and the finger order. It works in a console. Its footprint
  numbers its pads in reverse.
- timtashpulatov/fart's `Cart_Conn` footprint.
- US 4,095,791.
- The veswiki photo of a real cart's contact face.

Numbers only: no file from these sources is in this repository. The board is CERN-OHL-W-2.0.

The original thickness, the console key's width and the console connector's reach are documented
nowhere. That is why the tab carries no parts, and why `docs/tab-overlay-1to1.pdf` exists.

## The board

`docs/floorplan-study.md` has the whole story. In short:

- **The bus.** The two translators stand side by side over the bus fingers, with U8 (data) on the
  west. The RP2040 sits straight north of them at rotation 90, its GP0-GP14 along its south side
  and up its east side. With U9's channels in the board's order, translator → RP crosses nothing.
- **The RP2040's ring** started from the routed `atari2600-rev0` board's and was then measured and
  improved:
  - VREG_VOUT, DVDD and VREG_VIN reach their capacitors on F.Cu with no via;
  - the USB 27R sit in line right off the pins;
  - XOUT and the bus-side IOVDD pins drop through vias in the ring's free band.
- **Power.**
  - The AP63203's input loop closes on F.Cu: its three input capacitors are stacked under VIN and
    GND.
  - The AP2112K stands on the In2 island boundary: input in +5V, output in +3V3_RP.
  - The console's 5 V enters on fingers 19 / 20 into a CONS_5V island under the translators.
- **The grip end** stays outside the console. The ESP32-S3's antenna sits flush with it, over a
  copper-free keep-out on every layer, beside the microSD and the USB-C. RESET (SW1) and both LEDs
  are just inside. The USB-C's shell face stands 0.45 mm past the edge (HRO's recommended PCB-edge
  position) and the microSD's face 0.5 mm inside it.
- **Connector alignment (2026-10-13).** The USB-C (J2) moved 1.8 mm to HRO's recommended PCB-edge
  position (its face had sat 1.35 mm inside the board, where a plug's overmold meets the PCB edge),
  and the microSD / USB-C 3D models were re-seated on their footprints; DRC still 0 / 0 / 0 (design
  review, "Post-layout change").
- **Stack-up** JLC04161H-7628: F.Cu signal / In1 GND / In2 power islands / B.Cu signal.

## Build

```
tools/build_all.sh              # schematic, ERC, firmware checks, re-link + DRC the routed board, exports, fab gates
LAYOUT=1 tools/build_all.sh     # ... and re-place, re-route the board from scratch (~25 min, Freerouting)
```

It runs, in order:

1. `harvest_symbols.py`, `make_edge_fp.py`, `make_fp_extra.py`, `audit/edge_orientation.py`
2. `gen_sch.py`: drawing checks, hierarchy, netlist parity with `design.py`
3. KiCad ERC at all severities
4. `check_nets.py`
5. One of:
   - with `LAYOUT=1`: `gen_pcb.py` (placement, planes, locked support copper, fan-out) and
     `route_board.sh` (Freerouting, the grid finisher, clean-up, stitching, DRC gate);
   - otherwise: `sync_pcb_sheets.py` and DRC with schematic parity.
6. `export.py`: BOMs, schematic PDF, the JLCPCB package, layout views
7. `tab_overlay.py` and `audit/check_fab.py` (which runs `audit/check_gerbers.py`)

The circuit lives in `tools/design.py`, the drawing in `tools/sch_layout.py`, the floorplan in
`tools/placement.py` and the edge in `tools/edge_geom.py`. Never edit the generated `.kicad_*`
files. `tools/refs.lock` freezes the geographic references and `tools/nets.lock` the net names.

`check_nets.py` reads the firmware from `$FUJINET_FIRMWARE` (default
`~/Workspace/fujinet-firmware`) and the pico-sdk from `$PICO_SDK_PATH` (default
`/usr/share/pico-sdk`).

The audits:

| Command | What it checks |
|---|---|
| `tools/audit/run_sch_audit.sh` | kicad-happy schematic analysis, SPICE |
| `tools/audit/run_pcb_audit.sh` | PCB, cross-domain, EMC, thermal, gerbers, release gate |
| `tools/audit/margins.py` | Circuit margins |
| `tools/audit/layout_checks.py` | The layout's datasheet claims, measured on the copper |
| `tools/audit/make_deep_review.py` + `deep_review_gate.py` | Per-IC datasheet review |
| `tools/audit/sourcing.py` | JLC / LCSC stock |
| `tools/audit/jlc/measure_rotations.py` | CPL rotations against the EasyEDA footprints |

## Verification

2026-10-11, the board built by `LAYOUT=1 tools/build_all.sh`:

| Check | Result |
|---|---|
| KiCad ERC, all severities | 0 |
| Netlist parity with `design.py` | 87 nets match |
| `tools/check_nets.py` (netlist vs the firmware) | 204 checks, 0 failed, 1 warning (the pin map lacks `PIN_RP2040_RUN` / `_BOOTSEL`: open item 1) |
| `tools/audit/edge_orientation.py` | every check against aotta, fart and the veswiki numbers |
| KiCad DRC, schematic parity, all severities | 0 violations, 0 unconnected, 0 parity issues |
| `tools/check_vias.py` | 756 vias, none in a foreign pad (758 before the connector alignment below) |
| `tools/audit/layout_checks.py` | 9 / 9: decoupling, the buck's loop, crystal, exposed-pad vias, USB skew, antenna keep-out |
| `tools/audit/margins.py` | all positive |
| `tools/audit/check_fab.py` + `check_gerbers.py` | 10 / 10; every gerber check |
| JLC CPL rotations | measured for all 35 (footprint, LCSC) pairs |
| `tools/audit/sourcing.py` | 38 / 38 lines in JLCPCB stock for 5 boards; 37 "normal" at LCSC |
| kicad-happy | SPICE 15 / 15; thermal 100; EMC 40 (no critical); deep review 24 / 24 verified; `fab_release_gate --strict` 10 pass, 2 waived |
| Pinouts | every part with more than two pins, and every polarized part, against its datasheet: no mismatch |

`docs/design-review-rev0.md` has the full review: the triage, the waivers and two open questions.

## Before ordering

1. **The edge.** Print `docs/tab-overlay-1to1.pdf` at 100 % (no fit-to-page) and check its 50 mm
   ruler. Lay a real Videocart board on it, contacts up, edge toward you. These must match:
   - the 22 contacts in two groups of 11;
   - the key slot;
   - the 68.3 mm tab;
   - the 5.6 mm holes on the bosses.
2. **Stock.** Re-run `python3 tools/audit/sourcing.py`. On 2026-10-11 every line was in stock for
   5 boards (`docs/sourcing.md`). The thinnest lines are the TL3342 buttons (1.5k) and the
   W25Q16 (1.5k).
3. **The order.** Follow `exports/jlcpcb/ORDER-JLCPCB.md`:
   - 4 layers, ENIG, hard-gold beveled fingers;
   - Standard PCBA, top side;
   - check the placement preview, especially the parts whose CPL rotation is only medium
     confidence (the TL3342 buttons, the BAT54C, the USB-C).

## Open items

**Circuit, for a decision** (`docs/design-review-rev0.md`, *Open questions*). Both are left as
drawn:

- the USB D+ / D- protection: 80 pF ESD5Z parts, where the CP2102N's datasheet shows a
  low-capacitance USB array;
- the CP2102N's RSTb pull-up: 10k, where the datasheet recommends 1k.

**Firmware, not changed by this work:**

1. Add `PIN_RP2040_RUN GPIO_NUM_4` and `PIN_RP2040_BOOTSEL GPIO_NUM_5` to
   `fujiversal-channelf.h`, and drop its PROVISIONAL note.
2. The "'245" comments in `channelf_cart.h` should say SN74LVC4245A.

**Bring-up:**

3. Scope the WRITE edge and the write-data timing (PROVISIONAL in `channelf_cart.c`):
   - TP10 (WRITE), TP11 (PHI) and TP12 (DIR);
   - TP2 (GP17) is a spare for a firmware scope trigger;
   - SWD is on TP6 (SWCLK), TP5 (SWDIO), TP7 (GND) and TP4 (RUN), for the first flash with a Debug
     Probe.
4. Console +5V headroom with Wi-Fi bursts (~400 mA peak) is unmeasured. Measure CONS_5V at the
   fingers. If the console rail sags, run the cart from USB-C.
5. Older SN74LVC4245A dies may predate the Ioff / VCC-isolation spec (datasheet revision K). If
   so, the firmware's DIR = 1 idle still keeps U8 from driving the bus.
6. Getting back to CONFIG after booting a Videocart: press RESET (SW1, which resets the RP and
   the S3), then the console's reset. The cart edge has no reset line.
7. **The shell.** `case/board-anchors.scad` has the outline, slot, bosses, buttons, LEDs, USB-C,
   microSD and antenna positions. The board's height inside the shell has to match the console's
   slot; that is unmeasured.
