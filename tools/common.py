"""Shared helpers: paths, config, functions.csv, and the decompressed game image."""
import csv
import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
BUILD = os.path.join(ROOT, 'build')
CSV_PATH = os.path.join(ROOT, 'functions.csv')
IMAGE_PATH = os.path.join(BUILD, 'main.bin')

BASE = 0x7100000000          # where Ghidra (and the Switch) loads main
BUILD_ID = '89048449BA238C8CF565518B83BF02D3'  # FE3H v1.2.0

DEFAULT_CONFIG = {
    # Compiler used for matching: LLVM/clang 6.0.x (5.0.1 also works).
    # -g matters: debug info changes LLVM 5/6 scheduling, and Nintendo builds with it.
    'cxx': 'clang++',
    'flags': ['--target=aarch64-none-elf', '-O2', '-g', '-mcpu=cortex-a57', '-std=c++17',
              '-fno-exceptions', '-fno-rtti', '-nostdlibinc'],
}


def config():
    cfg = dict(DEFAULT_CONFIG)
    path = os.path.join(ROOT, 'config.json')
    if os.path.exists(path):
        with open(path) as f:
            cfg.update(json.load(f))
    return cfg


def load_functions():
    """Rows of functions.csv as dicts with int 'address'/'size'."""
    rows = []
    with open(CSV_PATH, newline='') as f:
        for row in csv.DictReader(f):
            row['address'] = int(row['address'], 16)
            row['size'] = int(row['size'], 16)
            rows.append(row)
    return rows


def find_function(name):
    for row in load_functions():
        if row['name'] == name or hex(row['address']).lower() == name.lower():
            return row
    sys.exit(f"'{name}' isn't in functions.csv")


def image():
    """Decompressed main (flat, base 0). Run tools/setup.py first."""
    if not os.path.exists(IMAGE_PATH):
        sys.exit('build/main.bin not found. Run:  python tools/setup.py')
    with open(IMAGE_PATH, 'rb') as f:
        return f.read()


def itanium_prefix(name):
    """'Camera::Set' -> '_ZN6Camera3SetE', 'Foo' -> '_Z3Foo' (enough to find our symbols)."""
    parts = name.split('::')
    if len(parts) == 1:
        return f'_Z{len(name)}{name}'
    return '_ZN' + ''.join(f'{len(p)}{p}' for p in parts) + 'E'


def decompress_nso(path):
    """Parse a Switch NSO, LZ4-decompress its segments, verify hashes. Returns (image, build_id)."""
    import lz4.block
    with open(path, 'rb') as f:
        d = f.read()
    if d[:4] != b'NSO0':
        sys.exit(f'{path} is not an NSO (bad magic)')
    flags = struct.unpack_from('<I', d, 0xC)[0]
    segs = []
    for i in range(3):
        foff, moff, dsz = struct.unpack_from('<III', d, 0x10 + i * 0x10)
        csz = struct.unpack_from('<I', d, 0x60 + i * 4)[0]
        digest = d[0xA0 + i * 0x20:0xC0 + i * 0x20]
        segs.append((foff, moff, dsz, csz, digest))
    img = bytearray(segs[2][1] + segs[2][2])
    for i, (foff, moff, dsz, csz, digest) in enumerate(segs):
        raw = d[foff:foff + csz]
        data = lz4.block.decompress(raw, uncompressed_size=dsz) if flags & (1 << i) else raw
        if hashlib.sha256(data).digest() != digest:
            sys.exit(f'segment {i} hash mismatch: the dump is damaged')
        img[moff:moff + dsz] = data
    return bytes(img), d[0x40:0x50].hex().upper()
