# RocmPilot Studio — Submission Demo Video Script (~3:00)

**Format:** screen recording of the app + voiceover. Structure: **Why → Problem →
Solution → Live demo → Close.** Read the NARRATION out loud; do the ACTION on screen
at that moment; WHY is a director's note (don't read it).

---

## Pre-flight checklist (do this BEFORE you hit record)
- Backend up on **:8001**, frontend on **:3000** (`frontend/.env.local` points at 8001).
- **Pre-warm the YOLOv5 run** so every screen is instant (no 40s spinner on camera):
  open `http://localhost:3000/runs/788690735404/scan` and click through all 6 screens once.
- Keep two tabs ready: the **YOLOv5** run (hero) and a **fresh Intake** tab (`http://localhost:3000`).
- Full-screen the browser; hide the bookmarks bar / other tabs for a clean frame.
- Optional wow: a second run in `VALIDATION_MODE=replay_fail` for the diagnosis beat.

---

## 0:00 – 0:25 · THE WHY  *(screen: a title slide or the Intake page, static)*
> **SAY:** "AMD's MI300 GPUs beat NVIDIA on price-performance. So why is almost every
> AI team still stuck on NVIDIA? It's not the hardware — it's the *software*. Moving a
> codebase to AMD is a slog, and worse: nobody can even tell you up front whether their
> project will run on AMD, or how much work it'll take."

*WHY: open on the business stakes (Unicorn track = market). Name the real blocker —*
*uncertainty + migration friction — not raw perf.*

## 0:25 – 0:45 · THE PROBLEM  *(screen: Intake page)*
> **SAY:** "A typical AI repo is CUDA-first top to bottom — NVIDIA base images,
> CUDA-only install wheels, hardcoded `cuda` device code, and sometimes hand-written
> GPU kernels. Automatic tools convert the easy majority, but the tail — and the
> not-knowing — is what stalls real migrations for weeks."

*WHY: set up exactly what RocmPilot will then resolve on screen. Keep it tight.*

## 0:45 – 1:00 · THE SOLUTION  *(screen: Intake page — the hero headline "CUDA-first in. AMD-ready out.")*
> **SAY:** "RocmPilot Studio is a migration command center. You give it a repo URL, and
> it triages the whole codebase, fixes what it can, containerizes it for ROCm, validates
> it on real AMD hardware, and hands you an honest readiness score — end to end, with a
> team of AI agents doing the reasoning."

