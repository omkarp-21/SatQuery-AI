# Project rules

Drop focused rule files here (one concern per file) that Claude should follow when
working in SATQUERY. Keep them short and imperative. Reference them from
[`../../CLAUDE.md`](../../CLAUDE.md) if you want them always loaded.

Suggested rules to add:

- `pipeline-contracts.md` — every stage takes/returns a typed model; no cross-stage reach-around.
- `provenance.md` — no result path without evidence + execution trace.
- `models.md` — models are only reached via adapters + registry.
- `secrets.md` — config only through `.env`; never read or print secrets.
