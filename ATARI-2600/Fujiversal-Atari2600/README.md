# Fujiversal-Atari2600 Rev0

All-in-one **Atari 2600 FujiNet cartridge**. It is the hardware for the Atari
2600 bring-up in fujinet-firmware (branch `2600-experiment`,
`pico/atari-2600/`). It uses the same two-chip architecture as INTV Rev0 and
Astrocade Rev0.

- **RP2040** + **W25Q16JV (2 MB)** runs the cart firmware built as board
  **`fujivcs`**. The pinout is exactly `include/vcs_pins.h`, so the firmware
  runs unchanged. The RP2040 is not 5 V tolerant, so every bus line goes
  through a **74LVC245A** powered at 3.3 V:
  - **U3** carries A0-A7 and **U4** carries A8-A12, both fixed A→B.
  - **U5** carries D0-D7. Its DIR pin is on GP26 and is pulled high.
- **ESP32-S3-WROOM-1-N16R8** runs the **`fujiversal-atari2600`** build of
  fujinet-firmware. It is the RP's USB *host*: S3 IO19/IO20 connect through
  27 R to the RP's USB, and the RP enumerates as a CDC device with VID
  0xCafe. There is no UART between the two chips.
- **USB-C** provides power and a CP2102N UART with UMH3N auto-program for
  flashing the S3.
- **microSD** is push-push, on SPI (IO38-41), with card-detect on IO42.
- **WS2812B-2020-V6** status LED (IO48), plus a green RP activity LED on GP25.
- **Buttons:**
  - **RESET** resets both chips. This is how you get back to the browser
    after booting a game (`main.c`: "an item for the PCB").
  - **BOOTSEL** for the RP2040.
  - S3 **EN** and S3 **BOOT**.
- The S3 can also force the RP into reset or BOOTSEL with IO4 → RUN and
  IO5 → QSPI_SS, active low through 1k, as on the INTV and Astrocade boards.

The board is a **4-layer**, **fully autorouted** design, with a printed
two-piece shell. Everything is generated from `tools/design.py` and
`tools/placement.py`: edit those, never the KiCad files (see *Regenerating*).

## Edge connector

2x12 gold fingers at 2.54 mm pitch, 1.5 x 7.0 mm, starting 0.5 mm from the
edge.

- **Tab:** 32.4 mm wide, with 45° shoulders reaching the full 54.4 mm width
  25.7 mm above the edge.
- **Geometry and orientation:** taken from the working FujiPlusCart prototype
  gerbers (`../FujiPlusCart-Prototype`). Its silkscreen reads "THIS SIDE TO
  CONSOLE REAR" on the component face.

| Face | Fingers, left → right (component face toward you) |
|---|---|
| **F.Cu** (components, console **rear**) | 13 D3, 14 D4, 15 D5, 16 D6, 17 D7, 18 A12, 19 A10, 20 A11, 21 A9, 22 A8, 23 +5V, 24 GND |
| **B.Cu** (label side, console **front**) | 12 GND, 11 D2, 10 D1, 9 D0, 8 A0, 7 A1, 6 A2, 5 A3, 4 A4, 3 A5, 2 A6, 1 A7 (pin 1 is behind pin 24) |

**Signals the edge does not carry:** R/W, clock, chip select (A12 is the only
decode) and reset.

**The RP pin map** (`vcs_pins.h`, checked by `tools/check_nets.py`):

| RP2040 | Net | Through |
|---|---|---|
| GP2-GP9 | RA0-RA7 | U3 (74LVC245A, DIR = H) ← CA0-CA7 |
| GP10-GP14 | RA8-RA12 | U4 (DIR = H; channels 5-7 unused, inputs grounded) ← CA8-CA12 |
| GP15-GP22 | RD0-RD7 | U5 ↔ CD0-CD7 |
| GP26 | BUF_DIR | U5 DIR, with a 10k pull-up |
| GP25 | RP_LED | green LED (`PICO_DEFAULT_LED_PIN`) |
| GP0 / GP1 | RP_TX / RP_RX | test pads TP4 / TP5 |
| SWCLK / SWDIO | | test pads TP1 / TP2, GND on TP3 |

**Why 74LVC245A and not the 74LVC8T245 named in the firmware.**

- **74LVC8T245:** its DIR pin is referenced to VCCA.
  - With the 5 V port as A, a 3.3 V GPIO can't reach VIH on DIR.
  - With the 3.3 V port as A, the polarity inverts relative to
    `DIR_PIN: 0 = cart drives the console`.
