#!/usr/bin/env python3
"""Cross-check the FujiNet-NES Rev1 schematic netlist against the firmware
that has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from fujinet-firmware
(default ~/Workspace/fujinet-firmware, or $FUJINET_FIRMWARE):
  pico/nes/firmware/include/nes_bus.h      CPU bus pins (RP-A)
  pico/nes/firmware/include/nes_cart.h     RP-A: PWR_OK, LED, /IRQ, the link, RP-B's SWD/RUN, PA12
  pico/nes/firmware/include/nes_ppu.h      RP-B: PPU bus, CIRAM, the link, PWR_OK, VSENSE
  include/pinmap/fujiversal-nes.h          S3 SD / LED / UART pins
  include/pinmap/fujiversal-intv.h         PIN_RP2040_RUN/BOOTSEL, until the
                                           NES pinmap defines them itself
and checks every one of them against the nesdev 72-pin edge map and the pin
*functions* the netlist reports (GPIOn on each RP2354B, IOn on the S3).  The
two RPs are told apart by their buses (RP-A: GPIO CA0_PIN on CPU A0; RP-B:
GPIO PA0_PIN on PPU A0).  Also checks the link (RP-B's LD pins mirrored, as
nes_link.h says), each RP on its own LDO, the PWR_OK divider against the
RP2350's pad limits, and reads the edge footprint to assert pin 1 is east on
F.Cu (nesdev: label side, fingers down, 36..1 left to right).

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
SCH = os.path.join(PRJ, 'FujiNet-NES-Rev1.kicad_sch')

# nesdev wiki, "Cartridge connector", 72-pin NES.  Pin N and N+36 share a position.
EDGE = {1: 'GND', 2: 'A11', 3: 'A10', 4: 'A9', 5: 'A8', 6: 'A7', 7: 'A6', 8: 'A5', 9: 'A4',
        10: 'A3', 11: 'A2', 12: 'A1', 13: 'A0', 14: 'R/W', 15: '/IRQ', 16: 'EXP0', 17: 'EXP1',
        18: 'EXP2', 19: 'EXP3', 20: 'EXP4', 21: 'PPU /RD', 22: 'CIRAM A10', 23: 'PA6', 24: 'PA5',
        25: 'PA4', 26: 'PA3', 27: 'PA2', 28: 'PA1', 29: 'PA0', 30: 'PD0', 31: 'PD1', 32: 'PD2',
        33: 'PD3', 34: 'CIC toPak', 35: 'CIC toMB', 36: '+5V', 37: 'SYSTEM CLK', 38: 'M2',
        39: 'A12', 40: 'A13', 41: 'A14', 42: 'D7', 43: 'D6', 44: 'D5', 45: 'D4', 46: 'D3',
        47: 'D2', 48: 'D1', 49: 'D0', 50: '/ROMSEL', 51: 'EXP9', 52: 'EXP8', 53: 'EXP7',
        54: 'EXP6', 55: 'EXP5', 56: 'PPU /WR', 57: 'CIRAM /CE', 58: 'PPU /A13', 59: 'PA7',
        60: 'PA8', 61: 'PA9', 62: 'PA11', 63: 'PA10', 64: 'PA12', 65: 'PA13', 66: 'PD7',
        67: 'PD6', 68: 'PD5', 69: 'PD4', 70: 'CIC +RST', 71: 'CIC CLK', 72: 'GND'}
UNUSED = ('EXP', 'SYSTEM CLK', 'PPU /A13')   # /A13: RP-B decodes PA13 itself
CIC = {'CIC toPak': 'PB1', 'CIC toMB': 'PB0', 'CIC +RST': 'PB2', 'CIC CLK': 'PB3'}   # avrciczz pin map

fails = 0
count = 0


def chk(desc, ok):
    global fails, count
    count += 1
    if not ok:
        fails += 1
        print('FAIL:', desc)


def define(path, name, default=None):
    txt = open(os.path.join(FW, path)).read()
    m = re.search(r'#define\s+%s\s+(\S+)' % re.escape(name), txt)
    if not m:
        if default is not None:
            return default
        raise SystemExit('%s: no #define %s' % (path, name))
    v = m.group(1)
    m2 = re.match(r'GPIO_NUM_(\d+)', v)
    if m2:
        return int(m2.group(1))
    return int(v.rstrip('uUlL'), 0)


def ohms(s):
    return float(s.replace('k', 'e3').replace('R', ''))


def main():
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-nes-check.xml')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn, SCH],
                   check=True, capture_output=True)
    t = ET.parse(fn)
    node_net, func_net, nets = {}, {}, {}
    for n in t.iter('net'):
        name = n.get('name')
        for nd in n.iter('node'):
            ref, pin, fn_ = nd.get('ref'), nd.get('pin'), (nd.get('pinfunction') or '')
            fn_ = re.sub(r'_%s$' % re.escape(pin), '', fn_)   # kicad-cli appends _<pin> to repeats
            node_net[(ref, pin)] = name
            func_net[(ref, fn_)] = name
            nets.setdefault(name, []).append((ref, pin, fn_))
    parts = {c.get('ref'): (c.findtext('value'), c.findtext('footprint')) for c in t.iter('comp')}
    by_value = lambda v: sorted(r for r, (val, _) in parts.items() if val == v)
    one = lambda v: (by_value(v) or [None])[0]
    unconn = lambda n: n is None or n.startswith('unconnected')
    on_tp = lambda n: n is not None and any(r.startswith('TP') for (r, _, _) in nets.get(n, []))

    J1 = one('NES_Cart_Edge_72')
    S3 = one('ESP32-S3-WROOM-1-N16R8')
    J2 = one('microSD')
    UCP = one('CP2102N-A02-GQFN28')
    WS = one('WS2812B-2020-V6')
    QFET, CIC_U = one('AO3401A'), one('ATtiny13A-SSU')
    rps, ldos = by_value('RP2354B'), by_value('AP2112K-3.3')
    for ref, what in ((J1, 'edge'), (S3, 'ESP32-S3'), (QFET, 'AO3401A'), (CIC_U, 'CIClone')):
        if ref is None:
            raise SystemExit('no %s in the netlist' % what)
    if len(rps) != 2 or len(ldos) != 2:
        raise SystemExit('expected two RP2354B and two AP2112K-3.3, found %r %r' % (rps, ldos))
    for gone in ('AS6C4008-55TIN', '74HCT595', '74HCT253', '74HCT14', '74HCT00', '74HCT32', '74HCT20'):
        chk('no %s (Rev1 has no SRAM and no glue)' % gone, not by_value(gone))

    def rp(ref, gpio):
        for (r, f), n in func_net.items():
            if r == ref and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((S3, 'IO%d' % io))

    def through_r(a, b):
        """a and b joined by exactly one 2-pin resistor: its value."""
        for r, (val, fp) in parts.items():
            if r.startswith('R') and not r.startswith('RN'):
                ends = {node_net.get((r, '1')), node_net.get((r, '2'))}
                if ends == {a, b}:
                    return val
        return None

    edge = {p: node_net.get((J1, str(p))) for p in EDGE}
    sig = {s: edge[p] for p, s in EDGE.items()}        # signal name -> net (GND: last wins)

    # ---- firmware pin contracts ----
    bus, cart, ppu = ('pico/nes/firmware/include/%s.h' % h for h in ('nes_bus', 'nes_cart', 'nes_ppu'))
    A = {k: define(bus, k + '_PIN') for k in ('CA0', 'CD0', 'M2', 'RW', 'ROMSEL', 'CA13')}
    A.update({k: define(cart, k + '_PIN') for k in ('PWROK', 'LED', 'IRQ', 'LACK', 'LD0', 'LCLK', 'LFRM',
                                                    'RPB_SWCLK', 'RPB_SWDIO', 'RPB_RUN', 'PA12')})
    B = {k: define(ppu, k + '_PIN') for k in ('PA0', 'PD0', 'PPU_RD', 'PPU_WR', 'PPU_PWROK', 'CIRAM_A10',
                                              'CIRAM_CE', 'RPB_LFRM', 'RPB_LCLK', 'RPB_LD7', 'RPB_LACK', 'VSENSE')}
    pm = 'include/pinmap/fujiversal-nes.h'
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    uart_rx, uart_tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN', -1), define(pm, 'PIN_RP2040_BOOTSEL', -1)
    if run_io < 0 or bsel_io < 0:
        alt = 'include/pinmap/fujiversal-intv.h'
        run_io, bsel_io = define(alt, 'PIN_RP2040_RUN'), define(alt, 'PIN_RP2040_BOOTSEL')
        print('note: %s does not define PIN_RP2040_RUN/BOOTSEL yet; using %s (IO%d/IO%d)' % (pm, alt, run_io, bsel_io))
    # every GPIO each header claims, once
    use_a = ([A['CA0'] + i for i in range(13)] + [A['CD0'] + i for i in range(8)] + [A['CA13'], A['CA13'] + 1] +
             [A['LD0'] + i for i in range(8)] +
             [A[k] for k in ('M2', 'RW', 'ROMSEL', 'PWROK', 'LED', 'IRQ', 'LACK', 'LCLK', 'LFRM',
                             'RPB_SWCLK', 'RPB_SWDIO', 'RPB_RUN', 'PA12')])
    use_b = ([B['PA0'] + i for i in range(14)] + [B['PD0'] + i for i in range(8)] + [B['RPB_LD7'] + i for i in range(8)] +
             [B[k] for k in ('PPU_RD', 'PPU_WR', 'PPU_PWROK', 'CIRAM_A10', 'CIRAM_CE', 'RPB_LFRM', 'RPB_LCLK',
                             'RPB_LACK', 'VSENSE')])
    for who, use in (('nes_bus.h + nes_cart.h (RP-A)', use_a), ('nes_ppu.h (RP-B)', use_b)):
        dup = sorted({g for g in use if use.count(g) > 1})
        chk('%s: no GPIO assigned twice %s' % (who, dup or ''), not dup)
        chk('%s: every GPIO in 0..47' % who, all(0 <= g < 48 for g in use))

    # ---- which RP is which: by the bus on its GPIOs ----
    UA = next((r for r in rps if rp(r, A['CA0']) == sig['A0'] and not unconn(sig['A0'])), None)
    UB = next((r for r in rps if rp(r, B['PA0']) == sig['PA0'] and not unconn(sig['PA0'])), None)
    if UA is None or UB is None or UA == UB:
        raise SystemExit('cannot tell RP-A (CPU A0 on GP%d) from RP-B (PPU A0 on GP%d): %r %r'
                         % (A['CA0'], B['PA0'], UA, UB))
    print('RP-A = %s, RP-B = %s' % (UA, UB))
    ra = lambda g: rp(UA, g)
    rb = lambda g: rp(UB, g)

    # ---- edge -> the two RPs, straight through (5V-tolerant pads, no buffers) ----
    for p, s in EDGE.items():
        n = edge[p]
        if s == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
        elif s.startswith(UNUSED):
            chk('J1.%d %s unconnected' % (p, s), unconn(n))
        elif s in CIC:
            chk('J1.%d %s -> CIClone %s' % (p, s, CIC[s]), n == func_net.get((CIC_U, CIC[s])) and not unconn(n))
        elif s == '+5V':
            chk('J1.36 +5V connected', not unconn(n))
        elif s == 'R/W':
            chk('J1.14 R/W -> RP-A GP%d' % A['RW'], n == ra(A['RW']))
        elif s == '/IRQ':
            chk('J1.15 /IRQ -> RP-A GP%d' % A['IRQ'], n == ra(A['IRQ']))
        elif s == 'M2':
            chk('J1.38 M2 -> RP-A GP%d' % A['M2'], n == ra(A['M2']))
        elif s == '/ROMSEL':
            chk('J1.50 /ROMSEL -> RP-A GP%d' % A['ROMSEL'], n == ra(A['ROMSEL']))
        elif s == 'PPU /RD':
            chk('J1.21 PPU /RD -> RP-B GP%d' % B['PPU_RD'], n == rb(B['PPU_RD']))
        elif s == 'PPU /WR':
            chk('J1.56 PPU /WR -> RP-B GP%d' % B['PPU_WR'], n == rb(B['PPU_WR']))
        elif s == 'CIRAM A10':
            chk('J1.22 CIRAM A10 <- RP-B GP%d' % B['CIRAM_A10'], n == rb(B['CIRAM_A10']))
        elif s == 'CIRAM /CE':
            chk('J1.57 CIRAM /CE <- RP-B GP%d' % B['CIRAM_CE'], n == rb(B['CIRAM_CE']))
        elif s.startswith('PA'):
            a = int(s[2:])
            chk('J1.%d PPU %s -> RP-B GP%d' % (p, s, B['PA0'] + a), n == rb(B['PA0'] + a))
        elif s.startswith('PD'):
            d = int(s[2:])
            chk('J1.%d PPU %s -> RP-B GP%d' % (p, s, B['PD0'] + d), n == rb(B['PD0'] + d))
        elif s.startswith('A'):
            a = int(s[1:])
            g = A['CA0'] + a if a <= 12 else A['CA13'] + a - 13
            chk('J1.%d CPU %s -> RP-A GP%d' % (p, s, g), n == ra(g))
        else:
            d = int(s[1:])
            chk('J1.%d CPU %s -> RP-A GP%d' % (p, s, A['CD0'] + d), n == ra(A['CD0'] + d))
    chk('PPU A12 also -> RP-A GP%d (MMC3 scanline filter)' % A['PA12'], sig['PA12'] == ra(A['PA12']))
    chk('/IRQ net has only J1 and RP-A (the console holds the pull-up)',
        all(r in (J1, UA) for (r, _, _) in nets.get(sig['/IRQ'], [])))
    chk('M2 on a test pad', on_tp(sig['M2']))
    # the bus touches only the edge, the RPs and test pads
    for p, s in EDGE.items():
        if s in ('GND', '+5V') or s.startswith(UNUSED) or s in CIC:
            continue
        others = [(r, pin) for (r, pin, f) in nets.get(edge[p], []) if r not in (J1, UA, UB) and not r.startswith('TP')]
        chk('J1.%d %s net carries no extra parts (no pull-ups, no series R)' % (p, s), not others)

    # ---- the link: RP-A LD0-7 out, RP-B's pins mirrored (LD7 first), LCLK/LFRM out, LACK back ----
    for i in range(8):
        n = ra(A['LD0'] + i)
        chk('LD%d: RP-A GP%d = RP-B GP%d' % (i, A['LD0'] + i, B['RPB_LD7'] + 7 - i),
            not unconn(n) and n == rb(B['RPB_LD7'] + 7 - i))
    for what, ga, gb in (('LCLK', A['LCLK'], B['RPB_LCLK']), ('LFRM', A['LFRM'], B['RPB_LFRM']),
                         ('LACK', A['LACK'], B['RPB_LACK'])):
        n = ra(ga)
        chk('%s: RP-A GP%d = RP-B GP%d, point to point' % (what, ga, gb),
            not unconn(n) and n == rb(gb) and all(r in (UA, UB) for (r, _, _) in nets[n]))
    for i in range(8):
        n = ra(A['LD0'] + i)
        chk('LD%d point to point' % i, n is not None and all(r in (UA, UB) for (r, _, _) in nets.get(n, [])))

    # ---- RP-B's SWD and RUN, from RP-A ----
    for what, g, f in (('SWCLK', A['RPB_SWCLK'], 'SWCLK'), ('SWDIO', A['RPB_SWDIO'], 'SWDIO'),
                       ('RUN', A['RPB_RUN'], 'RUN')):
        n = ra(g)
        chk('RP-A GP%d -> RP-B %s' % (g, f), not unconn(n) and n == func_net.get((UB, f)))
        chk('RP-B %s on a test pad' % f, on_tp(func_net.get((UB, f))))

    # ---- PWR_OK: console +5V (edge 36, before the P-FET) -> divider -> both RPs ----
    cons = sig['+5V']
    v5 = node_net.get((QFET, '2'))
    chk('edge +5V is not the logic 5V rail (P-FET / diode OR in between)', cons != v5 and not unconn(cons))
    vbus = node_net.get((one('USB-C'), 'A4'))
    chk('edge +5V -> P-FET drain, source = logic 5V rail, gate = VBUS',
        node_net.get((QFET, '3')) == cons and node_net.get((QFET, '1')) == vbus and not unconn(v5))
    chk('VBUS -> SS34 -> logic 5V rail',
        any(val == 'SS34' and node_net.get((r, '2')) == vbus and node_net.get((r, '1')) == v5
            for r, (val, _) in parts.items()))
    chk('VBUS held low when unplugged (sense divider to GND)', through_r(vbus, node_net.get((UCP, '8'))) is not None)
    pok = ra(A['PWROK'])
    chk('PWR_OK: RP-A GP%d = RP-B GP%d = RP-B GP%d (VSENSE)' % (A['PWROK'], B['PPU_PWROK'], B['VSENSE']),
        not unconn(pok) and pok == rb(B['PPU_PWROK']) == rb(B['VSENSE']))
    vs_f = next((f for (r, f) in func_net if r == UB and re.match(r'GPIO%d/' % B['VSENSE'], f)), '')
    chk('RP-B GP%d (VSENSE) is an ADC pin (%s)' % (B['VSENSE'], vs_f), 'ADC' in vs_f)
    top, bot = through_r(cons, pok), through_r(pok, 'GND')
    chk('PWR_OK divider: edge +5V -> R -> PWR_OK -> R -> GND', top is not None and bot is not None)
    if top and bot:
        rt, rb_ = ohms(top), ohms(bot)
        ratio, zsrc = rb_ / (rt + rb_), rt * rb_ / (rt + rb_)
        chk('PWR_OK ratio %.2f in 0.55..0.65' % ratio, 0.55 <= ratio <= 0.65)
        # RP2350 datasheet: a 5V-tolerant pad takes 3.63 V max while IOVDD is off;
        # VIH = 0.65 x IOVDD (2.15 V at 3.3 V) must be met by a 4.5 V console
        chk('PWR_OK at a 5.5 V console = %.2f V <= 3.63 V (FT pad, IOVDD off)' % (5.5 * ratio), 5.5 * ratio <= 3.63)
        chk('PWR_OK at a 4.5 V console = %.2f V >= VIH 2.15 V' % (4.5 * ratio), 4.5 * ratio >= 2.15)
        chk('PWR_OK source impedance %.0f R and bottom %s <= 8.2k (RP2350-E9)' % (zsrc, bot), zsrc <= 8200 and rb_ <= 8200)
    chk('PWR_OK net has only the divider and the two RPs',
        all(r in (UA, UB) or r.startswith('R') for (r, _, _) in nets.get(pok, [])))

    # ---- each RP on its own LDO; supplies, core regulator, crystal, QSPI ----
    rail = {}
    for who, U, ldo_want in (('RP-A', UA, None), ('RP-B', UB, None)):
        v = func_net.get((U, 'IOVDD'))
        rail[who] = v
        ldo = next((l for l in ldos if node_net.get((l, '5')) == v), None)
        chk('%s IOVDD rail %s is an AP2112K output' % (who, v), ldo is not None and v not in (v5, None))
        if ldo:
            chk('%s LDO %s fed from the logic 5V rail, EN = VIN' % (who, ldo),
                node_net.get((ldo, '1')) == v5 and node_net.get((ldo, '3')) == v5 and node_net.get((ldo, '2')) == 'GND')
            chk('%s LDO %s output carries only %s\'s supplies, its caps and its pull-ups' % (who, ldo, who),
                all(r in (U, ldo) or r[0] in 'CR' or r.startswith('TP') for (r, _, _) in nets[v]))
        dv = func_net.get((U, 'VREG_FB'))
        for n, nodes in nets.items():   # every supply pin (names repeat: IOVDD x8, DVDD x3)
            for (ref, pin, f) in nodes:
                if ref != U:
                    continue
                if f in ('IOVDD', 'QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN'):
                    chk('%s %s (pin %s) on %s' % (who, f, pin, v), n == v)
                if f == 'DVDD':
                    chk('%s DVDD (pin %s) on its VREG_FB net' % (who, pin), n == dv)
                if f in ('GND', 'VREG_PGND'):
                    chk('%s %s (pin %s) on GND' % (who, f, pin), n == 'GND')
        chk('%s VREG_AVDD from its rail through 33R' % who, through_r(v, func_net.get((U, 'VREG_AVDD'))) == '33R')
        lx = func_net.get((U, 'VREG_LX'))
        chk('%s VREG_LX -> 3.3uH -> DVDD' % who,
            any(r.startswith('L') and val == '3.3uH' and {node_net.get((r, '1')), node_net.get((r, '2'))} == {lx, dv}
                for r, (val, _) in parts.items()))
        xin, xout = func_net.get((U, 'XIN')), func_net.get((U, 'XOUT'))
        y = next((r for r in by_value('12MHz') if node_net.get((r, '1')) == xin), None)
        chk('%s XIN -> 12 MHz crystal pin 1' % who, y is not None)
        if y:
            chk('%s XOUT -> 1k -> crystal pin 3' % who, through_r(xout, node_net.get((y, '3'))) == '1k')
        for f in ('QSPI_SCLK', 'QSPI_SD0', 'QSPI_SD1', 'QSPI_SD2', 'QSPI_SD3'):
            chk('%s %s unconnected (flash is in the package)' % (who, f), unconn(func_net.get((U, f))))
        chk('%s RUN pull-up 10k to its rail' % who, through_r(func_net.get((U, 'RUN')), v) == '10k')
        chk('%s QSPI_SS pull-up 10k to its rail' % who, through_r(func_net.get((U, '~{QSPI_SS}')), v) == '10k')
    chk('RP-A and RP-B on different LDOs', rail['RP-A'] != rail['RP-B'])
    v33 = func_net.get((S3, '3V3'))
    chk('S3 3V3 is the buck rail, not an RP LDO', v33 not in (rail['RP-A'], rail['RP-B'], v5, None))

    # ---- RP-A only: USB to the S3, the S3's RUN / BOOTSEL, the LED, SWD pads ----
    chk('RP-A USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((UA, 'USB_DP')), func_net.get((S3, 'USB_D+'))) == '27R')
    chk('RP-A USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((UA, 'USB_DM')), func_net.get((S3, 'USB_D-'))) == '27R')
    run, ss = func_net.get((UA, 'RUN')), func_net.get((UA, '~{QSPI_SS}'))
    chk('S3 IO%d (PIN_RP2040_RUN) -> 1k -> RP-A RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (PIN_RP2040_BOOTSEL) -> 1k -> RP-A QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    for f in ('SWCLK', 'SWDIO', 'RUN'):
        chk('RP-A %s on a test pad' % f, on_tp(func_net.get((UA, f))))
    led = next((r for r in parts if r.startswith('D') and parts[r][1].endswith('LED_0603_1608Metric')), None)
    chk('RP-A GP%d -> 330R -> LED anode, cathode to GND' % A['LED'],
        led is not None and through_r(ra(A['LED']), node_net.get((led, '2'))) == '330R' and node_net.get((led, '1')) == 'GND')
    chk('LED is a low-Vf part (not the 3.1 V KT-0603G green)', led is not None and parts[led][0] != 'green')
    # ---- RP-B only: no USB, QSPI_SS only pulled up (it never boots its flash) ----
    for f in ('USB_DP', 'USB_DM'):
        chk('RP-B %s unconnected' % f, unconn(func_net.get((UB, f))))
    ssb = func_net.get((UB, '~{QSPI_SS}'))
    chk('RP-B QSPI_SS: only its pull-up', all(r == UB or r.startswith('R') for (r, _, _) in nets.get(ssb, [])))

    # ---- S3 pins ----
    chk('SD CS  IO%d -> J2 DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((J2, '2')))
    chk('SD MOSI IO%d -> J2 CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((J2, '3')))
    chk('SD SCK IO%d -> J2 CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((J2, '5')))
    chk('SD MISO IO%d -> J2 DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((J2, '7')))
    chk('J2 VDD on %s, VSS on GND' % v33, node_net.get((J2, '4')) == v33 and node_net.get((J2, '6')) == 'GND')
    ws_din = node_net.get((WS, '3'))
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), ws_din) is not None)
    chk('PIN_UART0_TX/RX are the module TXD0/RXD0 pads (GPIO43/44)', (uart_tx, uart_rx) == (43, 44))
    chk('S3 TXD0 -> CP2102N RXD', func_net.get((S3, 'TXD0')) == func_net.get((UCP, 'RXD')))
    chk('S3 RXD0 <- CP2102N TXD', func_net.get((S3, 'RXD0')) == func_net.get((UCP, 'TXD')))
    for io in (3, 45, 46):
        chk('S3 strapping IO%d unloaded' % io, unconn(s3(io)))
    for io in range(26, 38):
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, unconn(s3(io)))

    # ---- CIClone (DNP): console-powered, resets with it; /RESET on a pad ----
    chk('CIClone VCC on edge +5V (CONS_5V), GND on GND',
        func_net.get((CIC_U, 'VCC')) == cons and func_net.get((CIC_U, 'GND')) == 'GND')
    chk('CIClone /RESET on a test pad', any(r.startswith('TP') for (r, _, _) in nets.get(func_net.get((CIC_U, '~{RESET}/PB5')), [])))

    # ---- edge footprint orientation, from the footprint file itself ----
    fpt = open(os.path.join(PRJ, 'FujiNet-NES.pretty', 'NES_Cart_Edge_72.kicad_mod')).read()
    pads = {m.group(1): (float(m.group(2)), m.group(3)) for m in
            re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) [-\d.]+\)\s*\(size [^)]*\)\s*\(layers "([FB])\.Cu"\)', fpt)}
    chk('edge footprint has 72 pads', len(pads) == 72)
    chk('edge pad 1 east (+x) on F.Cu, pad 36 west, pad 37 under pad 1 on B.Cu (nesdev: label side reads 36..1)',
        pads.get('1', (0, ''))[0] > 0 and pads['1'][1] == 'F' and pads['36'][0] < 0 and pads['36'][1] == 'F'
        and pads['37'][0] == pads['1'][0] and pads['37'][1] == 'B' and pads['72'][1] == 'B')
    chk('edge pitch 2.50 mm (pads 2-3); 3.0 mm end pad sits 0.5 mm further out (pads 1-2 = 3.0)',
        abs((pads['2'][0] - pads['3'][0]) - 2.5) < 1e-6 and abs((pads['1'][0] - pads['2'][0]) - 3.0) < 1e-6)

    # ---- general ----
    for n, nodes in nets.items():
        if not n.startswith('unconnected'):
            chk('net %s has >= 2 pins' % n, len(nodes) >= 2)

    # ---- the GPIO tables, for the record ----
    edge_of = {}
    for p, s in EDGE.items():
        edge_of.setdefault(edge[p], []).append('J1.%d %s' % (p, s))
    for who, U in (('RP-A', UA), ('RP-B', UB)):
        pin_of = {f: pin for (ref, pin, f) in sum(nets.values(), []) if ref == U}
        print('%s (%s)\n%-6s %-4s %-12s %s' % (who, U, 'GPIO', 'pin', 'net', 'also on'))
        for g in range(48):
            n = rp(U, g)
            f = next(f for f in pin_of if re.match(r'GPIO%d(/|$)' % g, f))
            others = edge_of.get(n, []) + ['%s.%s' % (r, fn or pin) for (r, pin, fn) in nets.get(n, [])
                                           if r not in (U, J1)] if not unconn(n) else []
            print('GP%-4d %-4s %-12s %s' % (g, pin_of[f], '-' if unconn(n) else n, ', '.join(others)))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
