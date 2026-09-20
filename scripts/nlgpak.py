"""
Federation Force (3DS) NLG pak / 문자열 테이블 도구.

컨테이너
--------
`<name>.data` 와 `<name>.<lang>` 는 모두 같은 컨테이너다.
  - zlib(level 6) 스트림을 이어붙인 것. 각 스트림은 8바이트 경계에서 시작하고
    사이는 0x00 패딩. 파일이 0x78로 시작하지 않으면 무압축(단일 섹션) pak.
  - 압축 pak은 항상 4섹션(.lang) / 3섹션(.data).

리소스 인덱스
-------------
`.<lang>` 의 섹션 0 전체가 12바이트 레코드 배열이다.
    u32 typeTag ; u32 size ; u32 offset
offset 은 typeTag 가 지정하는 "컨테이너+섹션" 안에서의 상대 오프셋.
init.jp 에서 확인된 매핑:
    0x1201b312 등 0x..01b3.. 계열 -> init.data  섹션1
    0x2701b502                   -> init.data  섹션2
    0x33027011 / 0x33027012      -> init.jp    섹션1 (폰트 정의 / 페이지 목록)
    0x42027020                   -> init.jp    섹션2 (문자열 테이블, 레코드 1개)
    0x5701b502                   -> init.jp    섹션3 (폰트 텍스처 페이지)
섹션별로 오프셋이 독립이므로, 어떤 섹션의 크기를 바꾸면
그 섹션에 속한 레코드의 size/offset 만 갱신하면 된다.

문자열 테이블 (0x42027020)
--------------------------
    u32 languageIndex      (JP=1, 북미 영어=0)
    u32 count              (2119)
    count * { u32 nameHash ; u32 charOffset }
    UTF-16LE 문자열들, 0x0000 종단
charOffset 은 문자열 블롭 시작부터의 UTF-16 코드유닛 단위(바이트 = *2).
"""

import struct
import zlib

ALIGN = 8
ZLEVEL = 6

STRTAB_TAG = 0x42027020
FONTDESC_TAG = 0x33027011
FONTPAGELIST_TAG = 0x33027012
FONTPAGE_TAG = 0x5701B502


# --------------------------------------------------------------------------
# 컨테이너
# --------------------------------------------------------------------------
def unpack_container(data):
    """바이트열 -> 압축 해제된 섹션 리스트. 무압축 pak은 [data] 하나."""
    if not data[:1] == b"\x78":
        return [data]
    sections = []
    pos = 0
    while pos < len(data):
        obj = zlib.decompressobj()
        raw = obj.decompress(data[pos:])
        used = len(data) - pos - len(obj.unused_data)
        sections.append(raw)
        pos = (pos + used + ALIGN - 1) & ~(ALIGN - 1)
    return sections


def pack_container(sections, compressed=True):
    """섹션 리스트 -> 바이트열. 원본과 동일한 규칙으로 재조립한다."""
    if not compressed:
        assert len(sections) == 1
        return sections[0]
    out = bytearray()
    for i, raw in enumerate(sections):
        out += zlib.compress(raw, ZLEVEL)
        if i + 1 < len(sections):
            while len(out) % ALIGN:
                out += b"\x00"
    return bytes(out)


