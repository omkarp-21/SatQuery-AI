---
name: frontend-design
description: Deliberate visual design for the SatQuery dashboard — a committed aesthetic direction, real typographic scale, restrained color, purposeful motion, and production-quality implementation. Pushes away from generic AI-looking UI. Invoke before building or restyling any frontend screen, component, or layout.
---

# Frontend Design

> Adapted from Anthropic's official `frontend-design` guidance for this project.
> If you later vendor the upstream skill, replace this file and keep the SatQuery
> section below.

## Anti-goal: generic AI UI

Avoid the defaults that make an interface look auto-generated: a centered card on
a gradient, three equal feature boxes, purple-to-blue everything, emoji as icons,
`box-shadow` on every element, no real type hierarchy, filler copy. Make choices.

## Commit to a direction

Before coding a screen, decide and write down (in `docs/10_FRONTEND_SPEC.md`):

- **One aesthetic** — e.g. "instrument panel": dense, monospaced numerics,
  hairline rules, calm dark ground, one signal accent. Then hold it everywhere.
- **Type scale** — a real modular scale (e.g. 12 / 14 / 16 / 20 / 28 / 40),
  2 weights, 1–2 families (a humanist sans for UI, a mono for coordinates/metrics).
- **Color** — a neutral ramp (5–7 steps) + one accent + semantic status
  (ok / warn / error / info). Define as CSS custom properties; support light & dark.
- **Spacing** — an 8px (or 4px) grid. No arbitrary margins.
- **Motion** — 150–250ms, `ease-out`, on state changes only. No decorative loops.
  Respect `prefers-reduced-motion`.
- **Density** — this is an analyst tool, not a landing page. Favor information
  density and scannability over whitespace-heavy marketing layouts.

## Implementation quality

- Design tokens in one file; components consume tokens, never literals.
- Real loading / empty / error states, designed, not afterthoughts.
- Keyboard navigable; visible focus; semantic HTML; AA contrast.
- Responsive down to a laptop; the map + panels reflow, they don't break.
- No layout shift on data load (reserve space, skeletons match final size).

## SatQuery-specific

- The interface has three primary regions: **query console**, **map**, and
  **evidence / execution-trace panel**. They are peers — the trace is not a modal
  afterthought.
- Confidence is shown with its qualifier, never as a bare number.
- Every model claim in the UI links to its evidence. Design that link as a
  first-class affordance.
- SAR and optical layers are visually distinguished (different legend, never a
  shared RGB ramp).
