"""Hybrid summariser: extract the most important sentences, then rewrite them abstractively."""
from __future__ import annotations

from . import abstractive
from .extractive import summarize_extractive
from .text import word_count


def summarize_hybrid(text: str, model: str = abstractive.DEFAULT_MODEL, ratio: float = 0.25,
                     extractor: str = "textrank", max_words: int = 600) -> dict:
    total = max(word_count(text), 1)
    pre_ratio = min(0.7, max(0.35, max_words / total))
    stage1 = summarize_extractive(text, method=extractor, ratio=pre_ratio, diversity=0.3)
    # ratio is relative to the original text, so rescale it for the shortened input.
    stage2_ratio = min(1.0, ratio * total / max(word_count(stage1["summary"]), 1))
    stage2 = abstractive.summarize(stage1["summary"], model=model, ratio=stage2_ratio)
    return {
        "summary": stage2["summary"],
        "sentences": stage1["sentences"],
        "selected_indices": stage1["selected_indices"],
        "model": stage2["model"],
        "chunks": stage2["chunks"],
        "device": stage2["device"],
        "extractor": extractor,
    }
