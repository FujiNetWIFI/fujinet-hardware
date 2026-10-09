#!/usr/bin/env python3
"""Give the routed board the net names the schematic now carries, without touching anything else
in the .kicad_pcb.

KiCad names a net local to one sheet /sheet/NET, a net wired between sheets on the root /NET and
a power net NET.  The 2026-10-09 redraw moved the Astrocade's parts from four sheets (cart,
esp32, usb, power) to five (cart-bus, rp-core, fujinet, usb, power), so /cart/CA0 is now
/cart-bus/CA0, /cart/XIN /rp-core/XIN, /esp32/S3_EN /S3_EN, and so on: the same nets, the same
pads, new names.  This maps every net name on the board to the schematic's by its last path
element (design.py's name), refuses unless the map is one-to-one and covers every net on both
sides, and rewrites the (net "...") tokens -- pads, tracks, vias, zones.  The board with every
name cut to its last element is then byte for byte what it was.  Afterwards: sync_pcb_sheets.py
(the footprints' sheet links), gen_pcb.configure_project() (net classes and the .kicad_dru name the
nets too) and kicad-cli pcb drc --schematic-parity.  A no-connect pin's net is matched by its part
and pad: KiCad writes the symbol unit into its name (unconnected-(U1A-GPIO23-Pad35)).

Usage: python3 tools/sync_pcb_nets.py [--check]    (--check: report, write nothing)
"""
import os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, find, findall
import design as D
from tmpdir import tmp

PRJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(PRJ, D.PROJECT + '.kicad_pcb')
NET_TOKEN = re.compile(r'\(net "((?:[^"\\]|\\.)*)"\)')


def canon(n):
    """design.py's name for a KiCad net; an unconnected pin's net by its part and pad, since KiCad
    writes the unit into that name (unconnected-(U1A-GPIO23-Pad35) once the RP became two units)."""
    m = re.match(r'unconnected-\(([A-Z]+\d+)[A-Z]?-.*-Pad(\w+)\)$', n)
    if m:
        return 'unconnected:%s:%s' % m.groups()
    return n.rsplit('/', 1)[-1]


def schematic_nets():
    fn = tmp('sync.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn,
                    os.path.join(PRJ, D.PROJECT + '.kicad_sch')], check=True, capture_output=True)
    t = parse(open(fn).read())
    return [str(find(n, 'name')[1]) for n in findall(find(t, 'nets'), 'net')]


def main():
    check_only = '--check' in sys.argv
    text = open(PCB).read()
    board = sorted(set(NET_TOKEN.findall(text)))
    sch = schematic_nets()
    by_short = {}
    for n in sch:
        if canon(n) in by_short:
            raise SystemExit('schematic: %s and %s share a name' % (by_short[canon(n)], n))
        by_short[canon(n)] = n
    rename, bad = {}, []
    for n in board:
        new = by_short.get(canon(n))
        if new is None:
            bad.append('board net %s is not in the schematic' % n)
        elif new != n:
            rename[n] = new
    mapped = {rename.get(n, n) for n in board}
    if len(mapped) != len(board):
        bad.append('two board nets would share a name')
    single = set(sch) - mapped
    if single:
        bad.append('schematic nets with no copper on the board: %s' % sorted(single))
    if bad:
        raise SystemExit('sync_pcb_nets:\n  ' + '\n  '.join(bad))
    new_text = NET_TOKEN.sub(lambda m: '(net "%s")' % rename.get(m.group(1), m.group(1)), text)
    # proof: cut every name to its last element and the two boards are the same text
    cut = lambda s: NET_TOKEN.sub(lambda m: '(net "%s")' % canon(m.group(1)), s)
    assert cut(new_text) == cut(text), 'the rewrite changed more than net names'
    print('%d board nets, %d renamed' % (len(board), len(rename)))
    for o in sorted(rename)[:6]:
        print('  %s -> %s' % (o, rename[o]))
    if rename and len(rename) > 6:
        print('  ...')
    if not check_only and new_text != text:
        open(PCB, 'w').write(new_text)


if __name__ == '__main__':
    main()
