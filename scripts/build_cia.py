"""사용자가 가진 일본판 CIA 로 한글판 CIA 를 만든다.

LayeredFS 로는 HOME 메뉴의 제목·배너를 바꿀 수 없어서, 거기까지 한글로 하려면
CIA 를 다시 만들어야 한다. 게임 데이터를 배포하지 않으려면 사용자 PC 에서 돌려야 한다.

준비물
  * 일본판 CIA (000400000016CE00)
  * ctrtool, 3dstool, makerom  — PATH 에 있거나 --tools 로 폴더 지정
  * boot9.bin  — %USERPROFILE%/.3ds/boot9.bin 에 두면 ctrtool 이 알아서 쓴다
                 (GM9 덤프는 sd:/gm9/out/boot9.bin)
  * 디스크 여유 6GB 이상

겪어 본 함정 (이전 프로젝트 기록 + 이번 작업)
  * makerom 에 -ignoresign 이 없으면 "Content 0 Is Corrupt" 가 난다.
  * -content 는 <파일>:<인덱스>:<콘텐츠ID> 세 칸 형식이어야 한다.
  * CXI 를 --not-encrypt 로 만들어야 makerom 이 exheader 를 읽어 meta 영역까지 만든다.
  * 타이틀 버전은 makerom 이 exheader 의 remaster version(0)을 따라가서 -ver 가 안 먹는다.
    그래서 결과 CIA 의 TMD 버전 필드(2바이트 빅엔디언)를 원본 값으로 직접 덮어쓴다.
  * code.bin 은 손대지 않으므로 exheader 의 CompressExefsCode 플래그는 그대로 둔다.
"""
import argparse
import io
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import build_banner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE_ID = "000400000016ce00"


def np(p):
    """경로 구분자를 하나로 맞춘다.

    ctrtool 은 '/' 와 '\\' 가 섞인 경로를 거부한다
    ("Path literal has both forward and backward path separators").
    """
    return os.path.normpath(p)


def run(cmd, log):
    with open(log, "wb") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        print(open(log, encoding="utf-8", errors="replace").read()[-2000:])
        raise SystemExit(f"실패: {' '.join(str(c) for c in cmd)}  (로그 {log})")


def align(x, a):
    return (x + a - 1) & ~(a - 1)


