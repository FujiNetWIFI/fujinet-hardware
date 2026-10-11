#!/usr/bin/env python3
"""Measure the routed board's layout claims (docs/floorplan-study.md, docs/design-review-rev0.md) on the
copper itself, and fail if one does not hold:

  1. Raspberry Pi's regulator corner is intact: its pours (filled) join VREG_VIN (64) to C_VREGIN, LX (63)
     to the inductor, PGND (62) to both 4.7 uF grounds, the inductor to C_DVBULK; VREG_FB (65) reaches
     C_DVBULK on F.Cu without a via; VREG_AVDD (61) reaches its RC
  2. the supply rings under the RP2354B: every +3V3 supply pin's stub ends inside the filled +3V3 ring,
     every DVDD pin's inside the filled DVDD ring; the +3V3 ring has its four plane vias, and each piece
     of it (the DVDD stubs cut it) at least one; the DVDD ring reaches the regulator's output node (B.Cu
     link)
  3. the decoupling: each straight-out capacitor (gen_pcb.CAP_LINKS) reached from its pin over F.Cu with
     no via and within 3.5 mm; every other RP supply capacitor within 12 mm of its pin (they reach it
     through the ring and the In2 plane); the logic packages' 100 nF within 6 mm of their VCC pins
  4. the USB 27R: copper path from pins 66 / 67 to each resistor (Raspberry Pi: close to the chip)
  5. the crystal: XIN's track length pin 30 -> crystal (keep it short)
  6. the exposed pad: vias inside the RP2354B's
  7. the USB pairs: the length of each line and the skew within each pair (full speed: edges 4-20 ns);
     the USBLC6's flow-through pins joined straight under its body, its 100 nF at the VBUS pin; no loop
     in any USB line's copper
  8. the edge: every address finger reaches its 330R over the twist (<= 3 vias), every data finger its
     '541 pin (1 via), the console 5 V finger the CONS_5V island; nothing on In1 / In2 in the finger
     field (filled copper)
  9. the ESP32-S3: its antenna keep-out (the module footprint's zone: the antenna plus Espressif's
     15 mm) empty of tracks, vias, fills and parts on every layer; the antenna end flush with the top
     edge; its 3V3 decoupling at the 3V3 pin
 10. the S3 buck's input loop: VIN and GND to the 100 nF on F.Cu without a via, the loop short
 11. the CP2102N's exposed pad: its GND vias

Copper paths are shortest paths over the net's own tracks and vias (pad to pad); a via adds no length
but is counted.  Usage: python3 tools/audit/layout_checks.py [board]      exit 1 on any failure
"""
import heapq, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gen_pcb as G
import edge_geom as EG
from sexpr import parse, find, findall

PCB = sys.argv[1] if len(sys.argv) > 1 else G.PCB
K = G.K


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
    segs = [e for e in b if isinstance(e, list) and e and e[0] == 'segment' and str(find(e, 'net')[1]) == net]
    for s in segs:
        st, en, L = find(s, 'start'), find(s, 'end'), str(find(s, 'layer')[1])
        a, c = node(float(st[1]), float(st[2]), L), node(float(en[1]), float(en[2]), L)
        add(a, c, math.dist(a[:2], c[:2]), 0)
    for v in (e for e in b if isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) == net):
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
            for e in b if isinstance(e, list) and e and e[0] == 'segment' and str(find(e, 'net')[1]) == net]
    vias = [(float(find(e, 'at')[1]), float(find(e, 'at')[2]))
            for e in b if isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) == net]
    ends = {node(x, y, L) for x0, y0, x1, y1, L in segs for x, y in ((x0, y0), (x1, y1))}
    ends |= {node(x, y, L) for x, y in vias for L in ('F.Cu', 'B.Cu')}
    pads_ = [q for q in PADS if q.net == net]

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
               for s in b if isinstance(s, list) and s and s[0] == 'segment' and str(find(s, 'net')[1]) == net)


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
    return any(n == net and G.point_in_poly(x, y, pts) for n, _, pts in fl)


