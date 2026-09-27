#!/usr/bin/env python3
"""Cross-check the Fujiversal-Atari2600 Rev0 schematic netlist against the
firmware that has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from the fujinet-firmware
tree holding the 2600 port (default ~/Workspace/fn-2600, or $FUJINET_FIRMWARE):
  pico/atari-2600/firmware/include/vcs_pins.h        ADDR_PIN, ADDR_BITS, D0_PIN, DIR_PIN
  pico/atari-2600/firmware/boards/fujivcs.cmake      PICO_PLATFORM, PICO_FLASH_SIZE_BYTES
  pico/atari-2600/firmware/boards/fujivcs.h          -> boards/pico.h (LED = GP25)
  include/pinmap/fujiversal-atari2600.h              S3 SD/LED/UART/RUN/BOOTSEL pins
and checks every one of them, plus the Atari 2600 edge map, against the pin
*functions* the netlist reports (GPIOn on the RP2040, IOn on the S3), tracing
each bus line through its 74LVC245A.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fn-2600'))
SCH = os.path.join(PRJ, 'Fujiversal-Atari2600-Rev0.kicad_sch')

# Atari 2600 cartridge connector, pins 1-24 (1-12 console-front face,
# 13-24 rear face; pin 1 behind pin 24).  Independent copy of the map.
EDGE = {1: 'A7', 2: 'A6', 3: 'A5', 4: 'A4', 5: 'A3', 6: 'A2', 7: 'A1', 8: 'A0',
        9: 'D0', 10: 'D1', 11: 'D2', 12: 'GND', 13: 'D3', 14: 'D4', 15: 'D5', 16: 'D6',
        17: 'D7', 18: 'A12', 19: 'A10', 20: 'A11', 21: 'A9', 22: 'A8', 23: '+5V', 24: 'GND'}

fails = 0
count = 0


def chk(desc, ok):
    global fails, count
    count += 1
    if not ok:
        fails += 1
        print('FAIL:', desc)


def define(path, name):
    txt = open(os.path.join(FW, path)).read()
    m = re.search(r'#define\s+%s\s+(\S+)' % re.escape(name), txt)
    if not m:
        raise SystemExit('%s: no #define %s' % (path, name))
    v = m.group(1)
    m2 = re.match(r'GPIO_NUM_(\d+)', v)
    if m2:
        return int(m2.group(1))
    return int(v.rstrip('uUlL'), 0)


def cmake_set(path, name):
    m = re.search(r'set\(%s\s+(\S+)\)' % re.escape(name), open(os.path.join(FW, path)).read())
    if not m:
        raise SystemExit('%s: no set(%s)' % (path, name))
    return m.group(1)


def main():
    fn = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-check.xml')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn, SCH],
                   check=True, capture_output=True)
    t = ET.parse(fn)
    node_net, func_net, nets = {}, {}, {}
    for n in t.iter('net'):
        name = n.get('name')
        for nd in n.iter('node'):
            ref, pin, fn_ = nd.get('ref'), nd.get('pin'), (nd.get('pinfunction') or '')
            fn_ = re.sub(r'_%s$' % re.escape(pin), '', fn_)   # kicad-cli appends _<pin>
            node_net[(ref, pin)] = name
            func_net[(ref, fn_)] = name
            nets.setdefault(name, []).append((ref, pin, fn_))
    parts = {c.get('ref'): (c.findtext('value'), c.findtext('footprint'), c) for c in t.iter('comp')}
    by_value = lambda v: sorted(r for r, (val, _, _) in parts.items() if val == v)
    field = lambda ref, k: next((f.text for f in parts[ref][2].iter('field') if f.get('name') == k), None)

    U1 = by_value('RP2040')[0]
    U2 = by_value('ESP32-S3-WROOM-1-N16R8')[0]
    FL = by_value('W25Q16JVSSIQ')[0]
    J1 = by_value('Atari2600_Cart_Edge_24')[0]
    J2 = by_value('microSD')[0]
    UCP = by_value('CP2102N-A02-GQFN28')[0]
    WS = by_value('WS2812B-2020-V6')[0]
    BUFS = by_value('74LVC245A')

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((U2, 'IO%d' % io))

    def through_r(a, b):
        """a and b joined by exactly one 2-pin resistor; returns its value."""
        for r, (val, fp, _) in parts.items():
            if r.startswith('R') and not r.startswith('RN'):
                ends = {node_net.get((r, '1')), node_net.get((r, '2'))}
                if ends == {a, b}:
                    return val
        return None

    def through_245(edge_net):
        """(buffer ref, RP-side net, A->B only?) for a console net entering a '245 A input."""
        for b in BUFS:
            for k in range(8):
                if node_net.get((b, str(2 + k))) == edge_net:
                    return b, node_net.get((b, str(18 - k)))
        return None, None

    # ---- firmware contracts ----
    vp = 'pico/atari-2600/firmware/include/vcs_pins.h'
    addr_pin, addr_bits = define(vp, 'ADDR_PIN'), define(vp, 'ADDR_BITS')
    d0_pin, dir_pin = define(vp, 'D0_PIN'), define(vp, 'DIR_PIN')
    chk('vcs_pins.h: 13 address bits', addr_bits == 13)
    cm = 'pico/atari-2600/firmware/boards/fujivcs.cmake'
    chk('fujivcs is an RP2040 board', cmake_set(cm, 'PICO_PLATFORM') == 'rp2040')
    flash = int(cmake_set(cm, 'PICO_FLASH_SIZE_BYTES'))
    chk('flash part matches PICO_FLASH_SIZE_BYTES (%d = W25Q16)' % flash,
        flash == 2 * 1024 * 1024 and parts[FL][0] == 'W25Q16JVSSIQ')
    bh = open(os.path.join(FW, 'pico/atari-2600/firmware/boards/fujivcs.h')).read()
    chk('fujivcs.h is a boards/pico.h board (LED GP25, W25Q080-class boot2)', 'boards/pico.h' in bh)
    pm = 'include/pinmap/fujiversal-atari2600.h'
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN'), define(pm, 'PIN_RP2040_BOOTSEL')
    u0rx, u0tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')

    # ---- edge -> 74LVC245A -> RP2040 ----
    edge_net = {p: node_net.get((J1, str(p))) for p in EDGE}
    data_bufs = set()
    for p, sig in EDGE.items():
        n = edge_net[p]
        if sig == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
            continue
        if sig == '+5V':
            chk('J1.23 is +5V', n == '+5V')
            continue
        bit = int(sig[1:])
        gp = addr_pin + bit if sig[0] == 'A' else d0_pin + bit
        b, rp_net = through_245(n)
        chk('J1.%d %s -> 74LVC245A A-side' % (p, sig), b is not None)
        chk('J1.%d %s -> %s -> GP%d' % (p, sig, b, gp), rp_net is not None and rp(gp) == rp_net)
        others = [(r, pin) for (r, pin, f) in nets[n] if r not in (J1, b)]
        chk('console net %s touches only J1 + its buffer' % n, not others)
        if rp_net:
            others = [(r, pin) for (r, pin, f) in nets[rp_net] if r not in (U1, b)]
            chk('RP net %s touches only the buffer + U1' % rp_net, not others)
        if sig[0] == 'D' and b:
            data_bufs.add(b)
    chk('D0-D7 share one buffer', len(data_bufs) == 1)
    dir_net = rp(dir_pin)
    for b in BUFS:
        chk('%s VCC on +3V3 (A inputs 5V tolerant only when VCC is 3.3V)' % b, node_net.get((b, '20')) == '+3V3')
        chk('%s GND' % b, node_net.get((b, '10')) == 'GND')
        chk('%s /OE tied active (GND)' % b, node_net.get((b, '19')) == 'GND')
        d = node_net.get((b, '1'))
        if b in data_bufs:
            # LVC245: DIR high = A->B (console -> RP), low = B->A (cart drives).
            # vcs_pins.h: DIR_PIN "0 = cart drives the console"; main.c boots it 1.
            chk('%s DIR = GP%d (DIR_PIN), A = console side so low = cart drives' % (b, dir_pin), d == dir_net)
            chk('%s DIR pulled up (not driving while the RP is in reset)' % b, through_r(d, '+3V3') is not None)
        else:
            chk('%s (address) DIR tied high: console -> RP only' % b, d == '+3V3')
        for k in range(8):   # an unused channel's A input must not float
            a = node_net.get((b, str(2 + k)))
            chk('%s A%d not floating' % (b, k), a is not None and not a.startswith('unconnected'))
    chk('edge +5V feeds only the power path', all(r.startswith(('D', 'C', 'J')) for (r, _, _) in nets['+5V']))

    # ---- RP2040 support ----
    chk('GP25 (PICO_DEFAULT_LED_PIN) -> R -> LED', any(through_r(rp(25), n) for n in nets if n.startswith('RP_LED_A')))
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((U2, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((U2, 'USB_D-'))) == '27R')
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (PIN_RP2040_RUN) -> 1k -> RP RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (PIN_RP2040_BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up', through_r(run, '+3V3') == '10k')
    chk('QSPI_SS pull-up', through_r(ss, '+3V3') == '10k')
    qspi = {'~{QSPI_SS}': '~{CS}', 'QSPI_SCLK': 'CLK', 'QSPI_SD0': 'DI/IO_{0}', 'QSPI_SD1': 'DO/IO_{1}',
            'QSPI_SD2': '~{WP}/IO_{2}', 'QSPI_SD3': '~{HOLD}/~{RESET}/IO_{3}'}
    for a, b in qspi.items():
        chk('RP %s -> flash %s' % (a, b), func_net.get((U1, a)) is not None and func_net.get((U1, a)) == func_net.get((FL, b)))
    chk('flash VCC +3V3', func_net.get((FL, 'VCC')) == '+3V3')
    chk('RP TESTEN grounded', func_net.get((U1, 'TESTEN')) == 'GND')
    chk('RP VREG_VOUT feeds DVDD', func_net.get((U1, 'VREG_VOUT')) == 'DVDD')
    for n, nodes in nets.items():
        for (ref, pin, f) in nodes:
            if ref == U1 and f in ('IOVDD', 'USB_VDD', 'ADC_AVDD', 'VREG_VIN'):
                chk('RP %s (pin %s) on +3V3' % (f, pin), n == '+3V3')
            if ref == U1 and f == 'DVDD':
                chk('RP DVDD (pin %s) on DVDD' % pin, n == 'DVDD')
    xo = func_net.get((U1, 'XOUT'))
    chk('crystal: XIN direct, XOUT through 1k', through_r(xo, [n for n in nets if n == 'XOUT_Y'][0]) == '1k')

    # ---- S3 pins ----
    chk('SD CS  IO%d -> J2 DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((J2, '2')))
    chk('SD MOSI IO%d -> J2 CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((J2, '3')))
    chk('SD SCK IO%d -> J2 CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((J2, '5')))
    chk('SD MISO IO%d -> J2 DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((J2, '7')))
    chk('J2 VDD on +3V3, VSS on GND', node_net.get((J2, '4')) == '+3V3' and node_net.get((J2, '6')) == 'GND')
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), node_net.get((WS, '3'))) is not None)
    chk('UART0 TX IO%d is TXD0 -> CP2102N RXD' % u0tx, u0tx == 43 and func_net.get((U2, 'TXD0')) == func_net.get((UCP, 'RXD')))
    chk('UART0 RX IO%d is RXD0 <- CP2102N TXD' % u0rx, u0rx == 44 and func_net.get((U2, 'RXD0')) == func_net.get((UCP, 'TXD')))
    for io in (3, 45, 46):
        n = s3(io)
        chk('S3 strapping IO%d left alone' % io, n is None or n.startswith('unconnected'))
    for io in range(26, 38):
        n = s3(io)
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, n is None or n.startswith('unconnected'))

    # ---- general ----
    for n, nodes in nets.items():
        if not n.startswith('unconnected'):
            chk('net %s has >= 2 pins' % n, len(nodes) >= 2)
    for r in parts:
        if not r.startswith(('J1', 'TP', '#', 'H')):
            chk('%s has an LCSC code' % r, bool(field(r, 'LCSC')))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
