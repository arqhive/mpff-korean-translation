# -*- coding: utf-8 -*-
"""일본판 CIA/3DS 로 한글판 CIA/3DS 를 만든다 (개발용). 배포 패처(release/패치하기.bat)와 같은 ffpatch 를 쓴다.

  python scripts/build_patch.py                                  # 먼저 out/init.jp · out/init.dict
  python scripts/build_cia.py --cia "일본판.cia" --out "한글판.cia"
  python scripts/build_cia.py --cia "일본판.3ds" --out "한글판.3ds"

게임 안 한글(init.jp·init.dict)과 HOME 메뉴 배너·게임 이름이 모두 들어간다. 결과 형식은 --out 확장자로 정한다.
3dstool·makerom 은 tools/, 키(boot9.bin·seeddb.bin)는 Azahar sysdata 등에서 찾는다(ffpatch.key_dirs).
디스크 여유는 6GB 쯤 필요하다.

업데이트 타이틀(0004000E0016CE00)은 넣지 않는다. 콘텐츠 번호가 0·2 라서 다시 묶을 수 없고,
원본 그대로 설치해도 본편의 한글 제목·배너가 유지된다(실기 확인).
"""
import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import ffpatch
import make_patcher


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cia", required=True, help="일본판 .cia 또는 .3ds")
    ap.add_argument("--out", required=True, help="만들 .cia 또는 .3ds")
    ap.add_argument("--tools", default=os.path.join(ROOT, "tools"),
                    help="3dstool·makerom 이 있는 폴더")
    ap.add_argument("--work", default=os.path.join(ROOT, "work", "cia"), help="작업 폴더")
    ap.add_argument("--keep", action="store_true", help="작업 폴더를 지우지 않는다")
    a = ap.parse_args()

    payload = os.path.join(ROOT, "work", "payload")
    n = make_patcher.build_payload(payload, "dev")
    print(f"payload: romfs 교체 파일 {n}개")
    ffpatch.patch(os.path.abspath(a.cia), os.path.abspath(a.out), payload,
                  os.path.abspath(a.tools), os.path.abspath(a.work), keep=a.keep)
    print(f"\n완료: {a.out}  ({os.path.getsize(a.out):,} 바이트)")


if __name__ == "__main__":
    main()
