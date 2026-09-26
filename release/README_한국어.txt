메트로이드 프라임 페더레이션 포스 (3DS) 한글 패치 v0.3
제작: arqhive

「메트로이드 프라임 페더레이션 포스」(닌텐도 3DS, 일본판) 비공식 한국어 팬 패치입니다.
게임 안 문자열 2,119개를 전부 번역했고, 게임 그래픽에 남아 있던 일본어(타이틀 띠 2종)도 한글로 바꿨습니다.
배포 파일은 두 가지입니다. 게임 안 한글은 같으니 둘 중 하나만 고르면 됩니다.

- MPFF_KO_v0.3_LayeredFS.zip (방법 A)
  설치된 일본판은 그대로 두고, Luma3DS의 게임 패치(LayeredFS)나 에뮬레이터의 모드 폴더로 덮어씌웁니다.
  좋은 점: 파일 복사 몇 초로 끝나고, 키 파일이 필요 없고, 폴더만 지우면 원래대로 돌아갑니다.
  아쉬운 점: HOME 메뉴의 게임 이름과 배너는 일본어로 남고, Luma3DS 게임 패치를 켜 둬야 합니다.
  게임 안 타이틀 띠는 이 방법으로도 한글로 나옵니다.
- MPFF_KO_v0.3_Patcher.zip (방법 B)
  가지고 있는 일본판 CIA나 3DS 파일을 한글판으로 새로 만듭니다.
  좋은 점: HOME 메뉴 배너·게임 이름까지 한글이고, 만든 파일을 에뮬레이터에서 바로 실행할 수 있습니다.
  아쉬운 점: 일본판 CIA·3DS 파일과 윈도우 PC가 필요하고, 암호화된 원본이면 boot9.bin·seeddb.bin이 필요합니다.
             되돌리려면 원본 CIA를 다시 설치해야 합니다.

설치된 게임을 그대로 두고 간단히 쓰려면 A, HOME 메뉴까지 한글로 보고 싶으면 B를 고르세요.

※ 어느 방법을 쓰든 SD 카드의 locale.txt는 필요합니다. 아래 [locale.txt] 를 읽어 주세요.


[준비물]

- 일본판 「メトロイドプライム フェデレーションフォース」(타이틀 ID 000400000016CE00).
  북미판·유럽판(Metroid Prime: Federation Force)에는 적용할 수 없습니다.
  업데이트 v1.2.0이 설치돼 있어도 괜찮습니다.
- 3DS 실기: Luma3DS가 설치된 본체와 SD 카드.
- 에뮬레이터: Azahar.


[locale.txt — 빼면 크래시합니다]

한국판·북미판처럼 일본판이 아닌 리전의 본체에서는 게임이 시스템 언어에 맞는 언어 팩을
찾다 실패해 게임 시작 직후 크래시합니다. 두 ZIP 모두에 들어 있는 luma 폴더를 SD 카드
루트에 복사하세요.

  sd:/luma/titles/000400000016CE00/locale.txt      내용은 "JPN JP" 한 줄입니다.

Luma3DS의 기능이라 CIA에 담을 수 없습니다. 방법 B로 한글판 CIA를 설치한 경우에도
이 파일은 SD 카드에 따로 둬야 합니다. 일본판 본체라면 없어도 됩니다.


[방법 A. LayeredFS: 3DS 실기 (Luma3DS)]

1. MPFF_KO_v0.3_LayeredFS.zip 안의 luma 폴더를 SD 카드 루트에 그대로 복사합니다.
   다음과 같이 파일이 놓이면 됩니다.

     sd:/luma/titles/000400000016CE00/locale.txt
     sd:/luma/titles/000400000016CE00/romfs/init.jp
     sd:/luma/titles/000400000016CE00/romfs/init.dict
     sd:/luma/titles/000400000016CE00/romfs/FrontEnd/Persistent.data
     sd:/luma/titles/000400000016CE00/romfs/FrontEnd_BattleBall/Persistent.data

   init.jp와 init.dict는 짝입니다. 하나만 넣으면 게임 안 텍스트가 전부 빈칸으로
   나오거나 크래시합니다.

   FrontEnd 쪽 두 파일은 게임 안 타이틀 띠를 한글로 바꿉니다. 띠 4장(16KB)만 바뀐
   파일인데, LayeredFS가 파일 단위로만 교체되기 때문에 통째로 들어 있습니다.

2. 본체를 켤 때 SELECT를 누른 채로 두면 Luma3DS 설정 화면이 나옵니다.
   "Enable game patching"을 켜고 저장합니다.
3. 게임을 실행합니다.

