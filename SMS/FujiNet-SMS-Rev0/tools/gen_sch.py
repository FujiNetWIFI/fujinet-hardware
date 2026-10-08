#!/usr/bin/env python3
"""Generate the FujiNet-SMS Rev0 schematic (root + 7 sheets) from design.py.

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
(re)writes: FujiNet-SMS.kicad_sym.  The sheet list in the .kicad_pro is kept
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
DATE = '2026-10-08'
COMMENT3 = 'Rev0 v2 2026-10-08: board co-designed with this schematic, see docs/floorplan-study.md'
NS = uuid.UUID('3c0b5e2a-9d41-4f6a-8c1e-5a6d2f7b9e10')


def uid(*k):
    return Q(str(uuid.uuid5(NS, '/'.join(map(str, k)))))


def font(size=1.27):
    return ['effects', ['font', ['size', size, size]]]


def hidden():
    return ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]


# ---------------------------------------------------------------------------
# project-library symbols
def _unit(name, u, left, right=(), bottom=(), top=(), w=15.24, tb_x=0, pitch=2.54, tb_pitch=2.54):
    """One unit's body and pins (lib coordinates, y up): left/right/bottom/top are lists of
    (number, name, etype[, shape]); None in a list leaves a gap of one pitch.  Every pin end on
    the 2.54 grid (w a multiple of 5.08, pitches multiples of 2.54).  Returns (body, pins, box)."""
    n = max(len(left), len(right), 1)
    y0 = ((n - 1) // 2) * pitch
    top_y = y0 + pitch
    bot_y = y0 - n * pitch
    half = w / 2
    body = ['symbol', Q('%s_%d_1' % (name, u)) if u else Q(name + '_0_1'),
            ['rectangle', ['start', -half, top_y], ['end', half, bot_y],
             ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]]
    pins = []

    def pin(num, nm, et, x, y, ang, shape='line'):
        pins.append(['pin', et, shape, ['at', x, y, ang], ['length', 2.54],
                     ['name', Q(nm), font()], ['number', Q(str(num)), font()]])
    for i, e in enumerate(left):
        if e:
            pin(*e[:3], -half - 2.54, y0 - i * pitch, 0, *e[3:])
    for i, e in enumerate(right):
        if e:
            pin(*e[:3], half + 2.54, y0 - i * pitch, 180, *e[3:])
    for i, e in enumerate(bottom):
        if e:
            x = tb_x - ((len(bottom) - 1) // 2) * tb_pitch + i * tb_pitch
            pin(*e[:3], x, bot_y - 2.54, 90, *e[3:])
    for i, e in enumerate(top):
        if e:
            x = tb_x - ((len(top) - 1) // 2) * tb_pitch + i * tb_pitch
            pin(*e[:3], x, top_y + 2.54, 270, *e[3:])
    return body, pins, (top_y, bot_y)


def box_symbol(name, ref, value, footprint, desc, left, right=(), bottom=(), top=(), w=15.24, tb_x=0, ds='',
               pitch=2.54, tb_pitch=2.54):
    """A single-unit project symbol (see _unit)."""
    body, pins, (top_y, bot_y) = _unit(name, 0, left, right, bottom, top, w, tb_x, pitch, tb_pitch)
    return ['symbol', Q(name), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
            ['in_bom', 'yes'], ['on_board', 'yes'],
            ['property', Q('Reference'), Q(ref), ['at', 0, top_y + 1.27, 0], font()],
            ['property', Q('Value'), Q(value), ['at', 0, bot_y - 5.08, 0], font()],
            ['property', Q('Footprint'), Q(footprint), ['at', 0, 0, 0], hidden()],
            ['property', Q('Datasheet'), Q(ds), ['at', 0, 0, 0], hidden()],
            ['property', Q('Description'), Q(desc), ['at', 0, 0, 0], hidden()],
            body, ['symbol', Q(name + '_1_1')] + pins]


def multi_symbol(name, ref, value, footprint, desc, units, ds=''):
    """A project symbol with several units (not interchangeable): units = [dict(left=, right=,
    bottom=, top=, w=, tb_x=, pitch=, tb_pitch=)], unit 1 first."""
    out = ['symbol', Q(name), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
           ['in_bom', 'yes'], ['on_board', 'yes'],
           ['property', Q('Reference'), Q(ref), ['at', 0, 2.54, 0], font()],
           ['property', Q('Value'), Q(value), ['at', 0, -2.54, 0], font()],
           ['property', Q('Footprint'), Q(footprint), ['at', 0, 0, 0], hidden()],
           ['property', Q('Datasheet'), Q(ds), ['at', 0, 0, 0], hidden()],
           ['property', Q('Description'), Q(desc), ['at', 0, 0, 0], hidden()],
           ['property', Q('ki_locked'), Q(''), ['at', 0, 0, 0], hidden()]]
    for u, spec in enumerate(units, 1):
        body, pins, _ = _unit(name, u, **spec)
        body[1] = Q('%s_%d_1' % (name, u))
        body += pins
        out.append(body)
    return out


# The RP2354B in two units (KiCad's MCU_RaspberryPi:RP2354B pin names and numbers, checked by
# verify_pin_tables; the stacked hidden supply pins unstacked so each wires to its own capacitor):
#   unit A, the cart-bus sheet: the 48 GPIOs -- the console bus on the left (A0-A15, D0-D7, the
#           strobes), the glue / bank / LED / /WAIT / debug lines on the right
#   unit B, the rp-core sheet: supplies, the core regulator, crystal, RUN, SWD, USB, QSPI
# unit A: the console bus on the left in the edge's row order (control, A0-A15, D0-D7, strobes)
# with the bank lines under it (toward the SRAMs); /WAIT, the LED and the debug UART on top (to
# their parts at the page top), the glue's mode bits and PWR_OK at the bottom (down to the glue)
RP_A_LEFT = [31, 29, 30, 28, None,
             0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, None,
             16, 17, 18, 19, 20, 21, 22, 23, None,
             27, 24, 26, 25, None, None, 41, 42, 43, 44, 45, 46, 47]
RP_A_TOP = [34, 33, None, 36, 37]
RP_A_BOTTOM = [32, None, 35, 38, 39, 40]
# unit B sides by the board side their parts sit on (the page is the board turned fingers-left:
# board west -> page top, north -> right, east -> bottom, south -> left), in the package's own
# order along each side, and every supply pin far enough from the next that its capacitor and
# their two labels sit beside it (sides listed in 2.54 mm slots; None = an empty slot):
#   top     IOVDD 76, QSPI_SS (BOOTSEL), the QSPI pins, QSPI_IOVDD, USB_OTP_VDD, USB D+/D-, then the
#           core regulator: VREG_FB, VREG_VIN, VREG_LX, VREG_AVDD
#   right   IOVDD 41 / 50, DVDD 51, ADC_AVDD, IOVDD 60
#   bottom  IOVDD 24 / 29, XIN, XOUT, DVDD 32, SWD, RUN, grounds      left  IOVDD 5, DVDD 10, IOVDD 15
def _slots(spec):
    out = []
    for pin, gap in spec:
        out += [pin] + [None] * gap
    return out[:-1] if out and out[-1] is None else out


RP_B_TOP = _slots([(76, 6), (75, 3), (74, 0), (73, 0), (72, 0), (71, 0), (70, 3), (69, 6), (68, 6), (67, 2),
                   (66, 4), (65, 3), (64, 6), (63, 4), (61, 0)])
RP_B_RIGHT = _slots([(41, 6), (50, 6), (51, 6), (59, 6), (60, 0)])
RP_B_BOTTOM = _slots([(24, 6), (29, 6), (30, 4), (31, 6), (32, 6), (33, 3), (34, 3), (35, 8), (62, 2), (81, 0)])
RP_B_LEFT = _slots([(5, 6), (10, 6), (15, 0)])
RP_B_GND = []


def sym_w(top, pitch=2.54, margin=5.08):
    """The narrowest body (a multiple of 5.08) that holds a top row of len(top) slots."""
    import math
    need = (len(top) - 1) * pitch + 2 * margin
    return math.ceil(need / 5.08) * 5.08


def rp_split_symbol(stock):
    """FujiNet-SMS:RP2354B_Split from the stock symbol's pins."""
    pins = {}
    for sub in findall(stock, 'symbol'):
        for p in findall(sub, 'pin'):
            pins[str(find(p, 'number')[1])] = (str(find(p, 'name')[1]), str(p[1]))
    gpio = {g: str(n) for g, n in D.RP_GPIO_PIN.items()}
    used = set()

    def P(num, power=False):
        num = str(num)
        used.add(num)
        nm, et = pins[num]
        if power and et == 'passive':      # the stock symbol stacks these hidden behind a visible one
            et = 'power_in'
        return (num, nm, et)
    unit_a = dict(left=[P(gpio[g]) if g is not None else None for g in RP_A_LEFT],
                  top=[P(gpio[g]) if g is not None else None for g in RP_A_TOP],
                  bottom=[P(gpio[g]) if g is not None else None for g in RP_A_BOTTOM],
                  w=40.64, tb_x=7.62, tb_pitch=5.08)
    sup = lambda lst: [P(n, True) if n is not None else None for n in lst]
    unit_b = dict(top=sup(RP_B_TOP), right=sup(RP_B_RIGHT), bottom=sup(RP_B_BOTTOM),
                  left=sup(RP_B_LEFT), w=sym_w(RP_B_TOP), tb_pitch=2.54)
    assert used == set(pins), sorted(set(pins) - used)
    return multi_symbol('RP2354B_Split', 'U', 'RP2354B', D.FP('QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm'),
                        'RP2354B (RP2350B + 2 MB flash), KiCad MCU_RaspberryPi:RP2354B pins in two units: '
                        'A = GPIO0-47, B = supplies / regulator / crystal / RUN / SWD / USB / QSPI',
                        [unit_a, unit_b], ds='https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf')


