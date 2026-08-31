# SatQuery Claude Code harness

How Claude is configured to work in this repo. The layers, in order of authority:

```
                 CLAUDE.md            always loaded — mission, principle, non-negotiables, DoD
                    │
                    ▼
              PROJECT CONTEXT         docs/*, README, AGENTS.md
                                      └─ process: docs/17 (engineering strategy),
                                         18 (research→accuracy + the three numbers),
                                         19 (experiment registry), 20 (roadmap),
                                         21 (Claude working principles — read first)
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       RULES                SKILLS
   .claude/rules/       .claude/skills/       (rules always apply; skills load on demand)
          │                   │
          │          ┌────────┼────────┐
          │          ▼        ▼        ▼
          │      research-  geospatial- frontend-
          │      review     engineering design ...
          ▼
       SUBAGENTS
   .claude/agents/
          │
    ┌─────┼──────────────┐
    ▼     ▼              ▼
 architect  ml-engineer  red-team-reviewer ...
                    │
                    ▼
                  CODE → TESTS → EVALUATION → DEMO
```

## `rules/` — hard engineering constraints (always in effect)

`architecture` · `python` · `typescript` · `geospatial` · `ai-models` ·
`testing` · `security` · `git` · `documentation` · `scope`

Non-negotiable. A change that violates a rule does not merge.

## `skills/` — expert behaviors (model-invoked, loaded when relevant)

| Skill | Use for |
|-------|---------|
| `satquery-architecture` | structure, stage order, boundaries — before any restructuring |
| `remote-sensing` | imagery physics, SAR/optical, bands, change detection, what not to assume |
| `geospatial-engineering` | Rasterio/GDAL/Shapely/pyproj, reprojection, alignment, COG |
| `model-integration` | wrapping a research repo into a SpecialistAdapter |
| `agent-orchestration` | deterministic planner/router/executor design |
| `evaluation` | metric discipline — never fabricate a number |
| `evidence-provenance` | evidence objects + the audit record |
| `frontend-design` | deliberate visual direction, away from generic AI UI |
| `map-ui` | the map as part of the evidence system |
| `data-pipeline` | ingestion, STAC, raw/processed/demo layout, reproducible preprocessing |
| `testing` | pytest/vitest patterns, synthetic rasters, determinism |
| `performance` | measure-first, raster I/O, GPU batching, no-GPU path |
| `security` | input bounds, untrusted imagery, subprocess/path/secret safety |
| `research-review` | reading papers/repos critically; the conservative voice |
| `code-review` | pre-merge checklist against the rules + DoD |
| `fullstack-engineering` | cross-cutting backend↔frontend work |
| `product-engineering` | scope/speed decisions — bounded so "fast" ≠ "fake" |
| `demo-engineering` | the SIH demo as an engineered product surface |

## `agents/` — delegated work and review

`architect` · `remote-sensing-researcher` · `ml-engineer` · `geospatial-engineer` ·
`backend-engineer` · `frontend-engineer` · `ai-evaluator` · `security-engineer` ·
`performance-engineer` · `red-team-reviewer` · `hackathon-jury`

Route a change to the matching specialist. Run risky changes through
`red-team-reviewer` and demo-facing features through `hackathon-jury` before merge.

## Three voices, held in tension

**Product** ("ship") vs **Research** ("claim conservatively") vs **Engineering**
("measure everything"). When they conflict, research rigor wins over shipping speed.

## `hooks/` — automated enforcement

Not yet wired. See [`hooks/README.md`](hooks/README.md) for suggested
PostToolUse formatters and a PreToolUse secret/path guard.