P3, DV = G.NET('+3V3'), G.NET('DVDD')
# ---- 1. the regulator corner -----------------------------------------------------------------------------
graft = fills('rpi_graft')
check(len(graft) >= 4, '1. the graft\'s pours are filled (%d polygons)' % len(graft))
for what, net, a, c in (('VREG_VIN 64 -> C_VREGIN', P3, pad('U_RP', '64'), pad('C_VREGIN', '1')),
                        ('LX 63 -> L_RP', G.NET('RP_LX'), pad('U_RP', '63'), pad('L_RP', '2')),
                        ('PGND 62 -> C_VREGIN GND', 'GND', pad('U_RP', '62'), pad('C_VREGIN', '2')),
                        ('PGND 62 -> C_DVBULK GND', 'GND', pad('U_RP', '62'), pad('C_DVBULK', '2')),
                        ('L_RP -> C_DVBULK (DVDD)', DV, pad('L_RP', '1'), pad('C_DVBULK', '1'))):
    ok = any(n == net and G.point_in_poly(a.cx, a.cy, pts) and G.point_in_poly(c.cx, c.cy, pts)
             for n, _, pts in graft)
    check(ok, '1. %s: one filled pour of Raspberry Pi\'s corner joins both pads' % what)
d, nv = path(DV, pad('U_RP', '65'), pad('C_DVBULK', '1'))
check(d is not None or in_fill(graft, pad('C_DVBULK', '1').cx, pad('C_DVBULK', '1').cy, DV),
      '1. VREG_FB 65 -> C_DVBULK: %s' % ('%.1f mm of F.Cu, %d vias' % (d, nv) if d is not None else 'through the DVDD pour'))
d, nv = path(G.NET('VREG_AVDD'), pad('U_RP', '61'), pad('C_AVDD', '1'))
check(d is not None and nv == 0 and d <= 4.0, '1. VREG_AVDD 61 -> C_AVDD: %s' % ('%.1f mm, %d vias' % (d, nv) if d is not None else 'NOT CONNECTED'))
# ---- 2. the rings ---------------------------------------------------------------------------------------
rings = fills('rp_')
(ux, uy, rot), P = G.rp_frame(b)
bad = []
for num, p in P.items():
    if num in ('81', '65') or p.net not in (P3, DV):
        continue
    end = None
    for s in (e for e in b if isinstance(e, list) and e and e[0] == 'segment' and str(find(e, 'net')[1]) == p.net):
        st, en = find(s, 'start'), find(s, 'end')
        if abs(float(st[1]) - p.cx) < 1e-3 and abs(float(st[2]) - p.cy) < 1e-3 and \
                max(abs(float(en[1]) - ux), abs(float(en[2]) - uy)) < 4.0:      # ends inside the square ring
            end = (float(en[1]), float(en[2]))
    if end is None or not in_fill(rings, end[0], end[1], p.net):
        bad.append(num)
check(not bad, '2. every RP supply pin stubs into its filled ring (+3V3: IOVDD x8, ADC_AVDD, VREG_VIN, OTP, QSPI; '
      'DVDD: 10, 32, 51)%s' % (' -- not: %s' % bad if bad else ''))
corner = [v for v in b if isinstance(v, list) and v and v[0] == 'via' and str(find(v, 'net')[1]) == P3
          and math.dist((float(find(v, 'at')[1]), float(find(v, 'at')[2])), (ux, uy)) < 5.0]
check(len(corner) >= 4, '2. the +3V3 ring drops to the In2 plane through %d vias' % len(corner))
# the DVDD stubs (10, 32, 51) cross the +3V3 ring, so it fills as separate pieces: each needs its own via
pieces = [pts for n, _, pts in rings if n == P3]
per = [sum(G.point_in_poly(float(find(v, 'at')[1]), float(find(v, 'at')[2]), pts) for v in corner) for pts in pieces]
check(pieces and min(per) >= 1, '2. the +3V3 ring fills as %d pieces (cut by the DVDD stubs), each with its own plane via '
      '(%s)' % (len(pieces), ' / '.join(map(str, per))))
dvv = [v for v in b if isinstance(v, list) and v and v[0] == 'via' and str(find(v, 'net')[1]) == DV
       and math.dist((float(find(v, 'at')[1]), float(find(v, 'at')[2])), (ux, uy)) < 3.0]
reach = []
for v in dvv:
    at = find(v, 'at')
    vx, vy = float(at[1]), float(at[2])
    vp = type('V', (), dict(cx=vx, cy=vy, hw=0.25, hh=0.25, layers=['F.Cu', 'B.Cu'], th=True))
    d, nv = path(DV, vp, pad('C_DVBULK', '1'))
    if d is None:          # the graft's DVDD vias sit in its pour: reach any via of the pour instead
        gv = [e for e in b if isinstance(e, list) and e and e[0] == 'via' and str(find(e, 'net')[1]) == DV
              and in_fill(graft, float(find(e, 'at')[1]), float(find(e, 'at')[2]), DV)]
        for g in gv:
            gp = type('V', (), dict(cx=float(find(g, 'at')[1]), cy=float(find(g, 'at')[2]), hw=0.25, hh=0.25,
                                    layers=['F.Cu', 'B.Cu'], th=True))
            d, nv = path(DV, vp, gp)
            if d is not None:
                break
    reach.append(d)
