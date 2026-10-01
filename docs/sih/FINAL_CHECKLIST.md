# SatQuery — Final SIH Checklist

> Tick this the day before and the hour before. Companion to
> `docs/sih/DEMO_RUNBOOK.md`. Facts: `docs/G19_SIH_SOURCE_OF_TRUTH.md`.

## Environment

- [ ] Presentation machine: Python 3.11+, repo cloned, `.venvs/*` present
- [ ] `.venvs/satquery/Scripts/python.exe --version` → 3.11.x
- [ ] `pytest -m "not slow and not gpu and not integration"` → **383 passed, 0 failed**
- [ ] `torch.cuda.is_available()` → `False` (expected; CPU is the demo path)
- [ ] Power connected; sleep / hibernate / screen-lock disabled
- [ ] OS updates + antivirus full-scan disabled for the demo window
- [ ] Backup machine prepared **identically** and tested end-to-end

## Models

- [ ] `models/cache/{changeformer,remotesam,croma,remoteclip,tinyrs,dofa}` present
- [ ] Checkpoint sizes match `docs/G18_RELEASE_MANIFEST.md`
- [ ] `models/checkpoints/exp008_croma_lora.pt` present (only if showing the LoRA path — optional)
- [ ] Warm-up done: `python scripts/demo/run_final_demo.py` ran clean within the last ~2 h

## Data / fixtures

- [ ] `data/demo/investigation/` → 5 tiles (`t1_optical`, `t2_optical`, `t2_nochange`, `s2_dfc_optical`, `s1_dfc_sar`)
- [ ] `data/demo/grounding/scene.jpg` present
- [ ] `docs/sih/evidence/demos/final/*.json` + `*.report.html` present (recovery artefact)
- [ ] Mission text on the clipboard / in a sticky note

## Backend / ports

- [ ] `uvicorn app.main:app --host 127.0.0.1 --port 8000` running
- [ ] `GET /health` → `{"status":"ok"}`
- [ ] Port 8000 not taken by anything else
- [ ] Backend left running; terminal visible as a fallback surface

## Browser

- [ ] `http://127.0.0.1:8000/` loads; ASK / INVESTIGATE toggle visible
- [ ] Zoom 125–150 %; full-screen; other tabs + notifications closed
- [ ] `flagship_caseA_change.report.html` bookmarked
- [ ] "View full report ↗" button works (run CASE A once, click it)

## Internet / offline

- [ ] Demo verified with **Wi-Fi off** (must work fully offline)
- [ ] No run-time call to any external service

## Presentation assets

- [ ] Deck reviewed against `docs/sih/CLAIM_MATRIX.md` — **allowed wording only**
- [ ] No slide says: state-of-the-art / fully autonomous / real-time / hallucination-free / benchmark / any VRAM number / any confidence %
- [ ] "SAR benefit withdrawn" and "LLM planner rejected" framed as
      `docs/sih/RESEARCH_HONESTY_SLIDE.md`
- [ ] Architecture slide matches `docs/sih/ARCHITECTURE_DIAGRAM.md`
- [ ] Results slide matches `docs/sih/RESULTS_SLIDE_DATA.md` (every number has N)
- [ ] 3-minute script rehearsed (`docs/sih/FINAL_DEMO_SCRIPT.md`) — including CASE B
- [ ] 30-second pitch rehearsed (`docs/sih/PITCH.md`)

## Q&A

- [ ] `docs/sih/JUDGE_QA.md` (top 30) reviewed by the whole team
- [ ] `docs/sih/JUDGE_QA_NEGATIVE_RESULTS.md` reviewed — one person owns the SAR answer
- [ ] Who answers what: architecture / models / geospatial / evaluation split among the team

## Recording / logs

- [ ] Screen recorder ready (record the live demo as a fallback for later rounds)
- [ ] A clean pre-recorded flagship run saved on disk (in case of total failure)
- [ ] Backend logs visible / captured (structlog to console)

## Copies

- [ ] Full repo (incl. `models/cache/**`, `.venvs/**`) on a **USB stick**
- [ ] Same on the backup machine
- [ ] `docs/sih/` printed or on a phone/tablet for Q&A reference

## Docs

- [ ] `README.md` + `QUICKSTART.md` current and runnable
- [ ] `docs/PROJECT_STATUS.md` reflects G19 + `FINAL_TECH_FREEZE = TRUE`
- [ ] `docs/G19_SIH_SOURCE_OF_TRUTH.md` is the reference everyone used

## Final 10-minute pre-demo

- [ ] `/health` ok · backend up · Wi-Fi can be off
- [ ] Warm-up re-run if the machine slept
- [ ] Mission text on clipboard · tiles pre-selected if possible
- [ ] Report HTML bookmarked · backup machine on and ready
- [ ] Breathe. Lead with CASE A, finish with CASE B.
