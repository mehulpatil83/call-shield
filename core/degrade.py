"""Deterministic phone-line simulation used by the evaluation. It is an approximation, NOT a real network codec:
300-3400 Hz band-pass, 8 kHz sampling, 8-bit mu-law companding, optional noise at a chosen SNR."""
from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np

from .audio_io import load_mono_16k


def _resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    from scipy.signal import resample_poly

    g = gcd(sr_in, sr_out)
    return resample_poly(x, sr_out // g, sr_in // g).astype(np.float32)


def telephony(x16: np.ndarray, snr_db: float | None = None, seed: int = 0) -> np.ndarray:
    """16 kHz float audio in, 8 kHz float audio out."""
    from scipy.signal import butter, sosfiltfilt

    peak = float(np.max(np.abs(x16))) or 1.0
    x = x16 / peak * 0.9
    y = sosfiltfilt(butter(4, [300, 3400], btype="band", fs=16000, output="sos"), x)
    y8 = np.clip(_resample(y.astype(np.float32), 16000, 8000), -1.0, 1.0)
    mu = 255.0
    comp = np.sign(y8) * np.log1p(mu * np.abs(y8)) / np.log1p(mu)
    q = np.round((comp + 1.0) / 2.0 * 255.0) / 255.0 * 2.0 - 1.0
    out = np.sign(q) * np.expm1(np.log1p(mu) * np.abs(q)) / mu
    if snr_db is not None:
        active = out[np.abs(out) > 0.02]
        rms = float(np.sqrt(np.mean(active ** 2))) if active.size else 0.05
        out = out + np.random.default_rng(seed).normal(0.0, rms / (10 ** (snr_db / 20.0)), size=out.shape)
    return out.astype(np.float32)


CONDITIONS = {"orig": None, "tel8k": None, "tel8k_noisy": 15.0}


def make_condition(src: Path, condition: str, dest: Path) -> Path:
    """Write the recording under the given condition and return its path ('orig' returns the source itself)."""
    if condition == "orig":
        return src
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition}; use one of {list(CONDITIONS)}")
    import soundfile as sf

    dest.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest), np.clip(telephony(load_mono_16k(src), CONDITIONS[condition], seed=1), -1, 1), 8000, subtype="PCM_16")
    return dest