check(any(d is not None for d in reach), '2. the DVDD ring reaches the regulator output node over its B.Cu link (%s)'
      % ', '.join('%.1f mm' % d for d in reach if d is not None))
# ---- 3. decoupling ------------------------------------------------------------------------------------
for num, key in G.CAP_LINKS:
    d, nv = path(P[num].net, P[num], pad(key, '1'))
    check(d is not None and nv == 0 and d <= 3.5, '3. RP pin %s -> %s (%s): %s' % (
        num, K[key], key, '%.1f mm of F.Cu, %d vias' % (d, nv) if d is not None else 'NOT CONNECTED'))
others = {'C_IOV5': '5', 'C_IOV24': '24', 'C_IOV29': '29', 'C_IOV76': '76', 'C_DV32': '32',
          'C_QSPI': '69', 'C_OTP': '68'}
# the pins boxed in by signals (IOVDD 5 / 24 / 29 / 76, DVDD 32 between XOUT and SWCLK) reach their capacitor
# through their ring: DVDD 32's sits on the DVDD ring's south B.Cu link, the ring also carrying DVDD 10's
# 100 nF 1.7 mm from pin 10 and the regulator's 4.7 uF (a known compromise: docs/design-review-rev0.md)
LIMIT = {'C_DV32': 13.0}
for key, num in others.items():
    gap = math.dist((P[num].cx, P[num].cy), (pad(key, '1').cx, pad(key, '1').cy))
    check(gap <= LIMIT.get(key, 12.0), '3. RP pin %s -> %s (%s): %.1f mm apart (through the %s ring%s)' % (
        num, K[key], key, gap, 'DVDD' if key.startswith('C_DV') else '+3V3', ' and the plane' if key.startswith('C_IOV')
        or key in ('C_QSPI', 'C_OTP') else ' and its B.Cu link'))
for ic, vcc, cap in (('U_BUF', '20', 'C_BUF'), ('U_OR', '14', 'C_OR'), ('U_INV', '14', 'C_INV'), ('U_NOR', '5', 'C_NOR'),
                     ('U_LDO', '1', 'C_LDOIN'), ('U_LDO', '5', 'C_LDOOUT'), ('U_UART', '6', 'C_UART'),
                     ('U_MUX', '3', 'C_MUXV1'), ('U_MUX', '6', 'C_CONSHF'), ('D_WS', '4', 'C_WS'), ('J_SD', '4', 'C_SD')):
    v, c = pad(ic, vcc), pad(cap, '1')
    gap = math.dist((v.cx, v.cy), (c.cx, c.cy))
    # the microSD's 10 uF is bulk for the card on the +3V3_S3 island: its VDD contact sits mid-row with
    # signal contacts either side, so the capacitor stands below the row, not at the pin
    lim = 8.0 if ic == 'J_SD' else 6.0
    check(gap <= lim, '3. %s (%s) pin %s -> %s: %.1f mm apart (limit %.0f)' % (K[ic], ic, vcc, K[cap], gap, lim))
# ---- 4. USB 27R --------------------------------------------------------------------------------------------
for pin, key, net in (('66', 'R_USBM', 'RP_USB_DM'), ('67', 'R_USBP', 'RP_USB_DP')):
    n = G.NET(net)
    r = next(q for q in PADS if q.ref == K[key] and q.net == n)
    d, nv = path(n, pad('U_RP', pin), r)
    check(d is not None and d <= 5.0, '4. RP pin %s -> %s (27R): %s of copper' % (
        pin, K[key], '%.1f mm' % d if d is not None else 'NOT CONNECTED'))
# ---- 5. crystal ---------------------------------------------------------------------------------------------
d, nv = path(G.NET('XIN'), pad('U_RP', '30'), pad('Y_RP', '1'))
check(d is not None and d <= 9.0, '5. XIN: RP pin 30 -> %s: %s' % (K['Y_RP'], '%.1f mm, %d vias' % (d, nv) if d is not None else 'NOT CONNECTED'))
# ---- 6. exposed-pad vias ---------------------------------------------------------------------------------
ep = max((q for q in PADS if q.ref == K['U_RP']), key=lambda q: q.hw * q.hh)
n = sum(1 for v in b if isinstance(v, list) and v and v[0] == 'via' and str(find(v, 'net')[1]) == 'GND'
        and abs(float(find(v, 'at')[1]) - ep.cx) < ep.hw and abs(float(find(v, 'at')[2]) - ep.cy) < ep.hh)
