# FujiNet-Astrocade Rev0

All-in-one **Bally Astrocade FujiNet cartridge**: one board in an Astrocade
cassette shell carrying both halves of the Astrocade FujiNet stack, built
the same way as `INTV/FujiNet-INTV-Rev0`.

- **RP2354A** (RP2350A die + 2 MB flash in the package, QFN-60) runs the
  `fujicade` cart firmware from `fujinet-firmware/pico/astrocade`, board
  **`fujicade_rp2354`**. It serves the 8K cart window and the FujiNet
  mailbox straight off the 5 V bus through its 5 V-tolerant pads, with **no
  level shifters**, as on the INTV cart.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-astrocade`** build of
  fujinet-firmware. The two chips link **on the board over native USB**: the
  S3 is the USB *host* (IO19/IO20) and the RP a CDC device (VID 0xCafe).
  The S3 embeds the RP image and re-flashes it over PICOBOOT whenever it
  changes (`build_pico.py`, the same mechanism as fujiversal-intv).
- **USB-C** carries power plus a CP2102N UART with UMH3N auto-program
  (ESP32-S3-DevKitC-1 style) for flashing the S3.
- **microSD** (push-push, SPI on S3 IO38-41, card-detect on IO42).
- **WS2812B-2020-V6** status LED under a light pipe. It is the 3.3 V-rated
  part, so the data line needs no level shifting.
- **Buttons:**
  - top-face **RESET** (resets RP and S3)
  - **BOOTSEL** pinhole
  - S3 **EN/BOOT** (board-level)

The board is **fully autorouted** on a 6-layer stack. Everything is generated from
`tools/design.py` and `tools/placement.py` (see *Regenerating* below).

## Edge port

The cassette edge carries **A0-A12, D0-D7, one pre-decoded active-low
Enable (/CCS), +5V and 3x GND**. There is no /RD, /WR, clock or reset, and
the console only ever *reads* the cart. The RP pin map is exactly
`astrocade_cart.h`:

| RP2354A | Net | Edge (Tilton 1-26) |
|---|---|---|
| GP0-GP12 | CA0-CA12 | A0 9, A1 8, A2 7, A3 6, A4 5, A5 4, A6 3, A7 2, A8 24, A9 23, A10 20, A11 19, A12 22 |
| GP13 | CCS_N (10k pull-up to 3V3) | 21 |
| GP14-GP21 | CD0-CD7 | D0 10, D1 11, D2 12, D3 14, D4 15, D5 16, D6 17, D7 18 |
| GP26 | VSENSE: edge +5V through 100k/150k (3.0 V) | 25 |
| GP22 / GP27 | SELFTEST / DBG_TX test pads | - |
| GP25 | green activity LED | - |

**The unbuffered bus is safe because the firmware gates it.** The PCB has no
'245 with /OE on /CCS any more, so tri-state discipline lives in the core1
loop. That loop serves a read only while `(pins & SERVE_MASK) == SERVE_WANT`:
/CCS low **and** VSENSE high (`FUJICADE_VSENSE_PIN`).

Without the VSENSE gate, a cart running on USB power in an **unpowered**
console would see /CCS pulled low by the console's input clamps. It would
then drive D0-D7 into the dead console. The loop also lets go if the console
loses power mid-cycle. The bus pads' pull-downs are disabled
(`FUJICADE_BUS_NO_PULLS`, RP2350-E9).

The S3 pins follow `include/pinmap/fujiversal-astrocade.h`:

| S3 | Function |
|---|---|
| IO38/39/40/41 | SD MOSI / SCK / MISO / CS |
| IO42 | SD card-detect (10k pull-up; firmware leaves it NC until the polarity is confirmed) |
| IO48 | WS2812 |
| IO4 / IO5 | `PIN_RP2040_RUN` / `PIN_RP2040_BOOTSEL`, 1k each to RP RUN / QSPI_SS |
| IO19 / IO20 | USB D- / D+ to the RP (27R series) |
| TXD0 / RXD0 | CP2102N |

**Why RUN/BOOTSEL are direct 1k links rather than transistors.**
`fnPicoUpdater::forceBootselViaPins()` drives these pins **low** to assert
and leaves them as inputs when idle. An NPN driver, as on the INTV Rev0
board, inverts that: the firmware's low turns the transistor *off*, so the
hardware recovery path could never fire. Both chips share the 3.3 V rail, so
a series resistor is the whole interface.

## Mechanics: a cassette, not a finger cart

A Videocade is a closed cassette-style box lying label-up in an **open-top
well**. The console's 26-contact **blade** (0.100" pitch, about 74 mm wide
and 3.6-3.8 mm thick, reaching about 17-18 mm in) enters a slot in the
leading face. It presses **up** against gold lands on the **PCB underside**.

The sourced dossier is `case/case-spec.md`, and the parametric shell is
`case/FujiNet-Astrocade-Shell.scad`. Its openings come from
`case/board-anchors.scad`, which is generated from the placement.

**Board:**

| | |
|---|---|
| Outline | 96 x 58 x 1.6 mm (x 52..148, y 30..88), 4x M3 NPTH for the shell posts |
| Contact lands | 26 x (1.7 x 14 mm) on **B.Cu only**, 2.54 mm pitch, 63.5 mm span, centred; land 1 is **east** in top view |
| Blade strip | B.Cu rule area over the south 16.5 mm (y >= 71.5): no tracks, vias or pour where the blade wipes |
| Land escapes | Each land's footprint carries a 0.5 mm neck under solder mask to a 0.3/0.6 mm plated hole **17.4 mm** in from the edge (y = 70.6), beyond the blade's reach. Pads are allowed in the rule area; tracks and vias are not. |
| Stackup | **6 layers, 1.6 mm:** F.Cu signals + GND pour / In1.Cu **GND plane** / In2.Cu + In3.Cu signals / In4.Cu **+3V3 plane** (with a DVDD island under the RP2354A) / B.Cu signals + GND pour (outside the blade strip) |
| Trailing edge (y=30) | USB-C, microSD slot, and the ESP32-S3 antenna overhanging about 6.4 mm (shell antenna window) |
| Top face | SW1 RESET, SW2 BOOTSEL pinhole, D3 WS2812 light pipe |

## Power

- **Sources:** console +5V (land 25) and USB VBUS, each through an SS34
  (diode OR, so there is no back-feed between them) into VIN.
- **Regulation:** VIN goes to an AP63203 3.3 V/2 A buck (6.8 uH, 3x22 uF in,
  2x22 uF out).
- **RP2354A core:** uses its own SMPS (3.3 uH AOTA-B201610S3R3 to DVDD).
  VREG_AVDD is filtered with 33 R + 4.7 uF, and each IOVDD/DVDD pin has its
  own 100 nF.

## Flashing

- **ESP32-S3:** plug in the USB-C port (CP2102N, esptool auto-program) and run
  `pio run -e fujiversal-astrocade -t upload`. The build also compiles the
  RP firmware (`pico_src = pico/astrocade/firmware`,
  `pico_board = fujicade_rp2354`) and embeds it.
- **RP2354A:** flashed by the S3 at boot, over PICOBOOT.
  - It first tries the cooperative mailbox BOOTSEL doorbell.
  - Otherwise it uses hardware forcing: IO5 holds QSPI_SS low across an IO4
    pulse on RUN.
  - The image is capped below the flash store at 0x180000
    (`pico_flash_limit`).
- **Manual fallback:** hold SW2 (BOOTSEL) and press SW1 (RESET). In BOOTSEL
  the RP enumerates to the **S3**, not a PC.
- **Last resort:** SWD pads TP1 (SWCLK), TP2 (SWDIO), TP3 (GND).

## Regenerating

KiCad 10.0.6, Python 3, Java 21+, and Freerouting 2.4.1 at
`~/.local/share/freerouting/freerouting-2.4.1.jar` from
github.com/freerouting/freerouting/releases.

`tools/build_all.sh` runs the whole chain (about 35 minutes):

```sh
python3 tools/gen_sch.py      # design.py -> root + 4 sheets, project symbol lib
python3 tools/gen_pcb.py      # placement + RPi regulator graft + nets (from the schematic netlist)
                              # + locked plane fan-out; rules/net classes/.kicad_dru; case anchors
