"""HOME 메뉴용 배너/아이콘을 한글판으로 바꾸고 ExeFS 를 다시 만든다.

  * banner(CBMD) 안의 LZ11 압축 CGFX 에서 COMMON6(256x16) 띠를 한글로 교체.
    나머지 텍스처(METROID PRIME / FEDERATION FORCE 로고, 엠블럼)는 원래 영문이라 그대로 둔다.
  * icon(SMDH)의 제목을 12개 언어 칸 전부 한국어로. 시스템 언어와 무관하게 한글로 보이게 한다.
  * ExeFS 는 헤더의 오프셋/크기/SHA-256 을 다시 계산해 통째로 새로 쓴다.
    .code 는 ExeFS 안에서 압축돼 있으므로 원본 블롭을 그대로 옮긴다.
"""
import hashlib
import io
import os
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import lz11

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRIP = os.path.join(ROOT, "out", "banner", "COMMON6_ko_up.png")

SHORT = "페더레이션 포스"
LONG = "메트로이드 프라임\n페더레이션 포스"
PUBLISHER = "Nintendo"

# COMMON6 의 CGFX 안 위치 (TXOB 헤더에서 읽어 확인한다)
COMMON6_TXOB = 0x3924

_MORTON = []
for _i in range(64):
    _MORTON.append(((_i & 1) | ((_i >> 1) & 2) | ((_i >> 2) & 4),
                    ((_i >> 1) & 1) | ((_i >> 2) & 2) | ((_i >> 3) & 4)))


def encode_rgba8(img, w, h):
    """8x8 모턴 타일 RGBA8(바이트 순서 A,B,G,R)로 인코딩. 입력은 똑바로 선 그림.

    배너 CGFX 의 텍스처는 **세로로 뒤집혀 있지 않다**. 폰트 아틀라스(nlgfont)는
    뒤집혀 있어서 그쪽 관례를 그대로 옮겼다가, 배너 글자가 실기에서 거꾸로 나왔다.
    인코더가 디코더의 역함수이기만 하면 왕복 검사는 통과하므로 이 실수는 왕복으로
    잡히지 않는다 — 원본을 뒤집지 않고 디코딩해 글자가 똑바로 서는지 눈으로 봐야 한다.
    """
    a = np.array(img.convert("RGBA"), dtype=np.uint8)
    assert a.shape[:2] == (h, w), f"{a.shape} != {(h, w)}"
    out = bytearray()
    for ty in range(h // 8):
        for tx in range(w // 8):
            for px, py in _MORTON:
                r, g, b, al = a[ty * 8 + py, tx * 8 + px]
                out += bytes((al, b, g, r))
    return bytes(out)


def patch_banner(banner):
    cwav_off = struct.unpack_from("<I", banner, 0x84)[0]
    cgfx = bytearray(lz11.decompress(banner[0x88:cwav_off]))

    W = struct.unpack_from("<20I", cgfx, COMMON6_TXOB)
    h, w, size = W[6], W[7], W[17]
    data_off = COMMON6_TXOB + 18 * 4 + W[18]
    assert (w, h, size) == (256, 16, 0x4000), f"COMMON6 가 아니다: {w}x{h} {size}"

    blob = encode_rgba8(Image.open(STRIP), w, h)
    assert len(blob) == size, f"{len(blob)} != {size}"
    cgfx[data_off:data_off + size] = blob
    print(f"  COMMON6 {w}x{h} 교체 @ {hex(data_off)}")

    comp = lz11.compress(bytes(cgfx))
    assert lz11.decompress(comp) == bytes(cgfx), "LZ11 왕복 실패"

    new_cwav = (0x88 + len(comp) + 0x1F) & ~0x1F
    out = bytearray(banner[:0x88])
    struct.pack_into("<I", out, 0x84, new_cwav)
    out += comp
    out += b"\0" * (new_cwav - len(out))
    out += banner[cwav_off:]
    print(f"  CGFX {len(banner[0x88:cwav_off]):,} -> {len(comp):,} 바이트, "
          f"CWAV {hex(cwav_off)} -> {hex(new_cwav)}")
    return bytes(out)


def patch_smdh(icon):
    out = bytearray(icon)
    assert out[:4] == b"SMDH"

    def put(off, text, chars):
        raw = text.encode("utf-16-le")
        assert len(raw) < chars * 2, f"제목이 너무 길다: {text!r}"
        out[off:off + chars * 2] = raw + b"\0" * (chars * 2 - len(raw))

    for i in range(12):                      # 실제로 쓰이는 12개 언어 칸
        base = 8 + i * 0x200
        put(base, SHORT, 0x40)
        put(base + 0x80, LONG, 0x80)
        put(base + 0x180, PUBLISHER, 0x40)
    flat = LONG.replace("\n", " ")
    print(f"  SMDH 제목 12개 언어 칸에 {SHORT!r} / {flat!r} 기록")
    return bytes(out)


def read_exefs(d):
    """ExeFS 블롭 -> {이름: 내용}"""
    out = {}
    for i in range(10):
        name, off, size = struct.unpack_from("<8sII", d, i * 16)
        if not size:
            continue
        out[name.rstrip(b"\0").decode()] = d[0x200 + off:0x200 + off + size]
    return out


def rebuild_exefs(path, patches):
    d = open(path, "rb").read()
    entries = []
    for i in range(10):
        name, off, size = struct.unpack_from("<8sII", d, i * 16)
        if not size:
            continue
        key = name.rstrip(b"\0").decode()
        body = patches.get(key, d[0x200 + off:0x200 + off + size])
        entries.append((name, key, body))

    hdr = bytearray(0x200)
    blob = bytearray()
    for i, (name, key, body) in enumerate(entries):
        off = len(blob)
        struct.pack_into("<8sII", hdr, i * 16, name, off, len(body))
        hdr[0x200 - (i + 1) * 32:0x200 - i * 32] = hashlib.sha256(body).digest()
        blob += body
        while len(blob) % 0x200:
            blob.append(0)
        print(f"  [{i}] {key:10s} off={off:#x} size={len(body):,}")
    return bytes(hdr) + bytes(blob)


def patch_exefs_file(exefs_path):
    """ExeFS 파일을 제자리에서 한글판으로 바꾼다. 원본 배너/아이콘은 그 안에서 읽는다.

    업데이트 타이틀의 ExeFS 에는 banner 가 없고 icon 만 있다. 그 경우 아이콘만 바꾼다.
    업데이트가 설치돼 있으면 HOME 메뉴 제목은 업데이트의 SMDH 를 따라가므로
    본편만 고치면 제목이 일본어로 남는다.
    """
    src = read_exefs(open(exefs_path, "rb").read())
    patches = {}

    if "banner" in src:
        if not os.path.exists(STRIP):
            print("배너 띠 이미지가 없어 먼저 만든다")
            import make_banner_strip
            make_banner_strip.main()
        print("배너 패치")
        patches["banner"] = patch_banner(src["banner"])
    else:
        print("배너 없음 (업데이트 타이틀) — 아이콘만 바꾼다")

    print("아이콘(SMDH) 패치")
    patches["icon"] = patch_smdh(src["icon"])

    print("ExeFS 재구성")
    out = rebuild_exefs(exefs_path, patches)
    open(exefs_path, "wb").write(out)
    print(f"완료: {exefs_path} {len(out):,} 바이트")


def main():
    patch_exefs_file(sys.argv[1])


if __name__ == "__main__":
    main()
