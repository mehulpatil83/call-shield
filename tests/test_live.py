import asyncio

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.backend.main import create_app
from core.authenticity import AuthenticityScorer
from core.gnani_client import GnaniTranscriber
from tests.test_pipeline import FakeModel, FakeRest


class StreamTranscriptEvent:
    def __init__(self, text, idx):
        self.text, self.segment_index, self.segment_id, self.latency = text, idx, f"s{idx}", 250


class StreamErrorEvent:
    def __init__(self, message):
        self.message = message


class FakeStream:
    """Stands in for GnaniSTTStreamClient: emits scripted transcript events after a number of 1024-byte frames."""
    instances = []

    def __init__(self, script, errors=False):
        self.script, self.frames, self.queue, self.sent_sizes, self.errors = script, 0, asyncio.Queue(), set(), errors
        FakeStream.instances.append(self)

    async def connect(self):
        return None

    async def send_audio(self, frame):
        self.sent_sizes.add(len(frame))
        self.frames += 1
        for at, text in self.script:
            if self.frames == at:
                await self.queue.put(StreamTranscriptEvent(text, at))
        if self.errors and self.frames == 3:
            await self.queue.put(StreamErrorEvent("hiccup"))

    async def events(self):
        while True:
            ev = await self.queue.get()
            if ev is None:
                return
            yield ev

    async def close(self):
        await self.queue.put(None)
        return []


SCRIPT = [(10, "hello sir i am calling from your bank security department"),
          (20, "your account will be blocked today unless you verify right now"),
          (30, "please share the six digit otp")]


def pcm(seconds, amp=0.2):
    t = np.arange(int(16000 * seconds)) / 16000
    return (amp * 32767 * np.sin(2 * np.pi * 220 * t)).astype("<i2").tobytes()


def client(tmp_path, factory):
    app = create_app(
        data_dir=tmp_path / "data",
        transcriber_factory=lambda c: GnaniTranscriber(api_key="k", cache_dir=c, rest_client=FakeRest({})),
        scorer_factory=lambda c: AuthenticityScorer(model=FakeModel(-3.0), cache_dir=c),
        serve_frontend=False, stream_factory=factory)
    return TestClient(app)


def collect(ws, until="ended", limit=60):
    out = []
    for _ in range(limit):
        m = ws.receive_json()
        out.append(m)
        if m["type"] in (until, "error"):
            break
    return out


def run_call(c, seconds=2.0, query="language=en&consent=true", chunk=3000):
    with c.websocket_connect(f"/api/live?{query}") as ws:
        assert ws.receive_json()["type"] == "ready"
        data = pcm(seconds)
        for i in range(0, len(data), chunk):                  # odd chunk size on purpose: server must re-frame
            ws.send_bytes(data[i:i + chunk])
        ws.send_text('{"type":"stop"}')
        return collect(ws)


def test_live_call_raises_alert_and_is_stored(tmp_path):
    FakeStream.instances.clear()
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    msgs = run_call(c)
    types = [m["type"] for m in msgs]
    assert types.count("alert") == 2                          # elevated first, then high
    assert [m["level"] for m in msgs if m["type"] == "alert"] == ["elevated", "high"]
    analyses = [m for m in msgs if m["type"] == "analysis"]
    assert analyses[0]["level"] == "low" and analyses[-1]["level"] == "high"
    assert "otp" in analyses[-1]["tracks"][0]["text"]
    ended = msgs[-1]
    assert ended["type"] == "ended" and ended["id"] and ended["max_level"] == "high"
    # every frame sent to Gnani was exactly 1024 bytes
    assert FakeStream.instances[0].sent_sizes == {1024}
    # stored like any other analysis
    rec = c.get(f"/api/analyses/{ended['id']}").json()
    assert rec["status"] == "done" and rec["level"] == "high" and rec["report"]["meta"]["live"] is True
    assert rec["report"]["authenticity"]["status"] in ("ok", "inconclusive")
    assert c.delete(f"/api/analyses/{ended['id']}").status_code == 200


def test_hinglish_opens_two_streams(tmp_path):
    FakeStream.instances.clear()
    scripts = {"en-IN": SCRIPT, "hi-IN": [(15, "ओटीपी मला आत्ताच सांगा")]}
    c = client(tmp_path, lambda code: FakeStream(scripts[code]))
    msgs = run_call(c, query="language=hinglish&consent=true")
    assert len(FakeStream.instances) == 2
    last = [m for m in msgs if m["type"] == "analysis"][-1]
    assert {t["code"] for t in last["tracks"]} == {"en-IN", "hi-IN"}


def test_consent_required(tmp_path):
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    with c.websocket_connect("/api/live?language=en&consent=false") as ws:
        m = ws.receive_json()
        assert m["type"] == "error" and "Consent" in m["message"]


def test_unknown_language_rejected(tmp_path):
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    with c.websocket_connect("/api/live?language=fr&consent=true") as ws:
        assert ws.receive_json()["type"] == "error"


def test_second_live_call_is_refused_while_busy(tmp_path):
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    with c.websocket_connect("/api/live?language=en&consent=true") as first:
        assert first.receive_json()["type"] == "ready"
        with c.websocket_connect("/api/live?language=en&consent=true") as second:
            assert "Another live check" in second.receive_json()["message"]
        first.send_text('{"type":"stop"}')
        collect(first)


def test_too_short_call_is_not_stored(tmp_path):
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    msgs = run_call(c, seconds=0.3)
    assert msgs[-1]["type"] == "ended" and msgs[-1]["id"] is None
    assert c.get("/api/analyses").json() == []


def test_time_limit_stops_the_call(tmp_path, monkeypatch):
    import core.live
    monkeypatch.setattr(core.live, "LIVE_MAX_SECONDS", 1.0)
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    with c.websocket_connect("/api/live?language=en&consent=true") as ws:
        ws.receive_json()
        data = pcm(3.0)
        for i in range(0, len(data), 4000):
            try:
                ws.send_bytes(data[i:i + 4000])
            except Exception:
                break
        msgs = collect(ws)
    assert any(m["type"] == "limit" for m in msgs)


def test_stream_errors_become_warnings_not_crashes(tmp_path):
    c = client(tmp_path, lambda code: FakeStream(SCRIPT, errors=True))
    msgs = run_call(c)
    assert any(m["type"] == "warning" and m["message"] == "hiccup" for m in msgs)
    assert msgs[-1]["type"] == "ended"


def test_websocket_from_another_site_is_refused(tmp_path):
    from starlette.websockets import WebSocketDisconnect
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    with pytest.raises(WebSocketDisconnect) as e:
        with c.websocket_connect("/api/live?language=en&consent=true", headers={"Origin": "https://evil.example"}):
            pass
    assert e.value.code == 4403
