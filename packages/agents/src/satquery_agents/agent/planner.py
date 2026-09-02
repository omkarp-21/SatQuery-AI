"""Planners (G14): pluggable, small, text-only, structured-JSON output.

`RuleBasedPlanner` — always available, no model. Extracts features from the
mission (image count, modalities, verbs/nouns) and composes a schema-valid
`AgentPlan` from the task ontology. This is NOT a per-sentence hard-code: the
same feature logic produces different plans for different missions, and the
executor (`agent_runner`) prunes / extends the plan based on live observations —
that conditional-on-observation behaviour is where the agenticity lives.

`LlmPlanner` — optional. Runs a small local instruction model (Qwen2-VL-2B in
text-only mode via `.venvs/tinyrs`) or an HTTP provider, parses the first JSON
object as an `AgentPlan`. Any failure (missing model, timeout, invalid JSON,
crash) → the caller falls back to `RuleBasedPlanner` (`plan_with_fallback`).

`make_planner()` reads `SATQUERY_PLANNER` (`rule` default | `llm`) so the default
product is demo-robust without a planner model.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import AgentPlan, PlanStep, TaskType

_REPO_ROOT = Path(__file__).resolve().parents[5]

# --------------------------------------------------------------------------- #
# feature extraction
# --------------------------------------------------------------------------- #

_KW = {
    "change": ("change", "changed", "differ", "difference", "before and after", "bitemporal",
               "bi-temporal", "what happened", "evolv", "compare these two", "compare the two",
               "compare those two", "between these dates", "between the two"),
    # "describe the change" style — a flavour of change, not an extra analysis.
    # Every phrase must reference the change explicitly so it can't match a plain
    # "characterize this scene" (that is optical+SAR / scene, not semantic-change).
    "semantic": ("what kind of change", "what type of change", "describe what changed",
                 "describe what kind", "explain the change", "semantic change",
                 "nature of the change", "characterize the change", "characterise the change"),
    # grounding = a locative VERB phrase, never a bare noun (nouns also occur in VQA questions)
    "ground": ("where is", "where's", "where are", "locate", "identify the", "point to", "point at",
               "show me the", "which region", "pinpoint", "mark the", "highlight the"),
    "scene": ("what type of scene", "what kind of scene", "land cover", "classify the scene",
              "airport or", "retrieve similar"),
    "vqa": ("how many", "count", "is there", "are there", "does the", "what color", "what is in",
            "what objects", "what can you see", "?"),
    "sar": ("sar", "radar", "sentinel-1", "backscatter", " vv", " vh", "optical and sar",
            "optical vs sar", "fuse the sentinel"),
    "compare": ("compare the optical", "compare these optical", "using sar", "with sar",
                "sar evidence", "sar and optical", "complementary information"),
    "investigate": ("investigate", "investigation", "full analysis", "comprehensive",
                    "step by step", "and then locate", "and locate", "and identify the",
                    "and compare", "evidence-backed", "verified summary", "affected structures",
                    "affected buildings", "changed buildings", "changed structures",
                    "assess the changes", "summarize the evidence", "summarise the evidence",
                    "remote sensing investigation", "investigate this location"),
    # "which regions / the largest changed area" -> extract discrete regions from the mask
    "regions": ("changed area", "changed areas", "changed region", "changed regions",
                "which region", "which regions", "largest changed", "affected region",
                "affected regions", "the changed"),
}


class MissionFeatures:
    def __init__(self, mission: str, image_count: int, modalities: list[str]):
        q = (mission or "").lower()
        self.mission = mission
        self.image_count = image_count
        self.modalities = [m.lower() for m in modalities]
        # a REAL SAR raster is present iff the modality list says so, or there are
        # >= 3 images (T1, T2, ..., SAR). A bare "SAR" keyword with only optical
        # rasters is a mention, not an available input.
        self.sar_modality = "sar" in self.modalities
        self.has_sar = self.sar_modality or image_count >= 3
        self.sar_mentioned = self.sar_modality or any(k in q for k in _KW["sar"])
        self.has_optical = ("optical" in self.modalities or "multispectral" in self.modalities
                            or not self.modalities)
        self.want_change = any(k in q for k in _KW["change"])
        self.want_semantic = any(k in q for k in _KW["semantic"])
        self.want_ground = any(k in q for k in _KW["ground"])
        self.want_scene = any(k in q for k in _KW["scene"])
        self.want_vqa = any(k in q for k in _KW["vqa"])
        self.want_compare = any(k in q for k in _KW["compare"])
        self.want_investigate = any(k in q for k in _KW["investigate"])
        self.want_regions = any(k in q for k in _KW["regions"])
        # a mission is "multi-step" if it asks for >= 2 DISTINCT analyses.
        # "describe the change" (semantic) is a flavour of change, not an extra ask.
        pair = image_count >= 2
        asks = sum([self.want_change or self.want_semantic,
                    self.want_ground and pair,
                    (self.has_sar or self.want_compare) and image_count >= 3,
                    self.want_regions and pair])
        self.multi_step = self.want_investigate or asks >= 2


# --------------------------------------------------------------------------- #
# Planner protocol
# --------------------------------------------------------------------------- #


class Planner(Protocol):
    name: str

    def plan(self, mission: str, image_count: int, modalities: list[str]) -> AgentPlan: ...


# --------------------------------------------------------------------------- #
# rule-based planner
# --------------------------------------------------------------------------- #


class RuleBasedPlanner:
    name = "rule_based"

    def plan(self, mission: str, image_count: int, modalities: list[str]) -> AgentPlan:
        f = MissionFeatures(mission, image_count, modalities)
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

        imgs = [f"img{i}" for i in range(image_count)]
        last = None
        if image_count >= 1:
            last = add(TaskType.VALIDATE_INPUT, "validate_geospatial_input", {"images": imgs}, [],
                       "validate imagery (format/CRS/transform) and the co-registration gate for a pair",
                       "validation ok" + ("; pair co-registered" if image_count == 2 else ""))
        val = last

        two = image_count == 2
        # a temporal pair: an explicit CHANGE intent, OR an investigation of a 2+-image scene
        # (an "investigation" of a temporal pair is intrinsically about change).
        temporal_pair = image_count in (2, 3, 4) and (
            f.want_change or f.want_semantic or f.want_regions or f.want_investigate)
        # optical+SAR wins for a 2-image opt+SAR mission that is NOT about change
        opt_sar = two and f.has_sar and f.has_optical and not f.want_change and not f.want_semantic \
            and not f.want_investigate
        temporal = two and (f.want_change or f.want_semantic or f.want_regions) and not opt_sar
        single = image_count == 1

        if f.multi_step and temporal_pair:
            # flagship investigation shape
            s_ch = add(TaskType.TEMPORAL_CHANGE, "run_temporal_change",
                       {"t1": "img0", "t2": "img1"}, [val],
                       "quantify change between the two observations",
                       "change mask + changed fraction returned")
            s_reg = add(TaskType.EXTRACT_CHANGED_REGIONS, "extract_changed_regions",
                        {"change_result_ref": s_ch}, [s_ch],
                        "turn the change mask into discrete regions", "at least one region or an explicit none")
            deps_cross = []
            if f.want_ground or f.want_investigate:
                s_gr = add(TaskType.GROUND_OBJECT, "run_grounding",
                           {"image": "img1", "phrase": _ground_phrase(mission)}, [s_reg],
                           "locate the affected structures on the post-event image",
                           "a box or an explicit no-region result")
                deps_cross.append(s_gr)
            # only add the optical+SAR leg if a distinct SAR image is actually present.
            # 3 images -> [T1, T2, SAR]; 4 images -> [T1, T2, S2-optical, S1-SAR].
            if image_count >= 3 and (f.has_sar or f.want_compare):
                opt_ref = f"img{image_count - 2}" if image_count >= 4 else "img1"
                s_sar = add(TaskType.OPTICAL_SAR_ANALYSIS, "run_optical_sar",
                            {"optical": opt_ref, "sar": f"img{image_count - 1}"}, [s_reg],
                            "characterise the area with joint optical+SAR features",
                            "a joint representation is produced")
                deps_cross.append(s_sar)
            if len(deps_cross) >= 2:
                s_cc = add(TaskType.CROSS_CHECK_EVIDENCE, "cross_check_evidence",
                           {"refs": [s_reg, *deps_cross]}, deps_cross,
                           "check the grounded structures fall inside changed regions", "cross-check computed")
                pre_verify = s_cc
            else:
                pre_verify = deps_cross[-1] if deps_cross else s_reg
            s_v = add(TaskType.VERIFY, "verify_result", {}, [pre_verify],
                      "aggregate structural + geospatial + evidence verification", "verification computed")
            s_sum = add(TaskType.SUMMARIZE, "inspect_evidence", {}, [s_v],
                        "collate the evidence gathered", "digest built")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s_sum],
                "produce the evidence-first investigation report", "report assembled")

        elif opt_sar:
            s = add(TaskType.OPTICAL_SAR_ANALYSIS, "run_optical_sar",
                    {"optical": "img0", "sar": "img1"}, [val],
                    "paired optical + SAR -> joint representation", "a joint representation is produced")
            s_v = add(TaskType.VERIFY, "verify_result", {}, [s], "check structural coherence",
                      "verification computed")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s_v], "produce the report", "report assembled")

        elif temporal and f.want_semantic:
            s = add(TaskType.SEMANTIC_CHANGE, "run_semantic_temporal_baseline",
                    {"t1": "img0", "t2": "img1"}, [val],
                    "describe what changed via the EXPERIMENTAL composed baseline",
                    "a change description + regions returned")
            s_v = add(TaskType.VERIFY, "verify_result", {}, [s], "check coherence", "verification computed")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s_v], "produce the report", "report assembled")

        elif temporal:
            s = add(TaskType.TEMPORAL_CHANGE, "run_temporal_change",
                    {"t1": "img0", "t2": "img1"}, [val], "bi-temporal change detection",
                    "change mask + changed fraction returned")
            s_v = add(TaskType.VERIFY, "verify_result", {}, [s], "check coherence", "verification computed")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s_v], "produce the report", "report assembled")

        elif single and f.want_ground:
            s = add(TaskType.GROUND_OBJECT, "run_grounding",
                    {"image": "img0", "phrase": _ground_phrase(mission)}, [val],
                    "text -> box + mask on one image", "a box or an explicit no-region result")
            s_v = add(TaskType.VERIFY, "verify_result", {}, [s], "check the box is in bounds",
                      "verification computed")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s_v], "produce the report", "report assembled")

        elif single and f.want_scene:
            s = add(TaskType.SCENE_UNDERSTANDING, "run_scene_retrieval", {"image": "img0"}, [val],
                    "zero-shot scene tagging", "a ranking is returned")
            s_v = add(TaskType.VERIFY, "verify_result", {}, [s], "check coherence", "verification computed")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s_v], "produce the report", "report assembled")

        elif single and (f.want_vqa or True):  # default for a single image
            s = add(TaskType.VQA, "run_vqa", {"image": "img0", "question": mission}, [val],
                    "open-ended question about one image", "a text answer is returned")
            s_v = add(TaskType.VERIFY, "verify_result", {}, [s], "check the answer is coherent",
                      "verification computed")
            add(TaskType.FINALIZE, "finalize_answer", {}, [s_v], "produce the report", "report assembled")

        else:
            # unsupported / not enough to plan a specialist step
            if not steps:
                add(TaskType.VALIDATE_INPUT, "validate_geospatial_input", {"images": imgs or ["img0"]},
                    [], "validate whatever was supplied", "validation attempted")
            add(TaskType.FINALIZE, "finalize_answer", {}, [steps[-1].step_id],
                "the mission does not map to a supported specialist operation; finalize honestly",
                "an explicit unsupported result is returned")

        return AgentPlan(
            goal=mission.strip()[:200] or "geospatial mission",
            inputs=imgs,
            steps=steps,
            constraints=[f"<= {8} specialist steps", "no fabricated coordinates",
                         "no fabricated evidence", "no confidence values"],
            expected_output="an evidence-backed investigation summary",
            planner=self.name,
        )


_GROUND_NOUNS = ("building", "buildings", "structure", "structures", "ship", "ships", "vessel",
                 "runway", "road", "roads", "bridge", "vehicle", "vehicles", "aircraft", "plane",
                 "planes", "house", "houses", "settlement", "port", "harbour", "harbor", "tank",
                 "field", "tower")


def _ground_phrase(mission: str) -> str:
    q = (mission or "").lower()
    for noun in _GROUND_NOUNS:
        if noun in q:
            return noun
    return "buildings"


# --------------------------------------------------------------------------- #
# LLM planner (optional, pluggable)
# --------------------------------------------------------------------------- #


class LlmPlanner:
    name = "llm"

    def __init__(self, *, timeout_s: float = 60.0, provider: str | None = None):
        self.timeout_s = timeout_s
        self.provider = provider or os.environ.get("SATQUERY_PLANNER_PROVIDER", "local_qwen")

    def plan(self, mission: str, image_count: int, modalities: list[str]) -> AgentPlan:
        prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(mission, image_count, modalities)
        if self.provider == "local_qwen":
            raw = self._local_qwen(prompt)
        else:  # pragma: no cover - API provider wiring
            raw = self._http(prompt)
        obj = _first_json_object(raw)
        if obj is None:
            raise ValueError("planner produced no JSON object")
        obj.setdefault("planner", "llm")
        return AgentPlan.model_validate(obj)

    def _local_qwen(self, prompt: str) -> str:
        py = _REPO_ROOT / ".venvs" / "tinyrs" / "Scripts" / "python.exe"
        bridge = _REPO_ROOT / "scripts" / "research" / "planner_infer.py"
        weights = _REPO_ROOT / "models" / "cache" / "qwen2vl2b"
        if not py.exists() or not bridge.exists() or not (weights / "config.json").exists():
            raise FileNotFoundError("local planner model / venv / bridge not available")
        out = subprocess.run(  # noqa: S603 - explicit arg list, timeout
            [str(py), str(bridge), "--weights", str(weights), "--max-new-tokens", "700"],
            input=prompt, capture_output=True, text=True, timeout=self.timeout_s,
        )
        if out.returncode != 0:
            raise RuntimeError(f"planner bridge exited {out.returncode}: {out.stderr[-500:]}")
        return out.stdout

    def _http(self, prompt: str) -> str:  # pragma: no cover
        import urllib.request

        base = os.environ["SATQUERY_PLANNER_API_BASE"].rstrip("/")
        key = os.environ.get("SATQUERY_PLANNER_API_KEY", "")
        model = os.environ.get("SATQUERY_PLANNER_API_MODEL", "gpt-4o-mini")
        body = json.dumps({"model": model, "temperature": 0,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(f"{base}/chat/completions", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as r:  # noqa: S310
            return json.loads(r.read())["choices"][0]["message"]["content"]


def _first_json_object(text: str) -> dict | None:
    if not text:
        return None
    # strip code fences
    text = re.sub(r"```(?:json)?", "", text)
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = -1
    return None


# --------------------------------------------------------------------------- #
# factory + fallback
# --------------------------------------------------------------------------- #


def make_planner() -> Planner:
    choice = os.environ.get("SATQUERY_PLANNER", "rule").lower()
    if choice in ("llm", "qwen", "local_qwen") or os.environ.get("SATQUERY_PLANNER_API_BASE"):
        return LlmPlanner()
    return RuleBasedPlanner()


def plan_with_fallback(
    mission: str, image_count: int, modalities: list[str], *, planner: Planner | None = None
) -> tuple[AgentPlan, str, list[str]]:
    """Return (plan, planner_used, notes). LLM failure -> rule-based plan, never raises."""
    p = planner or make_planner()
    notes: list[str] = []
    if isinstance(p, RuleBasedPlanner):
        return p.plan(mission, image_count, modalities), p.name, notes
    try:
        t0 = time.time()
        plan = p.plan(mission, image_count, modalities)
        notes.append(f"llm planner ok in {time.time() - t0:.1f}s")
        return plan, "llm", notes
    except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired, ValueError,
            ValidationError, json.JSONDecodeError) as exc:
        notes.append(f"llm planner failed ({type(exc).__name__}: {str(exc)[:160]}) -> rule-based fallback")
        rb = RuleBasedPlanner()
        return rb.plan(mission, image_count, modalities), "rule_based_fallback", notes
    except Exception as exc:  # noqa: BLE001 - any planner crash must still fall back
        notes.append(f"llm planner crashed ({type(exc).__name__}) -> rule-based fallback")
        rb = RuleBasedPlanner()
        return rb.plan(mission, image_count, modalities), "rule_based_fallback", notes


if __name__ == "__main__":  # tiny manual check
    for m in ["what is in this image?", "where is the largest ship?",
              "what changed between these images?", "compare these optical and SAR images",
              "investigate this area: what changed, locate the buildings, use SAR to characterise them"]:
        pl, used, _ = plan_with_fallback(m, 2, ["optical", "sar"])
        print(f"\n{m!r} [{used}]")
        for s in pl.steps:
            print(f"  {s.step_id} {s.task.value:24} {s.tool:32} deps={s.depends_on}")
    sys.exit(0)
