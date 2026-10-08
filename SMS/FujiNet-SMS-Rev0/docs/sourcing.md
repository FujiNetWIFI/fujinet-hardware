# FujiNet-SMS Rev0: sourcing (2026-10-08)

Stock read 2026-10-08T12:34:50-05:00 by `tools/audit/sourcing.py`: JLCPCB parts library via jlcsearch, LCSC via its product-detail API (raw answers in `analysis/sourcing/2026-10-08.json`). Quantities for 2 and 5 assembled boards; JLCPCB makes at least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, in USD, before assembly fees.

| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | Need (2 / 5) | Status | USD per board |
|---|---|---|---|---|---|---|---|---|---|
| C1,C6,C16,C17,C24,C25 | Samsung Electro-Mechanics CL21A226MAQNNNE | C45783 | 6 | 1734789 | basic | 628400 | 12 / 30 | OK | 1.33 |
| C4,C7,C35,C36 | Samsung Electro-Mechanics CL10A105KB8NNNC | C15849 | 4 | 5979916 | basic | 2665550 | 8 / 20 | OK | 0.06 |
| C8,C14,C18,C21 | Samsung Electro-Mechanics CL10A475KO8NNNC | C19666 | 4 | 1373603 | basic | 450 | 8 / 20 | OK | 0.12 |
| C23,C33 | Samsung Electro-Mechanics CL10C150JB8NNNC | C1644 | 2 | 368878 | basic | 298550 | 4 / 10 | OK | 0.02 |
| C3,C27,C41,C48 | Samsung Electro-Mechanics CL10A106KP8NNNC | C19702 | 4 | 5302559 | basic | 2792340 | 8 / 20 | OK | 0.12 |
| C2,C5,C9,C10,C11,C12,C13,C15,C19,C20,... | YAGEO CC0603KRX7R9BB104 | C14663 | 28 | 12618106 | basic | 1667300 | 56 / 140 | OK | 0.35 |
| D1 | MDD (Microdiode Semiconductor) SS34 | C8678 | 1 | 3557042 | basic | 3518600 | 2 / 5 | OK | 0.04 |
| D2,D3,D4 | onsemi ESD5Z5.0T1G | C82044 | 3 | 315966 | extended | 377920 | 6 / 15 | OK | 0.11 |
| D5 | Nexperia BAT54C,215 | C37704 | 1 | 176230 | preferred | 286250 | 2 / 5 | OK | 0.02 |
| D6 | Worldsemi WS2812C-2020-V1 | C2976072 | 1 | 376897 | extended | 0 | 2 / 5 | OK | 0.10 |
| D7 | Hubei KENTO Elec KT-0603R | C2286 | 1 | 8154450 | basic | 4654500 | 2 / 5 | OK | 0.01 |
| J2 | Korean Hroparts Elec TYPE-C-31-M-12 | C165948 | 1 | 89797 | extended | 396270 | 2 / 5 | OK | 0.19 |
| J3 | SOFNG TF-015 | C113206 | 1 | 17779 | extended | 22930 | 2 / 5 | OK | 0.13 |
| L1 | Abracon AOTA-B201610S3R3-101-T | C42411119 | 1 | 20758 | extended | 5 | 2 / 5 | OK | 0.29 |
| L2 | Sunlord SWPA4030S6R8MT | C62684 | 1 | 2224 | extended | 0 | 2 / 5 | OK | ? |
| Q1 | Jiangsu Changjing (JSCJ) 2N7002 | C8545 | 1 | 432340 | basic | 925900 | 2 / 5 | OK | 0.02 |
| Q2 | Alpha & Omega Semiconductor AO3401A | C15127 | 1 | 715902 | basic | 262620 | 2 / 5 | OK | 0.10 |
| R1,R2 | UNI-ROYAL 0603WAF5101T5E | C23186 | 2 | 3775920 | basic | 20509800 | 4 / 10 | OK | 0.00 |
| R6 | UNI-ROYAL 0603WAF330JT5E | C23140 | 1 | 1772784 | basic | 3383600 | 2 / 5 | OK | 0.00 |
| R4,R5,R7,R9,R16 | UNI-ROYAL 0603WAF1002T5E | C25804 | 5 | 37165617 | basic | 0 | 10 / 25 | OK | 0.01 |
| R13 | UNI-ROYAL 0603WAF4702T5E | C25819 | 1 | 1803082 | basic | 0 | 2 / 5 | OK | 0.00 |
| R10,R17 | UNI-ROYAL 0603WAF270JT5E | C25190 | 2 | 103733 | preferred | 1200 | 4 / 10 | OK | 0.00 |
| R23 | UNI-ROYAL 0603WAF3300T5E | C23138 | 1 | 1090237 | basic | 1189200 | 2 / 5 | OK | 0.00 |
| R8,R11,R14,R15,R24 | UNI-ROYAL 0603WAF1001T5E | C21190 | 5 | 8013731 | basic | 3900 | 10 / 25 | OK | 0.01 |
| R3,R18,R19,R20,R21,R22,R25 | UNI-ROYAL 0603WAF4701T5E | C23162 | 7 | 7433362 | basic | 10725900 | 14 / 35 | OK | 0.02 |
| R12,R26 | UNI-ROYAL 0603WAF2202T5E | C31850 | 2 | 1245258 | basic | 2510300 | 4 / 10 | OK | 0.01 |
| R27 | UNI-ROYAL 0603WAF1003T5E | C25803 | 1 | 7990119 | basic | 13514000 | 2 / 5 | OK | 0.00 |
| RN1 | UNI-ROYAL 4D03WGJ0103T5E | C29718 | 1 | 826216 | basic | 1635200 | 2 / 5 | OK | 0.01 |
| RN2,RN3 | UNI-ROYAL 4D03WGJ0101T5E | C25506 | 2 | 182536 | extended | 165500 | 4 / 10 | OK | 0.02 |
| SW1 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1683297 | basic | 186340 | 8 / 20 | OK | 0.02 |
| SW2 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1683297 | basic | 186340 | 8 / 20 | OK | 0.02 |
| SW3 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1683297 | basic | 186340 | 8 / 20 | OK | 0.02 |
| SW4 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1683297 | basic | 186340 | 8 / 20 | OK | 0.02 |
| U1 | Espressif ESP32-S3-WROOM-1-N16R8 | C2913202 | 1 | 32101 | extended | 0 | 2 / 5 | OK | 5.19 |
| U2 | Silicon Labs CP2102N-A02-GQFN28R | C964632 | 1 | 14927 | extended | 37430 | 2 / 5 | OK | 1.84 |
| U3 | Jiangsu Changjing (JSCJ) UMH3N | C62892 | 1 | 28090 | extended | 50030 | 2 / 5 | OK | 0.05 |
| U4 | Raspberry Pi RP2354B | C39843328 | 1 | 385 | extended | 1050 | 2 / 5 | OK | 1.55 |
| U5 | Diodes Incorporated AP63203WU-7 | C780769 | 1 | 11392 | extended | 8601 | 2 / 5 | OK | 1.19 |
| U6 | Diodes Incorporated AP2112K-3.3TRG1 | C51118 | 1 | 79480 | extended | 31300 | 2 / 5 | OK | 0.17 |
| U8 | Nexperia 74HCT10D,653 | C547236 | 1 | 0 | unknown | 0 | 2 / 5 | not listed at JLC: consign / Global Sourcing / PCBWay | 0.26 |
| U9,U13 | Nexperia 74HCT27D,653 | C5984 | 2 | 0 | unknown | 0 | 4 / 10 | not listed at JLC: consign / Global Sourcing / PCBWay | 1.23 |
| U7,U10 | Alliance Memory AS6C4008-55TIN | C5569980 | 2 | 0 | unknown | 0 | 4 / 10 | not listed at JLC: consign / Global Sourcing / PCBWay | 12.43 |
| U11 | Texas Instruments SN74HCT00DR | C6764 | 1 | 2450 | extended | 2816 | 2 / 5 | OK | 0.40 |
| U12 | Texas Instruments SN74HCT14DR | C6769 | 1 | 1240 | extended | 16349 | 2 / 5 | OK | 0.52 |
| Y1 | Abracon ABM8-272-T3 | C20625731 | 1 | 18110 | extended | 10194 | 2 / 5 | OK | 0.63 |

