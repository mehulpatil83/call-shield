"""After-call report written by an open-source language model hosted online.

Default provider: Groq (free tier, no card; open models such as Llama 3.3 70B, GPT-OSS and Qwen3 behind an OpenAI-compatible API).
The app asks Groq which chat models it currently serves and tries a few in order: your preferred model (LLM_MODEL, optional), then a
fixed list of good multilingual open models, then any other chat model. If one is unavailable, rate-limited, returns garbage or answers
in the wrong language, the next is tried. A rejected key stops at once with a clear message.
Cloudflare Workers AI and any OpenAI-compatible service also work (see docs/REPORT_AI.md).

What it may do: write the story of the call (summary, what happened, why it looked risky, advice) in the chosen language.
What it may NOT do: change the verdict, the timeline or the quoted evidence, which all come from the rules and the call record.
What leaves this machine: text only. The call's transcript with every digit masked, the times and the tactic quotes. Never audio.
It happens only when the person presses the button (or has turned on the automatic option). Quotes in the answer are checked
against the transcript and dropped if they are not really in it. Without a key the report page shows the built-in summary."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

from . import config
from .session_log import mask_digits

LANG_NAMES = {"en": "English", "hi": "Hindi, written in Devanagari script", "mr": "Marathi, written in Devanagari script"}
DEFAULT_MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"          # Cloudflare only
GROQ = "https://api.groq.com/openai/v1"
PREFERRED = ("llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3-32b", "meta-llama/llama-4-scout-17b-16e-instruct", "openai/gpt-oss-20b")
MAX_ATTEMPTS = max(1, min(6, int(os.getenv("LLM_MAX_ATTEMPTS", "3") or 3)))        # limits are per model, so a few fallbacks are cheap
FAMILIES = ("gemma", "qwen", "llama", "gpt-oss", "mistral", "deepseek", "nemotron")     # best multilingual first (a guess; the answer shows the model used)
MAX_TRANSCRIPT_CHARS = 4000
TIMEOUT = 60


class AiError(Exception):
    """A message that is safe and useful to show to the person."""


def _env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if v:
        return v
    try:
        from dotenv import load_dotenv
    except ImportError:
        return ""
    for f in config.ENV_FILES:
        if f.exists():
            load_dotenv(f)
            v = os.getenv(name, "").strip()
            if v:
                return v
    return ""


class AiHttpError(AiError):
    def __init__(self, message: str, status: int = 0, detail: str = ""):
        super().__init__(message)
        self.status, self.detail = status, detail


class AiAllFailed(AiError):
    """Every free model failed; `attempts` says why (model, short reason, detail) for the connection-check tool."""
    def __init__(self, message: str, attempts: list[dict]):
        super().__init__(message)
        self.attempts = attempts


class AiUnusable(AiError):
    def __init__(self, message: str, sample: str = ""):
        super().__init__(message)
        self.sample = sample


class AiFatal(AiError):
    """Trying another model would not help (bad key, no credit, daily limit)."""


def settings() -> dict | None:
    provider = (_env("LLM_PROVIDER") or "").lower()
    model = _env("LLM_MODEL")
    gkey, acc, tok = _env("GROQ_API_KEY"), _env("CLOUDFLARE_ACCOUNT_ID"), _env("CLOUDFLARE_API_TOKEN")
    if not provider:
        provider = "groq" if gkey else "cloudflare" if acc and tok else "openai"
    if provider == "groq":
        if not gkey or "your-" in gkey:
            return None
        return {"provider": "groq", "model": model, "base": GROQ, "url": f"{GROQ}/chat/completions", "key": gkey,
                "sends_to": "Groq (open models hosted by Groq)"}
    if provider == "cloudflare":
        if not acc or not tok or "your-" in acc + tok:
            return None
        model = model or DEFAULT_MODEL
        return {"provider": "cloudflare", "model": model, "url": f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}",
                "key": tok, "sends_to": "Cloudflare Workers AI"}
    base, key = _env("LLM_BASE_URL").rstrip("/"), _env("LLM_API_KEY")
    if not base or not key or "your-" in key:
        return None
    return {"provider": "openai", "model": model, "base": base, "url": f"{base}/chat/completions", "key": key,
            "sends_to": re.sub(r"^https?://([^/]+).*$", r"\1", base)}


def status() -> dict:
    s = settings()
    return {"configured": s is not None, "provider": s["provider"] if s else None,
            "model": (s["model"] or "auto (best available open model)") if s else None, "sends_to": s["sends_to"] if s else None}


# ---------------------------------------------------------------------------------------------- the facts -----
def _mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def primary_track(session: dict) -> str | None:
    by: dict[str, int] = {}
    for s in session.get("segments", []):
        by[s["track"]] = by.get(s["track"], 0) + len(s["text"])
    if not by:
        return None
    return "en-IN" if "en-IN" in by else max(by, key=by.get)


def transcript_text(session: dict) -> str:
    """One transcript (digits already masked in the record), as timestamped lines, shortened if long."""
    tr = primary_track(session)
    lines = [f"[{_mmss(s['first_t'])}] {mask_digits(s['text'])}" for s in session.get("segments", []) if s["track"] == tr]
    text = "\n".join(lines)
    if len(text) > MAX_TRANSCRIPT_CHARS:
        text = text[:1500] + "\n[... middle of the call left out ...]\n" + text[-2500:]
    return text


def build_facts(session: dict) -> dict:
    ev = session.get("events", [])
    tactics, seen = [], set()
    for e in ev:
        if e["kind"] == "tactic" and (e["category"], e["quote"].casefold()) not in seen:
            seen.add((e["category"], e["quote"].casefold()))
            tactics.append({"at": e["t"], "type": e["category"], "words": mask_digits(e["quote"])})
    model_marks = [{"at": e["t"], "probability": e["prob"]} for e in ev if e["kind"] == "model"]
    return {
        "duration_seconds": session.get("duration", 0), "highest_level": session.get("max_level", "low"),
        "risk_changes": [{"at": e["t"], "to": e["to"], "by": e["source"]} for e in ev if e["kind"] == "level"],
        "alerts": [{"at": e["t"], "level": e["level"]} for e in ev if e["kind"] == "alert"],
        "tactics_heard": tactics[:14], "language_model_second_opinion": model_marks[:2], "transcript": transcript_text(session),
    }


def build_messages(facts: dict, lang: str) -> list[dict]:
    name = LANG_NAMES[lang]
    system = (
        "You write the after-call report for call-shield, a tool that warns people about scam phone calls. "
        f"Write every text field in {name}. Use ONLY the facts and the transcript given. Never invent names, organisations, "
        "amounts, numbers or events. If something is unclear, say it is unclear. Do not claim the call is certainly a scam: "
        "describe what the signals show and what the person should do. Spoken digits were hidden on purpose; do not guess them. "
        "Mention only what is written in the facts or the transcript. Do NOT mention phone numbers, caller ID, whether the number was known "
        "or unknown, whether identity was checked or offered, the caller's voice or accent, or what the person answered, unless it is written there. "
        "Every item in why_risky must rest on a tactic in tactics_heard or a risk change, in plain words. The advice must be general safety "
        "steps (hang up, never share codes or passwords, call the bank on the number printed on the card or on its official website) and must "
        "not mention call-shield or any app. "
        "Reply with ONE JSON object and nothing else: no thinking out loud, no text before or after it, no code fence. Exactly these keys: "
        '"summary" (2-4 sentences), "what_happened" (list of up to 6 objects {"at": seconds as a number taken from the facts, '
        '"text": one sentence}), "why_risky" (list of up to 4 short strings), "advice" (list of 3-5 short, concrete strings), '
        '"quotes" (list of up to 4 short phrases copied EXACTLY, letter for letter, from the transcript; they stay in the language spoken).')
    user = "Facts and transcript of the call:\n" + json.dumps(facts, ensure_ascii=False, indent=1)
    cfg = settings() or {}
    if cfg.get("provider") == "cloudflare" and "qwen3" in cfg.get("model", "").lower():
        user += "\n/no_think"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------------------------------------------------------------------------------------- the answer ----
def _norm(s: str) -> str:
    return re.sub(r"[\s.,!?;:\"'()\[\]\-–—]+", " ", s.casefold()).strip()


def _extract(data: dict) -> str:
    r = data.get("result", data) if isinstance(data, dict) else {}
    if isinstance(r, dict):
        if isinstance(r.get("response"), str):
            return r["response"]
        for ch in r.get("choices") or []:
            msg = ch.get("message") or {}
            if isinstance(msg.get("content"), str) and msg["content"].strip():
                return msg["content"]
            if isinstance(msg.get("content"), list):                      # some providers return parts
                joined = "".join(p.get("text", "") for p in msg["content"] if isinstance(p, dict))
                if joined.strip():
                    return joined
            if msg.get("reasoning") and not msg.get("content"):
                raise AiError("The model only wrote its reasoning and no answer.")
            if isinstance(ch.get("text"), str):
                return ch["text"]
    raise AiError("The AI service answered in a format this app does not understand.")


def _json_object(text: str) -> dict | None:
    """The first JSON object in the text that has a "summary" (models often write a sentence or a code fence around it)."""
    dec, fallback = json.JSONDecoder(), None
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text[m.start():])
        except ValueError:
            continue
        if isinstance(obj, dict):
            if "summary" in obj:
                return obj
            fallback = fallback or obj
    return fallback


def parse(text: str, session: dict) -> dict:
    """Turn the model's text into a validated report; anything that is not supported by the record is dropped."""
    sample = text[:200]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    raw = _json_object(text)
    if raw is None:                                            # cut off or broken JSON: rescue at least the summary
        m = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.S)
        if m:
            try:
                raw = {"summary": json.loads('"' + m.group(1) + '"')}
            except ValueError:
                raw = None
    if not isinstance(raw, dict) or not isinstance(raw.get("summary"), str) or not raw["summary"].strip():
        raise AiUnusable("The AI model did not return a usable report. Try again.", sample)
    dur = float(session.get("duration", 0))
    strs = lambda v, n: [x.strip()[:300] for x in (v if isinstance(v, list) else []) if isinstance(x, str) and x.strip()][:n]
    steps = []
    for x in (raw.get("what_happened") if isinstance(raw.get("what_happened"), list) else [])[:6]:
        if isinstance(x, dict) and isinstance(x.get("text"), str) and x["text"].strip():
            at = x.get("at")
            at = round(float(at), 1) if isinstance(at, (int, float)) and 0 <= at <= dur + 1 else None
            steps.append({"at": at, "text": x["text"].strip()[:300]})
    haystack = _norm(" ".join(s["text"] for s in session.get("segments", [])))
    quotes = strs(raw.get("quotes"), 8)
    good = [q for q in quotes if _norm(mask_digits(q)) and _norm(mask_digits(q)) in haystack][:4]
    return {"summary": raw["summary"].strip()[:900], "what_happened": steps, "why_risky": strs(raw.get("why_risky"), 4),
            "advice": strs(raw.get("advice"), 5), "quotes": good, "dropped_quotes": len(quotes) - len(good)}


