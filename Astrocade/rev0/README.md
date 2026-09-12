# FujiNet-Astrocade Rev0

All-in-one **Bally Astrocade FujiNet cartridge** — one board carrying both halves
of the Astrocade FujiNet stack:

- **RP2040** (QFN-56 + W25Q16 flash) running the `fujicade` firmware from
  `fujinet-firmware/pico/astrocade` (protocol verified end-to-end in MAME
  against a live fujinet-pc; see that tree's README). It serves the 8K cart
  window and the FujiNet mailbox over the edge.
- **ESP32-S3-WROOM-1-N16R8** running the `fujiversal-astrocade` build of
  fujinet-firmware. The two MCUs link **on-board over native USB** — the S3 is
  the USB *host* (GPIO19/20), the RP2040 a CDC-ACM *device* (VID 0xCafe).
- A **single USB-C port** replicates the ESP32-S3-DevKitC-1 "UART" port
  (CP2102N + UMH3N auto-program) to flash the S3; the RP2040 is flashed
  *through* the S3 (PICOBOOT doorbell, hardware forcing on S3 GPIO4/GPIO5).
- **microSD** on the S3 (GPIO38/39/40/41), **WS2812B** status LED (GPIO48),
  top-face **RESET** button (pulls RP2040 RUN + S3 EN via BAT54C).

Direct adaptation of `INTV/FujiNet-INTV-Rev0` in this repository (same
S3/USB/power/SD sections); the cart-bus side is new for the Astrocade.

## The port (why this cart is simple)

The Astrocade edge carries **A0–A12, D0–D7, one pre-decoded active-low
Enable (/CCS), +5V and 3× GND — nothing else** (no /RD, /WR, clock, or
reset). The console only ever *reads* the cart. Three 74LVC245A handle the
5V bus against the non-5V-tolerant RP2040:

- **U8, U9** (B→A, always enabled): A0–A12 + /CCS down to 3V3 → RP GPIO0–13.
- **U7** (A→B, **/OE = /CCS**): RP GPIO14–21 drive D0–D7 onto the bus *only
  while the console selects the cart* — tri-state discipline in hardware.
- RN2/RN3 (100k) keep U7's inputs defined while the RP2040 boots Hi-Z.

Firmware pin map is exactly `astrocade_cart.h` (GP0–12 = A0–12, GP13 =
/ENABLE, GP14–21 = D0–7, GP22 self-test TP, GP25 LED, **GP26 = console-5V
sense** via 100k/100k from the raw edge +5V, GP27 debug-TX TP).

## The cartridge is a cassette, not a finger cart

A Videocade is a closed cassette-style box lying label-up in an **open-top
well**; the console's 26-contact **blade** (1×26, 0.100" pitch, ~74 mm wide,
~3.6–3.8 mm thick, reaching ~17 mm in) enters a slot in the leading face and
presses **up** against gold lands on the **PCB underside**. Full sourced
dossier + shell mapping: **`case/case-spec.md`**; parametric two-piece shell:
`case/FujiNet-Astrocade-Shell.scad`. Key consequences on the PCB:

- 26 contact lands (1.7 × 14 mm, hard gold, **B.Cu only**) along the south
  edge, row centered, **land 1 east** in top view (= left when viewed
  insertion-away, per Tilton). No bevel, no fingers on top.
- A **rule area on B.Cu over the blade strip** (south 16.5 mm): no tracks,
  vias, or pours where the blade wipes.
- Top face stays exposed in the console → RESET (SW1), BOOTSEL (SW2) and the
  WS2812 light pipe act through the shell roof; USB-C + microSD exit the
  trailing edge, above the well rim (shell body is taller than an original
  cart — the well is open-topped).

## Board facts

| | |
|---|---|
| Outline | 96 × 58 mm, 1.6 mm; fits the ~102 × 65 mm shell with 4× M3 posts |
| Edge | 26 lands @ 2.54 mm on the bottom face, span 63.5 mm centers, centered |
| ESP32 antenna | module overhangs the trailing (north) edge ~6.4 mm; shell has an antenna window |
| Power | cart +5V (land 25) ⊕ USB VBUS → SS34 OR → 470 µF → AP63203 3.3 V/2 A buck |
| 5V sense | raw edge +5V → 100k/100k → GP26 (tells console power from USB bench power) |
| Stackup (suggested) | F.Cu / In1.Cu (GND) / In2.Cu (3V3 + 5V islands) / B.Cu, as INTV Rev0 |

## Status — Rev0: schematic + placed board, **unrouted**

- ERC: **0 errors / 0 warnings** (severity-all).
- DRC (`--schematic-parity`, severity-all): **0 electrical errors, 0 parity
  issues**; remaining items are the expected *unconnected* (unrouted) markers
  and silkscreen-text overlap warnings to tidy while routing.
- **`python3 tools/check_nets.py` → 151/151**: every edge land, every level
  shifter channel, both firmware pin maps, USB link, forcing/reset chains,
  QSPI, sense divider — machine-checked against the netlist. Run it after
  any schematic edit.