def parse_cia(path):
    """CIA 헤더와 TMD 를 읽어 (타이틀버전, [(인덱스, 콘텐츠ID, 크기)]) 를 낸다."""
    with open(path, "rb") as f:
        hdr = f.read(0x2020)
        hsize, ctype, ver, clen, tlen, tmdlen, metalen = struct.unpack_from("<IHHIIII", hdr, 0)
        clen2 = struct.unpack_from("<Q", hdr, 0x18)[0]
        off = align(hsize, 64)
        off = align(off + clen, 64)
        off = align(off + tlen, 64)
        f.seek(off)
        tmd = f.read(tmdlen)

    # TMD: 서명 종류에 따라 서명 블록 크기가 다르다
    sig_type = struct.unpack_from(">I", tmd, 0)[0]
    SIG = {0x10000: 0x200 + 0x3C, 0x10001: 0x100 + 0x3C, 0x10002: 0x3C + 0x40,
           0x10003: 0x200 + 0x3C, 0x10004: 0x100 + 0x3C, 0x10005: 0x3C + 0x40}
    if sig_type not in SIG:
        raise SystemExit(f"모르는 TMD 서명 종류 {sig_type:#x}")
    body = 4 + SIG[sig_type]
    title_ver = struct.unpack_from(">H", tmd, body + 0x9C)[0]
    count = struct.unpack_from(">H", tmd, body + 0x9E)[0]
    info = body + 0x9C + 4 + 0x24 + 36 * 64        # 콘텐츠 청크 기록 시작
    out = []
    for i in range(count):
        cid, idx, ctype_, size = struct.unpack_from(">IHHQ", tmd, info + i * 0x30)
        out.append((idx, cid, size))
    return title_ver, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cia", required=True, help="일본판 CIA 경로")
    ap.add_argument("--out", required=True, help="만들 한글판 CIA 경로")
    ap.add_argument("--tools", default="", help="ctrtool/3dstool/makerom 이 있는 폴더")
    ap.add_argument("--work", default=os.path.join(ROOT, "work", "cia"),
                    help="작업 폴더 (6GB 이상 여유 필요)")
    ap.add_argument("--keep", action="store_true", help="작업 폴더를 지우지 않는다")
    a = ap.parse_args()

    def tool(name):
        p = os.path.join(a.tools, name) if a.tools else name
        if a.tools and not os.path.exists(p) and os.path.exists(p + ".exe"):
            p += ".exe"
        return np(p)

    W = a.work
    os.makedirs(W, exist_ok=True)
    L = lambda n: os.path.join(W, n + ".log")

    ver, contents = parse_cia(a.cia)
    print(f"원본 CIA: 타이틀 버전 {ver}, 콘텐츠 {len(contents)}개")
    for idx, cid, size in contents:
        print(f"  인덱스 {idx} / ID {cid} / {size:,} 바이트")

    # 1) 콘텐츠 분리
    print("콘텐츠 분리 (ctrtool)")
    cdir = os.path.join(W, "contents")
    os.makedirs(cdir, exist_ok=True)
    run([tool("ctrtool"), f"--contents={np(os.path.join(cdir, 'c'))}", np(a.cia)], L("ctrtool"))
    files = {}
    for fn in os.listdir(cdir):
        parts = fn.split(".")
        if len(parts) == 3 and parts[0] == "c":
            files[int(parts[1], 16)] = os.path.join(cdir, fn)
    main_cxi = files[0]
    print(f"  메인 CXI: {os.path.basename(main_cxi)}")

    # 2) CXI 펼치기
    print("CXI 펼치기 (3dstool)")
    cx = os.path.join(W, "cxi")
    os.makedirs(cx, exist_ok=True)
    p = lambda n: np(os.path.join(cx, n))
    run([tool("3dstool"), "-xvtf", "cxi", np(main_cxi),
         "--header", p("ncchheader.bin"), "--exh", p("exheader.bin"),
         "--logo", p("logo.bin"), "--plain", p("plain.bin"),
         "--exefs", p("exefs.bin"), "--romfs", np(os.path.join(W, "romfs.bin"))], L("xcxi"))

    print("RomFS 펼치기")
    rx = os.path.join(W, "rx")
    run([tool("3dstool"), "-xvtf", "romfs", np(os.path.join(W, "romfs.bin")),
         "--romfs-dir", np(rx)], L("xromfs"))

    # 3) 한글 파일 덮어쓰기
    # 업데이트 타이틀의 romfs 에는 init.jp 가 없다. 그때는 아이콘만 바꾸면 된다
    # (본편의 init.jp 가 그대로 쓰이므로 게임 내 텍스트는 이미 한글이다).
    if os.path.exists(os.path.join(rx, "init.jp")):
        out_dir = os.path.join(ROOT, "out")
        for n in ("init.jp", "init.dict"):
            src = os.path.join(out_dir, n)
            if not os.path.exists(src):
                raise SystemExit(f"{src} 가 없다. 먼저 python scripts/build_patch.py 를 돌려라.")
            shutil.copy(src, os.path.join(rx, n))
        print("romfs 에 init.jp / init.dict 덮어씀")
    else:
        print("romfs 에 init.jp 가 없다 (업데이트 타이틀) — romfs 는 그대로 둔다")

    # 4) 배너·아이콘
    build_banner.patch_exefs_file(p("exefs.bin"))

    # 5) 다시 싸기
    print("RomFS 재빌드")
    run([tool("3dstool"), "-cvtf", "romfs", np(os.path.join(W, "romfs.bin")),
         "--romfs-dir", np(rx)], L("cromfs"))
    print("CXI 재빌드 (--not-encrypt)")
    ko_cxi = np(os.path.join(W, "ko.cxi"))
    run([tool("3dstool"), "-cvtf", "cxi", ko_cxi,
         "--header", p("ncchheader.bin"), "--exh", p("exheader.bin"),
         "--logo", p("logo.bin"), "--plain", p("plain.bin"),
         "--exefs", p("exefs.bin"), "--romfs", np(os.path.join(W, "romfs.bin")),
         "--not-encrypt"], L("ccxi"))

    # 6) CIA 로 묶기
    print("CIA 묶기 (makerom -ignoresign)")
    cmd = [tool("makerom"), "-f", "cia", "-o", np(a.out), "-ignoresign"]
    for idx, cid, _size in sorted(contents):
        f = ko_cxi if idx == 0 else np(files[idx])
        cmd += ["-content", f"{f}:{idx}:{cid}"]
    run(cmd, L("makerom"))

    # 7) TMD 버전 되돌리기 — makerom 이 0 으로 써 버린다
    fix_tmd_version(a.out, ver)
    print(f"\n완료: {a.out}  ({os.path.getsize(a.out):,} 바이트)")
    if not a.keep:
        print("작업 폴더 정리")
        shutil.rmtree(W, ignore_errors=True)


def fix_tmd_version(cia, want):
    """결과 CIA 의 TMD 타이틀 버전을 원본 값으로 되돌린다."""
    with open(cia, "r+b") as f:
        hdr = f.read(0x2020)
        hsize, _ct, _v, clen, tlen, tmdlen, _ml = struct.unpack_from("<IHHIIII", hdr, 0)
        off = align(hsize, 64)
        off = align(off + clen, 64)
        off = align(off + tlen, 64)
        f.seek(off)
        tmd = f.read(tmdlen)
        sig_type = struct.unpack_from(">I", tmd, 0)[0]
        SIG = {0x10000: 0x200 + 0x3C, 0x10001: 0x100 + 0x3C, 0x10002: 0x3C + 0x40,
               0x10003: 0x200 + 0x3C, 0x10004: 0x100 + 0x3C, 0x10005: 0x3C + 0x40}
        body = 4 + SIG[sig_type]
        cur = struct.unpack_from(">H", tmd, body + 0x9C)[0]
        if cur == want:
            print(f"TMD 버전 {cur} — 그대로")
            return
        f.seek(off + body + 0x9C)
        f.write(struct.pack(">H", want))
        print(f"TMD 버전 {cur} -> {want} 로 고침")


if __name__ == "__main__":
    main()
