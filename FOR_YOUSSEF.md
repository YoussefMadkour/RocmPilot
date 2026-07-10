# Hey Youssef 👋 — status + what's on your plate

*(From Jithendra, 2026-07-10. All [J] tasks through Phase 3 are done, verified
in-browser, and committed — small commits, one thing each, per your rules.)*

---

## ⬆️ Update from Youssef (2026-07-10, later) — most of the [Y] list has landed

Merged to `dev` + `main` since Jithendra's note below (PRs #1–#10, all tested):

- **Phase 1:** ✅ `clone_repo` hardened (allowlist/SSRF guard/token redaction) ·
  ✅ scoring **locked & made honest** — see decision below · scanner catalogue:
  Jith added 6 patterns; dedupe/docs-downweight/HIPIFY polish still open (items 7–8).
- **Phase 2:** ✅ Migration Planner prompt tuned + JSON-validity hardened ·
  ✅ Patch Explainer **wired to real snippets** (your item 5 — render away).
- **Phase 3:** ✅ patch transforms now cover `.cuda()` + `.to("cuda")` ·
  ✅ **Failure Diagnoser wired** + new `VALIDATION_MODE=replay_fail` (your item 6 —
  the failure panel now gets `validation.diagnosis`) · ✅ encoding bug fixed
  (item 2/3). ⏳ `live` validation still a stub.
- **Bonus — multi-agent:** ✅ code-first **Orchestrator + Critic** with an agent
  activity `trace` on `POST /plan` (`{plan, critique, trace}`) — render the timeline.

**Scoring decision (your call, made):** scoring is optimized for **honesty**, not
demo drama. ROCm maps `cuda` transparently, so clean repos (nanoGPT ~67) genuinely
score high; only real blockers (custom kernels, NVIDIA base image, `+cuXXX` wheels)
tank it (detectron2 ~12). The **demo leads with the bundled sample (37 → 72 → 86)**;
real repos are honest proof, not forced low. Full spectrum + tier list in
`docs/BENCHMARK_REPOS.md`.

