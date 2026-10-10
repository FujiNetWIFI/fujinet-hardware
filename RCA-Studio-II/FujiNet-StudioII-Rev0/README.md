# FujiNet-StudioII Rev0

FujiNet for the RCA Studio II: an RP2354B cartridge that serves the CDP1802 bus in software. The
ESP32-S3 (the FujiNet, `fujiversal-studio2`) is a separate board with its own supply, joined to this
one by USB alone.

**Status: schematic only.** No layout, no board. The schematic implements
`fujinet-firmware/pico/studio2/firmware/include/s2_cart.h` as it stands; the firmware runs on it
unchanged. The edge geometry is PROVISIONAL (see below).

| Check (2026-10-10) | Result |
|---|---|
| Drawing checks (`gen_sch.py`) | every sheet wired; 2 crossings on `cart-bus` (see Glue), 0 on `rp-core` and `power` |
| Netlist parity, kicad-cli netlist vs `design.py`, names included | 71 / 71 nets |
| KiCad ERC, all severities | 0 errors, 0 warnings |
| `tools/check_nets.py`: netlist vs `s2_cart.h`, the edge map, series R, pull-ups, senses, PWR_OK gating, power path, RP support, edge footprint | 292 checks, 0 failed |
| `tools/check_glue.py`: the '541 enables and CART CS vs `s2_glue_drive()` / `s2_glue_cartcs()` (three inputs each), compiled | 16 / 16 joint input combinations, 0 mismatches (8 / 8 per equation); RP unpowered 4 / 4 and console off 8 / 8 silent |
| Mutation run on copies of `s2_cart.h`: PWR_OK dropped from either equation, `DRIVE_PIN` moved, `PWROK_PIN` / `LED_PIN` swapped, the old two-argument glue | each fails |
| JLCPCB stock, every assembled line | 29 / 29 in stock |

## Sheets

| Page | Sheet | Contents |
|---|---|---|
| 1 | root | block diagram, notes; USB_DP / USB_DM wired between `rp-core` and `power` |
| 2 | `cart-bus` | 22-pin edge, 330R into GPIO0-9, 74HCT541, CART CS NOR, the PWR_OK-gating ORs, /DRIVE and /CLAIM pull-ups, PWR_OK, ADC sense, LED, debug UART, scope pads |
| 3 | `rp-core` | RP2354B supplies and decoupling, core regulator, crystal, SWD, RUN / RESET, BOOTSEL |
| 4 | `power` | console 5 V P-FET OR USB VBUS, AP2112K LDO, USB-C receptacle to the S3 board |

Each bus line is one straight wire from the edge to the RP: the edge symbol, the '541 and the RP's
GPIO unit are built on the same rows.

## Edge connector

| Pin | Signal | Net | Pin | Signal | Net |
|---|---|---|---|---|---|
| 1-5 | D7-D3 | '541 Y | 12-14 | MA1-MA3 | 330R -> GPIO1-3 |
| 6 | ROM DISABLE | GND (removes the built-in games, as a cart does) | 15 | +5 V (console 7805) | CONS_5V |
| 7 | GND | GND | 16-18 | MA4-MA6 | 330R -> GPIO4-6 |
| 8-10 | D2-D0 | '541 Y | 19 | TPA (gated by /MRD in the console) | 330R -> GPIO8 |
| 11 | MA0 | 330R -> GPIO0 | 20 | MA7 | 330R -> GPIO7 |
| | | | 21 | /MRD | '541 /OE1, NOR, 330R -> GPIO9 |
| | | | 22 | CART CS (cart output, high = console RAM off) | NOR output |

The pinout is the bring-up plan's (EJK's Studio II schematic, Paul Robson's notes, the FliP
multicart). There is no write strobe, clock or reset on the edge.

**PROVISIONAL** (`tools/edge_geom.py`, `FujiNet-StudioII.pretty/StudioII_Cart_Edge_22.kicad_mod`):

