"""Runtime configuration, loaded from environment variables / .env."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = backend/  (this file lives at backend/app/config.py)
BACKEND_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = BACKEND_DIR / "runs"
SAMPLE_PROJECTS_DIR = BACKEND_DIR / "sample_projects"
TEMPLATES_DIR = BACKEND_DIR / "app" / "templates"
FIXTURES_DIR = BACKEND_DIR / "app" / "fixtures"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    fireworks_api_key: str = ""
    fireworks_model: str = "accounts/fireworks/models/llama-v3p1-70b-instruct"
    fireworks_embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
    embedding_dim: int = 768

    # "replay" (demo-safe, loads a saved AMD run) or "live"
    validation_mode: str = "replay"
    amd_validation_log_path: str = str(FIXTURES_DIR / "validation_log.txt")

    github_token: str = ""

    # Guardrails for cloning arbitrary user-supplied repo URLs.
    clone_timeout_seconds: int = 120
    max_repo_mb: int = 500

    # ---- Qdrant knowledge base (ROCm/HIP migration docs) ----
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    knowledge_collection: str = "rocm_migration_docs"
    knowledge_top_k: int = 5

    # ---- Optional web research for the self-heal agent (no-op if blank) ----
    tavily_api_key: str = ""

    @property
    def fireworks_enabled(self) -> bool:
        return bool(self.fireworks_api_key)

    @property
    def knowledge_enabled(self) -> bool:
        return bool(self.qdrant_url and self.fireworks_api_key)


settings = Settings()

# Ensure runtime dirs exist.
RUNS_DIR.mkdir(parents=True, exist_ok=True)
