# Lightweight Model Replacement Audit

> **Question (from the brief):** can the heavyweight RS-VLMs on the critical path
> (GeoChat 7B, TEOChat 7B) be replaced by lighter, more reproducible models
> **without losing mandatory SIH capability** (single-image VQA / grounding /
> captioning, RS-domain adaptation, 4 GB-VRAM feasibility)?
>
> **Scope guard.** No architecture change. No new research repos cloned in this
> pass. Only the five named candidates were inspected, compared against **TinyRS**
> and **GeoChat**. Capabilities are taken from released artifacts / READMEs /
> model cards — **not inferred from paper titles**. No checkpoints were bulk-
> downloaded. No benchmark numbers are fabricated; every number below is tagged
> **#1 authors' / #2 our reproduction / #3 SatQuery** per `docs/18`.
>
> Date: **2026-09-01**. Companion: `EXP-002.md`, `CAPABILITY_GAP_MATRIX.md`,
> `MODEL_TOURNAMENT.md`, `EVIDENCE_LEDGER.md`, `docs/19_EXPERIMENT_REGISTRY.md`.

---

## 1. Candidate comparison (evidence-based)

Legend — **Repo health** as observed 2026-09-01 (commits / stars / last activity /
is there a runnable inference path). **Fit** = fits 4 GB VRAM for *inference*
(fp16 unless a 4-bit path is documented). All parameter counts and licences are
from the model card / repo, not the paper.

