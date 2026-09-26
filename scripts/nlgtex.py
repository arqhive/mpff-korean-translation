# -*- coding: utf-8 -*-
"""NLG pak(.data/.jp) 안 텍스처 추출 라이브러리.

찾아낸 규칙
-----------
1. `<name>.dict` 의 청크 엔트리(16바이트 {fileOffset, rawSize, compSize, flags})에서
   flags 바이트2 == 확장자 인덱스. `.data` 엔트리들이 그 파일의 청크(섹션) 목록이다.
   compSize == 0 이면 무압축.
2. 텍스처 기술자(태그 0xE977D350, 56바이트)는 **섹션 0 맨 앞**에 연속으로 놓인다.
3. 픽셀 데이터는 **마지막 섹션의 맨 앞(오프셋 0)** 부터, **기술자 순서대로**,
   각 텍스처의 밉 체인 전체(size 바이트)를 **패딩 없이** 이어 붙인다.
       dataOff(i) = lastSectionStart + sum(size[0..i-1])
4. 기술자 필드: +0x08 size(밉 체인 전체), +0x18 w|h<<16, +0x1c 상위바이트=밉 개수,
   +0x34 PICA 포맷 코드.
"""
import os
import struct
import zlib

import numpy as np

TEX_TAG = 0xE977D350
TEX_STRIDE = 0x38
DICT_MAGIC = 0xA9F32458

# PICA200 텍스처 포맷 -> 픽셀당 비트
BPP = {0: 32, 1: 24, 2: 16, 3: 16, 4: 16, 5: 16, 6: 16, 7: 8, 8: 8,
       9: 8, 10: 4, 11: 4, 12: 4, 13: 8}
FMT_NAME = {0: 'RGBA8', 1: 'RGB8', 2: 'RGBA5551', 3: 'RGB565', 4: 'RGBA4',
            5: 'LA8', 6: 'HILO8', 7: 'L8', 8: 'A8', 9: 'LA4', 10: 'L4',
            11: 'A4', 12: 'ETC1', 13: 'ETC1A4'}


# ---------------------------------------------------------------- dict
def dict_chunks(dict_path):
    """.dict -> {확장자: [(fileOffset, rawSize, compSize, flags), ...]}"""
    d = open(dict_path, 'rb').read()
    if struct.unpack_from('<I', d, 0)[0] != DICT_MAGIC:
        raise ValueError('dict 매직 불일치: ' + dict_path)
    tbl_end = None
    for off in range(0x10, len(d) - 1, 16):
        if d[off:off + 1] == b'.' and b'\x00' in d[off:]:
            tbl_end = off
            break
    if tbl_end is None:
        raise ValueError('확장자 문자열 영역 없음')
    exts = [x.decode() for x in d[tbl_end:].split(b'\x00') if x]

    def ok(off):
        _o, _r, _c, fl = struct.unpack_from('<4I', d, off)
        return (((fl >> 16) & 0xFF) < len(exts) and ((fl >> 8) & 0xFF) == 0
                and (fl >> 24) <= 1 and (fl & 0xFF) in (0, 2, 4, 8, 0x10,
                                                        0x20, 0x40, 0x80))

    start = tbl_end
    while start - 16 >= 0x10 and ok(start - 16):
        start -= 16
    res = {e: [] for e in exts}
    for off in range(start, tbl_end, 16):
        o, r, c, fl = struct.unpack_from('<4I', d, off)
        res[exts[(fl >> 16) & 0xFF]].append((o, r, c, fl))
    return res


def sections_of(pak_path):
    """pak 경로 -> [(섹션 블롭, 파일내 시작오프셋)] (압축이면 시작오프셋은 None)"""
    raw = open(pak_path, 'rb').read()
    base, ext = os.path.splitext(pak_path)
    dpath = base + '.dict'
    if os.path.exists(dpath):
        try:
            chunks = dict_chunks(dpath).get(ext, [])
        except Exception:
            chunks = []
        if chunks:
            out = []
            for o, r, c, fl in chunks:
                if c:                                  # 압축 청크
                    out.append((zlib.decompress(raw[o:o + c]), None))
                else:
                    out.append((raw[o:o + r], o))
            return out
    # dict 를 못 쓰면 zlib 경계로 자른다
    if raw[:1] == b'\x78':
        secs, pos = [], 0
        while pos < len(raw):
            ob = zlib.decompressobj()
            blob = ob.decompress(raw[pos:])
            used = len(raw) - pos - len(ob.unused_data)
            secs.append((blob, None))
            pos = (pos + used + 7) & ~7
        return secs
    return [(raw, 0)]