# The ESP32-S3 module by function (KiCad's RF_Module:ESP32-S3-WROOM-1 pin names, numbers and
# types; GND 40 / 41 stacked hidden behind GND 1 as there), each group facing the parts it serves
# on the page (the board turned fingers-left): the WS2812, BOOT and the RP2354B's RUN / BOOTSEL /
# USB on the left (west and south of the module on the board); EN beside 3V3 on top, to its
# power-on RC and button above the module; the UART to the USB bridge top right; the microSD's
# SPI lines along the bottom toward the socket (east), spaced for the pull-ups between them; the
# 23 spare GPIOs, in GPIO order, down the right.
S3_LEFT = ['IO48', None, None, None, None, None, 'IO0', None, None, None, None, None, None,
           'IO4', 'IO5', None, 'IO20', 'IO19']
S3_RIGHT = ['TXD0', 'RXD0', None] + ['IO%d' % g for g in (1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                                                         17, 18, 21, 35, 36, 37, 45, 46, 47)] + [None] * 2
S3_TOP = ['EN', None, None, None, None, None, '3V3']
S3_BOTTOM = ['GND', None, None, None, 'IO42', None, None, None, None, 'IO41', None, None, None,
             'IO40', None, None, None, 'IO39', None, 'IO38']


def s3_symbol(stock):
    pins = {}
    for sub in findall(stock, 'symbol'):
        for p in findall(sub, 'pin'):
            pins[str(find(p, 'number')[1])] = (str(find(p, 'name')[1]), str(p[1]))
    by_fn = {}
    for fn, pad in D.S3_PAD.items():
        for p in (pad if isinstance(pad, list) else [pad]):
            by_fn.setdefault(fn, []).append(str(p))
    used = set()

    def P(fn):
        if fn is None:
            return None
        num = by_fn[fn][0]
        used.add(num)
        return (num,) + pins[num]
    body, pl, (top_y, bot_y) = _unit('ESP32-S3-WROOM-1_Fn', 0, [P(f) for f in S3_LEFT], [P(f) for f in S3_RIGHT],
                                      [P(f) for f in S3_BOTTOM], [P(f) for f in S3_TOP], w=55.88, tb_x=-2.54)
    g1 = next(p for p in pl if find(p, 'number')[1] == Q('1'))
    for num in by_fn['GND'][1:]:              # 40 and 41: stacked on GND 1, hidden, as in the stock symbol
        used.add(num)
        pl.append(['pin', pins[num][1], 'line', list(find(g1, 'at')), ['length', 2.54], ['hide', 'yes'],
                   ['name', Q(pins[num][0]), font()], ['number', Q(num), font()]])
    assert used == set(pins), sorted(set(pins) - used)
    return ['symbol', Q('ESP32-S3-WROOM-1_Fn'), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
            ['in_bom', 'yes'], ['on_board', 'yes'],
            ['property', Q('Reference'), Q('U'), ['at', 0, top_y + 1.27, 0], font()],
            ['property', Q('Value'), Q('ESP32-S3-WROOM-1'), ['at', 0, bot_y - 5.08, 0], font()],
            ['property', Q('Footprint'), Q(D.FP('ESP32-S3-WROOM-1')), ['at', 0, 0, 0], hidden()],
            ['property', Q('Datasheet'), Q('https://www.espressif.com/sites/default/files/documentation/'
                                           'esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf'), ['at', 0, 0, 0], hidden()],
            ['property', Q('Description'), Q('ESP32-S3-WROOM-1 module, KiCad RF_Module:ESP32-S3-WROOM-1 pins '
                                             'grouped by function'), ['at', 0, 0, 0], hidden()],
            body, ['symbol', Q('ESP32-S3-WROOM-1_Fn_1_1')] + pl]


