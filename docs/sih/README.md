# SatQuery — SIH Package (G19)

> Everything needed to present SatQuery at SIH 2026 (PS 26167). **Start with the
> Source of Truth**, then the story, then the demo. `FINAL_TECH_FREEZE = TRUE` —
> after G19: bug fixes, demo reliability, docs, and presentation assets only.

## Read in this order

| # | Doc | Purpose |
|---|-----|---------|
| 0 | [`../G19_SIH_SOURCE_OF_TRUTH.md`](../G19_SIH_SOURCE_OF_TRUTH.md) | **The reference.** What we can / cannot claim · exact metrics (with N) · exact limitation wording · frozen flagship facts · architecture facts. Nothing on a slide or in an answer unless it agrees with this. |
| 1 | [`SIH_CORE_STORY.md`](SIH_CORE_STORY.md) | Problem → insight → SatQuery → differentiation → impact, for a non-ML judge. |
| 2 | [`PITCH.md`](PITCH.md) | Five one-sentence pitches + the final one; the ≤ 30-second spoken explanation. |
| 3 | [`ARCHITECTURE_DIAGRAM.md`](ARCHITECTURE_DIAGRAM.md) | PPT diagram + text description + MODEL / SYSTEM / SAFETY legend + a 6-box simplified version. |
| 4 | [`NOVELTY_ARGUMENT.md`](NOVELTY_ARGUMENT.md) | 9 system-composition points: existing approach → SatQuery difference → evidence. |
| 5 | [`COMPETITOR_COMPARISON.md`](COMPETITOR_COMPARISON.md) | Capability matrix: GIS · generic VLM · single RS-VLM · static pipeline · SatQuery. |
| 6 | [`RESULTS_SLIDE_DATA.md`](RESULTS_SLIDE_DATA.md) | Only validated numbers, each with its N and context; the "do not present as positive" list. |
| 7 | [`RESEARCH_HONESTY_SLIDE.md`](RESEARCH_HONESTY_SLIDE.md) | "What we learned" — the negative/inconclusive findings as a credibility argument. |
| 8 | [`USE_CASES.md`](USE_CASES.md) | Disaster assessment · infrastructure monitoring · agriculture — user → mission → output → decision. |
| 9 | [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md) | NOW / NEXT / LATER; what is explicitly not on the roadmap. |

## Demo

| Doc | Purpose |
|-----|---------|
| [`DEMO_STORYBOARD.md`](DEMO_STORYBOARD.md) | 11 screens: what the judge sees · what we say · why it matters. |
| [`FINAL_DEMO_SCRIPT.md`](FINAL_DEMO_SCRIPT.md) | The 3-minute rehearsal script, 0:00–3:00. |
| [`BACKUP_DEMO.md`](BACKUP_DEMO.md) | The ≤ 60-second guaranteed grounding demo (opener or recovery). |
| [`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md) | Machine prep · env checks · model warm-up · DEMO / RECOVERY / FALLBACK / FAILURE modes · exact expected output · what to say if something fails. |
| [`FINAL_CHECKLIST.md`](FINAL_CHECKLIST.md) | The day-before / hour-before tick list. |

## Q&A

| Doc | Purpose |
|-----|---------|
| [`JUDGE_QA.md`](JUDGE_QA.md) | Prepared answers to the top 30 judge questions. |
| [`JUDGE_QA_NEGATIVE_RESULTS.md`](JUDGE_QA_NEGATIVE_RESULTS.md) | The SAR-benefit-withdrawn and LLM-planner-rejected answers, in detail. |
| [`CLAIM_MATRIX.md`](CLAIM_MATRIX.md) | Every claim · evidence · N · **allowed / forbidden wording**. The G19 public claim sheet is at the top. |

## Evidence

- [`evidence/README.md`](evidence/README.md) — the traceability pack (every slide claim → a source or an experiment).
- [`evidence/demos/final/`](evidence/demos/final/) — the **frozen** flagship set: `flagship_caseA_change.json` / `flagship_caseB_nochange.json` / `secondary_grounding.json` (+ `*.report.html`). Regenerate with `python scripts/demo/run_final_demo.py`.

## The 60-second judge takeaway

> **What** — natural-language geospatial investigation over single-image,
> bi-temporal, and optical/SAR imagery.
> **Why not one VLM** — different questions need different specialists; one model
> is weaker at each and GPU-bound.
> **What's different** — deterministic planner + 12-check policy + a bounded
> agent that observes each specialist and adapts + geospatial validation +
> evidence + structural verification.
> **Trust** — every claim traced to an observation; 22/22 failure cases resolve
> cleanly; confidence is a category with a why, never a number.
>
> Remembered after the demo: **natural-language geospatial investigation →
> specialist orchestration → evidence → verified map / report.**
