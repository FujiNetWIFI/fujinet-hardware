#!/usr/bin/env bash
# Route the freshly generated FujiNet-ChannelF-Rev0.kicad_pcb (tools/gen_pcb.py) and finish it:
# the RP2040's crystal / SWD / DVDD pre-route, Freerouting, the grid A* finisher for what it
# leaves, clean-up, GND stitching, 3D models, silkscreen, and the DRC gate.  Called by
# build_all.sh (LAYOUT=1).  PASSES sets Freerouting's pass budget (default 16), STRATEGY its -us
# option (default: none, Freerouting's own greedy); PREROUTE overrides the locked pre-route nets.
set -euo pipefail
cd "$(dirname "$0")/.."
PCB=FujiNet-ChannelF-Rev0.kicad_pcb
# the crystal on the empty board, locked (XOUT and DVDD are drawn: gen_pcb.rp_support / rp_dvdd_link).  The RP's east-side escapes (GP17, GP16, RUN, SWDIO, SWCLK) are left to
# Freerouting: pre-routed one by one, each greedy diagonal walled in the next (SWDIO in V2, RUN in V3)
python3 tools/finish_route.py --nets="${PREROUTE:-XIN,XOUT_Y}" --lock || true
python3 tools/route.py --passes "${PASSES:-16}" ${STRATEGY:+--strategy "$STRATEGY"}
python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
python3 tools/finish_route.py || true
python3 tools/drc_fix.py                  # again: a rip-up transaction can leave a crossing behind
python3 tools/finish_route.py || true
python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'
python3 tools/tidy_tracks.py
python3 tools/fix_via_pairs.py            # same-net via pairs closer than the hole rule -> one track (V9's VBUS pair)
python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
python3 tools/check_vias.py               # before any pcbnew save re-nets a via that sits in a foreign pad
python3 tools/set_models.py
python3 tools/fix_silk.py                 # refs off pads/other silk (nearest clear spot, else hidden)
kicad-cli pcb drc --refill-zones --schematic-parity --severity-all --exit-code-violations $PCB -o /dev/null
