# G18 — Release Manifest

> Everything a second person needs to reproduce the SatQuery demo and evaluation.
> Generated for the G18 release candidate.

## Build

| | |
|---|---|
| Git commit (this manifest) | `dcf8deb` on branch `docs/lightweight-model-audit` (G17 head; G18 commit follows) |
| Python | **3.11.0** (product venv `.venvs/satquery`) |
| OS (dev host) | Windows 11 (`Windows-10-10.0.26200-SP0`) |
| Hardware (dev host) | ASUS Zephyrus G14 · RTX 3050 Ti 4 GB · **CUDA UNVERIFIED** (`torch 2.13.0+cpu`, `torch.cuda.is_available() == False`) |
| Product deps | `apps/backend/pyproject.toml` + `packages/*/pyproject.toml` (editable) via `make setup` |
| Research venvs | `.venvs/{tinyrs,croma,dofa,remotesam,changeformer,remoteclip}` — isolated, conflicting model environments; see `docs/research/environment_strategy.md` |

## Frozen model stack (ADR-021 — do not change)

| capability | model | version / upstream commit | checkpoint (path · bytes) |
|-----------|-------|---------------------------|---------------------------|
| A · VQA (primary) | **TinyRS-2B** (Qwen2-VL-TinyRS) | HF `Qwen2-VL-TinyRS` | `models/cache/tinyrs/Qwen2-VL-TinyRS/model.safetensors` · ~4.4 GB · 2 B params |
| A · VQA (fallback) / hybrid intent / rejected LLM planner | **Qwen2-VL-2B-Instruct** | HF `Qwen/Qwen2-VL-2B-Instruct` (bf16) | `models/cache/qwen2vl2b/Qwen2-VL-2B-Instruct/` · ~4.2 GB |
| B · Grounding | **RemoteSAM** | `1e12Leon/RemoteSAM` @ `ebb7bc27` | `models/cache/remotesam/RemoteSAM/RemoteSAMv1.pth` · 2,566,704,235 B · **LICENCE NOT STATED** |
| C · Temporal change | **ChangeFormer** V6 (LEVIR) | `afd1b7ed` | `models/cache/changeformer/CD_ChangeFormerV6_LEVIR_.../best_ckpt.pt` · ~492 MB |
| C · Semantic change | ChangeFormer + RemoteCLIP **composed baseline** (EXPERIMENTAL) | — | (uses the two above) |
| D · Optical+SAR (primary) | **CROMA** base | `antofuller/CROMA` @ `59505a6b` (MIT) | `models/cache/croma/CROMA_base.pt` · 777,563,846 B |
| D · Optical+SAR (fallback) | **DOFA** ViT-base | `0cfb7e10` | `models/cache/dofa/DOFA_ViT_base_e100.pth` · 447,669,164 B |
| Scene / retrieval | **RemoteCLIP** ViT-B/32 | `a6a47875` | `models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt` · 605,208,421 B |
| E · RS adaptation | **LoRA on frozen CROMA** (EXP-008) | r=8, α=16, 42 layers, 811,008 params | `models/checkpoints/exp008_croma_lora.pt` · 3,271,915 B — **opt-in only** (`--lora-weights`); production default is frozen CROMA |

`models/**` is gitignored. Checkpoint fetchers: `scripts/download_models/`.

## Datasets & evaluation splits

| id | purpose | file / manifest | N |
|----|---------|-----------------|---|
| `RSVQA-LR` (mirror `dmarsili/RSVQA-LR-2k`) | VQA sanity eval | `evaluation/datasets/rsvqa_lr_sample.json` | 40 |
| `DIOR-RSVG` (mirror `pzhang1990/DIOR-RSVG`) | grounding sanity eval | `evaluation/datasets/dior_rsvg_sample.json` | 25 |
| **DFC2020 frozen split (G12)** | optical+SAR probe / LoRA — **do not overwrite** | `evaluation/datasets/dfc2020_exp004_split.json` | 400 train / 200 eval |
| **DFC2020 larger split (G18)** | independent optical+SAR re-validation | `evaluation/datasets/dfc2020_g17_larger_split.json` | 600 train / 386 eval (full 986-patch validation) |
| Agent frozen missions (G17) | 3-arm planner eval | `evaluation/agent/frozen_missions_100.json` | 100 (20/category; first 50 = G15/G16 verbatim + `expected_intent`) |
| Trust cases (G18) | confidence rule validation | `evaluation/agent/trust_cases.json` | 30 |
| Demo fixtures | flagship + secondary | `data/demo/investigation/*.tif`, `data/demo/grounding/scene.jpg` | — |

Seeds: DFC probe/LoRA `SEED=20260902`; agent eval deterministic (greedy decoding).