python3 tools/finish_route.py --nets=VBUS,XIN,XOUT,XOUT_Y,DVDD --lock   # RP core nets first, locked
python3 tools/route.py        # DSN -> Freerouting (headless) -> SES -> GND pours -> zone fill
python3 tools/finish_route.py # two-layer A* (+ transactional rip-up) for anything left; drops dangling stubs
python3 tools/check_nets.py   # netlist vs fujinet-firmware headers (independent of design.py)
python3 tools/export.py       # BOM, JLCPCB BOM + CPL, gerbers/drill zip, schematic PDF, SVGs, renders
```

**Helper scripts:**

| Script | Purpose |
|---|---|
| `tools/lcsc.py` | Checks LCSC codes; `--search` queries JLCPCB's parts search |
| `tools/make_tf015_fp.py` | Rebuilds the microSD footprint from the EasyEDA export of C113206 |
| `tools/make_edge_fp.py` | Writes the land footprint |
| `tools/harvest_symbols.py` | Refreshes `tools/symcache.sexpr` |
| `tools/rpi_graft.py` | Re-extracts the Raspberry Pi regulator corner from the unzipped `Minimal-KiCAD.zip` |

**The RP2350 regulator corner is copied from Raspberry Pi.** Pins 46-50
(VREG_AVDD, PGND, LX, VREG_VIN, FB) sit side by side at 0.4 mm pitch next
to USB_DM/DP. The board uses Raspberry Pi's own layout for that corner, from
the RP2350A minimal design (MIT, `tools/RPI-MINIMAL-LICENSE.txt`):

- the QFN-60 footprint with its thermal vias
- the AOTA inductor, the 0402 VREG_VIN/DVDD caps, the AVDD RC and the USB
  27 R resistors, at Raspberry Pi's positions relative to the chip
- the small LX, 1V1 and GND pours and their tracks

`tools/rpi_graft.py` extracts all of this into `tools/rpi_core_graft.sexpr`.
A `.kicad_dru` rule allows Raspberry Pi's 0.12 mm clearance on the
DVDD/RP_LX/VREG_AVDD nets only.

**How the routing works.** `gen_pcb.py` places a locked stub and via on
every GND/+3V3 SMD pad, because Freerouting handles plane fan-out poorly.
It keeps a 1.2 mm via-free lane in front of every fine-pitch signal pin so
those vias can't wall off the RP2354A's escapes. Freerouting then routes the
signal nets. `finish_route.py` rasterises the clearances (0.05 mm grid) and
closes anything left.

**Why the board is written as text.** `pcbnew`'s SWIG bindings misbehave
under Python 3.14: several member accessors return raw SwigPyObjects. So the
board is written as S-expressions, and `pcbnew` is used only for DSN/SES and
zone filling.

## Status

Rev0, generated 2026-09-27: schematic, 6-layer layout, **100% routed**, fab
outputs exported. The board has not been built or tested on hardware.

| Check | Result |
|---|---|
| ERC (`--severity-all`) | 0 violations |
| DRC (`--schematic-parity`) | 0 errors, 0 unconnected, 0 parity. 62 warnings, all silkscreen cosmetics: silk over copper/pads is clipped by the mask in the gerbers, and the ESP32/microSD silk runs off the trailing edge where those parts overhang |
| `tools/check_nets.py` | 174 of 174 checks pass. It reads the firmware headers directly: the edge lands to GP0-21 map, VSENSE, the USB link, the S3 pins and the RUN/BOOTSEL links |
| Firmware | `fujicade_rp2354` builds in pico-sdk. `build_pico.py fujiversal-astrocade` embeds the RP image in the S3 build. The Astrocade host tests (fujibus, astromap, bankserve, fujimail, fujistore) pass |
| Shell | Both halves render in OpenSCAD with the generated anchors. The top half's non-manifold warning predates this revision |

**Fab (JLCPCB):**

- **Board:** 6-layer, 1.6 mm, ENIG or hard gold for the contact lands, no
  edge bevel.
- **Limits used:** 0.15 mm track minimum (0.10 allowed), 0.12 mm clearance
  only in the RP2350 regulator corner, and 0.25 mm minimum drill (the DVDD
  vias under the RP).
- **Vias in pads:** the thermal vias in the QFN exposed pads are via-in-pad.
  Order epoxy-filled and capped vias (JLC includes this on 6-layer boards) so
  solder doesn't wick away.
- **Upload files:** `exports/jlcpcb/`: `FujiNet-Astrocade-Rev0-gerbers.zip`,
  `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. Every placed part has an LCSC code;
  the 26 contact lands and test pads are not assembled.

