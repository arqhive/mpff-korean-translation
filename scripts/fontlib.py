"""
init.jp 의 메인 폰트(DFGothicP-W5)를 읽고 다시 만드는 층.

아틀라스 배치 (원본에서 역산해 확인함)
  - 페이지 256x256, 행 높이 34 -> 한 페이지에 7행
  - 글리프 셀 폭 = 정의의 `Width a b c d` 중 **b**
  - 정의에 적힌 순서대로 왼쪽->오른쪽으로 채우고, 폭이 모자라면 다음 행,
    행이 모자라면 다음 페이지
  - 글리프 목록은 코드포인트 오름차순으로 정렬돼 있다
  - 페이지 목록은 32비트 리소스 ID 배열이고, ID -> 섹션3 리소스 대응은
    섹션1 앞머리의 56바이트 텍스처 디스크립터 테이블 순서로 정해진다
"""

import struct

import numpy as np

import nlgfont as F
import nlgpak as N

TEX_TAG = 0xE977D350
TEX_STRIDE = 0x38
PAGE_DIM = 256
ROW_H = 34


def read_tex_table(sec1):
    """섹션1 앞머리 -> [(id, size, w, h)], 그리고 테이블이 끝나는 오프셋"""
    out = []
    off = 0
    while off + TEX_STRIDE <= len(sec1):
        tag, pid, size, _pid2 = struct.unpack_from("<4I", sec1, off)
        if tag != TEX_TAG:
            break
        wh = struct.unpack_from("<I", sec1, off + 0x18)[0]
        out.append((pid, size, wh & 0xFFFF, (wh >> 16) & 0xFFFF))
        off += TEX_STRIDE
    return out, off


class MainFont:
    """메인 폰트 한 벌: 정의 + 페이지 비트맵."""

    def __init__(self, pak_path):
        self.secs = N.unpack_container(open(pak_path, "rb").read())
        self.recs = N.parse_index(self.secs[0])
        s1, s3 = self.secs[1], self.secs[3]
        self.tex, self.tex_end = read_tex_table(s1)
        self.page_recs = [(i, s, o) for i, (t, s, o) in enumerate(self.recs)
                          if t == N.FONTPAGE_TAG]
        self.desc_recs = [(i, s, o) for i, (t, s, o) in enumerate(self.recs)
                          if t == N.FONTDESC_TAG]
        self.list_recs = [(i, s, o) for i, (t, s, o) in enumerate(self.recs)
                          if t == N.FONTPAGELIST_TAG]
        # 메인 폰트 = 첫 정의 (같은 정의가 두 벌 있고 페이지를 공유한다)
        di, dsz, doff = self.desc_recs[0]
        li, lsz, loff = self.list_recs[0]
        self.desc = F.parse_desc(s1[doff:doff + dsz])
        self.page_ids = list(struct.unpack_from(f"<{lsz // 4}I", s1, loff))
        id2res = {pid: i for i, (pid, *_) in enumerate(self.tex)}
        self.page_res = [id2res[p] for p in self.page_ids]
        # 페이지 비트맵
        self.pages = []
        self.page_fmt = []
        for res in self.page_res:
            _i, size, off = self.page_recs[res]
            dim = self.tex[res][2]
            bpp, levels = F.guess_format(size, dim)
            self.pages.append(F.decode_page(s3[off:off + size], dim, bpp))
            self.page_fmt.append((dim, bpp, levels))

    # ---------------------------------------------------------------- 배치
    @staticmethod
    def layout(glyphs):
        """[(key, a, b, c, d)] -> [(page, x, y, w)]  같은 순서"""
        place = []
        pi = x = y = 0
        for _k, _a, b, _c, _d in glyphs:
            if x + b > PAGE_DIM:
                x = 0
                y += ROW_H
                if y + ROW_H > PAGE_DIM:
                    pi += 1
                    y = 0
            place.append((pi, x, y, b))
            x += b
        return place

    def cells(self):
        """원본 글리프 비트맵을 {문자: (셀 2차원 배열, a, b, c, d)} 로 뽑는다."""
        place = self.layout(self.desc["glyphs"])
        out = {}
        for (key, a, b, c, d), (pi, x, y, w) in zip(self.desc["glyphs"], place):
            ch = char_of(key)
            out[ch] = (self.pages[pi][y:y + ROW_H, x:x + w].copy(), a, b, c, d)
        return out


def char_of(key):
    """정의의 글리프 키 -> 문자. 한 글자면 그대로, 여러 자리 숫자면 코드포인트."""
    return key if len(key) == 1 else (chr(int(key)) if key.isdigit() else key)


def key_of(ch):
    """문자 -> 정의에 적을 키. ASCII 출력 가능 문자는 그대로, 나머지는 10진 코드포인트."""
    return ch if 0x21 <= ord(ch) <= 0x7E else str(ord(ch))


def render_desc(desc, glyphs):
    """정의 텍스트를 다시 만든다. 줄바꿈 CRLF, 꼬리 공백까지 보존."""
    return F.render_desc(desc, glyphs)


def encode_pages(pages, fmts):
    """[2차원 배열] -> [밉 포함 바이트열]"""
    return [F.build_mips(p, bpp, levels) for p, (dim, bpp, levels) in zip(pages, fmts)]