# The USB-C receptacle as it sits on the page's right edge, facing the bridge: VBUS on top (to its
# rail and shunts along the top of the page), CC1 / CC2 and the two D- / D+ pairs facing left,
# grounds below; the stock symbol's stacked VBUS and GND pins stacked again, hidden.
def usbc_symbol(stock):
    pins = {}
    for sub in findall(stock, 'symbol'):
        for p in findall(sub, 'pin'):
            pins[str(find(p, 'number')[1])] = (str(find(p, 'name')[1]), str(p[1]))
    P = lambda n: (n,) + pins[n] if n else None
    left = [P(n) for n in ('A5', None, None, 'B5', None, None, None, 'A7', 'B7', None, 'A6', 'B6', None, 'A8', 'B8',
                           None, None)]
    body, pl, (top_y, bot_y) = _unit('USB_C_USB2.0_16P_Fn', 0, left, (), [P('A1'), None, P('SH')],
                                     [P('A4')], w=15.24, tb_x=0, tb_pitch=5.08)
    for main, extra in (('A4', ('A9', 'B4', 'B9')), ('A1', ('A12', 'B1', 'B12'))):
        at = find(next(p for p in pl if find(p, 'number')[1] == Q(main)), 'at')
        for n in extra:
            pl.append(['pin', pins[n][1], 'line', list(at), ['length', 2.54], ['hide', 'yes'],
                       ['name', Q(pins[n][0]), font()], ['number', Q(n), font()]])
    assert {str(find(p, 'number')[1]) for p in pl} == set(pins)
    return ['symbol', Q('USB_C_USB2.0_16P_Fn'), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'],
            ['in_bom', 'yes'], ['on_board', 'yes'],
            ['property', Q('Reference'), Q('J'), ['at', 0, top_y + 1.27, 0], font()],
            ['property', Q('Value'), Q('USB-C'), ['at', 0, bot_y - 5.08, 0], font()],
            ['property', Q('Footprint'), Q(D.FP('USB_C_Receptacle_HRO_TYPE-C-31-M-12')), ['at', 0, 0, 0], hidden()],
            ['property', Q('Datasheet'), Q('https://www.usb.org/sites/default/files/documents/usb_type-c.zip'),
             ['at', 0, 0, 0], hidden()],
            ['property', Q('Description'), Q('USB 2.0-only 16P Type-C receptacle, KiCad '
                                             'Connector:USB_C_Receptacle_USB2.0_16P pins by function'),
             ['at', 0, 0, 0], hidden()],
            body, ['symbol', Q('USB_C_USB2.0_16P_Fn_1_1')] + pl]


