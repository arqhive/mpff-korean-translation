# -*- coding: utf-8 -*-
"""게임 안 그래픽(타이틀 띠)을 한글판으로 바꾼 romfs 파일을 만든다.

  python scripts/build_graphics.py        # graphics/*.png -> out/romfs/...

일본어가 박힌 텍스처는 타이틀 띠 2종뿐이고, 같은 그림이 두 pak 에 하나씩 들어 있어
파일로는 4장을 고친다. HOME 메뉴 배너 띠(`scripts/build_banner.py`)도 같은 원본
(`graphics/title_strip_ff.png`)을 쓰므로 두 곳의 글자체가 같다.

**바이트 크기를 바꾸면 안 된다.** pak 안 텍스처 데이터는 오프셋 표 없이 기술자 순서대로
이어 붙어 있어서(누적합), 크기가 달라지면 뒤 텍스처가 전부 밀린다. 같은 규격
(256x16 ETC1A4, 4,096바이트)으로 다시 인코딩해 제자리에 덮어쓴다.
"""
import io
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import nlgtex as T

# (romfs 상대 경로, {텍스처 번호: 한글 원본})
TARGETS = [
    ("FrontEnd/Persistent.data", {93: "title_strip_ff.png", 89: "title_strip_bb.png"}),
    ("FrontEnd_BattleBall/Persistent.data", {69: "title_strip_ff.png", 65: "title_strip_bb.png"}),
]


def main():
    src_root = os.path.join(ROOT, "base_jp", "romfs")
    out_root = os.path.join(ROOT, "out", "romfs")
    cache = {}

    for rel, repl in TARGETS:
        src = os.path.join(src_root, *rel.split("/"))
        dst = os.path.join(out_root, *rel.split("/"))
        if not os.path.exists(src):
            raise SystemExit(f"{src} 가 없다. 일본판 romfs 를 base_jp/romfs/ 에 풀어 둬야 한다.")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)

        _blob, ds = T.layout(src)
        with open(dst, "r+b") as f:
            for idx, png in sorted(repl.items()):
                d = ds[idx]
                if png not in cache:
                    img = np.array(Image.open(os.path.join(ROOT, "graphics", png)).convert("RGBA"))
                    if img.shape[:2] != (16, 256):
                        raise SystemExit(f"{png} 크기가 256x16 이 아니다: {img.shape[1]}x{img.shape[0]}")
                    cache[png] = T.encode_etc1a4(img)
                blob = cache[png]
                if len(blob) != d["size"]:
                    raise SystemExit(f"{rel} #{idx}: 인코딩 {len(blob)} != 원본 {d['size']} 바이트")
                if d["fileOff"] is None:
                    raise SystemExit(f"{rel} 은 압축 pak 이라 제자리 교체를 할 수 없다")
                f.seek(d["fileOff"])
                f.write(blob)
                print(f"  {rel} #{idx} <- graphics/{png}  ({len(blob):,} 바이트 @ {d['fileOff']:#x})")

        if os.path.getsize(dst) != os.path.getsize(src):
            raise SystemExit(f"{rel}: 파일 크기가 달라졌다")

        # 되읽어 확인 (섹션 경계는 원본 .dict 로 계산한 것을 그대로 쓴다.
        # 크기를 바꾸지 않았으므로 오프셋은 원본과 같다)
        data = open(dst, "rb").read()
        for idx, png in repl.items():
            d = ds[idx]
            if data[d["fileOff"]:d["fileOff"] + d["size"]] != cache[png]:
                raise SystemExit(f"{rel} #{idx}: 되읽기 결과가 다르다")

    print(f"\n완료: {out_root}")


if __name__ == "__main__":
    main()
