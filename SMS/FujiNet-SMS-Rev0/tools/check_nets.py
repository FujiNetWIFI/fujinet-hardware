#!/usr/bin/env python3
"""Cross-check the FujiNet-SMS Rev0 schematic netlist against the firmware
that has to run on it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads
  $FUJINET_FIRMWARE/pico/sms/firmware/include/sms_cart.h   *_PIN GPIO numbers
      (default ~/Workspace/fujinet-firmware)
  $FUJINET_SMS_BOARD/include/pinmap/fujiversal-sms.h       S3 SD / LED / UART pins
      (default ~/Workspace/fn-sms-board), and fujiversal-intv.h there for
      PIN_RP2040_RUN/BOOTSEL until the SMS pinmap defines them itself
and checks every GPIO of both chips against the pin *functions* the netlist
reports (GPIOn on the RP2354B, IOn on the S3, An/DQn on the SRAMs), the
SMS 50-pin edge map (its own copy of the pin list), the 5 V-tolerance rule
for GPIO40-47, the power path, and the edge footprint's face / pin-1 split.
The glue logic itself is check_glue.py's.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, unconn, define, PRJ

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
BOARD = os.environ.get('FUJINET_SMS_BOARD', os.path.expanduser('~/Workspace/fn-sms-board'))
CART = os.path.join(FW, 'pico/sms/firmware/include/sms_cart.h')
PINMAP = os.path.join(BOARD, 'include/pinmap/fujiversal-sms.h')
PINMAP_RUN = os.path.join(BOARD, 'include/pinmap/fujiversal-intv.h')

# SMS / SMS2 50-pin cartridge slot, the user-corrected physical order.
EDGE = {1: '+5V', 2: '/WR', 3: '/MREQ', 4: '/RD', 5: '/M8-B', 6: 'A14', 7: 'A13', 8: 'A8', 9: 'A9',
        10: 'A11', 11: '/M0-7', 12: 'A10', 13: '/CE', 14: 'D7', 15: 'D6', 16: 'D5', 17: 'D4', 18: 'D3',
        19: 'GND', 20: 'GND', 21: 'GND', 22: 'D2', 23: 'D1', 24: 'D0', 25: 'A0', 26: 'A1', 27: 'A2',
        28: 'A3', 29: 'A4', 30: 'A5', 31: 'A6', 32: 'A7', 33: 'A12', 34: '/CONT', 35: '+5V', 36: 'A15',
        37: '/M1', 38: '/IORQ', 39: '/RFSH', 40: '/HALT', 41: '/WAIT', 42: '/INT', 43: 'KILLGA',
        44: '/BUSREQ', 45: '/BUSACK', 46: '/RESET', 47: 'CLK', 48: '/KBSEL', 49: '/MC-F', 50: '/NMI'}
UNUSED = ('/M8-B', '/M0-7', '/MC-F', '/RFSH', '/HALT', '/INT', '/NMI', '/KBSEL', 'KILLGA', '/BUSACK')
PADS_ONLY = ('/CONT', '/BUSREQ')
STROBE_PIN = {'/RD': 'RD', '/WR': 'WR', '/MREQ': 'MREQ', '/CE': 'CE', '/IORQ': 'IORQ', '/RESET': 'RESET',
              '/M1': 'M1', 'CLK': 'CLK'}   # edge signal -> sms_cart.h <name>_PIN
GLUE = ('74HCT14', '74HCT27', '74HCT10', '74HCT00')
INV6 = [(1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12)]          # 74xx14

fails = 0
count = 0


def chk(desc, ok):
    global fails, count
    count += 1
    if not ok:
        fails += 1
        print('FAIL:', desc)


def main():
    N = Netlist()
    node_net, func_net, nets, parts = N.node_net, N.func_net, N.nets, N.parts
    one = N.one
    U1, J1, S3 = one('RP2354B'), one('SMS_Cart_Edge_50'), one('ESP32-S3-WROOM-1-N16R8')
    J2, UCP, WS = one('microSD'), one('CP2102N-A02-GQFN28'), one('WS2812B-2020-V6')
    U14, LDO, QFET, QW = one('74HCT14'), one('AP2112K-3.3'), one('AO3401A'), one('2N7002')
    srams = N.by_value('AS6C4008-55TIN')
    for ref, what in ((U1, 'RP2354B'), (J1, 'edge'), (S3, 'ESP32-S3'), (U14, '74HCT14'), (LDO, 'AP2112K LDO'),
                      (QFET, 'AO3401A'), (QW, '2N7002')):
        if ref is None:
            raise SystemExit('no %s in the netlist' % what)
    if len(srams) != 2:
        raise SystemExit('expected two AS6C4008-55TIN, found %r' % srams)
    glue = {r for r, (v, _) in parts.items() if v in GLUE}

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((S3, 'IO%d' % io))

    def through_r(a, b):
        """a and b joined by exactly one 2-pin resistor: its value."""
        for r, (val, fp) in parts.items():
            if r.startswith('R') and not r.startswith('RN'):
                if {node_net.get((r, '1')), node_net.get((r, '2'))} == {a, b}:
                    return val
        return None

    def through_rn(a, b):
        """a and b joined by one element of a 4-resistor array (pin k <-> pin 9-k): its value."""
        for r, (val, fp) in parts.items():
            if r.startswith('RN'):
                for k in range(1, 5):
                    if {node_net.get((r, str(k))), node_net.get((r, str(9 - k)))} == {a, b}:
                        return val
        return None

    def inv(a):
        for pa, py in INV6:
            if node_net.get((U14, str(pa))) == a:
                return node_net.get((U14, str(py)))
        return None

    edge = {p: node_net.get((J1, str(p))) for p in EDGE}
    sig = {}
    for p, s in EDGE.items():
        sig.setdefault(s, edge[p])
    v5 = func_net.get((srams[0], 'VCC'))

    # ---- the firmware pin contract: sms_cart.h ----
    P = {k: define(CART, k + '_PIN') for k in ('A0', 'D0', 'RD', 'WR', 'MREQ', 'CE', 'IORQ', 'RESET', 'M1', 'CLK',
                                               'PWROK', 'LED', 'WAIT', 'MBOX', 'DBG_TX', 'DBG_RX', 'GAME',
                                               'RAMWE', 'LOAD', 'BANK')}
    claimed = list(range(P['A0'], P['A0'] + 16)) + list(range(P['D0'], P['D0'] + 8)) + \
        [P[k] for k in ('RD', 'WR', 'MREQ', 'CE', 'IORQ', 'RESET', 'M1', 'CLK', 'PWROK', 'LED', 'WAIT', 'MBOX',
                        'DBG_TX', 'DBG_RX', 'GAME', 'RAMWE', 'LOAD')] + list(range(P['BANK'], P['BANK'] + 7))
    chk('sms_cart.h claims all 48 GPIOs exactly once', sorted(claimed) == list(range(48)))
    for g in range(48):
        chk('GP%d is connected' % g, not unconn(rp(g)))

    # ---- edge <-> RP2354B, straight through except D0-D7 (100R) and /WAIT (2N7002) ----
    for p, s in EDGE.items():
        n = edge[p]
        if s == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
        elif s == '+5V':
            chk('J1.%d +5V is the console rail (not the cart logic rail)' % p, not unconn(n) and n != v5)
        elif s in UNUSED:
            chk('J1.%d %s unconnected' % (p, s), unconn(n))
        elif s in PADS_ONLY:
            on = nets.get(n, [])
            chk('J1.%d %s only on a test pad (no MCU pin)' % (p, s),
                not unconn(n) and {r for r, _, _ in on} - {J1} and all(r == J1 or r.startswith('TP') for r, _, _ in on))
        elif s == '/WAIT':
            chk('J1.41 /WAIT = 2N7002 drain', n == func_net.get((QW, 'D')) and not unconn(n))
        elif s in STROBE_PIN:
            g = P[STROBE_PIN[s]]
            chk('J1.%d %s -> GP%d' % (p, s, g), n == rp(g) and not unconn(n))
        elif s.startswith('A'):
            g = P['A0'] + int(s[1:])
            chk('J1.%d %s -> GP%d' % (p, s, g), n == rp(g) and not unconn(n))
        elif s.startswith('D'):
            d = int(s[1:])
            g = P['D0'] + d
            chk('J1.%d %s -> 100R -> GP%d' % (p, s, g), through_rn(n, rp(g)) == '4x100R')
        else:
            chk('J1.%d %s: unexpected edge signal' % (p, s), False)
    chk('edge +5V pins 1 and 35 are one net', edge[1] == edge[35])
    for s in ('/RD', '/WR', '/MREQ', '/CE', '/IORQ', '/RESET', '/M1', 'CLK') + tuple('A%d' % i for i in range(16)):
        others = [(r, pin) for (r, pin, f) in nets.get(sig[s], []) if r not in {J1, U1} | glue | set(srams)
                  and not r.startswith('TP')]
        chk('%s net carries no extra parts (no pull-ups, no series R)' % s, not others)
    for i in range(8):
        others = [r for (r, pin, f) in nets.get(sig['D%d' % i], []) if r not in {J1} | set(srams) and not r.startswith('RN')]
        chk('D%d net: edge, both SRAMs, the series pack only' % i, not others)
        others = [r for (r, pin, f) in nets.get(rp(P['D0'] + i), []) if r not in (U1,) and not r.startswith('RN')]
        chk('GP%d: RP and its series resistor only' % (P['D0'] + i), not others)

    # ---- the RP's own outputs ----
    gate = rp(P['WAIT'])
    chk('GP%d (WAIT) -> 2N7002 gate, source GND' % P['WAIT'],
        gate == func_net.get((QW, 'G')) and func_net.get((QW, 'S')) == 'GND')
    v33io = func_net.get((U1, 'IOVDD'))
    chk('2N7002 gate pulled up to the RP IO rail (/WAIT held from power-on)', through_r(gate, v33io) == '10k')
    led = one('red')
    chk('GP%d (LED) -> 1k -> LED anode, cathode GND' % P['LED'],
        led is not None and through_r(rp(P['LED']), node_net.get((led, '2'))) == '1k' and node_net.get((led, '1')) == 'GND')
    hdr = one('DBG UART')
    chk('GP%d DBG_TX -> header 1, GP%d DBG_RX -> header 2, header 3 GND' % (P['DBG_TX'], P['DBG_RX']),
        hdr is not None and node_net.get((hdr, '1')) == rp(P['DBG_TX']) and node_net.get((hdr, '2')) == rp(P['DBG_RX'])
        and node_net.get((hdr, '3')) == 'GND')
    glue_in = lambda n: any(r in glue and N.ptype.get((r, pin)) == 'input' for (r, pin, f) in nets.get(n, []))
    for k in ('MBOX', 'GAME', 'RAMWE', 'LOAD'):
        chk('GP%d (%s) -> a 74HCT glue input' % (P[k], k), glue_in(rp(P[k])))

    # ---- SRAMs: 1 MB, A19 picks the chip ----
    a19 = rp(P['BANK'] + 6)
    by_ce = {func_net.get((r, '~{CE}')): r for r in srams}
    S0, S1 = by_ce.get(a19), by_ce.get(inv(a19))
    chk('SRAM0 /CE = SRAM A19 (GP%d) directly' % (P['BANK'] + 6), S0 is not None)
    chk("SRAM1 /CE = !A19 through the '14", S1 is not None and S1 != S0)
    for r in srams:
        for i in range(13):
            chk('%s A%d = console A%d' % (r, i, i), func_net.get((r, 'A%d' % i)) == sig['A%d' % i])
        for i in range(6):
            chk('%s A%d = GP%d' % (r, 13 + i, P['BANK'] + i), func_net.get((r, 'A%d' % (13 + i))) == rp(P['BANK'] + i))
        for i in range(8):
            chk('%s DQ%d = console D%d' % (r, i, i), func_net.get((r, 'DQ%d' % i)) == sig['D%d' % i])
        chk('%s VCC on the cart 5V rail, VSS on GND' % r, func_net.get((r, 'VCC')) == v5 and func_net.get((r, 'VSS')) == 'GND')
    for f in ('~{OE}', '~{WE}'):
        n = func_net.get((srams[0], f))
        chk('both SRAMs share %s' % f, n == func_net.get((srams[1], f)))
        chk('SRAM %s driven by a glue output' % f,
            any(r in glue and N.ptype.get((r, pin)) == 'output' for (r, pin, _) in nets.get(n, [])))

    # ---- GPIO40-47 are not 5 V tolerant: inputs of 5 V parts only ----
    for g in range(40, 48):
        n = rp(g)
        bad = [(r, pin, N.ptype.get((r, pin))) for (r, pin, f) in nets.get(n, [])
               if r != U1 and N.ptype.get((r, pin)) != 'input']
        chk('GP%d (%s): nothing but inputs on the net (not 5 V tolerant)' % (g, n), not bad)
        chk('GP%d (%s): never an edge signal' % (g, n), n not in edge.values())

    # ---- PWR_OK: console +5V -> divider -> '14 -> '14 -> GP32 and the glue ----
    cons = sig['+5V']
    vsense = next((node_net.get((U14, str(pa))) for pa, py in INV6
                   if through_r(cons, node_net.get((U14, str(pa)))) is not None), None)
    chk("a '14 input is fed from edge +5V through a resistor (VSENSE)", vsense is not None)
    top, bot = through_r(cons, vsense), through_r(vsense, 'GND')
    chk('VSENSE divider to GND', top is not None and bot is not None)
    if top and bot:
        val = lambda s: float(s.replace('k', 'e3').replace('R', ''))
        ratio = val(bot) / (val(top) + val(bot))
        chk('VSENSE ratio %.2f below the 74HCT14 input clamp with both sources present (<= 0.9)' % ratio, 0.5 <= ratio <= 0.9)
    pwr_ok = inv(inv(vsense))
    chk('PWR_OK = !!VSENSE on the Schmitt', pwr_ok is not None)
    chk('PWR_OK -> GP%d' % P['PWROK'], pwr_ok == rp(P['PWROK']))
    chk('PWR_OK -> the glue', glue_in(pwr_ok))
    for r in sorted(glue):
        chk('%s %s on the cart 5V rail' % (r, parts[r][0]), node_net.get((r, '14')) == v5 and node_net.get((r, '7')) == 'GND')

    # ---- power path ----
    vbus = node_net.get((one('USB-C'), 'A4'))
    chk('edge +5V -> P-FET drain, source = cart 5V rail, gate = VBUS',
        node_net.get((QFET, '3')) == cons and node_net.get((QFET, '2')) == v5 and node_net.get((QFET, '1')) == vbus)
    chk('VBUS -> SS34 -> cart 5V rail', any(val == 'SS34' and node_net.get((r, '2')) == vbus and node_net.get((r, '1')) == v5
                                            for r, (val, _) in parts.items()))
    chk('VBUS held low when unplugged (sense divider to GND)', through_r(vbus, node_net.get((UCP, '8'))) is not None)

    # ---- RP support: everything on the LDO rail ----
    chk('RP IOVDD rail is the LDO output, LDO fed from the 5V rail, EN = VIN',
        node_net.get((LDO, '5')) == v33io and node_net.get((LDO, '1')) == v5 and node_net.get((LDO, '3')) == v5)
    v_in = func_net.get((U1, 'VREG_VIN'))
    chk('RP VREG_VIN on the IOVDD rail', v_in == v33io)
    chk('VREG_AVDD from VREG_VIN through 33R', through_r(v_in, func_net.get((U1, 'VREG_AVDD'))) == '33R')
    v33 = func_net.get((S3, '3V3'))
    chk('S3 3V3 is the buck rail, not the LDO', v33 not in (v33io, v5, None))
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((S3, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((S3, 'USB_D-'))) == '27R')
    run_io, bsel_io = define(PINMAP, 'PIN_RP2040_RUN', -2), define(PINMAP, 'PIN_RP2040_BOOTSEL', -2)
    if run_io == -2 or bsel_io == -2:
        run_io, bsel_io = define(PINMAP_RUN, 'PIN_RP2040_RUN'), define(PINMAP_RUN, 'PIN_RP2040_BOOTSEL')
        print('note: fujiversal-sms.h does not define PIN_RP2040_RUN/BOOTSEL yet; using fujiversal-intv.h (IO%d/IO%d)'
              % (run_io, bsel_io))
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('S3 IO%d (PIN_RP2040_RUN) -> 1k -> RP RUN' % run_io, through_r(s3(run_io), run) == '1k')
    chk('S3 IO%d (PIN_RP2040_BOOTSEL) -> 1k -> RP QSPI_SS' % bsel_io, through_r(s3(bsel_io), ss) == '1k')
    chk('RUN pull-up to the IO rail', through_r(run, v33io) == '10k')
    chk('QSPI_SS pull-up to the IO rail', through_r(ss, v33io) == '10k')
    for f in ('QSPI_SCLK', 'QSPI_SD0', 'QSPI_SD1', 'QSPI_SD2', 'QSPI_SD3'):
        chk('RP %s unconnected (flash is in the package)' % f, unconn(func_net.get((U1, f))))
    for n, nodes in nets.items():
        for (ref, pin, f) in nodes:
            if ref == U1 and f in ('IOVDD', 'QSPI_IOVDD', 'USB_OTP_VDD', 'ADC_AVDD', 'VREG_VIN'):
                chk('RP %s (pin %s) on %s' % (f, pin, v33io), n == v33io)
            if ref == U1 and f == 'DVDD':
                chk('RP DVDD (pin %s) on DVDD' % pin, n == func_net.get((U1, 'VREG_FB')))
            if ref == U1 and f in ('GND', 'VREG_PGND'):
                chk('RP %s (pin %s) on GND' % (f, pin), n == 'GND')
    for f in ('SWCLK', 'SWDIO', 'RUN'):
        chk('RP %s on a test pad' % f, any(r.startswith('TP') for (r, _, _) in nets.get(func_net.get((U1, f)), [])))

    # ---- S3 pins: fujiversal-sms.h ----
    sd = {k: define(PINMAP, 'PIN_SD_HOST_' + k) for k in ('CS', 'SCK', 'MISO', 'MOSI')}
    led_strip = define(PINMAP, 'PIN_LED_STRIP')
    uart_rx, uart_tx = define(PINMAP, 'PIN_UART0_RX'), define(PINMAP, 'PIN_UART0_TX')
    card = define(PINMAP, 'PIN_CARD_DETECT', -1)
    chk('SD CS  IO%d -> microSD DAT3/CS' % sd['CS'], s3(sd['CS']) == node_net.get((J2, '2')))
    chk('SD MOSI IO%d -> microSD CMD' % sd['MOSI'], s3(sd['MOSI']) == node_net.get((J2, '3')))
    chk('SD SCK IO%d -> microSD CLK' % sd['SCK'], s3(sd['SCK']) == node_net.get((J2, '5')))
    chk('SD MISO IO%d -> microSD DAT0' % sd['MISO'], s3(sd['MISO']) == node_net.get((J2, '7')))
    chk('microSD VDD on the S3 rail, VSS on GND', node_net.get((J2, '4')) == v33 and node_net.get((J2, '6')) == 'GND')
    cd = node_net.get((J2, '9'))
    cd_io = next((int(f[2:]) for (r, pin, f) in nets.get(cd, []) if r == S3 and f.startswith('IO')), None)
    if card >= 0:
        chk('microSD card-detect -> IO%d (PIN_CARD_DETECT)' % card, cd_io == card)
    else:
        print('note: fujiversal-sms.h leaves PIN_CARD_DETECT NC; the board wires card-detect to IO%s '
              '(pulled up) as the NES board does, unused by the firmware' % cd_io)
    ws_din = node_net.get((WS, '3'))
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), ws_din) is not None)
    chk('PIN_UART0_TX/RX are the module TXD0/RXD0 pads (GPIO43/44)', (uart_tx, uart_rx) == (43, 44))
    chk('S3 TXD0 -> CP2102N RXD', func_net.get((S3, 'TXD0')) == func_net.get((UCP, 'RXD')))
    chk('S3 RXD0 <- CP2102N TXD', func_net.get((S3, 'RXD0')) == func_net.get((UCP, 'TXD')))
    # every S3 IO the board uses is one the contract names
    contract = set(sd.values()) | {led_strip, run_io, bsel_io, 19, 20, 0} | ({card} if card >= 0 else {cd_io})
    for (r, f), n in sorted(func_net.items()):
        if r == S3 and re.match(r'IO\d+$', f) and not unconn(n):
            chk('S3 %s (%s) is in the pin contract' % (f, n), int(f[2:]) in contract)
    for io in (3, 45, 46):
        chk('S3 strapping IO%d unloaded' % io, unconn(s3(io)))
    for io in range(26, 38):
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, unconn(s3(io)))

    # ---- edge footprint: 2.54 mm, odd pins one face, even the other, pin 1 east (PROVISIONAL) ----
    fpt = open(os.path.join(PRJ, 'FujiNet-SMS.pretty', 'SMS_Cart_Edge_50.kicad_mod')).read()
    pads = {int(m.group(1)): (float(m.group(2)), m.group(3)) for m in
            re.finditer(r'\(pad "(\d+)" smd rect\s*\(at ([-\d.]+) [-\d.]+\)\s*\(size [^)]*\)\s*\(layers "([FB])\.Cu"\)', fpt)}
    chk('edge footprint has 50 pads', sorted(pads) == list(range(1, 51)))
    chk('edge: odd pads on F.Cu, even on B.Cu, pin 2k-1 over pin 2k',
        all(pads[2 * k - 1][1] == 'F' and pads[2 * k][1] == 'B' and pads[2 * k - 1][0] == pads[2 * k][0] for k in range(1, 26)))
    chk('edge: 2.54 mm pitch, pin 1 east (+x), pin 49 west',
        all(abs((pads[2 * k - 1][0] - pads[2 * k + 1][0]) - 2.54) < 1e-6 for k in range(1, 25)) and pads[1][0] > 0 > pads[49][0])

    # ---- general ----
    for n, nodes in nets.items():
        if not unconn(n):
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
        others = edge_of.get(n, []) + ['%s.%s' % (r, fn or pin) for (r, pin, fn) in nets.get(n, []) if r not in (U1, J1)]
        print('GP%-4d %-4s %-10s %s' % (g, pin_of[f], n, ', '.join(others)))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
