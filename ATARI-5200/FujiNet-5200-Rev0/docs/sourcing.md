# FujiNet-5200 Rev0: sourcing (2026-10-08)

Stock read 2026-10-08T23:58:48-05:00 by `tools/audit/sourcing.py`: JLCPCB parts library via its own search API, LCSC via its product-detail API (raw answers in `analysis/sourcing/2026-10-08.json`). Quantities for 2 and 5 assembled boards; JLCPCB makes at least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, in USD, before assembly fees.

| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | Need (2 / 5) | Status | USD per board |
|---|---|---|---|---|---|---|---|---|---|
| C3,C11,C12,C21,C22,C23,C44,C45,C47,C48 | Samsung Electro-Mechanics CL21A226MAQNNNE | C45783 | 10 | 3799247 | basic | 419160 | 20 / 50 | OK | 2.22 |
| C1,C8,C33,C35 | Samsung Electro-Mechanics CL10A105KB8NNNC | C15849 | 4 | 9043045 | basic | 2605800 | 8 / 20 | OK | 0.06 |
| C7,C16,C25,C27 | Samsung Electro-Mechanics CL10A475KO8NNNC | C19666 | 4 | 2291829 | basic | 0 | 8 / 20 | OK | 0.12 |
| C30,C31 | Samsung Electro-Mechanics CL10C150JB8NNNC | C1644 | 2 | 1000054 | basic | 261700 | 4 / 10 | OK | 0.02 |
| C5,C24,C42,C51 | Samsung Electro-Mechanics CL10A106KP8NNNC | C19702 | 4 | 11324016 | basic | 2265780 | 8 / 20 | OK | 0.12 |
| C2,C4,C6,C9,C10,C13,C14,C15,C17,C18,C... | YAGEO CC0603KRX7R9BB104 | C14663 | 28 | 59183821 | basic | 4000 | 56 / 140 | OK | 0.39 |
| D1,D2,D3 | onsemi ESD5Z5.0T1G | C82044 | 3 | 380934 | extended | 376860 | 6 / 15 | OK | 0.11 |
| D4,D8 | MDD (Microdiode Semiconductor) SS34 | C8678 | 2 | 4264924 | basic | 3432820 | 4 / 10 | OK | 0.07 |
| D5,D9 | Nexperia BAT54C,215 | C37704 | 2 | 300874 | preferred | 282700 | 4 / 10 | OK | 0.04 |
| D6 | Worldsemi WS2812B-2020-V6 | C52917434 | 1 | 650573 | extended | 650570 | 2 / 5 | OK | 0.09 |
| D7 | Hubei KENTO Elec KT-0603R | C2286 | 1 | 6896781 | basic | 4586400 | 2 / 5 | OK | 0.01 |
| F1 | Littelfuse 1206L035/30WR | C2153989 | 1 | 3542 | extended | 3540 | 2 / 5 | OK | 0.33 |
| J2 | Korean Hroparts Elec TYPE-C-31-M-12 | C165948 | 1 | 411942 | extended | 389360 | 2 / 5 | OK | 0.19 |
| J3 | SOFNG TF-015 | C113206 | 1 | 22905 | extended | 22905 | 2 / 5 | OK | 0.13 |
| L1 | Sunlord SWPA4030S6R8MT | C62684 | 1 | 17915 | extended | 0 | 2 / 5 | OK | ? |
| L2 | Abracon AOTA-B201610S3R3-101-T | C42411119 | 1 | 347 | extended | 5 | 2 / 5 | OK | 0.29 |
| L3 | Sunlord SWPA4030S4R7MT | C57269 | 1 | 31056 | extended | 0 | 2 / 5 | OK | ? |
| Q3 | Alpha & Omega Semiconductor AO3401A | C15127 | 1 | 763924 | basic | 267460 | 2 / 5 | OK | 0.10 |
| R1,R2 | UNI-ROYAL 0603WAF5101T5E | C23186 | 2 | 24849314 | basic | 20083800 | 4 / 10 | OK | 0.00 |
| R11 | UNI-ROYAL 0603WAF4702T5E | C25819 | 1 | 1673778 | basic | 0 | 2 / 5 | OK | 0.00 |
| R12 | UNI-ROYAL 0603WAF330JT5E | C23140 | 1 | 5439050 | basic | 3188400 | 2 / 5 | OK | 0.00 |
| R4,R5,R6,R13,R21 | UNI-ROYAL 0603WAF1002T5E | C25804 | 5 | 27822314 | basic | 0 | 10 / 25 | OK | 0.01 |
| R16,R17 | UNI-ROYAL 0603WAF270JT5E | C25190 | 2 | 73462 | preferred | 0 | 4 / 10 | OK | 0.00 |
| R19 | UNI-ROYAL 0603WAF3300T5E | C23138 | 1 | 3119079 | basic | 1073100 | 2 / 5 | OK | 0.00 |
| R9,R14,R15,R18,R20 | UNI-ROYAL 0603WAF1001T5E | C21190 | 5 | 20120865 | basic | 0 | 10 / 25 | OK | 0.01 |
| R3,R22,R25,R29 | UNI-ROYAL 0603WAF4701T5E | C23162 | 4 | 21495842 | basic | 9798100 | 8 / 20 | OK | 0.01 |
| R10,R27 | UNI-ROYAL 0603WAF2202T5E | C31850 | 2 | 3616459 | basic | 2439500 | 4 / 10 | OK | 0.01 |
| R7,R8,R23,R28 | UNI-ROYAL 0603WAF1003T5E | C25803 | 4 | 21357023 | basic | 12812900 | 8 / 20 | OK | 0.01 |
| R30 | YAGEO RC0603FR-072R2L | C112307 | 1 | 469181 | extended | 469100 | 2 / 5 | OK | 0.01 |
| RN1 | UNI-ROYAL 4D03WGJ0103T5E | C29718 | 1 | 2170225 | basic | 1574700 | 2 / 5 | OK | 0.01 |
| SW1 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 433962 | basic | 160340 | 8 / 20 | OK | 0.02 |
| SW2 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 433962 | basic | 160340 | 8 / 20 | OK | 0.02 |
| SW3 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 433962 | basic | 160340 | 8 / 20 | OK | 0.02 |
| SW4 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 433962 | basic | 160340 | 8 / 20 | OK | 0.02 |
| U1 | Espressif ESP32-S3-WROOM-1-N16R8 | C2913202 | 1 | 26828 | extended | 3 | 2 / 5 | OK | 5.20 |
| U2 | Silicon Labs CP2102N-A02-GQFN28R | C964632 | 1 | 37326 | extended | 37326 | 2 / 5 | OK | 1.84 |
| U3 | Jiangsu Changjing (JSCJ) UMH3N | C62892 | 1 | 54323 | extended | 49250 | 2 / 5 | OK | 0.05 |
| U4 | Diodes Incorporated AP63203WU-7 | C780769 | 1 | 13312 | extended | 4634 | 2 / 5 | OK | 1.19 |
| U5 | Raspberry Pi RP2354B | C39843328 | 1 | 1627 | extended | 1627 | 2 / 5 | OK | 1.55 |
| U6 | Diodes Incorporated AP2112K-3.3TRG1 | C51118 | 1 | 30995 | extended | 31010 | 2 / 5 | OK | 0.17 |
| U7 | Texas Instruments SN74HCT541PWR | C436096 | 1 | 25816 | extended | 25816 | 2 / 5 | OK | 0.51 |
| U8 | Texas Instruments SN74HCT08DR | C6767 | 1 | 1795 | extended | 1795 | 2 / 5 | OK | 0.43 |
| U9 | Texas Instruments SN74HCT14DR | C6769 | 1 | 16369 | extended | 16249 | 2 / 5 | OK | 0.52 |
| U10 | Diodes Incorporated AP63205WU-7 | C2071056 | 1 | 31957 | extended | 24869 | 2 / 5 | OK | 0.42 |
| U11 | Nexperia 74LVC1G17GW,125 | C426705 | 1 | 18420 | extended | 18130 | 2 / 5 | OK | 0.11 |
| Y1 | Abracon ABM8-272-T3 | C20625731 | 1 | 9889 | extended | 9889 | 2 / 5 | OK | 0.63 |

Parts cost per board (LCSC prices, 5-board quantities): **USD 17.07**, before JLC assembly, extended-part and Global Sourcing fees.

## Short at JLCPCB

Nothing: every assembled line is in JLCPCB stock for 5 boards.


For a short line, one of:

1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser, ship to JLC; `exports/jlcpcb/consigned.csv` lists them).
2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).
3. **PCBWay turnkey**: PCBWay sources every line by MPN (`exports/pcbway/BOM-PCBWay.csv`).
