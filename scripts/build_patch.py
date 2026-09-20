"""
번역 파일(tl/ko.json)을 읽어 한글판 init.jp / init.dict 를 만든다.

tl/ko.json 은 [{"hash": "0x...", "en": ..., "jp": ..., "ko": ...}, ...] 이고
`ko` 가 빈 문자열이면 원문(일본어)을 그대로 둔다. 그래서 번역이 진행되는 만큼
부분 적용된 빌드를 언제든 만들 수 있다.

지켜야 하는 규칙 (전부 실측으로 확인한 것들)
  * 문자열 블롭은 중복 제거 없이, 원본 블롭 순서를 지켜 쓴다.
  * 섹션 크기가 바뀌면 리소스 인덱스의 해당 레코드 size 를 갱신한다.
  * **init.dict 의 '.jp' 청크 엔트리를 갱신한다.** 빼먹으면 텍스트가 전부 사라진다.
  * 폰트 정의는 CRLF 평문이고 꼬리 공백까지 보존해야 한다.
  * 섹션1 은 인덱스가 전부를 덮지 않으므로 교체 구간만 바꾸고 나머지는 복사한다.
  * 자리가 바뀌지 않은 아틀라스 페이지는 원본 바이트를 손대지 않는다(밉 필터가 다름).
  * **섹션3 크기는 989,952 바이트를 넘길 수 없다.** 넘기면 부팅 중 크래시한다.
"""
import collections
import io
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import fontlib as FL
import nlgfont as F
import nlgpak as N

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "base_jp", "romfs")
OUT = os.path.join(ROOT, "out")
TL = os.path.join(ROOT, "tl", "ko.json")
FONT_TTF = os.path.join(ROOT, "fonts", "Pretendard-SemiBold.ttf")
FONT_PT = 24

# 한글 메트릭. b(셀 폭)는 아틀라스에서 차지하는 자리일 뿐 글자 크기와 무관하다.
# 한글 전체의 잉크가 펜 기준 x 0..21 에 들어가므로 22 면 충분하다.
HAN_A, HAN_B, HAN_C, HAN_D = 22, 22, 1, 0
SPACE_ADV = 7              # 원본 4px 은 한글 사이 1px 과 구분이 안 된다
PEN_X, BASELINE_Y = 1, 24  # 모든 음절을 같은 원점에 그려야 기준선이 맞는다

SEC1_TYPES = (0x33027011, 0x33027012, 0x32001301, 0x3201B501)
SEC3_LIMIT = 989952

# 한글화 후에는 더 이상 쓰지 않는 문자. 자리를 비워 한글 음절을 더 넣는다.
def is_droppable(ch):
    o = ord(ch)
    return (0x3040 <= o <= 0x30FF          # 가나
            or 0x4E00 <= o <= 0x9FFF       # 한자
            or 0x3000 <= o <= 0x303F       # 전각 구두점
            or 0xFF00 <= o <= 0xFFEF)      # 전각 영숫자


def hangul_cell(font, ch, width):
    pad = 24
    tmp = Image.new("L", (width + pad * 2, FL.ROW_H + pad * 2), 0)
    ImageDraw.Draw(tmp).text((PEN_X + pad, BASELINE_Y + pad), ch,
                             font=font, fill=255, anchor="ls")
    return np.array(tmp)[pad:pad + FL.ROW_H, pad:pad + width]


def replace_sec1_spans(sec1, recs, replace):
    spans = sorted(((recs[i][2], recs[i][1], i, data)
                    for i, data in replace.items()), key=lambda s: s[0])
    out = bytearray()
    newrecs = list(recs)
    shifts = []
    cur = delta = 0
    for off, size, i, data in spans:
        out += sec1[cur:off]
        padded = bytearray(data)
        while (len(padded) - size) % 4:
            padded += b" "          # 정의는 평문이라 NUL 이 아니라 공백
        newrecs[i] = (recs[i][0], len(padded), off + delta)
        out += padded
        delta += len(padded) - size
        shifts.append((off + size, delta))
        cur = off + size
    out += sec1[cur:]

    def shift_of(o):
        d = 0
        for base, dd in shifts:
            if o >= base:
                d = dd
        return d

    for i, (t, s, o) in enumerate(recs):
        if t in SEC1_TYPES and i not in replace:
            newrecs[i] = (t, s, o + shift_of(o))
    return bytes(out), newrecs


