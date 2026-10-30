"""Extractive summarisers: lead, frequency, TF-IDF, TextRank, LSA, centroid (+ MMR de-duplication)."""
from __future__ import annotations

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .text import content_words, split_sentences, word_count

EXTRACTIVE_METHODS = {
    "lead": {"label": "Lead sentences", "description": "Baseline that keeps the opening sentences. Surprisingly strong on news."},
    "frequency": {"label": "Word frequency", "description": "Luhn-style: favours sentences packed with the document's most frequent words."},
    "tfidf": {"label": "TF-IDF", "description": "Scores sentences by the total TF-IDF weight of their terms."},
    "textrank": {"label": "TextRank", "description": "Graph ranking (PageRank) over sentence similarity. A reliable general-purpose choice."},
    "lsa": {"label": "LSA", "description": "Latent Semantic Analysis: picks sentences that carry the main latent topics."},
    "centroid": {"label": "Centroid", "description": "Keeps sentences closest to the document's average meaning."},
}
MIN_ELIGIBLE_WORDS = 4


def target_count(n: int, ratio: float = 0.25, num_sentences: int | None = None) -> int:
    if num_sentences:
        return max(1, min(n, int(num_sentences)))
    return max(1, min(n, int(round(n * ratio))))


def _minmax(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    lo, hi = x.min(), x.max()
    return np.zeros_like(x) if hi - lo < 1e-12 else (x - lo) / (hi - lo)


def _lead_prior(n: int) -> np.ndarray:
    return 1.0 / (1.0 + np.arange(n))


def _pagerank(sim: np.ndarray, d: float = 0.85, iters: int = 100, tol: float = 1e-6) -> np.ndarray:
    n = sim.shape[0]
    row = sim.sum(axis=1, keepdims=True)
    P = np.where(row > 0, sim / np.maximum(row, 1e-12), 1.0 / n)
    r = np.full(n, 1.0 / n)
    for _ in range(iters):
        new = (1 - d) / n + d * (P.T @ r)
        done = np.abs(new - r).sum() < tol
        r = new
        if done:
            break
    return r


def _frequency_scores(sentences: list[str]) -> np.ndarray:
    toks = [content_words(s) for s in sentences]
    freq: dict[str, int] = {}
    for t in toks:
        for w in t:
            freq[w] = freq.get(w, 0) + 1
    if not freq:
        return np.zeros(len(sentences))
    top = max(freq.values())
    return np.array([sum(freq[w] / top for w in t) / np.sqrt(len(t)) if t else 0.0 for t in toks])


def score_sentences(sentences: list[str], method: str):
    """Return (raw scores, L2-normalised TF-IDF matrix or None)."""
    n = len(sentences)
    if method == "lead":
        return _lead_prior(n), None
    if method == "frequency":
        return _frequency_scores(sentences), None
    try:
        X = TfidfVectorizer(analyzer=content_words, sublinear_tf=True, norm=None).fit_transform(sentences)
    except ValueError:  # empty vocabulary
        return _lead_prior(n), None
    Xn = normalize(X)
    if method == "tfidf":
        nnz = np.maximum(X.getnnz(axis=1), 1)
        return np.asarray(X.sum(axis=1)).ravel() / np.sqrt(nnz), Xn
    if method == "textrank":
        sim = (Xn @ Xn.T).toarray()
        np.fill_diagonal(sim, 0.0)
        return _pagerank(sim), Xn
    if method == "lsa":
        k = min(3, min(Xn.shape) - 1)
        if k < 1:
            return np.asarray(X.sum(axis=1)).ravel(), Xn
        Z = TruncatedSVD(n_components=k, random_state=0).fit_transform(Xn)
        return np.linalg.norm(Z, axis=1), Xn
    if method == "centroid":
        c = np.asarray(Xn.mean(axis=0))
        return np.asarray(Xn @ c.T).ravel(), Xn
    raise ValueError(f"Unknown extractive method: {method}")


def _mmr(scores, sim, eligible, k, diversity) -> list[int]:
    """Maximal Marginal Relevance: relevance minus redundancy with what's already chosen."""
    cand = [i for i in range(len(scores)) if eligible[i]]
    chosen: list[int] = []
    while cand and len(chosen) < k:
        if sim is None or not chosen or diversity <= 0:
            best = max(cand, key=lambda i: scores[i])
        else:
            best = max(cand, key=lambda i: (1 - diversity) * scores[i] - diversity * max(sim[i][j] for j in chosen))
        chosen.append(best)
        cand.remove(best)
    return chosen


def summarize_extractive(
    text: str,
    method: str = "textrank",
    ratio: float = 0.25,
    num_sentences: int | None = None,
    diversity: float = 0.3,
    position_weight: float = 0.1,
) -> dict:
    if method not in EXTRACTIVE_METHODS:
        raise ValueError(f"Unknown extractive method: {method}")
    sentences = split_sentences(text)
    n = len(sentences)
    if n == 0:
        return {"method": method, "summary": "", "sentences": [], "selected_indices": []}

    k = target_count(n, ratio, num_sentences)
    scores, Xn = score_sentences(sentences, method)
    scores = _minmax(scores)
    if method != "lead" and position_weight > 0:
        scores = (1 - position_weight) * scores + position_weight * _minmax(_lead_prior(n))

    eligible = np.array([word_count(s) >= MIN_ELIGIBLE_WORDS for s in sentences])
    if eligible.sum() < k:
        eligible[:] = True

    sim = None
    if diversity > 0 and k > 1:
        if Xn is None:
            try:
                Xn = normalize(TfidfVectorizer(analyzer=content_words, sublinear_tf=True).fit_transform(sentences))
            except ValueError:
                Xn = None
        if Xn is not None:
            sim = (Xn @ Xn.T).toarray()

    chosen = sorted(_mmr(scores, sim, eligible, k, diversity))
    chosen_set = set(chosen)
    return {
        "method": method,
        "summary": " ".join(sentences[i] for i in chosen),
        "sentences": [
            {"index": i, "text": s, "score": round(float(scores[i]), 4), "selected": i in chosen_set}
            for i, s in enumerate(sentences)
        ],
        "selected_indices": chosen,
    }
