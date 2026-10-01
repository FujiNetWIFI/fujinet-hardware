#!/usr/bin/env bash
# Regenerate FujiNet-NES Rev0: schematic, checks, BOM.  The layout stage
# (gen_pcb / finish_route / route / tidy_tracks, gerbers) is NOT done for this
# board yet -- those scripts are unadapted Astrocade copies; see README.md.
# Needs KiCad 10 and Python 3.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 72-pin edge footprint
python3 tools/gen_sch.py                      # design.py -> root + 4 sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-NES-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF (CPL/gerbers once a .kicad_pcb exists)
