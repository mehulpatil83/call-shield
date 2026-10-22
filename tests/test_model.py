import asyncio

import pytest

from core.live import LiveSession
from core.model import ScamModel, combine
from tests.test_live import SCRIPT, FakeStream, pcm


class FakeScam:
    """Stands in for ScamModel: returns a fixed probability."""
    def __init__(self, prob, status="ready"):
        self.prob, self.status, self.calls = prob, status, 0

    def score(self, text):
        self.calls += 1
        return self.prob


def test_combine_never_lowers_and_needs_confidence():
    assert combine("low", None, 50) == ("low", False)
    assert combine("low", 0.80, 50) == ("low", False)
    assert combine("low", 0.90, 50) == ("elevated", True)
    assert combine("low", 0.90, 5) == ("low", False)            # too few words heard
    assert combine("low", 0.97, 50) == ("high", True)
    assert combine("low", 0.97, 10) == ("elevated", True)       # not enough words for high yet
    assert combine("high", 0.0, 50) == ("high", False)          # a low model score never lowers the rules
    assert combine("elevated", 0.99, 50) == ("high", True)
    assert combine("high", 0.99, 50) == ("high", False)


def test_missing_folder_is_unavailable_not_a_crash(tmp_path):
    m = ScamModel(tmp_path / "nope")
    m.load()
    assert m.status == "unavailable" and m.score("hello") is None


def run_session(language, model, texts):
    sent = []

    async def go():
        async def send(msg):
            sent.append(msg)
        stream = FakeStream([(10, texts[0])])
        s = LiveSession(language, lambda code: stream, send, model=model)
        await s.start()
        await s.feed(pcm(0.5))
        await s.stop(settle_seconds=0.2)
        return s
    s = asyncio.run(go())
    return s, [m for m in sent if m["type"] == "analysis"]


BENIGN = "hello how are you doing today I wanted to ask about the lunch plan for tomorrow afternoon with everyone"


def test_model_raises_a_benign_looking_text_and_reports_it():
    s, an = run_session("en", FakeScam(0.97), [BENIGN])
    last = an[-1]
    assert last["level"] == "high" and last["model"]["raised"] is True and last["model"]["status"] == "ready"
    assert last["model"]["prob"] == 0.97 and "language model" in last["summary"]


def test_low_model_score_changes_nothing():
    s, an = run_session("en", FakeScam(0.10), [BENIGN])
    assert an[-1]["level"] == "low" and an[-1]["model"]["raised"] is False


def test_hindi_and_marathi_calls_do_not_use_the_model():
    fake = FakeScam(0.99)
    for lang in ("hi", "mr"):
        s, an = run_session(lang, fake, [BENIGN])
        assert an[-1]["level"] == "low" and an[-1]["model"]["status"] == "off"
    assert fake.calls == 0


def test_unavailable_model_falls_back_to_rules():
    s, an = run_session("en", FakeScam(0.99, status="unavailable"), [BENIGN])
    assert an[-1]["level"] == "low" and an[-1]["model"]["status"] == "unavailable" and an[-1]["model"]["prob"] is None


def test_failing_model_never_breaks_the_call():
    class Boom(FakeScam):
        def score(self, text):
            raise RuntimeError("boom")
    s, an = run_session("en", Boom(0.9), [BENIGN])
    assert an and an[-1]["level"] == "low"


def test_rules_verdict_unchanged_without_model():
    s, an = run_session("en", None, ["this is your bank please share the otp right now or the account will be blocked"])
    assert an[-1]["level"] == "high" and an[-1]["model"]["status"] == "off"


def test_score_passes_only_the_inputs_distilbert_accepts():
    """A saved tokenizer may also return token_type_ids; DistilBERT's forward() rejects them (this crashed on the laptop)."""
    class Out:
        def __init__(self, logits): self.logits = logits

    class FakeTorch:
        class _Ctx:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        def inference_mode(self): return self._Ctx()
        def softmax(self, x, dim): return [0.2, 0.8]

    class Tok:
        def __call__(self, text, **kw):
            return {"input_ids": [1], "attention_mask": [1], "token_type_ids": [0]}

    class Net:
        def __call__(self, input_ids, attention_mask):        # no **kwargs: like the real forward()
            return Out([[0.0, 1.0]])

    m = ScamModel()
    m._tok, m._model, m._torch, m.status = Tok(), Net(), FakeTorch(), "ready"
    assert m.score("hello there friend") == 0.8
