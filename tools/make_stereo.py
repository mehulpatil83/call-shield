"""Build a two-person demo call from two separate mono recordings: one person on the left channel, the other on the right.

    python tools\\make_stereo.py caller.wav victim.wav demo_call.wav

Use your own acted recordings (for example a scam script read by you and a reply read by a friend). Then analyse with:
    python -m core.analyse demo_call.wav --lang en --conversation channels
or tick "This is a conversation between two people" in the web app. Because each person is on their own channel,
speakers are separated exactly, without relying on speaker labelling."""
import sys
from pathlib import Path

import numpy as np

from core.audio_io import load_mono_16k


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 3:
        print(__doc__)
        return 1
    import soundfile as sf

    left, right = load_mono_16k(Path(argv[0])), load_mono_16k(Path(argv[1]))
    n = max(len(left), len(right))
    pad = lambda x: np.pad(x, (0, n - len(x)))
    sf.write(argv[2], np.stack([pad(left), pad(right)], axis=1), 16000, subtype="PCM_16")
    print(f"Wrote {argv[2]}: {n / 16000:.1f} s, stereo (left = {Path(argv[0]).name}, right = {Path(argv[1]).name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
