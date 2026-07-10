"""Tests for patch generation + the wired-in Patch Explainer.

No network: the Fireworks call is stubbed. Focus is that patches are explained
with the REAL changed snippet (not a generic blurb), the explainer is bounded,
and the deterministic fallback stays grounded.
"""
from __future__ import annotations

import pytest

from app.agents import patch_explainer
from app.services import patch_service, run_store


# --------------------------------------------------------------------------- #
# _changed_lines — the real snippet fed to the explainer
# --------------------------------------------------------------------------- #
def test_changed_lines_captures_only_the_diff():
    original = 'a = 1\ndevice = torch.device("cuda")\nb = 2\n'
    patched = patch_service._rewrite_python(original)
    changed = patch_service._changed_lines(original, patched)
    assert len(changed) == 1
    lineno, before, after = changed[0]
    assert lineno == 2
    assert before == 'device = torch.device("cuda")'
    assert "is_available()" in after


def test_changed_lines_empty_when_no_rewrite():
    text = "x = 1\ny = 2\n"
    assert patch_service._changed_lines(text, patch_service._rewrite_python(text)) == []


# --------------------------------------------------------------------------- #
# patch_explainer — grounded, file-aware
# --------------------------------------------------------------------------- #
def test_explainer_uses_llm_when_available(monkeypatch):
    monkeypatch.setattr(patch_explainer.fireworks_service, "complete",
                        lambda **k: "  Looks good.  ")
    assert patch_explainer.explain("a", "b", file_path="m.py") == "Looks good."


def test_explainer_fallback_mentions_file(monkeypatch):
    monkeypatch.setattr(patch_explainer.fireworks_service, "complete", lambda **k: None)
    out = patch_explainer.explain("a", "b", file_path="model.py")
    assert "model.py" in out
    assert "torch.cuda" in out


# --------------------------------------------------------------------------- #
# patch_service.generate — end to end (filesystem + stubbed explainer)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def run_with_source(tmp_path, monkeypatch):
    """A run whose source/ has a couple of patchable + one clean python file."""
    monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path, raising=False)
    run_id = "testrun"
    src = tmp_path / run_id / "source"
    src.mkdir(parents=True)
    (src / "a.py").write_text('device = torch.device("cuda")\n')
    (src / "b.py").write_text('m = torch.device("cuda")\nx = 1\n')
    (src / "clean.py").write_text("print('hi')\n")
    monkeypatch.setattr(run_store, "source_dir", lambda rid: src)
    monkeypatch.setattr(run_store, "run_dir", lambda rid: tmp_path / rid)
    return run_id


def test_generate_explains_each_patched_file(run_with_source, monkeypatch):
    monkeypatch.setattr(patch_explainer.fireworks_service, "complete", lambda **k: None)
    artifacts, explanations = patch_service.generate(run_with_source)

    names = {a.name for a in artifacts}
    assert {"patch.diff", "Dockerfile.rocm", "smoke_test.py", "benchmark.py"} <= names

    # One explanation per patched file (a.py, b.py) — not the clean one.
    assert {e.file_path for e in explanations} == {"a.py", "b.py"}
    for e in explanations:
        assert 'torch.device("cuda")' in e.original
        assert "is_available()" in e.patched
        assert e.file_path in e.explanation  # grounded fallback


def test_generate_passes_real_snippet_to_explainer(run_with_source, monkeypatch):
    seen = []

    def _spy(original, patched, *, file_path=""):
        seen.append((original, patched, file_path))
        return "ok"

    monkeypatch.setattr(patch_service.patch_explainer, "explain", _spy)
    patch_service.generate(run_with_source)
    assert any('torch.device("cuda")' in orig and "is_available()" in patched
               for orig, patched, _ in seen)


def test_generate_caps_explanations(run_with_source, monkeypatch):
    monkeypatch.setattr(patch_service, "MAX_EXPLANATIONS", 1)
    monkeypatch.setattr(patch_explainer.fireworks_service, "complete", lambda **k: None)
    _, explanations = patch_service.generate(run_with_source)
    assert len(explanations) == 1  # bounded even though 2 files are patchable
