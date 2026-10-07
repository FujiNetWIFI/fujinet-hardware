#!/usr/bin/env python3
"""Finish whatever Freerouting leaves open: a two-layer grid A* router.

For each connection KiCad's DRC still reports as unconnected, rasterise the
other nets' copper (pads, tracks, vias, holes, board edge, the connector tab)
around it at 0.05 mm, inflated by clearance + half the track width,
and search F.Cu/B.Cu with vias.  The path is written back as tracks and vias
on the right net, the GND pours are refilled, and DRC is the judge.

Usage: python3 tools/finish_route.py [board] [--nets A,B,..] [--lock]
  --nets   only these nets (priority pre-route before Freerouting)
  --lock   write the new copper locked, so Freerouting keeps it
"""
import heapq, json, math, os, re, subprocess, sys, tempfile, uuid
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
import gen_pcb as G

_args = [a for a in sys.argv[1:] if not a.startswith('--')]
PCB = os.path.abspath(_args[0]) if _args else G.PCB
ONLY = next((a.split('=', 1)[1].split(',') for a in sys.argv[1:] if a.startswith('--nets=')), None)
LOCK = '--lock' in sys.argv
# --force=NETS: route these first, ignoring (and ripping up) other nets' unlocked
# router copper; the ripped nets are left for the next Freerouting round
FORCE = next((a.split('=', 1)[1].split(',') for a in sys.argv[1:] if a.startswith('--force=')), None)
RES = 0.05
MARGIN = 0.02          # grid discretisation allowance on top of the rule clearance (DRC verifies)
VIA_D, VIA_DRILL = 0.6, 0.3
RIP_PEN = 1.0           # rip-up mode: cost (mm per cell) of running through another net's unlocked copper,
                        # so the search detours around what it can and rips up only what it must
VIA_COST = 12.0
WIDTH = {'PWR': 0.5, 'VBUS': 0.3, 'USB': 0.25, 'Default': 0.2}
CLEAR = {'PWR': 0.2, 'VBUS': 0.15, 'USB': 0.15, 'Default': 0.15}
# --neck: signal tracks at 0.15 mm (as Freerouting necks down at fine-pitch pins; board minimum
# 0.1, JLCPCB 0.09): four tracks then pass 1.35 mm where 0.2 mm tracks need 1.55
NECK = '--neck' in sys.argv
if NECK:
    WIDTH['Default'] = 0.15
    CLEAR['Default'] = 0.12
NETCLASS = {n: c for c, _, _, _, _, nets in G.NETCLASSES for n in nets}
LAYERS = ('F.Cu', 'B.Cu')                 # outer copper
RLAYERS = ('F.Cu', 'B.Cu')                # the 4-layer stack's signal layers (In1 GND, In2 power)


def drc_unconnected():
    fn = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-rev1-finish.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', fn, PCB], capture_output=True)
    out = []
    for v in json.load(open(fn)).get('unconnected_items', []):
        ends = []
        for it in v['items']:
            d = it['description']
            net = re.search(r'\[(.*?)\]', d).group(1)
            if 'PTH' in d or d.startswith('Via'):
                lays = RLAYERS
            else:
                m = re.search(r' on (\w+\.Cu)', d)
                lays = (m.group(1),) if m and m.group(1) in RLAYERS else LAYERS
            ends.append((net, it['pos']['x'], it['pos']['y'], lays, d))
        out.append(ends)
    return out


