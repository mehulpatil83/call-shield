"""Live call analysis: PCM audio in -> Gnani streaming speech-to-text -> rules re-run on every new segment.

One Gnani stream is opened per language code (Hinglish and "not sure" use several, exactly like file analysis) and every
stream receives the same audio frames. The audio is also kept so the voice check and a stored report can be made when the
call ends. Streaming accepts only single language codes, 16 kHz or 8 kHz, in exact 1024-byte frames."""
from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from . import config
from .model import ELEVATED_AT, HIGH_AT, MODEL_LANGUAGES, ScamModel, combine
from .rules import analyse_text, merge_results
from .session_log import SessionLog

FRAME_BYTES = 1024            # 512 samples of 16-bit PCM = 32 ms at 16 kHz
SAMPLE_RATE = 16000
LEVEL_RANK = {"low": 0, "elevated": 1, "high": 2}
LIVE_MAX_SECONDS = 600


@dataclass
class Track:
    code: str
    client: object
    segments: dict = field(default_factory=dict)      # key -> text (a later event with the same key replaces it)
    order: list = field(default_factory=list)
    task: asyncio.Task | None = None

    @property
    def text(self) -> str:
        return " ".join(self.segments[k] for k in self.order if self.segments[k]).strip()


@dataclass
class LiveResult:
    texts: dict[str, str]
    pcm: bytes
    seconds: float
    level: str
    max_level: str
    log: dict | None = None                # the full timestamped record of the call (core/session_log.py)


