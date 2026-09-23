# -*- coding: utf-8 -*-
"""한글판 CIA/3DS 만들기 — 개발 도구(build_cia.py)와 배포 패처(release/patcher)가 함께 쓰는 핵심.

payload 폴더 구조
  manifest.json        버전, 타이틀 ID, 교체 대상 원본 파일 MD5
  romfs/init.jp        게임 안 텍스트 + 한글 폰트
  romfs/init.dict      위 파일의 청크 표 (짝으로 넣어야 한다)
  common6_rgba8.bin    배너 띠(COMMON6 256x16 RGBA8) 한글판 — 미리 인코딩해 둔 것
  titles.json          HOME 메뉴 짧은 제목·긴 제목·발행사

순서
  1. pyctr 로 CIA 콘텐츠 / 3DS 파티션을 모두 복호화 (본편은 seed 암호화 → boot9.bin·seeddb.bin 필요)
  2. 3dstool 로 본편 CXI 를 펼쳐 ExeFS 의 banner·icon 을 고치고, romfs 의 init.jp·init.dict 를 교체
  3. 3dstool 로 평문 CXI(--not-encrypt)를 다시 싸고 makerom 으로 CIA 또는 3DS(CCI)로 묶는다

겪어 본 함정
  * makerom 에 -ignoresign 이 없으면 "Content 0 Is Corrupt" 가 난다.
  * -content 는 <파일>:<인덱스>:<콘텐츠ID> 세 칸 형식이어야 하고, 인덱스가 이어져 있어야 한다.
    업데이트 타이틀은 인덱스가 0·2 라서 다시 묶을 수 없다. 어차피 본편만 고치면 된다.
  * CXI 를 --not-encrypt 로 만들어야 makerom 이 exheader 를 읽어 meta 영역까지 만든다.
  * 타이틀 버전은 makerom 이 exheader 의 remaster version(0)을 따라가서 -ver 가 안 먹는다.
    그래서 결과 CIA 의 TMD 버전 필드(2바이트 빅엔디언)를 원본 값으로 직접 덮어쓴다.
  * code.bin 은 손대지 않으므로 exheader 의 CompressExefsCode 플래그는 그대로 둔다.
  * 외부 도구는 한글 경로를 제대로 못 받을 수 있어서, 작업 폴더를 cwd 로 두고 짧은 영문 상대 경로만 넘긴다.
  * locale.txt 는 Luma 기능이라 CIA 에 담을 수 없다. 일본판이 아닌 리전 본체에서는
    SD 에 따로 둬야 게임이 시작한다.
"""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lz11

TID = '000400000016ce00'
UPDATE_TID = '0004000e0016ce00'
COMMON6_TXOB = 0x3924             # 배너 CGFX 안 COMMON6 텍스처의 TXOB 위치
PAYLOAD_FILES = ('init.jp', 'init.dict')

log = print


# ---------------------------------------------------------------- 키

def key_dirs(extra=()):
    env = os.environ
    return [d for d in list(extra) + [
        os.path.join(env.get('APPDATA', ''), 'Azahar', 'sysdata'),
        os.path.join(env.get('APPDATA', ''), 'Citra', 'sysdata'),
        os.path.join(env.get('APPDATA', ''), 'Lime3DS', 'sysdata'),
        os.path.join(os.path.expanduser('~'), '.3ds'),
        os.path.join(os.path.expanduser('~'), '3ds'),
    ] if d]


def find_key(name, dirs):
    for d in dirs:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------- 배너·아이콘

