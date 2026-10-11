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
from tmpdir import tmp
from sexpr import parse, dump, find, Q
import gen_pcb as G

_args = [a for a in sys.argv[1:] if not a.startswith('--')]
PCB = os.path.abspath(_args[0]) if _args else G.PCB
PITCH = float(next((a.split('=')[1] for a in sys.argv[1:] if a.startswith('--pitch=')), 4.0))
EDGE = float(next((a.split('=')[1] for a in sys.argv[1:] if a.startswith('--edge=')), 1.2))
VIA_D, VIA_DRILL = 0.6, 0.3


def inside(x, y):
    return G.point_in_poly(x, y, G.OUTLINE)


# return-path vias: a GND via beside every via of these nets (kicad-happy RP-001 wants one within
# 1 mm of each layer change), offered at 0.95 mm in eight directions and DRC-filtered like the grid;
# then every signal via left without one gets closer offers one at a time (second_ring).
# None goes under the RP2040 (the exclusion below)
NEAR_NETS = ('USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM')
NEAR_R = 0.95


def near_points(board):
    nets = {G.NET(n) for n in NEAR_NETS}
    pts = set()
    for e in board:
        if isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) in nets:
            ax, ay = float(find(e, 'at')[1]), float(find(e, 'at')[2])
            for k in range(8):
                t = math.radians(45 * k + 22.5)
                pts.add((round(ax + NEAR_R * math.cos(t), 2), round(ay + NEAR_R * math.sin(t), 2)))
    return pts


def candidates(extra=()):
    pts = list(extra)
    ux, uy, _ = G.PLACE[G.K['U_RP']] if G.PLACE else (0, 0, 0)
    # grid over the body (tab excluded), staggered every other row
    y = G.Y0 + EDGE + PITCH / 2
    row = 0
    while y < G.BLADE_Y - EDGE:
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
        if min(ya, yb) >= G.BLADE_Y - 0.01:
            continue                                  # edges inside the finger field
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
            if inside(cx, cy) and cy < G.BLADE_Y - EDGE:
                pts.append((round(cx, 2), round(cy, 2)))
    out = []
    for x, y in pts:
        if not inside(x, y):
            continue
        if any(math.hypot(x - hx, y - hy) < G.HOLE_CU + 0.4 for hx, hy, d in G.HOLES):
            continue                                  # the shell bosses' copper-free rings
        if abs(x - ux) < G.UNDER + 1.0 and abs(y - uy) < G.UNDER + 1.0:
            continue                                  # nothing new under the RP2040
        out.append((x, y))
    return out


def via(x, y, i):
    # keyed by position, not by list index: a second run's new vias must never reuse an earlier
    # run's uuids (DRC reports items by uuid, so a rejected new via took a good old one with it)
    return ['via', ['at', x, y], ['size', VIA_D], ['drill', VIA_DRILL], ['locked', 'yes'],
            ['layers', Q('F.Cu'), Q('B.Cu')], ['net', Q('GND')], ['uuid', Q(str(G.uid('stitch', x, y)))]]


def drc_uuids():
    """uuids of items in any DRC violation, plus GND vias that connect to nothing (a via in
    an area without the plane, e.g. the antenna keep-out, shows up as an unconnected item)."""
    fn = tmp('stitch.json')
    # every severity: a GND via dropped onto another net's track is re-netted to it by KiCad on load,
    # and then shows up only as a via_dangling warning, not as a short
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--severity-all', '--format', 'json', '-o', fn, PCB],
                   capture_output=True)
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
    G.do_placement(G.place, [])      # fills G.PLACE (the RP's position for the under-RP exclusion)
    board = parse(open(PCB).read())
    # never in or against a pad, whatever its net: DRC allows a GND via in a GND pad, but an
    # untented via in an SMD pad wicks the solder away during reflow
    pads, _ = G.board_pads(board)
    def off_pads(x, y):
        return all(max(abs(x - p.cx) - p.hw, 0) ** 2 + max(abs(y - p.cy) - p.hh, 0) ** 2 > (VIA_D / 2 + 0.2) ** 2
                   for p in pads)
    allc0 = set(candidates(near_points(board)))
    # an earlier run's stitching vias inside pads go
    board = [e for e in board if not (isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) == 'GND'
             and (round(float(find(e, 'at')[1]), 2), round(float(find(e, 'at')[2]), 2)) in allc0
             and not off_pads(float(find(e, 'at')[1]), float(find(e, 'at')[2])))]
    have = {(round(float(find(e, 'at')[1]), 2), round(float(find(e, 'at')[2]), 2))
            for e in board if isinstance(e, list) and e and e[0] == 'via'}
    allc = {c for c in allc0 if off_pads(*c)}
    cand = [p for p in allc if p not in have]
    k = max(k for k, e in enumerate(board) if isinstance(e, list) and e and e[0] in ('segment', 'via', 'footprint'))
    new = [via(x, y, i) for i, (x, y) in enumerate(cand)]
    board[k + 1:k + 1] = new
    open(PCB, 'w').write(dump(board) + '\n')
    # this run's vias, plus an earlier run's (a GND via on a candidate spot): all judged again
    mine = {str(find(e, 'uuid')[1]) for e in board if isinstance(e, list) and e and e[0] == 'via'
            and str(find(e, 'net')[1]) == 'GND'
            and (round(float(find(e, 'at')[1]), 2), round(float(find(e, 'at')[2]), 2)) in allc}
    for _ in range(10):
        bad, _d = drc_uuids()
        drop = bad & mine
        if not drop:
            break
        board = [e for e in board if not (isinstance(e, list) and e and e[0] == 'via'
                                          and str(find(e, 'uuid')[1]) in drop)]
        mine -= drop
        open(PCB, 'w').write(dump(board) + '\n')
    print('stitch_gnd: %d candidates, %d GND stitching vias on the board (%d dropped by DRC)' % (len(allc), len(mine), len(allc) - len(mine)))
    second_ring(off_pads)


