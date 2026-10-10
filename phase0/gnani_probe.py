"""Step 5: probe Gnani STT (REST + batch) on your recorded clips.

REST  : single call, 60 s max per file, one language code.
Batch : diarization, server-side denoise, vocabulary biasing, per-turn language
        identification ("hi-IN,en-IN"), "auto" language.
Every call is logged to results/ and to the credit ledger.
"""
import argparse
import time

from common import (AUDIO_DIR, LANG_PREFIX_CODES, Timer, VARIANT_DIR, cer, duration_seconds,
                    ledger_add, ledger_total_minutes, lang_prefix, list_audio, load_env, log_result,
                    key_terms_found, reference_texts, setup_console, variant_name, wer)

setup_console()

BIAS_WORDS = ["OTP", "KYC", "UPI", "PIN", "CVV", "Aadhaar", "account", "verify", "block", "freeze",
              "ओटीपी", "केवायसी", "यूपीआई", "आधार"]
BATCH_CONFIGS = {
    "base": {},
    "denoise": {"denoise": True},
    "bias": {"bias_words": BIAS_WORDS, "bias_score": 1.0},
    "diar": {"diarization": True, "speakers": 2},
    "mixed": {"_code": "hi-IN,en-IN"},   # per-turn language ID; Hinglish clips only
    "auto": {"_code": "auto"},
}

ap = argparse.ArgumentParser()
ap.add_argument("--dir", choices=["audio", "variants"], default="audio")
ap.add_argument("--only", default="", help="comma list of variants, e.g. orig,tel8k,tel8k_noisy")
ap.add_argument("--mode", choices=["rest", "batch"], default="rest")
ap.add_argument("--format", choices=["verbatim", "transcribe"], default="verbatim",
                help="REST only. 'transcribe' = inverse text normalisation (hi-IN/en-IN only)")
ap.add_argument("--configs", default="base,denoise,bias", help="batch configs: " + ",".join(BATCH_CONFIGS))
ap.add_argument("--codes", default="", help="override language codes, comma separated")
ap.add_argument("--file", default="", help="only files whose name contains this text, e.g. --file en_synth_scam")
ap.add_argument("--timeout", type=float, default=120, help="batch only: give up on a job after this many seconds (SDK default is to wait forever)")
ap.add_argument("--pause", type=float, default=3, help="batch only: seconds to wait between jobs (avoids HTTP 429 rate limits)")
ap.add_argument("--list-languages", action="store_true")
ap.add_argument("--dry-run", action="store_true", help="show the plan and estimated credits, call nothing")
ap.add_argument("--rupees-per-min", type=float, default=0.45, help="from your dashboard: 5000 INR ~ 11.1k min")
args = ap.parse_args()

import gnani.stt as g  # noqa: E402

if args.list_languages:
    print("REST/batch languages:", g.SUPPORTED_LANGUAGES)
    print("Streaming languages :", g.STREAM_SUPPORTED_LANGUAGES)
    raise SystemExit

directory = AUDIO_DIR if args.dir == "audio" else VARIANT_DIR
only = {v.strip() for v in args.only.split(",") if v.strip()} or None
files = list_audio(directory, only)
if args.file:
    files = [p for p in files if args.file in p.name]
if not files:
    raise SystemExit(f"No matching audio in {directory}. Did you run make_variants.py?")

# ---- build the plan: (path, code, config_name, options) ----------------------
plan = []
for p in files:
    prefix = lang_prefix(p.stem)
    codes = [c.strip() for c in args.codes.split(",") if c.strip()] or LANG_PREFIX_CODES.get(prefix)
    if not codes:
        print(f"skip {p.name}: unknown prefix '{prefix}' (name files en_*, hinglish_*, mr_* or pass --codes)")
        continue
    dur = duration_seconds(p)
    if args.mode == "rest":
        if dur > 60:
            print(f"skip {p.name}: {dur:.0f}s > 60s REST limit (use --mode batch)")
            continue
        plan += [(p, c, "rest", {}) for c in codes]
    else:
        for name in [c.strip() for c in args.configs.split(",") if c.strip()]:
            opts = dict(BATCH_CONFIGS[name])
            code = opts.pop("_code", codes[0])
            if name == "mixed" and prefix != "hinglish":
                continue
            plan.append((p, code, name, opts))

total_min = sum(duration_seconds(p) for p, *_ in plan) / 60.0
print(f"Plan: {len(plan)} call(s), {total_min:.1f} min of audio, about Rs {total_min * args.rupees_per_min:.1f}")
if args.dry_run:
    for p, code, name, opts in plan:
        print(f"  {p.name:36s} {code:12s} {name}")
    raise SystemExit

key = load_env()
rest = g.GnaniSTTClient(api_key=key)
batch = g.GnaniSTTBatchClient(api_key=key) if args.mode == "batch" else None

rows = []
def process(p, code, name, opts):
    dur = duration_seconds(p)
    rec = {"file": p.name, "variant": variant_name(p.stem), "code": code, "config": name,
           "mode": args.mode, "audio_s": round(dur, 2)}
    try:
        with Timer() as t:
            if args.mode == "rest":
                res = rest.transcribe(str(p), language_code=code, format=args.format)
                text, segs, extra = res.get("transcript", ""), None, {
                    k: res.get(k) for k in ("model", "processing_time", "end_to_end_latency")}
            else:
                res = batch.transcribe(str(p), language_code=code, progress=False,
                                       raise_on_failure=False, timeout=args.timeout, **opts)
                f = res[0]
                if not f.ok:
                    raise RuntimeError(f"batch file failed: {getattr(f, 'error', None)}")
                text = f.text
                segs = [{"start": s.start, "end": s.end, "speaker": s.speaker, "text": s.text}
                        for s in (f.segments or [])]
                extra = {}
        rec.update(ok=True, seconds=round(t.seconds, 2), text=text, segments=segs, **extra)
        ledger_add(args.mode, dur, f"{p.name} {code} {name}")
    except Exception as e:  # keep going: errors are data (unsupported code, limits...)
        rec.update(ok=False, error=f"{type(e).__name__}: {e}")
    refs = reference_texts(p.stem)
    if rec.get("ok"):
        rec["terms"] = key_terms_found(rec["text"])
        if refs:
            rec["wer"] = round(min(wer(r, rec["text"]) for r in refs), 3)
            rec["cer"] = round(min(cer(r, rec["text"]) for r in refs), 3)
    log_result(f"{args.mode}_probe", rec)
    rows.append(rec)
    status = f"WER {rec['wer']:.2f}" if "wer" in rec else ("ok" if rec.get("ok") else "ERROR")
    print(f"[{status:>9}] {p.name:34s} {code:12s} {name:8s} {rec.get('text', rec.get('error', ''))[:70]}")
    if rec.get("ok"):
        print(f"{'':12s}terms found: {', '.join(rec['terms']) or '-'}")

try:
    for item in plan:
        process(*item)
        if args.mode == "batch":
            time.sleep(args.pause)   # gentle on the API: the SDK polls and gets HTTP 429 if we go too fast
except KeyboardInterrupt:
    print("\nStopped with Ctrl+C. Results so far are saved in results/.")

print(f"\nDone. Billed-audio estimate this session ledger total: {ledger_total_minutes():.1f} min")
print("Now compare your dashboard balance with the number above (README step 8).")
