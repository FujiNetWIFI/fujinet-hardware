#!/usr/bin/env python3
"""ngspice checks the kicad-happy subcircuit simulator does not set up for this
board (it drives every divider from a 3.3 V test source):

1. PWR_OK sense: CONS_5V swept 0-5.5 V into the 22k/100k divider with the
   SN74HCT14 input (+-1 uA leakage, 10 pF); the console voltages at which VSENSE
   crosses the HCT14's VT+ / VT- limits.
2. P-FET gate (the VBUS net, no USB): the SS34's reverse leakage (sourced from
   +5V, so the node cannot rise above it) into the pull-down; plus the gate's decay
   after USB is unplugged with the console running (time until VGS < -2.5 V).
3. /IRQ: 2N7002 (level-1, VTO 1.6 / 2.5 V, K from ID(on) 500 mA at VGS 10 V) with GPIO28 at
   3.3 V against the console's R32 2.2k pull-up.
4. Cart audio: GPIO29 PWM (3.3 Vpp) through the board's RC into the console's EXT AUDIO input
   (C10 0.1 uF + R5 6.8k into its audio sum, modelled as a virtual ground), against a POKEY
   cart's network (1k pull-up, 12k series, 3.3 Vpp at the POKEY AUD pin); current into the sum
   at 100 Hz, 1 kHz, 5 kHz.
5. /HALT: MARIA's HALT (modelled as the ~550 ohm pull-up that meets its 30 ns / 25 pF rating) at
   the finger, with the board's R_HALT and ~17 pF behind it vs ~18 pF straight on the line: the
   console-side rise time.

Decks and logs go to analysis/helpers/spice/.  Values come from tools/design.py.
Usage: python3 tools/audit/spice_checks.py
"""
import os, re, subprocess, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

OUT = os.path.join(PRJ, 'analysis', 'helpers', 'spice')


def res(a, b):
    for p in D.PARTS:
        if p.prefix == 'R' and sorted(p.pins.values()) == sorted([a, b]):
            m = re.match(r'([\d.]+)([kMR]?)', p.value)
            return p.ref, float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]
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


