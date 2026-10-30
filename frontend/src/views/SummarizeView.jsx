import { useEffect, useRef, useState } from "react";
import { api, saveBlob } from "../api";
import { Empty, Icon, Slider, Spinner, Stat, pct } from "../components/ui";

export default function SummarizeView({ active, doc, meta, setHighlights, notify }) {
  const [method, setMethod] = useState("textrank");
  const [ratio, setRatio] = useState(0.25);
  const [diversity, setDiversity] = useState(0.3);
  const [model, setModel] = useState("distilbart");
  const [result, setResult] = useState(null);
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const runRef = useRef();

  const current = meta?.methods.find((m) => m.id === method);
  const isExtractive = current?.kind === "extractive";
  const usesModel = current?.kind === "abstractive" || current?.kind === "hybrid";

  async function run() {
    if (doc.text.trim().length < 40) {
      notify("Add at least a couple of sentences to summarize.", "error");
      return;
    }
    setLoading(true);
    setError(null);
    window.speechSynthesis?.cancel();
    setSpeaking(false);
    try {
      const [res, kw] = await Promise.all([
        api.summarize({ text: doc.text, title: doc.title, method, ratio, diversity, model }),
        api.keywords({ text: doc.text, top_k: 12 }).catch(() => ({ keywords: [] })),
      ]);
      setResult(res);
      setKeywords(kw.keywords);
      setHighlights(res.sentences || null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  runRef.current = run;

  useEffect(() => {
    if (!active) return undefined;
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(result.summary);
      notify("Summary copied");
    } catch {
      notify("Couldn't copy. Select the text and copy it manually.", "error");
    }
  }

  async function download(format) {
    try {
      const blob = await api.exportFile({ format, title: doc.title || "Summary", summary: result.summary,
        keywords: keywords.map((k) => k.keyword), method: result.label });
      saveBlob(blob, `summary.${format}`);
    } catch (e) {
      notify(e.message, "error");
    }
  }

  function speak() {
    const synth = window.speechSynthesis;
    if (!synth) return notify("Speech isn't supported in this browser.", "error");
    if (speaking) {
      synth.cancel();
      return setSpeaking(false);
    }
    const u = new SpeechSynthesisUtterance(result.summary);
    u.onend = () => setSpeaking(false);
    synth.speak(u);
    return setSpeaking(true);
  }

  const m = result?.metrics;
  const groups = [
    ["Extractive: picks sentences from your text", "extractive"],
    ["Abstractive: writes new sentences", "abstractive"],
    ["Hybrid: both", "hybrid"],
  ];

  return (
    <div className="view">
      <div className="panel controls">
        <div className="control-grid">
          <label className="field">
            <span className="field-head"><span>Method</span></span>
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              {groups.map(([label, kind]) => (
                <optgroup key={kind} label={label}>
                  {meta?.methods.filter((x) => x.kind === kind).map((x) => (
                    <option key={x.id} value={x.id}>{x.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
            <span className="hint">{current?.description}</span>
          </label>

          <Slider label="Summary length" value={ratio} min={0.05} max={0.6} step={0.05}
            onChange={setRatio} format={(v) => `${Math.round(v * 100)}% of the text`} />

          {isExtractive && (
            <Slider label="Variety" value={diversity} min={0} max={0.8} step={0.1} onChange={setDiversity}
              format={(v) => (v === 0 ? "Off" : v.toFixed(1))} hint="Higher values avoid picking near-duplicate sentences." />
          )}

          {usesModel && (
            <label className="field">
              <span className="field-head"><span>AI model</span></span>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {meta?.models.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
              </select>
              <span className="hint">
                {meta?.abstractive_available ? "Downloads on first use, then stays cached." : "Needs the optional ML packages (see README)."}
              </span>
            </label>
          )}
        </div>
        <div className="actions">
          <button className="btn primary" onClick={run} disabled={loading}>
            {loading ? <Spinner label="Summarizing" /> : <><Icon name="play" size={16} /> Summarize</>}
          </button>
          <small className="kbd-hint">Ctrl + Enter</small>
        </div>
      </div>

      {error && <div className="notice error" role="alert">{error}</div>}

      {!result && !error && !loading && (
        <Empty title="Your summary will appear here">
          Add text on the left, choose a method and press Summarize. For extractive methods, the sentences it keeps are marked in your document.
        </Empty>
      )}

      {result && (
        <article className="panel result" aria-live="polite">
          <header className="result-head">
            <h2>{result.label}</h2>
            <div className="toolbar">
              <button className="icon-btn" onClick={copy} title="Copy summary" aria-label="Copy summary"><Icon name="copy" /></button>
              <button className="icon-btn" onClick={speak} title={speaking ? "Stop reading" : "Read aloud"} aria-label="Read aloud">
                <Icon name={speaking ? "stop" : "speaker"} />
              </button>
              <span className="divider" />
              {["txt", "md", "docx"].map((f) => (
                <button key={f} className="btn small" onClick={() => download(f)} title={`Download as .${f}`}>
                  <Icon name="download" size={14} /> {f}
                </button>
              ))}
            </div>
          </header>

          <div className="summary-text">
            {result.summary.split(/\n{2,}/).map((p, i) => <p key={i}>{p}</p>)}
          </div>

          {result.model && <p className="meta-line">Model: {result.model}{result.chunks > 1 ? `, merged from ${result.chunks} chunks` : ""}{result.device ? `, ran on ${result.device}` : ""}</p>}

          <div className="stats">
            <Stat value={m.source_words.toLocaleString()} label="words in" />
            <Stat value={m.summary_words.toLocaleString()} label="words out" />
            <Stat value={`${m.reduction_pct}%`} label="shorter" />
            <Stat value={pct(m.keyword_coverage)} label="key terms kept" />
            <Stat value={result.elapsed_ms < 1000 ? `${result.elapsed_ms} ms` : `${(result.elapsed_ms / 1000).toFixed(1)} s`} label={result.cached ? "from cache" : "to generate"} />
          </div>

          {keywords.length > 0 && (
            <div className="keywords">
              <h3>Key terms</h3>
              <ul className="chips">
                {keywords.map((k) => (
                  <li key={k.keyword} style={{ "--w": k.score }}>{k.keyword}</li>
                ))}
              </ul>
            </div>
          )}
        </article>
      )}
    </div>
  );
}
