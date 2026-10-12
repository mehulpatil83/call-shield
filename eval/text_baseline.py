"""Rules only, perfect transcripts: run the reading scripts' own text through the rule engine (no audio, no Gnani).
This shows how good the word lists are when speech-to-text makes no mistakes.

    python -m eval.text_baseline                  dev scripts (fine to look at and tune on)
    python -m eval.text_baseline --split test --i-am-done-tuning      the test scripts: final numbers, run once"""
from __future__ import annotations

import argparse
import sys

from core.rules import analyse_text

from .scripts_bank import SCRIPTS


def main(argv=None) -> int:
    for s in (sys.stdout,):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--i-am-done-tuning", action="store_true")
    a = ap.parse_args(argv)
    if a.split == "test" and not a.i_am_done_tuning:
        print("The test scripts are for final numbers only. If you are still changing the word lists, use --split dev.\n"
              "Add --i-am-done-tuning to run them anyway.")
        return 1
    wrong = 0
    scripts = [s for s in SCRIPTS.values() if s["split"] == a.split]
    for s in scripts:
        r = analyse_text(s["text"])
        want = "high" if s["label"] == "scam" else "low"
        ok = r.level == want
        wrong += not ok
        cats = ", ".join(sorted({h.category for h in r.hits if h.kind != "warning"})) or "-"
        print(f"{'ok ' if ok else 'BAD'} {s['id']:12s} {s['label']:6s} -> {r.level:9s} ({cats})")
    print(f"\n{len(scripts) - wrong}/{len(scripts)} as expected on the {a.split} scripts (perfect transcripts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
