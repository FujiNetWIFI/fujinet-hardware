#!/usr/bin/env python3
"""Cross-check the FujiNet-O2 Rev0 schematic netlist against the firmware that
has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads, from the fujinet-firmware
tree ($FUJINET_FIRMWARE, default ~/Workspace/fujinet-firmware) at the git ref
$FUJINET_FIRMWARE_REF (default origin/master; '' reads the working tree):
  pico/o2/firmware/picopac_cart.c       A0_PIN..A11_PIN, P10/P11_PIN, D0_PIN..D7_PIN, PSEN_PIN,
                                        WR_PIN, CS_PIN (P14), LED_PIN, NOTCS_PIN (pin E), TD_PIN (T0)
  pico/o2/firmware/CMakeLists.txt       PICO_BOARD, PICO_FLASH_SIZE_BYTES
  include/pinmap/fujiversal-o2.h        S3 SD / LED strip / UART pins
and checks every one of them, plus the Odyssey 2 edge map (its own copy, from
Dan Boris's O2 Tech Specs), against the pin *functions* the netlist reports
(GPIOn on the RP2354B, IOn on the S3).  Each edge line must reach exactly
its GPIO through one 330R (pin B: 1k, plus its 10k pull-down).

Firmware that does not yet match this board (pico/o2 builds a plain RP2040
PicoPAC; the S3 pin map lacks RUN / BOOTSEL / card detect) is reported as NOTE
lines, not failures: the README lists the port.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, subprocess, sys, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
REF = os.environ.get('FUJINET_FIRMWARE_REF', 'origin/master')
SCH = os.path.join(PRJ, 'FujiNet-O2-Rev0.kicad_sch')

# Odyssey 2 / Videopac cartridge port (Dan Boris, Odyssey 2 Technical Specs v1.1 section 2.0: N = A7,
# P = A6).  Independent copy of the map.
EDGE = {'1': 'T0', '10': 'A10', '11': 'P14', '12': 'P11', '13': 'P10', '14': 'A11', '15': 'A9',
        'A': '/WR', 'B': 'B', 'C': 'GND', 'D': '+5V', 'E': 'E', 'F': '/PSEN', 'G': 'A0', 'H': 'A1',
        'J': 'A2', 'K': 'A3', 'L': 'A4', 'M': 'A5', 'N': 'A7', 'P': 'A6', 'R': 'A8'}
EDGE.update({str(2 + i): 'DB%d' % i for i in range(8)})
# signal -> the picopac_cart.c macro naming its GPIO
FW_PIN = {'A%d' % i: 'A%d_PIN' % i for i in range(12)}
FW_PIN.update({'DB%d' % i: 'D%d_PIN' % i for i in range(8)})
FW_PIN.update({'P10': 'P10_PIN', 'P11': 'P11_PIN', 'P14': 'CS_PIN', '/WR': 'WR_PIN', '/PSEN': 'PSEN_PIN',
               'E': 'NOTCS_PIN', 'T0': 'TD_PIN'})
# RP2350 datasheet Table 1674: on the QFN-80 package GPIO0-39 are "Digital IO (FT)"
# (5.5 V with IOVDD at 3.3 V); GPIO40-47 share the ADC and are not 5 V tolerant.
FT_GPIOS = range(40)
VPB_GPIO = 28              # this board's pin B line (no firmware macro yet)

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
    fn = os.path.join(tempfile.gettempdir(), 'fujinet-o2-rev0-check.xml')
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

    U1 = by_value('RP2354B')[0]
    U2 = by_value('ESP32-S3-WROOM-1-N16R8')[0]
    J1 = by_value('Videopac_Cart_Edge_30')[0]
    J2 = by_value('microSD')[0]
    UCP = by_value('CP2102N-A02-GQFN28')[0]
    WS = by_value('WS2812B-2020-V6')[0]
    LDO = by_value('AP2112K-3.3')[0]
    MUX = by_value('TPS2116')[0]
    ESD = by_value('USBLC6-2SC6')[0]

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
    cc = 'pico/o2/firmware/picopac_cart.c'
    gpio = {sig: define(cc, m) for sig, m in FW_PIN.items()}
    led_pin = define(cc, 'LED_PIN')
    chk('picopac_cart.c: A0-A11 on GP0-11 (addr = pins & 0xFFF)', [gpio['A%d' % i] for i in range(12)] == list(range(12)))
    chk('picopac_cart.c: D0-D7 on GP14-21, D0_PIN 14 (gpio_put_masked(DATA_PIN_MASK, b << D0_PIN))',
        [gpio['DB%d' % i] for i in range(8)] == list(range(14, 22)))
    chk('picopac_cart.c: DATA_PIN_MASK 0x003FC000', define(cc, 'DATA_PIN_MASK') == 0x003FC000)
    chk('picopac_cart.c: the 27 bus GPIOs are distinct', len(set(gpio.values())) == len(gpio))
    chk('picopac_cart.c: LED_PIN %d is not a bus pin' % led_pin, led_pin not in gpio.values())
    cm = read('pico/o2/firmware/CMakeLists.txt')
    if re.search(r'set\(PICO_BOARD\s+myboard\)', cm):
        note('pico/o2 builds PICO_BOARD myboard (boards/pico.h, an RP2040): this RP2354B board needs an rp2350 '
             'board file (README "Firmware changes this board needs")')
    m = re.search(r'PICO_FLASH_SIZE_BYTES=(\d+)', cm)
    if m and int(m.group(1)) != 2 * 1024 * 1024:
        note('pico/o2 PICO_FLASH_SIZE_BYTES=%s and a 15 MB flash filesystem: the RP2354B has 2 MB in the package '
             '(README "Firmware changes")' % m.group(1))
    pm = 'include/pinmap/fujiversal-o2.h'
    sd = {k: define(pm, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(pm, 'PIN_LED_STRIP')
    u0rx, u0tx = define(pm, 'PIN_UART0_RX'), define(pm, 'PIN_UART0_TX')
    run_io, bsel_io = define(pm, 'PIN_RP2040_RUN', -2), define(pm, 'PIN_RP2040_BOOTSEL', -2)
    cd_io = define(pm, 'PIN_CARD_DETECT', -2)
    if run_io == -2 or bsel_io == -2:
        note('fujiversal-o2.h has no PIN_RP2040_RUN / PIN_RP2040_BOOTSEL: this board wires S3 IO4 / IO5 '
             'to the RP\'s RUN / QSPI_SS (as every on-cart S3 board); the pin map needs them')
        run_io, bsel_io = 4, 5
    if cd_io < 0:
        note('fujiversal-o2.h PIN_CARD_DETECT is NC: this board wires the microSD card detect to IO42')
        cd_io = 42

    # ---- edge -> 330R -> RP2354B ----
    chk('the edge carries all 30 contacts', sorted(EDGE) == sorted(p for (r, p) in node_net if r == J1))
    for p, sig in EDGE.items():
        n = node_net.get((J1, p))
        if sig == 'GND':
            chk('J1.%s is GND' % p, n == 'GND')
            continue
        if sig == '+5V':
            chk('J1.%s (+5V) is CONS_5V' % p, n == 'CONS_5V')
            continue
        if sig == 'B':
            rn = rp(VPB_GPIO)
            chk('J1.B -> 1k -> GP%d' % VPB_GPIO, n is not None and rn is not None and through_r(n, rn) == '1k')
            chk('J1.B pulled down: 10k to GND', through_r(n, 'GND') == '10k')
            chk('GP%d (B) is a 5 V-tolerant pad' % VPB_GPIO, VPB_GPIO in FT_GPIOS)
            note('pin B (Videopac+ video-mixer override) is on GP%d: the firmware has no macro for it yet' % VPB_GPIO)
            continue
        gp = gpio[sig]
        rn = rp(gp)
        chk('J1.%s %s -> 330R -> GP%d (%s)' % (p, sig, gp, FW_PIN[sig]),
            n is not None and rn is not None and through_r(n, rn) == '330R')
        chk('GP%d (%s) is a 5 V-tolerant pad' % (gp, sig), gp in FT_GPIOS)
        others = [(r, pin) for (r, pin, f) in nets.get(n, []) if r != J1 and not r.startswith('R')]
        chk('edge net %s touches only J1 and its resistor' % n, not others and len(nets.get(n, [])) == 2)
        chk('RP side %s touches only its resistor and GP%d' % (rn, gp), len(nets.get(rn, [])) == 2)
    cons = nets['CONS_5V']
    chk('console 5V feeds only the mux, its caps, the sense divider and a test pad',
        all(r.startswith(('J', 'U', 'C', 'R', 'TP')) for (r, _, _) in cons) and
        {r for (r, _, _) in cons if r.startswith('U')} == {MUX})

    # ---- console 5 V sense (GP40) and the bring-up pins ----
    vs = rp(40)
    chk('GP40 (ADC0) = VSENSE', vs == 'VSENSE')
    hi, lo = through_r('CONS_5V', vs), through_r(vs, 'GND')
    chk('VSENSE divider CONS_5V -> R -> GP40 -> R -> GND', hi is not None and lo is not None)
    if hi and lo:
        v = 5.25 * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE at a 5.25 V console (%.2f V) under IOVDD (GP40 is not 5 V tolerant)' % v, v <= 3.3)
        v = 4.5 * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE at a 4.5 V console (%.2f V) above VIH 2.0 V' % v, v >= 2.0)
        z = ohms(hi) * ohms(lo) / (ohms(hi) + ohms(lo))
        chk('VSENSE source %.1f kOhm under RP2350-E9\'s 8.2 kOhm' % (z / 1e3), z <= 8.2e3)
    for gp, net in ((29, 'SELFTEST'), (44, 'DBG_TX'), (45, 'DBG_RX')):
        chk('GP%d (%s) on a test pad' % (gp, net), rp(gp) == net and any(r.startswith('TP') for r, _, _ in nets[net]))
    used = set(gpio.values()) | {VPB_GPIO, led_pin, 29, 40, 44, 45}
    for gp in sorted(set(range(48)) - used):
        chk('GP%d unused' % gp, unconnected(rp(gp)))

    # ---- RP2354B support ----
    chk('GP%d (LED_PIN) -> R -> LED' % led_pin, through_r(rp(led_pin), 'RP_LED_A') is not None)
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
    chk('+5V feeds the buck and the RP LDO', node_net.get((LDO, '1')) == '+5V')

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
