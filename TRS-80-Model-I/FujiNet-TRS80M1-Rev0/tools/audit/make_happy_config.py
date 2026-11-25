#!/usr/bin/env python3
"""Write .kicad-happy.json (kicad-happy project config) with its component suppressions resolved
from tools/design.py keys, so a reference renumbering can never point a suppression at the wrong
part.  Net patterns are fnmatch globs written to match both bare names (VSENSE) and the
hierarchy-prefixed names (/m1-bus/DRIVE).

kicad-happy 2.2.1 applies suppressions in the EMC and thermal analyzers only: the schematic and
PCB analyzers report suppressed rules anyway.  Every finding, suppressed or not, is triaged in
docs/design-review-rev0.md.

Usage: python3 tools/audit/make_happy_config.py
"""
import json, os, sys
PRJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D
import placement as PL

K = lambda *keys: [D.KEY[k] for k in keys]
G = lambda *ns: [p for n in ns for p in (n, '*/' + n)]
HOLES = ['H%d' % (i + 1) for i in range(len(PL.HOLES))]

cfg = {
    'version': 1,
    'project': {'name': 'FujiNet-TRS80M1 Rev0', 'revision': '0', 'company': 'FujiNet', 'market': 'us',
                'emc_standard': 'fcc-class-b', 'pdn_transient_current_a': 0.2},
    'preferred_suppliers': ['lcsc'],
    'bom': {'field_priority': ['MPN', 'LCSC'], 'group_by': 'value+footprint'},
    'design_intent': {'product_class': 'prototype', 'target_market': 'hobby', 'ipc_class': 2,
                      'preferred_passive_size': '0603', 'operating_temp_range': [0, 70]},
    'analysis': {
        'output_dir': 'analysis', 'retention': 5, 'auto_diff': True, 'track_in_git': False,
        'power_rails': {
            # divider / filter nodes that only look like rails by name
            'ignore': G('VREG_AVDD', 'VBUS_SNS', 'BUCK_FB'),
            'voltage_overrides': {'+3V3': 3.3, '+3V3_RP': 3.3, '+5V': 5.0, 'VBUS': 5.0, 'DVDD': 1.1}}},
    'suppressions': [
        {'rule_id': 'LB-001',
         'reason': "Hierarchical label + sheet pin of the same net on two sheets (the root block diagram's wiring); "
                   'KiCad joins them by design.'},
        {'rule_id': 'CG-AUD', 'components': K('J_M1'),
         'reason': "The TRS-80 Model I's expansion edge, as Tandy defined it (Tech Ref 26-2103 p.91): three grounds "
                   '(8, 29, 37; header 7, 30, 38 through the ribbon) among 40 pins; pin 39 is +5V on keyboard boards A-E and GND on G, so it is left open. '
                   'The card buffers every line at the header (tools/audit/spice/ribbon.py).'},
        {'rule_id': 'EP-AUD', 'components': K('J_M1'),
         'reason': "J_M1 is the Model I's own bus on a short ribbon, not a user-facing port: every line meets a 74LVC "
                   'buffer (2 kV HBM, Ioff, 5 V-tolerant) at the header, D0-D7 through 75R as well; the Model I '
                   'carries no ESD parts on its edge either.'},
        {'rule_id': 'EP-AUD', 'components': K('J_USB'),
         'reason': 'USB-C: the USBLC6-2SC6 clamps D+, D- and VBUS; CC1 / CC2 carry only the 5.1k Rd.'},
        {'rule_id': 'DC-002', 'components': K('U_AUTOPROG'),
         'reason': 'UMH3N is a dual pre-biased transistor (auto-program); it has no supply pin to decouple.'},
        {'rule_id': 'PU-001', 'components': K('U_UART'),
         'reason': "CP2102N CHREN / CHR0 / CHR1 are the battery-charger detection outputs; unused here (no battery), "
                   "left open as on FujiNet-ChannelF Rev0."},
        {'rule_id': 'KO-001', 'components': K('U_S3') + HOLES + ['FID1', 'FID2', 'FID3'],
         'reason': "Deliberate rule areas: the ESP32-S3's antenna keep-out is the module footprint's own zone over "
                   'its own antenna; each corner hole and fiducial sits in its own clear circle (the analyzer checks '
                   "the circle's bounding box; KiCad DRC checks the circle and passes)."},
        {'rule_id': 'PM-002', 'components': K('J_M1', 'J_USB', 'J_SD', 'U_S3'),
         'reason': "At the edge by design: the ribbon header's mouth on the west edge, the USB-C mouth on the north "
                   "edge and the microSD card slot on the south edge (the case's openings); the ESP32-S3's antenna "
                   'at the east edge (Espressif: the antenna at the board edge).'},
        {'rule_id': 'CC-002',
         'reason': "0.15 mm only where the pins need it: Raspberry Pi's own regulator-corner copper (DVDD, "
                   "VREG_AVDD, the USB pair into pins 66 / 67, as in their minimal design), the USB-C receptacle's "
                   "A6/B6 and A7/B7 joins between its 0.5 mm-pitch contacts, and finish_route --neck links between "
                   "fine-pitch pins; logic and USB currents of a few mA.  Nothing is below JLCPCB's 0.127 mm "
                   "(tidy_tracks widens Freerouting's necks)."},
        {'rule_id': 'TS-003', 'components': K('U_LDO'),
         'reason': 'The thermal analyzer assumes 168 mA out of the AP2112K.  Its loads are the RP2354B (~60 mA at '
                   '200 MHz, flash in package), the seven bus buffers (~10 mA) and pull-ups: ~70 mA, so (5.25 - 3.3) V '
                   'x 70 mA = 137 mW; at the datasheet\'s SOT25 theta-JA of 184 C/W (AP2112K p3) Tj = 25 + 25 = 50 C, '
                   '75 C at 50 C ambient inside the case.  The S3, microSD and CP2102N run from the TLV62569 buck '
                   '(+3V3), not from it (tools/audit/margins.py).'},
    ],
}
hdr = ('// kicad-happy project config for FujiNet-TRS80M1 Rev0 (JSONC) -- GENERATED by tools/audit/make_happy_config.py\n'
       '// from tools/design.py keys; do not edit.  kicad-happy 2.2.1 applies suppressions in the EMC and thermal\n'
       '// analyzers only.  Triage of every finding: docs/design-review-rev0.md.\n')
open(os.path.join(PRJ, '.kicad-happy.json'), 'w').write(hdr + json.dumps(cfg, indent=2) + '\n')
print('.kicad-happy.json: %d suppressions' % len(cfg['suppressions']))
