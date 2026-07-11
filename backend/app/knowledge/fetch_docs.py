"""Fetch + chunk REAL ROCm/HIP/HIPIFY documentation for the RAG index.

OWNER: Youssef (AI). Complements the hand-curated `corpus.py` with live doc
content so retrieval has breadth. Fully best-effort: any URL that fails or returns
non-200 is skipped, so ingestion never breaks. Sources are the real doc URLs, so
retrieved chunks cite where they came from.

`ingest.py` calls `fetch_web_docs()` and indexes the result alongside the corpus.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# Authoritative ROCm/HIP/HIPIFY pages. `.rst` are fetched raw; HTML via BeautifulSoup.
DOC_URLS: list[str] = [
    "https://rocm.docs.amd.com/projects/HIPIFY/en/latest/index.html",
    "https://rocm.docs.amd.com/en/latest/conceptual/gpu-arch.html",
    "https://raw.githubusercontent.com/ROCm/HIP/develop/docs/how-to/hip_porting_guide.rst",
    "https://raw.githubusercontent.com/ROCm/HIP/develop/docs/reference/kernel_language.rst",
    "https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/inference/index.html",
]

# Seeds + host allowlist for the bounded crawler (breadth beyond the fixed list).
CRAWL_SEEDS: list[str] = [
    "https://rocm.docs.amd.com/projects/HIP/en/latest/how-to/hip_porting_guide.html",
    "https://rocm.docs.amd.com/projects/HIPIFY/en/latest/index.html",
    "https://rocm.docs.amd.com/en/latest/conceptual/gpu-arch.html",
]
CRAWL_HOSTS = {"rocm.docs.amd.com"}

_HEADERS = {"User-Agent": "Mozilla/5.0 (RocmPilot doc indexer)"}


def _extract_text(url: str, body: str) -> str:
    if url.endswith(".rst"):
        text = body
    else:
        soup = BeautifulSoup(body, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        text = main.get_text("\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def _chunk(text: str, size: int = 800) -> list[str]:
    """Greedy paragraph packing into ~size-char chunks (keeps ideas whole)."""
    paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if cur and len(cur) + len(p) > size:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n\n{p}".strip() if cur else p
    if cur:
        chunks.append(cur)
    return chunks


def fetch_web_docs(limit_per_doc: int = 8) -> list[dict[str, str]]:
    """Return [{text, source}] from the fixed doc set. Best-effort; skips failures."""
    out: list[dict[str, str]] = []
    for url in DOC_URLS:
        try:
            r = httpx.get(url, timeout=25, follow_redirects=True, headers=_HEADERS)
            if r.status_code != 200:
                continue
            for chunk in _chunk(_extract_text(url, r.text))[:limit_per_doc]:
                out.append({"text": chunk, "source": url})
        except (httpx.HTTPError, ValueError):
            continue
    return out


def _doc_links(base_url: str, html: str) -> list[str]:
    """Same-host .html/dir doc links from a page (absolute, de-anchored). Pure."""
    links: list[str] = []
    seen: set[str] = set()
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        nxt = urljoin(base_url, a["href"].split("#")[0].strip())
        p = urlparse(nxt)
        if (p.scheme in ("http", "https") and p.netloc in CRAWL_HOSTS
                and (nxt.endswith(".html") or nxt.endswith("/")) and nxt not in seen):
            seen.add(nxt)
            links.append(nxt)
    return links


def crawl_docs(max_pages: int = 50, per_page_chunks: int = 5) -> list[dict[str, str]]:
    """Bounded BFS crawl of the ROCm docs site. Best-effort; skips failures.

    Static server-rendered HTML, so plain httpx + BeautifulSoup suffices (no
    browser). Same-host only, capped at max_pages — polite and reproducible.
    """
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    queue: list[str] = list(CRAWL_SEEDS)
    while queue and len(seen) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            r = httpx.get(url, timeout=25, follow_redirects=True, headers=_HEADERS)
            if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
                continue
        except httpx.HTTPError:
            continue
        for chunk in _chunk(_extract_text(url, r.text))[:per_page_chunks]:
            out.append({"text": chunk, "source": url})
        for link in _doc_links(url, r.text):
            if link not in seen and link not in queue:
                queue.append(link)
    return out
