#!/usr/bin/env python3
"""Cross-check the FujiNet-NES Rev0 schematic netlist against the firmware
that has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from fujinet-firmware
(default ~/Workspace/fujinet-firmware, or $FUJINET_FIRMWARE):
  pico/nes/firmware/include/nes_cart.h     *_PIN GPIO numbers, SR_* '595 bits
  include/pinmap/fujiversal-nes.h          S3 SD / LED / UART pins
  include/pinmap/fujiversal-intv.h         PIN_RP2040_RUN/BOOTSEL, until the
                                           NES pinmap defines them itself
and checks every one of them, plus the nesdev 72-pin edge map and the decode
equations of pico/nes/README.md, against the pin *functions* the netlist
reports (GPIOn on the RP2354B, IOn on the S3, An/DQn on the SRAMs, QA..QH
on the '595) -- gate by gate for the 74HCT glue.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
SCH = os.path.join(PRJ, 'FujiNet-NES-Rev0.kicad_sch')

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
UNUSED = ('EXP', 'CIC', 'SYSTEM CLK')
GATES4 = [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]          # 74xx00/08/32
INV6 = [(1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12)]          # 74xx14

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

    U1 = one('RP2354B')
    J1 = one('NES_Cart_Edge_72')
    U2 = one('ESP32-S3-WROOM-1-N16R8')
    J2 = one('microSD')
    UCP = one('CP2102N-A02-GQFN28')
    WS = one('WS2812B-2020-V6')
    U595, U253, U14, U00, U32 = (one(v) for v in ('74HCT595', '74HCT253', '74HCT14', '74HCT00', '74HCT32'))
    srams = by_value('AS6C4008-55TIN')
    for ref, what in ((U1, 'RP2354B'), (J1, 'edge'), (U2, 'ESP32-S3'), (U595, '74HCT595'), (U253, '74HCT253'),
                      (U14, '74HCT14'), (U00, '74HCT00'), (U32, '74HCT32')):
        if ref is None:
            raise SystemExit('no %s in the netlist' % what)
    if len(srams) != 2:
        raise SystemExit('expected two AS6C4008-55TIN, found %r' % srams)

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((U2, 'IO%d' % io))

    def through_r(a, b):
        """a and b joined by exactly one 2-pin resistor: its value."""
        for r, (val, fp) in parts.items():
            if r.startswith('R') and not r.startswith('RN'):
                ends = {node_net.get((r, '1')), node_net.get((r, '2'))}
                if ends == {a, b}:
                    return val
        return None

    def gate(ref, a, b):
        """Output net of the 2-input gate in ref whose inputs are nets {a, b}."""
        for pa, pb, py in GATES4:
            if {node_net.get((ref, str(pa))), node_net.get((ref, str(pb)))} == {a, b}:
                return node_net.get((ref, str(py)))
        return None

    def inv(a):
        for pa, py in INV6:
            if node_net.get((U14, str(pa))) == a:
                return node_net.get((U14, str(py)))
        return None

    nand = lambda a, b: gate(U00, a, b)
    or_ = lambda a, b: gate(U32, a, b)
    edge = {p: node_net.get((J1, str(p))) for p in EDGE}
    sig = {s: edge[p] for p, s in EDGE.items()}        # signal name -> net (GND: last wins)

    # ---- firmware pin contracts ----
    cart = 'pico/nes/firmware/include/nes_cart.h'
    P = {k: define(cart, k + '_PIN') for k in ('CA0', 'CD0', 'M2', 'RW', 'ROMSEL', 'CA13', 'PA10',
                                               'SR_SER', 'SR_SCK', 'SR_RCK', 'IRQ', 'PRG_BANK', 'CHR_BANK')}
    SR = {k: define(cart, 'SR_' + k).bit_length() - 1 for k in
          ('SRAM_EN', 'PRG_WE_EN', 'CHR_WE_EN', 'MIR0', 'MIR1', 'FOURSCREEN', 'LED', 'SPARE')}
    Q = lambda bit: func_net.get((U595, 'Q' + 'ABCDEFGH'[SR[bit]]))
    pm = 'include/pinmap/fujiversal-nes.h'
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    uart_rx, uart_tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN', -1), define(pm, 'PIN_RP2040_BOOTSEL', -1)
    if run_io < 0 or bsel_io < 0:
        alt = 'include/pinmap/fujiversal-intv.h'
        run_io, bsel_io = define(alt, 'PIN_RP2040_RUN'), define(alt, 'PIN_RP2040_BOOTSEL')
        print('note: %s does not define PIN_RP2040_RUN/BOOTSEL yet; using %s (IO%d/IO%d)' % (pm, alt, run_io, bsel_io))
    chk('nes_cart.h uses all 48 GPIOs (CHR_BANK_PIN + 9 == 48)', P['CHR_BANK'] + 9 == 48)
    chk("'595 bits are the eight distinct positions 0..7", sorted(SR.values()) == list(range(8)))

    # ---- edge <-> RP2354B, straight through (5V-tolerant pads, no buffers) ----
    for p, s in EDGE.items():
        n = edge[p]
        if s == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
        elif s.startswith(UNUSED):
            chk('J1.%d %s unconnected' % (p, s), unconn(n))
        elif s in ('+5V', 'CIRAM A10', 'CIRAM /CE', 'PPU /RD', 'PPU /WR', 'PPU /A13') or s.startswith(('PA', 'PD')):
            chk('J1.%d %s connected' % (p, s), not unconn(n))
        elif s == 'R/W':
            chk('J1.14 R/W -> GP%d' % P['RW'], n == rp(P['RW']))
        elif s == '/IRQ':
            chk('J1.15 /IRQ -> GP%d' % P['IRQ'], n == rp(P['IRQ']))
        elif s == 'M2':
            chk('J1.38 M2 -> GP%d' % P['M2'], n == rp(P['M2']))
        elif s == '/ROMSEL':
            chk('J1.50 /ROMSEL -> GP%d' % P['ROMSEL'], n == rp(P['ROMSEL']))
        elif s.startswith('A'):
            a = int(s[1:])
            g = P['CA0'] + a if a <= 12 else P['CA13'] + a - 13
            chk('J1.%d CPU %s -> GP%d' % (p, s, g), n == rp(g))
        else:
            d = int(s[1:])
            chk('J1.%d CPU %s -> GP%d' % (p, s, P['CD0'] + d), n == rp(P['CD0'] + d))
    for k in range(3):
        chk('J1 PPU A%d -> GP%d' % (10 + k, P['PA10'] + k), sig['PA%d' % (10 + k)] == rp(P['PA10'] + k))
    irq = sig['/IRQ']
    chk('/IRQ net has only J1 and U1 (the console holds the pull-up)',
        all(r in (J1, U1) for (r, _, _) in nets.get(irq, [])))

    # ---- '595 from the RP ----
    chk("GP%d -> '595 SER" % P['SR_SER'], rp(P['SR_SER']) == func_net.get((U595, 'SER')))
    chk("GP%d -> '595 SRCLK" % P['SR_SCK'], rp(P['SR_SCK']) == func_net.get((U595, 'SRCLK')))
    chk("GP%d -> '595 RCLK" % P['SR_RCK'], rp(P['SR_RCK']) == func_net.get((U595, 'RCLK')))
    chk("'595 /OE tied low", func_net.get((U595, '~{OE}')) == 'GND')
    v5 = func_net.get((U595, 'VCC'))
    chk("'595 /SRCLR tied high", func_net.get((U595, '~{SRCLR}')) == v5)
    chk("'595 QH' unconnected", unconn(func_net.get((U595, "QH'"))))

    # ---- the two SRAMs: PRG is the one whose A0 is CPU A0 ----
    PRG = next((r for r in srams if func_net.get((r, 'A0')) == sig['A0']), None)
    chk('one SRAM has A0 on CPU A0 (PRG)', PRG is not None)
    CHR = [r for r in srams if r != PRG][0]
    for i in range(13):
        chk('PRG A%d = CPU A%d' % (i, i), func_net.get((PRG, 'A%d' % i)) == sig['A%d' % i])
    for i in range(6):
        chk('PRG A%d = GP%d' % (13 + i, P['PRG_BANK'] + i), func_net.get((PRG, 'A%d' % (13 + i))) == rp(P['PRG_BANK'] + i))
    for i in range(8):
        chk('PRG DQ%d = CPU D%d' % (i, i), func_net.get((PRG, 'DQ%d' % i)) == sig['D%d' % i])
    for i in range(10):
        chk('CHR A%d = PPU A%d' % (i, i), func_net.get((CHR, 'A%d' % i)) == sig['PA%d' % i])
    for i in range(9):
        chk('CHR A%d = GP%d' % (10 + i, P['CHR_BANK'] + i), func_net.get((CHR, 'A%d' % (10 + i))) == rp(P['CHR_BANK'] + i))
    for i in range(8):
        chk('CHR DQ%d = PPU D%d' % (i, i), func_net.get((CHR, 'DQ%d' % i)) == sig['PD%d' % i])
    chk('CHR /CE = PPU A13', func_net.get((CHR, '~{CE}')) == sig['PA13'])
    for r in (PRG, CHR):
        chk('%s VCC on the 5V logic rail, VSS on GND' % r,
            func_net.get((r, 'VCC')) == v5 and func_net.get((r, 'VSS')) == 'GND')

    # ---- PWR_OK: console +5V (edge 36, before the OR diode) -> divider -> '14 ----
    cons = sig['+5V']
    chk('edge +5V is not the logic 5V rail (diode-OR in between)', cons != v5 and not unconn(cons))
    chk('edge +5V -> SS34 -> logic 5V rail',
        any(val == 'SS34' and node_net.get((r, '2')) == cons and node_net.get((r, '1')) == v5
            for r, (val, _) in parts.items()))
    vsense = next((node_net.get((U14, str(pa))) for pa, py in INV6
                   if through_r(cons, node_net.get((U14, str(pa)))) is not None), None)
    chk("a '14 input is fed from edge +5V through a resistor (VSENSE)", vsense is not None)
    top, bot = through_r(cons, vsense), through_r(vsense, 'GND')
    chk('VSENSE divider to GND', top is not None and bot is not None)
    if top and bot:
        val = lambda s: float(s.replace('k', 'e3').replace('R', ''))
        hi, lo = 5.25 * val(bot) / (val(top) + val(bot)), 4.75 * val(bot) / (val(top) + val(bot))
        chk('VSENSE <= 3.3V at 5.25V (%.2f) and >= 2.0V (HCT VIH) at 4.75V (%.2f)' % (hi, lo), hi <= 3.3 and lo >= 2.0)
    pwr_ok_n = inv(vsense)
    pwr_ok = inv(pwr_ok_n)
    chk('PWR_OK_N = !VSENSE, PWR_OK = !PWR_OK_N', pwr_ok_n is not None and pwr_ok is not None)

    # ---- the decode (pico/nes/README.md) ----
    romsel = inv(sig['/ROMSEL'])
    chk("ROMSEL = !(/ROMSEL) on a '14", romsel is not None)
    chk('PRG /CE = NAND(ROMSEL, SRAM_EN)', func_net.get((PRG, '~{CE}')) == nand(romsel, Q('SRAM_EN')) != None)
    chk('PRG /OE = NAND(R/W, PWR_OK)', func_net.get((PRG, '~{OE}')) == nand(sig['R/W'], pwr_ok) != None)
    chk('PRG /WE = NAND(ROMSEL, PRG_WE_EN) | R/W',
        func_net.get((PRG, '~{WE}')) == or_(nand(romsel, Q('PRG_WE_EN')), sig['R/W']) != None)
    chk('CHR /OE = PPU /RD | PWR_OK_N', func_net.get((CHR, '~{OE}')) == or_(sig['PPU /RD'], pwr_ok_n) != None)
    chk('CHR /WE = PPU /WR | !CHR_WE_EN', func_net.get((CHR, '~{WE}')) == or_(sig['PPU /WR'], inv(Q('CHR_WE_EN'))) != None)
    chk('CIRAM /CE = PPU /A13 | (FOURSCREEN & PWR_OK)',
        sig['CIRAM /CE'] == or_(sig['PPU /A13'], inv(nand(Q('FOURSCREEN'), pwr_ok))) != None)
    m = lambda f: func_net.get((U253, f))
    chk("'253 I0a = PPU A10, I1a = PPU A11, I2a = 0, I3a = 1",
        m('I0a') == sig['PA10'] and m('I1a') == sig['PA11'] and m('I2a') == 'GND' and m('I3a') == v5)
    chk("'253 selects A0 = MIR0, A1 = MIR1", m('A0') == Q('MIR0') and m('A1') == Q('MIR1'))
    chk("'253 Za = CIRAM A10, /OEa = PWR_OK_N", m('Za') == sig['CIRAM A10'] and m('OEa') == pwr_ok_n)
    chk("'253 half b parked", m('OEb') == v5 and unconn(m('Zb')) and
        all(m('I%db' % i) == 'GND' for i in range(4)))
    led = one('green')
    chk("'595 LED bit -> 1k -> LED anode", led is not None and through_r(Q('LED'), node_net.get((led, '2'))) == '1k'
        and node_net.get((led, '1')) == 'GND')
    chk("'595 spare bit on a test pad", any(r.startswith('TP') for (r, _, _) in nets.get(Q('SPARE'), [])))
    chk('M2 on a test pad', any(r.startswith('TP') for (r, _, _) in nets.get(sig['M2'], [])))
    for ref in (U595, U253):
        chk('%s on the 5V rail' % parts[ref][0], func_net.get((ref, 'VCC')) == v5 and func_net.get((ref, 'GND')) == 'GND')
    for ref in (U14, U00, U32):
        chk('%s on the 5V rail' % parts[ref][0], node_net.get((ref, '14')) == v5 and node_net.get((ref, '7')) == 'GND')
    # unused gate inputs grounded (an input that is on no checked net above)
    for ref, table in ((U00, GATES4), (U32, GATES4), (U14, INV6)):
        for g in table:
            ins = [node_net.get((ref, str(p))) for p in g[:-1]]
            out = node_net.get((ref, str(g[-1])))
            if unconn(out):
                chk('%s unused gate inputs tied to GND' % ref, all(i == 'GND' for i in ins))
    # the bus touches only the edge, the RP, the SRAMs, the glue and test pads
    glue = {J1, U1, PRG, CHR, U595, U253, U14, U00, U32}
    for p, s in EDGE.items():
        if s in ('GND', '+5V') or s.startswith(UNUSED):
            continue
        others = [(r, pin) for (r, pin, f) in nets.get(edge[p], []) if r not in glue and not r.startswith('TP')]
        chk('J1.%d %s net carries no extra parts (no pull-ups, no series R)' % (p, s), not others)

    # ---- RP support ----
    v33 = func_net.get((U1, 'IOVDD'))
    chk('RP IOVDD rail is not the 5V rail', v33 not in (v5, None))
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((U2, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((U2, 'USB_D-'))) == '27R')
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (PIN_RP2040_RUN) -> 1k -> RP RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (PIN_RP2040_BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up', through_r(run, v33) == '10k')
    chk('QSPI_SS pull-up', through_r(ss, v33) == '10k')
    for f in ('QSPI_SCLK', 'QSPI_SD0', 'QSPI_SD1', 'QSPI_SD2', 'QSPI_SD3'):
        chk('RP %s unconnected (flash is in the package)' % f, unconn(func_net.get((U1, f))))
    for n, nodes in nets.items():   # every supply pin (names repeat: IOVDD x8, DVDD x3)
        for (ref, pin, f) in nodes:
            if ref == U1 and f in ('IOVDD', 'QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN'):
                chk('RP %s (pin %s) on %s' % (f, pin, v33), n == v33)
            if ref == U1 and f == 'DVDD':
                chk('RP DVDD (pin %s) on DVDD' % pin, n == func_net.get((U1, 'VREG_FB')))
            if ref == U1 and f in ('GND', 'VREG_PGND'):
                chk('RP %s (pin %s) on GND' % (f, pin), n == 'GND')
    for f in ('SWCLK', 'SWDIO', 'RUN'):
        chk('RP %s on a test pad' % f, any(r.startswith('TP') for (r, _, _) in nets.get(func_net.get((U1, f)), [])))

    # ---- S3 pins ----
    chk('SD CS  IO%d -> J2 DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((J2, '2')))
    chk('SD MOSI IO%d -> J2 CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((J2, '3')))
    chk('SD SCK IO%d -> J2 CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((J2, '5')))
    chk('SD MISO IO%d -> J2 DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((J2, '7')))
    chk('J2 VDD on %s, VSS on GND' % v33, node_net.get((J2, '4')) == v33 and node_net.get((J2, '6')) == 'GND')
    ws_din = node_net.get((WS, '3'))
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), ws_din) is not None)
    chk('PIN_UART0_TX/RX are the module TXD0/RXD0 pads (GPIO43/44)', (uart_tx, uart_rx) == (43, 44))
    chk('S3 TXD0 -> CP2102N RXD', func_net.get((U2, 'TXD0')) == func_net.get((UCP, 'RXD')))
    chk('S3 RXD0 <- CP2102N TXD', func_net.get((U2, 'RXD0')) == func_net.get((UCP, 'TXD')))
    for io in (3, 45, 46):
        chk('S3 strapping IO%d unloaded' % io, unconn(s3(io)))
    for io in range(26, 38):
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, unconn(s3(io)))

    # ---- general ----
    for n, nodes in nets.items():
        if not n.startswith('unconnected'):
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
        others = edge_of.get(n, []) + ['%s.%s' % (parts[r][0] if r in srams else r, fn or pin)
                                       for (r, pin, fn) in nets.get(n, []) if r not in (U1, J1)]
        print('GP%-4d %-4s %-10s %s' % (g, pin_of[f], n, ', '.join(others)))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
