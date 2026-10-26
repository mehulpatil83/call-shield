"""The timestamped call record, the report API and the AI-written summary (with a fake AI service: no network)."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.backend.storage import Store
from core import report_ai
from core.live import LiveSession
from core.session_log import SessionLog, mask_digits
from tests.test_live import SCRIPT, FakeStream, client, pcm, run_call
from tests.test_model import FakeScam


# ------------------------------------------------------------------------------------------ the recorder ----
def test_session_log_basics():
    log = SessionLog("en")
    log.event("call_started", 0.0)
    log.segment("en-IN", "s1", "hello 1234", 2.0)
    log.segment("en-IN", "s1", "hello 1234 there", 3.5)         # the same segment grows: one entry, later last_t
    log.risk_point(1.0, "low", 0, None)
    log.risk_point(1.2, "low", 0, None)                          # nothing changed, too soon: not stored twice
    log.risk_point(4.0, "high", 6, 0.9)
    d = log.to_dict(5.0, "high", "high")
    assert len(d["segments"]) == 1 and d["segments"][0]["text"] == "hello •••• there" and d["segments"][0]["last_t"] == 3.5
    assert [r["level"] for r in d["risk"]] == ["low", "high"] and d["digits_masked"] is True
    assert d["events"][0]["kind"] == "call_started" and "wall" in d["events"][0]
    assert mask_digits("a1b22") == "a•b••"


def make_session(text="this is your bank please share the otp now or your account will be blocked", model=None):
    sent = []

    async def go():
        async def send(m):
            sent.append(m)
        s = LiveSession("en", lambda code: FakeStream([(10, text)]), send, model=model)
        await s.start()
        await s.feed(pcm(0.5))
        s.note("phone_dropped", "connection")
        await s.stop(settle_seconds=0.2)
        return s
    return asyncio.run(go())


def test_live_session_records_the_story_of_the_call():
    s = make_session()
    log = s._result().log
    kinds = [e["kind"] for e in log["events"]]
    assert kinds[0] == "call_started" and "first_words" in kinds and "tactic" in kinds and "alert" in kinds and "phone_dropped" in kinds
    tactics = [e for e in log["events"] if e["kind"] == "tactic"]
    assert any(e["category"] == "otp_request" and "otp" in e["quote"].lower() for e in tactics)
    assert [e["t"] for e in log["events"]] == sorted(e["t"] for e in log["events"])
    assert any(e["kind"] == "level" and e["to"] == "high" and e["source"] == "rules" for e in log["events"])
    assert log["segments"] and log["risk"][-1]["level"] == "high" and log["max_level"] == "high"


def test_model_events_are_recorded_when_the_model_raises():
    s = make_session("hello how are you doing today I wanted to ask about the lunch plan for tomorrow afternoon with everyone",
                     FakeScam(0.97))
    events = s._result().log["events"]
    assert any(e["kind"] == "model" and e["threshold"] == 0.95 for e in events)
    assert any(e["kind"] == "level" and e["source"] == "model" for e in events)


# ------------------------------------------------------------------------------------------------ AI -----
RECORD = {
    "duration": 40.0, "max_level": "high", "digits_masked": True,
    "segments": [{"track": "en-IN", "first_t": 3.0, "last_t": 3.0, "text": "This is your bank. Please read the OTP 12 now."},
                 {"track": "en-IN", "first_t": 12.0, "last_t": 12.0, "text": "Otherwise the account will be blocked today."}],
    "events": [{"i": 0, "t": 0, "wall": "w", "source": "system", "kind": "call_started"},
               {"i": 1, "t": 12.5, "wall": "w", "source": "rules", "kind": "tactic", "category": "otp_request", "quote": "read the OTP 12"},
               {"i": 2, "t": 12.5, "wall": "w", "source": "rules", "kind": "level", "frm": "low", "to": "high", "score": 6.0},
               {"i": 3, "t": 12.5, "wall": "w", "source": "alert", "kind": "alert", "level": "high"}],
}


def good_answer(**over):
    d = {"summary": "The caller asked for a code and threatened to block the account.",
         "what_happened": [{"at": 12.5, "text": "The caller asked for the code."}, {"at": 999, "text": "Impossible time."}],
         "why_risky": ["A code was requested."], "advice": ["Hang up.", "Call the bank on the number on your card."],
         "quotes": ["Please read the OTP", "invented words that were never said"]}
    d.update(over)
    return {"success": True, "result": {"response": json.dumps(d)}}


def configure(monkeypatch):
    for name in ("GROQ_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc123")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok456")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)


def test_not_configured_means_no_ai(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.setattr(report_ai, "_env", lambda name: "")
    assert report_ai.status()["configured"] is False
    with pytest.raises(report_ai.AiError):
        report_ai.generate(RECORD, "en")


def test_facts_sent_to_the_model_hold_no_digits_and_no_audio(monkeypatch):
    configure(monkeypatch)
    facts = report_ai.build_facts(RECORD)
    blob = json.dumps(facts, ensure_ascii=False)
    assert "OTP 12" not in blob and "OTP ••" in facts["transcript"] and "read the OTP ••" in blob      # timestamps keep their digits
    assert "audio" not in blob.lower().replace("audio_", "")
    msgs = report_ai.build_messages(facts, "mr")
    assert "Marathi" in msgs[0]["content"] and "Devanagari" in msgs[0]["content"]


def test_generate_validates_the_answer(monkeypatch):
    configure(monkeypatch)
    seen = {}

    def post(url, key, payload):
        seen.update(url=url, key=key, payload=payload)
        return good_answer()
    out = report_ai.generate(RECORD, "hi", post=post)
    assert "acc123" in seen["url"] and seen["url"].endswith(report_ai.DEFAULT_MODEL) and seen["key"] == "tok456"
    assert out["quotes"] == ["Please read the OTP"] and out["dropped_quotes"] == 1          # the invented quote is removed
    assert out["what_happened"][0]["at"] == 12.5 and out["what_happened"][1]["at"] is None       # an impossible time is dropped
    assert out["lang"] == "hi" and out["advice"]


def test_answer_parsing_is_forgiving_but_strict_about_use(monkeypatch):
    fenced = "<think>hmm</think>```json\n" + json.dumps({"summary": "ok", "advice": ["a"]}) + "\n```"
    assert report_ai.parse(fenced, RECORD)["summary"] == "ok"
    for bad in ("no json here", "{}", '{"summary": ""}', "{broken"):
        with pytest.raises(report_ai.AiError):
            report_ai.parse(bad, RECORD)
    openai_style = {"choices": [{"message": {"content": "x"}}]}
    assert report_ai._extract(openai_style) == "x"
    with pytest.raises(report_ai.AiError):
        report_ai._extract({"result": {}})


# ----------------------------------------------------------------------------------------------- the API ---
def test_live_call_saves_a_timeline_and_the_api_serves_it(tmp_path):
    FakeStream.instances.clear()
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    ended = run_call(c)[-1]
    got = c.get(f"/api/analyses/{ended['id']}/session").json()
    kinds = {e["kind"] for e in got["session"]["events"]}
    assert {"call_started", "tactic", "alert", "level", "voice_check"} <= kinds
    assert got["session"]["id"] == ended["id"] and got["ai_status"]["configured"] in (True, False) and "key" not in json.dumps(got["ai_status"])
    assert c.get("/api/analyses/aaaaaaaaaaaa/session").status_code == 404
    assert c.delete(f"/api/analyses/{ended['id']}").status_code == 200
    assert c.get(f"/api/analyses/{ended['id']}/session").status_code == 404
    assert not list((tmp_path / "data" / "reports").glob(f"{ended['id']}.*"))


def test_ai_endpoint_needs_consent_caches_and_handles_errors(tmp_path, monkeypatch):
    configure(monkeypatch)
    FakeStream.instances.clear()
    c = client(tmp_path, lambda code: FakeStream(SCRIPT))
    sid = run_call(c)[-1]["id"]
    url = f"/api/analyses/{sid}/ai"
    assert c.post(url, json={"lang": "en"}).status_code == 400                       # no consent
    assert c.post(url, json={"lang": "xx", "consent": True}).status_code == 400
    calls = []

    def post(u, k, p):
        calls.append(1)
        return good_answer()
    monkeypatch.setattr(report_ai, "_post", post)
    first = c.post(url, json={"lang": "mr", "consent": True})
    assert first.status_code == 200 and first.json()["cached"] is False and first.json()["ai"]["lang"] == "mr"
    again = c.post(url, json={"lang": "mr", "consent": True}).json()
    assert again["cached"] is True and len(calls) == 1                              # cached: no second request
    c.post(url, json={"lang": "mr", "consent": True, "force": True})
    assert len(calls) == 2
    assert c.get(f"/api/analyses/{sid}/session").json()["ai"]["mr"]["summary"]

    def boom(u, k, p):
        raise report_ai.AiError("The free daily allowance of the AI service may be used up. Try again later.")
    monkeypatch.setattr(report_ai, "_post", boom)
    r = c.post(url, json={"lang": "en", "consent": True})
    assert r.status_code == 503 and "allowance" in r.json()["detail"]


def test_the_connection_check_uses_a_fictional_call_and_works_with_a_fake_service(monkeypatch, capsys):
    configure(monkeypatch)
    monkeypatch.setattr(report_ai, "_post", lambda u, k, p: good_answer(quotes=["read out the code"]))
    monkeypatch.setattr("sys.argv", ["report_ai", "--lang", "hi"])
    assert report_ai.main() == 0
    out = capsys.readouterr().out
    assert "fictional sample call" in out and '"lang": "hi"' in out and "tok456" not in out


# ------------------------------------------------------------------------------------------------ Groq -----
MODELS = [{"id": "llama-3.3-70b-versatile", "active": True}, {"id": "qwen/qwen3-32b"}, {"id": "openai/gpt-oss-120b"},
          {"id": "whisper-large-v3"}, {"id": "meta-llama/llama-guard-4-12b"}, {"id": "groq/compound"}, {"id": "old-model", "active": False}]
HINDI = "फोन करने वाले ने कोड माँगा और खाता बंद करने की धमकी दी।"


def gq_answer(model, summary="The caller asked for a code and threatened to block the account."):
    body = {"summary": summary, "what_happened": [], "why_risky": ["x"], "advice": ["Hang up."], "quotes": []}
    return {"model": model, "choices": [{"message": {"content": json.dumps(body, ensure_ascii=False)}, "finish_reason": "stop"}]}


def gq_env(monkeypatch, preferred="", models=MODELS):
    for name in ("LLM_PROVIDER", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gqkey")
    if preferred:
        monkeypatch.setenv("LLM_MODEL", preferred)
    else:
        monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setattr(report_ai, "_models_list", lambda s: models)


def test_groq_is_picked_from_the_key_and_the_key_is_never_reported(monkeypatch):
    gq_env(monkeypatch)
    st = report_ai.status()
    assert st["configured"] and st["provider"] == "groq" and "auto" in st["model"] and "gqkey" not in json.dumps(st)
    assert report_ai.settings()["url"] == "https://api.groq.com/openai/v1/chat/completions"


def test_only_chat_models_are_chosen_known_good_ones_first(monkeypatch):
    assert report_ai.candidates("", MODELS) == ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3-32b"]       # no whisper, guard, compound, inactive
    assert report_ai.candidates("my/model", MODELS)[0] == "my/model" and len(report_ai.candidates("my/model", MODELS)) == report_ai.MAX_ATTEMPTS
    assert report_ai.candidates("", [])[0] == "llama-3.3-70b-versatile"                    # no list: the known models are tried blindly


def test_an_unavailable_or_limited_model_falls_through_to_the_next_one(monkeypatch):
    gq_env(monkeypatch)
    seen = []

    def post(url, key, payload):
        seen.append(payload["model"])
        if len(seen) == 1:
            raise report_ai.AiHttpError("x", 429, "Rate limit reached for model llama-3.3-70b-versatile on requests per day (RPD)")
        if len(seen) == 2:
            raise report_ai.AiHttpError("x", 400, "The model has been decommissioned")
        return gq_answer(payload["model"])
    out = report_ai.generate(RECORD, "en", post=post)
    assert out["model"] == seen[2] == "qwen/qwen3-32b" and out["provider"] == "groq"
    assert [a["result"] for a in out["attempts"]] == ["rate limited", "request refused", "ok"]


def test_a_rejected_key_stops_at_once(monkeypatch):
    gq_env(monkeypatch)
    calls = []

    def post(url, key, payload):
        calls.append(1)
        raise report_ai.AiFatal("The AI service rejected the key.")
    with pytest.raises(report_ai.AiFatal):
        report_ai.generate(RECORD, "en", post=post)
    assert len(calls) == 1


def test_a_model_answering_in_the_wrong_language_or_with_garbage_is_skipped(monkeypatch):
    gq_env(monkeypatch)
    n = []

    def post(url, key, payload):
        n.append(payload["model"])
        if len(n) == 1:
            return gq_answer(payload["model"])                                              # English, but Hindi was asked for
        if len(n) == 2:
            return {"choices": [{"message": {"content": "User Safety: safe"}, "finish_reason": "stop"}]}      # not a report
        return gq_answer(payload["model"], HINDI)
    out = report_ai.generate(RECORD, "hi", post=post)
    assert out["summary"] == HINDI and [a["result"] for a in out["attempts"]] == ["wrong language", "unusable answer", "ok"]
    assert report_ai._lang_ok(HINDI, "mr") and not report_ai._lang_ok(HINDI, "en") and report_ai._lang_ok("The caller asked for a code now.", "en")


def test_when_every_model_fails_the_message_is_clear_and_the_tries_are_limited(monkeypatch):
    gq_env(monkeypatch)
    n = []

    def post(url, key, payload):
        n.append(1)
        raise report_ai.AiHttpError("x", 503, "over capacity")
    with pytest.raises(report_ai.AiAllFailed) as e:
        report_ai.generate(RECORD, "en", post=post)
    assert "No model could write" in str(e.value) and "overloaded x3" in str(e.value) and len(n) == report_ai.MAX_ATTEMPTS
    assert len(e.value.attempts) == 3 and "over capacity" in e.value.attempts[0]["detail"]


def test_the_check_tool_gets_a_sample_of_every_rejected_answer(monkeypatch):
    gq_env(monkeypatch)
    with pytest.raises(report_ai.AiAllFailed) as e:
        report_ai.generate(RECORD, "en", post=lambda u, k, p: {"choices": [{"message": {"content": "Let me think about it first..."}, "finish_reason": "length"}]})
    d = e.value.attempts[0]["detail"]
    assert "finish=length" in d and "Let me think" in d


def test_reasoning_models_get_a_short_reasoning_setting_and_the_system_message_is_kept(monkeypatch):
    gq_env(monkeypatch, preferred="openai/gpt-oss-120b")
    seen = []
    report_ai.generate(RECORD, "en", post=lambda u, k, p: (seen.append(p), gq_answer("openai/gpt-oss-120b"))[1])
    assert seen[0]["reasoning_effort"] == "low" and seen[0]["messages"][0]["role"] == "system" and seen[0]["messages"][1]["role"] == "user"
    assert report_ai._extra_params("qwen/qwen3-32b") == {"reasoning_format": "hidden"} and report_ai._extra_params("llama-3.3-70b-versatile") == {}


def test_parsing_survives_prose_around_the_json_and_a_cut_off_answer():
    obj = json.dumps({"summary": "The caller asked for a code.", "advice": ["Hang up."]})
    wrapped = "Sure! Here is the report {as requested}:\n```json\n" + obj + "\n```\nHope that helps {really}."
    assert report_ai.parse(wrapped, RECORD)["advice"] == ["Hang up."]
    cut = '{"summary": "The caller asked for a code and made a threat.", "what_happened": [{"at": 12, "te'
    out = report_ai.parse(cut, RECORD)
    assert out["summary"].startswith("The caller asked") and out["advice"] == []                # the summary is rescued
    with pytest.raises(report_ai.AiUnusable) as e:
        report_ai.parse("I cannot help with that.", RECORD)
    assert e.value.sample.startswith("I cannot")
    parts = {"choices": [{"message": {"content": [{"type": "text", "text": "{\"summary\": \"ok\"}"}]}}]}
    assert report_ai._extract(parts) == "{\"summary\": \"ok\"}"
    with pytest.raises(report_ai.AiError, match="reasoning"):
        report_ai._extract({"choices": [{"message": {"content": None, "reasoning": "thinking..."}}]})
    system = report_ai.build_messages(report_ai.build_facts(RECORD), "en")[0]["content"]
    assert "no text before or after it" in system and "Do NOT mention phone numbers" in system and "rest on a tactic" in system and "not mention call-shield" in system


def test_the_connection_check_uses_a_fictional_call_and_works_with_a_fake_service(monkeypatch, capsys):
    gq_env(monkeypatch)
    monkeypatch.setattr(report_ai, "_post", lambda u, k, p: gq_answer("llama-3.3-70b-versatile"))
    monkeypatch.setattr("sys.argv", ["report_ai", "--lang", "en"])
    assert report_ai.main() == 0
    out = capsys.readouterr().out
    assert "fictional sample call" in out and "llama-3.3-70b-versatile" in out and "gqkey" not in out
