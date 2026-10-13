#!/usr/bin/env python3
"""ngspice checks the kicad-happy subcircuit simulator does not set up for this board (it drives
every divider from a 3.3 V test source):

1. PWR_OK sense: CONS_5V swept 0-5.5 V into the 22k / 100k divider with the SN74HCT14 input
   (+-1 uA leakage, 10 pF); the console voltages at which VSENSE crosses the HCT14's VT+ / VT-
   limits (TI SN74HCT14 datasheet: VT+ 1.2-1.9 V at 4.5 V, 1.4-2.1 V at 5.5 V; VT- 0.5-1.2 /
   0.6-1.4 V).
2. The console-path gate CONS_OFF (AO3401A, D = CONS_5V, S = +5V), the console powering the
   cart: the reverse leakage of both SS34s (D_VBUS, D_PRE: sourced from +5V into VBUS and PRE5V,
   so neither node can rise above it) into their 4.7k pull-downs, through the BAT54C OR and the
   100k gate pull-down; VGS against the AO3401A's RDS(on) point (-2.5 V) and VGS(th) (-0.5 to
   -1.3 V).  Then the gate after USB is unplugged with the console running, and the share of the
   cart's load the console still carries through the FET's body diode when raw DC or USB runs
   the cart.
3. PHI2 on the 2-port console (CA021374: a 74LS125 through CR9, a 1N914 with its anode at pin
   14): the cart's 4.7k pull-up to CONS_5V and the 74LVC1G17 input at 1.79 MHz; the low level
   against VT- min 1.32 V (VCC 4.5 V) and the rise to VT+ max 2.36 / 2.79 V (VCC 4.5 / 5.5 V)
   (Nexperia 74LVC1G17 Table 8).

Decks and logs go to analysis/helpers/spice/.  Values come from tools/design.py.
Usage: python3 tools/audit/spice_checks.py
"""
import os, re, subprocess, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

OUT = os.path.join(PRJ, 'analysis', 'helpers', 'spice')
MULT = {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}


def val(p):
    m = re.match(r'([\d.]+)([kMR]?)', p.value)
    return float(m.group(1)) * MULT[m.group(2)]


def res(a, b):
    for p in D.PARTS:
        if p.prefix == 'R' and sorted(v for v in p.pins.values()) == sorted([a, b]):
            return p.ref, val(p)
    return None, None


def run(name, deck):
    os.makedirs(OUT, exist_ok=True)
    cir = os.path.join(OUT, name + '.cir')
    open(cir, 'w').write(deck)
    r = subprocess.run(['ngspice', '-b', cir], capture_output=True, text=True)
    open(os.path.join(OUT, name + '.log'), 'w').write(r.stdout + r.stderr)
    return r.stdout


def meas(out, key):
    m = re.search(r'^\s*%s\s*=\s*([-+0-9.eE]+)' % re.escape(key), out, re.M)
    return float(m.group(1)) if m else None


def printed(out, node):
    m = re.search(r'%s\s*=\s*([-+0-9.eE]+)' % re.escape(node), out)
    return float(m.group(1)) if m else float('nan')


# BAT54C (Nexperia BAT54 series: VF <= 320 mV at 1 mA, 400 mV at 10 mA): fitted Shockley model
BAT54 = '.model bat54 D(IS=1e-7 N=1.34 RS=2 CJO=10p)'
# SS34 (Vishay: VF 0.5 V at 3 A): forward model for the OR; its reverse leakage is a current source
SS34 = '.model ss34 D(IS=5e-6 N=1.2 RS=0.03 CJO=200p)'
# AO3401A: level-1 P-MOS, VTO -0.9 V typ (datasheet -0.5..-1.3), K from RDS(on) 60 mOhm at -4.5 V;
# its body diode drain -> source
AO3401 = ('.model ao3401 PMOS(LEVEL=1 VTO=-0.9 KP=4.6 CGSO=1n)\n'
          '.model bodyd D(IS=1e-12 N=1.0 RS=0.02)')
# 1N914 / 1N4148 (the console's CR9); TT from its 4 ns trr, so the stored charge does not flatter the rise
D1N914 = '.model d1n914 D(IS=2.52n N=1.752 RS=0.568 CJO=4p M=0.4 TT=4n BV=100)'   # trr <= 4 ns


