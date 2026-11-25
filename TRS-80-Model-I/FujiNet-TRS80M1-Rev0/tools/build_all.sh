#!/usr/bin/env bash
# Regenerate FujiNet-TRS80M1 Rev0 end to end: the two EasyEDA-derived footprints, the schematic from
# tools/design.py + tools/sch_layout.py (drawing checks, netlist parity), KiCad ERC, the header against
# the Model I's expansion edge, the firmware cross-checks, the ribbon simulation and the margins; with
# LAYOUT=1 also the board (placement, Raspberry Pi's regulator corner, plane fan-out, routing, DRC with
# schematic parity); then the BOMs, the schematic PDF, the JLCPCB / PCBWay packages, layout views and
# the fab gates.
# Needs KiCad 10, Python 3 (+ numpy), ngspice, Java + Freerouting 2.4.1 for the board.
# check_nets.py reads pico/trs80m1 from $FUJINET_FIRMWARE (default ~/Workspace/fn-trs80m1, the bring-up's
# dev tree) at $FUJINET_FIRMWARE_REF (default '': its working tree).
# LAYOUT=1 regenerates and re-routes the board: routing varies run to run (README "Layout").
# REUSE_FROM=old.kicad_pcb (with LAYOUT=1) first copies that board's copper for every net the change left
# alone (tools/reuse_copper.py): how the header fix was routed, from PR #72's board (README "Layout").
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
PCB=FujiNet-TRS80M1-Rev0.kicad_pcb
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/make_fp_m1.py >/dev/null        # the box header and the DIP switch, from their EasyEDA footprints
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 5 drawn sheets, project symbols, netlist parity
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-TRS80M1-Rev0.kicad_sch -o /dev/null
python3 tools/audit/header_pinout.py | tail -1   # the header vs the Model I's expansion edge (four sources)
python3 tools/check_nets.py | tail -1         # netlist vs the pico/trs80m1 firmware (independent of design.py)
python3 tools/audit/spice/ribbon.py | tail -2 # the ribbon both ways (ngspice)
python3 tools/audit/margins.py | tail -1      # levels, loads, contention, read timing, power
if [ "${LAYOUT:-0}" = 1 ]; then
    python3 tools/gen_pcb.py                  # placement, outline, RP core graft, fan-out, planes, rules
    if [ -n "${REUSE_FROM:-}" ]; then
        python3 tools/reuse_copper.py "$REUSE_FROM"   # the old board's copper for the unchanged nets, locked
    fi
    bash tools/route_board.sh                 # Freerouting, finisher, stitching, fills, DRC
fi
if [ -f $PCB ]; then
    python3 tools/check_vias.py 2>/dev/null || true
    python3 tools/audit/layout_checks.py | tail -1   # the layout's claims, measured on the copper
fi
python3 tools/export.py                       # BOMs, schematic PDF (+ CPL/gerbers/renders with a .kicad_pcb)
if [ -f exports/jlcpcb/FujiNet-TRS80M1-Rev0-gerbers.zip ]; then
    python3 tools/audit/check_gerbers.py | tail -1    # the zip: outline, holes, header drills, antenna band, plane shorts
    python3 tools/audit/check_fab.py
fi
