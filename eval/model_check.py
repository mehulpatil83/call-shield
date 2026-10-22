"""Check that the model on THIS laptop gives the same scores as in Colab, and measure how fast it runs.

    python -m eval.model_check

Expected values are the fp16 scores printed in Colab for the 20 acted scripts. Differences above 0.02 mean the folder
models/model_v2_fp16 is wrong or damaged. Also prints the time per window on this CPU (the model is scored every few new words)."""
from __future__ import annotations

import sys
import time

from core.model import get_model

from .call_scripts import CALLS

EXPECTED = {"c-s1": .236, "c-s2": .622, "c-s3": .997, "c-s4": .030, "c-s5": .729, "c-b1": .000, "c-b2": .105, "c-b3": .000,
            "c-h1": .000, "c-h2": .073, "c-s6": .000, "c-s7": .993, "c-s8": .927, "c-s9": .403, "c-s10": .993, "c-b4": .000,
            "c-b5": .003, "c-b6": .000, "c-h3": .000, "c-h4": .001}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    m = get_model()
    t0 = time.time()
    m.load()
    if m.status != "ready":
        print("Model not loaded:", m.error)
        print("Check that the folder models\\model_v2_fp16 exists (config.json, model.safetensors, tokenizer files) and that "
              "`pip install transformers` finished.")
        return 1
    print(f"Loaded in {time.time() - t0:.1f}s")
    bad, times = 0, []
    for k, want in EXPECTED.items():
        t = time.time()
        got = m.score(CALLS[k]["text"])
        times.append(time.time() - t)
        ok = abs(got - want) <= 0.02
        bad += (not ok)
        print(f"{'ok ' if ok else 'BAD'} {k:6s} expected {want:.3f} got {got:.3f}")
    times.sort()
    print(f"\n{bad} of {len(EXPECTED)} scores differ from Colab by more than 0.02.")
    print(f"Time per window on this CPU: median {times[len(times) // 2] * 1000:.0f} ms, slowest {times[-1] * 1000:.0f} ms (first call is slower).")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