**Still on my plate:** `live` validation · Report Writer prompt (P4) · scanner
polish (dedupe dup rows, downweight `.md` findings, HIPIFY vocab) · include
`readiness_report.md` in `artifacts.zip` (item 4) · `GET /api/runs/{id}` (item 3 —
let's pair) · real AMD Dev Cloud log · demo (P5).

The rest of this doc is Jithendra's original note (statuses above supersede it).

---

## Where we are

Every screen except Report is real now: Intake → Scan (findings table with
severity/category filters) → Plan → Patch (diff viewer + artifact tabs +
zip download) → Validate (AMD card, terminal log, replay badge). Backend
[J] tasks done too: 6 new scanner patterns, 32 passing pytest cases,
`GET /api/runs`, `GET /api/runs/{id}/artifacts.zip`, and the three ROCm
templates hardened. Design direction is in `frontend/DESIGN.md`.

I followed the API-shape rule everywhere (models/api.ts/contract in the same
commit) and did not touch `agents/` or `scoring_service.py`.

## Your open [Y] items (from the tracker)

**Phase 1**
- [ ] Harden `repo_service.clone_repo` (URL validation, size/time limits, `GITHUB_TOKEN`)
- [ ] Expand scanner catalogue; unit-test each category (my `tests/test_scanner.py` has the harness ready — add cases to it)
- [ ] Lock scoring weights against nanoGPT / YOLOv5 / Real-ESRGAN — **see note 1 below, this one matters for the demo**

**Phase 2**
- [ ] Tune Migration Planner prompt against real findings; verify JSON validity
- [ ] Patch Explainer wired to real snippets

**Phase 3**
- [ ] Improve patch transforms (`.cuda()`, `.to("cuda")` → resolved device)
- [ ] Implement `live` validation mode
- [ ] Wire the Failure Diagnoser into the validate path — the Validate screen
  already renders a failure-diagnosis panel when `status == "failed"`; it just
  needs diagnosis text in the response (that's an API-shape change, so
  models.py + api.ts + contract together)

**Phase 4/5:** Report Writer prompt; demo recording + write-up.

## Things I hit while building (your call on each)

1. **Scoring vs real repos:** nanoGPT scans at **70/100 before patching** (15
   findings, few categories). The dramatic 37 → 72 → 86 curve currently only
   holds for the bundled sample. Since nanoGPT is the primary demo repo, the
   weights probably need to come down harder on `cuda_hardcoding` density — or
   we lead the demo with the sample. Your "lock scoring weights" task covers
   this; flagging that it changes the demo story.
2. **Encoding bug (1-line fix, your file):** `validation_service.py` reads the
   fixture with `read_text()` and no encoding. The fixture is UTF-8 with an
   em dash, so on Windows the log renders `â€"` in the UI. Fix:
   `read_text(encoding="utf-8")` (same for `benchmark.json` read).
3. **No single-run GET:** there's no `GET /api/runs/{id}`, so revisiting the
   Scan screen re-POSTs `/scan`, which resets `state.stage` backwards (rail
   LEDs regress). A read-only run-detail endpoint fixes it — you said to pair
   on endpoints, so ping me and I'll take it with you.
4. **Stale doc:** `docs/ARCHITECTURE.md` says Next.js 14; frontend is Next 16 +
   React 19 (verified builds).
5. **Real AMD log:** replay still runs on the scaffold fixture — your TODO to
   capture a genuine AMD Developer Cloud run stands; the templates now print
   parseable PASS/FAIL markers to make that log-parsing easier, and the smoke
   test takes `--require-gpu` for CI.

## Ideas to make it better (full-codebase pass, 2026-07-10)

Tagged by owner: **[Y]** you, **[J]** me, **[Both]** pair on it.

### Demo-critical — do before submission

1. **[J — fixed]** `docker compose up --build` was broken: `frontend/Dockerfile`
   copies `/app/public` but the directory didn't exist. Added
   `frontend/public/.gitkeep`; the full clean-clone compose verify is still my
   Phase 4 task.
2. **[Both] Score story vs reality.** `DEMO_SCRIPT.md` promises "before ≈ 37",
   but nanoGPT scans at **70** (few categories, capped penalties). Either the
   weights come down harder on `cuda_hardcoding` density (your Phase 1 lock
   task) or the demo leads with the bundled sample / YOLOv5 (strongest Docker
   story). Decide once — script and weights should tell the same story.
3. **[Y]** The two encoding reads in `validation_service.py` need
   `encoding="utf-8"` — the saved log renders `â€"` mojibake in the UI on
   Windows machines (i.e., my demo machine).
4. **[Y]** `artifacts.zip` never includes `readiness_report.md`:
   `report_service.build()` writes the file but the report endpoint doesn't
   append it to `state["artifacts"]`. One line in `main.py`; then "download
   everything" is genuinely everything. Ping me and we'll do it together.

### High-impact, low-risk

5. **[Y→J] Wire the Patch Explainer.** `patch_explainer.explain()` is currently
   called by nothing. If you add its output to `PatchResponse` (API-shape rule:
   models + api.ts + contract), I'll render a "why this patch is safe" panel on
   the Patch screen — that's a second visible Fireworks agent for judges.
6. **[Both] Failure Diagnoser demo moment.** `failure_diagnoser.diagnose()` is
   also unwired, and replay always passes, so judges never see it. Add a
   `replay_fail` fixture (broken HIP log) + a `VALIDATION_MODE=replay_fail`
   branch, and we can *show* the diagnoser in 10 seconds. My failure panel
   already renders on failed runs and is waiting for a diagnosis field.
7. **[Y] Scanner polish for real repos:** (a) two patterns matching one line
   produces duplicate rows (e.g. `device = f'cuda:{rank}'` hits both the
   device-string and ordinal patterns); dedupe per line or merge in the
   response. (b) Findings in `.md`/docs files inflate counts — nanoGPT's README
   examples get flagged like code. Downweight or tag them `docs` so the score
   is driven by code.
8. **[Y]** For `.cu`/`.cuh` manual blockers, point `recommended_action` at
   AMD's HIPIFY tooling explicitly — AMD judges will notice the vocabulary.
9. **[J]** "Recent runs" list on Intake (GET /api/runs already exists) — makes
   the cockpit feel like a tool, not a one-shot demo.

### If time allows

10. **[Y]** Capture a *real* AMD Dev Cloud run into `fixtures/` (your TODO).
    The refreshed templates print strictly parseable PASS/FAIL markers and
    `smoke_test.py --require-gpu` exists for CI, so log parsing is easy now.
11. **[J]** GitHub Actions: `pytest` + `next build` on push (Phase 4 optional).
12. **[Both]** Emit the Dockerfile's CUDA-wheel filtering as a reviewable 5th
    artifact (`requirements.rocm.txt`) — deterministic, and it makes the
    "we remove NVIDIA assumptions" claim inspectable.
13. **[Roadmap]** Auto-PR with `patch.diff`; SQLite run history; SSE streaming
    of agent output while the planner thinks.

Report screen (Phase 4 [J]) is my next slice. 🚀
— Jithendra
