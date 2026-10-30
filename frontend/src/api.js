const BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, options);
  } catch {
    throw new Error("Can't reach the API. Start the backend: uvicorn app.main:app --reload");
  }
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep status text */ }
    throw new Error(message);
  }
  return res;
}

const post = (path, body) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.json());

export const api = {
  methods: () => request("/methods").then((r) => r.json()),
  summarize: (body) => post("/summarize", body),
  compare: (body) => post("/compare", body),
  analyze: (body) => post("/analyze", body),
  keywords: (body) => post("/keywords", body),
  evaluate: (body) => post("/evaluate", body),
  fetchUrl: (url) => post("/fetch-url", { url }),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/upload", { method: "POST", body: form }).then((r) => r.json());
  },
  exportFile: (body) =>
    request("/export", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => r.blob()),
  history: () => request("/history").then((r) => r.json()),
  historyItem: (id) => request(`/history/${id}`).then((r) => r.json()),
  deleteHistory: (id) => request(`/history/${id}`, { method: "DELETE" }).then((r) => r.json()),
  clearHistory: () => request("/history", { method: "DELETE" }).then((r) => r.json()),
};

export function saveBlob(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
