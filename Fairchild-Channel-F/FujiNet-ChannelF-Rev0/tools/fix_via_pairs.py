#!/usr/bin/env python3
"""Collapse router via pairs: two unlocked vias of one net, closer than the hole-to-hole rule, joined
by a short jog on one copper layer (F.Cu -> via -> B.Cu jog -> via -> F.Cu, as Freerouting / the
finisher sometimes leave), become one straight track on the other layer: both vias and the jog go.
Each change is kept only if KiCad's DRC (zones refilled) comes out no worse -- no new violation, no
new unconnected item -- else it is reverted.  V9 left one such VBUS pair under the USB-C.

Usage: python3 tools/fix_via_pairs.py [board]
"""
import json, math, os, subprocess, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tmpdir import tmp
from sexpr import parse, dump, find, Q
import gen_pcb as G

PCB = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else G.PCB


def drc():
    fn = tmp('vp.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--refill-zones', '--severity-all', '--format', 'json', '-o', fn, PCB],
                   capture_output=True)
    d = json.load(open(fn))
    return d.get('violations', []), d.get('unconnected_items', [])


def xy(e, k='at'):
    a = find(e, k)
    return round(float(a[1]), 4), round(float(a[2]), 4)


def attempt(net, X, Y):
    """Drop via X and the unlocked one-layer segments that run from X toward Y's side (X's stub on
    that layer), and join X's other-layer track straight to Y on that other layer.  Returns the new
    board text, or None when X has no such stub."""
    b = parse(open(PCB).read())
    vx = [e for e in b if isinstance(e, list) and e and e[0] == 'via' and xy(e) == X and str(find(e, 'net')[1]) == net]
    if len(vx) != 1 or find(vx[0], 'locked'):
        return None
    segs = [e for e in b if isinstance(e, list) and e and e[0] == 'segment' and str(find(e, 'net')[1]) == net
            and X in (xy(e, 'start'), xy(e, 'end'))]
    for L in ('B.Cu', 'F.Cu'):
        stub = [s for s in segs if str(find(s, 'layer')[1]) == L]
        rest = [s for s in segs if str(find(s, 'layer')[1]) != L]
        # X's side on layer L must be a single unlocked segment, ending within 1 mm of Y (the jog)
        if len(stub) != 1 or find(stub[0], 'locked') or not rest:
            continue
        far = xy(stub[0], 'end') if xy(stub[0], 'start') == X else xy(stub[0], 'start')
        if math.dist(far, Y) > 1.0:
            continue
        other = str(find(rest[0], 'layer')[1])
        w = max(float(find(s, 'width')[1]) for s in rest)
        drop = {id(vx[0]), id(stub[0])}
        b2 = [e for e in b if id(e) not in drop]
        k = max(i for i, e in enumerate(b2) if isinstance(e, list) and e and e[0] in ('segment', 'via'))
        b2.insert(k + 1, ['segment', ['start', *X], ['end', *Y], ['width', w], ['layer', Q(other)], ['net', Q(net)],
                          ['uuid', Q(str(uuid.uuid4()))]])
        return dump(b2) + '\n', other
    return None


def main():
    viol, unc = drc()
    pairs = [v for v in viol if v['type'] == 'hole_to_hole' and all(i['description'].startswith('Via') for i in v['items'])]
    fixed = 0
    for v in pairs:
        A = (round(v['items'][0]['pos']['x'], 4), round(v['items'][0]['pos']['y'], 4))
        B = (round(v['items'][1]['pos']['x'], 4), round(v['items'][1]['pos']['y'], 4))
        net = v['items'][0]['description'].split('[')[1].split(']')[0]
        old = open(PCB).read()
        done = False
        for X, Y in ((B, A), (A, B)):
            r = attempt(net, X, Y)
            if not r:
                continue
            open(PCB, 'w').write(r[0])
            v2, u2 = drc()
            err = lambda vs: len([x for x in vs if x['severity'] == 'error'])
            if err(v2) <= err(viol) and len(u2) <= len(unc) and len(v2) < len(viol):
                viol, unc = v2, u2
                fixed += 1
                done = True
                print('fix_via_pairs: %s: via at %s dropped, its track joined to %s on %s' % (net, X, Y, r[1]))
                break
            open(PCB, 'w').write(old)
        if not done:
            print('fix_via_pairs: %s pair at %s / %s left as it is (no change made DRC better)' % (net, A, B))
    print('fix_via_pairs: %d of %d hole-to-hole via pair(s) collapsed' % (fixed, len(pairs)))


if __name__ == '__main__':
    main()
