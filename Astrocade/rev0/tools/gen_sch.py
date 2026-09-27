#!/usr/bin/env python3
"""Generate the schematic (root + 4 sheets) from design.py.

Style: every symbol stands alone and every connected pin carries a global
label with its net name (the same convention the INTV Rev0 sheets use);
unconnected pins get no-connect flags.  Symbols come from tools/symcache.sexpr
(stock KiCad symbols as flattened by eeschema) plus the project library,
which this script also (re)writes: FujiNet-Astrocade.kicad_sym.

Usage: python3 tools/gen_sch.py      (writes into the project directory)
"""
import os, sys, uuid, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
DATE = '2026-09-26'
NS = uuid.UUID('6f1c9a1e-3a52-4d7e-9b7d-0a57a0cade00')


def uid(*k):
    return Q(str(uuid.uuid5(NS, '/'.join(map(str, k)))))


def font(size=1.27):
    return ['effects', ['font', ['size', size, size]]]


def hidden():
    return ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]


# ---------------------------------------------------------------------------
# project-library symbols
def box_symbol(name, ref, value, footprint, desc, left, right=(), bottom=(), top=(), w=15.24):
    """left/right/bottom/top: lists of (number, name, etype).  2.54 pitch."""
    n = max(len(left), len(right), 1)
    h = (n + 1) * 2.54
    y0 = (n - 1) * 2.54 / 2
    y0 = round(y0 / 1.27) * 1.27
    top_y = y0 + 2.54
    bot_y = top_y - h
    bot_y = round(bot_y / 1.27) * 1.27
    half = w / 2
    body = ['symbol', Q(name + '_0_1'),
            ['rectangle', ['start', -half, top_y], ['end', half, bot_y],
             ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]]
    pins = ['symbol', Q(name + '_1_1')]

    def pin(num, nm, et, x, y, ang):
        pins.append(['pin', et, 'line', ['at', x, y, ang], ['length', 2.54],
                     ['name', Q(nm), font()], ['number', Q(str(num)), font()]])
    for i, (num, nm, et) in enumerate(left):
        pin(num, nm, et, -half - 2.54, y0 - i * 2.54, 0)
    for i, (num, nm, et) in enumerate(right):
        pin(num, nm, et, half + 2.54, y0 - i * 2.54, 180)
    for i, (num, nm, et) in enumerate(bottom):
        x = -((len(bottom) - 1) * 2.54) / 2 + i * 2.54
        pin(num, nm, et, round(x / 1.27) * 1.27, bot_y - 2.54, 90)
    for i, (num, nm, et) in enumerate(top):
        x = -((len(top) - 1) * 2.54) / 2 + i * 2.54
        pin(num, nm, et, round(x / 1.27) * 1.27, top_y + 2.54, 270)
    return ['symbol', Q(name), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
            ['in_bom', 'yes'], ['on_board', 'yes'],
            ['property', Q('Reference'), Q(ref), ['at', 0, top_y + 1.27, 0], font()],
            ['property', Q('Value'), Q(value), ['at', 0, bot_y - 5.08, 0], font()],
            ['property', Q('Footprint'), Q(footprint), ['at', 0, 0, 0], hidden()],
            ['property', Q('Datasheet'), Q(''), ['at', 0, 0, 0], hidden()],
            ['property', Q('Description'), Q(desc), ['at', 0, 0, 0], hidden()],
            body, pins]


def project_symbols():
    old = parse(open(os.path.join(HERE, 'symcache.sexpr')).read())
    edge = copy.deepcopy([s for s in old[1:] if s[1] == 'FujiNet-Astrocade:Astrocade_Cart_Edge_26'][0])
    edge[1] = Q('Astrocade_Cart_Edge_26')
    for s in findall(edge, 'symbol'):
        s[1] = Q(s[1].replace('FujiNet-Astrocade:', ''))
    sd = box_symbol('MicroSD_TF015', 'J', 'microSD', D.FP('TF-SMD_TF-015'),
                    'microSD push-push socket, SOFNG TF-015 (LCSC C113206)',
                    left=[(1, 'DAT2', 'bidirectional'), (2, 'DAT3/CS', 'bidirectional'),
                          (3, 'CMD/DI', 'input'), (4, 'VDD', 'power_in'), (5, 'CLK', 'input'),
                          (6, 'VSS', 'power_in'), (7, 'DAT0/DO', 'bidirectional'),
                          (8, 'DAT1', 'bidirectional'), (9, 'CD', 'passive')],
                    bottom=[(10, 'SH', 'passive'), (11, 'SH', 'passive'),
                            (12, 'SH', 'passive'), (13, 'SH', 'passive')], w=17.78)
    lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('fujinet_gen')],
           ['generator_version', Q('1.0')], edge, sd]
    open(os.path.join(PRJ, D.LIB + '.kicad_sym'), 'w').write(dump(lib) + '\n')
    cache = {}
    for s in (edge, sd):
        c = copy.deepcopy(s)
        c[1] = Q(D.LIB + ':' + s[1])
        cache[c[1]] = c
    return cache


