#!/usr/bin/env python3
"""Measure the routed board's layout claims on the copper itself, and fail if one does not hold:

  1. Raspberry Pi's regulator corner (on the QFN-80): VREG_VIN (64) joined to C_VREGIN, LX (63) to
     the inductor, the inductor to C_DVBULK (DVDD), VREG_AVDD (61) to its RC, each on the corner's copper
  2. decoupling: every RP supply capacitor within 14 mm of its pin (every supply pin stubs inward to
     the +3V3_RP / DVDD rings under the package; the capacitors sit round it), the south side's three
     (5, 10, 15: the bus owns that side) within 17 mm; the CP2102N, the S3, the buck and the LDO caps
     within 6 mm of their pins
  3. the USB 27R: copper path from pins 66 / 67 to each resistor (Raspberry Pi: close to the chip)
  4. the crystal: XIN's track length pin 30 -> crystal (keep it short)
  5. the exposed pads: vias inside the RP2354B's and the CP2102N's
  6. the USB pairs: each line's length and the skew within each pair (full speed: edges 4-20 ns); the
     USBLC6's flow-through pins joined; no loop in any USB line's copper
  7. the edge: every bus finger reaches its series resistor; nothing on In1 / In2 in the finger
     field (filled copper); +5V finger (D) -> the mux's VIN2; the GND finger on GND
  8. the ESP32-S3: its antenna keep-out (the module footprint's zone: the antenna plus Espressif's
     15 mm each side) empty of tracks, vias, fills and parts on every layer; the antenna end flush
     with the top edge
  9. the buck's input loop: VIN and GND to the input caps short
Copper paths are shortest paths over the net's own tracks and vias (pad to pad); a via adds no length
but is counted.  Usage: python3 tools/audit/layout_checks.py [board]      exit 1 on any failure
"""
import heapq, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gen_pcb as G
import edge_geom as EG
import design as D
from sexpr import parse, find, findall

PCB = sys.argv[1] if len(sys.argv) > 1 else G.PCB
K = D.KEY
C = lambda n: (n or '').rsplit('/', 1)[-1]   # /rp-core/RP_LX -> RP_LX (KiCad's hierarchical names)
G.do_placement(G.place)          # fills G.PLACE (the S3 module position for check 8)


def filled_copy(pcb):
    """The board with every zone freshly filled (a copy beside its project files, so the board's own rules
    apply): the pours are measured as KiCad fills them, not as the last save left them."""
    import shutil, subprocess
    from tmpdir import tmp
    d = tmp('layout-checks')
    os.makedirs(d, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pcb))[0]
    for ext in ('.kicad_pcb', '.kicad_pro', '.kicad_dru'):
        src = os.path.join(os.path.dirname(os.path.abspath(pcb)), stem + ext)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(d, stem + ext))
    fn = os.path.join(d, stem + '.kicad_pcb')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--save-board', '-o', os.devnull, fn],
                   capture_output=True)
    return fn
fails = []


def check(ok, msg):
    print(('ok   ' if ok else 'FAIL ') + msg)
    if not ok:
        fails.append(msg)


b = parse(open(filled_copy(PCB)).read())
PADS, _ = G.board_pads(b)


def pad(key, num):
    return next(p for p in PADS if p.ref == K[key] and p.num == num)


