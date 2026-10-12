"""Find evaluation recordings and attach their labels.

File name:  <speaker>_<script id>[_syn].<ext>     e.g.  p1_en-s1.wav   p2_mr-b3.m4a   ai1_en-s1_syn.wav
`_syn` marks a synthetic (AI or text-to-speech) voice reading the script; everything else is a real person.
The label (scam or benign), language, split (dev or test) and the reference text come from scripts_bank.py."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .scripts_bank import SCRIPTS

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
NAME_RE = re.compile(r"^(?P<speaker>[A-Za-z0-9]+)_(?P<script>[a-z]+-[sb]\d+)(?P<syn>_syn)?$")


@dataclass
class Item:
    path: Path
    speaker: str
    script_id: str
    language: str
    label: str            # scam | benign
    scenario: str
    hard: bool
    split: str            # dev | test
    voice: str            # real | synthetic
    reference: str


def scan(folder: Path) -> tuple[list[Item], list[tuple[str, str]]]:
    items, skipped = [], []
    for p in sorted(Path(folder).glob("*")):
        if p.suffix.lower() not in AUDIO_EXT:
            continue
        m = NAME_RE.match(p.stem)
        if not m:
            skipped.append((p.name, "name does not match <speaker>_<script id>[_syn]"))
            continue
        script = SCRIPTS.get(m["script"])
        if not script:
            skipped.append((p.name, f"unknown script id {m['script']}"))
            continue
        items.append(Item(p, m["speaker"], script["id"], script["language"], script["label"], script["scenario"],
                          script["hard"], script["split"], "synthetic" if m["syn"] else "real", script["text"]))
    return items, skipped
