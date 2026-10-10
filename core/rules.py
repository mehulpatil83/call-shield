"""Explainable social-engineering detector. No model, no randomness: every alert quotes the transcript.

Levels
  high      something is being requested (OTP, PIN/password, money, remote access) AND there is pressure,
            an authority claim or a KYC pretext around it
  elevated  something sensitive is requested without other cues, OR two different pressure tactics appear
  low       otherwise
"Never share your OTP" style wording is treated as a warning, not a request.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import lexicon as L
from .normalize import DigitRun, Match, Token, compile_phrases, find_digit_runs, find_matches, tokenize

REQUEST_CATS = {"otp_request", "credential_request", "payment_request", "remote_access"}
PRESSURE_CATS = {"urgency", "threat", "secrecy", "verification_bypass"}
CONTEXT_CATS = {"authority", "kyc_pretext"}
WINDOW = 6          # tokens either side of a sensitive term that count as "near"
SECRECY_WINDOW = 8

_C = {
    "otp": compile_phrases(L.OTP_TERMS),
    "cred": compile_phrases(L.CREDENTIAL_TERMS),
    "verbs": compile_phrases(L.DISCLOSE_VERBS),
    "warn": compile_phrases(L.WARNING_CUES),
    **{name: compile_phrases(c["phrases"]) for name, c in L.CATEGORIES.items()},
}


@dataclass
class Hit:
    category: str          # e.g. otp_request, urgency, warning_otp
    kind: str              # request | pressure | context | warning
    quote: str             # exact words from the transcript
    start: int             # character span in the transcript (for highlighting)
    end: int
    explanation: str
    source: str = ""       # which transcript produced it (language code)


@dataclass
class RuleResult:
    level: str
    score: float
    hits: list[Hit] = field(default_factory=list)
    digit_runs: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _span(toks: list[Token], i: int, j: int) -> tuple[int, int]:
    return toks[i].start, toks[j].end


def _near(a: Match, b: Match, window: int) -> bool:
    return b.i <= a.j + window and b.j >= a.i - window


def detect(text: str, source: str = "") -> tuple[list[Hit], list[DigitRun], list[Token]]:
    toks = tokenize(text)
    m = {k: find_matches(toks, v) for k, v in _C.items()}
    hits: list[Hit] = []

    def add(category, kind, i, j, explanation):
        s, e = _span(toks, i, j)
        hits.append(Hit(category, kind, text[s:e], s, e, explanation, source))

    # 1) sensitive terms: request vs warning, decided by nearby verbs and cautionary words
    for concept, cat in (("otp", "otp_request"), ("cred", "credential_request")):
        for term in m[concept]:
            verbs = [v for v in m["verbs"] if _near(term, v, WINDOW)]
            warns = [w for w in m["warn"] if _near(term, w, WINDOW)]
            if warns:
                lo = min([term.i] + [w.i for w in warns])
                hi = max([term.j] + [w.j for w in warns])
                add(f"warning_{concept}", "warning", lo, hi, L.WARNING_EXPLAIN)
            elif verbs:
                lo = min([term.i] + [v.i for v in verbs])
                hi = max([term.j] + [v.j for v in verbs])
                add(cat, "request", lo, hi, L.REQUEST_EXPLAIN[cat])

    sensitive = m["otp"] + m["cred"]

    # 2) the other categories (secrecy near a code is a warning, e.g. "don't tell anyone your OTP")
    for name, cfg in L.CATEGORIES.items():
        for mt in m[name]:
            if name == "secrecy" and any(_near(mt, s, SECRECY_WINDOW) for s in sensitive):
                continue
            add(name, cfg["kind"], mt.i, mt.j, cfg["explain"])

    runs = find_digit_runs(toks)
    return _merge_overlaps(hits, text), runs, toks


def _merge_overlaps(hits: list[Hit], text: str) -> list[Hit]:
    """Two matches of the same kind of indicator that overlap are one piece of evidence."""
    out: list[Hit] = []
    for h in sorted(hits, key=lambda h: (h.category, h.start)):
        prev = out[-1] if out else None
        if prev and prev.category == h.category and h.start <= prev.end:
            prev.end = max(prev.end, h.end)
            prev.quote = text[prev.start:prev.end]
        else:
            out.append(h)
    return sorted(out, key=lambda h: h.start)


def score_hits(hits: list[Hit]) -> tuple[str, float]:
    cats = {h.category for h in hits if h.kind != "warning"}
    req, pressure, context = cats & REQUEST_CATS, cats & PRESSURE_CATS, cats & CONTEXT_CATS
    score = min(10.0, 3.0 * len(req) + 1.5 * len(pressure) + 1.0 * len(context))
    if req and (pressure or context):
        return "high", score
    if req or len(pressure) >= 2:
        return "elevated", score
    return "low", score


def summarise(level: str, hits: list[Hit]) -> str:
    cats = sorted({h.category for h in hits if h.kind != "warning"})
    if level == "low":
        warn = any(h.kind == "warning" for h in hits)
        return ("No scam tactics found. Cautionary wording about sharing codes was present." if warn
                else "No scam tactics found in this transcript.")
    nice = ", ".join(c.replace("_", " ") for c in cats)
    if level == "high":
        return f"A request for sensitive information or money appears together with pressure or authority cues ({nice})."
    return (f"Worth checking: {nice}. Only share a code with someone you contacted yourself; "
            "if unsure, hang up and call the official number.")


def analyse_text(text: str, source: str = "") -> RuleResult:
    hits, runs, _ = detect(text, source)
    level, score = score_hits(hits)
    return RuleResult(level, score, hits,
                      [{"digits": r.digits, "start": r.start, "end": r.end, "quote": text[r.start:r.end]} for r in runs],
                      summarise(level, hits))


def merge_results(results: list[RuleResult], texts: list[str]) -> RuleResult:
    """Combine results from several transcripts of the SAME audio (e.g. Hinglish via en-IN and hi-IN).
    A hit found in any transcript counts; if any transcript shows a warning about OTP/credentials, requests
    for that concept are dropped (cautionary wording is strong evidence, spellings differ between transcripts)."""
    if len(results) == 1:
        return results[0]
    warned = {h.category.replace("warning_", "") for r in results for h in r.hits if h.kind == "warning"}
    merged, seen = [], set()
    for r in results:
        for h in r.hits:
            if h.kind == "request" and h.category in ("otp_request", "credential_request") and \
                    ("otp" if h.category == "otp_request" else "cred") in warned:
                continue
            key = (h.category, " ".join(h.quote.lower().split()))
            cat_key = (h.category,)
            if key in seen or (h.kind != "warning" and cat_key in seen):
                continue
            seen.add(key)
            seen.add(cat_key)
            merged.append(h)
    level, score = score_hits(merged)
    runs, seen_d = [], set()
    for r in results:
        for d in r.digit_runs:
            if d["digits"] not in seen_d:
                seen_d.add(d["digits"])
                runs.append({**d, "source": ""})
    return RuleResult(level, score, merged, runs, summarise(level, merged))
