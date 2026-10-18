"""Text normalisation shared by the rule engine: tokenising with character spans, spelling clean-up,
fuzzy token matching and spoken-digit detection for English, Hinglish (Roman) and Hindi/Marathi (Devanagari)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u2060"), None)
_DEV_DIGITS = {ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")}
_PUNCT = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~।॥“”‘’…—–•|"


@dataclass(frozen=True)
class Token:
    norm: str
    start: int   # character offsets in the ORIGINAL transcript, so evidence can be highlighted
    end: int


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s).translate(_ZERO_WIDTH).translate(_DEV_DIGITS).lower()
    return s.replace("’", "'").replace("‘", "'")


def tokenize(text: str) -> list[Token]:
    """Split on whitespace, hyphens and slashes; strip edge punctuation; join spelled-out Latin letters
    ("o t p" -> "otp"). Gnani's verbatim output has no punctuation, so we never rely on sentences."""
    toks = []
    for m in re.finditer(r"[^\s\-–—/]+", text):
        raw = m.group(0)
        norm = clean(raw).strip(_PUNCT)
        if norm:
            lead = len(raw) - len(raw.lstrip(_PUNCT))
            trail = len(raw) - len(raw.rstrip(_PUNCT))
            toks.append(Token(norm, m.start() + lead, m.end() - trail))   # span excludes edge punctuation
    return _collapse_spelled_letters(toks)


def _collapse_spelled_letters(toks: list[Token]) -> list[Token]:
    out, run = [], []

    def flush():
        if len(run) >= 2:
            out.append(Token("".join(t.norm for t in run), run[0].start, run[-1].end))
        else:
            out.extend(run)
        run.clear()

    for t in toks:
        if len(t.norm) == 1 and t.norm.isascii() and t.norm.isalpha():
            run.append(t)
        else:
            flush()
            out.append(t)
    flush()
    return out


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 3:
        return abs(len(a) - len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def stem(t: str) -> str:
    """Rough English stem so inflections match (verify / verifying / verified, block / blocked / blocking).
    Only ASCII words of 5+ letters are touched; everything else is returned unchanged."""
    if len(t) < 5 or not (t.isascii() and t.isalpha()):
        return t
    for suf, rep in (("ies", "y"), ("ied", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if t.endswith(suf) and len(t) - len(suf) >= 3 and not (suf == "s" and t.endswith("ss")):
            t = t[:-len(suf)] + rep
            break
    if len(t) > 3 and t.endswith("e"):
        t = t[:-1]
    if len(t) > 3 and t[-1] == t[-2] and t[-1] not in "aeioulsz":
        t = t[:-1]
    return t


def tok_match(a: str, b: str) -> bool:
    """Exact for tokens of 5 characters or fewer; for longer ones ~80% similar AND the same first letter (speech-to-text
    spells words inconsistently, but "kabhi" (never) must not match "abhi" (now), and the Marathi "आत्ता" (now)
    must not match "आत्ताच" (right now, a pressure phrase))."""
    if a == b:
        return True
    if min(len(a), len(b)) >= 5 and a[0] == b[0] and stem(a) == stem(b):
        return True                                   # inflections of the same word
    if min(len(a), len(b)) <= 5 or a[0] != b[0]:
        return False
    return 1 - lev(a, b) / max(len(a), len(b)) >= 0.8


def apply_slips(tokens: list[Token], slips, window: int = 3) -> list[Token]:
    """Read known speech-to-text slips as the word that was probably meant, when a neighbour word backs it up.
    Positions and character spans are kept, so evidence still quotes what was actually said."""
    out = list(tokens)
    for idx, t in enumerate(tokens):
        for heard, meant, neighbours in slips:
            if t.norm == heard:
                around = {x.norm for x in tokens[max(0, idx - window):idx]} | {x.norm for x in tokens[idx + 1:idx + 1 + window]}
                if around & neighbours:
                    out[idx] = Token(meant, t.start, t.end)
                    break
    return out


@dataclass(frozen=True)
class Match:
    i: int          # first token index
    j: int          # last token index (inclusive)
    phrase: str


def compile_phrases(phrases: list[str]) -> list[tuple[tuple[str, ...], str]]:
    out = []
    for p in phrases:
        toks = tuple(t.norm for t in tokenize(p))
        if toks:
            out.append((toks, p))
    return out


def find_matches(tokens: list[Token], compiled) -> list[Match]:
    """All phrase matches; overlapping matches are resolved in favour of the longest one."""
    found = []
    n = len(tokens)
    for toks, text in compiled:
        L = len(toks)
        for i in range(n - L + 1):
            if all(tok_match(tokens[i + k].norm, toks[k]) for k in range(L)):
                found.append(Match(i, i + L - 1, text))
    # words that the speech-to-text split or joined differently ("pass word" / "password", "any desk" / "anydesk")
    for toks, text in compiled:
        target = "".join(toks)
        if len(target) < 7 or not target.isascii():
            continue
        L = len(toks)
        for k in {max(1, L - 1), L + 1} - {L}:
            for i in range(n - k + 1):
                if "".join(t.norm for t in tokens[i:i + k]) == target:
                    found.append(Match(i, i + k - 1, text))
    found.sort(key=lambda m: (-(m.j - m.i), m.i))
    kept, used = [], set()
    for m in found:
        rng = set(range(m.i, m.j + 1))
        if rng & used:
            continue
        kept.append(m)
        used |= rng
    return sorted(kept, key=lambda m: m.i)


# ----------------------------------------------------------------- spoken digits ----
DIGIT_WORDS = {
    # English
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    # Hinglish (Roman)
    "shunya": 0, "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6,
    "chhah": 6, "chheh": 6, "saat": 7, "aath": 8, "nau": 9,
    # Marathi (Roman)
    "don": 2, "tin": 3, "paach": 5, "saha": 6, "naau": 9,
    # Hindi / Marathi (Devanagari)
    "शून्य": 0, "एक": 1, "दो": 2, "दोन": 2, "तीन": 3, "तिन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "पाच": 5,
    "छह": 6, "छः": 6, "छे": 6, "सहा": 6, "सात": 7, "आठ": 8, "नौ": 9, "नऊ": 9,
}


@dataclass(frozen=True)
class DigitRun:
    i: int
    j: int
    digits: str
    start: int
    end: int


def find_digit_runs(tokens: list[Token], min_digits: int = 4) -> list[DigitRun]:
    """Runs of spoken or written digits ("four seven two nine", "ek do teen char", "4721")."""
    runs, cur = [], []

    def flush():
        digits = "".join(d for _, d in cur)
        if len(digits) >= min_digits:
            i, j = cur[0][0], cur[-1][0]
            runs.append(DigitRun(i, j, digits, tokens[i].start, tokens[j].end))
        cur.clear()

    for idx, t in enumerate(tokens):
        if t.norm.isdigit():
            cur.append((idx, t.norm))
        elif t.norm in DIGIT_WORDS:
            cur.append((idx, str(DIGIT_WORDS[t.norm])))
        else:
            flush()
    flush()
    return runs
