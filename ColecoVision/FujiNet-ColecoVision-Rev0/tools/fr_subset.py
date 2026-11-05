#!/usr/bin/env python3
"""Freerouting on a few nets alone, before the full route: export the board's DSN, empty every other
net's pin list (their copper stays as obstacles, their connections are not asked for), route, import
the session and lock what it drew for those nets, so the full Freerouting run routes round them.

For the W25Q16's QSPI (placement.FR_FIRST): its corner west of the RP is crossed by B.Cu through-traffic
in the full run, which walls one of the six lines out; routed first, they take the corner and the rest
go round.  --keepout steers a subset away from a region for its own run only.

Usage: python3 tools/fr_subset.py NET[,NET...] [--passes N] [--keepout x,y;x,y;...]
"""
import argparse, os, re, subprocess, sys
import pcbnew
sys.path.insert(0, HERE := os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find
import route as R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nets')
    ap.add_argument('--passes', type=int, default=20)
    ap.add_argument('--keepout', default='', help='x,y;x,y;... (mm, board frame): a polygon the subset may not '
                    'cross on F.Cu or B.Cu, for this run only')
    ap.add_argument('--jar', default=os.path.expanduser('~/.local/share/freerouting/freerouting-2.4.1.jar'))
    a = ap.parse_args()
    want = a.nets.split(',')
    os.makedirs(R.EXP, exist_ok=True)
    dsn, ses = os.path.join(R.EXP, 'subset.dsn'), os.path.join(R.EXP, 'subset.ses')
    R.strip_pours()
    board = pcbnew.LoadBoard(R.PCB)
    assert pcbnew.ExportSpecctraDSN(board, dsn)
    txt = open(dsn).read()
    kept = []

    def keep_or_empty(m):
        name = m.group(1).strip('"')
        if name in want:
            kept.append(name)
            return m.group(0)
        return '(net %s\n      (pins)' % m.group(1)
    txt = re.sub(r'\(net ("[^"]+"|\S+)\s+\(pins[^)]*\)', keep_or_empty, txt)
    assert sorted(kept) == sorted(want), 'fr_subset: nets not found: %s' % sorted(set(want) - set(kept))
    if a.keepout:
        pts = [tuple(float(v) for v in p.split(',')) for p in a.keepout.split(';')]
        poly = '  '.join('%d %d' % (round(x * 1000), round(-y * 1000)) for x, y in pts + pts[:1])
        ko = ''.join('    (keepout "subset" (polygon %s 0  %s))\n' % (L, poly) for L in ('F.Cu', 'B.Cu'))
        k = txt.index('    (keepout ')
        txt = txt[:k] + ko + txt[k:]
    open(dsn, 'w').write(txt)
    if os.path.exists(ses):
        os.remove(ses)
    with open(os.path.join(R.EXP, 'freerouting-subset.log'), 'w') as log:
        subprocess.run(['java', '-jar', a.jar, '-de', dsn, '-do', ses, '-mp', str(a.passes), '--gui.enabled=false'],
                       stdout=log, stderr=subprocess.STDOUT, timeout=3600, check=True)
    board = pcbnew.LoadBoard(R.PCB)
    assert pcbnew.ImportSpecctraSES(board, ses)
    pcbnew.SaveBoard(R.PCB, board)
    t = parse(open(R.PCB).read())
    n = 0
    for e in t:
        if isinstance(e, list) and e and e[0] in ('segment', 'via', 'arc') and find(e, 'net') \
                and str(find(e, 'net')[1]) in want and not find(e, 'locked'):
            k = next(i for i, x in enumerate(e) if isinstance(x, list) and x and x[0] == 'net')
            e.insert(k, ['locked', 'yes'])
            n += 1
    open(R.PCB, 'w').write(dump(t) + '\n')
    left = [x for x in R_unconnected() if x in want]
    print('fr_subset: %d items locked on %d nets; %s' % (n, len(want), ('open: ' + ', '.join(sorted(set(left))))
                                                           if left else 'all joined'))


def R_unconnected():
    import json, tempfile
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-coleco-rev0-subset-drc.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '-o', fn, R.PCB], capture_output=True)
    out = []
    for v in json.load(open(fn)).get('unconnected_items', []):
        m = re.search(r'\[(.*?)\]', v['items'][0]['description'])
        if m:
            out.append(m.group(1))
    return out


if __name__ == '__main__':
    main()
