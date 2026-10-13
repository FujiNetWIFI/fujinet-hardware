#!/usr/bin/env python3
"""Write .kicad-happy.json (kicad-happy project config) with its component suppressions resolved
from tools/design.py keys, so a reference renumbering (refs.lock: geographic references) can never
point a suppression at the wrong part.  Net patterns are fnmatch globs written to match both bare
names (VBUS_SNS) and the hierarchy-prefixed names (/usb/VBUS_SNS, /cart-bus/A0).

kicad-happy 2.2.1 applies suppressions in the EMC and thermal analyzers only: the schematic and
PCB analyzers report suppressed rules anyway.  Every finding, suppressed or not, is triaged in
docs/design-review-rev0.md (Parts 1 and 2).

Usage: python3 tools/audit/make_happy_config.py
"""
import json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D

K = lambda *keys: [D.KEY[k] for k in keys]
G = lambda *ns: [p for n in ns for p in (n, '*/' + n)]
import placement as PL
HOLES = ['H%d' % (i + 1) for i in range(len(PL.HOLES))]

cfg = {
    'version': 1,
    'project': {'name': 'FujiNet-5200 Rev0', 'revision': '0', 'company': 'FujiNet', 'market': 'us',
                'emc_standard': 'fcc-class-b', 'pdn_transient_current_a': 0.6},
    'preferred_suppliers': ['lcsc'],
    'bom': {'field_priority': ['MPN', 'LCSC'], 'group_by': 'value+footprint'},
    'design_intent': {'product_class': 'prototype', 'target_market': 'hobby', 'ipc_class': 2,
                      'preferred_passive_size': '0603', 'operating_temp_range': [0, 70]},
    'analysis': {
        'output_dir': 'analysis', 'retention': 5, 'auto_diff': True, 'track_in_git': False,
        'power_rails': {
            'ignore': G('PWR_OK', 'PWR_OK_N', 'SERVE', 'SERVE_N', 'EN_ANY_N', 'VBUS_SNS', 'VSENSE', 'VSENSE_ADC',
                        'CONS_OFF', 'ILK_G'),
            'voltage_overrides': {'+3V3_RP': 3.3, '+3V3': 3.3, '+5V': 5.0, 'CONS_5V': 5.0, 'VBUS': 5.0,
                                  'PRE5V': 5.0, 'PRE_VIN': 13.0, 'UNREG': 13.0, 'UNREG_J': 13.0, 'UNREG_F': 13.0,
                                  'DVDD': 1.1, 'VREG_AVDD': 3.3}}},
    'suppressions': [
        {'rule_id': 'VM-001',
         'nets': G('A[0-9]', 'A1[0-3]', 'EN40_N', 'EN80_N', 'PWR_OK', 'PHI2_RP'),
         'reason': "Console 5 V outputs (and the 74HCT14's PWR_OK, the 74LVC1G17's PHI2_RP, both at 5 V) into "
                   "RP2354B GPIO0-25, all 'Digital IO (FT)': VPIN_FT 5.5 V while IOVDD = 3.3 V (RP2350 datasheet "
                   "p.1340); IOVDD is the AP2112K LDO off +5V. Deliberate, no level shifter."},
        {'rule_id': 'VM-001',
         'nets': G('RP_D[0-7]', 'BUF_EN', 'ILK'),
         'reason': 'RP2354B 3.3 V outputs into 74HCT inputs (the 541 A inputs, the 08: VIH 2.0 V) and the DNP '
                   "2N7002's gate; RP VOH >= 2.62 V at rated load, ~3.3 V into these CMOS loads. GPIO40-47 (not FT) "
                   'never see 5 V (tools/check_nets.py asserts it).'},
        {'rule_id': 'RS-001', 'nets': G('PWR_OK', 'PWR_OK_N', 'SERVE', 'SERVE_N', 'EN_ANY_N', 'VBUS_SNS', 'CONS_OFF'),
         'reason': 'Logic outputs of the 74HCT08 / 74HCT14, the CP2102N VBUS sense node and the P-FET gate OR, not rails.'},
        {'rule_id': 'PU-001', 'components': K('U_UART'),
         'reason': 'CP2102N CHREN/CHR0/CHR1 are charger-detect outputs, left open as in the ESP32-S3-DevKitC-1.'},
        {'rule_id': 'CG-AUD', 'components': K('J_EDGE'),
         'reason': "Console-defined 36-pin 5200 slot: GND on 12, 13, 23 and 25 by Atari's pinout (CX5200 FSM)."},
        {'rule_id': 'EP-AUD', 'components': K('J_EDGE', 'J_DBG', 'J_SD'),
         'reason': 'J_EDGE is the console bus (no 5200 cart carries ESD parts; RP2350 FT pads have enhanced ESD '
                   'protection); J_DBG is the DNP bring-up UART header; the microSD sits inside the shell.'},
        {'rule_id': 'DC-002', 'components': K('U_AUTOPROG'),
         'reason': 'UMH3N is a dual pre-biased transistor (auto-program); it has no supply pin to decouple.'},
        {'rule_id': 'VD-004', 'components': K('R_VBSL', 'R_VBPD', 'R_PREPD', 'R_OFFPD'),
         'reason': "0603 is the board's passive size; these are not power-sized."},
        {'rule_id': 'KO-001', 'components': K('J_EDGE') + HOLES,
         'reason': 'Deliberate rule areas: the tab keep-outs forbid tracks, vias and pour but allow pads (the gold '
                   'fingers belong there); the screw keep-outs keep copper off the holes inside them.'},
        {'rule_id': 'PM-002', 'components': K('J_EDGE', 'J_SD', 'J_USB', 'U_S3'),
         'reason': 'At the edge by design: the cart fingers, the microSD and USB-C mouths on the top edge, the '
                   'ESP32-S3 antenna flush with the top edge over its keep-out.'},
        {'rule_id': 'TS-003', 'components': K('U_LDO'),
         'reason': "Heuristic: it books the whole board's dissipation on the AP2112K. The LDO carries only the RP2354B "
                   '(30-60 mA from 5 V: 51-102 mW, tools/audit/margins.py), about +25 C in SOT-23-5; the RP core '
                   'regulator is a switcher, so the LDO never carries the core current.'},
        {'rule_id': 'TP-001', 'components': K('U_LDO'),
         'reason': 'Follows from TS-003 (the same heuristic Tj): the LDO runs about 50 C at 25 C ambient.'},
        {'rule_id': 'CC-002',
         'reason': "Signal nets necked down to 0.15 mm only for their last link at the RP2354B's 0.4 mm-pitch pins "
                   '(finish_route --neck); logic currents of a few mA.'},
    ],
}
hdr = ('// kicad-happy project config for FujiNet-5200 Rev0 (JSONC) -- GENERATED by tools/audit/make_happy_config.py\n'
       '// from tools/design.py keys; do not edit.  kicad-happy 2.2.1 applies suppressions in the EMC and thermal\n'
       '// analyzers only.  Triage of every finding: docs/design-review-rev0.md, Parts 1 and 2.\n')
open(os.path.join(PRJ, '.kicad-happy.json'), 'w').write(hdr + json.dumps(cfg, indent=2) + '\n')
print('.kicad-happy.json: %d suppressions' % len(cfg['suppressions']))
