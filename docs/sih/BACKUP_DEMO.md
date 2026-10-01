# SatQuery — Backup Demo (≤ 60 seconds)

> The guaranteed short visual win. One image, one model, one clear result.
> Use it as the opener if you want an early win, or as the recovery demo if the
> flagship is slow / unavailable. All output is real
> (`docs/sih/evidence/demos/final/secondary_grounding.json`).

## Scenario

**Query:** *"Where is the largest ship?"*
**Image:** `data/demo/grounding/scene.jpg` (a single optical scene, 800 × 800).
**Path:** `SINGLE_IMAGE_GROUNDING` → **RemoteSAM** → box + mask → structural
verification.

## Run it

- UI: **ASK** tab → pick `scene.jpg` → type the query → **Analyze**.
- Headless: `.venvs/satquery/Scripts/python.exe scripts/demo/run_final_demo.py --only secondary`

Expected ≈ 5–65 s (fast when warm).

## What the judge sees

1. The scene with a **box drawn** at pixel `[211, 427, 634, 512]`.
2. `interpreted_task: grounding`, `model_used: RemoteSAM`.
3. **Verification: SUPPORTED** — with the note "structural / deterministic checks
   only — NOT a semantic correctness judgement".
4. A `score` of ~0.999 labelled **"RemoteSAM foreground softmax probability —
   NOT a calibrated confidence"**.
5. A **warning**: "RemoteSAM upstream licence is NOT STATED — treat grounding
   output as prototype-only."

## What to say (≈ 40 s)

> "One image, one question. The router sent this to the grounding specialist —
> not to a VQA model — because it's a 'where' question. RemoteSAM returned a box
> and a mask. We run structural checks — the box is inside the image, the mask
> artefact exists — and we're explicit that this is a *structural* check, not a
> semantic one. That number is the model's raw foreground score, and we label it
> as *not* a calibrated confidence. And we flag that RemoteSAM's checkpoint
> licence isn't stated upstream — so it's an optional component. Nothing is
> hidden."

## Why this is the safe demo

- **One** subprocess, **one** checkpoint (still ~2.5 GB, so warm the machine).
- No planner, no multi-step loop, no cross-model dependency.
- If grounding finds nothing it returns an explicit "no region could be
  grounded" and `warnings: ["no_grounded_region"]` — **never a hallucinated
  box** — which is also a fine thing to show.

## If even this fails

Open `docs/sih/evidence/demos/final/secondary_grounding.json` and the flagship
`*.report.html` in the browser and narrate them. They are real captured runs
from the demo machine, not mock-ups.
