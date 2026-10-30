"""FastAPI application: summarise, compare, analyse, evaluate, ingest, export, history."""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import config, db
from .core import abstractive, analysis, evaluation, export, ingest, keywords
from .core.extractive import EXTRACTIVE_METHODS, summarize_extractive
from .core.hybrid import summarize_hybrid
from .core.text import word_count
from .schemas import (ALL_METHODS, CompareRequest, EvaluateRequest, ExportRequest, SummarizeRequest, TextRequest,
                      UrlRequest)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="AI Text Summarizer API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

_cache: OrderedDict[str, dict] = OrderedDict()


def _check_text(text: str) -> str:
    text = text.strip()
    if len(text) < 40:
        raise HTTPException(422, "Add at least a couple of sentences to work with.")
    if len(text) > config.MAX_CHARS:
        raise HTTPException(413, f"Text is too long. The limit is {config.MAX_CHARS:,} characters.")
    return text


def _label(method: str) -> str:
    if method in EXTRACTIVE_METHODS:
        return EXTRACTIVE_METHODS[method]["label"]
    return {"abstractive": "Abstractive (AI)", "hybrid": "Hybrid (extract + rewrite)"}.get(method, method)


def run_method(text: str, method: str, ratio: float, num_sentences: int | None, diversity: float, model: str) -> dict:
    if method not in ALL_METHODS:
        raise HTTPException(422, f"Unknown method '{method}'. Choose one of: {', '.join(ALL_METHODS)}")
    key = hashlib.sha1(json.dumps([text, method, ratio, num_sentences, diversity, model]).encode()).hexdigest()
    if key in _cache:
        _cache.move_to_end(key)
        return {**_cache[key], "cached": True}

    t0 = time.perf_counter()
    try:
        if method in EXTRACTIVE_METHODS:
            out = summarize_extractive(text, method, ratio, num_sentences, diversity)
        elif method == "abstractive":
            out = abstractive.summarize(text, model, ratio)
        else:
            out = summarize_hybrid(text, model, ratio)
    except abstractive.AbstractiveUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    out.update(
        method=method,
        label=_label(method),
        elapsed_ms=round((time.perf_counter() - t0) * 1000),
        metrics=evaluation.summary_metrics(text, out["summary"]),
        cached=False,
    )
    _cache[key] = out
    while len(_cache) > config.CACHE_SIZE:
        _cache.popitem(last=False)
    return out


@app.get("/api/health")
def health():
    return {"status": "ok", "abstractive_available": abstractive.is_available()}


@app.get("/api/methods")
def methods():
    avail = abstractive.is_available()
    items = [{"id": k, "label": v["label"], "description": v["description"], "kind": "extractive"}
             for k, v in EXTRACTIVE_METHODS.items()]
    items.append({"id": "abstractive", "label": "Abstractive (AI)", "kind": "abstractive",
                  "description": "A transformer writes a new summary in its own words."})
    items.append({"id": "hybrid", "label": "Hybrid (extract + rewrite)", "kind": "hybrid",
                  "description": "TextRank trims long text first, then a transformer rewrites it."})
    return {
        "methods": items,
        "abstractive_available": avail,
        "models": [{"id": k, "label": v["label"]} for k, v in abstractive.MODELS.items()],
        "default_model": abstractive.DEFAULT_MODEL,
    }


@app.post("/api/summarize")
def summarize(req: SummarizeRequest):
    text = _check_text(req.text)
    out = run_method(text, req.method, req.ratio, req.num_sentences, req.diversity, req.model)
    history_id = None
    if req.save and out["summary"]:
        history_id = db.add(req.title, out["label"], text, out["summary"], out["metrics"])
    return {**out, "history_id": history_id}


@app.post("/api/compare")
def compare(req: CompareRequest):
    text = _check_text(req.text)
    results = []
    for m in dict.fromkeys(req.methods):  # de-duplicate, keep order
        try:
            out = run_method(text, m, req.ratio, None, req.diversity, req.model)
            item = {"method": m, "label": out["label"], "summary": out["summary"], "elapsed_ms": out["elapsed_ms"],
                    "metrics": out["metrics"], "error": None}
            if req.reference and req.reference.strip():
                item["rouge"] = evaluation.rouge(req.reference, out["summary"])
        except HTTPException as exc:
            item = {"method": m, "label": _label(m), "summary": "", "elapsed_ms": 0, "metrics": {},
                    "error": exc.detail}
        results.append(item)
    return {"results": results, "has_reference": bool(req.reference and req.reference.strip())}


@app.post("/api/analyze")
def analyze(req: TextRequest):
    return analysis.analyze(_check_text(req.text))


@app.post("/api/keywords")
def get_keywords(req: TextRequest):
    return {"keywords": keywords.extract_keywords(_check_text(req.text), req.method, req.top_k)}


@app.post("/api/evaluate")
def evaluate(req: EvaluateRequest):
    out = {"rouge": evaluation.rouge(req.reference, req.summary)}
    if req.source:
        out["metrics"] = evaluation.summary_metrics(req.source, req.summary)
    return out


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    data = file.file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {config.MAX_UPLOAD_MB} MB.")
    try:
        title, text = ingest.extract_text(file.filename or "", data)
    except ingest.IngestError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"title": title, "text": text[: config.MAX_CHARS], "words": word_count(text), "truncated": len(text) > config.MAX_CHARS}


@app.post("/api/fetch-url")
def fetch_url(req: UrlRequest):
    try:
        title, text = ingest.fetch_url(req.url)
    except ingest.IngestError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"title": title, "text": text[: config.MAX_CHARS], "words": word_count(text), "truncated": len(text) > config.MAX_CHARS}


@app.post("/api/export")
def export_summary(req: ExportRequest):
    if req.format == "docx":
        body = export.to_docx(req.title, req.summary, req.keywords, req.method)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif req.format == "md":
        body, media = export.to_markdown(req.title, req.summary, req.keywords, req.method).encode(), "text/markdown"
    else:
        body, media = req.summary.encode(), "text/plain"
    return Response(body, media_type=media, headers={"Content-Disposition": f'attachment; filename="summary.{req.format}"'})


@app.get("/api/history")
def history():
    return {"items": db.list_items()}


@app.get("/api/history/{item_id}")
def history_item(item_id: int):
    item = db.get(item_id)
    if not item:
        raise HTTPException(404, "That history item no longer exists.")
    return item


@app.delete("/api/history/{item_id}")
def history_delete(item_id: int):
    if not db.delete(item_id):
        raise HTTPException(404, "That history item no longer exists.")
    return {"deleted": item_id}


@app.delete("/api/history")
def history_clear():
    db.clear()
    return {"cleared": True}
