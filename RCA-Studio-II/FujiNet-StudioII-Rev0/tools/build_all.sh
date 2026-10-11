#!/usr/bin/env bash
# Regenerate FujiNet-StudioII Rev0: the edge footprint and its audit against the sources, the
# schematic from tools/design.py + tools/sch_layout.py (drawing checks, netlist parity), KiCad ERC,
# the firmware cross-checks; with LAYOUT=1 also the board (placement, Raspberry Pi's regulator corner,
# the supply rings, the address twist and data fan-in, plane fan-out, routing, DRC with schematic
# parity); then the BOMs, the schematic PDF, the JLCPCB package, layout views and the fab gates.
# Needs KiCad 10, Python 3 (+ numpy, Pillow), a C compiler (check_glue.py compiles the firmware's glue
# equations) and, for LAYOUT=1, Java + Freerouting 2.4.1 (~/.local/share/freerouting/freerouting-2.4.1.jar).
# check_nets.py / check_glue.py read pico/studio2 from $FUJINET_FIRMWARE (default
# ~/Workspace/fujinet-firmware); check_nets.py also needs the ESP32-S3 firmware's pin map,
# $FUJINET_S2_BOARD/include/pinmap/fujiversal-studio2.h (default ~/Workspace/fn-studio2-board).
# Without LAYOUT=1 the routed board is kept as it is: only its sheet links and part fields are
# re-synced to the schematic (tools/sync_pcb_sheets.py), then DRC with schematic parity runs.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
PCB=FujiNet-StudioII-Rev0.kicad_pcb
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # the 22-pin Studio II edge footprint (edge_geom.py: FliP's geometry)
python3 tools/make_fp_extra.py >/dev/null     # 1x03 header, TS-1187A, the shell-post hole
python3 tools/audit/edge_orientation.py >/dev/null   # the edge footprint vs FliP / EJK / the original board
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 3 drawn sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-StudioII-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py | tail -1         # netlist vs s2_cart.h and the edge map (independent of design.py)
python3 tools/check_glue.py | tail -1         # the '541 enables and CART CS vs s2_glue_drive() / s2_glue_cartcs()
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement.py + design.py -> the placed, pre-routed board, planes, fan-out, case anchors
    bash tools/route_board.sh                 # crystal pre-route, Freerouting, finisher, stitching, check_vias, DRC gate
elif [ -f $PCB ]; then
    python3 tools/sync_pcb_sheets.py          # re-link the routed board to the schematic (copper untouched)
    python3 tools/fill_zones.py               # the gerbers plot the saved fills: keep them current
    kicad-cli pcb drc --schematic-parity --severity-all --exit-code-violations "$PWD/$PCB" -o /dev/null   # on the saved fills
fi
if [ -f $PCB ]; then
    python3 tools/check_vias.py               # no via in a foreign SMD pad (KiCad would re-net it silently)
    python3 tools/audit/layout_checks.py | tail -1   # the regulator corner, rings, decoupling, USB, crystal, edge on the copper
fi
python3 tools/export.py                       # BOMs, schematic PDF (+ the JLCPCB package, layout views, renders)
if [ -f exports/jlcpcb/FujiNet-StudioII-Rev0-gerbers.zip ]; then
    python3 tools/tab_overlay.py              # docs/tab-overlay-1to1.pdf
    python3 tools/audit/check_fab.py          # the package: BOM / CPL vs design.py, drills, the order-number spot, the gerbers
fi
