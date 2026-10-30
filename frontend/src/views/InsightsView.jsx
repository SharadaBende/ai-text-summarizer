import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { Empty, Icon, Spinner, Stat, pct } from "../components/ui";

const tip = { background: "var(--card)", border: "1px solid var(--line)", borderRadius: 8 };

function histogram(lengths, size = 5) {
  const bins = {};
  lengths.forEach((n) => {
    const b = Math.floor(n / size) * size;
    bins[b] = (bins[b] || 0) + 1;
  });
  const max = Math.max(0, ...Object.keys(bins).map(Number));
  return Array.from({ length: max / size + 1 }, (_, i) => ({ range: `${i * size}-${i * size + size - 1}`, sentences: bins[i * size] || 0 }));
}

export default function InsightsView({ doc, notify }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (doc.text.trim().length < 40) return notify("Add some text on the left first.", "error");
    setLoading(true);
    try {
      setData(await api.analyze({ text: doc.text }));
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setLoading(false);
    }
    return undefined;
  }

  const s = data?.stats;
  const sent = data?.sentiment;

  return (
    <div className="view">
      <div className="panel controls row-between">
        <div>
          <h2>Document insights</h2>
          <p className="hint">Length, readability, tone, key terms, names and topics, all computed from your text.</p>
        </div>
        <button className="btn primary" onClick={run} disabled={loading}>
          {loading ? <Spinner label="Analyzing" /> : <><Icon name="chart" size={16} /> Analyze document</>}
        </button>
      </div>

      {!data && <Empty title="See what your document is made of">Run the analysis to get reading time, difficulty, sentiment, key phrases, names and topics.</Empty>}

      {data && (
        <>
          <div className="panel stats wide">
            <Stat value={s.words.toLocaleString()} label="words" />
            <Stat value={s.sentences} label="sentences" />
            <Stat value={`${s.reading_time_min} min`} label="to read" />
            <Stat value={s.avg_sentence_words} label="words per sentence" />
            <Stat value={pct(s.lexical_diversity)} label="unique words" />
          </div>

          <div className="two-col">
            <div className="panel">
              <h3>Readability</h3>
              <p className="big">{data.readability.level}</p>
              <dl className="facts">
                <div><dt>Flesch reading ease</dt><dd>{data.readability.flesch_reading_ease}</dd></div>
                <div><dt>US school grade</dt><dd>{data.readability.flesch_kincaid_grade}</dd></div>
                <div><dt>Gunning fog</dt><dd>{data.readability.gunning_fog}</dd></div>
              </dl>
            </div>
            <div className="panel">
              <h3>Tone</h3>
              <p className="big">{sent.label}</p>
              <div className="tone-bar" role="img" aria-label={`${sent.positive_words} positive and ${sent.negative_words} negative words`}>
                <span className="pos" style={{ flexGrow: sent.positive_words || 0.0001 }} />
                <span className="neg" style={{ flexGrow: sent.negative_words || 0.0001 }} />
              </div>
              <p className="hint">{sent.positive_words} positive words, {sent.negative_words} negative words. Score {sent.compound}.</p>
            </div>
          </div>

          <div className="two-col">
            <div className="panel">
              <h3>Key terms</h3>
              <ul className="chips">{data.keywords.map((k) => <li key={k.keyword} style={{ "--w": k.score }}>{k.keyword}</li>)}</ul>
              <h3 className="spaced">Key phrases</h3>
              <ul className="chips alt">{data.keyphrases.map((k) => <li key={k.keyword}>{k.keyword}</li>)}</ul>
            </div>
            <div className="panel">
              <h3>Names and places</h3>
              {data.entities.length ? (
                <ul className="chips alt">{data.entities.map((e) => <li key={e.text}>{e.text}{e.count > 1 ? ` (${e.count})` : ""}</li>)}</ul>
              ) : <p className="hint">No named entities found.</p>}
              {data.topics.length > 0 && (
                <>
                  <h3 className="spaced">Topics</h3>
                  <ul className="topics">
                    {data.topics.map((t) => (
                      <li key={t.id}><span>{t.words.join(", ")}</span><em>{pct(t.share)}</em></li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>

          <div className="two-col">
            <div className="panel">
              <h3>Most used words</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={s.top_words.slice(0, 10)} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <CartesianGrid horizontal={false} stroke="var(--line)" />
                  <XAxis type="number" stroke="var(--muted)" allowDecimals={false} />
                  <YAxis type="category" dataKey="word" width={90} stroke="var(--muted)" />
                  <Tooltip contentStyle={tip} />
                  <Bar dataKey="count" fill="var(--accent)" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="panel">
              <h3>Sentence length</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={histogram(s.sentence_lengths)} margin={{ right: 8 }}>
                  <CartesianGrid vertical={false} stroke="var(--line)" />
                  <XAxis dataKey="range" stroke="var(--muted)" label={{ value: "words per sentence", position: "insideBottom", offset: -2, fill: "var(--muted)" }} height={44} />
                  <YAxis stroke="var(--muted)" allowDecimals={false} />
                  <Tooltip contentStyle={tip} />
                  <Bar dataKey="sentences" fill="var(--teal)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
