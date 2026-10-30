"""Draft drawing: every unit of a sheet placed on a grid, every pin on a short stub with its net's
label (a local label for a net that stays on the sheet, a hierarchical label for one that leaves
it, a power symbol for a rail, a no-connect flag for an NC pin), and a root whose blocks carry
exactly the hierarchical labels.  Electrically it is the final schematic -- same sheets, same
units on each sheet, same local / hierarchical split, same root labels -- so the net names KiCad
gives it (/cart-bus/A0, /USB_DP, GND) are the ones the hand-drawn sheets keep (gen_sch checks
nets.lock).  The board can be built and routed from it while sch_layout.py's drawing is made.
"""
import design as D
from sch_draw import Sheet, Pt, snap, units_of, lib_pins, lib_body, xform

STUB = 2.54


def _label_w(net):
    return 0.9 * 1.27 * len(net) + 4.0


def unit_box(sh, p, u):
    """Extent of a unit at the origin, rotation 0, pin stubs and labels included."""
    sym = sh.syms[p.lib_id]
    bx0, by0, bx1, by1 = lib_body(sym, u)
    x0, x1, y0, y1 = bx0, bx1, -by1, -by0
    f = xform(0, None)
    for (uu, num, px, py, ang) in lib_pins(sym):
        if uu not in (0, u):
            continue
        ox, oy = f(px, py)
        net = p.pins.get(num) or ''
        w = STUB + _label_w(net)
        x0, x1 = min(x0, ox - (w if ang == 0 else 0)), max(x1, ox + (w if ang == 180 else 0))
        y0, y1 = min(y0, oy - (w if ang == 270 else 0) - 1), max(y1, oy + (w if ang == 90 else 0) + 1)
    return x0, y0, x1, y1


def draft(sh, cross):
    """Place and label every unit of this sheet's parts.  cross: nets that leave the sheet."""
    W, H = sh.size
    x, y, row_h = 20.0, 20.0, 0.0
    for ref in sorted(sh.parts, key=lambda r: (D.BY_REF[r].prefix != 'U', D.BY_REF[r].prefix, int(r[len(D.BY_REF[r].prefix):]))):
        p = sh.parts[ref]
        for u in units_of(sh.syms[p.lib_id]):
            if p.unit_sheets and p.unit_sheets.get(u, p.sheet) != sh.stem:
                continue
            x0, y0, x1, y1 = unit_box(sh, p, u)
            if x + (x1 - x0) > W - 20:
                x, y, row_h = 20.0, y + row_h + 5.08, 0.0
            sh.place(ref, snap(x - x0), snap(y - y0), unit=u, fields='above')
            x += (x1 - x0) + 7.62
            row_h = max(row_h, y1 - y0)
    where = D.sheet_nets()
    flag = {n for n in D.PWR_FLAG_NETS if n in where and min(where[n], key=D.SHEET_ORDER.index) == sh.stem}
    for (ref, u), d in sh.placed.items():
        for num, pin in d['pins'].items():
            net = d['part'].pins.get(num)
            if net is None:
                sh.nc(pin)
                continue
            e = sh.stub(pin, STUB)
            if net in flag:              # PWR_FLAG once per passive-driven net, on its first sheet
                flag.discard(net)
                sh.flag(e, net)
            dirn = {(-1, 0): 'L', (1, 0): 'R', (0, -1): 'U', (0, 1): 'D'}[(pin.dx, pin.dy)]
            if net in D.RAIL_NETS:
                rot = {'U': 0, 'L': 90, 'D': 180, 'R': 270}[dirn] if net != 'GND' else \
                      {'D': 0, 'R': 90, 'U': 180, 'L': 270}[dirn]
                sh.rail(e, net, rot)
            elif net in cross:
                sh.hlabel(e, net, dirn, 'bidirectional')
            else:
                sh.label(e, net, dirn)
    sh.lint = False          # a draft: connectivity is checked, the geometry is not
    return sh


def draft_root(syms, sheets):
    """Root: one block per sheet in a row, its pins the sheet's hierarchical labels; each net
    runs in its own channel under the blocks, every pin dropping into it (KiCad names the net
    by the channel's local label: /NET)."""
    sh = Sheet('root', syms, [], 'A3')
    x, drops = 30.48, {}
    nets = []
    for stem, title, page in D.SHEETS:
        hier = sorted({l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'})
        h = max(25.4, snap(5.08 + 2.54 * len(hier) + 5.08))
        pins = sh.block(stem, x, 50.8, 50.8, h, right=[(n, 'bidirectional') for n in hier])
        for i, n in enumerate(hier):
            drops.setdefault(n, []).append((pins[n], snap(x + 50.8 + 2.54 * (len(hier) - i))))
            if n not in nets:
                nets.append(n)
        x += 76.2
    for k, n in enumerate(nets):
        y = 50.8 + 45.72 + 5.08 * k
        xs = []
        for pt, dx in drops[n]:
            sh.wire(pt, (dx, pt[1]), (dx, y))
            xs.append(dx)
        sh.wire((min(xs), y), (max(xs), y))
        for dx in xs[1:-1]:
            pass                     # interior drops end on the channel's run: a T, joined by check()
        sh.label((min(xs) + 1.27, y), n)
    sh.lint = False
    return sh
