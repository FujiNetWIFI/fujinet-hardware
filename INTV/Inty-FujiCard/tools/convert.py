#!/usr/bin/env python3
"""Yannick Erb's EasyEDA board -> Inty-FujiCard.kicad_pcb + Inty-FujiCard.pretty, copper unchanged.

Input: Original/PCB_PINTY-FUJI-CARD-PCB-v1.1_2026-11-04.json (EasyEDA Std 6.5.51), read with KiCad's
own EasyEDA Std importer (pcbnew.PCB_IO_MGR.EASYEDA).  What the import gets right is kept as it is:
every pad, track, via and zone, with the zone fills EasyEDA stored (this script never fills a zone;
tools/audit/gerber_equiv.py proves the plotted copper equals Yannick's gerbers).  What it gets wrong,
or what the house structure needs, is changed here and only here:

  1. layer names: the importer names KiCad's layers after EasyEDA's (TopLayer, 3DModel, ...); they
     get KiCad's standard names back.  No item changes layer.
  2. text visibility: the importer shows every Reference and Value; the JSON hides every value and
     40 of the 76 references (its TEXT display flag).  Applied from the JSON.
  3. references KiCad cannot annotate (no number) are numbered (RENAME); where the old label was on
     the silkscreen it stays there as a board text with the field's exact geometry, grouped with its
     footprint, so the printed board reads as Yannick's.
  4. footprints: each is copied at 0 degrees into Inty-FujiCard.pretty under its EasyEDA name (cleaned,
     FP_NAME), and the board's footprint IDs point there.  EasyEDA's hidden JLC_3DModel / JLC_3D_Size
     fields stay (fetch_models.py reads the model id from them; removing a field through the Python
     API corrupts SWIG's type table in KiCad 10.0.8).
  5. attributes: the edge, the test pads and the holes stay out of the BOM and the position files
     (Yannick's BOM leaves them out too); the holes are board-only.
  6. title block; deterministic UUIDs (uuid5 by order of appearance), so a rerun diffs clean.

Usage: python3 tools/convert.py      (writes the board and the library; run by build_all.sh with CONVERT=1)
"""
import hashlib, json, math, os, re, shutil, sys, uuid
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
SRC = os.path.join(PRJ, 'Original', 'PCB_PINTY-FUJI-CARD-PCB-v1.1_2026-11-04.json')
NAME = 'Inty-FujiCard'
PCB = os.path.join(PRJ, NAME + '.kicad_pcb')
LIB = os.path.join(PRJ, NAME + '.pretty')
NS = uuid.UUID('1b7e5c3a-9d40-4e2f-8a61-17c4d0f0ea11')    # the Inty-FujiCard namespace

# Yannick's reference -> KiCad's (the numbered ones stay as he has them)
RENAME = {'BOOT': 'SW1', 'RESET': 'SW2', 'RP-BOOT': 'SW3', 'RP-RUN': 'SW4', 'LED': 'D6', 'USB': 'J1',
          'GND': 'TP1', 'TX': 'TP2', 'RX': 'TP3', 'SWD': 'TP4', 'SWCLK': 'TP5',
          'Hole_gge2670': 'H1', 'Hole_gge2700': 'H2'}
# EasyEDA footprint name -> library name (only where the name needs cleaning)
FP_NAME = {'TESTPOINT{colon}TESTPOINT_PAD_D1.5MM': 'TESTPOINT_PAD_D1.5MM',
           'Hole_gge2670': 'Hole_D5.127mm_NPTH', 'Hole_gge2700': 'Hole_D5.127mm_NPTH'}
NOT_ASSEMBLED = {'K1', 'TP1', 'TP2', 'TP3', 'TP4', 'TP5', 'H1', 'H2'}
EXPECT = dict(footprints=78, tracks=727, vias=156, zones=391, nets=76, copper=2)
SAVED = dict(EXPECT, zones=5)   # 2 GND pours, the crystal's keep-out, 2 mask openings (solid_regions)


def die(msg):
    raise SystemExit('convert: ' + msg)


# EasyEDA (units of 10 mil, y down) -> KiCad nm: the importer's own mapping, checked on the outline
EASY_ORIGIN = (4075.2435, 3424.4886)       # the JSON head's x, y: the board's lower-left corner
KI_ORIGIN = (120.0, 140.0)                 # mm, where the importer put it (the aux origin)


