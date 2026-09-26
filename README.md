# 메트로이드 프라임 페더레이션 포스 (3DS) 한글 패치

*Metroid Prime: Federation Force* (닌텐도 3DS, 일본판 `CTR-P-BCAJ`) 비공식 한국어 팬 패치입니다.
대사와 문장은 북미판 원문을 기준으로 번역했고, 용어와 고유명사는 일본판 표기를 따랐습니다.

**제작: arqhive** · **최신 버전: [v0.3](https://github.com/arqhive/mpff-korean-translation/releases/tag/v0.3)**

- 게임 내 문자열 2,119개를 모두 번역했습니다(대사, 브리핑, 메뉴, HUD, 칩 설명, 데이터뱅크 로그, 시스템 메시지).
- 폰트 아틀라스를 교체해 한글 775자를 넣었습니다(Pretendard 기반).
- 게임 안 타이틀 띠 2종(「메트로이드 프라임 페더레이션 포스」, 「메트로이드 프라임 블라스트 볼」)도 한글로 바꿨습니다. 게임 그래픽에 일본어가 들어간 것은 이 둘뿐입니다.
- HOME 메뉴 배너와 아이콘도 한글화했습니다. 배너는 패처로 한글판 CIA를 만들 때 적용되며, 게임 안 타이틀 띠와 같은 그림을 씁니다.
- 배포본은 두 가지입니다. `init.jp`와 `init.dict` 두 파일만 바꾸는 LayeredFS 패치, 그리고 가진 일본판 CIA·3DS를 한글판으로 만들어 주는 패처입니다.

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 일본판 소프트(타이틀 ID `000400000016CE00`). 업데이트 v1.2.0이 설치돼 있어도 됩니다. 북미판(`000400000016E300`)에는 적용할 수 없습니다.
- 방법 A: 게임 패치(LayeredFS)를 켠 Luma3DS.
- 방법 B: 윈도우 PC와 본인이 가진 일본판 `.cia` 또는 `.3ds` 파일. 암호화된 원본이면 `boot9.bin`과 `seeddb.bin`이 필요합니다.

### 적용 방법

게임 안 한글은 두 방법이 같습니다. 하나만 고르면 됩니다.

| | 방법 A `MPFF_KO_v0.3_LayeredFS.zip` | 방법 B `MPFF_KO_v0.3_Patcher.zip` |
|---|---|---|
| 방식 | Luma3DS 게임 패치(LayeredFS)로 덮어씌웁니다 | 가진 일본판 CIA·3DS를 한글판으로 새로 만듭니다 |
| 게임 안 타이틀 띠 | 한글로 나옵니다 | 한글로 나옵니다 |
| HOME 메뉴 제목·배너 | 일본어로 남습니다 | 한글로 나옵니다 |
| 내려받는 크기 | 9MB | 22MB |
| 드는 수고 | 파일 복사 몇 초 | 윈도우 PC에서 10분 안쪽, 여유 공간 6GB |
| 되돌리기 | 폴더만 지우면 됩니다 | 원본 CIA를 다시 설치해야 합니다 |

두 ZIP 모두 [배포 페이지](https://github.com/arqhive/mpff-korean-translation/releases/tag/v0.3)에 있습니다.

#### 방법 A. LayeredFS

1. ZIP 안의 `luma` 폴더를 SD 카드 루트에 풉니다. 다음과 같이 파일이 놓입니다.

   ```
   sd:/luma/titles/000400000016CE00/locale.txt
   sd:/luma/titles/000400000016CE00/romfs/init.jp
   sd:/luma/titles/000400000016CE00/romfs/init.dict
   sd:/luma/titles/000400000016CE00/romfs/FrontEnd/Persistent.data
   sd:/luma/titles/000400000016CE00/romfs/FrontEnd_BattleBall/Persistent.data
   ```

2. Luma3DS 설정에서 **Enable game patching**을 켭니다. 본체를 켤 때 SELECT를 누른 채로 두면 설정 화면이 나옵니다.
3. 게임을 실행합니다.

Azahar에서는 게임을 오른쪽 클릭해 **Open Mods Location**을 누르고, 열린 폴더에 ZIP 안의 `romfs` 폴더를 통째로 복사합니다.

`init.jp`와 `init.dict`는 반드시 짝으로 넣습니다. 예전에 다른 한글 패치를 썼다면 `sd:/luma/titles/000400000016CE00/` 폴더를 지우고 새로 풉니다. 옛 파일과 섞이면 크래시합니다.

#### 방법 B. 패처

1. ZIP을 폴더째 풉니다. 임베디드 파이썬과 도구가 함께 들어 있어 따로 설치할 것은 없습니다.
2. 일본판 `.cia` 또는 `.3ds` 파일을 `패치하기.bat`에 끌어다 놓습니다. 여러 개를 한 번에 놓아도 됩니다.
3. 원본과 같은 폴더에 `<원래 이름>_KO.cia`(또는 `_KO.3ds`)가 생깁니다. 원본 파일은 바뀌지 않습니다.
4. 만든 CIA를 FBI 등으로 설치합니다. 이미 설치된 일본판에 덮어 설치해도 세이브는 유지되고, SD 카드의 LayeredFS 폴더는 필요 없어집니다.

패처에는 게임 데이터가 들어 있지 않습니다. 한글 `init.jp`·`init.dict`와 배너 띠 그림만 들어 있고, 배너·아이콘은 사용자 파일 안의 것을 고쳐 씁니다.
본편만 넣으면 됩니다. 업데이트 v1.2.0은 원본 그대로 설치해도 한국어 제목과 배너가 유지됩니다. 이미 패치한 파일, 다른 판, 업데이트 타이틀을 넣으면 확인 단계에서 멈춥니다.
암호화된 원본은 `boot9.bin`과 `seeddb.bin`이 필요합니다(이 게임은 seed 암호화를 씁니다). GodMode9으로 덤프한 파일을 `패치하기.bat`과 같은 폴더에 두거나, Azahar의 `sysdata` 폴더에 있으면 자동으로 찾습니다.

#### `locale.txt`는 어느 방법이든 필요합니다

내용이 `JPN JP` 한 줄인 이 파일을 `sd:/luma/titles/000400000016CE00/locale.txt`에 둬야 합니다. 한국판·북미판처럼 일본판이 아닌 본체에서는 게임이 시스템 언어에 맞는 언어 팩을 찾다 실패해 시작 직후 크래시합니다.
Luma3DS 기능이라 CIA에 담을 수 없어서, 패처로 만든 CIA를 설치한 경우에도 SD에 따로 둬야 합니다. 두 ZIP 모두에 들어 있습니다.

자세한 방법은 [`README_한국어.txt`](release/README_한국어.txt)를 참고하세요.

### 파일 확인값

LayeredFS 패치라 롬 전체가 아니라 바뀌는 파일을 비교합니다. 원본은 일본판 romfs의 파일, 패치는 배포 ZIP에 든 파일입니다. 텍스트를 담은 두 파일은 v0.1부터 내용이 같습니다.

| 항목 | 원본 `init.jp` | 원본 `init.dict` | 패치 `init.jp` | 패치 `init.dict` |
|---|---|---|---|---|
| 크기 | 367,785 바이트 | 1,128 바이트 | 340,984 바이트 | 1,128 바이트 |
| CRC32 | `A2DBDBC8` | `10EA79D7` | `E976B354` | `70BA9FE9` |
| MD5 | `0ab9fff6f004e27f939374cdbfb46648` | `1c3687092ba7ed23fbdfb1fb9dd299b3` | `f1118192b9edd4eaccbcbcf89209c95e` | `30ecc1dc858a9656ca736857ffdd026f` |
| SHA-1 | `c18661f265c4c7a95f05b9feafcf6405ed0aa425` | `7c749a4bad7168bd3433dd937895c0ba1e26b92f` | `957672ab2aeb928fec3a6c1e8d5e8a07c24fcae6` | `53e17c3e1b5f86d8d3570a2334e4db10c591d0c3` |

원본 파일 위치 예: 일본판 CIA의 romfs 루트(`romfs/init.jp`, `romfs/init.dict`).

타이틀 띠가 든 두 파일은 **크기가 원본과 같습니다**(텍스처를 제자리에 덮어쓰기 때문입니다).

| 파일 | 크기 | 원본 MD5 | 패치 MD5 (v0.3) |
|---|---|---|---|
| `FrontEnd/Persistent.data` | 11,244,228 바이트 | `d387e2cc2598e25ed7922c9fc9f1cee2` | `18cabac65645398a1dbba00807678b1a` |
| `FrontEnd_BattleBall/Persistent.data` | 7,888,032 바이트 | `37262db314c3f8dc4078648b0a40490c` | `bfebbae88a2bd5b4e4d7b1c9b96871bf` |

### 실행 환경

- **확인함**: 3DS + Luma3DS(LayeredFS), 3DS(패처로 만든 CIA 설치), Azahar.

### 알려진 문제

- LayeredFS로는 HOME 메뉴의 제목과 배너가 바뀌지 않습니다. 3DS가 설치된 타이틀의 메타데이터에서 읽기 때문이며, 패처로 한글판 CIA를 만들면 바뀝니다.
- 타이틀 띠 4장(16KB)을 바꾸느라 그 그림이 든 pak 두 개(19MB)를 통째로 배포합니다. LayeredFS가 파일 단위로만 교체되기 때문입니다.
- 시리즈 로고(`METROID PRIME`, `FEDERATION FORCE`, `BLAST BALL`)와 A/B/X/Y 버튼 글리프는 원문 그대로 두었습니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3, Pillow, NumPy(`pip install pillow numpy`).
- 일본판 romfs를 `base_jp/romfs/`에 풀어 둔 상태. 최소한 `init.jp`와 `init.dict`가 필요하며, CIA에서 뽑는 방법은 [`docs/BUILD.md`](docs/BUILD.md)에 있습니다.
- 폰트는 저장소의 [`fonts/`](fonts/)(Pretendard SemiBold·Bold)를 씁니다.
- 한글판 CIA·3DS 빌드에는 `3dstool`, `makerom`(둘 다 `tools/`에 둡니다), pyctr, pycryptodomex(`pip install pyctr pycryptodomex`), `boot9.bin`, `seeddb.bin`이 추가로 필요합니다.

### 빌드

```bash
python scripts/build_patch.py                      # tl/ko.json -> out/init.jp, out/init.dict
python scripts/build_graphics.py                   # graphics/*.png -> out/romfs/...
python scripts/make_patcher.py 0.3 --python <임베디드 파이썬>   # release/patcher, release/python 채우기
python scripts/make_release.py 0.3                 # 배포 ZIP 두 개 생성
```

빌드 결과 `out/init.jp`, `out/init.dict`는 v0.1 배포본과 바이트 단위로 같습니다.

빌드할 때 글리프가 없는 문자가 섞여 있으면 경고가 나옵니다. 그 문자는 화면에서 빈칸으로 나오므로 반드시 고쳐야 합니다.
빌드할 때 지켜야 하는 제약은 다음과 같습니다.

- 폰트 아틀라스 0, 1, 2페이지는 ETC1A4 압축이라 다시 그릴 수 없어 고정했습니다. 남은 16페이지에 한글 1,308자까지 들어갑니다(현재 775자).
- `init.jp` 섹션 3은 989,952바이트를 넘기면 부팅 중 크래시합니다.
- 섹션 3 글리프 아틀라스의 압축 크기가 272,729바이트를 넘으면 실기에서 게임 시작 직후 크래시합니다(에뮬레이터는 통과). 빌더가 매번 검사합니다.
- 일본판 후리가나용 루비 폰트가 그대로 남아 있습니다. 한글판에서는 `{rb}` 태그를 쓰지 않아 호출되지 않습니다.

### 번역 수정

- 번역: [`tl/ko.json`](tl/ko.json). 게임이 읽는 원본이며 제어 태그가 그대로 들어 있습니다.
- 검수용 파일은 `tl/review_io.py`로 주고받습니다. 문장 전체를 감싸는 태그만 벗기고, 줄 안쪽의 `{clr:...}`(키워드 강조)는 일부러 남겨 둡니다. 강조 위치도 함께 옮길 수 있고, 되돌려 넣을 때 손실이 없습니다.

```bash
python tl/review_io.py export          # ko.json -> ko_review.json (태그 정리, {p} -> 줄바꿈)
# ko_review.json 의 "ko" 만 고친 뒤
python tl/review_io.py merge           # 무엇이 바뀌는지 미리보기
python tl/review_io.py merge --apply   # ko.json 에 반영
python tl/review_io.py verify          # 전 행 왕복 무손실 검사
python scripts/build_patch.py          # out/init.jp, out/init.dict 생성
```

- 실기 확인은 CIA를 다시 만들지 말고 LayeredFS로 합니다. CIA 재빌드는 10분쯤 걸리지만 LayeredFS는 파일 두 개 복사로 끝납니다. 배너·아이콘은 CIA에 들어 있으므로 한 번 설치해 두면 그대로 유지됩니다.
- 새로 나온 `init.jp`와 `init.dict`를 `sd:/luma/titles/000400000016CE00/romfs/`에 짝으로 넣습니다. 그 폴더에 다른 패치가 남아 있지 않은지 확인하고, 무엇을 바꾸든 원본 대조군을 먼저 돌립니다. 자세한 주의점은 [`docs/BUILD.md`](docs/BUILD.md)에 있습니다.

### 폴더 구조

```
scripts/     빌드 도구 (아래 표 참고)
graphics/    게임 안 타이틀 띠·HOME 배너 띠의 한글 원본 PNG
tl/          번역(ko.json), 검수 왕복 도구, tl/history/는 번역 당시 일괄 적용 스크립트
docs/        FORMAT.md 파일 구조 정리, BUILD.md 빌드·CIA 재빌드 안내, 릴리즈 노트 사본(docs/releases/)
fonts/       Pretendard SemiBold·Bold와 라이선스(SIL OFL 1.1)
release/     사용자 설명서, 패처 진입점(patch.py·패치하기.bat), 배포 ZIP
             (payload·lib·bin·임베디드 파이썬은 빌드 때 채우고 커밋하지 않는다)
```

| 스크립트 | 하는 일 |
|---|---|
| `build_patch.py` | 번역을 읽어 `init.jp`, `init.dict` 생성(메인) |
| `build_banner.py` | 배너·아이콘을 한글로 바꾸고 ExeFS 재구성 |
| `build_graphics.py` | 타이틀 띠를 넣은 romfs 파일 생성 (`out/romfs/`) |
| `build_cia.py` | 일본판 CIA·3DS로 한글판 CIA·3DS 생성(개발용) |
| `ffpatch.py` | 위 작업의 핵심. 배포 패처도 같은 파일을 쓴다 |
| `make_patcher.py` | 배포 패처 꾸리기(payload, lib, bin, 임베디드 파이썬) |
| `make_banner_strip.py` | 배너 띠(256×16) 한글 이미지 생성 |
| `nlgpak.py` | NLG pak 컨테이너, 리소스 인덱스, 문자열 테이블, `.dict` |
| `nlgtex.py` | pak 안 텍스처 찾기, ETC1·ETC1A4·선형 포맷 디코더와 ETC1A4 인코더 |
| `extract_tex.py` | pak 안 텍스처를 전부 PNG로 뽑기(조사용) |
| `nlgfont.py` | 모턴 타일 코덱, 폰트 정의 파서 |
| `fontlib.py` | 폰트 한 벌 로드, 글리프 배치 계산 |
| `lz11.py` | LZ11 압축·해제(배너 CGFX) |
| `etc1a4.py` | ETC1A4 알파 평면 추출(아틀라스 0, 1, 2페이지 조사용) |
| `make_release.py` | 배포 ZIP 두 개(LayeredFS, 패처) 생성 |
| `make_testbuild.py` | 텍스트는 원문 그대로 두고 전체 경로만 지나가는 검증 빌드 |
| `verify_rebuild.py` | 재빌드 결과가 원본과 일치하는지 확인 |

### 기술 문서

파일 구조(NLG pak, 문자열 테이블, 폰트 아틀라스, 섹션 크기 한계, 배너·아이콘)는 [`docs/FORMAT.md`](docs/FORMAT.md)에 정리했습니다.
빌드 로그 읽는 법과 CIA 재빌드 절차는 [`docs/BUILD.md`](docs/BUILD.md)에 있습니다.

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드, 한국어 번역문, 문서: [MIT License](LICENSE) (© 2026 arqhive).
- 폰트: [Pretendard](https://github.com/orioncactus/pretendard) © Kil Hyung-jin, [SIL Open Font License 1.1](fonts/LICENSE.txt).

## 면책

비공식 팬 번역이며 Nintendo와 관련이 없습니다. 「메트로이드 프라임 페더레이션 포스」 관련 상표·저작권은 Nintendo에 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.
