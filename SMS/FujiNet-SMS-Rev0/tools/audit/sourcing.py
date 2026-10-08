#!/usr/bin/env python3
"""Build-day sourcing for FujiNet-SMS Rev0: every assembled BOM line's stock at JLCPCB (its parts
library, via jlcsearch.tscircuit.com) and at LCSC (wmsc.lcsc.com product detail), against the
quantities for 2 and 5 assembled boards, with the alternates design.py does not fit (the TI gates)
and a parts-cost estimate.  Writes docs/sourcing.md; the raw answers go to
analysis/sourcing/<date>.json so the table can be re-read without the network.

Usage: python3 tools/audit/sourcing.py [--offline]     (--offline: re-use the newest saved answers)
"""
import datetime, glob, json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D
import export as E

BOARDS = (2, 5)
# not fitted by design.py: second sources for the parts JLC / LCSC are short of
ALTERNATES = {'74HCT27D,653': [('CD74HCT27M96', 'Texas Instruments', 'C2878706')],
              '74HCT10D,653': [('CD74HCT10M', 'Texas Instruments', 'C2863188')]}
# Distributor stock for the consign / turnkey lines, read by web search (not by this script):
# figures as the search reported them, to be re-checked on the order day.
DISTRIBUTORS = '''Distributor stock for the consign / turnkey lines (web search, 2026-10-08; re-check on the order day):

- **AS6C4008-55TIN**: DigiKey 909 ($9.61 at 1), Mouser 195 (25 weeks beyond stock), TME 420, Farnell 297, Newark 212
  ([DigiKey](https://www.digikey.com/en/products/detail/alliance-memory-inc/AS6C4008-55TIN/4234589),
  [Mouser](https://www.mouser.com/ProductDetail/Alliance-Memory/AS6C4008-55TIN?qs=E5c5%2Bmu3i39Yioey6aezLQ%3D%3D)).
  10 for 5 boards, plus spares: about $100.
- **74HCT10D,653**: DigiKey 2655 ($0.48 at 1)
  ([DigiKey](https://www.digikey.com/en/products/detail/nexperia-usa-inc/74HCT10D-653/1230591)).
- **74HCT27D,653**: reported in stock at DigiKey (1491) and Mouser ($0.53); the search did not return the part's own
  DigiKey page, so confirm it there.
'''
UA = {'User-Agent': 'Mozilla/5.0 (FujiNet hardware sourcing check)'}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def lcsc(code):
    try:
        d = get('https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=%s' % code)['result'] or {}
    except Exception as e:                                    # noqa: BLE001  (report, keep going)
        return {'error': str(e)}
    ladder = [(p['ladder'], p['usdPrice']) for p in d.get('productPriceList') or []]
    return {'model': d.get('productModel'), 'brand': d.get('brandNameEn'), 'stock': d.get('stockNumber'),
            'ladder': ladder}


def ohms(v):
    m = {'k': 1e3, 'M': 1e6, 'R': 1.0}
    return float(v[:-1]) * m[v[-1]] if v[-1] in m else float(v)


def jlc(code, part=None):
    """JLC parts-library stock.  jlcsearch's text search misses some codes (C25804, a basic 10k,
    on 2026-10-08), so a miss on a single resistor is retried in its resistor listing; any other
    miss is reported as unknown, not as zero stock."""
    n = int(code[1:])
    try:
        hits = get('https://jlcsearch.tscircuit.com/api/search?q=%s&limit=5' % code)['components']
        for h in hits:
            if h.get('lcsc') == n:
                return {'stock': h.get('stock'), 'basic': h.get('is_basic'), 'preferred': h.get('is_preferred'),
                        'price': h.get('price')}
        if part is not None and part.prefix == 'R':
            pkg = '0402' if '0402' in part.footprint else '0603'
            for h in get('https://jlcsearch.tscircuit.com/resistors/list.json?resistance=%g&package=%s'
                         % (ohms(part.value), pkg))['resistors']:
                if h.get('lcsc') == n:
                    return {'stock': h.get('stock'), 'basic': h.get('is_basic'), 'preferred': h.get('is_preferred'),
                            'price': h.get('price1'), 'via': 'resistor listing'}
    except Exception as e:                                    # noqa: BLE001
        return {'error': str(e)}
    return {'stock': None, 'listed': False}


def price(l, qty):
    p = None
    for lad, usd in l.get('ladder') or []:
        if qty >= lad:
            p = usd
    if p is None and l.get('ladder'):
        p = l['ladder'][0][1]
    return p


