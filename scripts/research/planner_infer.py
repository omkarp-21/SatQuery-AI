"""Local text-only planner bridge (G14) — runs INSIDE .venvs/tinyrs.

Reads a full prompt on stdin, generates with a small instruction model
(Qwen2-VL-2B in text-only mode — no image), and prints the raw completion to
stdout. The caller (`satquery_agents.agent.planner.LlmPlanner`) extracts the
first JSON object as an `AgentPlan` and falls back to the rule planner on any
failure.

NOT product code. No network (weights are local). Deterministic decoding.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=700)
    a = ap.parse_args()

    prompt = sys.stdin.read()
    if not prompt.strip():
        print("", end="")
        return 1

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, AutoTokenizer

    torch.manual_seed(0)
    try:
        # Qwen2-VL exposes a text path via its tokenizer + LM head
        tok = AutoTokenizer.from_pretrained(a.weights, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            a.weights, torch_dtype=torch.float32, low_cpu_mem_usage=True, trust_remote_code=True
        )
    except Exception:  # noqa: BLE001 - fall back to the VL class, text-only
        from transformers import Qwen2VLForConditionalGeneration

        proc = AutoProcessor.from_pretrained(a.weights)
        tok = proc.tokenizer
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            a.weights, torch_dtype=torch.float32, low_cpu_mem_usage=True
        )

    model.eval()
    msgs = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inp = tok(text, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**inp, max_new_tokens=a.max_new_tokens, do_sample=False,
                             temperature=None, top_p=None)
    gen = tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)
    print(gen)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
