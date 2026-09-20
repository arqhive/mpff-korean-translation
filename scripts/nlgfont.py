"""
NLG 비트맵 폰트: 정의 텍스트 + 3DS 텍스처 페이지.

폰트 정의는 평문이다.
    NLG Font Description File
    Version 1.1
    Font "<이름>" <pt> color <r> <g> <b>
    PageSize <px> PageCount <n> TextType color Distribution english
    Height <h> RenderHeight <rh> Ascent <a> RenderAscent <ra> IL <il>
    CharSpacing <cs> LineHeight <lh>
    Glyph <문자 또는 10진 코드포인트> Width <w> <h> <ox> <oy>
    ...
    Kern <문자> <문자> <값> ...
    END
비ASCII 글리프는 10진 유니코드 코드포인트로 적는다.

페이지 텍스처는 3DS 표준 배치다. 8x8 타일을 래스터 순서로 늘어놓고,
타일 안에서는 모턴(Z) 순서. 세로는 위아래가 뒤집혀 있다.
크기로 포맷을 알 수 있다(256px 페이지 기준, 밉 포함):
    43680 = 4bpp 6단계, 87296 = 8bpp 5단계
    10912 = 128px 4bpp, 5376 = 64px 8bpp
"""

import numpy as np

# 8x8 타일 안의 모턴 순서 (인덱스 -> (x, y))
_MORTON = []
for _i in range(64):
    _x = (_i & 1) | ((_i >> 1) & 2) | ((_i >> 2) & 4)
    _y = ((_i >> 1) & 1) | ((_i >> 2) & 2) | ((_i >> 3) & 4)
    _MORTON.append((_x, _y))


def mip_sizes(dim, bpp):
    """밉 체인 각 단계의 바이트 수."""
    out = []
    d = dim
    while d >= 8:
        out.append(d * d * bpp // 8)
        d //= 2
    return out


def guess_format(size, dim):
    """(bpp, 밉단계수) 추정. 맞지 않으면 None."""
    for bpp in (4, 8, 16, 32):
        chain = mip_sizes(dim, bpp)
        for levels in range(1, len(chain) + 1):
            if sum(chain[:levels]) == size:
                return bpp, levels
    return None


def decode_page(data, dim, bpp, flip=True):
    """최상위 밉 한 장을 2차원 uint8 배열로 푼다 (4bpp 는 0..15 를 0..255 로 확장)."""
    img = np.zeros((dim, dim), dtype=np.uint8)
    tiles = dim // 8
    for ty in range(tiles):
        for tx in range(tiles):
            tile_index = ty * tiles + tx
            for i, (px, py) in enumerate(_MORTON):
                n = tile_index * 64 + i
                if bpp == 8:
                    v = data[n]
                elif bpp == 4:
                    b = data[n >> 1]
                    v = (b & 0x0F) if (n & 1) == 0 else (b >> 4)
                    v = v * 17
                else:
                    raise ValueError(f"{bpp}bpp 는 아직 안 된다")
                img[ty * 8 + py, tx * 8 + px] = v
    return img[::-1] if flip else img


def encode_page(img, bpp, flip=True):
    """2차원 uint8 배열 -> 최상위 밉 바이트열. decode_page 의 역."""
    dim = img.shape[0]
    assert img.shape == (dim, dim)
    src = img[::-1] if flip else img
    n_px = dim * dim
    out = bytearray(n_px * bpp // 8)
    tiles = dim // 8
    for ty in range(tiles):
        for tx in range(tiles):
            tile_index = ty * tiles + tx
            for i, (px, py) in enumerate(_MORTON):
                n = tile_index * 64 + i
                v = int(src[ty * 8 + py, tx * 8 + px])
                if bpp == 8:
                    out[n] = v
                elif bpp == 4:
                    q = (v + 8) // 17
                    q = 15 if q > 15 else q
                    if (n & 1) == 0:
                        out[n >> 1] = (out[n >> 1] & 0xF0) | q
                    else:
                        out[n >> 1] = (out[n >> 1] & 0x0F) | (q << 4)
                else:
                    raise ValueError(f"{bpp}bpp 는 아직 안 된다")
    return bytes(out)


def build_mips(img, bpp, levels):
    """최상위 + 밉 체인을 원본과 같은 구성으로 만든다. 밉은 2x2 평균."""
    out = bytearray()
    cur = img
    for lv in range(levels):
        out += encode_page(cur, bpp)
        if lv + 1 < levels:
            h = cur.shape[0] // 2
            cur = (cur.reshape(h, 2, h, 2).astype(np.uint16)
                   .mean(axis=(1, 3)).round().astype(np.uint8))
    return bytes(out)


# --------------------------------------------------------------------------
# 정의 텍스트
# --------------------------------------------------------------------------
def parse_desc(raw):
    """정의 바이트열 -> dict(head, glyphs=[(키,a,b,c,d)], kerns, tail)

    줄바꿈은 CRLF 다. 마지막은 "END\\r\\n" 뒤에 공백 몇 개가 붙는다(원본은 2개).
    tail 에 그 꼬리를 그대로 담아 두어야 바이트 단위로 되돌릴 수 있다.
    """
    text = raw.decode("utf-8", "replace")
    end = text.rfind("END\r\n")
    tail = text[end + 5:] if end >= 0 else ""
    body = text[:end] if end >= 0 else text
    head, glyphs, kerns = [], [], []
    for ln in body.split("\r\n"):
        if ln.startswith("Glyph "):
            parts = ln.split()
            # Glyph <키> Width a b c d   (키가 공백 문자면 "32" 처럼 코드포인트로 적힌다)
            wi = parts.index("Width")
            key = " ".join(parts[1:wi])
            a, b, c, d = (int(x) for x in parts[wi + 1:wi + 5])
            glyphs.append((key, a, b, c, d))
        elif ln.startswith("Kern "):
            kerns.append(ln)
        elif ln:
            head.append(ln)
    return {"head": head, "glyphs": glyphs, "kerns": kerns, "tail": tail}


def render_desc(desc, glyphs=None):
    """parse_desc 결과 -> 정의 바이트열. glyphs 를 주면 글리프 목록만 갈아끼운다."""
    lines = list(desc["head"])
    for key, a, b, c, d in (desc["glyphs"] if glyphs is None else glyphs):
        lines.append(f"Glyph {key} Width {a} {b} {c} {d}")
    lines.extend(desc["kerns"])
    lines.append("END")
    return ("\r\n".join(lines) + "\r\n" + desc["tail"]).encode("utf-8")


def glyph_char(key):
    """정의의 글리프 키 -> 실제 문자. 10진 코드포인트면 변환한다."""
    if len(key) == 1 and not key.isdigit():
        return key
    if key.isdigit():
        return chr(int(key))
    return key
