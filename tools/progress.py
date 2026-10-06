#!/usr/bin/env python3
"""Summarize functions.csv.

    python tools/progress.py
"""
import collections

from common import load_functions

TOTAL_FUNCTIONS = 34992      # lower-bound count of functions in v1.2.0 main
TOTAL_BYTES = 0xAFC000       # .text size, excluding the import stubs


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


if __name__ == '__main__':
    main()