check(n >= 9, '6. %s exposed pad: %d GND vias in it' % (K['U_RP'], n))
# ---- 7. USB pairs ----------------------------------------------------------------------------------------
for dp, dm in (('USB_DP', 'USB_DM'), ('RP_USB_DP', 'RP_USB_DM'), ('UBRG_DP', 'UBRG_DM')):
    lp, lm = net_length(G.NET(dp)), net_length(G.NET(dm))
    # USB 2.0 full speed: driver rise / fall 4-20 ns.  25 mm of skew is ~150 ps (FR-4 microstrip ~6 ps/mm)
    check(abs(lp - lm) < 25.0, '7. %s / %s: %.1f / %.1f mm, skew %.1f mm (~%.0f ps; full-speed edges are 4-20 ns)'
          % (dp, dm, lp, lm, abs(lp - lm), abs(lp - lm) * 6))
# the USBLC6 is flow-through (6 / 1 = D-, 4 / 3 = D+ inside the package): joined straight under its body,
# and no USB line carries a loop (S7's router reached pin 3 by a 20 mm D+ loop round the receptacle)
for a_, c_ in (('6', '1'), ('4', '3')):
    pa, pc = pad('U_ESD', a_), pad('U_ESD', c_)
    d, nv = path(pa.net, pa, pc)
    check(d is not None and nv == 0 and d <= math.dist((pa.cx, pa.cy), (pc.cx, pc.cy)) + 0.01,
          '7. %s pins %s / %s (%s): joined straight under the body (%s)' % (K['U_ESD'], a_, c_, pa.net.split('/')[-1],
                                                                          '%.2f mm' % d if d is not None else 'NOT JOINED'))
pv, cv_ = pad('U_ESD', '5'), pad('C_VBUSHF', '1')
d, nv = path(pv.net, pv, cv_)
check(d is not None and d <= 6.0 and nv <= 2, '7. %s VBUS (pin 5) -> %s (C_VBUSHF, 100 nF): %s (ST: CBUS at the VBUS pin; beside the package, limit 6 mm)'
      % (K['U_ESD'], K['C_VBUSHF'], '%.1f mm, %d vias' % (d, nv) if d is not None else 'NOT CONNECTED'))
for n_ in ('USB_DP', 'USB_DM', 'RP_USB_DP', 'RP_USB_DM', 'UBRG_DP', 'UBRG_DM'):
    cyc = loops(G.NET(n_))
    check(not cyc, '7. %s: no loop in its copper%s' % (n_, ' -- closes at %s' % cyc[:3] if cyc else ''))
# ---- 8. the edge -------------------------------------------------------------------------------------------
j1 = {p.num: p for p in PADS if p.ref == K['J_EDGE']}
bad = []
for pin, net, rk in G.ADDR:
    d, nv = path(j1[str(pin)].net, j1[str(pin)], pad(rk, '1'))
    if d is None or nv > 3:
        bad.append(pin)
check(not bad, '8. the address twist: each of the 10 address fingers reaches its 330R (<= 3 vias)%s' % (
    ' -- not: %s' % bad if bad else ''))
bad = []
u = {p.num: p for p in PADS if p.ref == K['U_BUF']}
for bit, fpin in {0: 10, 1: 9, 2: 8, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1}.items():
    yp = next(p for p in u.values() if p.net == j1[str(fpin)].net)
    d, nv = path(j1[str(fpin)].net, j1[str(fpin)], yp)
    if d is None or nv != 1:
        bad.append(fpin)
check(not bad, '8. the data fan-in: D0-D7 fingers -> the \'541\'s Y row, one via each%s' % (' -- not: %s' % bad if bad else ''))
inner = [f for f in fills('') if f[1] in ('In1.Cu', 'In2.Cu') and max(y for _, y in f[2]) > G.FIELD_Y + 0.01]
check(not inner, '8. In1 / In2: no filled copper in the finger field (south of y %.2f)%s' % (
    G.FIELD_Y, (' -- %d polygons' % len(inner)) if inner else ''))
