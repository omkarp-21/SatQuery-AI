# TypeScript / Frontend Rules

- TypeScript strict mode. No `any` — use `unknown` and narrow, or define a type.
- Functional React components with hooks. No class components.
- API response types are generated or hand-mirrored from `docs/09_API_CONTRACTS.md`
  and live in one place (`apps/frontend/src/features/*/types.ts`). Components never
  redefine server shapes inline.
- Server state via `@tanstack/react-query`. Local UI state via `zustand` or
  `useState`. Do not put server data in a global store.
- Side effects only in `useEffect`, event handlers, or query/mutation callbacks.
- Every async UI has explicit loading, empty, and error states. No silent failures.
- Map code uses MapLibre through the `maps/` module wrappers — components do not
  touch the raw `maplibre-gl` instance.
- Formatting with `prettier`, linting with `eslint --max-warnings 0`. Run `make fmt`.
- Colocate component tests (`*.test.tsx`) with `vitest`. New components ship with a test.
- No inline hex colors, magic spacing, or ad-hoc font sizes — use the design tokens
  from the `frontend-design` skill's system.
- Accessibility: semantic elements, keyboard focus, `aria-*` where needed. The
  evidence and execution-trace panels must be navigable without a mouse.