| # | Candidate | Type | Params | Licence (code / weights) | Released checkpoint | Runnable inference path today | 4 GB VRAM | CPU | Quant | Repo health | RS-domain | Benchmark evidence we could verify |
|---|-----------|------|:------:|--------------------------|--------------------|------------------------------|:---------:|:---:|-------|-------------|-----------|------------------------------------|
| 1 | **RSCoVLM** (`VisionXLab/RSCoVLM`) | RS multi-task VLM | **3B** & 7B (card: "3B outperforms 7B") | code **MIT** / data CC-BY-4.0 | HF collection `Qingyun/rscovlm` (3B + 7B, multi-task + detection-only) | **Yes** — `scripts/eval.sh`, vLLM or `transformers` generate; JSON/text I/O for detect+ground | 3B @ 4-bit ≈ 2.6–3.2 GB → **tight-fit**; fp16 ≈ 6 GB → no | Yes (slow) | not documented (community GGUF likely via Qwen2.5-VL lineage) | ~35 commits / ~39 ★ / **active 2026**; `Enviroment.md` present; arXiv 2511.21272 (Nov 2025) | **Yes** — trained for aerial detection + grounding + VQA + captioning | README shows multi-task tables; **specific scores not extractable from README** → treat as **#1 DOCUMENTED** |
| 2 | **EarthDial** (`hiyamdebary/EarthDial`) | RS multimodal VLM (InternVL2 + Phi-3-Mini) | **4B** | **MIT (code + weights)** | HF `akshaydudhane/EarthDial_4B_RGB`, `_MS`, `_Methane_UHI` | **Yes** — repo inference scripts, Python 3.9, `transformers`/InternVL stack | 4B fp16 ≈ 8 GB → **no**; 4-bit ≈ 3.2–3.8 GB → **tight-fit, undocumented** | Yes (slow) | **not documented** | ~45 commits / small ★ / CVPR 2025; multi-checkpoint release | **Yes, broadest** — RGB + **SAR** + NIR + multispectral + **bi/multi-temporal**; classification / detection / **captioning** / QA / reasoning / **grounding** / change | 44-dataset eval in paper; README says "outperforms generic and domain-specific models" — **numbers not in README** → **#1 DOCUMENTED** |
| 3 | **Qwen2-VL-2B-Instruct** (`QwenLM/Qwen2-VL`) | Generic VLM (control) | **2B** | **Apache-2.0** | `Qwen/Qwen2-VL-2B-Instruct` (+ community GGUF) | **Yes** — mature `transformers` + `qwen-vl-utils`; native `<\|box_start\|>` bbox grounding | fp16 ≈ 4.5–5 GB → **borderline no**; 4-bit ≈ 1.8–2.2 GB → **fits** | **Yes** (llama.cpp / transformers) | **community GGUF/AWQ**, no official 2B AWQ/GPTQ (7B has them) | upstream Qwen, very active; huge ecosystem | **No — generic** (this is the EXP-001/EXP-002 *control* arm, not an RS answer) | #1 generic: DocVQA 90.1, MMBench-EN 74.9, RealWorldQA 62.9, TextVQA 79.7 (**not RS**) |
| 4 | **SkyEyeGPT** (`ZhanYang-nwpu/SkyEyeGPT`) | RS VLM (MiniGPT-v2 / LLaMA-2) | **~7B** | **NOT stated** (no LICENSE; LLaMA-2 lineage) | HF `ZhanYang-nwpu/SkyEyeGPT` (May 2025) + `SkyEye-968k` dataset | **No** — README: inference tutorial *"coming soon"*; MiniGPT-v2 config wiring not provided | 7B → **no** | impractical | not documented | ~81 commits / moderate ★; weights up but **no inference recipe** | Yes — grounding / REC / captioning / VQA / UAV-video captioning | benchmark tables in README but **metrics not extractable**; no runnable path → **#1 DOCUMENTED, unverifiable** |
| 5 | **ISRO-GeoNLI** (`Vijayavallabh/ISRO-GeoNLI`) | **Pipeline / wrapper, not a model** | n/a (wraps Qwen3-VL + SAM3) | pipeline MIT / Qwen3-VL Apache-2.0 / **SAM3 Meta licence (gated)** | **none of its own** | Yes as a service (FastAPI `/process`, `/query`) | **No** — README recommends **36 GB+ VRAM**, CUDA 12.4 | No | n/a | ~162 commits / ~2 ★; competition-submission style | captioning / grounding / VQA via the wrapped models | **no benchmark numbers**; not lightweight → **reference architecture only** |
| — | **TinyRS / TinyRS-R1** (`aybora/TinyRS`) — *baseline* | RS VLM (Qwen2-VL-2B) | **2B** | code **Apache-2.0** / weights = Qwen2-VL-2B terms | `aybora/Qwen2-VL-TinyRS{,-CoT,-R1,-PRETRAIN}` (HF) | **Yes** — plain `transformers` generate; boxes-in-text grounding | fp16 ≈ 4.5 GB → **borderline**; 4-bit ≈ 1.8 GB → **fits** | Yes (slow) | via Qwen2-VL-2B lineage (community) | Apache-2.0 repo, GRSL 2025, arXiv 2505.12099; **weights download unreliable from this host (4 failed attempts)** | **Yes** — RS VQA / grounding / classification / open-QA; CoT + RL variants | #1 authors': base TinyRS **83.5 % VQA acc** (≈ GeoChat); R1 "matches/surpasses 7B RS models" — **unverified by us** |
| — | **GeoChat** (`mbzuai-oryx/GeoChat`) — *secondary / historical reference* | RS VLM (LLaVA-1.5-7B) | **7B** | Apache¹ (no LICENSE file on weights) | `MBZUAI/geochat-7B` | Needs `deepspeed` / `bitsandbytes` — **unbuildable on Windows** (G1) | **No** | impractical | bnb 4-bit (Linux) | established; widely cited | Yes — RS VQA / grounding / region caption / scene | #1 authors': RSVQA-LR ~90 %; our reproduction **BLOCKED** (no GPU box) |

### Per-candidate verification detail (the brief's checklist)

**RSCoVLM** — *checkpoint:* HF collection `Qingyun/rscovlm`, multi-task + detection-only,
3B & 7B (card explicitly says the 3B is the stronger model). *Licence:* MIT (code),
CC-BY-4.0 (datasets) — usable. *Params:* 3B / 7B. *Env:* Qwen2.5-VL stack (see repo
`Enviroment.md`); PyTorch + `transformers`; vLLM optional for speed. *Inference:*
`bash scripts/eval.sh`; conversation format; detection/grounding emit JSON or text
boxes. *Input:* single RGB image + text. *Output:* text; structured boxes for
detect/ground. *4 GB:* only via 4-bit (tight, quantisation not documented). *CPU:*
possible, slow. *Quant:* not documented. *Repo health:* ~35 commits, ~39 stars,
active in 2026, paper Nov 2025 (arXiv 2511.21272). *Benchmark evidence:* multi-task
capability shown; **no extractable numbers in README** → DOCUMENTED. *Integration
complexity:* **MEDIUM** — same adapter pattern as TinyRS (subprocess to a Qwen2.5-VL
venv), plus box-format parsing.

