#!/usr/bin/env python3
"""Generate the FujiNet-7800 Rev0 schematic (root + 7 sheets) from design.py.

design.py says what connects to what; sch_layout.py says how each sheet is
drawn: parts placed left to right in signal-flow order and joined by wires,
the address / data buses as KiCad buses, rails as power symbols, and
hierarchical labels where a net leaves a sheet, wired on the root's block
diagram (sch_draw.py has the conventions).  Each sheet is connectivity-checked
as it is drawn (sch_draw.Sheet.check), the hierarchy against design.py
(check_hierarchy: every net that crosses sheets leaves each of its sheets on
a hierarchical label and every label has its sheet pin), and the written
schematic once more through kicad-cli's netlist against design.py, net by
net, names included (the last element of KiCad's /sheet/NET path).  Symbols come from
tools/symcache.sexpr (stock KiCad symbols as flattened by eeschema, see
harvest_symbols.py) plus the project library, which this script also
(re)writes: FujiNet-7800.kicad_sym.  The sheet list in the .kicad_pro is kept
in step.

Usage: python3 tools/gen_sch.py      (writes into the project directory)
"""
import os, sys, uuid, copy, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q
import design as D
import sch_draw

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
DATE = '2026-10-07'
COMMENT3 = 'Rev0 audit 2026-10-07: kicad-happy + datasheets, see docs/design-review-rev0.md'
NS = uuid.UUID('3c0b5e2a-9d41-4f6a-8c1e-5a6d2f7b9e10')


def uid(*k):
    return Q(str(uuid.uuid5(NS, '/'.join(map(str, k)))))


def font(size=1.27):
    return ['effects', ['font', ['size', size, size]]]


def hidden():
    return ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]


# ---------------------------------------------------------------------------
# project-library symbols
def box_symbol(name, ref, value, footprint, desc, left, right=(), bottom=(), top=(), w=15.24, tb_x=0, ds=''):
    """left/right/bottom/top: lists of (number, name, etype); None in left/right
    leaves a one-pin gap between groups.  2.54 pitch, every pin end on the 2.54 grid
    (w a multiple of 5.08)."""
    n = max(len(left), len(right), 1)
    y0 = ((n - 1) // 2) * 2.54
    top_y = y0 + 2.54
    bot_y = y0 - n * 2.54
    half = w / 2
    body = ['symbol', Q(name + '_0_1'),
            ['rectangle', ['start', -half, top_y], ['end', half, bot_y],
             ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]]
    pins = ['symbol', Q(name + '_1_1')]

    def pin(num, nm, et, x, y, ang, shape='line'):
        pins.append(['pin', et, shape, ['at', x, y, ang], ['length', 2.54],
                     ['name', Q(nm), font()], ['number', Q(str(num)), font()]])
    for i, e in enumerate(left):
        if e:
            pin(*e[:3], -half - 2.54, y0 - i * 2.54, 0, *e[3:])
    for i, e in enumerate(right):
        if e:
            pin(*e[:3], half + 2.54, y0 - i * 2.54, 180, *e[3:])
    for i, (num, nm, et, *sh) in enumerate(bottom):
        x = tb_x - ((len(bottom) - 1) // 2) * 2.54 + i * 2.54
        pin(num, nm, et, x, bot_y - 2.54, 90)
    for i, (num, nm, et, *sh) in enumerate(top):
        x = tb_x - ((len(top) - 1) // 2) * 2.54 + i * 2.54
        pin(num, nm, et, x, top_y + 2.54, 270)
    return ['symbol', Q(name), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
            ['in_bom', 'yes'], ['on_board', 'yes'],
            ['property', Q('Reference'), Q(ref), ['at', 0, top_y + 1.27, 0], font()],
            ['property', Q('Value'), Q(value), ['at', 0, bot_y - 5.08, 0], font()],
            ['property', Q('Footprint'), Q(footprint), ['at', 0, 0, 0], hidden()],
            ['property', Q('Datasheet'), Q(ds), ['at', 0, 0, 0], hidden()],
            ['property', Q('Description'), Q(desc), ['at', 0, 0, 0], hidden()],
            body, pins]


# The edge drawn by function, not by finger: every console signal on the
# right (toward the cart), grouped address / data / control and audio.
# The control lines one pin apart, so each carries its own circuit or bring-up pad.
EDGE_GROUPS = [['A%d' % i for i in range(16)], ['D%d' % i for i in range(8)],
               ['RW', None, 'PHI2', None, 'HALT_N', None, 'IRQ_N', None, 'EAUDIO']]


def edge_symbol():
    by_net = {}
    for p, (net, nm) in D.EDGE.items():
        by_net.setdefault(net, []).append(p)
    right = []
    for g in EDGE_GROUPS:
        if right:
            right.append(None)
        right += [(by_net[n][0], D.EDGE[by_net[n][0]][1], 'passive') if n else None for n in g]
    top = [(p, '+5V', 'passive') for p in by_net['CONS_5V']]
    bottom = [(p, 'GND', 'passive') for p in by_net['GND']]
    assert len([e for e in right if e]) + len(top) + len(bottom) == 32
    return box_symbol('Atari7800_Cart_Edge_32', 'J', 'Atari7800_Cart_Edge_32', D.FP('Atari7800_Cart_Edge_32'),
                      'Atari 7800 32-pin cartridge edge: 18 positions at 2.54 mm per face, key slots at 3 and 16; '
                      'pins 1-16 on the component side (console rear), 17-32 behind, pin k over pin 33-k; '
                      'pins 3-14 / 19-30 are the 2600 edge',
                      left=[], right=right, top=top, bottom=bottom, w=20.32, tb_x=-5.08)


def project_symbols():
    edge = edge_symbol()
    sp = D.SRAM_PIN
    sram = box_symbol('AS6C4008-55TIN', 'U', 'AS6C4008-55TIN', D.FP('TSOP-I-32_18.4x8mm_P0.5mm'),
                      '512K x 8 low power CMOS SRAM, 55 ns, 2.7-5.5 V, TSOP-I-32 (Alliance pin order)',
                      left=[(sp['A%d' % i], 'A%d' % i, 'input') for i in range(19)] + [None] +
                           [(sp['CE#'], '~{CE}', 'input'), (sp['OE#'], '~{OE}', 'input'),
                            (sp['WE#'], '~{WE}', 'input')],
                      right=[(sp['DQ%d' % i], 'DQ%d' % i, 'bidirectional') for i in range(8)],
                      top=[(sp['VCC'], 'VCC', 'power_in')], bottom=[(sp['VSS'], 'VSS', 'power_in')],
                      w=20.32)
    # microSD drawn in the S3's SPI pin order, signals 5.08 apart (room for their names)
    sd = box_symbol('MicroSD_TF015', 'J', 'microSD', D.FP('TF-SMD_TF-015'),
                    'microSD push-push socket, SOFNG TF-015 (LCSC C113206)',
                    left=[(8, 'DAT1', 'bidirectional'), None, (1, 'DAT2', 'bidirectional'), None,
                          (3, 'CMD/DI', 'input'), None, (5, 'CLK', 'input'), None,
                          (7, 'DAT0/DO', 'bidirectional'), None, (2, 'DAT3/CS', 'bidirectional'), None,
                          (9, 'CD', 'passive'), None, (4, 'VDD', 'power_in'), (6, 'VSS', 'power_in')],
                    bottom=[(10, 'SH', 'passive'), (11, 'SH', 'passive'),
                            (12, 'SH', 'passive'), (13, 'SH', 'passive')], w=20.32)
    lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('fujinet_gen')],
           ['generator_version', Q('1.0')], edge, sram, sd]
    open(os.path.join(PRJ, D.LIB + '.kicad_sym'), 'w').write(dump(lib) + '\n')
    cache = {}
    for s in (edge, sram, sd):
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


def pin_names(sym):
    """pin number -> name."""
    out = {}
    for sub in findall(sym, 'symbol'):
        for p in findall(sub, 'pin'):
            out[str(find(p, 'number')[1])] = str(find(p, 'name')[1])
    return out


units_of = sch_draw.units_of


def verify_pin_tables(syms):
    """design.py's hand-written pin numbers against the symbols they index."""
    names = pin_names(syms['MCU_RaspberryPi:RP2354B'])
    for g, pin in D.RP_GPIO_PIN.items():
        nm = names.get(str(pin), '')
        if not re.match(r'GPIO%d(/|$)' % g, nm):
            raise SystemExit('RP_GPIO_PIN: GPIO%d -> pin %d, but the symbol calls that pin %r' % (g, pin, nm))
    for pin in D.RP_IOVDD_PINS:
        if names.get(str(pin)) != 'IOVDD':
            raise SystemExit('RP_IOVDD_PINS: pin %d is %r' % (pin, names.get(str(pin))))
    for pin in D.RP_DVDD_PINS:
        if names.get(str(pin)) != 'DVDD':
            raise SystemExit('RP_DVDD_PINS: pin %d is %r' % (pin, names.get(str(pin))))
    names = pin_names(syms['RF_Module:ESP32-S3-WROOM-1'])
    for fn, pad in D.S3_PAD.items():
        for p in (pad if isinstance(pad, list) else [pad]):
            nm = names[str(p)]
            if nm != fn and not (fn == 'IO19' and nm == 'USB_D-') and not (fn == 'IO20' and nm == 'USB_D+'):
                raise SystemExit('S3_PAD: %s -> pad %d, but the symbol calls it %r' % (fn, p, nm))


# ---------------------------------------------------------------------------
def field(name, value, pos, rot, hide=False, mirror=None):
    """A property at an absolute position; text kept horizontal on rotated symbols.
    pos's justification is as seen on the sheet; eeschema applies the symbol's
    own flip to it, so a 90/180-degree or y-mirrored symbol gets it swapped."""
    x, y, j = pos
    if j and ((rot in (90, 180)) != (mirror == 'y')):
        j = {'left': 'right', 'right': 'left'}[j]
    eff = ['effects', ['font', ['size', 1.27, 1.27]]]
    if j:
        eff.append(['justify', j])
    if hide:
        eff.append(['hide', 'yes'])
    return ['property', Q(name), Q(value), ['at', x, y, 90 if rot in (90, 270) else 0], eff]


def serialize(sh, title, root_uuid, sheet_uuid, pwr):
    """sch_draw.Sheet -> kicad_sch tree.  pwr: running #PWR / #FLG counter (dict)."""
    stem = sh.stem
    path = '/%s/%s' % (root_uuid, sheet_uuid)
    items, used = [], {}

    def inst(lib_id, x, y, rot, mirror, unit, ref, uu, fields, pins, bom=True, board=True, dnp=False):
        sym = sh.syms[lib_id]
        used[lib_id] = sym
        e = ['symbol', ['lib_id', Q(lib_id)], ['at', x, y, rot]]
        if mirror:
            e.append(['mirror', mirror])
        e += [['unit', unit], ['exclude_from_sim', 'no'], ['in_bom', 'yes' if bom else 'no'],
              ['on_board', 'yes' if board else 'no'], ['dnp', 'yes' if dnp else 'no'], ['uuid', uu]]
        e += fields
        for num in pins:
            e.append(['pin', Q(num), ['uuid', uid(stem, ref, unit, 'pin', num)]])
        e.append(['instances', ['project', Q(D.PROJECT), ['path', Q(path), ['reference', Q(ref)], ['unit', unit]]]])
        items.append(e)

    for (ref, u), d in sh.placed.items():
        p = d['part']
        sym = sh.syms[p.lib_id]
        ds = p.ds or next((pr[2] for pr in findall(sym, 'property') if pr[1] == 'Datasheet'), '')
        x, y, rot = d['x'], d['y'], d['rot']
        hid = (x, y, None)
        fl = [field('Reference', ref, d['fields'][0], rot, mirror=d['mirror']),
              field('Value', p.value, d['fields'][1], rot, mirror=d['mirror']),
              field('Footprint', p.footprint, hid, rot, True), field('Datasheet', ds, hid, rot, True),
              field('Description', p.desc, hid, rot, True)]
        for k, v in (('MPN', p.mpn), ('LCSC', p.lcsc)):
            if v:
                fl.append(field(k, v, hid, rot, True))
        pins = sorted({num for (uu, num, *_r) in sch_draw.lib_pins(sym) if uu in (0, u)})
        # symbol uuid: the same key as the shelf-placed sheets had (the board's paths follow it)
        inst(p.lib_id, x, y, rot, d['mirror'], u, ref, uid(stem, ref, u), fl, pins,
             bom=p.bom, dnp=p.dnp)
    for net, x, y, rot in sh.rails:
        lib = sch_draw.Sheet.RAILS[net]
        pwr['pwr'] += 1
        ref = '#PWR%03d' % pwr['pwr']
        ux, uy = (0, 1) if net == 'GND' else (0, -1)         # the symbol's tip direction...
        for _ in range(rot // 90):                         # ...turned with it (CCW on the sheet)
            ux, uy = uy, -ux
        w = 0.9 * 1.27 * len(net) / 2
        vx, vy = x + ux * (3.3 + w), y + uy * 3.81           # value beyond the tip
        inst(lib, x, y, rot, None, 1, ref, uid(stem, 'rail', net, x, y),
             [field('Reference', ref, (x, y + 6.35 if net == 'GND' else y - 6.35, None), rot, True),
              field('Value', net, (vx, vy, None), rot), field('Footprint', '', (x, y, None), 0, True),
              field('Datasheet', '', (x, y, None), 0, True), field('Description', '', (x, y, None), 0, True)],
             ['1'], bom=False, board=False)
    for net, x, y in sh.flags:
        pwr['flg'] += 1
        ref = '#FLG%02d' % pwr['flg']
        inst('power:PWR_FLAG', x, y, 0, None, 1, ref, uid(stem, 'flag', net),
             [field('Reference', ref, (x, y - 1.905, None), 0, True),
              field('Value', 'PWR_FLAG', (x, y - 3.81, None), 0), field('Footprint', '', (x, y, None), 0, True),
              field('Datasheet', '', (x, y, None), 0, True), field('Description', '', (x, y, None), 0, True)],
             ['1'], bom=False, board=False)
    st = ['stroke', ['width', 0], ['type', 'default']]
    for a, b in sh.wires:
        items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]], st, ['uuid', uid(stem, 'w', a, b)]])
    for a, b in sh.buses:
        items.append(['bus', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]], st, ['uuid', uid(stem, 'b', a, b)]])
    for (x, y), (dx, dy) in sh.entries:
        items.append(['bus_entry', ['at', x, y], ['size', dx, dy], st, ['uuid', uid(stem, 'e', x, y)]])
    for (x, y) in sh.junctions:
        items.append(['junction', ['at', x, y], ['diameter', 0], ['color', 0, 0, 0, 0], ['uuid', uid(stem, 'j', x, y)]])
    for (x, y) in sh.ncs:
        items.append(['no_connect', ['at', x, y], ['uuid', uid(stem, 'nc', x, y)]])
    for kind, net, x, y, ang, shape in sh.labels:
        just = 'left' if ang in (0, 90) else 'right'
        e = [kind, Q(net)]
        if kind != 'label':
            e.append(['shape', shape])
        e += [['at', x, y, ang]]
        if kind != 'label':
            e.append(['fields_autoplaced', 'yes'])
        e += [['effects', ['font', ['size', 1.27, 1.27]], ['justify', just] if kind != 'label'
               else ['justify', just, 'bottom']], ['uuid', uid(stem, kind, net, x, y)]]
        items.append(e)
    for s, x, y, size, j in sh.texts:
        items.append(['text', Q(s.replace('\n', '\\n')), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                      ['effects', ['font', ['size', size, size]], ['justify', j, 'top']], ['uuid', uid(stem, 'text', x, y)]])
    lib_symbols = ['lib_symbols'] + [used[k] for k in sorted(used)]
    tb = ['title_block', ['title', Q('FujiNet 7800 Rev0 - ' + title)], ['date', Q(DATE)],
          ['rev', Q('0')], ['company', Q('FujiNet')],
          ['comment', 1, Q('Generated from tools/design.py + tools/sch_layout.py - edit those, not this file')],
          ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-SMS-Rev0 / FujiNet-NES-Rev0 and their sources)')],
          ['comment', 3, Q(COMMENT3)]]
    return ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
            ['generator_version', Q('9.0')], ['uuid', Q(sheet_uuid)], ['paper', Q(sh.paper)], tb,
            lib_symbols] + items + [['embedded_fonts', 'no']]


def serialize_root(sh, root_uuid, sheet_uuids):
    """The root: the block diagram (sheet symbols with their pins, the wires and
    buses between them, net labels on every wire) and the notes."""
    items = []
    page = {s: pg for s, t, pg in D.SHEETS}
    title = {s: t for s, t, pg in D.SHEETS}
    st = ['stroke', ['width', 0], ['type', 'default']]
    for b in sh.blocks:
        stem, x, y, w, h = b['stem'], b['x'], b['y'], b['w'], b['h']
        e = ['sheet', ['at', x, y], ['size', w, h], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
             ['on_board', 'yes'], ['dnp', 'no'], ['fields_autoplaced', 'yes'],
             ['stroke', ['width', 0.1524], ['type', 'solid']], ['fill', ['color', 255, 255, 225, 1.0]],
             ['uuid', Q(sheet_uuids[stem])],
             ['property', Q('Sheetname'), Q(stem), ['at', x, round(y - 0.7, 3), 0],
              ['effects', ['font', ['size', 1.524, 1.524], 'bold'], ['justify', 'left', 'bottom']]],
             ['property', Q('Sheetfile'), Q(stem + '.kicad_sch'), ['at', x, round(y + h + 0.6, 3), 0],
              ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]]]
        for nm, pt in b['pins'].items():
            left = pt.dx < 0
            e.append(['pin', Q(nm), b['shapes'][nm], ['at', pt[0], pt[1], 180 if left else 0],
                      ['uuid', uid('rootpin', stem, nm)],
                      ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left' if left else 'right']]])
        e.append(['instances', ['project', Q(D.PROJECT), ['path', Q('/' + root_uuid), ['page', Q(str(page[stem]))]]]])
        items.append(e)
    for a, b in sh.wires:
        items.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]], st, ['uuid', uid('root', 'w', a, b)]])
    for a, b in sh.buses:
        items.append(['bus', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]], st, ['uuid', uid('root', 'b', a, b)]])
    for (x, y), (dx, dy) in sh.entries:
        items.append(['bus_entry', ['at', x, y], ['size', dx, dy], st, ['uuid', uid('root', 'e', x, y)]])
    for (x, y) in sh.junctions:
        items.append(['junction', ['at', x, y], ['diameter', 0], ['color', 0, 0, 0, 0], ['uuid', uid('root', 'j', x, y)]])
    for kind, net, x, y, ang, shape in sh.labels:
        assert kind == 'label', kind
        items.append(['label', Q(net), ['at', x, y, ang],
                      ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left' if ang in (0, 90) else 'right', 'bottom']],
                      ['uuid', uid('root', 'label', net, x, y)]])
    for s_, x, y, size, j in sh.texts:
        items.append(['text', Q(s_.replace('\n', '\\n')), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                      ['effects', ['font', ['size', size, size]], ['justify', j, 'top']], ['uuid', uid('root', 'text', x, y)]])
    tb = ['title_block', ['title', Q('FujiNet 7800 Rev0')], ['date', Q(DATE)], ['rev', Q('0')],
          ['company', Q('FujiNet')],
          ['comment', 1, Q('Generated from tools/design.py + tools/sch_layout.py - edit those, not this file')],
          ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-SMS-Rev0 / FujiNet-NES-Rev0 and their sources)')],
          ['comment', 3, Q(COMMENT3)]]
    return ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
            ['generator_version', Q('9.0')], ['uuid', Q(root_uuid)], ['paper', Q(sh.paper)], tb,
            ['lib_symbols']] + items + [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]],
                                        ['embedded_fonts', 'no']]


def bus_members(name):
    """'A[0..15]' -> ['A0', ..., 'A15']."""
    m = re.match(r'(\w+)\[(\d+)\.\.(\d+)\]$', name)
    if not m:
        raise SystemExit('bad bus name %r' % name)
    return ['%s%d' % (m.group(1), i) for i in range(int(m.group(2)), int(m.group(3)) + 1)]


def check_hierarchy(sheets, root):
    """Every net that has pins on two or more sheets (rails aside) leaves each of
    those sheets on a hierarchical label -- its own, or a bus label whose vector
    holds it with the member's local label on the sheet; no other net does; each
    sheet's hierarchical labels are exactly its block's pins on the root; and a
    bus has one vector everywhere (KiCad joins differing vectors by position)."""
    where = D.sheet_nets()
    cross = {n for n, ss in where.items() if len(ss) > 1 and n not in D.RAIL_NETS}
    bad, vectors = [], {}
    for stem, sh in sheets.items():
        hier = {l[1] for l in sh.labels if l[0] == 'hierarchical_label'}
        local = {l[1] for l in sh.labels if l[0] == 'label'}
        covered = {n for n in hier if '[' not in n}
        for b in (n for n in hier if '[' in n):
            vectors.setdefault(re.match(r'\w+', b).group(0), set()).add(b)
            covered |= {m for m in bus_members(b) if m in local}
        mine = {n for n in cross if stem in where[n]}
        for n in sorted(mine - covered):
            bad.append('%s: net %s (also on %s) has no hierarchical label' % (stem, n, sorted(where[n] - {stem})))
        for n in sorted(covered - mine):
            bad.append('%s: hierarchical %s carries no net that crosses sheets here' % (stem, n))
        blk = next((b for b in root.blocks if b['stem'] == stem), None)
        if blk is None:
            bad.append('root: no block for %s' % stem)
        elif set(blk['pins']) != hier:
            bad.append('root: %s pins %s / labels %s' % (stem, sorted(set(blk['pins']) - hier),
                                                         sorted(hier - set(blk['pins']))))
    for b in root.blocks:
        for nm in b['pins']:
            if '[' in nm:
                vectors.setdefault(re.match(r'\w+', nm).group(0), set()).add(nm)
    for base, vs in vectors.items():
        if len(vs) > 1:
            bad.append('bus %s used with different vectors %s' % (base, sorted(vs)))
    if bad:
        raise SystemExit('hierarchy:\n  ' + '\n  '.join(bad))


def canon(n):
    """KiCad's net name -> design.py's: /NET (root label), /sheet/NET (a sheet's
    own net) and NET (power symbols) all name NET; unconnected-(...) stays."""
    return n if n.startswith('unconnected-') else n.rsplit('/', 1)[-1]


def netlist_parity():
    """The written schematic's netlist (kicad-cli) against design.py, net by net:
    the same name and the same (ref, pad) set, NC pins on KiCad's unconnected-(...) nets."""
    import subprocess, tempfile
    fd, fn = tempfile.mkstemp(prefix='fujinet-7800-parity-', suffix='.net')
    os.close(fd)
    try:
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn,
                        os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
        t = parse(open(fn).read())
    finally:
        os.remove(fn)
    got, full = {}, {}
    for n in findall(find(t, 'nets'), 'net'):
        name = canon(str(find(n, 'name')[1]))
        if name in got:    # two KiCad nets, one design net: a missing sheet pin or label
            raise SystemExit('netlist parity: %s and %s are separate nets' % (full[name], str(find(n, 'name')[1])))
        full[name] = str(find(n, 'name')[1])
        got[name] = {(str(find(nd, 'ref')[1]), str(find(nd, 'pin')[1])) for nd in findall(n, 'node')}
    want = {n: set(v) for n, v in D.nets().items()}
    bad = []
    for n, v in want.items():
        if got.get(n) != v:
            bad.append('%s: want %s, got %s' % (n, sorted(v)[:8], sorted(got.get(n, ()))[:8]))
    for n, v in got.items():
        if n not in want and not (n.startswith('unconnected-') and len(v) == 1):
            bad.append('extra net %s %s' % (n, sorted(v)[:8]))
        if n.startswith('unconnected-'):
            (ref, pad), = v
            if D.BY_REF[ref].pins.get(pad) is not None:
                bad.append('%s %s is unconnected, design.py says %s' % (ref, pad, D.BY_REF[ref].pins[pad]))
    if bad:
        raise SystemExit('netlist parity:\n  ' + '\n  '.join(bad[:40]))
    print('netlist parity: %d nets match design.py' % len(want))


