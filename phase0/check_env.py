"""Step 1: report what this machine can run (Python, GPU, packages, ffmpeg, API key)."""
import importlib.metadata as md
import os
import platform
import shutil
import sys

from common import ROOT, setup_console

setup_console()


def ver(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "NOT INSTALLED"


print("== System ==")
print("OS:", platform.platform())
print("Python:", sys.version.split()[0], "(3.10 or 3.11 recommended)")
try:
    import psutil

    print("RAM: %.1f GB total, %.1f GB free" % (psutil.virtual_memory().total / 1e9, psutil.virtual_memory().available / 1e9))
except ImportError:
    print("RAM: install psutil to see it")

print("\n== CPU (this project runs on CPU only) ==")
print("Processor:", platform.processor() or "unknown")
try:
    import psutil

    print("Cores: %s physical / %s logical" % (psutil.cpu_count(logical=False), psutil.cpu_count(logical=True)))
except ImportError:
    print("Logical cores:", os.cpu_count())
try:
    import torch

    print("torch:", torch.__version__, "| threads:", torch.get_num_threads())
    if "+cu" in torch.__version__:
        print("Note: this is a CUDA build of torch. It still works on CPU but is a much bigger download; the CPU build is enough.")
except ImportError:
    print("torch not installed yet (README step 1)")

print("\n== Packages ==")
for pkg in ["gnani-vachana", "numpy", "scipy", "soundfile", "huggingface_hub", "python-dotenv", "fairseq", "faster-whisper", "websockets"]:
    print(f"{pkg:18s} {ver(pkg)}")

print("\n== Tools ==")
print("ffmpeg on PATH:", bool(shutil.which("ffmpeg")), "(optional for now)")
print("Ollama on PATH:", bool(shutil.which("ollama")), "(needed for the LLM test, README step 8)")

print("\n== Credentials ==")
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass
key = os.getenv("GNANI_API_KEY", "")
print("GNANI_API_KEY set:", bool(key) and key != "your-gnani-api-key")

print("\n== Audio folder ==")
wavs = [p.name for p in (ROOT / "audio").glob("*") if p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}]
print(f"{len(wavs)} audio file(s) in audio/:", ", ".join(sorted(wavs)) or "none yet")
