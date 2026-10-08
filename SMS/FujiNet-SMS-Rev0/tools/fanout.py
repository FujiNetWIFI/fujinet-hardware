"""Plane fan-out for gen_pcb.py (FujiNet-SMS Rev0).

Every SMD pad on a plane net (GND -> In1.Cu; +3V3, +5V, +3V3_RP, DVDD ->
the In4 plane and its islands, where gen_pcb.py has checked the island
under the pad carries that net) gets a short stub and a via, placed here
geometrically with explicit clearance checks, and written LOCKED so the
autorouter keeps them.  QFN exposed pads get a via array.  Freerouting is
then left with signal nets only -- it is poor at plane fan-out on its own.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

PLANE_NETS = ('GND', '+3V3', '+5V', '+3V3_RP', 'DVDD')
VIA_D, VIA_DRILL = 0.6, 0.3
STUB_W = 0.3
CLR = 0.16          # copper clearance kept by the fan-out (rules say 0.15)
EDGE_CLR = 0.6
EP_ARRAYS = {D.KEY['U_RP']: 3, D.KEY['U_UART']: 3}   # exposed-pad via grid (n x n): RP2354B QFN-80, CP2102N QFN-28
ESCAPE = 1.2        # length of the via-free lane kept in front of fine-pitch signal pins
# supply pins whose plane via sits ~3 mm out (see plan()): IOVDD 24 and 29 box in four strobes
# (25-28: /RD /WR /MREQ /CE) at 0.4 mm pitch, as on NES Rev0
FAR_VIA = {(D.KEY['U_RP'], '24'), (D.KEY['U_RP'], '29')}


class Pad:
    def __init__(self, ref, num, net, cx, cy, hw, hh, layers, th, fp_xy):
        self.ref, self.num, self.net = ref, num, net
        self.cx, self.cy, self.hw, self.hh = cx, cy, hw, hh
        self.layers, self.th, self.fp_xy = layers, th, fp_xy

    def dist(self, x, y):
        """distance from point to the pad rectangle (0 inside)."""
        dx = max(abs(x - self.cx) - self.hw, 0)
        dy = max(abs(y - self.cy) - self.hh, 0)
        return math.hypot(dx, dy)


def _seg_ok(x0, y0, x1, y1, pads, own, net, half):
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
    for i in range(n + 1):
        t = i / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        for p in pads:
            if p is own or ('F.Cu' not in p.layers and not p.th):
                continue
            if p.net == net and p.dist(x, y) < 1e-6:
                continue
            if p.net != net and p.dist(x, y) < half + CLR:
                return False
    return True


def plan(pads, keepouts, board_box, blade_y, holes, skip_refs=(), extra_segs=(), extra_vias=(), skip_pads=()):
    """Return (vias, segments, failed): new vias [(x, y, net)] and stubs
    [(x0, y0, x1, y1, net, width)].  extra_* is existing copper to respect."""
    vias, segs = list(extra_vias), list(extra_segs)
    n_vias0, n_segs0 = len(vias), len(segs)
    X0, Y0, X1, Y1 = board_box

    # Escape corridors: in front of every fine-pitch signal pin keep a lane
    # (pad width + clearance each side, ESCAPE mm long) free of fan-out vias,
    # or a power pin's via walls off its neighbours' only way out.
    corridors = []
    for q in pads:
        if q.th or q.net in PLANE_NETS or q.net is None or min(q.hw, q.hh) > 0.15:
            continue
        fx, fy = q.fp_xy
        esc = ESCAPE
        if q.hh > q.hw:      # pin on a top/bottom side: escapes along y
            sgn = 1 if q.cy > fy else -1
            ya, yb = sorted((q.cy + sgn * q.hh, q.cy + sgn * (q.hh + esc)))
            corridors.append((q.cx - q.hw - 0.12, ya, q.cx + q.hw + 0.12, yb))
        else:
            sgn = 1 if q.cx > fx else -1
            xa, xb = sorted((q.cx + sgn * q.hw, q.cx + sgn * (q.hw + esc)))
            corridors.append((xa, q.cy - q.hh - 0.12, xb, q.cy + q.hh + 0.12))

    def via_ok(x, y, net, own=None):
        for (cx0, cy0, cx1, cy1) in corridors:
            dx = max(cx0 - x, 0, x - cx1)
            dy = max(cy0 - y, 0, y - cy1)
            if math.hypot(dx, dy) < VIA_D / 2 + 0.05:
                return False
        if not (X0 + EDGE_CLR < x < X1 - EDGE_CLR and Y0 + EDGE_CLR < y < Y1 - EDGE_CLR):
            return False
        if y > blade_y - VIA_D / 2 - 0.2:
            return False
        for (hx, hy, hr) in holes:
            if math.hypot(x - hx, y - hy) < hr + VIA_D / 2 + 0.3:
                return False
        for (kx0, ky0, kx1, ky1) in keepouts:
            if kx0 - VIA_D / 2 < x < kx1 + VIA_D / 2 and ky0 - VIA_D / 2 < y < ky1 + VIA_D / 2:
                return False
        for p in pads:
            if p is own:
                continue
            d = p.dist(x, y)
            need = VIA_D / 2 + (0.3 if p.th else CLR)
            if p.net == net and not p.th:
                need = VIA_D / 2 + 0.1   # not inside a same-net pad either (no via-in-pad)
            if d < need:
                return False
        for (vx, vy, vn) in vias:
            if math.hypot(x - vx, y - vy) < VIA_D + (0.25 if vn == net else CLR + 0.05):
                return False
        for (sx0, sy0, sx1, sy1, sn, sw_) in segs:
            if sn != net and _pt_seg(x, y, sx0, sy0, sx1, sy1) < VIA_D / 2 + sw_ / 2 + CLR:
                return False
        return True

    by_ref = {}
    for p in pads:
        by_ref.setdefault(p.ref, []).append(p)

    # exposed-pad via arrays
    for ref, n in EP_ARRAYS.items():
        ep = max(by_ref.get(ref, []), key=lambda p: p.hw * p.hh)
        pitch = min(ep.hw, ep.hh) * 2 / (n + 0.5)
        for i in range(n):
            for j in range(n):
                vias.append((ep.cx + (i - (n - 1) / 2) * pitch, ep.cy + (j - (n - 1) / 2) * pitch, ep.net))

    todo = [p for p in pads if p.net in PLANE_NETS and not p.th and 'F.Cu' in p.layers
            and p.ref not in EP_ARRAYS.keys() | set(skip_refs)]
    todo += [p for p in pads if p.ref in EP_ARRAYS and p.net in PLANE_NETS and not p.th
             and p is not max(by_ref[p.ref], key=lambda q: q.hw * q.hh)]
    failed = []
    todo = [p for p in todo if id(p) not in set(skip_pads)]
    for p in todo:
        # a pad already touching a same-net via (e.g. shared) is done
        if any(p.dist(vx, vy) < 1e-6 for (vx, vy, vn) in vias if vn == p.net):
            continue
        if any(q.th and q.ref == p.ref and q.num == p.num for q in by_ref[p.ref]):
            continue   # joined to the planes by its own plated holes
        sw = min(STUB_W, 2 * min(p.hw, p.hh))
        fx, fy = p.fp_xy
        if p.ref in EP_ARRAYS:   # perimeter pin on the exposed pad's net: stub onto the EP
            ep = max(by_ref[p.ref], key=lambda q: q.hw * q.hh)
            if ep.net == p.net:
                # straight in past the pad row first, then onto the nearest EP point
                if p.hh > p.hw:
                    mx, my = p.cx, p.cy + math.copysign(p.hh + 0.3, ep.cy - p.cy)
                else:
                    mx, my = p.cx + math.copysign(p.hw + 0.3, ep.cx - p.cx), p.cy
                ex = min(max(mx, ep.cx - ep.hw + 0.05), ep.cx + ep.hw - 0.05)
                ey = min(max(my, ep.cy - ep.hh + 0.05), ep.cy + ep.hh - 0.05)
                others = [q for q in pads if q is not ep]
                def via_clear(x0_, y0_, x1_, y1_):
                    return not any(_pt_seg(ox, oy, x0_, y0_, x1_, y1_) < VIA_D / 2 + sw / 2 + CLR
                                   for (ox, oy, on) in vias if on != p.net)
                if (_seg_ok(p.cx, p.cy, mx, my, others, p, p.net, sw / 2)
                        and _seg_ok(mx, my, ex, ey, others, p, p.net, sw / 2)
                        and via_clear(p.cx, p.cy, mx, my) and via_clear(mx, my, ex, ey)):
                    segs.append((p.cx, p.cy, mx, my, p.net, sw))
                    segs.append((mx, my, ex, ey, p.net, sw))
                    continue
        base = math.atan2(p.cy - fy, p.cx - fx) if (abs(p.cx - fx) + abs(p.cy - fy)) > 1e-3 else 0.0
        if min(p.hw, p.hh) <= 0.15:   # fine-pitch pin: straight out along its own axis, not radially
            if p.hh > p.hw:
                base = math.pi / 2 if p.cy > fy else -math.pi / 2
            else:
                base = 0.0 if p.cx > fx else math.pi
        done = False
        for dang in (0, 45, -45, 90, -90, 135, -135, 180, 22.5, -22.5, 67.5, -67.5):
            a = base + math.radians(dang)
            ux, uy = math.cos(a), math.sin(a)
            # distance from pad centre to its edge along (ux, uy)
            edge = min(p.hw / abs(ux) if abs(ux) > 1e-9 else 1e9, p.hh / abs(uy) if abs(uy) > 1e-9 else 1e9)
            # RP2354B pins 24/29 (IOVDD) frame four 0.4 mm-pitch signal pins (CA13, CA14, PA10, PA11):
            # with their vias at the lane ends the four escapes have 1.4 mm between the vias and
            # need 1.55, so those two vias go ~3 mm out (the east side is kept free for it)
            far = (p.ref, p.num) in FAR_VIA
            for extra in ([2.4 + 0.1 * k for k in range(0, 6)] if far else []) + [0.1 * k for k in range(0, 26)]:
                dd = edge + VIA_D / 2 + 0.15 + extra
                vx, vy = round(p.cx + ux * dd, 3), round(p.cy + uy * dd, 3)
                if not via_ok(vx, vy, p.net, own=p):
                    continue
                if not _seg_ok(p.cx, p.cy, vx, vy, pads, p, p.net, sw / 2):
                    continue
                if any(_pt_seg(ox, oy, p.cx, p.cy, vx, vy) < VIA_D / 2 + sw / 2 + CLR
                       for (ox, oy, on) in vias if on != p.net):
                    continue
                vias.append((vx, vy, p.net))
                segs.append((p.cx, p.cy, vx, vy, p.net, sw))
                done = True
                break
            if done:
                break
        if not done:   # fall back to a straight stub onto a nearby same-net pad of another part
            for q in sorted((q for q in pads if q.net == p.net and q.ref != p.ref and not q.th
                             and 'F.Cu' in q.layers), key=lambda q: math.hypot(q.cx - p.cx, q.cy - p.cy)):
                if math.hypot(q.cx - p.cx, q.cy - p.cy) > 4.0:
                    break
                if _seg_ok(p.cx, p.cy, q.cx, q.cy, pads, p, p.net, sw / 2) and not any(
                        _pt_seg(ox, oy, p.cx, p.cy, q.cx, q.cy) < VIA_D / 2 + sw / 2 + CLR
                        for (ox, oy, on) in vias if on != p.net):
                    segs.append((p.cx, p.cy, q.cx, q.cy, p.net, sw))
                    done = True
                    break
        if not done:
            failed.append('%s.%s' % (p.ref, p.num))
    return vias[n_vias0:], segs[n_segs0:], failed


def _pt_seg(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L))
    return math.hypot(px - (x0 + t * dx), py - (y0 + t * dy))
