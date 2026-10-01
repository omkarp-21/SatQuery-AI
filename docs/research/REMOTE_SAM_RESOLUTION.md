# RemoteSAM — input resolution preparation (G11 Track F)

> RemoteSAM returned `no_box` on a 256 px LEVIR change-detection tile in G10.
> That could be **resolution** (small tile) or **domain** (LEVIR CD imagery ≠
> DIOR object imagery). This experiment isolates resolution: in-domain DIOR-RSVG
> cases, downscaled to 256 px, fed three ways.
> Harness: `evaluation/scripts/exp_remotesam_resolution.py`.
> Status: **DONE 2026-09-02** — B does not beat A, C is worse → production
> preprocessing unchanged; G10 `no_box` reclassified as a domain limit. See Result.

## Method

N in-domain DIOR-RSVG test cases (image + referring phrase + GT box), each:

1. downscaled to **256 px** short side (bicubic) → GT box scaled to match;
2. fed to RemoteSAM three ways, scored acc@IoU0.5 **on the 256-frame**:

| variant | input |
|---------|-------|
| **A `native256`** | the 256 px image as-is |
| **B `upscale2x`** | 256 px → bicubic 2× (512 px) |
| **C `pad_canvas`** | 256 px centred on a 512 px zero canvas (adds margin/context) |

RemoteSAM internally resizes everything to 896², so this measures whether a
better pre-upscale (B) or a larger canvas (C) recovers grounding the raw 256 px
input (A) loses.

## Result

`evaluation/reports/exp_rs_resolution_20260902T104558.json` — n = 10 DIOR-RSVG
cases, CPU, wall time 514.6 s.

| variant | acc@IoU0.5 | no_box | mean IoU |
|---------|:----------:|:------:|:--------:|
| A native256 | **0.90** | 0 | 0.848 |
| B upscale2x | **0.90** | 0 | 0.856 |
| C pad_canvas | 0.70 | 0 | 0.707 |

Per-case notes:

- **A vs B**: identical acc@IoU0.5 (9/10). B's mean IoU is +0.008 — noise. The one
  miss is the same case in both (`image_id 217`, "A ship is on the upper right of
  the small ship" — a relational expression RemoteSAM resolves to the wrong ship;
  a **language** failure, not resolution). No `no_box` in either.
- **C (pad canvas)** is clearly *worse*: two cases collapse (`57` IoU 0.004 —
  predicts nearly the whole canvas; `217` IoU 0.262). Centring a small image on a
  black canvas puts a hard artificial edge in the field of view and shrinks the
  target relative to 896², which hurts more than the extra margin helps.
- **The G10 `no_box` was NOT reproduced.** At native 256 px, RemoteSAM returned a
  box on all 10 in-domain cases (acc 0.90). The G10 `no_box` was on a **LEVIR
  change-detection tile** — that points to **domain** (CD imagery, thin
  linear/building change ≠ DIOR object imagery), not input resolution.

## Decision

_(rule fixed before the run)_ **If B or C does not materially beat A**
(≥ +0.15 acc@IoU0.5 or a large drop in `no_box`), **keep production preprocessing
unchanged.**

**B does not beat A** (0.90 vs 0.90; ΔmeanIoU +0.008; `no_box` already 0). **C is
worse.** → **Production preprocessing is unchanged.** `grounding_slice.py` keeps
handing RemoteSAM the image as-is and letting its own 896² resize do the work. No
resolution-handling branch is added — there is no evidence it would help, and
adding it would be unjustified complexity (`.claude/rules/scope.md`).

The G10 LEVIR `no_box` is reclassified as a **domain** limitation of RemoteSAM
(trained/eval'd on object-centric RS imagery), recorded as a known boundary of
capability B, not a preprocessing bug to fix.