def easy_nm(x, y):
    return pcbnew.VECTOR2I(int(round((KI_ORIGIN[0] + (x - EASY_ORIGIN[0]) * 0.254) * 1e6)),
                           int(round((KI_ORIGIN[1] + (y - EASY_ORIGIN[1]) * 0.254) * 1e6)))


def pour_fills(b):
    """The two GND pours' fills, from the JSON's stored fill (COPPERAREA field 10), holes included.
    Each fill path is one polygon: its first subpath the outline, the others its holes (the
    clearances round every foreign track, pad and via).  KiCad 10.0.8's importer keeps the
    outlines and drops the holes: as imported, the B.Cu pour covers 31 signal tracks (230 mm2 of
    copper Yannick's gerbers do not have) and the F.Cu pour 125 clearances.  Nothing else is
    filled from the JSON: the 386 solid regions are single paths, which the importer gets right."""
    d = json.load(open(SRC))
    areas = [s.split('~') for s in d['shape'] if s.startswith('COPPERAREA~')]
    layer = {'1': pcbnew.F_Cu, '2': pcbnew.B_Cu}
    done = 0
    for f in areas:
        net, lay = f[3], layer[f[2]]
        ol = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', f[4])]
        bb = easy_nm(min(ol[0::2]), min(ol[1::2])), easy_nm(max(ol[0::2]), max(ol[1::2]))
        cand = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() == net and z.GetLayer() == lay
                and abs(z.Outline().BBox().GetX() - bb[0].x) < 1000 and abs(z.Outline().BBox().GetY() - bb[0].y) < 1000
                and abs(z.Outline().BBox().GetRight() - bb[1].x) < 1000]
        if len(cand) != 1:
            die('COPPERAREA %s on layer %s: %d matching zones' % (net, f[2], len(cand)))
        z = cand[0]
        ps = pcbnew.SHAPE_POLY_SET()
        holes = 0
        for grp in json.loads(f[10]):
            for path in grp:
                subs = [x for x in re.split(r'(?=M)', path.strip()) if x.strip()]
                for k, sp in enumerate(subs):
                    n = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', sp)]
                    if re.search(r'[AaCcQqHhVv]', sp):
                        die('a fill path with curves or H / V moves: %s' % sp[:60])
                    ch = pcbnew.SHAPE_LINE_CHAIN()
                    for x, y in zip(n[0::2], n[1::2]):
                        ch.Append(easy_nm(x, y))
                    ch.SetClosed(True)
                    if k == 0:
                        ps.AddOutline(ch)
                    else:
                        ps.AddHole(ch)
                        holes += 1
        imported = z.GetFilledPolysList(lay).Area()
        if any(z.GetFilledPolysList(lay).HoleCount(i) for i in range(z.GetFilledPolysList(lay).OutlineCount())):
            die('the importer kept holes in %s: check pour_fills against KiCad\'s importer' % pcbnew.LayerName(lay))
        ps.Fracture()
        z.SetFilledPolysList(lay, ps)
        z.SetIsFilled(True)
        z.SetNeedRefill(False)
        print('%s %s pour: fill rebuilt from the JSON, %d holes (%.1f -> %.1f mm2)' % (
            pcbnew.LayerName(lay), net, holes, imported / 1e12, ps.Area() / 1e12))
        done += 1
    if done != 2:
        die('%d pours, want 2' % done)


