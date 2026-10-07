#!/usr/bin/env python3
"""Tidy router artifacts in FujiNet-7800-Rev0.kicad_pcb without changing
the routing topology:

  1. tiny segments (< 0.05 mm) collapse onto their pad/via end, neighbours re-joined
  2. fold-backs: a segment lying collinear on, and inside, another segment of
     the same net/layer (and no wider) is dropped
  3. collinear merge: two same-width segments meeting at a free point (no pad,
     no via, nothing else there) in a straight line become one
  4. acute corners (< 90 deg) at a free point: straightened A->B when that
     stays clear of other nets, otherwise chamfered 0.3 mm back on each leg

Each step is applied, zones are refilled and KiCad's DRC is run; a step that
adds any DRC error is reverted.  Usage: python3 tools/tidy_tracks.py
"""
import json, math, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tmpdir import tmp
from sexpr import parse, dump, find
import gen_pcb as G

PCB = G.PCB
EPS = 1e-3


def drc_errors():
    fn = tmp('tidy.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--schematic-parity', '--format', 'json', '-o', fn, PCB],
                   capture_output=True)
    d = json.load(open(fn))
    errs = sum(1 for v in d.get('violations', []) if v['severity'] == 'error')
    return errs + len(d.get('unconnected_items', [])) + len(d.get('schematic_parity', []))


def refill():
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)


def pt(e, k):
    q = find(e, k)
    return (float(q[1]), float(q[2]))


def setpt(e, k, p):
    q = find(e, k)
    q[1], q[2] = round(p[0], 4), round(p[1], 4)


def seginfo(e):
    return pt(e, 'start'), pt(e, 'end'), str(find(e, 'layer')[1]), str(find(e, 'net')[1]), float(find(e, 'width')[1])


def same(a, b):
    return abs(a[0] - b[0]) < EPS and abs(a[1] - b[1]) < EPS


def anchors(board):
    """(net, point) test: is there a pad or via of this net at the point?"""
    pads, _ = G.board_pads(board)
    vias = [(pt(e, 'at'), str(find(e, 'net')[1])) for e in board if isinstance(e, list) and e and e[0] == 'via']

    def at_anchor(net, p, layer):
        for (vp, vn) in vias:
            if vn == net and math.hypot(vp[0] - p[0], vp[1] - p[1]) < 0.35:
                return True
        for q in pads:
            if q.net == net and (q.th or layer in q.layers) and q.dist(p[0], p[1]) < EPS:
                return True
        return False
    return at_anchor


def same_pad(board, net, L, a, b):
    pads, _ = G.board_pads(board)
    return any(q.net == net and (q.th or L in q.layers) and q.dist(*a) < EPS and q.dist(*b) < EPS for q in pads)


def segments(board):
    return [e for e in board if isinstance(e, list) and e and e[0] == 'segment']


def ends_map(segs):
    m = {}
    for e in segs:
        a, b, L, n, w = seginfo(e)
        for k, p in (('start', a), ('end', b)):
            m.setdefault((n, L, round(p[0], 3), round(p[1], 3)), []).append((e, k))
    return m


def step_zero(board, only=None):
    """Collapse segments shorter than 0.05 mm onto one end: the end sitting in a
    pad/via if there is one, else the start.  Other same-net ends at the
    dropped point are moved onto the kept one.  only=uuid limits it to one."""
    at_anchor = anchors(board)
    n = 0
    for e in list(segments(board)):
        if e not in board or (only and str(find(e, 'uuid')[1]) != only):
            continue
        a, b, L, net, w = seginfo(e)
        if math.hypot(b[0] - a[0], b[1] - a[1]) >= 0.05:
            continue
        ka, kb = at_anchor(net, a, L), at_anchor(net, b, L)
        if ka and kb and math.hypot(b[0] - a[0], b[1] - a[1]) > 0.01:
            if same_pad(board, net, L, a, b):
                board.remove(e)     # lies wholly inside one pad: pure redundancy
                n += 1
            continue            # else it joins two different anchors: leave it
        keep, drop = (b, a) if (kb and not ka) else (a, b)
        for f in segments(board):
            if f is e:
                continue
            fa, fb, fL, fn, _ = seginfo(f)
            if fn == net and fL == L:
                if same(fa, drop):
                    setpt(f, 'start', keep)
                if same(fb, drop):
                    setpt(f, 'end', keep)
        board.remove(e)
        n += 1
    return n


def on_segment(p, a, b, tol=EPS):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    if L == 0:
        return same(p, a)
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L
    if t < -EPS or t > 1 + EPS:
        return False
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy)) < tol


def step_foldback(board):
    n = 0
    segs = segments(board)
    dead = set()
    for e in segs:
        if id(e) in dead:
            continue
        a, b, L, net, w = seginfo(e)
        for f in segs:
            if f is e or id(f) in dead:
                continue
            fa, fb, fL, fn, fw = seginfo(f)
            if fn == net and fL == L and fw >= w and on_segment(a, fa, fb) and on_segment(b, fa, fb):
                dead.add(id(e))
                n += 1
                break
    board[:] = [e for e in board if id(e) not in dead]
    return n


