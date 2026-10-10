"""Step 9 (optional): local Whisper second opinion on CPU with faster-whisper (int8).

Idea: if Gnani and Whisper disagree strongly on a segment, treat the transcript as less certain.
Marathi quality in Whisper is uncertain, which is why this is only a measurement for now.
    pip install faster-whisper
"""
import argparse
import time

from common import AUDIO_DIR, cer, duration_seconds, lang_prefix, list_audio, log_result, reference_texts, setup_console, wer

setup_console()
ap = argparse.ArgumentParser()
ap.add_argument("--model", default="small", help="tiny, base, small, medium (bigger = slower on CPU)")
ap.add_argument("--threads", type=int, default=0)
args = ap.parse_args()

from faster_whisper import WhisperModel  # noqa: E402

LANG = {"en": "en", "hinglish": "hi", "mr": "mr"}
model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=args.threads)
print(f"{'file':26s} {'lang':5s} {'audio_s':>7s} {'proc_s':>7s} {'RTF':>5s} {'WER':>5s}  text")
for p in list_audio(AUDIO_DIR):
    lang = LANG.get(lang_prefix(p.stem))
    t0 = time.perf_counter()
    segs, _ = model.transcribe(str(p), language=lang, beam_size=1)
    text = " ".join(s.text.strip() for s in segs)
    dt, dur = time.perf_counter() - t0, duration_seconds(p)
    refs = reference_texts(p.stem)
    w = min(wer(r, text) for r in refs) if refs else float("nan")
    print(f"{p.name:26s} {lang or '-':5s} {dur:7.1f} {dt:7.1f} {dt/dur:5.2f} {w:5.2f}  {text[:60]}")
    log_result("whisper_probe", {"file": p.name, "model": args.model, "audio_s": round(dur, 2), "proc_s": round(dt, 2),
                                 "wer": None if refs == [] else round(w, 3), "text": text})
