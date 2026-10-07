#!/usr/bin/env python3
"""Autoroute Fujiversal-Atari2600-Rev1.kicad_pcb with Freerouting.

  1. pcbnew: export exports/Fujiversal-Atari2600-Rev1.dsn (inner layers are
     'power' layers -> planes; the locked plane fan-out from gen_pcb.py is
     exported as fixed wiring)
  2. freerouting (headless) -> exports/Fujiversal-Atari2600-Rev1.ses
  3. pcbnew: import the session, add GND pours on F.Cu and B.Cu over the
     body (the finger-strip rule areas keep the finger field clear), fill all zones, save
  4. ask KiCad's DRC how many connections are still open; if any, strip the
     pours and go round again from the routed board (--rounds)

Usage: python3 tools/route.py [--passes N] [--rounds N] [--jar PATH]
Default jar: ~/.local/share/freerouting/freerouting-2.4.1.jar
(https://github.com/freerouting/freerouting/releases, v2.4.1)
"""
import argparse, json, os, re, subprocess, sys, tempfile
import pcbnew
sys.path.insert(0, HERE := os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find

PRJ = os.path.dirname(HERE)
NAME = 'Fujiversal-Atari2600-Rev1'
PCB = os.path.join(PRJ, NAME + '.kicad_pcb')
EXP = os.path.join(PRJ, 'exports')


def pour(board, layer, net, name):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(board.GetNetInfo().GetNetItem(net).GetNetCode())
    z.SetZoneName(name)
    z.SetAssignedPriority(0)
    z.SetLocalClearance(pcbnew.FromMM(0.15))   # net-class/DRU clearances still apply
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetThermalReliefGap(pcbnew.FromMM(0.3))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    ol.NewOutline()
    import gen_pcb as G
    for x, y in G.BODY:
        ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)


POURS = ('GND_top', 'GND_bottom')


def strip_pours():
    """Remove the outer-layer GND pours (text edit: the SWIG zone iterators
    are unusable under Python 3.14) so the router sees bare copper."""
    t = parse(open(PCB).read())
    t = [e for e in t if not (isinstance(e, list) and e and e[0] == 'zone'
                              and find(e, 'name') and find(e, 'name')[1] in POURS)]
    open(PCB, 'w').write(dump(t) + '\n')


def unconnected():
    fn = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-rev1-route-drc.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', fn, PCB], capture_output=True)
    return len(json.load(open(fn)).get('unconnected_items', []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--passes', type=int, default=60)
    ap.add_argument('--rounds', type=int, default=1)
    ap.add_argument('--jar', default=os.path.expanduser('~/.local/share/freerouting/freerouting-2.4.1.jar'))
    ap.add_argument('--timeout', type=int, default=7200)
    ap.add_argument('--strategy', default=None, help='freerouting -us (greedy|global|hybrid)')
    a = ap.parse_args()
    os.makedirs(EXP, exist_ok=True)
    dsn, ses = os.path.join(EXP, NAME + '.dsn'), os.path.join(EXP, NAME + '.ses')
    for rnd in range(1, a.rounds + 1):
        strip_pours()
        board = pcbnew.LoadBoard(PCB)
        assert pcbnew.ExportSpecctraDSN(board, dsn)
        if os.path.exists(ses):
            os.remove(ses)
        log = open(os.path.join(EXP, 'freerouting.log'), 'w')
        subprocess.run(['java', '-jar', a.jar, '-de', dsn, '-do', ses, '-mp', str(a.passes)]
                       + (['-us', a.strategy] if a.strategy else []) + ['--gui.enabled=false'], stdout=log, stderr=subprocess.STDOUT, timeout=a.timeout, check=True)
        txt = open(os.path.join(EXP, 'freerouting.log')).read()
        m = re.findall(r'final score: ([\d.]+) \((\d+) unrouted and (\d+) violations\)', txt)
        board = pcbnew.LoadBoard(PCB)
        assert pcbnew.ImportSpecctraSES(board, ses)
        pour(board, pcbnew.F_Cu, 'GND', 'GND_top')
        pour(board, pcbnew.B_Cu, 'GND', 'GND_bottom')
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(PCB, board)
        left = unconnected()
        print('round %d: freerouting %s; KiCad unconnected: %d' % (rnd, m[-1] if m else '?', left))
        if left == 0:
            break
    print('routed board saved')


if __name__ == '__main__':
    main()