def main():
    # ---- 1. VSENSE ------------------------------------------------------------------------
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
        lines.append('  leakage %+.0f uA: VSENSE %.3f / %.3f / %.3f V at CONS_5V 4.5 / 5.0 / 5.5 V; crosses VT+max 1.9 V at %.2f V, 2.1 V at %.2f V;'
                     ' VT-min 0.5 V at %.2f V, VT-max 1.4 V at %.2f V'
                     % (leak * 1e6, meas(o, 'v_45'), meas(o, 'v_50'), meas(o, 'v_55'), meas(o, 'c_19'), meas(o, 'c_21'),
                        meas(o, 'c_05'), meas(o, 'c_14')))
    print('== 1. PWR_OK sense (%s %s / %s %s) into SN74HCT14 VT+ 1.2-1.9 V (4.5 V) / 1.4-2.1 V (5.5 V), VT- 0.5-1.2 / 0.6-1.4 V'
          % (rt_ref, '%gk' % (rt / 1e3), rb_ref, '%gk' % (rb / 1e3)))
    print('\n'.join(lines))

    # ---- 2. P-FET gate --------------------------------------------------------------------
    h_ref, h = res('VBUS', 'VBUS_SNS')
    l_ref, l = res('VBUS_SNS', 'GND')
    pd_ref, pd = res('VBUS', 'GND')
    print('\n== 2. AO3401A gate = VBUS net, console powering the cart (+5V = 5.0 V), SS34 reverse leakage into VBUS')
    for label, extra in (('today: %s+%s only' % (h_ref, l_ref), ''),
                         ('planned: + 4.7k VBUS-GND', 'R3 vbus 0 4.7k\n')):
        if pd and 'planned' in label:
            label = 'fitted: + %s %gk VBUS-GND' % (pd_ref, pd / 1e3)
            extra = ''
        elif pd:
            extra = ''
        vals = []
        for ua in (10, 50, 100, 500):
            deck = '''* gate node under SS34 leakage %d uA
I1 0 vbus DC %gu
R1 vbus sns %g
R2 sns 0 %g
%sV5 v5 0 DC 5.0
D1 vbus v5 dclamp
.model dclamp D(IS=1e-14)
.op
.control
op
print v(vbus)
.endc
.end
''' % (ua, ua, h, l, extra + ('R4 vbus 0 %g\n' % pd if pd else ''))
            o = run('vbus_gate_%d%s' % (ua, '_pd' if 'planned' in label or 'fitted' in label else ''), deck)
            m = re.search(r'v\(vbus\)\s*=\s*([-+0-9.eE]+)', o)
            v = min(float(m.group(1)), 5.0) if m else float('nan')
            vals.append('%d uA -> %.2f V (VGS %+.2f V)' % (ua, v, v - 5.0))
        print('  %-28s %s' % (label, '; '.join(vals)))
    # unplug transient: VBUS cap (VBUS decoupling) from 5 V, console keeps +5V at 5.0 V, 50 uA leakage
    cvb = sum(1e-6 if p.value == '1uF' else 1e-7 if p.value == '100nF' else 0
              for p in D.PARTS if p.prefix == 'C' and 'VBUS' in p.pins.values())
    for label, extra in (('today', ''), ('with 4.7k', 'R3 vbus 0 4.7k\n')):
        deck = '''* VBUS decay after unplug
C1 vbus 0 %g IC=5
R1 vbus sns %g
R2 sns 0 %g
%sI1 0 vbus DC 50u
.tran 10u 300m UIC
.control
run
meas tran t_on when v(vbus)=2.5 fall=1
.endc
.end
''' % (cvb, h, l, extra + ('R4 vbus 0 %g\n' % pd if pd else ''))
        o = run('vbus_unplug_' + label.replace(' ', '_').replace('.', ''), deck)
        t = meas(o, 't_on')
        print('  unplug, %s (VBUS %.1f uF, 50 uA leakage): gate below 2.5 V (VGS < -2.5 V, FET on) after %s'
              % (label, cvb * 1e6, ('%.1f ms' % (t * 1e3)) if t else 'never (stays above 2.5 V)'))

    # ---- 3. /IRQ ------------------------------------------------------------------------------
    K = 0.5 / (10 - 2.5) ** 2
    print('\n== 3. /IRQ: GPIO28 3.3 V on the 2N7002 gate, console R32 2.2k to +5V')
    for vto in (1.6, 2.5):
        deck = '''* 2N7002 /IRQ
Vg g 0 DC 3.3
V5 v5 0 DC 5.0
Rc v5 d 2.2k
M1 d g 0 0 n7002 W=1 L=1
.model n7002 NMOS(LEVEL=1 VTO=%g KP=%g)
.op
.control
op
print v(d)
.endc
.end
''' % (vto, 2 * K)
        o = run('irq_%g' % vto, deck)
        vd = re.search(r'v\(d\)\s*=\s*([-+0-9.eE]+)', o)
        vd = float(vd.group(1)) if vd else float('nan')
        print('  VTO %.1f V: /IRQ %.2f V %s' % (vto, vd, '(asserted, < 0.8 V)' if vd < 0.8 else 'NOT ASSERTED'))

    # ---- 4. cart audio vs a POKEY cart into the console's EXT AUDIO input ---------------------------
    r_lp = res('AUD_PWM', 'AUD_LP')[1]
    r_lvl = res('AUD_LP', 'AUD_LVL')[1]
    print('\n== 4. cart audio into C10 0.1 uF + R5 6.8k -> virtual ground (current into the console\'s audio sum)')
    decks = {'ours': '''* FujiNet audio
V1 pwm 0 DC 0 AC 3.3
R1 pwm lp %g
C1 lp 0 10n
R2 lp lvl %g
C2 lvl ea 1u
C10 ea x 0.1u
R5 x sum 6.8k
Vsum sum 0 DC 0
.control
ac dec 20 20 20k
meas ac i100 find i(vsum) at=100
meas ac i1k find i(vsum) at=1k
meas ac i5k find i(vsum) at=5k
meas ac i10k find i(vsum) at=10k
.endc
.end
''' % (r_lp, r_lvl),
             'pokey': '''* POKEY cart: AUD swing 3.3 Vpp behind a 1k pull-up, 12k series
V1 aud 0 DC 0 AC 3.3
R0 aud au 1k
R2 au ea 12k
C10 ea x 0.1u
R5 x sum 6.8k
Vsum sum 0 DC 0
.control
ac dec 20 20 20k
meas ac i100 find i(vsum) at=100
meas ac i1k find i(vsum) at=1k
meas ac i5k find i(vsum) at=5k
meas ac i10k find i(vsum) at=10k
.endc
.end
'''}
    res_ = {}
    for name, deck in decks.items():
        o = run('audio_' + name, deck)
        res_[name] = [abs(meas(o, k) or 0) for k in ('i100', 'i1k', 'i5k', 'i10k')]
    for name in ('ours', 'pokey'):
        print('  %-6s current p-p at 100 Hz / 1 kHz / 5 kHz / 10 kHz: %s uA' %
              (name, ' / '.join('%.0f' % (v * 1e6) for v in res_[name])))
    import math
    print('  ours vs POKEY: %s dB' % ' / '.join('%+.1f' % (20 * math.log10(a / b)) for a, b in zip(res_['ours'], res_['pokey'])))

    # ---- 5. /HALT rise at the console --------------------------------------------------------------
    # MARIA's HALT is an NMOS output rated 30 ns rise into 25 pF (its 100 uA Ioh is the DC figure at
    # 2.4 V): modelled as the pull-up that meets that rating, 30 ns / (2.2 x 25 pF) ~ 550 ohm
    rh = res('HALT_N', 'HALT_RP')
    print('\n== 5. /HALT 10-90 %% rise at J1-2: MARIA pull-up ~550 ohm (30 ns into 25 pF), console side ~15 pF,'
          ' the cart ~1 pF stub then %s %gk + ~17 pF, or ~18 pF straight on the line' % (rh[0], rh[1] / 1e3))
    for label, cart in (('with %s %gk' % (rh[0], rh[1] / 1e3), 'Cs j 0 1p\nRh j r %g\nCr r 0 17p\n' % rh[1]),
                        ('straight on the line', 'Cs j 0 18p\n'), ('the 25 pF rating', 'Cs j 0 10p\n')):
        deck = """* halt rise
V5 v5 0 PULSE(0 5 10n 1n 1n 1u 2u)
Rm v5 j 550
Cc j 0 15p
%s.tran 0.2n 400n
.control
run
meas tran t10 when v(j)=0.5 rise=1
meas tran t90 when v(j)=4.5 rise=1
.endc
.end
""" % cart
        o = run('halt_' + label.split()[0], deck)
        t10, t90 = meas(o, 't10'), meas(o, 't90')
        print('  %-22s rise %s' % (label, ('%.1f ns' % ((t90 - t10) * 1e9)) if t10 and t90 else 'n/a'))

if __name__ == '__main__':
    main()