# The edge drawn by function, its groups in the fingers' west-to-east order -- the page is the
# board turned fingers-left, so board west is page top: the console inputs that end beside the
# edge (/BUSREQ, /WAIT, /CONT) and the control fingers (CLK /RESET /M1 /IORQ, west),
# the address and data bus (A0-A15, D0-D7, functional order), the strobes (/CE /RD /MREQ /WR,
# east).  Every console signal on the right, toward the cart; the ten unused console outputs on
# the left.
EDGE_GROUPS = [['BUSREQ_N', 'WAIT_N', 'CONT_N'], ['CLK', 'RESET_N', 'M1_N', 'IORQ_N'],
               ['A%d' % i for i in range(16)], ['D%d' % i for i in range(8)],
               ['CE_N', 'RD_N', 'MREQ_N', 'WR_N']]


def edge_symbol():
    by_net = {}
    for p, (net, nm) in D.EDGE.items():
        by_net.setdefault(net, []).append(p)
    right = []
    for g in EDGE_GROUPS:
        if right:
            right.append(None)
        right += [(by_net[n][0], D.EDGE[by_net[n][0]][1], 'passive') if n else None for n in g]
    left = [None, None] + [(p, D.EDGE[p][1], 'passive') for p in sorted(by_net[None])]   # clear of the +5V pin names
    top = [(p, '+5V', 'passive') for p in by_net['CONS_5V']]
    bottom = [(p, 'GND', 'passive') for p in by_net['GND']]
    assert len([e for e in right if e]) + len([e for e in left if e]) + len(top) + len(bottom) == 50
    return box_symbol('SMS_Cart_Edge_50', 'J', 'SMS_Cart_Edge_50', D.FP('SMS_Cart_Edge_50'),
                      'Sega Master System 50-pin cartridge edge, 2.54 mm pitch; odd pins one face, even pins '
                      'the other, pin 2k-1 over pin 2k (face and pin-1 end PROVISIONAL)',
                      left=left, right=right, top=top, bottom=bottom, w=30.48, tb_x=-7.62)


