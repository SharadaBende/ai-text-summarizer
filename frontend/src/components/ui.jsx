import { useEffect } from "react";

const PATHS = {
  pen: "M4 20h4L19 9l-4-4L4 16v4z M13 7l4 4",
  columns: "M4 5h7v14H4z M13 5h7v14h-7z",
  chart: "M5 19V10 M12 19V5 M19 19v-6",
  clock: "M12 4a8 8 0 100 16 8 8 0 000-16z M12 8v4l3 2",
  moon: "M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z",
  sun: "M12 8a4 4 0 100 8 4 4 0 000-8z M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5L19 19 M5 19l1.5-1.5 M17.5 6.5L19 5",
  copy: "M9 9h10v11H9z M5 15V4h10",
  download: "M12 4v11 M7 11l5 5 5-5 M5 20h14",
  speaker: "M4 9v6h4l5 4V5L8 9H4z M16.5 9.5a4 4 0 010 5",
  stop: "M7 7h10v10H7z",
  trash: "M5 7h14 M9 7V4h6v3 M7 7l1 13h8l1-13",
  upload: "M12 16V5 M7 9l5-5 5 5 M5 20h14",
  link: "M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1 M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1",
  play: "M8 5l11 7-11 7z",
  edit: "M4 20h4L19 9l-4-4L4 16v4z",
  check: "M5 12l5 5 9-10",
};

export function Icon({ name, size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name]} />
    </svg>
  );
}

export function Segmented({ value, onChange, options, label }) {
  return (
    <div className="segmented" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} role="tab" aria-selected={value === o.id} className={value === o.id ? "on" : ""}
          onClick={() => onChange(o.id)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Slider({ label, value, min, max, step = 1, onChange, format = (v) => v, hint }) {
  return (
    <label className="field">
      <span className="field-head">
        <span>{label}</span>
        <output>{format(value)}</output>
      </span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
      {hint && <span className="hint">{hint}</span>}
    </label>
  );
}

export function Stat({ value, label }) {
  return (
    <div className="stat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export function Spinner({ label }) {
  return (
    <span className="spinner-wrap" role="status">
      <span className="spinner" />
      {label}
    </span>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

export function Toast({ toast, onDone }) {
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(onDone, 3800);
    return () => clearTimeout(t);
  }, [toast, onDone]);
  if (!toast) return null;
  return (
    <div className={`toast ${toast.kind}`} role="status" aria-live="polite">
      {toast.message}
    </div>
  );
}

export const pct = (v, digits = 0) => `${(v * 100).toFixed(digits)}%`;
export const num = (v) => (typeof v === "number" ? v.toLocaleString() : v);
