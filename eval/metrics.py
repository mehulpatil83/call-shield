"""Metrics with confidence intervals. Small samples are the norm here, so every rate comes with a Wilson interval
and every table says how many recordings it is based on."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict

import numpy as np

_PUNCT = re.compile(r"[^\w\s\u0900-\u097F]", re.UNICODE)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None, float | None]:
    if n == 0:
        return None, None, None
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def auc(pos: list[float], neg: list[float], boot: int = 2000, seed: int = 0):
    """P(random positive scores above random negative); ties count half. Bootstrap 95% interval."""
    if not pos or not neg:
        return None, None, None

    def one(a, b):
        a, b = np.asarray(a), np.asarray(b)
        return float(((a[:, None] > b[None, :]).sum() + 0.5 * (a[:, None] == b[None, :]).sum()) / (len(a) * len(b)))

    point = one(pos, neg)
    rng = np.random.default_rng(seed)
    vals = [one(rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) for _ in range(boot)]
    return point, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def _tokens(s: str) -> list[str]:
    return _PUNCT.sub(" ", unicodedata.normalize("NFC", s).lower()).split()


def _edit(a: list, b: list) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def wer(ref: str, hyp: str) -> float:
    r = _tokens(ref)
    return _edit(r, _tokens(hyp)) / max(len(r), 1)


def best_wer(ref: str, hyps: list[str]) -> float | None:
    return min((wer(ref, h) for h in hyps if h), default=None)


def _rate(k, n):
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": p, "lo": lo, "hi": hi}


def conversation_table(records: list[dict]) -> list[dict]:
    """Recall on scams and false-alarm rate on benign calls, strict (high only) and lenient (elevated or high)."""
    rows = []
    groups = defaultdict(list)
    for r in records:
        if r.get("error"):
            continue
        groups[("all", "all")].append(r)
        groups[("language", r["language"])].append(r)
        groups[("condition", r["condition"])].append(r)
        groups[("voice", r["voice"])].append(r)
        if r["hard"]:
            groups[("hard cases", "legitimate but suspicious-sounding")].append(r)
    for (kind, name), rs in sorted(groups.items()):
        scams = [r for r in rs if r["label"] == "scam"]
        benign = [r for r in rs if r["label"] == "benign"]
        strict = lambda r: r["level"] == "high"
        lenient = lambda r: r["level"] in ("high", "elevated")
        tp_s, fp_s = sum(map(strict, scams)), sum(map(strict, benign))
        tp_l, fp_l = sum(map(lenient, scams)), sum(map(lenient, benign))
        prec = lambda tp, fp: tp / (tp + fp) if tp + fp else None
        rows.append({
            "group": kind, "name": name, "scams": len(scams), "benign": len(benign),
            "recall_high": _rate(tp_s, len(scams)), "false_alarm_high": _rate(fp_s, len(benign)),
            "recall_any": _rate(tp_l, len(scams)), "false_alarm_any": _rate(fp_l, len(benign)),
            "precision_high": prec(tp_s, fp_s), "precision_any": prec(tp_l, fp_l),
            "unreliable": sum(1 for r in rs if r.get("language_warning")),
        })
    return rows


def authenticity_table(records: list[dict]) -> dict:
    ok = [r for r in records if not r.get("error") and r.get("auth_median") is not None]
    out = {"by_group": [], "auc": [], "phone_shift": None}
    groups = defaultdict(list)
    for r in ok:
        groups[(r["voice"], r["condition"])].append(r)
    for (voice, cond), rs in sorted(groups.items()):
        meds = [r["auth_median"] for r in rs]
        codes = defaultdict(int)
        for r in rs:
            codes[r["auth_code"]] += 1
        out["by_group"].append({"voice": voice, "condition": cond, "n": len(rs), "median_of_medians": float(np.median(meds)),
                                "min": min(meds), "max": max(meds), "codes": dict(codes)})
    for cond in sorted({r["condition"] for r in ok}):
        real = [r["auth_median"] for r in ok if r["condition"] == cond and r["voice"] == "real"]
        syn = [r["auth_median"] for r in ok if r["condition"] == cond and r["voice"] == "synthetic"]
        point, lo, hi = auc(real, syn)
        out["auc"].append({"condition": cond, "n_real": len(real), "n_synthetic": len(syn), "auc": point, "lo": lo, "hi": hi})
    base = {(r["speaker"], r["script_id"]): r["auth_median"] for r in ok if r["voice"] == "real" and r["condition"] == "orig"}
    diffs = [r["auth_median"] - base[(r["speaker"], r["script_id"])] for r in ok
             if r["voice"] == "real" and r["condition"] != "orig" and (r["speaker"], r["script_id"]) in base]
    if diffs:
        out["phone_shift"] = {"n": len(diffs), "mean_change": float(np.mean(diffs))}
    return out


def stt_table(records: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in records:
        if not r.get("error") and r.get("wer") is not None and r["voice"] == "real":
            groups[(r["language"], r["condition"])].append(r["wer"])
    return [{"language": l, "condition": c, "n": len(v), "mean_wer": float(np.mean(v)), "max_wer": max(v)}
            for (l, c), v in sorted(groups.items())]


def failures(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        if r.get("error"):
            out.append({**r, "why": "error: " + r["error"]})
        elif r["label"] == "scam" and r["level"] != "high":
            out.append({**r, "why": f"scam call rated {r['level']}"})
        elif r["label"] == "benign" and r["level"] != "low":
            out.append({**r, "why": f"benign call rated {r['level']}"})
    return out


def summarise(records: list[dict]) -> dict:
    return {"n_records": len(records), "n_errors": sum(1 for r in records if r.get("error")),
            "speakers": sorted({r["speaker"] for r in records if r["voice"] == "real"}),
            "synthetic_voices": sorted({r["speaker"] for r in records if r["voice"] == "synthetic"}),
            "conversation": conversation_table(records), "authenticity": authenticity_table(records),
            "stt": stt_table(records), "failures": failures(records),
            "cost_rupees": round(sum(r.get("cost") or 0 for r in records), 2)}
