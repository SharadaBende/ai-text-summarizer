/** Renders the source text sentence by sentence; sentences chosen for the summary get a marker sweep. */
export default function Highlighted({ sentences }) {
  let order = 0;
  return (
    <div className="source-text" aria-label="Source text with summary sentences highlighted">
      {sentences.map((s) => {
        if (!s.selected) return <span key={s.index}>{s.text} </span>;
        const delay = order++ * 90;
        return (
          <span key={s.index}>
            <mark className="mark" style={{ animationDelay: `${delay}ms` }} title={`Relevance ${(s.score * 100).toFixed(0)}%`}>
              {s.text}
            </mark>{" "}
          </span>
        );
      })}
    </div>
  );
}
