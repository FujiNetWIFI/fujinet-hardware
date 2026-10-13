#!/usr/bin/env python3
"""Cross-check the FujiNet-5200 Rev0 schematic netlist against the firmware that has to run on
it -- independently of tools/design.py.

Exports a fresh netlist with kicad-cli and reads
  $FUJINET_FIRMWARE/pico/atari-5200/firmware/include/a52_cart.h   every *_PIN GPIO number
      (default ~/Workspace/fujinet-firmware)
  $FUJINET_A52_BOARD/include/pinmap/fujiversal-atari5200.h        S3 SD / LED / UART pins
      (default ~/Workspace/fn-5200-board; if it is missing, the SMS board's
      $FUJINET_SMS_BOARD/include/pinmap/fujiversal-sms.h, whose S3 contract this board
      copies, default ~/Workspace/fn-sms-board), and fujiversal-intv.h there for
      PIN_RP2040_RUN/BOOTSEL when the pinmap does not define them
and checks every GPIO of both chips against the pin *functions* the netlist reports (GPIOn on
the RP2354B, IOn on the S3, An/Yn on the '541), the 5200 36-pin edge map (its own copy of the
pinout, from Atari's CX5200 Field Service Manual), the 5 V-tolerance rule for GPIO40-47, the PHI2
buffer, the supply sense dividers, the interlock, the three-source power path, and the edge
footprint's faces, pin-1 end and short interlock fingers.  The enable logic itself is
check_glue.py's.

Usage: python3 tools/check_nets.py         exit 1 on any failure
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netlist import Netlist, unconn, define, PRJ

FW = os.environ.get('FUJINET_FIRMWARE', os.path.expanduser('~/Workspace/fujinet-firmware'))
CART = os.path.join(FW, 'pico/atari-5200/firmware/include/a52_cart.h')
A52_BOARD = os.environ.get('FUJINET_A52_BOARD', os.path.expanduser('~/Workspace/fn-5200-board'))
SMS_BOARD = os.environ.get('FUJINET_SMS_BOARD', os.path.expanduser('~/Workspace/fn-sms-board'))
PINMAP = os.path.join(A52_BOARD, 'include/pinmap/fujiversal-atari5200.h')
if not os.path.exists(PINMAP):
    PINMAP = os.path.join(SMS_BOARD, 'include/pinmap/fujiversal-sms.h')
PINMAP_RUN = os.path.join(SMS_BOARD, 'include/pinmap/fujiversal-intv.h')

# Atari 5200 36-pin cartridge edge, from the CX5200 Field Service Manual (Rev 4, 1983) schematics of
# CA018087 (original 4-port), CA020108 (universal 4-port), CA021374 (2-port).  'UNREG': NC on
# CA018087, the adapter's raw DC on the universal boards; 'PHI2': GND on CA018087, PHI2 through a
# diode on the universal boards; 'VIDEO' (24): GND on CA018087, video in on the universal boards;
# 'OSC' (30): NC / the colour oscillator; 23 is the shield, GND on every board.
EDGE = {1: 'D0', 2: 'D1', 3: 'D2', 4: 'D3', 5: 'D4', 6: 'D5', 7: 'D6', 8: 'D7', 9: '/EN80', 10: '/EN40',
        11: 'UNREG', 12: 'GND', 13: 'GND', 14: 'PHI2', 15: 'A6', 16: 'A5', 17: 'A2', 18: 'ILK', 19: 'A0',
        20: 'A1', 21: 'A3', 22: 'A4', 23: 'GND', 24: 'VIDEO', 25: 'GND', 26: 'PWR', 27: 'A7', 28: 'NC',
        29: 'A8', 30: 'OSC', 31: 'A9', 32: 'A13', 33: 'A10', 34: 'A12', 35: 'A11', 36: 'ILK'}
OPEN = ('NC', 'VIDEO', 'OSC')                 # never connected: the console may drive them
INV6 = [(1, 2), (3, 4), (5, 6), (9, 8), (11, 10), (13, 12)]          # 74xx14
VAL = lambda s: float(s.replace('k', 'e3').replace('R', '').replace('nF', 'e-9').replace('uF', 'e-6'))
VIH_HCT14_MAX, VCC_MIN = 2.1, 4.5             # SN74HCT14 VT+ max (TI SCLS225G: 1.9 at 4.5 V, taken at 2.1); 74HCT VCC min
LVC17_VTN_MIN = 1.32                          # 74LVC1G17 VT- min at VCC 4.5 V (Nexperia Table 8)
PHI2_LOW_MAX = 1.15                           # console PHI2 low at edge 14: VOL(74LS125) 0.4 + VF(1N914) 0.75

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
    U1, J1, S3 = one('RP2354B'), one('Atari5200_Cart_Edge_36'), one('ESP32-S3-WROOM-1-N16R8')
    J2, UCP, WS = one('microSD'), one('CP2102N-A02-GQFN28'), one('WS2812B-2020-V6')
    U14, U08, BUF, U17 = one('74HCT14'), one('74HCT08'), one('74HCT541'), one('74LVC1G17')
    LDO, PRE, BUCK = one('AP2112K-3.3'), one('AP63205WU'), one('AP63203WU')
    for ref, what in ((U1, 'RP2354B'), (J1, 'edge'), (S3, 'ESP32-S3'), (U14, '74HCT14'), (U08, '74HCT08'),
                      (BUF, '74HCT541'), (U17, '74LVC1G17'), (LDO, 'AP2112K LDO'), (PRE, 'AP63205 raw DC buck'),
                      (BUCK, 'AP63203 buck')):
        if ref is None:
            raise SystemExit('no %s in the netlist' % what)
    glue = {U14, U08, BUF, U17}
    tps = {r for r in parts if re.match(r'TP\d+$', r)}         # bring-up / SWD test pads (no BOM part)

    def rp(gpio):
        for (ref, f), n in func_net.items():
            if ref == U1 and re.match(r'GPIO%d(/|$)' % gpio, f):
                return n
        return None

    def s3(io):
        return func_net.get((S3, 'IO%d' % io))

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

    def pulldown(n):
        """refs of resistors from n to GND"""
        return {r for r, (v, _) in parts.items() if re.match(r'R\d+$', r) and
                {node_net.get((r, '1')), node_net.get((r, '2'))} == {n, 'GND'}}
    glue_in = lambda n: any(r in glue and N.ptype.get((r, pin)) == 'input' for (r, pin, f) in nets.get(n, []))

    edge = {p: node_net.get((J1, str(p))) for p in EDGE}
    sig = {}
    for p, s in EDGE.items():
        sig.setdefault(s, edge[p])
    v5 = func_net.get((BUF, 'VCC'))

    # ---- the firmware pin contract: every *_PIN in a52_cart.h ----
    names = re.findall(r'#define\s+(\w+)_PIN\s', open(CART).read())
    P = {k: define(CART, k + '_PIN') for k in names}
    want = {'A0', 'EN40', 'EN80', 'D0', 'PWROK', 'PHI2', 'BUFEN', 'LED', 'ILK', 'VSENSE', 'DBG_TX', 'DBG_RX'}
    chk('a52_cart.h defines exactly the pins this board wires (%s)' % sorted(set(names) ^ want), set(names) == want)
    claimed = list(range(P['A0'], P['A0'] + 14)) + list(range(P['D0'], P['D0'] + 8)) + \
        [P[k] for k in sorted(want - {'A0', 'D0'})]
    chk('a52_cart.h claims no GPIO twice', len(claimed) == len(set(claimed)) and max(claimed) < 48)
    chk('the bus word: A0-A13 then /EN40, /EN80 in gpio[15:0] (OFF_MASK / EN_MASK)',
        P['A0'] == 0 and (P['EN40'], P['EN80']) == (14, 15) and define(CART, 'OFF_MASK') == 0x7FFF)
    for g in range(48):
        if g in claimed:
            chk('GP%d is connected' % g, not unconn(rp(g)))
        else:
            chk('GP%d (not in a52_cart.h) is unconnected' % g, unconn(rp(g)))

    # ---- edge <-> RP2354B / '541 ----
    for p, s in EDGE.items():
        n = edge[p]
        if s == 'GND':
            chk('J1.%d is GND' % p, n == 'GND')
        elif s in OPEN:
            chk('J1.%d (%s) is left open' % (p, s), unconn(n))
        elif s == 'PWR':
            chk('J1.26 is the console 5 V (VR1), not the cart rail', not unconn(n) and n not in (v5, 'GND'))
        elif s == 'UNREG':
            chk('J1.11 (raw DC) is never GND or a cart rail', not unconn(n) and n not in (v5, 'GND', sig['PWR']))
        elif s == 'PHI2':           # GND on CA018087: never the cart's GND, never driven by the cart
            g = P['PHI2']
            chk('J1.14 PHI2 -> 74LVC1G17 input (not GND)', n != 'GND' and func_net.get((U17, 'A')) == n
                or node_net.get((U17, '2')) == n)
            chk('74LVC1G17 output -> GP%d' % g, node_net.get((U17, '4')) == rp(g) and not unconn(rp(g)))
            chk('74LVC1G17 on the cart 5 V rail', node_net.get((U17, '5')) == v5 and node_net.get((U17, '3')) == 'GND')
            pu = through_r(n, sig['PWR'])
            chk('J1.14 pulled up from the console 5 V (edge 26), not the cart rail: %s' % pu, pu is not None)
            if pu:
                chk('PHI2 pull-up %s: <= 4.7k (reaches VT+ inside PHI2 high), >= 2.2k (diode / LS125 sink)' % pu,
                    2.2e3 <= VAL(pu) <= 4.7e3)
            chk('PHI2 low %.2f V worst < 74LVC1G17 VT- min %.2f V' % (PHI2_LOW_MAX, LVC17_VTN_MIN),
                PHI2_LOW_MAX < LVC17_VTN_MIN)
            chk('J1.14 net: the finger, its pull-up, the buffer and a test pad only',
                not [r for r, _ in others(n, {J1, U17} | tps) if not r.startswith('R')])
        elif s == 'ILK':
            chk('J1.%d interlock is not GND or a rail' % p, not unconn(n) and n not in ('GND', v5))
        elif s in ('/EN40', '/EN80'):
            g = P[s[1:]]
            chk('J1.%d %s -> GP%d' % (p, s, g), n == rp(g) and not unconn(n))
            chk('J1.%d %s -> a 74HCT08 input' % (p, s),
                any(r == U08 and N.ptype.get((r, pin)) == 'input' for (r, pin, f) in nets.get(n, [])))
        elif s.startswith('A'):
            g = P['A0'] + int(s[1:])
            chk('J1.%d %s -> GP%d' % (p, s, g), n == rp(g) and not unconn(n))
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
        else:
            chk('J1.%d %s: unexpected edge signal' % (p, s), False)
    chk('the edge GND fingers 12, 13, 23, 25 are one net', len({edge[p] for p in (12, 13, 23, 25)}) == 1)
    for i in range(14):
        chk('A%d carries no extra parts (no pulls, no series R; test pads allowed)' % i,
            not others(sig['A%d' % i], {J1, U1} | tps))
    for s in ('/EN40', '/EN80'):
        chk('%s carries the RP, the 74HCT08 and a test pad only' % s, not others(sig[s], {J1, U1, U08} | tps))
    chk('GP%d (PHI2_RP): the RP and the buffer only' % P['PHI2'], not others(rp(P['PHI2']), {U1, U17} | tps))

    # ---- the RP's own outputs and inputs ----
    pwr_ok_pin = rp(P['PWROK'])
    bufen = rp(P['BUFEN'])
    chk('GP%d (BUF_EN) -> a 74HCT glue input' % P['BUFEN'], glue_in(bufen))
    pd = pulldown(bufen)
    chk('GP%d (BUF_EN) pulled down by <= 8.2k: the 541 stays off until the firmware drives it (RP2350-E9)'
        % P['BUFEN'], len(pd) == 1 and VAL(parts[next(iter(pd))][0]) <= 8.2e3)
    chk('GP%d (BUF_EN): drives only 5 V CMOS inputs and its pull-down' % P['BUFEN'],
        not [(r, pin) for (r, pin, f) in nets.get(bufen, [])
             if r != U1 and N.ptype.get((r, pin)) != 'input' and r not in pd and r not in tps])
    led = one('red')
    chk('GP%d (LED) -> 1k -> LED anode, cathode GND' % P['LED'],
        led is not None and through_r(rp(P['LED']), node_net.get((led, '2'))) == '1k' and node_net.get((led, '1')) == 'GND')
    hdr = one('DBG UART')
    chk('GP%d DBG_TX -> header 1, GP%d DBG_RX -> header 2, header 3 GND' % (P['DBG_TX'], P['DBG_RX']),
        hdr is not None and node_net.get((hdr, '1')) == rp(P['DBG_TX']) and node_net.get((hdr, '2')) == rp(P['DBG_RX'])
        and node_net.get((hdr, '3')) == 'GND')

    # ---- interlock: 18-36 shorted by the solder jumper; the DNP low-side switch from GPIO28 beside it ----
    ia, ib = edge[18], edge[36]
    jp = [r for r, (v, fp) in parts.items() if r.startswith('JP') and
          {node_net.get((r, '1')), node_net.get((r, '2'))} == {ia, ib}]
    chk('interlock 18-36 joined by a bridged solder jumper', ia != ib and len(jp) == 1 and 'Bridged' in parts[jp[0]][1])
    chk('interlock nets carry nothing else from the cart (no GND, no rail)',
        all(n not in ('GND', v5, sig['PWR']) for n in (ia, ib)))
    sw = [r for r, (v, fp) in parts.items() if v == '2N7002' and node_net.get((r, '2')) == ia and node_net.get((r, '3')) == ib]
    chk('an N-FET across the pair, low side: S = CI1 (pin 18, pulled low by the console), D = CI2 (pin 36)', len(sw) == 1)
    if sw:
        gate = node_net.get((sw[0], '1'))
        chk('its gate pulled up to the cart rail (closed whenever the cart has power)', through_r(gate, v5) is not None)
        drv = [r for r, (v, fp) in parts.items() if v == '2N7002' and node_net.get((r, '1')) == rp(P['ILK'])]
        chk('GP%d (ILK) -> 2N7002 gate, source GND, drain on the switch gate' % P['ILK'],
            len(drv) == 1 and node_net.get((drv[0], '2')) == 'GND' and node_net.get((drv[0], '3')) == gate)
        pdi = pulldown(rp(P['ILK']))
        chk('GP%d (ILK) pulled down by <= 8.2k (RP2350-E9: a latched pad would open the interlock)' % P['ILK'],
            len(pdi) == 1 and VAL(parts[next(iter(pdi))][0]) <= 8.2e3)
        dnp = set(N.dnp)
        chk('the interlock switch (FETs and their resistors) is DNP in Rev0',
            sw[0] in dnp and all(d in dnp for d in drv) and all(r in dnp for r in pdi) and
            all(r in dnp for r in [r for r in parts if re.match(r'R\d+$', r) and through_r(gate, v5) and
                                   {node_net.get((r, '1')), node_net.get((r, '2'))} == {gate, v5}]))

    # ---- GPIO40-47 are not 5 V tolerant: the ADC sense or the 3.3 V debug header only ----
    for g in range(40, 48):
        n = rp(g)
        if unconn(n):
            continue
        bad = [(r, pin, N.ptype.get((r, pin))) for (r, pin, f) in nets.get(n, [])
               if r != U1 and N.ptype.get((r, pin)) not in ('passive',) and r != hdr]
        chk('GP%d (%s): nothing but passives or the 3.3 V debug header on the net' % (g, n), not bad)
        chk('GP%d (%s): never an edge signal' % (g, n), n not in edge.values())

    # ---- supply sense: edge pin 26 (VR1) -> divider -> ADC (GPIO40) ----
    cons = sig['PWR']
    adc = rp(P['VSENSE'])
    top, bot = through_r(cons, adc), through_r(adc, 'GND')
    chk('GP%d (VSENSE) <- edge 26 through a divider' % P['VSENSE'], top is not None and bot is not None)
    if top and bot:
        r = VAL(bot) / (VAL(top) + VAL(bot))
        chk('ADC divider %.3f: 5.0 V reads %.2f V; the pad stays under 3.0 V up to %.1f V (want >= 5.5 V)'
            % (r, 5 * r, 3.0 / r), 3.0 / r >= 5.5 and 5 * r >= 1.0)
    chk('ADC pin: a filter capacitor to GND', through_c(adc, 'GND') is not None)

    # ---- PWR_OK: edge 26 -> divider -> '14 -> '14 -> GP24 and the glue ----
    vsense = next((node_net.get((U14, str(pa))) for pa, py in INV6
                   if through_r(cons, node_net.get((U14, str(pa)))) is not None), None)
    chk("a '14 input is fed from edge 26 through a resistor (VSENSE)", vsense is not None)
    top, bot = through_r(cons, vsense), through_r(vsense, 'GND')
    chk('VSENSE divider to GND', top is not None and bot is not None)
    if top and bot:
        rt, rb = VAL(top), VAL(bot)
        r = rb / (rt + rb)
        chk('VSENSE %.2f x: a 4.75 V supply gives %.2f V, over the 74HCT14 VT+ max %.1f V' % (r, 4.75 * r, VIH_HCT14_MAX),
            4.75 * r > VIH_HCT14_MAX + 0.5)
        chk('VSENSE at 5.25 V (78M05 max): %.2f V, under the 4.5 V the cart rail can sag to (no input-clamp '
            'current)' % (5.25 * r), 5.25 * r < VCC_MIN)
    pwr_ok = inv(inv(vsense))
    chk('PWR_OK = !!VSENSE on the Schmitt', pwr_ok is not None)
    chk('PWR_OK -> GP%d' % P['PWROK'], pwr_ok == pwr_ok_pin)
    chk('PWR_OK -> the glue', glue_in(pwr_ok))
    for r in sorted(glue):
        vcc, gnd = ('20', '10') if r == BUF else ('5', '3') if r == U17 else ('14', '7')
        chk('%s %s on the cart 5V rail' % (r, parts[r][0]), node_net.get((r, vcc)) == v5 and node_net.get((r, gnd)) == 'GND')
    for pa, py in INV6:
        if unconn(node_net.get((U14, str(py)))):
            chk("'14 unused gate (pin %d): input tied to GND" % pa, node_net.get((U14, str(pa))) == 'GND')
    for ins, out in (((1, 2), 3), ((4, 5), 6), ((9, 10), 8), ((12, 13), 11)):
        if unconn(node_net.get((U08, str(out)))):
            chk("'08 unused gate (pin %d): inputs tied to GND" % out, all(node_net.get((U08, str(i))) == 'GND' for i in ins))

    # ---- power path: +5V = CONS_5V (P-FET) | VBUS (SS34) | PRE5V (raw DC buck, SS34) ----
    vbus = node_net.get((one('USB-C'), 'A4'))
    QFET = next((r for r, (v, _) in parts.items() if v == 'AO3401A' and node_net.get((r, '2')) == v5), None)
    chk('CONS_5V (edge 26) -> P-FET drain, source = cart 5V rail', QFET is not None and node_net.get((QFET, '3')) == cons)
    pre5 = func_net.get((PRE, 'FB'))
    gate = node_net.get((QFET, '1')) if QFET else None
    ors = [r for r, (v, _) in parts.items() if v == 'BAT54C' and node_net.get((r, '3')) == gate]
    chk('P-FET gate = VBUS | PRE5V through a BAT54C (common cathode on the gate)',
        len(ors) == 1 and {node_net.get((ors[0], '1')), node_net.get((ors[0], '2'))} == {vbus, pre5})
    chk('P-FET gate pulled down (console path on by default)', bool(pulldown(gate)))
    ss34 = lambda a: any(val == 'SS34' and node_net.get((r, '2')) == a and node_net.get((r, '1')) == v5
                         for r, (val, _) in parts.items())
    chk('VBUS -> SS34 -> cart 5V rail', ss34(vbus))
    chk('PRE5V -> SS34 -> cart 5V rail', ss34(pre5))
    for n, what in ((vbus, 'VBUS'), (pre5, 'PRE5V')):
        chk('%s held low against the SS34 leakage: <= 4.7k' % what, any(VAL(parts[r][0]) <= 4.7e3 for r in pulldown(n)))
    raw = sig['UNREG']
    jpu = [r for r, (v, fp) in parts.items() if r.startswith('JP') and raw in (node_net.get((r, '1')), node_net.get((r, '2')))]
    chk('edge 11 (raw DC) -> a bridged solder jumper only', len(jpu) == 1 and not others(raw, {J1, jpu[0]} | tps))
    if jpu:
        after = ({node_net.get((jpu[0], '1')), node_net.get((jpu[0], '2'))} - {raw}).pop()
        fuse = [r for r, (v, fp) in parts.items() if r.startswith('F') and after in (node_net.get((r, '1')), node_net.get((r, '2')))]
        chk('then a PTC fuse', len(fuse) == 1 and 'Fuse' in parts[fuse[0]][1])
        if fuse:
            fused = ({node_net.get((fuse[0], '1')), node_net.get((fuse[0], '2'))} - {after}).pop()
            vin = func_net.get((PRE, 'IN'))
            chk('then a resistor into the AP63205 IN (inrush)', through_r(fused, vin) is not None)
            chk('AP63205 EN on its IN (3.8-32 V)', func_net.get((PRE, 'EN')) == vin)
            caps = [r for r, (v, fp) in parts.items() if r.startswith('C') and {node_net.get((r, '1')), node_net.get((r, '2'))} == {vin, 'GND'}]
            chk('raw DC capacitors are 25 V or more (%s)' % ', '.join('%s %s' % (r, parts[r][0]) for r in caps),
                caps and all(parts[r][0] in ('22uF', '100nF', '1uF') for r in caps))
    chk('AP63205 FB on its output (fixed 5 V), the inductor from SW to it',
        any(r.startswith('L') and {node_net.get((r, '1')), node_net.get((r, '2'))} == {func_net.get((PRE, 'SW')), pre5}
            for r in parts))
    chk('AP63203 (3.3 V buck) fed from the cart 5V rail', func_net.get((BUCK, 'IN')) == v5)
    chk('nothing but the P-FET, its capacitors, the sense dividers, the PHI2 pull-up and a test pad on edge 26',
        not [r for r, _ in others(cons, {J1, QFET} | tps) if not re.match(r'(R|C)\d+$', r)])

    # ---- RP support: everything on the LDO rail ----
    v33io = func_net.get((U1, 'IOVDD'))
    chk('RP IOVDD rail is the LDO output, LDO fed from the 5V rail, EN = VIN',
        node_net.get((LDO, '5')) == v33io and node_net.get((LDO, '1')) == v5 and node_net.get((LDO, '3')) == v5)
    v_in = func_net.get((U1, 'VREG_VIN'))
    chk('RP VREG_VIN on the IOVDD rail', v_in == v33io)
    chk('VREG_AVDD from VREG_VIN through 33R', through_r(v_in, func_net.get((U1, 'VREG_AVDD'))) == '33R')
    v33 = func_net.get((S3, '3V3'))
    chk('S3 3V3 is the buck rail, not the LDO', v33 not in (v33io, v5, None))
    chk('RP USB_DP -> 27R -> S3 USB_D+ (IO20)', through_r(func_net.get((U1, 'USB_DP')), func_net.get((S3, 'USB_D+'))) == '27R')
    chk('RP USB_DM -> 27R -> S3 USB_D- (IO19)', through_r(func_net.get((U1, 'USB_DM')), func_net.get((S3, 'USB_D-'))) == '27R')
    print('note: S3 pins from %s' % PINMAP)
    run_io, bsel_io = define(PINMAP, 'PIN_RP2040_RUN', -2), define(PINMAP, 'PIN_RP2040_BOOTSEL', -2)
    if run_io == -2 or bsel_io == -2:
        run_io, bsel_io = define(PINMAP_RUN, 'PIN_RP2040_RUN'), define(PINMAP_RUN, 'PIN_RP2040_BOOTSEL')
        print('note: %s does not define PIN_RP2040_RUN/BOOTSEL; using fujiversal-intv.h (IO%d/IO%d)'
              % (os.path.basename(PINMAP), run_io, bsel_io))
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

    # ---- S3 pins: the pinmap ----
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
        print('note: %s leaves PIN_CARD_DETECT NC; the board wires card-detect to IO%s '
              '(pulled up) as the 7800 / NES / SMS boards do, unused by the firmware' % (os.path.basename(PINMAP), cd_io))
    ws_din = node_net.get((WS, '3'))
    chk('LED strip IO%d -> R -> WS2812 DIN' % led_strip, through_r(s3(led_strip), ws_din) is not None)
    chk('PIN_UART0_TX/RX are the module TXD0/RXD0 pads (GPIO43/44)', (uart_tx, uart_rx) == (43, 44))
    chk('S3 TXD0 -> CP2102N RXD', func_net.get((S3, 'TXD0')) == func_net.get((UCP, 'RXD')))
    chk('S3 RXD0 <- CP2102N TXD', func_net.get((S3, 'RXD0')) == func_net.get((UCP, 'TXD')))
    contract = set(sd.values()) | {led_strip, run_io, bsel_io, 19, 20, 0} | ({card} if card >= 0 else {cd_io})
    for (r, f), n in sorted(func_net.items()):
        if r == S3 and re.match(r'IO\d+$', f) and not unconn(n):
            chk('S3 %s (%s) is in the pin contract' % (f, n), int(f[2:]) in contract)
    for io in (3, 45, 46):
        chk('S3 strapping IO%d unloaded' % io, unconn(s3(io)))
    for io in range(26, 38):
        chk('S3 IO%d (flash/PSRAM on N16R8) unused' % io, unconn(s3(io)))

    # ---- edge footprint: 18 positions at 2.54 mm per face, pins 1-18 F.Cu, pin k over pin 37-k,
    # pin 1 at the left, 18 / 36 short (audit/edge_orientation.py has the sources) ----
    from sexpr import parse as sparse, findall as sfindall, find as sfind
    fpe = sparse(open(os.path.join(PRJ, 'FujiNet-5200.pretty', 'Atari5200_Cart_Edge_36.kicad_mod')).read())
    pads = {int(p[1]): (float(sfind(p, 'at')[1]), sfind(p, 'layers')[1][0]) for p in sfindall(fpe, 'pad')}
    chk('edge footprint has 36 pads', sorted(pads) == list(range(1, 37)))
    if sorted(pads) == list(range(1, 37)):
        chk('edge: pins 1-18 on F.Cu, 19-36 on B.Cu, pin k over pin 37-k',
            all(pads[k][1] == 'F' and pads[37 - k][1] == 'B' and pads[k][0] == pads[37 - k][0] for k in range(1, 19)))
        steps = [round(pads[k + 1][0] - pads[k][0], 3) for k in range(1, 18)]
        chk('edge: 2.54 mm pitch, pin 1 at the left (-x), centred',
            steps == [2.54] * 17 and pads[1][0] < 0 < pads[18][0] and abs(pads[1][0] + pads[18][0]) < 1e-6)
        start = {int(p[1]): -(float(sfind(p, 'at')[2]) + float(sfind(p, 'size')[2]) / 2) for p in sfindall(fpe, 'pad')}
        chk('edge: pins 18 / 36 (interlock) start >= 1 mm further from the edge than the rest (last-make)',
            min(start[18], start[36]) >= max(v for k, v in start.items() if k not in (18, 36)) + 1.0)

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
        if unconn(n):
            continue
        more = edge_of.get(n, []) + ['%s.%s' % (r, fn or pin) for (r, pin, fn) in nets.get(n, []) if r not in (U1, J1)]
        print('GP%-4d %-4s %-10s %s' % (g, pin_of[f], n, ', '.join(more)))
    print('(GPIO%s unconnected)' % ', '.join(str(g) for g in range(48) if unconn(rp(g))))
    print('%d checks, %d failed' % (count, fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
