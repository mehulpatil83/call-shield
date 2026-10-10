"""Shared helpers for the Phase 0 smoke tests (paths, audio, WER, credit ledger)."""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from math import gcd
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
AUDIO_DIR = ROOT / "audio"
VARIANT_DIR = ROOT / "variants"
RESULTS_DIR = ROOT / "results"
MODELS_DIR = ROOT / "models"
LEDGER = RESULTS_DIR / "credit_ledger.csv"

# File-name prefix -> language codes to try. Hinglish has no dedicated single
# code in SDK 0.8.1, so we try Hindi, Indian English, and (batch only) the
# comma-separated "hi-IN,en-IN" per-turn language identification.
LANG_PREFIX_CODES = {
    "en": ["en-IN"],
    "hinglish": ["hi-IN", "en-IN"],
    "mr": ["mr-IN"],
}
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}


def setup_console() -> None:
    """Make Devanagari print correctly on a Windows console."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_env() -> str:
    """Load .env (if present) and return the Gnani API key or exit with help."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.getenv("GNANI_API_KEY", "").strip()
    if not key or key == "your-gnani-api-key":
        sys.exit("GNANI_API_KEY is missing. Copy .env.example to .env and paste your key.")
    return key


# ----------------------------------------------------------------- audio ----
def load_mono(path: Path) -> tuple[np.ndarray, int]:
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return x.mean(axis=1), int(sr)


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x.astype(np.float32)
    from scipy.signal import resample_poly

    g = gcd(sr_in, sr_out)
    return resample_poly(x, sr_out // g, sr_in // g).astype(np.float32)


def write_wav(path: Path, x: np.ndarray, sr: int) -> None:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(x, -1.0, 1.0), sr, subtype="PCM_16")


def to_pcm16_bytes(x: np.ndarray) -> bytes:
    return (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def duration_seconds(path: Path) -> float:
    import soundfile as sf

    info = sf.info(str(path))
    return info.frames / float(info.samplerate)


def telephony_sim(x16: np.ndarray, sr: int = 16000, snr_db: float | None = None, seed: int = 0) -> np.ndarray:
    """Cheap, deterministic phone-line simulation. Returns float32 audio at 8 kHz.

    300-3400 Hz band-pass -> 8 kHz resample -> 8-bit mu-law companding
    (G.711-style quantisation) -> optional additive noise at a target SNR.
    This is an approximation, NOT a real codec/network; we say so in the write-up.
    """
    from scipy.signal import butter, sosfiltfilt

    peak = float(np.max(np.abs(x16))) or 1.0
    x = x16 / peak * 0.9
    sos = butter(4, [300, 3400], btype="band", fs=sr, output="sos")
    y = sosfiltfilt(sos, x)
    y8 = resample(y.astype(np.float32), sr, 8000)
    mu = 255.0
    y8 = np.clip(y8, -1.0, 1.0)
    comp = np.sign(y8) * np.log1p(mu * np.abs(y8)) / np.log1p(mu)
    q = np.round((comp + 1.0) / 2.0 * 255.0) / 255.0 * 2.0 - 1.0
    out = np.sign(q) * np.expm1(np.log1p(mu) * np.abs(q)) / mu
    if snr_db is not None:
        active = out[np.abs(out) > 0.02]
        rms = float(np.sqrt(np.mean(active**2))) if active.size else 0.05
        sigma = rms / (10 ** (snr_db / 20.0))
        out = out + np.random.default_rng(seed).normal(0.0, sigma, size=out.shape)
    return out.astype(np.float32)


# ------------------------------------------------------------ file names ----
def lang_prefix(stem: str) -> str:
    return stem.split("_")[0].lower()


def base_stem(stem: str) -> str:
    """'en_scam__tel8k' -> 'en_scam'."""
    return stem.split("__")[0]


def variant_name(stem: str) -> str:
    return stem.split("__")[1] if "__" in stem else "orig"


def reference_texts(stem: str) -> list[str]:
    """All reference transcripts for a clip: <base>.txt plus optional <base>.alt.txt
    (e.g. the same text written in Devanagari). WER is taken against the closest one."""
    out = []
    for name in (f"{base_stem(stem)}.txt", f"{base_stem(stem)}.alt.txt"):
        f = AUDIO_DIR / name
        if f.exists():
            out.append(f.read_text(encoding="utf-8").strip())
    return out


def list_audio(directory: Path, only: set[str] | None = None) -> list[Path]:
    files = sorted(p for p in directory.iterdir() if p.suffix.lower() in AUDIO_EXTS)
    if only:
        files = [p for p in files if variant_name(p.stem) in only]
    return files


# ------------------------------------------------------------------ WER -----
_PUNCT = re.compile(r"[^\w\s\u0900-\u097F]", re.UNICODE)


def normalise_text(s: str) -> list[str]:
    s = unicodedata.normalize("NFC", s).lower()
    s = _PUNCT.sub(" ", s)
    return s.split()


def _edit_distance(a: list, b: list) -> int:
    prev = list(range(len(b) + 1))
    for i, ai in enumerate(a, 1):
        cur = [i]
        for j, bj in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ai != bj)))
        prev = cur
    return prev[-1]


def wer(ref: str, hyp: str) -> float:
    r, h = normalise_text(ref), normalise_text(hyp)
    return _edit_distance(r, h) / max(len(r), 1)


def cer(ref: str, hyp: str) -> float:
    r, h = list("".join(normalise_text(ref))), list("".join(normalise_text(hyp)))
    return _edit_distance(r, h) / max(len(r), 1)


# --------------------------------------------------------------- logging ----
def log_result(name: str, record: dict) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    record = {"ts": datetime.now().isoformat(timespec="seconds"), **record}
    with open(RESULTS_DIR / f"{name}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def ledger_add(mode: str, audio_seconds: float, note: str = "") -> None:
    """Append billed-audio estimate. Compare with your dashboard balance before/after."""
    RESULTS_DIR.mkdir(exist_ok=True)
    new = not LEDGER.exists()
    with open(LEDGER, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "mode", "audio_seconds", "note"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), mode, round(audio_seconds, 2), note])


def ledger_total_minutes() -> float:
    if not LEDGER.exists():
        return 0.0
    with open(LEDGER, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return sum(float(r["audio_seconds"]) for r in rows) / 60.0


class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.seconds = time.perf_counter() - self.t0


# ------------------------------------------------------- key-term check -----
# Script-independent check: did the transcript contain the scam-relevant words, in Latin or
# Devanagari spelling? (WER against a romanised Hinglish reference is unreliable because the
# service may answer in Devanagari.)
KEY_TERMS = {
    "otp": ["otp", "ओटीपी", "ओ टी पी"],
    "kyc": ["kyc", "केवायसी", "के वाय सी", "केवाईसी", "के वाई सी", "के वाइ सी"],
    "upi": ["upi", "यूपीआई", "यू पी आई"],
    "pin": ["pin", "पिन"],
    "account": ["account", "अकाउंट", "खाते", "खाता"],
    "block": ["block", "ब्लॉक", "बंद"],
    "verify": ["verify", "verification", "वेरिफाई", "पडताळणी", "सत्यापन"],
    "freeze": ["freeze", "फ्रीज", "गोठवले", "गोठवल"],
    "anydesk": ["anydesk", "एनीडेस्क", "एनी डेस्क"],
}


def key_terms_found(text: str) -> list[str]:
    t = unicodedata.normalize("NFC", text).lower()
    return sorted(k for k, variants in KEY_TERMS.items() if any(v in t for v in variants))