- **74LVC245A at 3.3 V:**
  - It tolerates 5 V on its inputs, and it has Ioff, so it is safe unpowered.
  - Its 3.3 V outputs clear the NMOS bus's TTL VIH (2.0 V), as PlusCart
    already relies on.
  - With A on the console, **DIR high = console → RP** (the boot value) and
    **DIR low = RP → console**.
  - Nothing on the board runs from the edge +5 V except the power diode, so
    the cart can't back-power a switched-off console through the bus.

> **Firmware item before bring-up:** nothing in the cart firmware drives
> DIR low yet. `main.c` sets GP26 = 1 at boot, and
> `DATA_DRIVE`/`DATA_RELEASE` in `vcs_pins.h` only toggle the RP's output
> enables. As written, the cart can't reach the console, and the RP would
> fight U5's B outputs whenever it drives.
>
> **Fix:** `DATA_DRIVE` must also clear `DIR_MASK`, and `DATA_RELEASE` must
> set it again (release the OEs first, then flip DIR). The '245 needs about
> 5-8 ns to turn around. This is noted in `README-fujinet.md` on the
> firmware side.

## Mechanics

**Board:** 54.4 x 88 mm, 1.6 mm thick. Every part sits on the component face,
above the shoulders; `gen_pcb.py` refuses a placement that breaks this.

**What goes into the console:** only the tab and shoulders, as with the
prototype.

**Finger strip:**
- It is a rule area on both faces: no tracks, vias or pour between the
  fingers.
- Each finger continues as a masked 0.5 mm neck to 10 mm from the edge,
  where the routers pick it up.
- The inner planes stop 9 mm from the edge, clear of the bevel.

**Top edge (y = 30):**
- USB-C and the microSD slot exit here.
- The ESP32-S3 antenna overhangs by 6.4 mm, into the shell's antenna pocket.

**Holes:** 4x M3 NPTH for the shell.

**Shell:** `case/`, see `case/case-spec.md`. It is a two-piece clamshell over
the full-width part of the board, 58 x 71 x 10 mm, with 4x M3 screws.

## Power

- **Sources:** console +5V (edge pin 23) and USB VBUS, each through an SS34
  (diode OR, so there is no back-feed between them) into VIN.
- **Regulation:** VIN feeds an AP63203 3.3 V/2 A buck (6.8 uH, 2x22 uF in,
  2x22 uF out).
- **RP2040 core:** 1.1 V from its internal LDO.
- **Decoupling:**
  - 100 nF on every IOVDD, USB_VDD, ADC_AVDD and DVDD pin
  - 1 uF on VREG_VIN and VREG_VOUT
  - 10 uF bulk each on 3V3 and at the edge +5V
- **Console budget:** the 2600 supplies +5V from its own 7805 fed by a 9 V
  adapter. At the 3.3 V rail this board should draw on the order of 60 mA
  idle and up to about 350 mA during WiFi TX bursts (estimated from the
  ESP32-S3 datasheet, not measured). Through the buck that is roughly
  250 mA peak from +5V.
  - The prototype (ESP32 DevKitC + Pico, all linear) ran on the same supply.
  - Still, measure the console's 5 V under WiFi load before trusting a
    2600 Jr (see the checklist).

## Flashing

- **ESP32-S3:** plug in the USB-C port (CP2102N, esptool auto-program) and run
  `pio run -e fujiversal-atari2600 -t upload`.
- **RP2040, first time:** the RP's USB goes only to the S3, so a PC can't
  see it as a UF2 drive. Use the SWD pads TP1 SWCLK, TP2 SWDIO and TP3 GND
  with a Raspberry Pi Debug Probe:
  `openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter speed 5000; program fujivcs.elf verify reset exit"`.
- **RP2040, afterwards:**
  - The mailbox BOOTSEL doorbell (`FN_REG_BOOTSEL_1/2`) puts the RP into
    BOOTSEL on the S3's USB.
  - So does holding **BOOTSEL** while pressing **RESET**.
  - So does IO5 held low across an IO4 pulse, which is `PIN_RP2040_BOOTSEL`
    / `PIN_RP2040_RUN`, as fnPicoUpdater expects.
  - A PICOBOOT client on the S3, as fujiversal-intv/-astrocade have, can
    then write the image. That client isn't on `2600-experiment` yet.

## Regenerating

**Requirements:**
- KiCad 10.0.6, Python 3, Java 21+
- Freerouting 2.4.1 at `~/.local/share/freerouting/freerouting-2.4.1.jar`
- the firmware tree at `~/Workspace/fn-2600` (or `$FUJINET_FIRMWARE`), for
  `check_nets.py`