def copper(board):
    """[(layer or None for both, net, kind, geometry)]"""
    items = []
    pads, _ = G.board_pads(board)
    for p in pads:
        for L in (RLAYERS if p.th else [l for l in p.layers if l in LAYERS]):
            items.append((L, p.net, 'rect', (p.cx, p.cy, p.hw, p.hh), p.th and p.net is None, None))
    for e in board:
        if not (isinstance(e, list) and e):
            continue
        if e[0] == 'zone' and find(e, 'name') and not find(e, 'keepout') and \
                str(find(e, 'name')[1]).startswith(('rp_dvdd_island', 'rp_io_island', 'rpi_graft')):
            # the FILLED copper (fill keeps clearance to other nets), not the outline
            net = find(e, 'net')
            for fp_ in findall(e, 'filled_polygon'):
                pts = [(float(q[1]), float(q[2])) for q in find(fp_, 'pts')[1:] if q[0] == 'xy']
                if len(pts) >= 3:
                    items.append((str(find(fp_, 'layer')[1]), str(net[1]) if net else None, 'poly', pts, False, None))
            continue
        if e[0] == 'segment':
            s, t = find(e, 'start'), find(e, 'end')
            net = find(e, 'net')
            items.append((str(find(e, 'layer')[1]), str(net[1]) if net else None, 'seg',
                          (float(s[1]), float(s[2]), float(t[1]), float(t[2]), float(find(e, 'width')[1]) / 2), False,
                          None if find(e, 'locked') else str(find(e, 'uuid')[1])))
        elif e[0] == 'via':
            a = find(e, 'at'); net = find(e, 'net')
            r = float(find(e, 'size')[1]) / 2
            for L in RLAYERS:
                items.append((L, str(net[1]) if net else None, 'circ', (float(a[1]), float(a[2]), r), False,
                              None if find(e, 'locked') else str(find(e, 'uuid')[1])))
    return items


def dist_field(kind, g, X, Y):
    if kind == 'poly_edges':  # distance to the outline, inside or out
        n = len(g)
        return np.minimum.reduce([dist_field('seg', (g[i][0], g[i][1], g[(i + 1) % n][0], g[(i + 1) % n][1], 0.0), X, Y)
                                  for i in range(n)])
    if kind == 'poly':      # 0 inside, else distance to the outline
        inside = np.zeros(X.shape, bool)
        d = np.full(X.shape, np.inf)
        n = len(g)
        for i in range(n):
            (xa, ya), (xb, yb) = g[i], g[(i + 1) % n]
            cond = (ya > Y) != (yb > Y)
            xint = xa + (Y - ya) * (xb - xa) / ((yb - ya) if yb != ya else 1e-12)
            inside ^= cond & (X < xint)
            d = np.minimum(d, dist_field('seg', (xa, ya, xb, yb, 0.0), X, Y))
        return np.where(inside, 0.0, d)
    if kind == 'rect':
        cx, cy, hw, hh = g
        return np.hypot(np.maximum(np.abs(X - cx) - hw, 0), np.maximum(np.abs(Y - cy) - hh, 0))
    if kind == 'circ':
        cx, cy, r = g
        return np.hypot(X - cx, Y - cy) - r
    x0, y0, x1, y1, hw = g
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = np.zeros_like(X) if L == 0 else np.clip(((X - x0) * dx + (Y - y0) * dy) / L, 0, 1)
    return np.hypot(X - (x0 + t * dx), Y - (y0 + t * dy)) - hw


