"""Sanity check: does the transcript look like the language the user said it was?

Why: if someone picks the wrong language, the speech-to-text still returns *something* (for example Marathi written in
Roman letters), the scam rules find nothing, and the report would say "no scam tactics found". That is false
reassurance, so the report marks such results as not reliable. These are cheap heuristics, not language detection."""
from __future__ import annotations

from .normalize import tokenize

EN_COMMON = set("""the a an and or but if so to of in on at for with from by is are was were be been am i you he she it we they
me my your our this that these those not no yes ok okay please thank thanks hello hi sir madam what when where why how who which
can could will would should do does did have has had just now today tomorrow call phone number account bank code otp pin password
money pay payment send share tell give get take need want know see look go come here there then than also very too more some any
all one two three four five six seven eight nine zero your yours its his her their them him us as up out about into over after
before again right well good thing time day week month""".split())


def _letters(text: str) -> list[str]:
    return [c for c in text if c.isalpha()]


def devanagari_share(text: str) -> float:
    letters = _letters(text)
    return sum("\u0900" <= c <= "\u097f" for c in letters) / len(letters) if letters else 0.0


def english_share(text: str) -> float:
    toks = [t.norm for t in tokenize(text) if t.norm.isascii() and t.norm.isalpha()]
    return sum(t in EN_COMMON for t in toks) / len(toks) if toks else 0.0


def check_language(text: str, selected: str) -> str | None:
    """Returns a warning code, or None when the transcript looks plausible. Only checks single-language choices."""
    if len(text.split()) < 15:
        return None
    if selected == "en":
        if devanagari_share(text) > 0.3 or english_share(text) < 0.3:
            return "not_english"
    elif selected in ("mr", "hi"):
        if devanagari_share(text) < 0.5:
            return "not_devanagari"
    return None
