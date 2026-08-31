---
name: agent-orchestration
description: SatQuery's planner/router/agent design — deterministic orchestration of specialist calls, not free-form LLM tool use. Covers plan representation, the routing decision, optional LangGraph use, retries, and the agents/specialists stage boundary. Invoke when touching routing, planning, or agents stages.
---

# Agent Orchestration

## Principle: deterministic execution, LLM-assisted planning

The LLM helps **build a plan**. The LLM does **not** freely decide, mid-run, which
model to call next. Once `planning` emits a plan, `agents` executes it
deterministically. This is what makes runs reproducible and auditable.

## Flow

```
routing   -> chooses modality path + candidate models (rules over registry capabilities)
planning  -> emits an ExecutionPlan: a typed DAG of steps
agents    -> executes the DAG deterministically, handles retries/timeouts
specialists -> each step calls one adapter, returns a normalized AdapterResult
```

## ExecutionPlan (typed, serializable)

```python
class PlanStep(BaseModel):
    id: str
    model: str                 # registry key
    task: str                  # must be in that model's supported tasks
    inputs: list[str]          # ids of prior steps or source inputs
    params: dict[str, JsonValue]

class ExecutionPlan(BaseModel):
    query_id: str
    modality_path: Literal["single", "bitemporal", "optical-sar"]
    steps: list[PlanStep]      # DAG; topologically ordered
    fusion: FusionSpec
```

The plan is stored in provenance verbatim. Re-running the same plan on the same
inputs must give the same result (seeds fixed).

## Routing decision

- Rules first: modality of the imagery + task type → allowed models
  (from `packages/model_adapters/model_registry.yaml` capabilities).
- LLM only to disambiguate the natural-language intent into a task + parameters,
  with its output validated against a schema and the registry. An LLM suggestion
  that names an unregistered model or unsupported task is rejected.
- No hidden fallbacks. If routing can't produce a valid plan, it fails with a
  reason the `reports` stage can explain.

## LangGraph

Allowed **only if** it genuinely simplifies the DAG execution/retry logic. If
used: nodes are pure functions over typed state, edges are static or
condition-on-typed-state, and there is **no** agent node with open-ended tool
choice. If a plain topological executor is clearer, use that.

## Retries & failure

- Per-step: bounded retries with backoff for transient errors (I/O, OOM→smaller
  tile). Deterministic errors (unsupported task) do not retry.
- A failed required step fails the plan with a typed error. A failed optional step
  is recorded and execution continues, and the final confidence reflects it.
- Every step logs start/end, inputs digest, duration, outcome.

## Boundary discipline

- `agents` never calls a model directly — only `specialists` steps do, via adapters.
- `agents` never mutates a `specialists` result; `fusion` consumes them.
