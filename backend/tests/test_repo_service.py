"""Tests for repo_service URL validation and clone guardrails.

The validation tests are pure (no network). The clone tests stub out
subprocess.run so nothing is actually cloned.
"""
from __future__ import annotations

import subprocess

import pytest

from app.config import settings
from app.services import repo_service
from app.services.repo_service import RepoError


# --------------------------------------------------------------------------- #
# URL validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("url", [
    "https://github.com/karpathy/nanoGPT",
    "https://github.com/karpathy/nanoGPT.git",
    "http://gitlab.com/group/project",
    "https://bitbucket.org/team/repo",
    "https://huggingface.co/org/model",
])
def test_valid_urls_pass(url):
    normalized, host = repo_service._validate_url(url)
    assert normalized.startswith(("http://", "https://"))
    assert host in repo_service.ALLOWED_HOSTS


@pytest.mark.parametrize("url", ["", "   ", None])
def test_empty_url_rejected(url):
    with pytest.raises(RepoError):
        repo_service._validate_url(url)  # type: ignore[arg-type]


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ssh://git@github.com/x/y",
    "git@github.com:x/y.git",              # scp-like syntax: parsed scheme is empty
    "ftp://github.com/x/y",
])
def test_non_http_schemes_rejected(url):
    with pytest.raises(RepoError):
        repo_service._validate_url(url)


def test_embedded_credentials_rejected():
    with pytest.raises(RepoError, match="credentials"):
        repo_service._validate_url("https://user:pass@github.com/x/y")


@pytest.mark.parametrize("url", [
    "https://evil.example.com/x/y",
    "https://gitlab.example.org/x/y",
])
def test_disallowed_host_rejected(url):
    with pytest.raises(RepoError, match="not allowed"):
        repo_service._validate_url(url)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/x/y",
    "http://localhost.localdomain/x/y",  # DNS name, blocked by host allowlist
    "http://169.254.169.254/latest",     # cloud metadata endpoint
    "http://10.0.0.5/x/y",
    "http://192.168.1.10/x/y",
])
def test_private_and_loopback_rejected(url):
    with pytest.raises(RepoError):
        repo_service._validate_url(url)


def test_normalization_strips_query_and_fragment():
    normalized, _ = repo_service._validate_url(
        "https://github.com/x/y?token=abc#readme"
    )
    assert normalized == "https://github.com/x/y"


# --------------------------------------------------------------------------- #
# Token injection & redaction
# --------------------------------------------------------------------------- #
def test_token_injected_for_github(monkeypatch):
    monkeypatch.setattr(settings, "github_token", "SECRET123")
    url = repo_service._authenticated_url("https://github.com/x/y", "github.com")
    assert "x-access-token:SECRET123@github.com" in url


def test_token_not_injected_for_other_hosts(monkeypatch):
    monkeypatch.setattr(settings, "github_token", "SECRET123")
    url = repo_service._authenticated_url("https://gitlab.com/x/y", "gitlab.com")
    assert "SECRET123" not in url


def test_redact_hides_token(monkeypatch):
    monkeypatch.setattr(settings, "github_token", "SECRET123")
    assert "SECRET123" not in repo_service._redact("fatal: repo SECRET123 not found")


# --------------------------------------------------------------------------- #
# clone_repo behaviour (subprocess stubbed)
# --------------------------------------------------------------------------- #
def _fake_source_dir(tmp_path):
    return tmp_path / "source"


def test_clone_rejects_bad_url_before_shelling_out(monkeypatch, tmp_path):
    called = False

    def _no_run(*a, **k):
        nonlocal called
        called = True
        raise AssertionError("git should not be invoked for an invalid URL")

    monkeypatch.setattr(subprocess, "run", _no_run)
    monkeypatch.setattr(repo_service.run_store, "source_dir",
                        lambda rid: _fake_source_dir(tmp_path))
    with pytest.raises(RepoError):
        repo_service.clone_repo("run1", "file:///etc/passwd")
    assert called is False


def test_clone_timeout_cleans_up(monkeypatch, tmp_path):
    dst = _fake_source_dir(tmp_path)
    monkeypatch.setattr(repo_service.run_store, "source_dir", lambda rid: dst)

    def _timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(subprocess, "run", _timeout)
    with pytest.raises(RepoError, match="timed out"):
        repo_service.clone_repo("run1", "https://github.com/x/y")
    assert not dst.exists()


def test_clone_failure_redacts_token(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "github_token", "SECRET123")
    dst = _fake_source_dir(tmp_path)
    monkeypatch.setattr(repo_service.run_store, "source_dir", lambda rid: dst)

    def _fail(*a, **k):
        raise subprocess.CalledProcessError(
            returncode=128, cmd="git", stderr="auth failed for SECRET123"
        )

    monkeypatch.setattr(subprocess, "run", _fail)
    with pytest.raises(RepoError) as exc:
        repo_service.clone_repo("run1", "https://github.com/x/y")
    assert "SECRET123" not in str(exc.value)


def test_clone_oversize_repo_cleaned_up(monkeypatch, tmp_path):
    dst = _fake_source_dir(tmp_path)
    monkeypatch.setattr(repo_service.run_store, "source_dir", lambda rid: dst)
    monkeypatch.setattr(settings, "max_repo_mb", 0)  # anything non-empty is "too large"

    def _fake_clone(*a, **k):
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "big.bin").write_bytes(b"x" * (1024 * 1024))  # 1 MB
        return subprocess.CompletedProcess(a, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_clone)
    with pytest.raises(RepoError, match="too large"):
        repo_service.clone_repo("run1", "https://github.com/x/y")
    assert not dst.exists()


def test_clone_success_returns_source_dir(monkeypatch, tmp_path):
    dst = _fake_source_dir(tmp_path)
    monkeypatch.setattr(repo_service.run_store, "source_dir", lambda rid: dst)
    monkeypatch.setattr(settings, "max_repo_mb", 500)

    def _fake_clone(*a, **k):
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "README.md").write_text("hi")
        return subprocess.CompletedProcess(a, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_clone)
    result = repo_service.clone_repo("run1", "https://github.com/x/y")
    assert result == dst
    assert (result / "README.md").exists()