# ---------------------------------------------------------------------------
def load_symbols():
    t = parse(open(os.path.join(HERE, 'symcache.sexpr')).read())
    syms = {s[1]: s for s in t[1:]}
    syms.update(project_symbols())
    return syms


def sym_pins(sym):
    """[(unit, number, x, y, angle)] in library coordinates (y up)."""
    out = []
    for sub in findall(sym, 'symbol'):
        unit = int(sub[1].rsplit('_', 2)[-2])
        for p in findall(sub, 'pin'):
            at = find(p, 'at')
            out.append((unit, str(find(p, 'number')[1]), float(at[1]), float(at[2]), int(float(at[3]))))
    return out


def sym_bbox(sym, unit):
    xs, ys = [], []

    def walk(e):
        for x in e:
            if isinstance(x, list) and x:
                if x[0] in ('xy', 'start', 'end', 'center', 'mid') and len(x) >= 3:
                    xs.append(float(x[1])); ys.append(float(x[2]))
                elif x[0] == 'pin':
                    at = find(x, 'at'); ln = float(find(x, 'length')[1])
                    xs.append(float(at[1])); ys.append(float(at[2]))
                elif x[0] != 'property':
                    walk(x)
    for sub in findall(sym, 'symbol'):
        u = int(sub[1].rsplit('_', 2)[-2])
        if u in (0, unit):
            walk(sub)
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))


def units_of(sym):
    us = sorted({u for u, *_ in sym_pins(sym) if u})
    return us or [1]


def side_fields(sym, unit):
    """Small parts whose pins all point up/down: put Reference/Value beside the body."""
    angs = {a for (u, n, x, y, a) in sym_pins(sym) if u in (0, unit)}
    return len(sym_pins(sym)) <= 3 and angs <= {90, 270}


def label_len(text):
    return 1.0 * len(text) + 3.0


