# 메트로이드 프라임 페더레이션 포스 한글 패치

닌텐도 3DS 『메트로이드 프라임 페더레이션 포스』(일본판, CTR-P-BCAJ) 한글화 프로젝트.

**v0.1** — 게임 내 문자열 2,119개 전부 번역, 폰트 아틀라스 교체, HOME 메뉴 배너·아이콘
한글화까지 마쳤습니다. 실기(3DS)에서 CIA 설치·구동을 확인했습니다.

| | |
|---|---|
| 대상 | 일본판 `000400000016CE00` (업데이트 v1.2.0 설치돼 있어도 됩니다) |
| 번역 분량 | 2,119행 / 한글 775자 |
| 번역 기준 | 대사·문장은 **북미판 원문**, 용어·고유명사는 **일본판** 표기 |
| 필요한 것 | Luma3DS (게임 패치 활성화) |

## 설치 (LayeredFS)

1. [Releases](../../releases) 에서 `mpff-korean-v0.1-layeredfs.zip` 을 받습니다.
2. SD 카드 루트에 압축을 풉니다. 이런 모양이 됩니다.

```
sd:/luma/titles/000400000016CE00/romfs/init.jp
sd:/luma/titles/000400000016CE00/romfs/init.dict
```

3. Luma3DS 설정에서 **Enable game patching** 을 켭니다
   (본체를 켤 때 SELECT 를 누른 채로 부팅 → 설정 화면).
4. 게임을 실행합니다.

게임 데이터는 배포하지 않습니다. 일본판 소프트를 직접 준비해야 합니다.

### HOME 메뉴 배너·아이콘까지 한글로 하려면

LayeredFS 는 HOME 메뉴에 나오는 제목·배너를 바꾸지 못합니다(설치된 타이틀의
메타데이터에서 읽기 때문입니다). 여기까지 원하면 본인이 가진 일본판 CIA 로 직접
한글판 CIA 를 만들어야 합니다.

```bash
python scripts/build_cia.py --cia "일본판.cia" --out "한글판.cia"
```

`ctrtool` · `3dstool` · `makerom` 과 본체에서 뽑은 `boot9.bin` 이 필요합니다.
**본편만** 다시 만들면 되고, 업데이트 v1.2.0 은 원본 그대로 설치해도 한국어 제목과
배너가 유지됩니다(실기 확인). 자세한 건 [docs/BUILD.md](docs/BUILD.md) 를 보세요.

## 직접 빌드하기

일본판 romfs 를 `base_jp/romfs/` 에 풀어 둔 상태에서:

```bash
python scripts/build_patch.py     # tl/ko.json -> out/init.jp, out/init.dict
```

빌드할 때 글리프가 없는 문자가 섞여 있으면 경고가 나옵니다. 그 문자는 화면에서
빈칸으로 나오므로 반드시 고쳐야 합니다.

## 번역 고치기

`tl/ko.json` 이 게임이 읽는 원본이고, 제어 태그가 그대로 들어 있습니다.
읽기 편한 검수용 파일을 따로 뽑을 수 있습니다.

```bash
python tl/review_io.py export          # ko.json -> ko_review.json (태그 정리, {p} -> 줄바꿈)
# ko_review.json 의 "ko" 만 고친 뒤
python tl/review_io.py merge           # 무엇이 바뀌는지 미리보기
python tl/review_io.py merge --apply   # ko.json 에 반영
python tl/review_io.py verify          # 전 행 왕복 무손실 검사
```

검수용 파일은 문장 전체를 감싸는 태그만 벗기고, 줄 안쪽의 `{clr:...}`(키워드 강조)는
일부러 남겨 둡니다. 강조 위치도 같이 옮길 수 있고, 되돌려 넣을 때 손실이 없습니다.

## 저장소 구조

```
scripts/     도구 (아래 참고)
tl/          번역 (ko.json), 검수 왕복 도구, tl/history/ 는 번역 당시 일괄 적용 스크립트
docs/        FORMAT.md 파일 구조 정리, BUILD.md CIA 재빌드 안내
fonts/       Pretendard SemiBold·Bold (SIL OFL 1.1)
release/     배포본
```

| 스크립트 | 하는 일 |
|---|---|
| `build_patch.py` | 번역을 읽어 `init.jp` / `init.dict` 생성 (메인) |
| `build_banner.py` | 배너·아이콘을 한글로 바꾸고 ExeFS 재구성 |
| `build_cia.py` | 사용자의 일본판 CIA 로 한글판 CIA 생성 |
| `make_banner_strip.py` | 배너 띠(256×16) 한글 이미지 생성 |
| `nlgpak.py` | NLG pak 컨테이너 · 리소스 인덱스 · 문자열 테이블 · `.dict` |
| `nlgfont.py` | 모턴 타일 코덱, 폰트 정의 파서 |
| `fontlib.py` | 폰트 한 벌 로드, 글리프 배치 계산 |
| `lz11.py` | LZ11 압축/해제 (배너 CGFX) |
| `etc1a4.py` | ETC1A4 알파 평면 추출 (아틀라스 0~2페이지 조사용) |
| `make_release.py` | 배포용 LayeredFS zip 생성 |
| `make_testbuild.py` | 텍스트는 원문 그대로 두고 전체 경로만 지나가는 검증 빌드 |
| `verify_rebuild.py` | 재빌드 결과가 원본과 일치하는지 확인 |

## 알아 둘 점

- **폰트 자리**: 아틀라스 0~2페이지는 ETC1A4 압축이라 다시 그릴 수 없어 고정했습니다.
  남은 16페이지에 한글 1,308자까지 들어갑니다(현재 775자).
- **섹션 3 한계**: `init.jp` 섹션 3은 989,952바이트를 넘기면 부팅 중 크래시합니다.
- **루비 폰트**: 일본판 후리가나용 가나 폰트가 그대로 남아 있습니다. 한글판에서는
  `{rb}` 태그를 쓰지 않아 호출되지 않습니다.

기술적인 내용은 [docs/FORMAT.md](docs/FORMAT.md) 에 정리해 두었습니다.

## 라이선스

도구와 문서는 자유롭게 쓰세요. 번역문은 원작의 2차적 저작물입니다.
`fonts/` 의 Pretendard 는 SIL Open Font License 1.1 입니다 (`fonts/LICENSE.txt`).

게임 데이터는 포함돼 있지 않으며, 배포하지도 않습니다.
