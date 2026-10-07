#!/usr/bin/env python3
"""Cross-check the Fujiversal-Atari2600 Rev1 schematic netlist against the
firmware that has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from the fujinet-firmware
tree holding the 2600 port (default ~/Workspace/fn-2600, or $FUJINET_FIRMWARE):
  pico/atari-2600/firmware/include/vcs_pins.h        ADDR_PIN, ADDR_BITS, D0_PIN, DIR_PIN
  pico/atari-2600/firmware/boards/fujivcs.cmake      PICO_PLATFORM, PICO_FLASH_SIZE_BYTES
  pico/atari-2600/firmware/boards/fujivcs.h          -> boards/pico.h (LED = GP25)
  include/pinmap/fujiversal-atari2600.h              S3 SD/LED/UART/RUN/BOOTSEL pins
and checks every one of them, plus the Atari 2600 edge map, against the pin
*functions* the netlist reports (GPIOn on the RP2354A, IOn on the S3).  Rev1
wires the bus straight from the fingers to the RP's 5 V-tolerant pads, so
each edge net must touch exactly J1 and the right GPIO.

Firmware that does not yet match this board (fujivcs is still an RP2040
board) is reported as NOTE lines, not failures: the README lists the port.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fn-2600'))
SCH = os.path.join(PRJ, 'Fujiversal-Atari2600-Rev1.kicad_sch')

# Atari 2600 cartridge connector, pins 1-24 (1-12 console-front face,
# 13-24 rear face; pin 1 behind pin 24).  Independent copy of the map.
EDGE = {1: 'A7', 2: 'A6', 3: 'A5', 4: 'A4', 5: 'A3', 6: 'A2', 7: 'A1', 8: 'A0',
        9: 'D0', 10: 'D1', 11: 'D2', 12: 'GND', 13: 'D3', 14: 'D4', 15: 'D5', 16: 'D6',
        17: 'D7', 18: 'A12', 19: 'A10', 20: 'A11', 21: 'A9', 22: 'A8', 23: '+5V', 24: 'GND'}
# RP2350 datasheet Table 1427: on the QFN-60 package GPIO0-25 are "Digital IO (FT)"
# (5.5 V with IOVDD at 3.3 V); GPIO26-29 share the ADC and are not 5 V tolerant.
FT_GPIOS = range(26)

fails = 0
count = 0


def chk(desc, ok):
    global fails, count
    count += 1
    if not ok:
        fails += 1
        print('FAIL:', desc)


def note(desc):
    print('NOTE:', desc)


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


def ohms(v):
    m = re.match(r'([\d.]+)([kMR]?)', v)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1, '': 1}[m.group(2)]


def main():
    fn = os.path.join(tempfile.gettempdir(), 'fujiversal-2600-rev1-check.xml')
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
            func_net.setdefault((ref, fn_), name)
            nets.setdefault(name, []).append((ref, pin, fn_))
    parts = {c.get('ref'): (c.findtext('value'), c.findtext('footprint'), c) for c in t.iter('comp')}
    by_value = lambda v: sorted(r for r, (val, _, _) in parts.items() if val == v)
    field = lambda ref, k: next((f.text for f in parts[ref][2].iter('field') if f.get('name') == k), None)
    unconnected = lambda n: n is None or n.startswith('unconnected')

    U1 = by_value('RP2354A')[0]
    U2 = by_value('ESP32-S3-WROOM-1-N16R8')[0]
    J1 = by_value('Atari2600_Cart_Edge_24')[0]
    J2 = by_value('microSD')[0]
    UCP = by_value('CP2102N-A02-GQFN28')[0]
    WS = by_value('WS2812B-2020-V6')[0]
    LDO = by_value('AP2112K-3.3')[0]

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def rp_pins(fname):
        return [(pin, n) for n, nodes in nets.items() for (ref, pin, f) in nodes if ref == U1 and f == fname]

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

    # ---- firmware contracts ----
    vp = 'pico/atari-2600/firmware/include/vcs_pins.h'
    addr_pin, addr_bits = define(vp, 'ADDR_PIN'), define(vp, 'ADDR_BITS')
    d0_pin, dir_pin = define(vp, 'D0_PIN'), define(vp, 'DIR_PIN')
    chk('vcs_pins.h: 13 address bits', addr_bits == 13)
    cm = 'pico/atari-2600/firmware/boards/fujivcs.cmake'
    plat = cmake_set(cm, 'PICO_PLATFORM')
    if plat != 'rp2350':
        note('fujivcs.cmake PICO_PLATFORM is %s: this RP2354A board needs an rp2350 board file '
             '(README "Firmware changes this board needs")' % plat)
    flash = int(cmake_set(cm, 'PICO_FLASH_SIZE_BYTES'))
    chk('PICO_FLASH_SIZE_BYTES (%d) = the RP2354A\'s 2 MB in-package flash' % flash, flash == 2 * 1024 * 1024)
    bh = open(os.path.join(FW, 'pico/atari-2600/firmware/boards/fujivcs.h')).read()
    chk('fujivcs.h is a pico-family board (PICO_DEFAULT_LED_PIN = GP25)', 'boards/pico' in bh)
    pm = 'include/pinmap/fujiversal-atari2600.h'
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN'), define(pm, 'PIN_RP2040_BOOTSEL')
    u0rx, u0tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')

    # ---- edge -> RP2354A, direct ----
    for p, sig in EDGE.items():
        n = node_net.get((J1, str(p)))
        if sig == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
            continue
        if sig == '+5V':
            chk('J1.23 (+5V) is CONS_5V', n == 'CONS_5V')
            continue
        bit = int(sig[1:])
        gp = addr_pin + bit if sig[0] == 'A' else d0_pin + bit
        chk('J1.%d %s -> GP%d directly' % (p, sig, gp), n is not None and rp(gp) == n)
        chk('GP%d (%s) is a 5 V-tolerant pad' % (gp, sig), gp in FT_GPIOS)
        others = [(r, pin) for (r, pin, f) in nets.get(n, []) if r not in (J1, U1)]
        chk('edge net %s touches only J1 and U1' % n, not others)
    chk('DIR_PIN GP%d (the RP2040 board\'s buffer direction) is not wired on this board' % dir_pin,
        unconnected(rp(dir_pin)))
    note('vcs_pins.h still defines DIR_PIN %d; on Rev1 the firmware should drop it' % dir_pin)
    cons = nets['CONS_5V']
    chk('console 5V feeds only the P-FET, its caps and the sense divider',
        all(r.startswith(('J', 'Q', 'C', 'R')) for (r, _, _) in cons))

    # ---- console 5 V sense ----
    vs = rp(27)
    chk('GP27 = VSENSE', vs == 'VSENSE')
    hi, lo = through_r('CONS_5V', vs), through_r(vs, 'GND')
    chk('VSENSE divider CONS_5V -> R -> GP27 -> R -> GND', hi is not None and lo is not None)
    if hi and lo:
        v = 5.25 * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE at a 5.25 V console (%.2f V) under IOVDD (GP27 is not 5 V tolerant)' % v, v <= 3.3)
        v = 4.5 * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE at a 4.5 V console (%.2f V) above VIH 2.0 V' % v, v >= 2.0)

    # ---- RP2354A support ----
    chk('GP25 (PICO_DEFAULT_LED_PIN) -> R -> LED', through_r(rp(25), 'RP_LED_A') is not None)
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((U2, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((U2, 'USB_D-'))) == '27R')
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (PIN_RP2040_RUN) -> 1k -> RP RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (PIN_RP2040_BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up to the RP rail', through_r(run, '+3V3_RP') == '10k')
    chk('QSPI_SS pull-up to the RP rail', through_r(ss, '+3V3_RP') == '10k')
    for f in ('QSPI_SCLK', 'QSPI_SD0', 'QSPI_SD1', 'QSPI_SD2', 'QSPI_SD3'):
        chk('RP %s unconnected (the flash is in the package)' % f, unconnected(func_net.get((U1, f))))
    for f in ('IOVDD', 'QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN'):
        pins = rp_pins(f)
        chk('RP %s present' % f, bool(pins))
        for pin, n in pins:
            chk('RP %s (pin %s) on +3V3_RP' % (f, pin), n == '+3V3_RP')
    chk('VREG_AVDD from +3V3_RP through 33R (datasheet Figure 19)', through_r('+3V3_RP', func_net.get((U1, 'VREG_AVDD'))) == '33R')
    for pin, n in rp_pins('DVDD') + rp_pins('VREG_FB'):
        chk('RP DVDD/VREG_FB (pin %s) on DVDD' % pin, n == 'DVDD')
    lx = func_net.get((U1, 'VREG_LX'))
    chk('VREG_LX -> 3.3uH -> DVDD', any(val == '3.3uH' and {node_net.get((r, '1')), node_net.get((r, '2'))} == {lx, 'DVDD'}
                                        for r, (val, _, _) in parts.items() if r.startswith('L')))
    chk('+3V3_RP is the AP2112K output', func_net.get((LDO, 'VO')) == '+3V3_RP' or node_net.get((LDO, '5')) == '+3V3_RP')
    chk('RP LDO input on +5V', node_net.get((LDO, '1')) == '+5V')
    xo = func_net.get((U1, 'XOUT'))
    chk('crystal: XIN direct, XOUT through 1k', through_r(xo, 'XOUT_Y') == '1k')
    chk('RP GND / VREG_PGND on GND', func_net.get((U1, 'GND')) == 'GND' and func_net.get((U1, 'VREG_PGND')) == 'GND')

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
        chk('S3 strapping IO%d left alone' % io, unconnected(s3(io)))
    for io in range(26, 38):
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, unconnected(s3(io)))

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
