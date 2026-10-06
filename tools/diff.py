#!/usr/bin/env python3
"""Compile your C++ for a function and compare it with the game's machine code.

    python tools/diff.py Camera::Set              # score only
    python tools/diff.py Camera::Set --diff       # show the instruction diff
    python tools/diff.py Camera::Set --asm        # show the game's instructions only

Reads the function's address, size and source file from functions.csv.
Scores:
  exact  - same instructions, same registers, same order (100% = byte match)
  shape  - same instructions and order, ignoring which register was used
  same   - how many of the game's instructions appear anywhere in yours
"""
import collections
import difflib
import os
import re
import subprocess
import sys

import capstone
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection

from common import BASE, BUILD, ROOT, config, find_function, image, itanium_prefix, load_functions

md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
R_AARCH64_CALL26, R_AARCH64_JUMP26 = 283, 282


def known_names():
    """Game offset -> name, for labelling calls."""
    return {row['address'] - BASE: row['name'] for row in load_functions()}


def normalize(ins, func_start, func_end, call_names):
    mn, ops = ins.mnemonic, ins.op_str
    if mn in ('bl', 'b') and ops.startswith('#'):
        target = int(ops[1:], 16)
        if mn == 'bl' or not func_start <= target < func_end:   # call, or tail call
            return f'{mn} {call_names(target)}'
    if mn in ('b', 'cbz', 'cbnz', 'tbz', 'tbnz') or mn.startswith('b.'):
        parts = ops.split(', ')
        target = int(parts[-1].lstrip('#'), 16)
        return f'{mn} {", ".join(parts[:-1] + [f"+{target - func_start:#x}"])}'.replace(' , ', ' ')
    return f'{mn} {ops}'.strip()


def game_listing(row):
    img = image()
    start = row['address'] - BASE
    names = known_names()
    label = lambda t: names.get(t, f'sub_{t + BASE:x}')
    end = start + row['size']
    return [normalize(i, start, end, label) for i in md.disasm(img[start:end], start)]


def compile_listing(row):
    cfg = config()
    src = os.path.join(ROOT, row['file'])
    if not os.path.exists(src):
        sys.exit(f"{row['file']} doesn't exist yet")
    os.makedirs(BUILD, exist_ok=True)
    obj = os.path.join(BUILD, os.path.basename(src) + '.o')
    cmd = [cfg['cxx'], *cfg['flags'], '-I', os.path.join(ROOT, 'include'), '-I', os.path.join(ROOT, 'lib'),
           '-c', src, '-o', obj]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit('compile failed:\n' + r.stderr)

    with open(obj, 'rb') as f:
        elf = ELFFile(f)
        symtab = elf.get_section_by_name('.symtab')
        want = itanium_prefix(row['name'])
        sym = next((s for s in symtab.iter_symbols()
                    if s['st_info']['type'] == 'STT_FUNC' and s.name.startswith(want)), None)
        if sym is None:
            sys.exit(f"{row['name']} ({want}...) not found in {row['file']}")
        sec = elf.get_section(sym['st_shndx'])
        code = sec.data()[sym['st_value']:sym['st_value'] + sym['st_size']]
        # map call sites -> called symbol names
        calls = {}
        for rs in elf.iter_sections():
            if isinstance(rs, RelocationSection) and rs.name in ('.rela' + sec.name, '.rel' + sec.name):
                rsym = elf.get_section(rs['sh_link'])
                for rel in rs.iter_relocations():
                    if rel['r_info_type'] in (R_AARCH64_CALL26, R_AARCH64_JUMP26):
                        calls[rel['r_offset']] = rsym.get_symbol(rel['r_info_sym']).name

    prefixes = {itanium_prefix(r['name']): r['name'] for r in load_functions()}

    def pretty(mangled):
        for p, n in prefixes.items():
            if mangled.startswith(p):
                return n
        return mangled

    out = []
    base = sym['st_value']
    for i in md.disasm(code, base):
        if i.mnemonic in ('bl', 'b') and i.address in calls:
            out.append(f'{i.mnemonic} {pretty(calls[i.address])}')
        else:
            out.append(normalize(i, base, base + len(code), lambda t: f'sub_{t:x}'))
    return out


def shape(lines):
    return [re.sub(r'\b([xwsqdv])\d+\b', r'\1R', l) for l in lines]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    row = find_function(args[0])
    game = game_listing(row)
    if '--asm' in sys.argv:
        print('\n'.join(game))
        return
    ours = compile_listing(row)
    ratio = lambda a, b: difflib.SequenceMatcher(None, a, b).ratio() * 100
    common = sum((collections.Counter(shape(game)) & collections.Counter(shape(ours))).values())
    match = game == ours
    print(f"{row['name']} @ {row['address']:#x}: game {len(game)} instrs, yours {len(ours)}")
    print(f"  exact {ratio(game, ours):5.1f}%   shape {ratio(shape(game), shape(ours)):5.1f}%   "
          f"same {common}/{len(game)}" + ('   *** MATCHING ***' if match else ''))
    if '--diff' in sys.argv:
        for line in difflib.unified_diff(game, ours, 'game', 'yours', lineterm='', n=2):
            print(line)


if __name__ == '__main__':
    main()
