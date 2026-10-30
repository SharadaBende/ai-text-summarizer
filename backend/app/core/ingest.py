"""Turn uploaded files and web pages into clean text (with SSRF protection)."""
from __future__ import annotations

import io
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

SUPPORTED = (".txt", ".md", ".markdown", ".pdf", ".docx", ".html", ".htm", ".csv")


class IngestError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Return (title, text) for an uploaded file."""
    name = filename or "document"
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    title = name.rsplit(".", 1)[0]
    if ext == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as exc:
            raise IngestError(f"Could not read this PDF: {exc}") from exc
        if not text.strip():
            raise IngestError("This PDF has no selectable text (it may be a scanned image).")
    elif ext == ".docx":
        from docx import Document

        try:
            text = "\n\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs if p.text.strip())
        except Exception as exc:
            raise IngestError(f"Could not read this Word file: {exc}") from exc
    elif ext in (".html", ".htm"):
        title2, text = _html_to_text(data.decode("utf-8", errors="ignore"))
        title = title2 or title
    elif ext in (".txt", ".md", ".markdown", ".csv", ""):
        text = data.decode("utf-8", errors="ignore")
    else:
        raise IngestError(f"Unsupported file type '{ext}'. Use: {', '.join(SUPPORTED)}")
    text = re.sub(r"[ \t]+\n", "\n", text).strip()
    if not text:
        raise IngestError("The file contains no text.")
    return title, text


def _html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    for tag in soup(["script", "style", "nav", "footer", "aside", "form", "noscript", "header", "svg"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    paras = [p.get_text(" ", strip=True) for p in root.find_all(["p", "li", "h2", "h3", "blockquote"])]
    paras = [p for p in paras if len(p.split()) >= 6]
    return title, "\n\n".join(paras)


def _assert_public(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise IngestError("Enter a full web address starting with http:// or https://")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise IngestError("Could not find that website.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise IngestError("That address points to a private network and can't be fetched.")


def fetch_url(url: str, timeout: int = 10, max_bytes: int = 5_000_000) -> tuple[str, str]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AITextSummarizer/1.0)"}
    current = url.strip()
    for _ in range(4):  # follow a few redirects, re-checking each hop
        _assert_public(current)
        try:
            resp = requests.get(current, headers=headers, timeout=timeout, stream=True, allow_redirects=False)
        except requests.RequestException as exc:
            raise IngestError(f"Could not reach the page: {exc.__class__.__name__}") from exc
        if resp.is_redirect and resp.headers.get("location"):
            current = urljoin(current, resp.headers["location"])
            continue
        if resp.status_code >= 400:
            raise IngestError(f"The website answered with status {resp.status_code}.")
        raw = resp.raw.read(max_bytes, decode_content=True)
        encoding = resp.encoding or "utf-8"
        title, text = _html_to_text(raw.decode(encoding, errors="ignore"))
        if len(text.split()) < 40:
            raise IngestError("Couldn't find enough article text on that page.")
        return title or urlparse(current).netloc, text
    raise IngestError("Too many redirects.")
