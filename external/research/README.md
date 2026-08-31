# external/research/

Third-party research repositories, cloned **for reference and inventory only**.

## Rules (enforced)

- **Read-only.** Do not modify source in these repos. No edits, no patches, no
  refactors here.
- **Not committed.** Every clone directory is gitignored (`external/research/*/`).
  The parent repo tracks only this README and the inventory docs.
- **Isolated environments.** Do not install these repos' dependencies into the
  main SatQuery environment and do not merge their requirements files. Each has
  conflicting pins (see `docs/research/repository_compatibility.md`). Per-model
  isolation strategy: `docs/research/environment_strategy.md`.
- **No large artifacts yet.** Checkpoints and datasets are not downloaded at this
  stage — only what is needed to inspect repository structure.
- Product code in `apps/` and `packages/` **never imports** from here. Integration
  happens later through adapters in `packages/model_adapters/` (subprocess or a
  minimal vendored inference path).

## Cloned repositories (shallow, `--depth 1`)

| Directory | Upstream | Pinned commit | Cloned | License |
|-----------|----------|---------------|--------|---------|
| `awesome-rs-vlms/` | lzw-lzw/awesome-remote-sensing-vision-language-models | `4d620f38e07a4c77a5d4d362fa68a012bc7ab011` | 2024-04-27 | MIT |
| `GeoChat/` | mbzuai-oryx/GeoChat | `4850920e005a849bd224d0ce35aa9db031fa5155` | 2024-11-28 | Apache-2.0 (declared in metadata; no LICENSE file in repo) |
| `Change-Agent/` | Chen-Yang-Liu/Change-Agent | `68cbaa7f388b36e4fc10872f7a2911482d26ae5b` | 2025-07-27 | MIT |
| `ChangeChat/` | hanlinwu/ChangeChat | `9facf50c68efa32f446f0f3aa700c0b76309029e` | 2025-06-16 | Apache-2.0 (declared in metadata; no LICENSE file in repo) |
| `ChangeFormer/` | wgcban/ChangeFormer | `afd1b7ed640aa265a2c730de958416ae7356a2f9` | 2024-01-31 | MIT |
| `RemoteCLIP/` | ChenDelong1999/RemoteCLIP | `a6a4787507e441f444c20404c90dd18520a8960d` | 2024-06-27 | Apache-2.0 |
| `CROMA/` | antofuller/CROMA | `59505a6bcadbf36ba20767270154bf9f3067c5e7` | 2024-01-10 | MIT | *(added G1.6 for optical–SAR)* |
| `DOFA/` | zhu-xlab/DOFA | `0cfb7e1099f4d4c4022946ff7862c7cd7b8411b9` | 2026-07-22 | MIT | *(added G1.6 — CROMA challenger)* |

`awesome-rs-vlms/` is a curated link list (a paper/model survey), not a runnable
model — kept for literature review.

## Re-cloning

```bash
bash scripts/setup/clone_research_repos.sh
```

## Also here

- `papers/` — PDFs / notes for literature review (tracked).
- `benchmarks/` — benchmark descriptions and local result tables (tracked).