def route_one(board, net, a, b, ignore_tracks=False, margin=8, protect=()):
    """Return (items, conflicting nets).  With ignore_tracks, other nets'
    unlocked (router-made) tracks/vias are not obstacles; the nets they belong
    to are reported so the caller can rip them up."""
    cls = NETCLASS.get(net, 'Default')
    w, c = WIDTH[cls], CLEAR[cls]
    # a finger's anchor sits in the finger strip (fingers only): aim for its neck instead,
    # which runs up to y = Y1 - 10 (make_edge_fp.py) -- TAB_Y - 1 is on the neck
    a = a if a[2] < G.TAB_Y - 1.0 else (a[0], a[1], G.TAB_Y - 1.0, a[3], a[4])
    b = b if b[2] < G.TAB_Y - 1.0 else (b[0], b[1], G.TAB_Y - 1.0, b[3], b[4])
    x0 = max(G.X0, min(a[1], b[1]) - margin); x1 = min(G.X1, max(a[1], b[1]) + margin)
    y0 = max(G.Y0, min(a[2], b[2]) - margin); y1 = min(G.TAB_Y, max(a[2], b[2]) + margin)
    xs = np.arange(x0, x1 + RES / 2, RES); ys = np.arange(y0, y1 + RES / 2, RES)
    X, Y = np.meshgrid(xs, ys)
    need_t = c + w / 2 + MARGIN
    need_v = c + VIA_D / 2 + MARGIN
    free = {L: np.ones(X.shape, bool) for L in RLAYERS}
    vfree = np.ones(X.shape, bool)
    edge = dist_field('poly', G.OUTLINE, X, Y)       # 0 inside, so measure the complement
    inside = edge == 0
    edge = np.where(inside, -dist_field('poly_edges', G.OUTLINE, X, Y), edge)
    for L in RLAYERS:
        free[L] &= (-edge > 0.25 + w / 2) & (Y < G.TAB_Y)
    vfree &= (-edge > 0.5 + VIA_D / 2) & (Y < G.TAB_Y - VIA_D / 2)
    for (hx, hy, hd) in G.HOLES:
        free_h = np.hypot(X - hx, Y - hy) > hd / 2 + 0.3 + w / 2
        for L in RLAYERS:
            free[L] &= free_h
        vfree &= np.hypot(X - hx, Y - hy) > hd / 2 + 0.3 + VIA_D / 2
    u1 = [e for e in board if isinstance(e, list) and e and e[0] == 'footprint'
          and any(isinstance(p, list) and p and p[0] == 'property' and p[1] == 'Reference' and p[2] == 'U1' for p in e)][0]
    ua = find(u1, 'at'); ux_, uy_ = float(ua[1]), float(ua[2])
    under = (np.abs(X - ux_) < G.UNDER) & (np.abs(Y - uy_) < G.UNDER)
    for L in ('F.Cu',):   # nothing new on F.Cu under the RP2354A (DVDD stubs, EP vias)
        free[L] &= ~under
    vfree &= ~under
    for e in board:     # rule areas that forbid tracks (e.g. under the RP2354A)
        if isinstance(e, list) and e and e[0] == 'zone' and find(e, 'keepout') \
                and find(find(e, 'keepout'), 'tracks') and find(find(e, 'keepout'), 'tracks')[1] == 'not_allowed':
            pts = [(float(q[1]), float(q[2])) for q in find(find(e, 'polygon'), 'pts')[1:]]
            d = dist_field('poly', pts, X, Y)
            L = str(find(e, 'layer')[1])
            if L in free:
                free[L] &= d > w / 2 + 0.05
            vfree &= d > VIA_D / 2 + 0.05
    soft, own_copper = [], []
    # only copper near the search window matters: cull the rest before rasterising
    pad_ = need_v + 1.0
    def near(kind, g):
        if kind == 'rect':
            cx, cy, hw, hh = g; bx0, by0, bx1, by1 = cx - hw, cy - hh, cx + hw, cy + hh
        elif kind == 'circ':
            cx, cy, r = g; bx0, by0, bx1, by1 = cx - r, cy - r, cx + r, cy + r
        elif kind == 'poly':
            bx0, by0 = min(p[0] for p in g), min(p[1] for p in g); bx1, by1 = max(p[0] for p in g), max(p[1] for p in g)
        else:
            sx0, sy0, sx1, sy1, hw = g
            bx0, by0, bx1, by1 = min(sx0, sx1) - hw, min(sy0, sy1) - hw, max(sx0, sx1) + hw, max(sy0, sy1) + hw
        return bx1 >= x0 - pad_ and bx0 <= x1 + pad_ and by1 >= y0 - pad_ and by0 <= y1 + pad_
    for (L, n, kind, g, npth, rid) in copper(board):
        if not near(kind, g):
            continue
        if n == net and not npth:
            own_copper.append((L, kind, g))
            if kind in ('circ', 'rect') and rid is None:
                # hole spacing to same-net vias, and no via inside or against a same-net pad
                # (an untented via in or at an SMD pad wicks the solder away): 0.2 mm mask dam
                vfree &= dist_field(kind, g, X, Y) > VIA_D / 2 + (0.2 if kind == 'rect' else 0.05)
            continue
        if ignore_tracks and rid is not None and n not in protect:
            soft.append((L, n, kind, g))
            continue
        d = dist_field(kind, g, X, Y)
        if npth:
            vfree &= d > 0.3 + VIA_D / 2
            for LL in RLAYERS:
                free[LL] &= d > 0.25 + w / 2
            continue
        if L in free:
            free[L] &= d > need_t
        if kind == 'poly' and n != 'DVDD':
            continue        # a big island's FILL re-pours around a via: only tracks must stay off it
            # (the small DVDD island under the RP is kept whole: vias stay out of it)
        vfree &= d > need_v     # a via crosses every layer, In2 tracks included
    # escape lanes in front of other nets' fine-pitch pins (as fanout.py keeps
    # them): no vias and no crossing tracks in the first 1.2 mm
    pads_, _ = G.board_pads(board)
    # the endpoints' own footprints are exempt from the lane rule: reaching a 0.5 mm-pitch
    # pad along its axis necessarily runs beside its siblings' lanes (their axes stay free)
    own = {re.search(r' of (\S+) ', s).group(1) for s in (a[4], b[4]) if re.search(r' of (\S+) ', s)}
    # ... for TRACKS.  A via next to one's own pin walls in the neighbours (0.4 mm pitch: there
    # is no via spot between two lanes), so the via rule still applies to the siblings: the pin's
    # via belongs beyond the lane ends, in the column between the fan-out vias and the ring
    # every narrow SMD pin gets a lane: 0.4/0.5 mm-pitch QFN/TSOP pins and 0.6 mm-wide SOIC
    # pins (0603 passives, 0.9 mm wide, do not); without it a pin boxed in by a neighbour's
    # track had no via spot at all once vias inside pads were ruled out
    for q in pads_:
        if q.th or q.net in (None, net) or min(q.hw, q.hh) > 0.3 or 'F.Cu' not in q.layers:
            continue
        # own-footprint tracks may run beside sibling lanes only at 0.4/0.5 mm pitch (there is no
        # other way to reach such a pad); a SOIC pin is entered along its own lane
        # (with --neck, 0.15 mm tracks at 0.12 mm clearance fit along their own axis without touching
        # the siblings' lanes, so there is no exemption -- and the lanes hold in every pass: a track
        # drifting across a 0.4 mm-pitch neighbour's lane end is what walls that neighbour in)
        exempt_tracks = q.ref in own and min(q.hw, q.hh) <= 0.15 and not NECK
        fx, fy = q.fp_xy
        # track lanes only while pre-routing (locked copper must not wall in a pin's
        # escape); in the final pass a crossing track is DRC's business, and 0.4 mm-pitch
        # neighbours could never be reached otherwise
        for length, target in ((1.2, 'via'),) + (((1.2, 'track'),) if (ONLY or NECK) and not exempt_tracks else ()):
            if q.hh > q.hw:
                sg = 1 if q.cy > fy else -1
                ya, yb = sorted((q.cy + sg * q.hh, q.cy + sg * (q.hh + length)))
                g = (q.cx, (ya + yb) / 2, q.hw + 0.05, (yb - ya) / 2)
            else:
                sg = 1 if q.cx > fx else -1
                xa, xb = sorted((q.cx + sg * q.hw, q.cx + sg * (q.hw + length)))
                g = ((xa + xb) / 2, q.cy, (xb - xa) / 2, q.hh + 0.05)
            d = dist_field('rect', g, X, Y)
            if target == 'via':
                vfree &= d > VIA_D / 2 + 0.05
            else:
                free['F.Cu'] &= d > w / 2 + 0.05
    # the net's own copper is always walkable, whatever masked the cells (an endpoint can
    # be a router leftover ending under the RP or inside a keep-out: walk it back to the pad)
    for (L, kind, g) in own_copper:
        d = dist_field(kind, g, X, Y)
        for L2 in (RLAYERS if kind == 'circ' else [L]):
            if L2 in free:
                free[L2] |= d <= 0
    for L in RLAYERS:
        vfree &= free[L]
    # rip-up mode: other nets' router copper is passable at a price, not free
    pen = {L: np.zeros(X.shape, np.float32) for L in RLAYERS}
    vpen = np.zeros(X.shape, np.float32)
    for (L, n, kind, g) in soft:
        d = dist_field(kind, g, X, Y)
        if L in pen:
            pen[L][d <= need_t] = RIP_PEN
        vpen[d <= need_v] = RIP_PEN

    def cell(x, y):
        return int(round((y - y0) / RES)), int(round((x - x0) / RES))
    (sy, sx), (ty, tx) = cell(a[1], a[2]), cell(b[1], b[2])
    H, W = X.shape
    if not (0 <= sy < H and 0 <= sx < W and 0 <= ty < H and 0 <= tx < W):
        return None, set()       # an endpoint outside the routable body (tab, off-board)
    starts = [(sy, sx, L) for L in a[3]]
    goals = {(ty, tx, L) for L in b[3]}
    # the endpoints sit on same-net copper; open a small disc around each
    for (cy, cx, L) in starts + list(goals):
        free[L][max(cy - 2, 0):cy + 3, max(cx - 2, 0):cx + 3] = True
    
    h = lambda y, x: RES * math.hypot(y - ty, x - tx)
    pq, best, prev = [], {}, {}
    for s in starts:
        best[s] = 0.0
        heapq.heappush(pq, (h(s[0], s[1]), 0.0, s))
    moves = [(dy, dx, RES * math.hypot(dy, dx)) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    found = None
    while pq:
        f, gcost, s = heapq.heappop(pq)
        if s in goals:
            found = s
            break
        if gcost > best.get(s, 1e18):
            continue
        y, x, L = s
        nbrs = []
        for dy, dx, cst in moves:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and free[L][ny, nx]:
                if dy and dx and not (free[L][y, nx] and free[L][ny, x]):
                    continue
                nbrs.append(((ny, nx, L), cst + float(pen[L][ny, nx])))
        if vfree[y, x]:
            for L2 in RLAYERS:
                if L2 != L:
                    nbrs.append(((y, x, L2), VIA_COST * RES + float(vpen[y, x])))
        for ns, cst in nbrs:
            ng = gcost + cst
            if ng < best.get(ns, 1e18):
                best[ns] = ng
                prev[ns] = s
                heapq.heappush(pq, (ng + h(ns[0], ns[1]), ng, ns))
    if not found:
        return None, set()
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    hit = set()         # filled in below, from the copper actually produced
    # split into same-layer runs (a via between runs), then string-pull each
    # run: keep a straight shot whenever every sample along it is a free cell
    runs, vias = [[path[0]]], []
    for p in path[1:]:
        if p[2] != runs[-1][-1][2]:
            vias.append(runs[-1][-1])
            runs.append([p])
        else:
            runs[-1].append(p)

    def clear(p, q):
        L = p[2]
        n = max(2, int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) * 2))
        for i in range(n + 1):
            t = i / n
            yy = int(round(p[0] + (q[0] - p[0]) * t)); xx = int(round(p[1] + (q[1] - p[1]) * t))
            if not free[L][yy, xx] or pen[L][yy, xx] > 0:
                return False
        return True
    segs = []
    for r in runs:
        i = 0
        pts = [r[0]]
        while i < len(r) - 1:
            j = len(r) - 1
            while j > i + 1 and not clear(r[i], r[j]):
                j -= 1
            pts.append(r[j])
            i = j
        segs += [[pts[k], pts[k + 1]] for k in range(len(pts) - 1)]
    xy = lambda s: (round(x0 + s[1] * RES, 4), round(y0 + s[0] * RES, 4))
    if soft:
        # which other nets does this copper actually touch: sample every straightened
        # segment on its layer, and test every via against all layers (it crosses them all)
        pts = {L: [] for L in RLAYERS}
        for r in segs:
            (ay, ax), (by, bx) = r[0][:2], r[-1][:2]
            n = max(2, int(max(abs(by - ay), abs(bx - ax)) * 2))
            for i in range(n + 1):
                t = i / n
                pts[r[0][2]].append((x0 + (ax + (bx - ax) * t) * RES, y0 + (ay + (by - ay) * t) * RES))
        vx_ = np.array([x0 + v[1] * RES for v in vias]); vy_ = np.array([y0 + v[0] * RES for v in vias])
        for (L, n, kind, g) in soft:
            if pts.get(L):
                px = np.array([q[0] for q in pts[L]]); py = np.array([q[1] for q in pts[L]])
                if (dist_field(kind, g, px, py) < need_t).any():
                    hit.add(n)
                    continue
            if len(vx_) and (dist_field(kind, g, vx_, vy_) < need_v).any():
                hit.add(n)
    out = []
    for r in segs:
        if len(r) >= 2 and r[0][:2] != r[-1][:2]:
            (ax, ay), (bx, by) = xy(r[0]), xy(r[-1])
            out.append(['segment', ['start', ax, ay], ['end', bx, by], ['width', w], ['layer', Q(r[0][2])]]
                       + ([['locked', 'yes']] if LOCK else []) + [['net', Q(net)], ['uuid', Q(str(uuid.uuid4()))]])
    for v in vias:
        vx, vy = xy(v)
        out.append(['via', ['at', vx, vy], ['size', VIA_D], ['drill', VIA_DRILL], ['layers', Q('F.Cu'), Q('B.Cu')]]
                   + ([['locked', 'yes']] if LOCK else []) + [['net', Q(net)], ['uuid', Q(str(uuid.uuid4()))]])
    # tie the grid-snapped ends onto the exact item anchors
    for (px, py, L), s in (((a[1], a[2], path[0][2]), path[0]), ((b[1], b[2], path[-1][2]), path[-1])):
        sx_, sy_ = xy(s)
        if (round(px, 4), round(py, 4)) != (sx_, sy_):
            out.append(['segment', ['start', round(px, 4), round(py, 4)], ['end', sx_, sy_], ['width', w],
                        ['layer', Q(L)]] + ([['locked', 'yes']] if LOCK else [])
                       + [['net', Q(net)], ['uuid', Q(str(uuid.uuid4()))]])
    return out, hit


