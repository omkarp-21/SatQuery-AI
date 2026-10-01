# SatQuery — Final Demo Script (3 minutes)

> Rehearsal script for the live SIH demo. Describes **only real behaviour**
> (`docs/G19_SIH_SOURCE_OF_TRUTH.md` §5). Timings assume the machine is warmed
> per `docs/sih/DEMO_RUNBOOK.md` §C. Keep the machine on; do not reboot.

Roles: **D** = driver (types / clicks), **N** = narrator. One person can do both.

---

### 0:00 – 0:20 — Problem

**N:** "Satellite imagery is everywhere, but answering a real question with it —
*what changed here, where are the affected buildings, does the radar agree?* —
means specialist GIS tools, knowing which model to run, and chaining them by
hand. SatQuery makes that a single natural-language request."

*(Screen: the SatQuery landing page.)*

### 0:20 – 0:35 — Introduce SatQuery

**N:** "It's not one big vision-language model. It's a deterministic planner, a
safety policy, and a bounded agent that runs specialist remote-sensing models
one at a time, watches what they return, adapts, and verifies. All on this
laptop, CPU-only, offline."

### 0:35 – 0:50 — Upload + mission

**D:** selects the four tiles (two optical dates + SAR), pastes the mission:
> "Investigate this area. Identify significant changes between the two
> observations, locate the affected structures, compare optical and SAR
> evidence, and provide a verified summary."
**D:** clicks **Analyze** (INVESTIGATE tab).

**N:** "One mission. No tool names."

### 0:50 – 1:00 — Plan

**N:** "The planner turned it into nine typed steps and chose the tools —
validate, detect change, extract regions, ground the structure, optical-plus-SAR,
cross-check, verify, summarise. A 12-check policy layer cleared it before
anything ran. We also built an LLM planner; it was unreliable, so it's off by
default."

*(Screen: the plan panel, steps pending.)*

### 1:00 – 1:20 — Temporal change

*(Steps tick to ✓.)*

**N:** "ChangeFormer found change across about 25 % of the scene — roughly
0.4 hectares — and we split it into six discrete regions, each with real-world
coordinates."

### 1:20 – 1:40 — Grounding

**N:** "RemoteSAM located the affected structure, and we cross-checked it: the
grounded region falls inside a changed region. Independent corroboration, not one
model's word."

### 1:40 – 2:00 — SAR

**N:** "CROMA produced a joint optical-plus-radar representation. We deliberately
don't let the system assert a conclusion from that embedding — and when we tested
whether SAR improves this task on a larger split, it didn't, so we withdrew that
claim. The representation is computed and shown; nothing is over-stated."

### 2:00 – 2:15 — Verification + confidence

**N:** "Every step passed structural verification. Confidence is a category —
HIGH here — with an explicit why: geometry valid, evidence present, cross-check
passed. Never a made-up percentage."

### 2:15 – 2:40 — Result / report

**D:** clicks **View full report ↗**.

**N:** "One click: a shareable report — mission, plan, findings, spatial
findings with a GeoJSON, evidence, verification, confidence and its reasons,
models used, warnings, and a full audit block. Everything traceable."

### 2:40 – 3:00 — Why it's different (CASE B)

**D:** re-runs with the no-change tile.

**N:** "Same mission. This time the system saw no real change, skipped the
localisation steps, stopped early, and dropped its confidence to MEDIUM — and it
says exactly why. That branch is decided by the real change output, not
hard-coded. That's the point: it reasons about what it observes."

*(End on the CASE B result beside the CASE A report.)*

---

## The one sentence to leave them with

> "Natural-language geospatial investigation → specialist orchestration →
> evidence → verified map and report."

## If you are behind on time

- Skip 1:20–1:40 (grounding narration) and 2:00–2:15 (verification narration).
- **Never skip CASE B** (2:40–3:00) — it is the whole argument.
- If a run is slow, talk through the frozen report
  (`docs/sih/evidence/demos/final/flagship_caseA_change.report.html`) — it is a
  real capture from this machine.
