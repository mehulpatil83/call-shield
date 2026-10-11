"""FastAPI backend. Local only: binds to 127.0.0.1, no accounts, nothing leaves the machine except the audio that
is sent to Gnani for transcription (and only after the user ticks the consent box)."""
from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from core import __version__, config
from core.analyse import analyse_file
from core.authenticity import AuthenticityScorer
from core.gnani_client import GnaniTranscriber, TranscriptionError, load_api_key

from .storage import ID_RE, Store

log = logging.getLogger("call-shield")
ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
LANGUAGES = {"en": "English", "hinglish": "Hinglish", "mr": "Marathi", "hi": "Hindi"}
CONSENT_TEXT_VERSION = "2026-10-v1"
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
REPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
UI_CSP = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; base-uri 'none'; form-action 'self'"


class Headers(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
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
               serve_frontend: bool = True, max_upload_mb: int = 25) -> FastAPI:
    store = Store(Path(data_dir or config.ROOT / "data"))
    store.recover_interrupted()
    shared_scorer = AuthenticityScorer()          # loads the model once, on first use
    transcriber_factory = transcriber_factory or (lambda cache_dir: GnaniTranscriber(cache_dir=cache_dir))

    def default_scorer(cache_dir: Path):
        shared_scorer.cache_dir = cache_dir
        return shared_scorer

    scorer_factory = scorer_factory or default_scorer
    pool = ThreadPoolExecutor(max_workers=1)      # one analysis at a time: the CPU is small
    app = FastAPI(title="call-shield", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(Headers)

    # ------------------------------------------------------------------ background job -----
    def run_job(id: str, skip_audio_check: bool) -> None:
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
                                        display_name=rec["filename"])
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
                "languages": LANGUAGES, "consent_text_version": CONSENT_TEXT_VERSION, "max_upload_mb": max_upload_mb}

    @app.post("/api/analyses", status_code=202)
    async def create(file: UploadFile = File(...), language: str = Form(...), consent: bool = Form(False),
                     skip_audio_check: bool = Form(False)):
        if not consent:
            raise HTTPException(400, "Consent is required: confirm you have permission to analyse this recording.")
        if language not in LANGUAGES:
            raise HTTPException(400, f"Unknown language. Choose one of: {', '.join(LANGUAGES)}")
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
        pool.submit(run_job, id, skip_audio_check)
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

    @app.exception_handler(404)
    async def not_found(request, exc):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": getattr(exc, "detail", "Not found")}, status_code=404)
        return HTMLResponse("Not found", status_code=404)

    if serve_frontend and (FRONTEND_DIST / "index.html").exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="ui")
    app.state.store = store
    return app
