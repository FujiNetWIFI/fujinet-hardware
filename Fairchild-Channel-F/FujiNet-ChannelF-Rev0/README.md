# FujiNet-ChannelF Rev0

FujiNet for the Fairchild Channel F: an RP2040 Videocart that serves the F8 bus, plus an ESP32-S3
(the FujiNet, the RP2040's USB host), on one cartridge.

**Status: schematic only.** No board has been laid out yet. The schematic implements the firmware
in `fujinet-firmware/pico/channelf/` exactly as it stands. The RP2040 firmware (`fujichannelf`)
runs unchanged.

| Sheet | Contents |
|---|---|
| root | Block diagram. Every connection between sheets is a drawn wire. |
| `cart-rp` (A2) | 22-contact edge → 2× SN74LVC4245A → RP2040 (one symbol), plus the RP2040's own circuit: supplies, 2 MB QSPI flash, 12 MHz crystal, SWD, RUN / BOOTSEL / RESET, USB to the S3 |
| `fujinet` | ESP32-S3-WROOM-1-N16R8, microSD, WS2812B status LED, S3 EN / BOOT buttons |
| `usb` | USB-C, CP2102N bridge and esptool auto-program pair (UMH3N) for flashing the S3 |
| `power` | Console 5 V and USB VBUS diode-ORed into +5V; AP63203 buck to +3V3 (S3 side); AP2112K LDO to +3V3_RP (RP side) |

Every sheet is fully wired: each net is one drawn piece, and labels only name wires or leave the
sheet. On `cart-rp` each bus line is a straight wire from the edge, through its translator, into
the RP2040, with no crossings.

## Firmware contract

Checked against the firmware by `tools/check_nets.py`, which does not read `design.py`:

| Signal | Edge pin | RP2040 | Source |
|---|---|---|---|
| D0-D7 | 3, 4, 9, 11, 14, 16, 17, 18 | GPIO0-7, through U2 | `channelf_cart.h` `D0_PIN` |
| ROMC0-4 | 6, 7, 8, 10, 12 | GPIO8-12, through U3 | `ROMC0_PIN` |
| WRITE / PHI | 15 / 13 | GPIO13 / GPIO14, through U3 | `WRITE_PIN`, `PHI_PIN` |
| DIR | n/a | GPIO15 → U2 DIR (1 = console → cart, 0 = cart drives) | `DIR_PIN`, `channelf_cart.c` |
| /INTREQ | 5 | GPIO16 → 2N7002 open drain (never driven) | `INTREQ_PIN` |
| LED | n/a | GPIO25 | stock `boards/pico.h` |
| +5V / GND / NC / +12V | 19-20 / 1-2 / 21 / 22 | +12V and NC left open | |

The edge pinout comes from the [channelf.se veswiki Pinouts](https://channelf.se/veswiki/index.php?title=Pinouts) page.

S3 pins follow `include/pinmap/fujiversal-channelf.h` on the `fujiversal-channelf-board` branch:
- microSD: IO38-41, card detect on IO42
- WS2812: IO48
- UART0: 43 / 44
- USB host to the RP: IO19 / IO20

RP2040 RUN and BOOTSEL are driven from S3 IO4 and IO5, the same pins as on the Astrocade board.
**That pinmap does not declare `PIN_RP2040_RUN` / `PIN_RP2040_BOOTSEL` yet.** `check_nets.py`
reports this as a warning.

## Why two SN74LVC4245A

- **The F3850's data bus needs VIH 2.9 V minimum** (F3850 datasheet, Table 7). A 3.3 V driver has
  almost no margin, whether it is a bare RP pin or a 74LVC245A at 3.3 V. The RP2040 is also not
  5 V tolerant (VPIN max = IOVDD + 0.5 V).
- **The '4245A's A port runs at 5 V with TTL inputs** (VIH 2.0 V). The console's outputs give
  3.9 V on DB/ROMC and 4.4 V on WRITE/PHI, and the A port drives 5 V levels back onto the bus.
- **DIR high = A → B.** With A on the console side, that is the firmware's own polarity: no
  inverter, no firmware change.
- **DIR and /OE are TTL inputs referenced to VCCA**, so the RP's 3.3 V drives them correctly.
- **R1, 4.7k to +3V3_RP, holds U2's DIR high** through RP reset and boot. Without it, the
  RP2040's 50-80 kΩ pad pull-down would read 0, and the cart would drive the bus while the BIOS
  runs.
- **VCCA is CONS_5V, taken straight off edge pins 19/20, ahead of the OR diode.** With the console
  off, VCCA drops below 100 mV and both translators go high-Z (TI SCAS375K §7.5, plus Ioff). A
  USB-powered cart therefore cannot back-power the console through the bus. The firmware's DIR = 1
  idle is the second line of defence.
- U3 is console → RP only: DIR is tied to VCCA and /OE to GND. Its spare A8 is held low through
  R2, 10k (SCAS375K 5.4 note 1), and B8 is left open.

## Build

```
tools/build_all.sh
```

It runs, in order:
1. `harvest_symbols.py`
2. `gen_sch.py`: drawing checks, hierarchy, netlist parity with `design.py`
3. KiCad ERC at all severities
4. `check_nets.py`
5. `export.py`: BOM, JLCPCB BOM, `docs/FujiNet-ChannelF-Rev0-schematic.pdf`

Edit `tools/design.py` (the circuit) and `tools/sch_layout.py` (the drawing), never the
`.kicad_sch` files.

`check_nets.py` reads the firmware from `$FUJINET_FIRMWARE` (default `~/Workspace/fujinet-firmware`)
and the pico-sdk from `$PICO_SDK_PATH` (default `/usr/share/pico-sdk`).

## Verification, 2026-10-09

| Check | Result |
|---|---|
| Drawing checks | Every sheet wired; 0 crossings on `cart-rp`, `fujinet` and `power`; 1 on `usb` (the auto-program pair, as on the Astrocade) |
| Netlist parity (kicad-cli netlist vs `design.py`) | 87 / 87 nets |
| KiCad ERC, all severities | 0 violations |
| `check_nets.py` | 204 checks, 0 failed, 1 warning (the RUN / BOOTSEL pinmap). A mutation run with DIR polarity, DIR pin and WRITE pin altered in a copy of the firmware failed as expected. |
| kicad-happy `analyze_schematic.py` | 0 errors. Two warnings, both triaged as false positives in `.kicad-happy.json`: CP2102N CHREN is an unused charger output; VBUS_SNS is a divider tap, not a rail. |

Pinouts were checked against the datasheet PDFs, not against KiCad symbols:
- RP2040 pin table
- SN74LVC4245A Table 4-1 and function table
- W25Q16JV §3.3 (SOIC-8 208 mil)
- JSCJ 2N7002 (G / S / D = 1 / 2 / 3)

Datasheets are in `datasheets/` (PDFs are git-ignored; `manifest.json` lists them). It also holds
`F3850.pdf` (the console CPU) and the Raspberry Pi *Hardware design with RP2040* guide.

Sourcing: every BOM line was in stock at JLCPCB on 2026-10-09, including SN74LVC4245APWR C7859
(119k), RP2040 C2040 (61k) and W25Q16JVSSIQ C82317 (1.9k).

## Open items

**Before layout:**
1. **Videocart edge geometry.** J1 has no footprint on purpose. Measure a real Videocart first:
   which faces carry contacts, the pitch, where pin 1 is, and the tab outline.
2. **PCB:** not started. The footprints for every other part are in `FujiNet-ChannelF.pretty`.

**Firmware, not changed by this work:**
3. Add `PIN_RP2040_RUN GPIO_NUM_4` and `PIN_RP2040_BOOTSEL GPIO_NUM_5` to `fujiversal-channelf.h`,
   and drop its PROVISIONAL note.
4. The "'245" comments in `channelf_cart.h` should say SN74LVC4245A.

**Bring-up:**
5. Scope the WRITE edge and write-data timing (PROVISIONAL in `channelf_cart.c`) on TP2 (WRITE),
   TP3 (PHI) and TP1 (DIR). TP4 (GPIO17) is a spare for a firmware scope trigger.
6. Console +5V headroom with Wi-Fi bursts (~400-500 mA) is unmeasured. If the console rail sags,
   run the cart from USB-C.
7. Older SN74LVC4245A dies may predate the Ioff / VCC-isolation spec (datasheet revision K). If so,
   the firmware's DIR = 1 idle still keeps U2 from driving the bus.
8. Getting back to CONFIG after booting a Videocart: press RESET (SW2, which resets the RP and the
   S3), then the console's reset. The cart edge has no reset line.