Parts cost per board (LCSC prices, 5-board quantities): **USD 28.63**, before JLC assembly, extended-part and Global Sourcing fees.

## Short at JLCPCB

- **Nexperia 74HCT10D,653** (C547236, U8): not listed by jlcsearch (no JLC stock shown; confirm on the order page), LCSC 0, need 5 for 5 boards. Alternates: CD74HCT10M Texas Instruments C2863188: JLC 9, LCSC 9.
- **Nexperia 74HCT27D,653** (C5984, U9, U13): not listed by jlcsearch (no JLC stock shown; confirm on the order page), LCSC 0, need 10 for 5 boards. Alternates: CD74HCT27M96 Texas Instruments C2878706: JLC 4, LCSC 3.
- **Alliance Memory AS6C4008-55TIN** (C5569980, U7, U10): not listed by jlcsearch (no JLC stock shown; confirm on the order page), LCSC 0, need 10 for 5 boards.

Distributor stock for the consign / turnkey lines (web search, 2026-10-08; re-check on the order day):

- **AS6C4008-55TIN**: DigiKey 909 ($9.61 at 1), Mouser 195 (25 weeks beyond stock), TME 420, Farnell 297, Newark 212
  ([DigiKey](https://www.digikey.com/en/products/detail/alliance-memory-inc/AS6C4008-55TIN/4234589),
  [Mouser](https://www.mouser.com/ProductDetail/Alliance-Memory/AS6C4008-55TIN?qs=E5c5%2Bmu3i39Yioey6aezLQ%3D%3D)).
  10 for 5 boards, plus spares: about $100.
- **74HCT10D,653**: DigiKey 2655 ($0.48 at 1)
  ([DigiKey](https://www.digikey.com/en/products/detail/nexperia-usa-inc/74HCT10D-653/1230591)).
- **74HCT27D,653**: reported in stock at DigiKey (1491) and Mouser ($0.53); the search did not return the part's own
  DigiKey page, so confirm it there.

For each short line, one of:

1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser, ship to JLC; `exports/jlcpcb/consigned.csv` lists them).
2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).
3. **PCBWay turnkey**: PCBWay sources every line by MPN (`exports/pcbway/BOM-PCBWay.csv`).
4. For the gates only: fit the TI alternates (pin-identical; `timing_margins.py --ti` keeps every margin positive) if their stock covers the build.
