#!/usr/bin/env python3
"""Gate: KiCad's DRC with schematic parity on the saved board, never refilling a zone.

kicad-cli pcb drc --schematic-parity (no --refill-zones), all severities, against the board's own
rules (Inty-FujiCard.kicad_pro constraints, Inty-FujiCard.kicad_dru).  Passes when there are no
errors, no unconnected items, no parity issues, the board file is byte for byte the same after the
run, and every warning is one of WAIVED, the warnings Yannick Erb's footprints and silkscreen carry
as he drew them (README "Design rules" says why each is accepted), in no larger number.

Usage: python3 tools/audit/check_drc.py      exit 1 on any failure
"""
import collections, hashlib, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
PCB = os.path.join(PRJ, 'Inty-FujiCard.kicad_pcb')
WAIVED = {   # warning type -> (at most, why)
    'lib_footprint_mismatch': (47, 'EasyEDA placed each instance of a footprint with its own 0.1-0.2 um rounding and '
                                   'fab-text angle; the library holds the first instance (tools/convert.py checks 1 um)'),
    'silk_overlap': (39, 'his polarity bars and pin-1 dots drawn over the parts\' own outlines'),
    'silk_edge_clearance': (10, 'the USB-C, the S3 module and the microSD outlines at the board edge (the S3 overhangs it)'),
    'silk_over_copper': (4, 'the USB-C outline over its own through-hole shell legs'),
    'track_dangling': (1, 'a zero-length 0.508 mm 3V3 track on B.Cu: a copper dot in his gerbers, kept'),
}


def main():
    before = hashlib.sha256(open(PCB, 'rb').read()).hexdigest()
    fd, out = tempfile.mkstemp(prefix='inty-drc-', suffix='.json')
    os.close(fd)
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--schematic-parity', '--format', 'json', '--severity-all',
                    '--units', 'mm', '-o', out, PCB], capture_output=True)
    d = json.load(open(out))
    os.remove(out)
    fails = []
    errs = [v for v in d['violations'] if v['severity'] == 'error']
    if errs:
        fails.append('%d errors: %s' % (len(errs), sorted({v['type'] for v in errs})))
    if d['unconnected_items']:
        fails.append('%d unconnected items' % len(d['unconnected_items']))
    if d.get('schematic_parity'):
        fails.append('%d schematic parity issues: %s' % (len(d['schematic_parity']),
                                                        sorted({v['type'] for v in d['schematic_parity']})))
    warn = collections.Counter(v['type'] for v in d['violations'] if v['severity'] == 'warning')
    for t, n in sorted(warn.items()):
        if t not in WAIVED or n > WAIVED[t][0]:
            fails.append('%d %s warnings (%s)' % (n, t, 'not waived' if t not in WAIVED else 'waived: %d' % WAIVED[t][0]))
    if hashlib.sha256(open(PCB, 'rb').read()).hexdigest() != before:
        fails.append('the DRC run changed the board file')
    for f in fails:
        print('FAIL  ' + f)
    print('%s  DRC + schematic parity: %d errors, %d unconnected, %d parity issues; warnings %s'
          % ('ok   ' if not fails else 'FAIL ', len(errs), len(d['unconnected_items']), len(d.get('schematic_parity', [])),
             ', '.join('%s %d' % kv for kv in sorted(warn.items())) or 'none'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