# the supplies: their vias are plane drops, not layer changes of a signal (kicad-happy skips them too)
POWER_NETS = ('+5V', '+3V3', '+3V3_RP', 'CONS_5V', 'VBUS', 'DVDD', 'BUCK_SW')


def second_ring(off_pads):
    """Every signal via still without a GND via within 1.0 mm (kicad-happy RP-001: the return current
    of a layer change wants a GND via beside it) gets closer offers, one per via per round (0.75 / 0.85
    / 0.95 mm, 16 directions): offers around the same via would overlap each other, and DRC would then
    drop both; offers for two neighbouring vias that land within 0.9 mm of each other wait a round.
    The first offer DRC accepts stays, and one GND via can serve several signal vias."""
    power = {G.NET(n) for n in POWER_NETS} | {'GND', ''}
    def vias_of(board, pred):
        return [(float(find(e, 'at')[1]), float(find(e, 'at')[2])) for e in board
                if isinstance(e, list) and e and e[0] == 'via' and pred(str(find(e, 'net')[1]))]
    board = parse(open(PCB).read())
    gnd = vias_of(board, lambda n: n == 'GND')
    lonely = [v for v in vias_of(board, lambda n: n not in power)
              if min(math.hypot(v[0] - g[0], v[1] - g[1]) for g in gnd) > 1.0]
    n_lonely = len(lonely)
    offers = {v: [(round(v[0] + r * math.cos(math.radians(22.5 * k)), 2), round(v[1] + r * math.sin(math.radians(22.5 * k)), 2))
                  for r in (0.75, 0.85, 0.95) for k in range(16)] for v in lonely}
    allowed = set(candidates([p for o in offers.values() for p in o]))
    segs = [(float(find(e, 'start')[1]), float(find(e, 'start')[2]), float(find(e, 'end')[1]), float(find(e, 'end')[2]),
             float(find(e, 'width')[1])) for e in board
            if isinstance(e, list) and e and e[0] == 'segment' and str(find(e, 'net')[1]) != 'GND']
    def off_tracks(x, y):
        for x0, y0, x1, y1, w in segs:
            dx, dy = x1 - x0, y1 - y0
            ll = dx * dx + dy * dy
            u = 0 if ll == 0 else max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / ll))
            if math.hypot(x0 + u * dx - x, y0 + u * dy - y) < VIA_D / 2 + w / 2 + 0.15:
                return False
        return True
    offers = {v: [p for p in o if p in allowed and off_pads(*p) and off_tracks(*p)] for v, o in offers.items()}
    offers = {v: o for v, o in offers.items() if o}
    added, rounds = 0, 0
    while offers and rounds < 60:
        rounds += 1
        todo = []
        for v, o in offers.items():
            if o and all(math.hypot(o[0][0] - q[0], o[0][1] - q[1]) > 0.9 for _, q in todo):
                todo.append((v, o.pop(0)))
        if not todo:
            break
        board = parse(open(PCB).read())
        k = max(k for k, e in enumerate(board) if isinstance(e, list) and e and e[0] in ('segment', 'via', 'footprint'))
        new = [via(x, y, 0) for _, (x, y) in todo]
        board[k + 1:k + 1] = new
        open(PCB, 'w').write(dump(board) + '\n')
        bad, _d = drc_uuids()
        board = [e for e in board if not (isinstance(e, list) and e and e[0] == 'via'
                                          and str(find(e, 'uuid')[1]) in bad
                                          and any(e is v for v in new))]
        open(PCB, 'w').write(dump(board) + '\n')
        done = [(float(find(v, 'at')[1]), float(find(v, 'at')[2])) for v in new if str(find(v, 'uuid')[1]) not in bad]
        added += len(done)
        # a via now within 1.0 mm of a new GND via is served, whoever's offer it was
        offers = {v: o for v, o in offers.items()
                  if o and all(math.hypot(v[0] - g[0], v[1] - g[1]) > 1.0 for g in done)}
    board = parse(open(PCB).read())
    gnd = vias_of(board, lambda n: n == 'GND')
    left = [v for v in vias_of(board, lambda n: n not in power)
            if min(math.hypot(v[0] - g[0], v[1] - g[1]) for g in gnd) > 1.0]
    print('stitch_gnd: second ring: %d signal vias without a GND via within 1 mm, %d GND vias added in %d rounds, '
          '%d signal vias still without one (no room, or under the RP2040)' % (n_lonely, added, rounds, len(left)))


if __name__ == '__main__':
    main()
