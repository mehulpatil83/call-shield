"""Rules-only evaluation of the acted English call scripts (perfect transcripts: no audio, no Gnani).

    python -m eval.call_eval                              DEV scripts (fine to look at and tune on)
    python -m eval.call_eval --split test --i-am-done-tuning      TEST scripts, final numbers, run once
    python -m eval.call_eval --split all --i-am-done-tuning       both, with a markdown file in eval/results/

For each script it reports the final risk level and how soon an alert would have fired, by feeding the transcript in
growing pieces at a speaking rate of 150 words per minute. That time excludes speech-to-text delay, so real delays
are longer. A "false alarm" is a benign script rated elevated or high ("false high" = high only). A "miss" is a scam
rated low; a scam rated only elevated counts as "caught, but not high"."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.model import combine, get_model
from core.rules import analyse_text

from .call_scripts import CALLS, by_split

WORDS_PER_SECOND = 2.5
STEP_WORDS = 4
RANK = {"low": 0, "elevated": 1, "high": 2}


def alert_times(text: str) -> dict:
    """Seconds (at 150 wpm) until the level first reaches elevated and high when the text arrives a few words at a time."""
    words = text.split()
    first = {"elevated": None, "high": None}
    for n in range(STEP_WORDS, len(words) + STEP_WORDS, STEP_WORDS):
        r = analyse_text(" ".join(words[:n]))
        t = round(min(n, len(words)) / WORDS_PER_SECOND, 1)
        for lvl in ("elevated", "high"):
            if first[lvl] is None and RANK[r.level] >= RANK[lvl]:
                first[lvl] = t
    return first


def evaluate(scripts: list[dict], use_model: bool = False) -> dict:
    rows = []
    for s in scripts:
        r = analyse_text(s["text"])
        level, prob = r.level, None
        if use_model:
            prob = get_model().score(s["text"])
            level, _ = combine(r.level, prob, len(s["text"].split()))
        r.level = level
        cats = sorted({h.category for h in r.hits if h.kind != "warning"})
        rows.append({**s, "level": r.level, "score": r.score, "cats": cats, "prob": prob, "times": alert_times(s["text"])})
    scams = [r for r in rows if r["label"] == "scam"]
    benign = [r for r in rows if r["label"] == "benign"]
    return {
        "rows": rows,
        "scams": len(scams), "benign": len(benign),
        "scam_high": sum(r["level"] == "high" for r in scams),
        "scam_elevated_only": sum(r["level"] == "elevated" for r in scams),
        "scam_missed": sum(r["level"] == "low" for r in scams),
        "false_alarms": sum(r["level"] != "low" for r in benign),
        "false_high": sum(r["level"] == "high" for r in benign),
        "easy_false_alarms": sum(r["level"] != "low" for r in benign if not r["hard"]),
        "hard_false_alarms": sum(r["level"] != "low" for r in benign if r["hard"]),
        "hard_total": sum(r["hard"] for r in benign),
    }


def to_text(result: dict, title: str) -> str:
    out = [f"{title}", ""]
    for r in result["rows"]:
        want_ok = (r["level"] == "high") if r["label"] == "scam" else (r["level"] == "low")
        t = r["times"]
        timing = f"alert at {t['elevated']}s, high at {t['high']}s" if r["label"] == "scam" else ""
        pm = f" model {r['prob']:.3f}" if r.get("prob") is not None else ""
        out.append(f"{'ok ' if want_ok else 'BAD'} {r['id']:6s} {r['label']:6s}{' (hard)' if r['hard'] else '       '} -> {r['level']:9s}{pm} "
                   f"{', '.join(r['cats']) or '-':55s} {timing}")
    out += ["",
            f"Scams: {result['scam_high']}/{result['scams']} rated high, {result['scam_elevated_only']} only elevated, "
            f"{result['scam_missed']} missed (rated low).",
            f"Benign: {result['false_alarms']}/{result['benign']} false alarms (elevated or high), {result['false_high']} false high. "
            f"Of these, ordinary calls {result['easy_false_alarms']}, hard cases {result['hard_false_alarms']}/{result['hard_total']}.",
            "Perfect transcripts. Real speech-to-text makes mistakes, so real numbers will be worse."]
    return "\n".join(out)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--i-am-done-tuning", action="store_true")
    ap.add_argument("--model", action="store_true", help="add the language model as a second opinion (needs models/model_v2_fp16)")
    ap.add_argument("--write", action="store_true", help="also write eval/results/call_eval_<split>.txt")
    a = ap.parse_args(argv)
    if a.split != "dev" and not a.i_am_done_tuning:
        print("The test scripts are for final numbers only. If you are still changing the word lists, use --split dev.\n"
              "Add --i-am-done-tuning to run them anyway.")
        return 1
    scripts = list(CALLS.values()) if a.split == "all" else by_split(a.split)
    if a.model:
        m = get_model()
        m.load()
        if m.status != "ready":
            print("The model could not be loaded:", m.error)
            return 1
    label = "rules + model" if a.model else "rules only"
    text = to_text(evaluate(scripts, use_model=a.model), f"Call-script evaluation, {a.split} scripts, {label}")
    print(text)
    if a.write:
        p = Path("eval/results")
        p.mkdir(parents=True, exist_ok=True)
        (p / f"call_eval_{a.split}.txt").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