`tools/build_all.sh` runs the whole chain (about 20 minutes):

```sh
python3 tools/make_edge_fp.py   # 2x12 finger footprint (both faces, masked necks)
python3 tools/gen_sch.py        # design.py -> root + 5 sheets, project symbol lib
python3 tools/gen_pcb.py        # placement + nets (from the schematic netlist) + locked plane fan-out,
                                # outline/tab, finger rule areas, planes, rules/net classes, case anchors,
                                # drawn DVDD ring / RP USB pair / GND-finger vias
python3 tools/finish_route.py --nets=DVDD,XIN,XOUT,XOUT_Y --lock   # core supply + crystal first, locked
python3 tools/route.py          # DSN -> Freerouting (headless) -> SES -> GND pours -> zone fill
python3 tools/finish_route.py   # grid A* (+ transactional rip-up) for anything left
python3 tools/tidy_tracks.py    # drop router crumbs, merge collinear runs, fix acute corners (DRC-checked)
python3 tools/set_models.py     # bundle-relative 3D models on every footprint
python3 tools/check_nets.py     # netlist vs the firmware headers (independent of design.py)
python3 tools/export.py         # BOM, JLCPCB BOM + CPL, gerbers/drill zip, schematic PDF, SVGs, renders
```

**Helper scripts:**

| Script | Purpose |
|---|---|
| `tools/lcsc.py` | Checks LCSC codes; `--search` queries JLCPCB's parts search |
| `tools/make_tf015_fp.py` | Rebuilds the microSD footprint from the EasyEDA export of C113206 |

**Toolchain origin:** the pipeline comes from `Astrocade/rev0`, without the
RP2350 regulator graft. That includes the S-expression board writer (pcbnew's
SWIG bindings are unreliable on Python 3.14), the locked plane fan-out with
1.2 mm escape lanes in front of fine-pitch pins, Freerouting, and the A*
finisher.

**How the bus is ordered.** The RP2040 is rotated 90°, so A0-A9 sit on its
south face directly above U3, and U3 sits directly above the B.Cu A0-A7
fingers, in the same order. The RP's other faces:
- **east:** A10-A12 (from U4, which sits south-east over the F.Cu A8-A12
  fingers), D0-D2 and the crystal
- **north:** D3-D7
- **west:** USB and QSPI, facing the S3 and the flash

U5 sits over the data fingers.

## Status

Rev0, generated 2026-09-27: schematic, 4-layer layout, **100% routed**,
fabrication outputs exported. **The board has not been built or tested on
hardware.**

| Check | Result |
|---|---|
| ERC (`--severity-all`) | 0 violations |
| DRC (`--schematic-parity`) | 0 errors, 0 unconnected, 0 parity. 81 warnings, all silkscreen cosmetics (reference text over copper or overlapping at 0603 density; silk over pads is clipped by the mask in the gerbers) |
| `tools/check_nets.py` | 355 of 355 checks pass. It reads `vcs_pins.h`, `fujivcs.cmake`/`fujivcs.h` and `fujiversal-atari2600.h` directly and traces every edge pin through its '245 to the right GPIO. It also checks DIR, /OE, the unused-input ties, the QSPI flash, the USB link, RUN/BOOTSEL, SD, LED and UART. A mutation test (D0_PIN 15 → 16, SD CS 41 → 42) fails 9 checks as it should |
| 3D | Every placed part has a bundled model (`docs/board-top.png`, `docs/board-bottom.png`) |
| Firmware | `pico/atari-2600/build-cart.sh` builds `fujivcs.uf2`, and `checksram` confirms core1 is SRAM-resident. `pio` env `fujiversal-atari2600` builds with the updated pinmap. The env needs a `data/webui/config/fujiversal-atari2600.yaml`, which is missing on `2600-experiment`; the build was verified with a temporary copy of the Astrocade one |
| Shell | Both halves render in OpenSCAD as 2-manifold (`Simple: yes`) |
| LCSC | Every code was checked with `tools/lcsc.py` against LCSC and JLC. All resolve to the part named, and all are in JLC stock |

**Routing notes.** Three spots were drawn as locked geometry in
`gen_pcb.py` rather than left to the routers, because a greedy router
always blocked one of the two lines:

- **DVDD** (`rp_dvdd_link`): VREG_VOUT pin 45 → DVDD pins 50 and 23, routed
  inside the RP2040's pin ring between the pads and the exposed pad, as
  Raspberry Pi's minimal design does.
- **The RP↔S3 USB pair** (`rp_usb_link`): pins 46/47 → R8/R7, down a
  via-free lane (`VIA_KEEP`).
