# G16 Part 1 — Planner Audit

Snapshot of the agent planner as it stood at the **start of G16** (after G15),
before any G16 change. Read alongside `docs/G14_AGENT_IMPLEMENTATION_MAP.md` and
`docs/G15_AGENT_IMPLEMENTATION.md`.

## TL;DR

- G15's planning metrics were produced **entirely by `RuleBasedPlanner`**. The
  `LlmPlanner` existed but **had never successfully run** — it looked for the
  Qwen2-VL-2B checkpoint at the wrong path (`models/cache/qwen2vl2b/config.json`;
  the files are actually one level deeper in
  `models/cache/qwen2vl2b/Qwen2-VL-2B-Instruct/`), so every call raised
  `FileNotFoundError` and fell straight back to the rule planner.
- The model **is** on disk (4.2 GB, full `safetensors`) and the `.venvs/tinyrs`
  environment can run it, but **CPU only** (`torch 2.13.0+cpu`, `cuda False`).
- The one-shot bridge **reloads the 4 GB model on every call** (~90 s), and the
  G14 prompt is ~2 800 tokens, so a single real plan took **>10 minutes** on this
  laptop. This is the core reason the LLM arm had never been measured.

G16 fixes the path, adds a compact prompt, a persistent model server, a
schema-repair layer, and then measures the real LLM arm.

## 1. Planner interface

`packages/agents/src/satquery_agents/agent/planner.py`

```python
class Planner(Protocol):
    name: str
    def plan(self, mission: str, image_count: int, modalities: list[str]) -> AgentPlan: ...
```

- Pure text in, typed `AgentPlan` out. **No images** are passed to the planner.
- `make_planner()` reads `SATQUERY_PLANNER` (`rule` default | `llm`) and
  `SATQUERY_PLANNER_API_BASE` (→ HTTP provider).
- `plan_with_fallback(mission, image_count, modalities, *, planner=None)
  -> (plan, planner_used, notes)` is what the executor calls. It **never
  raises**: any LLM failure → `RuleBasedPlanner`. `planner_used` ∈
  `{"rule_based", "llm", "rule_based_fallback"}`.
- Consumed by `apps/backend/app/services/agent_runner.py::run_investigation`
  (passes an optional `planner=`), and by `evaluation/agent/run_agent_eval.py`.

## 2. RuleBasedPlanner

- `MissionFeatures` extracts booleans from the mission text (keyword tables
  `_KW`: change / semantic / ground / scene / vqa / sar / compare / investigate /
  regions) plus `image_count` and `modalities`.
- A branch ladder composes a schema-valid plan: flagship multi-step
  (`VALIDATE → TEMPORAL_CHANGE → EXTRACT_CHANGED_REGIONS → GROUND_OBJECT →
  OPTICAL_SAR_ANALYSIS → CROSS_CHECK → VERIFY → SUMMARIZE → FINALIZE`),
  opt+SAR, temporal(+semantic), single-image ground / scene / vqa, and an
  explicit unsupported branch (`VALIDATE → FINALIZE`, reason says unsupported).
- Deterministic, <5 ms, always schema-valid. It is **not** a per-sentence
  hard-code — the same feature logic yields different plans — but it **is**
  keyword-driven, which is exactly what G16 tests the LLM against.

## 3. LLM provider interface

- `LlmPlanner(timeout_s=60.0, provider=…)`; provider `local_qwen` (default) or
  an OpenAI-compatible HTTP endpoint (`_http`, env-configured, `temperature=0`).
- `local_qwen` path: `subprocess.run([.venvs/tinyrs/python, scripts/research/
  planner_infer.py, --weights <dir>, --max-new-tokens 700], input=prompt,
  timeout=self.timeout_s)`. Explicit arg list, hard timeout — no shell string.
- Output handling: `_first_json_object(raw)` scans for the first balanced `{…}`
  and `json.loads` it; then `AgentPlan.model_validate(obj)`. **No repair** — a
  single missing field ⇒ `ValidationError` ⇒ fallback.

## 4/5. Does a local LLM already exist? Which checkpoint?

| | |
|---|---|
| Model | **Qwen2-VL-2B-Instruct** (used text-only — tokenizer + LM head, no vision tower) |
| Location | `models/cache/qwen2vl2b/Qwen2-VL-2B-Instruct/` — `config.json`, `model-0000{1,2}-of-00002.safetensors` (4.2 GB total), tokenizer, `chat_template.json` |
| Env | `.venvs/tinyrs` — `torch 2.13.0+cpu`, `transformers 4.49.0`; **`torch.cuda.is_available() == False`** |
| Bridge | `scripts/research/planner_infer.py` (runs *inside* `.venvs/tinyrs`) |
| GPU | RTX 3050 Ti 4 GB present but **no CUDA torch installed**; fp32 2B ≈ 9 GB would not fit anyway. Planner runs on **CPU**. |
| Status at G16 start | **never executed** — `LlmPlanner._local_qwen` checked `models/cache/qwen2vl2b/config.json` (missing) → `FileNotFoundError` on every call |

