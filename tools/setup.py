#!/usr/bin/env python3
"""One-time setup: decompress data/main into build/main.bin and check it's v1.2.0.

    python tools/setup.py
"""
import os
import sys

from common import BUILD, BUILD_ID, DATA, IMAGE_PATH, decompress_nso


def main():
    src = os.path.join(DATA, 'main')
    if not os.path.exists(src):
        sys.exit('Put your dumped ExeFS "main" at data/main first.')
    img, build_id = decompress_nso(src)
    if build_id != BUILD_ID:
        sys.exit(f'Build ID {build_id} is not v1.2.0 ({BUILD_ID}). Install the 1.2.0 update and re-dump.')
    os.makedirs(BUILD, exist_ok=True)
    with open(IMAGE_PATH, 'wb') as f:
        f.write(img)
    print(f'OK: v1.2.0 build {build_id}, {len(img):#x} bytes -> build/main.bin')


if __name__ == '__main__':
    main()
