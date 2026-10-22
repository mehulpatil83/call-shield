"""Dev half only, read-only: which phrases recur in the scams the rules MISS but almost never in benign calls?

    python -m eval.mine_misses

Prints word groups (2-5 words) with: misses = in how many missed scam calls, benign = in how many benign calls. Use it to see
which kinds of wording the word lists lack. Add general patterns to core/lexicon.py (not whole sentences), then re-run
`python -m eval.call_eval` and `python -m eval.benchmark_eval --split dev`: false alarms must stay at 0. The locked test half
is never read here."""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

from core.rules import analyse_text

from .benchmark_eval import DATA, clean, find_labels, is_test

STOP = set("the a an and or to of in on at for with is are was were be been i you your we our my me it this that these those do does did "
           "can could would will shall have has had not no yes so if as by from but about just can't i'm you're we're it's what how".split())


def grams(text: str, lo: int = 2, hi: int = 5) -> set[str]:
    w = re.findall(r"[a-z']+", text.lower())
    out = set()
    for n in range(lo, hi + 1):
        for i in range(len(w) - n + 1):
            g = w[i:i + n]
            if sum(x not in STOP for x in g) >= 2:           # at least two content words
                out.add(" ".join(g))
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DATA / "no_ident.csv"))
    ap.add_argument("--top", type=int, default=45)
    a = ap.parse_args()
    import pandas as pd
    df = pd.read_csv(a.file).dropna(subset=["conversation"])
    labels = find_labels(df["conversation"].tolist())
    df["text"] = df["conversation"].map(lambda t: clean(t, labels))
    df = df.drop_duplicates("text")
    df = df[~df["conversation_id"].map(is_test)]              # dev half only
    miss, ben = Counter(), Counter()
    n_miss = n_ben = 0
    for text, y in zip(df["text"], df["labels"].astype(int)):
        if y == 1 and analyse_text(text).level == "low":
            n_miss += 1
            miss.update(grams(text))
        elif y == 0:
            n_ben += 1
            ben.update(grams(text))
    print(f"Dev half: {n_miss} missed scams, {n_ben} benign calls.\n")
    rows = [(m, ben[g], g) for g, m in miss.items() if m >= 6 and ben[g] <= max(1, n_ben // 100)]
    rows.sort(key=lambda r: (-(r[0] - 5 * r[1]), r[2]))
    seen: list[str] = []
    print("misses | benign | phrase   (longer phrases that contain an already listed one are skipped)")
    shown = 0
    for m, b, g in rows:
        if any(s in g for s in seen):
            continue
        seen.append(g)
        print(f"{m:6d} | {b:6d} | {g}")
        shown += 1
        if shown >= a.top:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
