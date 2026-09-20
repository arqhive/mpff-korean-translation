"""ETC1A4 텍스처의 알파 평면을 뽑는다.

아틀라스 0~2페이지(87,296바이트 / 5,376바이트)가 이 포맷이다. 처음에는 크기만 보고
IA4(인텐시티+알파) 8bpp 로 잘못 봤는데, 니블을 어떻게 나눠도 화면이 체커보드처럼
깨져서 ETC1A4 임을 알아냈다.

구조: 8x8 타일을 4x4 블록 4개로 나누고(모턴 순서), 블록마다
      알파 4bpp 8바이트 + ETC1 색 8바이트. 블록 안은 열 우선.

폰트 아틀라스는 글리프 모양이 알파에만 들어 있어서, 알파 평면만 뽑으면 글자가
그대로 보인다. ETC1 색을 다시 인코딩하는 것은 만들지 않았다 — 그래서 빌더는
이 페이지들을 건드리지 않고 고정한다(docs/FORMAT.md 참고).

  python etc1a4.py <init.jp> <페이지번호> <저장할.png>
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 8x8 타일 안 4x4 블록의 좌상단 좌표 (모턴 순서)
SUB = [(0, 0), (4, 0), (0, 4), (4, 4)]


def alpha_plane(blob, dim, flip=True):
    """ETC1A4 블롭 -> 알파 평면 (0..255 로 확장한 2차원 uint8)"""
    img = np.zeros((dim, dim), np.uint8)
    p = 0
    for ty in range(dim // 8):
        for tx in range(dim // 8):
            for bx, by in SUB:
                a = blob[p:p + 8]
                p += 16                     # 알파 8바이트 + ETC1 색 8바이트
                for k in range(16):
                    px, py = k // 4, k % 4  # 블록 안은 열 우선
                    v = a[k >> 1] & 0x0F if (k & 1) == 0 else a[k >> 1] >> 4
                    img[ty * 8 + by + py, tx * 8 + bx + px] = v * 17
    return img[::-1] if flip else img


def main():
    from PIL import Image
    import fontlib as FL
    import nlgpak as N

    pak, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    font = FL.MainFont(pak)
    dim, bpp, _lv = font.page_fmt[page]
    if bpp == 4:
        raise SystemExit(f"{page}페이지는 4bpp 다. 이 도구는 ETC1A4 전용이다.")
    recs = [(i, s, o) for i, (t, s, o) in enumerate(font.recs)
            if t == N.FONTPAGE_TAG]
    _i, size, off = recs[font.page_res[page]]
    top = dim * dim                         # 최상위 밉의 바이트 수 (8bpp)
    Image.fromarray(alpha_plane(font.secs[3][off:off + top], dim)).save(out)
    print(f"{page}페이지 {dim}x{dim} ETC1A4 알파 평면 -> {out}")


if __name__ == "__main__":
    main()
