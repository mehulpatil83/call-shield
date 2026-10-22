"""Call mode (Part 1): a phone Speaker reaches the laptop Receiver through a tunnel address."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.backend import calls as calls_mod
from app.backend.calls import parse_public_url
from app.backend.main import create_app
from core.authenticity import AuthenticityScorer
from core.gnani_client import GnaniTranscriber
from tests.test_live import SCRIPT, FakeStream, pcm
from tests.test_pipeline import FakeModel, FakeRest

PUB = "demo-abc.trycloudflare.com"
PUB_URL = f"https://{PUB}"
PUBLIC = {"host": PUB, "origin": PUB_URL}          # what the phone's browser sends through the tunnel


def make_app(tmp_path, factory=None, probe=lambda: None, public_url=PUB_URL):
    FakeStream.instances.clear()
    return create_app(
        data_dir=tmp_path / "data",
        transcriber_factory=lambda c: GnaniTranscriber(api_key="k", cache_dir=c, rest_client=FakeRest({})),
        scorer_factory=lambda c: AuthenticityScorer(model=FakeModel(-3.0), cache_dir=c),
        serve_frontend=False, stream_factory=factory or (lambda code: FakeStream(SCRIPT)),
        public_url=public_url, tunnel_probe=probe)


def new_call(c, language="en", **extra):
    r = c.post("/api/calls", json={"language": language, "consent": True, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def drain(ws, until="ended", limit=80):
    out = []
    for _ in range(limit):
        m = ws.receive_json()
        out.append(m)
        if m["type"] in (until, "error"):
            break
    return out


def speak(c, code, headers=PUBLIC):
    return c.websocket_connect(f"/api/call/speak?code={code}", headers=headers)


def receive(c, code):
    return c.websocket_connect(f"/api/call/receive?code={code}")


# ------------------------------------------------------------------------------------------ the happy path -----
def test_speaker_talks_receiver_sees_analysis_and_speaker_sees_none(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        assert len(info["code"]) == 6 and info["join_url"] == f"{PUB_URL}/#/join/{info['code']}"
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            assert rx.receive_json() == {"type": "call", "state": "waiting"}
            assert tx.receive_json() == {"type": "joined", "language": "en"}
            assert rx.receive_json() == {"type": "call", "state": "joined"}
            tx.send_json({"type": "hello", "consent": True})
            ready = tx.receive_json()
            assert ready["type"] == "ready" and len(ready["resume"]) >= 16       # the phone alone gets a rejoin token
            data = pcm(2.0)
            for i in range(0, len(data), 3000):
                tx.send_bytes(data[i:i + 3000])
            tx.send_text('{"type":"stop"}')
            to_speaker = drain(tx)
            to_receiver = drain(rx)
    # the phone learns nothing about the analysis
    assert {m["type"] for m in to_speaker} <= {"ended"}
    types = [m["type"] for m in to_receiver]
    assert types[0] == "ready" and "analysis" in types and types.count("alert") == 2
    assert not any("resume" in m for m in to_receiver)                           # the Receiver never sees the rejoin token
    assert "audio" in types and all(0 <= m["rms"] <= 1 for m in to_receiver if m["type"] == "audio")
    last = [m for m in to_receiver if m["type"] == "analysis"][-1]
    assert last["level"] == "high" and "otp" in last["tracks"][0]["text"]
    ended = to_receiver[-1]
    assert ended["type"] == "ended" and ended["id"] and ended["max_level"] == "high"
    assert FakeStream.instances[0].sent_sizes == {1024}


def test_report_is_stored_for_the_receiver_and_can_be_deleted(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            rx.receive_json(); tx.receive_json(); rx.receive_json()
            tx.send_json({"type": "hello", "consent": True})
            tx.receive_json()
            tx.send_bytes(pcm(2.0))
            tx.send_text('{"type":"stop"}')
            sid = [m for m in drain(rx) if m["type"] == "ended"][0]["id"]
        rec = c.get(f"/api/analyses/{sid}").json()
        assert rec["status"] == "done" and rec["report"]["meta"]["live"] is True
        assert c.delete(f"/api/analyses/{sid}").status_code == 200


def test_receiver_can_end_the_call_and_still_gets_the_report(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            rx.receive_json(); tx.receive_json(); rx.receive_json()
            tx.send_json({"type": "hello", "consent": True})
            tx.receive_json()
            tx.send_bytes(pcm(2.0))
            rx.send_json({"type": "end"})
            assert drain(tx)[-1] == {"type": "ended"}
            assert [m for m in drain(rx) if m["type"] == "ended"][0]["id"]


def test_listen_is_off_by_default_and_forwards_audio_only_when_switched_on(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            rx.receive_json(); tx.receive_json(); rx.receive_json()
            tx.send_json({"type": "hello", "consent": True})
            tx.receive_json()
            assert rx.receive_json()["type"] == "ready"
            tx.send_bytes(pcm(0.2))                                   # listen is off: nothing forwarded
            while rx.receive_json()["type"] != "audio":               # the server reports the first chunk's loudness right after it
                pass                                                  # has decided not to forward it: only now switch listen on
            rx.send_json({"type": "listen", "on": True})
            tx.send_bytes(pcm(0.2))
            tx.send_bytes(pcm(0.2))
            tx.send_text('{"type":"stop"}')
            got = []
            while True:
                msg = rx.receive()
                if msg.get("bytes") is not None:
                    got.append(len(msg["bytes"]))
                elif msg.get("text") and '"ended"' in msg["text"]:
                    break
    assert got and all(n == len(pcm(0.2)) for n in got) and len(got) <= 2


# ------------------------------------------------------------------------------------------ roles and consent --
def test_creating_a_call_needs_consent_and_a_known_language(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        assert c.post("/api/calls", json={"language": "en", "consent": False}).status_code == 400
        assert c.post("/api/calls", json={"language": "fr", "consent": True}).status_code == 400


def test_speaker_cannot_start_without_consent_and_no_stream_is_opened(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            rx.receive_json(); tx.receive_json(); rx.receive_json()
            tx.send_json({"type": "hello", "consent": False})
            msgs = drain(tx)
            assert msgs[0]["type"] == "error" and "Consent" in msgs[0]["message"]
        assert FakeStream.instances == []


def test_audio_before_consent_is_refused(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            rx.receive_json(); tx.receive_json(); rx.receive_json()
            tx.send_bytes(pcm(0.5))
            assert drain(tx)[0]["type"] == "error"
        assert FakeStream.instances == []


def test_after_a_refused_speaker_the_same_code_can_be_used_again(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx:
            rx.receive_json()
            with speak(c, info["code"]) as tx:
                tx.receive_json(); rx.receive_json()
                tx.send_json({"type": "hello", "consent": False})
                drain(tx)
            assert rx.receive_json() == {"type": "call", "state": "waiting"}
            with speak(c, info["code"]) as tx2:
                assert tx2.receive_json()["type"] == "joined"


def test_a_second_speaker_is_refused(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as one:
            rx.receive_json(); one.receive_json()
            with speak(c, info["code"]) as two:
                assert "already has a speaker" in two.receive_json()["message"]


def test_a_second_receiver_is_refused(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx:
            rx.receive_json()
            with receive(c, info["code"]) as rx2:
                assert "already has a receiver" in rx2.receive_json()["message"]


def test_speaker_needs_a_ready_receiver(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with speak(c, info["code"]) as tx:
            assert "receiver is not ready" in tx.receive_json()["message"]


def test_wrong_codes_are_refused_and_rate_limited(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        wrong = "000000" if info["code"] != "000000" else "111111"
        for _ in range(calls_mod.MAX_FAILS):
            with speak(c, wrong) as tx:
                assert "not valid" in tx.receive_json()["message"]
        with speak(c, info["code"]) as tx:                           # even the right code waits out the limit
            assert "Too many" in tx.receive_json()["message"]


def test_a_new_call_replaces_an_unused_one(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        first = new_call(c)
        second = new_call(c)
        with receive(c, first["code"]) as rx:
            assert rx.receive_json()["type"] == "error"
        with receive(c, second["code"]) as rx:
            assert rx.receive_json()["state"] == "waiting"


def test_the_live_check_is_refused_while_a_call_is_running(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            rx.receive_json(); tx.receive_json(); rx.receive_json()
            tx.send_json({"type": "hello", "consent": True})
            tx.receive_json()
            with c.websocket_connect("/api/live?language=en&consent=true") as other:
                assert "Another live check" in other.receive_json()["message"]
            assert c.post("/api/calls", json={"language": "en", "consent": True}).status_code == 409
            tx.send_text('{"type":"stop"}')
            drain(tx)


# ------------------------------------------------------------------------------------------ the public surface -
def test_public_address_serves_only_the_phone_page_and_the_speaker_socket(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        for path in ("/api/health", "/api/analyses", "/api/analyses/abcdef012345/report.html", "/api/docs",
                     "/api/openapi.json", "/openapi.json", "/docs", "/api/calls/config", "/api//health", "/API/analyses"):
            assert c.get(path, headers=PUBLIC).status_code in (403, 404), path
            if path.lower().lstrip("/").startswith("api"):
                assert c.get(path, headers=PUBLIC).status_code == 403, path
        assert c.post("/api/calls", json={"language": "en", "consent": True}, headers=PUBLIC).status_code == 403
        assert c.delete("/api/analyses", headers=PUBLIC).status_code == 403
        assert c.get("/", headers=PUBLIC).status_code == 404         # no built page in tests, but it is not blocked


def test_public_address_cannot_open_the_receiver_or_the_plain_live_socket(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        for path in (f"/api/call/receive?code={info['code']}", "/api/live?language=en&consent=true"):
            with pytest.raises(WebSocketDisconnect):
                with c.websocket_connect(path, headers=PUBLIC) as ws:
                    ws.receive_json()


def test_unknown_hosts_are_refused_everywhere(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        assert c.get("/api/health", headers={"host": "evil.example.com"}).status_code == 400
        assert c.get("/api/health", headers={"host": "other.trycloudflare.com"}).status_code == 400
        with pytest.raises(WebSocketDisconnect):
            with c.websocket_connect("/api/call/speak?code=123456", headers={"host": "evil.example.com"}) as ws:
                ws.receive_json()


def test_speaker_socket_refuses_other_websites(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with pytest.raises(WebSocketDisconnect):
            with speak(c, info["code"], headers={"host": PUB, "origin": "https://evil.example.com"}) as ws:
                ws.receive_json()


def test_receiver_endpoints_refuse_cross_site_requests_on_localhost(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        assert c.post("/api/calls", json={"language": "en", "consent": True}, headers={"origin": "https://evil.example.com"}).status_code == 403
        info = new_call(c)
        with pytest.raises(WebSocketDisconnect):
            with c.websocket_connect(f"/api/call/receive?code={info['code']}", headers={"origin": "https://evil.example.com"}) as ws:
                ws.receive_json()


def test_public_page_gets_a_csp_that_allows_only_its_own_socket(tmp_path):
    app = make_app(tmp_path)
    app.add_api_route("/page", lambda: {"ok": True}, methods=["GET"])      # stands in for the built page
    with TestClient(app) as c:
        h = c.get("/page", headers=PUBLIC).headers
        assert f"wss://{PUB}" in h["content-security-policy"] and "ws://127.0.0.1" not in h["content-security-policy"]
        assert "microphone=(self)" in h["permissions-policy"]


# ------------------------------------------------------------------------------------------ tunnel address -----
@pytest.mark.parametrize("url,ok", [
    ("https://abc-def.trycloudflare.com", True), ("https://abc.trycloudflare.com/", True), ("https://x.ngrok-free.app", True),
    ("http://abc.trycloudflare.com", False), ("https://127.0.0.1", False), ("https://localhost", False),
    ("https://192.168.1.5", False), ("https://abc.trycloudflare.com:8443", False), ("https://user:pw@abc.example.com", False),
    ("", False), (None, False), ("ftp://abc.example.com", False), ("https://nodots", False),
])
def test_public_url_validation(url, ok):
    assert (parse_public_url(url) is not None) is ok


def test_tunnel_address_is_detected_or_pasted_and_then_trusted(tmp_path):
    app = make_app(tmp_path, probe=lambda: "https://found-one.trycloudflare.com", public_url=None)
    with TestClient(app) as c:
        assert c.get("/api/health", headers={"host": "found-one.trycloudflare.com"}).status_code == 400   # not trusted yet
        assert c.get("/api/calls/config").json()["public_url"] == "https://found-one.trycloudflare.com"
        info = new_call(c)                                          # creating a call approves the detected address
        assert info["join_url"].startswith("https://found-one.trycloudflare.com/#/join/")
        assert c.get("/api/health", headers={"host": "found-one.trycloudflare.com"}).status_code == 403
        assert c.post("/api/calls", json={"language": "en", "consent": True, "public_url": "http://bad"}).status_code == 400


def test_a_call_works_without_any_tunnel_for_testing_on_the_laptop(tmp_path):
    app = make_app(tmp_path, public_url=None)
    with TestClient(app) as c:
        info = new_call(c)
        assert info["join_url"] is None and info["public_url"] is None
        with receive(c, info["code"]) as rx, speak(c, info["code"], headers={}) as tx:    # two tabs on 127.0.0.1
            rx.receive_json()
            assert tx.receive_json()["type"] == "joined"


# ------------------------------------------------------------------------------------------ rejoin after a drop --
def phone_drops(tx, rx):
    """Simulate the phone losing its connection: a real server sees a disconnect (the test client would otherwise cancel the
    handler when the with-block exits, which is not what a network drop does). Waits until the Receiver is told."""
    tx.close(1006)
    while True:
        m = rx.receive_json()
        if m.get("type") == "call" and m.get("state") == "reconnecting":
            return m


def start_live(c, rx, tx):
    """Walk a call to the live state and return the phone's resume token."""
    rx.receive_json(); tx.receive_json(); rx.receive_json()
    tx.send_json({"type": "hello", "consent": True})
    ready = tx.receive_json()
    assert rx.receive_json()["type"] == "ready"
    return ready["resume"]