- **Pitch.** 3.96 mm (0.156") per the plan. MAME's notes give the console's CN1 as "0.154"
  spacing" (3.91 mm): over 21 pitches that is 1.05 mm at the ends. Measure a cartridge.
- **One face.** CN1 is a 2x22 connector; the lettered row is taken as unconnected, so the 22
  contacts are on F.Cu only. If that row is a duplicate of the numbered one, contacts on both faces
  are harmless; if it carries anything else, this changes.
- **Pin 1 end, finger size and depth, tab width and depth, board thickness.** Pin 1 at the left
  seen from the contact face, fingers 2.5 mm wide, copper 0.6-8.5 mm in, tab 88.9 x 12 mm,
  1.6 mm. None of these is measured.

## RP2354B pin map

Exactly `s2_cart.h`. `check_nets.py` reads every `*_PIN` and fails if the header names a pin this
board does not wire, or the board wires one the header does not name.

| GPIO | Net | Goes to |
|---|---|---|
| 0-7 | RP_MA0-7 | 330R -> edge MA0-MA7 |
| 8 | RP_TPA | 330R -> edge 19 |
| 9 | RP_MRD | 330R -> edge 21 |
| 16-23 | RP_D0-7 | 74HCT541 A0-A7 (outputs only) |
| 24 | DRIVE_N | 74HCT32 -> '541 /OE2; R11 10k to +5V |
| 25 | CLAIM_N | 74HCT32 -> NOR; R12 10k to +5V |
| 26 | PWR_OK | 74HCT14, two stages from the console 5 V; the first stage (PWR_OK_N) gates the ORs |
| 27 | RP_LED | 1k, red LED |
| 40 | VSENSE_ADC | ADC0: edge 15 through 100k / 100k (0.5 x), 100 nF |
| 44, 45 | DBG_TX, DBG_RX | J2 (DNP), 3.3 V only |

- The console's lines reach the RP through 330R: it limits the current into a 5 V-tolerant pad
  while IOVDD is still rising, and costs under 2 ns.
- GPIO40-47 are not 5 V tolerant. `check_nets.py` asserts only passives and the debug header reach
  them.
- No bus pin has a pull; the firmware turns the pad pulls off (RP2350-E9).

## Glue

```
'541 drives D0-D7  = !/MRD & !/DRIVE & PWR_OK                    (s2_glue_drive)
                     /OE1 = /MRD          /OE2 = /DRIVE | PWR_OK_N     74HCT32
CART CS            = NOR(/MRD, /CLAIM) & PWR_OK                  (s2_glue_cartcs)
                   = NOR(/MRD, /CLAIM | PWR_OK_N)                    74HCT32 + 74HCT1G02
```

- /MRD alone ends a read in hardware, for both outputs. It is the '541's /OE1 with no gate between
  them, and one gate from CART CS.
- **The console's power gates both outputs.** With the console off, PWR_OK_N (the first '14
  stage) is high, so nothing is driven into it: not D0-D7, not CART CS. This holds whatever the RP,
  running from USB, has left on /DRIVE and /CLAIM. The gates run on +5V, the cart's own OR-ed
  rail, so they work with the console off.
- No 74HCT27 (triple 3-input NOR) is stocked at JLCPCB, so the 3-input NOR is a '32 OR into the
  '1G02. The '32's other gate makes /OE2.
- The '541, '32 and NOR run on +5V, so D0-D7 and CART CS are 5 V CMOS levels (the 1802's VIH is
  3.5 V at 5 V). Their TTL inputs take the RP's 3.3 V.
- R11 / R12 hold /DRIVE and /CLAIM high, the cart silent, while the RP is unpowered or booting.
  10k beats the RP2350's reset pull-down. `check_glue.py` checks this and the console-off case.
- `cart-bus` has two crossings, both forced:
  - the /MRD riser crosses /OE2, because /OE1 = /MRD sits between the '541's A pins and /OE2;
  - PWR_OK_N crosses the /MRD line once, because it reaches one OR above that line and one below.

