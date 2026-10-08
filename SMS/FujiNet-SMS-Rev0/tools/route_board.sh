#!/usr/bin/env bash
# Route the freshly generated FujiNet-SMS-Rev0.kicad_pcb (tools/gen_pcb.py) and
# finish it: the RP2354B corner pre-route, Freerouting, the grid A* finisher for
# what it leaves, clean-up, GND stitching, 3D models, silkscreen, and the DRC
# gate.  Called by build_all.sh (LAYOUT=1).
# PASSES sets Freerouting's pass budget (default 12), STRATEGY its -us option (default: none,
# Freerouting's own greedy).  The v2 board (2026-10-08) came from six variants -- 12/16/20 passes,
# hybrid / global / greedy, two pre-route sets: all plateaued at 46-50 "unrouted" (mostly plane
# connections KiCad's zones make) by pass 8, and 12 passes greedy left KiCad 2 links, which the
# finisher closed; DRC 0/0/0.  PREROUTE overrides the locked pre-route net list.
set -euo pipefail
cd "$(dirname "$0")/.."
PCB=FujiNet-SMS-Rev0.kicad_pcb
# the core regulator, the crystal and SWD on the empty board, locked.  SWCLK (pin 33,
# the southern one) before SWDIO: their pads are south of the pins, and the other way
# round SWDIO's inner-layer run cuts across SWCLK's escape
python3 tools/finish_route.py --nets="${PREROUTE:-RP_LX,DVDD,VREG_AVDD,XIN,XOUT,XOUT_Y,SWCLK,SWDIO}" --lock || true
python3 tools/route.py --passes "${PASSES:-12}" ${STRATEGY:+--strategy "$STRATEGY"}
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
kicad-cli pcb drc --refill-zones --schematic-parity --severity-all --exit-code-violations $PCB -o /dev/null
