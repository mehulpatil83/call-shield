"""Builds the JSON report and a self-contained HTML page (no external files, safe against injected markup)."""
from __future__ import annotations

import html
from datetime import datetime

from . import __version__
from .authenticity import AuthResult
from .config import RUPEES_PER_MIN
from .gnani_client import Variant
from .rules import RuleResult

LIMITATIONS = [
    "The scam-word lists are a draft written by an AI assistant and have not been reviewed by native speakers.",
    "The transcript comes from speech-to-text; mistakes there can hide or invent scam words.",
    "Speakers are not separated, so the report cannot tell who said what (a caller or the person being called).",
    "The audio check uses a small pretrained model that is weak on fakes it has not seen (about 44% error on a "
    "published real-world test set). Its score is uncertain evidence, never proof either way.",
    "A real person can run a scam, and a synthetic voice can say something harmless. The two findings are independent.",
    "Audio was sent to Gnani's service for transcription. Only analyse recordings with the speakers' consent.",
]
LEVEL_TEXT = {"high": "High risk", "elevated": "Worth checking", "low": "No scam tactics found"}
PLAIN = {
    "high": "This call shows several signs of a scam.",
    "elevated": "Something sensitive is being asked for. Check who is really asking before you share anything.",
    "low": "No scam tactics were found in this recording.",
}
ADVICE = {
    "high": [
        "Do not share any code, PIN, password or payment details.",
        "Hang up. Call your bank on the number printed on the back of your card or on its official website.",
        "Do not install any app or click any link this caller sent.",
        "If you already shared something, call your bank straight away to block the account or card. "
        "In India you can also report cyber fraud on helpline 1930 or at cybercrime.gov.in.",
    ],
    "elevated": [
        "Only share a code with someone you contacted yourself and trust.",
        "If you are not sure, hang up and call the official number instead.",
    ],
    "low": ["This is a decision aid, not a guarantee. If anything still feels wrong, hang up and call the official number."],
}
DIGIT_NOTE = ("Spoken number sequences are shown for context only and do not change the risk level. "
              "Reading a code aloud to a stranger is a warning sign.")
AUTH_NOTE = ("This check only looks at how the voice sounds. It cannot show who a caller really is, and it does not "
             "reliably detect modern cloned voices.")


def build_report(name: str, lang: str, variants: list[Variant] | None, per_variant: list[RuleResult],
                 merged: RuleResult, auth: AuthResult | None, audio_seconds: float | None,
                 texts: list[str] | None = None) -> dict:
    return {
        "meta": {"file": name, "language": lang, "created": datetime.now().isoformat(timespec="seconds"),
                 "engine_version": __version__, "audio_seconds": audio_seconds,
                 "est_cost_rupees": round(sum(v.audio_seconds / 60 * RUPEES_PER_MIN for v in (variants or []) if not v.cached), 2),
                 "stt_models": sorted({v.model for v in (variants or []) if v.model})},
        "transcripts": [
            {**(v.to_dict() if v else {"code": "text", "mode": "text", "text": (texts or [""] * len(per_variant))[i]}),
             "rules": r.to_dict()}
            for i, (v, r) in enumerate(zip(variants or [None] * len(per_variant), per_variant))
        ],
        "plain_summary": PLAIN[merged.level],
        "advice": ADVICE[merged.level],
        "conversation": {"level": merged.level, "label": LEVEL_TEXT[merged.level], "score": merged.score,
                         "summary": merged.summary, "hits": [h.__dict__ for h in merged.hits],
                         "digit_runs": merged.digit_runs, "digit_note": DIGIT_NOTE},
        "authenticity": ({**auth.to_dict(), "plain_note": AUTH_NOTE} if auth else None),
        "limitations": LIMITATIONS,
    }


