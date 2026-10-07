# FujiNet-SMS Rev0 Design Review

**Project:** FujiNet-SMS-Rev0 (KiCad 10.0.6, root + 7 hierarchical sheets, generated from `tools/design.py`)
**Date:** 2026-10-06
**Baseline:** the schematic committed on master as `f5538b5` ("SMS: add the FujiNet-SMS-Rev0 schematic"), analysed as a frozen snapshot while the schematic was being redrawn. Fixes 1-3 below are **applied in `tools/design.py`** (keys `R_VBPD`, `R_WAIT`, `C_CONS`) and in the redrawn schematic; the edge-footprint correction (pin faces) was found separately and is in Part 2.
**Analyzers:** kicad-happy 2.2.1 `analyze_schematic.py` (run `2026-10-06_1950`), `simulate_subcircuits.py` (ngspice), `summarize_findings.py`, Deep Review pass (`analysis/deep_review.json`, 27 findings, evidence gate 27/27 verified, 0 quarantined), `lifecycle_audit.py --only lcsc`, KiCad ERC (`--severity-all`: 0 errors, 0 warnings), and the project's own scripts in `tools/audit/`.

# Part 1 — schematic audit

## Scope

All-in-one Sega Master System / SMS2 cartridge. An RP2354B (QFN-80, all 48 GPIOs) sits on the console's 5 V Z80 bus through its 5 V-tolerant pads and serves the mailbox, the loader and the bank lines. Two AS6C4008-55 (TSOP-I) SRAMs hold 1 MB on the 5 V rail. Five 74HCT packages (14, 27, 27, 10, 00) make SRAM /OE, /WE and PWR_OK. A 2N7002 holds console /WAIT. The FujiNet half is NES Rev0's circuit: ESP32-S3-WROOM-1-N16R8, CP2102N + UMH3N auto-program, USB-C, microSD, WS2812B-2020, AO3401A/SS34 power OR, AP63203 buck, AP2112K LDO.

Covered: every IC and transistor against its manufacturer PDF; the glue's pin-outs, logic levels and timing against the Z80; the power path, the console 5 V budget, power-on behaviour; the edge-connector signals left open; stock. Not covered: layout (none yet), the edge-finger geometry (README bring-up item 1).

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

1. `R('4.7k', 'VBUS', 'GND', desc='P-FET gate pull-down against the SS34 reverse leakage')` on the power sheet; 0603WAF4701T5E, C23162.
2. R11 (`+3V3_RP`-`WAIT_GATE`) 10k -> 4.7k; same part.
3. `C('10uF', 'CONS_5V', desc='edge 5V bulk')` next to the existing 100 nF; CL10A106KP8NNNC, C19702.
4. README: timing paragraph (/CE is on the critical path; SA lines are per-page), bring-up item 7 (VIH 2.0 V), the LOAD/GAME firmware contract, the adaptor note, the TI alternates.

## Signal and power analysis

- **Power tree:** edge CONS_5V -> Q2 AO3401A (G = VBUS, 4.7k planned) -> +5V; USB VBUS -> D7 SS34 -> +5V. +5V feeds U2/U3 SRAM, U4-U8 glue, D3 WS2812B, U12 AP63203 (+3V3: S3, microSD, CP2102N) and U13 AP2112K (+3V3_RP: every RP2354B supply pin; the RP core SMPS makes DVDD). PWR_OK = '14(0.82 x CONS_5V), sensed before the FET.
- **Regulators:** U12 fixed 3.3 V (switching, 6.8 uH, 3 x 22 uF in, 2 x 22 uF out), U13 fixed 3.3 V; RP SMPS 3.3 uH, FB = DVDD. Datasheet-verified (shared with NES Rev0).
- **SPICE (kicad-happy, ngspice):** 17 subcircuits, 17 pass: R14/C31 15.88 Hz; R12/R13 ratio 0.8197; R19/R20 3.406 V at 5 V; Y1 load 10.5 pF; Q1; D4-D6; six decoupling networks (+3V3_RP z_min 14 mOhm, +5V 3.2 mOhm, CONS_5V 0.32 ohm at 100 nF only); two inrush models. The auto testbench drives dividers from 3.3 V, so `spice_checks.py` adds: VSENSE over 0-5.5 V, the P-FET gate under 10-500 uA leakage plus the unplug decay, and the /WAIT FET at its corners.
- **Decoupling:** +3V3_RP 11 x 100 nF + 10 uF + 4.7 uF + 1 uF; DVDD 3 x 100 nF + 4.7 uF; +5V 3 x 22 uF, 10 uF, 100 nF per SRAM and per glue package, WS2812, LDO in; +3V3 2 x 22 uF buck out, 22 uF + 100 nF S3, 10 uF SD, 4.7 uF + 100 nF CP2102N; VBUS 1 uF + 100 nF; CONS_5V 100 nF (+10 uF planned).
- **Budget:** finding 3. +3V3 ~250 mA typical, 355 mA S3 peak; +3V3_RP 30-60 mA; the selected SRAM is always enabled (static /CE per page) at <= 10 mA (1 us cycle).

