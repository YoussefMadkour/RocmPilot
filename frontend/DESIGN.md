# RocmPilot Studio — design direction

*(Phase 1 note, as requested in FOR_JITHANDRA.md — keep every screen consistent with this.)*

## Concept: engine-bay cockpit

The UI is an instrument panel for a six-stage flight: Intake → Scan → Plan →
Patch → Validate → Report. The backend enforces that order (409 out of
sequence), so the UI's job is to make **sequence + status** legible at all
times. The signature element is the **flight-check rail**: a persistent left
rail with numbered stages and LED status dots driven by the real run state.

## Color

Red-warmed dark, not neutral gray — the whole surface leans subtly toward the
AMD end of the spectrum instead of stock Tailwind `neutral-*`.

| Token | Hex | Use |
|---|---|---|
| `bay` | `#141014` | page background |
| `panel` | `#1C1519` | cards, rail |
| `edge` | `#2B2026` | borders, dividers |
| `accent` | `#ED1C24` | AMD signal red — interactive + brand ONLY |
| `ember` | `#FF8A3D` | in-progress, caution |
| `ready` | `#3DDC97` | pass / done states |
| `ink` / `ink-dim` | `#F2EDEE` / `#A89DA2` | text |

Severity badges (Scan screen, Phase 2): critical `#FB7185`, high `#FF8A3D`
(ember), medium `#FACC15`, low `#A89DA2`. Keep brand red for actions so a
"critical" row never looks clickable.

## Type

- **Display — Chakra Petch** (600/700): squared, HUD-like. Headings and stage
  labels only; never body text.
- **Body — IBM Plex Sans**: everything readable.
- **Data — IBM Plex Mono**: file paths, scores, logs, badges, run ids.

Loaded via `next/font/google` (self-hosted at build, no runtime CDN).

## Layout

```
┌────────────────────────────────────────────────┐
│ topbar: wordmark · run id · mode badge         │
├──────────┬─────────────────────────────────────┤
│ 01 INTAKE│                                     │
│ 02 SCAN  │   stage content                     │
│ 03 PLAN  │   (max-w-3xl/4xl, quiet panels)     │
│ 04 PATCH │                                     │
│ 05 VALID │                                     │
│ 06 REPORT│                                     │
│ ──────   │                                     │
│ score    │                                     │
└──────────┴─────────────────────────────────────┘
```

Rail collapses to a horizontal stepper below `md`.

## Rules of restraint

- One accent. Red means "you can act on this" — nowhere else.
- Numbers (01–06) exist because the pipeline is genuinely ordered. Don't add
  ornamental numbering anywhere else.
- Motion: LED pulse on the in-progress stage, nothing ambient. Respect
  `prefers-reduced-motion`.
- Replay-mode validation must always show the ember "SAVED AMD RUN" badge —
  honesty is part of the visual language.
- Copy: plain verbs, sentence case. Buttons say what happens ("Start scan",
  not "Submit").
