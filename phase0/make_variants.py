"""Step 4: build deterministic test variants of every clip in audio/.

For clip  en_scam.wav  it writes into variants/:
  en_scam__16k.wav          clean, mono, 16 kHz
  en_scam__tel8k.wav        phone-line simulation, 8 kHz   (band-pass + mu-law)
  en_scam__tel8k_noisy.wav  same + noise at 15 dB SNR
  en_scam__tel8k_up16k.wav  tel8k upsampled back to 16 kHz (for the anti-spoofing model)
The telephony simulation is an approximation, not a real network codec.
"""
import argparse

from common import (AUDIO_DIR, VARIANT_DIR, list_audio, load_mono, resample, setup_console,
                    telephony_sim, write_wav)

setup_console()
ap = argparse.ArgumentParser()
ap.add_argument("--snr", type=float, default=15.0, help="SNR (dB) for the noisy variant")
args = ap.parse_args()

clips = [p for p in list_audio(AUDIO_DIR)]
if not clips:
    raise SystemExit("No audio found in audio/. Record the clips first (README step 4).")

for p in clips:
    x, sr = load_mono(p)
    x16 = resample(x, sr, 16000)
    tel = telephony_sim(x16, 16000)
    tel_noisy = telephony_sim(x16, 16000, snr_db=args.snr, seed=1)
    out = {
        "16k": (x16, 16000),
        "tel8k": (tel, 8000),
        "tel8k_noisy": (tel_noisy, 8000),
        "tel8k_up16k": (resample(tel, 8000, 16000), 16000),
    }
    for name, (sig, rate) in out.items():
        write_wav(VARIANT_DIR / f"{p.stem}__{name}.wav", sig, rate)
    print(f"{p.name}: {len(x16)/16000:.1f}s -> 4 variants")
print("Done. Files are in variants/")