- **Routing is the next step** (interactive, KiCad ≥ 10): fan the land row
  up into U7/U8/U9, keep USB_DP/USB_DM (U1↔U2) and UBRG pair short and
  coupled (`USB_DIFF` net class, 90 Ω target), then pour GND. Copper-to-edge
  clearance is 0 in the board file (the land row needs it); keep normal
  clearances elsewhere. Min through-hole set to 0.2 mm for the ESP32 module
  thermal vias — confirm with the fab or convert to 0.3 mm.

## Flashing

- **ESP32-S3**: USB-C port (CP2102N auto-program), `pio run -t upload` with
  `upload_port` = the CP2102N's `/dev/ttyUSB*`.
- **RP2040**: through the S3 — mailbox BOOTSEL doorbell, or hardware forcing
  (S3 GPIO5 → Q3 pulls QSPI_SS low, S3 GPIO4 → Q2 pulses RUN). Manual
  fallback SW2 (BOOTSEL) + SW1 (RESET); note BOOTSEL enumerates to the *S3*,
  not a PC. Last resort: SWD pads TP1/TP2/TP3 on the back.
- Firmware side: `fujiversal-astrocade.h` does not yet define
  `PIN_RP2040_RUN`/`PIN_RP2040_BOOTSEL` (GPIO4/GPIO5, as `fujiversal-intv.h`
  does) — add them when enabling PICOBOOT for this target. The `fujicade`
  board file also still targets a stock Pico; give the PCB a sibling board
  header when bring-up starts.

## Bring-up checklist (cannot be verified in CAD)

1. **Caliper pass** (before ordering shells; PCB is safe to order first):
   every VERIFY item in `case/case-spec.md` — cart envelope, slot geometry,
   land-row height above the slot floor, well rim height.
2. Enable polarity/timing on a real console with a scope: whether /CCS
   pulses during Z80 refresh or magic writes (the protocol tolerates all
   outcomes; the bus loop's one-event-per-assertion discipline should be
   confirmed).
3. Console 5V rail headroom under WiFi-burst load (~400 mA peak on 3V3)
   before trusting cart-only power; USB-C can co-power on the bench.
4. VSENSE threshold on GP26 with console vs USB power.
5. Blade contact wipe/force with the shell's clamp ribs fitted (adjust
   `pcb_seat_z`).
6. Test hardware BOOTSEL forcing (S3 GPIO5 low + GPIO4 pulse) before
   trusting PICOBOOT reflash; Q3 pulls the flash CS against the RP2040's
   pad driver — verified-working on INTV's identical circuit, but confirm.
7. WiFi RSSI with the shell on (antenna window vs. full window cut).
8. WS2812B runs from the diode-OR'd rail (~4.7 V): 3.3 V data is marginal
   at higher VDD — verify, or fit a series diode drop if flickery.

## Provenance & license

- Circuit blocks (ESP32-S3 + SD + WS2812, CP2102N USB-UART + auto-program,
  AP63203 power): adapted from `FujiNet-INTV-Rev0` in this repo, itself an
  adaptation of the PiNTY CARD (Yannick Erb / gtortone, **CERN-OHL-W-2.0**)
  and the public ESP32-S3-DevKitC-1 v1.1 reference. This design is likewise
  **CERN-OHL-W-2.0**.
- Edge pinout: Jay Tilton (1998 Usenet, via ballyalley.com
  `bally_technical_info_(cartridge_port).htm`), cross-checked against MCM
  Design's "Modified Cassette Cartridge with 28-Pin ZIF Socket" (Dec 2020,
  ballyalley.com) — the two agree contact-for-contact.
- Connector/physical: sakman55's Bally Astrocade cartreader adapter
  (github.com/sanni/cartreader discussion #354): 1×26 @ 0.100", 74 mm blade,
  thickness recipe; adapter gerbers used as the in-photo dimensional ruler.
- Symbols/footprints: official KiCad libraries (CC-BY-SA 4.0 + exception);
  microSD footprint from `Coco/CoCo-FujiNet-Rev0000`; RP2040 support circuit
  per the Raspberry Pi hardware design guide / Pico reference design.

## Files

- `FujiNet-Astrocade-Rev0.kicad_pro / .kicad_sch / *.kicad_sch / .kicad_pcb`
  — KiCad 10 project (root + 4 sheets: cart-rp2040, esp32s3-sd, usb-uart,
  power); self-contained project libraries (`FujiNet-Astrocade.kicad_sym`,
  `FujiNet-Astrocade.pretty/`), no external library dependencies.
- `FujiNet-Astrocade-Rev0-BOM.csv` — grouped BOM (complete generic passives'
  MPNs at order time).
- `tools/check_nets.py` — the 151-check netlist↔firmware validator.
- `case/` — dimension dossier (`case-spec.md`) + parametric shell
  (`FujiNet-Astrocade-Shell.scad`).
- `docs/` — schematic PDF, layout SVGs, 3D renders.
