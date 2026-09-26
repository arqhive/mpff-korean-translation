# -*- coding: utf-8 -*-
"""pak 경로를 주면 그 안 텍스처를 전부 PNG 로 뽑는다.

사용법:
    python scripts/extract_tex.py <pak경로> [...]        -> out/tex/<pak이름>/
    python scripts/extract_tex.py --list <pak경로>       -> 목록만
    python scripts/extract_tex.py --mips <pak경로>       -> 밉맵까지 저장
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nlgtex as T
from PIL import Image

OUTROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'out', 'tex')


def extract(path, outdir=None, mips=False, listonly=False, flip=True):
    blob, ds = T.layout(path)
    if not ds:
        print('%s: 텍스처 없음' % path)
        return []
    # 같은 이름의 pak 이 폴더마다 있으므로(예: 여러 곳의 Persistent.data)
    # 상위 폴더 이름까지 붙여 출력 폴더를 가른다.
    ap = os.path.abspath(path).replace('\\', '/').split('/')
    if 'romfs' in ap:
        name = '_'.join(ap[ap.index('romfs') + 1:]).replace('.', '_')
    else:
        name = os.path.basename(path).replace('.', '_')
    outdir = outdir or os.path.join(OUTROOT, name)
    if not listonly:
        os.makedirs(outdir, exist_ok=True)
    written = []
    for d in ds:
        fmt = d['fmt']
        tag = '%02d_%08x_%dx%d_%s' % (d['index'], d['pid'], d['w'], d['h'],
                                      T.FMT_NAME.get(fmt, 'fmt%d' % fmt))
        if listonly:
            print('  %s  size=%d dataOff=0x%x fileOff=%s mips=%d'
                  % (tag, d['size'], d['dataOff'],
                     None if d['fileOff'] is None else hex(d['fileOff']), d['mips']))
            continue
        if fmt not in T.BPP:
            print('  %s: 포맷 미지원' % tag)
            continue
        chain = T.mip_slices(d)
        for mi, (mo, mn, mw, mh) in enumerate(chain):
            if mi and not mips:
                break
            data = blob[d['dataOff'] + mo: d['dataOff'] + mo + mn]
            img = T.decode(data, mw, mh, fmt, flip=flip)
            fn = os.path.join(outdir, tag + ('' if mi == 0 else '_mip%d' % mi) + '.png')
            Image.fromarray(img, 'RGBA').save(fn)
            written.append(fn)
    return written


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = set(a for a in sys.argv[1:] if a.startswith('--'))
    for p in args:
        if '--list' in flags:
            print(p)
        w = extract(p, mips='--mips' in flags, listonly='--list' in flags,
                    flip='--noflip' not in flags)
        if w:
            print('%s -> %d개 PNG (%s)' % (p, len(w), os.path.dirname(w[0])))


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()