## Bring-up checklist (not verifiable in CAD)

1. **Caliper pass** on a real Videocade and console: every VERIFY item in
   `case/case-spec.md`. That includes the blade reach against the escape
   holes 17.4 mm in; they need at least about 1 mm margin past the blade tip.
2. **Power-up ordering:** the RP2350's 5 V tolerance holds only while IOVDD is
   up. The cart is powered by the console, so the buck brings 3V3 up within
   about a millisecond of +5V. Scope a console cold start (CA*/CCS_N vs +3V3)
   before trusting it. The same assumption applies to INTV Rev0.
3. **VSENSE gate:** the cart must stay silent on USB power with the console
   off, and serve with it on.
4. **Enable polarity and timing** on a real console with a scope: /CCS during
   Z80 refresh and magic writes.
5. **Console 5 V headroom** under WiFi bursts (about 400 mA peak on 3V3).
6. **Hardware BOOTSEL forcing** (IO5 low across an IO4 pulse) before trusting
   the PICOBOOT reflash.
7. **microSD card-detect polarity** on IO42, then set `PIN_CARD_DETECT`.
8. **JLC CPL rotations:** check the placement preview. The table is in
   `tools/export.py`.
9. **WiFi RSSI** in the shell. The antenna overhangs the trailing edge, and
   the microSD shell is about 2 mm from it.
