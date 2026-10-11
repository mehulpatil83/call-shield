"""Audio authenticity estimate with the pretrained AASIST-L anti-spoofing model, on CPU.

HONEST LIMITS (also shown in every report):
* AASIST-L is weak on fakes it has not seen: published In-the-Wild error rate is about 44%.
* The score bands below are PROVISIONAL, set from 3 real recordings of one speaker and 6 robotic synthetic
  clips in Phase 0. They must be re-calibrated on the Phase 3 evaluation set.
* The label is never a verdict. Short or quiet audio gives "inconclusive".
"""
from __future__ import annotations

import hashlib
import json
import sys
import types
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import config
from .audio_io import load_mono_16k, sha256_file

WINDOW = 64600                # about 4.04 s at 16 kHz, the length the model was trained on
MIN_WINDOWS = 3               # about 12 s of speech
REAL_AT_LEAST = -4.8          # median window score at or above this: consistent with natural speech
SYNTH_AT_MOST = -6.8          # at or below this: consistent with synthetic speech
BAND_NOTE = ("Bands are provisional (from 9 clips, one real speaker) and will be recalibrated in the evaluation phase.")


@dataclass
class AuthResult:
    status: str                       # ok | inconclusive | unavailable
    label: str
    code: str = ""                    # natural | synthetic | inconclusive_band | inconclusive_short | unavailable
    reason: str = ""
    median: float | None = None
    q25: float | None = None
    q75: float | None = None
    n_windows: int = 0
    window_scores: list = field(default_factory=list)
    real_at_least: float = REAL_AT_LEAST
    synth_at_most: float = SYNTH_AT_MOST
    note: str = BAND_NOTE
    model: str = "AASIST-L (pretrained, CPU)"

    def to_dict(self):
        return asdict(self)


def _ensure_stand_in() -> None:
    """The Hugging Face wrapper subclasses a base class from a package we do not need; provide a stand-in."""
    try:
        import speech_spoof_bench.model  # noqa: F401
        return
    except ImportError:
        pass
    pkg, sub = types.ModuleType("speech_spoof_bench"), types.ModuleType("speech_spoof_bench.model")

    class AntiSpoofingModel:
        name, expected_sample_rate, batch_size = "", 16000, 1

        def unload(self):
            pass

    sub.AntiSpoofingModel = AntiSpoofingModel
    pkg.model = sub
    sys.modules["speech_spoof_bench"], sys.modules["speech_spoof_bench.model"] = pkg, sub


def load_aasist_l(model_dir: Path | None = None):
    """Returns a loaded model object with score_batch(), or raises RuntimeError with a readable reason."""
    dirs = [Path(model_dir)] if model_dir else config.MODEL_DIRS
    found = next((d for d in dirs if (d / "aasist_l.py").exists()), None)
    if not found:
        raise RuntimeError("AASIST-L files not found. Run: python phase0/antispoof_probe.py --model aasist-l --download")
    try:
        import importlib
        import torch  # noqa: F401
    except ImportError as e:
        raise RuntimeError(f"PyTorch is not installed ({e}).")
    _ensure_stand_in()
    sys.path.insert(0, str(found))
    try:
        mod = importlib.import_module("aasist_l")
        cls = next(c for _, c in vars(mod).items() if isinstance(c, type) and c.__module__ == "aasist_l" and hasattr(c, "score_batch"))
        model = cls()
        model.load()
        return model
    except Exception as e:
        raise RuntimeError(f"Could not load AASIST-L: {type(e).__name__}: {e}")
    finally:
        if str(found) in sys.path:
            sys.path.remove(str(found))


def label_from_scores(scores: list[float]) -> AuthResult:
    if len(scores) < MIN_WINDOWS:
        return AuthResult("inconclusive", "Inconclusive: too little speech", "inconclusive_short",
                          f"Only {len(scores)} usable window(s); at least {MIN_WINDOWS} (about 12 s of speech) are needed.",
                          n_windows=len(scores), window_scores=[round(s, 2) for s in scores])
    med, q25, q75 = (float(np.percentile(scores, p)) for p in (50, 25, 75))
    if med >= REAL_AT_LEAST:
        label, status, code = "Consistent with natural speech (provisional)", "ok", "natural"
    elif med <= SYNTH_AT_MOST:
        label, status, code = "Synthetic-sounding (provisional)", "ok", "synthetic"
    else:
        label, status, code = "Inconclusive: score is between the two bands", "inconclusive", "inconclusive_band"
    return AuthResult(status, label, code, median=round(med, 2), q25=round(q25, 2), q75=round(q75, 2),
                      n_windows=len(scores), window_scores=[round(s, 2) for s in scores])


class AuthenticityScorer:
    def __init__(self, model=None, model_dir: Path | None = None, cache_dir: Path | None = None):
        self._model, self._model_dir = model, model_dir
        self.cache_dir = Path(cache_dir or config.CACHE_DIR / "auth")
        self._failed: str | None = None

    def _get_model(self):
        if self._model is None and self._failed is None:
            try:
                self._model = load_aasist_l(self._model_dir)
            except RuntimeError as e:
                self._failed = str(e)
        return self._model

    def score(self, path: Path) -> AuthResult:
        sha = sha256_file(path)
        cache_file = self.cache_dir / f"{sha[:32]}.json"
        if cache_file.exists():
            return label_from_scores(json.loads(cache_file.read_text())["scores"])
        x = load_mono_16k(path)
        wins = [x[i:i + WINDOW] for i in range(0, len(x), WINDOW)]
        wins = [w for w in wins if len(w) >= 16000]
        if wins:
            rms = np.array([float(np.sqrt(np.mean(w ** 2))) for w in wins])
            wins = [w for w, r in zip(wins, rms) if r >= max(0.004, 0.2 * rms.max())]
        model = self._get_model()
        if model is None:
            return AuthResult("unavailable", "Not available", "unavailable", self._failed or "model not loaded")
        scores = [float(np.asarray(model.score_batch([w.astype(np.float32)], [16000])).ravel()[0]) for w in wins]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"scores": scores}))
        return label_from_scores(scores)
