#!/usr/bin/env python3
"""Find or replace text in docs/index.html, showing which language each hit is in.

  site_text.py find TEXT [-i]               every occurrence: line, where it is (mn / en / tag attribute
                                            / other) and some context. -i ignores case (Cyrillic too).
  site_text.py replace OLD NEW [--count N]  replace EVERY occurrence of OLD, but only if there are
                                            exactly N of them (default 1); otherwise change nothing.
                                            To change only some places, widen OLD with surrounding
                                            markup until `find` counts exactly those.

Use `find` before every wording change: a phrase often appears in several places (titles, tables,
FAQ, alt text) and the owner should choose which ones change.
"""
import argparse
import os
import re
import sys

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'docs', 'index.html')
SPAN = re.compile(r'<(/?)span\b[^>]*>')


def lang_ranges(page):
    """(start, end, lang) for every <span lang="mn|en"> element, nested spans included."""
    out = []
    for m in re.finditer(r'<span lang="(mn|en)">', page):
        depth, j = 1, m.end()
        while depth:
            t = SPAN.search(page, j)
            if not t:
                break
            depth += -1 if t.group(1) else 1
            j = t.end()
        out.append((m.start(), j, m.group(1)))
    return out


def where(page, pos, ranges):
    lt, gt = page.rfind('<', 0, pos), page.rfind('>', 0, pos)
    if lt > gt:
        return 'attribute'
    hits = [r for r in ranges if r[0] <= pos < r[1]]
    return min(hits, key=lambda r: r[1] - r[0])[2] if hits else 'other'


def part(page, pos):
    """'#id' of the last <section>/<header>/<footer>/<nav> opened before pos, or the tag name."""
    tags = re.findall(r'<(head|section|header|footer|nav)\b([^>]*)>', page[:pos])
    if not tags:
        return '-'
    tag, attrs = tags[-1]
    m = re.search(r'\bid="([^"]+)"', attrs)
    return '#' + m.group(1) if m else tag


def context(page, start, end, width=60):
    a, b = max(0, start - width), min(len(page), end + width)
    text = page[a:b].replace('\n', ' ')
    return re.sub(r'<[^>]*>', '·', text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('find')
    f.add_argument('text')
    f.add_argument('-i', action='store_true', help='ignore case')
    r = sub.add_parser('replace')
    r.add_argument('old')
    r.add_argument('new')
    r.add_argument('--count', type=int, default=1)
    args = ap.parse_args()

    page = open(PAGE, encoding='utf-8').read()
    ranges = lang_ranges(page)
    if args.cmd == 'find':
        flags = re.I if args.i else 0
        hits = list(re.finditer(re.escape(args.text), page, flags))
        for m in hits:
            line = page.count('\n', 0, m.start()) + 1
            print('%5d  %-9s  %-12s  …%s…' % (line, where(page, m.start(), ranges), part(page, m.start()),
                                              context(page, m.start(), m.end())))
        print('%d occurrence(s)' % len(hits))
        return
    n = page.count(args.old)
    if n != args.count:
        sys.exit('expected %d occurrence(s) of %r, found %d; nothing changed (run find first)' % (args.count, args.old, n))
    lines = [page.count('\n', 0, m.start()) + 1 for m in re.finditer(re.escape(args.old), page)]
    page = page.replace(args.old, args.new)
    with open(PAGE, 'w', encoding='utf-8') as fh:
        fh.write(page)
    for ln in lines:
        print('changed line %d' % ln)


if __name__ == '__main__':
    main()