def patch_banner(b, strip):
    """배너(CBMD) 안 LZ11 압축 CGFX 의 COMMON6 띠를 한글판 그림으로 바꾼다.

    나머지 텍스처(METROID PRIME / FEDERATION FORCE 로고, 엠블럼)는 원래 영문이라 그대로 둔다.
    """
    if b[:4] != b'CBMD':
        raise SystemExit('배너(CBMD) 형식이 아닙니다.')
    table = struct.unpack_from('<17I', b, 0x08)
    if table[0] != 0x88 or any(table[1:]):
        raise SystemExit('배너 구조가 예상과 다릅니다: %s' % (tuple(hex(x) for x in table),))
    cwav = struct.unpack_from('<I', b, 0x84)[0]
    cgfx = bytearray(lz11.decompress(b[0x88:cwav]))

    W = struct.unpack_from('<20I', cgfx, COMMON6_TXOB)
    h, w, size = W[6], W[7], W[17]
    data = COMMON6_TXOB + 18 * 4 + W[18]
    if (w, h, size) != (256, 16, 0x4000) or len(strip) != size:
        raise SystemExit('배너 띠 형식이 예상과 다릅니다: %dx%d %d바이트' % (w, h, size))
    cgfx[data:data + size] = strip

    comp = lz11.compress(bytes(cgfx))
    if lz11.decompress(comp) != bytes(cgfx):
        raise SystemExit('배너 LZ11 압축 왕복에 실패했습니다.')
    new_cwav = (0x88 + len(comp) + 0x1F) & ~0x1F
    out = bytearray(b[:0x88])
    struct.pack_into('<I', out, 0x84, new_cwav)
    out += comp
    out += b'\0' * (new_cwav - len(out))
    out += b[cwav:]
    return bytes(out)


def patch_smdh(icon, short, long_, publisher):
    """아이콘(SMDH)의 제목을 12개 언어 칸 전부 한국어로. 시스템 언어와 무관하게 한글로 보이게 한다."""
    out = bytearray(icon)
    if out[:4] != b'SMDH':
        raise SystemExit('아이콘(SMDH) 형식이 아닙니다.')

    def put(off, text, chars):
        raw = text.encode('utf-16-le')
        if len(raw) >= chars * 2:
            raise SystemExit('제목이 너무 깁니다: %r' % text)
        out[off:off + chars * 2] = raw + b'\0' * (chars * 2 - len(raw))

    for i in range(12):
        base = 8 + i * 0x200
        put(base, short, 0x40)
        put(base + 0x80, long_, 0x80)
        put(base + 0x180, publisher, 0x40)
    return bytes(out)


def read_exefs(d):
    """ExeFS 블롭 -> {이름: 내용}"""
    out = {}
    for i in range(10):
        name, off, size = struct.unpack_from('<8sII', d, i * 16)
        if size:
            out[name.rstrip(b'\0').decode()] = d[0x200 + off:0x200 + off + size]
    return out


def rebuild_exefs(d, patches):
    """헤더의 오프셋·크기·SHA-256 을 다시 계산해 ExeFS 를 통째로 새로 쓴다.

    .code 는 ExeFS 안에서 압축돼 있으므로 원본 블롭을 그대로 옮긴다.
    """
    entries = []
    for i in range(10):
        name, off, size = struct.unpack_from('<8sII', d, i * 16)
        if not size:
            continue
        key = name.rstrip(b'\0').decode()
        entries.append((name, patches.get(key, d[0x200 + off:0x200 + off + size])))
    hdr = bytearray(0x200)
    blob = bytearray()
    for i, (name, body) in enumerate(entries):
        struct.pack_into('<8sII', hdr, i * 16, name, len(blob), len(body))
        hdr[0x200 - (i + 1) * 32:0x200 - i * 32] = hashlib.sha256(body).digest()
        blob += body
        blob += b'\0' * ((-len(blob)) % 0x200)
    return bytes(hdr) + bytes(blob)


# ---------------------------------------------------------------- 도구 실행

class Tools:
    def __init__(self, bindir, work):
        self.bin = bindir
        self.work = work

    def run(self, name, args, logname):
        exe = os.path.join(self.bin, name + ('.exe' if os.name == 'nt' else ''))
        with open(os.path.join(self.work, logname + '.log'), 'wb') as f:
            r = subprocess.run([exe] + args, cwd=self.work, stdout=f, stderr=subprocess.STDOUT)
        if r.returncode:
            tail = open(os.path.join(self.work, logname + '.log'), encoding='utf-8', errors='replace').read()[-1500:]
            raise SystemExit('%s 실패:\n%s' % (name, tail))


