#!/usr/bin/env bash
# Regenerate FujiNet-NES Rev0 end to end: schematic, checks, BOM; then (once
# the layout stage is enabled below) the board, routing, DRC and fab outputs.
# Needs KiCad 10, Python 3 (+ numpy), Java + Freerouting 2.4.1 for the board.
# check_nets.py reads the firmware headers from $FUJINET_FIRMWARE; the NES
# contract lives on fujinet-firmware branch nes-bringup (worktree ~/Workspace/fn-nes).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${FUJINET_FIRMWARE:-}" ] && [ -d "$HOME/Workspace/fn-nes/pico/nes" ]; then
    export FUJINET_FIRMWARE="$HOME/Workspace/fn-nes"
fi
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 72-pin edge footprint (measured NES-EWROM-01 geometry)
python3 tools/make_fp_extra.py >/dev/null     # SOT-23-5, SOIC-8
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 7 drawn sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-NES-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py
    # locked pre-routes on the empty board: the PPU bus (fingers -> CHR SRAM, which Freerouting
    # never reached in 8 passes), the CIC and console-5V fingers, then the RP corner nets;
    # VBUS stays Freerouting's (its P-FET gate run crosses the board)
    # PA10-12 sit on the RP's east (CPU-side) column by the firmware pin map and must cross the CPU
    # bus to the west fingers: routed first, on the empty board.  Order matters at 0.4 mm pitch:
    # PA11 (pin 28) before PA10 (pin 27) -- the other way round PA10's via blocks PA11.  CA13/CA14
    # (pins 25/26, between the same IOVDD pins 24/29 -- see fanout.FAR_VIA) go first of all
    PPU=CA13,CA14,PA11,PA10,PA12,PA0,PA1,PA2,PA3,PA4,PA5,PA6,PA7,PA8,PA9,PA13,PD0,PD1,PD2,PD3,PD4,PD5,PD6,PD7,PPU_RD_N,PPU_WR_N,PA13_N,CIRAM_A10,CIRAM_CE_N
    python3 tools/finish_route.py --nets=$PPU,CIC_CLK,CIC_RST,CIC_TOPAK,CIC_TOMB,CONS_5V || true   # unlocked: Freerouting may still adjust them
    # RP corner + crystal + SWD (SWDIO, the northern pin, before SWCLK: routed the other way round
    # SWCLK's track crosses SWDIO's lane end at the pin) + the links later stages left open on
    # this placement: CD3 (pin 16, beside the IOVDD pin 15 fan-out) and the '595 lines from the
    # RP's north-east corner
    python3 tools/finish_route.py --nets=RP_LX,DVDD,VREG_AVDD,XIN,XOUT,XOUT_Y,SWDIO,SWCLK,CD3,SR_SER,SR_SCK,SR_RCK --lock || true
    python3 tools/route.py --passes 8
    python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
    python3 tools/finish_route.py || true
    python3 tools/drc_fix.py                  # again: a rip-up transaction can leave a crossing behind
    python3 tools/finish_route.py || true
    python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'   # last links at 0.15 mm
    python3 tools/tidy_tracks.py
    python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
    python3 tools/set_models.py
    python3 tools/fix_silk.py                 # refs off pads/other silk (nearest clear spot, else hidden)
    kicad-cli pcb drc --refill-zones --schematic-parity --severity-error --exit-code-violations FujiNet-NES-Rev0.kicad_pcb -o /dev/null
fi
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF (+ CPL/gerbers/renders with a .kicad_pcb)
