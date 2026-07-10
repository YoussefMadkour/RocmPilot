"""Get project source into a run's source/ dir: from a sample or a git clone.

OWNER: Youssef (backend). The git-clone path takes an arbitrary user-supplied
URL, so it is validated hard before we ever shell out to `git`:

  * scheme allowlist        -> only http(s); blocks file://, ssh://, git@ scp-syntax
  * host allowlist          -> known public git hosts only (no localhost / private IPs)
  * no embedded credentials -> we inject the token ourselves; callers can't smuggle one
  * depth-1 + timeout       -> bounded time
  * post-clone size cap     -> bounded disk; oversized repos are deleted, not kept

Validation failures raise ``RepoError`` (a ValueError); main.py turns any raise
here into a 400 with the message, so keep messages user-facing and never leak the
injected token.
"""
from __future__ import annotations

import ipaddress
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from app.config import SAMPLE_PROJECTS_DIR, settings
from app.services import run_store

DEFAULT_SAMPLE = "cuda_first_transformers_demo"

# Only these schemes are ever handed to `git clone`.
ALLOWED_SCHEMES = {"http", "https"}

# Known public git hosts. Extend deliberately — every entry is a host we trust to
# point `git` at. Self-hosted/enterprise hosts should be added here explicitly.
ALLOWED_HOSTS = {
    "github.com",
    "www.github.com",
    "gitlab.com",
    "www.gitlab.com",
    "bitbucket.org",
    "huggingface.co",
}

_TOKEN_USERNAME = "x-access-token"  # noqa: S105 — a git username, not a secret


class RepoError(ValueError):
    """User-facing problem with a repo URL or clone. Surfaced as a 400."""


def load_sample(run_id: str, sample_name: str = DEFAULT_SAMPLE) -> Path:
    src = SAMPLE_PROJECTS_DIR / sample_name
    if not src.exists():
        raise FileNotFoundError(f"Sample project not found: {sample_name}")
    dst = run_store.source_dir(run_id)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    return dst


def _host_is_private(host: str) -> bool:
    """True if the host is a loopback/private/link-local IP literal."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a DNS name, not a literal IP — allowlist handles those
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved


def _validate_url(repo_url: str) -> tuple[str, str]:
    """Validate a user-supplied repo URL. Returns (normalized_url, host).

    Raises RepoError on anything we won't clone.
    """
    if not repo_url or not repo_url.strip():
        raise RepoError("Repo URL is required.")
    repo_url = repo_url.strip()

    parsed = urlparse(repo_url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise RepoError(
            f"Unsupported URL scheme '{parsed.scheme}'. Use an https:// git URL "
            "(SSH and file paths are not allowed)."
        )
    if parsed.username or parsed.password:
        raise RepoError("Do not embed credentials in the URL; set GITHUB_TOKEN instead.")

    host = (parsed.hostname or "").lower()
    if not host:
        raise RepoError("Repo URL has no host.")
    if _host_is_private(host):
        raise RepoError("Refusing to clone from a private/loopback address.")
    if host not in ALLOWED_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_HOSTS))
        raise RepoError(f"Host '{host}' is not allowed. Allowed hosts: {allowed}.")

    # Rebuild from parsed parts (drops any embedded auth, normalizes) and keep
    # only scheme/host/path — no params/query/fragment go to `git`.
    normalized = urlunparse((parsed.scheme.lower(), host, parsed.path, "", "", ""))
    return normalized, host


def _authenticated_url(normalized_url: str, host: str) -> str:
    """Inject GITHUB_TOKEN for private github.com repos, if configured."""
    if host in {"github.com", "www.github.com"} and settings.github_token:
        parsed = urlparse(normalized_url)
        netloc = f"{_TOKEN_USERNAME}:{settings.github_token}@{parsed.hostname}"
        return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))
    return normalized_url


def _redact(text: str) -> str:
    """Strip the token from any text we might surface (error messages, logs)."""
    if settings.github_token:
        text = text.replace(settings.github_token, "***")
    return text


def _dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def clone_repo(run_id: str, repo_url: str) -> Path:
    normalized_url, host = _validate_url(repo_url)
    clone_url = _authenticated_url(normalized_url, host)

    dst = run_store.source_dir(run_id)
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True, exist_ok=True)

    try:
        # --depth 1: snapshot only, we just scan the tree.
        # -c credential.helper= : never fall back to an interactive credential prompt.
        subprocess.run(
            [
                "git", "-c", "credential.helper=",
                "clone", "--depth", "1", "--single-branch",
                clone_url, str(dst),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=settings.clone_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dst, ignore_errors=True)
        raise RepoError(
            f"Clone timed out after {settings.clone_timeout_seconds}s. "
            "The repository may be too large."
        ) from exc
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dst, ignore_errors=True)
        stderr = _redact((exc.stderr or "").strip())
        raise RepoError(f"git clone failed: {stderr or 'unknown error'}") from exc

    size_mb = _dir_size_mb(dst)
    if size_mb > settings.max_repo_mb:
        shutil.rmtree(dst, ignore_errors=True)
        raise RepoError(
            f"Repository is too large ({size_mb:.0f} MB > {settings.max_repo_mb} MB limit)."
        )

    return dst
