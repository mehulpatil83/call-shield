"""Two-person calls: work out who said what, then judge each speaker separately.

Two ways to separate the speakers:
* channels      the recording is stereo with a different person on each channel (many call recorders do this)
* diarization   Gnani batch speech-to-text labels each segment with a speaker and gives start/end times

Everything else (rules, voice check) then runs once per speaker, so the report can say "Speaker 2 asked for the OTP"
instead of mixing both voices together."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .audio_io import _resample, load_mono_16k

MIN_SPAN_SECONDS = 0.2
GAP_SECONDS = 0.05


@dataclass
class SpeakerPart:
    label: str                                   # "Speaker 1", "Speaker 2", ...
    text: str
    spans: list[tuple[float, float]] = field(default_factory=list)    # seconds in the original recording
    wav: Path | None = None                      # audio of this speaker only (channels mode)

    @property
    def seconds(self) -> float:
        return round(sum(e - s for s, e in self.spans), 1)


def parts_from_segments(segments: list[dict]) -> list[SpeakerPart]:
    """Group diarized segments by speaker, ordered by first appearance."""
    order: list = []
    texts: dict = {}
    spans: dict = {}
    for seg in segments:
        who = seg.get("speaker")
        who = "?" if who is None else who
        if who not in texts:
            order.append(who)
            texts[who], spans[who] = [], []
        if seg.get("text"):
            texts[who].append(seg["text"])
        s, e = seg.get("start"), seg.get("end")
        if s is not None and e is not None and e - s >= MIN_SPAN_SECONDS:
            spans[who].append((float(s), float(e)))
    return [SpeakerPart(f"Speaker {i + 1}", " ".join(texts[w]).strip(), spans[w]) for i, w in enumerate(order)]


def speaker_audio(path: Path, spans: list[tuple[float, float]]) -> np.ndarray:
    """Concatenate the parts of the recording where this speaker talks (16 kHz mono)."""
    x = load_mono_16k(path)
    gap = np.zeros(int(GAP_SECONDS * 16000), dtype=np.float32)
    pieces = []
    for s, e in sorted(spans):
        pieces += [x[int(s * 16000):int(e * 16000)], gap]
    return np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)


def write_wav(path: Path, x: np.ndarray, sr: int = 16000) -> Path:
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(x, -1, 1), sr, subtype="PCM_16")
    return path


def read_channels(path: Path) -> list[np.ndarray] | None:
    """Per-channel 16 kHz audio, or None for a mono file or a format soundfile cannot read."""
    import soundfile as sf

    try:
        x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception:
        return None
    if x.shape[1] < 2:
        return None
    return [_resample(x[:, i], int(sr), 16000) for i in range(min(x.shape[1], 2))]


def channels_look_separate(chans: list[np.ndarray]) -> bool:
    """A stereo file where both channels are (almost) the same sound is just a mono recording stored twice."""
    if not chans or len(chans) < 2:
        return False
    a, b = chans[0], chans[1]
    n = min(len(a), len(b))
    if n == 0:
        return False
    a, b = a[:n], b[:n]
    if float(np.std(a)) < 1e-6 or float(np.std(b)) < 1e-6:
        return float(np.std(a)) + float(np.std(b)) > 1e-6        # one silent channel: the other holds the voice(s)
    corr = float(np.corrcoef(a, b)[0, 1])
    return abs(corr) < 0.6


def clean_label(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()
