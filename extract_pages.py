#!/usr/bin/env python3
"""
extract_pages.py — pull embedded page images out of a base64-encoded HTML viewer
and save them as pages/001.jpg, pages/002.jpg … ready for masterbook_local.html.

Usage:
    python3 extract_pages.py                     # looks for old_masterbook.html
    python3 extract_pages.py my_old_viewer.html  # specify a different source file
    python3 extract_pages.py source.html --out img --ext png  # custom folder/ext
"""

import re
import base64
import os
import sys


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Extract base64 page images from HTML viewer')
    ap.add_argument('source', nargs='?', default='old_masterbook.html',
                    help='Source HTML file with embedded base64 images (default: old_masterbook.html)')
    ap.add_argument('--out', default='pages', help='Output folder (default: pages)')
    ap.add_argument('--ext', default='jpg', help='Output file extension (default: jpg)')
    ap.add_argument('--pad', type=int, default=3,
                    help='Zero-padding for filenames: 3 → 001, 4 → 0001 (default: 3)')
    args = ap.parse_args()

    if not os.path.isfile(args.source):
        print(f'ERROR: source file not found: {args.source}')
        print('Pass the path to your old base64-embedded HTML as the first argument.')
        sys.exit(1)

    print(f'Reading {args.source} …')
    with open(args.source, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match all base64 data URLs (JPEG or PNG)
    pattern = re.compile(r'data:image/(?:jpeg|png|jpg);base64,([A-Za-z0-9+/=]+)')
    matches = pattern.findall(content)

    if not matches:
        print('No embedded base64 images found in the source file.')
        sys.exit(1)

    # Deduplicate while preserving order (thumbnails and main images are often
    # the same data stored twice — keep unique ones only)
    seen = {}
    unique = []
    for m in matches:
        key = m[:64]  # first 64 chars is a good fingerprint
        if key not in seen:
            seen[key] = True
            unique.append(m)

    print(f'Found {len(matches)} data URLs → {len(unique)} unique images')

    os.makedirs(args.out, exist_ok=True)

    for i, b64 in enumerate(unique, 1):
        filename = os.path.join(args.out, str(i).zfill(args.pad) + '.' + args.ext)
        try:
            data = base64.b64decode(b64)
        except Exception as e:
            print(f'  [SKIP] image {i}: decode error — {e}')
            continue
        with open(filename, 'wb') as f:
            f.write(data)
        print(f'  {filename}  ({len(data) // 1024} KB)')

    print(f'\nDone! {len(unique)} images saved to ./{args.out}/')
    print(f'\nIn masterbook_local.html, set:')
    print(f'  folder : \'{args.out}\',')
    print(f'  ext    : \'{args.ext}\',')
    print(f'  pages  : {len(unique)},')
    print(f'  pad    : {args.pad},')


if __name__ == '__main__':
    main()