## Power

- **Q1, AO3401A: console 5 V -> +5V.** D = CONS_5V (edge 15), S = +5V, G = VBUS, as on
  FujiNet-NES Rev0. Fully on with no USB. Off with VBUS present, leaving only its body diode, which
  never feeds the console.
- **D5, SS34: VBUS -> +5V.** With the S3 board connected, the cart takes nothing from the
  console's 7805. R27 4.7k holds VBUS (Q1's gate) low with no cable and against the SS34's leakage.
- **+5V feeds** the '541, '32, '1G02, '14 and U6 (AP2112K -> +3V3, every RP2354B supply pin). The
  LDO rises with +5V, so the 5 V-tolerant pads are never unpowered with 5 V on them.
- **Load** ~50 mA at 200 MHz. Nothing else is on this board.
- **USB-C** is a UFP (5.1k Rd on CC1 / CC2) with ESD diodes on D+, D- and VBUS. The S3 board is the
  host and supplies VBUS.

## Parts

Every part is JLCPCB-assemblable. The stock below is from JLCPCB's parts library on 2026-10-10;
`FujiNet-StudioII-Rev0-BOM.csv` has every line with MPN, manufacturer and LCSC.

| Part | LCSC | Stock | Note |
|---|---|---|---|
| RP2354B | C39843328 | 3812 | extended |
| SN74HCT541PWR | C436096 | 25567 | extended |
| 74HCT1G02GV,125 (Nexperia, SOT-753) | C12504 | 2952 | extended. Fallback: SN74AHCT1G02DBVR, C163710, 2279, same SOT-23-5 land (A / B swapped, which a NOR does not care about) |
| SN74HCT14DR | C6769 | 36312 | extended |
| SN74HCT32DR | C6781 | 3062 | extended. Alternate: 74HCT32D,653, C5985, 3282, same SOIC-14 |
| AP2112K-3.3TRG1 | C51118 | 29975 | extended |
| AO3401A, SS34 | C15127, C8678 | 682k, 4.2M | basic |
| ABM8-272-T3 12 MHz | C20625731 | 9481 | extended |
| **AOTA-B201610S3R3-101-T** 3.3 uH | C42411119 | **109** | the RP2350 core inductor Raspberry Pi qualifies; low stock. If it runs out, consign it, or try a shielded 2016 3.3 uH such as TDK VLS201610HBX-3R3M-1 (C695624, 502) on the same land, unqualified |
| TYPE-C-31-M-12, ESD5Z5.0T1G | C165948, C82044 | 409k, 374k | extended |

Re-check stock on the order day.

## Before layout

1. Measure a Studio II cartridge: pitch (0.154" or 0.156"), contact face, pin 1 end, finger size,
   tab outline, thickness.
2. Layout note, not a pin move: around the RP2354B's package GPIO0-9 run MA0-MA7, TPA, /MRD, the
   edge's own order except that the edge puts TPA between MA6 and MA7 (one crossing). D0-D7 arrive
   reversed, which the '541 absorbs by taking its channels in reverse, as on the 5200 board.
3. No board files yet. Every footprint except the edge is a copy of FujiNet-5200 Rev0's; the 3D
   models come with the layout.

## Firmware follow-ups (not changed here)

- Nothing initialises GPIO44 / 45 (J2), and nothing reads VSENSE (GPIO40). VSENSE could watch the
  console's 7805.
- `s2_cart.h` says `DRIVE_PIN` is "the '541's /OE2". It now reaches /OE2 through the 74HCT32, gated
  by PWR_OK_N.

## Bring-up

1. **USB only, no console.** +5V 4.6-4.7 V at TP15, +3V3 at TP16, DVDD 1.1 V at TP12. CONS_5V (TP13)
   and PWR_OK (TP6) stay at 0 V.
2. **In the console, no USB.** CONS_5V at TP13 and +5V at TP15 within ~30 mV of each other. Check the
   console's 7805 with the extra ~50 mA.
