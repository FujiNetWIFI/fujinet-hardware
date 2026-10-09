#!/usr/bin/env bash
# Regenerate FujiNet-Astrocade Rev0: schematic + checks, then either the routed board's links
# (default) or, with LAYOUT=1, the whole board from scratch: placement, pre-routes, Freerouting,
# finisher, tidy, GND stitching, DRC; then audits and fab outputs.
# Needs KiCad 10, Python 3 (+ numpy), and for LAYOUT=1 Java 21 + Freerouting 2.4.1
# (~/.local/share/freerouting/freerouting-2.4.1.jar).  check_nets.py reads the
# firmware headers from $FUJINET_FIRMWARE (default: the worktree
# ~/Workspace/fn-astrocade on fujinet-firmware branch astrocade-rp2354-board).
# The copper stack-up is gen_pcb.STACKUP (4 or 6).  Never edit this file while it runs.
# LAYOUT=1 re-routes: Freerouting is deterministic for the same inputs, but any change to them
# (a net name, a part) gives a different board -- the routed Rev0 board is the one in git.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
if [ -z "${FUJINET_FIRMWARE:-}" ] && [ -d "$HOME/Workspace/fn-astrocade/pico/astrocade" ]; then
    export FUJINET_FIRMWARE="$HOME/Workspace/fn-astrocade"
fi
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 26 contact lands on B.Cu
python3 tools/make_fp_extra.py >/dev/null     # SOT-23-5, fiducial
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 5 wired sheets; drawing checks,
                                              # board mirror, netlist parity with design.py, tools/nets.lock
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-Astrocade-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
if [ "${LAYOUT:-0}" != 1 ]; then
    # the routed board stays: give it the schematic's net names and sheet links, nothing else
    python3 tools/sync_pcb_nets.py            # (net "...") names, by design.py name; copper untouched
    python3 tools/sync_pcb_sheets.py          # footprint path / sheetname / sheetfile, fields
    python3 -c 'import sys; sys.path.insert(0, "tools"); import gen_pcb; gen_pcb.configure_project()'
    python3 tools/check_vias.py
    python3 tools/audit/edge_orientation.py
    kicad-cli pcb drc --refill-zones --schematic-parity --severity-error --exit-code-violations \
        FujiNet-Astrocade-Rev0.kicad_pcb -o /dev/null
else
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
