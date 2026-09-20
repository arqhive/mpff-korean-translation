"""배포용 LayeredFS zip 을 만든다.

  sd:/luma/titles/000400000016CE00/romfs/  에 들어갈 init.jp / init.dict 와
  한국어 설명서를 담는다. 게임 데이터는 들어가지 않는다.
"""
import io
import os
import sys
import zipfile

if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "0.1"
TITLE_ID = "000400000016CE00"


def main():
    out_dir = os.path.join(ROOT, "out")
    rel = os.path.join(ROOT, "release")
    zip_path = os.path.join(rel, f"mpff-korean-v{VERSION}-layeredfs.zip")
    romfs = f"luma/titles/{TITLE_ID}/romfs"

    items = [(os.path.join(out_dir, "init.jp"), f"{romfs}/init.jp"),
             (os.path.join(out_dir, "init.dict"), f"{romfs}/init.dict"),
             (os.path.join(rel, "README.txt"), "README.txt")]
    for src, _ in items:
        if not os.path.exists(src):
            raise SystemExit(f"{src} 가 없다. build_patch.py 를 먼저 돌려라.")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for src, name in items:
            z.write(src, name)
            print(f"  {name}  ({os.path.getsize(src):,} 바이트)")
    print(f"\n{zip_path}  ({os.path.getsize(zip_path):,} 바이트)")


if __name__ == "__main__":
    main()
