#!/usr/bin/env bash
# kicad-happy schematic-stage audit for FujiNet-5200 Rev0 (docs/design-review-rev0.md, Part 1).
# Writes into analysis/ (gitignored). Needs ngspice, pdftotext and the datasheets/ PDFs (manifest.json lists them).
set -euo pipefail
cd "$(dirname "$0")/../.."
K=${KICAD_HAPPY:-$HOME/.claude/plugins/cache/kicad-happy/kicad-happy/2.2.1/skills}
python3 $K/kicad/scripts/analyze_schematic.py FujiNet-5200-Rev0.kicad_sch --analysis-dir analysis/
python3 $K/spice/scripts/simulate_subcircuits.py --analysis-dir analysis/ || true
python3 tools/audit/spice_checks.py          # PWR_OK sense 0-5.5 V, the CONS_OFF gate under SS34 leakage, PHI2 through CR9
python3 tools/audit/margins.py > /dev/null   # levels, E9, budgets (VR1, raw DC), LED, crystal (prints the numbers when run alone)
python3 tools/audit/timing_margins.py > /dev/null   # the 6502 read path through the RP and the 541
python3 tools/audit/edge_orientation.py > /dev/null
python3 tools/audit/make_deep_review.py
python3 $K/kicad/review/scripts/deep_review_gate.py analysis/deep_review.json --analysis-dir analysis/ --datasheets-dir datasheets
python3 $K/kicad/scripts/summarize_findings.py analysis/ --top 40