- 예전에 다른 패치를 넣은 적이 있다면 sd:/luma/titles/000400000016CE00/ 폴더를 지운 뒤 새로
  복사하세요. 옛 파일과 섞이면 글자가 나오지 않거나 게임이 멈춥니다.


[방법 A. LayeredFS: Azahar]

1. 게임 목록에서 페더레이션 포스를 오른쪽 클릭하고 "Open Mods Location"을 누릅니다.
2. 열린 폴더(…/load/mods/000400000016CE00/)에 ZIP 안의
   luma/titles/000400000016CE00/romfs 폴더를 통째로 복사합니다.

     …/load/mods/000400000016CE00/romfs/init.jp
     …/load/mods/000400000016CE00/romfs/init.dict
     …/load/mods/000400000016CE00/romfs/FrontEnd/Persistent.data
     …/load/mods/000400000016CE00/romfs/FrontEnd_BattleBall/Persistent.data

3. 게임을 실행합니다.


[방법 B. 패처: 한글판 CIA / 3DS 만들기]

1. MPFF_KO_v0.3_Patcher.zip 을 폴더째 압축 풉니다.
2. 일본판 .cia 또는 .3ds 파일을 "패치하기.bat"에 끌어다 놓습니다. 여러 개를 한 번에 놓아도 됩니다.
3. 원본과 같은 폴더에 "원래 이름_KO.cia" 또는 "원래 이름_KO.3ds"가 생깁니다. 원본 파일은 바뀌지 않습니다.
4. 3DS 실기: 만든 CIA를 FBI 등으로 설치합니다. 이미 설치된 일본판에 덮어 설치해도 세이브는 유지됩니다.
   이렇게 설치했다면 SD 카드의 LayeredFS 폴더(luma/titles/000400000016CE00/romfs)는 필요 없습니다.
   locale.txt는 그대로 둬야 합니다.

- 넣을 파일은 본편입니다. 업데이트(0004000E0016CE00)는 패치하지 않아도 되고, 원본 그대로
  설치하면 본편의 한글 제목과 배너가 유지됩니다.
- 원본 파일이 암호화되어 있으면 boot9.bin과 seeddb.bin이 필요합니다. 이 게임은 seed 암호화를 씁니다.
  본체에서 GodMode9으로 덤프한 파일을 "패치하기.bat"과 같은 폴더에 두세요.
  Azahar(또는 Citra)의 sysdata 폴더에 이미 있으면 따로 둘 필요가 없습니다.
- 이미 복호화된 파일(Decrypted)은 키 없이도 됩니다.
- 만들어진 3DS 파일은 복호화된 상태라 에뮬레이터·플래시카트용입니다. 3DS 본체에는 CIA를 설치하세요.
- 이미 패치한 파일이나 다른 판(북미판·유럽판)을 넣으면 확인 단계에서 멈춥니다.
- 작업하는 동안 약 6GB의 여유 공간이 필요합니다.


[한글로 바뀌는 그래픽]

게임 그래픽에 일본어가 들어간 것은 타이틀 띠 2종뿐이고, 둘 다 한글로 바꿨습니다.

  「メトロイドプライム フェデレーションフォース」  -> 메트로이드 프라임 페더레이션 포스
  「メトロイドプライム ブラストボール」            -> 메트로이드 프라임 블라스트 볼

HOME 메뉴 배너 띠도 같은 그림을 써서 글자체가 같습니다(방법 B에서만 적용됩니다).
시리즈 로고(METROID PRIME, FEDERATION FORCE, BLAST BALL)와 A/B/X/Y 버튼 표기는
원문 그대로 두었습니다.


[번역 기준]

대사와 문장은 북미판 원문을 옮겼습니다. 개발사(Next Level Games, 캐나다)가 쓴 원문이기
때문입니다. 용어와 고유명사는 일본판 표기를 따랐습니다. 시리즈 공식 한국어 표기가 있는
것은 그쪽을 우선했습니다.

  예) Space Pirates  → 우주 해적
      Federation     → 페더레이션
      lock-on        → 록온
      turret         → 터릿

외래어는 국립국어원 외래어 표기법을 따랐습니다(대미지, 커패시티, 타깃 등).


[저장소]

https://github.com/arqhive/mpff-korean-translation

도구와 번역 파일이 전부 공개돼 있습니다. 오역 신고나 수정 제안을 환영합니다.
폰트는 Pretendard (SIL Open Font License 1.1) 를 썼습니다.


[면책]

비공식 팬 번역이며 Nintendo, Next Level Games와 관련이 없습니다.
「메트로이드 프라임 페더레이션 포스」 관련 상표·저작권은 Nintendo에 있습니다.
게임 데이터는 들어 있지 않으며, 패치를 적용한 게임 파일의 배포를 금지합니다.