def md5_file(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- 입력

KEY_HELP = ' 암호화된 파일은 boot9.bin 과 seeddb.bin 이 필요합니다. README_한국어.txt 를 확인하세요.'


def key_error(e):
    name = type(e).__name__
    if 'Seed' in name:
        return 'seed 암호화를 풀 seeddb.bin 이 없거나 이 게임의 seed 가 들어 있지 않습니다.' + KEY_HELP
    if 'Bootrom' in name or 'Keyslot' in name:
        return '암호화를 풀 boot9.bin 을 찾지 못했습니다.' + KEY_HELP
    return '파일을 읽지 못했습니다 (%s: %s).%s' % (name, e, KEY_HELP)


def wrong_title(tid):
    if tid == UPDATE_TID:
        return ('업데이트(v1.2.0) 파일입니다. 본편 CIA 만 패치하면 되고, 업데이트는 원본 그대로 '
                '설치해도 한글 제목과 배너가 유지됩니다.')
    return '일본판 페더레이션 포스(%s)가 아닙니다: %s' % (TID, tid)


def raw_cci_partitions(path):
    """키 없이 3DS(NCSD)의 파티션 위치를 읽는다. 모두 평문(NoCrypto)이어야 한다 → [(번호, 오프셋, 크기)]"""
    with open(path, 'rb') as f:
        h = f.read(0x200)
        if h[0x100:0x104] != b'NCSD':
            raise SystemExit('3DS(NCSD) 파일이 아닙니다.')
        out = []
        for i in range(8):
            off, size = struct.unpack_from('<II', h, 0x120 + i * 8)
            if not size:
                continue
            f.seek(off * 0x200)
            n = f.read(0x200)
            if n[0x100:0x104] != b'NCCH':
                raise SystemExit('파티션 %d 가 NCCH 가 아닙니다.' % i)
            if not n[0x18F] & 0x04:
                raise SystemExit('암호화된 3DS 파일입니다.' + KEY_HELP)
            if i == 0:
                tid = '%016x' % struct.unpack_from('<Q', n, 0x118)[0]
                if tid != TID:
                    raise SystemExit(wrong_title(tid))
            out.append((i, off * 0x200, size * 0x200))
    return out


def raw_cia_contents(path):
    """키 없이 CIA 콘텐츠 위치를 읽는다. 콘텐츠·NCCH 모두 평문이어야 한다 → ([(번호, ID, 오프셋, 크기)], 버전)"""
    al = lambda x: (x + 63) & ~63
    with open(path, 'rb') as f:
        hsize, _t, _v, clen, tlen, tmdlen, _m = struct.unpack('<IHHIIII', f.read(0x18))
        tmd_off = al(al(al(hsize) + clen) + tlen)
        f.seek(tmd_off)
        tmd = f.read(tmdlen)
        body = 4 + SIG[struct.unpack_from('>I', tmd, 0)[0]]
        v = struct.unpack_from('>H', tmd, body + 0x9C)[0]
        count = struct.unpack_from('>H', tmd, body + 0x9E)[0]
        rec = body + 0x9C + 4 + 0x24 + 36 * 64
        off = al(tmd_off + tmdlen)
        out = []
        for i in range(count):
            cid, idx, ctype, size = struct.unpack_from('>IHHQ', tmd, rec + i * 0x30)
            if ctype & 1:
                raise SystemExit('암호화된 CIA 입니다.' + KEY_HELP)
            f.seek(off)
            n = f.read(0x200)
            if n[0x100:0x104] != b'NCCH' or not n[0x18F] & 0x04:
                raise SystemExit('암호화된 CIA 입니다.' + KEY_HELP)
            out.append((idx, cid, off, size))
            off = al(off + size)
    return out, '%d.%d.%d' % (v >> 10, (v >> 4) & 63, v & 15)


SIG = {0x10000: 0x23C, 0x10001: 0x13C, 0x10002: 0x7C, 0x10003: 0x23C, 0x10004: 0x13C, 0x10005: 0x7C}


# ---------------------------------------------------------------- 본체

def patch(src, dst, payload, bindir, work, key_extra=(), keep=False):
    """src(.cia/.3ds) → dst. 형식은 dst 확장자로 정한다(.cia / .3ds). 실패해도 작업 폴더는 지운다."""
    try:
        return _patch(src, dst, payload, bindir, work, key_extra)
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)


