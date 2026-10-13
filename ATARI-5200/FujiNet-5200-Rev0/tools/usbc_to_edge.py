#!/usr/bin/env python3
"""Move the HRO TYPE-C-31-M-12 USB-C (rot 180, mouth to the top edge) onto HRO's board edge, keeping the routing.

HRO's recommended layout puts the PCB edge 5.79 mm in front of the locating pegs, i.e. at footprint
y +3.19: the shell face (+3.65) overhangs it by 0.46 mm, so a plug's overmold clears the board.  The
boards placed the origin 5.0 mm from the edge, the face 1.35 mm inside it, where the overmold meets
the board edge before the plug mates.  Found on FujiNet-NES Rev0, 2026-10-11 (fixed there by hand);
this is the same edit as a script, for a routed board:

  1. the footprint moves by D (toward the edge, to y = edge + 3.2)
  2. its private F.Cu ties (between the pad row and the shield, grown out from the SMD pads: the
     VBUS / D- / GND links and their vias) move with it; a segment that leaves that region keeps
     its far end and has its near end moved (stretched)
  3. an F.Cu stub joins each new SMD pad centre to the old one, where the rest of the routing ends
  4. PATCHES (below) re-draw the few exits that the stretch walks into a shield slot or a pad, or
     that would hug a rear shield slot so closely that its F.Cu thermal keeps a single spoke
     (KiCad's starved_thermal: the zone wants 2)
  5. GND stitch vias (no tracks) that the moved pads, slots or pegs land on are deleted
  6. the footprint's front silk (now past the edge) is dropped and the library's Dwgs.User edge
     line is added, so the board footprint matches the fixed library footprint
  7. moved and new copper is checked (copper 0.15, copper-to-hole 0.25, hole-to-hole 0.25 mm) and the
     board is saved only if all of it clears.  Zones are not refilled: run fill_zones.py next.

Usage: python3 tools/usbc_to_edge.py REF TARGET_Y [--dry-run] [board]
"""
import glob, os, sys
import pcbnew

MM = pcbnew.FromMM
mm = pcbnew.ToMM
V = pcbnew.VECTOR2I
EDGE_TO_ORIGIN = 3.2        # HRO: edge at footprint y +3.19
COURTYARD_HALF_W = 5.32
CLR, HOLE_CLR, HOLE_HOLE = MM(0.15), MM(0.25), MM(0.25)

# board file -> patches, applied after the move and stretch:
#   ('seg', layer, net, original segment (x1, y1, x2, y2), replacement polyline [(x, y), ...]):
#       the polyline replaces the segment; its ends are the segment's ends after the move / stretch,
#       or a new spot for a bend that two patched segments share (nothing else may end there)
#   ('via', net, (x, y), (new x, new y)): the via moves; every segment ending on it follows (stretch)
#   ('drop', 'GND', (x, y)): a GND stitching via (no tracks) in the way of a patch is removed
PATCHES = {
    'FujiNet-SMS-Rev0.kicad_pcb': [
        # the VBUS exit east: stretched, it cuts the rear shield slot and C4; between the slot and the
        # CC2 via it would leave the slot one F.Cu spoke.  The CC2 via moves onto its own bend, and VBUS
        # drops at x 134 onto the original 45 degree line to C4 (the same clearance to C4 as before)
        ('via', '/usb/CC2', (134.1991, 37.9655), (134.6405, 37.9655)),
        ('seg', 'F.Cu', 'VBUS', (137, 43.0688, 132.6195, 38.6883),
         [(137, 43.0688), (134.0, 40.0688), (134.0, 37.2883), (133.6, 36.8883), (132.6195, 36.8883)]),
    ],
    'FujiNet-ChannelF-Rev0.kicad_pcb': [
        # the VBUS exit east: stretched, it cuts the rear shield slot; hugging the slot it would leave it
        # one F.Cu spoke.  It runs down at x 136.9 instead, where an edge-guard GND via stood
        ('drop', 'GND', (137.3, 25.94)),
        ('seg', 'F.Cu', 'VBUS', (137.4908, 27.1153, 135.5844, 25.2089),
         [(137.4908, 27.1153), (136.9, 26.5245), (136.9, 24.0089), (136.3, 23.4089), (135.5844, 23.4089)]),
        ('seg', 'F.Cu', '/usb/CC2', (126.367, 25.2618, 125.2992, 26.3296),
         [(126.367, 23.4618), (125.7004, 23.4618), (125.2992, 23.8626), (125.2992, 26.3296)]),
    ],
    'FujiNet-Astrocade-Rev0.kicad_pcb': [
        # the CC1 run west to R17: stretched it meets R17 pad 2; it drops at x 118.15, between R17 and a
        # strip of pour that keeps the rear shield slot's west F.Cu spoke
        ('seg', 'F.Cu', '/usb/CC1', (118.992, 36.7334, 117.4, 38.325),
         [(118.992, 34.9334), (118.15, 35.7754), (118.15, 37.575), (117.4, 38.325)]),
    ],
    'Fujiversal-Atari2600-Rev1.kicad_pcb': [
        # the B.Cu CC1 run under the connector: the moved peg, a slot and the moved VBUS / CC2 vias land on it
        ('seg', 'B.Cu', 'CC1', (122.25, 36.7092, 121.4854, 35.9446),
         [(122.25, 35.7092), (121.4854, 34.9446)]),
        ('seg', 'B.Cu', 'CC1', (121.4854, 35.9446, 113.8809, 35.9446),
         [(121.4854, 34.9446), (115.0, 34.9446), (114.0, 35.9446), (113.8809, 35.9446)]),
        # the D- exit west, stretched to a shallow diagonal: back to 45 degrees
        ('seg', 'F.Cu', 'UBRG_DM', (115.9561, 33.9318, 113.9439, 33.9318),
         [(115.9561, 32.9318), (114.9561, 33.9318), (113.9439, 33.9318)]),
    ],
}


