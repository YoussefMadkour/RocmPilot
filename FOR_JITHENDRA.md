# Hey Jithendra 👋 — start here

> ## ⬆️ Update from Youssef (2026-07-11) — the AI layer grew a lot; here's what touches your UI
>
> All merged to `main`, 152 tests green. New API fields (all additive) for you to render:
> - **`POST /plan`** now returns `{plan, critique, trace}`. `trace` is the real
>   **agent-activity timeline** (orchestrator → planner → critic) — wire your Plan
>   screen's timeline to it. `critique` = `{approved, issues[], notes}` (show an
>   "independent review ✓/✗" badge). It's a **multi-model orchestra**: DeepSeek
>   plans, **GLM critiques** (different model on purpose), Kimi researches.
> - **`POST /patch`** returns `explanations[]` (`{file_path, line_number, original,
>   patched, explanation}`) — a "why this patch is safe" panel per changed file.
> - **`ValidationResult`** now has `diagnosis` (cited, RAG-grounded, Markdown) and a
>   new `mode: "replay_fail"`. Your failure panel already renders `diagnosis` — set
>   `VALIDATION_MODE=replay_fail` to demo it.
> - **Scanner** now flags the **hard 20%**: warp/wavefront-64, WMMA, CUTLASS, CUDA
>   libraries. They arrive as normal findings (category `manual_blocker` /
>   `cuda_dependency`) with AMD-specific text — your findings table shows them as-is,
>   but a "kernel risk" filter/badge would pop.
> - **Scoring is honest** now (nanoGPT ~67, sample 37→72→86) — your score cards
>   already handle the range; just don't hardcode 37.
>
> **AMD demo + setup:** see `docs/AMD_SETUP.md` (where AMD fits, how to capture a real
> MI300X run, live vs replay). **Pitch/story:** `PITCH.md`. **Contract:** always the
> source of truth in `docs/API_CONTRACT.md`.
>
> **Your open [J]:** Report screen, visual polish, clean `docker compose up --build`
> verify, optional CI. And when you want to pair: `GET /api/runs/{id}` (single-run
> fetch) so revisiting a screen doesn't re-POST.
>
> ---

Welcome to **RocmPilot Studio**, our AMD hackathon project. I've scaffolded the
whole thing so you're not staring at an empty repo — it already runs end to end.
This doc is how we'll work together and what's yours to own.

## The one-liner (memorize this)
> Most AI repos are CUDA-first. RocmPilot makes them AMD-ready — scan blockers,
> generate safe patches + a ROCm container, validate on AMD, and score readiness.

## How we'll split it
You own the **frontend cockpit** (the whole thing the judges actually see) **plus
a few backend tasks** so you learn the Python side too. I own the AI agents,
scanner logic, and scoring — the parts that decide whether it feels real. We meet
in the middle at one file: the **API contract**.

Think of it like this: I make the backend *smart*, you make the product *exist and
look great*. Both matter equally for winning.

## Get it running (10 minutes)
```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload         # open http://localhost:8000/docs and click around

# Frontend (new terminal)
cd frontend
npm install
npm run dev                           # open http://localhost:3000, click the button
```
The button on the homepage already calls the backend, scans the sample repo, and
shows real findings + a score. That's your seed — you'll grow it into 6 screens.

## Your first week (in order)
1. **Read three files**, in this order — they're short:
   - `docs/API_CONTRACT.md` — the exact shapes we send over the wire. This is our handshake.
   - `frontend/lib/api.ts` — the typed client. Every screen calls `api.something()`.
   - `frontend/app/page.tsx` — the working example to copy the pattern from.
2. **Run the `frontend-design` skill** before you build UI. Don't ship default
   Tailwind gray — we want an intentional "developer cockpit" look. Commit a short
   note on the direction you pick (colors, type, spacing) so we stay consistent.
3. **Build the Intake → Scan screens first** (Phase 1 in `PROJECT_TRACKER.md`).
   Get one real repo (try `https://github.com/karpathy/nanoGPT`) flowing through.

## Your backend ramp-up tasks (don't skip these — they teach you the codebase)
These are deliberately small, safe, and testable. Nothing here can break the demo.
1. **Add scanner patterns** — open `backend/app/services/scanner_service.py`, find
   the `PATTERNS` list. Each entry is one regex + metadata. Add 5 more (I left
   ideas in the tracker: `pin_memory`, `torch.backends.cudnn`, `apex`,
   `bitsandbytes`, `flash-attn`). Copy an existing entry, change the regex.
2. **Write tests** — `backend/tests/test_scanner.py`. Run a known string through
   the scanner, assert the right finding comes out. This is the best way to learn
   how the scanner thinks. (`pip install pytest`, then `pytest`.)
3. **Add one endpoint** — `GET /api/runs/{id}/artifacts.zip` that bundles the
   generated files. Copy the shape of the existing artifact endpoints in
   `backend/app/main.py`. Ask me and we'll pair on it.

Do these *between* frontend screens when you want a change of pace. If you get
stuck for more than ~30 min, ping me — that's what I'm here for.

## Rules of the road
- **One PR = one thing.** Small PRs, I'll review fast.
- **Never edit `agents/` or `scoring_service.py` without pinging me** — that's the
  AI path and it's easy to break subtly.
- **If you change an API shape, change all three:** `models.py`, `lib/api.ts`, and
  `docs/API_CONTRACT.md`, in the same PR. That's the one rule that keeps us unblocked.
- **Ask early, ask often.** There are no dumb questions on a 3-day hackathon.

## Where everything is
- What to do & when → `PROJECT_TRACKER.md` (phases + your tasks, tagged **[J]**)
- How it fits together → `docs/ARCHITECTURE.md`
- The demo we're building toward → `docs/DEMO_SCRIPT.md`

Let's win this. 🚀
— Youssef
