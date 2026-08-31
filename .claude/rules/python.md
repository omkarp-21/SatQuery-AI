# Python Rules

- Target Python 3.11+. Use modern syntax (`X | None`, `list[str]`, `match`).
- Full type hints on every function signature and dataclass/model field.
  `mypy --strict` must pass.
- Lint and format with `ruff` and `black` (line length 100). Run `make fmt` before commit.
- Data models are Pydantic v2. No bare dicts crossing a module boundary.
- Google-style docstrings on every public module, class, and function. The module
  docstring of a pipeline stage states its input and output contract.
- No `print` for diagnostics — use `structlog`. Log at stage boundaries with the
  query id and stage name.
- Raise specific exceptions (`SatQueryError` subclasses), never bare `Exception`.
  Never `except: pass`. Every caught exception is either handled or re-raised with context.
- No blocking I/O in async code paths. Use `httpx.AsyncClient`, async DB drivers.
- No global mutable state. Pass dependencies in (FastAPI `Depends`, explicit args).
- Heavy ML imports (`torch`, `transformers`) live in `models/` and its optional
  `ml` extra — never import them from `backend/app/` or a non-specialist stage.
- Tests use `pytest` in `backend/tests/`, mirroring the package layout. New code
  ships with tests in the same change.
- Randomness is seeded and the seed is recorded (evaluation, sampling, augmentation).