def project_symbols(stock=None):
    edge = edge_symbol()
    sp = D.SRAM_PIN
    # the SRAM's console pins on the left, row for row with the edge's A0-A15 / D0-D7 (A13-A15 rows
    # empty), so the ROM-spot SRAM wires straight across from the edge as its copper does; the
    # RP's bank lines and the glue's strobes on the right
    sram = box_symbol('AS6C4008-55TIN', 'U', 'AS6C4008-55TIN', D.FP('TSOP-I-32_18.4x8mm_P0.5mm'),
                      '512K x 8 low power CMOS SRAM, 55 ns, 2.7-5.5 V, TSOP-I-32 (Alliance pin order)',
                      left=[(sp['A%d' % i], 'A%d' % i, 'input') for i in range(13)] + [None] * 4 +
                           [(sp['DQ%d' % i], 'DQ%d' % i, 'bidirectional') for i in range(8)],
                      right=[None, None, None] +
                            [(sp['A%d' % i], 'A%d' % i, 'input') for i in range(13, 19)] + [None] +
                            [(sp['CE#'], '~{CE}', 'input'), (sp['OE#'], '~{OE}', 'input'),
                             (sp['WE#'], '~{WE}', 'input'), None,
                             (sp['VCC'], 'VCC', 'power_in'), None, None, (sp['VSS'], 'VSS', 'power_in')],
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
    rpx = rp_split_symbol(stock['MCU_RaspberryPi:RP2354B'])
    s3 = s3_symbol(stock['RF_Module:ESP32-S3-WROOM-1'])
    usbc = usbc_symbol(stock['Connector:USB_C_Receptacle_USB2.0_16P'])
    lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('fujinet_gen')],
           ['generator_version', Q('1.0')], edge, sram, sd, rpx, s3, usbc]
    open(os.path.join(PRJ, D.LIB + '.kicad_sym'), 'w').write(dump(lib) + '\n')
    cache = {}
    for s in (edge, sram, sd, rpx, s3, usbc):
        c = copy.deepcopy(s)
        c[1] = Q(D.LIB + ':' + s[1])
        cache[c[1]] = c
    return cache


