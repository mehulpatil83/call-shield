"""Call mode, Part 1: one Receiver (the laptop running call-shield) and one Speaker (a phone, reached through an HTTPS tunnel).

Audio path:  phone microphone -> WebSocket (PCM16 mono 16 kHz) -> this server -> the existing LiveSession
(Gnani streaming speech-to-text + rules). Only the Receiver's socket gets analysis messages; the Speaker's socket
never does. The server stays bound to 127.0.0.1: the tunnel program connects to it locally.

Security model (the tunnel makes this server reachable from the internet, so the surface is kept tiny):
  * Requests that arrive with a *public* Host (the tunnel address the owner approved) may only fetch the web page's
    static files (GET/HEAD, nothing under /api) and open the speaker WebSocket. Everything else (history, reports,
    uploads, the receiver socket, the plain live check, API docs) answers 403 on the public address.
  * Any other Host header is refused (blocks DNS-rebinding tricks), exactly as before.
  * A Speaker needs the 6-digit code of a call that is waiting. A code works once, expires after 10 minutes, and wrong
    guesses are rate-limited per client. Only one Speaker and one Receiver can be in a call.
  * Nothing is accepted from the Speaker before the Speaker's consent message; the server enforces it.
  * If the phone drops mid-call, the call waits GRACE_SECONDS for it. Only the same phone can rejoin: it holds a random
    resume token that was given to it alone (never to the Receiver) when the call started.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import posixpath
import re
import secrets
import time
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.responses import PlainTextResponse

from core.live import LIVE_MAX_SECONDS, LiveSession

log = logging.getLogger("call-shield")

LOCAL_HOSTS = {"127.0.0.1", "localhost", "testserver"}
SPEAK_PATH = "/api/call/speak"
CODE_RE = re.compile(r"^\d{6}$")
CODE_TTL = 600.0                  # seconds a waiting call can be joined
HELLO_TIMEOUT = 30.0              # seconds a Speaker has to confirm consent after joining
GRACE_SECONDS = 60.0              # a dropped phone can rejoin the same call for this long (screen lock, weak signal)
AUDIO_REPORT_EVERY = 0.25         # the Receiver is told how loud the incoming audio is at most this often (seconds)
MAX_FAILS, FAIL_WINDOW = 8, 60.0  # wrong codes allowed per client per minute
TUNNEL_METRICS = "http://127.0.0.1:20241/quicktunnel"     # cloudflared --metrics 127.0.0.1:20241 (best effort)


# ---------------------------------------------------------------------------------------------- hosts --------
def host_of(headers: list[tuple[bytes, bytes]]) -> str:
    for k, v in headers:
        if k == b"host":
            h = v.decode("latin-1").strip().lower()
            if h.startswith("["):                     # [ipv6]:port
                return h[1:h.find("]")] if "]" in h else h
            if ":" in h and h.rsplit(":", 1)[1].isdigit():
                h = h.rsplit(":", 1)[0]
            return h
    return ""


def parse_public_url(url: str | None) -> str | None:
    """Accept only a plain https address with a real host name (what a tunnel gives). Returns 'https://host' or None."""
    try:
        p = urlparse((url or "").strip())
    except ValueError:
        return None
    host = (p.hostname or "").lower()
    if p.scheme != "https" or not host or host in LOCAL_HOSTS or "." not in host:
        return None
    if p.port not in (None, 443) or p.username or p.password:
        return None
    try:
        ipaddress.ip_address(host)
        return None                                   # raw IP addresses are not tunnel addresses
    except ValueError:
        pass
    return f"https://{host}"


def public_path_allowed(scope: dict) -> bool:
    path = posixpath.normpath("/" + scope.get("path", "").lstrip("/")).lower()
    if scope["type"] == "websocket":
        return path == SPEAK_PATH
    if scope.get("method") not in ("GET", "HEAD"):
        return False
    return not (path.startswith("/api") or path in ("/openapi.json", "/docs", "/redoc") or path.startswith("/docs/"))


class HostGate:
    """Outermost ASGI layer. Local hosts pass. Approved public hosts pass only for the tiny public surface. Others: 400."""

    def __init__(self, app, public_hosts: set[str]):
        self.app, self.public_hosts = app, public_hosts

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        host = host_of(scope.get("headers", []))
        scope["hostname"] = host
        if host in LOCAL_HOSTS:
            scope["public"] = False
        elif host in self.public_hosts:
            scope["public"] = True
            if not public_path_allowed(scope):
                await self._deny(scope, receive, send, 403, "Not available on the public address.")
                return
        else:
            await self._deny(scope, receive, send, 400, "Invalid host header")
            return
        await self.app(scope, receive, send)

    @staticmethod
    async def _deny(scope, receive, send, status: int, text: str) -> None:
        if scope["type"] == "websocket":
            await receive()                                   # the connect event
            await send({"type": "websocket.close", "code": 1008})
        elif status == 403:
            await JSONResponse({"detail": text}, status_code=403)(scope, receive, send)
        else:
            await PlainTextResponse(text, status_code=status)(scope, receive, send)


# ---------------------------------------------------------------------------------------------- rooms --------
@dataclass
class CallRoom:
    code: str
    language: str
    skip_audio: bool
    created: float
    receiver: WebSocket | None = None
    speaker: WebSocket | None = None
    state: str = "waiting"                 # waiting | joined | live | reconnecting | ended
    listen: bool = False
    session: LiveSession | None = None
    resume: str | None = None              # secret for the Speaker's phone only
    conn_id: int = 0                       # which speaker connection is the current one
    owns_busy: bool = False
    grace_task: asyncio.Task | None = None
    stop: asyncio.Event | None = None      # set to make the speaker handler finish the call
    done: asyncio.Event | None = None      # set when the call is over (the receiver handler waits on it)

    async def to_receiver(self, msg: dict) -> None:
        if self.receiver is not None:
            try:
                await self.receiver.send_json(msg)
            except Exception:
                pass

    async def bytes_to_receiver(self, data: bytes) -> None:
        if self.receiver is not None:
            try:
                await self.receiver.send_bytes(data)
            except Exception:
                pass


class CallManager:
    """Holds at most one call (one live analysis at a time on this CPU)."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.room: CallRoom | None = None
        self.fails: dict[str, list[float]] = {}

    def create(self, language: str, skip_audio: bool) -> tuple[CallRoom, CallRoom | None]:
        old = self.room if self.room and self.room.state != "ended" else None
        if old and old.state in ("joined", "live"):
            raise RuntimeError("A call is in progress.")
        self.room = CallRoom(f"{secrets.randbelow(10**6):06d}", language, skip_audio, self.clock())
        return self.room, old

    def get(self, code: str) -> CallRoom | None:
        r = self.room
        if not r or r.state == "ended" or r.code != code:
            return None
        if r.state == "waiting" and self.clock() - r.created > CODE_TTL:
            return None
        return r

    def end(self, room: CallRoom) -> None:
        room.state = "ended"
        if self.room is room:
            self.room = None

    # --- wrong-guess limiter -------------------------------------------------------------------------------
    def too_many_failures(self, key: str) -> bool:
        now = self.clock()
        recent = [t for t in self.fails.get(key, []) if now - t < FAIL_WINDOW]
        self.fails[key] = recent
        return len(recent) >= MAX_FAILS

    def note_failure(self, key: str) -> None:
        self.fails.setdefault(key, []).append(self.clock())


