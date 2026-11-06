#!/usr/bin/env python3
"""The board's netlist, as Yannick's copper connects it: the source the schematic is drawn from.

  python3 tools/board_netlist.py           write tools/board_netlist.json from the converted board
                                           (run right after tools/convert.py, before sync_board.py
                                           renames the nets)
  python3 tools/board_netlist.py --check   check tools/design.py against tools/board_netlist.json:
                                           every design net is exactly one board net (the same
                                           (ref, pad) set), every pad the board leaves unconnected
                                           is NC in design.py, every part has the board's value
                                           and footprint

board_netlist.json: {ref: {"value", "footprint", "pads": {pad: net or null}}}, EasyEDA's net names.
Pads that share a number (the S3's nine pads 41, the microSD's shell 10) must share a net; the
unnumbered mechanical pads (NPTH pegs) are left out.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'board_netlist.json')


def dump():
    import pcbnew
    b = pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(os.path.join(PRJ, 'Inty-FujiCard.kicad_pcb'), None)
    out = {}
    for f in b.GetFootprints():
        pads = {}
        for p in f.Pads():
            num = p.GetNumber()
            if not num:
                continue
            net = p.GetNetname() or None
            if num in pads and pads[num] != net:
                raise SystemExit('%s pad %s: two nets %s / %s' % (f.GetReference(), num, pads[num], net))
            pads[num] = net
        out[f.GetReference()] = dict(value=f.GetValue(), footprint=f.GetFPID().GetUniStringLibItemName(),
                                     pads=dict(sorted(pads.items(), key=lambda kv: (len(kv[0]), kv[0]))))
    json.dump(dict(sorted(out.items())), open(OUT, 'w'), indent=1, ensure_ascii=False)
    open(OUT, 'a').write('\n')
    nets = {n for v in out.values() for n in v['pads'].values() if n}
    print('board_netlist.json: %d footprints, %d nets' % (len(out), len(nets)))


def check():
    sys.path.insert(0, HERE)
    import design as D
    bn = json.load(open(OUT))
    bad = []
    board = {}
    for ref, v in bn.items():
        for pad, net in v['pads'].items():
            if net:
                board.setdefault(net, set()).add((ref, pad))
    by_set = {frozenset(v): k for k, v in board.items()}
    design = {n: set(v) for n, v in D.nets().items()}
    for n, v in design.items():
        if frozenset(v) not in by_set:
            bad.append('design net %s %s is no board net' % (n, sorted(v)[:6]))
        elif D.NET_ALIAS.get(by_set[frozenset(v)], by_set[frozenset(v)]) != n:
            bad.append('design net %s is Yannick\'s %s (keep his name, or alias an automatic one)'
                       % (n, by_set[frozenset(v)]))
    if len(design) != len(board):
        bad.append('%d design nets, %d board nets' % (len(design), len(board)))
    refs = {p.ref for p in D.PARTS}
    if refs != set(bn):
        bad.append('parts: design only %s, board only %s' % (sorted(refs - set(bn)), sorted(set(bn) - refs)))
    for p in D.PARTS:
        if p.ref not in bn:
            continue
        b = bn[p.ref]
        if set(p.pins) != set(b['pads']):
            bad.append('%s: pads %s / board %s' % (p.ref, sorted(set(p.pins) ^ set(b['pads']))[:6], ''))
        for pad, net in b['pads'].items():
            if net is None and p.pins.get(pad) is not None:
                bad.append('%s pad %s: unconnected on the board, %s in design.py' % (p.ref, pad, p.pins[pad]))
        if p.footprint.split(':')[1] != b['footprint']:
            bad.append('%s: footprint %s, board %s' % (p.ref, p.footprint, b['footprint']))
    if bad:
        raise SystemExit('design.py vs the board:\n  ' + '\n  '.join(bad[:40]))
    print('design.py = the board: %d nets, %d parts, every unconnected pad NC' % (len(design), len(refs)))


if __name__ == '__main__':
    try:
        check() if '--check' in sys.argv else dump()
    except SystemExit as e:
        print(e, flush=True)
        os._exit(1 if e.code else 0)
    sys.stdout.flush()
    os._exit(0)
