"""Gnani speech-to-text with a disk cache, so re-running an analysis costs nothing and tests never re-bill.

REST   : one call, up to 60 s of audio, one language code.
Batch  : longer files, or when --batch is used (supports bias words and speaker separation).
The cache key covers the audio bytes, language code, mode and options.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from . import config
from .audio_io import duration_seconds, sha256_file


class TranscriptionError(RuntimeError):
    pass


@dataclass
class Variant:
    code: str
    mode: str                      # rest | batch
    text: str
    segments: list = field(default_factory=list)
    model: str | None = None
    seconds: float = 0.0           # wall time of the original call
    audio_seconds: float = 0.0
    cached: bool = False
    error: str | None = None

    def to_dict(self):
        return asdict(self)


def load_api_key() -> str | None:
    key = os.getenv("GNANI_API_KEY", "").strip()
    if key:
        return key
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None
    for f in config.ENV_FILES:
        if f.exists():
            load_dotenv(f)
            key = os.getenv("GNANI_API_KEY", "").strip()
            if key and key != "your-gnani-api-key":
                return key
    return None


class GnaniTranscriber:
    def __init__(self, api_key: str | None = None, cache_dir: Path | None = None, batch: bool = False,
                 bias: bool = False, rest_client=None, batch_client=None, batch_timeout: float = 180):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir or config.CACHE_DIR / "gnani")
        self.batch, self.bias, self.batch_timeout = batch, bias, batch_timeout
        self._rest, self._batch = rest_client, batch_client

    # -- clients are created lazily so cached runs need no API key --------------------------------
    def _rest_client(self):
        if self._rest is None:
            from gnani.stt import GnaniSTTClient

            self._rest = GnaniSTTClient(api_key=self._key())
        return self._rest

    def _batch_client(self):
        if self._batch is None:
            from gnani.stt import GnaniSTTBatchClient

            self._batch = GnaniSTTBatchClient(api_key=self._key())
        return self._batch

    def _key(self) -> str:
        key = self.api_key or load_api_key()
        if not key:
            raise TranscriptionError("GNANI_API_KEY not found. Put it in .env (see .env.example).")
        return key

    # ------------------------------------------------------------------------------------------
    def transcribe(self, path: Path, lang: str) -> list[Variant]:
        codes = config.LANG_CODES.get(lang)
        if not codes:
            raise TranscriptionError(f"Unknown language '{lang}'. Use one of: {', '.join(config.LANG_CODES)}")
        audio_hash = sha256_file(path)
        audio_s = duration_seconds(path)
        mode = "batch" if (self.batch or audio_s > config.REST_MAX_SECONDS) else "rest"
        variants = []
        for code in codes:
            v = self._one(path, audio_hash, audio_s, code, mode)
            variants.append(v)
        if not any(v.text for v in variants):
            errs = "; ".join(f"{v.code}: {v.error}" for v in variants if v.error) or "empty transcript"
            raise TranscriptionError(f"No transcript produced ({errs})")
        return variants

    def _one(self, path: Path, audio_hash: str, audio_s: float, code: str, mode: str) -> Variant:
        opts = {"bias": bool(self.bias and mode == "batch")}
        key = hashlib.sha256(json.dumps([audio_hash, code, mode, opts], sort_keys=True).encode()).hexdigest()[:32]
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            d = json.loads(cache_file.read_text(encoding="utf-8"))
            return Variant(**{**d, "cached": True})
        t0 = time.perf_counter()
        try:
            if mode == "rest":
                res = self._rest_client().transcribe(str(path), language_code=code, format="verbatim")
                text, segs, model = res.get("transcript", ""), [], res.get("model")
            else:
                kw = {"bias_words": config.BIAS_WORDS, "bias_score": 1.0} if opts["bias"] else {}
                res = self._batch_client().transcribe(str(path), language_code=code, progress=False,
                                                      raise_on_failure=False, timeout=self.batch_timeout, **kw)
                f = res[0]
                if not f.ok:
                    raise TranscriptionError(f"batch job failed: {getattr(f, 'error', None)}")
                text = f.text
                segs = [{"start": s.start, "end": s.end, "speaker": s.speaker, "text": s.text} for s in (f.segments or [])]
                model = "gnani-prisma-v2.5 (batch default)"
        except Exception as e:  # keep going: for Hinglish the other code may still work
            return Variant(code, mode, "", error=f"{type(e).__name__}: {e}", audio_seconds=audio_s)
        v = Variant(code, mode, text or "", segs, model, round(time.perf_counter() - t0, 2), round(audio_s, 2))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({k: val for k, val in v.to_dict().items() if k != "cached"},
                                         ensure_ascii=False), encoding="utf-8")
        self._ledger(audio_hash, mode, code, audio_s)
        return v

    def _ledger(self, audio_hash: str, mode: str, code: str, audio_s: float) -> None:
        ledger = self.cache_dir.parent / "gnani_ledger.csv"
        new = not ledger.exists()
        with open(ledger, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "audio_sha", "mode", "code", "audio_seconds", "est_rupees"])
            w.writerow([datetime.now().isoformat(timespec="seconds"), audio_hash[:10], mode, code,
                        round(audio_s, 1), round(audio_s / 60 * config.RUPEES_PER_MIN, 2)])
