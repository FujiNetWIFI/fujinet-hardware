#!/usr/bin/env python3
"""Cross-check the FujiNet-ColecoVision Rev0 schematic netlist against the firmware that
has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from the fujinet-firmware
tree ($FUJINET_FIRMWARE, default ~/Workspace/fujinet-firmware) at the git ref
$FUJINET_FIRMWARE_REF (default origin/master; '' reads the working tree):
  pico/coleco/firmware/include/coleco_cart.h   ADDR_MASK (A0-A14), D0_PIN / DATA_MASK (D0-D7), CE_PIN,
                                               DIR_PIN, PWR_PIN
  pico/coleco/firmware/boards/fujicoleco.*     the board (PICO_DEFAULT_LED_PIN via boards/pico.h, platform)
  include/pinmap/fujiversal-coleco.h           S3 SD / LED strip / UART pins
and checks every one of them, plus the ColecoVision edge map (its own copy, from MAME's
bus/coleco/cartridge/exp.h), against the pin *functions* the netlist reports (GPIOn on the RP2350A,
An / Bn on the 74LVC245A, IOn on the S3).  Each address line must reach exactly its GPIO through one
330R; each data line its '245 A pin, the matching B pin its GPIO; the four selects must AND into the
'245's /OE and CE_PIN, each pulled up.

Firmware that does not yet match this board (pico/coleco builds a stock-Pico RP2040; the S3 pin map
lacks RUN / BOOTSEL / card detect) is reported as NOTE lines, not failures: the README lists the port.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
REF = os.environ.get('FUJINET_FIRMWARE_REF', 'origin/master')
SCH = os.path.join(PRJ, 'FujiNet-ColecoVision-Rev0.kicad_sch')

# ColecoVision cartridge port (MAME src/devices/bus/coleco/cartridge/exp.h; ADAM TRM J1).
# Independent copy of the map.
EDGE = {'1': 'D2', '2': '/C000', '3': 'D1', '4': 'D3', '5': 'D0', '6': 'D4', '7': 'A0', '8': 'D5',
        '9': 'A1', '10': 'D6', '11': 'A2', '12': 'D7', '13': 'SHLD', '14': 'A11', '15': 'A3', '16': 'A10',
        '17': 'A4', '18': '/8000', '19': 'A13', '20': 'A14', '21': 'A5', '22': '/A000', '23': 'A6',
        '24': 'A12', '25': 'A7', '26': 'A9', '27': '/E000', '28': 'A8', '29': 'GND', '30': '+5V'}
SELECTS = ('/8000', '/A000', '/C000', '/E000')
# RP2350 datasheet: on the QFN-60 package GPIO0-25 are "Digital IO (FT)" (5.5 V with IOVDD at 3.3 V);
# GPIO26-29 share the ADC and are not 5 V tolerant.
FT_GPIOS = range(26)
PAD_GPIOS = {23: 'GP23', 24: 'DBG_TX', 29: 'SELFTEST'}     # this board's bring-up pads

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


def cmake_set(path, name):
    m = re.search(r'set\(%s\s+(\S+)\)' % re.escape(name), read(path))
    if not m:
        raise SystemExit('%s: no set(%s)' % (path, name))
    return m.group(1)


def ohms(v):
    m = re.match(r'([\d.]+)([kMR]?)', v)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1, '': 1}[m.group(2)]


def main():
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-coleco-rev0-check.xml')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn, SCH],
                   check=True, capture_output=True)
    t = ET.parse(fn)
    node_net, func_net, nets = {}, {}, {}
    canon = lambda n: n if n.startswith('unconnected') else n.rsplit('/', 1)[-1]   # /cart-bus/CA0 -> CA0
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

    U1 = by_value('RP2350A')[0]
    U2 = by_value('ESP32-S3-WROOM-1-N16R8')[0]
    J1 = by_value('Coleco_Cart_Edge_30')[0]
    J2 = by_value('microSD')[0]
    UB = by_value('74LVC245A')[0]
    UF = by_value('W25Q16JVUXIQ')[0]
    UCP = by_value('CP2102N-A02-GQFN28')[0]
    WS = by_value('WS2812B-2020-V6')[0]
    LDO = by_value('AP2112K-3.3')[0]
    MUX = by_value('TPS2116')[0]
    ESD = by_value('USBLC6-2SC6')[0]
    GATES = by_value('74LVC1G11') + by_value('74LVC1G08')

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def rp_pins(fname):
        return [(pin, n) for n, nodes in nets.items() for (ref, pin, f) in nodes if ref == U1 and f == fname]

    def s3(io):
        return func_net.get((U2, 'IO%d' % io))

    def resistors():
        """(value, end a, end b) for every resistor: 2-pin parts and each unit of an array (pins k / 9-k)."""
        for r, (val, fp, _) in parts.items():
            if r.startswith('RN'):
                for k in range(1, 5):
                    yield val, node_net.get((r, str(k))), node_net.get((r, str(9 - k)))
            elif r.startswith('R'):
                yield val, node_net.get((r, '1')), node_net.get((r, '2'))

    def through_r(a, b):
        """a and b joined by exactly one resistor; returns its value (an array's '4x330R' -> '330R')."""
        for val, x, y in resistors():
            if {x, y} == {a, b}:
                return val.split('x', 1)[1] if val.startswith('4x') else val
        return None

    # ---- firmware contracts ----
    ch = 'pico/coleco/firmware/include/coleco_cart.h'
    addr_mask, d0 = define(ch, 'ADDR_MASK'), define(ch, 'D0_PIN')
    ce_pin, dir_pin, pwr_pin = define(ch, 'CE_PIN'), define(ch, 'DIR_PIN'), define(ch, 'PWR_PIN')
    a_gp = [g for g in range(32) if addr_mask >> g & 1]
    chk('coleco_cart.h: ADDR_MASK 0x%X = A0-A14 on GP0-14' % addr_mask, a_gp == list(range(15)))
    d_gp = list(range(d0, d0 + 8))
    chk('coleco_cart.h: D0_PIN %d (DATA_MASK 0xFF << D0_PIN): D0-D7 on GP%d-%d' % (d0, d0, d0 + 7), d0 == 15)
    led_pin = 25                                       # boards/fujicoleco.h -> boards/pico.h PICO_DEFAULT_LED_PIN
    bh = read('pico/coleco/firmware/boards/fujicoleco.h')
    chk('fujicoleco.h takes the LED from boards/pico.h (PICO_DEFAULT_LED_PIN 25)', 'boards/pico.h' in bh)
    used = a_gp + d_gp + [ce_pin, dir_pin, pwr_pin, led_pin]
    chk('the firmware\'s %d GPIOs are distinct' % len(used), len(set(used)) == len(used))
    bc = read('pico/coleco/firmware/boards/fujicoleco.cmake')
    if re.search(r'PICO_PLATFORM\s+rp2040', bc):
        note('pico/coleco builds the stock-Pico board fujicoleco (RP2040): this RP2350A + W25Q16 board needs an '
             'rp2350 board file (README "Firmware changes this board needs")')
    pm = 'include/pinmap/fujiversal-coleco.h'
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    u0rx, u0tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN', -2), define(pm, 'PIN_RP2040_BOOTSEL', -2)
    cd_io = define(pm, 'PIN_CARD_DETECT', -2)
    if run_io == -2 or bsel_io == -2:
        note('fujiversal-coleco.h has no PIN_RP2040_RUN / PIN_RP2040_BOOTSEL: this board wires S3 IO4 / IO5 '
             'to the RP\'s RUN / QSPI_SS (as every on-cart S3 board); the pin map needs them')
        run_io, bsel_io = 4, 5
    if cd_io < 0:
        note('fujiversal-coleco.h PIN_CARD_DETECT is NC: this board wires the microSD card detect to IO42')
        cd_io = 42

    # ---- the edge ----
    chk('the edge carries all 30 contacts', sorted(EDGE) == sorted(p for (r, p) in node_net if r == J1))
    edge = lambda sig: node_net.get((J1, next(p for p, s_ in EDGE.items() if s_ == sig)))
    for p, sig in EDGE.items():
        n = node_net.get((J1, p))
        if sig in ('GND', 'SHLD'):
            chk('J1.%s (%s) is GND' % (p, sig), n == 'GND')
        elif sig == '+5V':
            chk('J1.%s (+5V) is CONS_5V' % p, n == 'CONS_5V')
        elif sig[0] == 'A':
            i = int(sig[1:])
            gp = a_gp[i]
            rn = rp(gp)
            chk('J1.%s %s -> 330R -> GP%d' % (p, sig, gp), n is not None and rn is not None and through_r(n, rn) == '330R')
            chk('GP%d (%s) is a 5 V-tolerant pad' % (gp, sig), gp in FT_GPIOS)
            chk('edge net %s touches only J1 and its resistor' % n, len(nets.get(n, [])) == 2)
            chk('RP side %s touches only its resistor and GP%d' % (rn, gp), len(nets.get(rn, [])) == 2)
        elif sig[0] == 'D':
            i = int(sig[1:])
            chk('J1.%s %s -> the 74LVC245A A%d' % (p, sig, i), func_net.get((UB, 'A%d' % i)) == n)
            chk('edge net %s touches only J1 and the buffer' % n, len(nets.get(n, [])) == 2)
            b = func_net.get((UB, 'B%d' % i))
            chk("the 74LVC245A B%d -> GP%d (D%d)" % (i, d_gp[i], i), b is not None and rp(d_gp[i]) == b
                and len(nets.get(b, [])) == 2)
    # the selects: each pulled up, all four ANDed (74LVC1G gates) into the buffer's /OE and CE_PIN
    ce = rp(ce_pin)
    chk('GP%d (CE_PIN) is the 74LVC245A /OE' % ce_pin, ce is not None and func_net.get((UB, 'CE')) == ce)
    gate_out = {node_net.get((g, '4')): g for g in GATES}

    def leaves(net, seen=()):
        g = gate_out.get(net)
        if g is None:
            return {net}
        ins = [node_net.get((g, p)) for p in ('1', '2', '3', '6') if (g, p) in node_net and p in
               (('1', '3', '6') if parts[g][0] == '74LVC1G11' else ('1', '2'))]
        out = set()
        for i in ins:
            out |= leaves(i)
        return out
    sel_nets = {edge(s_) for s_ in SELECTS}
    chk('/CE = the AND of /8000 /A000 /C000 /E000 (74LVC1G11 + 74LVC1G08)', leaves(ce) == sel_nets)
    for s_ in SELECTS:
        chk('%s pulled up (10k to +3V3_RP)' % s_, through_r(edge(s_), '+3V3_RP') == '10k')
    for g in GATES + [UB]:
        chk('%s (%s) on +3V3_RP (5 V-tolerant inputs at 3.3 V)' % (g, parts[g][0]),
            func_net.get((g, 'VCC')) == '+3V3_RP' and func_net.get((g, 'GND')) == 'GND')
    dirn = rp(dir_pin)
    chk("GP%d (DIR_PIN) is the 74LVC245A A->B: 1 = A (the edge) -> B (the RP) = console -> cart" % dir_pin,
        dirn is not None and func_net.get((UB, 'A->B')) == dirn)
    chk('DIR pulled up 10k (console -> cart while the RP is in reset)', through_r(dirn, '+3V3_RP') == '10k')
    chk('GP%d / GP%d / GP%d (CE, DIR, PWR) only meet 3.3 V' % (ce_pin, dir_pin, pwr_pin),
        not ({ce, dirn} & {node_net.get((J1, p)) for p in EDGE}))
    cons = nets['CONS_5V']
    chk('console 5V feeds only the mux, its caps, the sense divider and a test pad',
        all(r.startswith(('J', 'U', 'C', 'R', 'TP')) for (r, _, _) in cons) and
        {r for (r, _, _) in cons if r.startswith('U')} == {MUX})

    # ---- console 5 V sense (PWR_PIN) and the bring-up pins ----
    vs = rp(pwr_pin)
    chk('GP%d (PWR_PIN) = VSENSE' % pwr_pin, vs == 'VSENSE')
    hi, lo = through_r('CONS_5V', vs), through_r(vs, 'GND')
    chk('VSENSE divider CONS_5V -> R -> GP%d -> R -> GND' % pwr_pin, hi is not None and lo is not None)
    if hi and lo:
        v = 5.25 * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE at a 5.25 V console (%.2f V) under IOVDD (GP%d is not 5 V tolerant)' % (v, pwr_pin), v <= 3.3)
        v = 4.5 * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE at a 4.5 V console (%.2f V) above VIH 2.15 V (0.65 IOVDD)' % v, v >= 2.15)
        z = ohms(hi) * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE source %.1f kOhm under RP2350-E9\'s 8.2 kOhm' % (z / 1e3), z <= 8.2e3)
    for gp, net in PAD_GPIOS.items():
        chk('GP%d (%s) on a test pad' % (gp, net), rp(gp) == net and any(r.startswith('TP') for r, _, _ in nets[net]))
    allgp = set(used) | set(PAD_GPIOS)
    for gp in sorted(set(range(30)) - allgp):
        chk('GP%d unused' % gp, unconnected(rp(gp)))

    # ---- RP2350A support ----
    chk('GP%d (LED) -> R -> LED' % led_pin, through_r(rp(led_pin), 'RP_LED_A') is not None)
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((U2, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((U2, 'USB_D-'))) == '27R')
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (RUN) -> 1k -> RP RUN (active low, no inverter)' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up to the RP rail', through_r(run, '+3V3_RP') == '10k')
    chk('QSPI_SS pull-up to the RP rail', through_r(ss, '+3V3_RP') == '10k')
    fl = {'~{CS}': '~{QSPI_SS}', 'CLK': 'QSPI_SCLK', 'DI/IO_{0}': 'QSPI_SD0', 'DO/IO_{1}': 'QSPI_SD1',
          '~{WP}/IO_{2}': 'QSPI_SD2', '~{HOLD}/~{RESET}/IO_{3}': 'QSPI_SD3'}
    for ff, rf in fl.items():
        chk('W25Q16 %s = RP %s' % (ff, rf), func_net.get((UF, ff)) == func_net.get((U1, rf)) is not None)
    chk('W25Q16 VCC on +3V3_RP', func_net.get((UF, 'VCC')) == '+3V3_RP')
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

    # ---- power mux (TPS2116: VIN1 priority) ----
    mux = lambda f: func_net.get((MUX, f))
    chk('TPS2116 VIN1 = VBUS, VIN2 = CONS_5V, VOUT = +5V', mux('VIN1') == 'VBUS' and mux('VIN2') == 'CONS_5V'
        and mux('VOUT') == '+5V')
    chk('TPS2116 MODE on VIN1 (priority mode)', mux('MODE') == 'VBUS')
    ph, pl = through_r('VBUS', mux('PR1')), through_r(mux('PR1'), 'GND')
    chk('TPS2116 PR1 from a VBUS divider', ph is not None and pl is not None)
    if ph and pl:
        vt = 1.0 * (ohms(ph) + ohms(pl)) / ohms(pl)     # datasheet: PR1 reference 0.92-1.08 V, typ 1.0
        chk('VBUS switchover threshold %.2f V (0.92-1.08 V ref: %.2f-%.2f) inside 3.5-4.75 V' % (
            vt, 0.92 * vt, 1.08 * vt), 3.5 <= 0.92 * vt and 1.08 * vt <= 4.75)

    # ---- USB-C ----
    esd = lambda p: node_net.get((ESD, p))
    chk('USBLC6: D- on I/O1 (1, 6), D+ on I/O2 (3, 4), VBUS clamp, GND',
        esd('1') == esd('6') == func_net.get((UCP, 'D-')) and esd('3') == esd('4') == func_net.get((UCP, 'D+'))
        and esd('5') == 'VBUS' and esd('2') == 'GND')
    chk('CP2102N RSTb pull-up 1k (datasheet)', through_r(func_net.get((UCP, '~{RST}')), '+3V3') == '1k')
    chk('CC1 / CC2 5.1k Rd to GND', all(through_r(n, 'GND') == '5.1k' for n in ('CC1', 'CC2')))

    # ---- S3 pins ----
    chk('SD CS  IO%d -> J2 DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((J2, '2')))
    chk('SD MOSI IO%d -> J2 CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((J2, '3')))
    chk('SD SCK IO%d -> J2 CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((J2, '5')))
    chk('SD MISO IO%d -> J2 DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((J2, '7')))
    chk('SD card detect IO%d -> J2 CD' % cd_io, s3(cd_io) == node_net.get((J2, '9')))
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