def _patch(src, dst, payload, bindir, work, key_extra):
    man = json.load(open(os.path.join(payload, 'manifest.json'), encoding='utf-8'))
    titles = json.load(open(os.path.join(payload, 'titles.json'), encoding='utf-8'))
    strip = open(os.path.join(payload, 'common6_rgba8.bin'), 'rb').read()
    romfs_dir = os.path.join(payload, 'romfs')
    out_kind = os.path.splitext(dst)[1].lower()
    if out_kind not in ('.cia', '.3ds'):
        raise SystemExit('결과 파일 확장자는 .cia 또는 .3ds 여야 합니다.')

    dirs = key_dirs(key_extra)
    boot9 = find_key('boot9.bin', dirs)
    seeddb = find_key('seeddb.bin', dirs)
    # pyctr 는 키 경로를 환경 변수에서 읽는다(3DS 리더는 crypto 인자를 받지 않음)
    if boot9:
        os.environ['BOOT9_PATH'] = boot9
    if seeddb:
        os.environ['SEEDDB_PATH'] = seeddb
    from pyctr.crypto import CryptoEngine, load_seeddb
    from pyctr.type.ncch import NCCHSection
    if seeddb:
        load_seeddb(seeddb)

    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    T = Tools(bindir, work)
    W = lambda n: os.path.join(work, n)

    # 1) 읽기·복호화 → 작업 폴더에 평문 NCCH(p0 본편, p1 설명서 …)
    kind = os.path.splitext(src)[1].lower()
    if kind not in ('.cia', '.3ds', '.cci'):
        raise SystemExit('.cia 또는 .3ds 파일만 넣을 수 있습니다.')
    try:
        if kind == '.cia' and not boot9:
            rd = None
            raw, ver = raw_cia_contents(src)
            recs = [(i, off, size) for i, _c, off, size in raw]
            cids = {i: c for i, c, _o, _s in raw}
        elif kind == '.cia':
            from pyctr.type.cia import CIAReader
            rd = CIAReader(src, crypto=None if boot9 else CryptoEngine(setup_b9_keys=False))
            recs = [(r.cindex, int(r.id, 16)) for r in rd.tmd.chunk_records]
            ver = str(rd.tmd.title_version)
            parts = {idx: rd.contents[idx] for idx, _ in recs}
        elif boot9:
            from pyctr.type.cci import CCIReader
            rd = CCIReader(src)
            parts = {int(k): v for k, v in rd.contents.items()}
            recs = [(i, i) for i in sorted(parts)]
            ver = None
        else:
            rd = None
            recs = raw_cci_partitions(src)
            ver = None
            cids = {}
        if rd is not None:
            pid = str(parts[0].program_id).lower() if 0 in parts else None
            if pid != TID:
                raise SystemExit(wrong_title(pid))
            for idx, _ in recs:
                log('복호화: %s %d' % ('콘텐츠' if kind == '.cia' else '파티션', idx))
                with parts[idx].open_raw_section(NCCHSection.FullDecrypted) as f, open(W('p%d.ncch' % idx), 'wb') as o:
                    shutil.copyfileobj(f, o, 1 << 24)
            rd.close()
        else:
            for idx, off, size in recs:
                log('복사: %s %d (이미 복호화된 파일)' % ('콘텐츠' if kind == '.cia' else '파티션', idx))
                with open(src, 'rb') as f, open(W('p%d.ncch' % idx), 'wb') as o:
                    f.seek(off)
                    left = size
                    while left:
                        b = f.read(min(left, 1 << 24))
                        o.write(b)
                        left -= len(b)
            recs = [(i, cids[i] if kind == '.cia' else i) for i, _, _ in recs]
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(key_error(e))

    if sorted(i for i, _ in recs) != list(range(len(recs))):
        raise SystemExit('콘텐츠 번호가 이어져 있지 않아 다시 묶을 수 없습니다: %s'
                         % sorted(i for i, _ in recs))

    with open(W('p0.ncch'), 'rb') as f:
        h = f.read(0x200)
    tid = '%016x' % struct.unpack_from('<Q', h, 0x118)[0]
    if h[0x100:0x104] != b'NCCH' or tid != TID:
        raise SystemExit(wrong_title(tid))

    # 2) 본편 펼치기·교체
    cx = ['--header', 'hdr.bin', '--exh', 'exh.bin', '--logo', 'logo.bin', '--plain', 'plain.bin',
          '--exefs', 'exefs.bin', '--romfs', 'romfs.bin']
    log('본편 펼치는 중...')
    T.run('3dstool', ['-xvtf', 'cxi', 'p0.ncch'] + cx, 'xcxi')
    os.remove(W('p0.ncch'))
    ex = open(W('exefs.bin'), 'rb').read()
    src_ex = read_exefs(ex)
    patches = {'banner': patch_banner(src_ex['banner'], strip),
               'icon': patch_smdh(src_ex['icon'], titles['short'], titles['long'], titles['publisher'])}
    open(W('exefs.bin'), 'wb').write(rebuild_exefs(ex, patches))
    log('HOME 메뉴 배너·게임 이름 교체')

    T.run('3dstool', ['-xvtf', 'romfs', 'romfs.bin', '--romfs-dir', 'rx'], 'xromfs')
    log('원본 확인 중...')
    for rel, want in man['source_md5'].items():
        p = W(os.path.join('rx', *rel.split('/')))
        if not os.path.exists(p) or md5_file(p) != want:
            raise SystemExit('원본 파일이 다릅니다: %s. 이미 패치한 파일이거나 다른 버전입니다.' % rel)
    n = 0
    for name in PAYLOAD_FILES:
        s = os.path.join(romfs_dir, name)
        d = W(os.path.join('rx', name))
        if not os.path.exists(d):
            raise SystemExit('원본에 없는 파일: ' + name)
        shutil.copyfile(s, d)
        n += 1
    log('게임 안 한글 파일 %d개 교체' % n)
    T.run('3dstool', ['-cvtf', 'romfs', 'romfs.bin', '--romfs-dir', 'rx'], 'cromfs')
    shutil.rmtree(W('rx'))
    log('다시 묶는 중...')
    T.run('3dstool', ['-cvtf', 'cxi', 'p0.ncch'] + cx + ['--not-encrypt'], 'ccxi')

    # 3) CIA / 3DS 로 묶기
    args = ['-f', 'cia' if out_kind == '.cia' else 'cci', '-o', 'out' + out_kind, '-ignoresign']
    for idx, cid in recs:
        args += ['-content', 'p%d.ncch:%d:%d' % (idx, idx, cid)]     # 3DS(CCI)도 세 칸 형식이어야 한다
    T.run('makerom', args, 'makerom')
    if out_kind == '.cia' and ver:
        fix_tmd_version(W('out.cia'), ver)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(W('out' + out_kind), dst)
    return dst


def fix_tmd_version(cia, ver):
    """makerom 이 0 으로 써 버리는 TMD 타이틀 버전을 원본 값으로 되돌린다."""
    want = [int(x) for x in str(ver).split('.')]
    want = want[0] << 10 | want[1] << 4 | want[2]
    al = lambda x: (x + 63) & ~63
    with open(cia, 'r+b') as f:
        hsize, _t, _v, clen, tlen, tmdlen, _m = struct.unpack('<IHHIIII', f.read(0x18))
        off = al(al(al(hsize) + clen) + tlen)
        f.seek(off)
        sig = struct.unpack('>I', f.read(4))[0]
        o = off + 4 + SIG[sig] + 0x9C
        f.seek(o)
        cur = struct.unpack('>H', f.read(2))[0]
        if cur != want:
            f.seek(o)
            f.write(struct.pack('>H', want))
