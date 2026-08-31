# Experiment Decision Tree (post-G1.6)

> How the next experiments branch on their own outcomes, so we don't re-litigate
> the plan each session. Date: **2026-09-01**. Feeds `docs/19_EXPERIMENT_REGISTRY.md`
> and `docs/20_PROTOTYPE_ROADMAP.md`. Every leaf ends in a recorded
> `KEEP / REJECT / INVESTIGATE` + a doc update.

## Ordering principle

Run local, high-information, gap-closing experiments first. Spend money (remote
GPU) only when a mandatory capability is blocked **and** the local option is
measured to be materially worse.

```
                              ┌─────────────────────────────┐
                              │  START: G1.6 accepted         │
                              │  reproduced: RemoteCLIP,      │
                              │  ChangeFormer, CROMA, DOFA    │
                              └──────────────┬──────────────┘
                                             │
        ┌────────────────────────────────────┼────────────────────────────────────┐
        ▼                                    ▼                                    ▼
  EXP-004 (local)                      EXP-002 (local)                      EXP-007 (local)
  optical-only vs optical+SAR          TinyRS vs RSCoVLM-3B                  geospatial gate ON/OFF
  CROMA vs DOFA, reBEN subset,         on RSVQA-LR sample                   (build packages/geospatial
  linear probe, built-up F1           (VQA + grounding, 4-bit/CPU)          metadata + co-reg assert)
        │                                    │                                    │
        ▼                                    ▼                                    ▼
  ┌─────────────────┐             ┌──────────────────────┐            ┌──────────────────────┐
  │ SAR delta > 0   │             │ a local VLM reaches  │            │ gate rejects invalid │
  │ (abs & rel,     │             │ "usable" VQA acc     │            │ pairs, downstream    │
  │ with n, seed)?  │             │ (define threshold    │            │ change-error drops?  │
  └───┬─────────┬───┘             │ vs RSVQA baseline)?  │            └───┬──────────────┬───┘
      │YES      │NO               └───┬──────────────┬───┘                │YES           │NO
      ▼         ▼                     │YES           │NO                  ▼              ▼
 KEEP CROMA/  INVESTIGATE:       KEEP that VLM   TEST FURTHER:       KEEP the gate   REDESIGN gate
 DOFA for    is it preprocessing  (A + B via     rent 1 GPU ≥16 GB,  (H5 supported)  or drop it
 the SAR     (S1 dB/norm/tiling), one model),    reproduce GeoChat                   (H5 rejected —
 path (H3    task choice, or     lock it into    + GeoGround, rerun                  document why)
 supported)  probe capacity?     the registry    EXP-002 remote arm
      │         │                     │                │
      ▼         ▼                     ▼                ▼
 EXP-008 uses the winning       proceed to        if remote VLM also weak:
 encoder for the adaptation     V0.5 wiring       narrow VQA scope in the
 before→after (linear→LoRA)                        demo + say so in the PPT
      │
      ▼
 ┌────────────────────────┐
 │ adapted > frozen       │
 │ (multilabel mAP/F1,    │
 │ before→after)?         │
 └───┬────────────────┬───┘
     │YES             │NO
     ▼                ▼
 KEEP the         INVESTIGATE: probe too small? wrong layer?
 adaptation;      class imbalance? — try LoRA rank/scope,
 req. E satisfied then re-measure. If still flat: report
 (H1 evidence)    honestly that a bounded probe is
                  insufficient and scope a larger adaptation.
```

## Branch details

### EXP-004 — optical vs optical+SAR (CROMA vs DOFA)  → gap D, H3

- **Run 1 done (2026-09-01, `EXP-004.md`):** controlled synthetic-signal sanity
  check. All 3 arms' feature→probe→metric machinery works on the real CROMA/DOFA
  encoders; a SAR-only signal is recovered by CROMA-`joint_GAP` and DOFA-fused
  (1.00) and at chance for optical-only (~0.49). **Directional H3 support; not a
  benchmark; no KEEP/REJECT.** → proceed to Run 2.
