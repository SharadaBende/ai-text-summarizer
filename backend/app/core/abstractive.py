"""Abstractive summarisation with Hugging Face seq2seq models (lazy-loaded, chunked, map-reduce)."""
from __future__ import annotations

import importlib.util
import threading

from .text import split_sentences, word_count

MODELS = {
    "distilbart": {"id": "sshleifer/distilbart-cnn-12-6", "label": "DistilBART (fast, English)", "prefix": "", "max_input": 1024},
    "bart": {"id": "facebook/bart-large-cnn", "label": "BART large CNN (best quality, English)", "prefix": "", "max_input": 1024},
    "t5": {"id": "t5-small", "label": "T5 small (lightest)", "prefix": "summarize: ", "max_input": 512},
    "pegasus": {"id": "google/pegasus-xsum", "label": "PEGASUS XSum (one-line summaries)", "prefix": "", "max_input": 512},
    "mt5": {"id": "csebuetnlp/mT5_multilingual_XLSum", "label": "mT5 XL-Sum (45 languages)", "prefix": "", "max_input": 512},
}
DEFAULT_MODEL = "distilbart"


class AbstractiveUnavailable(RuntimeError):
    """Raised when transformers/torch are not installed or a model cannot be loaded."""


_cache: dict[str, tuple] = {}
_lock = threading.Lock()


def is_available() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in ("transformers", "torch"))


def _device():
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load(key: str):
    if not is_available():
        raise AbstractiveUnavailable(
            "Abstractive models need extra packages. Run: pip install -r requirements-ml.txt"
        )
    if key not in MODELS:
        raise AbstractiveUnavailable(f"Unknown model '{key}'. Choose one of: {', '.join(MODELS)}")
    with _lock:
        if key not in _cache:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            try:
                tok = AutoTokenizer.from_pretrained(MODELS[key]["id"])
                model = AutoModelForSeq2SeqLM.from_pretrained(MODELS[key]["id"])
            except Exception as exc:  # network / disk / auth problems
                raise AbstractiveUnavailable(f"Could not load {MODELS[key]['id']}: {exc}") from exc
            device = _device()
            model.to(device).eval()
            _cache[key] = (tok, model, device)
        return _cache[key]


def chunk_sentences(sentences: list[str], max_words: int) -> list[str]:
    chunks: list[str] = []
    cur: list[str] = []
    cur_words = 0
    for s in sentences:
        w = word_count(s)
        if cur and cur_words + w > max_words:
            chunks.append(" ".join(cur))
            cur, cur_words = [], 0
        cur.append(s)
        cur_words += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def _generate(text: str, key: str, target_tokens: int) -> str:
    import torch

    tok, model, device = _load(key)
    cfg = MODELS[key]
    enc = tok(cfg["prefix"] + text, return_tensors="pt", truncation=True, max_length=cfg["max_input"]).to(device)
    max_len = max(24, int(target_tokens))
    min_len = max(8, int(max_len * 0.5))
    with torch.no_grad():
        out = model.generate(
            **enc, num_beams=4, max_length=max_len, min_length=min_len,
            length_penalty=2.0, no_repeat_ngram_size=3, early_stopping=True,
        )
    return tok.decode(out[0], skip_special_tokens=True).strip()


def summarize(text: str, model: str = DEFAULT_MODEL, ratio: float = 0.25, _depth: int = 0) -> dict:
    """Chunk long inputs, summarise each chunk, then summarise the joined partials (map-reduce)."""
    key = model if model in MODELS else DEFAULT_MODEL
    sentences = split_sentences(text)
    total_words = sum(word_count(s) for s in sentences)
    if total_words == 0:
        return {"summary": "", "model": MODELS[key]["id"], "chunks": 0, "device": None}

    max_words = int(MODELS[key]["max_input"] * 0.7)
    chunks = chunk_sentences(sentences, max_words)
    overall = max(30, min(400, int(total_words * ratio * 1.4)))

    if len(chunks) == 1:
        summary = _generate(chunks[0], key, overall)
    else:
        per_chunk = max(30, min(256, int(overall / len(chunks) * 1.3)))
        joined = " ".join(_generate(c, key, per_chunk) for c in chunks)
        if word_count(joined) > max_words and _depth < 2:
            summary = summarize(joined, key, ratio=1.0, _depth=_depth + 1)["summary"]
        else:
            summary = _generate(joined, key, overall)
    return {"summary": summary, "model": MODELS[key]["id"], "chunks": len(chunks), "device": _cache[key][2]}
