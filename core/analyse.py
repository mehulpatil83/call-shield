"""Command line: python -m core.analyse <audio file> [--lang en|mr|hi|hinglish] [--text transcript.txt]

Audio in -> Gnani transcript(s) -> rule engine + AASIST-L authenticity -> reports/<name>.json and .html
Re-running the same file costs nothing (everything is cached in .cache/)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .audio_io import duration_seconds
from .authenticity import AuthenticityScorer, AuthResult
from .gnani_client import GnaniTranscriber, TranscriptionError, Variant
from .report import build_report, render_html
from .rules import analyse_text, detect, merge_results


def guess_lang(path: Path) -> str | None:
    prefix = path.stem.split("_")[0].lower()
    return prefix if prefix in config.LANG_CODES else None


def analyse_transcripts(name: str, lang: str, variants: list[Variant] | None, texts: list[str],
                        auth: AuthResult | None, audio_seconds: float | None):
    results = [analyse_text(t, source=(variants[i].code if variants else "")) for i, t in enumerate(texts)]
    merged = merge_results(results, texts)
    report = build_report(name, lang, variants, results, merged, auth, audio_seconds, texts)
    hits_by_t = [r.hits for r in results]
    return report, render_html(report, hits_by_t)


def analyse_file(path: Path, lang: str, transcriber: GnaniTranscriber, scorer: AuthenticityScorer | None):
    variants = [v for v in transcriber.transcribe(path, lang) if v.text]
    texts = [v.text for v in variants]
    auth = scorer.score(path) if scorer else None
    return analyse_transcripts(path.name, lang, variants, texts, auth, round(duration_seconds(path), 1))


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", nargs="?", help="audio file (wav, m4a, mp3, flac, ogg)")
    ap.add_argument("--lang", choices=sorted(config.LANG_CODES), help="default: from the file name prefix (en_, mr_, hinglish_)")
    ap.add_argument("--text", help="analyse a transcript text file instead of audio (no Gnani, no audio check)")
    ap.add_argument("--no-auth", action="store_true", help="skip the audio authenticity check")
    ap.add_argument("--batch", action="store_true", help="use Gnani batch STT with bias words (slower)")
    ap.add_argument("--out", default=str(config.REPORT_DIR), help="output folder")
    a = ap.parse_args(argv)
    src = Path(a.text or a.audio or "")
    if not a.text and not a.audio:
        ap.error("give an audio file or --text transcript.txt")
    if not src.exists():
        ap.error(f"file not found: {src}")
    lang = a.lang or guess_lang(src)
    if not lang:
        ap.error("cannot tell the language from the file name; use --lang en|mr|hi|hinglish")
    try:
        if a.text:
            report, page = analyse_transcripts(src.name, lang, None, [src.read_text(encoding="utf-8")], None, None)
        else:
            report, page = analyse_file(src, lang, GnaniTranscriber(batch=a.batch, bias=a.batch),
                                        None if a.no_auth else AuthenticityScorer())
    except TranscriptionError as e:
        print(f"Transcription failed: {e}")
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{src.stem}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / f"{src.stem}.html").write_text(page, encoding="utf-8")
    conv, auth = report["conversation"], report["authenticity"]
    print(f"\nConversation : {conv['label']} (score {conv['score']})\n  {conv['summary']}")
    for h in conv["hits"]:
        print(f"  - {h['category']:20s} \"{h['quote']}\"")
    if auth:
        print(f"Audio check  : {auth['label']}" + (f" (median {auth['median']}, {auth['n_windows']} windows)" if auth.get("median") is not None else f" ({auth.get('reason', '')})"))
    print(f"\nReport: {out / (src.stem + '.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
