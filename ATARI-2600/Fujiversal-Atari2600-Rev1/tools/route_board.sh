#!/usr/bin/env bash
# Route the freshly generated Fujiversal-Atari2600-Rev1.kicad_pcb (tools/gen_pcb.py) and
# finish it: Freerouting, the grid A* finisher for what it leaves, clean-up, GND
# stitching, 3D models, silkscreen, and the DRC gate.  Called by build_all.sh (LAYOUT=1).
# PASSES (default 20) sets Freerouting's pass budget.
set -euo pipefail
cd "$(dirname "$0")/.."
PCB=Fujiversal-Atari2600-Rev1.kicad_pcb
python3 tools/route.py --passes "${PASSES:-20}"
python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
python3 tools/finish_route.py || true
python3 tools/drc_fix.py                  # again: a rip-up transaction can leave a crossing behind
python3 tools/finish_route.py || true
python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'
python3 tools/tidy_tracks.py
python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
python3 tools/set_models.py
python3 tools/fix_silk.py                 # refs off pads/other silk (nearest clear spot, else hidden)
kicad-cli pcb drc --refill-zones --schematic-parity --severity-error --exit-code-violations $PCB -o /dev/null
