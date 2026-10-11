#!/usr/bin/env bash
# Regenerate FujiNet-ChannelF Rev0: the edge footprint, the schematic (drawing checks, netlist
# parity), KiCad ERC, the firmware cross-check and the edge audit; with LAYOUT=1 also the board
# (placement, plane fan-out, routing, DRC with schematic parity); then BOM, CPL, gerbers, the
# schematic PDF, layout views and the fab gates.
# Needs KiCad 10, Python 3 (+ numpy, Pillow) and, for LAYOUT=1, Java + Freerouting 2.4.1
# (~/.local/share/freerouting/freerouting-2.4.1.jar).  check_nets.py reads the firmware from
# $FUJINET_FIRMWARE (default ~/Workspace/fujinet-firmware; the S3 pin map from its
# fujiversal-channelf-board branch when the checkout lacks it) and the pico-sdk from
# $PICO_SDK_PATH (default /usr/share/pico-sdk).
# Without LAYOUT=1 the routed board is kept as it is: only its sheet links and part fields are
# re-synced to the schematic (tools/sync_pcb_sheets.py), then DRC with schematic parity runs.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
PCB=FujiNet-ChannelF-Rev0.kicad_pcb
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py >/dev/null      # the 22-contact Videocart edge footprint (edge_geom.py)
python3 tools/make_fp_extra.py >/dev/null     # the shell-boss NPTH hole
python3 tools/audit/edge_orientation.py >/dev/null   # the edge footprint vs aotta / fart / veswiki
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 4 wired sheets; drawing
                                              # checks, hierarchy, netlist parity with design.py
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-ChannelF-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement.py + design.py -> the placed board, planes, fan-out, case anchors
    bash tools/route_board.sh                 # pre-route, Freerouting, finisher, stitching, check_vias, DRC gate
elif [ -f $PCB ]; then
    python3 tools/sync_pcb_sheets.py          # re-link the routed board to the schematic (copper untouched)
    kicad-cli pcb drc --refill-zones --schematic-parity --severity-all --exit-code-violations $PCB -o /dev/null
fi
python3 tools/export.py                       # BOMs, schematic PDF (+ the JLCPCB package, layout views, renders)
if [ -f exports/jlcpcb/FujiNet-ChannelF-Rev0-gerbers.zip ]; then
    python3 tools/tab_overlay.py              # docs/tab-overlay-1to1.pdf
    python3 tools/audit/check_fab.py          # the package: BOM / CPL vs design.py, drills, the order-number spot
fi