def die(msg):
    raise SystemExit('usbc_to_edge: ' + msg)


def args():
    a = [x for x in sys.argv[1:] if x != '--dry-run']
    if len(a) not in (2, 3):
        die('usage: usbc_to_edge.py REF TARGET_Y [--dry-run] [board]')
    prj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(a) == 3:
        pcb = os.path.abspath(a[2])
    else:
        boards = glob.glob(os.path.join(prj, '*.kicad_pcb'))
        if len(boards) != 1:
            die('expected one .kicad_pcb in %s, found %d' % (prj, len(boards)))
        pcb = boards[0]
    return a[0], float(a[1]), '--dry-run' in sys.argv, pcb


def top_edge(b, x):
    """y of the Edge.Cuts segment straight above x (the board's top edge there)."""
    ys = []
    for d in b.Drawings():
        if d.GetLayer() != pcbnew.Edge_Cuts or d.GetClass() != 'PCB_SHAPE':
            continue
        d = d.Cast()
        if d.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            continue
        s, e = d.GetStart(), d.GetEnd()
        if s.y == e.y and min(s.x, e.x) <= x <= max(s.x, e.x):
            ys.append(s.y)
    if not ys:
        die('no horizontal Edge.Cuts segment above x %.3f' % mm(x))
    return min(ys)


def uid(t):
    return t.m_Uuid.AsString()


def seg_str(t):
    return '%s %s w%.3f (%.4f, %.4f)-(%.4f, %.4f)' % (t.GetLayerName(), t.GetNetname(), mm(t.GetWidth()),
                                                       mm(t.GetStart().x), mm(t.GetStart().y),
                                                       mm(t.GetEnd().x), mm(t.GetEnd().y))


def via_str(v):
    return 'via %s (%.4f, %.4f)' % (v.GetNetname(), mm(v.GetPosition().x), mm(v.GetPosition().y))


