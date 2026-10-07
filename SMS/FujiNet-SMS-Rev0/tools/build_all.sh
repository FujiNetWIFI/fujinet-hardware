#!/usr/bin/env bash
# Regenerate FujiNet-SMS Rev0 (schematic only): footprints, sheets, ERC, the
# firmware cross-checks, BOM and PDF.  Needs KiCad 10, Python 3 and a C
# compiler (check_glue.py compiles the firmware's glue equations).
# check_nets.py / check_glue.py read pico/sms from $FUJINET_FIRMWARE
# (default ~/Workspace/fujinet-firmware) and the S3 pinmap from
# $FUJINET_SMS_BOARD (default ~/Workspace/fn-sms-board).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1           # no __pycache__ in tools/
python3 tools/harvest_symbols.py >/dev/null   # stock symbols (via the NES Rev0 cache) -> tools/symcache.sexpr
python3 tools/make_edge_fp.py                 # 50-pin SMS edge footprint (PROVISIONAL geometry)
python3 tools/make_fp_extra.py >/dev/null     # 1x03 pin header
python3 tools/gen_sch.py                      # design.py + sch_layout.py -> root + 7 drawn sheets, project symbol lib, .kicad_pro sheets
kicad-cli sch erc --severity-all --exit-code-violations FujiNet-SMS-Rev0.kicad_sch -o /dev/null
python3 tools/check_nets.py                   # netlist vs fujinet-firmware headers (independent of design.py)
python3 tools/check_glue.py                   # the 74HCT glue vs sms_cart.h, every input combination
python3 tools/export.py                       # BOM, schematic PDF
