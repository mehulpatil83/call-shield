"""Step 9: summarise results/ into small tables (mean WER/CER by language, variant and setting)."""
import json
from collections import defaultdict
from statistics import mean

from common import RESULTS_DIR, ledger_total_minutes, lang_prefix, setup_console

setup_console()
for name in ("rest_probe", "batch_probe"):
    path = RESULTS_DIR / f"{name}.jsonl"
    if not path.exists():
        continue
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    groups = defaultdict(list)
    errors = defaultdict(int)
    for r in rows:
        key = (lang_prefix(r["file"]), r["variant"], r["code"], r["config"])
        if r.get("ok") and "wer" in r:
            groups[key].append(r)
        elif not r.get("ok"):
            errors[key] += 1
    print(f"\n=== {name} ===")
    print(f"{'lang':9s}{'variant':13s}{'code':13s}{'config':9s}{'n':>3s}{'WER':>7s}{'CER':>7s}{'sec/call':>9s}")
    for key, rs in sorted(groups.items()):
        print(f"{key[0]:9s}{key[1]:13s}{key[2]:13s}{key[3]:9s}{len(rs):3d}"
              f"{mean(r['wer'] for r in rs):7.2f}{mean(r['cer'] for r in rs):7.2f}{mean(r['seconds'] for r in rs):9.1f}")
    for key, n in sorted(errors.items()):
        print(f"ERRORS x{n}: {key}")
print(f"\nBilled-audio estimate across all runs: {ledger_total_minutes():.1f} min")
