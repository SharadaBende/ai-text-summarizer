"""Streamlit analytics dashboard: dataset EDA, method benchmark, length sensitivity, live playground.

Run from the project root:  streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core import abstractive, analysis, evaluation  # noqa: E402
from app.core.extractive import EXTRACTIVE_METHODS, summarize_extractive  # noqa: E402
from app.core.text import split_sentences, word_count  # noqa: E402

st.set_page_config(page_title="Summarizer analytics", page_icon="📊", layout="wide")
sns.set_theme(style="whitegrid", context="notebook")
PALETTE = sns.color_palette("viridis", 8)


@st.cache_data(show_spinner=False)
def load_sample() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "sample_articles.csv")


@st.cache_data(show_spinner="Loading CNN/DailyMail…")
def load_cnn(n: int) -> pd.DataFrame:
    from datasets import load_dataset  # optional dependency

    ds = load_dataset("cnn_dailymail", "3.0.0", split=f"test[:{n}]")
    return pd.DataFrame({"id": range(len(ds)), "topic": "news", "article": ds["article"], "reference": ds["highlights"]})


@st.cache_data(show_spinner="Running benchmark…")
def benchmark(df: pd.DataFrame, methods: tuple, ratio: float, use_model: str | None) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        for m in methods:
            t0 = time.perf_counter()
            if m in EXTRACTIVE_METHODS:
                summary = summarize_extractive(r["article"], m, ratio)["summary"]
            else:
                summary = abstractive.summarize(r["article"], use_model or "distilbart", ratio)["summary"]
            ms = (time.perf_counter() - t0) * 1000
            sc = evaluation.rouge(r["reference"], summary)
            met = evaluation.summary_metrics(r["article"], summary)
            rows.append({"id": r["id"], "method": m, "rouge1": sc["rouge1"]["f1"], "rouge2": sc["rouge2"]["f1"],
                         "rougeL": sc["rougeL"]["f1"], "coverage": met["keyword_coverage"],
                         "compression": met["compression_ratio"], "ms": ms, "words": met["summary_words"]})
    return pd.DataFrame(rows)


st.sidebar.title("Summarizer analytics")
page = st.sidebar.radio("Page", ["Dataset EDA", "Method benchmark", "Length sensitivity", "Playground"])

st.sidebar.divider()
source = st.sidebar.selectbox("Dataset", ["Bundled sample (6 articles)", "Upload CSV", "CNN/DailyMail (needs `datasets`)"])
if source.startswith("Bundled"):
    df = load_sample()
elif source.startswith("Upload"):
    up = st.sidebar.file_uploader("CSV with `article` and `reference` columns", type="csv")
    df = pd.read_csv(up) if up else load_sample()
    if "id" not in df:
        df["id"] = range(len(df))
else:
    n = st.sidebar.slider("Articles", 20, 500, 100, step=20)
    try:
        df = load_cnn(n)
    except Exception as exc:
        st.sidebar.error(f"Could not load CNN/DailyMail: {exc}")
        df = load_sample()

if not {"article", "reference"} <= set(df.columns):
    st.error("The dataset needs `article` and `reference` columns.")
    st.stop()

# ----------------------------------------------------------------------------------------------
if page == "Dataset EDA":
    st.title("Dataset exploration")
    df = df.assign(
        article_words=df["article"].map(word_count),
        reference_words=df["reference"].map(word_count),
        sentences=df["article"].map(lambda t: len(split_sentences(t))),
    )
    df["compression"] = df["reference_words"] / df["article_words"]
    c = st.columns(4)
    c[0].metric("Articles", len(df))
    c[1].metric("Avg article words", f"{df.article_words.mean():.0f}")
    c[2].metric("Avg reference words", f"{df.reference_words.mean():.0f}")
    c[3].metric("Avg compression", f"{df.compression.mean():.0%}")

    fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
    sns.histplot(df.article_words, bins=15, ax=ax[0], color=PALETTE[2]).set(title="Article length (words)")
    sns.histplot(df.reference_words, bins=15, ax=ax[1], color=PALETTE[5]).set(title="Reference length (words)")
    sns.scatterplot(data=df, x="article_words", y="reference_words", ax=ax[2], color=PALETTE[3]).set(
        title="Reference vs article length")
    st.pyplot(fig)

    all_text = " ".join(df["article"])
    stats = analysis.text_stats(all_text)
    top = pd.DataFrame(stats["top_words"])
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Most frequent content words")
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.barplot(data=top, y="word", x="count", ax=ax, color=PALETTE[4])
        st.pyplot(fig)
    with c2:
        st.subheader("Corpus facts")
        r = analysis.readability(all_text)
        st.dataframe(pd.DataFrame({
            "Measure": ["Lexical diversity", "Avg sentence length", "Flesch reading ease", "Grade level", "Sentiment"],
            "Value": [stats["lexical_diversity"], stats["avg_sentence_words"], r["flesch_reading_ease"],
                      r["flesch_kincaid_grade"], analysis.sentiment(all_text)["label"]]}), hide_index=True)
    st.subheader("Data")
    st.dataframe(df[["id", "topic", "article_words", "reference_words", "sentences"]], hide_index=True)

# ----------------------------------------------------------------------------------------------
elif page == "Method benchmark":
    st.title("Method benchmark")
    c1, c2 = st.columns([3, 1])
    methods = c1.multiselect("Methods", list(EXTRACTIVE_METHODS) + ["abstractive"],
                             default=["lead", "tfidf", "textrank", "lsa"])
    ratio = c2.slider("Summary ratio", 0.1, 0.6, 0.25, 0.05)
    if "abstractive" in methods and not abstractive.is_available():
        st.warning("Install `requirements-ml.txt` to benchmark the abstractive model. Skipping it.")
        methods = [m for m in methods if m != "abstractive"]
    if not methods:
        st.stop()
    res = benchmark(df, tuple(methods), ratio, None)
    agg = res.groupby("method")[["rouge1", "rouge2", "rougeL", "coverage", "compression", "ms"]].mean().round(3)
    st.subheader("Average scores")
    st.dataframe(agg.sort_values("rougeL", ascending=False).style.background_gradient(cmap="viridis", axis=0))

    long = res.melt(id_vars=["id", "method"], value_vars=["rouge1", "rouge2", "rougeL"], var_name="metric")
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.2))
    sns.barplot(data=long, x="metric", y="value", hue="method", ax=ax[0], palette="viridis", errorbar="sd")
    ax[0].set(title="ROUGE F1 by method (error bars: std dev)", ylabel="F1")
    sns.scatterplot(data=res, x="ms", y="rougeL", hue="method", s=90, ax=ax[1], palette="viridis")
    ax[1].set(title="Quality vs speed", xlabel="Time per summary (ms)", ylabel="ROUGE-L F1")
    st.pyplot(fig)

    st.subheader("Per-article ROUGE-L")
    heat = res.pivot(index="id", columns="method", values="rougeL")
    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.4 * len(heat))))
    sns.heatmap(heat, annot=len(heat) <= 25, fmt=".2f", cmap="viridis", ax=ax)
    st.pyplot(fig)
    st.download_button("Download results (CSV)", res.to_csv(index=False), "benchmark.csv", "text/csv")

# ----------------------------------------------------------------------------------------------
elif page == "Length sensitivity":
    st.title("How summary length changes quality")
    methods = st.multiselect("Methods", list(EXTRACTIVE_METHODS), default=["lead", "textrank", "lsa"])
    ratios = [0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6]
    rows = []
    with st.spinner("Scoring…"):
        for m in methods:
            for ratio in ratios:
                for _, r in df.iterrows():
                    s = summarize_extractive(r["article"], m, ratio)["summary"]
                    sc = evaluation.rouge(r["reference"], s)
                    rows.append({"method": m, "ratio": ratio, "ROUGE-L recall": sc["rougeL"]["recall"],
                                 "ROUGE-L precision": sc["rougeL"]["precision"], "ROUGE-L F1": sc["rougeL"]["f1"]})
    if rows:
        d = pd.DataFrame(rows).groupby(["method", "ratio"]).mean().reset_index()
        fig, ax = plt.subplots(1, 3, figsize=(15, 4))
        for a, col in zip(ax, ["ROUGE-L precision", "ROUGE-L recall", "ROUGE-L F1"]):
            sns.lineplot(data=d, x="ratio", y=col, hue="method", marker="o", ax=a, palette="viridis")
            a.set_title(col)
        st.pyplot(fig)
        st.caption("Longer summaries raise recall but lower precision; F1 shows the sweet spot for each method.")

# ----------------------------------------------------------------------------------------------
else:
    st.title("Playground")
    text = st.text_area("Paste text", df["article"].iloc[0], height=220)
    c1, c2 = st.columns(2)
    method = c1.selectbox("Method", list(EXTRACTIVE_METHODS), index=3)
    ratio = c2.slider("Ratio", 0.1, 0.7, 0.3, 0.05)
    if text.strip():
        out = summarize_extractive(text, method, ratio)
        st.subheader("Summary")
        st.write(out["summary"])
        sc = pd.DataFrame(out["sentences"])
        fig, ax = plt.subplots(figsize=(10, 0.35 * len(sc) + 1))
        colors = [PALETTE[5] if s else "#c8ccd4" for s in sc.selected]
        ax.barh(sc["index"] + 1, sc["score"], color=colors)
        ax.invert_yaxis()
        ax.set(xlabel="Sentence score", ylabel="Sentence #", title="Sentence scores (selected in colour)")
        st.pyplot(fig)
