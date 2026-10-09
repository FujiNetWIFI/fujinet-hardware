#!/usr/bin/env python3
"""Every assembled BOM line's stock at JLCPCB (its own parts-library API, the one jlcpcb.com/parts
uses) and LCSC (wmsc.lcsc.com product detail), per board.  The answers go to
analysis/sourcing/<date>.json; --offline prints the newest saved answers.  (The search functions are
FujiNet-5200 Rev0's tools/audit/sourcing.py.)

Usage: python3 tools/audit/stock_check.py [--offline]
"""
import datetime, glob, json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PRJ, 'tools'))
import design as D
UA = {'User-Agent': 'Mozilla/5.0 (FujiNet hardware sourcing check)'}


def lcsc(code):
    try:
        req = urllib.request.Request('https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=%s' % code, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)['result'] or {}
    except Exception as e:                                    # noqa: BLE001  (report, keep going)
        return {'error': str(e)}
    return {'model': d.get('productModel'), 'stock': d.get('stockNumber')}


def jlc(code):
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
            return {'stock': h.get('stockCount'), 'library': h.get('componentLibraryType')}
    return {'stock': 0, 'library': None}


def main():
    out_dir = os.path.join(PRJ, 'analysis', 'sourcing')
    if '--offline' in sys.argv:
        out = json.load(open(sorted(glob.glob(os.path.join(out_dir, '*.json')))[-1]))
    else:
        need = {}
        for p in D.PARTS:
            if p.bom and not p.dnp and p.lcsc:
                need.setdefault(p.lcsc, {'mpn': p.mpn, 'per_board': 0, 'refs': []})
                need[p.lcsc]['per_board'] += 1
                need[p.lcsc]['refs'].append(p.ref)
        out = {}
        for code, info in sorted(need.items(), key=lambda kv: kv[1]['mpn']):
            out[code] = dict(info, jlc=jlc(code), lcsc=lcsc(code))
            time.sleep(0.3)
        os.makedirs(out_dir, exist_ok=True)
        json.dump(out, open(os.path.join(out_dir, '%s.json' % datetime.date.today()), 'w'), indent=1)
    for code, r in out.items():
        print('%-24s %-10s x%-2d JLC %-9s %-9s LCSC %s' % (r['mpn'], code, r['per_board'], r['jlc'].get('stock'),
                                                       r['jlc'].get('library') or '', r['lcsc'].get('stock')))


if __name__ == '__main__':
    main()
