"""
검증용 테스트 빌드.

실제 한글 패치가 거치게 될 모든 경로를 그대로 지나가되, 텍스트는 일본어 원문을
유지한다(문제가 생기면 번역이 아니라 파이프라인 탓임이 분명해지도록).
  1. 문자열 블롭을 새로 배치  -> 오프셋 테이블 전면 재작성
  2. 섹션2 크기 변경           -> 리소스 레코드 #106 의 size 갱신
  3. 컨테이너 재압축
  4. 눈으로 확인할 표식 한 줄만 교체

출력: out/init.jp (+ out/init.jp.identity 는 크기 고정 방식 비교용)
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import nlgpak as N

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "base_jp", "romfs", "init.jp")
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

orig = open(SRC, "rb").read()
secs = N.unpack_container(orig)
recs = N.parse_index(secs[0])
si, ri = N.strtab_section(secs, recs)
lang, entries = N.parse_strings(secs[si])

# --- 의미 왕복: 새로 만든 테이블을 다시 읽어 원본과 (해시 -> 텍스트) 비교 -----
probe = N.build_strings(lang, entries)
plang, pentries = N.parse_strings(probe)
same = (plang == lang
        and [h for h, _ in pentries] == [h for h, _ in entries]
        and [t for _, t in pentries] == [t for _, t in entries])
print("의미 왕복(해시 순서/텍스트 전부 일치):", same)
print(f"   원본 테이블 {len(secs[si]):,}바이트 -> 재배치 {len(probe):,}바이트 "
      f"({len(secs[si]) - len(probe):,} 절약)")

# --- 표식 교체: 온라인 플레이 경고문 하나를 바꿔 적용 여부를 눈으로 확인 -------
MARK_TARGET = "{ts:0.9}やめる{/ts}"
MARK_NEW = "{ts:0.9}テスト{/ts}"
hit = [i for i, (_, t) in enumerate(entries) if t == MARK_TARGET]
print(f"표식 대상 {MARK_TARGET!r}: {len(hit)}곳")
marked = list(entries)
for i in hit:
    marked[i] = (marked[i][0], MARK_NEW)

# --- 빌드 A: 섹션 크기 변경 (레코드 size 갱신) --------------------------------
tab_a = N.build_strings(lang, marked)
recs_a = list(recs)
recs_a[ri] = (recs_a[ri][0], len(tab_a), recs_a[ri][2])
secs_a = list(secs)
secs_a[0] = N.build_index(recs_a)
secs_a[si] = tab_a
build_a = N.pack_container(secs_a)
open(os.path.join(OUT, "init.jp"), "wb").write(build_a)
print(f"\n[A] 크기변경 빌드: 섹션2 {len(secs[si]):,} -> {len(tab_a):,}, "
      f"파일 {len(orig):,} -> {len(build_a):,}바이트")

# --- 빌드 B: 섹션 크기 고정 (인덱스 무수정, 뒤를 0으로 채움) ------------------
tab_b = N.build_strings(lang, marked, pad_to=len(secs[si]))
secs_b = list(secs)
secs_b[si] = tab_b
build_b = N.pack_container(secs_b)
open(os.path.join(OUT, "init.jp.identity"), "wb").write(build_b)
print(f"[B] 크기고정 빌드: 섹션2 {len(tab_b):,} (인덱스 무수정), "
      f"파일 {len(build_b):,}바이트")

# --- 두 빌드 모두 다시 열어 자체 정합성 확인 ----------------------------------
for name, blob in (("A", build_a), ("B", build_b)):
    s = N.unpack_container(blob)
    r = N.parse_index(s[0])
    k, kri = N.strtab_section(s, r)
    lg, ent = N.parse_strings(s[k])
    ok = (lg == lang
          and len(ent) == len(entries)
          and [h for h, _ in ent] == [h for h, _ in entries]
          and [t for _, t in ent] == [t for _, t in marked])
    print(f"[{name}] 재파싱 검증: 섹션길이={[len(x) for x in s]} "
          f"레코드={len(r)} 문자열={len(ent)} 내용일치={ok}")