def solid_regions(b):
    """EasyEDA's board-level copper SOLIDREGIONs, which the importer makes zones of, as what they
    are: fixed copper.  The 386 netted ones (teardrops and copper shapes on F.Cu / B.Cu) become
    filled copper polygons with their net, each exactly its zone's fill.  As zones they overlap
    each other at one priority (KiCad DRC: zones_intersect), sit in the crystal's no-fill keep-out
    (items_not_allowed), and a refill would redraw them; as shapes they are copper that stays as
    drawn.  The two GND pours stay zones (pour_fills), the keep-out a rule area, and the two
    finger-field mask openings zones on F.Mask / B.Mask (as shapes KiCad reads every pad pair in
    them as a solder-mask bridge)."""
    pour = lambda z: z.GetNetname() == 'GND' and z.Outline().Area() > 1e14    # the 58 x 51 mm COPPERAREAs
    if sum(1 for z in b.Zones() if pour(z)) != 2:
        die('%d GND pours' % sum(1 for z in b.Zones() if pour(z)))
    done = {'copper': 0, 'twice': 0}
    gone, seen = [], set()
    for z in list(b.Zones()):
        lay = z.GetLayer()
        if z.GetIsRuleArea() or pour(z) or not pcbnew.IsCopperLayer(lay):
            continue          # the pours, the keep-out, and the mask openings stay zones
        fill = z.GetFilledPolysList(lay)
        if fill.OutlineCount() != 1 or fill.HoleCount(0):
            die('solid region on %s: %d outlines' % (pcbnew.LayerName(lay), fill.OutlineCount()))
        o = fill.COutline(0)
        key = (lay, z.GetNetname(), tuple((o.CPoint(i).x, o.CPoint(i).y) for i in range(o.PointCount())))
        gone.append(z)
        if key in seen:       # EasyEDA drew it twice: one copy (KiCad's writer keeps one of two equal shapes)
            done['twice'] += 1
            continue
        seen.add(key)
        sh = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_POLY)
        sh.SetPolyShape(fill)
        sh.SetFilled(True)
        sh.SetWidth(0)
        sh.SetLayer(lay)
        sh.SetNetCode(z.GetNetCode())
        done['copper'] += 1
        b.Add(sh)
    for z in gone:
        b.Remove(z)
    # a removed item belongs to Python; collecting its proxy corrupts SWIG's type table in KiCad
    # 10.0.8 (later calls return bare SwigPyObjects), so they are kept until os._exit
    KEEP.extend(gone)
    if done['copper'] + done['twice'] != 386:
        die('solid regions: %s, want 386 copper' % done)
    print('solid regions: %d netted copper polygons (from zones; %d drawn twice by EasyEDA, kept once)'
          % (done['copper'], done['twice']))
    # the crystal's no-fill keep-out (EasyEDA's pour cutout under U5): 10 um smaller, so the pour
    # EasyEDA filled round it, whose edge touches it (8 slivers, 0.0002 mm2), is not inside it
    # (KiCad DRC: items_not_allowed).  A keep-out is not fabricated; the copper does not move.
    ka = [z for z in b.Zones() if z.GetIsRuleArea()]
    if len(ka) != 1 or not ka[0].GetDoNotAllowZoneFills():
        die('want one no-fill keep-out')
    # in place: ZONE.SetOutline() takes ownership of the polygon it is given while the Python proxy
    # keeps it too, and the proxy's collection then frees the zone's outline (seen: the keep-out came
    # back as a USB paste rectangle on one run in two)
    ka[0].Outline().Deflate(10000, pcbnew.CORNER_STRATEGY_ALLOW_ACUTE_CORNERS, 1000)


REGION_LAYER = {'5': pcbnew.F_Paste, '3': pcbnew.F_SilkS}   # EasyEDA layer -> KiCad, footprint regions
NO_PASTE = -390.0     # EasyEDA paste expansion (10 mil units) at or below this: the pad prints no paste


