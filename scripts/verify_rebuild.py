"""init.jp 왕복 검증: 컨테이너 -> 인덱스 -> 문자열 테이블 -> 재직렬화 -> 재압축."""
import hashlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import nlgpak as N

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "base_jp", "romfs", "init.jp")

orig = open(SRC, "rb").read()
secs = N.unpack_container(orig)
print("섹션 길이:", [len(s) for s in secs])

recs = N.parse_index(secs[0])
print("인덱스 레코드:", len(recs), "(섹션0 =", len(secs[0]), "바이트)")

si, ri = N.strtab_section(secs, recs)
print(f"문자열 테이블: 섹션{si}, 레코드#{ri}, 크기 {recs[ri][1]}")

lang, entries = N.parse_strings(secs[si])
print(f"languageIndex={lang}, 문자열 {len(entries)}개, 고유 해시 {len(set(h for h, _ in entries))}")

# 1) 문자열 테이블 재직렬화
rebuilt_tab = N.build_strings(lang, entries)
print("[1] 문자열 테이블 재직렬화:",
      "바이트 동일" if rebuilt_tab == secs[si] else f"불일치 (원본 {len(secs[si])} / 재빌드 {len(rebuilt_tab)})")
if rebuilt_tab != secs[si]:
    for i, (a, b) in enumerate(zip(secs[si], rebuilt_tab)):
        if a != b:
            print("    첫 불일치 오프셋", hex(i))
            break

# 2) 인덱스 재직렬화
print("[2] 인덱스 재직렬화:", "바이트 동일" if N.build_index(recs) == secs[0] else "불일치")

# 3) 컨테이너 재압축
rebuilt = N.pack_container(secs)
print("[3] 컨테이너 재압축:",
      "바이트 동일" if rebuilt == orig else f"불일치 (원본 {len(orig)} / 재빌드 {len(rebuilt)})")
print("    md5 원본  ", hashlib.md5(orig).hexdigest())
print("    md5 재빌드", hashlib.md5(rebuilt).hexdigest())

# 4) 문자열 예산
header = 8 + len(entries) * 8
budget_chars = (len(secs[si]) - header) // 2
used_chars = sum(len(t) + 1 for _, t in dict.fromkeys(entries))
uniq = {}
for h, t in entries:
    uniq.setdefault(t, 0)
print(f"[4] 블롭 예산: {budget_chars:,} 코드유닛 / 고유 문자열 {len(uniq):,}개")
print(f"    현재 일본어 사용량: {sum(len(t) + 1 for t in uniq):,} 코드유닛")
