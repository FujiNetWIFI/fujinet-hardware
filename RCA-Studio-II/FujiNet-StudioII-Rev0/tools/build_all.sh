#!/usr/bin/env bash
# Regenerate FujiNet-StudioII Rev0 (schematic stage -- there is no board yet): footprints, the
# schematic from tools/design.py + tools/sch_layout.py with its drawing checks and netlist parity,
# KiCad ERC, the firmware cross-checks, then the BOMs and the schematic PDF.
# Needs KiCad 10, Python 3 and a C compiler (check_glue.py compiles the firmware's glue equations).
# check_nets.py / check_glue.py read pico/studio2 from $FUJINET_FIRMWARE (default
# ~/Workspace/fujinet-firmware); check_nets.py also reads the S3 board's pin map from
# $FUJINET_S2_BOARD (default ~/Workspace/fn-studio2-board) when it is there.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # the 22-pin Studio II edge footprint (edge_geom.py, PROVISIONAL)
python3 tools/make_fp_extra.py >/dev/null     # 1x03 header, TS-1187A
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 3 drawn sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-StudioII-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs s2_cart.h and the edge map (independent of design.py)
python3 tools/check_glue.py                   # the '541 enables and CART CS vs s2_glue_drive() / s2_glue_cartcs()
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF
