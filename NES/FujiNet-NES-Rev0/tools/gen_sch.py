#!/usr/bin/env python3
"""Generate the schematic (root + 7 sheets) from design.py.

design.py says what connects to what; sch_layout.py says how each sheet is
drawn: parts placed left to right in signal-flow order and joined by wires,
the parallel CPU / PPU buses as KiCad buses, rails as power symbols, global
labels only where a net leaves the sheet (sch_draw.py has the conventions).
Each sheet is connectivity-checked as it is drawn (sch_draw.Sheet.check) and
the written schematic is checked once more through kicad-cli's netlist
against design.py, net by net, names included.  Symbols come from
tools/symcache.sexpr (stock KiCad symbols as flattened by eeschema, see
harvest_symbols.py) plus the project library, which this script also
(re)writes: FujiNet-NES.kicad_sym.  The sheet list in the .kicad_pro is kept
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
DATE = '2026-10-04'
NS = uuid.UUID('6f1c9a1e-3a52-4d7e-9b7d-0a57a0ade5e5')


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
# right (toward the cart), grouped CPU address / data / control, PPU address /
# data / control, CIC; the unused EXP fingers and SYSTEM CLK on the left.
EDGE_GROUPS = [['CA%d' % i for i in range(15)], ['CD%d' % i for i in range(8)],
               ['M2', 'RW', 'ROMSEL_N', 'IRQ_N'],
               ['PA%d' % i for i in range(14)] + ['PA13_N'], ['PD%d' % i for i in range(8)],
               ['PPU_RD_N', 'PPU_WR_N', 'CIRAM_A10', 'CIRAM_CE_N'],
               ['CIC_TOMB', None, 'CIC_TOPAK', None, 'CIC_RST', None, 'CIC_CLK']]   # the CIClone's order, 5.08 apart for the net names


def edge_symbol():
    by_net = {}
    for p, (net, nm) in D.EDGE.items():
        by_net.setdefault(net, []).append(p)
    right = []
    for g in EDGE_GROUPS:
        if right:
            right.append(None)
        right += [(by_net[n][0], D.EDGE[by_net[n][0]][1], 'passive') if n else None for n in g]
    left = [(p, D.EDGE[p][1], 'passive') for p in sorted(by_net[None], key=lambda p: (D.EDGE[p][1] == 'SYSTEM CLK', int(D.EDGE[p][1][3:]) if D.EDGE[p][1].startswith('EXP') else 0))]
    assert len([e for e in right if e]) + len(left) + 3 == 72
    return box_symbol('NES_Cart_Edge_72', 'J', 'NES_Cart_Edge_72', D.FP('NES_Cart_Edge_72'),
                      'NES 72-pin cartridge edge, 2.50 mm pitch; pins 1-36 label side, 37-72 back (nesdev)',
                      left=left, right=right, top=[(36, '+5V', 'passive')],
                      bottom=[(1, 'GND', 'passive'), (72, 'GND', 'passive')], w=30.48, tb_x=-7.62)


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
    # the '253 with its pins in signal-flow order (selects, half a, half b), same
    # pin numbers / names / types as 74xx:74LS253 so check_nets reads it the same
    mux = box_symbol('74HCT253', 'U', '74HCT253', D.SOIC16,
                     'Dual 4-to-1 multiplexer, 3-state outputs (drawn in signal-flow order)',
                     left=[(14, 'A0', 'input'), (2, 'A1', 'input'), None,
                           (6, 'I0a', 'input'), (5, 'I1a', 'input'), (4, 'I2a', 'input'), (3, 'I3a', 'input'),
                           (1, 'OEa', 'input', 'inverted'), None,
                           (10, 'I0b', 'input'), (11, 'I1b', 'input'), (12, 'I2b', 'input'), (13, 'I3b', 'input'),
                           (15, 'OEb', 'input', 'inverted')],
                     right=[None, None, None, (7, 'Za', 'tri_state')] + [None] * 5 + [(9, 'Zb', 'tri_state')],
                     top=[(16, 'VCC', 'power_in')], bottom=[(8, 'GND', 'power_in')], w=20.32,
                     ds='https://www.ti.com/lit/gpn/sn74hct253')
    lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('fujinet_gen')],
           ['generator_version', Q('1.0')], edge, sram, sd, mux]
    open(os.path.join(PRJ, D.LIB + '.kicad_sym'), 'w').write(dump(lib) + '\n')
    cache = {}
    for s in (edge, sram, sd, mux):
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
        ds = next((pr[2] for pr in findall(sym, 'property') if pr[1] == 'Datasheet'), '')
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
        if kind == 'global_label':
            e.append(['shape', shape])
        e += [['at', x, y, ang]]
        if kind == 'global_label':
            e.append(['fields_autoplaced', 'yes'])
        e += [['effects', ['font', ['size', 1.27, 1.27]], ['justify', just] if kind == 'global_label'
               else ['justify', just, 'bottom']], ['uuid', uid(stem, kind, net, x, y)]]
        items.append(e)
    for s, x, y, size, j in sh.texts:
        items.append(['text', Q(s.replace('\n', '\\n')), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                      ['effects', ['font', ['size', size, size]], ['justify', j, 'top']], ['uuid', uid(stem, 'text', x, y)]])
    lib_symbols = ['lib_symbols'] + [used[k] for k in sorted(used)]
    tb = ['title_block', ['title', Q('FujiNet NES Rev0 - ' + title)], ['date', Q(DATE)],
          ['rev', Q('0')], ['company', Q('FujiNet')],
          ['comment', 1, Q('Generated by tools/gen_sch.py + tools/sch_layout.py from tools/design.py - edit those, not this file')],
          ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-Astrocade-Rev0 / FujiNet-INTV-Rev0 / PiNTY CARD)')],
          ['comment', 3, Q('Rev0 audit 2026-10-01: kicad-happy + datasheets; see docs/design-review-rev0.md')]]
    return ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
            ['generator_version', Q('9.0')], ['uuid', Q(sheet_uuid)], ['paper', Q(sh.paper)], tb,
            lib_symbols] + items + [['embedded_fonts', 'no']]


def netlist_parity():
    """The written schematic's netlist (kicad-cli) against design.py, net by net:
    the same name and the same (ref, pad) set, NC pins on KiCad's unconnected-(...) nets."""
    import subprocess, tempfile
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-nes-sch-parity.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    t = parse(open(fn).read())
    got = {}
    for n in findall(find(t, 'nets'), 'net'):
        name = str(find(n, 'name')[1])
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


NOTES = """FujiNet for the Nintendo Entertainment System - Rev0 (RP2354B)

RP2354B (48 GPIO) sits on the 5V cart bus directly through its 5V-tolerant pads: CPU A0-A14, D0-D7, M2, R/W,
/ROMSEL, PPU A10-A12 in; /IRQ out; it serves $5000-$7FFF and the reset vectors itself and drives the two
AS6C4008 SRAMs' bank lines (PRG A13-A18 = GP33-38, CHR A10-A18 = GP39-47) from PIO lookup tables.
Its IOVDD group runs from a fast LDO (+3V3_RP) so the pads are powered before the console bus is; the core
regulator input stays on the buck (+3V3).  The SRAMs and the 74HCT glue run on +5V: console 5V through a
P-FET (on without USB) ORed with USB VBUS through a Schottky, so their outputs drive the 5V bus at full level.
74HCT595 holds the slow control bits (SRAM_EN PRG_WE_EN CHR_WE_EN MIR0 MIR1 FOURSCREEN LED spare); its /OE
is held off for ~140 ms after power-on and whenever the console is off, with 100k pull-downs on every bit.
74HCT253 muxes CIRAM A10 for mirroring and gates CIRAM /CE; PWR_OK (console +5V sense) tri-states both and
disables every SRAM output toward the console.  PRG /WE = NAND4(M2, ROMSEL, !R/W, PRG_WE_EN) on a 74HCT20: one gate after M2.
ESP32-S3-WROOM-1-N16R8 runs FujiNet (fujiversal-nes) and is the USB host of the RP (CDC, VID 0xCafe);
S3 IO4/IO5 force RP RUN/QSPI_SS so the S3 can re-flash the RP over PICOBOOT.
USB-C: power + CP2102N UART bridge for flashing the S3.  microSD on S3 SPI.  CIClone (ATtiny13A) on the
CIC fingers, DNP until its firmware exists.
Edge: 72 pins, 2.50 mm pitch, 1-36 on the label side, pin 1 at the RIGHT seen from the label side with the
fingers down (nesdev Cartridge connector; NES-EWROM-01 geometry).  EXP and SYSTEM CLK unconnected."""


def write_project(root_uuid, sheet_uuids):
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    pro['meta']['filename'] = D.PROJECT + '.kicad_pro'
    pro['sheets'] = [[root_uuid, 'Root']] + [[sheet_uuids[s[0]], s[0]] for s in D.SHEETS]
    # bus members carry local labels (CA3 under the global bus CA[0..14]) while
    # single lines of the same net leave other sheets on global labels -- by design
    pro['erc']['rule_severities']['same_local_global_label'] = 'ignore'
    json.dump(pro, open(fn, 'w'), indent=2)
    open(fn, 'a').write('\n')


def main():
    import sch_layout
    syms = load_symbols()
    verify_pin_tables(syms)
    root_uuid = str(uid('root'))
    sheet_uuids = {s[0]: str(uid('sheet', s[0])) for s in D.SHEETS}
    pwr = {'pwr': 0, 'flg': 0}
    for stem, title, page in D.SHEETS:
        parts = [p for p in D.PARTS if p.sheet == stem]
        sh = sch_layout.draw(stem, syms, parts)
        sh.center()
        sh.check()
        sch = serialize(sh, title, root_uuid, sheet_uuids[stem], pwr)
        open(os.path.join(PRJ, stem + '.kicad_sch'), 'w').write(dump(sch) + '\n')
    root = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')],
            ['generator_version', Q('9.0')], ['uuid', Q(root_uuid)], ['paper', Q('A3')],
            ['title_block', ['title', Q('FujiNet NES Rev0')], ['date', Q(DATE)], ['rev', Q('0')],
             ['company', Q('FujiNet')], ['comment', 1, Q('Generated by tools/gen_sch.py')]],
            ['lib_symbols']]
    # sheet symbols in signal-flow order: the cart side (console -> RP -> SRAM -> glue)
    # on the first row, the FujiNet side (S3 -> USB -> power) on the second
    for i, (stem, title, page) in enumerate(D.SHEETS):
        x, y = 20.32 + (i % 4) * 96.52, 35.56 + (i // 4) * 45.72
        root.append(['sheet', ['at', x, y], ['size', 81.28, 25.4], ['fields_autoplaced', 'yes'],
                     ['stroke', ['width', 0.12], ['type', 'solid']], ['fill', ['color', 0, 0, 0, 0.0]],
                     ['uuid', Q(sheet_uuids[stem])],
                     ['property', Q('Sheetname'), Q(stem), ['at', x, y - 1, 0],
                      ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'bottom']]],
                     ['property', Q('Sheetfile'), Q(stem + '.kicad_sch'), ['at', x, y + 26.4, 0],
                      ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']]],
                     ['instances', ['project', Q(D.PROJECT), ['path', Q('/' + root_uuid), ['page', Q(str(page))]]]]])
        words, lines = title.split(), ['']
        for w in words:
            if len(lines[-1]) + len(w) > 62:
                lines.append('')
            lines[-1] = (lines[-1] + ' ' + w).strip()
        root.append(['text', Q('\\n'.join(lines)), ['exclude_from_sim', 'no'], ['at', x + 2.54, y + 5.08, 0],
                     ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top']],
                     ['uuid', uid('roottext', stem)]])
    root.append(['text', Q(NOTES.replace('\n', '\\n')), ['exclude_from_sim', 'no'], ['at', 20, 125, 0],
                 ['effects', ['font', ['size', 2, 2]], ['justify', 'left', 'top']], ['uuid', uid('notes')]])
    root.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
    root.append(['embedded_fonts', 'no'])
    open(os.path.join(PRJ, D.PROJECT + '.kicad_sch'), 'w').write(dump(root) + '\n')
    for stem in ('cart-rp2354b',):          # sheets this generator no longer writes
        if os.path.exists(os.path.join(PRJ, stem + '.kicad_sch')):
            os.remove(os.path.join(PRJ, stem + '.kicad_sch'))
    write_project(root_uuid, sheet_uuids)
    netlist_parity()
    print('schematic written')


if __name__ == '__main__':
    main()
