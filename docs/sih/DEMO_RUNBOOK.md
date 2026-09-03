# SatQuery — Demo Runbook

> Operational procedure for the SIH live demo. The largest risk is **cold-start
> model loading** (a first flagship run is ~90 s; ~90 % of that is reading
> checkpoints off disk). This runbook removes that risk. All commands are real;
> no output is ever faked. Facts: `docs/G19_SIH_SOURCE_OF_TRUTH.md`.

## 0. The four modes

| Mode | When | Action |
|------|------|--------|
| **DEMO MODE** | before the judge arrives | warm every model with one real run; keep the machine on |
| **RECOVERY MODE** | first live run is slow or errors | do **not** fake output — restart the backend, re-warm, retry once; if still slow, switch to the secondary demo, then show the frozen captured report |
| **FALLBACK MODE** | planner unavailable | the deterministic `/analyze` path still answers single-step questions; `POST /investigate` falls back to it visibly (`AGENT FALLBACK` warning + `resolution.qualifier`) |
| **FAILURE MODE** | a specialist fails mid-investigation | the agent surfaces a **degraded / partial** result — failed step listed in `failures[]`, downstream steps skipped, `warnings[]` populated, no fabricated value (this is CASE B's behaviour and is itself a demo point) |

## A. Machine preparation (the evening before)

1. **Presentation machine + backup machine**, both prepared identically. Decide
   which is primary.
2. OS: the dev/reference host is Windows 11, Python **3.11**. Any OS with Python
   3.11+ and the per-model venvs works. **CPU-only is fine and expected.**
3. Disk: ~12 GB free. RAM: 8 GB minimum, 16 GB comfortable (RemoteSAM peaks
   ~6–8 GB RSS on CPU).
4. Power: plugged in. Disable sleep / hibernate / screen-lock. Disable OS
   updates and antivirus full-scans for the demo window.
5. **No internet is required at run time.** Confirm the demo still works with
   Wi-Fi off (it must).
6. Copy the whole repo to a **USB stick** and to the backup machine. Include
   `models/cache/**` and `.venvs/**` (they are gitignored but needed to run).

## B. Environment checks (run once, expect all green)

```bash
cd <repo>

# 1. Python + venvs exist
.venvs/satquery/Scripts/python.exe --version           # -> Python 3.11.x
ls .venvs/                                              # satquery tinyrs remotesam changeformer remoteclip croma dofa

# 2. checkpoints present (sizes in docs/G18_RELEASE_MANIFEST.md)
ls -l models/cache/changeformer models/cache/remotesam models/cache/croma models/cache/remoteclip

# 3. GPU status (expected: False — this is fine, it is the shipped path)
.venvs/satquery/Scripts/python.exe -c "import torch; print('cuda:', torch.cuda.is_available())"

# 4. fast test suite (expect: 383 passed, 0 failed)
.venvs/satquery/Scripts/python.exe -m pytest packages apps/backend/tests -q -m "not slow and not gpu and not integration"

# 5. demo fixtures present
ls data/demo/investigation/    # s1_dfc_sar.tif s2_dfc_optical.tif t1_optical.tif t2_nochange.tif t2_optical.tif
ls data/demo/grounding/        # scene.jpg
ls docs/sih/evidence/demos/final/   # frozen captures + *.report.html (the recovery artefact)
```

If step 4 is not `383 passed`: **do not demo on this machine** — use the backup.

## C. Model warm-up (DEMO MODE — do this ~20 min before)

One real run of the frozen demo set loads every model that the flagship uses
(ChangeFormer, RemoteSAM, CROMA) plus the grounding path. After it, the
checkpoints are in the OS page cache and subsequent live runs are markedly
faster (still tens of seconds for grounding — that is honest and expected).

```bash
.venvs/satquery/Scripts/python.exe scripts/demo/run_final_demo.py
# ~3–4 min total. Re-writes docs/sih/evidence/demos/final/*.json + *.report.html
# Expected tail: "flagship caseA … OK", "flagship caseB … OK (early_stopped)", "secondary … OK"
```

Then **leave the machine on and do not reboot**. Re-run the warm-up if more than
~2 h pass or the machine sleeps.

Start the backend and leave it running:

```bash
cd apps/backend
../../.venvs/satquery/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
#   http://127.0.0.1:8000/       self-contained UI (ASK / INVESTIGATE)
#   http://127.0.0.1:8000/health -> {"status":"ok"}
```

## D. Browser checks

1. Open `http://127.0.0.1:8000/` — the UI loads with an **ASK / INVESTIGATE**
   toggle, a file picker, a query box.
2. `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`.
3. Zoom the browser to ~125–150 % so the plan / trace / evidence panels are
   legible on the projector.
4. Pre-select the **INVESTIGATE** tab. Pre-load the 4 investigation tiles in the
   file picker if the venue lets you (saves 15 s of fumbling).
5. Close other tabs and notifications. Full-screen the browser.

## E. Demo commands (the ones you will actually run)

### Flagship — CASE A (real change), in the UI

- Tab: **INVESTIGATE**
- Files: `data/demo/investigation/t1_optical.tif`, `t2_optical.tif`,
  `s2_dfc_optical.tif`, `s1_dfc_sar.tif`
- Mission (paste verbatim):
  > Investigate this area. Identify significant changes between the two
  > observations, locate the affected structures, compare optical and SAR
  > evidence, and provide a verified summary.
- Click **Analyze**. Expected ≈ **60–95 s** warm.
- Then click **View full report ↗** (opens the HTML report in a new tab).

### Flagship — CASE B (minimal change)

- Same as CASE A but swap `t2_optical.tif` → `t2_nochange.tif`.
- Expected ≈ **15–20 s**, `early_stopped = true`, 2 tool calls, 2 replans,
  confidence **MEDIUM**.

### Secondary — grounding (guaranteed short win)

- Tab: **ASK**
- File: `data/demo/grounding/scene.jpg`
- Query: `Where is the largest ship?`
- Expected ≈ **5–65 s** (fast if warm), box drawn on the image, verification
  SUPPORTED.

### Headless equivalents (if the UI misbehaves)

```bash
.venvs/satquery/Scripts/python.exe scripts/demo/run_final_demo.py --only flagship
.venvs/satquery/Scripts/python.exe scripts/demo/run_final_demo.py --only secondary
# render any captured run as HTML:
.venvs/satquery/Scripts/python.exe scripts/demo/mission_report.py docs/sih/evidence/demos/final/flagship_caseA_change.json
```

## F. Exact expected output (what to point at)

**CASE A** — conclusion text:
> "~25.3% of the scene changed, 6 changed region(s) isolated, 1 structure
> region(s) located, optical+SAR representation computed. Verification:
> SUPPORTED."
- Tool calls **4**; models **ChangeFormer, RemoteSAM, CROMA**; replans **none**;
  confidence **HIGH**; total ≈ **93 s** cold.
- 6 changed regions with lon/lat boxes; a grounded structure box `[17,16,241,239]`;
  cross-check "1/1 grounded region(s) fall inside a changed region".

**CASE B** — key findings:
> "No significant change: changed fraction ~0.00% (below the 1% threshold)."
> "Grounding: no matching region could be localised (returned explicitly, not
> fabricated)."
- Tool calls **2**; `early_stopped = true`; replans **`NEW_EVIDENCE`** +
  **`TOOL_FAILURE`**; confidence **MEDIUM** (reason: "A required modality (SAR)
  was missing"); total ≈ **17 s**.

**Secondary** — `SINGLE_IMAGE_GROUNDING`, RemoteSAM, box `[211, 427, 634, 512]`
in an 800×800 image, verification SUPPORTED, warning: "RemoteSAM upstream licence
is NOT STATED".

(Small live variations in region count / box pixels / seconds are expected — the
*shape* of the result is what matters.)

## G. Recovery procedure

1. **First run slow (> 2 min) or spinner stuck:**
   - Let it finish once if you can — it is loading, not hung.
   - If it errors: `Ctrl-C` the backend, re-run the warm-up
     (`run_final_demo.py`), restart uvicorn, retry **once**.
2. **Still failing:** run the **secondary** grounding demo instead — it is one
   model and the most reliable visual.
3. **UI broken:** run the headless `run_final_demo.py --only flagship` in the
   terminal on screen; narrate the JSON.
4. **Everything failing:** open the **pre-rendered report** —
   `docs/sih/evidence/demos/final/flagship_caseA_change.report.html` — in the
   browser. Say plainly: *"this is a captured run from this machine; let me walk
   you through it."* It is a real captured output, not a mock-up.
5. **Switch to the backup machine** if the primary is unrecoverable in ~60 s.

## H. What to say if something fails

- Slow first run: *"That pause is the model checkpoints loading from disk on
  CPU — about 90 seconds the first time, seconds after. On a GPU or a warm
  system it is not noticeable."*
- A specialist errors mid-investigation: *"Good — you can see it did not invent a
  result. The failed step is listed, the downstream steps were skipped, and the
  confidence dropped. That is the design: fail loudly, never fabricate."*
- Planner/agent unavailable: *"It fell back to the deterministic path — the
  warning says so — so you still get a verified single-step answer."*
- Judge asks for the GPU / 4 GB number: *"We don't have a CUDA machine, so we
  record GPU fit as unverified rather than estimate it. Everything you're seeing
  is CPU-only on a laptop."*

## I. One-line pre-demo checklist

`383 tests green` · `uvicorn up` · `/health ok` · `run_final_demo.py ran once`
· `Wi-Fi can be off` · `backup machine ready` · `report.html bookmarked` ·
`mission text on clipboard`.