def graph(net):
    """Nodes (x, y, layer); edges along tracks (their length) and through vias (0 length, 1 via)."""
    adj = {}
    node = lambda x, y, l: (round(x, 3), round(y, 3), l)

    def add(a, c, w, v):
        adj.setdefault(a, []).append((c, w, v))
        adj.setdefault(c, []).append((a, w, v))
    segs = [e for e in b if isinstance(e, list) and e and e[0] == 'segment' and C(str(find(e, 'net')[1])) == C(net)]
    for s in segs:
        st, en, L = find(s, 'start'), find(s, 'end'), str(find(s, 'layer')[1])
        a, c = node(float(st[1]), float(st[2]), L), node(float(en[1]), float(en[2]), L)
        add(a, c, math.dist(a[:2], c[:2]), 0)
    for v in (e for e in b if isinstance(e, list) and e and e[0] == 'via' and C(str(find(e, 'net')[1])) == C(net)):
        at = find(v, 'at')
        add(node(float(at[1]), float(at[2]), 'F.Cu'), node(float(at[1]), float(at[2]), 'B.Cu'), 0.0, 1)
    nodes = list(adj)
    for s in segs:          # T-junctions: join every node to the segments it lies on
        st, en, L = find(s, 'start'), find(s, 'end'), str(find(s, 'layer')[1])
        x0, y0, x1, y1 = float(st[1]), float(st[2]), float(en[1]), float(en[2])
        for n in nodes:
            if n[2] != L:
                continue
            dx, dy = x1 - x0, y1 - y0
            ll = dx * dx + dy * dy
            if ll == 0:
                continue
            t = ((n[0] - x0) * dx + (n[1] - y0) * dy) / ll
            if 0 < t < 1 and math.hypot(x0 + t * dx - n[0], y0 + t * dy - n[1]) < 0.01:
                add(n, node(x0, y0, L), t * math.sqrt(ll), 0)
    return adj


def path(net, a, c):
    """(length mm, vias) of the shortest copper path between pads a and c, or (None, None)."""
    adj = graph(net)

    def touching(p):
        return [n for n in adj if (n[2] in p.layers or p.th) and abs(n[0] - p.cx) <= p.hw + 1e-3
                and abs(n[1] - p.cy) <= p.hh + 1e-3]
    src, dst = touching(a), set(touching(c))
    if not src or not dst:
        return None, None
    best = {s: (0.0, 0) for s in src}
    pq = [(0.0, 0, s) for s in src]
    while pq:
        d, nv, u = heapq.heappop(pq)
        if u in dst:
            return d, nv
        if (d, nv) > best.get(u, (1e9, 0)):
            continue
        for v, w, iv in adj.get(u, []):
            nd = (d + w, nv + iv)
            if nd < best.get(v, (1e9, 0)):
                best[v] = nd
                heapq.heappush(pq, (nd[0], nd[1], v))
    return None, None


def loops(net):
    """Redundant copper on a net: the cycles in its track / via graph, each pad taken as one node and
    every track split where another's end lies on it.  A tree has none."""
    node = lambda x, y, l: (round(x, 3), round(y, 3), l)
    segs = [(float(find(e, 'start')[1]), float(find(e, 'start')[2]), float(find(e, 'end')[1]),
             float(find(e, 'end')[2]), str(find(e, 'layer')[1]))
            for e in b if isinstance(e, list) and e and e[0] == 'segment' and C(str(find(e, 'net')[1])) == C(net)]
    vias = [(float(find(e, 'at')[1]), float(find(e, 'at')[2]))
            for e in b if isinstance(e, list) and e and e[0] == 'via' and C(str(find(e, 'net')[1])) == C(net)]
    ends = {node(x, y, L) for x0, y0, x1, y1, L in segs for x, y in ((x0, y0), (x1, y1))}
    ends |= {node(x, y, L) for x, y in vias for L in ('F.Cu', 'B.Cu')}
    pads_ = [q for q in PADS if C(q.net) == C(net)]

    def key(n):
        for q in pads_:
            if (n[2] in q.layers or q.th) and abs(n[0] - q.cx) <= q.hw + 1e-3 and abs(n[1] - q.cy) <= q.hh + 1e-3:
                return (q.ref, q.num)
        return n
    edges = [(node(x, y, 'F.Cu'), node(x, y, 'B.Cu')) for x, y in vias]
    for x0, y0, x1, y1, L in segs:
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy or 1e-12
        on = sorted((((n[0] - x0) * dx + (n[1] - y0) * dy) / ll, n) for n in ends if n[2] == L
                    and 0 < ((n[0] - x0) * dx + (n[1] - y0) * dy) / ll < 1
                    and math.hypot(x0 + dx * ((n[0] - x0) * dx + (n[1] - y0) * dy) / ll - n[0],
                                   y0 + dy * ((n[0] - x0) * dx + (n[1] - y0) * dy) / ll - n[1]) < 0.01)
        chain = [node(x0, y0, L)] + [n for _, n in on] + [node(x1, y1, L)]
        edges += list(zip(chain, chain[1:]))
    parent = {}

    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    cyc = []
    for a, c in edges:
        ra, rc = root(key(a)), root(key(c))
        if key(a) == key(c):
            continue
        if ra == rc:
            cyc.append(a[:2])
        else:
            parent[ra] = rc
    return cyc


