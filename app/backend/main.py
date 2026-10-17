"""FastAPI backend. Local only: binds to 127.0.0.1, no accounts, nothing leaves the machine except the audio that
is sent to Gnani for transcription (and only after the user ticks the consent box)."""
from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core import __version__, config
import asyncio
import json
from datetime import datetime

import numpy as np
import soundfile as sf

from core.analyse import analyse_file, analyse_transcripts
from core.audio_io import duration_seconds
from core.gnani_client import Variant
from core.live import LIVE_MAX_SECONDS, SAMPLE_RATE, LiveSession
from core.authenticity import AuthenticityScorer
from core.gnani_client import GnaniTranscriber, TranscriptionError, load_api_key

from .storage import ID_RE, Store

log = logging.getLogger("call-shield")
ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
LANGUAGES = {"auto": "Not sure (English, Hindi and Marathi)", "en": "English", "hinglish": "Hinglish", "mr": "Marathi", "hi": "Hindi"}
CONSENT_TEXT_VERSION = "2026-10-v1"
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
REPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
UI_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
          "connect-src 'self' ws://127.0.0.1:* ws://localhost:*; base-uri 'none'; form-action 'self'")


LOCAL_HOSTS = {"127.0.0.1", "localhost", "testserver"}


def origin_ok(origin: str | None) -> bool:
    """Browsers attach an Origin header to cross-site requests. Any website could otherwise talk to this local server
    from the user's browser, so only pages served by this machine are accepted. No Origin (curl, tests) is allowed."""
    if not origin:
        return True
    return (urlparse(origin).hostname or "") in LOCAL_HOSTS


