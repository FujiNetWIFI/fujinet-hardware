#!/usr/bin/env python3
"""Refresh tools/symcache.sexpr: the flattened stock KiCad symbols gen_sch.py
embeds in the sheets, so the generator never depends on another project.

Two sources:
  * the Astrocade Rev0 cache (itself harvested from the INTV Rev0 sheets:
    stock symbols as flattened by eeschema) -- kept as-is for every symbol
    the S3 / USB-UART / power sheets share with that board;
  * the installed KiCad symbol libraries (/usr/share/kicad/symbols), for the
    parts new to this board.  Derived symbols ("extends") are flattened the
    way eeschema does it: the parent's units and drawings under the derived
    name, the derived symbol's own properties on top.

Usage: python3 tools/harvest_symbols.py        (rewrites tools/symcache.sexpr)
"""
import copy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import parse, dump, find, findall, Q

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'symcache.sexpr')
ASTRO = os.path.join(HERE, '../../../Astrocade/rev0/tools/symcache.sexpr')
KICAD_SYMS = os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')

# lib -> symbols to flatten from the stock libraries
STOCK = {
    'MCU_RaspberryPi': ['RP2354B'],
    '74xx': ['74HCT00', '74HCT595', '74HC14', '74LS32', '74LS20'],   # the '253 is drawn by gen_sch
    'Regulator_Linear': ['AP2112K-3.3'],          # RP IOVDD LDO
    'Transistor_FET': ['AO3401A'],                # console 5V P-FET switch
    'MCU_Microchip_ATtiny': ['ATtiny13A-SS'],     # CIClone (DNP)
    'power': ['GND', '+5V', '+3V3', 'VBUS'],      # rail symbols (the drawn sheets; Value = net name)
}
# symbols the Astrocade cache carries that this board does not use
DROP = {'FujiNet-Astrocade:Astrocade_Cart_Edge_26', 'FujiNet-INTV:INTV_Cart_Edge_44',
        'MCU_RaspberryPi:RP2040', 'MCU_RaspberryPi:RP2354A', 'Memory_Flash:W25Q32JVSS',
        '74xx:74LS245', 'Transistor_BJT:BC847', 'Connector:Micro_SD_Card', 'Device:C_Polarized'}


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
    for s in parse(open(ASTRO).read())[1:]:
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
