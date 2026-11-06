#!/usr/bin/env python3
"""Schematic -> board, metadata only: what KiCad's "Update PCB from Schematic" would carry, without
it ever touching a pad, a track or a zone.

From the schematic's netlist (kicad-cli): every footprint's symbol path, sheet name / file, value
and fields (MPN, Manufacturer, LCSC, Datasheet, Description); every board net renamed to the
schematic's name (KiCad's /sheet/NET, /NET for a net that crosses sheets, the rail names), and
every pad the board leaves open put on its unconnected-(...) net.  The renaming is a bijection or
it stops: each schematic net must land on exactly one of the board's nets (the same pads), so a
drawing that joined or split a net cannot reach the board.  The copper hash (tools/convert.py
copper_hash: pads, tracks, vias, fills, copper shapes, by geometry) must be the same before and
after, and equal to tools/copper.sha256, what tools/convert.py wrote.

Usage: python3 tools/sync_board.py
"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
from sexpr import parse, find, findall
import convert as C

PRJ = os.path.dirname(HERE)
PCB = os.path.join(PRJ, 'Inty-FujiCard.kicad_pcb')
SCH = os.path.join(PRJ, 'Inty-FujiCard.kicad_sch')
FIELDS = ('Datasheet', 'Description', 'MPN', 'Manufacturer', 'LCSC')
KEEP = []


def die(msg):
    raise SystemExit('sync_board: ' + msg)


def netlist():
    fd, fn = tempfile.mkstemp(prefix='inty-sync-', suffix='.net')
    os.close(fd)
    try:
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', fn, SCH],
                       check=True, capture_output=True)
        t = parse(open(fn).read())
    finally:
        os.remove(fn)
    comps = {}
    for c in findall(find(t, 'components'), 'comp'):
        ref = str(find(c, 'ref')[1])
        fields = {}
        for f in findall(find(c, 'fields'), 'field'):
            nm = str(find(f, 'name')[1])
            fields[nm] = str(f[2]) if len(f) > 2 else ''
        props = {str(find(p, 'name')[1]): (str(find(p, 'value')[1]) if find(p, 'value') else '')
                 for p in findall(c, 'property')}
        sp = find(c, 'sheetpath')
        comps[ref] = dict(value=str(find(c, 'value')[1]), footprint=str(find(c, 'footprint')[1]),
                          fields=fields, props=props, path=str(find(sp, 'tstamps')[1]) + str(find(c, 'tstamps')[1]))
    nets = {}
    for n in findall(find(t, 'nets'), 'net'):
        nets[str(find(n, 'name')[1])] = {(str(find(nd, 'ref')[1]), str(find(nd, 'pin')[1])) for nd in findall(n, 'node')}
    return comps, nets


def main():
    comps, nets = netlist()
    b = pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(PCB, None)
    h0 = C.copper_hash(b)
    want = open(os.path.join(HERE, 'copper.sha256')).read().strip()
    if h0 != want:
        die('the board\'s copper is not what tools/convert.py wrote (%s, want %s): rerun it' % (h0[:16], want[:16]))
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    if set(fps) != set(comps):
        die('footprints %s / symbols %s' % (sorted(set(fps) - set(comps)), sorted(set(comps) - set(fps))))
    # footprints
    for ref, c in comps.items():
        f = fps[ref]
        if f.GetFPIDAsString() != c['footprint']:
            die('%s: board footprint %s, schematic %s' % (ref, f.GetFPIDAsString(), c['footprint']))
        f.SetValue(c['value'])
        f.SetPath(pcbnew.KIID_PATH(c['path'].rstrip('/')))
        f.SetSheetname(c['props'].get('Sheetname', ''))
        f.SetSheetfile(c['props'].get('Sheetfile', ''))
        for k in FIELDS:
            v = c['fields'].get(k, '')
            if v or f.HasField(k):
                f.SetField(k, v)
                f.GetField(k).SetVisible(False)
                if k not in ('Datasheet', 'Description'):
                    f.GetField(k).SetLayer(pcbnew.F_Fab)
        bom = c['props'].get('exclude_from_bom') is None
        if bom == bool(f.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM):
            die('%s: in the BOM %s in the schematic, not on the board' % (ref, bom))
    # nets: schematic net -> the one board net on its pads
    pad_net = {}
    for f in fps.values():
        for p in f.Pads():
            if p.GetNumber():
                pad_net.setdefault((f.GetReference(), p.GetNumber()), set()).add(p.GetNetname())
    rename = {}
    for name, nodes in nets.items():
        old = set()
        for n in nodes:
            if n not in pad_net:
                die('net %s: %s has no pad %s' % (name, n[0], n[1]))
            old |= pad_net[n]
        if len(old) != 1:
            die('net %s lands on board nets %s' % (name, sorted(old)))
        o = old.pop()
        if name.startswith('unconnected-'):
            # '' straight from convert.py, an unconnected-(...) name once synced (KiCad's name for it
            # follows the drawing: a unit letter appears once the sheet is drawn)
            if o != '' and not o.startswith('unconnected-'):
                die('%s is on %s on the board' % (name, o))
            continue
        if o in rename:
            die('board net %s is both %s and %s' % (o, rename[o], name))
        rename[o] = name
    board_nets = {n for s in pad_net.values() for n in s if n and not n.startswith('unconnected-')}
    if set(rename) != board_nets:
        die('board nets no schematic net names: %s' % sorted(board_nets - set(rename)))
    new = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
        new[name] = ni
    moved = 0
    for f in fps.values():
        for p in f.Pads():
            if not p.GetNumber():
                continue
            o = p.GetNetname()
            if o and not o.startswith('unconnected-'):
                p.SetNet(new[rename[o]])
            else:
                cand = [n for n, nodes in nets.items() if (f.GetReference(), p.GetNumber()) in nodes]
                if len(cand) != 1:
                    die('%s pad %s: unconnected on the board, schematic nets %s' % (f.GetReference(), p.GetNumber(), cand))
                p.SetNet(new[cand[0]])
            moved += 1
    items = list(b.GetTracks()) + list(b.Zones()) + \
        [d for d in b.GetDrawings() if d.GetClass() == 'PCB_SHAPE' and pcbnew.IsCopperLayer(d.GetLayer())]
    for it in items:
        o = it.GetNetname()
        if o:
            if o not in rename:
                die('%s on board net %s, which no pad carries' % (it.GetClass(), o))
            it.SetNet(new[rename[o]])
    b.RemoveUnusedNets(None)
    KEEP.append(new)
    if C.copper_hash(b) != h0:
        die('the copper changed')
    pcbnew.PCB_IO_KICAD_SEXPR().SaveBoard(PCB, b)
    # the fields added here got random UUIDs: renumber by content, as tools/convert.py does
    C.deterministic_uuids(PCB, reorder=True)
    pcbnew.PCB_IO_KICAD_SEXPR().SaveBoard(PCB, pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(PCB, None))
    # reload and check every pad against the netlist
    r = pcbnew.PCB_IO_KICAD_SEXPR().LoadBoard(PCB, None)
    if C.copper_hash(r) != h0:
        die('the saved board\'s copper changed')
    got = {}
    for f in r.GetFootprints():
        for p in f.Pads():
            if p.GetNumber():
                got.setdefault(p.GetNetname(), set()).add((f.GetReference(), p.GetNumber()))
    if got != nets:
        bad = sorted(set(got) ^ set(nets))[:6] or [n for n in nets if got.get(n) != nets[n]][:6]
        die('saved board nets differ from the schematic: %s' % bad)
    print('board synced: %d footprints, %d nets (%d renamed, %d unconnected pads), copper unchanged (%s)'
          % (len(comps), len(nets), len(rename), sum(1 for n in nets if n.startswith('unconnected-')), h0[:16]))


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        print(e, flush=True)
        os._exit(1 if e.code else 0)
    sys.stdout.flush()
    os._exit(0)