def lib_regions(b):
    """The footprints' own filled regions that the importer drops: EasyEDA's LIB SOLIDREGIONs on
    the top paste layer (142: the paste of every pad whose own paste is off, below) and the top
    silkscreen (13: polarity bars and marks).  Their pads carry EasyEDA's paste expansion -393.7
    (x 10 mil = -100 mm: "this pad prints none"), which the importer keeps as a -100 mm margin;
    here such a pad simply has no F.Paste.  Regions on EasyEDA's document and component-shape
    layers (12, 99, 100) are not fabricated and stay out."""
    d = json.load(open(SRC))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    n = {pcbnew.F_Paste: 0, pcbnew.F_SilkS: 0}
    off = 0
    for s in d['shape']:
        if not s.startswith('LIB~'):
            continue
        parts = s.split('#@$')
        ref = next(p.split('~')[10] for p in parts if p.startswith('TEXT~P'))
        fp = fps[ref]
        for part in parts:
            f = part.split('~')
            if f[0] == 'SOLIDREGION' and f[1] in REGION_LAYER:
                num = r'(-?\d+(?:\.\d+)?)'
                dot = re.match(r'^M %s %s A %s %s 0 1 1 %s %s A %s %s 0 1 1 %s %s Z\s*$' % ((num,) * 10), f[3].strip())
                if dot:          # a filled dot: two half circles (U2's and U7's pin-1 marks)
                    v = [float(x) for x in dot.groups()]
                    c = easy_nm((v[0] + v[4]) / 2, (v[1] + v[5]) / 2)
                    if abs(v[2] - math.hypot(v[4] - v[0], v[5] - v[1]) / 2) > 1e-3 or (v[8], v[9]) != (v[0], v[1]):
                        die('%s: an arc region that is not a full circle' % ref)
                    sh = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_CIRCLE)
                    sh.SetCenter(c)
                    sh.SetEnd(pcbnew.VECTOR2I(c.x + int(round(v[2] * 0.254 * 1e6)), c.y))
                elif re.search(r'[AaCcQqHhVv]', f[3]) or f[3].count('M') != 1:
                    die('%s: a region with curves or holes on EasyEDA layer %s' % (ref, f[1]))
                else:
                    v = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', f[3])]
                    pts = [easy_nm(x, y) for x, y in zip(v[0::2], v[1::2])]
                    if pts[0] == pts[-1]:
                        pts = pts[:-1]
                    sh = pcbnew.PCB_SHAPE(fp, pcbnew.SHAPE_T_POLY)
                    sh.SetPolyPoints(pts)
                sh.SetFilled(True)
                sh.SetWidth(0)
                sh.SetLayer(REGION_LAYER[f[1]])
                fp.Add(sh)
                n[REGION_LAYER[f[1]]] += 1
        sentinel = {(f[8], f[2], f[3]) for f in (p.split('~') for p in parts if p.startswith('PAD~'))
                    if float(f[17] or 0) <= NO_PASTE}
        for pad in fp.Pads():
            m = pad.GetLocalSolderPasteMargin()
            if m is not None and m <= int(NO_PASTE * 0.254 * 1e6):
                ls = pad.GetLayerSet()
                ls.RemoveLayer(pcbnew.F_Paste)
                pad.SetLayerSet(ls)
                pad.SetLocalSolderPasteMargin(None)
                off += 1
        if sum(1 for pad in fp.Pads() if not pad.IsOnLayer(pcbnew.F_Paste) and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
               and pad.IsOnLayer(pcbnew.F_Cu)) != len(sentinel):
            die('%s: %d pads with EasyEDA\'s no-paste expansion, a different number without F.Paste' % (ref, len(sentinel)))
    if (n[pcbnew.F_Paste], n[pcbnew.F_SilkS], off) != (142, 13, 138):
        die('footprint regions: %d paste, %d silk, %d pads without paste; want 142, 13, 138'
            % (n[pcbnew.F_Paste], n[pcbnew.F_SilkS], off))
    print('footprints: %d paste and %d silkscreen regions restored; %d pads print their paste through them'
          % (n[pcbnew.F_Paste], n[pcbnew.F_SilkS], off))


