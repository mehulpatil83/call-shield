"""A full, timestamped record of one live call: what was heard, every tactic, every risk change, every alert and every
connection event. It is saved with the report and drives the interactive report page.

Times: `t` is how many seconds of audio the server had received when the thing happened (call time). `wall` is the laptop's
clock at that moment. Both are ARRIVAL times: the speech-to-text service may deliver words a second or two after they were
spoken, so a tactic's time is when the app learned of it, not the exact moment it was said."""
from __future__ import annotations

import re
from datetime import datetime

VERSION = 1
RISK_MIN_GAP = 1.5        # seconds between two risk samples when nothing changed


def mask_digits(text: str) -> str:
    """Spoken numbers (OTPs, card and phone numbers) are not kept: every digit becomes a bullet. Character positions stay the same."""
    return re.sub(r"\d", "•", str(text))


def wall_now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


class SessionLog:
    def __init__(self, language: str):
        self.language = language
        self.started_at = wall_now()
        self.events: list[dict] = []
        self.segments: dict[tuple, dict] = {}
        self.risk: list[dict] = []

    def event(self, kind: str, t: float, source: str = "system", **data) -> dict:
        ev = {"i": len(self.events), "t": round(float(t), 2), "wall": wall_now(), "source": source, "kind": kind, **data}
        self.events.append(ev)
        return ev

    def segment(self, track: str, key, text: str, t: float) -> None:
        k = (track, str(key))
        seg = self.segments.get(k)
        if seg is None:
            self.segments[k] = {"track": track, "first_t": round(float(t), 2), "first_wall": wall_now(), "last_t": round(float(t), 2),
                                "text": text}
        else:
            seg["last_t"], seg["text"] = round(float(t), 2), text

    def risk_point(self, t: float, level: str, score: float, model_prob: float | None) -> None:
        last = self.risk[-1] if self.risk else None
        if last and last["level"] == level and abs(last["score"] - score) < 1e-9 and t - last["t"] < RISK_MIN_GAP:
            return
        self.risk.append({"t": round(float(t), 2), "level": level, "score": round(float(score), 2),
                          "model": None if model_prob is None else round(float(model_prob), 3)})

    def to_dict(self, duration: float, max_level: str, level: str) -> dict:
        segs = sorted(self.segments.values(), key=lambda s: (s["first_t"], s["track"]))
        return {
            "version": VERSION, "started_at": self.started_at, "language": self.language, "duration": round(float(duration), 2),
            "max_level": max_level, "level": level, "digits_masked": True,
            "timestamps_note": "Times are when the app received the words (arrival time), which can lag the speech by a second or two.",
            "segments": [{**s, "text": mask_digits(s["text"])} for s in segs],
            "events": [self._masked(e) for e in self.events],
            "risk": list(self.risk),
        }

    @staticmethod
    def _masked(e: dict) -> dict:
        return {k: (mask_digits(v) if k in ("quote", "message") and isinstance(v, str) else v) for k, v in e.items()}