def test_phone_drops_and_rejoins_the_same_call_and_the_report_covers_both_parts(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx:
            with speak(c, info["code"]) as tx:
                token = start_live(c, rx, tx)
                tx.send_bytes(pcm(1.0))
                # the connection is gone without a "stop": the Receiver is told, the call is not ended
                assert phone_drops(tx, rx) == {"type": "call", "state": "reconnecting", "seconds": 60}
            with c.websocket_connect(f"/api/call/speak?code={info['code']}&resume={token}", headers=PUBLIC) as tx2:
                again = tx2.receive_json()
                assert again["type"] == "ready" and again["resumed"] is True and again["resume"] == token
                tx2.send_bytes(pcm(1.0))
                tx2.send_text('{"type":"stop"}')
                assert drain(tx2)[-1] == {"type": "ended"}
            rest = drain(rx)
        assert {"type": "call", "state": "live"} in rest
        ended = rest[-1]
        assert ended["type"] == "ended" and ended["id"]
        rec = c.get(f"/api/analyses/{ended['id']}").json()
        assert rec["report"]["meta"]["audio_seconds"] >= 1.9                 # both parts, and no keepalive silence stored
        assert len(FakeStream.instances) == 1                                # the same analysis streams carried on


def test_rejoin_needs_the_right_token_and_a_call_in_progress(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx:
            with c.websocket_connect(f"/api/call/speak?code={info['code']}&resume=guess", headers=PUBLIC) as bad:
                assert "can no longer be rejoined" in bad.receive_json()["message"]      # nothing to resume yet
            with speak(c, info["code"]) as tx:
                token = start_live(c, rx, tx)
                with c.websocket_connect(f"/api/call/speak?code={info['code']}&resume=wrong-token-value", headers=PUBLIC) as bad:
                    assert "can no longer be rejoined" in bad.receive_json()["message"]
                tx.send_text('{"type":"stop"}')
                drain(tx)
        with c.websocket_connect(f"/api/call/speak?code={info['code']}&resume={token}", headers=PUBLIC) as late:
            assert "can no longer be rejoined" in late.receive_json()["message"]          # the call is over


def test_a_brand_new_phone_cannot_join_a_call_that_has_already_started(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx:
            with speak(c, info["code"]) as tx:
                start_live(c, rx, tx)
                tx.send_bytes(pcm(0.5))
                phone_drops(tx, rx)
            with speak(c, info["code"]) as other:                          # the first phone dropped; a stranger tries the code
                assert "already started" in other.receive_json()["message"]


def test_a_rejoin_replaces_a_connection_the_server_has_not_noticed_is_dead(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as old:
            token = start_live(c, rx, old)
            with c.websocket_connect(f"/api/call/speak?code={info['code']}&resume={token}", headers=PUBLIC) as new:
                assert new.receive_json()["resumed"] is True
                new.send_bytes(pcm(1.2))
                new.send_text('{"type":"stop"}')
                assert drain(new)[-1] == {"type": "ended"}
            ended = [m for m in drain(rx) if m["type"] == "ended"][0]
            assert ended["id"]                                             # the old socket's end did not end or double-store the call


def test_receiver_can_end_the_call_while_the_phone_is_reconnecting(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx:
            with speak(c, info["code"]) as tx:
                start_live(c, rx, tx)
                tx.send_bytes(pcm(2.0))
                phone_drops(tx, rx)
            rx.send_json({"type": "end"})
            ended = [m for m in drain(rx) if m["type"] == "ended"][0]
            assert ended["id"]


def test_the_call_ends_by_itself_when_the_phone_does_not_come_back(tmp_path, monkeypatch):
    monkeypatch.setattr(calls_mod, "GRACE_SECONDS", 0.3)
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx:
            with speak(c, info["code"]) as tx:
                start_live(c, rx, tx)
                tx.send_bytes(pcm(2.0))
                phone_drops(tx, rx)
            ended = [m for m in drain(rx) if m["type"] == "ended"][0]
            assert ended["id"] and ended["max_level"] in ("low", "elevated", "high")
        assert c.post("/api/calls", json={"language": "en", "consent": True}).status_code == 201     # the analysis slot is free again


def test_receiver_hears_about_audio_and_its_level(tmp_path):
    with TestClient(make_app(tmp_path)) as c:
        info = new_call(c)
        with receive(c, info["code"]) as rx, speak(c, info["code"]) as tx:
            start_live(c, rx, tx)
            tx.send_bytes(pcm(0.5, amp=0.5))
            tx.send_bytes(bytes(3200))
            tx.send_text('{"type":"stop"}')
            audio = [m for m in drain(rx) if m["type"] == "audio"]
    assert audio and max(m["rms"] for m in audio) > 0.1                    # loud sine wave: rms about 0.35


def test_keepalive_sends_silence_to_the_streams_but_not_to_the_stored_audio():
    import asyncio
    from core.live import FRAME_BYTES, LiveSession

    async def go():
        stream = FakeStream([])
        s = LiveSession("en", lambda code: stream, lambda m: asyncio.sleep(0))
        await s.start()
        await s.feed(pcm(0.2))
        before, frames = len(s.pcm), stream.frames
        await s.keepalive()
        await s.keepalive()
        return before == len(s.pcm), stream.frames - frames, stream.sent_sizes

    same, extra, sizes = asyncio.run(go())
    assert same and extra == 2 and sizes == {FRAME_BYTES}
