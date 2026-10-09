#!/usr/bin/env python3
"""Refresh tools/symcache.sexpr: the flattened stock KiCad symbols gen_sch.py
embeds in the sheets, so the generator never depends on another project.

Two sources:
  * the existing cache (carried over from FujiNet-Astrocade Rev0: stock
    symbols as flattened by eeschema), kept for every symbol it already has;
  * the installed KiCad symbol libraries (/usr/share/kicad/symbols) for the
    rest.  Derived symbols ("extends") are flattened the way eeschema does
    it: the parent's units and drawings under the derived name, the derived
    symbol's own properties on top.

Usage: python3 tools/harvest_symbols.py        (rewrites tools/symcache.sexpr)
"""
import copy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'symcache.sexpr')
KICAD_SYMS = os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')

# lib -> symbols to (re)flatten from the stock libraries
STOCK = {
    'MCU_RaspberryPi': ['RP2040'],                     # the cart's MCU (gen_sch splits it in two units)
    'Memory_Flash': ['W25Q16JVSS'],                    # its 2 MB boot flash
    'Logic_LevelTranslator': ['SN74LVC8T245'],         # pin-number reference for the SN74LVC4245A symbol
    'Transistor_FET': ['2N7002'],                      # /INTREQ open-drain driver
    'Regulator_Linear': ['AP2112K-3.3'],               # RP LDO (+3V3_RP)
    'Device': ['R_Pack04_Split'],                      # the SD pull-up pack, one unit per resistor
    'power': ['GND', '+1V1', '+3V3', '+5V', 'VBUS', 'PWR_FLAG'],
}
# symbols the carried-over cache holds that this board does not use
DROP = {'MCU_RaspberryPi:RP2354A'}


def flatten(lib, name, syms):
    s = syms[name]
    ext = find(s, 'extends')
    if not ext:
        out = copy.deepcopy(s)
    else:
        out = flatten(lib, str(ext[1]), syms)
        parent = out[1].split(':', 1)[1]
        # the derived symbol's properties replace the parent's of the same name
        mine = {str(p[1]): p for p in findall(s, 'property')}
        for i, e in enumerate(out):
            if isinstance(e, list) and e and e[0] == 'property' and str(e[1]) in mine:
                out[i] = copy.deepcopy(mine.pop(str(e[1])))
        first_sub = next(i for i, e in enumerate(out) if isinstance(e, list) and e and e[0] == 'symbol')
        for p in mine.values():
            out.insert(first_sub, copy.deepcopy(p)); first_sub += 1
        for sub in findall(out, 'symbol'):
            sub[1] = Q(name + str(sub[1])[len(parent):])
    out[1] = Q(lib + ':' + name)
    return out


def main():
    got = {}
    for s in parse(open(CACHE).read())[1:]:
        if s[1] not in DROP:
            got[s[1]] = s
    for lib, names in STOCK.items():
        t = parse(open(os.path.join(KICAD_SYMS, lib + '.kicad_sym')).read())
        syms = {str(s[1]): s for s in t[1:] if isinstance(s, list) and s[0] == 'symbol'}
        for n in names:
            f = flatten(lib, n, syms)
            got[f[1]] = f
    out = ['symcache'] + [got[k] for k in sorted(got)]
    open(CACHE, 'w').write(dump(out) + '\n')
    print('\n'.join(sorted(got)))


if __name__ == '__main__':
    main()
