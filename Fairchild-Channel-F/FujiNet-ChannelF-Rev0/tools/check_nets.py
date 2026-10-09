#!/usr/bin/env python3
"""Cross-check the FujiNet-ChannelF Rev0 schematic netlist against the firmware that has to run on
it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from fujinet-firmware ($FUJINET_FIRMWARE, else
~/Workspace/fujinet-firmware) and the pico-sdk ($PICO_SDK_PATH, else /usr/share/pico-sdk):
  pico/channelf/firmware/include/channelf_cart.h   D0_PIN, ROMC0_PIN, WRITE_PIN, PHI_PIN, DIR_PIN,
                                                   INTREQ_PIN
  pico/channelf/firmware/src/channelf_cart.c       the DIR polarity (data_drive / data_release)
  pico/channelf/firmware/boards/fujichannelf.cmake PICO_PLATFORM, PICO_FLASH_SIZE_BYTES
  <pico-sdk>/src/boards/include/boards/pico.h      PICO_DEFAULT_LED_PIN (fujichannelf.h includes it)
  include/pinmap/fujiversal-channelf.h             S3 SD / LED / UART pins (from the branch
                                                   fujiversal-channelf-board when the checkout lacks it)
and checks every one of them, plus the Videocart's 22-pin edge map, against the pin *functions* the
netlist reports (GPIOn on the RP2040, A1-B8 / DIR / VCCA on the translators, IOn on the S3).

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE') or os.path.expanduser('~/Workspace/fujinet-firmware')
SDK = os.environ.get('PICO_SDK_PATH') or '/usr/share/pico-sdk'
SCH = os.path.join(PRJ, 'FujiNet-ChannelF-Rev0.kicad_sch')
RP_RAIL = '+3V3_RP'

# channelf.se veswiki 'Pinouts' (Cartridge Connector Pinout), transcribed separately from design.py
EDGE = {1: 'GND', 2: 'GND', 3: 'D0', 4: 'D1', 5: '/INTREQ', 6: 'ROMC0', 7: 'ROMC1', 8: 'ROMC2', 9: 'D2',
        10: 'ROMC3', 11: 'D3', 12: 'ROMC4', 13: 'PHI', 14: 'D4', 15: 'WRITE', 16: 'D5', 17: 'D6', 18: 'D7',
        19: '+5V', 20: '+5V', 21: 'NC', 22: '+12V'}

fails = 0
warns = 0
count = 0


def chk(desc, ok):
    global fails, count
    count += 1
    if not ok:
        fails += 1
        print('FAIL:', desc)


def warn(desc):
    global warns
    warns += 1
    print('WARN:', desc)


def text(path):
    """A firmware file: the checkout's copy, else the fujiversal-channelf-board branch's."""
    fn = os.path.join(FW, path)
    if os.path.exists(fn):
        return open(fn).read()
    r = subprocess.run(['git', '-C', FW, 'show', 'fujiversal-channelf-board:' + path], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('%s: not in %s nor on its fujiversal-channelf-board branch' % (path, FW))
    return r.stdout


def define(txt, name, default=None):
    m = re.search(r'#define\s+%s\s+(\S+)' % re.escape(name), txt)
    if not m:
        if default is not None:
            return default
        raise SystemExit('no #define %s' % name)
    v = m.group(1)
    if v == 'GPIO_NUM_NC':
        return -1
    m2 = re.match(r'GPIO_NUM_(\d+)', v)
    if m2:
        return int(m2.group(1))
    return int(v.rstrip('uUlL'), 0)


def main():
    fd, fn = tempfile.mkstemp(prefix='fujinet-channelf-check-', suffix='.xml')
    os.close(fd)
    try:
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn, SCH],
                       check=True, capture_output=True)
        t = ET.parse(fn)
    finally:
        os.remove(fn)
    node_net, func_net, nets = {}, {}, {}
    for n in t.iter('net'):
        name = n.get('name')
        name = name if name.startswith('unconnected') else name.rsplit('/', 1)[-1]
        for nd in n.iter('node'):
            ref, pin, f = nd.get('ref'), nd.get('pin'), (nd.get('pinfunction') or '')
            f = re.sub(r'_%s$' % re.escape(pin), '', f)        # kicad-cli appends _<pin>
            node_net[(ref, pin)] = name
            func_net[(ref, f)] = name
            nets.setdefault(name, []).append((ref, pin, f))
    parts = {c.get('ref'): (c.findtext('value'), c.findtext('footprint')) for c in t.iter('comp')}
    by_value = lambda v: sorted(r for r, (val, _) in parts.items() if val == v)
    net = lambda ref, pin: node_net.get((ref, str(pin)))
    unconn = lambda n: n is None or n.startswith('unconnected')

    U_RP = by_value('RP2040')[0]
    U_S3 = by_value('ESP32-S3-WROOM-1-N16R8')[0]
    J_EDGE = by_value('ChannelF_Cart_Edge_22')[0]
    J_SD = by_value('microSD')[0]
    U_CP = by_value('CP2102N-A02-GQFN28')[0]
    WS = by_value('WS2812B-2020-V6')[0]
    LVC = by_value('SN74LVC4245APWR')
    chk('two SN74LVC4245A', len(LVC) == 2)

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U_RP and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((U_S3, 'IO%d' % io))

    def through_r(a, b):
        """a and b joined by exactly one 2-pin resistor: its value."""
        for r, (val, fp) in parts.items():
            if r.startswith('R') and not r.startswith('RN'):
                if {net(r, 1), net(r, 2)} == {a, b}:
                    return val
        return None

    def lvc(ref, f):
        return func_net.get((ref, f))

    def lvc_chan(ref, n):
        """(A-side net, B-side net) of a translator channel whose A side is net n."""
        for k in range(1, 9):
            if lvc(ref, 'A%d' % k) == n:
                return k, lvc(ref, 'B%d' % k)
        return None, None

    # ---- firmware contracts ----
    cart_h = text('pico/channelf/firmware/include/channelf_cart.h')
    d0, romc0 = define(cart_h, 'D0_PIN'), define(cart_h, 'ROMC0_PIN')
    write_pin, phi_pin = define(cart_h, 'WRITE_PIN'), define(cart_h, 'PHI_PIN')
    dir_pin, intreq_pin = define(cart_h, 'DIR_PIN'), define(cart_h, 'INTREQ_PIN')
    cart_c = text('pico/channelf/firmware/src/channelf_cart.c')
    drive = re.search(r'data_drive\(uint8_t v\)\s*\{(.*?)\n\}', cart_c, re.S).group(1)
    release = re.search(r'data_release\(void\)\s*\{(.*?)\n\}', cart_c, re.S).group(1)
    chk('firmware: data_drive clears DIR (0 = cart drives the console)', 'gpio_clr = DIR_MASK' in drive)
    chk('firmware: data_release sets DIR (1 = console -> cart)', 'gpio_set = DIR_MASK' in release)
    cmake = text('pico/channelf/firmware/boards/fujichannelf.cmake')
    chk('firmware: PICO_PLATFORM rp2040', re.search(r'set\(PICO_PLATFORM\s+rp2040\)', cmake) is not None)
    flash = int(re.search(r'PICO_FLASH_SIZE_BYTES\s+(\d+)', cmake).group(1))
    board_h = text('pico/channelf/firmware/boards/fujichannelf.h')
    chk('firmware: fujichannelf.h is the stock Pico board header', '#include "boards/pico.h"' in board_h)
    led_pin = define(open(os.path.join(SDK, 'src/boards/include/boards/pico.h')).read(), 'PICO_DEFAULT_LED_PIN')
    pm = text('include/pinmap/fujiversal-channelf.h')
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    uart_rx, uart_tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN', -2), define(pm, 'PIN_RP2040_BOOTSEL', -2)
    if run_io == -2 or bsel_io == -2:
        warn('fujiversal-channelf.h declares no PIN_RP2040_RUN / _BOOTSEL: this board wires S3 IO4 / IO5 '
             '(the fujiversal-astrocade board pins) -- add them to the pinmap')
        run_io, bsel_io = 4, 5

    # ---- the edge ----
    edge = {p: net(J_EDGE, p) for p in EDGE}
    for p, sig in EDGE.items():
        if sig == 'GND':
            chk('J.%d is GND' % p, edge[p] == 'GND')
        elif sig == '+5V':
            chk('J.%d +5V is CONS_5V' % p, edge[p] == 'CONS_5V')
        elif sig in ('NC', '+12V'):
            chk('J.%d %s left open' % (p, sig), unconn(edge[p]))
    # which translator is which: the data one carries the edge's D0
    data = next((u for u in LVC if lvc_chan(u, edge[3])[0]), None)
    ctrl = next((u for u in LVC if u != data), None)
    chk('a translator takes D0 on its A port', data is not None and ctrl is not None)
    if data is None or ctrl is None:
        print('%d checks, %d failed' % (count, fails))
        sys.exit(1)

    # ---- edge -> translator A port -> B port -> RP2040 GPIO, signal by signal ----
    sig_gpio = {'D%d' % i: d0 + i for i in range(8)}
    sig_gpio.update({'ROMC%d' % i: romc0 + i for i in range(5)})
    sig_gpio.update({'WRITE': write_pin, 'PHI': phi_pin})
    for p, sig in EDGE.items():
        if sig not in sig_gpio:
            continue
        u = data if sig.startswith('D') else ctrl
        k, b = lvc_chan(u, edge[p])
        chk('J.%d %s -> %s A%s -> B%s -> GP%d' % (p, sig, u, k, k, sig_gpio[sig]),
            k is not None and b is not None and rp(sig_gpio[sig]) == b)
        others = [(r, pin) for (r, pin, f) in nets.get(edge[p], []) if r not in (J_EDGE, u)]
        chk('edge net %s touches only the edge and its translator' % sig, not others)
    # no RP2040 pin anywhere on a 5 V net or straight on an edge net (it is not 5 V tolerant)
    five = {'CONS_5V', '+5V', 'VBUS'} | {n for n in edge.values() if n and n not in ('GND',)}
    bad = sorted((pin, n) for (r, pin), n in node_net.items() if r == U_RP and n in five)
    chk('no RP2040 pin on a 5 V or edge net %s' % bad, not bad)

    # ---- translator supplies and directions ----
    for u in (data, ctrl):
        chk('%s VCCA on CONS_5V (straight off the edge, ahead of the OR diode)' % u, lvc(u, 'V_{CCA}') == 'CONS_5V')
        chk('%s VCCB (23, 24) on %s' % (u, RP_RAIL), net(u, 23) == RP_RAIL and net(u, 24) == RP_RAIL)
        chk('%s /OE low (always enabled)' % u, lvc(u, '~{OE}') == 'GND')
        chk('%s GND 11-13' % u, all(net(u, p) == 'GND' for p in (11, 12, 13)))
    chk('data translator DIR = GP%d (DIR_PIN)' % dir_pin, lvc(data, 'DIR') == rp(dir_pin))
    pu = through_r(rp(dir_pin), RP_RAIL)
    chk('DIR pulled up to %s (console -> cart through RP reset; firmware idles DIR = 1)' % RP_RAIL, pu is not None)
    if pu:
        r_pu = float(pu.replace('k', 'e3').replace('R', ''))
        # RP2040 datasheet 5.5.3: pad pull-down 50-80 kOhm; '4245A VIH 2.0 V (VCCA-referenced TTL)
        chk('DIR pull-up %s holds >= 2.0 V against a 50 kOhm pad pull-down at 3.0 V' % pu,
            3.0 * 50e3 / (50e3 + r_pu) >= 2.0)
    chk('control translator DIR tied high (CONS_5V: A -> B, console -> RP only)', lvc(ctrl, 'DIR') == 'CONS_5V')
    for k in range(1, 9):
        a = lvc(ctrl, 'A%d' % k)
        if a not in [edge[p] for p in EDGE]:
            chk('control translator spare A%d held at a rail (through a resistor)' % k,
                through_r(a, 'GND') is not None or through_r(a, 'CONS_5V') is not None)
            chk('control translator spare B%d open' % k, unconn(lvc(ctrl, 'B%d' % k)))

    # ---- /INTREQ: open drain through an N-FET, gate from GP16, pulled down ----
    q = [r for r in parts if r.startswith('Q') and func_net.get((r, 'D')) == edge[5]]
    chk('/INTREQ (J.5) on an N-FET drain', len(q) == 1)
    if q:
        g = func_net.get((q[0], 'G'))
        chk('/INTREQ FET gate = GP%d (INTREQ_PIN)' % intreq_pin, g == rp(intreq_pin))
        chk('/INTREQ FET source on GND', func_net.get((q[0], 'S')) == 'GND')
        chk('/INTREQ FET gate pulled down', through_r(g, 'GND') is not None)

    # ---- the activity LED ----
    led = rp(led_pin)
    led_r = [r for r in parts if r.startswith('R') and led in (net(r, 1), net(r, 2))]
    chk('GP%d (PICO_DEFAULT_LED_PIN) -> resistor -> LED anode -> GND' % led_pin, len(led_r) == 1 and any(
        net(d, 2) in (net(led_r[0], 1), net(led_r[0], 2)) and net(d, 1) == 'GND'
        for d in parts if d.startswith('D') and parts[d][0] == 'green'))

    # ---- RP2040 support ----
    chk('RP2040 flash: W25Q16JV (16 Mbit) = PICO_FLASH_SIZE_BYTES %d' % flash,
        flash == 2 * 1024 * 1024 and by_value('W25Q16JVSSIQ'))
    fl = by_value('W25Q16JVSSIQ')[0]
    for rpf, flf in (('~{QSPI_SS}', '~{CS}'), ('QSPI_SCLK', 'CLK'), ('QSPI_SD0', 'DI/IO_{0}'),
                     ('QSPI_SD1', 'DO/IO_{1}'), ('QSPI_SD2', '~{WP}/IO_{2}'), ('QSPI_SD3', '~{HOLD}/~{RESET}/IO_{3}')):
        chk('RP %s -> flash %s' % (rpf, flf), func_net.get((U_RP, rpf)) is not None and
            func_net.get((U_RP, rpf)) == func_net.get((fl, flf)))
    chk('flash VCC on %s' % RP_RAIL, func_net.get((fl, 'VCC')) == RP_RAIL)
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U_RP, 'USB_DP')), func_net.get((U_S3, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U_RP, 'USB_DM')), func_net.get((U_S3, 'USB_D-'))) == '27R')
    run, ss = func_net.get((U_RP, 'RUN')), func_net.get((U_RP, '~{QSPI_SS}'))
    chk('S3 IO%d (RUN forcing) -> 1k -> RP RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (BOOTSEL forcing) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up', through_r(run, RP_RAIL) == '10k')
    chk('RP TESTEN on GND', func_net.get((U_RP, 'TESTEN')) == 'GND')
    chk('RP XIN / XOUT to the 12 MHz crystal (XOUT through 1k)',
        any(parts[y][0] == '12MHz' and net(y, 1) == func_net.get((U_RP, 'XIN')) for y in parts) and
        through_r(func_net.get((U_RP, 'XOUT')), next(net(y, 3) for y in parts if parts[y][0] == '12MHz')) == '1k')
    vout = func_net.get((U_RP, 'VREG_VOUT'))
    for n_, nodes in nets.items():          # every supply pin (IOVDD x6, DVDD x2 repeat their names)
        for (ref, pin, f) in nodes:
            if ref == U_RP and f in ('IOVDD', 'USB_VDD', 'ADC_AVDD', 'VREG_VIN'):
                chk('RP %s (pin %s) on %s' % (f, pin, RP_RAIL), n_ == RP_RAIL)
            if ref == U_RP and f == 'DVDD':
                chk('RP DVDD (pin %s) on VREG_VOUT (the 1.1 V core regulator)' % pin, n_ == vout)

    # ---- power ----
    ldo = by_value('AP2112K-3.3')
    chk('AP2112K VIN/EN on +5V, VOUT on the RP rail', len(ldo) == 1 and func_net.get((ldo[0], 'VIN')) == '+5V'
        and func_net.get((ldo[0], 'EN')) == '+5V' and func_net.get((ldo[0], 'VOUT')) == RP_RAIL)
    ors = by_value('SS34')
    chk('SS34 diode-OR: CONS_5V and VBUS anodes, +5V cathodes',
        sorted(net(r, 2) for r in ors) == ['CONS_5V', 'VBUS'] and all(net(r, 1) == '+5V' for r in ors))
    chk('CONS_5V feeds only the OR diode, the translators\' VCCA / DIR and decoupling',
        all(r in ors + LVC or r == J_EDGE or r.startswith('C') for (r, p, f) in nets['CONS_5V']))
    buck = by_value('AP63203WU')
    chk('AP63203 IN on +5V, FB on +3V3', bool(buck) and func_net.get((buck[0], 'IN')) == '+5V'
        and func_net.get((buck[0], 'FB')) == '+3V3')
    chk('WS2812B VDD on +5V (datasheet 3.7-5.3 V)', net(WS, 4) == '+5V')

    # ---- S3 pins ----
    chk('SD CS  IO%d -> DAT3/CS' % sd['CS'], s3(sd['CS']) == net(J_SD, 2))
    chk('SD MOSI IO%d -> CMD' % sd['MOSI'], s3(sd['MOSI']) == net(J_SD, 3))
    chk('SD SCK IO%d -> CLK' % sd['SCK'], s3(sd['SCK']) == net(J_SD, 5))
    chk('SD MISO IO%d -> DAT0' % sd['MISO'], s3(sd['MISO']) == net(J_SD, 7))
    chk('microSD VDD on +3V3, VSS on GND', net(J_SD, 4) == '+3V3' and net(J_SD, 6) == 'GND')
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), net(WS, 3)) is not None)
    chk('UART0 TX IO%d / RX IO%d are the module TXD0 / RXD0 pins' % (uart_tx, uart_rx), (uart_tx, uart_rx) == (43, 44))
    chk('S3 TXD0 -> CP2102N RXD', func_net.get((U_S3, 'TXD0')) == func_net.get((U_CP, 'RXD')))
    chk('S3 RXD0 <- CP2102N TXD', func_net.get((U_S3, 'RXD0')) == func_net.get((U_CP, 'TXD')))
    for io in (3, 45, 46):
        chk('S3 strapping IO%d unloaded' % io, unconn(s3(io)))
    for io in range(26, 38):
        chk('S3 IO%d (flash / octal PSRAM on N16R8) unused' % io, unconn(s3(io)))

    # ---- general ----
    for n_, nodes in nets.items():
        if not n_.startswith('unconnected'):
            chk('net %s has >= 2 pins' % n_, len(nodes) >= 2)
    print('%d checks, %d failed, %d warnings' % (count, fails, warns))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
