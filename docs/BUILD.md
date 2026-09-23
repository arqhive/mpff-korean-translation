# 직접 빌드하기

## 1. 한글 패치 파일 만들기 (LayeredFS 용)

일본판 romfs 가 있어야 한다. `base_jp/romfs/` 에 풀어 둔다. 최소한 이 두 파일이
필요하다.

```
base_jp/romfs/init.jp
base_jp/romfs/init.dict
```

`ctrtool` 로 CIA 에서 뽑는 방법:

```bash
ctrtool --contents=c "일본판.cia"                     # c.0000.00000003 이 메인 CXI
3dstool -xvtf cxi c.0000.00000003 --romfs romfs.bin \
        --header h.bin --exh exh.bin --logo logo.bin --plain plain.bin --exefs exefs.bin
3dstool -xvtf romfs romfs.bin --romfs-dir base_jp/romfs
```

`boot9.bin` 을 `%USERPROFILE%/.3ds/boot9.bin` 에 두면 ctrtool 이 알아서 복호화한다
(GM9 덤프 위치는 `sd:/gm9/out/boot9.bin`).

그다음:

```bash
pip install pillow numpy
python scripts/build_patch.py
```

`out/init.jp` 와 `out/init.dict` 가 나온다. 이 두 파일을 SD 카드의
`luma/titles/000400000016CE00/romfs/` 에 넣으면 끝이다.

배포용 zip 까지 만들려면:

```bash
python scripts/make_release.py
```

### 빌드 로그 읽기

```
번역 2117/2119개 적용 (99%)        ← 해시가 겹치는 2행이 합쳐져서 2117 이 정상이다
한글 고유 음절 775자
고정 페이지 위 글리프 112자 (ETC1A4)
글리프 1130 -> 1318 (일본어 587자 제거, 그중 아직 쓰이는 글자 0자), 페이지 19/19
다시 그리는 페이지 16장: [3, 4, ...]
init.jp 369,502바이트, 섹션 [41916, 81632, 190688, 989952]
아틀라스: 한글 775자 사용 / 번역 완료 시 최대 1,308자
```

- **"아직 쓰이는 글자"가 0 이 아니면** 번역이 덜 끝난 상태다. 남은 일본어 문장이
  쓰는 글자를 자리 부족으로 덜어냈다는 뜻이고, 그 글자는 화면에서 빈칸이 된다.
- **"글리프 없는 문자" 경고가 나오면** 번역문에 아틀라스에 없는 기호가 들어갔다.
  그 문자는 빈칸으로 나오니 반드시 고쳐야 한다. 실제로 가운뎃점 `·`(U+00B7)이
  이렇게 걸렸다.
- 섹션 3 은 989,952바이트를 넘길 수 없다. 넘기면 부팅 중 크래시한다.
- **`섹션3 압축 ... 여유 -N` 이 나오면 빌드가 실패한다.** 섹션3 의 압축 크기가
  272,729바이트를 넘으면 실기에서 게임 시작 직후 크래시한다(에뮬레이터는 통과).
  `NIBBLE_MASK` 를 더 낮추거나 한글 음절 수를 줄여야 한다.

## 실기 테스트는 LayeredFS 로 하라

CIA 재빌드는 10분 걸리지만 LayeredFS 는 파일 두 개 복사로 끝난다.

```
sd:/luma/titles/000400000016CE00/romfs/init.jp
sd:/luma/titles/000400000016CE00/romfs/init.dict
```

**반드시 둘을 짝으로 넣어라.** `.dict` 는 `.jp` 의 청크 오프셋·크기 표이므로 한쪽만
덮으면 조용히 깨져서 크래시한다. 그리고 **테스트 전에 그 폴더에 남의 패치가 있는지
확인하라** — 이 프로젝트에서 옛 아마추어 패치의 `init.jp` 가 남아 있어 내 패치가
아예 실행되지 않는 상태로 여섯 번을 헛테스트했다.

무엇을 바꾸든 **원본을 layer 에 넣은 대조군을 먼저 돌려라.** 기준점 없이 변종을
돌리면 "전부 크래시"에서 아무 정보도 못 얻는다.

## 2. 한글판 CIA / 3DS 만들기 (HOME 메뉴 배너까지)

LayeredFS 는 HOME 메뉴의 제목·배너를 바꾸지 못한다. 거기까지 원하면 CIA 를
다시 만들어야 한다. 게임 데이터를 배포할 수 없으니 각자 PC 에서 돌려야 한다.
배포용 패처(`release/patcher`)와 개발용 `scripts/build_cia.py` 는 같은
`scripts/ffpatch.py` 를 쓴다 — 고칠 일이 있으면 그 파일만 고치면 둘 다 바뀐다.

### 준비물

| | |
|---|---|
| 일본판 CIA 또는 3DS | `000400000016CE00` |
| 3dstool · makerom | `tools/` 에 두거나 `--tools` 로 폴더 지정 |
| pyctr · pycryptodomex | `pip install pyctr pycryptodomex` |
| boot9.bin · seeddb.bin | Azahar 의 `sysdata`, `%USERPROFILE%/.3ds` 등에서 자동으로 찾는다 |
| 디스크 여유 | 6GB 이상 |

이 게임은 **seed 암호화**를 쓴다. 암호화된 원본을 넣으려면 `boot9.bin` 만으로는
안 되고 `seeddb.bin` 도 있어야 한다. 이미 복호화된 파일은 키 없이 된다.

