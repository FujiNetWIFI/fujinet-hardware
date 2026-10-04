#!/usr/bin/env python3
"""Return-path GND vias beside the layer changes of the fast / sensitive nets
(USB pairs, crystal drive, SWD clock): for each such signal via, try GND via
spots on rings 0.8-1.0 mm around it (kicad-happy RP-001 wants one within 1.0 mm) and keep the first one KiCad's DRC and
tools/check_vias.py accept (kicad-happy EMC rule RP-001).

Usage: python3 tools/stitch_transitions.py [board]
"""
import json, math, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, Q
import gen_pcb as G

PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else G.PCB
NETS = ('USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM', 'XIN', 'XOUT', 'XOUT_Y', 'SWCLK')
VIA_D, VIA_DRILL = 0.6, 0.3


def drc_bad():
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-astrocade-stitchtr.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', fn, PCB], capture_output=True)
    d = json.load(open(fn))
    bad = {it['uuid'] for v in d.get('violations', []) for it in v['items']}
    bad |= {it['uuid'] for u in d.get('unconnected_items', []) for it in u['items'] if it['description'].startswith('Via [GND]')}
    return bad


def main():
    board = parse(open(PCB).read())
    pads, _ = G.board_pads(board)
    full = {G.NET(n) for n in NETS}
    sig = [(float(find(e, 'at')[1]), float(find(e, 'at')[2]), str(find(e, 'net')[1])) for e in board
           if isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) in full]
    gnd = [(float(find(e, 'at')[1]), float(find(e, 'at')[2])) for e in board
           if isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) == 'GND']
    todo = [(x, y, n) for x, y, n in sig if not any(math.hypot(x - gx, y - gy) <= 1.0 for gx, gy in gnd)]
    placed = 0
    for rnd, (r, k) in enumerate(((0.8, 0), (0.8, 0.5), (0.9, 0.25), (1.0, 0), (1.0, 0.5), (0.95, 0.75))):
        if not todo:
            break
        cands = []
        for i, (x, y, n) in enumerate(todo):
            for a in range(8):
                t = (a + k) * math.pi / 4
                cx, cy = round(x + r * math.cos(t), 3), round(y + r * math.sin(t), 3)
                if cy > G.BLADE_Y - 0.6 or any(not p.th and abs(cx - p.cx) < p.hw + VIA_D / 2 + 0.2
                                               and abs(cy - p.cy) < p.hh + VIA_D / 2 + 0.2 for p in pads):
                    continue
                cands.append((i, a, cx, cy))
        k0 = max(j for j, e in enumerate(board) if isinstance(e, list) and e and e[0] in ('segment', 'via', 'footprint'))
        new = {}
        for (i, a, cx, cy) in cands:
            u = str(G.uid('stitchtr', rnd, i, a)).strip('"')
            new[u] = (i, ['via', ['at', cx, cy], ['size', VIA_D], ['drill', VIA_DRILL], ['locked', 'yes'],
                          ['layers', Q('F.Cu'), Q('B.Cu')], ['net', Q('GND')], ['uuid', Q(u)]])
        board[k0 + 1:k0 + 1] = [v for _, v in new.values()]
        open(PCB, 'w').write(dump(board) + '\n')
        bad = drc_bad()
        keep, done = set(), set()
        for u, (i, v) in new.items():           # first DRC-clean spot per signal via; candidates can clash with
            if u not in bad and i not in done:  # each other, so keep one per via and re-check below
                keep.add(u); done.add(i)
        board = [e for e in board if not (isinstance(e, list) and e and e[0] == 'via'
                                          and str(find(e, 'uuid')[1]).strip('"') in set(new) - keep)]
        open(PCB, 'w').write(dump(board) + '\n')
        bad = drc_bad() & keep
        if bad:
            board = [e for e in board if not (isinstance(e, list) and e and e[0] == 'via'
                                              and str(find(e, 'uuid')[1]).strip('"') in bad)]
            open(PCB, 'w').write(dump(board) + '\n')
            done = {new[u][0] for u in keep - bad}
        placed += len(done)
        todo = [t for i, t in enumerate(todo) if i not in done]
    print('stitch_transitions: %d signal vias, %d got a GND return via, %d left without' % (len(sig), placed, len(todo)))


if __name__ == '__main__':
    main()