## Analyzer findings and false positives

The schematic analyzer reports suppressed findings anyway; `.kicad-happy.json` carries the suppressions below for the PCB/EMC/thermal stages (net patterns are globs, e.g. `*/VBUS_SNS`, so they survive the hierarchy-prefixed names of the redrawn schematic).

| Rule | Count | Disposition |
|---|---|---|
| VM-001 5 V / 3.3 V crossing (RD_N, WR_N, CE_N, GAME, MBOX, RAM_WE, LOAD) | 7 | False positive: console 5 V into FT pads (findings 11-12); RP 3.3 V into HCT/SRAM inputs. The analyzer missed the same crossing on A0-A15/D0-D7 only because of the bus split below. |
| NT-001 single-pin nets `/rp2354b/A0`, `/edge/A0`, `/sram/D0`, `/rp2354b/SA13` ... | 23 warning + 32 info | False positive: analyzer limitation. The bus members are joined across sheets by the global bus labels `A[0..15]`, `D[0..7]`, `SA[13..19]`; kicad-happy 2.2.1 does not expand them. The KiCad netlist joins them (A0 = J1.25, U1.77, U2.20, U3.20; 31 nets checked). |
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

- **Layout, cross-domain, EMC, thermal, gerber analyses:** no PCB yet (Part 2).
- **Lifecycle:** `lifecycle_audit.py --only lcsc` ran; LCSC gives no lifecycle status, so every part is "unknown"; no DigiKey/Mouser/element14 keys. Stock was queried per LCSC code instead (finding 4).
- **Console-side timing:** the slot /CE delay after /MREQ (315-5216 / 315-5237) is not published; 40 ns is assumed. The SMS Z80 clock is taken as 50 % duty; Zilog's formula figures use TfC = 0 (pessimistic). The NEC D780C-1 used in early SMS1 boards was not checked separately.
- **Console 5 V headroom:** no SMS1 figure for the console's own draw or the cart-slot current; SMS2 adaptor ratings only (service manual). Bench item.
- **Pin-outs from figures:** SN74HCT00 (TI p.3) and the 4D03 array (p.4) were read from drawings; the Z80 table is an OCR of an image-only PDF (values cross-checked against the scan).
- **2N7002 model:** level-1, K derived from the datasheet's ID(on) at the worst VTH; real devices are stronger.
- **Firmware-timed paths** (core1 bank lines, RP-served reads, LOAD release) depend on code latency, measurable only on hardware.
- **Structured extractions** (`datasheets/extracted/`) were not produced; every claim is a direct PDF read with the page in `analysis/deep_review.json`.

## Verdict (schematic)

No design error that stops the board. Two real circuit issues (findings 1-2) have one-resistor fixes planned in `tools/design.py`; the console budget (3) gets a capacitor and a bench measurement; the rest are confirmations, documentation corrections and firmware contracts. Ready for layout once the three `design.py` changes are in and ERC / `check_nets.py` / `check_glue.py` are re-run.

Re-run: `tools/audit/run_sch_audit.sh` (analyzer, SPICE, `spice_checks.py`, `make_deep_review.py`, gate, summary).
