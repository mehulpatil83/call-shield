"""Run labelled recordings through the full pipeline.

    python -m eval.run_eval --recordings eval\\recordings --split dev --conditions orig,tel8k
    python -m eval.run_eval --split test --conditions orig,tel8k,tel8k_noisy       (only when you are done tuning!)

Everything Gnani returns is cached in eval/.cache, so re-running costs nothing. Add --dry-run to see the cost first."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from core import __version__, config
from core.analyse import analyse_file
from core.audio_io import duration_seconds
from core.authenticity import AuthenticityScorer
from core.degrade import CONDITIONS, make_condition
from core.gnani_client import GnaniTranscriber

from .manifest import Item, scan
from .metrics import best_wer

ROOT = Path(__file__).resolve().parent


def lexicon_hash() -> str:
    h = hashlib.sha256()
    for name in ("lexicon.py", "rules.py", "normalize.py"):
        h.update((Path(config.ROOT) / "core" / name).read_bytes())
    return h.hexdigest()[:12]


def record_for(item: Item, condition: str, lang: str, report: dict, seconds: float) -> dict:
    conv, auth = report["conversation"], report["authenticity"]
    hits = [h for h in conv["hits"] if h["kind"] != "warning"]
    return {
        "file": item.path.name, "speaker": item.speaker, "script_id": item.script_id, "language": item.language,
        "label": item.label, "scenario": item.scenario, "hard": item.hard, "split": item.split, "voice": item.voice,
        "condition": condition, "lang_used": lang, "level": conv["level"], "score": conv["score"],
        "categories": sorted({h["category"] for h in hits}), "quotes": [h["quote"] for h in hits][:8],
        "language_warning": report.get("language_warning"),
        "auth_code": auth["code"] if auth else None, "auth_median": auth["median"] if auth else None,
        "auth_windows": auth["n_windows"] if auth else None,
        "wer": best_wer(item.reference, [t["text"] for t in report["transcripts"]]),
        "cost": report["meta"]["est_cost_rupees"], "seconds": round(seconds, 1),
        "transcripts": [t["text"] for t in report["transcripts"]],
    }


def run_eval(items: list[Item], conditions: list[str], out_dir: Path, transcriber, scorer, lang_mode: str = "true",
             work_dir: Path | None = None, log=print) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(work_dir or ROOT / "work")
    rec_file = out_dir / "records.jsonl"
    done = set()
    records = []
    if rec_file.exists():
        for line in rec_file.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            records.append(r)
            done.add((r["file"], r["condition"]))
    for item in items:
        for cond in conditions:
            if (item.path.name, cond) in done:
                continue
            lang = "auto" if lang_mode == "auto" else item.language
            t0 = time.perf_counter()
            try:
                path = make_condition(item.path, cond, work / f"{item.path.stem}__{cond}.wav")
                report, _ = analyse_file(path, lang, transcriber, scorer, display_name=item.path.name)
                rec = record_for(item, cond, lang, report, time.perf_counter() - t0)
            except Exception as e:
                rec = {"file": item.path.name, "speaker": item.speaker, "script_id": item.script_id, "language": item.language,
                       "label": item.label, "scenario": item.scenario, "hard": item.hard, "split": item.split, "voice": item.voice,
                       "condition": cond, "lang_used": lang, "error": f"{type(e).__name__}: {e}"[:300]}
            records.append(rec)
            with open(rec_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log(f"{item.path.name:28s} {cond:12s} -> {rec.get('level') or rec.get('error')}")
    return records


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recordings", default=str(ROOT / "recordings"))
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--conditions", default="orig,tel8k", help="comma list from: " + ",".join(CONDITIONS))
    ap.add_argument("--lang-mode", choices=["true", "auto"], default="true",
                    help="'true' uses each script's real language; 'auto' tests the not-sure option")
    ap.add_argument("--no-auth", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    items, skipped = scan(Path(a.recordings))
    for name, why in skipped:
        print(f"skipped {name}: {why}")
    if a.split != "all":
        items = [i for i in items if i.split == a.split]
    conditions = [c.strip() for c in a.conditions.split(",") if c.strip()]
    if not items:
        print("No matching recordings. See eval/README.md for the naming rule.")
        return 1
    calls = {"true": lambda i: len(config.LANG_CODES[i.language]), "auto": lambda i: 3}[a.lang_mode]
    minutes = sum(duration_seconds(i.path) / 60 * calls(i) * len(conditions) for i in items)
    print(f"{len(items)} recordings x {len(conditions)} condition(s): about {minutes:.1f} billed minutes, "
          f"Rs {minutes * config.RUPEES_PER_MIN:.1f} if nothing is cached")
    if a.dry_run:
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(a.out or ROOT / "results" / f"{a.split}-{stamp}")
    meta = {"split": a.split, "conditions": conditions, "lang_mode": a.lang_mode, "created": stamp,
            "engine_version": __version__, "lexicon_hash": lexicon_hash(), "contaminated": False}
    if a.split in ("test", "all"):
        log = ROOT / "results" / "test_runs.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        previous = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
        if any(p["lexicon_hash"] != meta["lexicon_hash"] for p in previous):
            meta["contaminated"] = True
            print("WARNING: the TEST scripts were already run with a different version of the word lists. "
                  "Anything you changed after seeing test results makes these numbers optimistic. This is recorded in the report.")
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": stamp, "lexicon_hash": meta["lexicon_hash"], "out": str(out_dir)}) + "\n")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    transcriber = GnaniTranscriber(cache_dir=ROOT / ".cache" / "gnani")
    scorer = None if a.no_auth else AuthenticityScorer(cache_dir=ROOT / ".cache" / "auth")
    run_eval(items, conditions, out_dir, transcriber, scorer, a.lang_mode)
    print(f"\nDone. Next: python -m eval.make_report {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
