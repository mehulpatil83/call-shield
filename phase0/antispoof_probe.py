"""Step 7: load a pretrained anti-spoofing model and score your clips on CPU.

Models (MIT-licensed checkpoints published by SpeechAntiSpoofingBenchmarks on Hugging Face):
  aasist-l  AASIST-L     tiny, pure PyTorch   <- start here on CPU
  aasist    AASIST       pure PyTorch
  w2v2      W2V2-AASIST  best generalisation, needs fairseq + 1.2 GB XLS-R checkpoint, heavy on CPU

Scores: higher = more bona fide (human). There is NO universal threshold yet. At this stage we measure:
does it run, seconds per ~4 s window, RAM, and how scores move between clean and phone-quality audio.
--quantize (experimental) tries int8 dynamic quantisation of the Linear layers for a CPU speed-up and
prints speed AND score change, because a faster model that changes its answers is not a win.
"""
import argparse
import importlib
import inspect
import os
import sys
import time
import types
import urllib.request

import numpy as np

from common import (AUDIO_DIR, MODELS_DIR, VARIANT_DIR, base_stem, list_audio, load_mono, log_result,
                    resample, setup_console, variant_name)

setup_console()
MODELS = {
    "aasist-l": dict(repo="SpeechAntiSpoofingBenchmarks/AASIST-L", module="aasist_l", extra=None),
    "aasist": dict(repo="SpeechAntiSpoofingBenchmarks/AASIST", module="aasist", extra=None),
    "w2v2": dict(repo="SpeechAntiSpoofingBenchmarks/W2V2-AASIST", module="w2v2_aasist",
                 extra=("https://dl.fbaipublicfiles.com/fairseq/wav2vec/xlsr2_300m.pt", "xlsr2_300m.pt")),
}
WINDOW = 64600  # ~4.04 s at 16 kHz, the length these models were trained on

ap = argparse.ArgumentParser()
ap.add_argument("--model", choices=MODELS, default="aasist-l")
ap.add_argument("--download", action="store_true", help="download weights (w2v2 is about 1.5 GB total)")
ap.add_argument("--onnx", action="store_true", help="also download the .onnx export (large; not used by this script)")
ap.add_argument("--variants", default="16k,tel8k_up16k", help="variant names to score from variants/")
ap.add_argument("--include-orig", action="store_true", help="also score the originals in audio/")
ap.add_argument("--threads", type=int, default=0, help="CPU threads for PyTorch (default: physical cores)")
ap.add_argument("--quantize", action="store_true", help="experimental int8 dynamic quantisation, compared with fp32")
args = ap.parse_args()
cfg = MODELS[args.model]
local = MODELS_DIR / args.model

if args.model == "w2v2":
    try:
        import fairseq  # noqa: F401
    except Exception as e:
        print(f"W2V2-AASIST needs the 'fairseq' package, which is not importable here ({type(e).__name__}).")
        print("Not downloading about 2.5 GB for nothing. Use --model aasist-l for now (README step 7).")
        raise SystemExit(1)

if args.download or not local.exists():
    from huggingface_hub import snapshot_download

    ignore = [".eval_results/*"] + ([] if args.onnx else ["*.onnx"])
    print("Downloading", cfg["repo"], "->", local, "(skipping benchmark score files" + ("" if args.onnx else " and the .onnx export") + ")")
    snapshot_download(repo_id=cfg["repo"], local_dir=str(local), ignore_patterns=ignore)
    if cfg["extra"]:
        url, name = cfg["extra"]
        target = local / name
        if not target.exists():
            print("Downloading base checkpoint", name, "(about 1.2 GB, one time)...")
            urllib.request.urlretrieve(url, str(target),
                                       lambda b, bs, tot: print(f"\r  {min(b*bs, tot)/1e6:.0f}/{tot/1e6:.0f} MB", end=""))
            print()


def ensure_speech_spoof_bench() -> None:
    """The Hugging Face wrappers subclass a base class from the benchmark's own package. We only need that
    base class to exist, so if the package is not installed we provide a tiny stand-in."""
    try:
        import speech_spoof_bench.model  # noqa: F401
        return
    except ImportError:
        pass
    pkg, sub = types.ModuleType("speech_spoof_bench"), types.ModuleType("speech_spoof_bench.model")

    class AntiSpoofingModel:
        name, expected_sample_rate, batch_size = "", 16000, 1

        def load(self):
            raise NotImplementedError

        def score_batch(self, audios, srs):
            raise NotImplementedError

        def unload(self):
            pass

    sub.AntiSpoofingModel = AntiSpoofingModel
    pkg.model = sub
    sys.modules["speech_spoof_bench"], sys.modules["speech_spoof_bench.model"] = pkg, sub
    print("(speech_spoof_bench is not installed: using a small built-in stand-in for its base class)")