# ---------------------------------------------------------------------------
def build_sheet(stem, title, page, parts, syms, root_uuid, sheet_uuid, flags=()):
    items = []
    used = {}
    # instances to place: (part, unit)
    places = []
    for p in parts:
        sym = syms[p.lib_id]
        for u in units_of(sym):
            places.append((p, u))
    for i, n in enumerate(flags):
        places.append((('FLAG', i, n), 1))

    # footprint of each placement incl. labels (sheet coords relative to origin)
    def extent(p, u):
        if isinstance(p, tuple):
            sym = syms['power:PWR_FLAG']
            pins = {'1': p[2]}
        else:
            sym = syms[p.lib_id]
            pins = p.pins
        x0, y0, x1, y1 = sym_bbox(sym, u)
        # sheet coords: flip y
        L, T, Rr, B = x0, -y1, x1, -y0
        for (uu, num, px, py, ang) in sym_pins(sym):
            if uu not in (0, u):
                continue
            net = pins.get(num)
            ll = label_len(net) if net else 1.5
            sx, sy = px, -py
            if ang == 0:
                L = min(L, sx - ll)
            elif ang == 180:
                Rr = max(Rr, sx + ll)
            elif ang == 90:
                B = max(B, sy + ll)
            else:
                T = min(T, sy - ll)
        if side_fields(sym, u):
            ref = 'X' if isinstance(p, tuple) else p.ref
            val = 'PWR_FLAG' if isinstance(p, tuple) else p.value
            Rr = max(Rr, x1 + 2.0 + 1.0 * max(len(ref), len(val)))
            return L - 2.54, T - 1.27, Rr + 2.54, B + 2.54
        return L - 2.54, T - 5.08, Rr + 2.54, B + 2.54

    paper, (PW, PH) = ('A3', (420, 297))
    if len(places) > 60:
        paper, (PW, PH) = ('A2', (594, 420))
    margin, x, y, shelf = 15.0, 15.0, 30.0, 0.0
    pos = []
    big = sorted(places, key=lambda pu: 0 if isinstance(pu[0], tuple) else -len(pu[0].pins))
    # biggest first, then keep declaration order for the small ones
    order = [pu for pu in big if not isinstance(pu[0], tuple) and len(pu[0].pins) > 8] + \
            [pu for pu in places if isinstance(pu[0], tuple) or len(pu[0].pins) <= 8]
    for p, u in order:
        L, T, Rr, B = extent(p, u)
        w, h = Rr - L, B - T
        if x + w > PW - margin:
            x = margin; y += shelf; shelf = 0.0
        ox = round((x - L) / 2.54) * 2.54
        oy = round((y - T) / 2.54) * 2.54
        pos.append((p, u, ox, oy))
        x += w + 2.54
        shelf = max(shelf, h + 2.54)
    if y + shelf > PH - 40:
        raise SystemExit('%s: does not fit on %s (y=%.1f)' % (stem, paper, y + shelf))

    path = '/%s/%s' % (root_uuid, sheet_uuid)
    for p, u, ox, oy in pos:
        if isinstance(p, tuple):
            ref, lib_id, value, fp, pins, fields, bom = '#FLG%02d' % (p[1] + 1), 'power:PWR_FLAG', 'PWR_FLAG', '', {'1': p[2]}, {}, False
            key = ('flag', p[2])
        else:
            ref, lib_id, value, fp, pins, bom = p.ref, p.lib_id, p.value, p.footprint, p.pins, p.bom
            fields = {'MPN': p.mpn, 'LCSC': p.lcsc}
            key = (p.ref, u)
        sym = syms[lib_id]
        used[lib_id] = sym
        x0, y0, x1, y1 = sym_bbox(sym, u)
        ds = ''
        for pr in findall(sym, 'property'):
            if pr[1] == 'Datasheet':
                ds = pr[2]
        desc = '' if isinstance(p, tuple) else p.desc
        if side_fields(sym, u):
            fx = ox + x1 + 1.27
            fpos = [[['at', fx, oy - 1.27, 0], ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left']]],
                    [['at', fx, oy + 1.27, 0], ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left']]]]
        else:
            top = oy - y1
            for (uu, num, px, py, ang) in sym_pins(sym):
                if uu in (0, u) and ang == 270 and pins.get(num):
                    top = min(top, oy - py - label_len(pins[num]))
            fpos = [[['at', ox, top - 3.81, 0], font()], [['at', ox, top - 1.27, 0], font()]]
        e = ['symbol', ['lib_id', Q(lib_id)], ['at', ox, oy, 0], ['unit', u],
             ['exclude_from_sim', 'no'], ['in_bom', 'yes' if bom else 'no'],
             ['on_board', 'no' if isinstance(p, tuple) else 'yes'], ['dnp', 'no'],
             ['uuid', uid(stem, *key)],
             ['property', Q('Reference'), Q(ref)] + fpos[0],
             ['property', Q('Value'), Q(value)] + fpos[1],
             ['property', Q('Footprint'), Q(fp), ['at', ox, oy, 0], hidden()],
             ['property', Q('Datasheet'), Q(ds), ['at', ox, oy, 0], hidden()],
             ['property', Q('Description'), Q(desc), ['at', ox, oy, 0], hidden()]]
        for k, v in fields.items():
            if v:
                e.append(['property', Q(k), Q(v), ['at', ox, oy, 0], hidden()])
        allpins = sym_pins(sym)
        for (uu, num, px, py, ang) in allpins:
            if uu in (0, u):
                e.append(['pin', Q(num), ['uuid', uid(stem, *key, 'pin', num)]])
        e.append(['instances', ['project', Q(D.PROJECT),
                                ['path', Q(path), ['reference', Q(ref)], ['unit', u]]]])
        items.append(e)
        # labels / no-connects, one per distinct pin position
        seen = {}
        for (uu, num, px, py, ang) in allpins:
            if uu not in (0, u):
                continue
            sx, sy = round(ox + px, 2), round(oy - py, 2)
            net = pins.get(num)
            if num not in pins and not isinstance(p, tuple):
                raise SystemExit('%s pin %s not assigned in design.py' % (ref, num))
            if (sx, sy) in seen:
                if seen[(sx, sy)] != net:
                    raise SystemExit('%s: stacked pins with different nets at %s' % (ref, (sx, sy)))
                continue
            seen[(sx, sy)] = net
            if net is None:
                items.append(['no_connect', ['at', sx, sy], ['uuid', uid(stem, *key, 'nc', num)]])
            else:
                just = {0: 'right', 180: 'left', 90: 'right', 270: 'left'}[ang]
                items.append(['global_label', Q(net), ['shape', 'passive'], ['at', sx, sy, ang],
                              ['fields_autoplaced', 'yes'],
                              ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just]],
                              ['uuid', uid(stem, *key, 'lbl', num)]])
    # every lib symbol that the sheet references
    lib_symbols = ['lib_symbols'] + [used[k] for k in sorted(used)]
    tb = ['title_block', ['title', Q('FujiNet Astrocade Rev0 - ' + title)], ['date', Q(DATE)],
          ['rev', Q('0')], ['company', Q('FujiNet')],
          ['comment', 1, Q('Generated by tools/gen_sch.py from tools/design.py - edit design.py, not this file')],
          ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-INTV-Rev0 / PiNTY CARD)')]]
    return ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
            ['generator_version', Q('9.0')], ['uuid', Q(sheet_uuid)], ['paper', Q(paper)], tb,
            lib_symbols] + items + [['embedded_fonts', 'no']]


