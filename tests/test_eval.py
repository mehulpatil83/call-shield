import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf

from core.authenticity import AuthenticityScorer
from core.gnani_client import GnaniTranscriber
from eval.make_report import load, to_markdown
from eval.manifest import scan
from eval.metrics import auc, best_wer, summarise, wer, wilson
from eval.run_eval import run_eval
from eval.scripts_bank import SCRIPTS


def wav(path: Path, amp: float, seconds=22, sr=16000):
    # a different tone per file name, otherwise identical audio would share one cache entry (as it should)
    freq = 150 + (sum(map(ord, path.stem)) % 300)
    t = np.arange(int(sr * seconds)) / sr
    sf.write(str(path), (amp * np.sin(2 * np.pi * freq * t) * (1 + np.sin(2 * np.pi * 3 * t)) / 2).astype("float32"), sr)


class ByNameRest:
    """Fake Gnani: the transcript depends on the file name, so we control exactly what the 'speech-to-text' returns."""
    def __init__(self, table):
        self.table = table

    def transcribe(self, path, language_code, format="verbatim"):
        stem = Path(path).stem.split("__")[0]
        return {"transcript": self.table.get(stem, ""), "model": "fake"}


class AmpModel:
    """Fake audio model: quiet files look synthetic (low score), louder ones natural."""
    def score_batch(self, audios, srs):
        return [-8.0 if float(np.mean(np.abs(a))) < 0.05 else -3.0 for a in audios]


SCAM = "please share the otp right now or your account will be blocked, I am calling from your bank security department"
BENIGN = "hello this is a reminder, we will never ask for your otp, hang up and call the number on your card"


def build(tmp_path):
    rec = tmp_path / "rec"
    rec.mkdir()
    table = {}
    for name, amp, text in [("p1_en-s1", 0.4, SCAM), ("p2_en-s1", 0.4, SCAM), ("p1_en-s2", 0.4, SCAM), ("p2_en-s2", 0.4, "hello how are you today"),
                            ("p1_en-b1", 0.4, BENIGN), ("p2_en-b1", 0.4, BENIGN), ("p1_en-b2", 0.4, BENIGN), ("p2_en-b2", 0.4, "please share otp right now your account blocked"),
                            ("ai_en-s1_syn", 0.04, SCAM), ("ai_en-b1_syn", 0.04, BENIGN)]:
        wav(rec / f"{name}.wav", amp)
        table[name] = text
    return rec, table


def test_manifest_reads_names_and_labels(tmp_path):
    rec, _ = build(tmp_path)
    (rec / "notes.txt").write_text("x")
    wav(rec / "bad name.wav", 0.2)
    wav(rec / "p3_zz-s9.wav", 0.2)
    items, skipped = scan(rec)
    assert len(items) == 10 and {n for n, _ in skipped} == {"bad name.wav", "p3_zz-s9.wav"}
    by = {i.path.stem: i for i in items}
    assert by["p1_en-s1"].label == "scam" and by["p1_en-s1"].split == "dev" and by["p1_en-s1"].voice == "real"
    assert by["ai_en-s1_syn"].voice == "synthetic" and by["p1_en-b2"].hard


def test_scripts_bank_is_balanced_and_split():
    assert len(SCRIPTS) == 24
    for lang in ("en", "hinglish", "mr"):
        for split in ("dev", "test"):
            labels = [s["label"] for s in SCRIPTS.values() if s["language"] == lang and s["split"] == split]
            assert labels.count("scam") == 2 and labels.count("benign") == 2
    assert sum(s["hard"] for s in SCRIPTS.values()) == 6


def test_metrics_helpers():
    p, lo, hi = wilson(7, 8)
    assert abs(p - 0.875) < 1e-9 and 0.5 < lo < p < hi <= 1
    assert wilson(0, 0) == (None, None, None)
    a, lo, hi = auc([-3, -2, -4], [-8, -9, -7])
    assert a == 1.0 and lo == 1.0
    assert auc([1, 2], []) == (None, None, None)
    assert wer("a b c d", "a b x d") == 0.25 and best_wer("a b", ["", "a b"]) == 0.0


def test_full_evaluation_run_and_report(tmp_path):
    rec, table = build(tmp_path)
    items = [i for i in scan(rec)[0] if i.split == "dev"]
    out = tmp_path / "out"
    transcriber = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "gc", rest_client=ByNameRest(table))
    scorer = AuthenticityScorer(model=AmpModel(), cache_dir=tmp_path / "ac")
    records = run_eval(items, ["orig", "tel8k"], out, transcriber, scorer, work_dir=tmp_path / "work", log=lambda *_: None)
    assert len(records) == len(items) * 2 and not any(r.get("error") for r in records)
    s = summarise(records)
    allrow = next(r for r in s["conversation"] if r["group"] == "all")
    # scams: p1_en-s1, p2_en-s1, p1_en-s2, ai_en-s1_syn caught; p2_en-s2 ('hello how are you') missed -> 4 of 5 per condition
    assert allrow["recall_high"]["k"] == 8 and allrow["recall_high"]["n"] == 10
    # benign: the one wrongly flagged (p2_en-b2) is a false alarm
    assert allrow["false_alarm_any"]["k"] == 2 and allrow["false_alarm_any"]["n"] == 10
    fails = {(f["file"]) for f in s["failures"]}
    assert "p2_en-s2.wav" in fails and "p2_en-b2.wav" in fails
    a = s["authenticity"]
    aucs = {r["condition"]: r["auc"] for r in a["auc"]}
    assert aucs["orig"] == 1.0 and a["phone_shift"]["n"] > 0
    # resume: a second run does nothing and adds no records
    again = run_eval(items, ["orig", "tel8k"], out, transcriber, scorer, work_dir=tmp_path / "work", log=lambda *_: None)
    assert len(again) == len(records) == len((out / "records.jsonl").read_text().splitlines())
    md = to_markdown(s, {"split": "dev", "lexicon_hash": "abc"})
    assert "Evaluation summary" in md and "fewer than 3 real speakers" in md and "AUC" in md


def test_errors_are_recorded_not_fatal(tmp_path):
    rec, table = build(tmp_path)
    items = scan(rec)[0][:2]
    transcriber = GnaniTranscriber(api_key="k", cache_dir=tmp_path / "gc", rest_client=ByNameRest({}))   # no transcripts at all
    records = run_eval(items, ["orig"], tmp_path / "out", transcriber, None, work_dir=tmp_path / "w", log=lambda *_: None)
    assert all("error" in r for r in records)
    assert summarise(records)["n_errors"] == 2
