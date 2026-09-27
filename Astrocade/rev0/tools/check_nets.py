#!/usr/bin/env python3
"""Cross-check the FujiNet-Astrocade Rev0 schematic netlist against the
firmware that has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from fujinet-firmware
(default ~/Workspace/fujinet-firmware, or $FUJINET_FIRMWARE):
  pico/astrocade/firmware/include/astrocade_cart.h      ADDR_MASK, EN_PIN, D0_PIN
  pico/astrocade/firmware/boards/fujicade_rp2354.h      FUJICADE_VSENSE_PIN
  include/pinmap/fujiversal-astrocade.h                 S3 SD/LED/UART/RUN/BOOTSEL pins
and checks every one of them, plus the Tilton 26-pin edge map, against the
pin *functions* the netlist reports (GPIOn on the RP2354A, IOn on the S3).

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
SCH = os.path.join(PRJ, 'FujiNet-Astrocade-Rev0.kicad_sch')

EDGE = {1: 'GND', 2: 'A7', 3: 'A6', 4: 'A5', 5: 'A4', 6: 'A3', 7: 'A2', 8: 'A1', 9: 'A0',
        10: 'D0', 11: 'D1', 12: 'D2', 13: 'GND', 14: 'D3', 15: 'D4', 16: 'D5', 17: 'D6',
        18: 'D7', 19: 'A11', 20: 'A10', 21: '/CCS', 22: 'A12', 23: 'A9', 24: 'A8', 25: '+5V',
        26: 'GND'}   # Tilton 1-26 (= MCM 0-25), ballyalley cartridge-port page

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


def main():
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-astrocade-check.xml')
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
    parts = {c.get('ref'): (c.findtext('value'), c.findtext('footprint')) for c in t.iter('comp')}
    by_value = lambda v: sorted(r for r, (val, _) in parts.items() if val == v)

    U1 = by_value('RP2354A')[0]
    U2 = by_value('ESP32-S3-WROOM-1-N16R8')[0]
    J1 = by_value('Astrocade_Cart_Edge_26')[0]
    J2 = by_value('microSD')[0]
    UCP = by_value('CP2102N-A02-GQFN28')[0]
    WS = by_value('WS2812B-2020-V6')[0]

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((U2, 'IO%d' % io))

    def through_r(a, b):
        """a and b joined by exactly one 2-pin resistor."""
        for r, (val, fp) in parts.items():
            if r.startswith('R') and not r.startswith('RN'):
                ends = {node_net.get((r, '1')), node_net.get((r, '2'))}
                if ends == {a, b}:
                    return val
        return None

    # ---- firmware pin contracts ----
    cart = 'pico/astrocade/firmware/include/astrocade_cart.h'
    addr_mask = define(cart, 'ADDR_MASK')
    en_pin = define(cart, 'EN_PIN')
    d0_pin = define(cart, 'D0_PIN')
    vsense = define('pico/astrocade/firmware/boards/fujicade_rp2354.h', 'FUJICADE_VSENSE_PIN')
    pm = 'include/pinmap/fujiversal-astrocade.h'
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN'), define(pm, 'PIN_RP2040_BOOTSEL')
    chk('ADDR_MASK is A0-A12 unshifted', addr_mask == 0x1FFF)

    # ---- edge <-> RP2354A, straight through (5V-tolerant pads, no buffers) ----
    edge_net = {p: node_net.get((J1, str(p))) for p in EDGE}
    for p, sig in EDGE.items():
        n = edge_net[p]
        if sig == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
        elif sig == '+5V':
            chk('J1.25 is +5V', n == '+5V')
        elif sig == '/CCS':
            chk('J1.21 /CCS -> GP%d (EN_PIN)' % en_pin, n is not None and rp(en_pin) == n)
        elif sig.startswith('A'):
            a = int(sig[1:])
            chk('J1.%d %s -> GP%d' % (p, sig, a), n is not None and rp(a) == n)
        else:
            d = int(sig[1:])
            chk('J1.%d %s -> GP%d' % (p, sig, d0_pin + d), n is not None and rp(d0_pin + d) == n)
    bus = [edge_net[p] for p, s in EDGE.items() if s not in ('GND', '+5V')]
    for n in bus:
        others = [(r, pin) for (r, pin, f) in nets[n] if r not in (U1, J1)]
        allowed = n == edge_net[21] and len(others) == 1   # /CCS pull-up only
        chk('bus net %s touches only J1 + U1 (+ /CCS pull-up)' % n, not others or allowed)
    ccs = edge_net[21]
    chk('/CCS has a pull-up to +3V3', through_r(ccs, '+3V3') is not None)

    # ---- console power sense ----
    vs = rp(vsense)
    top, bot = through_r('+5V', vs), through_r(vs, 'GND')
    chk('GP%d VSENSE divider from +5V' % vsense, top is not None and bot is not None)
    if top and bot:
        val = lambda s: float(s.replace('k', 'e3').replace('R', ''))
        vout = 5.25 * val(bot) / (val(top) + val(bot))
        chk('VSENSE <= 3.3V at 5.25V in (%.2fV) and >= 2.0V at 4.75V' % vout,
            vout <= 3.3 and 4.75 * val(bot) / (val(top) + val(bot)) >= 2.0)

    # ---- RP support ----
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((U2, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((U2, 'USB_D-'))) == '27R')
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (PIN_RP2040_RUN) -> 1k -> RP RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (PIN_RP2040_BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up', through_r(run, '+3V3') == '10k')
    chk('QSPI_SS pull-up', through_r(ss, '+3V3') == '10k')
    for f in ('QSPI_SCLK', 'QSPI_SD0', 'QSPI_SD1', 'QSPI_SD2', 'QSPI_SD3'):
        chk('RP %s unconnected (flash is in the package)' % f, func_net.get((U1, f), '').startswith('unconnected'))
    for n, nodes in nets.items():   # every supply pin (names repeat: IOVDD x6, DVDD x3)
        for (ref, pin, f) in nodes:
            if ref == U1 and (f == 'IOVDD' or f in ('QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN')):
                chk('RP %s (pin %s) on +3V3' % (f, pin), n == '+3V3')
            if ref == U1 and f == 'DVDD':
                chk('RP DVDD (pin %s) on DVDD' % pin, n == 'DVDD')
    chk('RP VREG_FB on DVDD', func_net.get((U1, 'VREG_FB')) == 'DVDD')

    # ---- S3 pins ----
    chk('SD CS  IO%d -> J2 DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((J2, '2')))
    chk('SD MOSI IO%d -> J2 CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((J2, '3')))
    chk('SD SCK IO%d -> J2 CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((J2, '5')))
    chk('SD MISO IO%d -> J2 DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((J2, '7')))
    chk('J2 VDD on +3V3, VSS on GND', node_net.get((J2, '4')) == '+3V3' and node_net.get((J2, '6')) == 'GND')
    ws_din = node_net.get((WS, '3'))
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), ws_din) is not None)
    chk('S3 TXD0 -> CP2102N RXD', func_net.get((U2, 'TXD0')) == func_net.get((UCP, 'RXD')))
    chk('S3 RXD0 <- CP2102N TXD', func_net.get((U2, 'RXD0')) == func_net.get((UCP, 'TXD')))
    for io in (0, 3, 45, 46):
        n = s3(io)
        chk('S3 strapping IO%d not loaded by anything but EN/BOOT circuitry' % io,
            n is None or n.startswith('unconnected') or io == 0)
    for io in range(26, 38):
        n = s3(io)
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, n is None or n.startswith('unconnected'))

    # ---- general ----
    for n, nodes in nets.items():
        if not n.startswith('unconnected'):
            chk('net %s has >= 2 pins' % n, len(nodes) >= 2)
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
