"""Local text-only planner bridge (G14, serve mode added G16) - runs INSIDE .venvs/tinyrs.

Two modes:

* one-shot (default): read a full prompt on stdin, generate once, print the raw
  completion to stdout, exit. Used by `LlmPlanner` in the product runtime.
* serve (`--serve`): load the model ONCE, then loop reading one JSON request per
  line on stdin -- `{"id": <str>, "prompt": <str>, "max_new_tokens": <int>}` --
  and write one JSON response per line to stdout -- `{"id": <str>, "raw": <str>,
  "gen_s": <float>}` or `{"id": <str>, "error": <str>}`. A line `{"cmd":"stop"}`
  or EOF ends the loop. Used by the G16 evaluation so 50+ plans do not each pay
  the ~90 s checkpoint-load cost.

The caller (`satquery_agents.agent.planner.LlmPlanner`) extracts the first JSON
object as an `AgentPlan` and falls back to the rule planner on any failure.

NOT product code. No network (weights are local). Deterministic decoding
(`do_sample=False`, fixed seed).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _resolve_weights(root: str) -> str:
    """Accept either the dir holding config.json or a parent holding one model subdir."""
    p = Path(root)
    if (p / "config.json").exists():
        return str(p)
    subs = [d for d in p.iterdir() if d.is_dir() and (d / "config.json").exists()] if p.is_dir() else []
    if len(subs) == 1:
        return str(subs[0])
    raise FileNotFoundError(f"no config.json under {root} (subdirs checked: {[s.name for s in subs]})")


def _load(weights: str):
    import os

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

    # CPU-only host: use the physical cores explicitly (torch sometimes defaults to 1)
    try:
        torch.set_num_threads(max(1, (os.cpu_count() or 4)))
    except Exception:  # noqa: BLE001
        pass
    torch.manual_seed(0)
    try:
        tok = AutoTokenizer.from_pretrained(weights, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            weights, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, trust_remote_code=True
        )
    except Exception:  # noqa: BLE001 - fall back to the VL class, text-only
        from transformers import Qwen2VLForConditionalGeneration

        proc = AutoProcessor.from_pretrained(weights)
        tok = proc.tokenizer
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            weights, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True
        )
    model.eval()
    return tok, model


def _make_stopper(tok, prompt_len: int):
    """Stop as soon as the generated text is a balanced JSON object (>=1 pair of
    braces, depth back to 0). A 2B model writes very long `reason` strings and
    would otherwise run to max_new_tokens and truncate mid-JSON."""
    from transformers import StoppingCriteria

    class _BraceBalance(StoppingCriteria):
        def __call__(self, input_ids, scores, **kw):  # noqa: D401
            txt = tok.decode(input_ids[0][prompt_len:], skip_special_tokens=True)
            depth = 0
            seen = False
            for ch in txt:
                if ch == "{":
                    depth += 1
                    seen = True
                elif ch == "}":
                    depth -= 1
            # done: the top-level object closed
            if seen and depth <= 0:
                return True
            # runaway: a 2B model sometimes recurses "steps":[{"steps":[{... —
            # stop once nesting is clearly pathological or a 2nd "steps" appears.
            if depth >= 6 or txt.count('"steps"') >= 2:
                return True
            return False

    return _BraceBalance()


def _generate(tok, model, prompt: str, max_new_tokens: int) -> str:
    import torch
    from transformers import StoppingCriteriaList

    msgs = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inp = tok(text, return_tensors="pt")
    plen = inp["input_ids"].shape[1]
    with torch.no_grad():
        out = model.generate(
            **inp, max_new_tokens=max_new_tokens, do_sample=False, temperature=None, top_p=None,
            pad_token_id=tok.eos_token_id,
            stopping_criteria=StoppingCriteriaList([_make_stopper(tok, plen)]),
        )
    return tok.decode(out[0][plen:], skip_special_tokens=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=700)
    ap.add_argument("--serve", action="store_true", help="persistent JSON-lines server on stdin/stdout")
    a = ap.parse_args()

    weights = _resolve_weights(a.weights)

    if not a.serve:
        prompt = sys.stdin.read()
        if not prompt.strip():
            print("", end="")
            return 1
        tok, model = _load(weights)
        print(_generate(tok, model, prompt, a.max_new_tokens))
        return 0

    # --- serve mode ---
    t0 = time.time()
    tok, model = _load(weights)
    sys.stderr.write(f"[planner_infer] model loaded in {time.time() - t0:.1f}s; ready\n")
    sys.stderr.flush()
    print(json.dumps({"ready": True, "load_s": round(time.time() - t0, 1)}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"id": None, "error": "bad request json"}), flush=True)
            continue
        if req.get("cmd") == "stop":
            break
        rid = req.get("id")
        try:
            g0 = time.time()
            raw = _generate(tok, model, req["prompt"], int(req.get("max_new_tokens", a.max_new_tokens)))
            print(json.dumps({"id": rid, "raw": raw, "gen_s": round(time.time() - g0, 2)}), flush=True)
        except Exception as exc:  # noqa: BLE001 - report, keep serving
            print(json.dumps({"id": rid, "error": f"{type(exc).__name__}: {exc}"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
