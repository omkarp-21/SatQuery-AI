# Testing Rules

- New code ships with tests in the same change. No "tests later".
- Package code: `pytest` in `packages/<pkg>/tests/`, mirroring the module path.
  API / integration code: `pytest` in `apps/backend/tests/`. Frontend: `vitest`,
  colocated `*.test.tsx`.
- Every pipeline stage has: a unit test for its transform, a contract test that the
  output validates against its schema, and a failure test (bad input → typed error).
- Every model adapter has a smoke test that loads the checkpoint and runs one real
  inference. Mark it `@pytest.mark.gpu` / `@pytest.mark.slow` if it needs hardware.
- Deterministic tests: seed all randomness, freeze time where relevant, no network.
  Tests that hit real imagery providers are marked `@pytest.mark.integration` and
  excluded from the default run.
- Fixtures for imagery use tiny synthetic rasters with known CRS/transform, checked
  into `packages/geospatial/tests/fixtures/` (shared via a fixture plugin). Do not
  download in a unit test.
- A bug fix starts with a failing test that reproduces it.
- `make test` and `make lint` must be green before a PR is opened.
- Evaluation is not a substitute for tests. Eval measures model quality; tests
  guarantee the plumbing. Both are required.
- Coverage is a signal, not a target — but a new stage or adapter under 80% needs
  a note saying why.