- **Run 2 dataset (blocked on a download):** no small labelled S1+S2 set is free —
  `DFC_preprocessed.pt` (CROMA's DFC2020) is **11 GB**; reBEN needs shard pulls.
  Plan: download DFC2020 **once**, use only the **8 874-patch val split**, 8-class
  majority-label scene classification.
- **Inputs (Run 2):** the DFC2020 val split (or a reBEN shard), held-out, leakage-checked.
- **Arms:** (1) optical-only linear probe on S2 features; (2) optical+SAR — CROMA
  `joint_GAP` linear probe; (3) optical+SAR — DOFA S1⊕S2 concatenated features
  linear probe. Same head, same budget, same split.
- **Decide:**
  - SAR delta clearly > 0 on built-up (and ≥ 1 other class), abs + rel, n + seed
    recorded → **KEEP** the better of CROMA/DOFA for the SAR path; that encoder
    goes to EXP-008. H3 **supported** (for these tasks).
  - Delta ≈ 0 or negative → **INVESTIGATE** preprocessing (S1 calibration, dB,
    speckle, norm, 120-px tiling), task suitability, probe capacity — one fix,
    re-measure. If still flat → H3 **not supported for this task**; record it,
    keep optical-only, revisit SAR for change/flood tasks where it should help more.
- **Never** write "SAR improves accuracy" before this experiment produces the number.

### EXP-002 — TinyRS vs RSCoVLM-3B (local)  → gaps A, B

- **Threshold:** define "usable" up front — e.g. within X points of the RSVQA-LR
  published baseline, and grounding acc@0.5 ≥ Y on a DIOR-RSVG sample. Record the
  threshold in the EXP entry *before* running.
- **Decide:**
  - One local VLM clears the threshold → **KEEP** it; it serves both A (VQA) and
    B (grounding); lock into `model_registry.yaml`; proceed to V0.5.
  - Neither clears it → **TEST FURTHER (remote):** this is the trigger to rent
    **one** Linux GPU ≥16 GB and reproduce GeoChat + GeoGround, re-running EXP-002's
    remote arm. If the remote models are also weak on our subset → narrow the VQA
    scope for the demo and state the limitation in the PPT (`docs/16`).

### EXP-007 — geospatial validation gate ON/OFF (local)  → gap G, H5

- Build the `metadata` + `geospatial` validation first (rasterio/pyproj: CRS,
  transform, bounds, GSD, NoData, pair co-registration assertion).
- Stress set: valid pairs + deliberately broken pairs (different CRS / gross &
  sub-pixel offset / different GSD / missing NoData).
- **Decide:** gate rejects the invalid pairs **and** downstream change-metric error
  drops with the gate on → **KEEP** (H5 supported). No effect → **REDESIGN** the
  checks or, if genuinely no benefit, drop the gate and document why (anti-bloat).

### EXP-008 — adaptation probe on reBEN (local)  → gap E, H1

- Uses EXP-004's winning encoder + the same subset/split.
- Linear probe (frozen features + linear head) → then LoRA (rank/scope recorded).
- **Decide:** adapted > frozen on multilabel mAP/F1 (before→after, n, seed) →
  **KEEP**; req. E satisfied; H1 gets local evidence. Flat → **INVESTIGATE** probe
  size / layer / imbalance; if still flat, report that a bounded probe is
  insufficient and scope a larger (but still justified) adaptation.

## Remote-GPU gate (single decision point)

Rent a GPU **only** when *all* of:
1. EXP-002 local arm ran and no local VLM cleared the usability threshold; **and**
2. A mandatory capability (A/B, or C-semantic, or D at higher fidelity) is still
   unmet after the local options; **and**
3. The experiment's information value is high (it changes the stack, not just a number).

Then: one Linux box ≥16 GB, a few hours, batch-reproduce GeoChat + GeoGround +
TEOChat + (optionally, with conda) Change-Agent. Record cost and outcomes.

## What this tree deliberately does NOT branch into

- No new repository hunting (the G1.6 pool is closed).
- No full fine-tuning / from-scratch training.
- No frontend work until A–D are MEASURED.
- No "add a model to be safe" — every KEEP is earned by a measurement.
