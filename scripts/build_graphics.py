# -*- coding: utf-8 -*-
"""게임 안 그래픽(타이틀 띠)을 한글판으로 바꾼다.

  python scripts/build_graphics.py        # graphics/*.png -> out/romfs, out/romfs_upd, out/texpatch

일본어가 박힌 텍스처는 타이틀 띠 2종뿐이다. 그 그림이 세 pak 에 들어 있어 여섯 자리를 고친다.

  본편     FrontEnd/Persistent.data              #93 페더레이션 포스, #89 블라스트 볼
  본편     FrontEnd_BattleBall/Persistent.data   #69 페더레이션 포스, #65 블라스트 볼
  업데이트 FrontEnd/Persistent.data              #93, #89   ← 업데이트 v1.2.0 을 설치하면 이쪽을 읽는다

**바이트 크기를 바꾸면 안 된다.** pak 안 텍스처 데이터는 오프셋 표 없이 기술자 순서대로
이어 붙어 있어서(누적합), 크기가 달라지면 뒤 텍스처가 전부 밀린다. 같은 규격
(256x16 ETC1A4, 4,096바이트)으로 다시 인코딩해 제자리에 덮어쓴다.

만드는 것
  out/romfs/...        본편 pak 통째 (LayeredFS 배포용)
  out/romfs_upd/...    업데이트 pak 통째 (검증용)
  out/texpatch/        배포 패처가 쓰는 것 — 띠 블롭과 patch.json(파일 MD5별 덮어쓸 위치)

업데이트 pak 은 `upd_jp/romfs/` 에 있어야 한다(업데이트 CIA 에서 뽑는다). 없으면 본편만 만들고,
patch.json 의 업데이트 항목은 이전에 만든 것을 그대로 둔다.
"""
import hashlib
import io
import json
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

STRIPS = {"ff": "title_strip_ff.png", "bb": "title_strip_bb.png"}

# (romfs 상대 경로, 어느 쪽, {텍스처 번호: 띠 이름})
TARGETS = [
    ("FrontEnd/Persistent.data", "base", {93: "ff", 89: "bb"}),
    ("FrontEnd_BattleBall/Persistent.data", "base", {69: "ff", 65: "bb"}),
    ("FrontEnd/Persistent.data", "upd", {93: "ff", 89: "bb"}),
]

SRC = {"base": "base_jp/romfs", "upd": "upd_jp/romfs"}
OUT = {"base": "out/romfs", "upd": "out/romfs_upd"}


def md5_file(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def encode_strips():
    """띠 PNG 를 ETC1A4 로 인코딩해 둔다."""
    out = {}
    for key, png in STRIPS.items():
        img = np.array(Image.open(os.path.join(ROOT, "graphics", png)).convert("RGBA"))
        if img.shape[:2] != (16, 256):
            raise SystemExit(f"{png} 크기가 256x16 이 아니다: {img.shape[1]}x{img.shape[0]}")
        out[key] = T.encode_etc1a4(img)
        print(f"  graphics/{png} -> ETC1A4 {len(out[key]):,}바이트")
    return out


def main():
    blobs = encode_strips()
    patch_dir = os.path.join(ROOT, "out", "texpatch")
    os.makedirs(patch_dir, exist_ok=True)
    for key, b in blobs.items():
        open(os.path.join(patch_dir, f"strip_{key}.bin"), "wb").write(b)

    pj = os.path.join(patch_dir, "patch.json")
    patch = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else {}

    for rel, side, repl in TARGETS:
        src = os.path.join(ROOT, *SRC[side].split("/"), *rel.split("/"))
        if not os.path.exists(src):
            if side == "upd":
                print(f"  (업데이트 {rel} 없음 — 건너뛴다. patch.json 의 기존 항목은 그대로 둔다)")
                continue
            raise SystemExit(f"{src} 가 없다. 일본판 romfs 를 풀어 둬야 한다.")

        dst = os.path.join(ROOT, *OUT[side].split("/"), *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)

        _blob, ds = T.layout(src)
        writes = []
        with open(dst, "r+b") as f:
            for idx, key in sorted(repl.items()):
                d = ds[idx]
                if len(blobs[key]) != d["size"]:
                    raise SystemExit(f"{rel} #{idx}: 인코딩 {len(blobs[key])} != 원본 {d['size']} 바이트")
                if d["fileOff"] is None:
                    raise SystemExit(f"{rel} 은 압축 pak 이라 제자리 교체를 할 수 없다")
                f.seek(d["fileOff"])
                f.write(blobs[key])
                writes.append([d["fileOff"], key])
        if os.path.getsize(dst) != os.path.getsize(src):
            raise SystemExit(f"{rel}: 파일 크기가 달라졌다")

        # 되읽어 확인 (섹션 경계는 원본 .dict 로 계산한 것을 그대로 쓴다)
        data = open(dst, "rb").read()
        for idx, key in repl.items():
            d = ds[idx]
            if data[d["fileOff"]:d["fileOff"] + d["size"]] != blobs[key]:
                raise SystemExit(f"{rel} #{idx}: 되읽기 결과가 다르다")

        entry = {"md5": md5_file(src), "patched_md5": md5_file(dst),
                 "size": os.path.getsize(src), "side": side, "writes": sorted(writes)}
        same = [e for e in patch.get(rel, []) if e["md5"] != entry["md5"]]
        patch[rel] = sorted(same + [entry], key=lambda e: e["side"])
        print(f"  {side:4s} {rel} #{sorted(repl)} 교체 @ "
              + ", ".join(f"{o:#x}" for o, _ in sorted(writes)))

    with io.open(pj, "w", encoding="utf-8") as f:
        json.dump(patch, f, ensure_ascii=False, indent=1)
    n = sum(len(v) for v in patch.values())
    print(f"\nout/texpatch/patch.json — 파일 {len(patch)}종, 판본 {n}개")
    print("완료:", os.path.join(ROOT, "out"))


if __name__ == "__main__":
    main()
