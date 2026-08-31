# Per-Model Environment / Container Strategy

> Companion to `model_inventory.md` and `repository_compatibility.md`.
> Nothing here is built yet — this is the plan. No deps installed, no images built.

## Principles

1. **One isolation unit per research model.** No shared environment. No merged
   requirements.
2. **Nothing installed into the SatQuery product environment** (`apps/`, `packages/`
   — Python 3.11, Pydantic v2).
3. **Research code stays read-only** in `external/research/` (gitignored).
4. Each unit exposes a **thin CLI contract** (stdin/args in, JSON + artifact paths
   out) that a future `packages/model_adapters/` adapter calls by **subprocess**.
   Product code never imports research code.
5. Checkpoints and datasets are **not** fetched now. When they are, they go to
   `models/checkpoints/<model>/` and `models/cache/` (both gitignored), pulled by a
   script with a recorded SHA256.

## Isolation unit per model

| Model | Unit | Base | Key constraints |
|-------|------|------|-----------------|
| GeoChat | container `satquery/research-geochat` | `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`, Python 3.10 | `torch==2.0.1`, `transformers==4.31.0`, `bitsandbytes`/`deepspeed` (Linux), `gradio==3.35.2` → `pydantic<2` |
| ChangeChat | container `satquery/research-changechat`, `FROM satquery/research-geochat` | same | weights + `requirements.txt` not released upstream; pin when they are |
| Change-Agent — perception | container `satquery/research-changeagent` | `nvidia/cuda:11.8.0-cudnn8-devel` (needs a compiler), Python 3.9 | `torch==2.0.1+cu118`, `transformers==4.33.1`, **mmcv 1.3.1 source build**, `mmsegmentation==0.13.0` |
| Change-Agent — agent (lagent) | venv `.venvs/changeagent-lagent` or a light container | Python 3.10 | `transformers>=4.34`, `lmdeploy`/`vllm` optional, needs an LLM endpoint (OpenAI-compatible) |
| ChangeFormer | container `satquery/research-changeformer` | `nvidia/cuda:11.3.1-cudnn8-runtime-ubuntu20.04`, Python 3.8 | **rebuilt**: `torch==1.12.1+cu113`, `torchvision==0.13.1`, `timm==0.6.13` — **not** the repo's cu10.2 conda lockfile |
| RemoteCLIP | venv `.venvs/remoteclip` | host Python 3.11 | `pip install open-clip-torch huggingface_hub torch pillow`; add `clip_benchmark` only for retrieval eval |
| awesome-rs-vlms | none | — | not runnable code |

## Layout (to be created when integration starts — not now)

```
infrastructure/
  research/
    geochat/Dockerfile          research-changeformer/Dockerfile
    changechat/Dockerfile       changeagent/Dockerfile
    README.md                   docker-compose.research.yml   # profile: research, never default
scripts/
  setup/
    clone_research_repos.sh     # re-clone at pinned commits (this step)
    make_research_env.sh <model># build one unit
  research/
    run_geochat.sh  run_changeformer.sh  run_changeagent.sh  run_remoteclip.sh
.venvs/                          # gitignored; RemoteCLIP + lagent
```

`docker-compose.research.yml` sits behind a `research` profile so `make dev` /
the product compose never pulls a multi-GB CUDA image.

## Adapter ↔ environment contract (future)

```
packages/model_adapters/src/satquery_model_adapters/<model>.py
    └── execute():  subprocess -> `scripts/research/run_<model>.sh` (host venv)
                      or `docker run --rm satquery/research-<model> ...`
        stdin/args:  image path(s), task, params, output dir
        stdout:      JSON  { answer, artifacts: {mask,boxes,embedding,...}, score }
        provenance:  model+commit, checkpoint sha256, env id (image digest / venv hash)
```

## Windows dev-host note

The dev machine is Windows 11. `bitsandbytes`, `deepspeed`, `flash-attn`, and the
mmcv source build are Linux-only. Run the containerized units under **Docker
Desktop + WSL2**; run the two venv units (RemoteCLIP, lagent) natively. GPU
containers need the NVIDIA Container Toolkit inside WSL2; without a GPU, GeoChat and
Change-Agent perception run CPU-only (slow) and ChangeFormer runs CPU-only via
`--gpu_ids -1`.

## Not doing yet

- Building any image or venv.
- Downloading checkpoints or datasets.
- Writing the adapters or run scripts.
- Wiring `docker-compose.research.yml`.

Next step after this inventory: pick the **first** model to integrate (RemoteCLIP
is lowest-risk) and build only its unit.