def net_length(net):
    return sum(math.dist((float(find(s, 'start')[1]), float(find(s, 'start')[2])),
                         (float(find(s, 'end')[1]), float(find(s, 'end')[2])))
               for s in b if isinstance(s, list) and s and s[0] == 'segment' and C(str(find(s, 'net')[1])) == C(net))


def fills(name_prefix, layer=None):
    """The filled polygons of the zones whose name starts with name_prefix: [(net, layer, pts)]."""
    out = []
    for e in b:
        if isinstance(e, list) and e and e[0] == 'zone' and find(e, 'name') and \
                str(find(e, 'name')[1]).startswith(name_prefix):
            for fp_ in findall(e, 'filled_polygon'):
                L = str(find(fp_, 'layer')[1])
                if layer is None or L == layer:
                    out.append((str(find(e, 'net')[1]), L,
                                [(float(q[1]), float(q[2])) for q in find(fp_, 'pts')[1:] if q[0] == 'xy']))
    return out


def in_fill(fl, x, y, net):
    return any(C(n) == C(net) and G.point_in_poly(x, y, pts) for n, _, pts in fl)




def near(net, ka, pa, kb, pb, lim, via_ok=True, fill=None):
    """Copper path pad -> pad within lim mm (or both pads inside one filled pour of the net)."""
    a, c = pad(ka, pa), pad(kb, pb)
    d, nv = path(net, a, c)
    if d is None and fill is not None:
        if any(C(n) == C(net) and G.point_in_poly(a.cx, a.cy, pts) and G.point_in_poly(c.cx, c.cy, pts) for n, _, pts in fill):
            return 0.0, 0, 'pour'
    return d, nv, None


# ---- 1. the regulator corner ---------------------------------------------------------------------------
graft = fills('rpi_graft') + fills('GND_top', 'F.Cu')
for what, net, ka, pa, kb, pb in (('VREG_VIN 64 -> C_VREGIN', '+3V3_RP', 'U_RP', '64', 'C_VREGIN', '1'),
                                  ('LX 63 -> L_RP', 'RP_LX', 'U_RP', '63', 'L_RP', '2'),
                                  ('L_RP -> C_DVBULK (DVDD)', 'DVDD', 'L_RP', '1', 'C_DVBULK', '1'),
                                  ('VREG_AVDD 61 -> C_AVDD', 'VREG_AVDD', 'U_RP', '61', 'C_AVDD', '1')):
    d, nv, how = near(net, ka, pa, kb, pb, 6.0, fill=graft)
    check(d is not None and d <= 6.0, '1. %s: %s' % (what, ('%.1f mm, %d vias' % (d, nv) if how is None else 'one filled pour')
                                                     if d is not None else 'NOT CONNECTED on copper'))
# ---- 2. decoupling ----------------------------------------------------------------------------------------
rp_caps = ([('C_IOV%d' % p, str(p)) for p in D.RP_IOVDD_PINS] + [('C_DV%d' % p, str(p)) for p in D.RP_DVDD_PINS]
           + [('C_ADC', '59'), ('C_OTP', '68'), ('C_QSPI', '69')])
SOUTH = ('5', '10', '15')                       # boxed in by the bus: their capacitors sit north
for key, pin in rp_caps:
    net = pad('U_RP', pin).net
    a, c = pad('U_RP', pin), pad(key, '1')
    check(C(c.net) == C(net), '2. %s pad 1 on %s (pin %s)' % (key, C(net), pin))
    dist = math.dist((a.cx, a.cy), (c.cx, c.cy))
    lim = 17.0 if pin in SOUTH else 14.0
    check(dist <= lim, '2. %s on pin %s (%s): %.1f mm from the pin, through the ring under the package (limit %.0f)'
          % (key, pin, C(net), dist, lim))
