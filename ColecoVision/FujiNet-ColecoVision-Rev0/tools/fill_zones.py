#!/usr/bin/env python3
"""Refill every zone and save the board: the last copper step before the DRC gate and the export.

The gerbers are plotted from the fills saved in the .kicad_pcb.  stitch_gnd.py adds its vias to the
file as text, after the last ZONE_FILLER fill, so the saved inner pours still covered those GND vias:
a plane short at each one in the fab zip, while `kicad-cli pcb drc --refill-zones` (fresh fills in
memory) passed.  Found on FujiNet-StudioII Rev0, 2026-10-11.  The DRC gate now runs on the saved
fills, and tools/audit/check_gerbers.py (check 8) checks the zip itself.

Usage: python3 tools/fill_zones.py [board]
"""
import glob, os, sys
import pcbnew

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) > 1:
    PCB = os.path.abspath(sys.argv[1])
else:
    boards = glob.glob(os.path.join(PRJ, '*.kicad_pcb'))
    if len(boards) != 1:
        raise SystemExit('fill_zones: expected one .kicad_pcb in %s, found %d' % (PRJ, len(boards)))
    PCB = boards[0]
b = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('fill_zones: %d zones refilled' % len(b.Zones()))
