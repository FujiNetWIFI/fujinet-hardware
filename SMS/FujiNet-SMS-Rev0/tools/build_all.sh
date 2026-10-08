#!/usr/bin/env bash
# Regenerate FujiNet-SMS Rev0: footprints, sheets, ERC, the firmware
# cross-checks; with LAYOUT=1 also the board (placement, routing, DRC with
# schematic parity); then BOM, CPL, gerbers, schematic PDF and layout views.
# Needs KiCad 10, Python 3 (+ numpy), a C compiler (check_glue.py compiles the
# firmware's glue equations) and, for the board, Java + Freerouting 2.4.1.
# check_nets.py / check_glue.py read pico/sms from $FUJINET_FIRMWARE
# (default ~/Workspace/fujinet-firmware; the SMS contract lives on branch
# add-sms, e.g. the worktree ~/Workspace/fn-sms) and the S3 pinmap from
# $FUJINET_SMS_BOARD (default ~/Workspace/fn-sms-board).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
if [ -z "${FUJINET_FIRMWARE:-}" ] && [ -f "$HOME/Workspace/fn-sms/pico/sms/firmware/include/sms_cart.h" ]; then
    export FUJINET_FIRMWARE="$HOME/Workspace/fn-sms"
fi
python3 tools/harvest_symbols.py >/dev/null   # stock symbols (via the NES Rev0 cache) -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 50-pin SMS edge footprint
python3 tools/make_fp_extra.py >/dev/null     # 1x03 pin header
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 7 drawn sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-SMS-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
python3 tools/check_glue.py                   # the 74HCT glue vs sms_cart.h, every input combination
python3 tools/audit/edge_orientation.py >/dev/null   # the edge footprint vs the cartridge sources
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement.py + design.py -> the placed board, planes, fan-out, case anchors
    bash tools/route_board.sh                 # pre-route, Freerouting, finisher, stitching, check_vias, DRC gate
fi
python3 tools/export.py                       # BOM, schematic PDF (+ JLCPCB / PCBWay packages, layout views, renders with a .kicad_pcb)
if [ -f exports/jlcpcb/FujiNet-SMS-Rev0-gerbers.zip ]; then
    python3 tools/audit/check_gerbers.py >/dev/null   # the fab zips: fingers both faces, mask windows, nothing in the tab
fi