for key, ukey, upin in (('C_UART', 'U_UART', '6'), ('C_S3', 'U_S3', '2'), ('C_BINHF', 'U_BUCK', '3'),
                        ('C_LDOIN', 'U_LDO', '1'), ('C_LDOOUT', 'U_LDO', '5'), ('C_WS', 'D_WS', '4'),
                        ('C_MUXV1', 'U_MUX', '3')):
    a, c = pad(ukey, upin), pad(key, '1')
    dist = math.dist((a.cx, a.cy), (c.cx, c.cy))
    lim = 7.0 if key == 'C_UART' else 6.0          # the bridge's 100 nF: 6.2 mm, both ends on the +3V3 island
    check(dist <= lim, '2. %s at %s pin %s: %.1f mm (limit %.0f)' % (key, ukey, upin, dist, lim))
# ---- 3. USB 27R ---------------------------------------------------------------------------------------------
for pin, key in (('66', 'R_USBM'), ('67', 'R_USBP')):
    net = pad('U_RP', pin).net
    d, nv = path(net, pad('U_RP', pin), pad(key, '2'))
    check(d is not None and d <= 6.0, '3. RP pin %s -> %s: %s' % (pin, key, '%.1f mm, %d vias' % (d, nv) if d is not None else 'NOT CONNECTED'))
# ---- 4. crystal -----------------------------------------------------------------------------------------------
d, nv = path('XIN', pad('U_RP', '30'), pad('Y_RP', '1'))
check(d is not None and d <= 10.0, '4. XIN pin 30 -> crystal: %s' % ('%.1f mm, %d vias' % (d, nv) if d is not None else 'NOT CONNECTED'))
# ---- 5. exposed pads --------------------------------------------------------------------------------------------
for key in ('U_RP', 'U_UART'):
    ep = [p for p in PADS if p.ref == K[key] and C(p.net) == 'GND' and p.hw > 1.0]
    vias = [e for e in b if isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) == 'GND'
            and any(abs(float(find(e, 'at')[1]) - q.cx) < q.hw and abs(float(find(e, 'at')[2]) - q.cy) < q.hh for q in ep)]
    th = [p for p in PADS if p.ref == K[key] and p.th and p.net == 'GND']
    check(len(vias) + len(th) >= 4, '5. %s exposed pad: %d vias + %d plated holes' % (key, len(vias), len(th)))
# ---- 6. USB pairs ---------------------------------------------------------------------------------------------------
for a_, c_ in (('USB_DP', 'USB_DM'), ('UBRG_DP', 'UBRG_DM'), ('RP_USB_DP', 'RP_USB_DM')):
    la, lc = net_length(a_), net_length(c_)
    check(abs(la - lc) <= 10.0, '6. %s / %s: %.1f / %.1f mm, skew %.1f mm (%.0f ps; FS edges 4-20 ns)'
          % (a_, c_, la, lc, abs(la - lc), abs(la - lc) * 6.7))
for n in ('USB_DP', 'USB_DM', 'UBRG_DP', 'UBRG_DM', 'RP_USB_DP', 'RP_USB_DM'):
    cyc = loops(n)
    check(not cyc, '6. %s: no loop in its copper%s' % (n, ' -- cycle at %s' % cyc[:2] if cyc else ''))
for x, y in (('1', '6'), ('3', '4')):
    net = pad('U_ESD', x).net
    d, nv = path(net, pad('U_ESD', x), pad('U_ESD', y))
    check(d is not None, '6. USBLC6 pins %s / %s (%s) joined on copper: %s' % (x, y, net, '%.1f mm' % d if d is not None else 'NO'))
# ---- 7. the edge ------------------------------------------------------------------------------------------------------
bad, worst = [], 0
RKEY = {cn: 'R_' + rn[3:] for cn, rn, g, rv in D.BUS}
for pin, (net, _nm) in D.EDGE.items():
    if net is None or net in ('GND', 'CONS_5V'):
        continue
    key = RKEY[net]
    d, nv = path(net, pad('J_EDGE', str(pin)), pad(key, '1'))
    if d is None or nv > 8:
        bad.append('%s(%s)' % (pin, 'open' if d is None else '%d vias' % nv))
    elif nv > worst:
        worst = nv
