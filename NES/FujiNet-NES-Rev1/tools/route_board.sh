#!/usr/bin/env bash
# Route the freshly generated FujiNet-NES-Rev1.kicad_pcb (tools/gen_pcb.py) and
# finish it: locked pre-routes, Freerouting, the grid A* finisher for what it
# leaves, clean-up, GND stitching, the via gate, the saved zone fills, 3D models,
# silkscreen and the DRC gate.  Called by build_all.sh (LAYOUT=1).
# PASSES sets Freerouting's pass budget (default 12), STRATEGY its -us option (default:
# none, Freerouting's own greedy).  PREROUTE overrides the locked pre-route list.
# Parallel variants: run each in its own copy of the project with its own TMPDIR (the tools
# keep their scratch files in the temp directory under fixed names).
set -euo pipefail
cd "$(dirname "$0")/.."
PCB=FujiNet-NES-Rev1.kicad_pcb
# each RP's core regulator, crystal and SWD pads on the empty board, locked (Rev0's corner set,
# twice).  SWDIO (pin 34, the northern one) before SWCLK: their pads are north-east of the pins
# and the other way round SWCLK's track crosses SWDIO's lane end at the pin
CORNERS=RP_LX,DVDD,VREG_AVDD,XIN,XOUT,XOUT_Y,SWDIO,SWCLK,RPB_LX,DVDD_B,VREG_AVDD_B,XIN_B,XOUT_B,XOUT_Y_B
python3 tools/finish_route.py --nets="${PREROUTE:-$CORNERS}" --lock || true
# (the link, RP-B north -> RP-A north, is gen_pcb.link_route's locked copper already)
python3 tools/route.py --passes "${PASSES:-12}" ${STRATEGY:+--strategy "$STRATEGY"}
python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
python3 tools/finish_route.py || true
python3 tools/drc_fix.py                  # again: a rip-up transaction can leave a crossing behind
python3 tools/finish_route.py || true
python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'
python3 tools/tidy_tracks.py
python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
python3 tools/check_vias.py               # before any pcbnew save re-nets a via that sits in a foreign pad
python3 tools/fill_zones.py               # the fills the gerbers are plotted from, after the last via
python3 tools/set_models.py
python3 tools/fix_silk.py                 # refs off pads/other silk (nearest clear spot, else hidden)
python3 tools/fill_zones.py
# the gate runs on the SAVED fills (no --refill-zones): those are what the fab gets
kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations $PCB -o /dev/null
