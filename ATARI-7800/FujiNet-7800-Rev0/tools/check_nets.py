#!/usr/bin/env python3
"""Cross-check the FujiNet-7800 Rev0 schematic netlist against the firmware
that has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads
  $FUJINET_FIRMWARE/pico/atari-7800/firmware/include/a78_cart.h   *_PIN GPIO numbers
  $FUJINET_FIRMWARE/pico/atari-7800/firmware/include/a78map.h     slot-word bits (SLOT_PIN + bit)
      (default ~/Workspace/fujinet-firmware)
  $FUJINET_A78_BOARD/include/pinmap/fujiversal-atari7800.h       S3 SD / LED / UART pins
      (default ~/Workspace/fn-7800-board; if it is missing, the SMS board's
      $FUJINET_SMS_BOARD/include/pinmap/fujiversal-sms.h, whose S3 contract
      this board copies, default ~/Workspace/fn-sms-board), and
      fujiversal-intv.h there for PIN_RP2040_RUN/BOOTSEL, which
      fujiversal-atari7800.h does not define yet
and checks every GPIO of both chips against the pin *functions* the netlist
reports (GPIOn on the RP2354B, IOn on the S3, An/DQn on the SRAM), the
7800 32-pin edge map (its own copy of the pin list), the 5 V-tolerance rule
for GPIO40-47, the audio and /IRQ circuits, the power path, and the edge
footprint's face / pin-1 split.  The glue logic itself is check_glue.py's.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, unconn, define, PRJ

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
INC = os.path.join(FW, 'pico/atari-7800/firmware/include')
CART = os.path.join(INC, 'a78_cart.h')
MAP = os.path.join(INC, 'a78map.h')
A78_BOARD = os.environ.get('FUJINET_A78_BOARD', os.path.expanduser('~/Workspace/fn-7800-board'))
SMS_BOARD = os.environ.get('FUJINET_SMS_BOARD', os.path.expanduser('~/Workspace/fn-sms-board'))
PINMAP = os.path.join(A78_BOARD, 'include/pinmap/fujiversal-atari7800.h')
if not os.path.exists(PINMAP):
    PINMAP = os.path.join(SMS_BOARD, 'include/pinmap/fujiversal-sms.h')
PINMAP_RUN = os.path.join(SMS_BOARD, 'include/pinmap/fujiversal-intv.h')

# Atari 7800 32-pin cartridge edge: Dan Boris (atarihq.com/danb/7800cart),
# matching hardwarebook.info and allpinouts.  3-14 / 19-30 are the 2600's.
EDGE = {1: 'R/W', 2: '/HALT', 3: 'D3', 4: 'D4', 5: 'D5', 6: 'D6', 7: 'D7', 8: 'A12', 9: 'A10',
        10: 'A11', 11: 'A9', 12: 'A8', 13: '+5V', 14: 'GND', 15: 'A13', 16: 'A14', 17: 'A15',
        18: 'EAUDIO', 19: 'A7', 20: 'A6', 21: 'A5', 22: 'A4', 23: 'A3', 24: 'A2', 25: 'A1', 26: 'A0',
        27: 'D0', 28: 'D1', 29: 'D2', 30: 'GND', 31: '/IRQ', 32: 'PHI2'}
STROBE_PIN = {'R/W': 'RW', 'PHI2': 'PHI2', '/HALT': 'HALT'}   # edge signal -> a78_cart.h <name>_PIN
GLUE = ('74HCT14', '74HCT00', '74HCT20')
INV6 = [(1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12)]          # 74xx14
VAL = lambda s: float(s.replace('k', 'e3').replace('R', '').replace('nF', 'e-9').replace('uF', 'e-6'))

fails = 0
count = 0


def chk(desc, ok):
    global fails, count
    count += 1
    if not ok:
        fails += 1
        print('FAIL:', desc)


def main():
    N = Netlist()
    node_net, func_net, nets, parts = N.node_net, N.func_net, N.nets, N.parts
    one = N.one
    U1, J1, S3 = one('RP2354B'), one('Atari7800_Cart_Edge_32'), one('ESP32-S3-WROOM-1-N16R8')
    J2, UCP, WS = one('microSD'), one('CP2102N-A02-GQFN28'), one('WS2812C-2020-V1')
    U14, LDO, QFET, QI = one('74HCT14'), one('AP2112K-3.3'), one('AO3401A'), one('2N7002')
    srams = N.by_value('AS6C4008-55TIN')
    for ref, what in ((U1, 'RP2354B'), (J1, 'edge'), (S3, 'ESP32-S3'), (U14, '74HCT14'), (LDO, 'AP2112K LDO'),
                      (QFET, 'AO3401A'), (QI, '2N7002')):
        if ref is None:
            raise SystemExit('no %s in the netlist' % what)
    if len(srams) != 1:
        raise SystemExit('expected one AS6C4008-55TIN, found %r' % srams)
    S = srams[0]
    glue = {r for r, (v, _) in parts.items() if v in GLUE}
    tps = {r for r in parts if re.match(r'TP\d+$', r)}         # bring-up / SWD test pads (no BOM part)

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((S3, 'IO%d' % io))

    def two_pin(a, b, prefix):
        """a and b joined by exactly one 2-pin part of this prefix: its value."""
        for r, (val, fp) in parts.items():
            if re.match(prefix + r'\d+$', r):
                if {node_net.get((r, '1')), node_net.get((r, '2'))} == {a, b}:
                    return val
        return None
    through_r = lambda a, b: two_pin(a, b, 'R')
    through_c = lambda a, b: two_pin(a, b, 'C')

    def through_rn(a, b):
        """a and b joined by one element of a 4-resistor array (pin k <-> pin 9-k): its value."""
        for r, (val, fp) in parts.items():
            if r.startswith('RN'):
                for k in range(1, 5):
                    if {node_net.get((r, str(k))), node_net.get((r, str(9 - k)))} == {a, b}:
                        return val
        return None

    def inv(a):
        for pa, py in INV6:
            if node_net.get((U14, str(pa))) == a:
                return node_net.get((U14, str(py)))
        return None

    def others(n, allowed):
        return [(r, pin) for (r, pin, f) in nets.get(n, []) if r not in allowed]

    edge = {p: node_net.get((J1, str(p))) for p in EDGE}
    sig = {}
    for p, s in EDGE.items():
        sig.setdefault(s, edge[p])
    v5 = func_net.get((S, 'VCC'))

    # ---- the firmware pin contract: a78_cart.h, a78map.h ----
    P = {k: define(CART, k + '_PIN') for k in ('D0', 'A0', 'RW', 'PHI2', 'HALT', 'PWROK', 'IRQ', 'AUDIO', 'LED',
                                               'SLOT', 'DBG_TX', 'DBG_RX')}
    bit = lambda m: define(MAP, m).bit_length() - 1
    page_bits = bin(define(MAP, 'A78S_PAGE_MASK')).count('1')
    slot_bits = define(MAP, 'A78S_BITS')
    chk('slot word: page bits 0-%d, then ROM_EN, RAM_EN, A8MASK, %d bits' % (page_bits - 1, slot_bits),
        (bit('A78S_ROM_EN'), bit('A78S_RAM_EN'), bit('A78S_A8MASK'), slot_bits) ==
        (page_bits, page_bits + 1, page_bits + 2, page_bits + 3) and define(MAP, 'A78S_PAGE_MASK') == (1 << page_bits) - 1)
    chk('page bits address 512K of 8K pages (SRAM A13-A18)', page_bits == 6 and define(MAP, 'A78MAP_PAGE_SIZE') == 0x2000)
    slot = {'SA%d' % (13 + i): P['SLOT'] + i for i in range(page_bits)}
    slot.update({'ROM_EN': P['SLOT'] + bit('A78S_ROM_EN'), 'RAM_EN': P['SLOT'] + bit('A78S_RAM_EN'),
                 'A8MASK': P['SLOT'] + bit('A78S_A8MASK')})
    claimed = list(range(P['D0'], P['D0'] + 8)) + list(range(P['A0'], P['A0'] + 16)) + \
        [P[k] for k in ('RW', 'PHI2', 'HALT', 'PWROK', 'IRQ', 'AUDIO', 'LED', 'DBG_TX', 'DBG_RX')] + \
        list(range(P['SLOT'], P['SLOT'] + slot_bits))
    chk('a78_cart.h claims no GPIO twice', len(claimed) == len(set(claimed)) and max(claimed) < 48)
    for g in range(48):
        if g in claimed:
            chk('GP%d is connected' % g, not unconn(rp(g)))
        else:
            chk('GP%d (not in a78_cart.h) is unconnected' % g, unconn(rp(g)))

    # ---- edge <-> RP2354B, straight through except D0-D7 (100R), /IRQ (2N7002), EAUDIO (RC) ----
    for p, s in EDGE.items():
        n = edge[p]
        if s == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
        elif s == '+5V':
            chk('J1.%d +5V is the console rail (not the cart logic rail)' % p, not unconn(n) and n != v5)
        elif s == '/IRQ':
            chk('J1.31 /IRQ = 2N7002 drain', n == func_net.get((QI, 'D')) and not unconn(n))
        elif s == 'EAUDIO':
            chk('J1.18 EAUDIO connected', not unconn(n))
        elif s == '/HALT':      # MARIA's weak MOS output: a series 10k at the finger, the RP behind it
            g = P[STROBE_PIN[s]]
            chk('J1.%d %s -> 10k -> GP%d' % (p, s, g), through_r(n, rp(g)) == '10k' and not unconn(n))
        elif s in STROBE_PIN:
            g = P[STROBE_PIN[s]]
            chk('J1.%d %s -> GP%d' % (p, s, g), n == rp(g) and not unconn(n))
        elif s.startswith('A'):
            g = P['A0'] + int(s[1:])
            chk('J1.%d %s -> GP%d' % (p, s, g), n == rp(g) and not unconn(n))
        elif s.startswith('D'):
            d = int(s[1:])
            g = P['D0'] + d
            chk('J1.%d %s -> 100R -> GP%d' % (p, s, g), through_rn(n, rp(g)) == '4x100R')
        else:
            chk('J1.%d %s: unexpected edge signal' % (p, s), False)
    chk('edge GND pins 14 and 30 are one net', edge[14] == edge[30] == 'GND')
    chk('the PIO table index (A0_PIN + 13..15, a78_pio.c) is the edge A13-A15',
        all(rp(P['A0'] + 13 + i) == sig['A%d' % (13 + i)] for i in range(3)))
    for s in ('R/W', 'PHI2') + tuple('A%d' % i for i in range(16)):
        chk('%s net carries no extra parts (no pull-ups, no series R; test pads allowed)' % s,
            not others(sig[s], {J1, U1, S} | glue | tps))
    rh = [r for r, _ in others(sig['/HALT'], {J1})]
    chk('/HALT at the finger: its 10k and nothing else (the console\'s HALT is a weak MOS output)',
        len(rh) == 1 and rh[0].startswith('R'))
    if len(rh) == 1:
        hr = rp(P['HALT'])
        chk('/HALT behind the 10k: the RP (observed, never driven) and a test pad only',
            not others(hr, {U1, rh[0]} | tps))
    chk('console A8 does not reach the SRAM directly', func_net.get((S, 'A8')) != sig['A8'])
    for i in range(8):
        chk('D%d net: edge, the SRAM, the series pack only' % i,
            not [r for r, _ in others(sig['D%d' % i], {J1, S}) if not r.startswith('RN')])
        chk('GP%d: RP and its series resistor only' % (P['D0'] + i),
            not [r for r, _ in others(rp(P['D0'] + i), {U1}) if not r.startswith('RN')])

    # ---- the RP's own outputs ----
    gate = rp(P['IRQ'])
    chk('GP%d (IRQ) -> 2N7002 gate, source GND' % P['IRQ'],
        gate == func_net.get((QI, 'G')) and func_net.get((QI, 'S')) == 'GND')
    chk('2N7002 gate pulled down (/IRQ released from power-on)', through_r(gate, 'GND') == '10k')
    led = one('red')
    chk('GP%d (LED) -> 1k -> LED anode, cathode GND' % P['LED'],
        led is not None and through_r(rp(P['LED']), node_net.get((led, '2'))) == '1k' and node_net.get((led, '1')) == 'GND')
    hdr = one('DBG UART')
    chk('GP%d DBG_TX -> header 1, GP%d DBG_RX -> header 2, header 3 GND' % (P['DBG_TX'], P['DBG_RX']),
        hdr is not None and node_net.get((hdr, '1')) == rp(P['DBG_TX']) and node_net.get((hdr, '2')) == rp(P['DBG_RX'])
        and node_net.get((hdr, '3')) == 'GND')
    # audio: GPIO -> R -> (C to GND) -> R -> C -> edge 18
    pwm = rp(P['AUDIO'])
    lp = next((n for n in nets if n != pwm and through_r(pwm, n)), None)
    r1 = through_r(pwm, lp)
    c1 = through_c(lp, 'GND')
    lvl = next((n for n in nets if n not in (pwm, lp) and through_r(lp, n)), None)
    cdc = through_c(lvl, edge[18]) if lvl else None
    chk('GP%d (AUDIO) -> R -> C to GND -> R -> C -> edge 18: low-pass %s / %s, level %s, DC block %s'
        % (P['AUDIO'], r1, c1, through_r(lp, lvl), cdc),
        None not in (lp, r1, c1, lvl, cdc))
    if r1 and c1:
        fc = 1 / (2 * math.pi * VAL(r1) * VAL(c1))
        chk('audio low-pass corner %.1f kHz within 5-20 kHz' % (fc / 1e3), 5e3 <= fc <= 20e3)
    real = lambda n: [x for x in nets.get(n, []) if x[0] not in tps]
    chk('audio nets carry nothing else (EAUDIO: a test pad allowed)', all(len(real(n)) == 2 for n in (lvl,)) and
        len(real(edge[18])) == 2 and len(real(pwm)) == 2 and len(real(lp)) == 3)

    # ---- SRAM: 512K, console address and data, the slot lines ----
    for i in range(13):
        if i != 8:
            chk('SRAM A%d = console A%d' % (i, i), func_net.get((S, 'A%d' % i)) == sig['A%d' % i])
    a8 = func_net.get((S, 'A8'))
    chk('SRAM A8 driven by a glue output',
        any(r in glue and N.ptype.get((r, pin)) == 'output' for (r, pin, _) in nets.get(a8, [])))
    for i in range(page_bits):
        g = slot['SA%d' % (13 + i)]
        chk('SRAM A%d = GP%d (slot word bit %d)' % (13 + i, g, i), func_net.get((S, 'A%d' % (13 + i))) == rp(g))
    for i in range(8):
        chk('SRAM DQ%d = console D%d' % (i, i), func_net.get((S, 'DQ%d' % i)) == sig['D%d' % i])
    chk('SRAM /CE tied active (GND)', func_net.get((S, '~{CE}')) == 'GND')
    chk('SRAM VCC on the cart 5V rail, VSS on GND', v5 not in (None, sig['+5V']) and func_net.get((S, 'VSS')) == 'GND')
    for f in ('~{OE}', '~{WE}'):
        n = func_net.get((S, f))
        chk('SRAM %s driven by a glue output' % f,
            any(r in glue and N.ptype.get((r, pin)) == 'output' for (r, pin, _) in nets.get(n, [])))
    glue_in = lambda n: any(r in glue and N.ptype.get((r, pin)) == 'input' for (r, pin, f) in nets.get(n, []))
    for k in ('ROM_EN', 'RAM_EN', 'A8MASK'):
        chk('GP%d (%s) -> a 74HCT glue input' % (slot[k], k), glue_in(rp(slot[k])))
    def pulldown(n):
        """refs of resistors from n to GND"""
        return {r for r, (v, _) in parts.items() if re.match(r'R\d+$', r) and
                {node_net.get((r, '1')), node_net.get((r, '2'))} == {n, 'GND'}}
    for k in ('ROM_EN', 'RAM_EN', 'A8MASK'):   # RP2350-E9 (stepping A2): an external pull-down <= 8.2k
        pd = pulldown(rp(slot[k]))
        chk('GP%d (%s) pulled down by <= 8.2k until the PIO table runs (RP2350-E9)' % (slot[k], k),
            len(pd) == 1 and VAL(parts[next(iter(pd))][0]) <= 8.2e3)
    for k, g in sorted(slot.items(), key=lambda kv: kv[1]):
        pd = pulldown(rp(g))
        bad = [(r, pin, N.ptype.get((r, pin))) for (r, pin, f) in nets.get(rp(g), [])
               if r != U1 and N.ptype.get((r, pin)) != 'input' and r not in pd]
        chk('GP%d (%s): drives only 5 V CMOS inputs (and its pull-down)' % (g, k),
            not bad and len(nets.get(rp(g), [])) >= 2)

    # ---- GPIO40-47 are not 5 V tolerant: 5 V-rail inputs or the 3.3 V debug header only ----
    for g in range(40, 48):
        n = rp(g)
        if unconn(n):
            continue
        bad = [(r, pin, N.ptype.get((r, pin))) for (r, pin, f) in nets.get(n, [])
               if r != U1 and N.ptype.get((r, pin)) != 'input' and r != hdr and r not in pulldown(n)]
        chk('GP%d (%s): nothing but inputs, its pull-down or the 3.3 V debug header on the net' % (g, n), not bad)
        chk('GP%d (%s): never an edge signal' % (g, n), n not in edge.values())

    # ---- PWR_OK: console +5V -> divider -> '14 -> '14 -> GP27 and the glue ----
    cons = sig['+5V']
    vsense = next((node_net.get((U14, str(pa))) for pa, py in INV6
                   if through_r(cons, node_net.get((U14, str(pa)))) is not None), None)
    chk("a '14 input is fed from edge +5V through a resistor (VSENSE)", vsense is not None)
    top, bot = through_r(cons, vsense), through_r(vsense, 'GND')
    chk('VSENSE divider to GND', top is not None and bot is not None)
    if top and bot:
        ratio = VAL(bot) / (VAL(top) + VAL(bot))
        chk('VSENSE ratio %.2f below the 74HCT14 input clamp with both sources present (<= 0.9)' % ratio, 0.5 <= ratio <= 0.9)
    pwr_ok = inv(inv(vsense))
    chk('PWR_OK = !!VSENSE on the Schmitt', pwr_ok is not None)
    chk('PWR_OK -> GP%d' % P['PWROK'], pwr_ok == rp(P['PWROK']))
    chk('PWR_OK -> the glue', glue_in(pwr_ok))
    for r in sorted(glue):
        chk('%s %s on the cart 5V rail' % (r, parts[r][0]), node_net.get((r, '14')) == v5 and node_net.get((r, '7')) == 'GND')

    # ---- power path ----
    vbus = node_net.get((one('USB-C'), 'A4'))
    chk('edge +5V -> P-FET drain, source = cart 5V rail, gate = VBUS',
        node_net.get((QFET, '3')) == cons and node_net.get((QFET, '2')) == v5 and node_net.get((QFET, '1')) == vbus)
    chk('VBUS -> SS34 -> cart 5V rail', any(val == 'SS34' and node_net.get((r, '2')) == vbus and node_net.get((r, '1')) == v5
                                            for r, (val, _) in parts.items()))
    chk('VBUS held low when unplugged (sense divider to GND)', through_r(vbus, node_net.get((UCP, '8'))) is not None)

    # ---- RP support: everything on the LDO rail ----
    v33io = func_net.get((U1, 'IOVDD'))
    chk('RP IOVDD rail is the LDO output, LDO fed from the 5V rail, EN = VIN',
        node_net.get((LDO, '5')) == v33io and node_net.get((LDO, '1')) == v5 and node_net.get((LDO, '3')) == v5)
    v_in = func_net.get((U1, 'VREG_VIN'))
    chk('RP VREG_VIN on the IOVDD rail', v_in == v33io)
    chk('VREG_AVDD from VREG_VIN through 33R', through_r(v_in, func_net.get((U1, 'VREG_AVDD'))) == '33R')
    v33 = func_net.get((S3, '3V3'))
    chk('S3 3V3 is the buck rail, not the LDO', v33 not in (v33io, v5, None))
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((S3, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((S3, 'USB_D-'))) == '27R')
    print('note: S3 pins from %s' % PINMAP)
    run_io, bsel_io = define(PINMAP, 'PIN_RP2040_RUN', -2), define(PINMAP, 'PIN_RP2040_BOOTSEL', -2)
    if run_io == -2 or bsel_io == -2:
        run_io, bsel_io = define(PINMAP_RUN, 'PIN_RP2040_RUN'), define(PINMAP_RUN, 'PIN_RP2040_BOOTSEL')
        print('note: %s does not define PIN_RP2040_RUN/BOOTSEL; using fujiversal-intv.h (IO%d/IO%d)'
              % (os.path.basename(PINMAP), run_io, bsel_io))
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (PIN_RP2040_RUN) -> 1k -> RP RUN' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (PIN_RP2040_BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up to the IO rail', through_r(run, v33io) == '10k')
    chk('QSPI_SS pull-up to the IO rail', through_r(ss, v33io) == '10k')
    for f in ('QSPI_SCLK', 'QSPI_SD0', 'QSPI_SD1', 'QSPI_SD2', 'QSPI_SD3'):
        chk('RP %s unconnected (flash is in the package)' % f, unconn(func_net.get((U1, f))))
    for n, nodes in nets.items():
        for (ref, pin, f) in nodes:
            if ref == U1 and f in ('IOVDD', 'QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN'):
                chk('RP %s (pin %s) on %s' % (f, pin, v33io), n == v33io)
            if ref == U1 and f == 'DVDD':
                chk('RP DVDD (pin %s) on DVDD' % pin, n == func_net.get((U1, 'VREG_FB')))
            if ref == U1 and f in ('GND', 'VREG_PGND'):
                chk('RP %s (pin %s) on GND' % (f, pin), n == 'GND')
    for f in ('SWCLK', 'SWDIO', 'RUN'):
        chk('RP %s on a test pad' % f, any(r.startswith('TP') for (r, _, _) in nets.get(func_net.get((U1, f)), [])))

    # ---- S3 pins: the pinmap ----
    sd = {k: define(PINMAP, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(PINMAP, 'PIN_LED_STRIP')
    uart_rx, uart_tx = define(PINMAP, 'PIN_UART0_RX'), define(PINMAP, 'PIN_UART0_TX')
    card = define(PINMAP, 'PIN_CARD_DETECT', -1)
    chk('SD CS  IO%d -> microSD DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((J2, '2')))
    chk('SD MOSI IO%d -> microSD CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((J2, '3')))
    chk('SD SCK IO%d -> microSD CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((J2, '5')))
    chk('SD MISO IO%d -> microSD DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((J2, '7')))
    chk('microSD VDD on the S3 rail, VSS on GND', node_net.get((J2, '4')) == v33 and node_net.get((J2, '6')) == 'GND')
    cd = node_net.get((J2, '9'))
    cd_io = next((int(f[2:]) for (r, pin, f) in nets.get(cd, []) if r == S3 and f.startswith('IO')), None)
    if card >= 0:
        chk('microSD card-detect -> IO%d (PIN_CARD_DETECT)' % card, cd_io == card)
    else:
        print('note: %s leaves PIN_CARD_DETECT NC; the board wires card-detect to IO%s '
              '(pulled up) as the NES / SMS boards do, unused by the firmware' % (os.path.basename(PINMAP), cd_io))
    ws_din = node_net.get((WS, '3'))
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), ws_din) is not None)
    chk('PIN_UART0_TX/RX are the module TXD0/RXD0 pads (GPIO43/44)', (uart_tx, uart_rx) == (43, 44))
    chk('S3 TXD0 -> CP2102N RXD', func_net.get((S3, 'TXD0')) == func_net.get((UCP, 'RXD')))
    chk('S3 RXD0 <- CP2102N TXD', func_net.get((S3, 'RXD0')) == func_net.get((UCP, 'TXD')))
    # every S3 IO the board uses is one the contract names
    contract = set(sd.values()) | {led_strip, run_io, bsel_io, 19, 20, 0} | ({card} if card >= 0 else {cd_io})
    for (r, f), n in sorted(func_net.items()):
        if r == S3 and re.match(r'IO\d+$', f) and not unconn(n):
            chk('S3 %s (%s) is in the pin contract' % (f, n), int(f[2:]) in contract)
    for io in (3, 45, 46):
        chk('S3 strapping IO%d unloaded' % io, unconn(s3(io)))
    for io in range(26, 38):
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, unconn(s3(io)))

    # ---- edge footprint: 18 positions at 2.54 mm with key slots at positions 3 and 16; pins 1-16
    # F.Cu (component side, console rear), 17-32 B.Cu, k over 33-k, pin 1 left (audit/edge_orientation.py
    # holds the sources) ----
    from sexpr import parse as sparse, findall as sfindall, find as sfind
    fpe = sparse(open(os.path.join(PRJ, 'FujiNet-7800.pretty', 'Atari7800_Cart_Edge_32.kicad_mod')).read())
    pads = {int(p[1]): (float(sfind(p, 'at')[1]), sfind(p, 'layers')[1][0]) for p in sfindall(fpe, 'pad')}
    chk('edge footprint has 32 pads', sorted(pads) == list(range(1, 33)))
    if sorted(pads) == list(range(1, 33)):
        chk('edge: pins 1-16 on F.Cu, 17-32 on B.Cu, pin k over pin 33-k',
            all(pads[k][1] == 'F' and pads[33 - k][1] == 'B' and pads[k][0] == pads[33 - k][0] for k in range(1, 17)))
        steps = [round(pads[k + 1][0] - pads[k][0], 3) for k in range(1, 16)]
        chk('edge: 2.54 mm pitch with a key position (5.08 mm step) between pins 2-3 and 14-15, '
            'pin 1 at the left (-x)', steps == [2.54, 5.08] + [2.54] * 11 + [5.08, 2.54] and pads[1][0] < 0 < pads[16][0])
        chk('edge: 2600 pins in the middle (7800 pins 3-14 centred)', abs(pads[3][0] + pads[14][0]) < 1e-6)

    # ---- general ----
    for n, nodes in nets.items():
        if not unconn(n):
            chk('net %s has >= 2 pins' % n, len(nodes) >= 2)

    # ---- the 48-GPIO table, for the record ----
    pin_of = {f: pin for (ref, pin, f) in sum(nets.values(), []) if ref == U1}
    edge_of = {}
    for p, s in EDGE.items():
        edge_of.setdefault(edge[p], []).append('J1.%d %s' % (p, s))
    print('%-6s %-4s %-10s %s' % ('GPIO', 'pin', 'net', 'also on'))
    for g in range(48):
        n = rp(g)
        f = next(f for f in pin_of if re.match(r'GPIO%d(/|$)' % g, f))
        if unconn(n):
            print('GP%-4d %-4s %-10s' % (g, pin_of[f], '-'))
            continue
        more = edge_of.get(n, []) + ['%s.%s' % (r, fn or pin) for (r, pin, fn) in nets.get(n, []) if r not in (U1, J1)]
        print('GP%-4d %-4s %-10s %s' % (g, pin_of[f], n, ', '.join(more)))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
