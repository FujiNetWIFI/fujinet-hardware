# FujiNet-SMS Rev0 Design Review

**Project:** FujiNet-SMS-Rev0 (KiCad 10.0.6, a root and five region sheets, generated from `tools/design.py`)
**Dates:** 2026-10-06 (Part 1, the first audit); 2026-10-08 (Part 1b, the v2 schematic; Part 2, the v2 layout, which replaces the first layout's Part 2 -- that one is in git at `158d41f`)
**Analyzers (v2):** kicad-happy 2.2.1 run `2026-10-08_1256` (schematic, deep review 28/28 verified, 0 quarantined) and `2026-10-08_1256-3` (`analyze_pcb --full --proximity`, `cross_analysis`, `cross_verify`, `analyze_emc`, `analyze_thermal`, `simulate_subcircuits`, `analyze_gerbers` on the JLC zip, `fab_release_gate --strict`); KiCad 10.0.6 ERC and DRC at every severity; the project's own scripts in `tools/audit/`. Re-run: `tools/audit/run_sch_audit.sh`, `tools/audit/run_pcb_audit.sh`, `tools/audit/check_fab.py`.

**References.** v2 numbers parts by where they sit on the board (`tools/refs.lock`). Part 1 keeps the first audit's references; the ones it names map to v2 as follows:

| First audit | v2 | Part | | First audit | v2 | Part |
|---|---|---|---|---|---|---|
| U1 | U4 | RP2354B | | R11 | R25 | /WAIT gate pull-up |
| U2, U3 | U10, U7 | AS6C4008 (SRAM0, SRAM1) | | R12, R13 | R26, R27 | PWR_OK sense 22k / 100k |
| U4 | U12 | 74HCT14 | | R14 | R5 | S3 EN pull-up |
| U5, U6 | U9, U13 | 74HCT27 (/WE, decode) | | R19, R20 | R12, R13 | VBUS sense 22k / 47k |
| U7 | U8 | 74HCT10 | | R22 | R3 | VBUS pull-down (`R_VBPD`) |
| U8 | U11 | 74HCT00 | | C21, C22 | C42, C34 | SRAM 100 nF |
| U9 | U1 | ESP32-S3 | | C31 | C7 | S3 EN 1 uF |
| U10, U11 | U2, U3 | CP2102N, UMH3N | | C38 | C48 | CONS_5V 10 uF |
| U12, U13 | U5, U6 | AP63203 buck, AP2112K LDO | | D3 | D6 | WS2812 |
| Q1, Q2 | Q1, Q2 | 2N7002 /WAIT, AO3401A | | D7 | D1 | SS34 |
| RN1, RN2 | RN2, RN3 | D0-D7 100R | | D4-D6 | D3, D4, D2 | ESD5Z (D+, D-, VBUS) |
| J2, J4 | J4, J2 | debug header (DNP), USB-C | | TP1, TP2 | TP16, TP15 | /CONT, /BUSREQ pads |

# Part 1 — schematic audit

## Scope

All-in-one Sega Master System / SMS2 cartridge. An RP2354B (QFN-80, all 48 GPIOs) sits on the console's 5 V Z80 bus through its 5 V-tolerant pads and serves the mailbox, the loader and the bank lines. Two AS6C4008-55 (TSOP-I) SRAMs hold 1 MB on the 5 V rail. Five 74HCT packages (14, 27, 27, 10, 00) make SRAM /OE, /WE and PWR_OK. A 2N7002 holds console /WAIT. The FujiNet half is NES Rev0's circuit: ESP32-S3-WROOM-1-N16R8, CP2102N + UMH3N auto-program, USB-C, microSD, WS2812B-2020, AO3401A/SS34 power OR, AP63203 buck, AP2112K LDO.

Covered: every IC and transistor against its manufacturer PDF; the glue's pin-outs, logic levels and timing against the Z80; the power path, the console 5 V budget, power-on behaviour; the edge-connector signals left open; stock. Not covered here: layout and the edge-finger geometry (Part 2).

## Verification basis

| Item | Basis |
|---|---|
| Datasheets | `datasheets/` (46 PDFs, `manifest.json`), every file opened and checked to be the named part. Shared parts copied from NES Rev0 / 2600 Rev1; new parts fetched by LCSC code or from the manufacturer. Two fetches were wrong and replaced: LCSC C5984 served a 1990 Philips 74HC/HCT27 scan (now Nexperia rev.7), and **NES Rev0's `SN74HCT14DR.pdf` is TI's SNx4HC14 (an HC part)**, so it was replaced with TI SCLS225G. Also added: TI CD74HCT27/CD74HCT10 (alternates), `Z0840004.pdf` (OCR of Zilog PS0178 p.38-39, the console Z80's AC table), `SMS-CARTRIDGE-SLOT.pdf` (SMS Power! slot reference). |
| Component count | Analyzer 110 = `design.py` 110 (1 DNP: J2 debug header). |
| Connectivity | KiCad netlist (`kicad-cli`) compared pin by pin with the analyzer and with `design.py`. The analyzer splits 31 bus nets (see False positives); KiCad's netlist is correct. |
| Pin-outs | RP2354B: 48 GPIO pins and every supply pin parsed from the RP2350 datasheet table (p.1337-1339), 0 mismatches. AS6C4008 TSOP-I: 32/32 (p.2). 74HCT27/10 (Nexperia p.2), SN74HCT14 (TI p.3), SN74HCT00 (TI p.3, figure): every glue pin of the netlist, 0 mismatches. 2N7002 (CJ p.1: 1 G, 2 S, 3 D), 4D03 arrays (R_k between k and 9-k, p.4). |
| Shared circuits | ESP32-S3, CP2102N, UMH3N, AP63203, AP2112K, AO3401A, SS34, BAT54C, WS2812B, TF-015, USB-C, crystal, both inductors and every passive on the `esp32s3-sd`, `usb-uart` and `power` sheets are identical to NES Rev0 (part-by-part comparison of the two `design.py` files), so the NES Rev0 Part 1 pin verification applies; the SMS-specific uses were re-checked. |
| Computations | `tools/audit/margins.py`, `timing_margins.py` (static timing over the `design.py` gate network), `spice_checks.py` (ngspice decks). |

## Findings

| # | Severity | Finding | Evidence | Fix |
|---|---|---|---|---|
| 1 | WARNING | **SS34 reverse leakage lifts the P-FET gate.** Q2's gate is VBUS, pulled down only by the 22k/47k CP2102N divider (69k). With the console powering the cart the SS34 is reverse-biased by +5V and leaks into VBUS: 50 uA gives VGS -1.55 V (weak), >= 100 uA turns the FET off and the console feeds the cart through the body diode (~0.7 V drop). After USB is unplugged with the console on, the gate never gets back under 2.5 V at 50 uA. | SS34 IR 0.5 mA @25 C / 20 mA @100 C (p.2); AO3401A VGS(th) -0.5..-1.3 V (p.2); ngspice | **Applied in design.py:** R 4.7k VBUS-GND (0603WAF4701T5E, C23162): 500 uA -> VGS -2.80 V; unplug recovery 3.6 ms; costs 1.06 mA from USB. Same fix as 2600 Rev1 `R_VBPD`; NES Rev0 needs it too. |
| 2 | WARNING | **/WAIT hold before the firmware runs is not guaranteed.** GPIO34 resets with its pull-down on (RPD 36-113k); against the 10k pull-up the 2N7002 gate sits at 2.58-3.03 V, and the CJ 2N7002 VGS(th) is up to 2.5 V. At VTH 2.5 V / RPD 36k the FET does not pull /WAIT below 0.8 V (4.4-4.7 V with a 10k or 4.7k console pull-up). | RP2350 p.1337 (GPIO34 Pull-Down), p.1341 (RPD); 2N7002 p.2; ngspice (level-1 model, K from ID(on)) | **Applied in design.py:** R11 10k -> 4.7k (0603WAF4701T5E, C23162): gate 2.92-3.17 V, /WAIT <= 0.17 V at every corner; 0.70 mA while the firmware holds GPIO34 low. |
| 3 | WARNING | **Console 5 V budget.** Cart draw from the console regulator ~480 mA peak (S3 TX 355 mA through the buck, RP 60, SRAM 12, glue 6, WS2812 white 36 mA) and ~180 mA average. SMS2 (service manual): LM7805 on a heat sink, adaptors 9 V 0.5 A (AU/EU/UK) or 1 A. CONS_5V has only 100 nF at the fingers. | ESP32-S3 p.27-28; WS2812B p.1; AS6C4008 p.3; `margins.py` | **Applied in design.py:** C 10uF CONS_5V-GND at the fingers (CL10A106KP8NNNC, C19702), as 2600 Rev1. Bring-up: measure the console rail under WiFi TX on SMS1 and SMS2. Firmware option: cap S3 TX power. README: recommend a >= 1 A adaptor; USB power takes the load off the console. |
| 4 | WARNING (sourcing) | AS6C4008-55TIN (C5569980), 74HCT27D,653 (C5984), 74HCT10D,653 (C547236): 0 at JLCPCB and 0 at LCSC on 2026-10-06. TI CD74HCT27M96 (C2878706, JLC 4 / LCSC 3) and CD74HCT10M (C2863188, 9 / 9) are pin-identical (TI p.3); with their tpd (29 / 30 ns) every timing margin stays positive. HC parts are not substitutes (TTL thresholds needed). | LCSC product detail; TI SCHS406/SCHS404 | Consign the SRAMs; use the TI gates as alternates or consign. |
| 5 | INFO | Stock symbols fit the HCT parts: 74LS27/74LS10 units 1,2,13->12 / 3,4,5->6 / 9,10,11->8, 74HC14 1->2 ... 13->12, 74HCT00 1,2->3 / 4,5->6 / 9,10->8 / 12,13->11, VCC 14, GND 7. | Nexperia p.2, TI p.3 | None. |
| 6 | INFO | PWR_OK: 0.82 x CONS_5V = 3.69 V at 4.5 V against SN74HCT14 VT+ max 1.9 V (4.5 V) / 2.1 V (5.5 V); PWR_OK rises at 2.3-2.6 V console and falls at 0.6-1.7 V. The divider keeps VSENSE under the '14's VCC when USB feeds +5V (4.3-4.9 V) and the console is at 5.25 V (4.30 V). The NES review's "VT+ = 0.70 x VCC" came from the mislabelled HC14 PDF. | TI SCLS225G p.5; ngspice sweep | None here; fix the NES Rev0 datasheet copy and that review line. |
| 7 | INFO | M1 fetch: the critical /OE path is console /CE -> '14 -> '00 -> '27 -> '10 (121 ns), not /RD (56 ns). /CE on SMS1/SMS2 is /MREQ gated by the I/O chip's slot enable and falls with /RD, so README's "/CE has opened long before the strobe" is wrong. Data valid 416 ns after T1 vs 524 ns needed: +108 ns with a 40 ns /CE decode (unpublished; 148 ns would use it all). Memory reads +233 ns. The 6-gate arena decode settles before /CE can open /OE (Z80 #7). | Zilog #6/#8/#13/#15; AS6C4008 tOE/tAA p.4; gate tpd p.5-6; `timing_margins.py` | None; correct the README timing paragraph; scope /MREQ -> /CE -> /OE at bring-up. |
| 8 | INFO | RAM_WE write: /WE rises <= 52 ns after /WR (two '27s); Z80 data stays >= 69.7 ns (#35), address >= 89.7 ns (#45): +17.7 ns data hold (+11.7 with CD74HCT27), +37.7 ns address hold; tWP/tDW/tAS met by > 150 ns; decode settles 183 ns before /WR falls. | Zilog p.38-39; AS6C4008 p.4 | None; README bring-up item 2 stays. |
| 9 | INFO | LOAD copy: /WE rises <= 52 ns after /RD; core1 holds D0-D7 150 ns past /RD (30 cycles at 200 MHz): +98 ns. Address hold +37.7 ns, but only for non-M1 reads: in an opcode fetch the refresh address replaces A0-A15 together with /RD rising. GAME + LOAD together would assert /OE and /WE at once. | Zilog #45; `sms_cart.c` | Firmware contract (README): LOAD only for data reads of $8000-$9FFF, never while executing there; GAME = 0 while LOAD = 1. |
| 10 | INFO | SA13-SA19 (and SA19 = chip select) are not static: core1 puts the 1K page's bank on every address change. Budget from address valid: 359 ns for M1 (71 cycles at 200 MHz), 483 ns for memory reads. | AS6C4008 tAA; `timing_margins.py` | None; README wording; measure on hardware. |
| 11 | INFO | RP 3.3 V outputs into the 5 V rail: VOH >= 2.62 V vs 74HCT VIH 2.0 V (+0.62) and **AS6C4008 VIH 2.4 V at VCC 4.5-5.5 V** (+0.22; ~+0.85 into CMOS loads). 2.2 V (NES review) is the 2.7-4.5 V figure. GPIO40-47 (not FT) drive only these inputs. | RP2350 p.1341; AS6C4008 p.3 | None. |
| 12 | INFO | Console signals into GPIO0-31 and the '14's PWR_OK into GPIO32: all Digital IO (FT), 5.5 V-tolerant with IOVDD 3.3 V. VIH(FT) is 2.0 V at IOVDD 3.3 V (README item 7 says 0.65 x IOVDD). | RP2350 p.14, p.1336, p.1340-1341 | README item 7: 2.0 V. |
| 13 | INFO | USB and console both on: P-FET off, +5V = VBUS - VF(SS34) = 4.3-4.9 V; the 74HCTs can sit below their 4.5 V minimum and console 5 V levels exceed their VCC (through the console drivers into the clamps). Inherited from NES Rev0. | `margins.py` | None for Rev0; README: USB with the console on is for flashing. |
| 14 | INFO | AS6C4008 TSOP-I map in `SRAM_PIN` matches p.2 (not DIP order); -55TIN = TSOP-I 8 x 20 mm (p.14); VCC 2.7-5.5 V covers +5V in every source combination. | AS6C4008 p.2-3, p.14 | None. |
| 15 | INFO | **/CONT (34) and /BUSREQ (44): leave on the test pads.** /CONT is a general-purpose input the I/O chip reports on the second controller port, not a boot or cart-detect line; the BIOS detects media by the `TMR SEGA` header after enabling the slot via port $3E; a parts page reports fingers 34 and 44 absent on Sega's 171-5507D board (its numbering not cross-checked); SMS Power lists /CONT as unnecessary for slot adaptors; the console must pull /BUSREQ up (Zilog: wired-OR, external pull-up) since it runs with no cart. Nothing found ties boot on SMS1, SMS2, Mark III or the Power Base Converter to /CONT. | SMS-CARTRIDGE-SLOT p.4; smstech; 171-5507 | None (no 0R fitted, none to DNP). |
| 16 | INFO | 2N7002 at power-on: its gate follows +3V3_RP (the LDO tracks +5V), so /WAIT is pulled within the 5 V ramp (microseconds after +5V passes ~3.3 V), ahead of any console reset release; the RP's pad state does not matter (pull-down: finding 2; high-Z: gate at 3.3 V). | AP2112K start-up 20 us; RP2350 p.1337 | Covered by finding 2. |
| 17 | INFO | No ESD on the edge (as every SMS cart; FT pads have enhanced ESD protection); USB-C D+/D-/VBUS have ESD5Z; CC 5.1k x 2. | RP2350 p.1336 | None. |
| 18 | INFO | Shared FujiNet half re-checked where SMS uses it: AP63203 VIN 3.8-32 V vs 4.3-5.25 V; AP2112K EN = VIN (<= 6 V); CP2102N VBUS sense 3.41 V; S3 EN RC 15.9 Hz; WS2812B VDD 3.7-5.3 V covers 4.3-5.25 V, VIH 2.7 V; crystal CL 10.5 pF vs 10 pF; RP USB 27R; LDO 51-102 mW. | p. cites in `deep_review.json` | None. |
| 19 | INFO | Activity LED (red, 1k from 3.3 V): 1.3-1.5 mA. | KT-0603R p.3 | Optional: 680R (~2 mA) as on 2600 Rev1. |

## design.py changes (in severity order, applied 2026-10-06)

1. R22 (key `R_VBPD`): `R('4.7k', 'VBUS', 'GND', ...)` on the power sheet; 0603WAF4701T5E, C23162.
2. R11 (key `R_WAIT`, `+3V3_RP`-`WAIT_GATE`) 10k -> 4.7k; same part.
3. C38 (key `C_CONS`): `C('10uF', 'CONS_5V', ...)` next to the existing 100 nF; CL10A106KP8NNNC, C19702.
4. README: timing paragraph (/CE is on the critical path; SA lines are per-page), bring-up item 7 (VIH 2.0 V), the LOAD/GAME firmware contract, the adaptor note, the TI alternates.

## Signal and power analysis

- **Power tree:** edge CONS_5V -> Q2 AO3401A (G = VBUS, R22 4.7k to GND) -> +5V; USB VBUS -> D7 SS34 -> +5V. +5V feeds U2/U3 SRAM, U4-U8 glue, D3 WS2812B, U12 AP63203 (+3V3: S3, microSD, CP2102N) and U13 AP2112K (+3V3_RP: every RP2354B supply pin; the RP core SMPS makes DVDD). PWR_OK = '14(0.82 x CONS_5V), sensed before the FET.
- **Regulators:** U12 fixed 3.3 V (switching, 6.8 uH, 3 x 22 uF in, 2 x 22 uF out), U13 fixed 3.3 V; RP SMPS 3.3 uH, FB = DVDD. Datasheet-verified (shared with NES Rev0).
- **SPICE (kicad-happy, ngspice):** 17 subcircuits, 17 pass: R14/C31 15.88 Hz; R12/R13 ratio 0.8197; R19/R20 3.406 V at 5 V; Y1 load 10.5 pF; Q1; D4-D6; six decoupling networks (+3V3_RP z_min 14 mOhm, +5V 3.2 mOhm, CONS_5V 0.32 ohm at 100 nF only); two inrush models. The auto testbench drives dividers from 3.3 V, so `spice_checks.py` adds: VSENSE over 0-5.5 V, the P-FET gate under 10-500 uA leakage plus the unplug decay, and the /WAIT FET at its corners.
- **Decoupling:** +3V3_RP 11 x 100 nF + 10 uF + 4.7 uF + 1 uF; DVDD 3 x 100 nF + 4.7 uF; +5V 3 x 22 uF, 10 uF, 100 nF per SRAM and per glue package, WS2812, LDO in; +3V3 2 x 22 uF buck out, 22 uF + 100 nF S3, 10 uF SD, 4.7 uF + 100 nF CP2102N; VBUS 1 uF + 100 nF; CONS_5V 100 nF + C38 10 uF.
- **Budget:** finding 3. +3V3 ~250 mA typical, 355 mA S3 peak; +3V3_RP 30-60 mA; the selected SRAM is always enabled (static /CE per page) at <= 10 mA (1 us cycle).

## Analyzer findings and false positives

The schematic analyzer reports suppressed findings anyway; `.kicad-happy.json` carries the suppressions below for the PCB/EMC/thermal stages (net patterns are globs, e.g. `*/VBUS_SNS`, so they survive the hierarchy-prefixed names of the redrawn schematic).

| Rule | Count | Disposition |
|---|---|---|
| VM-001 5 V / 3.3 V crossing (RD_N, WR_N, CE_N, GAME, MBOX, RAM_WE, LOAD) | 7 | False positive: console 5 V into FT pads (findings 11-12); RP 3.3 V into HCT/SRAM inputs. The analyzer missed the same crossing on A0-A15/D0-D7 only because of the bus split below. |
| NT-001 single-pin nets `/rp2354b/A0`, `/edge/A0`, `/sram/D0`, `/rp2354b/SA13` ... | 23 warning + 32 info | False positive on the baseline: its sheets joined the bus members through global bus labels `A[0..15]`, `D[0..7]`, `SA[13..19]`, which kicad-happy 2.2.1 does not expand. The KiCad netlist joined them (A0 = J1.25, U1.77, U2.20, U3.20; 31 nets checked). The redrawn schematic carries the buses on hierarchical labels and root buses; the analyzer follows those and NT-001 no longer fires (Part 2). |
| RS-001 PWR_OK, PWR_OK_N, VBUS_SNS "no source" | 3 | False positive: '14 outputs and a divider node. |
| DO-DET "missing decoupling on PWR_OK / VBUS_SNS" | 4 | Same naming confusion. |
| PU-001 U10 CHREN | 1 | Charger-detect output, open as in the DevKitC-1. |
| EP-AUD J1, J2, J3 none; J4 partial (CC1/CC2, SBU) | 4 | Console bus / DNP debug header / microSD inside the shell; CC lines carry 5.1k Rd only, SBU unconnected. |
| CG-AUD J1 15:1 | 1 | Console-defined pin-out (GND 19-21). |
| PS-001 U12 PG unknown | 1 | AP63203 has no PG pin. |
| VD-004 R20 0603 over-sized | 1 | Board passive size. |
| XL-DET target 20 pF | 1 | Frequency default; the part is CL 10 pF (load 10.5 pF). |
| CERT-001 / WL-001 | 2 | Pre-certified S3 module; informational. |
| LC-ACT x 41 / LC-007 | 42 | Lifecycle unknown (LCSC returns no status). |
| DC-002 U11 (stage-2 rule, pre-suppressed) | - | UMH3N has no supply pin. |

## Not performed / limits

- **Layout, cross-domain, EMC, thermal, gerber analyses:** Part 2.
- **Lifecycle:** `lifecycle_audit.py --only lcsc` ran; LCSC gives no lifecycle status, so every part is "unknown"; no DigiKey/Mouser/element14 keys. Stock was queried per LCSC code instead (finding 4).
- **Console-side timing:** the slot /CE delay after /MREQ (315-5216 / 315-5237) is not published; 40 ns is assumed. The SMS Z80 clock is taken as 50 % duty; Zilog's formula figures use TfC = 0 (pessimistic). The NEC D780C-1 used in early SMS1 boards was not checked separately.
- **Console 5 V headroom:** no SMS1 figure for the console's own draw or the cart-slot current; SMS2 adaptor ratings only (service manual). Bench item.
- **Pin-outs from figures:** SN74HCT00 (TI p.3) and the 4D03 array (p.4) were read from drawings; the Z80 table is an OCR of an image-only PDF (values cross-checked against the scan).
- **2N7002 model:** level-1, K derived from the datasheet's ID(on) at the worst VTH; real devices are stronger.
- **Firmware-timed paths** (core1 bank lines, RP-served reads, LOAD release) depend on code latency, measurable only on hardware.
- **Structured extractions** (`datasheets/extracted/`) were not produced; every claim is a direct PDF read with the page in `analysis/deep_review.json`.

## Verdict (schematic)

No design error that stops the board. Two real circuit issues (findings 1-2) are fixed by one resistor each in `tools/design.py`; the console budget (3) gets a capacitor and a bench measurement; the rest are confirmations, documentation corrections and firmware contracts. With the three changes applied: ERC 0, `check_nets.py` 437/437, `check_glue.py` 8192/8192. Reference designators are those of the baseline; the redraw kept them (new parts: R22, C38).

Re-run: `tools/audit/run_sch_audit.sh` (analyzer, SPICE, `spice_checks.py`, `make_deep_review.py`, gate, summary).

# Part 1b — the v2 schematic (2026-10-08)

## Circuit changes since Part 1

| Change | Why | Evidence |
|---|---|---|
| **R18-R22, 4.7k pull-downs on SA19, MBOX, GAME, RAM_WE, LOAD** | RP2350-E9 (stepping A2; fixed in A3/A4, but the stepping a buyer receives is not guaranteed): a Bank 0 pad with its input enabled and output off, between VIL and VIH, sources ~120 uA and sits near 2.2 V; the pad pull-down cannot overcome it, a pull of <= 8.2k can. At 2.2 V the HCT glue reads GAME / MBOX / RAM_WE / LOAD as set, and SA19 can select neither or both SRAMs, which would fight on D0-D7. Right after a PoR or RUN reset the input enable is clear, so the window is a firmware state that tristates these pads. | RP2354B.pdf p.1367-1368 (deep review, finding `io`); `margins.py`: 120 uA x 4.7k = 0.56 V < VIL 0.8 V on every line, 0.70 mA per pin driven high (3.5 mA for all five). FujiNet-7800 Rev0 carries the same pull-downs. |
| **Bring-up pads** TP14 CONS_5V, TP11 +5V, TP2 +3V3, TP7 +3V3_RP, TP1 DVDD; TP8 /CE, TP9 SRAM /OE, TP10 SRAM /WE, TP12 PWR_OK, TP13 GND | The PROVISIONAL timings in `sms_cart.c` and the /MREQ -> /CE -> /OE scope item need probe points; the rails need a check before a console is risked. | README bring-up checklist; `check_nets.py` requires them (442 checks). |
| **Buttons TS-1187A-B-A-B** (C318884, JLC basic) for the TL3342 | 5 in stock on 2026-10-07 against 4 per board. | As on FujiNet-7800 Rev0; footprint and 3D model from it. |
| **WS2812C-2020-V1** (C2976072) for the WS2812B-2020-V6 | 5 in stock. Same 2020 package, land and pin order (1 DO, 2 GND, 3 DI, 4 VDD); VDD 3.7-5.3 V, VIH 2.7 V; 5 mA per channel, not 12. | WS2812C-2020-V1.pdf p.1, p.3 (deep review, finding `led`). The console 5 V budget drops to ~460 mA peak / ~185 mA average (`margins.py`). |

The three Part 1 fixes are fitted and re-verified: the deep review now states them as verified findings (SS34 leakage with R3: VGS -2.8 V at 500 uA; /WAIT held at every corner with R25 4.7k; 10 uF + 100 nF on CONS_5V). `spice_checks.py` was corrected on the way: once R_VBPD existed, its "without" case silently included it too, so both rows matched; it now compares without and with explicitly.

## The redraw

Every sheet is the board turned so the fingers face left (south -> left, north -> right, west -> top, east -> bottom), with each part where it sits and every connection a wire (README, *Schematic*):

- **Functional symbols** for the RP2354B (two units), the ESP32-S3, the USB-C, the SRAM, the microSD and the edge. Their pin names and numbers are the stock KiCad symbols' (`gen_sch.verify_pin_tables`).
- **Gates.** `gen_sch.py` fails the build if any of these break:
  - connectivity and overlap lint;
  - one wired piece per net per sheet;
  - crossing budgets: cart-bus 75 (the glue network), usb 1 (the auto-program pair, whose crossing is unavoidable), all others 0;
  - the mirror check: Kendall tau 1.00 / 1.00 on every sheet;
  - netlist parity;
  - net names equal to `tools/nets.lock`.
- **Results:**
  - ERC: 0 at every severity.
  - `check_nets.py`: 442/442.
  - `check_glue.py`: 8192/8192.
  - The deep review: 28 findings, each verified against its datasheet page, none quarantined.

## Analyzer findings (schematic, v2 run)

The same dispositions as Part 1, with v2's references:

| Rule | Count | Disposition |
|---|---|---|
| VM-001 | 30 | False positive: console 5 V into FT pads, RP 3.3 V into HCT / SRAM inputs (findings 11-12). Now resolved on every bus net. |
| RS-001 PWR_OK / PWR_OK_N / VBUS_SNS | 3 | Logic outputs and a divider node, not rails. |
| PU-001 U2 CHREN | 1 | Charger-detect output, open as on the DevKitC-1. |
| LB-001 | 8 | One hierarchical label per sheet on each cross-sheet net (S3_EN on rp-core, fujinet and usb). The analyzer names them by sheet uuid. `gen_sch.check_hierarchy` holds every label to a root sheet pin. |
| EP-AUD, CG-AUD, VD-004, PS-001, LA-AUD, CERT-001, WL-001, LC-007 | 12 info | As Part 1. |

# Part 2 — the v2 layout and the edge connector (2026-10-08)

**Board:** `FujiNet-SMS-Rev0.kicad_pcb`, placed by `tools/gen_pcb.py` from `tools/placement.py` (floorplan P3) and routed by `tools/route_board.sh`.

## Edge connector (CRITICAL, fixed in the first layout, unchanged)

The baseline `SMS_Cart_Edge_50` had its faces swapped:
- it put the odd pins on F.Cu, with pin 1 at the east end;
- on a console, every finger would have met its partner's contact, and the console's +5V contacts (pins 1 and 35) would have reached the board's /WR (pin 2) and A15 (pin 36).

Every source agrees on the correct layout: the **even pins are on the component (label) side**, with pins 1/2 at the right seen from that side, fingers down.
- [1] SMS Power slot diagram.
- [2] little-scale.
- [3] MrSVCD's 1200 dpi scan of a 171-5519: "50 ... 2" on the component side.
- [4] raphnet SMS4MBIT.
- [5] barbeque KiCad footprint.
- [6] reidrac KiCad footprint.

`tools/make_edge_fp.py` generates the even pads on F.Cu and the odd pads directly behind them on B.Cu:
- pins 1/2 at x +30.48, 2.54 mm pitch;
- fingers 1.75 x 8.75 mm, 0.75-9.5 mm from the edge;
- a 65.8 x 15 mm tab with 1 mm chamfers.

`tools/edge_geom.py` holds these numbers for every tool. Three checks enforce them:
- `tools/audit/edge_orientation.py` checks them against [1]-[6];
- `check_nets.py` checks the faces on the netlist;
- `tools/audit/check_gerbers.py` checks the fab zips: 25 fingers per face at their pins' x, nothing in the tab.

One physical check remains, and it gates ordering: `docs/tab-overlay-1to1.pdf` laid on a real cartridge board.

## The floorplan (co-design)

`docs/floorplan-study.md` has the study. The SMS edge is the JEDEC 32-pin memory pinout unrolled, so an AS6C4008 standing upright in the classic ROM spot (U10, rotation 270, x 107.6) takes A0-A12, D0-D7 and GND from the fingers without one crossing. `gen_pcb.sram0_fanin()` draws that fan-in and locks it before routing.

Four candidates were scored by ratsnest and crossings, then trial-routed. P3 led from pass 4:
- U10 in the ROM spot;
- the RP2354B (U4) straight north of it, its A/D side facing U10;
- SRAM1 (U7) west;
- the glue east, over the strobes;
- the FujiNet half along the top edge.

On the page, P3 also reads straight across: edge, SRAM0, RP.

## Stack-up, rules, placement

| Item | Value |
|---|---|
| Outline | 100 x 78 mm body (x 50-150, y 32-110) + 65.8 x 15 mm tab = 100 x 93 mm; 1.6 mm (VERIFY: no original measured). 4 x M3 holes, 3 fiducials. |
| Layers | F.Cu parts and even fingers / In1 GND, solid under the body / In2, In3 signals / In4 power: +3V3 north, a +5V island south and east, +3V3_RP under the RP ring, DVDD under its core / B.Cu odd fingers and signals. |
| Tab | Fingers only: no tracks, vias or pour on F/B inside the finger rows, and no inner copper anywhere in the tab, so the bevel never exposes a plane. |
| Rules | Default 0.2 mm track / 0.15 mm clearance; PWR 0.5 mm, vias 0.8 / 0.4; VBUS 0.3 mm; USB pairs 0.25 mm. A 0.12 mm clearance floor (`.kicad_dru`) for the last links at the RP's 0.4 mm-pitch pins. The narrowest track is 0.15 mm; JLCPCB's 6-layer minimum is 0.09. |
| Parts | 134 footprints, all on F.Cu: 109 assembled, plus J1 (the edge), 16 test pads, the DNP header J4, H1-H4 and FID1-3. `gen_pcb.check_parts_inside()` checks the body, the hole rings, the antenna keep-out and courtyard overlaps. |

## Routing

Pipeline:
1. The SRAM0 fan-in, the RP's core-regulator corner, the crystal and SWD are drawn or routed first and locked.
2. Freerouting 2.4.1 runs.
3. `drc_fix` and the A* finisher close what it leaves.
4. Then `tidy_tracks`, GND stitching, `check_vias`, 3D models and silkscreen.

Six variants ran in parallel copies:

| Variant | Freerouting | Pre-route | Freerouting "unrouted" | KiCad unconnected after it | Outcome |
|---|---|---|---|---|---|
| V1 | 12 passes, hybrid | corner, crystal, SWD | 46 | 14 | finisher still working when stopped |
| V2 | 20, hybrid | as V1 | 47 at pass 15 | - | stopped (plateau) |
| **V3** | **12, greedy (default)** | **as V1** | **48** | **2** | **finished: 0 unconnected, chosen** |
| V4 | 16, hybrid | corner, crystal only | 47 at pass 14 | - | stopped |
| V5 | 20, global | as V1 | 48 at pass 15 | - | stopped |
| V6 | 16, hybrid | + USB pair | 49 at pass 14 | - | stopped |

Every variant plateaued by pass 8. Most of Freerouting's "unrouted" are plane connections that KiCad's zone fills make: the Phase 2 trials showed 44-47 "unrouted" against 10-20 real KiCad unconnected. On V3, the finisher routed A12 and QSPI_SS.

Two changes after routing:
- **The board title moved** to a clear spot above the edge. The first layout's spot sat on R14, R15 and C18 in this floorplan (8 silk warnings). The new spot was found by rasterising the routed board's pads, courtyards and silk.
- **`fix_silk.py` adds a bold pin-1 dot on U7 / U10.** Both are placed without an EasyEDA footprint, so their CPL rotation is the TSOP-I convention, marked low confidence.

| Result | Value |
|---|---|
| DRC (every severity, refilled zones, schematic parity) | 0 violations, 0 unconnected, 0 parity issues |
| Nets | 126 (design), all routed; analyzer `routing_complete`, 184/184 KiCad nets |
| Copper | 1951 segments, 6055 mm of track (F.Cu 1109, In2 391, In3 353, B.Cu 98) |
| Vias | 743: 390 GND (271 of them stitching, edge guard and USB return), the rest signal and plane fan-out; `check_vias` 743/743 |
| Mirror | every footprint exactly at its `placement.py` position, so the schematic's mirror check holds on the routed board; references geographic (`annotate.py --check`) |

## Fab packages

`tools/export.py` writes `exports/jlcpcb/` and `exports/pcbway/`. `tools/audit/check_fab.py` passes all of these:

1. The JLC BOM, JLC CPL, PCBWay BOM and PCBWay centroid all carry exactly the 109 assembled parts, once each.
2. Every JLC line carries its LCSC code.
3. Every PCBWay line carries its MPN and manufacturer.
4. JLC CPL positions and rotations recompute from the measured EasyEDA offsets.
5. The PCBWay centroid is KiCad's own.
6. The drills: 770 hits = 743 vias + 19 plated pads (the four USB-C shell slots included) + 8 unplated holes.
7. The order-number text: a clear spot, in the JLC F.Silkscreen (88 strokes), not in PCBWay's.
8. `check_gerbers.py`: the zips are identical except the silkscreen, 25 fingers per face, the tab clean.

`docs/sourcing.md` (2026-10-08): 42 of 45 lines are in JLC stock for 5 boards, at about USD 29 of parts per board. The AS6C4008-55TIN and the Nexperia 74HCT27D / 74HCT10D are not, and are to be consigned, bought through Global Sourcing, or ordered turnkey at PCBWay. The TI CD74HCT10M covers 5 boards; the CD74HCT27M96 does not.

## Analyzer findings (layout run) and triage

| Rule | Count | Disposition |
|---|---|---|
| KO-001 H1-H4, J1 inside keep-outs | 6 | Deliberate rule areas. The screw keep-outs exist for the holes; the tab keep-outs allow pads (the fingers). |
| PM-002 J3 0.2 mm, U1 0.15 mm, J2 0.85 mm, FID1 / TP14 0.75 mm from the edge | 1 + 5 | The microSD and USB-C mouths and the S3 antenna face the shell's top wall by design; JLCPCB mills the outline. FID1's centre is 2.0 mm in: its copper and mask ring stay 1 mm clear, and JLC adds its own rail fiducials. TP14 is a probe pad. |
| GP-001 reference-plane gap: BUSREQ_N 67 %, A10 78 %, WAIT_N 80 %; 18 more nets at 87-95 % | 3 + 18 | Accepted. Each finger stub crosses the tab, which carries no inner copper (about 5.5 mm per net); the rest are In3 runs crossing In4 island boundaries. The bus runs at 3.58 MHz with HCT / Z80 edges, and every cartridge board has the same stubs over no plane. |
| RP-001 layer change without a GND via within 1 mm | 1 high (/USB_DM) + 20 warning + 1 info | /USB_DM: one of its three transitions lacks a GND via within 1 mm (`stitch_gnd` placed 3 of 5 USB return vias; 2 had no room). Full-speed USB (12 Mb/s) over a short run is tolerant; the S3-RP pair stays on the board. The 20 warnings are 3.58 MHz bus nets through the RP and SRAM fan-out. |
| **DC-001 U10 (SRAM0) nearest 100 nF 8.7 mm** | 1 high | Measured: C42 is 9.2 mm from VCC pin 8, pad to pin; U7's cap is 6.6 mm from its pin. The TSOP-I puts VCC (pin 8) and VSS (pin 24) mid-row on opposite ends, 19.4 mm apart, and in the ROM spot pin 8 faces the RP's fan-out, so it drops through a via straight into the In4 +5V island under both SRAMs. C42 has its own vias to In4 and In1 0.9 mm from its pads. Moving it into the one clear patch nearby (6.6 mm) would cost its GND via (the nearest GND via there is 4 mm away), with no net gain, so it stays. The SRAM draws <= 10 mA at a 1 us cycle on a 3.58 MHz bus. **Rev1:** a dedicated 100 nF at pin 8 (needs a local reroute). |
| DC-002 U3 | 1 (suppressed) | UMH3N: no supply pin. |
| CC-002 narrow signal 0.15 mm | 12 | The `--neck` last links at the RP's and the glue's fine-pitch pins; logic currents. |
| CK-001 / CK-003 clocks on outer layers, near J3 / J4 | 5 + 2 | CLK (3.58 MHz, one RP load), XIN / XOUT (the crystal corner, inside the RP ring), SD_SCK (the microSD's own clock); J4 is the DNP debug header beside CLK's run. Accepted. |
| XT-001 SD_CD / SD_MISO, A5 / A7, A11 / A8 parallel | 3 info | A slow card-detect line and the 3.58 MHz bus. |
| BE-002 ground pour on part of the perimeter | 1 | The tab (fingers, no pour) and the antenna keep-out are the missing edges. By design. |
| SW-001 / EE-001 / EE-002 buck harmonics, cavity resonance | 3 + 2 info | Estimates. No pre-compliance scan has been done. The S3 is a certified module; the buck follows the NES Rev0 layout. |
| IO-001 / IO-002 J1, J4 filtering, J1 ground pins | 3 info | Console-defined connector, as on every SMS cartridge; DNP header. |
| TE-001 test points 11/180 nets | 1 | The bring-up set: every rail, /CE, SRAM /OE and /WE, PWR_OK, SWD, RUN, scope GNDs; the bus is probed at the fingers. |
| CP-002 no copper under H1-H4, J1, J4, TP3, TP16 | 8 info | Screw keep-outs, the tab, THT and probe pads. |
| OR-001 34 passives not at 0 degrees | 1 info | The decoupling ring follows the RP's pins; the CPL carries measured rotations. |
| TS-003 / TP-001 U6 Tj 96 C | 1 + 5 (suppressed) | Heuristic: it books the whole board's 0.286 W on the AP2112K. The LDO actually carries only the RP: 51-102 mW, about +25 C. Thermal score 100. |
| Cross-analysis, cross_verify | 0 | Schematic and board agree. |

**EMC risk score: 32.5** (lower is better; the first layout scored 41.5).

## Fab release gate (`fab_release_gate.py --strict`)

10 pass, 2 fail. Both failures are waived:

| Check | Result | Waiver |
|---|---|---|
| Routing, BOM (109/109 MPNs), footprints, DFM, revision and board name on the board, net counts (184), gerber layers, thermal, EMC | pass | -- |
| Component count: schematic 126 placeable vs PCB 134 | fail | The gate subtracts DNP parts from the schematic count but not from the board's, and counts board-only footprints. The difference is exactly H1-H4, FID1-3 and the DNP header J4. KiCad's own schematic parity, which knows both, is 0. |
| Gerber "layer alignment": height varies by 17.2 mm | fail | By design: In1-In4 stop at the body, because the tab carries no inner copper, so the bevel never exposes a plane. F.Cu / B.Cu reach the fingers. `check_gerbers.py` asserts both. |

The revision check passes since this run: the board now has a KiCad title block with rev 0, which `gen_pcb.py` writes.

## Not performed / limits (layout)

- **No field solver or SI/PI simulation.** GP-001, RP-001, DC-001 and XT-001 were judged by hand against signal speed.
- **No EMC pre-compliance scan.** The analyzer's emission numbers are heuristics.
- **The mechanical items are not measured:** board thickness, the edge recess and mouth, tab depth, seat depth and the console overlay. Each is a VERIFY in `case/case-spec.md`. The overlay (`docs/tab-overlay-1to1.pdf`) and the thickness gate the order.
- **The assemblers' rotation of U7 / U10** (AS6C4008, no EasyEDA footprint) follows the TSOP-I convention. Confirm it in the placement preview against the pin-1 dots.
- **No impedance-controlled stack-up was ordered.** USB is full speed over short runs, so 90 ohm control is not needed.
- **Freerouting is not deterministic** across machines. `LAYOUT=1 build_all.sh` reproduces the method (12 passes, greedy), not the same copper; the committed board is the reviewed one.

## Verdict (layout)

The v2 board is routed and DRC-clean, with schematic parity at every severity. Every analyzer finding is triaged. One is worth a Rev1 change: a dedicated 100 nF at SRAM0's VCC pin. The two release-gate failures are tool limits, explained above. Both fab packages pass `check_fab.py`.

Before ordering:
1. Lay the 1:1 tab overlay on a real cartridge, and measure an original board's thickness.
2. Check U7 / U10 against their pin-1 dots in the assembler's preview.
3. Source the SRAMs and the Nexperia '27 / '10 (consign, Global Sourcing, or PCBWay turnkey).
