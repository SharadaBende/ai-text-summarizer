"""Text utilities: normalisation, sentence splitting, tokenisation, syllables."""
from __future__ import annotations

import re

STOPWORDS = frozenset(
    """a about above after again against all am an and any are as at be because been before being below
    between both but by can could did do does doing down during each few for from further had has have having
    he her here hers herself him himself his how i if in into is it its itself just me more most my myself no
    nor not now of off on once only or other our ours ourselves out over own same she should so some such than
    that the their theirs them themselves then there these they this those through to too under until up very
    was we were what when where which while who whom why will with would you your yours yourself yourselves
    also may might must shall said says say one two""".split()
)

_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "inc", "ltd", "co", "e.g", "i.e",
    "fig", "no", "u.s", "u.k", "a.m", "p.m", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep",
    "sept", "oct", "nov", "dec", "approx", "dept", "est",
}
_BOUNDARY = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][\"')\]])\s+|\n{2,}")
_TOKEN = re.compile(r"\w+(?:['’]\w+)?", re.UNICODE)


def normalize(text: str) -> str:
    """Unify newlines/whitespace; single newlines inside a paragraph become spaces."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _should_merge(prev: str, nxt: str) -> bool:
    ends_sentence = prev.rstrip("\"')]")[-1:] in {".", "!", "?"}
    if not ends_sentence:
        return False
    last = prev.split()[-1].lower().rstrip(".")
    if prev.endswith(".") and (last in _ABBREVIATIONS or (len(last) == 1 and last.isalpha())):
        return True
    return nxt[:1].islower()


def split_sentences(text: str) -> list[str]:
    """Rule-based sentence splitter (handles abbreviations, initials, quotes, paragraphs)."""
    text = normalize(text)
    if not text:
        return []
    raw = [p.strip() for p in _BOUNDARY.split(text) if p and p.strip()]
    merged: list[str] = []
    for part in raw:
        if merged and _should_merge(merged[-1], part):
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


def content_words(text: str) -> list[str]:
    """Lower-cased tokens without stop-words, numbers or very short tokens."""
    return [t for t in tokenize(text) if t not in STOPWORDS and len(t) > 2 and not t.isdigit()]


def word_count(text: str) -> int:
    return len(_TOKEN.findall(text))


def count_syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", word)))
