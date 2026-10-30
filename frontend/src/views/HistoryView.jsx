import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Empty, Icon } from "../components/ui";

export default function HistoryView({ active, loadDoc, notify }) {
  const [items, setItems] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setItems((await api.history()).items);
    } catch (e) {
      notify(e.message, "error");
    }
  }, [notify]);

  useEffect(() => {
    if (active) refresh();
  }, [active, refresh]);

  async function open(id) {
    try {
      const item = await api.historyItem(id);
      loadDoc({ text: item.text, title: item.title === "Untitled" ? "" : item.title });
      notify("Document loaded. Press Summarize to run it again.");
    } catch (e) {
      notify(e.message, "error");
    }
  }

  async function remove(id) {
    await api.deleteHistory(id).catch((e) => notify(e.message, "error"));
    refresh();
  }

  async function clearAll() {
    if (!window.confirm("Delete all saved summaries? This can't be undone.")) return;
    await api.clearHistory().catch((e) => notify(e.message, "error"));
    refresh();
  }

  return (
    <div className="view">
      <div className="panel controls row-between">
        <div>
          <h2>History</h2>
          <p className="hint">Every summary you generate is saved on this computer.</p>
        </div>
        {items?.length > 0 && <button className="btn quiet" onClick={clearAll}><Icon name="trash" size={15} /> Clear all</button>}
      </div>

      {items && items.length === 0 && <Empty title="Nothing saved yet">Summaries you generate will show up here so you can reopen the document later.</Empty>}

      <ul className="history">
        {items?.map((it) => (
          <li key={it.id} className="panel">
            <div className="history-head">
              <h3>{it.title}</h3>
              <span className="meta-line">{it.method}, {new Date(it.created * 1000).toLocaleString()}</span>
            </div>
            <p>{it.summary.length > 260 ? `${it.summary.slice(0, 260)}…` : it.summary}</p>
            <div className="actions">
              <button className="btn small" onClick={() => open(it.id)}>Open document</button>
              <button className="btn small quiet" onClick={() => navigator.clipboard.writeText(it.summary).then(() => notify("Summary copied"))}>
                <Icon name="copy" size={14} /> Copy summary
              </button>
              <button className="icon-btn" onClick={() => remove(it.id)} aria-label="Delete this item" title="Delete"><Icon name="trash" size={16} /></button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
