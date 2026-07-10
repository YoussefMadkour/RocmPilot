# RocmPilot — Project Rules

## Git workflow

- **`main`** — protected, release/stable branch. No direct commits.
- **`dev`** — integration branch. All feature work merges here first via PR.
- **Feature branches** — branch off `dev`, named `feat/<short-desc>` (or `fix/<short-desc>`, `docs/<short-desc>`).

### Process

1. Branch off `dev`: `git checkout dev && git pull && git checkout -b feat/<short-desc>`
2. Commit your work on the feature branch.
3. Open a PR **into `dev`** (never directly into `main`).
4. `dev` → `main` happens as a separate release PR once things are stable.

**Rule: never commit directly to `main` or `dev`. Every change goes through a feature branch and a PR targeting `dev`.**
