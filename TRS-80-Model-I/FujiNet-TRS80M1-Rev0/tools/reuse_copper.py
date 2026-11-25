#!/usr/bin/env python3
"""Copy a routed board's copper into the freshly placed one, for every net the change left alone.

The header fix (edge pins swapped in pairs, 2026-11-25) changed only the m1-bus sheet's nets.  This copies
the old board's tracks and vias, locked, for every other net whose pads are unchanged (same references,
pad numbers and positions): the rp-core, fujinet, usb and power sheets' signal nets, VBUS, and the m1-bus
sheet's RP-side nets around the RP2354B's south pins (REUSE_BUS).  Freerouting and the finisher then
route only what changed.  Plane nets (GND, +5V, +3V3, +3V3_RP and the core rails) are left to the plane
fan-out gen_pcb.py makes.

Usage (after gen_pcb.py, before route_board.sh):
    git show 3278d76:TRS-80-Model-I/FujiNet-TRS80M1-Rev0/FujiNet-TRS80M1-Rev0.kicad_pcb > old.kicad_pcb
    python3 tools/reuse_copper.py old.kicad_pcb [board.kicad_pcb]
"""
import os, sys
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pcb as G   # noqa: E402

PLANE_NETS = {'GND', '+5V', '+3V3', '+3V3_RP', '+1V1', 'DVDD', 'PGND'}
REUSE_BUS = ['RP_SYSRES_N', 'DRIVE', 'DIP_RAM', 'DIP_EI', 'DIP_RS232', 'RP_INT_N', 'RP_INTAK_N', 'RP_LED',
             'DBG_RX', 'DBG_TX']


def pads(board):
    out = {}
    for p in board.GetPads():
        n = p.GetNetname()
        if n:
            q = p.GetPosition()
            out.setdefault(n, set()).add((p.GetParentFootprint().GetReference(), p.GetNumber(), q.x, q.y))
    return out


def main():
    old_p = sys.argv[1]
    new_p = sys.argv[2] if len(sys.argv) > 2 else G.PCB
    old, new = pcbnew.LoadBoard(old_p), pcbnew.LoadBoard(new_p)
    po, pn = pads(old), pads(new)
    short = lambda n: n.rsplit('/', 1)[-1]
    keep = lambda n: (short(n) not in PLANE_NETS and not n.startswith('unconnected')
                      and (not n.startswith('/m1-bus/') or short(n) in REUSE_BUS))
    same = sorted(n for n in pn if keep(n) and po.get(n) == pn[n])
    nets = new.GetNetInfo()
    # what gen_pcb.py already drew on those nets (the USB macro's stubs, the regulator graft's VREG_AVDD)
    # gives way: the old board holds it too, as routing and tidying left it
    for t in [t for t in new.GetTracks() if t.GetNetname() in same]:
        new.Remove(t)
    copied = 0
    for t in old.GetTracks():
        n = t.GetNetname()
        if n in same:
            c = t.Duplicate()
            c.SetParent(new)
            c.SetNet(nets.GetNetItem(n))
            c.SetLocked(True)
            new.Add(c)
            copied += 1
    pcbnew.SaveBoard(new_p, new)
    left = sorted(short(n) for n in pn if n not in same and short(n) not in PLANE_NETS and not n.startswith('unconnected'))
    print('reuse_copper: %d items of %d nets copied, locked; %d nets left to route' % (copied, len(same), len(left)))


if __name__ == '__main__':
    main()