## 6. Prompt construction

- `prompts.SYSTEM_PROMPT` — role, the 12-name task ontology, 8 rules
  (VALIDATE first, FINALIZE last, VERIFY before finalize, smallest plan,
  grounding-tool-is-grounding-only, ≤ 8 specialist steps, unsupported →
  VALIDATE+FINALIZE), the **full `registry_digest()` JSON** (12 tools ×
  ~8 fields), and the `AgentPlan` JSON shape.
- `build_user_prompt` — **two** few-shot examples (a 4-step VQA plan and the
  9-step investigation plan) fully serialised, then the mission + image count +
  modalities.
- Total ≈ **2 800 tokens**. On a 2B CPU model the prefill alone is minutes.

## 7. Decoding configuration

`planner_infer.py`: `torch.manual_seed(0)`, `model.generate(max_new_tokens=700,
do_sample=False, temperature=None, top_p=None)` — greedy, deterministic. fp32,
`low_cpu_mem_usage=True`. Loads via `AutoModelForCausalLM`, falls back to
`Qwen2VLForConditionalGeneration`. Chat template applied.

## 8. Schema validation

- `AgentPlan` / `PlanStep` (Pydantic v2): `step_id` pattern `^s[0-9]{1,2}$`,
  `task` ∈ `TaskType` enum, `tool` ∈ `ToolName` `Literal` (closed 12),
  `depends_on` no self-ref, `steps` min length 1, hard cap `MAX_STEPS+4 = 12`,
  no duplicate `step_id`.
- At G16 start there was **no repair step**: `model_validate` either passed or
  the whole plan was discarded.
- The **policy layer** (`policy.validate_plan`, 12 checks) is separate and
  unchanged — it runs on whatever plan (LLM or rule) reaches it and is the
  actual execution guard.

## 9. Timeout behavior

- `subprocess.run(..., timeout=self.timeout_s)` (default 60 s). `TimeoutExpired`
  is caught by `plan_with_fallback` → rule fallback.
- 60 s was far below the real cold-call time (>600 s), so in practice the LLM
  path could only ever have timed out — another reason it was never measured.

## 10. Deterministic fallback

`plan_with_fallback` catches `FileNotFoundError, RuntimeError,
TimeoutExpired, ValueError, ValidationError, JSONDecodeError` **and** any other
`Exception` → constructs a `RuleBasedPlanner` plan, tags `planner_used =
"rule_based_fallback"`. `run_investigation` then adds a `PLANNER FALLBACK`
warning and sets `plan_status = "fallback"`. The UI shows the warning. Never a
silent downgrade.

---

## What G16 changes (summary — details in `docs/G16_AGENT_VALUE_ANALYSIS.md` /
`docs/G16_REAL_LLM_EVALUATION.md`)

| area | G16 change |
|---|---|
| checkpoint path | `LlmPlanner` + bridge now resolve `models/cache/qwen2vl2b/` **or** its single model subdir |
| prompt | new **compact** system+user prompt (~1.4 k tokens, one-line tool list, one few-shot) — default for the small local model; verbose prompt kept behind `SATQUERY_PLANNER_VERBOSE=1` |
| latency | `planner_infer.py --serve` — a persistent JSON-lines model server (load once). `SATQUERY_PLANNER_PERSISTENT=1` opt-in; the evaluation uses it |
| timeout | `LlmPlanner` default raised to 240 s (one-shot); the eval uses the persistent server so per-call cost is generation only |
| repair | new `agent/repair.py` — parse → **safe, intent-preserving** structural repair (renumber `step_id`, coerce `depends_on`, map near-miss tool names, prepend VALIDATE / append VERIFY+FINALIZE, drop unknown keys) → validate; else fallback. Over-long plans are **not** trimmed (a real planning error → fallback) |
| provenance | `PlannerAttempt` (raw output, parse/schema/repair status, repairs, `final_source`, `fallback_reason`) — stored in `provenance.planner_attempt`; the **raw model text is never surfaced to users** |
| fallback tag | `planner_used` gains `"llm_repaired"`; `plan_with_fallback_ex` returns the attempt |
