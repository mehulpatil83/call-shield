"""Command line: python -m core.analyse <audio file> [--lang en|mr|hi|hinglish] [--text transcript.txt]

Audio in -> Gnani transcript(s) -> rule engine + AASIST-L authenticity -> reports/<name>.json and .html
Re-running the same file costs nothing (everything is cached in .cache/)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .audio_io import duration_seconds, sha256_file
from .conversation import (SpeakerPart, channels_look_separate, parts_from_segments, read_channels, speaker_audio,
                           write_wav)
from .authenticity import AuthenticityScorer, AuthResult
from .langcheck import check_language
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
    warnings = [check_language(t, lang) for t in texts]
    report["language_warning"] = warnings[0] if warnings and all(warnings) else None
    hits_by_t = [r.hits for r in results]
    return report, render_html(report, hits_by_t)


def analyse_conversation(path: Path, lang: str, transcriber: GnaniTranscriber, scorer: AuthenticityScorer | None,
                         mode: str = "auto", on_status=None, display_name: str | None = None, work_dir: Path | None = None):
    """Two-person call: separate the speakers (stereo channels or Gnani diarization), then judge each one."""
    from .config import RUPEES_PER_MIN
    from .rules import RuleResult, analyse_text, score_hits, summarise

    say = on_status or (lambda step: None)
    work = Path(work_dir or transcriber.cache_dir.parent / "speakers")
    sha = sha256_file(path)[:12]
    say("transcribing")
    chans = read_channels(path) if mode in ("auto", "channels") else None
    by_channels = bool(chans) and (mode == "channels" or channels_look_separate(chans))
    parts: list[SpeakerPart] = []
    cost, note = 0.0, None
    if by_channels:
        for i, ch in enumerate(chans[:2]):
            wav = write_wav(work / f"{sha}-ch{i + 1}.wav", ch)
            v = transcriber.transcribe_code(wav, lang)
            cost += 0 if v.cached else v.audio_seconds / 60 * RUPEES_PER_MIN
            parts.append(SpeakerPart(f"Speaker {i + 1}", v.text, [(0.0, round(len(ch) / 16000, 2))], wav))
        note = "Speakers were separated using the two stereo channels."
    else:
        v = transcriber.transcribe_conversation(path, lang)
        cost += 0 if v.cached else v.audio_seconds / 60 * RUPEES_PER_MIN
        parts = parts_from_segments(v.segments)
        if not parts:
            parts = [SpeakerPart("Speaker 1", v.text, [])]
        if len(parts) == 1:
            note = "Only one speaker was detected, so this is the same as a normal analysis."
        else:
            note = "Speakers were separated by Gnani's speaker labelling (diarization); it can mix up voices."
    say("analysing")
    results = [analyse_text(p.text, source=p.label) for p in parts]
    hits = [h for r in results for h in r.hits]
    level, score = score_hits(hits)
    ranks = {"low": 0, "elevated": 1, "high": 2}
    worst = max(range(len(parts)), key=lambda i: (ranks[results[i].level], results[i].score)) if parts else 0
    overall = RuleResult(level, score, hits, [d for r in results for d in r.digit_runs], summarise(level, hits))
    say("checking_audio")
    auths = []
    for p in parts:
        auth = None
        if scorer:
            wav = p.wav
            if wav is None and p.spans:
                audio = speaker_audio(path, p.spans)
                wav = write_wav(work / f"{sha}-{p.label.replace(' ', '')}.wav", audio) if len(audio) >= 16000 else None
            auth = scorer.score(wav) if wav else None
        auths.append(auth)
    texts = [p.text for p in parts]
    report = build_report(display_name or path.name, lang, None, results, overall, None, round(duration_seconds(path), 1),
                          texts, [p.label for p in parts])
    report["meta"]["est_cost_rupees"] = round(cost, 2)
    report["meta"]["conversation_mode"] = "channels" if by_channels else "diarization"
    who = parts[worst].label if overall.level != "low" and len(parts) > 1 else None
    report["speakers"] = [{
        "label": p.label, "level": r.level if r.hits or p.text else "none", "score": r.score, "seconds": p.seconds,
        "quotes": [h.quote for h in r.hits if h.kind != "warning"], "categories": sorted({h.category for h in r.hits if h.kind != "warning"}),
        "authenticity": a.to_dict() if a else None,
    } for p, r, a in zip(parts, results, auths)]
    report["conversation"]["who"] = who
    report["conversation"]["who_text"] = (f"The warning signs come from {who}." if who else
                                          "No speaker stood out as suspicious." if len(parts) > 1 else (note or ""))
    report["speaker_note"] = note
    if who:
        report["plain_summary"] += f" {report['conversation']['who_text']}"
    warnings = [check_language(t, lang) for t in texts]
    report["language_warning"] = warnings[0] if warnings and all(warnings) else None
    return report, render_html(report, [r.hits for r in results])


def analyse_file(path: Path, lang: str, transcriber: GnaniTranscriber, scorer: AuthenticityScorer | None,
                 on_status=None, display_name: str | None = None, conversation: str | None = None):
    """Shared by the command line and the web app. on_status(step) is called with
    'transcribing', 'analysing', 'checking_audio' so a UI can show progress."""
    if conversation:
        return analyse_conversation(path, lang, transcriber, scorer, conversation, on_status, display_name)
    say = on_status or (lambda step: None)
    say("transcribing")
    variants = [v for v in transcriber.transcribe(path, lang) if v.text]
    texts = [v.text for v in variants]
    say("analysing")
    seconds = round(duration_seconds(path), 1)
    say("checking_audio")
    auth = scorer.score(path) if scorer else None
    return analyse_transcripts(display_name or path.name, lang, variants, texts, auth, seconds)


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
    ap.add_argument("--conversation", nargs="?", const="auto", choices=["auto", "channels", "diarization"],
                    help="two-person call: separate the speakers (stereo channels or Gnani diarization) and judge each")
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
                                        None if a.no_auth else AuthenticityScorer(), conversation=a.conversation)
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
