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

## 2. 한글판 CIA 만들기 (HOME 메뉴 배너까지)

LayeredFS 는 HOME 메뉴의 제목·배너를 바꾸지 못한다. 거기까지 원하면 CIA 를
다시 만들어야 한다. 게임 데이터를 배포할 수 없으니 각자 PC 에서 돌려야 한다.

### 준비물

| | |
|---|---|
| 일본판 CIA | `000400000016CE00` |
| ctrtool · 3dstool · makerom | PATH 에 두거나 `--tools` 로 폴더 지정 |
| boot9.bin | `%USERPROFILE%/.3ds/boot9.bin` |
| 디스크 여유 | 6GB 이상 |

### 실행

**본편 CIA 만** 다시 만들면 된다. 업데이트 타이틀은 그대로 설치해도
본편의 한국어 제목·아이콘·배너가 유지된다(실기 확인).

```bash
python scripts/build_patch.py                       # 먼저 out/ 을 만들어 둔다
python scripts/build_cia.py --cia "일본판.cia" --out "한글판.cia"
```

참고로 업데이트 타이틀은 makerom 으로 재현할 수도 없다. 콘텐츠 인덱스가 원래 0·2번
(1번 없음)인데 **makerom 은 인덱스가 0 부터 연속이어야 한다** — 0,2 로 주면
`[NCCH ERROR] Content not a valid ncch` 로 실패한다(암호화 문제가 아니다. 평문으로
다시 싸도 같다).

`--tools`, `--work`, `--keep` 을 쓸 수 있다. `--keep` 은 중간 파일을 남긴다.

### 스크립트가 하는 일

1. `ctrtool --contents` 로 콘텐츠 3개를 분리한다 (메인 CXI, 전자설명서, DLP 자식).
2. 메인 CXI 를 헤더·exheader·logo·plain·exefs·romfs 로 펼친다.
3. romfs 를 펼쳐 `init.jp` / `init.dict` 를 덮어쓴다.
4. ExeFS 의 배너·아이콘을 한글판으로 바꾸고 SHA-256 을 다시 계산한다.
5. romfs 와 CXI 를 `--not-encrypt` 로 다시 싼다.
6. `makerom -f cia -ignoresign` 으로 묶는다.
7. TMD 타이틀 버전을 원본 값(16)으로 되돌린다.

### 겪어 본 함정

- **`-ignoresign` 이 없으면** makerom 이 "Content 0 Is Corrupt" 로 실패한다.
- **`-content` 는 세 칸 형식**이어야 한다. `<파일>:<인덱스>:<콘텐츠ID>`.
  이 게임은 `0:3`, `1:1`, `2:4` 다.
- **CXI 는 `--not-encrypt` 로 만들어야** makerom 이 exheader 를 읽어 meta 영역까지
  생성한다.
- **타이틀 버전은 `-ver` 로 지정할 수 없다.** makerom 이 exheader 의 remaster
  version(0)을 따라가서 TMD 에 0 을 쓴다. 그래서 7번 단계에서 직접 고친다.
  실측으로 확인했다 — 묶은 직후 0, 고친 뒤 16.
- `code.bin` 은 손대지 않으므로 exheader 의 `CompressExefsCode` 플래그는 그대로
  둔다 (이 플래그를 잘못 끄면 부팅하지 않는다).

## 3. 번역 고치기

[README](../README.md#번역-고치기) 를 보라. `tl/review_io.py` 로 검수용 JSON 을
주고받는다.
