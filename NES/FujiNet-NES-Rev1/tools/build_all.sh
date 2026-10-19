#!/usr/bin/env bash
# Regenerate FujiNet-NES Rev1 end to end: schematic, checks, BOM; then (once
# the layout stage is enabled below) the board, routing, DRC and fab outputs.
# Needs KiCad 10, Python 3 (+ numpy), Java + Freerouting 2.4.1 for the board.
# check_nets.py reads the firmware headers from $FUJINET_FIRMWARE (default
# ~/Workspace/fujinet-firmware); the Rev1 contract (nes_bus.h, nes_cart.h,
# nes_ppu.h) lives on fujinet-firmware branch simplify-nes.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
cd "$(dirname "$0")/.."
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 72-pin edge footprint (measured NES-EWROM-01 geometry)
python3 tools/make_fp_extra.py >/dev/null     # SOT-23-5, SOIC-8
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 6 drawn sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-NES-Rev1.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement.py + design.py -> the placed board, planes, fan-out, case anchors
    bash tools/route_board.sh                 # pre-routes, Freerouting, finisher, stitching, check_vias, fills, DRC gate
fi
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF (+ CPL/gerbers/renders with a .kicad_pcb)
if [ -f exports/jlcpcb/FujiNet-NES-Rev1-gerbers.zip ]; then
    python3 tools/audit/check_plane_shorts.py   # the zip: no plated hole in an inner pour of another net
    python3 tools/audit/check_gerbers.py >/dev/null   # the zip: 36 fingers a face, mask windows, nothing on the tab
fi