def remove_dangling():
    """Drop vias/track stubs DRC reports as dangling (router leftovers)."""
    fn = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-rev1-finish2.json')
    removed = 0
    for _ in range(5):
        subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--format', 'json', '-o', fn, PCB], capture_output=True)
        ids = {it['uuid'] for v in json.load(open(fn)).get('violations', [])
               if v['type'] in ('via_dangling', 'track_dangling') for it in v['items']}
        if not ids:
            break
        board = parse(open(PCB).read())
        keep = [e for e in board if not (isinstance(e, list) and e and e[0] in ('via', 'segment')
                                         and find(e, 'uuid') and str(find(e, 'uuid')[1]) in ids
                                         and not find(e, 'locked'))]
        removed += len(board) - len(keep)
        open(PCB, 'w').write(dump(keep) + '\n')
    return removed


def fill():
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)


def force_route():
    global LOCK
    LOCK = True
    ripped = set()
    for _ in range(20):
        todo = [(a, b) for a, b in drc_unconnected() if a[0] in FORCE and 'Zone' not in a[4] + b[4]]
        if not todo:
            break
        a, b = todo[0]
        board = parse(open(PCB).read())
        items, hit = route_one(board, a[0], a, b, ignore_tracks=True, margin=12)
        if items is None:
            print('finish_route: --force: no path for %s' % a[0])
            break
        board = [e for e in board if not (isinstance(e, list) and e and e[0] in ('segment', 'via')
                                          and not find(e, 'locked') and find(e, 'net')
                                          and str(find(e, 'net')[1]) in hit)]
        k = max(k for k, e in enumerate(board) if isinstance(e, list) and e and e[0] in ('segment', 'via', 'footprint'))
        board[k + 1:k + 1] = items
        open(PCB, 'w').write(dump(board) + '\n')
        ripped |= hit
        print('finish_route: --force routed %s (locked), ripped %s' % (a[0], ', '.join(sorted(hit)) or '-'))
    fill()
    return ripped


