#!/usr/bin/env python3
"""Cross-check the FujiNet-TRS80M1 Rev0 schematic netlist against the firmware that has to run on it --
independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from the fujinet-firmware tree ($FUJINET_FIRMWARE,
default ~/Workspace/fn-trs80m1: the TRS-80 bring-up's dev tree; nothing of pico/trs80m1 is on master
yet) at the git ref $FUJINET_FIRMWARE_REF (default '': the working tree; the files' sha256 are printed):
  pico/trs80m1/firmware/include/m1_card.h            M1_PIN_A0, M1_PIN_D0, WR, RD, IN, OUT, DRIVE, SYSRES,
                                                     INT, WAIT, DIP0, TXD, RXD, LED
  pico/trs80m1/firmware/boards/fujitrs80m1_rp2354b.h the RP2354B (B variant, 2 MB flash)
  include/pinmap/fujiversal-trs80m1.h                S3 SD / LED strip / UART pins
and checks every one of them, plus the Model I expansion edge (its own copy of the pinout), against
the pin *functions* the netlist reports (GPIOn on the RP2354B, IOn on the S3, the buffers' A / B / Y
pins): each header line must reach exactly its GPIO through exactly its buffer, the data lines through
their 75R too, and every bus-side input must have its 100k pull-down.

Firmware that does not yet match this board (INTAK* on GP32, the S3's RUN / BOOTSEL / card detect) is
reported as NOTE lines, not failures: the README lists the changes.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import hashlib, os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fn-trs80m1'))
REF = os.environ.get('FUJINET_FIRMWARE_REF', '')
SCH = os.path.join(PRJ, 'FujiNet-TRS80M1-Rev0.kicad_sch')
CARD = 'pico/trs80m1/firmware/include/m1_card.h'
BOARD = 'pico/trs80m1/firmware/boards/fujitrs80m1_rp2354b.h'
PINMAP = 'include/pinmap/fujiversal-trs80m1.h'

# The Model I expansion edge, Level II (TRS-80 Technical Reference Handbook 26-2103 p.91).  An
# independent copy of the map (tools/audit/header_pinout.py checks it against four sources).
EDGE = {1: 'RAS*', 2: 'SYSRES*', 3: 'CAS*', 4: 'A10', 5: 'A12', 6: 'A13', 7: 'A15', 8: 'GND', 9: 'A11',
        10: 'A14', 11: 'A8', 12: 'OUT*', 13: 'WR*', 14: 'INTAK*', 15: 'RD*', 16: 'MUX', 17: 'A9', 18: 'D4',
        19: 'IN*', 20: 'D7', 21: 'INT*', 22: 'D1', 23: 'TEST*', 24: 'D6', 25: 'A0', 26: 'D3', 27: 'A1',
        28: 'D5', 29: 'GND', 30: 'D0', 31: 'A4', 32: 'D2', 33: 'WAIT*', 34: 'A3', 35: 'A5', 36: 'A7',
        37: 'GND', 38: 'A6', 39: '+5V/GND', 40: 'A2'}
OPEN = ('RAS*', 'CAS*', 'MUX', 'TEST*', '+5V/GND')
STROBES = {'WR*': 'M1_PIN_WR', 'RD*': 'M1_PIN_RD', 'IN*': 'M1_PIN_IN', 'OUT*': 'M1_PIN_OUT',
           'SYSRES*': 'M1_PIN_SYSRES'}
INTAK_GPIO = 32           # this board's INTAK* line (no firmware macro yet)
# RP2350 datasheet Table 1674: GPIO0-39 on the QFN-80 are FT; nothing here puts 5 V on the RP, but the
# buffered lines stay off the ADC pins (GPIO40-47) anyway
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
    if m2:
        return int(m2.group(1))
    return int(v.rstrip('uUlL'), 0)


def ohms(v):
    m = re.match(r'([\d.]+)([kMR]?)', v.replace('4x', ''))
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1, '': 1}[m.group(2)]


def main():
    for f in (CARD, BOARD, PINMAP):
        print('firmware %s%s: sha256 %s' % (f, ' @' + REF if REF else ' (working tree of %s)' % FW,
                                             hashlib.sha256(read(f).encode()).hexdigest()[:16]))
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-trs80m1-rev0-check.xml')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn, SCH],
                   check=True, capture_output=True)
    t = ET.parse(fn)
    node_net, func_net, nets = {}, {}, {}
    canon = lambda n: n if n.startswith('unconnected') else n.rsplit('/', 1)[-1]   # /m1-bus/M1_A0 -> M1_A0
    for n in t.iter('net'):
        name = canon(n.get('name'))
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

    U1 = by_value('RP2354B')[0]
    U2 = by_value('ESP32-S3-WROOM-1-N16R8')[0]
    J1 = by_value('TRS-80 Model I expansion')[0]
    JSD = by_value('microSD')[0]
    UCP = by_value('CP2102N-A02-GQFN28')[0]
    WS = by_value('WS2812B-2020-V6')[0]
    LDO = by_value('AP2112K-3.3')[0]
    BUCK = by_value('TLV62569DBV')[0]
    ESD = by_value('USBLC6-2SC6')[0]
    B245 = by_value('74LVC245A')
    G17 = by_value('74LVC3G17')
    G07 = by_value('74LVC2G07')
    G11 = by_value('74LVC1G11')
    DIP = by_value('RAM EI RS232')
    chk('three 74LVC245A, two 74LVC3G17, one 74LVC2G07, one 74LVC1G11, one DIP switch',
        (len(B245), len(G17), len(G07), len(G11), len(DIP)) == (3, 2, 1, 1, 1))

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def rp_pins(fname):
        return [(pin, n) for n, nodes in nets.items() for (ref, pin, f) in nodes if ref == U1 and f == fname]

    def s3(io):
        return func_net.get((U2, 'IO%d' % io))

    def through_r(a, b, arrays=False):
        """a and b joined by exactly one resistor (an array element too, with arrays); its value."""
        for r, (val, fp, _) in parts.items():
            if r.startswith('R') and not r.startswith('RN'):
                if {node_net.get((r, '1')), node_net.get((r, '2'))} == {a, b}:
                    return val
            if arrays and r.startswith('RN'):
                for k in range(1, 5):
                    if {node_net.get((r, str(k))), node_net.get((r, str(9 - k)))} == {a, b}:
                        return val
        return None

    def across(net, kinds):
        """[(part, in_pin_function, out_net)] for every buffer channel whose input sits on net."""
        out = []
        for (ref, pin, f) in nets.get(net, []):
            if ref in B245 and re.match(r'[AB]\d$', f):
                other = ('B' if f[0] == 'A' else 'A') + f[1]
                out.append((ref, f, func_net.get((ref, other))))
            elif ref in G17 + G07 and re.match(r'\dA$', f):
                out.append((ref, f, func_net.get((ref, f[0] + 'Y'))))
            elif ref in G07 + G17 and re.match(r'\dY$', f):
                out.append((ref, f, func_net.get((ref, f[0] + 'A'))))
        return out

    # ---- firmware contracts ----
    a0, d0 = define(CARD, 'M1_PIN_A0'), define(CARD, 'M1_PIN_D0')
    gp = {k: define(CARD, m) for k, m in STROBES.items()}
    drive, gint, gwait = define(CARD, 'M1_PIN_DRIVE'), define(CARD, 'M1_PIN_INT'), define(CARD, 'M1_PIN_WAIT')
    dip0, txd, rxd, led = (define(CARD, n) for n in ('M1_PIN_DIP0', 'M1_PIN_TXD', 'M1_PIN_RXD', 'M1_PIN_LED'))
    hot = [a0 + i for i in range(16)] + [d0 + i for i in range(8)] + list(gp.values()) + [drive, gint, gwait]
    chk('m1_card.h: the hot pins are GPIO0-31 (one sio_hw->gpio_in read) and distinct',
        all(g < 32 for g in hot) and len(set(hot)) == len(hot))
    chk('m1_card.h: RD* on an odd pin (PWM-B counts it)', gp['RD*'] % 2 == 1)
    chk('fujitrs80m1_rp2354b.h: the B variant (PICO_RP2350A 0), 2 MB flash',
        define(BOARD, 'PICO_RP2350A') == 0 and re.search(r'PICO_FLASH_SIZE_BYTES \(2 \* 1024 \* 1024\)', read(BOARD)))
    if not re.search(r'M1_PIN_INTAK', read(CARD)):
        note('m1_card.h has no M1_PIN_INTAK: this board receives INTAK* on GP%d (README "Firmware changes")' % INTAK_GPIO)
    if 'provisional' in read(CARD):
        note('m1_card.h still calls its pin map provisional: this board implements it (README "Firmware changes")')

    # ---- the header: every edge pin ----
    hp = lambda p: node_net.get((J1, str(p)))
    chk('the header carries all 40 pins', sorted(int(p) for (r, p) in node_net if r == J1) == list(range(1, 41)))
    for p, sig in EDGE.items():
        n = hp(p)
        if sig == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
        elif sig in OPEN:
            chk('J1.%d (%s) is not connected' % (p, sig), unconnected(n))
    pd = lambda net: through_r(net, 'GND', arrays=True)
    # address: header -> '245 A -> B -> GPIO, always on, 100k pull-down
    for i in range(16):
        p = next(q for q, s in EDGE.items() if s == 'A%d' % i)
        n = hp(p)
        hops = across(n, None)
        ok = len(hops) == 1 and hops[0][0] in B245 and hops[0][1].startswith('A') and hops[0][2] == rp(a0 + i)
        chk('J1.%d A%d -> 74LVC245A A -> B -> GP%d (M1_PIN_A0 + %d)' % (p, i, a0 + i, i), ok)
        chk('A%d pulled down by 100k' % i, pd(n) == '4x100k')
        chk('A%d edge net touches only J1, its receiver and its pull-down' % i, len(nets.get(n, [])) == 3)
        chk('GP%d (A%d) touches only its receiver' % (a0 + i, i), len(nets.get(rp(a0 + i), [])) == 2)
    for ref in B245:
        if any(f.startswith('A') and f[1:].isdigit() and node_net.get((ref, pin), '').startswith('M1_A')
               for (r, pin, f) in sum(nets.values(), []) if r == ref):
            chk('%s (address): DIR high (+3V3_RP), /OE low' % ref,
                func_net.get((ref, 'A->B')) == '+3V3_RP' and func_net.get((ref, 'CE')) == 'GND')
        chk('%s VCC on +3V3_RP, GND' % ref, func_net.get((ref, 'VCC')) == '+3V3_RP' and func_net.get((ref, 'GND')) == 'GND')
    # data: header -> 75R -> '245 B <-> A -> GPIO; 100k pull-down on the buffer side
    dbuf = None
    for i in range(8):
        p = next(q for q, s in EDGE.items() if s == 'D%d' % i)
        n = hp(p)
        ds = next((node_net.get((r, str(9 - k))) for (r, pin, f) in nets.get(n, []) if r.startswith('RN')
                   for k in (int(pin),) if k <= 4), None)
        chk('J1.%d D%d -> 75R' % (p, i), ds is not None and through_r(n, ds, arrays=True) == '4x75R')
        hops = across(ds, None)
        ok = len(hops) == 1 and hops[0][0] in B245 and hops[0][1].startswith('B') and hops[0][2] == rp(d0 + i)
        chk('D%d -> 74LVC245A B <-> A -> GP%d (M1_PIN_D0 + %d)' % (i, d0 + i, i), ok)
        if ok:
            chk('D0-D7 share one transceiver', dbuf in (None, hops[0][0]))
            dbuf = hops[0][0]
        chk('D%d pulled down by 100k (buffer side)' % i, pd(ds) == '4x100k')
    if dbuf:
        chk('data transceiver DIR = GP%d (M1_PIN_DRIVE)' % drive, func_net.get((dbuf, 'A->B')) == rp(drive))
        oe = func_net.get((dbuf, 'CE'))
        g = G11[0]
        gin = {func_net.get((g, '')) for _ in (0,)}
        ins = {node_net.get((g, k)) for k in ('1', '3', '6')}
        chk('data /OE = 74LVC1G11 output = DRIVE . RD* . IN* (the buffered strobes)',
            node_net.get((g, '4')) == oe and ins == {rp(drive), rp(gp['RD*']), rp(gp['IN*'])})
        chk('74LVC1G11 on +3V3_RP', node_net.get((g, '5')) == '+3V3_RP' and node_net.get((g, '2')) == 'GND')
        dr = through_r(rp(drive), 'GND')
        chk('DRIVE pulled down (%s) under RP2350-E9\'s 8.2 kOhm' % dr, dr is not None and ohms(dr) <= 8.2e3)
    # strobes and INTAK*: header -> 74LVC3G17 (Schmitt) -> GPIO, 100k pull-down
    for sig, g in list(gp.items()) + [('INTAK*', INTAK_GPIO)]:
        p = next(q for q, s in EDGE.items() if s == sig)
        n = hp(p)
        hops = across(n, None)
        chk('J1.%d %s -> 74LVC3G17 (Schmitt) -> GP%d' % (p, sig, g),
            len(hops) == 1 and hops[0][0] in G17 and hops[0][2] == rp(g))
        chk('%s pulled down by 100k' % sig, pd(n) == '4x100k')
    for ref in G17 + G07:
        chk('%s VCC on +3V3_RP' % ref, func_net.get((ref, 'VCC')) == '+3V3_RP' and func_net.get((ref, 'GND')) == 'GND')
    # INT*, WAIT*: GPIO -> 74LVC2G07 (open drain) -> header, the driver's input pulled up
    for sig, g in (('INT*', gint), ('WAIT*', gwait)):
        p = next(q for q, s in EDGE.items() if s == sig)
        n = hp(p)
        hops = across(n, None)
        chk('GP%d -> 74LVC2G07 (open drain) -> J1.%d %s' % (g, p, sig),
            len(hops) == 1 and hops[0][0] in G07 and hops[0][2] == rp(g))
        chk('%s driver input pulled up (off through reset)' % sig, through_r(rp(g), '+3V3_RP') is not None)
        chk('%s has no pull-down (the Z80\'s own 4.7k pull-up holds it)' % sig, pd(n) is None)
    # DIPs, debug UART, LED
    for k, n in enumerate(('RAM', 'EI', 'RS232')):
        g = dip0 + k
        net = rp(g)
        chk('GP%d (DIP %s) -> the switch -> GND, pulled up' % (g, n),
            net is not None and through_r(net, '+3V3_RP', arrays=True) is not None and
            any(r in DIP for (r, _, _) in nets.get(net, [])))
    for g, net in ((txd, 'DBG_TX'), (rxd, 'DBG_RX')):
        chk('GP%d (%s) on a test pad' % (g, net), rp(g) == net and any(r.startswith('TP') for r, _, _ in nets[net]))
    chk('GP%d (M1_PIN_LED) -> R -> LED' % led, through_r(rp(led), 'RP_LED_A') is not None)
    used = set(hot) | {INTAK_GPIO, dip0, dip0 + 1, dip0 + 2, txd, rxd, led}
    for g in sorted(set(range(48)) - used):
        chk('GP%d unused' % g, unconnected(rp(g)))

    # ---- RP2354B support ----
    pm = PINMAP
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    u0rx, u0tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN', -2), define(pm, 'PIN_RP2040_BOOTSEL', -2)
    cd_io = define(pm, 'PIN_CARD_DETECT', -2)
    if run_io < 0 or bsel_io < 0:
        note('fujiversal-trs80m1.h has no PIN_RP2040_RUN / PIN_RP2040_BOOTSEL: this board wires S3 IO4 / IO5 '
             'to the RP\'s RUN / QSPI_SS (as every on-cart S3 board); the pin map needs them')
        run_io, bsel_io = 4, 5
    if cd_io < 0:
        note('fujiversal-trs80m1.h PIN_CARD_DETECT is NC: this board wires the microSD card detect to IO42')
        cd_io = 42
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((U2, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((U2, 'USB_D-'))) == '27R')
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (RUN) -> 1k -> RP RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
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
    dvdd_caps = [r for r, _, _ in nets['DVDD'] if r.startswith('C')]
    chk('DVDD: a capacitor for each of its 3 pins + the regulator output (%d)' % len(dvdd_caps), len(dvdd_caps) >= 4)
    lx = func_net.get((U1, 'VREG_LX'))
    chk('VREG_LX -> 3.3uH -> DVDD', any(val == '3.3uH' and {node_net.get((r, '1')), node_net.get((r, '2'))} == {lx, 'DVDD'}
                                        for r, (val, _, _) in parts.items() if r.startswith('L')))
    chk('+3V3_RP is the AP2112K output', node_net.get((LDO, '5')) == '+3V3_RP')
    chk('RP LDO input and enable on +5V', node_net.get((LDO, '1')) == '+5V' and node_net.get((LDO, '3')) == '+5V')
    xo = func_net.get((U1, 'XOUT'))
    chk('crystal: XIN direct, XOUT through 1k', through_r(xo, 'XOUT_Y') == '1k')
    chk('RP GND / VREG_PGND on GND', func_net.get((U1, 'GND')) == 'GND' and func_net.get((U1, 'VREG_PGND')) == 'GND')

    # ---- power: USB only, the fuse, the buck ----
    chk('VBUS -> resettable fuse -> +5V', any(r.startswith('F') and {node_net.get((r, '1')), node_net.get((r, '2'))} ==
                                              {'VBUS', '+5V'} for r in parts))
    b = lambda f: func_net.get((BUCK, f))
    chk('TLV62569 VIN and EN on +5V (EN terminated: datasheet 7.4.1)', b('VIN') == '+5V' and b('EN') == '+5V')
    fh, fl = through_r('+3V3', b('FB')), through_r(b('FB'), 'GND')
    chk('TLV62569 FB divider from +3V3', fh is not None and fl is not None)
    if fh and fl:
        v = 0.6 * (1 + ohms(fh) / ohms(fl))
        chk('buck output %.3f V (VFB 0.588-0.612: %.2f-%.2f V) inside 3.0-3.6 V (ESP32-S3 VDD)' % (
            v, v * 0.98, v * 1.02), 3.0 <= v * 0.98 and v * 1.02 <= 3.6)
        chk('TLV62569 R2 (%s) <= 200 kOhm (datasheet 8.2.2.2)' % fl, ohms(fl) <= 200e3)
    chk('TLV62569 SW -> 2.2uH -> +3V3', any(val == '2.2uH' and {node_net.get((r, '1')), node_net.get((r, '2'))} ==
                                            {b('SW'), '+3V3'} for r, (val, _, _) in parts.items() if r.startswith('L')))

    # ---- USB-C ----
    esd = lambda p: node_net.get((ESD, p))
    chk('USBLC6: D- on I/O1 (1, 6), D+ on I/O2 (3, 4), VBUS clamp, GND',
        esd('1') == esd('6') == func_net.get((UCP, 'D-')) and esd('3') == esd('4') == func_net.get((UCP, 'D+'))
        and esd('5') == 'VBUS' and esd('2') == 'GND')
    chk('CP2102N RSTb pull-up 1k (datasheet)', through_r(func_net.get((UCP, '~{RST}')), '+3V3') == '1k')
    chk('CC1 / CC2 5.1k Rd to GND', all(through_r(n, 'GND') == '5.1k' for n in ('CC1', 'CC2')))

    # ---- S3 pins ----
    chk('SD CS  IO%d -> DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((JSD, '2')))
    chk('SD MOSI IO%d -> CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((JSD, '3')))
    chk('SD SCK IO%d -> CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((JSD, '5')))
    chk('SD MISO IO%d -> DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((JSD, '7')))
    chk('SD card detect IO%d -> CD' % cd_io, s3(cd_io) == node_net.get((JSD, '9')))
    chk('microSD VDD on +3V3, VSS on GND', node_net.get((JSD, '4')) == '+3V3' and node_net.get((JSD, '6')) == 'GND')
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
        dnp = field(r, 'dnp') or parts[r][2].find('property[@name="dnp"]') is not None
        if not r.startswith(('TP', '#', 'H')) and r != by_value('LA probe')[0]:
            chk('%s has an LCSC code' % r, bool(field(r, 'LCSC')))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
