# AI Text Summarizer

A full-stack NLP project: **FastAPI** backend with six extractive algorithms plus transformer-based abstractive and hybrid summarisation, a **React** workspace that highlights what was kept, and a **Streamlit** dashboard for evaluation and EDA.

```
┌────────────────────┐   /api    ┌─────────────────────────────┐
│ React (Vite)       │──────────▶│ FastAPI                     │
│ document pane,     │           │  core/extractive  (sklearn) │
│ summarize, compare,│           │  core/abstractive (HF)      │
│ insights, history  │           │  core/hybrid                │
└────────────────────┘           │  core/evaluation (ROUGE)    │
┌────────────────────┐  imports  │  core/analysis, keywords    │
│ Streamlit dashboard│──────────▶│  core/ingest (PDF/DOCX/URL) │
│ EDA, benchmarks    │           │  SQLite history             │
└────────────────────┘           └─────────────────────────────┘
```

## Features

**Summarization**
- Extractive: Lead, Word frequency, TF-IDF, TextRank, LSA, Centroid
- Variety control (Maximal Marginal Relevance) to avoid near-duplicate sentences
- Abstractive: DistilBART, BART-large-CNN, T5-small, PEGASUS-XSum, mT5 (multilingual)
- Hybrid: TextRank trims long text, then a transformer rewrites it
- Long documents: sentence-aware chunking with map-reduce merging
- Adjustable length (% of the text), GPU/MPS/CPU auto-detection, request cache

**Input**: paste, upload PDF / DOCX / TXT / Markdown / HTML, or fetch a web page (with SSRF protection)

**Evaluation**: ROUGE-1/2/L (precision, recall, F1), key-term coverage, similarity to source, repetition, compression, latency

**Insights**: reading time, readability (Flesch, grade level, Gunning fog), sentiment, TF-IDF keywords, RAKE key phrases, named entities (spaCy if installed), NMF topic modelling, word and sentence-length charts

**App**: marker-style highlighting of selected sentences, side-by-side comparison with charts, copy, read aloud, export to TXT / Markdown / DOCX, saved history, dark mode, keyboard shortcut (Ctrl+Enter), responsive layout

**Dashboard (Streamlit, Matplotlib, Seaborn, Pandas)**: dataset EDA, method benchmark with heatmaps, quality-vs-speed plot, length sensitivity curves, playground; bundled sample data, CSV upload, or CNN/DailyMail

## Quick start

Requires Python 3.10+ and Node 18+.

```bash
# 1. Backend (classic ML only, runs on any laptop)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload                          # http://localhost:8000/docs

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                                            # http://localhost:5173

# 3. Dashboard (new terminal, from the project root)
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py                         # http://localhost:8501
```

### Enable abstractive and hybrid models

```bash
cd backend
pip install -r requirements-ml.txt
```

Models download from Hugging Face on first use (DistilBART is about 1.2 GB; T5-small about 240 MB) and are then cached. On a CPU-only laptop, start with **DistilBART** or **T5 small**. Optional: `pip install spacy && python -m spacy download en_core_web_sm` for better entity recognition.

### Docker

```bash
docker compose up --build            # app :8080, API :8000, dashboard :8501
docker compose build --build-arg WITH_ML=true backend    # include transformer support
```

## API

Interactive docs at `/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health`, `/api/methods` | Status, available methods and models |
| POST | `/api/summarize` | Summarize with any method |
| POST | `/api/compare` | Run several methods, optional ROUGE against a reference |
| POST | `/api/analyze` | Stats, readability, sentiment, keywords, entities, topics |
| POST | `/api/keywords` | TF-IDF or RAKE keywords |
| POST | `/api/evaluate` | ROUGE between a reference and a summary |
| POST | `/api/upload`, `/api/fetch-url` | Extract text from a file or web page |
| POST | `/api/export` | Download TXT, Markdown or DOCX |
| GET/DELETE | `/api/history[/{id}]` | Saved summaries |

```bash
curl -X POST localhost:8000/api/summarize -H 'Content-Type: application/json' \
  -d '{"text": "Your long text here...", "method": "textrank", "ratio": 0.25}'
```

## Project layout

```
backend/app/core/   text.py extractive.py abstractive.py hybrid.py keywords.py analysis.py evaluation.py ingest.py export.py
backend/app/        main.py schemas.py db.py config.py
backend/tests/      unit tests (core) and API tests
frontend/src/       App.jsx, components/, views/, styles.css
dashboard/app.py    Streamlit analytics
data/               sample_articles.csv (6 articles with reference summaries)
```

## Tests

```bash
cd backend && pip install -r requirements-dev.txt && pytest
```

## How the algorithms work

- **TextRank**: sentences are nodes, TF-IDF cosine similarity gives edge weights, PageRank ranks them.
- **LSA**: truncated SVD on the sentence-term matrix; sentences with the largest weight on the main latent topics win.
- **MMR**: after scoring, sentences are picked greedily by `(1 − λ)·score − λ·max similarity to chosen`, which controls redundancy.
- **Abstractive**: sequence-to-sequence transformers generate new text with beam search. Long inputs are split into chunks, summarised, then merged.

## Notes and limits

- ROUGE rewards word overlap, so it favours extractive methods on short texts. Judge abstractive output by reading it too.
- The bundled 6-article sample is for demos; use CNN/DailyMail or your own CSV for meaningful benchmarks.
- Sentiment uses a small built-in lexicon, and the fallback entity detector is heuristic. Both are indicative, not production-grade.
- English is the default. mT5 handles other languages; the extractive methods work on any whitespace-separated language, but stop-word filtering is English only.
- History is stored in a local SQLite file with no authentication. Add auth and rate limiting before exposing the API publicly.

## Ideas to extend

Fine-tune a model on your own data, add BERTScore, add user accounts, stream tokens as they are generated, add a browser extension.