# ---------------------------------------------------------------- 기술자
def descriptors(sec0):
    """섹션0 맨 앞의 텍스처 기술자들. 태그가 0x38 간격으로 이어지는 동안만 읽는다."""
    out = []
    off = 0
    while off + TEX_STRIDE <= len(sec0):
        if struct.unpack_from('<I', sec0, off)[0] != TEX_TAG:
            break
        f = struct.unpack_from('<14I', sec0, off)
        wh = f[6]
        out.append(dict(index=len(out), off=off, pid=f[1], size=f[2],
                        w=wh & 0xFFFF, h=wh >> 16,
                        mips=(f[7] >> 24) & 0xF, fmt=f[13]))
        off += TEX_STRIDE
    return out


def index_offsets(sec0, ds):
    """섹션0 이 리소스 인덱스(12바이트 레코드)면 텍스처 데이터 오프셋을 거기서 읽는다.

    `.jp` 처럼 인덱스를 가진 pak 은 텍스처 데이터가 0x100 정렬로 놓여 있어서
    누적합만으로는 맞지 않는다. 인덱스가 없는 `.data` 는 빈틈없이 이어 붙인다.
    """
    if len(sec0) % 12 or len(sec0) < 12 * len(ds):
        return None
    sizes = [d['size'] for d in ds]
    groups = {}
    for i in range(len(sec0) // 12):
        tag, size, off = struct.unpack_from('<III', sec0, i * 12)
        if (tag & 0xFFFFFF) == 0x01B502:
            groups.setdefault(tag, []).append((size, off))
    # 태그 상위 니블이 "어느 컨테이너의 몇 번 섹션"인지를 가른다.
    # 기술자 크기 목록과 그대로 일치하는 그룹이 이 pak 의 텍스처다.
    for tag, hits in groups.items():
        if [s for s, _ in hits] == sizes:
            return [o for _, o in hits]
    return None


def layout(pak_path):
    """pak -> (마지막 섹션 블롭, [기술자(dataOff 포함)])

    기술자는 **어느 섹션이든 그 맨 앞(offset 0)** 에 놓인다.
    `.data`(무압축, 섹션 3개)는 섹션 0, `.jp`(압축, 섹션 4개)는 섹션 0 이
    리소스 인덱스라서 섹션 1 이 기술자 자리다.
    """
    secs = sections_of(pak_path)
    ds = []
    for blob, _ in secs[:-1]:
        ds = descriptors(blob)
        if ds:
            break
    if not ds:
        return None, []
    blob = secs[-1][0]
    idx = index_offsets(secs[0][0], ds)
    o = 0
    for i, d in enumerate(ds):
        d['dataOff'] = idx[i] if idx else o
        d['fileOff'] = None if secs[-1][1] is None else secs[-1][1] + d['dataOff']
        o += d['size']
    if o > len(blob):
        raise ValueError('텍스처 합계 %d > 마지막 섹션 %d (%s)'
                         % (o, len(blob), pak_path))
    return blob, ds


# ---------------------------------------------------------------- 디코더
_ETC_TBL = np.array([[2, 8, -2, -8], [5, 17, -5, -17], [9, 29, -9, -29],
                     [13, 42, -13, -42], [18, 60, -18, -60],
                     [24, 80, -24, -80], [33, 106, -33, -106],
                     [47, 183, -47, -183]], dtype=np.int16)
_SUB = ((0, 0), (4, 0), (0, 4), (4, 4))      # 8x8 타일 안 4x4 블록(모턴)


def _morton8():
    """8x8 타일 안 모턴 순서 -> (x, y) 64개"""
    out = []
    for i in range(64):
        x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
        y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
        out.append((x, y))
    return out


_M8 = _morton8()


def _s3(v):
    return v - 8 if v >= 4 else v


def _etc1_block(blk):
    c = blk >> 32
    px = blk & 0xFFFFFFFF
    flip = c & 1
    if (c >> 1) & 1:
        r1, g1, b1 = (c >> 27) & 0x1F, (c >> 19) & 0x1F, (c >> 11) & 0x1F
        base = [[r1 << 3 | r1 >> 2, g1 << 3 | g1 >> 2, b1 << 3 | b1 >> 2]]
        r2 = max(0, min(31, r1 + _s3((c >> 24) & 7)))
        g2 = max(0, min(31, g1 + _s3((c >> 16) & 7)))
        b2 = max(0, min(31, b1 + _s3((c >> 8) & 7)))
        base.append([r2 << 3 | r2 >> 2, g2 << 3 | g2 >> 2, b2 << 3 | b2 >> 2])
    else:
        n = [(c >> 28) & 0xF, (c >> 24) & 0xF, (c >> 20) & 0xF,
             (c >> 16) & 0xF, (c >> 12) & 0xF, (c >> 8) & 0xF]
        base = [[n[0] * 17, n[2] * 17, n[4] * 17],
                [n[1] * 17, n[3] * 17, n[5] * 17]]
    cw = ((c >> 5) & 7, (c >> 2) & 7)
    out = np.zeros((4, 4, 3), dtype=np.int16)
    for i in range(16):
        x, y = i >> 2, i & 3
        half = (y >= 2) if flip else (x >= 2)
        idx = ((px >> (16 + i)) & 1) << 1 | ((px >> i) & 1)
        out[y, x] = (np.array(base[1 if half else 0], dtype=np.int16)
                     + _ETC_TBL[cw[1 if half else 0]][idx])
    return np.clip(out, 0, 255).astype(np.uint8)


def decode_etc1(data, w, h, alpha):
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[..., 3] = 255
    step = 16 if alpha else 8
    p = 0
    for ty in range(max(h // 8, 1)):
        for tx in range(max(w // 8, 1)):
            for sx, sy in _SUB:
                if p + step > len(data):
                    return img
                if alpha:
                    a8 = data[p:p + 8]
                    blk = int.from_bytes(data[p + 8:p + 16], 'little')
                else:
                    a8 = None
                    blk = int.from_bytes(data[p:p + 8], 'little')
                p += step
                y0, x0 = ty * 8 + sy, tx * 8 + sx
                if y0 + 4 > h or x0 + 4 > w:
                    continue
                img[y0:y0 + 4, x0:x0 + 4, :3] = _etc1_block(blk)
                if a8 is not None:
                    a = np.zeros((4, 4), dtype=np.uint8)
                    for i in range(16):
                        x, y = i >> 2, i & 3
                        a[y, x] = ((a8[i >> 1] >> ((i & 1) * 4)) & 0xF) * 17
                    img[y0:y0 + 4, x0:x0 + 4, 3] = a
    return img


def _px_linear(data, fmt, n):
    """선형 포맷 n픽셀 -> (n,4) uint8 (저장 순서 그대로)"""
    b = np.frombuffer(data, dtype=np.uint8)
    out = np.zeros((n, 4), dtype=np.uint8)
    out[:, 3] = 255
    if fmt == 0:                                    # RGBA8 (저장: A,B,G,R)
        v = b[:n * 4].reshape(n, 4)
        out[:, 0], out[:, 1], out[:, 2], out[:, 3] = v[:, 3], v[:, 2], v[:, 1], v[:, 0]
    elif fmt == 1:                                  # RGB8 (저장: B,G,R)
        v = b[:n * 3].reshape(n, 3)
        out[:, 0], out[:, 1], out[:, 2] = v[:, 2], v[:, 1], v[:, 0]
    elif fmt in (2, 3, 4):
        u = b[:n * 2].view('<u2')
        if fmt == 3:                                # RGB565
            out[:, 0] = ((u >> 11) & 0x1F) * 255 // 31
            out[:, 1] = ((u >> 5) & 0x3F) * 255 // 63
            out[:, 2] = (u & 0x1F) * 255 // 31
        elif fmt == 2:                              # RGBA5551
            out[:, 0] = ((u >> 11) & 0x1F) * 255 // 31
            out[:, 1] = ((u >> 6) & 0x1F) * 255 // 31
            out[:, 2] = ((u >> 1) & 0x1F) * 255 // 31
            out[:, 3] = (u & 1) * 255
        else:                                       # RGBA4
            out[:, 0] = ((u >> 12) & 0xF) * 17
            out[:, 1] = ((u >> 8) & 0xF) * 17
            out[:, 2] = ((u >> 4) & 0xF) * 17
            out[:, 3] = (u & 0xF) * 17
    elif fmt == 5:                                  # LA8
        v = b[:n * 2].reshape(n, 2)
        out[:, 0] = out[:, 1] = out[:, 2] = v[:, 1]
        out[:, 3] = v[:, 0]
    elif fmt == 6:                                  # HILO8
        v = b[:n * 2].reshape(n, 2)
        out[:, 0], out[:, 1] = v[:, 1], v[:, 0]
    elif fmt == 7:                                  # L8
        out[:, 0] = out[:, 1] = out[:, 2] = b[:n]
    elif fmt == 8:                                  # A8
        out[:, 0] = out[:, 1] = out[:, 2] = 255
        out[:, 3] = b[:n]
    elif fmt == 9:                                  # LA4
        v = b[:n]
        out[:, 0] = out[:, 1] = out[:, 2] = (v >> 4) * 17
        out[:, 3] = (v & 0xF) * 17
    elif fmt in (10, 11):
        v = b[:(n + 1) // 2]
        nib = np.empty(len(v) * 2, dtype=np.uint8)
        nib[0::2] = v & 0xF
        nib[1::2] = v >> 4
        nib = nib[:n] * 17
        if fmt == 10:
            out[:, 0] = out[:, 1] = out[:, 2] = nib
        else:
            out[:, 0] = out[:, 1] = out[:, 2] = 255
            out[:, 3] = nib
    else:
        raise ValueError('포맷 %d 미지원' % fmt)
    return out


def decode_linear(data, w, h, fmt):
    n = w * h
    px = _px_linear(data, fmt, n)
    img = np.zeros((h, w, 4), dtype=np.uint8)
    k = 0
    for ty in range(max(h // 8, 1)):
        for tx in range(max(w // 8, 1)):
            for mx, my in _M8:
                y, x = ty * 8 + my, tx * 8 + mx
                if y < h and x < w:
                    img[y, x] = px[k]
                k += 1
    return img


def decode(data, w, h, fmt, flip=True):
    if fmt == 12:
        img = decode_etc1(data, w, h, False)
    elif fmt == 13:
        img = decode_etc1(data, w, h, True)
    else:
        img = decode_linear(data, w, h, fmt)
    return img[::-1] if flip else img


def mip_slices(d):
    """기술자 -> [(오프셋, 길이, w, h), ...] 밉 체인"""
    out = []
    o, w, h = 0, d['w'], d['h']
    for _ in range(max(d['mips'], 1)):
        n = max(w, 1) * max(h, 1) * BPP[d['fmt']] // 8
        if o + n > d['size']:
            break
        out.append((o, n, max(w, 1), max(h, 1)))
        o += n
        w, h = max(w // 2, 1), max(h // 2, 1)
    return out


# ---------------------------------------------------------------- 인코더

def _sub_halves(flip):
    """(서브블록 0, 1) 각각의 (y, x) 목록. 디코더의 half 판정과 순서를 그대로 맞춘다.

    디코더는 픽셀 i 를 (x=i>>2, y=i&3) 으로 놓고 flip 이면 y>=2, 아니면 x>=2 를
    두 번째 서브블록으로 본다. 서브블록 안 픽셀 순서는 numpy 로 자른 뒤 편 순서와 같다.
    """
    if flip:
        return ([(y, x) for y in range(2) for x in range(4)],
                [(y, x) for y in range(2, 4) for x in range(4)])
    return ([(y, x) for y in range(4) for x in range(2)],
            [(y, x) for y in range(4) for x in range(2, 4)])


def _best_sub(px, wt, diff):
    """서브블록 하나: (오차, 양자화색, 테이블, 픽셀별 수정자 인덱스)"""
    tot = wt.sum()
    avg = (px * wt[:, None]).sum(0) / tot if tot else px.mean(0)
    scale = 31 if diff else 15
    q0 = np.clip(np.rint(avg * scale / 255), 0, scale).astype(int)
    best = None
    for dr in (-1, 0, 1):                      # 평균 양자화 주변까지 조금 넓게 본다
        for dg in (-1, 0, 1):
            for db in (-1, 0, 1):
                q = np.clip(q0 + (dr, dg, db), 0, scale)
                base = (q << 3 | q >> 2) if diff else (q * 17)
                v = np.clip(base[None, :] + _ETC_TBL[:, :, None], 0, 255)      # (8,4,3)
                err = (((px[:, None, None, :] - v[None]) ** 2).sum(3)
                       * wt[:, None, None])                                    # (n,8,4)
                idx = err.argmin(2)
                e = np.take_along_axis(err, idx[..., None], 2)[..., 0].sum(0)  # (8,)
                cw = int(e.argmin())
                if best is None or e[cw] < best[0]:
                    best = (float(e[cw]), q, cw, idx[:, cw])
    return best


def _etc1_encode_block(rgb, alpha):
    """(4,4,3) + (4,4) 알파 -> ETC1 블록 8바이트 정수.

    flip 2가지 × individual/differential 2가지를 모두 시도해 가장 오차가 작은 것을 쓴다.
    알파 0 인 픽셀은 화면에 안 보이므로 오차 계산에서 가볍게 친다.
    """
    rgb = rgb.astype(np.float64)
    w = (alpha.astype(np.float64) / 255.0) * 0.99 + 0.01
    best = None
    for flip in (0, 1):
        halves = _sub_halves(flip)
        for diff in (0, 1):
            subs = []
            for pts in halves:
                px = np.array([rgb[y, x] for y, x in pts])
                wt = np.array([w[y, x] for y, x in pts])
                subs.append(_best_sub(px, wt, diff))
            if diff:                            # 두 base 차이가 -4..3 안에 들어와야 한다
                d = subs[1][1] - subs[0][1]
                if np.any(d < -4) or np.any(d > 3):
                    continue
            tot = subs[0][0] + subs[1][0]
            if best is None or tot < best[0]:
                best = (tot, flip, diff, subs)
    _e, flip, diff, subs = best
    c = flip | (diff << 1) | (subs[1][2] << 2) | (subs[0][2] << 5)
    q1, q2 = subs[0][1], subs[1][1]
    if diff:
        d = q2 - q1
        for k, (sh_b, sh_d) in enumerate(((27, 24), (19, 16), (11, 8))):
            c |= int(q1[k]) << sh_b | (int(d[k]) & 7) << sh_d
    else:
        for k, (sh1, sh2) in enumerate(((28, 24), (20, 16), (12, 8))):
            c |= int(q1[k]) << sh1 | int(q2[k]) << sh2
    pos = {}
    for hi, pts in enumerate(_sub_halves(flip)):
        for k, yx in enumerate(pts):
            pos[yx] = (hi, k)
    px = 0
    for i in range(16):
        x, y = i >> 2, i & 3
        hi, k = pos[(y, x)]
        m = int(subs[hi][3][k])
        px |= (m & 1) << i
        px |= ((m >> 1) & 1) << (16 + i)
    return (c << 32) | px


def encode_etc1a4(img, flip=True):
    """(h,w,4) uint8 -> ETC1A4 바이트열. 8x8 타일 래스터, 타일 안 4x4 블록 모턴."""
    a = np.asarray(img, dtype=np.uint8)
    if flip:
        a = a[::-1]
    h, w = a.shape[:2]
    out = bytearray()
    for ty in range(h // 8):
        for tx in range(w // 8):
            for sx, sy in _SUB:
                blk = a[ty * 8 + sy:ty * 8 + sy + 4, tx * 8 + sx:tx * 8 + sx + 4]
                al = bytearray(8)
                for i in range(16):
                    x, y = i >> 2, i & 3
                    al[i >> 1] |= (int(blk[y, x, 3]) >> 4) << ((i & 1) * 4)
                out += al
                out += _etc1_encode_block(blk[..., :3], blk[..., 3]).to_bytes(8, 'little')
    return bytes(out)