- **The two GND fingers:** each is stitched to the In1 plane by a via 1.27 mm
  outboard of its neck. The fingers are back to back, so a via on the neck
  would short the finger behind it.

**Fab (JLCPCB):**

- **Board:** 4-layer, 1.6 mm, ENIG.
- **Gold fingers:** yes. **Bevel:** 30° on the insertion edge. Copper stops
  0.5 mm short of the edge, and the inner planes 9 mm short.
- **Limits used:** 0.15 mm clearance and track minimum, 0.3 mm minimum drill.
  This is standard 4-layer process.
- **Vias in pads:** the via arrays in the RP2040, CP2102N and ESP32-S3
  exposed pads are via-in-pad. Order "epoxy filled & capped" if it's
  offered at a sensible price; otherwise expect some solder wicking on the
  exposed pads (they are GND/thermal only).
- **Upload files:** `exports/jlcpcb/Fujiversal-Atari2600-Rev0-gerbers.zip`,
  `BOM-JLCPCB.csv` and `CPL-JLCPCB.csv`. 78 parts are assembled, all on the
  top side. The fingers, test pads and holes are not assembled.

## Bring-up checklist (not verifiable in CAD)

1. **DIR in firmware:** `DATA_DRIVE` must clear GP26 (see above). Until
   then, never insert the cart in a powered console with a firmware that
   drives.
2. **Fit in a real 2600** (heavy sixer, 4-switch, Jr, 7800): the fingers must
   seat, and the shell must clear the slot surround (`case/case-spec.md`).
3. **Console 5 V under WiFi bursts** at the edge pin, especially on a Jr.
4. **Timing on a scope:** address → data at the edge against the 6507's
   read window. Budget about 500 ns: the '245 adds about 3 ns each way plus
   the DIR turnaround.
5. **Back-power:** with USB-C power and the console off, the console must
   stay dead (DIR high, and the LVC245A's Ioff).
6. **RESET** must bring up the browser. **BOOTSEL + RESET** must enumerate
   the RP (VID 0x2E8A) on the S3.
7. **microSD card-detect polarity** on IO42, then set `PIN_CARD_DETECT`.
8. **JLC CPL rotations:** check the placement preview (pin-1 marks). The
   table is in `tools/export.py`.
9. **WiFi RSSI** inside the shell.

## Provenance and license

**CERN-OHL-W-2.0.**

- **Circuit blocks:** the ESP32-S3, USB-C/CP2102N/auto-program, microSD,
  WS2812 and buck blocks come from `Astrocade/rev0` and `INTV/FujiNet-INTV-Rev0`
  in this repository, which derive from the PiNTY CARD (CERN-OHL-W-2.0) and
  the ESP32-S3-DevKitC-1 reference design.
- **RP2040 support:** Raspberry Pi "Hardware design with RP2040" minimal
  design values (12 MHz ABM8 + 15 pF + 1k, W25Q16, decoupling).
- **Edge geometry and orientation:** the FujiPlusCart prototype in this
  repository.
- **Symbols and footprints:** official KiCad libraries (CC-BY-SA 4.0 with
  exception). The TF-015 footprint and models are from LCSC/EasyEDA via
  easyeda2kicad. The finger footprint is original.
- Nothing is taken from PlusCart-Pico or UnoCart hardware files.

## Files

| Path | Contents |
|---|---|
| `Fujiversal-Atari2600-Rev0.kicad_pro/.kicad_sch/.kicad_pcb/.kicad_dru` | KiCad 10 project: root sheet plus `cart-rp2040`, `bus-buffers`, `esp32s3-sd`, `usb-uart`, `power`. It uses only the project libraries `Fujiversal-Atari2600.kicad_sym` and `Fujiversal-Atari2600.pretty/`, plus `3d/` |
| `Fujiversal-Atari2600-Rev0-BOM.csv` | Grouped BOM with an MPN and LCSC code on every line |
| `exports/jlcpcb/` | `Fujiversal-Atari2600-Rev0-gerbers.zip`, `BOM-JLCPCB.csv`, `CPL-JLCPCB.csv` |
| `exports/freerouting.log` | Last autorouter run (the `.dsn`/`.ses` it leaves beside it are gitignored) |
| `docs/` | Schematic PDF, front/back layout SVGs, top/bottom 3D renders |
| `3d/` | STEP/WRL models for every placed part (sources in `3d/README.md`) |
| `case/` | OpenSCAD shell, generated anchors, `case-spec.md` |
| `tools/` | The generator pipeline |