**EarthDial** — *checkpoint:* three HF checkpoints (`_RGB`, `_MS`, `_Methane_UHI`)
under `akshaydudhane/…`. *Licence:* **MIT for code *and* weights** — the most
permissive of the set. *Params:* 4B (InternVL2 vision + Phi-3-Mini LLM). *Env:*
Python 3.9, InternVL/`transformers` stack. *Inference:* repo scripts; conversation
+ image(s). *Input:* RGB / **SAR** / NIR / multispectral, **single or temporal**.
*Output:* natural-language text + spatial coordinates. *4 GB:* fp16 no (~8 GB);
4-bit maybe (~3.5 GB) but **not documented**. *CPU:* possible, slow. *Quant:* not
documented. *Repo health:* ~45 commits, CVPR 2025, multi-checkpoint release, small
star count. *Benchmark evidence:* 44-dataset evaluation in the paper across
classification/detection/caption/QA/grounding/change; **README gives no numbers**
→ DOCUMENTED. *Integration complexity:* **MEDIUM-HIGH** — InternVL runtime, 4B
size forces a 4-bit path we would have to validate ourselves; broadest modality
coverage of any candidate (only one here that natively claims **SAR + temporal +
grounding + captioning** in one model).

**Qwen2-VL-2B-Instruct** — *checkpoint:* `Qwen/Qwen2-VL-2B-Instruct`. *Licence:*
Apache-2.0. *Params:* 2B. *Env:* recent `transformers` (install from source to
avoid `KeyError: 'qwen2_vl'`), `qwen-vl-utils`. *Inference:* standard generate
loop. *Input:* image(s) + text, dynamic resolution. *Output:* text; **native bbox
grounding** via `<|box_start|>…<|box_end|>` / `<|object_ref_start|>` tokens.
*4 GB:* fp16 borderline (~4.5–5 GB), **4-bit fits comfortably** (~2 GB). *CPU:*
yes (llama.cpp GGUF or transformers). *Quant:* many community GGUF/AWQ; no official
2B AWQ/GPTQ. *Repo health:* upstream Qwen, extremely active, largest ecosystem of
any candidate. *Benchmark evidence:* strong **generic** VLM numbers (DocVQA 90.1,
MMBench-EN 74.9, RealWorldQA 62.9); **no RS benchmark** — it is the *generic
control*, not an RS specialist. *Integration complexity:* **LOW** — best-supported
runtime here; it is the backbone TinyRS and (2.5) RSCoVLM adapt.

**SkyEyeGPT** — *checkpoint:* `ZhanYang-nwpu/SkyEyeGPT` weights + `SkyEye-968k`
dataset on HF (May 2025). *Licence:* **not stated** (no LICENSE file; MiniGPT-v2 /
LLaMA-2 lineage implies non-commercial constraints). *Params:* ~7B. *Env:*
MiniGPT-v2 stack. *Inference:* **no runnable recipe** — README says the inference
tutorial is "coming soon"; config wiring for the released weights is absent.
*Input/Output:* image + text → text, boxes for grounding/REC. *4 GB:* no (7B).
*CPU:* impractical. *Quant:* not documented. *Repo health:* ~81 commits, moderate
stars, weights present but **not runnable as shipped**. *Benchmark evidence:*
tables in README, metrics not extractable. *Integration complexity:* **HIGH** —
7B + missing inference path + licence ambiguity. **BLOCKED (no inference path).**

**ISRO-GeoNLI** — **not a model.** A FastAPI pipeline wrapping Qwen3-VL + SAM3.
*Licence:* pipeline MIT, but SAM3 is under a **gated Meta licence**. *Checkpoint:*
none of its own. *Requirements:* README recommends **36 GB+ VRAM**, CUDA 12.4,
Python 3.10+. *4 GB / CPU:* no. *Repo health:* ~162 commits, ~2 stars,
competition-submission style. *Benchmark evidence:* none. *Value to SatQuery:*
**reference architecture only** — it is an existence proof of a "VLM + segmentation
+ FastAPI query endpoint" ISRO-flavoured stack, which is roughly what `/analyze`
already is. Nothing to integrate; nothing to reproduce.

