#!/usr/bin/env bash
# Regenerate FujiNet-5200 Rev0: footprints, sheets, ERC, the firmware
# cross-checks; with LAYOUT=1 also the board (placement, routing, DRC with
# schematic parity); then BOM, CPL, gerbers, schematic PDF and layout views.
# Needs KiCad 10, Python 3 (+ numpy), a C compiler (check_glue.py compiles the
# firmware's glue equation) and, for the board, Java + Freerouting 2.4.1.
# check_nets.py / check_glue.py read pico/atari-5200 from $FUJINET_FIRMWARE
# (default ~/Workspace/fujinet-firmware, branch add-5200) and the S3 pin map
# from $FUJINET_A52_BOARD (default ~/Workspace/fn-5200-board).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # the 36-pin 5200 edge footprint (edge_geom.py)
python3 tools/make_fp_extra.py >/dev/null     # 1x03 header, TS-1187A, the bridged solder jumper
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 5 drawn sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-5200-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
python3 tools/check_glue.py                   # the '541 enable glue vs a52_glue_drive(), every input combination
python3 tools/audit/edge_orientation.py >/dev/null   # the edge footprint vs the cartridge sources
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement.py + design.py -> the placed board, planes, fan-in, case anchors
    bash tools/route_board.sh                 # pre-route, Freerouting, finisher, stitching, check_vias, DRC gate
fi
python3 tools/export.py                       # BOM, schematic PDF (+ JLCPCB / PCBWay packages, layout views, renders with a .kicad_pcb)
if [ -f exports/jlcpcb/FujiNet-5200-Rev0-gerbers.zip ]; then
    python3 tools/tab_overlay.py              # docs/tab-overlay-1to1.pdf
    python3 tools/audit/check_fab.py          # the packages: BOM / CPL / centroid vs design.py, the order-number spot
    python3 tools/audit/check_gerbers.py >/dev/null   # the fab zips: fingers both faces, mask windows, nothing in the tab
fi
