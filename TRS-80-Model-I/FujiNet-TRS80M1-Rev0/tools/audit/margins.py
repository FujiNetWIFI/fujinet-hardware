#!/usr/bin/env python3
"""Electrical margins of FujiNet-TRS80M1 Rev0 against datasheet limits: the Model I's drivers into the
card's buffers, the card's drivers into the Model I, the load the card puts on each line, the overlap
when a card read ends, the read-timing budget (in step with the firmware's test_timing.c), and the
power tree.  Values come from design.py (resistors, parts) and the datasheets below; every line is a
margin (positive = inside the limit).  Exit 1 if any margin is negative.

Datasheets (worst case over 0-70 C unless noted):
  SN74LS367A (TI SDLS063): VOH >= 2.4 V at -2.6 mA (2.7 V at -0.4 mA), VOL <= 0.4 V at 12 mA; IIH 20 uA,
      IIL -0.4 mA; tPLH 16, tPHL 22, tPZH 30, tPZL 40 ns max (the 74LS keyboard-unit drivers: T pp.15-18)
  SN74LS02 / SN74LS32: VOH >= 2.7 V at -0.4 mA (SYSRES* and INTAK*)
  Z80 (Zilog UM0080): VIL <= 0.8 V, VIH >= 2.0 V; INT* and WAIT* pulled up by 4.7k in the keyboard unit
  SN74LVC245A (TI SCAS218): VIH 2.0 V, VIL 0.8 V (2.7-3.6 V); VOH >= 2.4 V at -12 mA (3.0 V); tpd 6.3,
      ten 8.5, tdis 7.5 ns max at 3.3 +- 0.3 V; II +-5 uA; Ioff
  SN74LVC3G17 (TI SCES400): VT+ 1.5-1.87 V, VT- 0.84-1.14 V, hysteresis >= 0.56 V at 3.0 V (2.16-2.74 /
      1.41-1.79 at 4.5 V); tpd 5.4 ns max at 3.3 V
  SN74LVC1G11: tpd 4.1 ns max at 3.3 V.  74LVC2G07: VOL <= 0.4 V at 16 mA (3.0 V); Ioff
  TLV62569 (TI SLVSDG1C): VFB 0.588-0.612 V, VIN 2.5-5.5 V, 2 A.  AP2112K-3.3: 600 mA, dropout 250 mV
  ESP32-S3-WROOM-1: 3.0-3.6 V, ~355 mA peak TX (datasheet 5.5)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import design as D   # noqa: E402

rows = []


def m(what, value, limit, unit, higher_is_ok=True, note=''):
    margin = (value - limit) if higher_is_ok else (limit - value)
    rows.append((what, value, limit, margin, unit, note))


def ohms(v):
    v = v.replace('4x', '')
    return float(v.rstrip('kMR')) * {'k': 1e3, 'M': 1e6, 'R': 1}.get(v[-1], 1)


def main():
    R = lambda key: ohms(D.BY_KEY[key].value)
    VCC = (3.0, 3.6)                       # +3V3_RP, the LDO: 3.3 V +- 1.5 % at worst well inside
    # ---- the Model I's drivers into the card's receivers ----
    m('LS367 VOH (light load) - LVC245 VIH, address', 2.7, 2.0, 'V')
    m('LS367 VOL - LVC245 VIL, address', 0.8, 0.4, 'V')
    vt_hi = 1.87 + (2.74 - 1.87) * (VCC[1] - 3.0) / 1.5     # VT+ max at 3.6 V (linear between 3.0 and 4.5)
    vt_lo = 0.84                                            # VT- min at 3.0 V
    m('LS367 VOH - 3G17 VT+ max at 3.6 V (strobes)', 2.7, vt_hi, 'V')
    m('3G17 VT- min - LS367 VOL (strobes)', vt_lo, 0.4, 'V')
    m('LS02 / LS32 VOH - 3G17 VT+ (SYSRES*, INTAK*)', 2.7, vt_hi, 'V')
    m('3G17 hysteresis (ringing it rejects)', 0.56, 0.3, 'V', note='>= 0.3 V asked of a ribbon receiver')
    # ---- the card's load on each line: one LVC input and a 100k pull-up to +3V3_RP ----
    pu = ohms(D.BY_KEY['RN_AH1'].value)
    assert all(D.BY_KEY[k].pins['5'] == D.RP_RAIL for k in ('RN_AH1', 'RN_AH2', 'RN_AL1', 'RN_AL2', 'RN_D1',
                                                            'RN_D2', 'RN_STA', 'RN_STB')), 'the bus pulls are pull-ups'
    i_lo = VCC[1] / pu + 5e-6                  # driven low: the pull-up's current plus the LVC input's II
    i_hi = (3.95 - VCC[0]) / pu + 5e-6         # driven high past the rail (LS VOH ~3.95 V unloaded at 5.25 V)
    m('LS367 IOL 12 mA - card load low (100k pull-up + LVC II), uA', 12000, i_lo * 1e6, 'uA')
    m('LS367 IOH 2.6 mA - card load high, uA', 2600, i_hi * 1e6, 'uA')
    m('LS02 / LS32 IOL 8 mA (SYSRES*, INTAK*) - card load low, uA', 8000, i_lo * 1e6, 'uA')
    # undriven (ribbon unplugged, the Model I off): the pull-up holds every input high, strobes inactive;
    # an unanswered read floats the keyboard unit's LS inputs high anyway, and the pull-up agrees (FFh)
    m('undriven input: +3V3_RP min - II x 100k - LVC VIH', VCC[0] - 5e-6 * pu, 2.0, 'V',
      note='strobes inactive unplugged; unanswered reads stay FFh (the ROM boot test at 37ECh)')
    # the Model I on, the card off: the keyboard unit's highs back-feed the unpowered RP rail through the
    # 30 pull-ups (the LVC inputs themselves are Ioff)
    i_bf = 30 * 3.95 / pu
    m('back-feed into an unpowered +3V3_RP (30 x 3.95 V / 100k) under 10 % of its 70 mA draw, mA', 7.0,
      i_bf * 1e3, 'mA', note='too little to start the RP; gone once USB powers the card')
    # INT* / WAIT*: the Z80's 4.7k pull-ups against the 2G07
    i_od = 5.0 / 4.7e3
    m('2G07 VOL at %.1f mA - Z80 VIL' % (i_od * 1e3), 0.8, 0.4, 'V', higher_is_ok=True)
    # ---- the card driving D0-D7 into the keyboard unit (its LS367 inputs and the internal bus) ----
    rs = ohms(D.BY_KEY['RS_D1'].value)
    m('LVC245 VOH (-12 mA) - 75R drop (2 LS loads) - LS VIH', 2.4 - rs * 0.8e-3, 2.0, 'V')
    m('LS VIL - (LVC245 VOL + 75R drop)', 0.8, 0.55 + rs * 0.8e-3, 'V')
    # ---- the end of a card read: the keyboard unit takes D0-D7 back as the Z80's RD rises ----
    # it re-enables its LS367 data drivers through an LS132 (DBOUT*) -- fastest ~1/3 of their typical delays;
    # the card's RD* at the edge lags the Z80's (LS32 + LS367, up to 44 ns), then the 3G17, the 1G11 and
    # the '245's disable
    kb_on_min = (11 + 19) / 3                                  # LS132 + LS367 tPZx, typical / 3
    card_off_max = 22 + 22 + 1.5 + 5.4 + 4.1 + 7.5             # LS32 + LS367 + cable + 3G17 + 1G11 + tdis
    overlap = max(0.0, card_off_max - kb_on_min)
    i_c = 3.3 / (rs + 15 + 15)                                 # 75R + LVC and LS367 output resistances
    m('LVC245 abs max 50 mA - contention current through %gR (%.0f ns worst overlap)' % (rs, overlap),
      50, i_c * 1e3, 'mA')
    # ---- read timing (firmware pico/trs80m1/firmware/host_test/test_timing.c, the same model) ----
    cpus = [('Z80 1.774 MHz (stock)', 564, 130, 50), ('Z80A 2.66 MHz', 376, 85, 35), ('Z80A 3.55 MHz', 282, 85, 35)]
    lvc_in, gate, lvc245 = 5.4, 4.1, 6.3                       # this board: 3G17, 1G11, '245 tpd (test_timing: 7/5/7)
    rc = 2.2 * rs * 100e-12 * 1e9                              # the series R into ~100 pF of cable + bus, to 90 %
    core = lambda chore: (2 + chore + 35) * 1000 / 200        # SYNC + chore + SERVE cycles at 200 MHz
    for name, t, rd, su in cpus:
        budget = t * 1.5 - rd - su - 22 - 22 - 22
        worst = lvc_in + core(50) + gate + lvc245 + rc + 2 * 1.5
        typ = lvc_in + core(0) + gate + lvc245 + rc + 2 * 1.5
        if name.startswith('Z80 1'):
            m('read budget - card worst, %s' % name, budget, worst, 'ns', note='test_timing: worst case met')
        else:
            m('read budget - card typical, %s' % name, budget, typ, 'ns', note='speed-ups: typical only (README)')
    # ---- pull-ups / pull-downs on the RP pins (RP2350-E9: 8.2 kOhm or stronger) ----
    m('DRIVE pull-down under 8.2 kOhm (E9)', 8.2e3, R('R_DRIVE'), 'Ohm', higher_is_ok=True)
    m('GP28 current holding DRIVE high (mA) under 4 mA', 4.0, 3.3 / R('R_DRIVE') * 1e3, 'mA', higher_is_ok=True)
    # ---- power ----
    r1, r2 = R('R_FBH'), R('R_FBL')
    vout = (0.588 * (1 + r1 / r2), 0.612 * (1 + r1 / r2))
    m('+3V3 (buck) min - ESP32-S3 VDD min 3.0', vout[0], 3.0, 'V')
    m('ESP32-S3 VDD max 3.6 - +3V3 max', 3.6, vout[1], 'V', higher_is_ok=True)
    i_s3 = 0.355 + 0.020 + 0.010 + 0.100                       # S3 TX peak, CP2102N, LEDs on 3V3, microSD write
    i_5v_buck = 3.3 * i_s3 / 0.85 / 4.75
    i_rp = 0.060 + 0.010                                       # RP2354B at 200 MHz + the bus buffers
    i_ws = 0.060
    i_5v = i_5v_buck + i_rp + i_ws
    m('fuse hold 1.1 A - peak draw at 5 V', 1.1, i_5v, 'A')
    m('USB-C default 0.5 A... a 1.5 A charger - peak draw', 1.5, i_5v, 'A', note='a PC USB 2.0 port (0.5 A) may sag in WiFi bursts')
    m('AP2112K 600 mA - RP rail', 0.6, i_rp, 'A')
    m('AP2112K dissipation (5 V in) under 0.25 W', 0.25, (5.25 - 3.3) * i_rp, 'W', higher_is_ok=True)
    m('TLV62569 2 A - S3 rail peak', 2.0, i_s3, 'A')
    w = max(len(r[0]) for r in rows)
    bad = 0
    for what, v, lim, mg, unit, note in rows:
        flag = 'ok ' if mg >= 0 else 'NEG'
        bad += mg < 0
        print('%s %-*s %10.3g %s  (limit %.3g, margin %+.3g)%s' % (flag, w, what, v, unit, lim, mg,
                                                                  '  -- ' + note if note else ''))
    print('%d margins, %d negative' % (len(rows), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