---

## 2. Best lightweight single-image **VQA** model

**Rank (evidence-weighted):**

1. **RSCoVLM-3B** — RS-domain, MIT code, released 3B checkpoint the authors call
   their *best* model, active repo, runnable eval script. Fits 4 GB only at 4-bit
   (undocumented) — the main risk. **DOCUMENTED**, not yet reproduced.
2. **TinyRS-2B** — smallest true RS-VLM, Apache-2.0, definitively fits 4 GB, venv
   already built. Authors claim 83.5 % VQA (≈ GeoChat). **BLOCKED** on weight
   download from this host (4 failed attempts) — *not rejected*.
3. **Qwen2-VL-2B** — the control. Runs anywhere, but **generic**: it defines the
   floor ("what do you get with no RS adaptation"), it is not the VQA answer.
4. EarthDial-4B — capable but 4B forces an unvalidated 4-bit path; heavier runtime.
5. SkyEyeGPT — no inference path. **BLOCKED.**

**Pick to evaluate first: RSCoVLM-3B**, with **TinyRS-2B** as the co-equal fallback
(smaller, surer fit). Neither has a *verified* VQA number yet — both are #1
DOCUMENTED.

---

## 3. Best lightweight **grounding** model

**Rank:**

1. **RSCoVLM-3B** — grounding is a first-class task in its multi-task training and
   detection-only checkpoint; structured box output; RS-domain. Best evidence of a
   *designed-for-grounding* lightweight RS model.
2. **Qwen2-VL-2B** — **native, well-documented** bbox grounding tokens and the most
   reliable runtime; but generic (RS referring expressions unproven). Strong
   *mechanical* grounding baseline.
3. **TinyRS-2B** — grounding claimed (boxes-in-text), Apache-2.0, fits; unverified,
   BLOCKED on download.
4. EarthDial-4B — claims grounding across 44 datasets; 4B weight/runtime cost.
5. SkyEyeGPT — REC/grounding claimed, no runnable path. BLOCKED.

**Pick: RSCoVLM-3B** for the RS-domain grounding evaluation; **Qwen2-VL-2B** as the
generic-grounding control on the same DIOR-RSVG sample.

---

## 4. Best **combined VQA + grounding** model (one model, both capabilities A+B)

**RSCoVLM-3B.** It is the only lightweight candidate that (a) is RS-domain-trained,
(b) has *released* checkpoints, (c) covers VQA **and** grounding **and** captioning
in one model, (d) has a runnable eval path, and (e) has a permissive licence (MIT
code). Its single weakness is the 4 GB fit (needs 4-bit). **TinyRS-2B** is the
fallback that trades a little capability breadth for a certain memory fit.

EarthDial-4B is the *capability* winner (adds SAR + temporal) but loses on local
feasibility — it belongs on the remote box next to GeoChat, not on the 4 GB laptop.

> **Role update (ADR-012).** "GeoChat = ceiling" is retired. **EarthDial** is now
> the **PRIMARY HIGH-CAPABILITY REFERENCE** (REFERENCE CANDIDATE — not reproduced);
> **GeoChat** is the **SECONDARY / HISTORICAL** reference and is **not** on the
> critical path. Neither is a "ceiling" until reproduced + measured. Authoritative
> hierarchy: `MODEL_TOURNAMENT.md`.

---

## 5. Comparison against the high-capability references (EarthDial, GeoChat)

