from __future__ import annotations

from pydantic import BaseModel, Field

ALL_METHODS = ["lead", "frequency", "tfidf", "textrank", "lsa", "centroid", "abstractive", "hybrid"]


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1)
    title: str = ""
    method: str = "textrank"
    ratio: float = Field(0.25, ge=0.03, le=0.9)
    num_sentences: int | None = Field(None, ge=1, le=100)
    diversity: float = Field(0.3, ge=0.0, le=1.0)
    model: str = "distilbart"
    save: bool = True


class CompareRequest(BaseModel):
    text: str = Field(min_length=1)
    methods: list[str] = Field(min_length=1, max_length=8)
    ratio: float = Field(0.25, ge=0.03, le=0.9)
    diversity: float = Field(0.3, ge=0.0, le=1.0)
    model: str = "distilbart"
    reference: str | None = None


class TextRequest(BaseModel):
    text: str = Field(min_length=1)
    top_k: int = Field(12, ge=1, le=40)
    method: str = "tfidf"


class EvaluateRequest(BaseModel):
    reference: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source: str | None = None


class UrlRequest(BaseModel):
    url: str


class ExportRequest(BaseModel):
    format: str = Field("txt", pattern="^(txt|md|docx)$")
    title: str = "Summary"
    summary: str
    keywords: list[str] = []
    method: str = ""
