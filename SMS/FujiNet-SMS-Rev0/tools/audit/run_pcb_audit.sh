#!/usr/bin/env bash
# kicad-happy PCB-stage audit for FujiNet-SMS Rev0: run after the board is routed and exported.
# Writes into analysis/ (gitignored); summarise with summarize_findings.py.
set -euo pipefail
cd "$(dirname "$0")/../.."
K=${KICAD_HAPPY:-$HOME/.claude/plugins/cache/kicad-happy/kicad-happy/2.2.1/skills}
python3 $K/kicad/scripts/analyze_schematic.py FujiNet-SMS-Rev0.kicad_sch --analysis-dir analysis/
python3 $K/kicad/scripts/analyze_pcb.py FujiNet-SMS-Rev0.kicad_pcb --analysis-dir analysis/ --full --proximity
RUN=$(python3 -c "import json; print(json.load(open('analysis/manifest.json'))['current'])")
python3 $K/kicad/scripts/cross_analysis.py --schematic analysis/$RUN/schematic.json --pcb analysis/$RUN/pcb.json --analysis-dir analysis/
python3 $K/emc/scripts/analyze_emc.py --schematic analysis/$RUN/schematic.json --pcb analysis/$RUN/pcb.json --analysis-dir analysis/ || true
python3 $K/kicad/scripts/analyze_thermal.py -s analysis/$RUN/schematic.json -p analysis/$RUN/pcb.json --analysis-dir analysis/ || true
python3 $K/spice/scripts/simulate_subcircuits.py --analysis-dir analysis/ || true
if [ -d exports/jlcpcb/gerbers ] || [ -f exports/jlcpcb/FujiNet-SMS-Rev0-gerbers.zip ]; then
    rm -rf analysis/gerbers_tmp && mkdir -p analysis/gerbers_tmp && unzip -q -o exports/jlcpcb/FujiNet-SMS-Rev0-gerbers.zip -d analysis/gerbers_tmp
    python3 $K/kicad/scripts/analyze_gerbers.py analysis/gerbers_tmp/ --analysis-dir analysis/ || true
fi
python3 $K/kicad/scripts/summarize_findings.py analysis/ --top 40
