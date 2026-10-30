import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Empty, Icon, Segmented, Slider, Spinner, pct } from "../components/ui";

const METRICS = [
  { id: "rougeL", label: "ROUGE-L", ref: true, get: (r) => r.rouge?.rougeL.f1, fmt: (v) => v.toFixed(3) },
  { id: "rouge1", label: "ROUGE-1", ref: true, get: (r) => r.rouge?.rouge1.f1, fmt: (v) => v.toFixed(3) },
  { id: "rouge2", label: "ROUGE-2", ref: true, get: (r) => r.rouge?.rouge2.f1, fmt: (v) => v.toFixed(3) },
  { id: "coverage", label: "Key terms kept", get: (r) => r.metrics.keyword_coverage, fmt: (v) => pct(v) },
  { id: "similarity", label: "Similarity to source", get: (r) => r.metrics.similarity, fmt: (v) => v.toFixed(2) },
  { id: "speed", label: "Time (ms)", get: (r) => r.elapsed_ms, fmt: (v) => `${v} ms` },
];

export default function CompareView({ doc, meta, notify }) {
  const [picked, setPicked] = useState(["lead", "tfidf", "textrank", "lsa"]);
  const [ratio, setRatio] = useState(0.25);
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [metric, setMetric] = useState("coverage");

  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  async function run() {
    if (doc.text.trim().length < 40) return notify("Add some text on the left first.", "error");
    if (!picked.length) return notify("Pick at least one method to compare.", "error");
    setLoading(true);
    try {
      const res = await api.compare({ text: doc.text, methods: picked, ratio, reference: reference.trim() || null });
      setData(res);
      setMetric(res.has_reference ? "rougeL" : "coverage");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setLoading(false);
    }
    return undefined;
  }

  const options = METRICS.filter((m) => !m.ref || data?.has_reference);
  const active = METRICS.find((m) => m.id === metric) || METRICS[3];
  const ok = data?.results.filter((r) => !r.error) || [];
  const chart = ok.map((r) => ({ name: r.label, value: active.get(r) ?? 0 }));
  const best = chart.length ? (metric === "speed" ? Math.min : Math.max)(...chart.map((c) => c.value)) : 0;

  return (
    <div className="view">
      <div className="panel controls">
        <h2>Methods to compare</h2>
        <ul className="chips pickable">
          {meta?.methods.map((m) => {
            const off = m.kind !== "extractive" && !meta.abstractive_available;
            return (
              <li key={m.id}>
                <button className={picked.includes(m.id) ? "on" : ""} disabled={off} onClick={() => toggle(m.id)}
                  aria-pressed={picked.includes(m.id)} title={off ? "Install requirements-ml.txt to enable" : m.description}>
                  {m.label}
                </button>
              </li>
            );
          })}
        </ul>
        <Slider label="Summary length" value={ratio} min={0.05} max={0.6} step={0.05} onChange={setRatio}
          format={(v) => `${Math.round(v * 100)}% of the text`} />
        <details className="reference">
          <summary>Score against a reference summary (optional)</summary>
          <p className="hint">Paste a human-written summary to add ROUGE-1, ROUGE-2 and ROUGE-L scores.</p>
          <textarea rows={4} value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Reference summary" />
        </details>
        <div className="actions">
          <button className="btn primary" onClick={run} disabled={loading}>
            {loading ? <Spinner label="Comparing" /> : <><Icon name="columns" size={16} /> Compare methods</>}
          </button>
        </div>
      </div>

      {!data && <Empty title="Compare summarizers side by side">Choose two or more methods and see which one keeps the most of what matters.</Empty>}

      {data && (
        <>
          <div className="panel">
            <div className="chart-head">
              <h2>Scores</h2>
              <Segmented label="Metric" value={metric} onChange={setMetric} options={options} />
            </div>
            <div className="chart" role="img" aria-label={`Bar chart of ${active.label} by method`}>
              <ResponsiveContainer width="100%" height={Math.max(180, chart.length * 46)}>
                <BarChart data={chart} layout="vertical" margin={{ left: 8, right: 32 }}>
                  <CartesianGrid horizontal={false} stroke="var(--line)" />
                  <XAxis type="number" stroke="var(--muted)" tickFormatter={(v) => (active.id === "coverage" ? pct(v) : v)} />
                  <YAxis type="category" dataKey="name" width={150} stroke="var(--muted)" />
                  <Tooltip formatter={(v) => active.fmt(v)} contentStyle={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: 8 }} />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                    {chart.map((c) => <Cell key={c.name} fill={c.value === best ? "var(--accent)" : "var(--bar-muted)"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Method</th><th>Words</th><th>Key terms kept</th><th>Similarity</th><th>Repetition</th>
                    {data.has_reference && <><th>ROUGE-1</th><th>ROUGE-2</th><th>ROUGE-L</th></>}
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((r) => (
                    <tr key={r.method}>
                      <td>{r.label}</td>
                      {r.error ? <td colSpan={data.has_reference ? 8 : 5} className="err">{r.error}</td> : (
                        <>
                          <td>{r.metrics.summary_words}</td>
                          <td>{pct(r.metrics.keyword_coverage)}</td>
                          <td>{r.metrics.similarity.toFixed(2)}</td>
                          <td>{r.metrics.redundancy.toFixed(2)}</td>
                          {data.has_reference && <><td>{r.rouge.rouge1.f1.toFixed(3)}</td><td>{r.rouge.rouge2.f1.toFixed(3)}</td><td>{r.rouge.rougeL.f1.toFixed(3)}</td></>}
                          <td>{r.elapsed_ms} ms</td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="hint">Repetition is how similar the summary's own sentences are to each other. Lower is better.</p>
          </div>

          <div className="cards">
            {ok.map((r) => (
              <article key={r.method} className="panel mini">
                <h3>{r.label}</h3>
                <p>{r.summary}</p>
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
