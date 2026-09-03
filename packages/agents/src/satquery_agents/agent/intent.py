"""Hybrid planner (G17): LLM intent extraction -> deterministic plan synthesis.

G16 measured that the local 2 B LLM cannot build a valid execution graph
(semantic plan validity 0.25, tool-selection 0.40, ~100 s). Its one strength is
understanding the *goal*. So G17 splits the job:

    mission text
      -> IntentExtractor  (LLM, or the deterministic keyword extractor)
      -> typed Intent      (task family + required capabilities + flags)
      -> PlanSynthesizer   (deterministic: ontology + registry + dependencies)
      -> AgentPlan          -> policy -> bounded adaptive execution

The LLM never chooses a tool or orders a step. `PlanSynthesizer` owns execution
safety. `HybridPlanner` wires the two and implements the `Planner` protocol, so
it drops straight into `run_investigation(planner=...)`.

Fallback (Part 13): if LLM intent extraction fails (missing model, timeout,
invalid or unrepairable JSON, crash) the deterministic extractor is used and the
result is tagged `source="rule_based_fallback"` - never silent.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .planner import MissionFeatures, _ground_phrase, _weights_dir
from .schemas import AgentPlan, Capability, Intent, PlanStep, TaskFamily, TaskType

_REPO_ROOT = Path(__file__).resolve().parents[5]

_CAP = Capability
_ALL_CAPS = {c.value for c in Capability}
_ALL_FAMILIES = {t.value for t in TaskFamily}


# --------------------------------------------------------------------------- #
# 1. deterministic intent extractor (also the fallback)
# --------------------------------------------------------------------------- #


def derive_intent_rulebased(mission: str, image_count: int, modalities: list[str]) -> Intent:
    """The G14 keyword/feature logic, expressed as a typed Intent. Deterministic,
    <1 ms, always valid. This is what `RuleBasedPlanner` effectively computes."""
    f = MissionFeatures(mission, image_count, modalities)
    caps: list[Capability] = []
    two_plus = image_count >= 2

    want_regions = f.want_regions
    want_ground = f.want_ground
    want_sar = (image_count >= 3 and (f.has_sar or f.want_compare))
    change_ish = f.want_change or f.want_semantic or want_regions or f.want_investigate

    if f.multi_step and two_plus and change_ish:
        family = TaskFamily.INVESTIGATION
        caps.append(_CAP.TEMPORAL_CHANGE)
        caps.append(_CAP.CHANGED_REGIONS)
        if want_ground or f.want_investigate:
            caps.append(_CAP.GROUNDING)
        if want_sar:
            caps.append(_CAP.OPTICAL_SAR)
        if len([c for c in caps if c in (_CAP.GROUNDING, _CAP.OPTICAL_SAR)]) >= 2:
            caps.append(_CAP.CROSS_CHECK)
    elif image_count == 2 and f.has_sar and f.has_optical and not f.want_change \
            and not f.want_semantic and not f.want_investigate:
        family = TaskFamily.OPTICAL_SAR
        caps = [_CAP.OPTICAL_SAR]
    elif image_count == 2 and f.want_semantic and (f.want_change or f.want_semantic or want_regions):
        family = TaskFamily.SEMANTIC_CHANGE
        caps = [_CAP.SEMANTIC_CHANGE]
    elif image_count == 2 and (f.want_change or f.want_semantic or want_regions):
        family = TaskFamily.TEMPORAL_CHANGE
        caps = [_CAP.TEMPORAL_CHANGE]
        if want_regions:
            caps.append(_CAP.CHANGED_REGIONS)
    elif image_count == 1 and f.want_ground:
        family, caps = TaskFamily.GROUNDING, [_CAP.GROUNDING]
    elif image_count == 1 and f.want_scene:
        family, caps = TaskFamily.SCENE, [_CAP.SCENE_RETRIEVAL]
    elif image_count == 1:
        family, caps = TaskFamily.VQA, [_CAP.VQA]
    else:
        family, caps = TaskFamily.UNSUPPORTED, []

    outputs = ["evidence", "verification"]
    if _CAP.TEMPORAL_CHANGE in caps or _CAP.SEMANTIC_CHANGE in caps:
        outputs.append("change_map")
    if _CAP.CHANGED_REGIONS in caps:
        outputs += ["regions", "geojson"]

    return Intent(
        goal=(mission or "geospatial mission").strip()[:200] or "geospatial mission",
        task_family=family,
        required_capabilities=caps,
        objects=[_ground_phrase(mission)] if (_CAP.GROUNDING in caps) else [],
        temporal_required=_CAP.TEMPORAL_CHANGE in caps or _CAP.SEMANTIC_CHANGE in caps,
        spatial_required=_CAP.GROUNDING in caps or _CAP.CHANGED_REGIONS in caps,
        comparison_required=_CAP.OPTICAL_SAR in caps,
        investigation_required=family == TaskFamily.INVESTIGATION,
        requested_outputs=outputs,
        ambiguity="none",
        source="rule_based",
    )


# --------------------------------------------------------------------------- #
# 2. deterministic PlanSynthesizer:  Intent -> AgentPlan
# --------------------------------------------------------------------------- #


class PlanSynthesizer:
    """Turns a typed `Intent` into a schema-valid `AgentPlan` using the task
    ontology, the tool registry, and fixed dependency/modality rules. No model,
    no per-sentence hard-code. This is the execution-safety owner."""

    name = "plan_synthesizer"

    def synthesize(
        self, intent: Intent, image_count: int, modalities: list[str], *, mission: str = ""
    ) -> AgentPlan:
        steps: list[PlanStep] = []
        n = 0

        def add(task: TaskType, tool: str, inputs: dict, deps: list[str], reason: str,
                cond: str = "tool returned ok and produced its declared output") -> str:
            nonlocal n
            n += 1
            sid = f"s{n}"
            steps.append(PlanStep(step_id=sid, task=task, tool=tool, inputs=inputs,
                                  depends_on=deps, reason=reason, success_condition=cond))
            return sid

        imgs = [f"img{i}" for i in range(max(image_count, 0))]
        val = None
        if image_count >= 1:
            val = add(TaskType.VALIDATE_INPUT, "validate_geospatial_input", {"images": imgs}, [],
                      "validate imagery (format/CRS/transform) and the co-registration gate for a pair",
                      "validation ok" + ("; pair co-registered" if image_count == 2 else ""))

        caps = set(intent.required_capabilities)
        fam = intent.task_family
        phrase = (intent.objects[0] if intent.objects else _ground_phrase(mission or intent.goal))

        def tail(pre: str) -> None:
            v = add(TaskType.VERIFY, "verify_result", {}, [pre],
                    "aggregate structural + geospatial + evidence verification", "verification computed")
            add(TaskType.FINALIZE, "finalize_answer", {}, [v], "produce the report", "report assembled")

        def tail_with_summary(pre: str) -> None:
            v = add(TaskType.VERIFY, "verify_result", {}, [pre],
                    "aggregate structural + geospatial + evidence verification", "verification computed")
            s = add(TaskType.SUMMARIZE, "inspect_evidence", {}, [v],
                    "collate the evidence gathered", "digest built")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s],
                "produce the evidence-first investigation report", "report assembled")

        if fam == TaskFamily.INVESTIGATION and image_count in (2, 3, 4):
            s_ch = add(TaskType.TEMPORAL_CHANGE, "run_temporal_change",
                       {"t1": "img0", "t2": "img1"}, [val],
                       "quantify change between the two observations",
                       "change mask + changed fraction returned")
            s_reg = add(TaskType.EXTRACT_CHANGED_REGIONS, "extract_changed_regions",
                        {"change_result_ref": s_ch}, [s_ch],
                        "turn the change mask into discrete regions",
                        "at least one region or an explicit none")
            cross_deps: list[str] = []
            if _CAP.GROUNDING in caps or intent.investigation_required:
                cross_deps.append(add(
                    TaskType.GROUND_OBJECT, "run_grounding",
                    {"image": "img1", "phrase": phrase}, [s_reg],
                    "locate the affected structures on the post-event image",
                    "a box or an explicit no-region result"))
            if image_count >= 3 and (_CAP.OPTICAL_SAR in caps or intent.comparison_required):
                opt_ref = f"img{image_count - 2}" if image_count >= 4 else "img1"
                cross_deps.append(add(
                    TaskType.OPTICAL_SAR_ANALYSIS, "run_optical_sar",
                    {"optical": opt_ref, "sar": f"img{image_count - 1}"}, [s_reg],
                    "characterise the area with joint optical+SAR features",
                    "a joint representation is produced"))
            if len(cross_deps) >= 2:
                pre = add(TaskType.CROSS_CHECK_EVIDENCE, "cross_check_evidence",
                          {"refs": [s_reg, *cross_deps]}, cross_deps,
                          "check the grounded structures fall inside changed regions",
                          "cross-check computed")
            else:
                pre = cross_deps[-1] if cross_deps else s_reg
            tail_with_summary(pre)

        elif fam == TaskFamily.OPTICAL_SAR and image_count == 2:
            s = add(TaskType.OPTICAL_SAR_ANALYSIS, "run_optical_sar",
                    {"optical": "img0", "sar": "img1"}, [val],
                    "paired optical + SAR -> joint representation", "a joint representation is produced")
            tail(s)

        elif fam == TaskFamily.SEMANTIC_CHANGE and image_count == 2:
            s = add(TaskType.SEMANTIC_CHANGE, "run_semantic_temporal_baseline",
                    {"t1": "img0", "t2": "img1"}, [val],
                    "describe what changed via the EXPERIMENTAL composed baseline",
                    "a change description + regions returned")
            tail(s)

        elif fam == TaskFamily.TEMPORAL_CHANGE and image_count == 2:
            s = add(TaskType.TEMPORAL_CHANGE, "run_temporal_change",
                    {"t1": "img0", "t2": "img1"}, [val], "bi-temporal change detection",
                    "change mask + changed fraction returned")
            if _CAP.CHANGED_REGIONS in caps:
                # "which regions changed" — extract regions, but NOT grounding/SAR
                # (that was the G16 over-planning flaw; the synthesizer fixes it).
                s = add(TaskType.EXTRACT_CHANGED_REGIONS, "extract_changed_regions",
                        {"change_result_ref": s}, [s],
                        "turn the change mask into discrete regions",
                        "at least one region or an explicit none")
                tail_with_summary(s)
            else:
                tail(s)

        elif fam == TaskFamily.GROUNDING and image_count == 1:
            s = add(TaskType.GROUND_OBJECT, "run_grounding",
                    {"image": "img0", "phrase": phrase}, [val],
                    "text -> box + mask on one image", "a box or an explicit no-region result")
            tail(s)

        elif fam == TaskFamily.SCENE and image_count == 1:
            s = add(TaskType.SCENE_UNDERSTANDING, "run_scene_retrieval", {"image": "img0"}, [val],
                    "zero-shot scene tagging", "a ranking is returned")
            tail(s)

        elif fam == TaskFamily.VQA and image_count == 1:
            s = add(TaskType.VQA, "run_vqa", {"image": "img0", "question": mission or intent.goal},
                    [val], "open-ended question about one image", "a text answer is returned")
            tail(s)

        else:
            if not steps:
                add(TaskType.VALIDATE_INPUT, "validate_geospatial_input",
                    {"images": imgs or ["img0"]}, [], "validate whatever was supplied",
                    "validation attempted")
            add(TaskType.FINALIZE, "finalize_answer", {}, [steps[-1].step_id],
                "the mission does not map to a supported specialist operation; finalize honestly",
                "an explicit unsupported result is returned")

        return AgentPlan(
            goal=(mission or intent.goal).strip()[:200] or "geospatial mission",
            inputs=imgs,
            steps=steps,
            constraints=["<= 8 specialist steps", "no fabricated coordinates",
                         "no fabricated evidence", "no confidence values"],
            expected_output="an evidence-backed investigation summary",
            planner=f"hybrid:{intent.source}",
        )


# --------------------------------------------------------------------------- #
# 3. LLM intent extractor
# --------------------------------------------------------------------------- #

_INTENT_SYSTEM = f"""You are a geospatial INTENT EXTRACTOR. Classify the user's mission.
You do NOT choose tools. You do NOT build a plan. You do NOT invent capabilities.
Return ONE JSON object and stop. No prose.

