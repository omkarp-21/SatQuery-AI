---
name: security
description: Security review practice for SatQuery — input validation and bounds, untrusted imagery handling, path-traversal and subprocess safety, secret hygiene, dependency review, and sanitized error boundaries. Invoke when adding an endpoint, handling user or provider input, calling a subprocess, adding a dependency, or before a release.
---

# Security

Enforces `.claude/rules/security.md`. This is the review checklist.

## Input validation (every external boundary)

- Query text: max length, reject control chars, treat as data never as a path/command.
- Geometry: cap vertex count, cap AOI area, valid ring topology, CRS present.
- Dates: valid range, sane bounds, start ≤ end.
- Requested imagery: cap dimensions, band count, pixel budget before allocation.
- Reject with a typed 4xx and a sanitized message. Fail before allocating memory.

## Untrusted imagery

- Provider and local (ISRO) files are untrusted. Verify driver, dimensions, dtype,
  band count, CRS before processing.
- Guard decompression bombs: enforce a max decoded size; use windowed reads.
- Never trust embedded paths/URLs in metadata.

## Filesystem

- User-influenced paths resolve against an allowlisted base dir; reject `..`,
  absolute paths, symlinks out of base.
- Checkpoints, `.env`, and `data/raw/` are never served or logged.

## Subprocess (research-repo inference)

- Explicit `args` list, `shell=False`, absolute executable path, `timeout=`,
  bounded output capture. No f-string command building.
- Run with least privilege; no network if not needed.

## Secrets

- Only from `.env`. Never in code, tests, fixtures, docs, logs, error messages,
  provenance, or commits. Scrub provenance/audit before write.
- `.gitignore` protecting secrets and checkpoints is load-bearing — don't weaken it.

## Errors at the boundary

- API errors are typed and sanitized: no stack traces, internal paths, or provider
  keys in responses. Log detail server-side with the query id.

## Dependencies

- Pin versions. Review transitive additions. Run `pip-audit` / `npm audit` before
  release. New dependency needs a written justification (`.claude/rules/*`).

## Before release

Run through `docs/12_SECURITY.md` threat model; confirm deployment hardening
(CORS origin locked, TLS, rate limits, resource quotas).