# ---------------------------------------------------------------------------------------------- routes -------
class CallCreate(BaseModel):
    language: str = "en"
    consent: bool = False
    skip_audio_check: bool = False
    public_url: str | None = None


def probe_cloudflared() -> str | None:
    """Ask a locally running `cloudflared tunnel --metrics 127.0.0.1:20241` for its quick-tunnel address (best effort)."""
    try:
        with urllib.request.urlopen(TUNNEL_METRICS, timeout=0.6) as r:                    # noqa: S310 (fixed local URL)
            host = (json.loads(r.read().decode()).get("hostname") or "").strip()
        return parse_public_url(f"https://{host}") if host else None
    except Exception:
        return None


def speak_origin_ok(origin: str | None, public_hosts: set[str]) -> bool:
    if not origin:
        return True
    return (urlparse(origin).hostname or "") in (LOCAL_HOSTS | public_hosts)


async def _send_safe(ws: WebSocket, msg: dict) -> None:
    try:
        await ws.send_json(msg)
    except Exception:
        pass


def add_call_routes(app: FastAPI, *, manager: CallManager, languages: dict, origin_ok, live_busy: dict, pool,
                    finish_live, stream_factory, public_hosts: set[str], tunnel_probe=probe_cloudflared) -> None:

    @app.get("/api/calls/config")
    async def call_config():
        url = app.state.public_url or await asyncio.get_running_loop().run_in_executor(None, tunnel_probe)
        return {"public_url": url, "max_seconds": LIVE_MAX_SECONDS, "code_ttl": int(CODE_TTL)}

    @app.post("/api/calls", status_code=201)
    async def create_call(body: CallCreate):
        if not body.consent:
            return JSONResponse({"detail": "Consent is required before a call can be started."}, status_code=400)
        if body.language not in languages:
            return JSONResponse({"detail": "Unknown language."}, status_code=400)
        if live_busy["on"]:
            return JSONResponse({"detail": "Another live check is running. Try again in a minute."}, status_code=409)
        url = body.public_url or app.state.public_url or await asyncio.get_running_loop().run_in_executor(None, tunnel_probe)
        public = None
        if url:
            public = parse_public_url(url)
            if not public:
                return JSONResponse({"detail": "The public address must be the https address the tunnel printed."}, status_code=400)
            public_hosts.add(urlparse(public).hostname)
            app.state.public_url = public
        try:
            room, old = manager.create(body.language, body.skip_audio_check)
        except RuntimeError:
            return JSONResponse({"detail": "A call is already in progress."}, status_code=409)
        if old:                                           # a waiting call that was never used: cancel it
            old.state = "ended"
            await old.to_receiver({"type": "ended", "id": None, "message": "Replaced by a new call."})
            if old.done:
                old.done.set()
        return {"code": room.code, "language": room.language, "public_url": public,
                "join_url": f"{public}/#/join/{room.code}" if public else None, "expires_in": int(CODE_TTL)}

    # ------------------------------------------------------------------ receiver ---------------------------
    @app.websocket("/api/call/receive")
    async def call_receive(ws: WebSocket, code: str = ""):
        if not origin_ok(ws.headers.get("origin")):
            await ws.close(code=4403)
            return
        await ws.accept()
        room = manager.get(code) if CODE_RE.fullmatch(code) else None
        if not room:
            await _send_safe(ws, {"type": "error", "message": "No such call (or it has expired)."})
            await ws.close(code=4404)
            return
        if room.receiver is not None:
            await _send_safe(ws, {"type": "error", "message": "This call already has a receiver."})
            await ws.close(code=4409)
            return
        room.receiver, room.done = ws, asyncio.Event()
        await _send_safe(ws, {"type": "call", "state": "waiting"})

        async def pump() -> None:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    return
                if not msg.get("text"):
                    continue
                try:
                    data = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "listen":
                    room.listen = bool(data.get("on"))
                elif data.get("type") == "end":
                    if room.stop:
                        room.stop.set()
                    else:                                      # nobody has joined yet: just cancel
                        manager.end(room)
                        await _send_safe(ws, {"type": "ended", "id": None, "message": "The call was cancelled."})
                        return

        pump_task = asyncio.ensure_future(pump())
        done_task = asyncio.ensure_future(room.done.wait())
        try:
            await asyncio.wait({pump_task, done_task}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in (pump_task, done_task):
                t.cancel()
            if room.receiver is ws:
                room.receiver = None
            if room.state != "ended":                          # receiver left: finish the call, keep the report
                if room.stop:
                    room.stop.set()
                else:
                    manager.end(room)
            try:
                await ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------ ending a call ---------------------
    async def end_call(room: CallRoom, problem: str | None = None) -> None:
        """Stop the analysis, store the report, tell both sides. A call that never started goes back to waiting."""
        if room.state == "ended":
            return
        session, room.session = room.session, None
        speaker = room.speaker
        try:
            result = await session.stop() if session else None
            if problem and speaker is not None:
                await _send_safe(speaker, {"type": "error", "message": problem})
            if result is not None:
                if result.seconds >= 1.0:
                    loop = asyncio.get_running_loop()
                    sid = await loop.run_in_executor(pool, finish_live, result, room.language, room.skip_audio)
                    await room.to_receiver({"type": "ended", "id": sid, "level": result.level, "max_level": result.max_level})
                else:
                    await room.to_receiver({"type": "ended", "id": None, "message": "The call was too short to analyse."})
                if speaker is not None:
                    await _send_safe(speaker, {"type": "ended"})
                manager.end(room)
                if room.done:
                    room.done.set()
            else:                                             # the speaker never started: let the code be used again
                room.speaker, room.state, room.stop = None, "waiting", None
                if room.receiver is None:                     # ...unless the receiver has gone too
                    manager.end(room)
                else:
                    await room.to_receiver({"type": "call", "state": "waiting"})
                if speaker is not None:
                    await _send_safe(speaker, {"type": "ended"})
        finally:
            if room.owns_busy:
                live_busy["on"], room.owns_busy = False, False
            if speaker is not None:
                try:
                    await speaker.close()
                except Exception:
                    pass

    async def grace(room: CallRoom) -> None:
        """The phone dropped: keep the call (and the speech-to-text streams) alive for a while so it can rejoin."""
        deadline = time.monotonic() + GRACE_SECONDS
        while time.monotonic() < deadline:
            if room.state != "reconnecting":
                return
            if room.stop is not None and room.stop.is_set():
                break
            if room.session is not None:
                await room.session.keepalive()
            await asyncio.sleep(0.032)
        await end_call(room)

    async def pump(ws: WebSocket, room: CallRoom, my_id: int) -> tuple[str, str | None]:
        """Read the phone's audio until it stops, drops, or the Receiver ends the call."""
        stop_wait = asyncio.ensure_future(room.stop.wait())
        recv: asyncio.Future | None = None
        last_report, peak = 0.0, 0.0
        try:
            while True:
                if recv is None:
                    recv = asyncio.ensure_future(ws.receive())
                done, _ = await asyncio.wait({recv, stop_wait}, return_when=asyncio.FIRST_COMPLETED)
                if room.conn_id != my_id:
                    return "superseded", None
                if stop_wait in done:
                    return "receiver_end", None
                msg, recv = recv.result(), None
                if msg.get("type") == "websocket.disconnect":
                    return "dropped", None
                data = msg.get("bytes")
                if data is not None:
                    if room.session is None:
                        return "problem", "The call is no longer running."
                    if not await room.session.feed(data):
                        await room.to_receiver({"type": "limit", "seconds": LIVE_MAX_SECONDS})
                        return "limit", None
                    if room.listen:
                        await room.bytes_to_receiver(data)
                    if len(data) >= 2:                                      # tell the Receiver audio is arriving, and how loud
                        a = np.frombuffer(data[: len(data) - len(data) % 2], dtype="<i2").astype("float32") / 32768.0
                        peak = max(peak, float(np.sqrt(np.mean(a * a))))
                    now = time.monotonic()
                    if now - last_report >= AUDIO_REPORT_EVERY:
                        await room.to_receiver({"type": "audio", "rms": round(peak, 4)})
                        last_report, peak = now, 0.0
                elif msg.get("text"):
                    try:
                        kind = json.loads(msg["text"]).get("type")
                    except json.JSONDecodeError:
                        continue
                    if kind == "stop":
                        return "stop", None
        except Exception as e:                                # never log audio or transcripts
            log.exception("call failed")
            return "problem", type(e).__name__
        finally:
            for t in (recv, stop_wait):
                if t is not None:
                    t.cancel()

    async def after_pump(room: CallRoom, ws: WebSocket, outcome: str, problem: str | None) -> None:
        if outcome == "superseded":
            return
        if outcome == "dropped" and room.session is not None and room.state == "live":
            room.speaker, room.state = None, "reconnecting"
            await room.to_receiver({"type": "call", "state": "reconnecting", "seconds": int(GRACE_SECONDS)})
            room.grace_task = asyncio.ensure_future(grace(room))
            return
        await end_call(room, problem)

    # ------------------------------------------------------------------ speaker ----------------------------
    @app.websocket(SPEAK_PATH)
    async def call_speak(ws: WebSocket, code: str = "", resume: str = ""):
        if not speak_origin_ok(ws.headers.get("origin"), public_hosts):
            await ws.close(code=4403)
            return
        await ws.accept()
        key = ws.headers.get("cf-connecting-ip") or (ws.client.host if ws.client else "?")

        async def refuse(message: str, close_code: int, failed: bool = False) -> None:
            if failed:
                manager.note_failure(key)
            await _send_safe(ws, {"type": "error", "message": message})
            await ws.close(code=close_code)

        if manager.too_many_failures(key):
            await refuse("Too many wrong codes. Wait a minute and try again.", 4429)
            return
        room = manager.get(code) if CODE_RE.fullmatch(code) else None

        # ---- the same phone coming back after a drop or a screen lock -----------------------------------------
        if resume:
            ok = (room is not None and room.resume is not None and room.state in ("live", "reconnecting")
                  and secrets.compare_digest(resume, room.resume))
            if not ok:
                await refuse("This call can no longer be rejoined.", 4404, failed=True)
                return
            room.conn_id += 1
            my_id = room.conn_id
            if room.grace_task is not None:
                room.grace_task.cancel()
                room.grace_task = None
            old, room.speaker, room.state = room.speaker, ws, "live"
            if old is not None and old is not ws:
                try:
                    await old.close()
                except Exception:
                    pass
            await _send_safe(ws, {"type": "ready", "resume": room.resume, "resumed": True})
            await room.to_receiver({"type": "call", "state": "live"})
            outcome, problem = await pump(ws, room, my_id)
            await after_pump(room, ws, outcome, problem)
            return

        # ---- a new speaker ------------------------------------------------------------------------------------
        if not room:
            await refuse("That code is not valid, or the call has expired.", 4404, failed=True)
            return
        if room.receiver is None:
            await refuse("The receiver is not ready yet.", 4409)
            return
        if room.speaker is not None:
            await refuse("This call already has a speaker.", 4409)
            return
        if room.state != "waiting":
            await refuse("This call has already started.", 4409)
            return

        room.conn_id += 1
        my_id = room.conn_id
        room.speaker, room.state, room.stop = ws, "joined", asyncio.Event()
        await room.to_receiver({"type": "call", "state": "joined"})
        await _send_safe(ws, {"type": "joined", "language": room.language})

        async def forward(msg: dict) -> None:
            await room.to_receiver(msg)
            if msg.get("type") == "ready":                    # the Speaker only learns that it may talk (and its resume token)
                await _send_safe(ws, {"type": "ready", "resume": room.resume})

        # phase 1: wait for the consent message
        problem: str | None = None
        stop_wait = asyncio.ensure_future(room.stop.wait())
        recv: asyncio.Future | None = None
        deadline = time.monotonic() + HELLO_TIMEOUT
        started = False
        try:
            while not started:
                if recv is None:
                    recv = asyncio.ensure_future(ws.receive())
                done, _ = await asyncio.wait({recv, stop_wait}, timeout=max(0.05, deadline - time.monotonic()),
                                             return_when=asyncio.FIRST_COMPLETED)
                if not done:
                    problem = "Consent was not confirmed in time."
                    break
                if stop_wait in done:
                    break
                msg, recv = recv.result(), None
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    problem = "Consent is required before audio is accepted."
                    break
                if not msg.get("text"):
                    continue
                try:
                    data = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "hello":
                    if data.get("consent") is not True:
                        problem = "Consent is required before the call can start."
                        break
                    if live_busy["on"]:
                        problem = "Another live check is running. Try again in a minute."
                        break
                    live_busy["on"], room.owns_busy = True, True
                    try:
                        room.resume = secrets.token_urlsafe(16)
                        room.session = LiveSession(room.language, stream_factory, forward)
                        await room.session.start()
                        room.state, started = "live", True
                    except Exception as e:
                        log.exception("could not start the call analysis")
                        await room.to_receiver({"type": "error", "message": f"{type(e).__name__}: {str(e)[:200]}"})
                        room.session, room.resume = None, None
                        problem = "The receiver could not start the analysis."
                        break
                elif data.get("type") == "stop":
                    break
        except Exception as e:
            log.exception("call failed")
            problem = problem or type(e).__name__
        finally:
            for t in (recv, stop_wait):
                if t is not None:
                    t.cancel()

        if not started:
            await end_call(room, problem)
            return
        # phase 2: stream (also used again when the phone rejoins)
        outcome, problem = await pump(ws, room, my_id)
        await after_pump(room, ws, outcome, problem)
