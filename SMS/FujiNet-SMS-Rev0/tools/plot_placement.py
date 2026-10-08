#!/usr/bin/env python3
"""Placement preview: the board outline, courtyards (labelled by design.py key),
pads, and every signal net's ratsnest (minimum spanning tree over its pads;
the plane nets are left out), drawn to a PNG; prints the total ratsnest
length and the number of crossing ratsnest edges -- the numbers to compare
placement variants by, before any routing.

Usage: python3 tools/plot_placement.py [board.kicad_pcb] [-o out.png] [--scale px/mm]
"""
import argparse, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
from sexpr import parse
import design as D
import gen_pcb as G

PLANES = {'GND', '+3V3', '+5V', '+3V3_RP', 'DVDD'}


def mst(pts):
    """Prim's MST over points: [(i, j)]."""
    n = len(pts)
    if n < 2:
        return []
    inside, out = {0}, []
    best = {j: (math.dist(pts[0], pts[j]), 0) for j in range(1, n)}
    while best:
        j = min(best, key=lambda k: best[k][0])
        d, i = best.pop(j)
        out.append((i, j))
        inside.add(j)
        for k in best:
            dk = math.dist(pts[j], pts[k])
            if dk < best[k][0]:
                best[k] = (dk, j)
    return out


def crosses(a, b, c, d):
    def o(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return (v > 1e-9) - (v < -1e-9)
    if a in (c, d) or b in (c, d):
        return False
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pcb', nargs='?', default=G.PCB)
    ap.add_argument('-o', default=os.path.join(G.PRJ, 'placement.png'))
    ap.add_argument('--scale', type=float, default=9.0)
    ap.add_argument('--window', help='x0,y0,x1,y1: crop to this region (mm)')
    ap.add_argument('--no-rats', action='store_true')
    a = ap.parse_args()
    board = parse(open(a.pcb).read())
    G.do_placement(G.place, [])
    pads, crt = G.board_pads(board)
    S = a.scale
    wx0, wy0, wx1, wy1 = (map(float, a.window.split(',')) if a.window else
                          (G.X0 - 3, G.Y0 - 3, G.X1 + 3, G.Y1 + 3))
    ox, oy = wx0, wy0
    W, H = int((wx1 - wx0) * S), int((wy1 - wy0) * S)
    im = Image.new('RGB', (W, H), 'white')
    dr = ImageDraw.Draw(im)
    P = lambda x, y: ((x - ox) * S, (y - oy) * S)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', max(9, int(S * 1.1)))
    except OSError:
        font = ImageFont.load_default()
    dr.polygon([P(*p) for p in G.OUTLINE], outline='black', width=2)
    for x, y, d in G.HOLES:
        r = d / 2 * S
        dr.ellipse([P(x, y)[0] - r, P(x, y)[1] - r, P(x, y)[0] + r, P(x, y)[1] + r], outline='black', width=2)
    dr.polygon([P(*p) for p in G.five_v_island()], outline=(255, 170, 170), width=1)     # In4 +5V island
    if G.K['U_RP'] in G.PLACE:
        ux, uy, _ = G.PLACE[G.K['U_RP']]
        r = G.RP_ISLAND
        dr.rectangle([P(ux - r, uy - r), P(ux + r, uy + r)], outline=(170, 170, 255), width=1)
    key = {p.ref: p.key for p in D.PARTS}
    for ref, (x0, y0, x1, y1) in crt.items():
        dr.rectangle([P(x0, y0), P(x1, y1)], outline=(150, 150, 150), width=1)
        dr.text(P(x0 + 0.2, y0 + 0.1), key.get(ref, ref), fill=(90, 90, 90), font=font)
    for p in pads:
        col = (200, 60, 60) if 'F.Cu' in p.layers else (60, 60, 200)
        dr.rectangle([P(p.cx - p.hw, p.cy - p.hh), P(p.cx + p.hw, p.cy + p.hh)], fill=col)
    LC = {'F.Cu': (230, 120, 0), 'In2.Cu': (0, 170, 170), 'In3.Cu': (170, 0, 170), 'B.Cu': (40, 90, 255)}
    for e in board:
        if isinstance(e, list) and e and e[0] == 'segment':
            st, en = [x for x in e if isinstance(x, list) and x[0] == 'start'][0], \
                [x for x in e if isinstance(x, list) and x[0] == 'end'][0]
            L = [x for x in e if isinstance(x, list) and x[0] == 'layer'][0][1]
            w = float([x for x in e if isinstance(x, list) and x[0] == 'width'][0][1])
            dr.line([P(float(st[1]), float(st[2])), P(float(en[1]), float(en[2]))], fill=LC.get(str(L), (0, 0, 0)),
                    width=max(1, int(w * S)))
        elif isinstance(e, list) and e and e[0] == 'via':
            at = [x for x in e if isinstance(x, list) and x[0] == 'at'][0]
            r = float([x for x in e if isinstance(x, list) and x[0] == 'size'][0][1]) / 2 * S
            cx, cy = P(float(at[1]), float(at[2]))
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 0, 0), fill=(255, 220, 0))
    by_net = {}
    for p in pads:
        if p.net and not p.net.startswith('unconnected') and G.canon(p.net) not in PLANES:
            by_net.setdefault(p.net, []).append((p.cx, p.cy))
    edges, total = [], 0.0
    for net, pts in by_net.items():
        for i, j in mst(pts):
            edges.append((pts[i], pts[j], net))
            total += math.dist(pts[i], pts[j])
    for (a_, b_, net) in edges if not a.no_rats else []:
        dr.line([P(*a_), P(*b_)], fill=(0, 160, 0), width=1)
    nx = sum(crosses(edges[i][0], edges[i][1], edges[k][0], edges[k][1])
             for i in range(len(edges)) for k in range(i + 1, len(edges)))
    im.save(a.o)
    print('ratsnest: %d nets, %d edges, %.0f mm, %d crossings -> %s' % (len(by_net), len(edges), total, nx, a.o))


if __name__ == '__main__':
    main()