def write_project(root_uuid, sheet_uuids):
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    pro['meta']['filename'] = D.PROJECT + '.kicad_pro'
    pro['sheets'] = [[root_uuid, 'Root']] + [[sheet_uuids[s[0]], s[0]] for s in D.SHEETS]
    # the template's project file named the NES root here; KiCad 10 opens the schematic by this entry
    pro['schematic']['top_level_sheets'] = [{'filename': D.PROJECT + '.kicad_sch', 'name': D.PROJECT,
                                             'uuid': '00000000-0000-0000-0000-000000000000'}]
    pro['erc']['rule_severities']['same_local_global_label'] = 'warning'   # no global labels left
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')


def main():
    import sch_layout
    syms = load_symbols()
    verify_pin_tables(syms)
    root_uuid = str(uid('root'))
    sheet_uuids = {s[0]: str(uid('sheet', s[0])) for s in D.SHEETS}
    pwr = {'pwr': 0, 'flg': 0}
    drawn = {}
    for stem, title, page in D.SHEETS:
        parts = [p for p in D.PARTS if p.sheet == stem]
        sh = sch_layout.draw(stem, syms, parts)
        sh.center()
        sh.check()
        drawn[stem] = sh
        sch = serialize(sh, title, root_uuid, sheet_uuids[stem], pwr)
        open(os.path.join(PRJ, stem + '.kicad_sch'), 'w').write(dump(sch) + '\n')
    root = sch_layout.draw_root(syms)
    root.check()
    check_hierarchy(drawn, root)
    open(os.path.join(PRJ, D.PROJECT + '.kicad_sch'), 'w').write(dump(serialize_root(root, root_uuid, sheet_uuids)) + '\n')
    write_project(root_uuid, sheet_uuids)
    netlist_parity()
    print('schematic written')


if __name__ == '__main__':
    main()
