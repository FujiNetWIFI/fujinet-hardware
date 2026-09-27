#!/usr/bin/env bash
# Regenerate FujiNet-Astrocade Rev0 end to end: schematic, placed board,
# priority pre-route, Freerouting, finisher, checks, fabrication outputs.
# Takes ~30-40 min (Freerouting). Needs KiCad 10, Java, and
# ~/.local/share/freerouting/freerouting-2.4.1.jar.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/gen_sch.py
python3 tools/gen_pcb.py
# RP2354A misc, crystal and core-supply nets first, locked, so the bus routes around them
python3 tools/finish_route.py --nets=VBUS,XIN,XOUT,XOUT_Y,DVDD --lock || true   # leftovers go to Freerouting
python3 tools/route.py --passes 25
python3 tools/finish_route.py
python3 tools/tidy_tracks.py     # drop router crumbs / fold-backs, merge, fix acute corners (DRC-checked)
python3 tools/check_nets.py
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-Astrocade-Rev0.kicad_sch -o /dev/null
kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations FujiNet-Astrocade-Rev0.kicad_pcb -o /dev/null
python3 tools/export.py
