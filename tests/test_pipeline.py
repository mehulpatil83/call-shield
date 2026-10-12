import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from core.analyse import analyse_file, analyse_transcripts, main
from core.authenticity import AuthenticityScorer, label_from_scores
from core.gnani_client import GnaniTranscriber, TranscriptionError
from tests.cases import BENIGN, SCAM


def make_wav(path: Path, seconds=20, sr=16000, amp=0.2):
    t = np.arange(int(sr * seconds)) / sr
    sf.write(str(path), (amp * np.sin(2 * np.pi * 200 * t) * (1 + np.sin(2 * np.pi * 3 * t)) / 2).astype("float32"), sr)


class FakeRest:
    def __init__(self, texts):
        self.calls, self.texts = [], texts

    def transcribe(self, path, language_code, format="verbatim"):
        self.calls.append(language_code)
        return {"transcript": self.texts.get(language_code, ""), "model": "fake-model"}


class FakeModel:
    def __init__(self, value):
        self.value = value

    def score_batch(self, audios, srs):
        return [self.value for _ in audios]


def test_cache_means_second_run_costs_nothing(tmp_path):
    wav = tmp_path / "en_call.wav"
    make_wav(wav)
    rest = FakeRest({"en-IN": SCAM["en_scam"]})
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c", rest_client=rest)
    v1 = tr.transcribe(wav, "en")
    v2 = tr.transcribe(wav, "en")
    assert rest.calls == ["en-IN"]
    assert not v1[0].cached and v2[0].cached and v2[0].text == v1[0].text
    assert (tmp_path / "gnani_ledger.csv").exists()


def test_hinglish_runs_both_codes_and_survives_one_failure(tmp_path):
    wav = tmp_path / "hinglish_call.wav"
    make_wav(wav)
    rest = FakeRest({"en-IN": SCAM["hinglish_scam"], "hi-IN": ""})
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c", rest_client=rest)
    vs = tr.transcribe(wav, "hinglish")
    assert rest.calls == ["en-IN", "hi-IN"] and len(vs) == 2


def test_all_failures_raise(tmp_path):
    wav = tmp_path / "en_call.wav"
    make_wav(wav)
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c", rest_client=FakeRest({}))
    with pytest.raises(TranscriptionError):
        tr.transcribe(wav, "en")


def test_unknown_language(tmp_path):
    wav = tmp_path / "x.wav"
    make_wav(wav)
    with pytest.raises(TranscriptionError):
        GnaniTranscriber(api_key="k", cache_dir=tmp_path).transcribe(wav, "fr")


def test_authenticity_bands():
    assert label_from_scores([-3.0] * 5).label.startswith("No sign")
    assert label_from_scores([-8.0] * 5).label.startswith("Synthetic")
    assert label_from_scores([-5.8] * 5).status == "inconclusive"
    assert label_from_scores([-3.0] * 2).status == "inconclusive"      # too little speech


def test_authenticity_unavailable_without_model(tmp_path):
    wav = tmp_path / "en_call.wav"
    make_wav(wav)
    r = AuthenticityScorer(model_dir=tmp_path / "nope", cache_dir=tmp_path / "a").score(wav)
    assert r.status == "unavailable" and r.reason


def test_authenticity_scoring_and_cache(tmp_path):
    wav = tmp_path / "en_call.wav"
    make_wav(wav, seconds=20)
    sc = AuthenticityScorer(model=FakeModel(-3.1), cache_dir=tmp_path / "a")
    r = sc.score(wav)
    assert r.status == "ok" and r.n_windows >= 4 and r.median == -3.1
    again = AuthenticityScorer(model=None, model_dir=tmp_path / "nope", cache_dir=tmp_path / "a").score(wav)
    assert again.median == -3.1          # served from cache, no model needed


def test_end_to_end_report_files(tmp_path):
    wav = tmp_path / "hinglish_call.wav"
    make_wav(wav, seconds=22)
    rest = FakeRest({"en-IN": SCAM["hinglish_scam"], "hi-IN": SCAM["hinglish_scam_deva"]})
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c", rest_client=rest)
    report, page = analyse_file(wav, "hinglish", tr, AuthenticityScorer(model=FakeModel(-3.0), cache_dir=tmp_path / "a"))
    assert report["conversation"]["level"] == "high"
    assert report["authenticity"]["status"] == "ok"
    assert len(report["transcripts"]) == 2
    assert "<mark" in page and "Limitations" in page
    json.dumps(report, ensure_ascii=False)            # must be serialisable


def test_html_escapes_transcript_markup():
    report, page = analyse_transcripts("x.txt", "en", None, ["<script>alert(1)</script> please share your OTP now"], None, None)
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page


def test_text_mode_cli(tmp_path):
    f = tmp_path / "mr_test.txt"
    f.write_text(BENIGN["mr_benign"], encoding="utf-8")
    assert main([str(f), "--text", str(f), "--out", str(tmp_path / "out")]) == 0
    rep = json.loads((tmp_path / "out" / "mr_test.json").read_text(encoding="utf-8"))
    assert rep["conversation"]["level"] == "low"


def test_report_has_advice_and_notes(tmp_path):
    wav = tmp_path / "en_call.wav"
    make_wav(wav, seconds=20)
    rest = FakeRest({"en-IN": SCAM["en_scam"]})
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c", rest_client=rest)
    seen = []
    report, page = analyse_file(wav, "en", tr, AuthenticityScorer(model=FakeModel(-3.0), cache_dir=tmp_path / "a"),
                                on_status=seen.append, display_name="shown.wav")
    assert seen == ["transcribing", "analysing", "checking_audio"]
    assert report["meta"]["file"] == "shown.wav" and report["meta"]["est_cost_rupees"] > 0
    assert any("Do not share" in a for a in report["advice"]) and "What to do now" in page
    assert report["conversation"]["digit_note"] and report["authenticity"]["plain_note"]
    # cached second run costs nothing
    r2, _ = analyse_file(wav, "en", tr, None)
    assert r2["meta"]["est_cost_rupees"] == 0
