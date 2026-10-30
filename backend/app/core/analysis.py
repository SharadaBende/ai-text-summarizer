"""Document analytics: stats, readability, sentiment, entities, topics."""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from .keywords import extract_keywords
from .text import STOPWORDS, content_words, count_syllables, split_sentences, tokenize, word_count

POSITIVE = set("""good great excellent amazing wonderful best better love loved happy success successful growth gain gains
improve improved improvement benefit benefits positive strong win wins won progress innovative effective efficient
safe reliable hope hopeful bright boost rise rising record breakthrough support helpful beneficial opportunity
healthy clean secure stable thrive remarkable impressive outstanding enjoy pleased praise peace""".split())
NEGATIVE = set("""bad worse worst poor terrible awful hate hated sad failure fail failed failing loss losses decline declined
decrease risk risks threat threats negative weak lose lost crisis problem problems harm harmful damage damaged
danger dangerous unsafe unstable fear concern concerns worry worried drop fall falling cut cuts war conflict
death disease pollution shortage delay delays scandal fraud violence pain difficult controversial""".split())
NEGATIONS = {"not", "no", "never", "n't", "without", "hardly", "neither", "nor", "cannot"}
INTENSIFIERS = {"very", "extremely", "highly", "really", "significantly", "deeply", "remarkably"}


def text_stats(text: str) -> dict:
    sentences = split_sentences(text)
    tokens = tokenize(text)
    words = len(tokens)
    uniq = len(set(tokens))
    lengths = [word_count(s) for s in sentences]
    top = Counter(content_words(text)).most_common(15)
    return {
        "characters": len(text),
        "words": words,
        "sentences": len(sentences),
        "paragraphs": len([p for p in re.split(r"\n\s*\n", text) if p.strip()]),
        "avg_sentence_words": round(words / max(len(sentences), 1), 1),
        "avg_word_length": round(sum(len(t) for t in tokens) / max(words, 1), 2),
        "lexical_diversity": round(uniq / max(words, 1), 3),
        "reading_time_min": round(words / 200, 1),
        "speaking_time_min": round(words / 130, 1),
        "top_words": [{"word": w, "count": c} for w, c in top],
        "sentence_lengths": lengths,
    }


def readability(text: str) -> dict:
    sentences = max(len(split_sentences(text)), 1)
    words = re.findall(r"[A-Za-z']+", text)
    n = max(len(words), 1)
    syll = sum(count_syllables(w) for w in words)
    complex_words = sum(1 for w in words if count_syllables(w) >= 3)
    ease = 206.835 - 1.015 * (n / sentences) - 84.6 * (syll / n)
    grade = 0.39 * (n / sentences) + 11.8 * (syll / n) - 15.59
    fog = 0.4 * ((n / sentences) + 100 * (complex_words / n))
    if ease >= 80:
        level = "Easy"
    elif ease >= 60:
        level = "Standard"
    elif ease >= 40:
        level = "Fairly difficult"
    else:
        level = "Difficult"
    return {
        "flesch_reading_ease": round(ease, 1),
        "flesch_kincaid_grade": round(grade, 1),
        "gunning_fog": round(fog, 1),
        "level": level,
    }


def sentiment(text: str) -> dict:
    """Small lexicon-based sentiment scorer with negation and intensifier handling."""
    toks = re.findall(r"[a-z']+", text.lower())
    pos = neg = 0
    total = 0.0
    for i, t in enumerate(toks):
        val = 1.0 if t in POSITIVE else -1.0 if t in NEGATIVE else 0.0
        if not val:
            continue
        window = toks[max(0, i - 3): i]
        if any(w in NEGATIONS or w.endswith("n't") for w in window):
            val = -val * 0.8
        if any(w in INTENSIFIERS for w in window):
            val *= 1.5
        total += val
        pos += val > 0
        neg += val < 0
    compound = total / math.sqrt(total * total + 15) if total else 0.0
    label = "Positive" if compound >= 0.05 else "Negative" if compound <= -0.05 else "Neutral"
    n = max(len(toks), 1)
    return {
        "label": label,
        "compound": round(compound, 3),
        "positive_words": int(pos),
        "negative_words": int(neg),
        "positive_share": round(pos / n, 4),
        "negative_share": round(neg / n, 4),
    }


def entities(text: str, top_k: int = 15) -> list[dict]:
    """Named entities via spaCy if available, otherwise a capitalised-phrase heuristic."""
    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        counts = Counter((e.text.strip(), e.label_) for e in nlp(text[:100000]).ents if len(e.text.strip()) > 1)
        return [{"text": t, "label": lab, "count": c} for (t, lab), c in counts.most_common(top_k)]
    except Exception:
        pass
    counts: Counter = Counter()
    for sent in split_sentences(text):
        words = re.findall(r"[A-Za-z][\w'’.-]*", sent)
        run: list[str] = []
        start = 0
        for idx, w in enumerate(words + [""]):
            if w and w[0].isupper() and w.lower() not in STOPWORDS:
                if not run:
                    start = idx
                run.append(w.strip(".-"))
            else:
                if run and not (len(run) == 1 and start == 0):
                    counts[" ".join(run)] += 1
                run = []
    return [{"text": t, "label": "ENTITY", "count": c} for t, c in counts.most_common(top_k)]


def topics(text: str, n_topics: int = 3, n_words: int = 6) -> list[dict]:
    sentences = split_sentences(text)
    if len(sentences) < 6:
        return []
    try:
        vec = TfidfVectorizer(analyzer=content_words, sublinear_tf=True, min_df=1)
        X = vec.fit_transform(sentences)
    except ValueError:
        return []
    k = min(n_topics, len(sentences) // 2, X.shape[1] - 1)
    if k < 1:
        return []
    model = NMF(n_components=k, init="nndsvda", random_state=0, max_iter=400)
    W = model.fit_transform(X)
    terms = vec.get_feature_names_out()
    share = W.argmax(axis=1)
    out = []
    for i, comp in enumerate(model.components_):
        words = [terms[j] for j in np.argsort(comp)[::-1][:n_words]]
        out.append({"id": i + 1, "words": words, "share": round(float((share == i).mean()), 3)})
    return sorted(out, key=lambda t: -t["share"])


def analyze(text: str) -> dict:
    return {
        "stats": text_stats(text),
        "readability": readability(text),
        "sentiment": sentiment(text),
        "keywords": extract_keywords(text, "tfidf", 12),
        "keyphrases": extract_keywords(text, "rake", 10),
        "entities": entities(text),
        "topics": topics(text),
    }