sys.path.insert(0, str(local))
import torch  # noqa: E402

try:
    import psutil

    proc = psutil.Process(os.getpid())
    threads = args.threads or psutil.cpu_count(logical=False) or os.cpu_count() or 4
except ImportError:
    proc, threads = None, args.threads or os.cpu_count() or 4
torch.set_num_threads(threads)
print(f"CPU-only run | torch {torch.__version__} | threads: {threads}")

ensure_speech_spoof_bench()
try:
    mod = importlib.import_module(cfg["module"])
except Exception as e:  # fairseq / package problems land here
    print(f"\nCould not import {cfg['module']}: {type(e).__name__}: {e}")
    print("If this mentions fairseq or a missing package, copy the full message back to me,")
    print("and use the pure-PyTorch model instead:  python antispoof_probe.py --model aasist-l")
    raise SystemExit(1)

classes = [c for _, c in inspect.getmembers(mod, inspect.isclass)
           if c.__module__ == mod.__name__ and hasattr(c, "load") and hasattr(c, "score_batch")]
if not classes:
    raise SystemExit(f"No model class with load()/score_batch() found in {cfg['module']}. Paste me the file list of {local}.")
model = classes[0]()
t0 = time.perf_counter()
model.load()
print(f"Model {classes[0].__name__} loaded in {time.perf_counter() - t0:.1f}s")

files = list_audio(VARIANT_DIR, set(args.variants.split(",")))
if args.include_orig:
    files = list_audio(AUDIO_DIR) + files
if not files:
    raise SystemExit("No clips to score. Record audio and run make_variants.py first.")
clips = {}
for p in files:
    x, sr = load_mono(p)
    x = resample(x, sr, 16000)
    clips[p] = [x[i:i + WINDOW].astype(np.float32) for i in range(0, len(x), WINDOW) if len(x[i:i + WINDOW]) >= 16000]


def run(label: str) -> dict:
    """Score every clip; returns {path: (scores, seconds_per_window)}."""
    out = {}
    print(f"\n[{label}] {'file':42s} {'win':>3s} {'mean':>7s} {'min':>7s} {'max':>7s} {'s/win':>6s}")
    for p, wins in clips.items():
        if not wins:
            print(f"{'':{len(label)+3}s}{p.name:42s} too short (<1 s)")
            continue
        t1 = time.perf_counter()
        scores = [float(np.asarray(model.score_batch([w], [16000])).ravel()[0]) for w in wins]
        per = (time.perf_counter() - t1) / len(wins)
        s = np.array(scores)
        print(f"{'':{len(label)+3}s}{p.name:42s} {len(wins):3d} {s.mean():7.2f} {s.min():7.2f} {s.max():7.2f} {per:6.2f}")
        out[p] = (scores, per)
        log_result("antispoof_probe", {"model": args.model, "mode": label, "file": p.name, "base": base_stem(p.stem),
                                       "variant": variant_name(p.stem), "windows": len(wins),
                                       "scores": [round(v, 3) for v in scores], "sec_per_window": round(per, 3),
                                       "threads": threads})
    return out


# warm-up so the first timed clip is not penalised by lazy initialisation
first = next((w for w in clips.values() if w), None)
if first:
    model.score_batch([first[0]], [16000])
base = run("fp32")
if proc:
    print(f"\nProcess RAM now: {proc.memory_info().rss / 1e9:.2f} GB")
rtf = [per / (WINDOW / 16000) for _, per in base.values()]
if rtf:
    print(f"Real-time factor (compute time / audio time): {np.mean(rtf):.2f}  (below 1.0 = faster than real time)")

if args.quantize:
    print("\nTrying int8 dynamic quantisation (experimental)...")
    done = []
    try:
        for attr, m in list(vars(model).items()):
            if isinstance(m, torch.nn.Module):
                setattr(model, attr, torch.quantization.quantize_dynamic(m.cpu().eval(), {torch.nn.Linear}, dtype=torch.qint8))
                done.append(attr)
        if not done:
            print("No torch module attribute found on the wrapper; cannot quantise it automatically.")
        else:
            quant = run("int8")
            diffs = [abs(np.mean(quant[p][0]) - np.mean(base[p][0])) for p in base if p in quant]
            speed = np.mean([base[p][1] / quant[p][1] for p in base if p in quant])
            print(f"\nQuantised {done}: speed-up x{speed:.2f}, mean |score change| {np.mean(diffs):.3f}")
            print("If scores moved a lot relative to the spread between clean and phone audio, do NOT use it.")
    except Exception as e:
        print(f"Quantisation failed: {type(e).__name__}: {e}")
if hasattr(model, "unload"):
    model.unload()