> **DO:** In the fresh Intake tab, click the **`ultralytics/yolov5`** suggestion chip so
> the URL fills in. *(Don't start it — cut to the pre-warmed run for speed.)*

*WHY: state the one-liner while the product is on screen. YOLOv5 = a repo with real*
*NVIDIA blockers, so the before/after is genuine.*

## 1:00 – 1:20 · SCAN  *(screen: the pre-warmed YOLOv5 run → Scan)*
> **DO:** Switch to the YOLOv5 run tab (already on Scan).
> **SAY:** "In seconds, a deterministic scanner — no LLM, so it can't hallucinate —
> reads all 131 files and scores this repo **43 out of 100**. It found the real
> blockers: an NVIDIA Docker base image, CUDA-only dependencies, and hardcoded devices."
> **DO:** Click the **`nvidia docker`** category chip to filter.
> **SAY:** "There's the `nvidia/cuda` base image and `--gpus all` — the things that
> literally won't run on AMD."

*WHY: 43 (not ~70) proves the score means something; the nvidia_docker filter is the*
*"this is a real problem" moment.*

## 1:20 – 1:45 · PLAN  *(screen: Plan)*
> **DO:** Click **"Generate migration plan →"** (on the pre-warmed run it's instant;
> if you want the live effect, do this on a fresh run and let it stream).
> **SAY:** "Now a multi-agent team takes over — all running on AMD hardware through
> Fireworks. **DeepSeek** drafts the migration plan, and then a *different* model,
> **GLM**, independently critiques it before we ever see it. Watch the agents work in
> the activity trace — each step tagged with the model that ran it."
> **DO:** Point at the **model badges** (`deepseek-v4-pro`, `glm-5p2`) and the
> **Critic: approved** badge.

*WHY: this is the multi-model + independent-review differentiator. The badges make it*
*concrete and on-brand for AMD (models hosted on AMD).*

## 1:45 – 2:10 · PATCH  *(screen: Patch — open the Dockerfile tab)*
> **DO:** Click **"Generate patches →"**, then click the **`Dockerfile.rocm`** tab.
> **SAY:** "It generates the actual fixes. This is the key one: it replaced the NVIDIA
> base image with a **ROCm PyTorch** image and filtered out the CUDA-only install
> wheels — so the repo will actually build and run on AMD. It also patched the device
> code and wrote a smoke test and benchmark."
> **DO:** Click the **`patch.diff`** tab briefly to show the red/green device fix, then
> hover **"Download patched repo (.zip)"**.
> **SAY:** "And you can download the fully patched, ready-to-run repo."

*WHY: the ROCm Dockerfile is the "we removed the NVIDIA assumption" proof — the concrete*
*thing that makes it run on AMD. Show the artifact, don't just claim it.*

## 2:10 – 2:35 · VALIDATE  *(screen: Validate)*
> **DO:** Click **"Run AMD validation →"**.
> **SAY:** "Then we validate on **real AMD hardware** — this ran on a Radeon GPU on
> AMD's cloud: ROCm detected, smoke test passed, latency measured. The readiness jumps
> to **86**. And notice the badge — we're honest that this is a saved run, not faked."
> **DO:** Point at **AMD Radeon (gfx1100)**, **passed**, **86/100**, and the
> **"Saved AMD run"** badge.

*WHY: real hardware + honesty. The honesty badge is a trust signal judges respect.*

## 2:35 – 2:55 · REPORT  *(screen: Report)*
> **DO:** Click **"View readiness report →"**.
> **SAY:** "Finally, a judge-ready report — readiness went **43 → 72 → 86** — written by
> another AMD-hosted model, with the fixes, the artifacts, and the evidence. From a repo
> URL to an AMD-ready, validated deployment, in minutes."
> **DO:** Point at the **43 → 72 → 86** score journey; hover **"Download report"**.

*WHY: closes the before→after arc with a downloadable, trustworthy artifact.*

## 2:55 – 3:00 · CLOSE  *(screen: Report, or a title card)*
> **SAY:** "RocmPilot removes the uncertainty and the grunt work that keep teams on
> NVIDIA — so AMD adoption stops being a months-long question and becomes a minutes-long
> answer. That's how the ROCm ecosystem grows."

*WHY: land the mission (AMD adoption) — ties back to the Why.*

---

## Optional 15-sec bonus beats (drop in if you have room)
- **The hard 20%:** on a kernel-heavy repo (detectron2, score ~12) show the **kernel-risk
  callout** — "for repos with custom CUDA kernels, we precisely flag what needs manual
  porting." *(Positions us honestly on the deepest problem.)*
- **It actually runs:** the `run_nanogpt_on_amd.ipynb` output — nanoGPT **generating text
  on the AMD GPU**. "Not just a report — the patched model runs on AMD."
- **Failure diagnosis:** a `replay_fail` run — the Validate screen's cited, `kimi-k2p6`
  diagnosis. "When something breaks, a research agent tells you why, with sources."

## Delivery tips
- Talk to the *value*, not the UI ("it found the real blockers", not "here's a table").
- Never say "it fails on AMD without us" for a clean repo — for YOLOv5 the honest line is
  "the NVIDIA Docker setup won't run on AMD; we replaced it."
- Pause ~1s after each click so the cut reads cleanly.
- Keep the cursor deliberate; point at the number/badge you're naming.
