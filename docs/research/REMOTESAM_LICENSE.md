# RemoteSAM — licence status

> **Conclusion: LICENSE NOT STATED.** As of 2026-09-02 there is no licence for the
> RemoteSAM code, the `RemoteSAMv1.pth` checkpoint, or the RemoteSAM-270K dataset
> from any authoritative source. "Models and data are publicly available" is
> **not** a licence grant. Recorded verbatim as `NOT STATED` in
> `packages/model_adapters/model_registry.yaml` and `external/research/README.md`.

## What was checked (Track B, G11 — nothing inferred)

| Source | Result |
|--------|--------|
| `github.com/1e12Leon/RemoteSAM` — `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `COPYING`, `license` | **all HTTP 404** — no licence file at commit `ebb7bc2` |
| GitHub REST API `GET /repos/1e12Leon/RemoteSAM` → `.license` | **`null`** |
| README (`master`) | no licence section; no "released under" / "for research use" / "non-commercial" statement |
| HF checkpoint `1e12Leon/RemoteSAM` — API `cardData` | **`None`**; no `license:` tag; siblings = `.gitattributes`, `RemoteSAMv1.pth` only (**no model card**) |
| HF dataset `1e12Leon/RemoteSAM270k` | not a substitute for the model licence; not relied on |
| Paper: arXiv **2505.18022v3** (submitted 23 May 2025, revised 2 Jun 2025; ACM MM 2025) | abstract/HTML says *"Models and data are publicly available"* + a GitHub link — **no licence terms** (no CC-BY / MIT / Apache / data-use agreement). The arXiv metadata licence ("arXiv.org perpetual, non-exclusive license") covers **the paper PDF only** and grants no rights to code or weights. |

## Implication for SatQuery

- **SIH / non-commercial prototype (current use):** proceed, with this risk
  documented. RemoteSAM is `evidence_level: reproduced`,
  `status: KEEP … pending … licence`, and the registry `license` field literally
  reads `"NOT STATED …"`. The adapter's `model_meta.license` surfaces the same
  string in every provenance record, so no downstream consumer can mistake it for
  an open licence.
- **Redistribution of the checkpoint, a hosted service, or any commercial use:**
  **blocked** until the authors state a licence. Do not vendor `RemoteSAMv1.pth`
  into a distributable artifact; keep it in `models/cache/` (gitignored).
- **Do not** assume MIT/Apache by analogy to other OpenMMLab-adjacent repos — that
  would be inferring a licence, which this doc explicitly does not do.

## Open action

Open a GitHub issue on `1e12Leon/RemoteSAM` (or email the corresponding author)
asking for an explicit licence for the code and the `RemoteSAMv1.pth` weights.
Update this file and the registry when answered. Until then: **NOT STATED**.
