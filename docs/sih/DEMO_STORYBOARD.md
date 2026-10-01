# SatQuery — Demo Storyboard

> Screen-by-screen. Judge-facing text stays simple; the technical trace is
> expandable, not front-and-centre. All behaviour described here is real —
> see `docs/sih/evidence/demos/final/` and `docs/G19_SIH_SOURCE_OF_TRUTH.md` §5.

Legend: **SEE** = what is on screen · **SAY** = spoken line · **WHY** = why it
matters to a judge.

---

### Screen 1 — Landing

- **SEE**: the SatQuery UI. One page. An **ASK / INVESTIGATE** toggle, a file
  picker, a natural-language box. No login, no cloud.
- **SAY**: "This runs entirely on this laptop, CPU-only, no internet. Two modes:
  ASK for a single question, INVESTIGATE for a multi-step mission."
- **WHY**: local, self-contained, no hidden backend. Sets up "mission" as the
  unit of work.

### Screen 2 — Upload imagery

- **SEE**: four tiles selected — two optical observations, one SAR, one
  no-change optical (for CASE B).
- **SAY**: "Two dates of optical imagery over the same area, plus the radar
  view."
- **WHY**: real multi-modal, multi-temporal input — the hard case the problem
  statement asks for.

### Screen 3 — Enter the mission

- **SEE**: the mission text typed in:
  *"Investigate this area. Identify significant changes between the two
  observations, locate the affected structures, compare optical and SAR
  evidence, and provide a verified summary."*
- **SAY**: "One plain-English mission. No tool names, no parameters."
- **WHY**: the interface is language, not GIS menus.

### Screen 4 — The plan appears

- **SEE**: the **Agent plan & execution** panel — 9 typed steps:
  `VALIDATE_INPUT → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS → GROUND_OBJECT →
  OPTICAL_SAR_ANALYSIS → CROSS_CHECK_EVIDENCE → VERIFY → SUMMARIZE → FINALIZE`,
  and "planner: rule_based".
- **SAY**: "A deterministic planner turned the mission into typed steps and
  chose the tools. We *built* an LLM planner too — it was unreliable, so it is
  off by default. A 12-check policy layer cleared this plan before anything ran."
- **WHY**: planning is explicit, inspectable, and safety-checked — not a
  black-box prompt.

### Screen 5 — Execution timeline

- **SEE**: steps flip to ✓ as they run; each shows a one-line summary
  ("changed_fraction 0.2526 …"). One model runs at a time.
- **SAY**: "Each specialist runs, and the agent *reads* its output before
  deciding the next step."
- **WHY**: this is the "agentic" part — observation drives the next action.

### Screen 6 — Change map

- **SEE**: the change result — ~25.3 % of the scene changed, ~0.41 ha, 6 changed
  regions isolated, each with a lon/lat box.
- **SAY**: "ChangeFormer found the change; we split it into discrete regions with
  real-world coordinates."
- **WHY**: concrete, spatially grounded output — not a sentence, a map.

### Screen 7 — Grounding

- **SEE**: a box over the affected structure; cross-check line: "1/1 grounded
  region(s) fall inside a changed region".
- **SAY**: "RemoteSAM located the structure the mission asked for, and we
  cross-checked that it actually sits inside the changed area."
- **WHY**: independent evidence corroboration, not a single model's word.

### Screen 8 — SAR evidence

- **SEE**: "Optical+SAR: a joint representation (dim 768) was produced —
  representation-level only; no textual fact is inferred from the embedding."
- **SAY**: "We compute a joint optical-plus-radar representation with CROMA. We
  deliberately do **not** have the system assert a conclusion from that
  embedding — and our larger experiment showed SAR did not improve this
  downstream task, so we withdrew that claim."
- **WHY**: scientific honesty; the system never over-reaches from a vector.

### Screen 9 — Verification

- **SEE**: **Verification: SUPPORTED** (aggregate of per-step structural
  checks). Below it, **Confidence: HIGH** with a "Why" list.
- **SAY**: "Structural verification on every step. Confidence is a *category*
  with reasons — geometry valid, evidence present, cross-check passed — never a
  made-up percentage."
- **WHY**: trust is explained, not asserted.

### Screen 10 — Final report

- **SEE**: click **View full report ↗** → a clean, self-contained HTML report:
  mission, understood-as, plan & execution, replans, key findings, spatial
  findings, evidence, verification, confidence category + why, models used,
  warnings, execution time, raw provenance.
- **SAY**: "One click gives a shareable report — everything traceable, nothing
  hidden."
- **WHY**: deliverable a real analyst could hand to a decision-maker.

### Screen 11 (the differentiator) — CASE B, same mission, no change

- **SEE**: re-run with the no-change tile. Plan is identical, but only **2** tool
  calls run; two structured replans (`NEW_EVIDENCE`, `TOOL_FAILURE`);
  `early_stopped = true`; confidence **MEDIUM**; conclusion states "No
  significant change … (below the 1% threshold)".
- **SAY**: "Same mission. The system saw there was no real change, skipped the
  localisation steps, and stopped early — and it says so. This branch is decided
  by the actual change output, not hard-coded."
- **WHY**: this is the proof that the agent *reasons about observations* rather
  than replaying a fixed script.

---

## Panel priority (what's big vs collapsed)

| Prominent (judge-facing) | Collapsed / expandable (technical) |
|---|---|
| Conclusion sentence | full execution trace (timestamped events) |
| Plan steps with ✓ status | raw provenance / audit block |
| Change map + regions | per-evidence JSON payloads |
| Grounding box + cross-check | GeoJSON FeatureCollection (copy button) |
| Verification status + Confidence category & why | policy-check internals |
| **View full report ↗** button | — |
