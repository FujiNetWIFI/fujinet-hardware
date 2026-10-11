# FujiNet-ChannelF Rev0: sourcing (2026-10-11)

Stock read 2026-10-11T03:30:14-05:00 by `tools/audit/sourcing.py`: JLCPCB parts library via its own search API, LCSC via its product-detail API (raw answers in `analysis/sourcing/2026-10-11.json`). Quantities for 2 and 5 assembled boards; JLCPCB makes at least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, in USD, before assembly fees.

| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | LCSC lifecycle | Need (2 / 5) | Status | USD per board |
|---|---|---|---|---|---|---|---|---|---|---|
| C1,C10,C11,C12,C15,C36 | Samsung Electro-Mechanics CL21A226MAQNNNE | C45783 | 6 | 3690761 | basic | 185140 | normal | 12 / 30 | OK | 1.34 |
| C2,C3,C6,C9,C13,C14,C16,C17,C20,C21,C... | YAGEO CC0603KRX7R9BB104 | C14663 | 22 | 56334056 | basic | 4000 | normal | 44 / 110 | OK | 0.31 |
| C4,C23 | Samsung Electro-Mechanics CL10A106KP8NNNC | C19702 | 2 | 10370333 | basic | 1093280 | normal | 4 / 10 | OK | 0.06 |
| C5,C7,C18,C19,C30,C33 | Samsung Electro-Mechanics CL10A105KB8NNNC | C15849 | 6 | 8596676 | basic | 2290450 | normal | 12 / 30 | OK | 0.10 |
| C8 | Samsung Electro-Mechanics CL10A475KO8NNNC | C19666 | 1 | 2189705 | basic | 71410 | normal | 2 / 5 | OK | 0.03 |
| C22,C29 | Samsung Electro-Mechanics CL10C150JB8NNNC | C1644 | 2 | 958201 | basic | 204350 | normal | 4 / 10 | OK | 0.02 |
| D1 | Worldsemi WS2812B-2020-V6 | C52917434 | 1 | 988150 | extended | 974790 | normal | 2 / 5 | OK | 0.09 |
| D2 | Nexperia BAT54C,215 | C37704 | 1 | 275861 | preferred | 252500 | normal | 2 / 5 | OK | 0.02 |
| D3 | Hubei KENTO Elec KT-0603G | C12624 | 1 | 264031 | extended | 251800 | normal | 2 / 5 | OK | 0.01 |
| D4,D5,D6 | onsemi ESD5Z5.0T1G | C82044 | 3 | 373643 | extended | 369820 | normal | 6 / 15 | OK | 0.11 |
| D7,D8 | MDD (Microdiode Semiconductor) SS34 | C8678 | 2 | 4164415 | basic | 3319500 | normal | 4 / 10 | OK | 0.07 |
| J2 | Korean Hroparts Elec TYPE-C-31-M-12 | C165948 | 1 | 408716 | extended | 384415 | normal | 2 / 5 | OK | 0.19 |
| J3 | SOFNG TF-015 | C113206 | 1 | 22576 | extended | 22575 | normal | 2 / 5 | OK | 0.13 |
| L1 | Sunlord SWPA4030S6R8MT | C62684 | 1 | 16314 | extended | 0 | no LCSC record (JLC lists it) | 2 / 5 | OK | ? |
| Q1 | Jiangsu Changjing (JSCJ) 2N7002 | C8545 | 1 | 1311770 | basic | 700250 | normal | 2 / 5 | OK | 0.02 |
| R1,R2,R7,R13,R15,R20 | UNI-ROYAL 0603WAF1002T5E | C25804 | 6 | 26004432 | basic | 0 | normal | 12 / 30 | OK | 0.01 |
| R3,R4 | UNI-ROYAL 0603WAF5101T5E | C23186 | 2 | 24570320 | basic | 19482400 | normal | 4 / 10 | OK | 0.00 |
| R5,R6 | UNI-ROYAL 0603WAF3300T5E | C23138 | 2 | 3034657 | basic | 840200 | normal | 4 / 10 | OK | 0.01 |
| R8 | UNI-ROYAL 0603WAF2202T5E | C31850 | 1 | 3566038 | basic | 2334900 | normal | 2 / 5 | OK | 0.00 |
| R9 | UNI-ROYAL 0603WAF4702T5E | C25819 | 1 | 2204792 | basic | 0 | normal | 2 / 5 | OK | 0.00 |
| R10,R14,R16,R17 | UNI-ROYAL 0603WAF1001T5E | C21190 | 4 | 19307450 | basic | 0 | normal | 8 / 20 | OK | 0.01 |
| R11,R12 | UNI-ROYAL 0603WAF270JT5E | C25190 | 2 | 86940 | preferred | 0 | normal | 4 / 10 | OK | 0.00 |
| R18 | UNI-ROYAL 0603WAF4701T5E | C23162 | 1 | 20891443 | basic | 8624700 | normal | 2 / 5 | OK | 0.00 |
| R19 | UNI-ROYAL 0603WAF1003T5E | C25803 | 1 | 20968246 | basic | 11978600 | normal | 2 / 5 | OK | 0.00 |
| RN1 | UNI-ROYAL 4D03WGJ0103T5E | C29718 | 1 | 2108416 | basic | 1485600 | normal | 2 / 5 | OK | 0.01 |
| SW1 | E-Switch TL3342F160QG | C2886898 | 1 | 1579 | extended | 1570 | normal | 8 / 20 | OK | 1.05 |
| SW2 | E-Switch TL3342F160QG | C2886898 | 1 | 1579 | extended | 1570 | normal | 8 / 20 | OK | 1.05 |
| SW3 | E-Switch TL3342F160QG | C2886898 | 1 | 1579 | extended | 1570 | normal | 8 / 20 | OK | 1.05 |
| SW4 | E-Switch TL3342F160QG | C2886898 | 1 | 1579 | extended | 1570 | normal | 8 / 20 | OK | 1.05 |
| U1 | Espressif ESP32-S3-WROOM-1-N16R8 | C2913202 | 1 | 34522 | extended | 0 | normal | 2 / 5 | OK | 5.20 |
| U2 | Jiangsu Changjing (JSCJ) UMH3N | C62892 | 1 | 54488 | extended | 48510 | normal | 2 / 5 | OK | 0.05 |
| U3 | Silicon Labs CP2102N-A02-GQFN28R | C964632 | 1 | 36880 | extended | 36699 | normal | 2 / 5 | OK | 1.84 |
| U4 | Diodes Incorporated AP63203WU-7 | C780769 | 1 | 12759 | extended | 4911 | normal | 2 / 5 | OK | 1.19 |
| U5 | Raspberry Pi RP2040 | C2040 | 1 | 59391 | extended | 50612 | normal | 2 / 5 | OK | 1.00 |
| U6 | Winbond W25Q16JVSSIQ | C82317 | 1 | 1573 | extended | 1261 | normal | 2 / 5 | OK | 1.07 |
| U7 | Diodes Incorporated AP2112K-3.3TRG1 | C51118 | 1 | 29850 | extended | 29855 | normal | 2 / 5 | OK | 0.17 |
| U8,U9 | Texas Instruments SN74LVC4245APWR | C7859 | 2 | 118162 | preferred | 95751 | normal | 4 / 10 | OK | 0.79 |
| Y1 | Abracon ABM8-272-T3 | C20625731 | 1 | 9363 | extended | 9363 | normal | 2 / 5 | OK | 0.63 |

Parts cost per board (LCSC prices, 5-board quantities): **USD 18.66**, before JLC assembly, extended-part and Global Sourcing fees.

## Lifecycle

LCSC's product-cycle flag for every line: not "normal" for:

- SWPA4030S6R8MT C62684 (L1): no LCSC record (JLC lists it)

## Short at JLCPCB

Nothing: every assembled line is in JLCPCB stock for 5 boards.


For a short line, one of:

1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser by MPN, ship to JLC).
2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).
3. **A drop-in substitute** in stock at JLC (same footprint and pinout): change design.py, re-run `tools/build_all.sh` and the JLC rotation measurement.
