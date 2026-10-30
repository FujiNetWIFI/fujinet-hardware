#!/usr/bin/env python3
"""Query LCSC for part codes: python3 tools/lcsc.py C123 C456 ...  (or --search kw: JLCPCB parts search, basic parts first)"""
import json, sys, urllib.request, urllib.parse
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(req, timeout=30))
def detail(code):
    r = get('https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=' + code).get('result') or {}
    return (code, r.get('productModel'), r.get('brandNameEn'), r.get('encapStandard'), r.get('stockNumber'), r.get('productIntroEn', '')[:70])
if __name__ == '__main__':
    if sys.argv[1] == '--search':
        body = json.dumps({'keyword': ' '.join(sys.argv[2:]), 'currentPage': 1, 'pageSize': 25}).encode()
        req = urllib.request.Request('https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList',
                                     data=body, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})
        lst = json.load(urllib.request.urlopen(req, timeout=30))['data']['componentPageInfo']['list'] or []
        lst.sort(key=lambda p: (p.get('componentLibraryType') != 'base', -(p.get('stockCount') or 0)))
        for p in lst:
            print(p.get('componentCode'), p.get('componentModelEn'), p.get('componentSpecificationEn'), p.get('componentLibraryType'),
                  p.get('stockCount'), (p.get('describe') or '')[:70], sep=' | ')
    else:
        for c in sys.argv[1:]:
            print(*detail(c), sep=' | ')
