# Research

Reference material backing SATQUERY's model and architecture choices.

## Layout

| Path | Contents |
|------|----------|
| `papers/` | PDFs / notes on relevant papers (RS-VLMs, change detection, geospatial reasoning). |
| `benchmarks/` | Benchmark descriptions, leaderboards, and our local result tables. |
| `repos/` | Vendored reference implementations — **read-only**, do not edit. |
| `MODEL_COMPARISON.md` | Side-by-side comparison driving the registry. |

## Vendored repos

- `repos/GeoChat/` — conversational RS VQA + grounding.
- `repos/Change-Agent/` — agentic bitemporal change analysis.
- `repos/ChangeChat/` — instruction-tuned change conversation.
- `repos/ChangeFormer/` — transformer change detection.
- `repos/RemoteCLIP/` — RS-tuned CLIP.

Add each as a git submodule or a shallow copy; keep upstream commit hashes noted
in `MODEL_COMPARISON.md`.
