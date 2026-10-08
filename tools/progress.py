#!/usr/bin/env python3
"""Summarize functions.csv.

    python tools/progress.py
    python tools/progress.py --map
"""
import collections
import os
import sys

from common import BASE, ROOT, load_functions

TOTAL_FUNCTIONS = 34992      # lower-bound count of functions in v1.2.0 main
TOTAL_BYTES = 0xAFC000       # .text size, excluding the import stubs

#Progress map: one square per 1 KiB of code, in address order.
CELL = 1024                  # bytes of code per square
COLS = 128                   # squares per row
PX = 6                       #pixels per square, including a 1px gap
COLORS = {'wip': '#d29922', 'decompiled': '#d29922', 'nonmatching': '#f0883e', 'matching': '#3fb950'}
RANK = {'wip': 1, 'decompiled': 1, 'nonmatching': 2, 'matching': 3}


def write_map(rows, path):
    """Color each square by the best status of any function inside it."""
    best = {}
    for r in rows:
        if r['status'] not in COLORS:
            continue
        start = r['address'] - BASE
        first, last = start // CELL, (start + r['size'] - 1) // CELL
        for cell in range(first, last + 1):
            if cell not in best or RANK[r['status']] > RANK[best[cell]]:
                best[cell] = r['status']

    cells = TOTAL_BYTES // CELL
    full_rows, extra = cells // COLS, cells % COLS
    width, height = COLS * PX, (cells + COLS - 1) // COLS * PX
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
           f'<defs><pattern id="grey" width="{PX}" height="{PX}" patternUnits="userSpaceOnUse">'
           f'<rect width="{PX - 1}" height="{PX - 1}" fill="#8b949e" fill-opacity="0.35"/></pattern></defs>',
           f'<rect width="{width}" height="{full_rows * PX}" fill="url(#grey)"/>',
           f'<rect y="{full_rows * PX}" width="{extra * PX}" height="{PX}" fill="url(#grey)"/>']
    for cell, status in sorted(best.items()):
        x, y = cell % COLS * PX, cell // COLS * PX
        out.append(f'<rect x="{x}" y="{y}" width="{PX - 1}" height="{PX - 1}" fill="{COLORS[status]}"/>')
    out.append('</svg>')
    with open(path, 'w') as f:
        f.write('\n'.join(out) + '\n')


def main():
    rows = load_functions()
    by_status = collections.Counter(r['status'] for r in rows)
    done = [r for r in rows if r['status'] in ('matching', 'nonmatching', 'decompiled')]
    done_bytes = sum(r['size'] for r in done)
    print(f'Tracked functions: {len(rows)}')
    for status in ('matching', 'nonmatching', 'decompiled', 'wip', 'todo'):
        if by_status.get(status):
            print(f'  {status:12s} {by_status[status]}')
    print(f'Progress: {len(done)}/{TOTAL_FUNCTIONS} functions ({len(done) / TOTAL_FUNCTIONS * 100:.3f}%), '
          f'{done_bytes:#x}/{TOTAL_BYTES:#x} bytes ({done_bytes / TOTAL_BYTES * 100:.4f}%)')
    if '--map' in sys.argv:
        path = os.path.join(ROOT, 'docs', 'progress.svg')
        write_map(rows, path)
        print(f'Map written to {path}')


if __name__ == '__main__':
    main()
