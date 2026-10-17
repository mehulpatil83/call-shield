import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app.backend.main import create_app
from core.analyse import analyse_file
from core.authenticity import AuthenticityScorer
from core.conversation import channels_look_separate, parts_from_segments, speaker_audio
from core.gnani_client import GnaniTranscriber, TranscriptionError

SCAM_A = ("hello sir i am calling from your bank security department your account will be blocked today unless you verify "
          "right now please share the six digit otp")


class Seg:
    def __init__(self, start, end, speaker, text):
        self.start, self.end, self.speaker, self.text = start, end, speaker, text


class FakeFile:
    ok, error = True, None

    def __init__(self, segments):
        self.segments = segments
        self.text = " ".join(s.text for s in segments)


class FakeBatch:
    def __init__(self, segments):
        self.segments, self.calls = segments, []

    def transcribe(self, path, language_code, progress=False, raise_on_failure=False, timeout=None, **kw):
        self.calls.append((language_code, kw))
        return [FakeFile(self.segments)]


class AmpModel:
    def score_batch(self, audios, srs):
        return [-8.0 if float(np.mean(np.abs(a))) < 0.1 else -3.0 for a in audios]


def two_voice_wav(path, seconds=40, sr=16000):
    """0-10 s and 20-30 s: loud tone (speaker A). 10-20 s and 30-40 s: quiet tone (speaker B)."""
    t = np.arange(sr * seconds) / sr
    x = np.zeros_like(t, dtype="float32")
    for a, b, amp, f in [(0, 10, 0.4, 220), (10, 20, 0.04, 330), (20, 30, 0.4, 220), (30, 40, 0.04, 330)]:
        m = (t >= a) & (t < b)
        x[m] = amp * np.sin(2 * np.pi * f * t[m])
    sf.write(str(path), x, sr)


SEGMENTS = [Seg(0, 10, 0, SCAM_A[:80]), Seg(10, 20, 1, "no i will not share my otp with anyone"),
            Seg(20, 30, 0, SCAM_A[80:]), Seg(30, 40, 1, "okay then i will hang up")]


def test_parts_group_by_speaker_in_order_of_appearance():
    segs = [{"start": 0, "end": 2, "speaker": "B", "text": "hi"}, {"start": 2, "end": 4, "speaker": "A", "text": "yo"},
            {"start": 4, "end": 6, "speaker": "B", "text": "bye"}, {"start": 6, "end": 6.05, "speaker": None, "text": ""}]
    parts = parts_from_segments(segs)
    assert [p.label for p in parts] == ["Speaker 1", "Speaker 2", "Speaker 3"]
    assert parts[0].text == "hi bye" and parts[0].seconds == 4.0 and parts[1].text == "yo"


def test_speaker_audio_takes_only_that_speakers_time(tmp_path):
    wav = tmp_path / "c.wav"
    two_voice_wav(wav)
    a = speaker_audio(wav, [(0, 10), (20, 30)])
    b = speaker_audio(wav, [(10, 20), (30, 40)])
    assert 19.5 < len(a) / 16000 < 21 and np.mean(np.abs(a)) > 5 * np.mean(np.abs(b))


def test_channels_detection():
    rng = np.random.default_rng(0)
    left, right = rng.normal(size=16000).astype("float32"), rng.normal(size=16000).astype("float32")
    assert channels_look_separate([left, right])
    assert not channels_look_separate([left, left * 0.9])            # same sound twice = mono stored as stereo
    assert not channels_look_separate([left])
    assert channels_look_separate([left, np.zeros(16000, dtype="float32")])