# ---------------------------------------------------------------------------
def load_symbols():
    t = parse(open(os.path.join(HERE, 'symcache.sexpr')).read())
    syms = {s[1]: s for s in t[1:]}
    syms.update(project_symbols(syms))
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
    if pin_names(syms[D.LIB + ':RP2354B_Split']) != names:
        raise SystemExit('RP2354B_Split: pin names differ from the stock RP2354B symbol')
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
    if pin_names(syms[D.LIB + ':USB_C_USB2.0_16P_Fn']) != pin_names(syms['Connector:USB_C_Receptacle_USB2.0_16P']):
        raise SystemExit('USB_C_USB2.0_16P_Fn: pin names differ from the stock USB-C symbol')
    if pin_names(syms[D.LIB + ':ESP32-S3-WROOM-1_Fn']) != names:
        raise SystemExit('ESP32-S3-WROOM-1_Fn: pin names differ from the stock ESP32-S3-WROOM-1 symbol')
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
        hid_f = d.get('hide_fields', ())
        fl = [field('Reference', ref, d['fields'][0], rot, 'Reference' in hid_f, mirror=d['mirror']),
              field('Value', p.value, d['fields'][1], rot, 'Value' in hid_f, mirror=d['mirror']),
              field('Footprint', p.footprint, hid, rot, True), field('Datasheet', ds, hid, rot, True),
              field('Description', p.desc, hid, rot, True)]
        for k, v in (('MPN', p.mpn), ('Manufacturer', p.mfr), ('LCSC', p.lcsc)):
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
    tb = ['title_block', ['title', Q('FujiNet SMS Rev0 - ' + title)], ['date', Q(DATE)],
          ['rev', Q('0')], ['company', Q('FujiNet')],
          ['comment', 1, Q('Generated from tools/design.py + tools/sch_layout.py - edit those, not this file')],
          ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-NES-Rev0 and its sources)')],
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
    for k, (pts, dash) in enumerate(sh.graphics):
        items.append(['polyline', ['pts'] + [['xy', x, y] for x, y in pts],
                      ['stroke', ['width', 0.254], ['type', 'dash' if dash else 'solid']], ['fill', ['type', 'none']],
                      ['uuid', uid('root', 'poly', k)]])
    tb = ['title_block', ['title', Q('FujiNet SMS Rev0')], ['date', Q(DATE)], ['rev', Q('0')],
          ['company', Q('FujiNet')],
          ['comment', 1, Q('Generated from tools/design.py + tools/sch_layout.py - edit those, not this file')],
          ['comment', 2, Q('CERN-OHL-W-2.0 (derived from FujiNet-NES-Rev0 and its sources)')],
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
    fd, fn = tempfile.mkstemp(prefix='fujinet-sms-parity-', suffix='.net')
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
    # the names KiCad gives the nets are what the board carries (/cart-bus/A0, /USB_DP, GND, ...):
    # frozen in tools/nets.lock once the hierarchy is final, so a redraw can change geometry only
    names = sorted(full.values()) + sorted(n for n in got if n.startswith('unconnected-'))
    lock = os.path.join(HERE, 'nets.lock')
    if '--lock-nets' in sys.argv:
        json.dump(names, open(lock, 'w'), indent=0)
        open(lock, 'a').write('\n')
        print('nets.lock: %d net names written' % len(names))
    elif os.path.exists(lock):
        old = json.load(open(lock))
        if old != names:
            raise SystemExit('nets.lock: the net names changed (the board carries the locked ones):\n  -%s\n  +%s'
                             % (sorted(set(old) - set(names))[:20], sorted(set(names) - set(old))[:20]))
        print('nets.lock: %d net names unchanged' % len(names))


def mirror_gate(drawn):
    """Every hand-drawn sheet mirrors the board (tools/sch_place.py): its major parts in their
    board order across and down the page.  The placement is placement.py's, the one the board is
    built from."""
    import sch_place
    import gen_pcb
    gen_pcb.do_placement(gen_pcb.place, [])
    bad = []
    for stem, sh in drawn.items():
        if not sh.wired:
            continue
        tx, ty, probs = sch_place.mirror_check(sh, gen_pcb.PLACE)
        print('%s: mirrors the board, tau %.2f across, %.2f down' % (stem, tx, ty))
        bad += probs
    if bad:
        msg = 'mirror check:\n  ' + '\n  '.join(bad)
        if os.environ.get('SCH_DRAFT'):
            print(msg)
        else:
            raise SystemExit(msg)


def write_project(root_uuid, sheet_uuids):
    fn = os.path.join(PRJ, D.PROJECT + '.kicad_pro')
    pro = json.load(open(fn))
    pro['meta']['filename'] = D.PROJECT + '.kicad_pro'
    pro['sheets'] = [[root_uuid, 'Root']] + [[sheet_uuids[s[0]], s[0]] for s in D.SHEETS]
    pro['erc']['rule_severities']['same_local_global_label'] = 'warning'   # no global labels left
    # KiCad 10 opens the schematic by this entry (a template's project file can name another root)
    pro['schematic']['top_level_sheets'] = [{'filename': D.PROJECT + '.kicad_sch', 'name': D.PROJECT,
                                             'uuid': '00000000-0000-0000-0000-000000000000'}]
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
    where = D.sheet_nets()
    for stem, title, page in D.SHEETS:
        parts = [p for p in D.PARTS if stem in p.sheets()]
        cross = {n for n, ss in where.items() if len(ss) > 1 and n not in D.RAIL_NETS and stem in ss}
        sh = sch_layout.draw(stem, syms, parts, cross)
        sh.center()
        sh.check()
        if sh.wired:
            print('%s: drawn, %d wire crossings' % (stem, sh.crossings))
        drawn[stem] = sh
        sch = serialize(sh, title, root_uuid, sheet_uuids[stem], pwr)
        open(os.path.join(PRJ, stem + '.kicad_sch'), 'w').write(dump(sch) + '\n')
    mirror_gate(drawn)
    root = sch_layout.draw_root(syms, drawn)
    root.check()
    check_hierarchy(drawn, root)
    open(os.path.join(PRJ, D.PROJECT + '.kicad_sch'), 'w').write(dump(serialize_root(root, root_uuid, sheet_uuids)) + '\n')
    write_project(root_uuid, sheet_uuids)
    netlist_parity()
    print('schematic written')


if __name__ == '__main__':
    main()
