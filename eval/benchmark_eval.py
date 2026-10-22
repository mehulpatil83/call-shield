"""Blind benchmark: synthetic scam / non-scam phone dialogues from a DIFFERENT source than the model's training data.

Data: BothBosu/Scammer-Conversation (Apache-2.0, English, LLM-generated). Related paper: "AI-in-the-Loop: Privacy Preserving Real-Time
Scam Detection and Conversational Scambaiting" (arXiv 2509.05362). Download no_ident.csv into data/bench/ (git-ignored; do not commit it).

    python -m eval.benchmark_eval --split dev                          (look at errors, check numbers; may be run any time)
    python -m eval.benchmark_eval --split test --i-am-done-tuning      (the locked half: run ONCE, at the very end)

The split is by conversation_id (md5 hash, so it never changes). Calls are scored as GROWING PREFIXES (first 25%, 50%, 100% of the
words), because a live call starts with only a few words. Rules, model alone, and rules + model are compared with the thresholds
fixed in core/model.py. Nothing here changes a threshold."""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from core.model import ELEVATED_AT, HIGH_AT, MIN_WORDS_ELEVATED, combine, get_model
from core.rules import analyse_text

DATA = Path(__file__).resolve().parent.parent / "data" / "bench"
FRACTIONS = (0.25, 0.5, 1.0)
KNOWN_LABELS = ("Suspect", "Innocent", "Scammer", "Caller", "Receiver", "Victim", "Agent", "Customer", "Person A", "Person B", "Speaker 1", "Speaker 2")


def find_labels(texts, share: float = 0.2) -> list[str]:
    """Speaker labels = capitalised words followed by a colon that occur in at least `share` of the conversations."""
    seen: dict[str, int] = {}
    for t in texts:
        for w in set(re.findall(r"\b([A-Z][A-Za-z]{2,14}(?: ?\d)?)\s*:", str(t))):
            seen[w] = seen.get(w, 0) + 1
    n = max(1, len(texts))
    return sorted(w for w, c in seen.items() if c / n >= share) or list(KNOWN_LABELS)


def clean(text: str, labels=KNOWN_LABELS) -> str:
    """Speaker labels are not in live speech-to-text, so remove them (only the labels found in the data, so 'The OTP: 1234' survives)."""
    rx = re.compile(r"\b(?:" + "|".join(re.escape(x) for x in labels) + r")\s*:\s*", re.IGNORECASE)
    return " ".join(rx.sub(" ", str(text)).split())


def is_test(conversation_id) -> bool:
    return int(hashlib.md5(str(conversation_id).encode()).hexdigest(), 16) % 2 == 1


def prefix(text: str, frac: float) -> str:
    w = text.split()
    return " ".join(w[: max(1, int(len(w) * frac))])


def pct(a: int, b: int) -> str:
    return f"{a}/{b} = {100 * a / b:.1f}%" if b else "-"


def run(rows: list[tuple[str, int]], use_model: bool, show_errors: bool) -> str:
    model = get_model() if use_model else None
    n_scam = sum(y for _, y in rows)
    n_ben = len(rows) - n_scam
    out = [f"{len(rows)} calls: {n_scam} scam, {n_ben} benign. Thresholds fixed in core/model.py: elevated at {ELEVATED_AT}, high at {HIGH_AT}.", ""]
    miss, fa = [], []
    for f in FRACTIONS:
        c = {k: [0, 0] for k in ("rules_any", "rules_high", "model_any", "both_any", "both_high")}   # [scam hits, benign hits]
        for text, y in rows:
            p = prefix(text, f)
            r = analyse_text(p)
            prob = model.score(p) if model else None
            words = len(p.split())
            comb, _ = combine(r.level, prob, words)
            flags = {"rules_any": r.level != "low", "rules_high": r.level == "high",
                     "model_any": prob is not None and prob >= ELEVATED_AT and words >= MIN_WORDS_ELEVATED,
                     "both_any": comb != "low", "both_high": comb == "high"}
            for k, v in flags.items():
                c[k][0 if y else 1] += int(v)
            if f == 1.0 and show_errors:
                if y and comb == "low":
                    miss.append((p, r.level, prob))
                if not y and comb != "low":
                    fa.append((p, r.level, prob))
        out.append(f"First {int(f * 100)}% of each call")
        out.append("                      scams flagged            benign false alarms")
        for k, name in (("rules_any", "rules (elevated+)"), ("rules_high", "rules (high only)"), ("model_any", "model alone"),
                        ("both_any", "rules + model (elev+)"), ("both_high", "rules + model (high)")):
            if k.startswith("model") and not model:
                continue
            out.append(f"  {name:21s} {pct(c[k][0], n_scam):24s} {pct(c[k][1], n_ben)}")
        out.append("")
    if show_errors:
        out.append("Dev only: missed scams (full call, rules+model rated low):")
        for p, lv, pr in miss[:6]:
            out.append(f"  rules={lv} model={pr if pr is None else round(pr, 3)} | {p[:230]}")
        out.append("Dev only: benign calls flagged (full call):")
        for p, lv, pr in fa[:6]:
            out.append(f"  rules={lv} model={pr if pr is None else round(pr, 3)} | {p[:230]}")
        out.append("")
    out.append("Synthetic, LLM-written US-style dialogues: a different source from the training data, but still not real calls. "
               "No accuracy claims; report both numbers (scams flagged AND benign false alarms).")
    return "\n".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DATA / "no_ident.csv"))
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--i-am-done-tuning", action="store_true", help="required for the locked test half")
    ap.add_argument("--again", action="store_true", help="allow a second run of the test half (then it is no longer blind)")
    ap.add_argument("--no-model", action="store_true", help="rules only")
    a = ap.parse_args()
    import pandas as pd
    df = pd.read_csv(a.file)
    if not {"conversation_id", "conversation", "labels"} <= set(df.columns):
        print("Expected columns conversation_id, conversation, labels; found", list(df.columns))
        return 1
    df = df.dropna(subset=["conversation"]).copy()
    labels = find_labels(df["conversation"].tolist())
    print("Speaker labels removed from the text:", ", ".join(labels))
    df["text"] = df["conversation"].map(lambda t: clean(t, labels))
    df = df.drop_duplicates("text")
    want_test = a.split == "test"
    sub = df[df["conversation_id"].map(is_test) == want_test]
    rows = list(zip(sub["text"], sub["labels"].astype(int)))
    lock = Path(a.file).with_name(".test_run_done")
    if want_test:
        if not a.i_am_done_tuning:
            print("The test half is for ONE final run. Add --i-am-done-tuning when you are finished with the dev half.")
            return 1
        if lock.exists() and not a.again:
            print("The test half was already run once (see data\\bench\\results_test.txt). Running it again makes it no longer blind: add --again if you really want to.")
            return 1
    if not a.no_model:
        m = get_model()
        print("Loading the model...")
        m.load()
        if m.status != "ready":
            print("Model not loaded:", m.error, "\n(use --no-model for rules only)")
            return 1
    text = f"Blind benchmark, {a.split} half, {'rules only' if a.no_model else 'rules + model'}\n" + run(rows, not a.no_model, not want_test)
    print(text)
    Path(a.file).with_name(f"results_{a.split}.txt").write_text(text, encoding="utf-8")
    if want_test:
        lock.write_text("done", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
