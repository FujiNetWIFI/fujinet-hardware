#!/usr/bin/env python3
"""GND stitching vias: a grid over the body plus a row just inside the board edge,
tying the F.Cu / B.Cu pours to the In1 plane (return paths for the layer changes
Freerouting makes, and a ground guard along the edges).  Every candidate is tried
and KiCad's DRC decides: vias in any violation are dropped, so the result is
DRC-clean by construction.  The vias are locked (tidy/finish leave them alone).

Usage: python3 tools/stitch_gnd.py [board.kicad_pcb] [--pitch 4.0] [--edge 1.2]
"""
import os, sys, json, math, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, Q
import gen_pcb as G

_args = [a for a in sys.argv[1:] if not a.startswith('--')]
PCB = os.path.abspath(_args[0]) if _args else G.PCB
PITCH = float(next((a.split('=')[1] for a in sys.argv[1:] if a.startswith('--pitch=')), 4.0))
EDGE = float(next((a.split('=')[1] for a in sys.argv[1:] if a.startswith('--edge=')), 1.2))
VIA_D, VIA_DRILL = 0.6, 0.3
PADS = []


def inside(x, y):
    return G.point_in_poly(x, y, G.OUTLINE)


def candidates():
    pts = []
    ux, uy, _ = G.PLACE['U1'] if G.PLACE else (0, 0, 0)
    # grid over the body (tab excluded), staggered every other row
    y = G.Y0 + EDGE + PITCH / 2
    row = 0
    while y < G.TAB_Y - EDGE:
        x = G.X0 + EDGE + (PITCH / 2 if row % 2 else PITCH)
        while x < G.X1 - EDGE:
            pts.append((round(x, 2), round(y, 2)))
            x += PITCH
        y += PITCH
        row += 1
    # guard row along the outline, EDGE inside every edge of the body (notches included)
    n = len(G.OUTLINE)
    for i in range(n):
        (xa, ya), (xb, yb) = G.OUTLINE[i], G.OUTLINE[(i + 1) % n]
        if max(ya, yb) > G.TAB_Y + 0.01 and min(ya, yb) >= G.TAB_Y - 0.01:
            continue                                  # the tab's own edges
        L = math.hypot(xb - xa, yb - ya)
        if L < 2.0:
            continue
        k = max(1, int(L / (PITCH / 1.5)))
        for j in range(1, k):
            t = j / k
            px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
            # inward normal: the outline is traced clockwise (y down), so inside is to the right
            nx, ny = (yb - ya) / L, -(xb - xa) / L
            cx, cy = px + nx * EDGE, py + ny * EDGE
            if not inside(cx, cy):
                cx, cy = px - nx * EDGE, py - ny * EDGE
            if inside(cx, cy) and cy < G.TAB_Y - EDGE:
                pts.append((round(cx, 2), round(cy, 2)))
    out = []
    for x, y in pts:
        if not inside(x, y):
            continue
        if any(math.hypot(x - hx, y - hy) < d / 2 + 1.0 for hx, hy, d in G.HOLES):
            continue
        if abs(x - ux) < G.UNDER + 1.0 and abs(y - uy) < G.UNDER + 1.0:
            continue                                  # keep the DVDD island under the RP whole
        if any(G.point_in_poly(x + dx, y + dy, [(ux + px, uy + py) for px, py in G.dvdd_island()])
               for dx in (-0.6, 0, 0.6) for dy in (-0.6, 0, 0.6)):
            continue                                  # ... and its lobe / bridge west of the package
        if any(not p.th and abs(x - p.cx) < p.hw + VIA_D / 2 + 0.2 and abs(y - p.cy) < p.hh + VIA_D / 2 + 0.2
               for p in PADS):
            continue                                  # never in or against an SMD pad (DRC allows a same-net one)
        out.append((x, y))
    return out


def via(x, y, i):
    return ['via', ['at', x, y], ['size', VIA_D], ['drill', VIA_DRILL], ['locked', 'yes'],
            ['layers', Q('F.Cu'), Q('B.Cu')], ['net', Q('GND')], ['uuid', Q(str(G.uid('stitch', i)))]]


def drc_uuids():
    """uuids of items in any DRC violation, plus GND vias that connect to nothing (a via in
    an area without the plane, e.g. the antenna keep-out, shows up as an unconnected item)."""
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-astrocade-stitch.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', fn, PCB], capture_output=True)
    d = json.load(open(fn))
    bad = set()
    for v in d.get('violations', []):
        for it in v['items']:
            bad.add(it['uuid'])        # via_dangling included: a via touching one layer only is no stitch
    for u in d.get('unconnected_items', []):
        for it in u['items']:
            if it['description'].startswith('Via [GND]'):
                bad.add(it['uuid'])
    return bad, d


def main():
    G.do_placement(G.place)          # fills G.PLACE (U1's position for the under-RP exclusion)
    board = parse(open(PCB).read())
    PADS[:] = G.board_pads(board)[0]
    have = {(round(float(find(e, 'at')[1]), 2), round(float(find(e, 'at')[2]), 2))
            for e in board if isinstance(e, list) and e and e[0] == 'via'}
    allc = set(candidates())
    cand = [p for p in allc if p not in have]
    k = max(k for k, e in enumerate(board) if isinstance(e, list) and e and e[0] in ('segment', 'via', 'footprint'))
    new = [via(x, y, i) for i, (x, y) in enumerate(cand)]
    board[k + 1:k + 1] = new
    open(PCB, 'w').write(dump(board) + '\n')
    # this run's vias, plus an earlier run's (a GND via on a candidate spot): all judged again
    mine = {str(find(e, 'uuid')[1]) for e in board if isinstance(e, list) and e and e[0] == 'via'
            and str(find(e, 'net')[1]) == 'GND'
            and (round(float(find(e, 'at')[1]), 2), round(float(find(e, 'at')[2]), 2)) in allc}
    for _ in range(3):
        bad, _d = drc_uuids()
        drop = bad & mine
        if not drop:
            break
        board = [e for e in board if not (isinstance(e, list) and e and e[0] == 'via'
                                          and str(find(e, 'uuid')[1]) in drop)]
        mine -= drop
        open(PCB, 'w').write(dump(board) + '\n')
    print('stitch_gnd: %d candidates, %d GND stitching vias on the board (%d dropped by DRC)' % (len(allc), len(mine), len(allc) - len(mine)))


if __name__ == '__main__':
    main()
