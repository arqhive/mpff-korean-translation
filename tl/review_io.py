"""검수용 JSON 내보내기 / 되돌려 넣기.

ko.json 은 게임이 읽는 원본이라 제어 태그가 그대로 들어 있다. 그대로 읽기는 불편하니
검수용으로는 **문자열 전체를 감싸는 태그만** 벗기고 `{p}` 는 진짜 줄바꿈으로 바꾼다.
줄 안쪽 태그({clr:...} 같은 키워드 강조)는 **일부러 남긴다** — 검수하며 강조 위치도
같이 옮길 수 있어야 하고, 남겨 두면 되돌려 넣을 때 손실이 없다.

  python review_io.py export          # ko.json -> ko_review.json
  python review_io.py merge           # 무엇이 바뀌는지 미리보기
  python review_io.py merge --apply   # ko_review.json 의 수정을 ko.json 에 반영
  python review_io.py verify          # 전 행 왕복 무손실 검사
"""
import io
import json
import os
import re
import sys

if getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
KO = os.path.join(BASE, "ko.json")
REVIEW = os.path.join(BASE, "ko_review.json")
TAG = re.compile(r"\{/?[a-z]+(?::[^}]*)?\}")


OPEN = re.compile(r"\{([a-z]+)(?::[^}]*)?\}")


def split_shell(s):
    """(전체를 감싸는 앞 태그, 본문, 뒤 태그).

    **짝이 맞는 것만** 벗긴다. 맨 앞의 {clr:...} 처럼 닫는 태그가 문장 중간에
    있는 것은 본문에 남겨야 한다. 안 그러면 검수본에 {/clr} 만 외톨이로 남고,
    검수자가 여는 태그를 손으로 되살리면 반영할 때 태그가 두 번 들어간다.
    """
    i, j = 0, len(s)
    while True:
        m = OPEN.match(s, i)
        if not m or m.group(1) == "p":
            break
        close = "{/%s}" % m.group(1)
        if s.endswith(close, 0, j):                     # 여는 것과 닫는 것이 짝
            i, j = m.end(), j - len(close)
        elif close not in s[m.end():j]:                 # 닫는 태그가 아예 없음
            i = m.end()
        else:                                           # 닫는 태그가 중간에 있음
            break
    return s[:i], s[i:j], s[j:]


def split_shell_v1(s):
    """옛 규칙: 앞의 태그를 짝과 무관하게 전부 벗겼다.

    2025-09-20 이전에 내보낸 ko_review.json 은 이 규칙으로 만들어졌다.
    그 파일을 되돌려 넣을 때만 쓴다.
    """
    i = 0
    while True:
        m = TAG.match(s, i)
        if not m or m.group(0) == "{p}":
            break
        i = m.end()
    j = len(s)
    while True:
        last = None
        for t in TAG.finditer(s, i):
            if t.end() == j and t.group(0) != "{p}":
                last = t
        if not last:
            break
        j = last.start()
    return s[:i], s[i:j], s[j:]


def to_review(s):
    """ko.json 문자열 -> 검수용 문자열 (앞뒤 감싼 태그만 제거, {p} -> 줄바꿈)"""
    _pre, body, _post = split_shell(s)
    return body.replace("{p}", "\n")


def to_raw(orig, text):
    """검수용 문자열 -> ko.json 문자열 (원문의 앞뒤 태그를 다시 씌운다)"""
    pre, _body, post = split_shell(orig)
    return pre + text.replace("\n", "{p}") + post


def load():
    return json.load(open(KO, encoding="utf-8"))


def cmd_export():
    rows = load()
    out = [{"hash": r["hash"],
            "en": to_review(r["en"]),
            "jp": to_review(r["jp"]),
            "ko": to_review(r["ko"])} for r in rows]
    json.dump(out, open(REVIEW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ko_review.json 에 {len(out)}행 내보냈다.")


def cmd_verify():
    rows = load()
    bad = [r for r in rows if to_raw(r["ko"], to_review(r["ko"])) != r["ko"]]
    print(f"왕복 무손실 {len(rows) - len(bad)}/{len(rows)}행")
    for r in bad[:10]:
        print("!!", r["hash"])
        print("  원:", repr(r["ko"]))
        print("  복:", repr(to_raw(r["ko"], to_review(r["ko"]))))
    return not bad


def cmd_merge(apply):
    rows = load()
    rev = json.load(open(REVIEW, encoding="utf-8"))

    if len(rows) != len(rev) or any(a["hash"] != b["hash"] for a, b in zip(rows, rev)):
        print("행 순서가 다르다. hash 로 짝을 맞춘다.")
        by_hash = {}
        for r in rev:
            by_hash.setdefault(r["hash"], []).append(r)
        missing = [r["hash"] for r in rows if not by_hash.get(r["hash"])]
        if missing:
            print(f"검수 파일에 없는 hash {len(missing)}개: {missing[:5]}")
            return
        rev = [by_hash[r["hash"]].pop(0) for r in rows]

    changed = []
    for r, v in zip(rows, rev):
        if to_review(r["ko"]) == v["ko"]:
            continue
        changed.append((r, v, to_raw(r["ko"], v["ko"])))

    print(f"그대로 {len(rows) - len(changed)}행 / 수정 {len(changed)}행")
    for r, v, new in changed[:60]:
        print(f"--- {r['hash']}")
        print("  전:", r["ko"])
        print("  후:", new)
    if len(changed) > 60:
        print(f"  ... 그 외 {len(changed) - 60}행")

    if not apply:
        print("\n(미리보기다. 반영하려면 merge --apply)")
        return
    if not changed:
        print("\n반영할 것이 없다.")
        return
    for r, _v, new in changed:
        r["ko"] = new
    json.dump(rows, open(KO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nko.json 에 {len(changed)}행 반영했다. build_patch.py 를 다시 돌리면 된다.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "export":
        cmd_export()
    elif cmd == "merge":
        cmd_merge("--apply" in sys.argv)
    elif cmd == "verify":
        sys.exit(0 if cmd_verify() else 1)
    else:
        print(__doc__)
