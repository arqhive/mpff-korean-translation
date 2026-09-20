"""(en, jp) 짝으로 번역을 ko.json 에 적용한다. 같은 영문이라도 문맥(일본어)이
다르면 다르게 번역해야 하므로 짝으로 찾는다."""
import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))

def apply(pairs):
    path = os.path.join(BASE, "ko.json")
    rows = json.load(open(path, encoding="utf-8"))
    table = {(en, jp): ko for en, jp, ko in pairs}
    hit = 0
    miss = set(table)
    for r in rows:
        key = (r["en"], r["jp"])
        if key in table and not r["ko"]:
            r["ko"] = table[key]
            hit += 1
            miss.discard(key)
    json.dump(rows, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    done = sum(1 for r in rows if r["ko"])
    print(f"{hit}행 적용, 누적 {done}/{len(rows)} ({done*100//len(rows)}%)")
    for k in list(miss)[:10]:
        print("  못 찾음:", k)
    return done
