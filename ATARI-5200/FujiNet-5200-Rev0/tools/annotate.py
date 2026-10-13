#!/usr/bin/env python3
"""Geographic reference designators: number every part by where it sits on the board, and lock
the result in tools/refs.lock (design.py reads it; the drawing, the layout and every audit address
parts by key, so references are only labels).

Order, per prefix (C, R, U, ...): the board seen from the component side with the fingers down,
read in 8 mm bands from the top edge, left to right within a band (a part's band is that of its
footprint centre).  J1 stays the cartridge edge, whatever its position.

Run it only on a placement that is final: references change footprint paths and the
unconnected-(REF-pad) net names, so a routed board needs tools/sync_refs.py afterwards.

Usage: python3 tools/annotate.py [--check]     (--check: exit 1 if refs.lock is not geographic)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D
import gen_pcb as G

LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'refs.lock')
BAND = 8.0


def geographic():
    G.do_placement(G.place, [])
    by_key = {D.BY_REF[r].key: xy for r, xy in G.PLACE.items()}
    out = {}
    groups = {}
    for p in D.PARTS:
        groups.setdefault(p.prefix, []).append(p)
    for prefix, ps in groups.items():
        def order(p):
            if p.key == 'J_EDGE':
                return (-1, 0)
            x, y, _ = by_key[p.key]
            return (int((y - G.Y0) // BAND), x)
        for i, p in enumerate(sorted(ps, key=order), 1):
            out[p.key] = '%s%d' % (prefix, i)
    return out


def main():
    want = geographic()
    if '--check' in sys.argv:
        have = json.load(open(LOCK)) if os.path.exists(LOCK) else {}
        bad = sorted(k for k in want if have.get(k) != want[k])
        if bad:
            print('refs.lock is not geographic for: %s' % ', '.join('%s %s->%s' % (k, have.get(k), want[k])
                                                                 for k in bad[:20]))
            return 1
        print('refs.lock: %d references, geographic' % len(want))
        return 0
    json.dump(dict(sorted(want.items())), open(LOCK, 'w'), indent=1)
    open(LOCK, 'a').write('\n')
    print('refs.lock: %d references written' % len(want))
    return 0


if __name__ == '__main__':
    sys.exit(main())