10. **TL3342 RESET actuator** height against the roof (printed plunger, see
    `case/case-spec.md`).

## Provenance and license

**CERN-OHL-W-2.0.**

- **Circuit blocks:** adapted from `FujiNet-INTV-Rev0` in this repository,
  itself an adaptation of the PiNTY CARD (CERN-OHL-W-2.0). The
  ESP32-S3-DevKitC-1 v1.1 reference design is the other source.
- **Edge pinout:** Jay Tilton (ballyalley.com
  `bally_technical_info_(cartridge_port).htm`), cross-checked against MCM
  Design's modified cassette cartridge drawing.
- **Blade and physical data:** sakman55's Astrocade cartreader adapter
  (github.com/sanni/cartreader discussion #354).
- **RP2350 regulator corner:** Raspberry Pi RP2350A minimal design
  (`RPI-RP2350A-MINIMAL_R4-S1`, MIT, Copyright Raspberry Pi Ltd; license in
  `tools/RPI-MINIMAL-LICENSE.txt`). That covers placement, footprints and
  copper around pins 46-54.
- **Symbols and footprints:** official KiCad libraries (CC-BY-SA 4.0 with
  exception). The TF-015 footprint is from LCSC/EasyEDA C113206 via
  easyeda2kicad. The land footprint is original.

## Files

| Path | Contents |
|---|---|
| `FujiNet-Astrocade-Rev0.kicad_pro/.kicad_sch/.kicad_pcb` | KiCad 10 project: root sheet plus `cart-rp2354a`, `esp32s3-sd`, `usb-uart`, `power`. It uses only the project libraries `FujiNet-Astrocade.kicad_sym` and `FujiNet-Astrocade.pretty/`, plus `3d/` |
| `FujiNet-Astrocade-Rev0-BOM.csv` | Grouped BOM with an MPN and LCSC code on every line |
| `exports/jlcpcb/` | `BOM-JLCPCB.csv`, `CPL-JLCPCB.csv`, `FujiNet-Astrocade-Rev0-gerbers.zip` |
| `exports/*.dsn/.ses`, `exports/freerouting.log` | The last autorouting run |
| `tools/` | Generators and checks (see *Regenerating*) |
| `case/` | Dimension dossier, parametric shell, generated anchors |
| `docs/` | Schematic PDF, layout SVGs, 3D renders |
