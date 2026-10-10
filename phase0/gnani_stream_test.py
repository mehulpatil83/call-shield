"""Step 6: streaming test - latency, 8 kHz behaviour, idle-connection billing check.

Sends one clip as raw PCM at real-time pace and prints every transcript event
with the server-reported latency and our own arrival time.
"""
import argparse
import asyncio
import io
import time
from pathlib import Path

from common import (AUDIO_DIR, LANG_PREFIX_CODES, VARIANT_DIR, lang_prefix, ledger_add, load_env,
                    load_mono, log_result, resample, setup_console, to_pcm16_bytes)

setup_console()
FRAME = 1024  # bytes: 512 samples of 16-bit PCM


def prepare_pcm(path: Path, rate: int, tail_s: float = 2.5) -> bytes:
    """Mono PCM16 at `rate` plus silence so the server VAD can close the last segment."""
    x, sr = load_mono(path)
    data = to_pcm16_bytes(resample(x, sr, rate)) + bytes(int(tail_s * rate) * 2)
    return data + bytes((-len(data)) % FRAME)  # every frame exactly 1024 bytes


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("clip", help="file name inside audio/ or variants/ (or a full path)")
    ap.add_argument("--rate", type=int, choices=[8000, 16000], default=16000)
    ap.add_argument("--code", default="", help="e.g. en-IN, hi-IN, mr-IN (default: from file prefix)")
    ap.add_argument("--format", choices=["verbatim", "transcribe"], default="verbatim")
    ap.add_argument("--idle", type=float, default=0.0,
                    help="keep the connection open this many seconds with NO audio afterwards "
                         "(then compare your dashboard balance to see whether idle time is billed)")
    args = ap.parse_args()

    path = Path(args.clip)
    if not path.exists():
        path = next((d / args.clip for d in (AUDIO_DIR, VARIANT_DIR) if (d / args.clip).exists()), path)
    if not path.exists():
        raise SystemExit(f"Cannot find {args.clip}")
    code = args.code or LANG_PREFIX_CODES.get(lang_prefix(path.stem), ["en-IN"])[0]

    from gnani.stt import GnaniSTTStreamClient

    key = load_env()
    pcm = prepare_pcm(path, args.rate)
    audio_s = len(pcm) / 2 / args.rate
    events: list[dict] = []
    t0 = time.monotonic()

    def stamp(kind):
        def cb(ev):
            events.append({"kind": kind, "arrival_s": round(time.monotonic() - t0, 2),
                           "text": getattr(ev, "text", None),
                           "server_latency_ms": getattr(ev, "latency", None),
                           "audio_ms": getattr(ev, "audio_duration_ms", None),
                           "segment": getattr(ev, "segment_index", None),
                           "message": getattr(ev, "message", None)})
        return cb

    print(f"Streaming {path.name} as {args.rate} Hz PCM, language {code}, {audio_s:.1f}s at real-time pace...")
    async with GnaniSTTStreamClient(api_key=key, language_code=code, sample_rate=args.rate,
                                    format=args.format) as stream:
        print("Connected:", getattr(stream, "connected_config", None))
        t0 = time.monotonic()
        await stream.stream_audio(io.BytesIO(pcm), on_transcript=stamp("transcript"),
                                  on_processing=stamp("processing"), on_error=stamp("error"),
                                  chunk_size=FRAME, realtime_pace=True)
        if args.idle:
            print(f"Idle hold: {args.idle:.0f}s with no audio (note your dashboard balance now)...")
            await asyncio.sleep(args.idle)
    wall = time.monotonic() - t0

    print("\nkind         arrive(s)  server_lat(ms)  audio(ms)  text")
    for e in events:
        print(f"{e['kind']:12s} {e['arrival_s']:8.2f}  {str(e['server_latency_ms'] or ''):>14}  "
              f"{str(e['audio_ms'] or ''):>9}  {(e['text'] or e['message'] or '')[:70]}")
    log_result("stream_probe", {"file": path.name, "rate": args.rate, "code": code, "audio_s": round(audio_s, 2),
                                "wall_s": round(wall, 2), "idle_s": args.idle, "events": events})
    ledger_add("stream", audio_s + args.idle, f"{path.name} rate={args.rate} idle={args.idle}")
    print(f"\nWall time {wall:.1f}s for {audio_s:.1f}s of audio (plus idle {args.idle:.0f}s).")


if __name__ == "__main__":
    asyncio.run(main())
