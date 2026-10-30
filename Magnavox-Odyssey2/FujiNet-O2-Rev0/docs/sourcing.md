# FujiNet-O2 Rev0: sourcing (2026-10-30)

Stock read 2026-10-30T15:51:19-05:00 by `tools/audit/sourcing.py`: JLCPCB parts library via its own search API, LCSC via its product-detail API (raw answers in `analysis/sourcing/2026-10-30.json`). Quantities for 2 and 5 assembled boards; JLCPCB makes at least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, in USD, before assembly fees.

| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | LCSC lifecycle | Need (2 / 5) | Status | USD per board |
|---|---|---|---|---|---|---|---|---|---|---|
| C1,C2,C3,C4,C5,C6,C8,C9,C10,C12,C15,C... | YAGEO CC0603KRX7R9BB104 | C14663 | 19 | 42216924 | basic | 599300 | normal | 38 / 95 | OK | 0.17 |
| C7,C11,C17 | Samsung Electro-Mechanics CL05B104KO5NNNC | C1525 | 3 | 35984475 | basic | 5548600 | normal | 6 / 15 | OK | 0.01 |
| C13,C25,C32 | Samsung Electro-Mechanics CL10A106KP8NNNC | C19702 | 3 | 11850268 | basic | 2628240 | normal | 6 / 15 | OK | 0.06 |
| C14,C18 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 2 | 2387920 | basic | 189900 | normal | 6 / 15 | OK | 0.03 |
| C19 | Samsung Electro-Mechanics CL05A475MP5NRNC | C23733 | 1 | 2387920 | basic | 189900 | normal | 6 / 15 | OK | 0.02 |
| C20,C21 | Samsung Electro-Mechanics CL10C150JB8NNNC | C1644 | 2 | 1052753 | basic | 306600 | normal | 4 / 10 | OK | 0.02 |
| C22,C34,C35,C38,C39 | Samsung Electro-Mechanics CL21A226MAQNNNE | C45783 | 5 | 3793753 | basic | 225120 | normal | 10 / 25 | OK | 0.97 |
| C24,C27,C31,C40,C41 | Samsung Electro-Mechanics CL10A105KB8NNNC | C15849 | 5 | 12319975 | basic | 0 | normal | 10 / 25 | OK | 0.07 |
| C30 | Samsung Electro-Mechanics CL10A475KO8NNNC | C19666 | 1 | 4250663 | basic | 1430020 | normal | 2 / 5 | OK | 0.02 |
| D1 | Hubei KENTO Elec KT-0603R | C2286 | 1 | 7287025 | basic | 4713200 | normal | 2 / 5 | OK | 0.01 |
| D2 | Nexperia BAT54C,215 | C37704 | 1 | 559872 | preferred | 518800 | normal | 2 / 5 | OK | 0.02 |
| D3 | Worldsemi WS2812B-2020-V6 | C52917434 | 1 | 704224 | extended | 666235 | normal | 2 / 5 | OK | 0.09 |
| J2 | SOFNG TF-015 | C113206 | 1 | 14707 | extended | 14705 | normal | 2 / 5 | OK | 0.13 |
| J3 | Korean Hroparts Elec TYPE-C-31-M-12 | C165948 | 1 | 283609 | extended | 266570 | normal | 2 / 5 | OK | 0.19 |
| L1 | Abracon AOTA-B201610S3R3-101-T | C42411119 | 1 | 519 | extended | 5 | normal | 2 / 5 | OK | 0.36 |
| L2 | Sunlord SWPA4030S6R8MT | C62684 | 1 | 13190 | extended | 0 | no LCSC record (JLC lists it) | 2 / 5 | OK | ? |
| R1,R2,R3,R4,R5,R6,R7,R8,R9,R10,R11,R1... | UNI-ROYAL 0603WAF3300T5E | C23138 | 28 | 3402296 | basic | 1134700 | normal | 56 / 140 | OK | 0.06 |
| R28,R34,R36,R38,R39,R49 | UNI-ROYAL 0603WAF1001T5E | C21190 | 6 | 31319698 | basic | 5647700 | normal | 12 / 30 | OK | 0.01 |
| R29,R31,R35,R37,R42,R43,R51 | UNI-ROYAL 0603WAF1002T5E | C25804 | 7 | 40316252 | basic | 778000 | normal | 14 / 35 | OK | 0.02 |
| R30 | UNI-ROYAL 0603WAF6800T5E | C23228 | 1 | 1874558 | basic | 1107200 | normal | 2 / 5 | OK | 0.00 |
| R32 | UNI-ROYAL 0603WAF1502T5E | C22809 | 1 | 3602551 | basic | 2032000 | normal | 2 / 5 | OK | 0.00 |
| R33 | UNI-ROYAL 0402WGF330JTCE | C25105 | 1 | 1949913 | basic | 0 | normal | 2 / 5 | OK | 0.00 |
| R40,R41 | UNI-ROYAL 0402WGF270JTCE | C25100 | 2 | 40972 | extended | 0 | normal | 4 / 10 | OK | 0.00 |
| R45,R46 | UNI-ROYAL 0603WAF5101T5E | C23186 | 2 | 21370458 | basic | 16193600 | normal | 4 / 10 | OK | 0.00 |
| R47 | UNI-ROYAL 0603WAF2202T5E | C31850 | 1 | 2918784 | basic | 1762000 | normal | 2 / 5 | OK | 0.00 |
| R48 | UNI-ROYAL 0603WAF4702T5E | C25819 | 1 | 3120611 | basic | 415700 | normal | 2 / 5 | OK | 0.00 |
| R50 | UNI-ROYAL 0603WAF3302T5E | C4216 | 1 | 3222392 | basic | 2417700 | normal | 2 / 5 | OK | 0.00 |
| RN1 | UNI-ROYAL 4D03WGJ0103T5E | C29718 | 1 | 1327091 | basic | 674900 | normal | 2 / 5 | OK | 0.01 |
| SW1 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1107578 | basic | 844760 | normal | 8 / 20 | OK | 0.02 |
| SW2 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1107578 | basic | 844760 | normal | 8 / 20 | OK | 0.02 |
| SW3 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1107578 | basic | 844760 | normal | 8 / 20 | OK | 0.02 |
| SW4 | XKB Connection TS-1187A-B-A-B | C318884 | 1 | 1107578 | basic | 844760 | normal | 8 / 20 | OK | 0.02 |
| U1 | Raspberry Pi RP2354B | C39843328 | 1 | 90 | extended | 0 | normal | 2 / 5 | OK | 1.53 |
| U2 | Espressif ESP32-S3-WROOM-1-N16R8 | C2913202 | 1 | 35183 | extended | 30131 | normal | 2 / 5 | OK | 5.40 |
| U3 | STMicroelectronics USBLC6-2SC6 | C7519 | 1 | 33481 | extended | 30835 | normal | 2 / 5 | OK | 0.18 |
| U4 | Silicon Labs CP2102N-A02-GQFN28R | C964632 | 1 | 37899 | extended | 37041 | normal | 2 / 5 | OK | 1.88 |
| U5 | Jiangsu Changjing (JSCJ) UMH3N | C62892 | 1 | 23475 | extended | 17610 | normal | 2 / 5 | OK | 0.05 |
| U6 | Texas Instruments TPS2116DRLR | C3235557 | 1 | 53431 | extended | 53608 | normal | 2 / 5 | OK | 0.40 |
| U7 | Diodes Incorporated AP63203WU-7 | C780769 | 1 | 4070 | extended | 0 | normal | 2 / 5 | OK | 1.20 |
| U8 | Diodes Incorporated AP2112K-3.3TRG1 | C51118 | 1 | 7454 | extended | 7260 | normal | 2 / 5 | OK | 0.18 |
| Y1 | Abracon ABM8-272-T3 | C20625731 | 1 | 0 | extended | 57 | normal | 2 / 5 | JLC short: LCSC has 57 | 0.66 |

Parts cost per board (LCSC prices, 5-board quantities): **USD 13.84**, before JLC assembly, extended-part and Global Sourcing fees.

## Lifecycle

LCSC's product-cycle flag for every line: not "normal" for:

- SWPA4030S6R8MT C62684 (L2): no LCSC record (JLC lists it)

## Short at JLCPCB

- **Abracon ABM8-272-T3** (C20625731, Y1): JLC 0, LCSC 57, need 5 for 5 boards.


For a short line, one of:

1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser by MPN, ship to JLC).
2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).
3. **A drop-in substitute** in stock at JLC (same footprint and pinout): change design.py, re-run `tools/build_all.sh` and the JLC rotation measurement.
