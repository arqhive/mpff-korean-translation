"""배너 CGFX 의 COMMON6(256x16 띠)를 한글로 다시 그린다.

원본은 「メトロイドプライム フェデレーションフォース」.
흰 글자 코어 + 시안(3,204,235) 글로우 구조라서 같은 방식으로 만든다.
원본 실측: 잉크 x 8..242(235px), 코어 y 3..11, 글로우까지 y 0..15.
"""
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTF = os.path.join(ROOT, "fonts", "Pretendard-Bold.ttf")
OUT = os.path.join(ROOT, "out", "banner")

W, H = 256, 16
SS = 8
TEXT = "메트로이드 프라임  페더레이션 포스"
GLOW = (3, 204, 235)
CORE = (250, 253, 255)

MAX_W, MAX_H = 235, 12      # 잉크가 들어갈 상자 (1배 기준)
CENTER_Y = 7.3              # 코어 세로 중심


def ink(size):
    """글자 마스크를 넉넉한 캔버스에 그리고 잉크 영역만 잘라낸다."""
    font = ImageFont.truetype(TTF, size)
    pad = size
    cw, ch = W * SS + pad * 2, size * 3
    img = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(img).text((cw // 2, ch // 2), TEXT, font=font, fill=255, anchor="mm")
    bb = img.getbbox()
    return img.crop(bb) if bb else None


def main():
    best = None
    for size in range(40, 160, 2):
        m = ink(size)
        if m is None:
            continue
        if m.width <= MAX_W * SS and m.height <= MAX_H * SS:
            best = (size, m)
    size, m = best
    print(f"폰트 크기 {size} -> 잉크 {m.width / SS:.1f} x {m.height / SS:.1f} px "
          f"(상자 {MAX_W}x{MAX_H})")

    # 슈퍼샘플 마스크를 1배로 줄여 안티에일리어싱
    tw, th = round(m.width / SS), round(m.height / SS)
    small = m.resize((tw, th), Image.LANCZOS)

    mask = Image.new("L", (W, H), 0)
    x0 = (W - tw) // 2
    y0 = int(round(CENTER_Y - th / 2))
    mask.paste(small, (x0, y0))
    print(f"배치: x {x0}..{x0 + tw - 1}, y {y0}..{y0 + th - 1}")

    a = np.array(mask).astype(np.float32) / 255.0
    glow = np.array(mask.filter(ImageFilter.GaussianBlur(1.15))).astype(np.float32) / 255.0
    glow = np.clip(glow * 2.7, 0, 1)

    alpha = glow + a * (1 - glow)
    rgb = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        pre = GLOW[i] * glow * (1 - a) + CORE[i] * a
        rgb[..., i] = np.where(alpha > 1e-6, pre / np.maximum(alpha, 1e-6), 0)

    out = np.concatenate([np.clip(rgb, 0, 255), (alpha * 255)[..., None]], axis=2)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, "COMMON6_ko_up.png"))
    img.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(OUT, "COMMON6_ko_zoom.png"))
    print("저장 완료")


if __name__ == "__main__":
    main()
