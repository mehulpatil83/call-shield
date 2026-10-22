"""Second opinion from a fine-tuned language model (distilbert-base-multilingual-cased, trained on ICFD-31k windows).

The rules (core/rules.py) stay the main verdict and the only source of quoted evidence. The model can only RAISE the level,
never lower it, and only when it is confident:
    probability >= 0.85 (and >= 8 words heard)                  -> at least "elevated"
    probability >= 0.95 (and >= 15 words heard)                 -> "high"
It runs on the laptop CPU; nothing leaves the machine. If the folder or the `transformers` package is missing the model
reports "unavailable" and everything works with rules only. English and Hinglish only: for Hindi and Marathi calls it is off.
Input: the last 200 words, at most 192 tokens (exactly as in training). Weights live in models/model_v2_fp16 (git-ignored)."""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from . import config

log = logging.getLogger("callshield.model")

MODEL_DIR = config.ROOT / "models" / "model_v2_fp16"
ELEVATED_AT, HIGH_AT = 0.85, 0.95
MIN_WORDS_ELEVATED, MIN_WORDS_HIGH = 8, 15
WINDOW_WORDS, MAX_TOKENS = 200, 192
RANK = {"low": 0, "elevated": 1, "high": 2}
NAMES = {0: "low", 1: "elevated", 2: "high"}
MODEL_LANGUAGES = {"en", "hinglish", "auto"}      # Hindi and Marathi are not in the training data


def combine(rule_level: str, prob: float | None, words: int) -> tuple[str, bool]:
    """Return (new level, raised). The model never lowers the rules' level."""
    target = 0
    if prob is not None:
        if prob >= ELEVATED_AT and words >= MIN_WORDS_ELEVATED:
            target = 1
        if prob >= HIGH_AT and words >= MIN_WORDS_HIGH:
            target = 2
    new = max(RANK[rule_level], target)
    return NAMES[new], new > RANK[rule_level]


class ScamModel:
    """status: idle (nobody asked it to load) | loading | ready | unavailable."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else MODEL_DIR
        self.status = "idle"
        self.error = ""
        self._tok = self._model = self._torch = None
        self._lock = threading.Lock()
        self._started = False

    # ------------------------------------------------------------------ loading ------------
    def start_loading(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self.status = "loading"
        threading.Thread(target=self.load, name="scam-model-load", daemon=True).start()

    def load(self) -> None:
        t0 = time.time()
        try:
            if not (self.path / "config.json").exists():
                raise FileNotFoundError(f"model folder not found: {self.path}")
            os.environ.setdefault("USE_TF", "0")             # we only use PyTorch: do not let transformers import TensorFlow (slow)
            os.environ.setdefault("USE_FLAX", "0")
            os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
            os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            tok = AutoTokenizer.from_pretrained(str(self.path))
            tok.truncation_side = "left"                      # keep the END of the call, as in training
            model = AutoModelForSequenceClassification.from_pretrained(str(self.path)).float().eval()
            try:
                torch.set_num_threads(2)
            except Exception:
                pass
            self._tok, self._model, self._torch = tok, model, torch
            self.status = "ready"
            log.info("scam model ready in %.1fs", time.time() - t0)
        except Exception as e:                                  # missing folder, missing package, damaged file: rules only
            self.status, self.error = "unavailable", f"{type(e).__name__}: {e}"[:300]
            log.warning("scam model unavailable: %s", self.error)

    # ------------------------------------------------------------------ scoring ------------
    def score(self, text: str) -> float | None:
        """Probability that the text is a scam call (0..1), or None when the model is not ready."""
        if self.status != "ready":
            return None
        words = text.split()
        if not words:
            return 0.0
        enc = self._tok(" ".join(words[-WINDOW_WORDS:]), return_tensors="pt", truncation=True, max_length=MAX_TOKENS)
        enc = {k: enc[k] for k in ("input_ids", "attention_mask")}      # DistilBERT takes no token_type_ids
        with self._torch.inference_mode():
            logits = self._model(**enc).logits[0]
        return float(self._torch.softmax(logits, -1)[1])


_MODEL = ScamModel()


def get_model() -> ScamModel:
    return _MODEL


def start_loading() -> None:
    """Called once by the server at start so the first call does not wait for the weights."""
    _MODEL.start_loading()
