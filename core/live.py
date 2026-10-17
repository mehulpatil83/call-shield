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
from .rules import analyse_text, merge_results

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


class LiveSession:
    def __init__(self, language: str, stream_factory: Callable[[str], object],
                 send: Callable[[dict], Awaitable[None]]):
        self.codes = config.LANG_CODES[language]
        self.factory, self.send = stream_factory, send
        self.tracks: list[Track] = []
        self.buffer = bytearray()
        self.pcm = bytearray()
        self.max_rank = 0
        self.level = "low"
        self.closed = False

    # ------------------------------------------------------------------ lifecycle -----------
    async def start(self) -> None:
        for code in self.codes:
            client = self.factory(code)
            await client.connect()
            t = Track(code, client)
            t.task = asyncio.create_task(self._consume(t))
            self.tracks.append(t)
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
                          rank_name[self.max_rank])

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
                    await self._analyse()
                elif name == "StreamErrorEvent":
                    await self.send({"type": "warning", "code": track.code, "message": str(getattr(ev, "message", ""))[:200]})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self.send({"type": "warning", "code": track.code, "message": f"{type(e).__name__}: {e}"[:200]})

    async def _analyse(self, final: bool = False) -> None:
        live = [t for t in self.tracks if t.text]
        if not live:
            return
        results = [analyse_text(t.text, source=t.code) for t in live]
        merged = merge_results(results, [t.text for t in live])
        self.level = merged.level
        await self.send({
            "type": "analysis", "final": final, "level": merged.level, "score": merged.score, "summary": merged.summary,
            "seconds": round(self.seconds, 1),
            "tracks": [{"code": t.code, "text": t.text, "hits": [h.__dict__ for h in r.hits]} for t, r in zip(live, results)],
            "hits": [h.__dict__ for h in merged.hits],
        })
        rank = LEVEL_RANK[merged.level]
        if rank > self.max_rank:
            self.max_rank = rank
            if rank >= 1:
                await self.send({"type": "alert", "level": merged.level})
