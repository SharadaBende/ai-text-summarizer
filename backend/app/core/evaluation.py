"""Summary evaluation: ROUGE-1/2/L plus reference-free quality signals."""
from __future__ import annotations

import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .keywords import keyword_set
from .text import content_words, split_sentences, word_count

_WORD = re.compile(r"\w+", re.UNICODE)
_MAX_LCS_TOKENS = 1500


def _tok(text: str) -> list[str]:
    return [t.lower() for t in _WORD.findall(text)]


def _prf(overlap: float, ref_total: int, cand_total: int) -> dict:
    p = overlap / cand_total if cand_total else 0.0
    r = overlap / ref_total if ref_total else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)}


def _rouge_n(ref: list[str], cand: list[str], n: int) -> dict:
    grams = lambda t: Counter(tuple(t[i:i + n]) for i in range(len(t) - n + 1))
    r, c = grams(ref), grams(cand)
    overlap = sum((r & c).values())
    return _prf(overlap, sum(r.values()), sum(c.values()))


def _lcs(a: list[str], b: list[str]) -> int:
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def rouge(reference: str, candidate: str) -> dict:
    ref, cand = _tok(reference), _tok(candidate)
    lcs = _lcs(ref[:_MAX_LCS_TOKENS], cand[:_MAX_LCS_TOKENS])
    return {
        "rouge1": _rouge_n(ref, cand, 1),
        "rouge2": _rouge_n(ref, cand, 2),
        "rougeL": _prf(lcs, min(len(ref), _MAX_LCS_TOKENS), min(len(cand), _MAX_LCS_TOKENS)),
    }


def _redundancy(summary: str) -> float:
    sents = split_sentences(summary)
    if len(sents) < 2:
        return 0.0
    try:
        X = TfidfVectorizer(analyzer=content_words).fit_transform(sents)
    except ValueError:
        return 0.0
    sim = cosine_similarity(X)
    return float(sim[np.triu_indices(len(sents), k=1)].mean())


def summary_metrics(source: str, summary: str) -> dict:
    """Reference-free metrics that work on any document."""
    src_w, sum_w = word_count(source), word_count(summary)
    kws = keyword_set(source, 12)
    covered = {w for w in content_words(summary) if w in kws}
    coverage = len(covered) / len(kws) if kws else 0.0
    try:
        X = TfidfVectorizer(analyzer=content_words, sublinear_tf=True).fit_transform([source, summary])
        similarity = float(cosine_similarity(X[0], X[1])[0, 0])
    except ValueError:
        similarity = 0.0
    return {
        "source_words": src_w,
        "summary_words": sum_w,
        "compression_ratio": round(sum_w / max(src_w, 1), 4),
        "reduction_pct": round(100 * (1 - sum_w / max(src_w, 1)), 1),
        "keyword_coverage": round(coverage, 4),
        "similarity": round(similarity, 4),
        "redundancy": round(_redundancy(summary), 4),
    }
