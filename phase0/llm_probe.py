"""Step 8: can a small LOCAL LLM on CPU extract scam tactics, fast enough and honestly?

Needs Ollama (free, https://ollama.com/download) running locally and at least one model, e.g.
    ollama pull qwen2.5:3b
    ollama pull llama3.2:3b
No audio and no Gnani credits are used: the input is the six reference passages in audio/*.txt.

For each passage the model must return JSON {"tactics":[{"type":..., "quote":...}], "risk":...}.
We then check that every quote really appears in the text (our anti-hallucination rule) and report
tokens/second, so we know how much LLM work a CPU-only live demo can afford.
"""
import argparse
import json
import time
import urllib.error
import urllib.request

from common import AUDIO_DIR, log_result, normalise_text, setup_console

setup_console()
TACTICS = ["authority_claim", "urgency", "otp_request", "pin_or_password_request", "payment_request",
           "remote_access_request", "secrecy", "verification_bypass", "threat", "legitimate_warning"]
PROMPT = """You analyse phone-call transcripts for social-engineering tactics. The transcript may be English,
Hinglish (Hindi in Roman script) or Marathi.
Return ONLY JSON: {{"tactics":[{{"type":<one of {types}>,"quote":<exact words copied from the transcript>}}],
"risk":"low"|"medium"|"high"}}.
Rules: copy quotes exactly, never invent text. If the speaker WARNS people not to share codes, use
"legitimate_warning", not "otp_request". If nothing suspicious, return an empty tactics list and risk "low".

Transcript:
{text}"""

ap = argparse.ArgumentParser()
ap.add_argument("--models", default="qwen2.5:3b", help="comma-separated Ollama model names")
ap.add_argument("--host", default="http://localhost:11434")
ap.add_argument("--max-tokens", type=int, default=250)
args = ap.parse_args()


def generate(model: str, prompt: str) -> dict:
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": "json",
                       "options": {"temperature": 0, "num_predict": args.max_tokens}}).encode()
    req = urllib.request.Request(f"{args.host}/api/generate", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


passages = sorted(AUDIO_DIR.glob("*.txt"))
passages = [p for p in passages if ".alt." not in p.name]
if not passages:
    raise SystemExit("No audio/*.txt reference passages found.")

for model in [m.strip() for m in args.models.split(",") if m.strip()]:
    print(f"\n=== {model} ===")
    for p in passages:
        text = p.read_text(encoding="utf-8").strip()
        try:
            res = generate(model, PROMPT.format(types=" | ".join(TACTICS), text=text))
        except urllib.error.URLError as e:
            raise SystemExit(f"Cannot reach Ollama at {args.host} ({e}). Install/start Ollama, then `ollama pull {model}`.")
        except Exception as e:
            print(f"{p.stem:18s} ERROR {type(e).__name__}: {e}")
            continue
        raw = res.get("response", "")
        tps = res.get("eval_count", 0) / (res.get("eval_duration", 1) / 1e9)
        total = res.get("total_duration", 0) / 1e9
        try:
            data = json.loads(raw)
            valid_json = True
        except json.JSONDecodeError:
            data, valid_json = {}, False
        tactics = data.get("tactics", []) if isinstance(data, dict) else []
        norm_text = " ".join(normalise_text(text))
        quotes = [t.get("quote", "") for t in tactics if isinstance(t, dict)]
        verified = [bool(q) and " ".join(normalise_text(q)) in norm_text for q in quotes]
        types = [t.get("type") for t in tactics if isinstance(t, dict)]
        print(f"{p.stem:18s} json={'ok' if valid_json else 'BAD'} risk={data.get('risk') if valid_json else '-':7} "
              f"quotes verified {sum(verified)}/{len(verified)} | {tps:4.1f} tok/s | {total:5.1f}s | {types}")
        log_result("llm_probe", {"model": model, "passage": p.stem, "valid_json": valid_json, "output": raw,
                                 "types": types, "quotes_verified": sum(verified), "quotes_total": len(verified),
                                 "tokens_per_s": round(tps, 2), "total_s": round(total, 2)})
print("\nLook at the raw outputs in results/llm_probe.jsonl, especially the Marathi and Hinglish ones.")
print("Expected: *_scam passages -> several tactics, high risk; *_benign passages -> 'legitimate_warning' / low risk.")
