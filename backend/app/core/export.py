"""Export summaries as Markdown or Word documents."""
from __future__ import annotations

import io
from datetime import date


def to_markdown(title: str, summary: str, keywords: list[str], method: str) -> str:
    lines = [f"# {title or 'Summary'}", "", f"*Method: {method} | {date.today().isoformat()}*", "", summary, ""]
    if keywords:
        lines += ["## Keywords", "", ", ".join(keywords), ""]
    return "\n".join(lines)


def to_docx(title: str, summary: str, keywords: list[str], method: str) -> bytes:
    from docx import Document

    doc = Document()
    doc.add_heading(title or "Summary", level=1)
    doc.add_paragraph(f"Method: {method}  |  {date.today().isoformat()}").italic = True
    for para in summary.split("\n\n"):
        doc.add_paragraph(para)
    if keywords:
        doc.add_heading("Keywords", level=2)
        doc.add_paragraph(", ".join(keywords))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
