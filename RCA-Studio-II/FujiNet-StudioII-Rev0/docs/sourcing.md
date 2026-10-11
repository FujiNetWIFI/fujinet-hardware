# FujiNet-StudioII Rev0: sourcing (2026-10-11)

Stock read 2026-10-11T10:13:48-05:00 by `tools/audit/sourcing.py`: JLCPCB parts library via its own search API, LCSC via its product-detail API (raw answers in `analysis/sourcing/2026-10-11.json`). Quantities for 2 and 5 assembled boards; JLCPCB makes at least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, in USD, before assembly fees.

| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | LCSC lifecycle | Need (2 / 5) | Status | USD per board |
|---|---|---|---|---|---|---|---|---|---|---|
| C1,C2,C3,C4,C6,C7,C8,C9,C10,C11,C13,C... | YAGEO CC0603KRX7R9BB104 | C14663 | 23 | 56335260 | basic | 5850 | normal | 46 / 115 | OK | 0.32 |
| C5,C18,C30,C37 | Samsung Electro-Mechanics CL10A106KP8NNNC | C19702 | 4 | 10372994 | basic | 1091180 | normal | 8 / 20 | OK | 0.12 |
| C12,C16,C22 | Samsung Electro-Mechanics CL05B104KO5NNNC | C1525 | 3 | 24527055 | basic | 10035600 | normal | 6 / 15 | OK | 0.01 |
| C19,C23 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 2 | 2096896 | basic | 990150 | normal | 6 / 15 | OK | 0.03 |
| C24 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 1 | 2096896 | basic | 990150 | normal | 6 / 15 | OK | 0.02 |
| C25,C26 | Samsung Electro-Mechanics CL10C150JB8NNNC | C1644 | 2 | 957825 | basic | 204300 | normal | 4 / 10 | OK | 0.02 |
| C27,C39,C40,C43,C44 | Samsung Electro-Mechanics CL21A226MAQNNNE | C45783 | 5 | 3689034 | basic | 184920 | normal | 10 / 25 | OK | 1.11 |
| C29,C32,C36,C45,C46 | Samsung Electro-Mechanics CL10A105KB8NNNC | C15849 | 5 | 8605470 | basic | 2289200 | normal | 10 / 25 | OK | 0.08 |
| C35 | Samsung Electro-Mechanics CL10A475KO8NNNC | C19666 | 1 | 2906583 | basic | 43480 | normal | 2 / 5 | OK | 0.03 |
| D1 | Hubei KENTO Elec KT-0603R | C2286 | 1 | 7253911 | basic | 4751100 | normal | 2 / 5 | OK | 0.01 |
| D2 | Nexperia BAT54C,215 | C37704 | 1 | 275887 | preferred | 233100 | normal | 2 / 5 | OK | 0.02 |
| D3 | Worldsemi WS2812B-2020-V6 | C52917434 | 1 | 987440 | extended | 974170 | normal | 2 / 5 | OK | 0.09 |
| J3 | SOFNG TF-015 | C113206 | 1 | 22566 | extended | 22565 | normal | 2 / 5 | OK | 0.13 |
| J4 | Korean Hroparts Elec TYPE-C-31-M-12 | C165948 | 1 | 408397 | extended | 384315 | normal | 2 / 5 | OK | 0.19 |
| L1 | Abracon AOTA-B201610S3R3-101-T | C42411119 | 1 | 24 | extended | 0 | normal | 2 / 5 | OK | 0.29 |
| L2 | Sunlord SWPA4030S6R8MT | C62684 | 1 | 16824 | extended | 0 | no LCSC record (JLC lists it) | 2 / 5 | OK | ? |
| R1,R2,R3,R4,R5,R6,R7,R8,R9,R10,R29 | UNI-ROYAL 0603WAF3300T5E | C23138 | 11 | 3023915 | basic | 834700 | normal | 22 / 55 | OK | 0.03 |
| R11,R12,R20,R22,R27,R28,R36 | UNI-ROYAL 0603WAF1002T5E | C25804 | 7 | 33667481 | basic | 0 | normal | 14 / 35 | OK | 0.02 |
| R13,R32 | UNI-ROYAL 0603WAF2202T5E | C31850 | 2 | 3569998 | basic | 2334600 | normal | 4 / 10 | OK | 0.01 |
| R14,R15,R16 | UNI-ROYAL 0603WAF1003T5E | C25803 | 3 | 20957285 | basic | 11975600 | normal | 6 / 15 | OK | 0.01 |
| R17,R19,R21,R23,R24,R34 | UNI-ROYAL 0603WAF1001T5E | C21190 | 6 | 26932924 | basic | 7655200 | normal | 12 / 30 | OK | 0.02 |
| R18 | UNI-ROYAL 0402WGF330JTCE | C25105 | 1 | 1681338 | basic | 0 | normal | 2 / 5 | OK | 0.00 |
| R25,R26 | UNI-ROYAL 0402WGF270JTCE | C25100 | 2 | 38383 | extended | 0 | normal | 4 / 10 | OK | 0.00 |
| R30,R31 | UNI-ROYAL 0603WAF5101T5E | C23186 | 2 | 24565845 | basic | 19479900 | normal | 4 / 10 | OK | 0.00 |
| R33 | UNI-ROYAL 0603WAF4702T5E | C25819 | 1 | 2205194 | basic | 0 | normal | 2 / 5 | OK | 0.00 |
| R35 | UNI-ROYAL 0603WAF3302T5E | C4216 | 1 | 3792151 | basic | 2929400 | normal | 2 / 5 | OK | 0.00 |
| RN1 | UNI-ROYAL 4D03WGJ0103T5E | C29718 | 1 | 2105259 | basic | 1485600 | normal | 2 / 5 | OK | 0.01 |
| SW1 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 381248 | basic | 101560 | normal | 8 / 20 | OK | 0.02 |
| SW2 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 381248 | basic | 101560 | normal | 8 / 20 | OK | 0.02 |
| SW3 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 381248 | basic | 101560 | normal | 8 / 20 | OK | 0.02 |
| SW4 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 381248 | basic | 101560 | normal | 8 / 20 | OK | 0.02 |
| U1 | Raspberry Pi RP2354B | C39843328 | 1 | 3640 | extended | 3192 | normal | 2 / 5 | OK | 1.53 |
| U2 | Texas Instruments SN74HCT541PWR | C436096 | 1 | 25567 | extended | 25567 | normal | 2 / 5 | OK | 0.51 |
| U3 | Nexperia 74HCT1G02GV,125 | C12504 | 1 | 2952 | extended | 2950 | normal | 2 / 5 | OK | 0.11 |
| U4 | Texas Instruments SN74HCT32DR | C6781 | 1 | 3062 | extended | 3060 | normal | 2 / 5 | OK | 0.54 |
| U5 | Texas Instruments SN74HCT14DR | C6769 | 1 | 36312 | extended | 36302 | normal | 2 / 5 | OK | 0.70 |
| U6 | Espressif ESP32-S3-WROOM-1-N16R8 | C2913202 | 1 | 34474 | extended | 0 | normal | 2 / 5 | OK | 5.20 |
| U7 | STMicroelectronics USBLC6-2SC6 | C7519 | 1 | 35283 | extended | 31335 | normal | 2 / 5 | OK | 0.18 |
| U8 | Silicon Labs CP2102N-A02-GQFN28R | C964632 | 1 | 36874 | extended | 36698 | normal | 2 / 5 | OK | 1.84 |
| U9 | Jiangsu Changjing (JSCJ) UMH3N | C62892 | 1 | 54424 | extended | 48510 | normal | 2 / 5 | OK | 0.05 |
| U10 | Texas Instruments TPS2116DRLR | C3235557 | 1 | 75447 | extended | 75464 | normal | 2 / 5 | OK | 0.40 |
| U11 | Diodes Incorporated AP63203WU-7 | C780769 | 1 | 12732 | extended | 4909 | normal | 2 / 5 | OK | 1.19 |
| U12 | Diodes Incorporated AP2112K-3.3TRG1 | C51118 | 1 | 29779 | extended | 29785 | normal | 2 / 5 | OK | 0.17 |
| Y1 | Abracon ABM8-272-T3 | C20625731 | 1 | 9321 | extended | 9321 | normal | 2 / 5 | OK | 0.63 |

Parts cost per board (LCSC prices, 5-board quantities): **USD 15.71**, before JLC assembly, extended-part and Global Sourcing fees.

## Lifecycle

LCSC's product-cycle flag for every line: not "normal" for:

- SWPA4030S6R8MT C62684 (L2): no LCSC record (JLC lists it)

## Short at JLCPCB

Nothing: every assembled line is in JLCPCB stock for 5 boards.


For a short line, one of:

1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser by MPN, ship to JLC).
2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).
3. **A drop-in substitute** in stock at JLC (same footprint and pinout): change design.py, re-run `tools/build_all.sh` and the JLC rotation measurement.
