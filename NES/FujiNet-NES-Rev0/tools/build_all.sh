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
python3 tools/gen_sch.py                      # design.py -> root + 4 sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-NES-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py
    python3 tools/finish_route.py --nets=VBUS,XIN,XOUT,XOUT_Y,DVDD --lock || true   # locked pre-routes
    python3 tools/route.py --passes 25
    python3 tools/finish_route.py
    python3 tools/tidy_tracks.py
    python3 tools/set_models.py
    kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations FujiNet-NES-Rev0.kicad_pcb -o /dev/null
fi
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF (+ CPL/gerbers/renders with a .kicad_pcb)
