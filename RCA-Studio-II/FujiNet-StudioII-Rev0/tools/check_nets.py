#!/usr/bin/env python3
"""Cross-check the FujiNet-StudioII Rev0 schematic netlist against the firmware that has to run on
it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads
  $FUJINET_FIRMWARE/pico/studio2/firmware/include/s2_cart.h   every *_PIN GPIO number
      (default ~/Workspace/fujinet-firmware)
  $FUJINET_S2_BOARD/include/pinmap/fujiversal-studio2.h       if present: the S3 board's contract
      that the cart is joined by USB alone (default ~/Workspace/fn-studio2-board)
and checks every GPIO of the RP2354B against the pin *functions* the netlist reports (GPIOn on the
RP2354B, An/Yn on the '541), the Studio II 22-pin edge map (its own copy of the pinout), the series
resistors on the console's lines, the 5 V-tolerance rule for GPIO40-47, the /DRIVE and /CLAIM
pull-ups, the supply sense dividers and the PWR_OK_N gating, the power OR, the RP's support circuit
and the edge footprint.  The glue logic itself is check_glue.py's.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, unconn, define, PRJ

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
CART = os.path.join(FW, 'pico/studio2/firmware/include/s2_cart.h')
S2_BOARD = os.environ.get('FUJINET_S2_BOARD', os.path.expanduser('~/Workspace/fn-studio2-board'))
PINMAP = os.path.join(S2_BOARD, 'include/pinmap/fujiversal-studio2.h')

# RCA Studio II 22-pin cartridge edge, 0.156" pitch, contacts on one face (the bring-up plan, from
# EJK's schematic, Paul Robson's notes and the FliP multicart).  ROMDIS: the console's ROM DISABLE,
# grounded by a cartridge to remove the built-in games; PWR: the console's +5 V (its 7805).
EDGE = {1: 'D7', 2: 'D6', 3: 'D5', 4: 'D4', 5: 'D3', 6: 'ROMDIS', 7: 'GND', 8: 'D2', 9: 'D1', 10: 'D0',
        11: 'MA0', 12: 'MA1', 13: 'MA2', 14: 'MA3', 15: 'PWR', 16: 'MA4', 17: 'MA5', 18: 'MA6', 19: 'TPA',
        20: 'MA7', 21: '/MRD', 22: 'CARTCS'}
INV6 = [(1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12)]          # 74xx14
VAL = lambda s: float(s.replace('k', 'e3').replace('R', '').replace('nF', 'e-9').replace('uF', 'e-6'))
SERIES_R = (100, 330)                         # the console's lines into the RP: 100-330R
VIH_HCT14_MAX, VCC_MIN = 2.1, 4.5             # SN74HCT14 VT+ max (TI SCLS225G: 1.9 at 4.5 V, taken at 2.1); 74HCT VCC min
HCT_VIH = 2.0
RP_PD_MIN = 30e3                              # RP2350 pad pull-down, taken low (datasheet: ~50k typ)

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
    U1, J1, BUF = one('RP2354B'), one('StudioII_Cart_Edge_22'), one('74HCT541')
    NOR, U14, U32 = one('74HCT1G02'), one('74HCT14'), one('74HCT32')
    LDO, USB = one('AP2112K-3.3'), one('USB-C')
    for ref, what in ((U1, 'RP2354B'), (J1, 'edge'), (BUF, '74HCT541'), (NOR, '74HCT1G02'), (U14, '74HCT14'),
                      (U32, '74HCT32'), (LDO, 'AP2112K LDO'), (USB, 'USB-C')):
        if ref is None:
            raise SystemExit('no %s in the netlist' % what)
    glue = {BUF, NOR, U14, U32}
    glue_in = lambda n: any(r in glue and N.ptype.get((r, pin)) == 'input' for (r, pin, f) in nets.get(n, []))
    tps = {r for r in parts if re.match(r'TP\d+$', r)}         # bring-up / SWD test pads (no BOM part)

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def two_pin(a, b, prefix):
        """a and b joined by exactly one 2-pin part of this prefix: its value."""
        for r, (val, fp) in parts.items():
            if re.match(prefix + r'\d+$', r):
                if {node_net.get((r, '1')), node_net.get((r, '2'))} == {a, b}:
                    return val
        return None
    through_r = lambda a, b: two_pin(a, b, 'R')
    through_c = lambda a, b: two_pin(a, b, 'C')

    def inv(a):
        for pa, py in INV6:
            if node_net.get((U14, str(pa))) == a:
                return node_net.get((U14, str(py)))
        return None

    def others(n, allowed):
        return [(r, pin) for (r, pin, f) in nets.get(n, []) if r not in allowed]

    def resistors(n):
        """{ref: other net} of every resistor on n."""
        out = {}
        for r in parts:
            if re.match(r'R\d+$', r):
                a, b = node_net.get((r, '1')), node_net.get((r, '2'))
                if n in (a, b):
                    out[r] = b if a == n else a
        return out

    def pulldown(n):
        return {r for r, o in resistors(n).items() if o == 'GND'}

    edge = {p: node_net.get((J1, str(p))) for p in EDGE}
    sig = {}
    for p, s in EDGE.items():
        sig.setdefault(s, edge[p])
    v5 = node_net.get((BUF, '20'))
    cons = sig['PWR']

    # ---- the firmware pin contract: every *_PIN in s2_cart.h ----
    names = re.findall(r'#define\s+(\w+)_PIN\s', open(CART).read())
    P = {k: define(CART, k + '_PIN') for k in names}
    want = {'MA0', 'TPA', 'MRD', 'D0', 'DRIVE', 'CLAIM', 'PWROK', 'LED', 'VSENSE', 'DBG_TX', 'DBG_RX'}
    chk('s2_cart.h defines exactly the pins this board wires (%s)' % sorted(set(names) ^ want), set(names) == want)
    claimed = list(range(P['MA0'], P['MA0'] + 8)) + list(range(P['D0'], P['D0'] + 8)) + \
        [P[k] for k in sorted(want - {'MA0', 'D0'})]
    chk('s2_cart.h claims no GPIO twice', len(claimed) == len(set(claimed)) and max(claimed) < 48)
    bus = list(range(P['MA0'], P['MA0'] + 8)) + list(range(P['D0'], P['D0'] + 8)) + \
        [P[k] for k in ('TPA', 'MRD', 'DRIVE', 'CLAIM', 'PWROK', 'LED')]
    chk('every bus pin is in GPIO0-31 (s2_cart.h: read in one word, 5 V tolerant)', max(bus) < 32)
    chk('s2_cart.h puts ADC VSENSE on GPIO40-47 (ADC0-7)', 40 <= P['VSENSE'] <= 47)
    for g in range(48):
        if g in claimed:
            chk('GP%d is connected' % g, not unconn(rp(g)))
        else:
            chk('GP%d (not in s2_cart.h) is unconnected' % g, unconn(rp(g)))

    # ---- edge <-> RP2354B / '541 / NOR ----
    for p, s in EDGE.items():
        n = edge[p]
        if s in ('GND', 'ROMDIS'):
            chk('J1.%d (%s) is GND' % (p, s), n == 'GND')
        elif s == 'PWR':
            chk('J1.15 is the console 5 V, not the cart rail or GND', not unconn(n) and n not in (v5, 'GND'))
        elif s.startswith('MA') or s in ('TPA', '/MRD'):
            g = P['MA0'] + int(s[2:]) if s.startswith('MA') else P[s.strip('/')]
            rs = {r: o for r, o in resistors(n).items() if o == rp(g)}
            chk('J1.%d %s -> one series R -> GP%d' % (p, s, g), len(rs) == 1 and not unconn(rp(g)))
            if len(rs) == 1:
                v = VAL(parts[next(iter(rs))][0])
                chk('J1.%d %s series R %g ohm in %d-%d' % (p, s, v, SERIES_R[0], SERIES_R[1]),
                    SERIES_R[0] <= v <= SERIES_R[1])
            chk('GP%d (%s): the RP and its series R only' % (g, s), not others(rp(g), {U1} | set(rs)))
            if s == '/MRD':
                chk("J1.21 /MRD -> '541 /OE1 (pin 1)", node_net.get((BUF, '1')) == n)
                chk('J1.21 /MRD -> a NOR input', n in (node_net.get((NOR, '1')), node_net.get((NOR, '2'))))
                chk('J1.21 /MRD: the finger, its series R, the 541, the NOR and a test pad only',
                    not others(n, {J1, BUF, NOR} | set(rs) | tps))
            else:
                chk('J1.%d %s: the finger, its series R and a test pad only' % (p, s),
                    not others(n, {J1} | set(rs) | tps))
        elif s.startswith('D'):
            d = int(s[1:])
            ch = next((f[1:] for (r, f), nn in func_net.items() if r == BUF and f.startswith('Y') and nn == n), None)
            chk("J1.%d %s = a '541 output (Y%s)" % (p, s, ch), ch is not None and not unconn(n))
            g = P['D0'] + d
            chk("GP%d (D%d) = the same '541 channel's input (A%s)" % (g, d, ch),
                ch is not None and rp(g) == func_net.get((BUF, 'A' + ch)) and not unconn(rp(g)))
            chk('D%d at the edge: the finger, the buffer and nothing else (no pulls, no series R)' % d,
                not others(n, {J1, BUF}))
            chk("GP%d: the RP and the '541 input only" % g, not others(rp(g), {U1, BUF}))
        elif s == 'CARTCS':
            chk('J1.22 CART CS = the NOR output (5 V CMOS)', node_net.get((NOR, '4')) == n and not unconn(n))
            chk('J1.22 CART CS: the finger, the NOR and a test pad only', not others(n, {J1, NOR} | tps))
        else:
            chk('J1.%d %s: unexpected edge signal' % (p, s), False)

    # ---- the glue's controls: /DRIVE and /CLAIM into the glue, each pulled up to the glue supply (the
    # logic, with PWR_OK gating both outputs, is check_glue.py's) ----
    drv, clm = rp(P['DRIVE']), rp(P['CLAIM'])
    chk('GP%d (/DRIVE) -> a 74HCT glue input' % P['DRIVE'], glue_in(drv) and not unconn(drv))
    chk('GP%d (/CLAIM) -> a 74HCT glue input' % P['CLAIM'], glue_in(clm) and not unconn(clm))
    chk("'541 /OE2 (pin 19) is a glue gate output, not an RP pin",
        any(r in glue and N.ptype.get((r, pin)) == 'output' for (r, pin, f) in nets.get(node_net.get((BUF, '19')), [])))
    chk('the NOR\'s second input is a glue gate output (not /CLAIM itself)',
        any(r in glue and r != NOR and N.ptype.get((r, pin)) == 'output'
            for (r, pin, f) in nets.get(node_net.get((NOR, '2')), [])))
    for g, n, what in ((P['DRIVE'], drv, '/DRIVE'), (P['CLAIM'], clm, '/CLAIM')):
        pu = [r for r, o in resistors(n).items() if o == v5]
        chk('GP%d (%s) pulled up to the glue supply (the cart silent while the RP is unpowered)' % (g, what),
            len(pu) == 1)
        if len(pu) == 1:
            rpu = VAL(parts[pu[0]][0])
            lvl = 4.5 * RP_PD_MIN / (RP_PD_MIN + rpu)
            chk('%s pull-up %s against the RP reset pull-down (>= %dk): %.2f V at 4.5 V, over the HCT VIH %.1f V'
                % (what, parts[pu[0]][0], RP_PD_MIN / 1e3, lvl, HCT_VIH), lvl > HCT_VIH + 1.0)
        chk('GP%d (%s): the RP, the glue input, its pull-up and a test pad only' % (g, what),
            not others(n, {U1} | glue | set(pu) | tps))

    # ---- the RP's other outputs and inputs ----
    led = one('red')
    chk('GP%d (LED) -> 1k -> LED anode, cathode GND' % P['LED'],
        led is not None and through_r(rp(P['LED']), node_net.get((led, '2'))) == '1k' and node_net.get((led, '1')) == 'GND')
    hdr = one('DBG UART')
    chk('GP%d DBG_TX -> header 1, GP%d DBG_RX -> header 2, header 3 GND' % (P['DBG_TX'], P['DBG_RX']),
        hdr is not None and node_net.get((hdr, '1')) == rp(P['DBG_TX']) and node_net.get((hdr, '2')) == rp(P['DBG_RX'])
        and node_net.get((hdr, '3')) == 'GND')

    # ---- GPIO40-47 are not 5 V tolerant: the ADC sense or the 3.3 V debug header only ----
    for g in range(40, 48):
        n = rp(g)
        if unconn(n):
            continue
        bad = [(r, pin, N.ptype.get((r, pin))) for (r, pin, f) in nets.get(n, [])
               if r != U1 and N.ptype.get((r, pin)) not in ('passive',) and r != hdr]
        chk('GP%d (%s): nothing but passives or the 3.3 V debug header on the net' % (g, n), not bad)
        chk('GP%d (%s): never an edge signal' % (g, n), n not in edge.values())

    # ---- supply sense: edge 15 (the console's 7805) -> divider -> ADC ----
    adc = rp(P['VSENSE'])
    top, bot = through_r(cons, adc), through_r(adc, 'GND')
    chk('GP%d (VSENSE) <- edge 15 through a divider' % P['VSENSE'], top is not None and bot is not None)
    if top and bot:
        r = VAL(bot) / (VAL(top) + VAL(bot))
        chk('ADC divider %.3f: 5.0 V reads %.2f V; the pad stays under 3.0 V up to %.1f V (want >= 5.5 V)'
            % (r, 5 * r, 3.0 / r), 3.0 / r >= 5.5 and 5 * r >= 1.0)
    chk('ADC pin: a filter capacitor to GND', through_c(adc, 'GND') is not None)

    # ---- PWR_OK: edge 15 -> divider -> '14 -> '14 -> GPIO PWROK_PIN ----
    vsense = next((node_net.get((U14, str(pa))) for pa, py in INV6
                   if through_r(cons, node_net.get((U14, str(pa)))) is not None), None)
    chk("a '14 input is fed from edge 15 through a resistor (VSENSE)", vsense is not None)
    top, bot = through_r(cons, vsense), through_r(vsense, 'GND')
    chk('VSENSE divider to GND', top is not None and bot is not None)
    if top and bot:
        rt, rb = VAL(top), VAL(bot)
        r = rb / (rt + rb)
        chk('VSENSE %.2f x: a 4.75 V supply gives %.2f V, over the 74HCT14 VT+ max %.1f V' % (r, 4.75 * r, VIH_HCT14_MAX),
            4.75 * r > VIH_HCT14_MAX + 0.5)
        chk('VSENSE at 5.25 V (7805 max): %.2f V, under the 4.5 V the cart rail can sag to (no input-clamp '
            'current)' % (5.25 * r), 5.25 * r < VCC_MIN)
    pwr_ok_n = inv(vsense)
    pwr_ok = inv(pwr_ok_n)
    chk('PWR_OK = !!VSENSE on the Schmitt', pwr_ok is not None)
    chk('PWR_OK_N (the first stage) gates the glue: a 74HCT32 input', any(r == U32 and N.ptype.get((r, pin)) == 'input'
                                                                         for (r, pin, f) in nets.get(pwr_ok_n, [])))
    chk('PWR_OK -> GP%d' % P['PWROK'], pwr_ok == rp(P['PWROK']) and not unconn(pwr_ok))
    chk('GP%d (PWR_OK): the RP, the Schmitt output and a test pad only' % P['PWROK'],
        not others(rp(P['PWROK']), {U1, U14} | tps))
    for pa, py in INV6:
        if unconn(node_net.get((U14, str(py)))):
            chk("'14 unused gate (pin %d): input tied to GND" % pa, node_net.get((U14, str(pa))) == 'GND')
    for ins, out in (((1, 2), 3), ((4, 5), 6), ((9, 10), 8), ((12, 13), 11)):
        if unconn(node_net.get((U32, str(out)))):
            chk("'32 unused gate (pin %d): inputs tied to GND" % out, all(node_net.get((U32, str(i))) == 'GND' for i in ins))
    for r, vcc, gnd in ((BUF, '20', '10'), (NOR, '5', '3'), (U14, '14', '7'), (U32, '14', '7')):
        chk('%s %s on the cart 5V rail' % (r, parts[r][0]), node_net.get((r, vcc)) == v5 and node_net.get((r, gnd)) == 'GND')
    dec = [r for r, (v, _) in parts.items() if re.match(r'C\d+$', r) and v == '100nF'
           and {node_net.get((r, '1')), node_net.get((r, '2'))} == {v5, 'GND'}]
    chk("a 100 nF on the cart 5V rail per glue package (%d for 4)" % len(dec), len(dec) >= 4)

    # ---- power path: +5V = CONS_5V (P-FET, gate = VBUS) | VBUS (SS34) ----
    vbus = func_net.get((USB, 'VBUS'))
    qfet = next((r for r, (v, _) in parts.items() if v == 'AO3401A' and node_net.get((r, '2')) == v5), None)
    chk('edge 15 -> P-FET drain, source = cart 5V rail', qfet is not None and node_net.get((qfet, '3')) == cons)
    chk('P-FET gate = USB VBUS (off when the S3 board powers the cart)', qfet is not None and node_net.get((qfet, '1')) == vbus)
    chk('VBUS -> SS34 -> cart 5V rail', any(val == 'SS34' and node_net.get((r, '2')) == vbus and node_net.get((r, '1')) == v5
                                            for r, (val, _) in parts.items()))
    chk('VBUS held low with no cable and against the SS34 leakage: <= 4.7k',
        any(VAL(parts[r][0]) <= 4.7e3 for r in pulldown(vbus)))
    chk('nothing but the P-FET, its capacitors, the sense dividers and a test pad on edge 15',
        not [r for r, _ in others(cons, {J1, qfet} | tps) if not re.match(r'(R|C)\d+$', r)])
    chk('no glue pull-up goes to the console 5 V (nothing pushed into an unpowered console)',
        not [r for r in parts if re.match(r'R\d+$', r) and cons in (node_net.get((r, '1')), node_net.get((r, '2')))
             and ({node_net.get((r, '1')), node_net.get((r, '2'))} - {cons}) & {drv, clm}])

    # ---- RP support: everything on the LDO rail ----
    v33io = func_net.get((U1, 'IOVDD'))
    chk('RP IOVDD rail is the LDO output, LDO fed from the 5V rail, EN = VIN',
        func_net.get((LDO, 'VOUT')) == v33io and func_net.get((LDO, 'VIN')) == v5 and func_net.get((LDO, 'EN')) == v5)
    v_in = func_net.get((U1, 'VREG_VIN'))
    chk('RP VREG_VIN on the IOVDD rail', v_in == v33io)
    chk('VREG_AVDD from VREG_VIN through 33R', through_r(v_in, func_net.get((U1, 'VREG_AVDD'))) == '33R')
    chk('VREG_LX -> 3.3uH -> DVDD (VREG_FB)', two_pin(func_net.get((U1, 'VREG_LX')), func_net.get((U1, 'VREG_FB')), 'L') == '3.3uH')
    run, ss = func_net.get((U1, 'RUN')), func_net.get((U1, '~{QSPI_SS}'))
    chk('RUN pull-up to the IO rail', through_r(run, v33io) == '10k')
    chk('QSPI_SS pull-up to the IO rail', through_r(ss, v33io) == '10k')
    sws = {r: {node_net.get((r, '1')), node_net.get((r, '2'))} for r in parts if re.match(r'SW\d+$', r)}
    chk('RESET button: RUN to GND', any(n == {run, 'GND'} for n in sws.values()))
    bsel = [o for r, o in resistors(ss).items() if parts[r][0] == '1k']
    chk('BOOTSEL: QSPI_SS -> 1k -> button to GND', len(bsel) == 1 and any(n == {bsel[0], 'GND'} for n in sws.values()))
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
    xin, xout = func_net.get((U1, 'XIN')), func_net.get((U1, 'XOUT'))
    xtal = one('12MHz')
    chk('12 MHz crystal: XIN direct, XOUT through 1k, 15 pF loads',
        xtal is not None and node_net.get((xtal, '1')) == xin and through_r(xout, node_net.get((xtal, '3'))) == '1k'
        and through_c(xin, 'GND') == '15pF' and through_c(node_net.get((xtal, '3')), 'GND') == '15pF')

    # ---- USB: the RP's native USB to the receptacle (the S3 board is the host) ----
    for f, cf in (('USB_DP', 'D+'), ('USB_DM', 'D-')):
        conn = func_net.get((USB, cf))
        chk('RP %s -> 27R -> USB-C %s (both rows)' % (f, cf), through_r(func_net.get((U1, f)), conn) == '27R'
            and len({node_net.get((USB, p)) for p in ((('A6', 'B6') if cf == 'D+' else ('A7', 'B7')))}) == 1)
        chk('USB-C %s has an ESD diode to GND' % cf, any(v.startswith('ESD') and {node_net.get((r, '1')),
                                                         node_net.get((r, '2'))} == {conn, 'GND'} for r, (v, _) in parts.items()))
    for cc in ('A5', 'B5'):
        chk('USB-C %s: 5.1k Rd to GND (UFP)' % cc, through_r(node_net.get((USB, cc)), 'GND') == '5.1k')
    if os.path.exists(PINMAP):
        chk('%s declares no RP RUN / BOOTSEL lines (the cart is joined by USB alone)' % os.path.basename(PINMAP),
            define(PINMAP, 'PIN_RP2040_RUN', -2) == -2 and define(PINMAP, 'PIN_RP2040_BOOTSEL', -2) == -2)
    else:
        print('note: %s not found; the USB-only link to the S3 board is not cross-checked' % PINMAP)

    # ---- edge footprint: 22 contacts at 3.96 mm on one face, pin 1 at the left (edge_geom.py) ----
    from sexpr import parse as sparse, findall as sfindall, find as sfind
    fpe = sparse(open(os.path.join(PRJ, 'FujiNet-StudioII.pretty', 'StudioII_Cart_Edge_22.kicad_mod')).read())
    pads = {int(p[1]): (float(sfind(p, 'at')[1]), sfind(p, 'layers')[1]) for p in sfindall(fpe, 'pad')}
    chk('edge footprint has 22 pads', sorted(pads) == list(range(1, 23)))
    if sorted(pads) == list(range(1, 23)):
        chk('edge: every contact on one copper face', len({pads[k][1] for k in pads}) == 1)
        steps = [round(pads[k + 1][0] - pads[k][0], 3) for k in range(1, 22)]
        chk('edge: 3.96 mm (0.156") pitch, pin 1 at the left (-x), centred',
            steps == [3.96] * 21 and pads[1][0] < 0 < pads[22][0] and abs(pads[1][0] + pads[22][0]) < 1e-6)

    # ---- general ----
    for n, nodes in nets.items():
        if not unconn(n):
            chk('net %s has >= 2 pins' % n, len(nodes) >= 2)

    # ---- the 48-GPIO table, for the record ----
    pin_of = {f: pin for (ref, pin, f) in sum(nets.values(), []) if ref == U1}
    edge_of = {}
    for p, s in EDGE.items():
        edge_of.setdefault(edge[p], []).append('J1.%d %s' % (p, s))
    print('%-6s %-4s %-11s %s' % ('GPIO', 'pin', 'net', 'also on'))
    for g in range(48):
        n = rp(g)
        f = next(f for f in pin_of if re.match(r'GPIO%d(/|$)' % g, f))
        if unconn(n):
            continue
        more = ['%s.%s' % (r, fn or pin) for (r, pin, fn) in nets.get(n, []) if r not in (U1, J1)]
        for r, o in resistors(n).items():             # through a series R to an edge signal
            if o not in ('GND', v5, cons):
                more += edge_of.get(o, [])
        print('GP%-4d %-4s %-11s %s' % (g, pin_of[f], n, ', '.join(edge_of.get(n, []) + more)))
    print('(GPIO%s unconnected)' % ', '.join(str(g) for g in range(48) if unconn(rp(g))))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
