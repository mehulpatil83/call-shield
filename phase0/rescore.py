"""Re-score saved Gnani results WITHOUT calling Gnani (free).

Use it after you change a reference text (for example add audio/hinglish_scam.alt.txt, the same words in
Devanagari) or the key-term lists in common.py. It reads results/rest_probe.jsonl and results/batch_probe.jsonl.
    python rescore.py            real recordings only
    python rescore.py --all      include the synthetic clips
"""
import argparse
import json
from pathlib import Path

from common import RESULTS_DIR, cer, key_terms_found, reference_texts, setup_console, wer

setup_console()
ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true", help="include *_synth_* clips")
args = ap.parse_args()

print(f"{'file':34s} {'code':12s} {'cfg':8s} {'WER old->new':>14s} {'CER':>5s}  terms")
for name in ("rest_probe", "batch_probe"):
    path = RESULTS_DIR / f"{name}.jsonl"
    if not path.exists():
        continue
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if not r.get("ok") or (not args.all and "synth" in r["file"]):
            continue
        stem = Path(r["file"]).stem
        refs = reference_texts(stem)
        new_wer = min(wer(x, r["text"]) for x in refs) if refs else None
        new_cer = min(cer(x, r["text"]) for x in refs) if refs else None
        old = r.get("wer")
        fmt = lambda v: "  -" if v is None else f"{v:.2f}"
        print(f"{r['file']:34s} {r['code']:12s} {r['config']:8s} {fmt(old):>6s} -> {fmt(new_wer):>5s} {fmt(new_cer):>5s}  "
              f"{', '.join(key_terms_found(r['text'])) or '-'}")
