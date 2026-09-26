# -*- coding: utf-8 -*-
"""배포 ZIP 두 개 만들기.

  python scripts/build_patch.py                                  # out/init.jp · out/init.dict
  python scripts/make_patcher.py 0.3 --python <임베디드 파이썬>    # release/patcher · release/python
  python scripts/make_release.py 0.3

release/MPFF_KO_v<버전>_LayeredFS.zip
  luma/titles/000400000016CE00/locale.txt         빼면 크래시한다
  luma/titles/000400000016CE00/romfs/init.jp      게임 안 텍스트 + 한글 폰트
  luma/titles/000400000016CE00/romfs/init.dict    위 파일의 청크 표
  luma/titles/000400000016CE00/romfs/FrontEnd*/Persistent.data   게임 안 타이틀 띠
  README_한국어.txt, LICENSE.txt
release/MPFF_KO_v<버전>_Patcher.zip
  MPFF_KO_v<버전>_Patcher/패치하기.bat, patcher/, python/    일본판 CIA·3DS 를 한글판으로 만드는 패처
  MPFF_KO_v<버전>_Patcher/luma/...                           패처로 설치해도 locale.txt 는 필요하다
  README_한국어.txt, LICENSE.txt

locale.txt 는 두 ZIP 모두에 들어간다. 일본판이 아닌 리전 본체(한국판 등)에서는
게임이 시스템 언어에 맞는 언어 팩을 찾다 실패해 게임 시작 직후 크래시한다.
Luma 기능이라 CIA 에 담을 수 없어서, 패처로 만든 CIA 를 쓰는 사람도 SD 에 따로 둬야 한다.
"""
import io
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TITLE_ID = "000400000016CE00"
LOCALE = "JPN JP"      # 타 리전 본체에서 크래시를 막는다. 빼면 안 된다.


def add_tree(z, src, arc):
    n = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            p = os.path.join(root, f)
            z.write(p, (arc + "/" + os.path.relpath(p, src).replace(os.sep, "/")).lstrip("/"))
            n += 1
    return n


def main():
    ver = sys.argv[1] if len(sys.argv) > 1 else "0.3"
    out_dir = os.path.join(ROOT, "out")
    rel = os.path.join(ROOT, "release")
    romfs = f"luma/titles/{TITLE_ID}/romfs"
    locale_arc = f"luma/titles/{TITLE_ID}/locale.txt"
    docs = [(os.path.join(rel, "README_한국어.txt"), "README_한국어.txt"),
            (os.path.join(ROOT, "LICENSE"), "LICENSE.txt")]

    items = [(os.path.join(out_dir, "init.jp"), f"{romfs}/init.jp"),
             (os.path.join(out_dir, "init.dict"), f"{romfs}/init.dict")]
    gr = os.path.join(out_dir, "romfs")                   # 게임 안 그래픽(타이틀 띠)
    for root, _, files in os.walk(gr):
        for f in sorted(files):
            sub = os.path.relpath(os.path.join(root, f), gr).replace(os.sep, "/")
            items.append((os.path.join(root, f), f"{romfs}/{sub}"))
    for src, _ in items + docs:
        if not os.path.exists(src):
            raise SystemExit(f"{src} 가 없다. build_patch.py 를 먼저 돌려라.")

    a = os.path.join(rel, f"MPFF_KO_v{ver}_LayeredFS.zip")
    with zipfile.ZipFile(a, "w", zipfile.ZIP_DEFLATED) as z:
        for src, name in items:
            z.write(src, name)
            print(f"  {name}  ({os.path.getsize(src):,} 바이트)")
        z.writestr(locale_arc, LOCALE)
        for src, name in docs:
            z.write(src, name)
    print(f"{a}  ({os.path.getsize(a):,} 바이트)\n")

    patcher = os.path.join(rel, "patcher")
    python = os.path.join(rel, "python")
    if not os.path.isdir(os.path.join(patcher, "payload")) or not os.path.isdir(python):
        raise SystemExit(f"패처가 준비되지 않았다. 먼저 python scripts/make_patcher.py {ver} "
                         f"--python <임베디드 파이썬> 을 돌려라.")

    b = os.path.join(rel, f"MPFF_KO_v{ver}_Patcher.zip")
    top = f"MPFF_KO_v{ver}_Patcher"
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(rel, "패치하기.bat"), f"{top}/패치하기.bat")
        n = add_tree(z, patcher, f"{top}/patcher")
        n += add_tree(z, python, f"{top}/python")
        z.writestr(f"{top}/{locale_arc}", LOCALE)
        for src, name in docs:
            z.write(src, f"{top}/{name}")
    print(f"{b}  파일 {n + 4}개 ({os.path.getsize(b):,} 바이트)")


if __name__ == "__main__":
    main()
