#!/usr/bin/env python3
"""Move reference designators that KiCad's DRC reports on copper or on other
silkscreen (silk_over_copper / silk_overlap) to the nearest free spot beside
their footprint.  Board text, outlines and other fields are never moved; a
reference with no free spot anywhere near its part is hidden (it stays on the
Fab layer) and listed.  Saves through pcbnew, so the file keeps KiCad's own
formatting; only the moved fields change.

Usage: python3 tools/fix_silk.py [board]
"""
from tmpdir import tmp
import json, os, re, subprocess, sys, tempfile
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else \
    os.path.join(os.path.dirname(HERE), 'FujiNet-SMS-Rev0.kicad_pcb')
KINDS = ('silk_over_copper', 'silk_overlap')
MM = pcbnew.FromMM
CLR = MM(0.15)          # kept from pads, other silk and text
EDGE_CLR = MM(0.4)      # kept from the board outline
GAPS = [0.15, 0.4, 0.8, 1.2]       # mm between the part and the text
SLIDES = [0, -0.4, 0.4, -0.8, 0.8]  # mm along the side


def items(seq):
    return [seq[i] for i in range(len(seq))]   # SWIG iterators break on Python 3.14


def drc():
    fn = tmp('silk.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '-o', fn, PCB], capture_output=True)
    return [v for v in json.load(open(fn)).get('violations', []) if v['type'] in KINDS]


def offenders(violations, board):
    """Reference fields to move: the ref on copper; of two colliding refs, the smaller part's."""
    def ref_of(desc):
        m = re.match(r'Reference field of (\S+)', desc)
        return m and m.group(1)
    area = lambda r: board.FindFootprintByReference(r).GetBoundingBox(False).GetArea()
    out = set()
    for v in violations:
        refs = [r for r in (ref_of(i['description']) for i in v['items']) if r]
        if len(refs) == 2:
            out.add(min(refs, key=area))
        elif refs:
            out.add(refs[0])
    return sorted(out)


def box(item):
    b = item.GetBoundingBox()
    return (b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom())


def obstacles(board, skip):
    """Bounding boxes of front pads (with their mask margin), front silk and visible silk text,
    except the reference field `skip`."""
    obs = []
    for fp in items(board.Footprints()):
        for p in items(fp.Pads()):
            if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask) or p.GetDrillSize().x:
                m = max(p.GetSolderMaskExpansion(pcbnew.F_Mask), 0) if p.IsOnLayer(pcbnew.F_Mask) else 0
                l, t, r, b = box(p)
                obs.append((l - m, t - m, r + m, b + m))
        for g in items(fp.GraphicalItems()):
            if g.GetLayer() == pcbnew.F_SilkS and not (hasattr(g, 'IsVisible') and not g.IsVisible()):
                obs.append(box(g))
        for f in items(fp.GetFields()):
            if f.GetLayer() == pcbnew.F_SilkS and f.IsVisible() and f.m_Uuid.AsString() != skip:
                obs.append(box(f))
    for d in items(board.Drawings()):
        if d.GetLayer() == pcbnew.F_SilkS:
            obs.append(box(d))
    return obs


def hits(b, obs):
    l, t, r, bt = b
    return any(l - CLR < o[2] and o[0] < r + CLR and t - CLR < o[3] and o[1] < bt + CLR for o in obs)


def inside(b, board):
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline, True)
    l, t, r, bt = b
    pts = [(l, t), (r, t), (l, bt), (r, bt), ((l + r) // 2, t), ((l + r) // 2, bt)]
    if not all(outline.Contains(pcbnew.VECTOR2I(int(x), int(y))) for x, y in pts):
        return False
    for d in items(board.Drawings()):          # clear of the outline itself (silk_edge_clearance)
        if d.GetLayer() == pcbnew.Edge_Cuts:
            el, et, er, eb = box(d)
            if l - EDGE_CLR < er and el < r + EDGE_CLR and t - EDGE_CLR < eb and et < bt + EDGE_CLR:
                return False
    return True


def body(fp):
    """Pads plus front silk/courtyard outline, without text."""
    bs = [box(it) for it in items(fp.Pads()) + [g for g in items(fp.GraphicalItems())
                                                 if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_CrtYd)]]
    if not bs:
        return box(fp)
    return (min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs))


def dist(x, y, bx):
    """Distance from a point to a box (0 inside)."""
    dx = max(bx[0] - x, 0, x - bx[2])
    dy = max(bx[1] - y, 0, y - bx[3])
    return (dx * dx + dy * dy) ** 0.5


def place(board, fp, obs, bodies):
    """Nearest free spot beside the part whose label reads as this part's: the text
    centre must be closer to its own part than to any other."""
    ref = fp.Reference()
    l, t, r, b = own = body(fp)
    others = [bx for k, bx in bodies.items() if k != fp.GetReference()]
    cx, cy = (l + r) // 2, (t + b) // 2
    best = None
    for ang in (0, 90):
        ref.SetTextAngleDegrees(ang)
        ref.SetPosition(pcbnew.VECTOR2I(cx, cy))
        tl, tt, tr, tb = box(ref)
        w, h = tr - tl, tb - tt
        for g in GAPS:
            G = MM(g)
            for s in SLIDES:
                S = MM(s)
                for x, y in ((cx + S, t - G - h // 2), (cx + S, b + G + h // 2),
                             (l - G - w // 2, cy + S), (r + G + w // 2, cy + S)):
                    cand = (x - w // 2, y - h // 2, x + w // 2, y + h // 2)
                    if hits(cand, obs) or not inside(cand, board):
                        continue
                    if min(dist(x, y, o) for o in others) <= dist(x, y, own):
                        continue      # would read as a neighbour's label
                    # nearest wins; a turned label costs a little, so upright is preferred
                    cost = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 + (MM(0.3) if ang else 0)
                    if best is None or cost < best[0]:
                        best = (cost, ang, x, y)
            if best:
                break      # nearest gap that fits; don't drift further out
    if best:
        _, ang, x, y = best
        ref.SetTextAngleDegrees(ang)
        ref.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
        return True
    return False


def main():
    moved, hidden = [], []
    for _ in range(3):
        v = drc()
        if not v:
            break
        board = pcbnew.LoadBoard(PCB)
        bodies = {f.GetReference(): body(f) for f in items(board.Footprints())
                  if f.GetLayer() == pcbnew.F_Cu and f.GetReference() != 'J1'}
        for r in offenders(v, board):
            fp = board.FindFootprintByReference(r)
            ref = fp.Reference()
            old = (pcbnew.VECTOR2I(ref.GetPosition()), ref.GetTextAngleDegrees())
            if place(board, fp, obstacles(board, ref.m_Uuid.AsString()), bodies):
                moved.append(r)
            else:
                ref.SetPosition(old[0]); ref.SetTextAngleDegrees(old[1])
                ref.SetVisible(False)
                hidden.append(r)
        board.Save(PCB)
    left = drc()
    print('fix_silk: moved %d refs (%s); hidden %d (%s); %d silk warnings left'
          % (len(set(moved)), ' '.join(sorted(set(moved))), len(hidden), ' '.join(hidden), len(left)))


if __name__ == '__main__':
    main()
