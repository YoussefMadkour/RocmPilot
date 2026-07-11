"""Fetch + chunk REAL ROCm/HIP/HIPIFY documentation for the RAG index.

OWNER: Youssef (AI). Complements the hand-curated `corpus.py` with live doc
content so retrieval has breadth. Fully best-effort: any URL that fails or returns
non-200 is skipped, so ingestion never breaks. Sources are the real doc URLs, so
retrieved chunks cite where they came from.

`ingest.py` calls `fetch_web_docs()` and indexes the result alongside the corpus.
"""
from __future__ import annotations

import re

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
    """Return [{text, source}] from the live doc set. Best-effort; skips failures."""
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