def main():
    fill()                  # the finisher reads the small pours' filled copper
    if FORCE:
        force_route()
        return 0
    n = remove_dangling()
    if n:
        print('finish_route: removed %d dangling via/track items' % n)
    todo = drc_unconnected()
    if not todo:
        print('finish_route: nothing to do')
        if n:
            import pcbnew
            b = pcbnew.LoadBoard(PCB)
            pcbnew.ZONE_FILLER(b).Fill(b.Zones())
            pcbnew.SaveBoard(PCB, b)
        return 0
    def insert(board, items):
        k = max(k for k, e in enumerate(board) if isinstance(e, list) and e and e[0] in ('segment', 'via', 'footprint'))
        board[k + 1:k + 1] = items

    done, failed = 0, set()
    for _ in range(60):
        todo = [(a, b) for a, b in drc_unconnected()
                if 'Zone' not in a[4] and 'Zone' not in b[4] and (a[4], b[4]) not in failed
                and (ONLY is None or a[0] in ONLY)]
        if ONLY:   # priority order = the order given on the command line
            todo.sort(key=lambda ab: ONLY.index(ab[0][0]))
        if not todo:
            break
        a, b = todo[0]
        net = a[0]
        board = parse(open(PCB).read())
        items, _ = route_one(board, net, a, b)
        if items is None:   # maybe it needs a long detour: widen the search (the whole board
            # in the final pass; a bounded window while pre-routing, where a far-apart pair
            # of a plane net is Freerouting's job, not a minutes-long A* over 4 M cells)
            items, _ = route_one(board, net, a, b, margin=40)
        if items is not None:
            insert(board, items)
            open(PCB, 'w').write(dump(board) + '\n')
            done += 1
            print('finish_route: routed %s (%d items)' % (net, len(items)))
            continue
        # transactional rip-up: keep it only if every ripped net comes back
        items, hit = (None, set()) if ONLY else route_one(board, net, a, b, ignore_tracks=True)
        if items is None:
            print('finish_route: NO PATH for %s even with rip-up' % net)
            failed.add((a[4], b[4]))
            continue
        before = len(drc_unconnected())
        snapshot = open(PCB).read()
        board = [e for e in board if not (isinstance(e, list) and e and e[0] in ('segment', 'via')
                                          and not find(e, 'locked') and find(e, 'net')
                                          and str(find(e, 'net')[1]) in hit)]
        insert(board, items)
        open(PCB, 'w').write(dump(board) + '\n')
        ok = True
        ripped = set(hit)           # every net ripped in this transaction (each at most once)
        for _ in range(40):
            victims = [(x, y) for x, y in drc_unconnected() if x[0] in ripped]
            if not victims:
                break
            va, vb = victims[0]
            board = parse(open(PCB).read())
            items, _ = route_one(board, va[0], va, vb)
            if items is None:
                ok = False
                break
            insert(board, items)
            open(PCB, 'w').write(dump(board) + '\n')
        hit = ripped
        after = len(drc_unconnected())
        if ok and after < before:
            done += 1
            print('finish_route: routed %s by ripping up %s (%d -> %d open)' % (net, ', '.join(sorted(hit)), before, after))
        else:
            open(PCB, 'w').write(snapshot)
            failed.add((a[4], b[4]))
            print('finish_route: rip-up for %s did not pay off (%s); reverted' % (net, ', '.join(sorted(hit))))
    if ONLY is None:
        remove_dangling()
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    left = len([1 for a, b in drc_unconnected() if ONLY is None or a[0] in ONLY])
    print('finish_route: %d routed, %d still unconnected%s' % (done, left, ' (of those nets)' if ONLY else ''))
    return 1 if left else 0


if __name__ == '__main__':
    sys.exit(main())