def _post(url: str, key: str, payload: dict) -> dict:
    import httpx
    try:
        r = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT)
    except httpx.HTTPError:
        raise AiHttpError("Could not reach the AI service. Check the internet connection.", 0, "network") from None
    if r.status_code in (401, 403):
        raise AiFatal("The AI service rejected the key. Check the key and its permissions in .env.")
    if r.status_code >= 400:
        text = r.text[:600]
        msg = ("The free allowance of the AI service may be used up. Try again later." if r.status_code == 429
               else f"The AI service returned an error ({r.status_code}).")
        raise AiHttpError(msg, r.status_code, text)
    try:
        return r.json()
    except ValueError:
        raise AiHttpError("The AI service returned something that is not JSON.", 200, "not json") from None


# --------------------------------------------------------------------------------------------- model choice -----
_MODELS_CACHE: dict = {"data": None, "at": 0.0}
_SKIP = ("whisper", "guard", "tts", "orpheus", "embed", "compound", "playai", "safeguard", "moderation", "transcribe")


def _models_list(s: dict) -> list[dict]:
    """The chat models the service currently serves (cached ten minutes). [] if the list cannot be fetched."""
    import time
    import httpx
    now = time.time()
    if _MODELS_CACHE["data"] is not None and now - _MODELS_CACHE["at"] < 600:
        return _MODELS_CACHE["data"]
    try:
        r = httpx.get(f"{s['base']}/models", headers={"Authorization": f"Bearer {s['key']}"}, timeout=20)
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception:
        return []
    _MODELS_CACHE.update(data=data, at=now)
    return data


