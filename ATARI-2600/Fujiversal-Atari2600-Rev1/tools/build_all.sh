#!/usr/bin/env bash
# Regenerate Fujiversal-Atari2600 Rev1 end to end: schematic, checks, BOM; with
# LAYOUT=1 also the board, routing, DRC and the fab outputs.
# Needs KiCad 10, Python 3 (+ numpy), Java + Freerouting 2.4.1 for the board.
# check_nets.py reads the firmware headers from $FUJINET_FIRMWARE (default
# ~/Workspace/fn-2600, fujinet-firmware branch 2600-experiment).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 2x12 finger footprint (FujiPlusCart geometry)
python3 tools/make_fp_extra.py >/dev/null     # SOT-23-5, fiducial
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 4 drawn sheets, project symbols, netlist parity
kicad-cli sch erc --severity-all --exit-code-violations Fujiversal-Atari2600-Rev1.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs the fn-2600 firmware headers (independent of design.py)
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement, outline, fingers, RP core graft, fan-out, planes, rules
    bash tools/route_board.sh                 # pre-routes, Freerouting, finisher, stitching, DRC
fi
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF (+ CPL/gerbers/renders with a .kicad_pcb)