check(not bad, '7. every bus finger reaches its series resistor on copper (at most %d vias; ~1 us /PSEN does not mind)%s'
      % (worst, ' -- ' + ', '.join(bad) if bad else ''))
inner = [pts for n, L, pts in fills('', None) if L in ('In1.Cu', 'In2.Cu') and max(p[1] for p in pts) > G.FINGER_Y + 0.01]
check(not inner, '7. In1 / In2: no filled copper below y %.2f (the finger field)' % G.FINGER_Y)
# the console 5 V: finger D -> its neck via -> In2's CONS_5V island <- VIN2's via (no track between them)
isl = fills('cons5v_island')
viav = [(float(find(e, 'at')[1]), float(find(e, 'at')[2])) for e in b if isinstance(e, list) and e and e[0] == 'via'
        and C(str(find(e, 'net')[1])) == 'CONS_5V']
on_isl = [v for v in viav if in_fill(isl, v[0], v[1], 'CONS_5V')]
fp4 = pad('J_EDGE', 'D')
near4 = [v for v in on_isl if abs(v[1] - (G.Y1 - EG.NECK_Y1)) < 1.0 and abs(v[0] - fp4.cx) < 2.0]
vin2 = pad('U_MUX', '6')
d, nv = None, None
for v in on_isl:
    q = type(vin2)('via', 'v', vin2.net, v[0], v[1], 0.3, 0.3, ['F.Cu', 'B.Cu'], True, v)
    d0, n0 = path('CONS_5V', vin2, q)
    if d0 is not None and (d is None or d0 < d):
        d, nv = d0, n0
check(bool(isl) and near4 and d is not None,
      '7. +5V finger (pin D) -> neck via on In2\'s CONS_5V island (%d vias on it) <- TPS2116 VIN2 (%s)'
      % (len(on_isl), '%.1f mm to its via' % d if d is not None else 'NO via on the island'))
# ---- 8. the ESP32-S3 antenna --------------------------------------------------------------------------------------------
ux, uy, _r = G.PLACE[K['U_S3']]
ko = (ux - 24.0, uy - 27.75, ux + 24.0, uy - 6.75)
inside = lambda x, y: ko[0] < x < ko[2] and ko[1] < y < ko[3]
segs = [e for e in b if isinstance(e, list) and e and e[0] == 'segment'
        and (inside(float(find(e, 'start')[1]), float(find(e, 'start')[2])) or inside(float(find(e, 'end')[1]), float(find(e, 'end')[2])))]
vias = [e for e in b if isinstance(e, list) and e and e[0] == 'via' and inside(float(find(e, 'at')[1]), float(find(e, 'at')[2]))]
fl = [1 for n, L, pts in fills('', None) if any(inside(x, y) for x, y in pts)
      and not str(n).startswith('rpi')]
parts_in = [p.ref for p in PADS if p.ref != K['U_S3'] and inside(p.cx, p.cy)]
check(not segs and not vias and not fl and not parts_in, '8. S3 antenna keep-out: %d tracks, %d vias, %d fills, parts %s'
      % (len(segs), len(vias), len(fl), sorted(set(parts_in)) or 'none'))
check(abs((uy - 12.85) - G.Y0) < 0.3, '8. the module\'s antenna end (y %.2f) flush with the top edge (y %.2f)' % (uy - 12.85, G.Y0))
# ---- 9. buck input loop ----------------------------------------------------------------------------------------------------
for key in ('C_BIN', 'C_BINHF'):
    a, c = pad('U_BUCK', '3'), pad(key, '1')
    dist = math.dist((a.cx, a.cy), (c.cx, c.cy))
    check(dist <= 5.0, '9. buck VIN -> %s: %.1f mm' % (key, dist))
print('%d failures' % len(fails))
sys.exit(1 if fails else 0)
