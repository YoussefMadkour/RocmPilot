"""Tests for the live-docs fetcher's pure parts (extract + chunk). No network."""
from __future__ import annotations

from app.knowledge import fetch_docs


def test_extract_strips_html_chrome():
    html = """<html><head><style>x{}</style></head><body>
      <nav>menu menu menu</nav>
      <main><p>HIP maps warp shuffles to wavefront-aware equivalents.</p></main>
      <footer>copyright</footer></body></html>"""
    text = fetch_docs._extract_text("https://x/doc.html", html)
    assert "wavefront-aware" in text
    assert "menu" not in text and "copyright" not in text


def test_extract_rst_kept_raw():
    rst = "Kernel Language\n===============\n\n__shfl is available in HIP.\n"
    assert "__shfl" in fetch_docs._extract_text("https://x/a.rst", rst)


def test_chunk_packs_paragraphs_under_size():
    text = "\n\n".join([f"paragraph number {i} " + "x" * 200 for i in range(10)])
    chunks = fetch_docs._chunk(text, size=800)
    assert len(chunks) > 1
    assert all(len(c) <= 1100 for c in chunks)  # greedy packing, ~size with slack


def test_chunk_drops_tiny_fragments():
    text = "short\n\n" + "y" * 300
    chunks = fetch_docs._chunk(text, size=800)
    assert all("short" not in c or len(c) > 80 for c in chunks)
