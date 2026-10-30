import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { SAMPLE_TEXT, SAMPLE_TITLE } from "../sample";
import Highlighted from "./Highlighted";
import { Icon, Segmented, Spinner } from "./ui";

const TABS = [
  { id: "paste", label: "Paste text" },
  { id: "file", label: "Upload file" },
  { id: "url", label: "Web page" },
];

export default function DocumentPane({ doc, setDoc, highlights, notify }) {
  const [tab, setTab] = useState("paste");
  const [editing, setEditing] = useState(false);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const fileRef = useRef(null);

  const words = doc.text.trim() ? doc.text.trim().split(/\s+/).length : 0;
  const showMarks = Boolean(highlights) && !editing;

  useEffect(() => {
    if (highlights) setEditing(false);
  }, [highlights]);

  async function load(promise, okMessage) {
    setBusy(true);
    try {
      const r = await promise;
      setDoc({ text: r.text, title: r.title || "" });
      setTab("paste");
      notify(okMessage(r) + (r.truncated ? " (truncated to the size limit)" : ""));
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  const onFile = (file) => file && load(api.upload(file), (r) => `Loaded ${file.name}: ${r.words.toLocaleString()} words`);
  const onUrl = () => url.trim() && load(api.fetchUrl(url.trim()), (r) => `Fetched "${r.title}": ${r.words.toLocaleString()} words`);

  return (
    <section className="doc-pane" aria-label="Document">
      <header className="doc-head">
        <h1 className="brand">AI Text Summarizer</h1>
        <input className="title-input" placeholder="Untitled document" value={doc.title}
          onChange={(e) => setDoc({ ...doc, title: e.target.value }, true)} aria-label="Document title" />
      </header>

      {!showMarks && <Segmented label="Input source" value={tab} onChange={setTab} options={TABS} />}

      {showMarks ? (
        <>
          <div className="legend">
            <mark className="mark static">Highlighted</mark>
            <span>sentences made it into the summary. Hover one to see its relevance score.</span>
            <button className="btn quiet" onClick={() => setEditing(true)}><Icon name="edit" size={15} /> Edit text</button>
          </div>
          <Highlighted sentences={highlights} />
        </>
      ) : tab === "paste" ? (
        <>
          <textarea className="editor" value={doc.text} spellCheck="false"
            placeholder="Paste an article, essay, report or transcript. Anything over a few sentences works."
            onChange={(e) => setDoc({ ...doc, text: e.target.value })} aria-label="Text to summarize" />
          <div className="doc-foot">
            <span>{words.toLocaleString()} words, about {Math.max(1, Math.round(words / 200))} min read</span>
            <span className="grow" />
            {!doc.text && <button className="btn quiet" onClick={() => setDoc({ text: SAMPLE_TEXT, title: SAMPLE_TITLE })}>Try a sample</button>}
            {doc.text && <button className="btn quiet" onClick={() => setDoc({ text: "", title: "" })}>Clear</button>}
          </div>
        </>
      ) : tab === "file" ? (
        <div className={`drop ${drag ? "over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); onFile(e.dataTransfer.files[0]); }}>
          <Icon name="upload" size={28} />
          <p>Drop a file here</p>
          <small>PDF, Word (.docx), TXT, Markdown or HTML, up to 10 MB.</small>
          <button className="btn" onClick={() => fileRef.current?.click()} disabled={busy}>
            {busy ? <Spinner label="Reading file" /> : "Choose file"}
          </button>
          <input ref={fileRef} type="file" hidden accept=".pdf,.docx,.txt,.md,.markdown,.html,.htm,.csv"
            onChange={(e) => { onFile(e.target.files[0]); e.target.value = ""; }} />
        </div>
      ) : (
        <div className="url-box">
          <label htmlFor="url">Article address</label>
          <div className="row">
            <input id="url" type="url" value={url} placeholder="https://example.com/article"
              onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === "Enter" && onUrl()} />
            <button className="btn" onClick={onUrl} disabled={busy || !url.trim()}>
              {busy ? <Spinner label="Fetching" /> : "Fetch article"}
            </button>
          </div>
          <small>We pull the main article text and ignore menus, ads and footers.</small>
        </div>
      )}
    </section>
  );
}
