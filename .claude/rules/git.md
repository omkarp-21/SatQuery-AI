# Git / GitHub Rules

- Never commit or push unless the user asks. Never force-push a shared branch.
- Work on a branch, not `main`/`master`. Branch names: `feat/…`, `fix/…`,
  `docs/…`, `chore/…`, `eval/…`.
- One logical change per commit. Conventional Commit subject line
  (`feat(geospatial): co-register bi-temporal rasters`), imperative, ≤72 chars.
- The body explains *why*, lists dependency changes, and links the doc/ADR updated.
- A PR updates the matching `docs/NN_*.md` and adds/updates an `evaluation/cases/`
  entry when behavior changes. `make lint` and `make test` green before review.
- Never commit: `.env`, `models/checkpoints/**`, `data/raw/**`, `data/processed/**`,
  `evaluation/reports/**`, large binaries. If `git add -A` would stage one, stop.
- `external/research/` entries are git submodules or shallow vendored copies with the
  upstream commit hash recorded in `docs/research/MODEL_COMPARISON.md`. Do not commit
  edits to them.
- Rewriting published history is off-limits. Fix forward with a new commit.
- Tag releases `vMAJOR.MINOR.PATCH`; update `CHANGELOG` and `VERSION` in the same commit.
- Co-author trailer on AI-assisted commits:
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
