"""Keyword / keyphrase extraction: TF-IDF (with bigrams) and RAKE."""
from __future__ import annotations

import re
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .text import STOPWORDS, content_words, split_sentences


def _dedupe(ranked: list[tuple[str, float]], top_k: int) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for phrase, score in ranked:
        if any(phrase in kept or kept in phrase for kept, _ in out):
            continue
        out.append((phrase, score))
        if len(out) == top_k:
            break
    return out


def _normalise(pairs: list[tuple[str, float]]) -> list[dict]:
    if not pairs:
        return []
    top = max(s for _, s in pairs) or 1.0
    return [{"keyword": k, "score": round(float(s / top), 4)} for k, s in pairs]


def tfidf_keywords(text: str, top_k: int = 12) -> list[dict]:
    sentences = split_sentences(text)
    if len(sentences) < 3:
        sentences = re.split(r"[,;]\s+|\s{2,}", text) if len(sentences) < 2 else sentences
    try:
        vec = TfidfVectorizer(
            ngram_range=(1, 2), stop_words=list(STOPWORDS), sublinear_tf=True,
            token_pattern=r"(?u)\b[^\W\d_]{3,}\b",
        )
        X = vec.fit_transform(sentences)
    except ValueError:
        return []
    scores = np.asarray(X.sum(axis=0)).ravel()
    terms = vec.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda p: -p[1])[: top_k * 6]
    return _normalise(_dedupe(ranked, top_k))


def rake_keywords(text: str, top_k: int = 12, max_words: int = 4) -> list[dict]:
    """Rapid Automatic Keyword Extraction: phrases between stop-words, scored by degree/frequency."""
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]+|[.,;:!?()\[\]\"\n]", text.lower())
    phrases: list[list[str]] = []
    cur: list[str] = []
    for tok in tokens:
        if tok in STOPWORDS or not tok[0].isalpha():
            if cur:
                phrases.append(cur)
                cur = []
        else:
            cur.append(tok)
    if cur:
        phrases.append(cur)
    phrases = [p for p in phrases if len(p) <= max_words]
    freq: dict[str, int] = defaultdict(int)
    degree: dict[str, int] = defaultdict(int)
    for p in phrases:
        for w in p:
            freq[w] += 1
            degree[w] += len(p)
    word_score = {w: degree[w] / freq[w] for w in freq}
    scored: dict[str, float] = {}
    for p in phrases:
        scored[" ".join(p)] = sum(word_score[w] for w in p)
    ranked = sorted(scored.items(), key=lambda kv: -kv[1])[: top_k * 4]
    return _normalise(_dedupe(ranked, top_k))


def extract_keywords(text: str, method: str = "tfidf", top_k: int = 12) -> list[dict]:
    if method == "rake":
        return rake_keywords(text, top_k)
    return tfidf_keywords(text, top_k)


def keyword_set(text: str, top_k: int = 12) -> set[str]:
    return {w for k in tfidf_keywords(text, top_k) for w in content_words(k["keyword"])}
