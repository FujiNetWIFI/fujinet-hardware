#!/usr/bin/env bash
# Route the freshly generated FujiNet-StudioII-Rev0.kicad_pcb (tools/gen_pcb.py) and finish it:
# the RP2354B's crystal / SWD pre-route, Freerouting, the grid A* finisher for what it leaves,
# clean-up, GND stitching, 3D models, silkscreen, and the DRC gate.  Called by build_all.sh
# (LAYOUT=1).  PASSES sets Freerouting's pass budget (default 16), STRATEGY its -us option (default:
# none, Freerouting's own greedy); PREROUTE overrides the locked pre-route nets.  (The core regulator,
# the supply rings, the address twist and the data fan-in are already drawn by gen_pcb.py.)
set -euo pipefail
cd "$(dirname "$0")/.."
PCB=FujiNet-StudioII-Rev0.kicad_pcb
# the crystal on the board before Freerouting, locked: XIN straight east, XOUT up into its 1k, XOUT_Y
# round the crystal's GND pad (SWD is drawn: gen_pcb.swd_escape; TP_DVDD's link: gen_pcb.tp_dvdd_link)
python3 tools/finish_route.py --nets="${PREROUTE:-XIN,XOUT,XOUT_Y}" --lock || true
python3 tools/route.py --passes "${PASSES:-16}" ${STRATEGY:+--strategy "$STRATEGY"}
python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
python3 tools/finish_route.py || true
python3 tools/drc_fix.py                  # again: a rip-up transaction can leave a crossing behind
python3 tools/finish_route.py || true
python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'
python3 tools/drc_fix.py                  # the neck pass can leave a squeeze at 0.5 mm pitch (S3: the USB-C's pair)
python3 tools/finish_route.py --neck || echo 'finish_route: links left open -- the DRC gate below will fail'
python3 tools/tidy_tracks.py
python3 tools/fix_via_pairs.py            # same-net via pairs closer than the hole rule -> one track
python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
python3 tools/check_vias.py               # before any pcbnew save re-nets a via that sits in a foreign pad
python3 tools/set_models.py
python3 tools/fix_silk.py                 # refs off pads/other silk (nearest clear spot, else hidden)
python3 tools/fill_zones.py               # refill + save: the gerbers plot the saved fills (stitch_gnd's vias came after the last fill)
# on the SAVED fills (no --refill-zones: that checks fresh fills in memory, not what is plotted); an
# absolute path: with a relative one KiCad asserts (harmlessly) when it loads the schematic for parity
kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations "$PWD/$PCB" -o /dev/null
