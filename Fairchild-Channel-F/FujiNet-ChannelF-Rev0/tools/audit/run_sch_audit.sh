#!/usr/bin/env bash
# kicad-happy schematic-stage audit for FujiNet-ChannelF Rev0 (docs/design-review-rev0.md).
# Writes into analysis/ (gitignored). Needs ngspice, pdftotext and the datasheets/ PDFs (manifest.json lists them).
set -euo pipefail
cd "$(dirname "$0")/../.."
K=${KICAD_HAPPY:-$HOME/.claude/plugins/cache/kicad-happy/kicad-happy/2.2.1/skills}
python3 tools/audit/make_happy_config.py
python3 $K/kicad/scripts/analyze_schematic.py FujiNet-ChannelF-Rev0.kicad_sch --analysis-dir analysis/
python3 $K/spice/scripts/simulate_subcircuits.py --analysis-dir analysis/ || true
python3 tools/audit/margins.py > /dev/null   # bus levels, DIR pull-up, /INTREQ, +5V budget, crystal, LED
python3 tools/audit/edge_orientation.py > /dev/null
python3 $K/kicad/scripts/summarize_findings.py analysis/ --top 40
