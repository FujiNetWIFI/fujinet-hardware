# FujiNet-INTV Rev0

All-in-one **Intellivision FujiNet cartridge**: one board carrying both halves of the
INTV FujiNet stack —

- **RP2354A** (RP2350A + 2 MB stacked flash, QFN-60) running the
  [Minty](https://github.com/gtortone/Minty)-derived cartridge firmware from
  `fujinet-firmware/pico/intellivision/firmware`, built with `-DPICO_BOARD=fujicard`.
  It emulates the cartridge on the CP-1610 bus (GPIO0–15 = AD0–AD15 wired **directly**
  to the 5 V cart edge — RP2350-family pads are 5 V-tolerant with IOVDD = 3.3 V) and
  exposes the FujiNet mailbox at `$9C00-$9F3F`.
- **ESP32-S3-WROOM-1-N16R8** running the `fujiversal-intv` build of
  [fujinet-firmware](https://github.com/FujiNetWIFI/fujinet-firmware)
  (`./build.sh -e fujiversal-intv`). The two MCUs are linked **on-board over native
  USB** — the S3 is the USB *host* (GPIO19/20) and the RP2354A is a CDC-ACM *device*
  (VID 0xCafe), exactly as the firmware expects. No UART link exists between them.

A **single USB-C port** replicates the ESP32-S3-DevKitC-1 v1.1 "UART" port:
CP2102N-A02-GQFN28 bridge into UART0 (GPIO43/44) with the classic DTR/RTS → EN/IO0
auto-program circuit (UMH3NTN dual transistor), so `pio run -t upload` just works.

## Provenance & license

This design **adapts the [PiNTY CARD](https://oshwlab.com/yannick.erb/intv-pirto-hb)**
by Yannick Erb (with gtortone), licensed **CERN-OHL-W-2.0**. The 44-pin edge-finger
geometry, the direct-connect CP-1610 bus interface, the RP2354A support circuit
(crystal, VREG inductor, USB series resistors) and the ECS-audio RC network follow the
PiNTY CARD design; the full bus/edge net map was verified by tracing the published
PiNTY gerbers. This derivative is likewise released under **CERN-OHL-W-2.0**.

Additional sources: standard package footprints from the official KiCad footprint
library (CC-BY-SA 4.0 with the KiCad libraries exception); microSD footprint reused
from `Coco/CoCo-FujiNet-Rev0000` in this repository; USB-UART port per the public
Espressif ESP32-S3-DevKitC-1 v1.1 reference schematic.

## Status — Rev0, schematic + placed board, **unrouted**

- ERC: 0 errors / 0 warnings. DRC (with `--schematic-parity`): 0 electrical errors;
  remaining items are the expected *unconnected* (unrouted) markers and a handful of
  silkscreen-text overlap warnings to tidy while routing.
- Every net was machine-checked against the firmware pin maps
  (`pico/intellivision/firmware/boards/fujicard.h` and
  `include/pinmap/fujiversal-intv.h`) and the PiNTY-verified edge map — 100/100 checks.
- **Routing is the next step** (interactive, in KiCad ≥ 10): suggested stackup
  F.Cu / In1.Cu (GND plane) / In2.Cu (3V3 + 5 V/VIN islands) / B.Cu, 1.6 mm.
  Route the AD0–15 fan-out from U1 straight down to the fingers, keep the
  USB_DP/USB_DM pair (U1 ↔ U2) short and coupled (90 Ω target, `USB_DIFF` net class),
  then pour GND on In1 and both outer layers.

## Board facts

| | |
|---|---|
| Outline | 58.2 × 78.0 mm, PiRTO-II-profile shell fit: bottom tongue with 45° chamfers, left shell notch, two Ø5.38 mm shell-post holes |
| Edge | 2×22 fingers, 2.54 mm pitch, 1.32 × 7.0 mm pads, copper held 0.9 mm off the edge (per PiNTY) |
| ESP32 antenna | module **overhangs the top edge by ~5.7 mm** so the RF keepout falls off-board (Espressif best practice) — the cart shell needs a matching relief |
| USB-C / microSD | both exit through the top edge |
| Power | cart +5 V (edge 43) ⊕ USB VBUS → SS34 OR → 470 µF → AP63203 3.3 V/2 A buck → both MCUs. Estimated draw ~80 mA avg / ~400 mA peak (WiFi bursts) |
| ECS audio | GPIO28 → R5 1k / C18 1 µF → edge pin 6, **DNP** (firmware `CONFIG_ECS_AUDIO=OFF`); fit R5/C18 to enable once firmware supports it |

## Flashing

- **ESP32-S3**: the USB-C port (CP2102N + auto-program). `upload_port` is the
  CP2102N's `/dev/ttyUSB*`.
- **RP2354A**: no dedicated port — it is flashed *through* the ESP32-S3 over the
  internal USB link: normal path is the mailbox BOOTSEL doorbell
  (`FUJI_MB_BOOTSEL_DOORBELL`, magic `0xB5` → `reset_usb_boot()`); recovery path is
  hardware forcing (S3 GPIO5 → Q3 pulls QSPI_SS low, S3 GPIO4 → Q2 pulses RUN).
  The S3-side PICOBOOT client currently lives on the `intv-combined-flash` branch of
  fujinet-firmware. Manual fallback: SW2 (BOOTSEL) + SW1 (RUN) — but note BOOTSEL
  enumerates to the *S3*, not to a PC. Last resort: SWD pads TP1/TP2/TP3 on the back.
- Note: the `fujicard` pico build target is not yet in
  `pico/intellivision/firmware/scripts/build-*.sh` / CI — build it directly with
  `cmake -B build -DPICO_BOARD=fujicard -DCMAKE_BUILD_TYPE=Release -DCONFIG_FUJINET=ON`.

## Fabrication notes

- 4-layer, 1.6 mm, ENIG (or selective **hard gold on the edge fingers**), **30–45°
  edge bevel** on the finger edge. Fingers intentionally stop 0.9 mm short of the
  edge so the bevel does not cut copper.
- Min through-hole on this board is 0.2 mm (ESP32 module thermal vias) — confirm with
  the fab or convert those to 0.3 mm.
- Copper-to-edge clearance is set to 0 in the board file (edge fingers demand it);
  keep normal clearances elsewhere when routing.
- BOM: `FujiNet-INTV-Rev0-BOM.csv` (MPN/LCSC filled where verified — complete the
  remaining generic passives at order time).

## Bring-up checklist (bench items that cannot be verified in CAD)

1. Measure console 5 V rail headroom under WiFi-burst load on each console variant
   before trusting cart-only power (USB-C can co-power on the bench).
2. Scope the 5 V-tolerance precondition: IOVDD (3.3 V) must be up before the console
   drives the bus — MSYNC gating covers normal operation; verify power-up ordering.
3. WS2812B-2020 runs from the diode-OR'd rail (~4.7 V): VDD spec is 3.5–5.3 V and the
   3.3 V data level is marginal at higher VDD — verify, or fit a small series diode
   drop if flickery.
4. WiFi RF check: USB-C and microSD metal bodies sit ~5 mm laterally from the antenna
   (which overhangs the board edge). Verify RSSI is acceptable in-shell; Rev1 could
   move the module if needed.
5. Shell fit: antenna + USB-C overhang need shell relief; verify the left notch and
   post holes against the actual PiRTO-II-style shell before ordering many boards.
6. Test hardware BOOTSEL forcing (drive GPIO5 low, pulse GPIO4) before trusting the
   PICOBOOT reflash path.

## Files

- `FujiNet-INTV-Rev0.kicad_pro / .kicad_sch / *.kicad_sch / .kicad_pcb` — KiCad 10
  project (root + 4 sheets: cart-rp2354a, esp32s3-sd, usb-uart, power)
- `FujiNet-INTV.kicad_sym`, `FujiNet-INTV.pretty/` — fully self-contained project
  libraries (no external library dependencies)
- `FujiNet-INTV-Rev0-BOM.csv` — grouped BOM with DNP column
- `docs/` — schematic PDF, layout SVGs, 3D renders

PCBs can be ordered by submitting gerbers exported from the routed board to the fab
house of your choice (routing pass required first).
