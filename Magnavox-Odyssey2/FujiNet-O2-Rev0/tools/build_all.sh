#!/usr/bin/env bash
# Regenerate FujiNet-O2 Rev0 end to end: the edge footprint and its audit against the published
# pinouts, the schematic from tools/design.py + tools/sch_layout.py (drawing checks, netlist parity),
# KiCad ERC, the firmware cross-checks and the margins; with LAYOUT=1 also the board (placement,
# Raspberry Pi's regulator corner, plane fan-out, routing, DRC with schematic parity); then the BOMs,
# the schematic PDF, the JLCPCB package, layout views and the fab gates.
# Needs KiCad 10, Python 3 (+ numpy), Java + Freerouting 2.4.1 for the board.
# check_nets.py reads pico/o2 from $FUJINET_FIRMWARE (default ~/Workspace/fujinet-firmware) at
# $FUJINET_FIRMWARE_REF (default origin/master).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
PCB=FujiNet-O2-Rev0.kicad_pcb
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # the 2x15 Videopac edge footprint (tools/edge_geom.py)
python3 tools/make_fp_extra.py >/dev/null     # SOT-23-5, fiducial
python3 tools/audit/edge_orientation.py | tail -3   # the edge vs Boris's pinout and three built carts
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 4 drawn sheets, project symbols, netlist parity
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-O2-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs the pico/o2 firmware (independent of design.py)
python3 tools/audit/margins.py | tail -1      # bus levels both ways, VSENSE, the mux threshold, the cart's draw
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement, outline, fingers, RP core graft, fan-out, planes, rules
    bash tools/route_board.sh                 # Freerouting, finisher, stitching, fills, DRC
fi
if [ -f $PCB ]; then
    python3 tools/check_vias.py 2>/dev/null || true
    python3 tools/audit/layout_checks.py | tail -1   # the layout's claims, measured on the copper
fi
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF (+ CPL/gerbers/renders with a .kicad_pcb)
if [ -f exports/jlcpcb/FujiNet-O2-Rev0-gerbers.zip ]; then
    python3 tools/audit/check_gerbers.py | tail -1    # the zip: fingers, outline, masks, plane shorts
    python3 tools/audit/check_fab.py
fi
