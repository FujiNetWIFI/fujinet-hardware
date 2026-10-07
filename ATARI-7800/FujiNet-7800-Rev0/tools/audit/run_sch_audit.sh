#!/usr/bin/env bash
# kicad-happy schematic-stage audit for FujiNet-7800 Rev0 (docs/design-review-rev0.md, Part 1).
# Writes into analysis/ (gitignored). Needs ngspice, pdftotext and the datasheets/ PDFs.
set -euo pipefail
cd "$(dirname "$0")/../.."
K=${KICAD_HAPPY:-$HOME/.claude/plugins/cache/kicad-happy/kicad-happy/2.2.1/skills}
python3 tools/audit/make_happy_config.py     # .kicad-happy.json, suppressions resolved from design.py keys
python3 $K/kicad/scripts/analyze_schematic.py FujiNet-7800-Rev0.kicad_sch --analysis-dir analysis/
python3 $K/spice/scripts/simulate_subcircuits.py --analysis-dir analysis/ || true
python3 tools/audit/spice_checks.py          # VSENSE, P-FET gate, /IRQ, audio vs a POKEY cart, /HALT isolation
python3 tools/audit/margins.py > /dev/null   # levels, budget, E9, audio, power-on race (prints when run alone)
python3 tools/audit/timing_margins.py > /dev/null
python3 tools/audit/edge_orientation.py > /dev/null
python3 tools/audit/make_deep_review.py
python3 $K/kicad/review/scripts/deep_review_gate.py analysis/deep_review.json --analysis-dir analysis/ --datasheets-dir datasheets
python3 $K/kicad/scripts/summarize_findings.py analysis/ --top 40