### 실행

**본편 CIA 만** 다시 만들면 된다. 업데이트 타이틀은 그대로 설치해도
본편의 한국어 제목·아이콘·배너가 유지된다(실기 확인).

```bash
python scripts/build_patch.py                       # 먼저 out/ 을 만들어 둔다
python scripts/build_cia.py --cia "일본판.cia" --out "한글판.cia"
python scripts/build_cia.py --cia "일본판.3ds" --out "한글판.3ds"
```

결과 형식은 `--out` 확장자로 정한다. `--tools`, `--work`, `--keep` 을 쓸 수 있다.

업데이트 타이틀은 makerom 으로 재현할 수 없다. 콘텐츠 인덱스가 원래 0·2번
(1번 없음)인데 **makerom 은 인덱스가 0 부터 연속이어야 한다** — 0,2 로 주면
`[NCCH ERROR] Content not a valid ncch` 로 실패한다(암호화 문제가 아니다. 평문으로
다시 싸도 같다). `ffpatch` 는 이 경우를 미리 걸러 낸다.

### 스크립트가 하는 일

1. pyctr 로 CIA 콘텐츠(또는 3DS 파티션) 전부를 복호화해 평문 NCCH 로 꺼낸다.
2. 본편 CXI 를 헤더·exheader·logo·plain·exefs·romfs 로 펼친다.
3. ExeFS 의 배너·아이콘을 한글판으로 바꾸고 SHA-256 을 다시 계산한다.
4. romfs 를 펼쳐 원본 `init.jp`·`init.dict` 의 MD5 를 확인한 뒤 한글판으로 덮어쓴다.
   이미 패치한 파일이나 다른 판을 넣으면 여기서 멈춘다.
5. romfs 와 CXI 를 `--not-encrypt` 로 다시 싼다.
6. `makerom -f cia`(또는 `-f cci`) `-ignoresign` 으로 묶는다.
7. CIA 면 TMD 타이틀 버전을 원본 값(16)으로 되돌린다.

### 겪어 본 함정

- **`-ignoresign` 이 없으면** makerom 이 "Content 0 Is Corrupt" 로 실패한다.
- **`-content` 는 세 칸 형식**이어야 한다. `<파일>:<인덱스>:<콘텐츠ID>`.
  이 게임은 `0:3`, `1:1`, `2:4` 다. CCI 도 같은 형식이어야 한다.
- **CXI 는 `--not-encrypt` 로 만들어야** makerom 이 exheader 를 읽어 meta 영역까지
  생성한다.
- **타이틀 버전은 `-ver` 로 지정할 수 없다.** makerom 이 exheader 의 remaster
  version(0)을 따라가서 TMD 에 0 을 쓴다. 그래서 7번 단계에서 직접 고친다.
  실측으로 확인했다 — 묶은 직후 0, 고친 뒤 16.
- `code.bin` 은 손대지 않으므로 exheader 의 `CompressExefsCode` 플래그는 그대로
  둔다 (이 플래그를 잘못 끄면 부팅하지 않는다).
- 외부 도구(3dstool·makerom)는 한글·일본어 경로를 제대로 못 받는다. 그래서
  작업 폴더를 cwd 로 두고 짧은 영문 상대 경로만 넘긴다.

## 3. 배포 파일 만들기

배포는 두 갈래다. 게임 안 한글은 같고, HOME 메뉴까지 한글로 하려면 패처를 쓴다.

```bash
python scripts/build_patch.py                                         # out/init.jp, out/init.dict
python scripts/make_patcher.py 0.2 --python <임베디드 파이썬 폴더나 zip>   # release/patcher, release/python
python scripts/make_release.py 0.2                                     # ZIP 두 개
```

| 파일 | 내용 |
|---|---|
| `MPFF_KO_v0.2_LayeredFS.zip` | `luma/titles/.../romfs` 두 파일 + `locale.txt` |
| `MPFF_KO_v0.2_Patcher.zip` | `패치하기.bat` + `patcher/` + `python/` + `locale.txt` |

- 패처에는 **게임 데이터가 들어가지 않는다.** payload 는 한글 `init.jp`·`init.dict`,
  배너 띠 그림(`common6_rgba8.bin`), 게임 이름, 원본 MD5 뿐이다. 배너·아이콘은
  사용자 파일 안의 것을 고쳐 쓴다.
- 배너 띠는 `make_patcher.py` 가 미리 RGBA8 로 인코딩해 둔다. 그래야 패처가
  Pillow·numpy 없이 순수 파이썬으로 돈다 — 임베디드 파이썬에 패키지를 넣지 않아도 된다.
- `--python` 에는 python.org 의 embeddable package 를 풀어 둔 폴더를 주면 된다.
  다른 패처 배포 zip 의 `python/` 폴더도 그대로 읽는다.
- `release/patcher/{lib,bin,payload}` 와 `release/python` 은 커밋하지 않는다
  (`.gitignore`). 저장소에는 `patch.py`·`패치하기.bat`·설명서만 둔다.
- 첨부 파일 이름에 한글을 쓰면 GitHub 이 지운다. 릴리즈에 올릴 때 설명서는
  `README_KO.txt` 로 올린다(ZIP 안에서는 `README_한국어.txt` 그대로).

## 4. 번역 고치기

[README](../README.md#번역-수정) 를 보라. `tl/review_io.py` 로 검수용 JSON 을
주고받는다.
