# 변경 내역

## v0.2 — 2026-09-23

설치 방법을 두 가지로 늘렸습니다. [릴리즈 노트](docs/releases/v0.2.md)

- 가진 일본판 CIA·3DS 파일을 한글판으로 만들어 주는 패처를 추가했습니다. 파일을 `패치하기.bat`에 끌어다 놓으면 끝이고, 파이썬과 도구가 함께 들어 있어 따로 설치할 것이 없습니다.
- 패처로 만든 CIA는 HOME 메뉴 배너와 게임 이름도 한글로 나옵니다.
- 게임 안 번역과 폰트는 v0.1과 같습니다. `init.jp`, `init.dict`는 바이트 단위로 동일합니다.
- 배포 파일 이름을 `MPFF_KO_v0.2_LayeredFS.zip`, `MPFF_KO_v0.2_Patcher.zip`으로 정리했습니다.
- CIA 재빌드에서 `ctrtool` 의존을 없애고 pyctr로 복호화하도록 바꿨습니다(`scripts/ffpatch.py`). `.3ds` 출력도 지원합니다.

## v0.1 — 2026-09-20

첫 공개 버전입니다. [릴리즈 노트](docs/releases/v0.1.md)

- 게임 내 문자열 2,119개를 모두 한글화했습니다.
- 폰트 아틀라스를 교체해 한글 775자(Pretendard)를 넣었습니다.
- LayeredFS용 `init.jp`, `init.dict`와 타 리전 본체용 `locale.txt`를 배포했습니다.
- HOME 메뉴 배너·아이콘을 한글로 바꾸는 CIA 재빌드 도구(`scripts/build_cia.py`)를 함께 공개했습니다.