def main():
    # ---- 1. PWR_OK sense ----------------------------------------------------------------------
    rt_ref, rt = res('CONS_5V', 'VSENSE')
    rb_ref, rb = res('VSENSE', 'GND')
    lines = []
    for leak, tag in ((1e-6, 'src'), (-1e-6, 'snk')):
        deck = '''* VSENSE divider %s %g / %s %g, HCT14 input leakage %g A
V1 cons 0 DC 0
R1 cons vs %g
R2 vs 0 %g
I1 0 vs DC %g
C1 vs 0 10p
.control
dc V1 0 5.5 0.001
meas dc c_19 when v(vs)=1.9 rise=1
meas dc c_21 when v(vs)=2.1 rise=1
meas dc c_05 when v(vs)=0.5 rise=1
meas dc c_14 when v(vs)=1.4 rise=1
meas dc v_45 find v(vs) at=4.5
meas dc v_50 find v(vs) at=5.0
meas dc v_55 find v(vs) at=5.5
.endc
.end
''' % (rt_ref, rt, rb_ref, rb, leak, rt, rb, leak)
        o = run('vsense_' + tag, deck)
        lines.append('  leakage %+.0f uA: VSENSE %.3f / %.3f / %.3f V at CONS_5V 4.5 / 5.0 / 5.5 V; crosses VT+max 1.9 V at '
                     '%.2f V, 2.1 V at %.2f V; VT-min 0.5 V at %.2f V, VT-max 1.4 V at %.2f V'
                     % (leak * 1e6, meas(o, 'v_45'), meas(o, 'v_50'), meas(o, 'v_55'), meas(o, 'c_19'), meas(o, 'c_21'),
                        meas(o, 'c_05'), meas(o, 'c_14')))
    print('== 1. PWR_OK sense (%s %gk / %s %gk) into SN74HCT14 VT+ 1.2-1.9 V (4.5 V) / 1.4-2.1 V (5.5 V), '
          'VT- 0.5-1.2 / 0.6-1.4 V' % (rt_ref, rt / 1e3, rb_ref, rb / 1e3))
    print('\n'.join(lines))

    # ---- 2. the console-path gate ----------------------------------------------------------------
    vh_ref, vh = res('VBUS', 'VBUS_SNS')
    vl_ref, vl = res('VBUS_SNS', 'GND')
    vpd_ref, vpd = res('VBUS', 'GND')
    ppd_ref, ppd = res('PRE5V', 'GND')
    opd_ref, opd = res('CONS_OFF', 'GND')
    assert vpd and ppd and opd, 'R_VBPD / R_PREPD / R_OFFPD missing from design.py'
    k = D.KEY
    print('\n== 2. %s AO3401A gate CONS_OFF = %s BAT54C OR of VBUS / PRE5V, %s %gk to GND; the console '
          'powering the cart (+5V 5.0 V)' % (k['Q_CONS'], k['D_OFF'], opd_ref, opd / 1e3))
    print('  SS34 reverse leakage from +5V into VBUS (%s %gk, %s+%s) and PRE5V (%s %gk), both diodes leaking '
          '(Vishay IR max at the rated 40 V: 0.5 mA at 25 C, 20 mA at 100 C; at 5 V it is far less):'
          % (vpd_ref, vpd / 1e3, vh_ref, vl_ref, ppd_ref, ppd / 1e3))
    for ua in (10, 100, 500, 1000):
        deck = '''* CONS_OFF under SS34 leakage %d uA into VBUS and PRE5V
V5 v5 0 DC 5.0
I1 0 vbus DC %gu
I2 0 pre DC %gu
Rv vbus 0 %g
Rh vbus sns %g
Rl sns 0 %g
Rp pre 0 %g
Dclv vbus v5 ss34
Dclp pre v5 ss34
D1 vbus off bat54
D2 pre off bat54
Ro off 0 %g
%s
%s
.op
.control
op
print v(vbus) v(pre) v(off)
.endc
.end
''' % (ua, ua, ua, vpd, vh, vl, ppd, opd, BAT54, SS34)
        o = run('cons_off_%d' % ua, deck)
        voff = printed(o, 'v(off)')
        vgs = voff - 5.0
        print('    %5d uA each: VBUS %.2f V, PRE5V %.2f V -> CONS_OFF %.2f V, VGS %+.2f V: %s'
              % (ua, printed(o, 'v(vbus)'), printed(o, 'v(pre)'), voff, vgs,
                 'on (RDS(on) specified)' if vgs <= -2.5 else 'on (VGS beyond VGS(th) max -1.3 V)'
                 if vgs <= -1.3 else 'NOT reliably on'))
    # USB unplugged with the console running: VBUS decays through its pull-down + divider and caps
    cvb = sum({'1uF': 1e-6, '100nF': 1e-7}.get(p.value, 0) for p in D.PARTS if p.prefix == 'C' and 'VBUS' in p.pins.values())
    deck = '''* USB unplugged, console running: VBUS %g F from 5.0 V, CONS_OFF follows through the BAT54C
Cv vbus 0 %g IC=5.0
Rv vbus 0 %g
Rh vbus sns %g
Rl sns 0 %g
I1 0 vbus DC 50u
D1 vbus off bat54
Ro off 0 %g
Cg off 0 645p IC=4.7
%s
.tran 10u 100m UIC
.control
run
meas tran t_th when v(off)=3.7 fall=1
meas tran t_on when v(off)=2.5 fall=1
.endc
.end
''' % (cvb, cvb, vpd, vh, vl, opd, BAT54)
    o = run('usb_unplug', deck)
    print('  USB unplugged, console running (VBUS %.1f uF, 50 uA leakage, AO3401A Ciss 645 pF): VGS reaches -1.3 V '
          '(conducting) after %.2f ms, -2.5 V (RDS(on) specified) after %.2f ms; until then the console feeds +5V '
          'through the body diode' % (cvb * 1e6, (meas(o, 't_th') or float('nan')) * 1e3, (meas(o, 't_on') or float('nan')) * 1e3))
    # raw DC (or USB) running the cart: how much of the load the console still carries
    print('  raw DC running the cart (PRE5V from the AP63205: 4.95-5.05 V), 400 mA load on +5V, VR1 4.75-5.25 V:')
    for vpre in (4.95, 5.05):
        for vcons in (4.75, 5.0, 5.25):
            deck = '''* PRE5V %g V vs CONS_5V %g V, 400 mA on +5V
Vp pre 0 DC %g
Vc cons 0 DC %g
Dp pre v5 ss34
Dq pre off bat54
Ro off 0 %g
M1 cons off v5 v5 ao3401 W=1 L=1
Db cons v5 bodyd
Il v5 0 DC 0.4
%s
%s
%s
.op
.control
op
print v(v5) v(off) i(Vc)
.endc
.end
''' % (vpre, vcons, vpre, vcons, opd, BAT54, SS34, AO3401)
            o = run('rawdc_%g_%g' % (vpre, vcons), deck)
            ic = -printed(o, 'i(vc)')
            print('    PRE5V %.2f, CONS_5V %.2f: +5V %.2f V, VGS %+.2f V, from the console %.0f mA'
                  % (vpre, vcons, printed(o, 'v(v5)'), printed(o, 'v(off)') - printed(o, 'v(v5)'), ic * 1e3))

    # ---- 3. PHI2 on the 2-port console -----------------------------------------------------------
    pu_ref, pu = res('CONS_5V', 'PHI2')
    f = 3.579545e6 / 2                             # NTSC 5200: PHI2 = 1.79 MHz
    per = 1 / f
    print('\n== 3. PHI2, 2-port console: 74LS125 (VOL 0.35-0.5 V, VOH 2.7-3.4 V, can source only) -> CR9 1N914 '
          '(anode at pin 14) -> the cart: %s %gk to CONS_5V, %s 74LVC1G17 (CI 5 pF) + 7 pF board, %.3f MHz'
          % (pu_ref, pu / 1e3, k['U_PHI2'], f / 1e6))
    for vol, vcons, cl in ((0.35, 5.0, 12e-12), (0.5, 4.75, 12e-12), (0.5, 4.75, 25e-12)):
        deck = '''* PHI2 through the console's isolation diode
Vlo lo 0 DC %g
Vhi hi 0 DC 3.4
* lowc high: the LS125 drives low; highc = 1 - lowc: it drives high
Vck lowc 0 PULSE(0 1 0 5n 5n %g %g)
Bn highc 0 V=1-v(lowc)
* the LS125 output: a 15R sink to VOL, or an emitter follower to VOH (source only)
Slo ls lo lowc 0 sw
Shi hs hi highc 0 sw
Dhi hs ls dlin
Rls ls 0 100k
.model sw SW(VT=0.5 VH=0.1 RON=15 ROFF=1e9)
.model dlin D(IS=1e-14)
* CR9: anode at the cart's pin 14, cathode on the LS125
Dcr pin ls d1n914
Rpu cons pin %g
Vcons cons 0 DC %g
Cl pin 0 %g
%s
.tran 0.5n %g
.control
run
meas tran vlow find v(pin) at=%g
meas tran vhigh find v(pin) at=%g
meas tran t_rel when v(lowc)=0.5 fall=2
meas tran t_236 when v(pin)=2.36 rise=2
meas tran t_279 when v(pin)=2.79 rise=2
meas tran t_132 when v(pin)=1.32 fall=2
meas tran t_drv when v(lowc)=0.5 rise=2
.endc
.end
''' % (vol, per / 2, per, pu, vcons, cl, D1N914, 3 * per, 1.25 * per, 1.95 * per)
        o = run('phi2_%g_%g_%g' % (vol, vcons, cl * 1e12), deck)
        tr, td = meas(o, 't_rel') or 0.0, meas(o, 't_drv') or 0.0
        t236, t279, t132 = meas(o, 't_236'), meas(o, 't_279'), meas(o, 't_132')
        vlow = meas(o, 'vlow')
        dt = lambda t, t0: ('%.0f' % ((t - t0) * 1e9)) if t else 'n/a'
        print('  LS125 VOL %.2f V, CONS_5V %.2f V, %2.0f pF: pin 14 low %.2f V (VT- min 1.32 V: %+.2f V margin), high %.2f V; '
              'rises past 2.36 / 2.79 V %s / %s ns after the console lets go, falls past 1.32 V %s ns after it pulls '
              'low (half period %.0f ns)'
              % (vol, vcons, cl * 1e12, vlow, 1.32 - vlow, meas(o, 'vhigh'), dt(t236, tr), dt(t279, tr), dt(t132, td),
                 per / 2 * 1e9))


if __name__ == '__main__':
    main()
