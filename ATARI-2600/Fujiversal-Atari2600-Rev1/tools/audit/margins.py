#!/usr/bin/env python3
"""Numbers behind the Rev1 deep review (docs/design-review-rev1.md): divider
levels, the P-FET gate under Schottky leakage, LED current, crystal load,
the RP LDO's dissipation and the bus timing budget.  Values come from
tools/design.py; limits are the datasheet figures quoted in the review.

Usage: python3 tools/audit/margins.py
"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import design as D

K = D.KEY


def ohms(ref):
    v = D.BY_REF[K[ref]].value
    m = re.match(r'([\d.]+)([kMR]?)', v)
    return float(m.group(1)) * {'k': 1e3, 'M': 1e6, 'R': 1.0, '': 1.0}[m.group(2)]


def main():
    # console 5 V sense on GPIO27 (ADC pin: VPIN max IOVDD + 0.5 V; digital VIH 2.0 V at IOVDD 3.3 V)
    hi, lo = ohms('R_VSH'), ohms('R_VSL')
    k = lo / (hi + lo)
    print('VSENSE ratio %.3f: %.2f V at 4.50 V, %.2f V at 5.00 V, %.2f V at 5.25 V, %.2f V at 5.50 V'
          % (k, 4.5 * k, 5.0 * k, 5.25 * k, 5.5 * k))
    print('VSENSE source impedance %.1f k, filter tau %.1f ms' % (hi * lo / (hi + lo) / 1e3, hi * lo / (hi + lo) * 100e-9 * 1e3))
    # CP2102N VBUS sense: VIH = VIO - 0.6 V, abs max VIO + 2.5 V (VIO = 3.3 V)
    h2, l2 = ohms('R_VBH'), ohms('R_VBL')
    print('VBUS_SNS at 5.0 V: %.2f V (VIH 2.70 V, abs max 5.80 V); at 4.40 V: %.2f V' % (5 * l2 / (h2 + l2), 4.4 * l2 / (h2 + l2)))
    # P-FET gate = VBUS net with no USB: pulled down by R_VBPD || (R_VBH + R_VBL), lifted by the SS34's
    # reverse leakage from +5V.  AO3401A VGS(th) -0.5..-1.3 V; source at ~5 V
    pd = 1 / (1 / ohms('R_VBPD') + 1 / (h2 + l2))
    for ua in (10, 50, 200, 500):
        vg = ua * 1e-6 * pd
        print('SS34 leakage %3d uA -> gate %.2f V, VGS %.2f V (%s)' % (ua, vg, vg - 5.0,
              'fully on' if vg - 5.0 < -2.5 else 'partly on' if vg - 5.0 < -1.3 else 'may be off'))
    without = h2 + l2
    print('  (without the 10k: 50 uA -> %.2f V, VGS %.2f V)' % (50e-6 * without, 50e-6 * without - 5))
    # RP activity LED, KT-0603R VF ~1.8-2.0 V at low current, from a 3.3 V pin
    r = ohms('R_LED')
    print('RP LED: (3.3 - 1.9 V) / %d R = %.1f mA' % (r, (3.3 - 1.9) / r * 1e3))
    # crystal: ABM8-272-T3 CL 10 pF; 15 pF loads in series + ~3 pF stray
    print('crystal load: 15*15/30 + 3 = %.1f pF (CL 10 pF)' % (15 * 15 / 30 + 3))
    # RP LDO dissipation: RP2350 core at 150-250 MHz + IO ~ 30-60 mA (estimate)
    for ma in (30, 60):
        print('AP2112K at %d mA from 5.0 V: %.0f mW; from 4.3 V: %.0f mW' % (ma, (5.0 - 3.3) * ma, (4.3 - 3.3) * ma))
    # 2600 bus: 6507 at 1.193182 MHz, phi2 high half; firmware budget ~500 ns address -> data
    t = 1e9 / 1.193182e6
    print('6507 cycle %.0f ns; at 150 MHz one RP cycle is %.2f ns -> %d cycles in a 500 ns budget' % (t, 1e3 / 150, 500 / (1e3 / 150)))
    # RP2350 supply current: datasheet Table 1693 (hello_usb 52.7 mW total at 3.3 V); allow 40 mA flat out
    for ma in (16, 40):
        print('RP rail %d mA: AP2112K %.0f mW -> Tj %.0f C at 25 C ambient (SOT-23-5, 250 C/W)'
              % (ma, (5.0 - 3.3) * ma, 25 + (5.0 - 3.3) * ma / 1e3 * 250))
    # USB pair lengths on the routed board (kicad-happy pcb.json, current run)
    import json
    prj = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        run = json.load(open(os.path.join(prj, 'analysis', 'manifest.json')))['current']
        pcb = json.load(open(os.path.join(prj, 'analysis', run, 'pcb.json')))
    except (OSError, KeyError):
        return
    L = {n['net']: n['total_length_mm'] for n in pcb['net_lengths']}
    for a, b in (('USB_DP', 'USB_DM'), ('UBRG_DP', 'UBRG_DM'), ('RP_USB_DP', 'RP_USB_DM')):
        if a in L and b in L:
            d = abs(L[a] - L[b])
            print('%s/%s %.1f / %.1f mm: skew %.1f mm = %.0f ps (FR-4 ~6.7 ps/mm); FS USB edges 4-20 ns'
                  % (a, b, L[a], L[b], d, d * 6.7))


if __name__ == '__main__':
    main()