## Test counts (fast suite, `-m "not slow and not gpu and not integration"`)

| suite | tests |
|-------|------:|
| pre-G18 (G10–G17) | 249 |
| G18 trust cases (`test_g18_trust_cases.py`) | 32 |
| G18 failure matrix (`test_g18_failure_matrix.py`) | 22 |
| G18 claim evidence (`test_g18_claim_evidence.py`) | 69 |
| G18 report export (`test_g18_report_export.py`) | 9 |
| G18 CROMA LoRA plumbing (`test_repr_adapters.py::test_croma_lora_weights_recorded_in_provenance`) | 1 |
| **fast total** | **382** — see `docs/G18_RELEASE_REPORT.md` Part 10 for the pass count |

Slow / model tests are marked `@pytest.mark.slow` and skip when a checkpoint/venv
is absent. G18 added `test_croma_lora_adapter_loads_and_changes_representation`
(slow) — loads the persisted EXP-008 LoRA delta through the real `CromaAdapter`,
asserts 42/42 wrapped Linears match and the joint embedding measurably shifts.

## API endpoints

| method + path | purpose |
|---------------|---------|
| `GET /` | self-contained single-page UI |
| `POST /analyze` · `POST /analyze/upload` | NL query + 0–2 images → routed specialist → `NormalizedResponse` |
| `POST /investigate` | agentic investigation → `AgentInvestigationResult` (plan, steps, replans, evidence, verification, **confidence category**, geojson, provenance) |
| `POST /investigate/report` | render an `AgentInvestigationResult` as standalone HTML |
| `GET /artifact?req=&name=` | sandboxed per-request artifact (mask, input echo) |
| `POST /change` · `POST /scene` · `GET /health` | direct specialist / health |

Planner selection: `SATQUERY_PLANNER` env — `rule` (**default**), `hybrid` (opt-in
LLM intent), `llm` (rejected pure planner, kept for the record).

## Reproduce the demo

```bash
make setup && make dev-backend                       # http://127.0.0.1:8000/
.venvs/satquery/Scripts/python.exe scripts/demo/run_final_demo.py
#   -> docs/sih/evidence/demos/final/flagship_case{A_change,B_nochange}.json + secondary_grounding.json
.venvs/satquery/Scripts/python.exe scripts/demo/mission_report.py \
    docs/sih/evidence/demos/final/flagship_caseA_change.json     # -> .report.html
```

## Reproduce the evaluations

```bash
# agent: 3-arm planner eval (100 missions) - ARM A/C fast, ARM B carried from G16
.venvs/satquery/Scripts/python.exe evaluation/agent/run_g17_eval.py --plan
# trust-layer rule validation (30 cases)
.venvs/satquery/Scripts/python.exe -m pytest apps/backend/tests/test_g18_trust_cases.py -q
# optical+SAR, LARGER independent split (986 patches) - G12 split untouched
bash scripts/research/run_g17_larger_de.sh
#   -> evaluation/reports/exp004_run2_g18_larger_*.{json,md}  (probe: SAR benefit did NOT survive)
#   -> evaluation/reports/exp008_g18_larger_*.{json,md} + models/checkpoints/exp008_croma_lora.pt  (LoRA, directional)
# verify the persisted LoRA adapter loads through the real CromaAdapter:
.venvs/satquery/Scripts/python.exe -m pytest -q \
  packages/model_adapters/tests/test_repr_adapters.py -k lora
```

## Hardware status

| | status |
|---|---|
| CPU path (every specialist + agent) | **VERIFIED WORKING** on the dev host |
| 4 GB GPU fit | **UNVERIFIED** — no CUDA build; no numerical VRAM claim is made |
| One model resident at a time | **enforced** — subprocess-per-specialist, released before the next |
| CPU RSS observed | TinyRS ~6 GB · RemoteSAM ~6–8 GB · CROMA ~1.3 GB · DOFA ~1.0 GB · Qwen2-VL-2B ~3 GB (bf16) |
| specialist cold-load latency | grounding ~70 s · temporal ~17 s · optical+SAR ~13 s · VQA ~27 s (≈ 90 % load, not inference) |

## Known caveats (also in PROJECT_STATUS)

- Evaluation is **sanity-scale** (n = tens–hundreds); significance stated per number.
- **DFC2020 SAR benefit does not survive the larger split** (G18 Part 2) — the G12 +0.067 was within noise.
- **4 GB GPU fit UNVERIFIED.**
- **RemoteSAM checkpoint licence NOT STATED** — packaged as an optional component.
- Deterministic planner is the **production default**; pure local LLM planner **rejected**; hybrid intent planner **optional**.
- Semantic-change *language* remains an **experimental** composed baseline.
- Confidence is an **evidence-derived category**, never a probability.