def candidates(preferred: str, models: list[dict]) -> list[str]:
    """Models to try, in order: the preferred one, then the known good multilingual open models that exist, then any other chat model."""
    ids = [str(m.get("id", "")) for m in models if m.get("active", True) is not False]
    ids = [i for i in ids if i and not any(x in i.lower() for x in _SKIP)]
    if not ids:                                                          # list unavailable: try the known models blindly
        ids = list(PREFERRED)
    def rank(i: str):
        fam = next((k for k, f in enumerate(FAMILIES) if f in i.lower()), len(FAMILIES))
        size = re.search(r"(\d+(?:\.\d+)?)b", i.lower())
        return (fam, -(float(size.group(1)) if size else 0.0), i)
    order = ([preferred.strip()] if preferred.strip() else []) + [p for p in PREFERRED if p in ids] + sorted(ids, key=rank)
    seen: list[str] = []
    for i in order:
        if i not in seen:
            seen.append(i)
    return seen[:MAX_ATTEMPTS]


def _lang_ok(text: str, lang: str) -> bool:
    """The summary must really be in the chosen language (small models often answer in English or Chinese)."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 8:
        return False
    deva = sum("\u0900" <= c <= "\u097f" for c in letters) / len(letters)
    latin = sum(c.isascii() for c in letters) / len(letters)
    return deva >= 0.5 if lang in ("hi", "mr") else latin >= 0.7


def _why(e: AiError) -> str:
    st = getattr(e, "status", 0)
    return {429: "rate limited", 404: "not available", 400: "request refused", 503: "overloaded"}.get(st) or ("no answer in time" if st == 0 else "error") \
        if isinstance(e, AiHttpError) else "unusable answer"


def _finish(data) -> str:
    try:
        return str(data["choices"][0].get("finish_reason"))
    except Exception:
        return "?"


def _extra_params(model: str) -> dict:
    """Small per-model switches that keep reasoning models short and their reasoning out of the answer."""
    m = model.lower()
    if "gpt-oss" in m:
        return {"reasoning_effort": "low"}
    if "qwen3" in m:
        return {"reasoning_format": "hidden"}
    return {}


def _generate_pool(session: dict, lang: str, s: dict, msgs: list[dict], post) -> dict:
    cands = candidates(s["model"], _models_list(s))
    attempts: list[dict] = []
    for cand in cands:
        payload = {"model": cand, "messages": msgs, "max_tokens": 2000, "temperature": 0.1, **_extra_params(cand)}
        try:
            data = post(s["url"], s["key"], payload)
        except AiFatal:
            raise
        except AiHttpError as e:
            attempts.append({"model": cand, "result": _why(e), "status": e.status, "detail": e.detail[:240]})
            continue
        try:
            out = parse(_extract(data), session)
            if not _lang_ok(out["summary"], lang):
                raise AiError("wrong language: " + out["summary"][:80])
        except AiError as e:
            sample = getattr(e, "sample", "")
            attempts.append({"model": cand, "result": "wrong language" if "language" in str(e) else "unusable answer", "status": 200,
                             "detail": f"{str(e)[:120]} | finish={_finish(data)} | starts with: {sample[:160]!r}"})
            continue
        used = (data.get("model") if isinstance(data, dict) else None) or cand
        attempts.append({"model": used, "result": "ok"})
        out.update({"lang": lang, "model": used, "provider": s["provider"], "attempts": [{"model": a["model"], "result": a["result"]} for a in attempts],
                    "made_at": datetime.now().isoformat(timespec="seconds")})
        return out
    counts: dict[str, int] = {}
    for a in attempts:
        counts[a["result"]] = counts.get(a["result"], 0) + 1
    why = ", ".join(f"{k} x{v}" for k, v in counts.items())
    raise AiAllFailed(f"No model could write the summary right now ({len(attempts)} tried: {why}). Try again in a few minutes.", attempts)


def generate(session: dict, lang: str, post=None) -> dict:
    s = settings()
    if s is None:
        raise AiError("No AI service is set up. Add the key to .env (see docs/REPORT_AI.md).")
    if lang not in LANG_NAMES:
        raise AiError("Unknown language.")
    if not session.get("segments"):
        raise AiError("There is no transcript to write about.")
    msgs = build_messages(build_facts(session), lang)
    if s["provider"] in ("groq", "openai") and (s["provider"] == "groq" or not s["model"]):
        return _generate_pool(session, lang, s, msgs, post or _post)
    payload = {"messages": msgs, "max_tokens": 1400, "temperature": 0.1}
    if s["provider"] == "openai":
        payload["model"] = s["model"]
    data = (post or _post)(s["url"], s["key"], payload)
    if isinstance(data, dict) and data.get("success") is False:
        raise AiError("The AI service refused the request.")
    out = parse(_extract(data), session)
    out.update({"lang": lang, "model": s["model"], "provider": s["provider"], "made_at": datetime.now().isoformat(timespec="seconds"),
                "attempts": [{"model": s["model"], "result": "ok"}]})
    return out


def sample_session() -> dict:
    """A tiny FICTIONAL call, used only to test the connection to the AI service."""
    return {"duration": 30.0, "max_level": "high", "digits_masked": True,
            "segments": [{"track": "en-IN", "first_t": 2.0, "last_t": 2.0, "text": "Hello this is the bank security department."},
                         {"track": "en-IN", "first_t": 9.0, "last_t": 9.0, "text": "Please read out the code we sent you right now, otherwise your account will be blocked."}],
            "events": [{"i": 0, "t": 9.4, "wall": "", "source": "rules", "kind": "tactic", "category": "otp_request", "quote": "read out the code"},
                       {"i": 1, "t": 9.4, "wall": "", "source": "rules", "kind": "level", "frm": "low", "to": "high", "score": 6.0},
                       {"i": 2, "t": 9.4, "wall": "", "source": "alert", "kind": "alert", "level": "high"}]}


def main() -> int:
    """python -m core.report_ai --lang mr : checks the keys and shows what the model writes for a fictional call."""
    import argparse
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en", choices=sorted(LANG_NAMES))
    a = ap.parse_args()
    st = status()
    if not st["configured"]:
        print("No AI service is set up. Add GROQ_API_KEY to .env (see docs/REPORT_AI.md).")
        return 1
    print(f"Using {st['model']} via {st['sends_to']} (only the fictional sample call is sent)...")
    if st["provider"] in ("groq", "openai") and not (settings() or {}).get("model"):
        names = candidates("", _models_list(settings()))
        print(f"Models I will try, in this order: {names}")
    t0 = time.time()
    try:
        out = generate(sample_session(), a.lang)
    except AiAllFailed as e:
        print("Failed:", e, "\nWhat happened with each model:")
        for a in e.attempts:
            print(f"  {a['model']}: {a['result']} (HTTP {a.get('status')}) {a.get('detail', '')}")
        return 1
    except AiError as e:
        print("Failed:", e)
        return 1
    print(f"Answered in {time.time() - t0:.1f}s\n")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
