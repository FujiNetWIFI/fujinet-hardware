#!/usr/bin/env python3
"""Measure the routed board's layout claims (docs/floorplan-study.md, docs/design-review-rev0.md) on the
copper itself, and fail if one does not hold:

  1. VREG_VOUT 1 uF and the two DVDD 100 nF: the copper path from RP2040 pin 45 to each capacitor's DVDD
     pad, and that it has no via (design guide 2.1.3: 1 uF close to VREG_OUT)
  2. VREG_VIN 1 uF: the copper path from pin 44 (design guide 2.1.3: 1 uF close to VREG_IN)
  3. the USB 27R: copper path from pins 46 / 47 to each resistor (design guide 2.4: close to the chip)
  4. the AP63203 input loop: VIN and GND pins to the 100 nF on F.Cu only, and the loop's length
     (AP63203 datasheet, Layout 4: VIN capacitors as close to the device as possible)
  5. the crystal: XIN's track length pin 20 -> crystal (design guide 2.3: keep the layout short)
  6. the exposed pads: vias inside the RP2040's and the CP2102N's
  7. the USB pairs: the length of each line and the skew within each pair (full speed: edges 4-20 ns)
  8. the ESP32-S3 antenna keep-out: no track, via or filled copper inside it on any layer
  9. the ESP32-S3's 3V3 pin: its 100 nF and 22 uF (the datasheet's peripheral schematic) beside it

Copper paths are shortest paths over the net's own tracks and vias (pad to pad); a via adds no length but
is counted.  Usage: python3 tools/audit/layout_checks.py [board]      exit 1 on any failure
"""
import heapq, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gen_pcb as G
from sexpr import parse, find, findall

PCB = sys.argv[1] if len(sys.argv) > 1 else G.PCB
K = G.K
fails = []


def check(ok, msg):
    print(('ok   ' if ok else 'FAIL ') + msg)
    if not ok:
        fails.append(msg)


b = parse(open(PCB).read())
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
    # track ends that touch each other mid-segment (T-junctions): join every node to segments it lies on
    nodes = list(adj)
    for s in segs:
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
        return [n for n in adj if n[2] in p.layers and abs(n[0] - p.cx) <= p.hw + 1e-3 and abs(n[1] - p.cy) <= p.hh + 1e-3]
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


def net_length(net):
    return sum(math.dist((float(find(s, 'start')[1]), float(find(s, 'start')[2])),
                         (float(find(s, 'end')[1]), float(find(s, 'end')[2])))
               for s in b if isinstance(s, list) and s and s[0] == 'segment' and str(find(s, 'net')[1]) == net)


# ---- 1. VREG_VOUT / DVDD ------------------------------------------------------------------------------
DVDD = G.NET('DVDD')
for key, lim in (('C_VREGOUT', 6.0), ('C_DV50', 8.5), ('C_DV23', 10.5)):
    p = next(q for q in PADS if q.ref == K[key] and q.net == DVDD)
    d, nv = path(DVDD, pad('U_RP', '45'), p)
    check(d is not None and d <= lim and nv == 0,
          '1. RP pin 45 -> %s (%s) DVDD pad: %s of copper, %s vias (limit %.1f mm, no via)'
          % (K[key], key, '%.1f mm' % d if d is not None else 'NOT CONNECTED', nv, lim))
# ---- 2. VREG_VIN --------------------------------------------------------------------------------------
P33 = G.NET('+3V3_RP')
cvi = next(q for q in PADS if q.ref == K['C_VREGIN'] and q.net == P33)
d, nv = path(P33, pad('U_RP', '44'), cvi)
check(d is not None and d <= 5.0, '2. RP pin 44 (VREG_VIN) -> %s 1 uF: %s of copper' % (
    K['C_VREGIN'], '%.1f mm' % d if d is not None else 'NOT CONNECTED'))
# ---- 3. USB 27R -------------------------------------------------------------------------------------
for pin, key, net in (('46', 'R_USBM', 'RP_USB_DM'), ('47', 'R_USBP', 'RP_USB_DP')):
    n = G.NET(net)
    r = next(q for q in PADS if q.ref == K[key] and q.net == n)
    d, nv = path(n, pad('U_RP', pin), r)
    check(d is not None and d <= 7.0, '3. RP pin %s -> %s (27R): %s of copper' % (
        pin, K[key], '%.1f mm' % d if d is not None else 'NOT CONNECTED'))
# ---- 4. the buck's input loop ---------------------------------------------------------------------------
loop = 0.0
for pin, num, net in (('3', '1', G.NET('+5V')), ('4', '2', 'GND')):
    c = pad('C_BINHF', num)
    d, nv = path(net, pad('U_BUCK', pin), c)
    check(d is not None and nv == 0 and d <= 2.5, '4. AP63203 pin %s -> %s pad %s on F.Cu: %s, %s vias' % (
        pin, K['C_BINHF'], num, '%.1f mm' % d if d is not None else 'NOT CONNECTED', nv))
    loop += d or 0
