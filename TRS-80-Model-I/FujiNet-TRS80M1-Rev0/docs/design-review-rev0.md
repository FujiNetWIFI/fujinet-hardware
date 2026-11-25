# FujiNet-TRS80M1 Rev0: design review

Reviewed 2026-11-24 against the routed board (686 vias, 1678 tracks), with:
- this project's own gates (`tools/build_all.sh`);
- kicad-happy 2.2.1 (`tools/audit/run_sch_audit.sh`, `run_pcb_audit.sh`);
- KiCad's ERC and DRC through kicad-cli and the KiCad MCP;
- ngspice (`tools/audit/spice/ribbon.py`).

## 1. What the board has to get right, and how it is checked

| Claim | Check | Result |
|---|---|---|
| Header pin h carries the Model I's edge pin h+1 (h odd) or h-1 (h even): a straight IDC ribbon swaps Tandy's pairs, because Fig. 22 is the mirror of the IDC connector | `tools/audit/header_pinout.py`: the netlist against four independent sources (Tech Ref 26-2103 p.91, the RetroStack rev G replica, the 26-1132 HD-adapter document, TRS-IO M1); the pair swap derived from Fig. 22 and checked against the HD adapter's cable table and TRS-IO M1's pad numbers; the footprint against its EasyEDA original, pin 1 at the south end | 0 failures |
| Edge pin 39 (header 40) is open (+5V on keyboard boards A-E, GND on G); grounds are edge 8, 29, 37 (header 7, 30, 38) | the same | ok |
| Every line reaches the RP through exactly its buffer, on the firmware's GPIO | `tools/check_nets.py` against `m1_card.h`, `fujitrs80m1_rp2354b.h` and `fujiversal-trs80m1.h` in the dev tree (sha256 printed) | 461 checks, 0 failed, 4 NOTEs (firmware changes, README) |
| Every bus input defined with the ribbon unplugged, idling inactive | `check_nets.py`: a 100k pull-up to +3V3_RP on each of the 30 inputs; none on INT* / WAIT* (the Z80's own 4.7k pull-ups) | ok |
| The data buffer drives only while RD* or IN* is low | `check_nets.py`: /OE = 74LVC1G11(DRIVE, the BUFFERED RD*, the BUFFERED IN*); DIR = DRIVE with 4.7k down | ok |
| A ringing strobe never counts twice | `spice/ribbon.py`: LS367 -> 15 / 45 cm ribbon -> 74LVC3G17. The input never re-crosses the other Schmitt threshold (lowest high 2.66 V vs VT- 0.84 V; highest low 0.94 V vs VT+ 2.22 V at 45 cm) | ok |
| The card's data drive is clean on the ribbon | `spice/ribbon.py`, swept over the series resistor. At 75R: peak 3.30 V at 15 cm, 3.45 V / -0.15 V at 45 cm, settled by 13 ns. At 47R and 45 cm it was 3.94 / -0.64 V, which is why 75R | ok |
| Levels, loads, contention, read timing, power | `tools/audit/margins.py` | 27 margins, 0 negative |
| Layout claims on the copper | `tools/audit/layout_checks.py` | 69 checks, 0 failures |

Margin highlights:
- **Strobe high level:** LS367 VOH 2.7 V vs the 3G17's VT+ max 2.22 V at 3.6 V: +0.48 V.
- **Read timing:** the stock 1.774 MHz read has 600 ns of budget against 464 ns worst case: +136 ns.
  - 2.66 / 3.55 MHz speed-ups are met only when no FD1771 post lands as the strobe falls, as the firmware README says (+164 / +23 ns typical).
- **Contention at the end of a read:** 31 mA through the 75R for at most ~52 ns, inside the LVC245's 50 mA.
- **Load per line:** the card asks at most 41 uA of an LS367 driving low (12 mA available).
- **Unanswered reads stay FFh:** the LS inputs float high and the card's pull-ups agree.
- **Back-feed:** with the Model I on and the card unpowered, the 30 pull-ups carry ~1.2 mA into +3V3_RP, under 2 % of its running draw.

## 2. kicad-happy findings (run 2026-11-25_1315 after the header fix, 225 findings in 53 rule groups; the same high groups as 2026-11-24_2050)

**High**
- **TS-001: the AP2112K (U14) at Tj 142 C.** The analyzer assumes 275 mA out of it. Its loads are the RP2354B (~60 mA at 200 MHz) and the seven bus buffers (~10 mA): (5.25 - 3.3) V x 70 mA = 0.14 W, +26 C at the datasheet's 184 C/W. Not a defect (`margins.py`).
- **GP-001 (5): header-side bus lines with 50-78 % reference-plane coverage over 7-21 mm** (M1_D2, M1_DS2, M1_D0, M1_D5, M1_A0; M1_D3 before the header fix's re-route). The box header's 40 clearance holes interrupt In1 / In2 beside the header. Each line runs a few mm on the board after 150 mm of ribbon with three grounds in 40 wires. Accepted.
- **RP-001: USB_DP has two layer changes without a GND via within 1 mm.** It is a 12 Mb/s full-speed link (edges 4-20 ns). The same was accepted on the sibling carts.
- **PM-002: J1's courtyard overhangs the edge by 0.74 mm.** By design: the box header's mouth stands 0.24 mm past the west edge, flush with the case wall.
- **KO-001 (7): FID1-3 and the holes "inside" their keep-outs.** The analyzer tests the circles' bounding boxes; each part sits in its own clear circle, and KiCad DRC passes.
- **DC-002: no decoupling near U12.** The UMH3N is a pre-biased transistor pair with no supply pin.

**Warnings**
- **RP-001 (18): bus lines change layer without a GND via within 1 mm.** Logic edges of 2-6 ns over a few cm, on a board whose In1 is solid GND. The return paths worth caring about are the ribbon's, and the Schmitt receivers cover those.
- **GP-001 (15): partial plane gaps.** Same cause as above (header and RP-ring antipads). Accepted.
- **CC-002 (11): 0.15 mm necks.** Where the 0.65 / 0.4 mm-pitch pins need them; logic currents. JLCPCB's minimum is 0.09 mm.
- **CK-001 / CK-003: SD_SCK on an outer layer, near the microSD.** It is the microSD's own clock, on the way to its socket.
- **GP-005: two ground domains.** Raspberry Pi's regulator corner keeps its PGND pour separate and joins main GND through its own vias, as their minimal design says (RP2350 datasheet 6.3.8.1).
- **PU-001: CP2102N CHREN.** A battery-charger detection output, unused, left open as on the sibling carts.
- **RS-001: VBUS_SNS has no source.** It is a divider node (22k / 47k).
- **SW-001: buck harmonics in the FM band.** The TLV62569 runs at 1.5 MHz; check at bring-up if a radio sits nearby.
- **TE-001: 7 of 188 nets on test pads.** The bus has the logic-analyser header (DNP) instead: one plug for every strobe and control.
- **GR-004: paste on 44 % of the copper flashes.** The THT pads and the vias carry no paste.

**Info (no action):**
- AH-001: the header taken for a "headphone jack".
- EP-AUD: no ESD parts on the header. It is the Model I's own bus; LVC inputs are 2 kV HBM with Ioff.
- CG-AUD: 12:1 signal-to-ground ratio. The Model I's edge has three grounds in 40 pins.
- PS-002: the +3V3_RP / VBUS "plane splits". +3V3_RP is an In2 island plus the RP's F.Cu rings; VBUS is the connector and its ESD.
- The rest are detections.

## 3. Rev0 compromises

- **One schematic crossing on m1-bus.** The OE gate takes both buffered RD* and IN* from below. Every arrangement puts one of them past the other, because both run from the strobe buffer to the RP. A bus would avoid it but break the wires-only rule.
- **C_DB moved after routing.** The data buffer's 100 nF was 8.4 mm from its VCC pin in the routed variant. It was moved to 2.1 mm by hand: one F.Cu stub to the pin's own plane via, and a GND via. `placement.py` carries the new spot, so `LAYOUT=1` puts it there.
- **The board is not reproduced by `LAYOUT=1`.** Routing varies run to run. This board is placement variant vB of five run in parallel (rsync + TMPDIR each): the SWD pads in a row south of the crystal, the debug pads and the LED east of the RP. Only vB closed every connection.
- **The S3 module's silkscreen** stands at the flush east edge: three KiCad silk-edge warnings, as on the sibling carts.
- **A long ribbon is the user's.** `spice/ribbon.py` is clean to 45 cm with 75R, but at 45 cm the strobes undershoot to -1.8 V into the LVC clamp diodes (the LS367's output resistance limits the current). The README asks for 15 cm (Tandy's EI cable was 6 in) and no more than 30.

## 4. Not verifiable here

- Bus timing and contention on real silicon, and the keyboard unit's buffer turnaround: these wait for a Model I and a logic analyser. The LA header puts every strobe and the buffer controls on one 2x10.
- The DIP switch's ON side: the silkscreen's ON follows the EasyEDA footprint's marks. Check it against the delivered part before trusting the legend.
- The case: nothing was printed or measured (`case/case-spec.md`, VERIFY).