def main():
    ref, target_y, dry, pcb = args()
    b = pcbnew.LoadBoard(pcb)
    fp = b.FindFootprintByReference(ref)
    if fp is None or 'HRO_TYPE-C-31-M-12' not in fp.GetFPIDAsString():
        die('%s is not the HRO TYPE-C-31-M-12' % ref)
    if round(fp.GetOrientationDegrees()) % 360 != 180 or fp.IsFlipped():
        die('%s must be on F.Cu at 180 deg (mouth toward the top edge)' % ref)
    pos = fp.GetPosition()
    edge = top_edge(b, pos.x)
    if abs(target_y - (mm(edge) + EDGE_TO_ORIGIN)) > 0.01:
        die('target y %.3f is not the top edge (%.3f) + %.1f' % (target_y, mm(edge), EDGE_TO_ORIGIN))
    D = MM(target_y) - pos.y
    print('%s: %s at (%.3f, %.3f), top edge y %.3f, target y %.3f, move %.3f mm'
          % (os.path.basename(pcb), ref, mm(pos.x), mm(pos.y), mm(edge), target_y, mm(D)))
    if abs(D) <= MM(0.02):
        print('no change: %s already sits at the edge + %.1f mm' % (ref, EDGE_TO_ORIGIN))
        return
    dv = V(0, D)
    pads = list(fp.Pads())
    smd = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    th = [p for p in pads if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD]
    row = {p.GetPosition().y for p in smd}
    if len(row) != 1:
        die('the SMD pads are not on one row')
    row = row.pop()
    nets = {p.GetNetCode() for p in pads if p.GetNetCode() > 0}
    x0 = pos.x

    def in_R(pt):
        return abs(pt.x - x0) <= MM(COURTYARD_HALF_W) and pt.y < row - MM(0.002)

    def smd_at(pt, net):
        for p in smd:
            if p.GetNetCode() == net and p.HitTest(pt):
                return p
        return None

    tracks = [b.Tracks()[i] for i in range(len(b.Tracks()))]
    segs = [t for t in tracks if t.GetClass() == 'PCB_TRACK']
    vias = [t for t in tracks if t.GetClass() == 'PCB_VIA']
    key = lambda p: (p.x, p.y)

    # ---- 1. translate set: F.Cu ties grown out from the SMD pads, inside R
    T, moved = set(), set()
    grew = True
    while grew:
        grew = False
        for t in segs:
            if uid(t) in T or t.GetLayer() != pcbnew.F_Cu or t.GetNetCode() not in nets:
                continue
            ends = []
            for pt in (t.GetStart(), t.GetEnd()):
                # a pad centre is the pad's; any other point north of the row centre is R's
                p = smd_at(pt, t.GetNetCode())
                if p and (key(pt) == key(p.GetPosition()) or not in_R(pt)):
                    ends.append(('pad', p))
                else:
                    ends.append(('R', None) if in_R(pt) else (None, None))
            if any(k is None for k, _ in ends):
                continue
            (ka, pa), (kb, pb) = ends
            a, c = key(t.GetStart()), key(t.GetEnd())
            linked = ka == 'pad' or kb == 'pad' or a in moved or c in moved
            if not linked:
                continue
            if ka == 'R' or kb == 'R' or key(pa.GetPosition()) != key(pb.GetPosition()):
                T.add(uid(t))
                moved |= {pt for pt, (k, _) in zip((a, c), ends) if k == 'R'}
                grew = True
    tseg = [t for t in segs if uid(t) in T]
    tvia = [v for v in vias if v.GetNetCode() in nets and in_R(v.GetPosition()) and key(v.GetPosition()) in moved]

    # ---- 2. stretch: every other segment (any layer) with one end on a moved point, or in a moved TH pad
    def on_th(pt, t):
        return any(p.GetNetCode() == t.GetNetCode() and p.HitTest(pt) and p.IsOnLayer(t.GetLayer()) for p in th)
    stretch = []
    for t in segs:
        if uid(t) in T:
            continue
        s_in = key(t.GetStart()) in moved or on_th(t.GetStart(), t)
        e_in = key(t.GetEnd()) in moved or on_th(t.GetEnd(), t)
        if s_in or e_in:
            stretch.append((t, s_in, e_in))

    # ---- 3. stubs: SMD pads that non-moved F.Cu still reaches, at the old pad centres
    stubs = {}
    for p in smd:
        c = p.GetPosition()
        touching = [t for t in segs if uid(t) not in T and t.GetLayer() == pcbnew.F_Cu
                    and t.GetNetCode() == p.GetNetCode() and (p.HitTest(t.GetStart()) or p.HitTest(t.GetEnd()))]
        # the stub ends at the old centre: a track reaching into the pad must start there, or join one that does
        central = [t for t in touching if key(c) in (key(t.GetStart()), key(t.GetEnd()))]
        joints = {key(pt) for t in central for pt in (t.GetStart(), t.GetEnd())}
        for t in touching:
            if t not in central and not any(p.HitTest(pt) and key(pt) in joints for pt in (t.GetStart(), t.GetEnd())):
                die('%s pad %s: %s reaches into the pad but not to its centre' % (ref, p.GetNumber(), seg_str(t)))
        if central:
            w = min(t.GetWidth() for t in central)
            k = key(c)
            if k not in stubs or w < stubs[k][1]:
                stubs[k] = (p, w)

    # ---- patches: find the segments by their original coordinates before anything moves
    patches, via_moves = [], []
    tol = MM(0.0006)
    drops = []
    for kind, *pa in PATCHES.get(os.path.basename(pcb), []):
        if kind == 'drop':
            net, (x, y) = pa
            hit = [v for v in vias if v.GetNetname() == net and abs(v.GetPosition().x - MM(x)) <= tol and abs(v.GetPosition().y - MM(y)) <= tol]
            if len(hit) != 1 or net != 'GND' or any(key(hit[0].GetPosition()) in (key(t.GetStart()), key(t.GetEnd())) for t in segs):
                die('patch drop %s (%s, %s): not one free GND via' % (net, x, y))
            drops.append(hit[0])
            continue
        if kind == 'via':
            net, (x, y), (nx, ny) = pa
            hit = [v for v in vias if v.GetNetname() == net and abs(v.GetPosition().x - MM(x)) <= tol and abs(v.GetPosition().y - MM(y)) <= tol]
            if len(hit) != 1:
                die('patch via %s (%s, %s): %d matching vias' % (net, x, y, len(hit)))
            v = hit[0]
            at = key(v.GetPosition())
            ends = [(t, key(t.GetStart()) == at, key(t.GetEnd()) == at) for t in segs
                    if t.GetNetCode() == v.GetNetCode() and at in (key(t.GetStart()), key(t.GetEnd()))]
            via_moves.append((v, V(MM(nx), MM(ny)), ends))
            continue
        layer, net, (x1, y1, x2, y2), poly = pa
        a, c = (MM(x1), MM(y1)), (MM(x2), MM(y2))
        hit = [t for t in segs if t.GetLayerName() == layer and t.GetNetname() == net and
               any(abs(p[0][0] - q.x) <= tol and abs(p[0][1] - q.y) <= tol and abs(p[1][0] - r.x) <= tol and abs(p[1][1] - r.y) <= tol
                   for p, q, r in (((a, c), t.GetStart(), t.GetEnd()), ((c, a), t.GetStart(), t.GetEnd())))]
        if len(hit) != 1:
            die('patch %s %s (%s, %s)-(%s, %s): %d matching segments' % (layer, net, x1, y1, x2, y2, len(hit)))
        patches.append((hit[0], poly))

    # ---- apply
    fp.Move(dv)
    for t in tseg:
        t.Move(dv)
    for v in tvia:
        v.Move(dv)
    for t, s_in, e_in in stretch:
        if s_in:
            t.SetStart(t.GetStart() + dv)
        if e_in:
            t.SetEnd(t.GetEnd() + dv)
    for v in drops:
        print('  patch   delete %s' % via_str(v))
        b.Remove(v)
    vmoved, zero = [], []
    for v, to, ends in via_moves:
        print('  patch   %s -> (%.4f, %.4f)' % (via_str(v), mm(to.x), mm(to.y)))
        v.SetPosition(to)
        vmoved.append(v)
        for t, s_at, e_at in ends:
            if s_at:
                t.SetStart(to)
            if e_at:
                t.SetEnd(to)
            if key(t.GetStart()) == key(t.GetEnd()):
                zero.append(t)
            else:
                vmoved.append(t)
    for t in zero:
        print('  delete  %s (zero length after the via move)' % seg_str(t))
        b.Remove(t)
    new = []
    for (cx, cy), (p, w) in sorted(stubs.items()):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(cx, cy) + dv)
        t.SetEnd(V(cx, cy))
        t.SetWidth(w)
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(p.GetNet())
        b.Add(t)
        new.append(t)
    # a polyline end meets its segment's (moved) end, or moves a junction that two patched segments
    # share -- then both polylines must end on the same new point
    near = lambda p, q: abs(p.x - q.x) <= tol and abs(p.y - q.y) <= tol
    polys = [[V(MM(x), MM(y)) for x, y in poly] for _, poly in patches]
    for n, (old, poly) in enumerate(patches):
        pts = polys[n]
        for i in (0, -1):
            hit = [q for q in (old.GetStart(), old.GetEnd()) if near(q, pts[i])]
            if len(hit) == 1:
                pts[i] = V(hit[0].x, hit[0].y)      # the table is in 0.1 um: snap onto the exact end
                continue
            other_end = old.GetEnd() if near(old.GetStart(), pts[-1 - i]) else old.GetStart()
            shared = [m for m, (o, _) in enumerate(patches) if m != n and
                      any(key(e) == key(other_end) for e in (o.GetStart(), o.GetEnd())) and
                      any(near(e, pts[i]) for e in (polys[m][0], polys[m][-1]))]
            if len(shared) != 1:
                die('patch %s: polyline ends %s do not meet the moved segment %s' % (old.GetNetname(), poly, seg_str(old)))
            others_at = [t for t in tracks if uid(t) not in {uid(o) for o, _ in patches} and
                         (key(t.GetPosition()) == key(other_end) if t.GetClass() == 'PCB_VIA'
                          else key(other_end) in (key(t.GetStart()), key(t.GetEnd())))]
            if others_at:
                die('patch %s: the junction (%.4f, %.4f) also joins %d other items' % (old.GetNetname(), mm(other_end.x), mm(other_end.y), len(others_at)))
    for (old, poly), pts in zip(patches, polys):
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(a)
            t.SetEnd(c)
            t.SetWidth(old.GetWidth())
            t.SetLayer(old.GetLayer())
            t.SetNet(old.GetNet())
            b.Add(t)
            new.append(t)
        print('  patch   %s -> %d segments' % (seg_str(old), len(pts) - 1))
        b.Remove(old)
    patched = {uid(o) for o, _ in patches}

    # ---- 5. GND stitch vias under the moved pads, slots and pegs
    gone = patched | {uid(t) for t in zero} | {uid(v) for v in drops}
    moved_items = [t for t in tseg if uid(t) not in gone] + tvia + \
                  [t for t, _, _ in stretch if uid(t) not in gone] + new + \
                  [t for t in vmoved if uid(t) not in gone]
    moved_ids = {uid(t) for t in moved_items}
    holes = [p for p in pads if p.HasHole()]
    gnd = b.GetNetcodeFromNetname('GND')
    ends_at = {}
    for t in segs + new:
        if uid(t) in gone:
            continue
        for pt in (t.GetStart(), t.GetEnd()):
            ends_at.setdefault(key(pt), []).append(t)
    culled = []

    def via_conflict(v):
        for p in pads:
            for L in (pcbnew.F_Cu, pcbnew.B_Cu) if p.HasHole() else (pcbnew.F_Cu,):
                if p.IsOnLayer(L) and v.IsOnLayer(L) and p.GetEffectiveShape(L).Collide(v.GetEffectiveShape(L), 0 if p.GetNetCode() == v.GetNetCode() else CLR):
                    return 'pad %s' % p.GetNumber()
        for p in holes:
            if p.GetEffectiveHoleShape().Collide(v.GetEffectiveHoleShape(), HOLE_HOLE):
                return 'hole of pad %s' % (p.GetNumber() or 'NPTH')
        for t in moved_items:
            if t.GetNetCode() != v.GetNetCode():
                for L in (t.GetLayer(),) if t.GetClass() == 'PCB_TRACK' else (pcbnew.F_Cu, pcbnew.B_Cu):
                    if v.IsOnLayer(L) and t.GetEffectiveShape(L).Collide(v.GetEffectiveShape(L), CLR):
                        return seg_str(t) if t.GetClass() == 'PCB_TRACK' else via_str(t)
        return None
    for v in vias:
        if uid(v) in moved_ids or uid(v) in gone:
            continue
        why = via_conflict(v)
        if why is None:
            continue
        if v.GetNetCode() == gnd and not ends_at.get(key(v.GetPosition())):
            culled.append((v, why))
        else:
            die('%s conflicts with %s and is not a free GND stitch via' % (via_str(v), why))
    for v, why in culled:
        print('  delete  %s (on %s)' % (via_str(v), why))
        b.Remove(v)

    # ---- 6. footprint graphics: front silk past the edge out, the library's Dwgs.User edge line in
    libdir = os.path.join(os.path.dirname(pcb), fp.GetFPID().GetLibNickname().wx_str() + '.pretty')
    lib = pcbnew.FootprintLoad(libdir, fp.GetFPID().GetLibItemName().wx_str())
    if lib is None:
        die('cannot load %s from %s' % (fp.GetFPIDAsString(), libdir))
    for g in [g.Cast() for g in fp.GraphicalItems()]:
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == 'PCB_SHAPE' and g.GetBoundingBox().GetTop() < edge:
            print('  silk    remove %s line past the edge' % ref)
            fp.Remove(g)
    have = [g.Cast() for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.Dwgs_User]
    for src in [g.Cast() for g in lib.GraphicalItems() if g.GetLayer() == pcbnew.Dwgs_User]:
        if have:
            break
        g = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_SEGMENT)
        g.SetLayer(pcbnew.Dwgs_User)
        g.SetStroke(src.GetStroke())
        # library coordinates -> board: the footprint is at 180 deg
        g.SetStart(V(pos.x - src.GetStart().x, pos.y + D - src.GetStart().y))
        g.SetEnd(V(pos.x - src.GetEnd().x, pos.y + D - src.GetEnd().y))
        fp.Add(g)
        print('  dwgs    add the edge line at y %.3f' % mm(g.GetStart().y))
    fp.SetLibDescription(lib.GetLibDescription())

    # ---- 7. self-check of everything that moved or is new
    fails = []
    others = [t for t in b.Tracks() if uid(t) not in moved_ids]
    allpads = [p for f in b.GetFootprints() for p in f.Pads()]
    cu = list(b.GetEnabledLayers().CuStack())

    def layers_of(t):
        return [t.GetLayer()] if t.GetClass() == 'PCB_TRACK' else [L for L in cu if t.IsOnLayer(L)]
    checked = moved_items + [p for p in pads]
    for it in checked:
        is_pad = it.GetClass() == 'PAD'
        bb = it.GetBoundingBox()
        bb.Inflate(MM(1))
        Ls = [L for L in cu if it.IsOnLayer(L)] if is_pad else layers_of(it)
        for o in others + [p for p in allpads if p.GetParentFootprint() is not None]:
            if uid(o) == uid(it) or (is_pad and o.GetClass() == 'PAD' and o.GetParentFootprint().GetReference() == ref):
                continue
            if not bb.Intersects(o.GetBoundingBox()):
                continue
            same = it.GetNetCode() == o.GetNetCode() and it.GetNetCode() > 0
            for L in Ls:
                if o.IsOnLayer(L) and not same and \
                        it.GetEffectiveShape(L).Collide(o.GetEffectiveShape(L), CLR):
                    fails.append('copper %s %s ~ %s' % (b.GetLayerName(L),
                                                        desc(it), desc(o)))
                    break
            ih = it.HasHole() if is_pad else it.GetClass() == 'PCB_VIA'
            oh = o.HasHole() if o.GetClass() == 'PAD' else o.GetClass() == 'PCB_VIA'
            if oh and not same:
                for L in Ls:
                    if it.GetEffectiveShape(L).Collide(o.GetEffectiveHoleShape(), HOLE_CLR):
                        fails.append('hole %s ~ hole of %s' % (desc(it), desc(o)))
                        break
            if ih and not same:
                for L in [L for L in cu if o.IsOnLayer(L)]:
                    if o.GetEffectiveShape(L).Collide(it.GetEffectiveHoleShape(), HOLE_CLR):
                        fails.append('hole of %s ~ %s' % (desc(it), desc(o)))
                        break
            if ih and oh and it.GetEffectiveHoleShape().Collide(o.GetEffectiveHoleShape(), HOLE_HOLE):
                fails.append('hole-to-hole %s ~ %s' % (desc(it), desc(o)))

    print('  moved %d segments + %d vias, stretched %d, %d stubs, %d patched, deleted %d vias'
          % (len(tseg), len(tvia), len(stretch), len(stubs), len(patches) + len(via_moves) + len(drops),
             len(culled) + len(drops)))
    for t in tseg:
        print('  move    %s' % seg_str(t))
    for v in tvia:
        print('  move    %s' % via_str(v))
    for t, _, _ in stretch:
        if uid(t) not in gone:
            print('  stretch %s' % seg_str(t))
    for t in vmoved:
        if t.GetClass() == 'PCB_TRACK' and uid(t) not in gone:
            print('  follow  %s' % seg_str(t))
    for t in new:
        print('  new     %s' % seg_str(t))
    if fails:
        for f in sorted(set(fails)):
            print('  FAIL    ' + f)
        die('%d clearance failures, board not saved' % len(set(fails)))
    if dry:
        print('dry run: board not saved')
        return
    pcbnew.SaveBoard(pcb, b)
    print('saved %s' % pcb)


def desc(o):
    if o.GetClass() == 'PAD':
        return 'pad %s.%s %s' % (o.GetParentFootprint().GetReference(), o.GetNumber(), o.GetNetname())
    if o.GetClass() == 'PCB_VIA':
        return via_str(o)
    return seg_str(o)


if __name__ == '__main__':
    main()