xy = lambda q: (q.cx, q.cy)
around = loop + math.dist(xy(pad('U_BUCK', '3')), xy(pad('U_BUCK', '4'))) + \
    math.dist(xy(pad('C_BINHF', '1')), xy(pad('C_BINHF', '2')))
# ~3.8 mm of that is the parts themselves (the TSOT's VIN-GND pin spacing, the 0603's pad pitch)
check(around < 8.0, '4. the hot loop VIN -> 100 nF -> GND -> IC: %.1f mm around (%.1f mm of it inside the two parts)'
      % (around, around - loop))
# ---- 5. crystal --------------------------------------------------------------------------------------
XIN = G.NET('XIN')
d, nv = path(XIN, pad('U_RP', '20'), pad('Y_RP', '1'))
check(d is not None and d <= 6.0, '5. XIN: RP pin 20 -> %s: %s' % (K['Y_RP'], '%.1f mm' % d if d is not None else 'NOT CONNECTED'))
# ---- 6. exposed-pad vias ---------------------------------------------------------------------------------
for key, want in (('U_RP', 9), ('U_UART', 9)):
    ep = max((q for q in PADS if q.ref == K[key]), key=lambda q: q.hw * q.hh)
    n = sum(1 for v in b if isinstance(v, list) and v and v[0] == 'via' and str(find(v, 'net')[1]) == 'GND'
            and abs(float(find(v, 'at')[1]) - ep.cx) < ep.hw and abs(float(find(v, 'at')[2]) - ep.cy) < ep.hh)
    check(n >= want, '6. %s (%s) exposed pad: %d GND vias in it' % (K[key], key, n))
# ---- 7. USB pairs -----------------------------------------------------------------------------------------
for dp, dm in (('UBRG_DP', 'UBRG_DM'), ('USB_DP', 'USB_DM'), ('RP_USB_DP', 'RP_USB_DM')):
    lp, lm = net_length(G.NET(dp)), net_length(G.NET(dm))
    # USB 2.0 full speed: driver rise / fall 4-20 ns.  25 mm of skew is ~150 ps (FR-4 microstrip ~6 ps/mm),
    # under 4 % of the fastest edge
    check(abs(lp - lm) < 25.0, '7. %s / %s: %.1f / %.1f mm, skew %.1f mm (~%.0f ps; full-speed edges are 4-20 ns)'
          % (dp, dm, lp, lm, abs(lp - lm), abs(lp - lm) * 6))
# ---- 8. the S3 antenna keep-out ---------------------------------------------------------------------------
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
        s, t = find(e, 'start'), find(e, 'end')
        if any(inside(float(p[1]), float(p[2])) for p in (s, t)):
            hits.append('track %s' % find(e, 'net')[1])
    elif e[0] == 'via' and inside(float(find(e, 'at')[1]), float(find(e, 'at')[2])):
        hits.append('via %s' % find(e, 'net')[1])
    elif e[0] == 'zone' and not find(e, 'keepout'):
        for fp_ in findall(e, 'filled_polygon'):
            if any(inside(float(q[1]), float(q[2])) for q in find(fp_, 'pts')[1:] if q[0] == 'xy'):
                hits.append('fill of %s on %s' % (find(e, 'name')[1] if find(e, 'name') else '?', find(fp_, 'layer')[1]))
                break
check(not hits, '8. ESP32-S3 antenna keep-out x %.1f-%.1f, y %.1f-%.1f (on the board: y %.1f-%.1f): empty on every layer%s'
      % (kx0, kx1, ky0, ky1, G.Y0, ky1, (' -- ' + ', '.join(sorted(set(hits))[:6])) if hits else ''))
# ---- 9. the ESP32-S3's 3V3 decoupling --------------------------------------------------------------------
P3 = '+3V3'
s3v = next(q for q in PADS if q.ref == K['U_S3'] and q.net == P3)
for key, lim in (('C_S3', 4.0), ('C_S3BULK', 7.0)):
    c = next(q for q in PADS if q.ref == K[key] and q.net == P3)
    d, nv = path(P3, s3v, c)
    gap = math.dist((s3v.cx, s3v.cy), (c.cx, c.cy))
    check(gap <= lim, '9. ESP32-S3 3V3 (pin %s) -> %s (%s) +3V3 pad: %.1f mm apart, %s (limit %.1f mm)' % (
        s3v.num, K[key], key, gap, 'copper path %.1f mm, %d vias' % (d, nv) if d is not None else 'joined through the In2 plane', lim))
print('layout_checks: %s' % ('%d FAILED' % len(fails) if fails else 'all pass'))
sys.exit(1 if fails else 0)
