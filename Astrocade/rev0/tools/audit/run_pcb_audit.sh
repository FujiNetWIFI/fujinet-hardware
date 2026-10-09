#!/usr/bin/env bash
# kicad-happy PCB-stage audit for FujiNet-Astrocade Rev0: run after the board is routed and exported.
# Writes into analysis/ (gitignored); needs ngspice, pdftotext and datasheets/ (manifest.json lists the PDFs).
set -euo pipefail
cd "$(dirname "$0")/../.."
K=${KICAD_HAPPY:-$HOME/.claude/plugins/cache/kicad-happy/kicad-happy/2.2.1/skills}
python3 $K/kicad/scripts/analyze_schematic.py FujiNet-Astrocade-Rev0.kicad_sch --analysis-dir analysis/
python3 $K/kicad/scripts/analyze_pcb.py FujiNet-Astrocade-Rev0.kicad_pcb --analysis-dir analysis/ --full --proximity
RUN=$(python3 -c "import json; print(json.load(open('analysis/manifest.json'))['current'])")
python3 $K/kicad/scripts/cross_analysis.py --schematic analysis/$RUN/schematic.json --pcb analysis/$RUN/pcb.json --analysis-dir analysis/
python3 $K/emc/scripts/analyze_emc.py --schematic analysis/$RUN/schematic.json --pcb analysis/$RUN/pcb.json --analysis-dir analysis/ || true
python3 $K/kicad/scripts/analyze_thermal.py -s analysis/$RUN/schematic.json -p analysis/$RUN/pcb.json --analysis-dir analysis/ || true
python3 $K/spice/scripts/simulate_subcircuits.py --analysis-dir analysis/ || true
if [ -d exports/jlcpcb/gerbers ] || [ -f exports/jlcpcb/FujiNet-Astrocade-Rev0-gerbers.zip ]; then
    rm -rf analysis/gerbers_tmp && mkdir -p analysis/gerbers_tmp && unzip -q -o exports/jlcpcb/FujiNet-Astrocade-Rev0-gerbers.zip -d analysis/gerbers_tmp
    python3 $K/kicad/scripts/analyze_gerbers.py analysis/gerbers_tmp/ --analysis-dir analysis/ || true
fi
python3 $K/kicad/scripts/cross_verify.py -s analysis/$RUN/schematic.json -p analysis/$RUN/pcb.json \
    $( [ -f analysis/$RUN/thermal.json ] && echo -t analysis/$RUN/thermal.json ) -o analysis/$RUN/cross_verify.json
python3 $K/kicad/scripts/lifecycle_audit.py analysis/$RUN/schematic.json --only lcsc --temp-range commercial \
    --output analysis/$RUN/lifecycle.json > /dev/null || true      # LCSC gives stock, not lifecycle status
python3 tools/audit/stock_check.py > /dev/null || true             # JLC / LCSC stock per line (network)
python3 tools/audit/make_deep_review.py
python3 $K/kicad/review/scripts/deep_review_gate.py analysis/deep_review.json --analysis-dir analysis/ --datasheets-dir datasheets
python3 $K/kicad/scripts/summarize_findings.py analysis/ --top 40
# the release gate, warnings as failures (its waivers are triaged in docs/design-review-rev0.md)
opt() { [ -f "analysis/$RUN/$2" ] && echo "$1 analysis/$RUN/$2"; }
python3 $K/kicad/scripts/fab_release_gate.py -s analysis/$RUN/schematic.json -p analysis/$RUN/pcb.json \
    $(opt -g gerber.json) $(opt -t thermal.json) $(opt -e emc.json) --strict --text | tee analysis/$RUN/fab_release_gate.txt