3. **Bus.** Scope /MRD (TP1), TPA (TP2), CART CS (TP3), /DRIVE (TP4), /CLAIM (TP5) and D0:
   - the gated-TPA width and the low-byte settle time (`S2_LO_DELAY_NS`);
   - CART CS against the console RAM's release before the '541 drives;
   - whether non-memory execute cycles assert /MRD.
4. **Power-on race.** The BIOS reaches `$0400` about 50 ms after power-on: scope /DRIVE against the
   first TPA with the cart on the console alone.
5. **Power-off on USB.** Switch the console off with the S3 board connected. As PWR_OK (TP6) falls,
   /OE2 ('541 pin 19) must go high and CART CS (TP3) low, and D0 must float.

Flashing: hold BOOTSEL (SW2), press RESET (SW1), copy the UF2 over USB-C; or SWD on TP8 SWCLK, TP9
SWDIO, TP10 GND, TP11 RUN. The S3 board has no wires to RUN or BOOTSEL: it can only ask running
firmware for BOOTSEL over USB, so a hung cart needs the buttons, which the shell must leave reachable.

## Regenerating

You need KiCad 10, Python 3 and a C compiler (`check_glue.py` compiles the firmware's glue).

```sh
tools/build_all.sh
```

It runs, in order:

1. `harvest_symbols.py`, `make_edge_fp.py`, `make_fp_extra.py`;
2. `gen_sch.py`: drawing checks, hierarchy, netlist parity with `design.py`;
3. KiCad ERC at all severities;
4. `check_nets.py`, then `check_glue.py`;
5. `export.py`: BOM, JLCPCB BOM, `docs/FujiNet-StudioII-Rev0-schematic.pdf`.

`check_*.py` read `$FUJINET_FIRMWARE/pico/studio2` (default `~/Workspace/fujinet-firmware`).
`check_nets.py` also reads the S3 board's pin map from
`$FUJINET_S2_BOARD/include/pinmap/fujiversal-studio2.h` (default `~/Workspace/fn-studio2-board`) when
present, to confirm the cart is joined by USB alone.

Never edit the KiCad files. Edit `tools/design.py` (the circuit), `tools/sch_layout.py` (the
drawing) or `tools/edge_geom.py` (the edge).

## Provenance and license

**CERN-OHL-W-2.0.**

- **This repository:** the RP2354B core, the '541 data path, the PWR_OK and ADC senses and the
  generators come from FujiNet-5200 Rev0 (`ATARI-5200/FujiNet-5200-Rev0`, not yet on master); the
  console-side P-FET OR from FujiNet-NES Rev0.
- **Edge and bus facts:** the bring-up plan's sources (EJK's schematic, Paul Robson, the FliP
  multicart), MAME `rca/studio2.cpp`, the CDP1802A datasheet.
- **Glue and pin map:** `fujinet-firmware` `pico/studio2` `s2_cart.h`.
- **Symbols:** official KiCad libraries (CC-BY-SA 4.0 with exception); the 74HCT1G02 uses the
  74LVC1G02 symbol and the 74HCT14 the 74HC14's (same pinouts). Project symbols: the edge, the
  RP2354B in two units, the USB-C 16P by function.

## Files

| Path | Contents |
|---|---|
| `FujiNet-StudioII-Rev0.kicad_pro/.kicad_sch` | KiCad 10 project: root + `cart-bus`, `rp-core`, `power` |
| `FujiNet-StudioII.kicad_sym`, `FujiNet-StudioII.pretty/` | project symbols and footprints |
| `FujiNet-StudioII-Rev0-BOM.csv` | grouped BOM (MPN, manufacturer, LCSC; DNP flagged) |
| `exports/jlcpcb/BOM-JLCPCB.csv` | JLCPCB assembly BOM |
| `docs/FujiNet-StudioII-Rev0-schematic.pdf` | the schematic |
| `tools/` | generators and checks |