task_family (pick ONE): {", ".join(sorted(_ALL_FAMILIES))}
required_capabilities (0+ from): {", ".join(sorted(_ALL_CAPS))}

Guidance:
- one image, asks what/how-many/describe   -> VQA
- one image, asks WHERE / locate / outline -> GROUNDING (+ objects: the noun)
- one image, asks scene type / land cover  -> SCENE
- two images, asks what changed            -> TEMPORAL_CHANGE (+ CHANGED_REGIONS if it asks which/where)
- two images, asks what KIND of change     -> SEMANTIC_CHANGE
- optical + SAR, asks to compare/fuse them -> OPTICAL_SAR
- asks for several of the above together   -> INVESTIGATION (list every capability it needs)
- impossible / out of scope                -> UNSUPPORTED, capabilities []

JSON shape:
{{"goal":"<one line>","task_family":"<FAMILY>","required_capabilities":["<CAP>",...],
"objects":["<noun>"],"temporal_required":false,"spatial_required":false,
"comparison_required":false,"investigation_required":false,
"requested_outputs":["evidence","verification"],"constraints":[],"ambiguity":"none"}}"""


def _build_intent_prompt(mission: str, image_count: int, modalities: list[str]) -> str:
    mods = ", ".join(modalities) if modalities else "unknown"
    return (f"{_INTENT_SYSTEM}\n\nMISSION: {mission}\n"
            f"IMAGES: {image_count}   MODALITIES: {mods}\nJSON:")


@dataclass
class IntentAttempt:
    raw_output: str = ""
    parse_status: str = "not_attempted"   # ok | no_json | json_error
    schema_status: str = "not_attempted"  # ok | invalid
    repairs: list[str] = field(default_factory=list)
    final_source: str = "none"            # llm | llm_repaired | rule_based_fallback
    fallback_reason: str | None = None
    gen_s: float | None = None

    def public(self) -> dict[str, Any]:
        return {"parse_status": self.parse_status, "schema_status": self.schema_status,
                "repairs": list(self.repairs), "final_source": self.final_source,
                "fallback_reason": self.fallback_reason, "gen_s": self.gen_s}


def _first_json(text: str) -> tuple[dict | None, str]:
    if not text or not text.strip():
        return None, "no_json"
    import re
    t = re.sub(r"```(?:json)?", "", text)
    depth = 0
    start = -1
    for i, ch in enumerate(t):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(t[start:i + 1]), "ok"
                except json.JSONDecodeError:
                    start = -1
    return None, "json_error"


def _repair_intent_dict(obj: dict, mission: str) -> tuple[dict, list[str]]:
    """Safe, intent-preserving fixes only."""
    reps: list[str] = []
    out = dict(obj)
    out.setdefault("goal", (mission or "geospatial mission").strip()[:200] or "geospatial mission")
    if not isinstance(out.get("goal"), str) or not out["goal"].strip():
        out["goal"] = (mission or "geospatial mission").strip()[:200] or "geospatial mission"
        reps.append("filled goal")

    fam = str(out.get("task_family", "")).upper().replace(" ", "_")
    _alias = {"CHANGE": "TEMPORAL_CHANGE", "TEMPORAL": "TEMPORAL_CHANGE",
              "SAR": "OPTICAL_SAR", "OPTICAL_AND_SAR": "OPTICAL_SAR", "FUSION": "OPTICAL_SAR",
              "LOCATE": "GROUNDING", "LOCALIZATION": "GROUNDING", "DETECTION": "GROUNDING",
              "QA": "VQA", "QUESTION_ANSWERING": "VQA", "DESCRIBE": "VQA",
              "CLASSIFICATION": "SCENE", "SCENE_CLASSIFICATION": "SCENE",
              "INVESTIGATE": "INVESTIGATION", "COMPREHENSIVE": "INVESTIGATION",
              "NONE": "UNSUPPORTED", "UNKNOWN": "UNSUPPORTED"}
    fam = _alias.get(fam, fam)
    if fam not in _ALL_FAMILIES:
        out["task_family"] = "UNSUPPORTED"
        reps.append(f"task_family {out.get('task_family')!r} -> UNSUPPORTED")
    else:
        if fam != out.get("task_family"):
            reps.append(f"task_family -> {fam}")
        out["task_family"] = fam

    caps = out.get("required_capabilities") or []
    if isinstance(caps, str):
        caps = [caps]
        reps.append("required_capabilities str -> list")
    _capalias = {"GROUND": "GROUNDING", "CHANGE": "TEMPORAL_CHANGE", "REGIONS": "CHANGED_REGIONS",
                 "SAR": "OPTICAL_SAR", "SCENE": "SCENE_RETRIEVAL", "RETRIEVAL": "SCENE_RETRIEVAL",
                 "CROSSCHECK": "CROSS_CHECK"}
    clean: list[str] = []
    for c in caps if isinstance(caps, list) else []:
        cu = str(c).upper().replace(" ", "_").replace("-", "_")
        cu = _capalias.get(cu, cu)
        if cu in _ALL_CAPS and cu not in clean:
            clean.append(cu)
        elif cu not in _ALL_CAPS:
            reps.append(f"dropped unknown capability {c!r}")
    out["required_capabilities"] = clean

    objs = out.get("objects") or []
    out["objects"] = [str(x) for x in objs][:4] if isinstance(objs, list) else []
    for b in ("temporal_required", "spatial_required", "comparison_required", "investigation_required"):
        out[b] = bool(out.get(b))
    ro = out.get("requested_outputs") or []
    out["requested_outputs"] = [str(x) for x in ro][:8] if isinstance(ro, list) else []
    cs = out.get("constraints") or []
    out["constraints"] = [str(x) for x in cs][:8] if isinstance(cs, list) else []
    amb = str(out.get("ambiguity", "none")).lower()
    out["ambiguity"] = amb if amb in ("none", "low", "high") else "none"
    for k in list(out):
        if k not in {"goal", "task_family", "required_capabilities", "objects", "temporal_required",
                     "spatial_required", "comparison_required", "investigation_required",
                     "requested_outputs", "constraints", "ambiguity", "ambiguity_note", "source"}:
            out.pop(k)
            reps.append(f"dropped unknown key {k!r}")
    return out, reps


def intent_from_raw(raw: str, mission: str, *, gen_s: float | None = None) -> tuple[Intent | None, IntentAttempt]:
    att = IntentAttempt(raw_output=raw or "", gen_s=gen_s)
    obj, att.parse_status = _first_json(raw)
    if obj is None:
        att.schema_status = "invalid"
        att.fallback_reason = f"parse_{att.parse_status}"
        return None, att
    obj.setdefault("source", "llm")
    try:
        it = Intent.model_validate(obj)
        att.schema_status = "ok"
        att.final_source = "llm"
        return it, att
    except ValidationError:
        att.schema_status = "invalid"
    fixed, reps = _repair_intent_dict(dict(obj), mission)
    fixed["source"] = "llm_repaired"
    att.repairs = reps
    try:
        it = Intent.model_validate(fixed)
        att.final_source = "llm_repaired"
        return it, att
    except ValidationError as e:
        att.fallback_reason = f"schema_invalid_after_repair: {str(e)[:120]}"
        return None, att


class LlmIntentExtractor:
    name = "llm_intent"

    def __init__(self, *, timeout_s: float = 90.0):
        # 90 s: an intent classification that cannot answer in this budget is
        # unusable interactively -> the caller falls back to the deterministic
        # keyword extractor. Caps the hybrid path's planning-latency tail.
        self.timeout_s = timeout_s
        self.persistent = os.environ.get("SATQUERY_PLANNER_PERSISTENT", "") == "1"
        self.last_attempt: IntentAttempt | None = None

    def extract(self, mission: str, image_count: int, modalities: list[str]) -> tuple[Intent | None, IntentAttempt]:
        prompt = _build_intent_prompt(mission, image_count, modalities)
        raw, gen_s = self._generate(prompt)
        it, att = intent_from_raw(raw, mission, gen_s=gen_s)
        self.last_attempt = att
        return it, att

    def _generate(self, prompt: str) -> tuple[str, float]:
        if self.persistent:
            from .planner import _PersistentServer  # reuse the loaded model server
            return _PersistentServer.get(self.timeout_s).generate(prompt)
        py = _REPO_ROOT / ".venvs" / "tinyrs" / "Scripts" / "python.exe"
        bridge = _REPO_ROOT / "scripts" / "research" / "planner_infer.py"
        weights = _weights_dir()
        if not py.exists() or not bridge.exists() or weights is None:
            raise FileNotFoundError("local intent model / venv / bridge not available")
        t0 = time.time()
        out = subprocess.run(  # noqa: S603 - explicit arg list + timeout
            [str(py), str(bridge), "--weights", str(weights), "--max-new-tokens", "260"],
            input=prompt, capture_output=True, text=True, timeout=self.timeout_s,
        )
        if out.returncode != 0:
            raise RuntimeError(f"intent bridge exited {out.returncode}: {out.stderr[-300:]}")
        return out.stdout, round(time.time() - t0, 2)


# --------------------------------------------------------------------------- #
# 4. HybridPlanner  (Planner protocol)
# --------------------------------------------------------------------------- #

_INTENT_EXC = (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired, ValueError,
               ValidationError, json.JSONDecodeError)


def _intent_plausible(it: Intent, image_count: int) -> bool:
    """A cheap image-count sanity check on the LLM intent. A mismatch (e.g.
    INVESTIGATION / TEMPORAL_CHANGE with a single image, or VQA / GROUNDING /
    SCENE with a co-registered pair) means the classification is unusable ->
    the caller falls back to the deterministic intent."""
    fam = it.task_family
    if fam in (TaskFamily.INVESTIGATION, TaskFamily.TEMPORAL_CHANGE,
               TaskFamily.SEMANTIC_CHANGE, TaskFamily.OPTICAL_SAR) and image_count < 2:
        return False
    if fam in (TaskFamily.VQA, TaskFamily.GROUNDING, TaskFamily.SCENE) and image_count >= 2:
        return False
    return True


class HybridPlanner:
    """LLM intent extraction -> deterministic PlanSynthesizer. Implements the
    `Planner` protocol. `plan_ex()` also returns the Intent + IntentAttempt."""

    name = "hybrid"

    def __init__(self, *, extractor: LlmIntentExtractor | None = None):
        self.extractor = extractor or LlmIntentExtractor()
        self.synth = PlanSynthesizer()
        self.last_intent: Intent | None = None
        self.last_attempt: IntentAttempt | None = None

    def plan(self, mission: str, image_count: int, modalities: list[str]) -> AgentPlan:
        return self.plan_ex(mission, image_count, modalities)[0]

    def plan_ex(
        self, mission: str, image_count: int, modalities: list[str]
    ) -> tuple[AgentPlan, Intent, IntentAttempt]:
        try:
            it, att = self.extractor.extract(mission, image_count, modalities)
        except _INTENT_EXC as exc:  # noqa: BLE001 handled below
            it, att = None, IntentAttempt(fallback_reason=f"{type(exc).__name__}: {str(exc)[:120]}")
        except Exception as exc:  # noqa: BLE001 - any crash still falls back
            it, att = None, IntentAttempt(fallback_reason=f"crash_{type(exc).__name__}")

        if it is not None and not _intent_plausible(it, image_count):
            att.repairs.append(f"intent family {it.task_family.value} implausible for "
                               f"{image_count} image(s) -> deterministic intent")
            it = None

        if it is None:
            it = derive_intent_rulebased(mission, image_count, modalities)
            it.source = "rule_based_fallback"
            att.final_source = "rule_based_fallback"
            att.fallback_reason = att.fallback_reason or "intent_unusable"

        self.last_intent, self.last_attempt = it, att
        plan = self.synth.synthesize(it, image_count, modalities, mission=mission)
        return plan, it, att


def make_hybrid_planner() -> HybridPlanner:
    return HybridPlanner()
