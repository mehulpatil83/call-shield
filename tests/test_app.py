import io
import time

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.backend.main import create_app
from core.authenticity import AuthenticityScorer
from core.gnani_client import GnaniTranscriber, TranscriptionError
from tests.cases import SCAM
from tests.test_pipeline import FakeModel, FakeRest


def wav_bytes(seconds=20, sr=16000):
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 200 * t) * (1 + np.sin(2 * np.pi * 3 * t)) / 2).astype("float32"), sr, format="WAV")
    return buf.getvalue()


def make_client(tmp_path, texts=None, max_upload_mb=25, rest=None):
    rest = rest or FakeRest(texts if texts is not None else {"en-IN": SCAM["en_scam"]})
    app = create_app(
        data_dir=tmp_path / "data",
        transcriber_factory=lambda cache: GnaniTranscriber(api_key="k", cache_dir=cache, rest_client=rest),
        scorer_factory=lambda cache: AuthenticityScorer(model=FakeModel(-3.0), cache_dir=cache),
        serve_frontend=False, max_upload_mb=max_upload_mb)
    return TestClient(app), app


def upload(client, name="en_call.wav", language="en", consent="true", data=None):
    return client.post("/api/analyses", files={"file": (name, data if data is not None else wav_bytes(), "audio/wav")},
                       data={"language": language, "consent": consent})


def wait_done(client, id, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        rec = client.get(f"/api/analyses/{id}").json()
        if rec["status"] in ("done", "error"):
            return rec
        time.sleep(0.05)
    raise AssertionError("timed out")


def test_consent_is_required(tmp_path):
    c, _ = make_client(tmp_path)
    r = upload(c, consent="false")
    assert r.status_code == 400 and "Consent" in r.json()["detail"]
    assert c.get("/api/analyses").json() == []


def test_rejects_bad_type_language_and_empty(tmp_path):
    c, _ = make_client(tmp_path)
    assert upload(c, name="x.exe").status_code == 400
    assert upload(c, language="fr").status_code == 400
    assert upload(c, data=b"").status_code == 400


def test_rejects_large_upload_and_cleans_up(tmp_path):
    c, app = make_client(tmp_path, max_upload_mb=1)
    r = upload(c, data=b"0" * (2 * 1024 * 1024))
    assert r.status_code == 413
    assert list((tmp_path / "data" / "uploads").iterdir()) == []


def test_full_flow_report_html_and_delete(tmp_path):
    c, _ = make_client(tmp_path)
    r = upload(c)
    assert r.status_code == 202
    id = r.json()["id"]
    rec = wait_done(c, id)
    assert rec["status"] == "done" and rec["level"] == "high"
    assert rec["report"]["advice"] and rec["report"]["authenticity"]["status"] == "ok"
    assert "audio_ext" not in rec and "consent_at" not in rec
    listed = c.get("/api/analyses").json()
    assert [x["id"] for x in listed] == [id] and listed[0]["level"] == "high"
    html = c.get(f"/api/analyses/{id}/report.html")
    assert html.status_code == 200 and "What to do now" in html.text
    assert "default-src 'none'" in html.headers["content-security-policy"]
    assert "attachment" in c.get(f"/api/analyses/{id}/report.html?download=true").headers["content-disposition"]
    data = tmp_path / "data"
    assert any(data.joinpath("uploads").iterdir()) and (data / "cache" / id).exists()
    assert c.delete(f"/api/analyses/{id}").status_code == 200
    assert c.get(f"/api/analyses/{id}").status_code == 404
    assert not any(data.joinpath("uploads").iterdir()) and not any(data.joinpath("reports").iterdir())
    assert not (data / "cache" / id).exists()          # transcript cache removed too


def test_transcription_error_is_reported(tmp_path):
    c, _ = make_client(tmp_path, texts={})
    id = upload(c).json()["id"]
    rec = wait_done(c, id)
    assert rec["status"] == "error" and "No transcript" in rec["error"] and rec["report"] is None


def test_skip_audio_check(tmp_path):
    c, _ = make_client(tmp_path)
    id = c.post("/api/analyses", files={"file": ("en_call.wav", wav_bytes(), "audio/wav")},
                data={"language": "en", "consent": "true", "skip_audio_check": "true"}).json()["id"]
    assert wait_done(c, id)["report"]["authenticity"] is None


def test_invalid_ids_and_delete_all(tmp_path):
    c, _ = make_client(tmp_path)
    assert c.get("/api/analyses/..%2Fsecret").status_code == 404
    assert c.get("/api/analyses/not-an-id").status_code == 404
    assert c.delete("/api/analyses/zzzzzzzzzzzz").status_code == 404
    for _ in range(2):
        wait_done(c, upload(c).json()["id"])
    assert c.delete("/api/analyses").json() == {"deleted": 2}
    assert c.get("/api/analyses").json() == []


def test_interrupted_jobs_are_marked_after_restart(tmp_path):
    c, app = make_client(tmp_path)
    store = app.state.store
    store.create("abcdef012345", "x.wav", "en", ".wav")
    store.update("abcdef012345", status="running", step="transcribing")
    c2, _ = make_client(tmp_path)
    rec = c2.get("/api/analyses/abcdef012345").json()
    assert rec["status"] == "error" and "restart" in rec["error"]


def test_health_does_not_expose_the_key(tmp_path, monkeypatch):
    monkeypatch.setenv("GNANI_API_KEY", "super-secret-key")
    c, _ = make_client(tmp_path)
    r = c.get("/api/health")
    assert r.json()["gnani_key_present"] is True and "super-secret-key" not in r.text
    assert r.headers["x-content-type-options"] == "nosniff"


def test_auto_language_is_accepted(tmp_path):
    c, _ = make_client(tmp_path, texts={"en-IN": SCAM["en_scam"], "hi-IN": "", "mr-IN": ""})
    r = upload(c, language="auto")
    assert r.status_code == 202
    assert wait_done(c, r.json()["id"])["status"] == "done"


def test_cross_site_requests_are_refused(tmp_path):
    c, _ = make_client(tmp_path)
    evil = {"Origin": "https://evil.example"}
    r = c.post("/api/analyses", files={"file": ("en_call.wav", wav_bytes(), "audio/wav")},
               data={"language": "en", "consent": "true"}, headers=evil)
    assert r.status_code == 403
    assert c.delete("/api/analyses", headers=evil).status_code == 403
    assert c.get("/api/analyses", headers=evil).status_code == 200          # reading is not the risk; writing and cost are
    ok = c.post("/api/analyses", files={"file": ("en_call.wav", wav_bytes(), "audio/wav")},
                data={"language": "en", "consent": "true"}, headers={"Origin": "http://127.0.0.1:8000"})
    assert ok.status_code == 202


def test_unknown_host_header_is_refused(tmp_path):
    c, _ = make_client(tmp_path)
    assert c.get("/api/health", headers={"Host": "attacker.example"}).status_code == 400
