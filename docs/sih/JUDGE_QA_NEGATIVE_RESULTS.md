# Judge Q&A — Negative Results Defense

> How to answer questions about the results we withdrew or that came out
> inconclusive. These are **credibility strengths**, not weaknesses to hide.
> Facts: `docs/G19_SIH_SOURCE_OF_TRUTH.md`, `docs/G18_RELEASE_REPORT.md`,
> `docs/sih/CLAIM_MATRIX.md` §6–§7.

---

## Q1. "You claimed SAR helped, but your later experiment didn't show that. What happened?"

**Answer:**

> "We had a hypothesis: adding SAR to a frozen optical encoder improves
> downstream land-cover classification. On the first split (DFC2020, 200 eval
> patches) we measured a +0.067 macro-F1 gain for the joint optical+SAR
> representation — but the confidence interval already crossed zero, so we
> labelled it 'positive, not significant'.
>
> In G18 we re-ran it properly on a larger independent split — the full 986-patch
> validation set, 386 held out, a fresh train/eval partition, same method. The
> gain didn't just shrink — the point estimate **flipped sign** to −0.026, still
> not significant. So the earlier delta was within noise.
>
> We **withdrew the claim**. We keep CROMA as the optical+SAR component because
> it was the stronger representation in the bake-off — it beat DOFA on the
> primary metric on *both* splits — but we do **not** claim that SAR universally
> improves this downstream task.
>
> That result strengthened our validation discipline. It's why our claim matrix
> now separates 'measured' from 'measured and survived a larger split'."

**Do NOT say:** "SAR still helps in some cases" (not measured), "it was a data
issue" (it wasn't — the method was identical), "we'll prove it with more data"
(don't promise).

---

## Q2. "So why is CROMA still in the system?"

**Answer:**

> "Two reasons. One: in the head-to-head, CROMA produced a better downstream
> representation than DOFA on the primary metric on both splits — it's the
> stronger *encoder*, independent of the SAR question. Two: the joint optical+SAR
> representation is genuinely computed and shown in the investigation — we just
> don't let the system assert a semantic conclusion from that 768-dimensional
> vector. The representation is real; a measured *task* benefit from SAR is not,
> and we say so."

---

## Q3. "Your LoRA result is +0.126 on the larger split — isn't that significant?"

**Answer:**

> "It's directional, not significant. That run was 3 training epochs on CPU with
> no bootstrap or paired test, and the frozen baselines it's compared against
> were under-trained 3-epoch linear heads — a fully-converged probe on the same
> frozen features scores about 0.85, so the absolute numbers between our two
> experiments aren't directly comparable. What *does* replicate is the
> *direction*: LoRA adaptation beat the frozen encoder on both splits
> (+0.061 on the first, +0.09 vs optical on the larger). We wired it as an
> optional, provenance-tracked path — `--lora-weights`, verified end-to-end
> through the real adapter, 42 of 42 layers matched — but the **production
> default stays the frozen encoder**. We won't flip a production default on a
> directional CPU run."

---

## Q4. "You said the LLM planner failed. Isn't that a failure of the project?"

**Answer:**

> "It's a finding, and it shaped the architecture. We built a real local
> LLM planner — Qwen2-VL-2B, text-only — and evaluated it on 100 frozen
> missions. It echoed its own prompt example; semantic plan validity was 0.25
> versus 0.886 for the deterministic planner, and in execution its factual
> consistency was 0.33. So we **rejected it for production**. We kept a *hybrid*
> where the LLM only classifies intent and a deterministic synthesiser builds
> the plan — that's optional and still doesn't beat the deterministic planner on
> this hardware. The point: we didn't ship a component we couldn't stand behind,
> and the deterministic planner we did ship is measured."

---

## Q5. "Why is everything 'sanity-scale'? Where are the benchmarks?"

**Answer:**

> "We deliberately don't call any of our numbers a benchmark. Our evaluations
> are n = tens to low hundreds — enough to catch gross problems and to compare
> arms, not enough to claim a leaderboard result. Every number in our materials
> carries its N and a significance caveat. Given the timeframe and a CPU-only
> host, we chose to be honest about scale rather than run a big evaluation we
> couldn't do carefully. The three specialist numbers we do report —
> VQA 0.87 (n=40), grounding 0.84 (n=25), change-IoU ~0.83 (n=7, a
> reproduction) — are all integrated-system measurements, not paper numbers."

---

## Q6. "Can it run in 4 GB of GPU memory?"

**Answer:**

> "We don't know, and we won't guess. There's no CUDA build on our development
> host, so we record 'GPU fit = UNVERIFIED' and make no VRAM claim. What we *can*
> say is that every specialist and the full agent run CPU-only on a laptop — one
> model resident at a time, in its own subprocess — and that's the path we
> demoed."

---

## The framing to keep

Every one of these is the same move: **we tested a hypothesis, it didn't hold,
we said so and adjusted.** That is what a research-backed prototype is supposed
to do. A team that reports only positive results is the one to be suspicious of.