def silk_texts(b):
    """Every visible F.Silkscreen text on the board: board texts, footprint texts and fields."""
    items = [d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT']
    for f in b.GetFootprints():
        items += [t for t in f.GraphicalItems() if t.GetClass() == 'PCB_TEXT'] + list(f.GetFields())
    return [t for t in items if t.GetLayer() == pcbnew.F_SilkS and t.IsVisible()]


def ink_centre(t):
    bb = t.GetEffectiveTextShape().BBox()
    return bb.GetX() + bb.GetWidth() / 2.0, bb.GetY() + bb.GetHeight() / 2.0


def align_texts(b):
    """Each visible silkscreen text moved so that its strokes are centred where EasyEDA's are.
    The importer anchors KiCad's text where EasyEDA's starts, which leaves every text 0.2-0.3 mm
    off (and a long one up to 1.4 mm: KiCad's stroke font is narrower).  Size, angle and font
    stay KiCad's import; only the position moves."""
    sys.path.insert(0, HERE)
    import easyeda
    his = [t for t in easyeda.texts() if t['shown'] and t['layer'] == '3']
    pool = list(his)
    moved = []
    for t in silk_texts(b):
        cx, cy = ink_centre(t)
        s = t.GetShownText(False)
        cand = [h for h in pool if h['text'] == s and abs((h['angle'] - t.GetDrawRotation().AsDegrees() + 180) % 360 - 180) < 0.5]
        if not cand:
            die('silk text %r at (%.2f, %.2f) has no EasyEDA text' % (s, cx / 1e6, cy / 1e6))
        h = min(cand, key=lambda h: math.hypot((h['ink'][0] + h['ink'][2]) / 2 - cx / 1e6, (h['ink'][1] + h['ink'][3]) / 2 - cy / 1e6))
        hx, hy = (h['ink'][0] + h['ink'][2]) / 2 * 1e6, (h['ink'][1] + h['ink'][3]) / 2 * 1e6
        if math.hypot(hx - cx, hy - cy) > 2e6:
            die('silk text %r: the nearest EasyEDA one is %.2f mm away' % (s, math.hypot(hx - cx, hy - cy) / 1e6))
        pool.remove(h)
        t.Move(pcbnew.VECTOR2I(int(round(hx - cx)), int(round(hy - cy))))
        nx, ny = ink_centre(t)
        if math.hypot(nx - hx, ny - hy) > 2000:
            die('silk text %r did not land on EasyEDA\'s centre' % s)
        moved.append(math.hypot(hx - cx, hy - cy) / 1e6)
    if pool:
        die('EasyEDA silk texts with no KiCad text: %s' % [h['text'] for h in pool])
    print('silkscreen: %d texts centred on EasyEDA\'s (moved %.2f-%.2f mm)' % (len(moved), min(moved), max(moved)))


def json_text_flags():
    """reference -> (reference shown, value shown), from the JSON's LIB TEXT records
    (TEXT~P|N~x~y~...~text(10)~path~display(12): 'none' = hidden)."""
    d = json.load(open(SRC))
    out = {}
    for s in d['shape']:
        if not s.startswith('LIB~'):
            continue
        ref = val = None
        for part in s.split('#@$'):
            f = part.split('~')
            if f[0] == 'TEXT' and f[1] == 'P':
                ref = (f[10], f[12] != 'none')
            elif f[0] == 'TEXT' and f[1] == 'N':
                val = f[12] != 'none'
        if ref is None or val is None:
            die('LIB without a P / N text: %s' % s[:80])
        if ref[0] in out:
            die('two LIBs called %s' % ref[0])
        out[ref[0]] = (ref[1], val)
    return out


def counts(b):
    tr = list(b.GetTracks())
    return dict(footprints=len(b.GetFootprints()), tracks=sum(t.Type() != pcbnew.PCB_VIA_T for t in tr),
                vias=sum(t.Type() == pcbnew.PCB_VIA_T for t in tr), zones=b.GetAreaCount(),
                nets=b.GetNetCount() - 1, copper=b.GetCopperLayerCount())


OUTER = (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask)   # paste: tools/audit/gerber_equiv.py


def copper_hash(b):
    """A hash of everything that is copper (pads, tracks, vias, zone outlines and fills), by
    geometry only: net names and UUIDs left out, so a rename of either cannot hide a change."""
    h = hashlib.sha256()
    for r in copper_rows(b):
        h.update(r.encode())
    return h.hexdigest()


def copper_rows(b):
    rows = []
    for f in b.GetFootprints():
        for p in f.Pads():
            sh = p.GetEffectivePolygon(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
            # the outer layers only: KiCad writes an NPTH pad's F/B.Cu + F/B.Mask as *.Cu *.Mask
            lay = ','.join(pcbnew.LayerName(l) for l in OUTER if p.IsOnLayer(l))
            rows.append('pad %s %d %d %s %s %s %d' % (p.GetNumber(), p.GetPosition().x,
                        p.GetPosition().y, lay, p.GetDrillSize(), sh.Area(), p.GetAttribute()))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            rows.append('via %d %d %d %d' % (t.GetPosition().x, t.GetPosition().y, t.GetWidth(pcbnew.F_Cu), t.GetDrill()))
        else:
            rows.append('trk %d %d %d %d %d %d' % (t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y,
                                                    t.GetWidth(), t.GetLayer()))
    for d in b.GetDrawings():
        if d.GetClass() == 'PCB_SHAPE' and d.GetLayer() in OUTER:
            ps = d.GetPolyShape() if d.GetShape() == pcbnew.SHAPE_T_POLY else None
            pts = [(ps.CVertex(i).x, ps.CVertex(i).y) for i in range(ps.FullPointCount())] if ps else \
                [(d.GetStart().x, d.GetStart().y), (d.GetEnd().x, d.GetEnd().y)]
            rows.append('shape %d %s %d' % (d.GetLayer(), pts, d.IsSolidFill()))
    for z in b.Zones():
        o = z.Outline()
        rows.append('zone %s %s %d' % (z.GetLayerSet().FmtHex(), [(o.CVertex(i).x, o.CVertex(i).y)
                                                                   for i in range(o.FullPointCount())], z.GetIsRuleArea()))
        for l in z.GetLayerSet().Seq():
            if z.HasFilledPolysForLayer(l):
                fp = z.GetFilledPolysList(l)
                rows.append('fill %d %d %d' % (l, fp.OutlineCount(), fp.Area()))
    return sorted(rows)


def text_geometry(t):
    bb = t.GetBoundingBox()
    return (bb.GetX(), bb.GetY(), bb.GetWidth(), bb.GetHeight(), t.GetTextAngle().AsDegrees(), t.GetLayer())


def lib_copy(fp, name):
    """The footprint as a library item: at the origin, 0 degrees, no nets, REF** / name."""
    c = pcbnew.FOOTPRINT(fp)
    c.SetOrientationDegrees(0)
    c.SetPosition(pcbnew.VECTOR2I(0, 0))
    for p in c.Pads():
        p.SetNetCode(0, True)
    c.SetReference('REF**')
    c.SetValue(name)
    c.SetFPID(pcbnew.LIB_ID('', name))
    return c


def fp_geometry(c):
    """A library copy's pads and graphics, to 1 um, for comparing two instances of one footprint.
    Fields and user texts are left out (their placement is per instance); a shape is its layer,
    kind, width and bounding box (EasyEDA writes a rectangle's corners in either order)."""
    um = lambda v: int(round(v / 1000.0))
    rows = []
    for p in c.Pads():
        rows.append(('pad', p.GetNumber(), int(p.GetShape(pcbnew.F_Cu)), um(p.GetSize(pcbnew.F_Cu).x),
                     um(p.GetSize(pcbnew.F_Cu).y), um(p.GetPosition().x), um(p.GetPosition().y),
                     round(p.GetOrientationDegrees() % 360, 3), p.GetLayerSet().FmtHex(), um(p.GetDrillSize().x),
                     um(p.GetDrillSize().y), int(p.GetAttribute())))
    for g in c.GraphicalItems():
        if g.GetClass() == 'PCB_SHAPE':
            bb = g.GetBoundingBox()
            rows.append(('shape', g.GetLayer(), int(g.GetShape()), um(g.GetWidth()), um(bb.GetX()), um(bb.GetY()),
                         um(bb.GetWidth()), um(bb.GetHeight())))
    return sorted(rows)


def close(a, b, tol=1):
    """Two fp_geometry lists equal to tol um in every coordinate."""
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return False
        for x, y in zip(ra, rb):
            if isinstance(x, int) and isinstance(y, int) and not isinstance(x, bool):
                if abs(x - y) > tol:
                    return False
            elif x != y:
                return False
    return True


KEEP = []      # see solid_regions
UUID_RE = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def deterministic_uuids(path, key='pcb', reorder=False):
    """Every UUID in the file -> uuid5(NS, a key made from the item's own content, UUIDs left out),
    so the same board gets the same UUIDs on every run whatever the importer drew.  References
    (group members) follow because every occurrence of one UUID gets the same new one.  reorder:
    the top-level items sorted by kind and new UUID too (KiCad writes footprints sorted by UUID but
    tracks in list order, i.e. the importer's), for KiCad's writer to normalise afterwards."""
    sys.path.insert(0, HERE)
    from sexpr import parse, dump
    txt = open(path).read()
    tree = parse(txt)
    strip = lambda s: re.sub(UUID_RE, '', s)
    new = {}

    def walk(node, parent, seen):
        own = next((x for x in node if isinstance(x, list) and len(x) == 2 and x[0] == 'uuid'), None)
        here = parent
        if own is not None:
            k = '%s/%s:%s' % (parent, node[0], hashlib.sha1(strip(dump(node)).encode()).hexdigest()[:16])
            seen[k] = seen.get(k, 0) + 1          # identical items: numbered in file order
            here = '%s#%d' % (k, seen[k])
            if str(own[1]) in new:
                die('UUID %s used by two items' % own[1])
            new[str(own[1])] = str(uuid.uuid5(NS, here))
        sub = {}
        for x in node:
            if isinstance(x, list):
                walk(x, here, sub)
    walk(tree, key, {})
    # only an item's own (uuid "...") and the group members that name one; a footprint's (path ...)
    # holds its schematic symbol's UUIDs, which belong to the schematic and stay as they are
    sub = lambda m: re.sub(UUID_RE, lambda u: new[u.group(0)], m.group(0))
    txt = re.sub(r'\(uuid "%s"\)' % UUID_RE, sub, txt)
    txt = re.sub(r'\(members(?:\s+"%s")+\s*\)' % UUID_RE, sub, txt)
    left = set(re.findall(UUID_RE, re.sub(r'\(path "[^"]*"\)', '', txt))) - set(new.values())
    if left:
        die('UUIDs that are no item\'s own: %s' % sorted(left)[:4])
    if reorder:
        tree = parse(txt)
        own = lambda x: next((str(y[1]) for y in x if isinstance(y, list) and len(y) == 2 and y[0] == 'uuid'), None)
        idx = [i for i, x in enumerate(tree) if isinstance(x, list) and own(x)]
        rank = {}
        for i in idx:
            rank.setdefault(tree[i][0], len(rank))
        items = sorted((tree[i] for i in idx), key=lambda x: (rank[x[0]], own(x)))
        for i, x in zip(idx, items):
            tree[i] = x
        txt = dump(tree) + '\n'
    open(path, 'w').write(txt)
    return len(new)


def write_project():
    """Inty-FujiCard.kicad_pro from tools/project_template.json (FujiNet-ColecoVision Rev0's project
    settings): Yannick's EasyEDA rule as the Default net class (0.1016 mm clearance, 0.2032 mm
    track, 0.4572 / 0.254 mm via: EasyEDA stores it in units of 10 mil), the constraints and
    severities in tools/rules.json.  gen_sch.py fills in the sheets."""
    pro = json.load(open(os.path.join(HERE, 'project_template.json')))
    pro['meta']['filename'] = NAME + '.kicad_pro'
    rules = json.load(open(os.path.join(HERE, 'rules.json')))
    pro['board']['design_settings']['rules'].update(rules['constraints'])
    pro['board']['design_settings']['rule_severities'].update(rules['severities'])
    fn = os.path.join(PRJ, NAME + '.kicad_pro')
    if os.path.exists(fn):         # keep what gen_sch.py wrote (sheets, top-level sheet)
        old = json.load(open(fn))
        for k in ('sheets',):
            pro[k] = old.get(k, pro[k])
        pro['schematic'] = old.get('schematic', pro['schematic'])
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')


def main():
    b = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.EASYEDA, SRC)
    got = counts(b)
    if got != EXPECT:
        die('import counts %s, want %s' % (got, EXPECT))
    pour_fills(b)
    solid_regions(b)
    lib_regions(b)
    h0 = copper_hash(b)

    # 1. KiCad's layer names; every layer that holds an item enabled
    used = set()
    for d in b.GetDrawings():
        used.add(d.GetLayer())
    for f in b.GetFootprints():
        for it in f.GraphicalItems():
            used.add(it.GetLayer())
    en = b.GetEnabledLayers()
    for l in used:
        en.AddLayer(l)
    b.SetEnabledLayers(en)
    for l in b.GetEnabledLayers().Seq():
        b.SetLayerName(l, pcbnew.LayerName(l))

    # 2. text visibility from the JSON
    flags = json_text_flags()
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    if set(flags) != set(fps) - {'Hole_gge2670', 'Hole_gge2700'}:
        die('JSON references %s / board %s' % (sorted(set(flags) ^ set(fps)), ''))
    for ref, f in fps.items():
        rv, vv = flags.get(ref, (False, False))
        f.Reference().SetVisible(rv)
        f.Value().SetVisible(vv)
    n_ref = sum(f.Reference().IsVisible() for f in fps.values())
    n_val = sum(f.Value().IsVisible() for f in fps.values())
    if (n_ref, n_val) != (36, 0):
        die('visible references / values %d / %d, want 36 / 0' % (n_ref, n_val))

    # 3. numbered references; the old silk label kept as a board text
    labels = []
    for old, new in RENAME.items():
        f = fps[old]
        fld = f.Reference()
        if fld.IsVisible():
            t = pcbnew.PCB_TEXT(b)
            t.SetText(old)
            t.SetAttributes(fld)
            t.SetPosition(fld.GetPosition())
            t.SetLayer(fld.GetLayer())
            t.SetVisible(True)
            b.Add(t)
            if text_geometry(t) != text_geometry(fld):
                die('%s: label geometry %s, field %s' % (old, text_geometry(t), text_geometry(fld)))
            g = pcbnew.PCB_GROUP(b)
            g.SetName(new)
            b.Add(g)
            g.AddItem(f)
            g.AddItem(t)
            labels.append(old)
            fld.SetVisible(False)
        f.SetReference(new)
    print('renamed %d references; %d silk labels kept as board text (%s)' % (len(RENAME), len(labels), ', '.join(labels)))
    align_texts(b)

    # 4 / 5. the library, the footprint IDs, the attributes
    shutil.rmtree(LIB, True)
    io = pcbnew.PCB_IO_KICAD_SEXPR()
    io.CreateLibrary(LIB)
    texts = {}
    for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
        src = f.GetFPID().GetLibItemName().wx_str()
        name = FP_NAME.get(src, src)
        if not re.match(r'^[A-Za-z0-9_.+-]+$', name):
            die('footprint name %r needs cleaning (FP_NAME)' % name)
        ref = f.GetReference()
        a = f.GetAttributes()
        smd = all(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in f.Pads())
        if ref not in NOT_ASSEMBLED:
            a |= pcbnew.FP_SMD if smd else pcbnew.FP_THROUGH_HOLE
        else:
            a |= pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES
        if ref in ('H1', 'H2'):
            a |= pcbnew.FP_BOARD_ONLY
        f.SetAttributes(a)
        c = lib_copy(f, name)
        t = fp_geometry(c)
        if name in texts and not close(texts[name][1], t):
            bad = [(x, y) for x, y in zip(texts[name][1], t) if not close([x], [y])]
            die('footprint %s: %s and %s differ: %s' % (name, texts[name][0], f.GetReference(), bad[:4]))
        if name not in texts:
            texts[name] = (f.GetReference(), t)
            io.FootprintSave(LIB, c)
        f.SetFPID(pcbnew.LIB_ID(NAME, name))
    for fn in sorted(os.listdir(LIB)):
        deterministic_uuids(os.path.join(LIB, fn), 'fp/' + fn)
    print('library: %d footprints from %d instances' % (len(texts), len(fps)))
    open(os.path.join(PRJ, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")(uri "${KIPRJMOD}/%s.pretty")(options "")'
        '(descr "Yannick Erb\'s EasyEDA footprints, as on the board"))\n)\n' % (NAME, NAME))

    # 6. title block
    tb = b.GetTitleBlock()
    tb.SetTitle('Inty-FujiCard')
    tb.SetRevision('1.1')
    tb.SetDate('2026-11-04')
    tb.SetCompany('FujiNet')
    tb.SetComment(0, 'Design: Yannick Erb (EasyEDA PINTY-FUJI-CARD-PCB v1.1); converted by tools/convert.py')
    tb.SetComment(1, 'Copper as in Yannick Erb\'s gerbers of 2026-11-04 - never refill the zones')

    if copper_hash(b) != h0:
        die('the copper changed during the conversion')
    rows0 = copper_rows(b)
    if os.path.exists(PCB):
        os.remove(PCB)
    # the plain writer: pcbnew.SaveBoard also saves a project file and throws std::out_of_range
    # (map::at) on this imported board in KiCad 10.0.8; the project is written by write_project()
    pcbnew.PCB_IO_KICAD_SEXPR().SaveBoard(PCB, b)
    n = deterministic_uuids(PCB, reorder=True)
    # once more through KiCad's writer, which sorts the items by their (now fixed) UUIDs
    pcbnew.PCB_IO_KICAD_SEXPR().SaveBoard(PCB, pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(PCB, None))

    # reload: the same counts, the same copper, every zone still filled
    r = pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(PCB, None)
    if counts(r) != SAVED:
        die('saved board counts %s' % counts(r))
    if copper_hash(r) != h0:
        import collections
        a, c = collections.Counter(rows0), collections.Counter(copper_rows(r))
        die('the saved board\'s copper differs from the import: -%s +%s' % (sorted((a - c).items())[:3],
                                                                             sorted((c - a).items())[:3]))
    unfilled = [z for z in r.Zones() if not z.GetIsRuleArea() and not z.IsFilled()]
    if unfilled:
        die('%d zones lost their fill' % len(unfilled))
    open(os.path.join(HERE, 'copper.sha256'), 'w').write(h0 + '\n')
    write_project()
    print('board written: %s (%d UUIDs renumbered); copper hash %s' % (os.path.basename(PCB), n, h0[:16]))


if __name__ == '__main__':
    # os._exit: KiCad 10's Python teardown can hang or dump core after the work is done
    try:
        main()
    except SystemExit as e:
        print(e, flush=True)
        os._exit(1 if e.code else 0)
    sys.stdout.flush()
    os._exit(0)