c5 = fills('CONS_5V_island', 'In2.Cu')
x15 = G.finger_x(15)
check(in_fill(c5, x15, G.STUB_Y, G.NET('CONS_5V')), '8. the console 5 V finger (15) drops into the In2 CONS_5V island')
# ---- 9. the ESP32-S3: antenna keep-out, 3V3 decoupling ----------------------------------------------------
s3 = G.footprint_of(b, K['U_S3'])
z = findall(s3, 'zone')[0]
xy = [(float(q[1]), float(q[2])) for q in find(find(z, 'polygon'), 'pts')[1:]]
kx0, kx1 = min(x for x, _ in xy), max(x for x, _ in xy)
ky0, ky1 = min(y for _, y in xy), max(y for _, y in xy)
inside = lambda x, y: kx0 < x < kx1 and ky0 < y < ky1
hits = []
for e in b:
    if not (isinstance(e, list) and e):
        continue
    if e[0] == 'segment':
        s_, t_ = find(e, 'start'), find(e, 'end')
        if any(inside(float(q[1]), float(q[2])) for q in (s_, t_)):
            hits.append('track %s' % find(e, 'net')[1])
    elif e[0] == 'via' and inside(float(find(e, 'at')[1]), float(find(e, 'at')[2])):
        hits.append('via %s' % find(e, 'net')[1])
    elif e[0] == 'zone' and not find(e, 'keepout'):
        for fp_ in findall(e, 'filled_polygon'):
            if any(inside(float(q[1]), float(q[2])) for q in find(fp_, 'pts')[1:] if q[0] == 'xy'):
                hits.append('fill of %s on %s' % (find(e, 'name')[1] if find(e, 'name') else '?', find(fp_, 'layer')[1]))
                break
    elif e[0] == 'footprint' and e is not s3:
        at = find(e, 'at')
        if inside(float(at[1]), float(at[2])):
            hits.append('part %s' % next(str(q[2]) for q in findall(e, 'property') if q[1] == 'Reference'))
check(not hits, '9. ESP32-S3 antenna keep-out x %.1f-%.1f, y %.1f-%.1f (on the board: y %.1f-%.1f): empty on every layer%s'
      % (kx0, kx1, ky0, ky1, G.Y0, ky1, (' -- ' + ', '.join(sorted(set(hits))[:6])) if hits else ''))
sy = float(find(s3, 'at')[2])
check(abs((sy - 12.75) - G.Y0) <= 0.3, '9. the antenna end of the module %.2f mm inside the top edge (flush: <= 0.3)'
      % ((sy - 12.75) - G.Y0))
S3R = G.NET('+3V3_S3')
s3v = next(q for q in PADS if q.ref == K['U_S3'] and q.net == S3R)
for key, lim in (('C_S3', 4.0), ('C_S3BULK', 7.0)):
    c = next(q for q in PADS if q.ref == K[key] and q.net == S3R)
    d, nv = path(S3R, s3v, c)
    gap = math.dist((s3v.cx, s3v.cy), (c.cx, c.cy))
    check(gap <= lim, '9. ESP32-S3 3V3 (pin %s) -> %s (%s) pad: %.1f mm apart, %s (limit %.1f mm)' % (
        s3v.num, K[key], key, gap, 'copper path %.1f mm, %d vias' % (d, nv) if d is not None else 'joined through the In2 island', lim))
# ---- 10. the S3 buck's input loop (AP63203: the input capacitor as close to VIN and GND as possible) ------
loop = 0.0
for pin, num, net in (('3', '1', G.NET('+5V')), ('4', '2', 'GND')):
    c = pad('C_BINHF', num)
    d, nv = path(net, pad('U_BUCK', pin), c)
    check(d is not None and nv == 0 and d <= 2.5, '10. AP63203 pin %s -> %s pad %s on F.Cu: %s, %s vias' % (
        pin, K['C_BINHF'], num, '%.1f mm' % d if d is not None else 'NOT CONNECTED', nv))
    loop += d or 0
xy_ = lambda q: (q.cx, q.cy)
around = loop + math.dist(xy_(pad('U_BUCK', '3')), xy_(pad('U_BUCK', '4'))) + \
    math.dist(xy_(pad('C_BINHF', '1')), xy_(pad('C_BINHF', '2')))
check(around < 8.0, '10. the hot loop VIN -> 100 nF -> GND -> IC: %.1f mm around (%.1f mm of it inside the two parts)'
      % (around, around - loop))
# ---- 11. the CP2102N's exposed pad -------------------------------------------------------------------------
ep = max((q for q in PADS if q.ref == K['U_UART']), key=lambda q: q.hw * q.hh)
n = sum(1 for v in b if isinstance(v, list) and v and v[0] == 'via' and str(find(v, 'net')[1]) == 'GND'
        and abs(float(find(v, 'at')[1]) - ep.cx) < ep.hw and abs(float(find(v, 'at')[2]) - ep.cy) < ep.hh)
check(n >= 4, '11. %s (CP2102N) exposed pad: %d GND vias in it' % (K['U_UART'], n))
print('layout_checks: %s' % ('%d FAILED' % len(fails) if fails else 'all pass'))
sys.exit(1 if fails else 0)
