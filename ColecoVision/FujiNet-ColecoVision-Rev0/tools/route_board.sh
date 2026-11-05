#!/usr/bin/env bash
# Route the freshly generated FujiNet-ColecoVision-Rev0.kicad_pcb (tools/gen_pcb.py) and
# finish it: the edge nets and the USB pair with the grid router, the '245's B side alone in
# Freerouting, then Freerouting, the grid A* finisher for what it leaves, clean-up, GND
# stitching, 3D models, silkscreen, and the DRC gate.  Called by build_all.sh (LAYOUT=1).
# PASSES (default 20) sets Freerouting's pass budget.
set -euo pipefail
cd "$(dirname "$0")/.."
PCB=FujiNet-ColecoVision-Rev0.kicad_pcb
# the edge nets and the USB pair first, locked (placement.PRE_ROUTE): Freerouting never enters a
# finger's neck, so left to the finisher they get only what Freerouting leaves over
PRE=$(cd tools && python3 -c 'import placement; print(",".join(placement.PRE_ROUTE))')
python3 tools/finish_route.py --nets="$PRE" --lock || true
# then the W25Q16's QSPI alone in Freerouting, locked (placement.FR_FIRST): left to the full run, the
# through traffic on B.Cu walls one of its lines out of the flash corner
python3 tools/fr_subset.py "$(cd tools && python3 -c 'import placement; print(",".join(placement.FR_FIRST))')"
python3 tools/route.py --passes "${PASSES:-20}" ${STRATEGY:+--strategy "$STRATEGY"}
python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
python3 tools/finish_route.py || true
python3 tools/drc_fix.py                  # again: a rip-up transaction can leave a crossing behind
python3 tools/finish_route.py || true
python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'
python3 tools/tidy_tracks.py
python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
python3 tools/set_models.py
python3 tools/fix_silk.py                 # refs off pads/other silk (nearest clear spot, else hidden)
python3 tools/fill_zones.py               # refill + save: the gerbers plot the SAVED fills (stitch_gnd adds vias after the last fill)
kicad-cli pcb drc --schematic-parity --severity-error --exit-code-violations $PCB -o /dev/null   # on the saved fills