| Dimension | GeoChat 7B | RSCoVLM-3B | TinyRS-2B | EarthDial-4B |
|-----------|-----------|-----------|-----------|--------------|
| RS VQA (authors' #1) | ~90 % RSVQA-LR | multi-task, no extractable # | 83.5 % (base) | 44-dset, no extractable # |
| Grounding | region caption + ground | first-class task | claimed | claimed (broad) |
| Runs on 4 GB VRAM | **No** | 4-bit only (tight) | **Yes** (4-bit), borderline fp16 | 4-bit only (tight) |
| Runs on Windows dev host | **No** (deepspeed/bnb) | Yes (Qwen2.5-VL stack) | Yes | Yes (InternVL stack) |
| Licence | Apache¹ (weights unclear) | **MIT** code | **Apache-2.0** code | **MIT** code+weights |
| Extra modality | none | none | none | **SAR + temporal** |
| Repro status here | **BLOCKED** (no GPU) | DOCUMENTED, repro pending | **BLOCKED** (download) | DOCUMENTED |

**Read:** EarthDial and GeoChat are *references*, not the default and **not
"ceilings"** (nothing is measured yet). Two lighter models (RSCoVLM-3B, TinyRS-2B)
are *plausible* local replacements for capabilities **A + B** at 4-bit — but
**neither is yet reproduced**, so the references stay the comparison target the
moment a GPU box exists.

---

## 6. Is a remote GPU still necessary?

**Yes — but its role narrows.**

- **Still required for:** (a) the EarthDial (4B) / GeoChat / SkyEyeGPT (7B) reference comparison, (b)
  EarthDial-4B *full* evaluation at fp16 (SAR + temporal arms), (c) EXP-004 Run 2 /
  EXP-008 datasets (multi-GB S1+S2 — unrelated to this audit), (d) reliable
  bandwidth for **any** multi-GB checkpoint, which is the actual thing blocking
  this host (`EXP-002`: 4 failed TinyRS downloads, < 1 MB/s with drops).
- **No longer strictly required for a first VQA/grounding result:** if RSCoVLM-3B
  *or* TinyRS-2B can be fetched and run at 4-bit on the RTX 3050 Ti, capabilities
  A + B get a *local* #2 reproduction and a candidate for V0.5 — without renting a
  box. The blocker is **download reliability**, not compute.

**Recommendation:** keep the remote-GPU gate open (it is justified on infrastructure
grounds), but attempt the local 4-bit RSCoVLM-3B / TinyRS-2B path first — it is
cheaper and, if it clears the usability threshold, defers the rental.

---

## 7. Recommended SatQuery **A/B stack**

> "A/B" = the two experiment arms for the single-image capabilities, **not** a
> commitment to ship. Nothing enters `model_registry.yaml` `models:` until it has a
> #2 reproduction that clears the `EXP-002` threshold (VQA bal-acc ≥ 0.60,
> grounding acc@0.5 ≥ 0.30, CPU ≤ 45 s/query).

| Arm | Model | Role | Where it runs | Gate |
|-----|-------|------|---------------|------|
| **A (primary)** | **RSCoVLM-3B** (MIT, `Qingyun/rscovlm`) | RS-domain VQA + grounding + captioning in one model | RTX 3050 Ti @ **4-bit** (fallback CPU) | reproduce → EXP-002 threshold |
| **A (fallback)** | **TinyRS-2B** (Apache-2.0, `aybora/Qwen2-VL-TinyRS`) | smaller, certain 4 GB fit; RS VQA + grounding | RTX 3050 Ti @ 4-bit / CPU | download → smoke → EXP-002 |
| **B (control)** | **Qwen2-VL-2B-Instruct** (Apache-2.0) | generic floor for VQA + grounding — measures "value of RS adaptation" | anywhere (4-bit / CPU / GGUF) | already runnable |
| **High-capability reference** | **EarthDial-4B** (primary, REFERENCE CANDIDATE) + **GeoChat-7B** (secondary / historical) | local-vs-reference comparison; EarthDial adds the SAR + temporal arms; **not a "ceiling" until reproduced + measured** | **remote** Linux GPU ≥ 16 GB | after local EXP-002 arms are measured |
| Rejected from stack | SkyEyeGPT (no inference path), ISRO-GeoNLI (wrapper, 36 GB) | — | — | — |

Registry `excluded:` block updates (measured facts, statuses only — no capability
claims):

```yaml
rscovlm:        { status: TEST FURTHER, reason: "EXP-002 primary — Qwen2.5-VL-3B, MIT code, HF Qingyun/rscovlm; 4 GB only at 4-bit; local repro pending" }
earthdial_4b:   { status: TEST FURTHER (remote), reason: "InternVL2+Phi-3 4B, MIT code+weights, SAR+temporal+grounding; needs 4-bit or a GPU box; DOCUMENTED only" }
qwen2_vl_2b:    { status: CONTROL, reason: "generic VLM baseline for EXP-001/002 — Apache-2.0, native grounding; not an RS specialist" }
skyeyegpt:      { status: BLOCKED, reason: "~7B; no released inference recipe (README 'coming soon'); licence not stated" }
isro_geonli:    { status: REJECT, reason: "not a model — FastAPI wrapper over Qwen3-VL + SAM3; 36 GB+ VRAM; no own checkpoint" }
tinyrs:         { status: TEST FURTHER, reason: "EXP-002 fallback — 2B Apache-2.0; weight download BLOCKED from this host (see EXP-002)" }
```

