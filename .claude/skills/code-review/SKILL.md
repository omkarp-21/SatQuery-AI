---
name: code-review
description: Pre-merge code review for SatQuery — checks the change against the rules (architecture boundaries, geospatial metadata, adapter contract, tests, security, provenance), looks for correctness bugs and needless complexity, and confirms the Definition of Done. Invoke before opening or approving a PR.
---

# Code Review

## Order of checks

1. **Does it respect the boundaries?** (`.claude/rules/architecture.md`)
   - Pipeline stage order untouched; typed in/out; forward-only data flow.
   - Models reached only via adapter + registry.
   - No import from `external/research/` in product code.
   - Orchestration vs pipeline vs model code not mixed.

2. **Geospatial correctness** (`.claude/rules/geospatial.md`)
   - CRS / transform / bounds / nodata preserved and carried.
   - No silent resize/reproject; resampling method named and logged.
   - Bi-temporal inputs asserted co-registered before differencing.
   - Area/length computed in a projected CRS.

3. **Model adapters** (`.claude/rules/ai-models.md`)
   - All required registry fields present; capability claims match upstream.
   - SAR not treated as RGB; unsupported task raises, doesn't approximate.
   - Output has provenance block + qualified confidence.
   - Smoke test loads checkpoint and runs one real inference.

4. **Provenance** — no result path returns without an audit record. No secrets in it.

5. **Tests** (`.claude/rules/testing.md`) — transform + contract + failure tests
   for new stages; adapter smoke test; deterministic; ships in the same change.

6. **Security** (`.claude/skills/security`) — input bounds, path safety, subprocess
   arg lists, sanitized errors, no secret leakage, deps justified.

7. **Correctness & clarity**
   - Obvious bugs, off-by-one, unit mix-ups (dB vs linear, degrees vs metres).
   - Error handling: specific exceptions, no `except: pass`, every failure logged.
   - Needless complexity: could this reuse an existing stage/util? Delete dead code.
   - Names match the surrounding code; docstrings state contracts.

8. **Definition of Done** — code works, tests exist, logging exists, errors
   handled, docs updated (matching `docs/NN_*.md`), demo path still works.

## Output

Findings ranked by severity. Blocking issues vs nits, each with file:line and a
concrete fix. Approve only when blocking issues are resolved and DoD is met.
