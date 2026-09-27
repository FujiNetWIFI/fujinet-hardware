#!/usr/bin/env bash
# Regenerate Fujiversal-Atari2600 Rev0 end to end: schematic, placed board,
# priority pre-route, Freerouting, finisher, checks, fabrication outputs.
# Needs KiCad 10, Java, and ~/.local/share/freerouting/freerouting-2.4.1.jar;
# check_nets.py reads the firmware from ~/Workspace/fn-2600 ($FUJINET_FIRMWARE).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/make_edge_fp.py
python3 tools/set_models.py >/dev/null 2>&1 || true   # library models (board may not exist yet)
python3 tools/gen_sch.py
python3 tools/gen_pcb.py
# core supply and crystal first (the RP USB pair is drawn by gen_pcb.py), short and locked, so the buses route around them
python3 tools/finish_route.py --nets=DVDD,XIN,XOUT,XOUT_Y --lock || true   # leftovers go to Freerouting
python3 tools/route.py --passes 20
python3 tools/finish_route.py
python3 tools/tidy_tracks.py     # drop router crumbs / fold-backs, merge, fix acute corners (DRC-checked)
python3 tools/set_models.py
python3 tools/check_nets.py
kicad-cli sch erc --severity-all --exit-code-violations Fujiversal-Atari2600-Rev0.kicad_sch -o /dev/null
kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations Fujiversal-Atari2600-Rev0.kicad_pcb -o /dev/null
python3 tools/export.py
