#!/usr/bin/env python3
"""Refill every zone and save the board: the last copper step before the DRC gate and the export.

The gerbers are plotted from the fills saved in the .kicad_pcb.  stitch_gnd.py and the hand patches add
vias to the file as text, after tidy_tracks.py's last fill, so the saved In2 pours still covered those
GND vias: 427 of them would have been shorted to +5V / +3V3 / +3V3_S3 / CONS_5V in the 2026-10-11
11:42 zip (`kicad-cli pcb drc --refill-zones` checks fresh fills in memory and passed).  The DRC gate now
runs on the saved fills, and audit/check_gerbers.py checks every via against the plotted inner layers.

Usage: python3 tools/fill_zones.py [board]
"""
import os, sys
import pcbnew

PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'FujiNet-StudioII-Rev0.kicad_pcb')
b = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('fill_zones: %d zones refilled' % len(b.Zones()))