def free_corners(board):
    at_anchor = anchors(board)
    m = ends_map(segments(board))
    vias_pts = [pt(e, 'at') for e in board if isinstance(e, list) and e and e[0] == 'via']
    for (net, L, x, y), lst in m.items():
        if len(lst) != 2 or at_anchor(net, (x, y), L):
            continue
        # a T-junction (another same-net track passing through) is not free either
        others = [s for s in segments(board) if s is not lst[0][0] and s is not lst[1][0]]
        if any(seginfo(s)[3] == net and seginfo(s)[2] == L and on_segment((x, y), *seginfo(s)[:2]) for s in others):
            continue
        yield (net, L, (x, y)), lst


def step_merge(board):
    n = 0
    changed = True
    while changed:
        changed = False
        for (net, L, p), [(e, ke), (f, kf)] in free_corners(board):
            if abs(seginfo(e)[4] - seginfo(f)[4]) > EPS:
                continue
            a = pt(e, 'end' if ke == 'start' else 'start')
            b = pt(f, 'end' if kf == 'start' else 'start')
            cross = (p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0])
            dot = (p[0] - a[0]) * (b[0] - p[0]) + (p[1] - a[1]) * (b[1] - p[1])
            if abs(cross) < 1e-4 and dot > 0:
                setpt(e, ke, b)
                board.remove(f)
                n += 1
                changed = True
                break
    return n


def clear_line(board, net, L, a, b, w):
    import finish_route as FR
    k = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
    X = np.array([a[0] + (b[0] - a[0]) * i / k for i in range(k + 1)])
    Y = np.array([a[1] + (b[1] - a[1]) * i / k for i in range(k + 1)])
    for (l2, n2, kind, g, npth, rid) in FR.copper(board):
        if l2 != L or n2 == net:
            continue
        if (FR.dist_field(kind, g, X, Y) < 0.15 + w / 2 + 0.01).any():
            return False
    return True


def step_acute(board):
    n = 0
    changed = True
    while changed:
        changed = False
        for (net, L, p), [(e, ke), (f, kf)] in free_corners(board):
            a = pt(e, 'end' if ke == 'start' else 'start')
            b = pt(f, 'end' if kf == 'start' else 'start')
            v1, v2 = (a[0] - p[0], a[1] - p[1]), (b[0] - p[0], b[1] - p[1])
            n1, n2 = math.hypot(*v1), math.hypot(*v2)
            if n1 < EPS or n2 < EPS:
                continue
            ang = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))))
            if ang >= 89.5:
                continue
            w = max(seginfo(e)[4], seginfo(f)[4])
            if clear_line(board, net, L, a, b, w):
                setpt(e, ke, b)
                board.remove(f)
            else:
                d = min(0.3, n1 / 2, n2 / 2)
                p1 = (p[0] + v1[0] / n1 * d, p[1] + v1[1] / n1 * d)
                p2 = (p[0] + v2[0] / n2 * d, p[1] + v2[1] / n2 * d)
                setpt(e, ke, p1)
                setpt(f, kf, p2)
                chamfer = [x if not (isinstance(x, list) and x and x[0] in ('start', 'end', 'uuid')) else x
                           for x in e]
                import copy, uuid
                c = copy.deepcopy(e)
                setpt(c, 'start', p1)
                setpt(c, 'end', p2)
                find(c, 'uuid')[1] = str(uuid.uuid4())
                board.insert(board.index(e) + 1, c)
            n += 1
            changed = True
            break
    return n


def short_ids():
    b = parse(open(PCB).read())
    return [str(find(e, 'uuid')[1]) for e in segments(b)
            if math.hypot(pt(e, 'end')[0] - pt(e, 'start')[0], pt(e, 'end')[1] - pt(e, 'start')[1]) < 0.05]


def main():
    base = drc_errors()
    print('tidy_tracks: DRC errors before: %d' % base)
    kept = rev = 0
    for sid in short_ids():     # one at a time: each collapse must keep DRC clean
        before = open(PCB).read()
        board = parse(before)
        if not step_zero(board, only=sid):
            continue
        open(PCB, 'w').write(dump(board) + '\n')
        refill()
        if drc_errors() > base:
            open(PCB, 'w').write(before)
            rev += 1
        else:
            kept += 1
    print('tidy_tracks: %-16s %d collapsed, %d left (would break DRC)' % ('tiny segments', kept, rev))
    for name, step in (('fold-back', step_foldback),
                       ('collinear merge', step_merge), ('acute corners', step_acute)):
        before = open(PCB).read()
        board = parse(before)
        n = step(board)
        if not n:
            print('tidy_tracks: %-16s nothing to do' % name)
            continue
        open(PCB, 'w').write(dump(board) + '\n')
        refill()
        e = drc_errors()
        if e > base:
            open(PCB, 'w').write(before)
            print('tidy_tracks: %-16s %d edits REVERTED (DRC errors %d -> %d)' % (name, n, base, e))
        else:
            print('tidy_tracks: %-16s %d edits' % (name, n))
            base = e
    refill()
    print('tidy_tracks: DRC errors after: %d' % drc_errors())


if __name__ == '__main__':
    main()
