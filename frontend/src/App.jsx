import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import DocumentPane from "./components/DocumentPane";
import { Icon, Toast } from "./components/ui";
import CompareView from "./views/CompareView";
import HistoryView from "./views/HistoryView";
import InsightsView from "./views/InsightsView";
import SummarizeView from "./views/SummarizeView";

const VIEWS = [
  { id: "summarize", label: "Summarize", icon: "pen" },
  { id: "compare", label: "Compare", icon: "columns" },
  { id: "insights", label: "Insights", icon: "chart" },
  { id: "history", label: "History", icon: "clock" },
];

function initialTheme() {
  try {
    const saved = localStorage.getItem("theme");
    if (saved) return saved;
  } catch { /* storage unavailable */ }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [view, setView] = useState("summarize");
  const [doc, setDoc] = useState({ text: "", title: "" });
  const [highlights, setHighlights] = useState(null);
  const [meta, setMeta] = useState(null);
  const [offline, setOffline] = useState(null);
  const [theme, setTheme] = useState(initialTheme);
  const [toast, setToast] = useState(null);

  const notify = useCallback((message, kind = "info") => setToast({ message, kind, id: Date.now() }), []);
  const dismissToast = useCallback(() => setToast(null), []);

  // Editing the text invalidates the highlights; changing only the title does not.
  const updateDoc = useCallback((next, keepHighlights = false) => {
    setDoc(next);
    if (!keepHighlights) setHighlights(null);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch { /* ignore */ }
  }, [theme]);

  useEffect(() => {
    api.methods().then(setMeta).catch((e) => setOffline(e.message));
  }, []);

  return (
    <div className="app">
      <nav className="rail" aria-label="Main">
        {VIEWS.map((v) => (
          <button key={v.id} className={view === v.id ? "on" : ""} onClick={() => setView(v.id)}
            aria-current={view === v.id ? "page" : undefined}>
            <Icon name={v.icon} size={20} />
            <span>{v.label}</span>
          </button>
        ))}
        <span className="grow" />
        <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle dark mode">
          <Icon name={theme === "dark" ? "sun" : "moon"} size={20} />
          <span>{theme === "dark" ? "Light" : "Dark"}</span>
        </button>
      </nav>

      <main className="workspace">
        <DocumentPane doc={doc} setDoc={updateDoc} highlights={highlights} notify={notify} />

        <section className="result-pane" aria-label={VIEWS.find((v) => v.id === view).label}>
          {offline && (
            <div className="notice error" role="alert">
              {offline}
              <br /><small>From the <code>backend</code> folder, run <code>uvicorn app.main:app --reload</code>, then refresh.</small>
            </div>
          )}
          <div hidden={view !== "summarize"}>
            <SummarizeView active={view === "summarize"} doc={doc} meta={meta} setHighlights={setHighlights} notify={notify} />
          </div>
          <div hidden={view !== "compare"}><CompareView doc={doc} meta={meta} notify={notify} /></div>
          <div hidden={view !== "insights"}><InsightsView doc={doc} notify={notify} /></div>
          <div hidden={view !== "history"}>
            <HistoryView active={view === "history"} loadDoc={(d) => { updateDoc(d); setView("summarize"); }} notify={notify} />
          </div>
        </section>
      </main>
      <Toast toast={toast} onDone={dismissToast} />
    </div>
  );
}
