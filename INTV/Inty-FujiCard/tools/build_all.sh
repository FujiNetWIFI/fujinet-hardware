#!/usr/bin/env bash
# Regenerate Inty-FujiCard end to end and run every gate.
#
# CONVERT=1 first brings Yannick Erb's EasyEDA board (Original/PCB_*.json) to KiCad again
# (tools/convert.py: copper unchanged, fills from the JSON, never refilled), points its footprints at
# the bundled 3D models and re-reads its netlist; without it the board is kept as it is.  Then: the
# schematic from tools/design.py + tools/sch_layout.py (checked against the board's netlist, ERC, the
# firmware), the board's metadata from the schematic (tools/sync_board.py: names only, copper hash
# checked), DRC with schematic parity, the BOMs / CPL / gerbers / docs, and the fab gates against
# Yannick's own gerbers, BOM and pick-and-place file.
# Needs KiCad 10 and Python 3 with numpy, scipy and pycairo.  check_nets.py reads fujinet-firmware
# from $FUJINET_FIRMWARE (default ~/Workspace/fujinet-firmware) at $FUJINET_FIRMWARE_REF (default
# origin/master).  tools/audit/sourcing.py (network) is run by hand on order day.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
if [ "${CONVERT:-0}" = 1 ]; then
    python3 tools/convert.py                  # JSON -> Inty-FujiCard.kicad_pcb + .pretty (+ .kicad_pro)
    python3 tools/set_models.py               # the bundled 3D models (3d/, tools/fetch_models.py)
    python3 tools/board_netlist.py            # the board's netlist -> tools/board_netlist.json
fi
python3 tools/board_netlist.py --check        # design.py = the board's netlist
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/gen_sch.py                      # root + 5 drawn sheets, project symbols, netlist parity
kicad-cli sch erc --severity-all --exit-code-violations Inty-FujiCard.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # the netlist vs the firmware (independent of design.py)
python3 tools/sync_board.py                   # schematic -> board: names, fields, paths (copper hash checked)
python3 tools/audit/check_drc.py              # DRC + parity on the saved fills, the waived warnings only
python3 tools/export.py                       # BOMs, CPL, centroid, gerber zips, ORDER files, PDFs, renders
python3 tools/audit/gerber_equiv.py exports/pcbway/Inty-FujiCard-gerbers.zip | tail -1   # = Yannick's gerbers
python3 tools/audit/check_fab.py | tail -1    # = Yannick's BOM and pick-and-place; the zips
