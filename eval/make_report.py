"""Turn a run folder into tables:   python -m eval.make_report eval\\results\\dev-20261020-101500"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from .metrics import summarise


def pct(r: dict) -> str:
    if r["n"] == 0:
        return "n/a"
    return f"{r['k']}/{r['n']} = {r['rate']*100:.0f}% (95% CI {r['lo']*100:.0f}-{r['hi']*100:.0f}%)"


def load(run: Path) -> tuple[list[dict], dict]:
    recs = [json.loads(l) for l in (run / "records.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8")) if (run / "meta.json").exists() else {}
    return recs, meta


def to_markdown(s: dict, meta: dict) -> str:
    L = [f"# Evaluation summary ({meta.get('split', '?')} split)", ""]
    L.append(f"- Recordings x conditions analysed: {s['n_records']} ({s['n_errors']} errors)")
    L.append(f"- Real speakers: {', '.join(s['speakers']) or 'none'} ({len(s['speakers'])}); synthetic voices: {', '.join(s['synthetic_voices']) or 'none'}")
    L.append(f"- Word-list version: {meta.get('lexicon_hash', '?')}; engine {meta.get('engine_version', '?')}; estimated Gnani cost Rs {s['cost_rupees']}")
    if meta.get("contaminated"):
        L.append("- **WARNING: the test scripts had already been run with a different version of the word lists, so these numbers are optimistic.**")
    if len(s["speakers"]) < 3:
        L.append("- **Caution: fewer than 3 real speakers. Results describe these voices, not people in general.**")
    L += ["", "## 1. Is the conversation flagged correctly?", "",
          "'high' counts only the top level; 'any alert' counts elevated or high. Recall = scam calls caught. "
          "False alarms = benign calls flagged. Intervals are Wilson 95% and are wide because samples are small.", "",
          "| group | name | scams | benign | recall (high) | false alarms (high) | recall (any alert) | false alarms (any alert) | unreliable |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in s["conversation"]:
        L.append(f"| {r['group']} | {r['name']} | {r['scams']} | {r['benign']} | {pct(r['recall_high'])} | {pct(r['false_alarm_high'])} | "
                 f"{pct(r['recall_any'])} | {pct(r['false_alarm_any'])} | {r['unreliable']} |")
    L += ["", "## 2. Does Gnani transcribe it well? (real voices, word error rate against the script)", "",
          "| language | condition | n | mean WER | worst |", "|---|---|---|---|---|"]
    for r in s["stt"]:
        L.append(f"| {r['language']} | {r['condition']} | {r['n']} | {r['mean_wer']*100:.0f}% | {r['max_wer']*100:.0f}% |")
    a = s["authenticity"]
    L += ["", "## 3. Audio authenticity (AASIST-L median window score; higher means more natural-sounding)", "",
          "| voice | condition | n | median | min | max | labels |", "|---|---|---|---|---|---|---|"]
    for r in a["by_group"]:
        L.append(f"| {r['voice']} | {r['condition']} | {r['n']} | {r['median_of_medians']:.2f} | {r['min']:.2f} | {r['max']:.2f} | {r['codes']} |")
    if a["auc"]:
        L += ["", "Ability to rank real above synthetic voices (AUC, 0.5 = chance, 1.0 = perfect):", "",
              "| condition | real n | synthetic n | AUC (95% bootstrap CI) |", "|---|---|---|---|"]
        for r in a["auc"]:
            val = "n/a (need both kinds)" if r["auc"] is None else f"{r['auc']:.2f} ({r['lo']:.2f}-{r['hi']:.2f})"
            L.append(f"| {r['condition']} | {r['n_real']} | {r['n_synthetic']} | {val} |")
    if a["phone_shift"]:
        L.append(f"\nPhone-quality audio moved real voices by {a['phone_shift']['mean_change']:+.2f} on average (n={a['phone_shift']['n']}).")
    L += ["", "## 4. Where it went wrong", ""]
    if not s["failures"]:
        L.append("No misclassified recordings in this run.")
    else:
        L += ["| file | condition | label | result | why | evidence found |", "|---|---|---|---|---|---|"]
        for f in s["failures"]:
            L.append(f"| {f['file']} | {f['condition']} | {f['label']} | {f.get('level', 'error')} | {f['why']} | {', '.join(f.get('categories', [])) or '-'} |")
    L += ["", "## How to read this honestly", "",
          "- Small samples: a perfect score on a handful of recordings does not mean the system is perfect.",
          "- The scripts are read aloud, which is easier than real calls (interruptions, accents, background noise, two voices).",
          "- Synthetic test voices are older text-to-speech engines unless stated; modern cloned voices were not tested.",
          "- Phone conditions are a simulation (band-pass, 8 kHz, mu-law), not a real network."]
    return "\n".join(L) + "\n"


def write_csvs(s: dict, run: Path) -> None:
    with open(run / "conversation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group", "name", "scams", "benign", "recall_high", "false_alarm_high", "recall_any", "false_alarm_any", "unreliable"])
        for r in s["conversation"]:
            w.writerow([r["group"], r["name"], r["scams"], r["benign"]] +
                       [f"{x['k']}/{x['n']}" for x in (r["recall_high"], r["false_alarm_high"], r["recall_any"], r["false_alarm_any"])] + [r["unreliable"]])
    with open(run / "failures.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "condition", "label", "level", "why", "categories", "quotes"])
        for r in s["failures"]:
            w.writerow([r["file"], r["condition"], r["label"], r.get("level", ""), r["why"],
                        " ".join(r.get("categories", [])), " | ".join(r.get("quotes", []))])


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    run = Path(argv[0])
    recs, meta = load(run)
    s = summarise(recs)
    (run / "summary.md").write_text(to_markdown(s, meta), encoding="utf-8")
    write_csvs(s, run)
    print(f"Wrote {run / 'summary.md'}, conversation.csv and failures.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
