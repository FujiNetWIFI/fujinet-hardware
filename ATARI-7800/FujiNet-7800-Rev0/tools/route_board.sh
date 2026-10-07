#!/usr/bin/env bash
# Route the freshly generated FujiNet-7800-Rev0.kicad_pcb (tools/gen_pcb.py) and
# finish it: the RP2354B corner pre-route, Freerouting, the grid A* finisher for
# what it leaves, clean-up, GND stitching, 3D models, silkscreen, and the DRC
# gate.  Called by build_all.sh (LAYOUT=1).
# PASSES sets Freerouting's pass budget, STRATEGY its -us option; the defaults (12, hybrid) are what
# routed the committed board (2026-10-07: five variants, design review Part 2).
set -euo pipefail
cd "$(dirname "$0")/.."
PCB=FujiNet-7800-Rev0.kicad_pcb
# the core regulator and the crystal on the empty board, locked (the SWD pads sit in the
# bring-up block in the upper body, far from the RP: SWCLK / SWDIO are Freerouting's)
python3 tools/finish_route.py --nets=RP_LX,DVDD,VREG_AVDD,XIN,XOUT,XOUT_Y --lock || true
python3 tools/route.py --passes "${PASSES:-12}" --strategy "${STRATEGY:-hybrid}"
python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
python3 tools/finish_route.py || true
python3 tools/drc_fix.py                  # again: a rip-up transaction can leave a crossing behind
python3 tools/finish_route.py || true
python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'
python3 tools/tidy_tracks.py
python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
python3 tools/check_vias.py               # before any pcbnew save re-nets a via that sits in a foreign pad
python3 tools/set_models.py
python3 tools/fix_silk.py                 # refs off pads/other silk (nearest clear spot, else hidden)
kicad-cli pcb drc --refill-zones --schematic-parity --severity-error --exit-code-violations $PCB -o /dev/null
