# FujiNet-TRS80M1 Rev0: sourcing (2026-11-24)

Stock read 2026-11-24T20:49:08-06:00 by `tools/audit/sourcing.py`: JLCPCB parts library via its own search API, LCSC via its product-detail API (raw answers in `analysis/sourcing/2026-11-24.json`). Quantities for 2 and 5 assembled boards; JLCPCB makes at least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, in USD, before assembly fees.

| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | LCSC lifecycle | Need (2 / 5) | Status | USD per board |
|---|---|---|---|---|---|---|---|---|---|---|
| C1,C2,C3,C4,C5,C6,C7,C9,C10,C11,C12,C... | YAGEO CC0603KRX7R9BB104 | C14663 | 23 | 51492609 | basic | 1000400 | normal | 46 / 115 | OK | 0.13 |
| C8,C20,C32,C39 | Samsung Electro-Mechanics CL10A106KP8NNNC | C19702 | 4 | 9165268 | basic | 0 | normal | 8 / 20 | OK | 0.06 |
| C14,C18,C24 | Samsung Electro-Mechanics CL05B104KO5NNNC | C1525 | 3 | 31783584 | basic | 659200 | normal | 6 / 15 | OK | 0.01 |
| C21,C25 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 2 | 2952675 | basic | 2209700 | normal | 6 / 15 | OK | 0.02 |
| C26 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 1 | 2952675 | basic | 2209700 | normal | 6 / 15 | OK | 0.01 |
| C27,C28 | Samsung Electro-Mechanics CL10C150JB8NNNC | C1644 | 2 | 891977 | basic | 176700 | normal | 4 / 10 | OK | 0.02 |
| C29,C38,C41,C42 | Samsung Electro-Mechanics CL21A226MAQNNNE | C45783 | 4 | 4600413 | basic | 589200 | normal | 8 / 20 | OK | 0.44 |
| C31,C34,C43,C44 | Samsung Electro-Mechanics CL10A105KB8NNNC | C15849 | 4 | 11743247 | basic | 0 | normal | 8 / 20 | OK | 0.06 |
| C37 | Samsung Electro-Mechanics CL10A475KO8NNNC | C19666 | 1 | 3012305 | basic | 0 | normal | 2 / 5 | OK | 0.02 |
| D1 | Hubei KENTO Elec KT-0603R | C2286 | 1 | 8169076 | basic | 5496600 | normal | 2 / 5 | OK | 0.01 |
| D2 | Nexperia BAT54C,215 | C37704 | 1 | 417864 | preferred | 390150 | normal | 2 / 5 | OK | 0.01 |
| D3 | Worldsemi WS2812B-2020-V6 | C52917434 | 1 | 670186 | extended | 659190 | normal | 2 / 5 | OK | 0.09 |
| F1 | Brightking SMD1206B110TFT | C269119 | 1 | 98544 | extended | 96330 | normal | 2 / 5 | OK | 0.04 |
| J1 | XFCN BH254R-40P | C48603651 | 1 | 603 | extended | 603 | normal | 2 / 5 | OK | 0.29 |
| J3 | SOFNG TF-015 | C113206 | 1 | 28227 | extended | 27920 | normal | 2 / 5 | OK | 0.13 |
| J4 | Korean Hroparts Elec TYPE-C-31-M-12 | C165948 | 1 | 440228 | extended | 427390 | normal | 2 / 5 | OK | 0.19 |
| L1 | Abracon AOTA-B201610S3R3-101-T | C42411119 | 1 | 8698 | extended | 4160 | normal | 2 / 5 | OK | 0.32 |
| L2 | Sunlord SWPA4030S2R2MT | C36409 | 1 | 21773 | extended | 0 | no LCSC record (JLC lists it) | 2 / 5 | OK | ? |
| R1 | UNI-ROYAL 0603WAF4701T5E | C23162 | 1 | 18449855 | basic | 5314900 | normal | 2 / 5 | OK | 0.00 |
| R2,R3,R7,R9,R14,R15 | UNI-ROYAL 0603WAF1002T5E | C25804 | 6 | 40988308 | basic | 0 | normal | 12 / 30 | OK | 0.01 |
| R4 | UNI-ROYAL 0603WAF6800T5E | C23228 | 1 | 1259390 | basic | 386800 | normal | 2 / 5 | OK | 0.00 |
| R5 | UNI-ROYAL 0402WGF330JTCE | C25105 | 1 | 4328624 | basic | 1023600 | normal | 2 / 5 | OK | 0.00 |
| R6,R8,R10,R11,R21 | UNI-ROYAL 0603WAF1001T5E | C21190 | 5 | 38784481 | basic | 12337500 | normal | 10 / 25 | OK | 0.01 |
| R12,R13 | UNI-ROYAL 0402WGF270JTCE | C25100 | 2 | 564974 | extended | 441800 | normal | 4 / 10 | OK | 0.00 |
| R16 | UNI-ROYAL 0603WAF3300T5E | C23138 | 1 | 2344632 | basic | 0 | normal | 2 / 5 | OK | 0.00 |
| R17,R18 | UNI-ROYAL 0603WAF5101T5E | C23186 | 2 | 17630090 | basic | 12222400 | normal | 4 / 10 | OK | 0.00 |
| R19,R23 | UNI-ROYAL 0603WAF2202T5E | C31850 | 2 | 2120599 | basic | 755100 | normal | 4 / 10 | OK | 0.01 |
| R20 | UNI-ROYAL 0603WAF4702T5E | C25819 | 1 | 2797926 | basic | 125200 | normal | 2 / 5 | OK | 0.00 |
| R22 | UNI-ROYAL 0603WAF1003T5E | C25803 | 1 | 12440488 | basic | 3128800 | normal | 2 / 5 | OK | 0.00 |
| RN1,RN2,RN3,RN4,RN7,RN8,RN9,RN10 | UNI-ROYAL 4D03WGJ0104T5E | C1996 | 8 | 102137 | extended | 102100 | normal | 16 / 40 | OK | 0.07 |
| RN5,RN6 | UNI-ROYAL 4D03WGJ0750T5E | C25514 | 2 | 11383 | extended | 11350 | normal | 4 / 10 | OK | 0.02 |
| RN11,RN12 | UNI-ROYAL 4D03WGJ0103T5E | C29718 | 2 | 1231189 | basic | 557700 | normal | 4 / 10 | OK | 0.01 |
| SW1 | SHOU HAN 2.54-3P TPGT | C7421520 | 1 | 17805 | extended | 17334 | normal | 2 / 5 | OK | 0.53 |
| SW2 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 665840 | basic | 347640 | normal | 8 / 20 | OK | 0.02 |
| SW3 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 665840 | basic | 347640 | normal | 8 / 20 | OK | 0.02 |
| SW4 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 665840 | basic | 347640 | normal | 8 / 20 | OK | 0.02 |
| SW5 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 665840 | basic | 347640 | normal | 8 / 20 | OK | 0.02 |
| U1 | Raspberry Pi RP2354B | C39843328 | 1 | 10551 | extended | 9906 | normal | 2 / 5 | OK | 1.53 |
| U2,U3,U4 | Texas Instruments SN74LVC245APWR | C7848 | 3 | 47777 | extended | 47155 | normal | 6 / 15 | OK | 0.86 |
| U5 | Texas Instruments SN74LVC1G11DBVR | C22046 | 1 | 31478 | extended | 31475 | normal | 2 / 5 | OK | 0.16 |
| U6,U7 | Texas Instruments SN74LVC3G17DCTR | C18213 | 2 | 10520 | extended | 10169 | normal | 4 / 10 | OK | 1.46 |
| U8 | Texas Instruments SN74LVC2G07DCKR | C7849 | 1 | 25169 | extended | 25165 | normal | 2 / 5 | OK | 0.11 |
| U9 | Espressif ESP32-S3-WROOM-1-N16R8 | C2913202 | 1 | 36713 | extended | 0 | normal | 2 / 5 | OK | 5.35 |
| U10 | STMicroelectronics USBLC6-2SC6 | C7519 | 1 | 43836 | extended | 43835 | normal | 2 / 5 | OK | 0.15 |
| U11 | Silicon Labs CP2102N-A02-GQFN28R | C964632 | 1 | 28215 | extended | 26692 | normal | 2 / 5 | OK | 1.82 |
| U12 | Jiangsu Changjing (JSCJ) UMH3N | C62892 | 1 | 40983 | extended | 34780 | normal | 2 / 5 | OK | 0.05 |
| U13 | Texas Instruments TLV62569DBVR | C141836 | 1 | 460922 | extended | 457780 | normal | 2 / 5 | OK | 0.07 |
| U14 | Diodes Incorporated AP2112K-3.3TRG1 | C51118 | 1 | 15893 | extended | 15905 | normal | 2 / 5 | OK | 0.17 |
| Y1 | Abracon ABM8-272-T3 | C20625731 | 1 | 8545 | extended | 8545 | normal | 2 / 5 | OK | 0.40 |

Parts cost per board (LCSC prices, 5-board quantities): **USD 14.75**, before JLC assembly, extended-part and Global Sourcing fees.

## Lifecycle

LCSC's product-cycle flag for every line: not "normal" for:

- SWPA4030S2R2MT C36409 (L2): no LCSC record (JLC lists it)

## Short at JLCPCB

Nothing: every assembled line is in JLCPCB stock for 5 boards.


For a short line, one of:

1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser by MPN, ship to JLC).
2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).
3. **A drop-in substitute** in stock at JLC (same footprint and pinout): change design.py, re-run `tools/build_all.sh` and the JLC rotation measurement.