def main():
    rows = json.load(open(TL, encoding="utf-8"))
    tl = {r["hash"]: r["ko"] for r in rows if r.get("ko")}
    done = len(tl)
    print(f"번역 {done}/{len(rows)}개 적용 ({done * 100 // len(rows)}%)")

    font = FL.MainFont(os.path.join(SRC, "init.jp"))
    secs, recs = list(font.secs), list(font.recs)
    dct = open(os.path.join(SRC, "init.dict"), "rb").read()

    si, ri = N.strtab_section(secs, recs)
    lang, entries = N.parse_strings(secs[si])
    order = N.blob_order_of(secs[si])
    new_entries = [(h, tl.get(f"{h:#010x}", t)) for h, t in entries]

    # --- 필요한 문자 집합 ----------------------------------------------------
    used = set("".join(t for _, t in new_entries))
    syll = sorted(c for c in used if "가" <= c <= "힣")
    print(f"한글 고유 음절 {len(syll)}자")

    # 글리프가 없는 문자는 화면에서 빈칸이 된다. 번역을 고친 뒤 새 기호나 한자가
    # 섞여 들어오면 여기서 잡힌다. (태그 안쪽은 그려지지 않으니 제외)
    have = {FL.char_of(g[0]) for g in font.desc["glyphs"]} | set(syll)
    drawn = set("".join(re.sub(r"\{[^}]*\}", "", t) for _, t in new_entries))
    missing = sorted(c for c in drawn - have if c not in "\r\n")
    if missing:
        where = {}
        for h, t in new_entries:
            for c in set(re.sub(r"\{[^}]*\}", "", t)) & set(missing):
                where.setdefault(c, f"{h:#010x}")
        print(f"  !! 글리프 없는 문자 {len(missing)}자 — 빈칸으로 나온다:")
        for c in missing:
            print(f"     {c!r} (U+{ord(c):04X})  처음 쓰인 곳 {where[c]}")

    # 페이지 0~2 는 ETC1A4 압축이라 다시 그릴 수 없다. 그 위에 놓인 글리프는
    # 원래 자리에 그대로 두고, 한글은 3페이지부터 채운다.
    frozen = {FL.char_of(g[0])
              for g, (pi, *_) in zip(font.desc["glyphs"],
                                     FL.MainFont.layout(font.desc["glyphs"]))
              if font.page_fmt[pi][1] != 4}
    print(f"고정 페이지 위 글리프 {len(frozen)}자 (ETC1A4)")

    # --- 글리프 목록: 일본어 글리프를 덜어내고 한글을 넣는다 ------------------
    # 번역이 끝나기 전에는 남은 일본어 문장이 한자·가나를 계속 쓴다. 자리가
    # 모자라면 **남은 일본어 본문에서 적게 쓰이는 글자부터** 덜어낸다.
    # 번역이 끝나면 일본어 글리프가 전부 안 쓰이게 되어 자연히 사라진다.
    freq = collections.Counter(c for _, t in new_entries for c in t
                               if is_droppable(c))
    hangul = [(FL.key_of(c), HAN_A, HAN_B, HAN_C, HAN_D) for c in syll]

    def build_list(drop):
        keep = [g for g in font.desc["glyphs"] if FL.char_of(g[0]) not in drop]
        out = sorted(keep + hangul, key=lambda g: ord(FL.char_of(g[0])))
        return [(k, SPACE_ADV, b, c, d) if FL.char_of(k) == " " else (k, a, b, c, d)
                for k, a, b, c, d in out]

    jp_glyphs = [FL.char_of(g[0]) for g in font.desc["glyphs"]
                 if is_droppable(FL.char_of(g[0]))
                 and FL.char_of(g[0]) not in frozen]
    jp_glyphs.sort(key=lambda c: freq.get(c, 0))     # 안 쓰이는 것부터
    lo, hi = 0, len(jp_glyphs)
    while lo < hi:                                    # 최소한만 덜어낸다
        mid = (lo + hi) // 2
        merged = build_list(set(jp_glyphs[:mid]))
        if FL.MainFont.layout(merged)[-1][0] + 1 <= len(font.pages):
            hi = mid
        else:
            lo = mid + 1
    dropped = set(jp_glyphs[:lo])
    merged = build_list(dropped)
    place = FL.MainFont.layout(merged)
    used_pages = place[-1][0] + 1
    if used_pages > len(font.pages):
        raise SystemExit("한글만으로도 자리가 모자란다")
    still_used = sum(1 for c in dropped if freq.get(c, 0))
    print(f"글리프 {len(font.desc['glyphs'])} -> {len(merged)} "
          f"(일본어 {len(dropped)}자 제거, 그중 아직 쓰이는 글자 {still_used}자), "
          f"페이지 {used_pages}/{len(font.pages)}")

    # --- 아틀라스 -----------------------------------------------------------
    old_place = {FL.char_of(k): p
                 for (k, *_), p in zip(font.desc["glyphs"],
                                       FL.MainFont.layout(font.desc["glyphs"]))}
    cells = font.cells()
    ttf = ImageFont.truetype(FONT_TTF, FONT_PT)
    pages = [p.copy() for p in font.pages]
    touched = set()
    for (key, a, b, c, d), (pi, x, y, w) in zip(merged, place):
        ch = FL.char_of(key)
        if old_place.get(ch) == (pi, x, y, w):
            continue
        cell = hangul_cell(ttf, ch, w) if "가" <= ch <= "힣" else cells[ch][0]
        pages[pi][y:y + FL.ROW_H, x:x + w] = cell[:, :w]
        touched.add(pi)
    print(f"다시 그리는 페이지 {len(touched)}장: {sorted(touched)}")

    # --- 정의 ---------------------------------------------------------------
    desc_bytes = F.render_desc(font.desc, merged)
    desc_idx = [i for i, (t, s, o) in enumerate(recs)
                if t == N.FONTDESC_TAG and s == 32696]
    secs[1], recs = replace_sec1_spans(secs[1], recs,
                                       {i: desc_bytes for i in desc_idx})

    # --- 섹션3 --------------------------------------------------------------
    s3 = bytearray(secs[3])
    page_recs = [(i, s, o) for i, (t, s, o) in enumerate(recs)
                 if t == N.FONTPAGE_TAG]
    for pi in sorted(touched):
        _i, size, off = page_recs[font.page_res[pi]]
        dim, bpp, levels = font.page_fmt[pi]
        if bpp != 4:
            raise SystemExit(f"페이지 {pi} 는 ETC1A4 라 다시 그릴 수 없다")
        s3[off:off + size] = F.build_mips(pages[pi], bpp, levels)
    secs[3] = bytes(s3)
    assert len(secs[3]) <= SEC3_LIMIT, "섹션3 한도 초과"

    # --- 문자열 -------------------------------------------------------------
    tab = N.build_strings(lang, new_entries, blob_order=order)
    recs[ri] = (recs[ri][0], len(tab), recs[ri][2])
    secs[si] = tab

    # --- 마무리 -------------------------------------------------------------
    secs[0] = N.build_index(recs)
    pak = N.pack_container(secs)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "init.jp"), "wb").write(pak)
    open(os.path.join(OUT, "init.dict"), "wb").write(
        N.patch_dict(dct, ".jp", N.container_chunk_table(pak)))
    print(f"init.jp {len(pak):,}바이트, 섹션 {[len(s) for s in secs]}")

    # --- 남은 자리 ----------------------------------------------------------
    # 번역이 끝나면 일본어 글리프가 전부 빠지므로, 그때의 여유를 기준으로 알린다
    free_pages = sum(1 for dim, bpp, lv in font.page_fmt if bpp == 4)
    total = free_pages * 7 * FL.PAGE_DIM
    latin = sum(b for k, a, b, c, d in merged
                if not is_droppable(FL.char_of(k))
                and FL.char_of(k) not in frozen
                and not ("가" <= FL.char_of(k) <= "힣"))
    print(f"아틀라스: 한글 {len(syll)}자 사용 / 번역 완료 시 최대 "
          f"{(total - latin) // HAN_B:,}자")


if __name__ == "__main__":
    main()
