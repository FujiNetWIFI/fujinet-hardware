#!/usr/bin/env python3
"""Build-day sourcing for FujiNet-StudioII Rev0: every assembled BOM line's stock at JLCPCB (its own
parts-library API, the one jlcpcb.com/parts uses: jlcsearch's index misses codes -- it reported no
74HCT08 at all, which the first Rev0 README repeated) and at LCSC (wmsc.lcsc.com product detail),
against the quantities for 2 and 5 assembled boards, and a parts-cost estimate.  Writes docs/sourcing.md; the raw answers go to
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
# second sources for lines JLC / LCSC are short of (filled in when a line is short)
ALTERNATES = {
    # README: the 74HCT1G02 (Nexperia) has a TI fallback on the same SOT-23-5 land; the AOTA inductor is the thin line
    '74HCT1G02GV,125': [('SN74AHCT1G02DBVR', 'Texas Instruments', 'C163710')],
    'SN74HCT32DR': [('74HCT32D,653', 'Nexperia', 'C5985')],
    'AOTA-B201610S3R3-101-T': [('VLS201610HBX-3R3M-1', 'TDK', 'C695624')],
}
DISTRIBUTORS = ''
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
    # productCycle is LCSC's lifecycle flag ('normal' for an active part; anything else is reported)
    return {'model': d.get('productModel'), 'brand': d.get('brandNameEn'), 'stock': d.get('stockNumber'),
            'ladder': ladder, 'cycle': d.get('productCycle')}


def ohms(v):
    m = {'k': 1e3, 'M': 1e6, 'R': 1.0}
    return float(v[:-1]) * m[v[-1]] if v[-1] in m else float(v)


def jlc(code, part=None):
    """JLC parts-library stock from JLCPCB's own search API (by LCSC code, exact match)."""
    body = json.dumps({'keyword': code, 'currentPage': 1, 'pageSize': 25, 'searchSource': 'search'}).encode()
    req = urllib.request.Request(
        'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList', data=body,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/plain, */*',
                 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36',
                 'Origin': 'https://jlcpcb.com', 'Referer': 'https://jlcpcb.com/parts'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except Exception as e:                                    # noqa: BLE001
        return {'error': str(e)}
    for h in ((d.get('data') or {}).get('componentPageInfo') or {}).get('list') or []:
        if h.get('componentCode') == code:
            kind = h.get('componentLibraryType')
            return {'stock': h.get('stockCount'), 'basic': kind == 'base', 'preferred': kind == 'expand' and
                    bool(h.get('preferredComponentFlag')), 'type': kind, 'model': h.get('componentModelEn')}
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
    # export.groups: (value, footprint, MPN, LCSC, DNP) -> parts; here with the manufacturer folded in
    lines = [((k[0], k[1], k[2], ps[0].mfr, k[3], k[4]), ps) for k, ps in E.groups(True)]
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
    out = ['# FujiNet-StudioII Rev0: sourcing (%s)' % day, '',
           'Stock read %s by `tools/audit/sourcing.py`: JLCPCB parts library via its own search API, LCSC via its '
           'product-detail API (raw answers in `%s`). Quantities for %s assembled boards; JLCPCB makes at '
           'least 5 PCBs and assembles 2 or more of them. Prices are LCSC unit prices at the 5-board quantity, '
           'in USD, before assembly fees.' % (when, os.path.relpath(fn, PRJ), ' and '.join(map(str, BOARDS))), '',
           '| Designators | Part | LCSC | Per board | JLC stock | JLC type | LCSC stock | LCSC lifecycle | Need (2 / 5) | Status | USD per board |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    eol = []
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
        cyc = a['lcsc'].get('cycle') or ('no LCSC record (JLC lists it)' if a['lcsc'].get('model') is None
                                         and a['jlc'].get('model') else '?')
        if cyc != 'normal' and code not in {e[2] for e in eol}:
            eol.append((refs, mpn, code, cyc))
        out.append('| %s | %s %s | %s | %d | %s | %s | %s | %s | %d / %d | %s | %s |'
                   % (refs if len(refs) < 40 else refs[:37] + '...', mfr, mpn, code, n, js, kind, ls, cyc, need[0], need[1],
                      status, '%.2f' % (p * n) if p is not None else '?'))
    out += ['', 'Parts cost per board (LCSC prices, 5-board quantities): **USD %.2f**, before JLC assembly, '
            'extended-part and Global Sourcing fees.' % cost, '']
    out += ['## Lifecycle', '', 'LCSC\'s product-cycle flag for every line: %s' % (
        'all "normal" (active).' if not eol else 'not "normal" for:'), '']
    out += ['- %s %s (%s): %s' % (mpn, code, refs, cyc) for refs, mpn, code, cyc in eol] + ([''] if eol else [])
    out += ['## Short at JLCPCB', '']
    if not short:
        out.append('Nothing: every assembled line is in JLCPCB stock for 5 boards.')
    for ps, mpn, mfr, code, js, ls, need, unknown in short:
        refs = ', '.join(sorted((q.ref for q in ps), key=E.ref_key))
        alts = ALTERNATES.get(mpn, [])
        alt = '; '.join('%s %s %s: JLC %s, LCSC %s' % (m, f, c, ans[c]['jlc'].get('stock') or 0,
                                                       ans[c]['lcsc'].get('stock') or 0) for m, f, c in alts)
        out.append('- **%s %s** (%s, %s): %s, LCSC %d, need %d for 5 boards.%s'
                   % (mfr, mpn, code, refs, 'not found by the JLC search (confirm on the order page)'
                      if unknown else 'JLC %d' % js, ls, need[-1], (' Alternates: ' + alt + '.') if alt else ''))
    out += ['', DISTRIBUTORS, 'For a short line, one of:', '',
            '1. **Consign** the parts to JLCPCB (buy from DigiKey / Mouser by MPN, ship to JLC).',
            "2. **JLC Global Sourcing**: JLC buys them for the order (lead time and a fee; quote on the order page).",
            '3. **A drop-in substitute** in stock at JLC (same footprint and pinout): change design.py, re-run '
            '`tools/build_all.sh` and the JLC rotation measurement.', '']
    open(os.path.join(PRJ, 'docs', 'sourcing.md'), 'w').write('\n'.join(out))
    print('sourcing: %d lines, %d short at JLCPCB for %d boards, %d not "normal" at LCSC; USD %.2f parts per board; '
          'docs/sourcing.md' % (len(lines), len(short), BOARDS[-1], len(eol), cost))
    return short


if __name__ == '__main__':
    main()
