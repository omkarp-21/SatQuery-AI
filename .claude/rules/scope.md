# Scope Rules

Every proposed feature must justify itself. Before starting one, answer all seven
(from `chatgpt.context.md` §27):

1. Which SIH requirement (PS 26167) does it satisfy?
2. What user value does it add?
3. What **measurable** improvement does it create, and how is it measured?
4. Does it improve the demo?
5. What is the engineering cost (new deps, new env, adapter effort)?
6. Can it be validated — is there an evaluation path / `evaluation/cases/` entry?
7. What will we delay to build it?

If the feature cannot justify itself on these, **cut it.**

## Do not build

- Buzzword tech with no functional need (blockchain, needless microservices).
- Extra agents or abstraction layers that no measured need requires.
- A large model where a smaller one meets the quality bar (`docs/18` model-selection).
- Any feature with no evaluation path.
- UI animation / polish that hides weak underlying functionality.

## Priority order when choosing what is next (`docs/17`)

1. Mandatory SIH requirement
2. Measurable impact on accuracy / reliability
3. Critical prototype functionality (unblocks the end-to-end path)
4. High-value, *validated* innovation
5. Performance / latency
6. UI polish
7. Nice-to-have

Visual polish never outranks core model correctness. Research that cannot improve
SatQuery is out of scope.
