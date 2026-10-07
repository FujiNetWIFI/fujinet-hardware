#!/usr/bin/env python3
"""ngspice checks the kicad-happy subcircuit simulator does not set up for this
board (it drives every divider from a 3.3 V test source):

1. PWR_OK sense: CONS_5V swept 0-5.5 V into the 22k/100k divider with the
   SN74HCT14 input (+-1 uA leakage, 10 pF); the console voltages at which VSENSE
   crosses the HCT14's VT+ / VT- limits.
2. P-FET gate (the VBUS net, no USB): the SS34's reverse leakage (sourced from
   +5V, so the node cannot rise above it) into the pull-down, today (22k+47k) and with the planned 4.7k; plus the gate's decay
   after USB is unplugged with the console running (time until VGS < -2.5 V).
3. /WAIT hold before the firmware runs: 2N7002 (level-1 model, VTO 1.6 typ /
   2.5 V max, K from ID(on) 500 mA at VGS 10 V) with its gate pull-up against
   the RP2350 reset pull-down (36k / 113k), drain to a console /WAIT pull-up.

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

    # ---- 3. /WAIT gate -----------------------------------------------------------------------
    pu_ref, pu = None, None
    for p in D.PARTS:
        if p.prefix == 'R' and 'WAIT_GATE' in p.pins.values():
            pu_ref = p.ref
            m = re.match(r'([\d.]+)([kMR]?)', p.value)
            pu = float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]
    K = 0.5 / (10 - 2.5) ** 2                      # A/V^2, worst device (VTO 2.5 V, ID(on) 500 mA at 10 V)
    print('\n== 3. /WAIT held before the firmware runs: %s pull-up to +3V3_RP vs RP2350 RPD (reset default), 2N7002 K = %.1f mA/V^2'
          % (pu_ref, K * 1e3))
    for rpu in sorted({pu, 4.7e3}, reverse=True):
        for vto in (1.6, 2.5):
            for rpd in (36e3, 113e3):
                for rcons in (10e3, 4.7e3):
                    deck = '''* 2N7002 /WAIT pull-down at power-on
Vrp rp 0 DC 3.3
Rpu rp g %g
Rpd g 0 %g
V5 v5 0 DC 5.0
Rc v5 d %g
M1 d g 0 0 n7002 W=1 L=1
.model n7002 NMOS(LEVEL=1 VTO=%g KP=%g)
.op
.control
op
print v(d) v(g)
.endc
.end
''' % (rpu, rpd, rcons, vto, 2 * K)
                    o = run('wait_%g_%g_%g_%g' % (rpu, vto, rpd, rcons), deck)
                    vd = re.search(r'v\(d\)\s*=\s*([-+0-9.eE]+)', o)
                    vg = re.search(r'v\(g\)\s*=\s*([-+0-9.eE]+)', o)
                    vd = float(vd.group(1)) if vd else float('nan')
                    print('  pull-up %4.1fk VTO %.1f RPD %3.0fk console %4.1fk: gate %.2f V, /WAIT %.2f V %s'
                          % (rpu / 1e3, vto, rpd / 1e3, rcons / 1e3, float(vg.group(1)) if vg else float('nan'), vd,
                             'held (< 0.8 V)' if vd < 0.8 else 'NOT held'))


if __name__ == '__main__':
    main()
