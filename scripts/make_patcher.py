# -*- coding: utf-8 -*-
"""CIA·3DS 패처 꾸리기 → release/patcher (payload·lib·bin) + release/python (임베디드 파이썬)

  python scripts/build_patch.py                       # 먼저 out/init.jp · out/init.dict 를 만든다
  python scripts/make_patcher.py 0.2 [--python <임베디드 파이썬 폴더 또는 zip>]

payload 에는 한글 init.jp·init.dict, 배너 띠 그림, 게임 이름, 원본 파일 MD5 만 담는다.
배너·아이콘은 사용자 파일 안의 것을 고쳐 쓰므로 원본 게임 데이터는 들어가지 않는다.
lib 에는 ffpatch·lz11 과 pyctr·pycryptodomex(설치된 것 복사), bin 에는 3dstool·makerom 을 넣는다.

배너 띠는 여기서 미리 RGBA8 로 인코딩해 둔다. 그래야 배포 패처가 Pillow·numpy 없이
순수 파이썬만으로 돌아간다(임베디드 파이썬에 추가 패키지를 넣지 않아도 된다).
"""
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import build_banner
import ffpatch

TITLE_ID = "000400000016CE00"
PATCHER = os.path.join(ROOT, "release", "patcher")


def build_payload(dst, version):
    """payload 폴더를 새로 만든다. 돌려주는 값은 romfs 교체 파일 개수."""
    from PIL import Image

    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.join(dst, "romfs"))

    src_md5 = {}
    for name in ffpatch.PAYLOAD_FILES:
        ko = os.path.join(ROOT, "out", name)
        jp = os.path.join(ROOT, "base_jp", "romfs", name)
        if not os.path.exists(ko):
            raise SystemExit(f"{ko} 가 없다. 먼저 python scripts/build_patch.py 를 돌려라.")
        if not os.path.exists(jp):
            raise SystemExit(f"{jp} 가 없다. 일본판 romfs 를 base_jp/romfs/ 에 풀어 둬야 한다.")
        shutil.copyfile(ko, os.path.join(dst, "romfs", name))
        src_md5[name] = ffpatch.md5_file(jp)

    if not os.path.exists(build_banner.STRIP):
        print("배너 띠 이미지가 없어 먼저 만든다")
        import make_banner_strip
        make_banner_strip.main()
    strip = build_banner.encode_rgba8(Image.open(build_banner.STRIP), 256, 16)
    assert len(strip) == 0x4000, len(strip)
    open(os.path.join(dst, "common6_rgba8.bin"), "wb").write(strip)

    json.dump({"short": build_banner.SHORT, "long": build_banner.LONG,
               "publisher": build_banner.PUBLISHER},
              open(os.path.join(dst, "titles.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"version": version, "title_id": TITLE_ID, "source_md5": src_md5},
              open(os.path.join(dst, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return len(src_md5)


def copy_python(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
        return
    with zipfile.ZipFile(src) as z:                 # 파이썬 임베디드 배포 zip 또는 다른 패처 zip
        for i in z.infolist():
            if i.is_dir():
                continue
            parts = i.filename.replace("\\", "/").split("/")
            rel = parts[parts.index("python") + 1:] if "python" in parts[:-1] else parts
            out = os.path.join(dst, *rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "wb").write(z.read(i))


def main():
    ver = sys.argv[1] if len(sys.argv) > 1 else "0.2"
    py = sys.argv[sys.argv.index("--python") + 1] if "--python" in sys.argv else None

    n = build_payload(os.path.join(PATCHER, "payload"), ver)

    lib = os.path.join(PATCHER, "lib")
    os.makedirs(lib, exist_ok=True)
    for f in ("ffpatch.py", "lz11.py"):
        shutil.copyfile(os.path.join(HERE, f), os.path.join(lib, f))
    import Cryptodome
    import pyctr
    for m in (pyctr, Cryptodome):
        d = os.path.join(lib, m.__name__)
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(os.path.dirname(m.__file__), d,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyi", "SelfTest"))

    b = os.path.join(PATCHER, "bin")
    os.makedirs(b, exist_ok=True)
    for f in ("3dstool.exe", "makerom.exe"):
        shutil.copyfile(os.path.join(ROOT, "tools", f), os.path.join(b, f))

    if py:
        copy_python(py, os.path.join(ROOT, "release", "python"))
    print(f"패처 준비 완료: payload 교체 파일 {n}개, lib·bin -> {PATCHER}"
          + (", 파이썬 -> release/python" if py else ""))


if __name__ == "__main__":
    main()
