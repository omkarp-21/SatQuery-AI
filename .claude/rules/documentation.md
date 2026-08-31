# Documentation Rules

- The numbered `docs/NN_*.md` files are the source of truth for design. Code and
  its doc change together in one PR — never let them drift.
- Architectural decisions are appended to `docs/DECISIONS.md` as ADRs (context /
  decision / consequences), newest first. Superseded ADRs are marked, not deleted.
- Every pipeline stage module has a docstring stating its input type, output type,
  side effects, and failure modes.
- Every model adapter documents: what the upstream model does, what it does *not*
  do, the exact input it expects, its output schema, and what its confidence means.
- Public API changes update `docs/09_API_CONTRACTS.md` with request/response
  examples before the endpoint ships.
- `README.md` stays runnable: if a setup or run command changes, the README changes.
- No claim in docs without a basis. Performance numbers cite the benchmark run
  (`docs/13_PERFORMANCE.md`); accuracy numbers cite the eval run
  (`docs/11_EVALUATION_PLAN.md` + `evaluation/reports/`). Mark estimates as estimates.
- Diagrams have a text description alongside them (accessibility + diffability).
- Write for a new teammate joining mid-hackathon: assume domain interest, not
  project context.