def _highlight(text: str, hits) -> str:
    spans = sorted((h for h in hits if h.kind != "warning" or True), key=lambda h: (h.start, -h.end))
    out, pos = [], 0
    for h in spans:
        if h.start < pos:
            continue
        out.append(html.escape(text[pos:h.start]))
        cls = {"request": "req", "pressure": "pre", "context": "ctx", "warning": "warn"}[h.kind]
        out.append(f'<mark class="{cls}" title="{html.escape(h.explanation, quote=True)}">'
                   f'{html.escape(text[h.start:h.end])}</mark>')
        pos = h.end
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _bars(auth: dict) -> str:
    scores = auth.get("window_scores") or []
    if not scores:
        return ""
    lo, hi, w, h = -11.0, 3.0, 260, 90
    def y(v):
        return h - (max(lo, min(hi, v)) - lo) / (hi - lo) * h
    bw = max(6, min(28, (w - 10) // len(scores) - 4))
    parts = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Score per 4-second window" class="bars">']
    for v, label, colour in ((auth["real_at_least"], "natural", "#2e7d32"), (auth["synth_at_most"], "synthetic", "#c62828")):
        parts.append(f'<line x1="0" x2="{w}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{colour}" stroke-dasharray="4 3" stroke-width="1"/>')
        parts.append(f'<text x="2" y="{y(v)-2:.1f}" font-size="8" fill="{colour}">{label}</text>')
    for i, v in enumerate(scores):
        x = 6 + i * (bw + 4)
        parts.append(f'<rect x="{x}" y="{y(v):.1f}" width="{bw}" height="{h - y(v):.1f}" fill="#5c6bc0"><title>window {i+1}: {v}</title></rect>')
    parts.append("</svg>")
    return "".join(parts)


def render_html(report: dict, hits_by_transcript: list[list]) -> str:
    esc = html.escape
    conv, auth, meta = report["conversation"], report["authenticity"], report["meta"]
    ev = "".join(
        f'<li><span class="tag {esc(h["kind"])}">{esc(h["category"].replace("_", " "))}</span> '
        f'<q>{esc(h["quote"])}</q><br><small>{esc(h["explanation"])}'
        f'{" (from " + esc(h["source"]) + ")" if h.get("source") else ""}</small></li>'
        for h in conv["hits"]) or "<li>No indicators matched.</li>"
    digits = "".join(f'<li><q>{esc(d["quote"])}</q> ({len(d["digits"])} digits)</li>' for d in conv["digit_runs"])
    if auth is None:
        auth_html = "<p>Not run.</p>"
    else:
        stats = ""
        if auth.get("median") is not None:
            stats = (f'<p>Median window score <b>{auth["median"]}</b> (middle half {auth["q25"]} to {auth["q75"]}) '
                     f'over {auth["n_windows"]} window(s) of about 4 s.</p>{_bars(auth)}')
        auth_html = (f'<p class="big">{esc(auth["label"])}</p><p>{esc(auth.get("reason", ""))}</p>{stats}'
                     f'<p><small>{esc(auth.get("plain_note", ""))}</small></p>'
                     f'<p><small>{esc(auth["note"])} Model: {esc(auth["model"])}.</small></p>')
    blocks = "".join(
        f'<h3>Transcript ({esc(t.get("code", "text"))})</h3><p class="tx">{_highlight(t.get("text", ""), hits_by_transcript[i])}</p>'
        for i, t in enumerate(report["transcripts"]))
    lim = "".join(f"<li>{esc(x)}</li>" for x in report["limitations"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>call-shield report: {esc(meta["file"])}</title><style>
:root{{--bg:#fff;--fg:#1b1b1f;--card:#f4f5f8;--mut:#5f6368}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16171a;--fg:#e8e8ec;--card:#222428;--mut:#a0a4ab}}}}
body{{margin:0;padding:20px;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,Segoe UI,Roboto,sans-serif;max-width:980px;margin-inline:auto}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.card{{background:var(--card);border-radius:12px;padding:16px}} h1{{font-size:1.4rem}} h2{{font-size:1.1rem;margin-top:0}}
.badge{{display:inline-block;padding:4px 12px;border-radius:999px;font-weight:600;color:#fff}}
.high{{background:#c62828}}.elevated{{background:#ef6c00}}.low{{background:#2e7d32}}
.big{{font-size:1.15rem;font-weight:600}} small,.mut{{color:var(--mut)}} ul{{padding-left:1.1rem}} li{{margin:.4rem 0}}
.tag{{font-size:.75rem;padding:1px 8px;border-radius:6px;background:#5c6bc0;color:#fff}}
.tag.request{{background:#c62828}}.tag.pressure{{background:#ef6c00}}.tag.context{{background:#6d4c41}}.tag.warning{{background:#2e7d32}}
mark{{border-radius:4px;padding:0 2px;color:inherit}} mark.req{{background:#ffcdd2}} mark.pre{{background:#ffe0b2}}
mark.ctx{{background:#d7ccc8}} mark.warn{{background:#c8e6c9}}
@media (prefers-color-scheme:dark){{mark.req{{background:#6d2a2a}}mark.pre{{background:#6b4a1e}}mark.ctx{{background:#4e403b}}mark.warn{{background:#27472b}}}}
.advice{{border-left:6px solid #ef6c00;margin:12px 0}} .tx{{white-space:pre-wrap;word-break:break-word}} .bars{{width:100%;max-width:300px}}
</style></head><body>
<h1>call-shield report</h1>
<p class="mut">File {esc(meta["file"])} · language {esc(meta["language"])} · {esc(meta["created"])} · engine {esc(meta["engine_version"])}</p>
<p class="big">{esc(report["plain_summary"])}</p>
<section class="card advice"><h2>What to do now</h2><ul>{"".join("<li>" + esc(a) + "</li>" for a in report["advice"])}</ul></section>
<p>Two independent checks: <b>what is said</b> and <b>how the voice sounds</b>. Neither one overrides the other.</p>
<div class="grid">
<section class="card"><h2>1. Conversation</h2><p><span class="badge {esc(conv["level"])}">{esc(conv["label"])}</span></p>
<p>{esc(conv["summary"])}</p><ul>{ev}</ul>{("<h3>Spoken number sequences</h3><p><small>" + esc(conv.get("digit_note", "")) + "</small></p><ul>" + digits + "</ul>") if digits else ""}</section>
<section class="card"><h2>2. Audio authenticity</h2>{auth_html}</section></div>
<section class="card" style="margin-top:16px"><h2>Transcript with evidence</h2>
<p class="mut"><mark class="req">request</mark> <mark class="pre">pressure</mark> <mark class="ctx">claim or pretext</mark> <mark class="warn">warning wording</mark> (hover for the reason)</p>{blocks}</section>
<section class="card" style="margin-top:16px"><h2>Limitations</h2><ul>{lim}</ul></section>
</body></html>"""
