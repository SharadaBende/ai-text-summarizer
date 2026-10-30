from app.core import analysis, evaluation, keywords
from app.core.extractive import EXTRACTIVE_METHODS, summarize_extractive
from app.core.text import count_syllables, split_sentences

TEXT = (
    "Solar power is growing quickly across the world. Dr. Smith said that new solar panels cost far less than "
    "a decade ago. Wind power is also expanding, especially offshore. Governments are funding grid upgrades so "
    "that renewable energy can reach more homes. Critics warn that storage remains expensive. Batteries are "
    "getting cheaper every year, which makes solar and wind more reliable. The International Energy Agency "
    "expects renewables to supply most new electricity by 2030. Many farmers now lease land for solar farms. "
    "Local communities benefit from jobs and tax revenue. Still, mining the minerals for batteries raises "
    "environmental questions that researchers are working to answer."
)


def test_sentence_splitter_handles_abbreviations():
    s = split_sentences("Dr. Smith arrived at 5 p.m. today. He left early! Was it U.S. policy? Yes.")
    assert s[0].startswith("Dr. Smith") and len(s) == 4


def test_syllables():
    assert count_syllables("cat") == 1 and count_syllables("reliable") >= 3


def test_every_extractive_method_returns_requested_length():
    n = len(split_sentences(TEXT))
    for m in EXTRACTIVE_METHODS:
        out = summarize_extractive(TEXT, m, ratio=0.3)
        assert len(out["selected_indices"]) == round(n * 0.3), m
        assert out["summary"] and len(out["sentences"]) == n


def test_num_sentences_overrides_ratio_and_order_is_preserved():
    out = summarize_extractive(TEXT, "textrank", ratio=0.9, num_sentences=2)
    assert out["selected_indices"] == sorted(out["selected_indices"]) and len(out["selected_indices"]) == 2


def test_lead_picks_first_sentence():
    assert summarize_extractive(TEXT, "lead", ratio=0.1, diversity=0)["selected_indices"] == [0]


def test_empty_and_tiny_inputs_do_not_crash():
    assert summarize_extractive("", "textrank")["summary"] == ""
    assert summarize_extractive("One short sentence here.", "lsa")["summary"]


def test_rouge_identity_and_disjoint():
    assert evaluation.rouge("the cat sat", "the cat sat")["rougeL"]["f1"] == 1.0
    assert evaluation.rouge("alpha beta", "gamma delta")["rouge1"]["f1"] == 0.0


def test_summary_metrics_are_sane():
    out = summarize_extractive(TEXT, "textrank", ratio=0.3)
    m = evaluation.summary_metrics(TEXT, out["summary"])
    assert 0 < m["compression_ratio"] < 1 and 0 <= m["keyword_coverage"] <= 1


def test_keywords_and_rake():
    assert keywords.tfidf_keywords(TEXT, 5)
    assert any("solar" in k["keyword"] for k in keywords.rake_keywords(TEXT, 8))


def test_analysis_bundle():
    a = analysis.analyze(TEXT)
    assert a["stats"]["sentences"] == 10 and a["sentiment"]["label"] in {"Positive", "Neutral", "Negative"}
    assert a["readability"]["flesch_reading_ease"] > 0
    assert analysis.sentiment("This is not good at all")["compound"] < 0
