# RocmPilot Studio — Project Tracker

Living doc. Check boxes as you go (`- [x]`). Each task is tagged **[Y]** Youssef or
**[J]** Jithendra. Phase is "done" only when every acceptance criterion passes.

- **Y = Youssef** — senior AI eng. Owns the intelligence: agents, prompts, scanner
  core, scoring, validation, product/demo direction.
- **J = Jithendra** — owns the frontend cockpit, *and* takes scoped, testable
  backend tasks to ramp up (marked **[J] backend**).

Legend: 🔴 not started · 🟡 in progress · 🟢 done

---

## Split at a glance

| Layer | Youssef | Jithendra |
|-------|---------|-----------|
| Frontend | product/UX review | **all 6 screens + design + API client** |
| Backend – AI (`agents/`) | **all 4 Fireworks agents + prompts** | — |
| Backend – core (`services/`) | scanner core, scoring, patch logic, validation | **add scanner patterns, templates, tests, artifact-zip endpoint** |
| Sample / fixtures | validation fixtures | **sample repos** |
| Infra | — | **Docker / compose / CI** |
| Docs & demo | demo script, positioning | setup docs, screenshots |

Why this split: Youssef holds the parts that decide whether the project *feels
real* (agents, scoring, the ROCm nuance). Jithendra owns the whole visible surface
plus low-risk backend slices (patterns, tests, templates) that are easy to verify
and teach the codebase without gating the AI path.

---

## Phase 0 — Scaffold  🟢 (done this session)
- [x] Repo structure, runnable FastAPI backend, typed frontend client
- [x] Deterministic scanner + scoring (demo curve **37 → 72 → 86**)
- [x] Fireworks agents with offline fallback
- [x] Sample CUDA-first repo, ROCm templates, replay validation fixture
- [x] Docker + compose, docs, this tracker
**Acceptance:** `docker compose up` builds; sample run completes end to end. ✅ verified via backend TestClient.

---

