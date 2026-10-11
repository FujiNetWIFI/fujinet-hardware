#!/usr/bin/env python3
"""Find which page of a datasheet PDF carries a verbatim quote (for the deep
review's citations).  Uses pdftotext -layout; whitespace runs are folded.

Usage: python3 tools/audit/find_quote_page.py <pdf> "<quote>" ["<quote>" ...]
"""
import re, subprocess, sys


def pages(pdf):
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True, errors='replace').stdout
    return txt.split('\f')


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def main():
    pdf, quotes = sys.argv[1], sys.argv[2:]
    pg = [norm(p) for p in pages(pdf)]
    for q in quotes:
        hits = [i + 1 for i, p in enumerate(pg) if norm(q) in p]
        print('%s | %s | %s' % (pdf.split('/')[-1][:40], q[:70], ','.join(map(str, hits)) if hits else 'NOT FOUND'))


if __name__ == '__main__':
    main()