class LiveSession:
    def __init__(self, language: str, stream_factory: Callable[[str], object],
                 send: Callable[[dict], Awaitable[None]], model: ScamModel | None = None):
        self.codes = config.LANG_CODES[language]
        self.model = model if language in MODEL_LANGUAGES else None     # second opinion: English / Hinglish only
        self.language = language
        self.model_peak = 0.0                 # highest model probability heard in this call (the rules are cumulative too)
        self.model_now: float | None = None
        self.model_raised = False
        self._scored_words = 0
        self._scoring = False
        self.factory, self.send = stream_factory, send
        self.tracks: list[Track] = []
        self.buffer = bytearray()
        self.pcm = bytearray()
        self.max_rank = 0
        self.level = "low"
        self.closed = False
        self.log = SessionLog(language)
        self._seen_hits: set = set()
        self._model_marks: set = set()
        self._first_words = False

    def note(self, kind: str, source: str = "system", **data) -> None:
        """Record a call event (phone joined, dropped, listen switched ...) at the current call time."""
        self.log.event(kind, self.seconds, source, **data)

    # ------------------------------------------------------------------ lifecycle -----------
    async def start(self) -> None:
        for code in self.codes:
            client = self.factory(code)
            await client.connect()
            t = Track(code, client)
            t.task = asyncio.create_task(self._consume(t))
            self.tracks.append(t)
        self.log.event("call_started", 0.0, codes=self.codes)
        await self.send({"type": "ready", "codes": self.codes})

    async def feed(self, data: bytes) -> bool:
        """Accept PCM16 mono 16 kHz of any size. Returns False when the time limit is reached."""
        if self.closed:
            return False
        self.pcm += data
        self.buffer += data
        while len(self.buffer) >= FRAME_BYTES:
            frame = bytes(self.buffer[:FRAME_BYTES])
            del self.buffer[:FRAME_BYTES]
            for t in self.tracks:
                await t.client.send_audio(frame)
        return self.seconds < LIVE_MAX_SECONDS

    async def keepalive(self) -> None:
        """One frame of silence for the speech-to-text streams, NOT added to the stored audio. Used while the phone
        reconnects, so the streams stay open and are not closed for being idle."""
        if self.closed:
            return
        for t in self.tracks:
            with contextlib.suppress(Exception):
                await t.client.send_audio(bytes(FRAME_BYTES))

    @property
    def seconds(self) -> float:
        return len(self.pcm) / 2 / SAMPLE_RATE

    async def stop(self, settle_seconds: float = 3.0) -> LiveResult:
        if self.closed:
            return self._result()
        self.closed = True
        # flush the partial frame and add silence so the server's voice-activity detector closes the last segment
        tail = bytes(self.buffer) + bytes(int(1.5 * SAMPLE_RATE) * 2)
        self.buffer.clear()
        tail += bytes((-len(tail)) % FRAME_BYTES)
        for i in range(0, len(tail), FRAME_BYTES):
            for t in self.tracks:
                with contextlib.suppress(Exception):
                    await t.client.send_audio(tail[i:i + FRAME_BYTES])
        await asyncio.sleep(0)
        for t in self.tracks:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(t.client.close(), timeout=settle_seconds)
        for t in self.tracks:
            if t.task:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(t.task, timeout=settle_seconds)
        await self._analyse(final=True)
        return self._result()

    def _result(self) -> LiveResult:
        rank_name = {v: k for k, v in LEVEL_RANK.items()}
        return LiveResult({t.code: t.text for t in self.tracks}, bytes(self.pcm), self.seconds, self.level,
                          rank_name[self.max_rank], self.log.to_dict(self.seconds, rank_name[self.max_rank], self.level))

    # ------------------------------------------------------------------ events -------------
    async def _consume(self, track: Track) -> None:
        try:
            async for ev in track.client.events():
                name = type(ev).__name__
                if name == "StreamTranscriptEvent" and getattr(ev, "text", ""):
                    key = getattr(ev, "segment_id", None) or getattr(ev, "segment_index", None) or len(track.order)
                    if key not in track.segments:
                        track.order.append(key)
                    track.segments[key] = ev.text
                    self.log.segment(track.code, key, ev.text, self.seconds)
                    if not self._first_words:
                        self._first_words = True
                        self.log.event("first_words", self.seconds, "system", track=track.code)
                    await self._analyse()
                elif name == "StreamErrorEvent":
                    msg = str(getattr(ev, "message", ""))[:200]
                    self.log.event("warning", self.seconds, "system", track=track.code, message=msg)
                    await self.send({"type": "warning", "code": track.code, "message": msg})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self.send({"type": "warning", "code": track.code, "message": f"{type(e).__name__}: {e}"[:200]})

    def _model_text(self, live: list) -> str:
        """The model reads ONE transcript: the Roman-script English track when there is one, else the longest."""
        for t in live:
            if t.code == "en-IN":
                return t.text
        return max((t.text for t in live), key=len, default="")

    async def _model_step(self, text: str, final: bool) -> None:
        m = self.model
        if m is None or m.status != "ready":
            return
        words = len(text.split())
        if words - self._scored_words < (1 if final else 3) or self._scoring:
            return
        self._scoring = True
        try:
            p = await asyncio.to_thread(m.score, text)
            if p is not None:
                self.model_now, self._scored_words = p, words
                self.model_peak = max(self.model_peak, p)
        except Exception:
            self.model_now = None                       # a failing model must never break the call: rules carry on
        finally:
            self._scoring = False

    def _model_status(self) -> str:
        if self.model is None or self.model.status == "idle":
            return "off"
        return self.model.status

    def _record(self, merged, level: str, raised: bool, rule_score: float) -> None:
        t = self.seconds
        for h in merged.hits:
            key = (h.category, h.quote.casefold(), h.source)
            if key in self._seen_hits:
                continue
            self._seen_hits.add(key)
            self.log.event("tactic", t, "rules", category=h.category, kind_of=h.kind, quote=h.quote, track=h.source,
                           explanation=h.explanation)
        for mark, name in ((ELEVATED_AT, "elevated"), (HIGH_AT, "high")):
            if self.model_peak >= mark and mark not in self._model_marks:
                self._model_marks.add(mark)
                self.log.event("model", t, "model", prob=round(self.model_peak, 3), threshold=mark, would_raise=name)
        if level != self.level:
            self.log.event("level", t, "model" if raised else "rules", frm=self.level, to=level,
                           score=round(max(rule_score, {"elevated": 3.0, "high": 6.0}.get(level, 0.0)) if raised else rule_score, 2))
        self.log.risk_point(t, level, max(rule_score, {"elevated": 3.0, "high": 6.0}.get(level, 0.0)) if raised else rule_score,
                            self.model_now)

    async def _analyse(self, final: bool = False) -> None:
        live = [t for t in self.tracks if t.text]
        if not live:
            return
        results = [analyse_text(t.text, source=t.code) for t in live]
        merged = merge_results(results, [t.text for t in live])
        mtext = self._model_text(live)
        await self._model_step(mtext, final)
        level, raised = combine(merged.level, self.model_peak if self.model_now is not None else None, len(mtext.split()))
        self.model_raised = raised
        summary = merged.summary
        if raised:
            summary += (" The language model also rates this call as very likely a scam"
                        f" ({round(self.model_peak * 100)}%), though no single phrase stands out.")
        self._record(merged, level, raised, merged.score)
        self.level = level
        await self.send({
            "type": "analysis", "final": final, "level": level, "score": max(merged.score, {"elevated": 3.0, "high": 6.0}[level]) if raised else merged.score,
            "summary": summary, "seconds": round(self.seconds, 1),
            "tracks": [{"code": t.code, "text": t.text, "hits": [h.__dict__ for h in r.hits]} for t, r in zip(live, results)],
            "hits": [h.__dict__ for h in merged.hits],
            "model": {"status": self._model_status(), "prob": None if self.model_now is None else round(self.model_now, 3),
                      "peak": round(self.model_peak, 3), "raised": raised},
        })
        rank = LEVEL_RANK[level]
        if rank > self.max_rank:
            self.max_rank = rank
            if rank >= 1:
                self.log.event("alert", self.seconds, "alert", level=level)
                await self.send({"type": "alert", "level": level})
