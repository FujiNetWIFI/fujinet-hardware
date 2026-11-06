#!/usr/bin/env python3
"""Cross-check the Inty-FujiCard schematic netlist against the firmware that has to run on it --
independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from the fujinet-firmware tree ($FUJINET_FIRMWARE,
default ~/Workspace/fujinet-firmware) at the git ref $FUJINET_FIRMWARE_REF (default origin/master;
'' reads the working tree):
  pico/intellivision/firmware/boards/fujicard.h    the cart bus (MI_AD0_PIN, MI_MSYNC_PIN, MI_BDIR_PIN,
                                                   MI_BC1_PIN, MI_BC2_PIN, MI_RST_PIN), MI_LED_PIN, the
                                                   debug UART, the self-test pin
  pico/intellivision/firmware/boards/pintycard.h   MI_AUDIO_PIN (ECS audio; fujicard.h defines none)
  include/pinmap/fujiversal-intv.h                 the S3's SD, UART0, LED strip, RP RUN / BOOTSEL pins
and checks them, plus the Intellivision edge (its own copy of the cartridge pinout and of the finger
numbering, below), against the pin *functions* the netlist reports (GPIOn on the RP2354A, IOn on
the S3, the microSD's and the CP2102N's pin names, B / C / E on the transistors).

Firmware that does not match this board is reported as NOTE lines, not failures: README "Firmware".

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
REF = os.environ.get('FUJINET_FIRMWARE_REF', 'origin/master')
SCH = os.path.join(PRJ, 'Inty-FujiCard.kicad_sch')
BOARD_H = 'pico/intellivision/firmware/boards/fujicard.h'
PINTY_H = 'pico/intellivision/firmware/boards/pintycard.h'
S3_H = 'include/pinmap/fujiversal-intv.h'

# The Intellivision cartridge port, INTV pin -> signal (an independent copy: the attic
# FujiNet-INTV-Rev0's edge, traced from the PiNTY CARD's gerbers).  Even pins on the component face,
# odd behind; the finger A(k) (component face, left to right) is pin 46 - 2k, B(k) is 45 - 2k.
INTV = {1: 'GND', 3: 'MSYNC', 5: 'D7', 6: 'EXT_AUDIO', 7: 'D8', 8: 'GND', 9: 'D6', 10: 'GND', 11: 'D9',
        12: 'RESET', 13: 'D5', 15: 'D10', 17: 'D4', 19: 'D11', 20: 'GND', 21: 'D3', 22: 'GND', 23: 'D12',
        24: 'GND', 25: 'D13', 26: 'GND', 27: 'D2', 28: 'GND', 29: 'D14', 31: 'D1', 33: 'D0', 35: 'D15',
        37: 'BDIR', 39: 'BC2', 41: 'BC1', 43: '+5V', 44: 'GND'}
NC_PINS = (2, 4, 14, 16, 18, 30)
PASS = ((32, 42), (34, 40), (36, 38))           # shorted pairs: the cart passes these through
pad = lambda pin: ('A%d' % ((46 - pin) // 2)) if pin % 2 == 0 else ('B%d' % ((45 - pin) // 2))
# RP2350 datasheet: on the QFN-60 GPIO0-25 are "Digital IO (FT)" (5 V tolerant with IOVDD up);
# GPIO26-29 share the ADC and are not (VPIN max IOVDD + 0.5 V)
FT = range(26)

fails = count = 0


def chk(desc, ok):
    global fails, count
    count += 1
    if not ok:
        fails += 1
        print('FAIL:', desc)


def note(desc):
    print('NOTE:', desc)


def read(path):
    if REF:
        return subprocess.run(['git', '-C', FW, 'show', '%s:%s' % (REF, path)], check=True,
                              capture_output=True, text=True).stdout
    return open(os.path.join(FW, path)).read()


def define(path, name, default=None):
    m = re.search(r'#define\s+%s\s+(\S+)' % re.escape(name), read(path))
    if not m:
        if default is not None:
            return default
        raise SystemExit('%s: no #define %s' % (path, name))
    v = m.group(1)
    if v == 'GPIO_NUM_NC':
        return -1
    m2 = re.match(r'GPIO_NUM_(\d+)', v)
    return int(m2.group(1)) if m2 else int(v.rstrip('uUlL'), 0)


def main():
    fd, fn = tempfile.mkstemp(prefix='inty-check-', suffix='.xml')
    os.close(fd)
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn, SCH],
                   check=True, capture_output=True)
    t = ET.parse(fn)
    os.remove(fn)
    node_net, func, nets = {}, {}, {}
    canon = lambda n: n if n.startswith('unconnected') else n.rsplit('/', 1)[-1]
    for n in t.iter('net'):
        name = canon(n.get('name'))
        for nd in n.iter('node'):
            ref, pin, f = nd.get('ref'), nd.get('pin'), (nd.get('pinfunction') or '')
            f = re.sub(r'_%s$' % re.escape(pin), '', f)
            node_net[(ref, pin)] = name
            func.setdefault((ref, f), name)
            nets.setdefault(name, []).append((ref, pin, f))
    parts = {c.get('ref'): c.findtext('value') for c in t.iter('comp')}
    one = lambda v: next(r for r, val in parts.items() if val == v)
    RP, S3, EDGE, SD, CP, LED = (one('RP2354A'), one('ESP32-S3-WROOM-1-N16R8'), one('INTV_Cart_Edge_44'),
                                 one('microSD'), one('CP2102N-A02-GQFN28'), one('SK6805-EC20'))
    unconnected = lambda n: n is None or n.startswith('unconnected')
    rp = lambda g: next((n for (r, f), n in func.items() if r == RP and re.match(r'GPIO%d(/|$)' % g, f)), None)
    s3 = lambda io: func.get((S3, 'IO%d' % io)) or func.get((S3, {19: 'USB_D-', 20: 'USB_D+', 43: 'TXD0', 44: 'RXD0'}.get(io, '')))
    edge = lambda pin: node_net.get((EDGE, pad(pin)))
    others = lambda net, *keep: [(r, p) for r, p, f in nets.get(net, []) if r not in keep]

    def through(net, prefix='R'):
        """The nets on the far side of every 2-pin part with this prefix that touches net."""
        out = []
        for r, p, f in nets.get(net, []):
            if r.rstrip('0123456789') == prefix:
                other = node_net.get((r, '2' if p == '1' else '1'))
                out.append((r, other))
        return out

    def npn_on_collector(net):
        """[(ref, base net, emitter net)] of every transistor whose collector is on net."""
        return [(r, func.get((r, 'B')), func.get((r, 'E'))) for r, p, f in nets.get(net, []) if f == 'C']

    # ---- the edge ----------------------------------------------------------------
    AD0 = define(BOARD_H, 'MI_AD0_PIN')
    bus = {'MSYNC': define(BOARD_H, 'MI_MSYNC_PIN'), 'BDIR': define(BOARD_H, 'MI_BDIR_PIN'),
           'BC1': define(BOARD_H, 'MI_BC1_PIN'), 'BC2': define(BOARD_H, 'MI_BC2_PIN')}
    bus.update({'D%d' % i: AD0 + i for i in range(16)})
    for pin, sig in sorted(INTV.items()):
        n = edge(pin)
        if sig in bus:
            g = bus[sig]
            chk('INTV pin %d (%s, finger %s) straight to GP%d, nothing else on it' % (pin, sig, pad(pin), g),
                n is not None and n == rp(g) and len(nets[n]) == 2)
            if g not in FT:
                note('INTV pin %d (%s) meets GP%d directly: an ADC pin, not 5 V tolerant (RP2350 datasheet: '
                     'GPIO26-29 VPIN max IOVDD + 0.5 V); as on the PiNTY CARD' % (pin, sig, g))
        elif sig == 'GND':
            chk('INTV pin %d (finger %s) on GND' % (pin, pad(pin)), n == 'GND')
        elif sig == '+5V':
            chk('INTV pin 43 (+5V, finger %s) on VSYS, into an SS34\'s anode' % pad(pin),
                n == 'VSYS' and any(f == 'A' and parts[r] == 'SS34' for r, p, f in nets[n]))
    for pin in NC_PINS:
        chk('INTV pin %d (finger %s) not connected' % (pin, pad(pin)), unconnected(edge(pin)))
    for a, b in PASS:
        n = edge(a)
        chk('INTV pins %d / %d joined, nothing else on them' % (a, b),
            n is not None and n == edge(b) and sorted(p for r, p, f in nets[n]) == sorted([pad(a), pad(b)]))
    # /RESET: an open collector, its base driven from MI_RST_PIN through a resistor
    rst = define(BOARD_H, 'MI_RST_PIN')
    q = npn_on_collector(edge(12))
    ok = len(q) == 1 and q[0][2] == 'GND' and any(o == rp(rst) for _, o in through(q[0][1]))
    chk('INTV pin 12 (/RESET) on an NPN collector (emitter GND) whose base GP%d drives through a resistor '
        '(GP%d high = console reset; cartridge.c drives it as an output)' % (rst, rst), ok and len(nets[edge(12)]) == 2)
    # ECS audio
    aud = define(PINTY_H, 'MI_AUDIO_PIN')
    chk('INTV pin 6 (EXT_AUDIO) from GP%d (pintycard.h MI_AUDIO_PIN) through a resistor' % aud,
        any(o == rp(aud) for _, o in through(edge(6))))
    if define(BOARD_H, 'MI_AUDIO_PIN', -2) == -2:
        note('fujicard.h has no MI_AUDIO_PIN (and fujicard.cmake CONFIG_ECS_AUDIO OFF): this board wires GP28 '
             'to EXT_AUDIO as pintycard.h does')

    # ---- the RP2354A's other pins ---------------------------------------------------
    for name, label in (('MI_LED_PIN', 'the activity LED'), ('MI_DBG_UART_TX_PIN', 'the debug UART TX'),
                        ('FUJI_SELFTEST_TRIGGER_PIN', 'the self-test trigger')):
        g = define(BOARD_H, name, -1)
        if g >= 0 and unconnected(rp(g)):
            note('fujicard.h %s %d (%s): GP%d is not connected on this board' % (name, g, label, g))
    for g, lab in ((16, 'TX'), (17, 'RX')):
        tp = [r for r, p, f in nets.get(rp(g), []) if parts[r] == lab]
        chk('GP%d on the %s test pad' % (g, lab), len(tp) == 1)
    note('the board\'s TX / RX pads are GP16 / GP17; fujicard.h puts the debug TX on GP%d'
         % define(BOARD_H, 'MI_DBG_UART_TX_PIN', -1))
    # USB to the S3, through 27R each way
    for f_rp, io in (('USB_DP', 20), ('USB_DM', 19)):
        n = func.get((RP, f_rp))
        far = [(r, o) for r, o in through(n) if o == s3(io)]
        chk('RP %s to S3 IO%d through one 27R' % (f_rp, io), len(far) == 1 and parts[far[0][0]] == '27R')
    chk('RP RUN pulled up to 3V3', any(o == '3V3' for _, o in through(func.get((RP, 'RUN')))))
    chk('RP QSPI_SS pulled up to 3V3', any(o == '3V3' for _, o in through(func.get((RP, '~{QSPI_SS}')))))
    for f in ('QSPI_SD0', 'QSPI_SD1', 'QSPI_SD2', 'QSPI_SD3', 'QSPI_SCLK'):
        chk('RP %s not connected (the flash is in the package)' % f, unconnected(func.get((RP, f))))

    # ---- the S3 ---------------------------------------------------------------
    for name, sdpin in (('PIN_SD_HOST_CS', 'DAT3/CS'), ('PIN_SD_HOST_SCK', 'CLK'), ('PIN_SD_HOST_MISO', 'DAT0/DO'),
                        ('PIN_SD_HOST_MOSI', 'CMD/DI')):
        io = define(S3_H, name)
        chk('%s IO%d on the microSD\'s %s' % (name, io, sdpin), s3(io) is not None and s3(io) == func.get((SD, sdpin)))
    for sdpin in ('DAT3/CS', 'DAT0/DO', 'CMD/DI', 'DAT1', 'DAT2'):
        chk('microSD %s pulled up to 3V3' % sdpin, any(r.startswith('RN') for r, p, f in nets.get(func.get((SD, sdpin)), [])))
    chk('PIN_CARD_DETECT not connected, as the pin map says', define(S3_H, 'PIN_CARD_DETECT') == -1 and
        unconnected(func.get((SD, 'CD'))))
    led = define(S3_H, 'PIN_LED_STRIP')
    chk('PIN_LED_STRIP IO%d to the SK6805\'s DIN through a resistor' % led,
        any(o == func.get((LED, 'DIN')) for _, o in through(s3(led))))
    chk('PIN_UART0_TX IO%d to the CP2102N\'s RXD' % define(S3_H, 'PIN_UART0_TX'),
        s3(define(S3_H, 'PIN_UART0_TX')) == func.get((CP, 'RXD')))
    chk('PIN_UART0_RX IO%d to the CP2102N\'s TXD' % define(S3_H, 'PIN_UART0_RX'),
        s3(define(S3_H, 'PIN_UART0_RX')) == func.get((CP, 'TXD')))
    for name, target, rp_f in (('PIN_RP2040_RUN', 'RUN', 'RUN'), ('PIN_RP2040_BOOTSEL', 'QSPI_SS', '~{QSPI_SS}')):
        io = define(S3_H, name)
        bases = [(r, o) for r, o in through(s3(io))]
        ok = False
        for r, base in bases:
            for q_ in [x for x, p, f in nets.get(base, []) if f == 'B']:
                col, em = func.get((q_, 'C')), func.get((q_, 'E'))
                hit = col == func.get((RP, rp_f)) or any(o == func.get((RP, rp_f)) for _, o in through(col))
                ok |= hit and em == 'GND'
        chk('%s IO%d drives an NPN (through a resistor) that pulls the RP\'s %s low' % (name, io, target), ok)
    note('this board asserts RP RUN / BOOTSEL through NPNs (Q4 / Q3): the S3 must drive IO%d / IO%d HIGH; '
         'fnPicoUpdater::forceBootselViaPins() drives them LOW (for a direct 1k link), so that recovery path does '
         'nothing here (the USB mailbox doorbell, the normal path, is unaffected)'
         % (define(S3_H, 'PIN_RP2040_RUN'), define(S3_H, 'PIN_RP2040_BOOTSEL')))

    # ---- power ------------------------------------------------------------------
    vin_d = [r for r, p, f in nets.get('VIN', []) if f == 'K' and parts[r] == 'SS34']
    anodes = sorted(func.get((r, 'A')) for r in vin_d)
    chk('VIN the diode-OR of VSYS (console) and VBUS (USB): two SS34 cathodes', anodes == ['VBUS', 'VSYS'])
    buck = one('AP63203WU')
    chk('AP63203WU (3.3 V fixed) in from VIN, FB on 3V3, EN on VIN',
        func.get((buck, 'IN')) == 'VIN' and func.get((buck, 'FB')) == '3V3' and func.get((buck, 'EN')) == 'VIN')
    iovdd = [n for r, p, f in [(r, p, f) for n_, l in nets.items() for (r, p, f) in l] if r == RP and f == 'IOVDD'
             for n in [node_net[(r, p)]]]
    chk('every RP IOVDD on 3V3 (%d pins)' % len(iovdd), iovdd and all(n == '3V3' for n in iovdd))
    dvdd = {node_net[(r, p)] for n, l in nets.items() for (r, p, f) in l if r == RP and f == 'DVDD'}
    chk('every RP DVDD on the core regulator\'s output (VREG_FB, through L1 from VREG_LX)',
        dvdd == {func.get((RP, 'VREG_FB'))} and any(o == func.get((RP, 'VREG_LX'))
                                                     for _, o in through(func.get((RP, 'VREG_FB')), 'L')))
    chk('S3 EN pulled up, with its RC', any(o == '3V3' for _, o in through(func.get((S3, 'EN')))) and
        any(o == 'GND' for _, o in through(func.get((S3, 'EN')), 'C')))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