def test_diarized_call_is_judged_per_speaker(tmp_path):
    wav = tmp_path / "convo.wav"
    two_voice_wav(wav)
    batch = FakeBatch(SEGMENTS)
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c" / "gnani", batch_client=batch)
    sc = AuthenticityScorer(model=AmpModel(), cache_dir=tmp_path / "c" / "auth")
    seen = []
    report, page = analyse_file(wav, "en", tr, sc, on_status=seen.append, conversation="diarization")
    assert batch.calls[0][0] == "en-IN" and batch.calls[0][1]["diarization"] is True and batch.calls[0][1]["speakers"] == 2
    a, b = report["speakers"]
    assert a["label"] == "Speaker 1" and a["level"] == "high" and "otp" in " ".join(a["quotes"]).lower()
    assert b["level"] == "low" and not b["quotes"]                    # "I will not share my OTP" is a warning, not a request
    assert report["conversation"]["level"] == "high" and report["conversation"]["who"] == "Speaker 1"
    assert "Speaker 1" in report["plain_summary"]
    # voice check ran on each speaker's own audio: loud tone looks natural, quiet tone looks synthetic
    assert a["authenticity"]["code"] == "natural" and b["authenticity"]["code"] == "synthetic"
    assert [t["code"] for t in report["transcripts"]] == ["Speaker 1", "Speaker 2"]
    assert seen == ["transcribing", "analysing", "checking_audio"]
    assert "Who said what" in page and report["meta"]["conversation_mode"] == "diarization"
    assert report["meta"]["est_cost_rupees"] > 0
    again, _ = analyse_file(wav, "en", tr, None, conversation="diarization")
    assert again["meta"]["est_cost_rupees"] == 0 and len(batch.calls) == 1       # cached


def test_hinglish_uses_one_code_and_auto_language_is_refused(tmp_path):
    wav = tmp_path / "convo.wav"
    two_voice_wav(wav)
    batch = FakeBatch(SEGMENTS)
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c" / "gnani", batch_client=batch)
    analyse_file(wav, "hinglish", tr, None, conversation="diarization")
    assert batch.calls[0][0] == "en-IN"
    with pytest.raises(TranscriptionError):
        analyse_file(wav, "auto", tr, None, conversation="diarization")


def test_single_detected_speaker_is_reported_honestly(tmp_path):
    wav = tmp_path / "solo.wav"
    two_voice_wav(wav)
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c" / "gnani", batch_client=FakeBatch([Seg(0, 30, 0, SCAM_A)]))
    report, _ = analyse_file(wav, "en", tr, None, conversation="diarization")
    assert len(report["speakers"]) == 1 and "Only one speaker" in report["speaker_note"]
    assert report["conversation"]["who"] is None


class ChannelRest:
    def __init__(self):
        self.calls = []

    def transcribe(self, path, language_code, format="verbatim"):
        self.calls.append(str(path))
        return {"transcript": SCAM_A if "ch1" in str(path) else "i will never share my otp with anyone", "model": "fake"}


def test_stereo_channels_are_separated_without_diarization(tmp_path):
    rng = np.random.default_rng(1)
    t = np.arange(16000 * 20) / 16000
    left = (0.3 * np.sin(2 * np.pi * 200 * t) * (1 + rng.normal(0, 0.2, len(t)))).astype("float32")
    right = (0.3 * np.sin(2 * np.pi * 333 * t) * (1 + rng.normal(0, 0.2, len(t)))).astype("float32")
    wav = tmp_path / "stereo.wav"
    sf.write(str(wav), np.stack([left, right], axis=1), 16000)
    rest = ChannelRest()
    tr = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "c" / "gnani", rest_client=rest, batch_client=FakeBatch([]))
    report, _ = analyse_file(wav, "en", tr, AuthenticityScorer(model=AmpModel(), cache_dir=tmp_path / "c" / "auth"), conversation="auto")
    assert report["meta"]["conversation_mode"] == "channels" and len(rest.calls) == 2
    assert report["speakers"][0]["level"] == "high" and report["speakers"][1]["level"] == "low"
    assert "stereo channels" in report["speaker_note"]


# --------------------------------------------------------------------------- web app
def app_client(tmp_path, batch):
    app = create_app(
        data_dir=tmp_path / "data",
        transcriber_factory=lambda c: GnaniTranscriber(api_key="k", cache_dir=c, batch_client=batch),
        scorer_factory=lambda c: AuthenticityScorer(model=AmpModel(), cache_dir=c), serve_frontend=False)
    return TestClient(app)


def test_conversation_flag_through_the_app(tmp_path):
    import time
    wav = tmp_path / "convo.wav"
    two_voice_wav(wav)
    c = app_client(tmp_path, FakeBatch(SEGMENTS))
    send = lambda lang: c.post("/api/analyses", files={"file": ("convo.wav", wav.read_bytes(), "audio/wav")},
                               data={"language": lang, "consent": "true", "conversation": "true"})
    assert send("auto").status_code == 400
    r = send("en")
    assert r.status_code == 202
    for _ in range(100):
        rec = c.get(f"/api/analyses/{r.json()['id']}").json()
        if rec["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert rec["status"] == "done", rec.get("error")
    assert rec["level"] == "high" and len(rec["report"]["speakers"]) == 2
