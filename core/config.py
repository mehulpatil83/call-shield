from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".cache"
REPORT_DIR = ROOT / "reports"
MODEL_DIRS = [ROOT / "models" / "aasist-l", ROOT / "phase0" / "models" / "aasist-l"]
ENV_FILES = [ROOT / ".env", ROOT / "phase0" / ".env"]

# Language key -> Gnani language codes. Hinglish is transcribed twice (Roman-script via en-IN, Devanagari via
# hi-IN) because on a real recording each caught terms the other missed (Phase 0). Streaming accepts only single codes.
LANG_CODES = {"en": ["en-IN"], "mr": ["mr-IN"], "hi": ["hi-IN"], "hinglish": ["en-IN", "hi-IN"]}
REST_MAX_SECONDS = 60
RUPEES_PER_MIN = 0.47          # measured in Phase 0: Rs 9.88 for about 21 min

# Words nudged by Gnani batch STT (`bias_words`); it improved scam-term spelling on the Phase 0 test clips.
BIAS_WORDS = ["OTP", "KYC", "UPI", "PIN", "CVV", "Aadhaar", "account", "verify", "block", "freeze",
              "ओटीपी", "केवायसी", "यूपीआई", "आधार"]