# --------------------------------------------------------------------------
# 리소스 인덱스
# --------------------------------------------------------------------------
def parse_index(section0):
    """섹션0 -> [(typeTag, size, offset), ...]"""
    assert len(section0) % 12 == 0, "섹션0 길이가 12의 배수가 아니다"
    return [struct.unpack_from("<III", section0, i * 12)
            for i in range(len(section0) // 12)]


def build_index(records):
    out = bytearray()
    for tag, size, off in records:
        out += struct.pack("<III", tag, size, off)
    return bytes(out)


def find_records(records, tag):
    """해당 태그 레코드의 [(index, size, offset), ...]"""
    return [(i, s, o) for i, (t, s, o) in enumerate(records) if t == tag]


# --------------------------------------------------------------------------
# 문자열 테이블
# --------------------------------------------------------------------------
def parse_strings(blob):
    """문자열 테이블 -> (languageIndex, [(hash, text), ...] 원래 순서)"""
    lang, count = struct.unpack_from("<II", blob, 0)
    base = 8 + count * 8
    entries = []
    for i in range(count):
        h, coff = struct.unpack_from("<II", blob, 8 + i * 8)
        start = base + coff * 2
        end = start
        while end + 1 < len(blob) and blob[end:end + 2] != b"\x00\x00":
            end += 2
        entries.append((h, blob[start:end].decode("utf-16le")))
    return lang, entries


def blob_order_of(blob):
    """원본 테이블의 블롭 작성 순서(엔트리 인덱스 배열)를 뽑는다."""
    lang, count = struct.unpack_from("<II", blob, 0)
    offs = [struct.unpack_from("<II", blob, 8 + i * 8)[1] for i in range(count)]
    return sorted(range(count), key=lambda i: offs[i])


def build_strings(lang, entries, pad_to=None, blob_order=None):
    """(languageIndex, [(hash, text), ...]) -> 문자열 테이블 바이트열.

    원본은 **중복을 제거하지 않고** 2,119개 문자열을 각각 따로 저장하며,
    블롭 순서는 엔트리 순서(해시 오름차순)와 다른 별개의 작성 순서다.
    중복을 합치거나 블롭 순서를 바꾸면 게임이 문자열을 하나도 못 읽는다
    (에뮬레이터 실측 확인). 그래서 기본값은 무중복 + 주어진 블롭 순서다.

    blob_order: 블롭에 기록할 엔트리 인덱스 순서. None 이면 엔트리 순서.
    pad_to: 그 길이까지 0x00 으로 채운다(섹션 크기 고정용).
    """
    count = len(entries)
    order = list(range(count)) if blob_order is None else list(blob_order)
    if sorted(order) != list(range(count)):
        raise ValueError("blob_order 가 엔트리 인덱스 전체의 순열이 아니다")
    blob = bytearray()
    offsets = [0] * count
    for i in order:
        offsets[i] = len(blob) // 2
        blob += entries[i][1].encode("utf-16le") + b"\x00\x00"
    out = bytearray(struct.pack("<II", lang, count))
    for (h, _), coff in zip(entries, offsets):
        out += struct.pack("<II", h, coff)
    out += blob
    if pad_to is not None:
        if len(out) > pad_to:
            raise ValueError(f"문자열 테이블이 {len(out)}바이트로 한도 {pad_to}를 넘었다")
        out += b"\x00" * (pad_to - len(out))
    return bytes(out)


# --------------------------------------------------------------------------
# .dict — pak 계열의 청크 테이블
# --------------------------------------------------------------------------
# 레이아웃:
#   0x00 u32 magic 0xa9f32458
#   0x04 u32 버전/카운트
#   0x08 u32 이 pak 의 최대 압축 청크 크기 (무압축이면 0)
#   0x0C u32 266802 — 614개 dict 전부 동일한 전역 상수. 건드리지 않는다.
#   0x10 .. S     16바이트 이름 엔트리 {u32 hash, u16, u16, u8[8] 조각인덱스}
#   S    .. T     16바이트 청크 엔트리 {u32 압축오프셋, u32 원본크기, u32 압축크기, u32 flags}
#                 flags: bit16-23 = 확장자 인덱스, 하위바이트 = 정렬/플래그
#   T    .. end   확장자 문자열들 (".efigs\0.debug\0.jp\0.data\0")
#
# 게임은 이 테이블의 압축 오프셋으로 시크해서 압축크기만큼 읽는다.
# 따라서 언어 pak 을 다시 압축했으면 반드시 여기도 갱신해야 한다.
# (갱신하지 않으면 문자열이 하나도 표시되지 않는다 — 에뮬레이터 실측 확인)

DICT_MAGIC = 0xA9F32458
_CHUNK_FLAG_LOW = (0x04, 0x08, 0x10, 0x20, 0x40, 0x80)


def parse_dict(data):
    """.dict -> (exts, table_start, table_end, [(entry_off, ext_index, comp_off, raw, comp, flags)])"""
    if struct.unpack_from("<I", data, 0)[0] != DICT_MAGIC:
        raise ValueError("dict 매직이 맞지 않는다")
    # 확장자 문자열 영역: 16바이트 정렬 경계에서 시작하는 첫 '.' 문자열
    end = None
    for off in range(0x10, len(data) - 1, 16):
        if data[off:off + 1] == b"." and b"\x00" in data[off:]:
            end = off
            break
    if end is None:
        raise ValueError("확장자 문자열 영역을 찾지 못했다")
    exts = [x.decode() for x in data[end:].split(b"\x00") if x]

    def looks(off):
        a, b, c, fl = struct.unpack_from("<4I", data, off)
        return ((fl >> 24) <= 1 and ((fl >> 16) & 0xFF) < len(exts)
                and ((fl >> 8) & 0xFF) == 0 and (fl & 0xFF) in _CHUNK_FLAG_LOW
                and b > 0 and c > 0 and c <= b)

    start = end
    while start - 16 >= 0x10 and looks(start - 16):
        start -= 16
    rows = []
    for off in range(start, end, 16):
        a, b, c, fl = struct.unpack_from("<4I", data, off)
        rows.append((off, (fl >> 16) & 0xFF, a, b, c, fl))
    return exts, start, end, rows


def patch_dict(data, ext, chunks):
    """확장자 ext(예 '.jp')의 청크 엔트리를 chunks=[(comp_off, raw, comp), ...] 로 교체.

    엔트리 순서는 파일 안의 청크 순서와 같다고 본다(원본에서 확인됨).
    헤더 0x08(이 pak 최대 압축 크기)도 다시 계산한다.
    """
    exts, start, end, rows = parse_dict(data)
    if ext not in exts:
        raise ValueError(f"{ext} 가 dict 확장자 목록 {exts} 에 없다")
    ei = exts.index(ext)
    target = [r for r in rows if r[1] == ei]
    if len(target) != len(chunks):
        raise ValueError(f"{ext} 엔트리 {len(target)}개 vs 청크 {len(chunks)}개")
    out = bytearray(data)
    for (entry_off, _ei, _a, _b, _c, flags), (co, raw, comp) in zip(target, chunks):
        struct.pack_into("<4I", out, entry_off, co, raw, comp, flags)
    # 헤더 0x08 재계산
    _, _, _, rows2 = parse_dict(bytes(out))
    struct.pack_into("<I", out, 8, max(r[4] for r in rows2))
    return bytes(out)


def container_chunk_table(data):
    """컨테이너 바이트열 -> [(압축오프셋, 원본크기, 압축크기), ...]"""
    if not data[:1] == b"\x78":
        return []
    res = []
    pos = 0
    while pos < len(data):
        obj = zlib.decompressobj()
        raw = obj.decompress(data[pos:])
        used = len(data) - pos - len(obj.unused_data)
        res.append((pos, len(raw), used))
        pos = (pos + used + ALIGN - 1) & ~(ALIGN - 1)
    return res


# --------------------------------------------------------------------------
# 고수준 도우미
# --------------------------------------------------------------------------
def load_pak(path):
    return unpack_container(open(path, "rb").read())


def strtab_section(sections, records):
    """문자열 테이블이 어느 섹션인지 찾는다. 섹션 크기와 레코드 size 가 맞는 것."""
    hits = find_records(records, STRTAB_TAG)
    if len(hits) != 1:
        raise ValueError(f"문자열 테이블 레코드가 {len(hits)}개다")
    idx, size, off = hits[0]
    for si, sec in enumerate(sections):
        if off == 0 and size == len(sec):
            return si, idx
    raise ValueError("문자열 테이블 섹션을 찾지 못했다")
