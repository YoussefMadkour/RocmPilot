# Hey Youssef 👋 — status + what's on your plate

*(From Jithendra, 2026-07-10. All [J] tasks through Phase 3 are done, verified
in-browser, and committed — small commits, one thing each, per your rules.)*

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

Report screen (Phase 4 [J]) is my next slice. 🚀
— Jithendra