def main():
    os.makedirs(os.path.join(PRJ, 'analysis', 'sourcing'), exist_ok=True)
    lines = [(k, ps) for k, ps in E.groups() if not k[5]]
    codes = sorted({k[4] for k, _ in lines} | {a[2] for v in ALTERNATES.values() for a in v})
    part_of = {k[4]: ps[0] for k, ps in lines}
    per_code = {}
    for k, ps in lines:
        per_code[k[4]] = per_code.get(k[4], 0) + len(ps)
    if '--offline' in sys.argv:
        fn = sorted(glob.glob(os.path.join(PRJ, 'analysis', 'sourcing', '*.json')))[-1]
        saved = json.load(open(fn))
        ans, when = saved['answers'], saved['when']
    else:
        when = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
        ans = {}
        for c in codes:
            ans[c] = {'lcsc': lcsc(c), 'jlc': jlc(c, part_of.get(c))}
            time.sleep(0.3)
        fn = os.path.join(PRJ, 'analysis', 'sourcing', when[:10] + '.json')
        json.dump({'when': when, 'answers': ans}, open(fn, 'w'), indent=1)
    day = when[:10]
    out = ['# FujiNet-SMS Rev0: sourcing (%s)' % day, '',
           'Stock read %s by `tools/audit/sourcing.py`: JLCPCB parts library via jlcsearch, LCSC via its '
           'product-detail API (raw answers in `%s`). Quantities for %s assembled boards; JLCPCB makes at '
           'least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, '
           'in USD, before assembly fees.' % (when, os.path.relpath(fn, PRJ), ' and '.join(map(str, BOARDS))), '',
           '| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | Need (2 / 5) | Status | USD per board |',
           '|---|---|---|---|---|---|---|---|---|---|']
    short, cost, done = [], 0.0, set()
    for (val, fp, mpn, mfr, code, dnp), ps in lines:
        a = ans[code]
        n = len(ps)
        unknown = a['jlc'].get('stock') is None
        js, ls = a['jlc'].get('stock') or 0, a['lcsc'].get('stock') or 0
        kind = 'basic' if a['jlc'].get('basic') else 'preferred' if a['jlc'].get('preferred') else \
            'unknown' if unknown else 'extended'
        need = [per_code[code] * b for b in BOARDS]     # the code's whole need (the four buttons are four lines)
        ok = js >= need[-1]
        status = 'OK' if ok else '%s: %s' % ('not listed at JLC' if unknown else 'JLC short',
                                              'LCSC has %d' % ls if ls >= need[-1] else 'consign / Global Sourcing / PCBWay')
        if not ok and code not in done:
            short.append((ps, mpn, mfr, code, js, ls, need, unknown))
            done.add(code)
        p = price(a['lcsc'], n * BOARDS[-1])
        cost += (p or 0) * n
        refs = ','.join(sorted((q.ref for q in ps), key=E.ref_key))
        out.append('| %s | %s %s | %s | %d | %s | %s | %s | %d / %d | %s | %s |'
                   % (refs if len(refs) < 40 else refs[:37] + '...', mfr, mpn, code, n, js, kind, ls, need[0], need[1],
                      status, '%.2f' % (p * n) if p is not None else '?'))
    out += ['', 'Parts cost per board (LCSC prices, 5-board quantities): **USD %.2f**, before JLC assembly, '
            'extended-part and Global Sourcing fees.' % cost, '']
    out += ['## Short at JLCPCB', '']
    if not short:
        out.append('Nothing: every assembled line is in JLCPCB stock for 5 boards.')
    for ps, mpn, mfr, code, js, ls, need, unknown in short:
        refs = ', '.join(sorted((q.ref for q in ps), key=E.ref_key))
        alts = ALTERNATES.get(mpn, [])
        alt = '; '.join('%s %s %s: JLC %s, LCSC %s' % (m, f, c, ans[c]['jlc'].get('stock') or 0,
                                                       ans[c]['lcsc'].get('stock') or 0) for m, f, c in alts)
        out.append('- **%s %s** (%s, %s): %s, LCSC %d, need %d for 5 boards.%s'
                   % (mfr, mpn, code, refs, 'not listed by jlcsearch (no JLC stock shown; confirm on the order page)'
                      if unknown else 'JLC %d' % js, ls, need[-1], (' Alternates: ' + alt + '.') if alt else ''))
    out += ['', DISTRIBUTORS, 'For each short line, one of:', '',
            '1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser, ship to JLC; `exports/jlcpcb/consigned.csv` lists them).',
            "2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).",
            '3. **PCBWay turnkey**: PCBWay sources every line by MPN (`exports/pcbway/BOM-PCBWay.csv`).',
            '4. For the gates only: fit the TI alternates (pin-identical; `timing_margins.py --ti` keeps every margin positive) '
            'if their stock covers the build.', '']
    open(os.path.join(PRJ, 'docs', 'sourcing.md'), 'w').write('\n'.join(out))
    print('sourcing: %d lines, %d short at JLCPCB for %d boards; USD %.2f parts per board; docs/sourcing.md'
          % (len(lines), len(short), BOARDS[-1], cost))
    return short


if __name__ == '__main__':
    main()