NOTES = """FujiNet for the Bally Astrocade - Rev0 (RP2354A)

RP2354A serves the 8K cart window (A0-A12 GP0-12, /CCS GP13, D0-D7 GP14-21) straight off the
5V bus through its 5V-tolerant pads (IOVDD must be up - it is: the cart is powered by the console).
ESP32-S3-WROOM-1-N16R8 runs FujiNet (fujiversal-astrocade) and is the USB host of the RP (CDC, VID 0xCafe);
S3 IO4/IO5 force RP RUN/QSPI_SS so the S3 can re-flash the RP over PICOBOOT.
USB-C: power + CP2102N UART bridge for flashing the S3.  microSD on S3 SPI.
Power: console +5V (edge 25) and USB VBUS diode-OR -> AP63203 3.3V buck.
Contact lands are on the PCB UNDERSIDE (the console blade presses up on them)."""


def main():
    syms = load_symbols()
    root_uuid = str(uid('root'))
    sheet_uuids = {s[0]: str(uid('sheet', s[0])) for s in D.SHEETS}
    for stem, title, page in D.SHEETS:
        parts = [p for p in D.PARTS if p.sheet == stem]
        flags = D.PWR_FLAG_NETS if stem == 'power' else ()
        sch = build_sheet(stem, title, page, parts, syms, root_uuid, sheet_uuids[stem], flags)
        open(os.path.join(PRJ, stem + '.kicad_sch'), 'w').write(dump(sch) + '\n')
    root = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
            ['generator_version', Q('9.0')], ['uuid', Q(root_uuid)], ['paper', Q('A3')],
            ['title_block', ['title', Q('FujiNet Astrocade Rev0')], ['date', Q(DATE)], ['rev', Q('0')],
             ['company', Q('FujiNet')], ['comment', 1, Q('Generated by tools/gen_sch.py')]],
            ['lib_symbols']]
    for i, (stem, title, page) in enumerate(D.SHEETS):
        x, y = 30 + i * 90, 40
        root.append(['sheet', ['at', x, y], ['size', 63.5, 25.4], ['fields_autoplaced', 'yes'],
                     ['stroke', ['width', 0.12], ['type', 'solid']], ['fill', ['color', 0, 0, 0, 0.0]],
                     ['uuid', Q(sheet_uuids[stem])],
                     ['property', Q('Sheetname'), Q(stem), ['at', x, y - 1, 0],
                      ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'bottom']]],
                     ['property', Q('Sheetfile'), Q(stem + '.kicad_sch'), ['at', x, y + 26.4, 0],
                      ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]],
                     ['instances', ['project', Q(D.PROJECT), ['path', Q('/' + root_uuid), ['page', Q(str(page))]]]]])
        root.append(['text', Q(title), ['exclude_from_sim', 'no'], ['at', x, y + 12.7, 0],
                     ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left']],
                     ['uuid', uid('roottext', stem)]])
    root.append(['text', Q(NOTES.replace('\n', '\\n')), ['exclude_from_sim', 'no'], ['at', 30, 90, 0],
                 ['effects', ['font', ['size', 2, 2]], ['justify', 'left', 'top']], ['uuid', uid('notes')]])
    root.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
    root.append(['embedded_fonts', 'no'])
    open(os.path.join(PRJ, D.PROJECT + '.kicad_sch'), 'w').write(dump(root) + '\n')
    print('schematic written')


if __name__ == '__main__':
    main()
