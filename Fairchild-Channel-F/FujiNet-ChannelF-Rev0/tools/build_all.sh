#!/usr/bin/env bash
# Regenerate FujiNet-ChannelF Rev0 (schematic stage -- there is no board yet): the schematic from
# tools/design.py + tools/sch_layout.py with its drawing checks and netlist parity, KiCad ERC, the
# firmware cross-check, then the BOMs and the schematic PDF.
# Needs KiCad 10 and Python 3.  check_nets.py reads the firmware from $FUJINET_FIRMWARE (default
# ~/Workspace/fujinet-firmware; the S3 pin map from its fujiversal-channelf-board branch when the
# checkout lacks it) and the pico-sdk from $PICO_SDK_PATH (default /usr/share/pico-sdk).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
python3 tools/harvest_symbols.py >/dev/null   # stock symbols -> tools/symcache.sexpr
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 4 wired sheets; drawing
                                              # checks, hierarchy, netlist parity with design.py
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-ChannelF-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
python3 tools/export.py                       # BOM, JLCPCB BOM, schematic PDF