---

## 8. Updated capability matrix (A / B only — the audit's scope)

| Cap | Before this audit | After this audit | Evidence level |
|-----|-------------------|------------------|----------------|
| **A. Single-image VQA** | candidate = TinyRS (BLOCKED download) or GeoChat (remote) | **LOCAL A/B PRIMARY = RSCoVLM-3B** (MIT, released 3B, active repo), FALLBACK TinyRS-2B, GENERIC CONTROL Qwen2-VL-2B; references EarthDial (primary) + GeoChat (secondary) — no "ceiling" | still **DOCUMENTED** — no #2 reproduction yet |
| **B. Grounding / captioning** | RemoteCLIP retrieval only (not PS-grounding); TinyRS DOCUMENTED | **primary = RSCoVLM-3B** (grounding is a first-class task; also does captioning), control = Qwen2-VL-2B native boxes | still **DOCUMENTED** |
| SAR + temporal in a VLM (context, not audit scope) | TEOChat 7B (remote, non-commercial) | **EarthDial-4B** is a lighter, **MIT-weights**, SAR+temporal+grounding option for the remote box — replaces TEOChat as the first VLM to try for C/D-language | DOCUMENTED |

No capability moves up a level from this audit — it is a **planning** result:
it swaps the *candidates*, it does not add a *measurement*. The INTEGRATED count
for A/B stays **0**.

---

## 9. Exact next experiment

> **EXP-002 (revised) — RSCoVLM-3B @ 4-bit on the RTX 3050 Ti: load, smoke, then
> a 30–50 Q RSVQA-LR + 20–30 expr DIOR-RSVG sample; TinyRS-2B as the second arm,
> Qwen2-VL-2B as the generic control.**

Concrete steps, in order:

1. **Acquire one checkpoint (bounded).** `huggingface-cli download` the RSCoVLM
   **3B** weights to `models/cache/rscovlm/` — **one attempt, ≤ 15 min wall**,
   `max_workers=2`, `HF_HUB_ENABLE_HF_TRANSFER=0`, resume on. In parallel retry
   TinyRS-2B (`aybora/Qwen2-VL-TinyRS`). If **both** fail → record **BLOCKED
   (artifact acquisition)** in `EXP-002.md`, open the remote-GPU gate, stop.
2. **Env.** New `.venvs/rscovlm` — Python 3.11, `torch` (cpu ok), `transformers`
   matching Qwen2.5-VL, `qwen-vl-utils`, `accelerate`, `bitsandbytes` *if* it
   imports on Windows (else fp32 CPU). No deepspeed, no flash-attn.
3. **Smoke (n = 3–5).** One RS image + a yes/no question + a "where is the X"
   grounding prompt. Assert: model loads under the VRAM budget (or CPU), output is
   coherent, record **s/query**.
4. **Sample eval.** Fixed, id-recorded: 30–50 RSVQA-LR questions (yes/no +
   comparison) → **balanced accuracy**; 20–30 DIOR-RSVG expressions →
   **acc@IoU0.5**; **latency/query**. Same script for TinyRS-2B and Qwen2-VL-2B.
   Label everything **sanity check** (n small) — **#2 our reproduction**, never a
   benchmark.
5. **Decide** against the `EXP-002` threshold: **KEEP** the best local model →
   add to `model_registry.yaml` `models:` with a real adapter + smoke test →
   candidate for a V0.5 `/analyze` VQA path. **Else** open the remote-GPU gate
   (GeoChat + EarthDial-4B + RSCoVLM-7B on a ≥ 16 GB Linux box).

**Do not**: bulk-download all five candidates; clone new research repos; wire any
model into `/analyze` before its adapter smoke test passes; report any of these
numbers without its dataset / split / seed / hardware / date record.

---

¹ GeoChat weights carry no LICENSE file; "Apache" is from repo metadata only.