## Phase 1 — Core loop solid  🟡 ([J] done; [Y] mostly done — scanner polish open)
**Backend [Y]**
- [x] Harden `repo_service.clone_repo` — scheme/host allowlist, SSRF guard, size/time limits, `GITHUB_TOKEN` + redaction (PR #2, 29 tests)
- [x] Expand scanner pattern catalogue + polish — Jith added 6 patterns; [Y] added per-line dedupe (collapse same-line/same-category rows, keep most severe) and pointed `.cu`/CUDAExtension blockers at AMD HIPIFY tooling (PR #15, 4 tests). Deferred: downweight `.md`/docs findings (needs a scoring re-tune + band update — own pass).
- [x] Lock scoring weights against 3 real repos — **rebuilt honest, count-sensitive model** (PR #3, 17 tests); see `docs/BENCHMARK_REPOS.md` + scoring decision

**Backend [J] backend** (ramp-up tasks)
- [x] Add ≥5 new patterns to `scanner_service.PATTERNS` (added 6: `pin_memory`, `torch.backends.cudnn`, `torch.backends.cuda`/TF32, `apex`, `bitsandbytes`, `flash-attn`) with a test each
- [x] Write `backend/tests/test_scanner.py` + `test_scoring.py` (pytest — 29 passing)
- [x] Add `GET /api/runs` (list runs) endpoint

**Frontend [J]**
- [x] Run the **frontend-design** skill; commit a design direction note (`frontend/DESIGN.md`)
- [x] App shell + nav (Intake → Scan → Plan → Patch → Validate → Report)
- [x] **Intake** screen: repo URL input, "use sample" button, create run

**Acceptance:**
- Scanner has ≥15 patterns, all covered by a passing `pytest`.
- Frontend shell navigates all 6 routes; Intake creates a run and routes to Scan.

---

## Phase 2 — Scan + Plan  🟢 ([J] + [Y] done)
**Backend [Y]**
- [x] Tune Migration Planner prompt + harden JSON validity (fenced/prose recovery, enum guard) (PR #5, 15 tests)
- [x] Patch Explainer wired to real changed snippets, surfaced in `PatchResponse` (PR #7, 7 tests)
- [x] **Bonus:** code-first multi-agent Orchestrator + Critic with agent-activity `trace` on `POST /plan` (PR #8)

**Frontend [J]**
- [x] **Scan** screen: readiness score card, findings table (severity badges, file:line, category filter), findings-by-category summary
- [x] **Plan** screen: agent summary, prioritized actions, manual-blockers list, agent-activity timeline

**Acceptance:**
- Scan screen renders all findings from a real repo with working severity/category filtering.
- Plan screen shows a coherent plan (works with AND without a Fireworks key).

---

## Phase 3 — Patch + Validate  🟢 ([J] + [Y] done)
**Backend [Y]**
- [x] Improve patch transforms — now guards `.cuda()`, `.to("cuda")`, `torch.device("cuda")`; conservative + idempotent (PR #10, +5 tests)
- [x] Implement `live` validation mode — build `Dockerfile.rocm`, run smoke+bench, **parse stdout** into a ValidationResult; graceful fallback to replay when Docker/AMD unavailable. Parser unit-tested; the docker path needs a real AMD host to exercise.
- [x] Wire Failure Diagnoser into the validate path on failure + `VALIDATION_MODE=replay_fail` demo mode; UI panel renders `validation.diagnosis` (PR #9, 4 tests)

**Backend [J] backend**
- [x] Refine the three templates so generated artifacts run clean on ROCm (CUDA-wheel filtering in Dockerfile, parseable PASS/FAIL + `--require-gpu` in smoke test, TFLOPS in benchmark)
- [x] Add `GET /api/runs/{id}/artifacts.zip` (bundle all artifacts for download)

**Frontend [J]**
- [x] **Patch** screen: diff viewer, artifact tabs (Dockerfile/​smoke/​benchmark), download
- [x] **Validate** screen: AMD validation card, terminal-style log panel, **clear replay-mode badge**, failure-diagnosis panel

**Acceptance:**
- Patch screen shows a real diff + 4 downloadable artifacts.
- Validate screen shows pass/fail, GPU name, latency; replay is clearly labeled.

---

## Phase 4 — Report + polish + ship
**Backend [Y]**
- [x] Report Writer prompt produces a judge-ready report from real data — sharpened prompt (6 sections, honest replay labeling, ROCm nuance), richer fallback (failure diagnosis + replay note), and `readiness_report.md` now registered as an artifact so `artifacts.zip` includes it (PR #14, 6 tests)

**Frontend [J]**
- [ ] **Report** screen: before/after score comparison, rendered Markdown, artifact list, download report
- [ ] Visual polish pass (dark cockpit, consistent spacing/badges)

**Infra [J]**
- [ ] Verify clean `docker compose up --build` from scratch on a fresh clone
- [ ] Optional: GitHub Actions (lint backend + build frontend)

**Acceptance:**
- Full flow runs in the UI in < 3 minutes on a fresh clone.
- Report downloads; before/after score visible.

---

## Phase 5 — Submission
- [ ] [Y] Record 3-min demo (follow `docs/DEMO_SCRIPT.md`)
- [ ] [Y] Submission write-up + positioning
- [ ] [J] Screenshots + README setup polish
- [ ] [Both] Dry-run the demo twice; fix anything that stutters

---

## Showcase repos (verified CUDA-first — July 2026)

| Repo | Why it's a good showcase | Confirmed patterns |
|------|--------------------------|--------------------|
| [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) | **Primary.** Small, famous, fast to clone, clean text-gen demo. | `device = 'cuda'`, `device = f'cuda:{ddp_local_rank}'`, `torch.backends.cuda.matmul.allow_tf32` |
| [ultralytics/yolov5](https://github.com/ultralytics/yolov5) | Very recognizable, **visual** (bounding boxes), ships a GPU Dockerfile. | `FROM pytorch/pytorch:…cuda12.8…`, `--gpus all`, `--ipc=host` |
| [xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | **Most visual** (before/after image upscaling); great for judges. | fp16 GPU inference, `--gpu-id`, `half=` |
| [openai/whisper](https://github.com/openai/whisper) | Household name; audio angle. Note: already has a CPU fallback, so fewer hard blockers — use as a "already partly ready" contrast. | `default="cuda" if torch.cuda.is_available() else "cpu"` |

Recommendation (updated for **honest scoring** — see `docs/BENCHMARK_REPOS.md`):
**lead the demo with the bundled sample** (37 → 72 → 86; it hits every blocker
category). Real repos are honest proof, not forced-low: nanoGPT ~67, Real-ESRGAN
~65, YOLOv5 ~55 "before" (ROCm maps `cuda` transparently, so clean repos really
are closer to ready). Use **YOLOv5** for the strongest real Docker-blocker story
and **Real-ESRGAN** as the visual "wow." Custom-kernel repos (detectron2 ~12,
flash-attention ~17) are the honest low end / Tier-2 backlog.

---

## Limitations & future work
- v1 = PyTorch/HF **inference** repos. Training repos partially supported.
- Custom CUDA kernels (`.cu`/`.cuh`), native extensions → flagged, not solved.
  **Tier 2** repos (detectron2, mmcv, flash-attention, apex) are deferred until
  the Tier 1 application-repo pipeline is polished — see `docs/BENCHMARK_REPOS.md`.
- `live` AMD validation is implemented (docker build + run + log parser) but
  needs a real AMD/ROCm host; without one it falls back to the **saved** run
  (replay), which is what the demo uses. Capturing a genuine AMD Dev Cloud log
  into `fixtures/` is still a TODO.
- No automatic GitHub PR creation yet (roadmap).
- Single-run filesystem store; no multi-user history yet.
