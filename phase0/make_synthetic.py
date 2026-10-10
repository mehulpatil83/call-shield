"""Optional: make an EASY synthetic-voice sample with Windows' built-in offline TTS (pyttsx3).

Not a realistic deepfake. It only checks that the anti-spoofing pipeline can tell an obviously
synthetic voice from your real recording. Output: audio/en_synth_scam.wav (+ matching reference text).
Install first:  pip install pyttsx3
"""
import shutil

from common import AUDIO_DIR, setup_console

setup_console()
src = AUDIO_DIR / "en_scam.txt"
if not src.exists():
    raise SystemExit("audio/en_scam.txt is missing.")
import pyttsx3  # noqa: E402

engine = pyttsx3.init()
engine.setProperty("rate", 160)
engine.save_to_file(src.read_text(encoding="utf-8"), str(AUDIO_DIR / "en_synth_scam.wav"))
engine.runAndWait()
shutil.copy(src, AUDIO_DIR / "en_synth_scam.txt")
print("Wrote audio/en_synth_scam.wav")
