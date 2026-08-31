# Security Rules

- Configuration and secrets come only from environment variables / `.env`
  (see `.env.example`). No secret literals in code, tests, fixtures, or docs.
- Never read, log, echo, or commit `.env`, credentials, or checkpoint files.
  `.gitignore` protects them — do not weaken it.
- Validate and bound every external input: query text length, geometry vertex
  count, requested area, image dimensions, band count, date ranges. Reject early
  with a typed error.
- Treat imagery from providers as untrusted: verify format, dimensions, and CRS
  before processing. Guard against decompression bombs and pathological rasters.
- No arbitrary path access. File paths derived from user input are resolved against
  an allowlisted base directory and checked for traversal.
- Any subprocess call to research-repo code uses an explicit argument list (no
  shell string interpolation) and a timeout.
- API responses never leak internal paths, stack traces, or provider keys. Errors
  are typed and sanitized at the boundary.
- Dependencies: pin versions, review transitive additions, run an advisory check
  (`pip-audit` / `npm audit`) before release. New deps need justification.
- Provenance and audit records must not contain secrets — scrub before writing.
- Follow `docs/12_SECURITY.md` for the threat model and deployment hardening.