class Headers(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not origin_ok(request.headers.get("origin")):
            return JSONResponse({"detail": "Cross-site requests are not allowed."}, status_code=403)
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        if request.url.path.endswith("/report.html"):
            resp.headers["Content-Security-Policy"] = REPORT_CSP
        elif not request.url.path.startswith("/api/"):
            resp.headers.setdefault("Content-Security-Policy", UI_CSP)
        return resp


def create_app(data_dir: Path | None = None, transcriber_factory=None, scorer_factory=None,
               serve_frontend: bool = True, max_upload_mb: int = 25, stream_factory=None) -> FastAPI:
    store = Store(Path(data_dir or config.ROOT / "data"))
    store.recover_interrupted()
    shared_scorer = AuthenticityScorer()          # loads the model once, on first use
    transcriber_factory = transcriber_factory or (lambda cache_dir: GnaniTranscriber(cache_dir=cache_dir))

    def default_scorer(cache_dir: Path):
        shared_scorer.cache_dir = cache_dir
        return shared_scorer

    scorer_factory = scorer_factory or default_scorer

    def default_stream(code: str):
        from gnani.stt import GnaniSTTStreamClient

        key = load_api_key()
        if not key:
            raise TranscriptionError("GNANI_API_KEY not found. Put it in .env")
        return GnaniSTTStreamClient(api_key=key, language_code=code, sample_rate=SAMPLE_RATE)

    stream_factory = stream_factory or default_stream
    live_busy = {"on": False}
    pool = ThreadPoolExecutor(max_workers=1)      # one analysis at a time: the CPU is small
    app = FastAPI(title="call-shield", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(Headers)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=sorted(LOCAL_HOSTS))   # blocks DNS-rebinding tricks

    # ------------------------------------------------------------------ background job -----
    def run_job(id: str, skip_audio_check: bool, conversation: bool = False) -> None:
        rec = store.get(id)
        if not rec:
            return
        path = store.audio_path(id, rec["audio_ext"])
        cache = store.cache_dir(id)
        try:
            transcriber = transcriber_factory(cache / "gnani")
            scorer = None if skip_audio_check else scorer_factory(cache / "auth")
            report, page = analyse_file(path, rec["language"], transcriber, scorer,
                                        on_status=lambda s: store.update(id, status="running", step=s),
                                        display_name=rec["filename"], conversation="auto" if conversation else None)
            store.save_report(id, report, page)
            auth = report["authenticity"]
            store.update(id, status="done", step=None, level=report["conversation"]["level"],
                         auth_label=auth["label"] if auth else None, est_rupees=report["meta"]["est_cost_rupees"],
                         audio_seconds=report["meta"]["audio_seconds"])
        except TranscriptionError as e:
            store.update(id, status="error", step=None, error=str(e)[:400])
        except Exception as e:                    # never log transcripts or audio content
            log.exception("analysis %s failed", id)
            store.update(id, status="error", step=None, error=f"{type(e).__name__}: {str(e)[:300]}")

    # ------------------------------------------------------------------ API ----------------------
    @app.get("/api/health")
    def health():
        return {"ok": True, "version": __version__, "gnani_key_present": load_api_key() is not None,
                "languages": LANGUAGES, "consent_text_version": CONSENT_TEXT_VERSION, "max_upload_mb": max_upload_mb, "live_max_seconds": LIVE_MAX_SECONDS}

    @app.post("/api/analyses", status_code=202)
    async def create(file: UploadFile = File(...), language: str = Form(...), consent: bool = Form(False),
                     skip_audio_check: bool = Form(False), conversation: bool = Form(False)):
        if not consent:
            raise HTTPException(400, "Consent is required: confirm you have permission to analyse this recording.")
        if language not in LANGUAGES:
            raise HTTPException(400, f"Unknown language. Choose one of: {', '.join(LANGUAGES)}")
        if conversation and language == "auto":
            raise HTTPException(400, "Speaker separation needs a specific language (not 'not sure').")
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXT:
            raise HTTPException(400, f"Unsupported file type. Use one of: {', '.join(sorted(ALLOWED_EXT))}")
        id = uuid.uuid4().hex[:12]
        dest, size, limit = store.audio_path(id, ext), 0, max_upload_mb * 1024 * 1024
        try:
            with open(dest, "wb") as out:
                while chunk := await file.read(1 << 20):
                    size += len(chunk)
                    if size > limit:
                        raise HTTPException(413, f"File is larger than {max_upload_mb} MB.")
                    out.write(chunk)
            if size == 0:
                raise HTTPException(400, "The file is empty.")
        except HTTPException:
            dest.unlink(missing_ok=True)
            raise
        name = Path(file.filename or "recording").name[:120]
        store.create(id, name, language, ext)
        pool.submit(run_job, id, skip_audio_check, conversation)
        return {"id": id, "status": "queued"}

    @app.get("/api/analyses")
    def list_all():
        return store.list()

    @app.get("/api/analyses/{id}")
    def get_one(id: str):
        rec = store.get(id)
        if not rec:
            raise HTTPException(404, "Not found")
        rec = {k: v for k, v in rec.items() if k not in ("audio_ext", "consent_at")}
        rec["report"] = store.load_report(id) if rec["status"] == "done" else None
        return rec

    @app.get("/api/analyses/{id}/report.html", response_class=HTMLResponse)
    def report_html(id: str, download: bool = False):
        page = store.report_html(id) if ID_RE.match(id) else None
        if page is None:
            raise HTTPException(404, "Not found")
        headers = {"Content-Disposition": f'attachment; filename="call-shield-{id}.html"'} if download else {}
        return HTMLResponse(page, headers=headers)

    @app.delete("/api/analyses/{id}")
    def delete_one(id: str):
        if not store.delete(id):
            raise HTTPException(404, "Not found")
        return {"deleted": id}

    @app.delete("/api/analyses")
    def delete_all():
        ids = store.ids()
        for i in ids:
            store.delete(i)
        return {"deleted": len(ids)}


    # ------------------------------------------------------------------ live call ----------------
    def finish_live(result, language: str, skip_audio: bool) -> str:
        """Store the finished live call like any other analysis (audio, report, history entry)."""
        id = uuid.uuid4().hex[:12]
        path = store.audio_path(id, ".wav")
        pcm = np.frombuffer(result.pcm, dtype="<i2").astype("float32") / 32768.0
        sf.write(str(path), pcm, SAMPLE_RATE, subtype="PCM_16")
        name = f"live-call-{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        store.create(id, name, language, ".wav")
        try:
            codes = list(result.texts)
            variants = [Variant(c, "stream", result.texts[c], audio_seconds=round(result.seconds, 2)) for c in codes if result.texts[c]]
            if not variants:
                raise TranscriptionError("No speech was transcribed during the call.")
            scorer = None if skip_audio else scorer_factory(store.cache_dir(id) / "auth")
            auth = scorer.score(path) if scorer else None
            report, page = analyse_transcripts(name, language, variants, [v.text for v in variants], auth, round(result.seconds, 1))
            report["meta"]["est_cost_rupees"] = round(result.seconds / 60 * config.RUPEES_PER_MIN * len(codes), 2)
            report["meta"]["live"] = True
            store.save_report(id, report, page)
            store.update(id, status="done", level=report["conversation"]["level"],
                         auth_label=auth.label if auth else None, est_rupees=report["meta"]["est_cost_rupees"],
                         audio_seconds=report["meta"]["audio_seconds"])
        except Exception as e:
            store.update(id, status="error", error=str(e)[:400])
        return id

    @app.websocket("/api/live")
    async def live(ws: WebSocket, language: str = "auto", consent: bool = False, skip_audio_check: bool = False):
        if not origin_ok(ws.headers.get("origin")):
            await ws.close(code=4403)
            return
        await ws.accept()
        if not consent:
            await ws.send_json({"type": "error", "message": "Consent is required before the microphone is used."})
            await ws.close(code=4403)
            return
        if language not in LANGUAGES:
            await ws.send_json({"type": "error", "message": "Unknown language."})
            await ws.close(code=4400)
            return
        if live_busy["on"]:
            await ws.send_json({"type": "error", "message": "Another live check is running. Try again in a minute."})
            await ws.close(code=4409)
            return
        live_busy["on"] = True
        session = None
        try:
            async def send(msg: dict) -> None:
                try:
                    await ws.send_json(msg)
                except Exception:
                    pass

            session = LiveSession(language, stream_factory, send)
            await session.start()
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    if not await session.feed(msg["bytes"]):
                        await send({"type": "limit", "seconds": LIVE_MAX_SECONDS})
                        break
                elif msg.get("text"):
                    try:
                        if json.loads(msg["text"]).get("type") == "stop":
                            break
                    except json.JSONDecodeError:
                        pass
            result = await session.stop()
            if result.seconds < 1.0:
                await send({"type": "ended", "id": None, "message": "The call was too short to analyse."})
            else:
                loop = asyncio.get_running_loop()
                id = await loop.run_in_executor(pool, finish_live, result, language, skip_audio_check)
                await send({"type": "ended", "id": id, "level": result.level, "max_level": result.max_level})
        except WebSocketDisconnect:
            if session:
                await session.stop()
        except Exception as e:
            log.exception("live call failed")
            try:
                await ws.send_json({"type": "error", "message": f"{type(e).__name__}: {str(e)[:200]}"})
            except Exception:
                pass
        finally:
            live_busy["on"] = False
            try:
                await ws.close()
            except Exception:
                pass

    @app.exception_handler(404)
    async def not_found(request, exc):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": getattr(exc, "detail", "Not found")}, status_code=404)
        return HTMLResponse("Not found", status_code=404)

    if serve_frontend and (FRONTEND_DIST / "index.html").exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="ui")
    app.state.store = store
    return app
