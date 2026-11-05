# FujiNet-ColecoVision Rev0: sourcing (2026-11-05)

Stock read 2026-11-05T05:40:24-06:00 by `tools/audit/sourcing.py`: JLCPCB parts library via its own search API, LCSC via its product-detail API (raw answers in `analysis/sourcing/2026-11-05.json`). Quantities for 2 and 5 assembled boards; JLCPCB makes at least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, in USD, before assembly fees.

| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | LCSC lifecycle | Need (2 / 5) | Status | USD per board |
|---|---|---|---|---|---|---|---|---|---|---|
| C1,C2,C3,C4,C8,C9,C10,C11,C20,C24,C27... | YAGEO CC0603KRX7R9BB104 | C14663 | 16 | 36377320 | basic | 0 | normal | 32 / 80 | OK | 0.16 |
| C5,C6,C7,C12,C17,C18 | Samsung Electro-Mechanics CL05B104KO5NNNC | C1525 | 6 | 32734474 | basic | 3236800 | normal | 12 / 30 | OK | 0.02 |
| C13,C26,C33 | Samsung Electro-Mechanics CL10A106KP8NNNC | C19702 | 3 | 10684366 | basic | 1579280 | normal | 6 / 15 | OK | 0.06 |
| C14,C16 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 2 | 1108013 | basic | 0 | normal | 8 / 20 | OK | 0.02 |
| C15,C19 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 2 | 1108013 | basic | 0 | normal | 8 / 20 | OK | 0.02 |
| C21,C22 | Samsung Electro-Mechanics CL10C150JB8NNNC | C1644 | 2 | 939084 | basic | 220050 | normal | 4 / 10 | OK | 0.02 |
| C23,C35,C36,C39,C40 | Samsung Electro-Mechanics CL21A226MAQNNNE | C45783 | 5 | 3525432 | basic | 0 | normal | 10 / 25 | OK | 0.93 |
| C25,C28,C32,C41,C42 | Samsung Electro-Mechanics CL10A105KB8NNNC | C15849 | 5 | 11841474 | basic | 450200 | normal | 10 / 25 | OK | 0.07 |
| C31 | Samsung Electro-Mechanics CL10A475KO8NNNC | C19666 | 1 | 4143746 | basic | 1307620 | normal | 2 / 5 | OK | 0.02 |
| D1 | Hubei KENTO Elec KT-0603R | C2286 | 1 | 6667363 | basic | 4208400 | normal | 2 / 5 | OK | 0.01 |
| D2 | Nexperia BAT54C,215 | C37704 | 1 | 420298 | preferred | 382500 | normal | 2 / 5 | OK | 0.02 |
| D3 | Worldsemi WS2812B-2020-V6 | C52917434 | 1 | 777098 | extended | 754650 | normal | 2 / 5 | OK | 0.09 |
| J2 | SOFNG TF-015 | C113206 | 1 | 13480 | extended | 13480 | normal | 2 / 5 | OK | 0.13 |
| J3 | Korean Hroparts Elec TYPE-C-31-M-12 | C165948 | 1 | 150169 | extended | 140190 | normal | 2 / 5 | OK | 0.19 |
| L1 | Abracon AOTA-B201610S3R3-101-T | C42411119 | 1 | 1 | extended | 0 | normal | 2 / 5 | JLC short: consign / Global Sourcing / PCBWay | 0.36 |
| L2 | Sunlord SWPA4030S6R8MT | C62684 | 1 | 894 | extended | 0 | no LCSC record (JLC lists it) | 2 / 5 | OK | ? |
| R1,R3,R7,R9,R14,R15,R23 | UNI-ROYAL 0603WAF1002T5E | C25804 | 7 | 43612502 | basic | 4906700 | normal | 14 / 35 | OK | 0.02 |
| R2 | UNI-ROYAL 0603WAF6800T5E | C23228 | 1 | 1802395 | basic | 993800 | normal | 2 / 5 | OK | 0.00 |
| R4 | UNI-ROYAL 0603WAF1502T5E | C22809 | 1 | 3373838 | basic | 1781700 | normal | 2 / 5 | OK | 0.00 |
| R5 | UNI-ROYAL 0402WGF330JTCE | C25105 | 1 | 3887121 | basic | 1064600 | normal | 2 / 5 | OK | 0.00 |
| R6,R8,R10,R11,R21 | UNI-ROYAL 0603WAF1001T5E | C21190 | 5 | 27863407 | basic | 2862900 | normal | 10 / 25 | OK | 0.01 |
| R12,R13 | UNI-ROYAL 0402WGF270JTCE | C25100 | 2 | 715057 | extended | 681100 | normal | 4 / 10 | OK | 0.00 |
| R16 | UNI-ROYAL 0603WAF3300T5E | C23138 | 1 | 2951437 | basic | 635900 | normal | 2 / 5 | OK | 0.00 |
| R17,R18 | UNI-ROYAL 0603WAF5101T5E | C23186 | 2 | 20526562 | basic | 15451500 | normal | 4 / 10 | OK | 0.00 |
| R19 | UNI-ROYAL 0603WAF2202T5E | C31850 | 1 | 2722249 | basic | 1592000 | normal | 2 / 5 | OK | 0.00 |
| R20 | UNI-ROYAL 0603WAF4702T5E | C25819 | 1 | 2554464 | basic | 7100 | normal | 2 / 5 | OK | 0.00 |
| R22 | UNI-ROYAL 0603WAF3302T5E | C4216 | 1 | 3053738 | basic | 2245100 | normal | 2 / 5 | OK | 0.00 |
| RN1,RN2,RN3,RN4 | UNI-ROYAL 4D03WGJ0331T5E | C12018 | 4 | 56110 | extended | 56100 | normal | 8 / 20 | OK | 0.09 |
| RN5,RN6 | UNI-ROYAL 4D03WGJ0103T5E | C29718 | 2 | 1211896 | basic | 612700 | normal | 4 / 10 | OK | 0.02 |
| SW1 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 977380 | basic | 743500 | normal | 6 / 15 | OK | 0.02 |
| SW2 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 977380 | basic | 743500 | normal | 6 / 15 | OK | 0.02 |
| SW3 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 977380 | basic | 743500 | normal | 6 / 15 | OK | 0.02 |
| U1 | Raspberry Pi RP2350A | C42411118 | 1 | 3481 | extended | 3481 | normal | 2 / 5 | OK | 1.30 |
| U2 | Texas Instruments SN74LVC1G11DBVR | C22046 | 1 | 23051 | extended | 23050 | normal | 2 / 5 | OK | 0.15 |
| U3 | Texas Instruments SN74LVC1G08DBVR | C7666 | 1 | 95849 | extended | 94700 | normal | 2 / 5 | OK | 0.05 |
| U4 | Texas Instruments SN74LVC245APWR | C7848 | 1 | 29563 | extended | 28730 | normal | 2 / 5 | OK | 0.28 |
| U5 | Winbond W25Q16JVUXIQ | C2843335 | 1 | 2877 | extended | 2253 | normal | 2 / 5 | OK | 1.59 |
| U6 | Espressif ESP32-S3-WROOM-1-N16R8 | C2913202 | 1 | 31132 | extended | 26659 | normal | 2 / 5 | OK | 5.41 |
| U7 | STMicroelectronics USBLC6-2SC6 | C7519 | 1 | 45548 | extended | 44985 | normal | 2 / 5 | OK | 0.16 |
| U8 | Silicon Labs CP2102N-A02-GQFN28R | C964632 | 1 | 34217 | extended | 33964 | normal | 2 / 5 | OK | 1.88 |
| U9 | Jiangsu Changjing (JSCJ) UMH3N | C62892 | 1 | 20956 | extended | 16210 | normal | 2 / 5 | OK | 0.05 |
| U10 | Texas Instruments TPS2116DRLR | C3235557 | 1 | 54523 | extended | 54538 | normal | 2 / 5 | OK | 0.39 |
| U11 | Diodes Incorporated AP63203WU-7 | C780769 | 1 | 0 | extended | 0 | normal | 2 / 5 | JLC short: consign / Global Sourcing / PCBWay | 1.20 |
| U12 | Diodes Incorporated AP2112K-3.3TRG1 | C51118 | 1 | 9216 | extended | 8830 | normal | 2 / 5 | OK | 0.18 |
| Y1 | Abracon ABM8-272-T3 | C20625731 | 1 | 6047 | extended | 5305 | normal | 2 / 5 | OK | 0.40 |

Parts cost per board (LCSC prices, 5-board quantities): **USD 15.38**, before JLC assembly, extended-part and Global Sourcing fees.

## Lifecycle

LCSC's product-cycle flag for every line: not "normal" for:

- SWPA4030S6R8MT C62684 (L2): no LCSC record (JLC lists it)

## Short at JLCPCB

- **Abracon AOTA-B201610S3R3-101-T** (C42411119, L1): JLC 1, LCSC 0, need 5 for 5 boards. Alternates: VLS201610HBX-3R3M-1 TDK C695624: JLC 343, LCSC 340.
- **Diodes Incorporated AP63203WU-7** (C780769, U11): JLC 0, LCSC 0, need 5 for 5 boards.


For a short line, one of:

1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser by MPN, ship to JLC).
2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).
3. **A drop-in substitute** in stock at JLC (same footprint and pinout): change design.py, re-run `tools/build_all.sh` and the JLC rotation measurement.
