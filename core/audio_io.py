from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from math import gcd
from pathlib import Path

import numpy as np


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x.astype(np.float32)
    from scipy.signal import resample_poly

    g = gcd(sr_in, sr_out)
    return resample_poly(x, sr_out // g, sr_in // g).astype(np.float32)


def load_mono_16k(path: Path) -> np.ndarray:
    """Mono float32 at 16 kHz. Uses soundfile; falls back to ffmpeg for formats like .m4a."""
    import soundfile as sf

    try:
        x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception:
        if not shutil.which("ffmpeg"):
            raise RuntimeError(f"Cannot read {path.name}. Convert it to WAV or install ffmpeg.")
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000", tmp],
                           check=True)
            x, sr = sf.read(tmp, dtype="float32", always_2d=True)
        finally:
            os.remove(tmp)
    return _resample(x.mean(axis=1), int(sr), 16000)


def duration_seconds(path: Path) -> float:
    return len(load_mono_16k(path)) / 16000.0
