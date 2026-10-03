#!/usr/bin/env bash
# Regenerate FujiNet-Astrocade Rev0 end to end: schematic + checks, placed board,
# pre-routes, Freerouting, finisher, tidy, GND stitching, DRC, audits, fab outputs.
# Needs KiCad 10, Python 3 (+ numpy), Java 21 + Freerouting 2.4.1
# (~/.local/share/freerouting/freerouting-2.4.1.jar).  check_nets.py reads the
# firmware headers from $FUJINET_FIRMWARE (default: the worktree
# ~/Workspace/fn-astrocade on fujinet-firmware branch astrocade-rp2354-board).
# The copper stack-up is gen_pcb.STACKUP (4 or 6).  Never edit this file while it runs.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${FUJINET_FIRMWARE:-}" ] && [ -d "$HOME/Workspace/fn-astrocade/pico/astrocade" ]; then
    export FUJINET_FIRMWARE="$HOME/Workspace/fn-astrocade"
fi
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 26 contact lands on B.Cu
python3 tools/make_fp_extra.py >/dev/null     # SOT-23-5, fiducial
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 4 sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-Astrocade-Rev0.kicad_sch -o /dev/null
python3 tools/check_sch_layout.py             # drawn netlist == design.py, no overlapping symbols
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
if [ "${LAYOUT:-1}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement, RPi regulator-corner graft, plane fan-out, zones
    python3 tools/audit/edge_orientation.py
    # RP crystal + VBUS first, locked.  The cart bus is NOT pre-routed: A* tracks laid one
    # pin at a time wall in the neighbouring 0.4 mm QFN-60 pins (every other bus net was left
    # with no path, on 4 and on 6 layers alike); Freerouting escapes the pin rows itself.
    python3 tools/finish_route.py --nets=XIN,XOUT,XOUT_Y,VBUS --lock || true
    python3 tools/route.py --passes 25 --rounds 2   # a second Freerouting round on whatever the first leaves open
    python3 tools/drc_fix.py                  # drop router copper that breaks DRC; the finisher redoes it
    python3 tools/finish_route.py || echo 'finish_route: links left open -- the DRC gate below will fail'
    python3 tools/tidy_tracks.py              # router crumbs, fold-backs, acute corners (DRC-gated)
    python3 tools/stitch_gnd.py               # GND stitching grid + edge guard row, DRC-filtered
    python3 tools/stitch_transitions.py       # GND return vias beside USB / crystal / SWCLK layer changes
    python3 tools/check_vias.py               # no via inside another net's pad (KiCad's DRC re-nets such vias)
    python3 tools/set_models.py
    kicad-cli pcb drc --refill-zones --schematic-parity --severity-error --exit-code-violations \
        FujiNet-Astrocade-Rev0.kicad_pcb -o /dev/null
fi
python3 tools/export.py                       # BOM, JLCPCB BOM + CPL, gerbers, schematic PDF, SVGs, renders
