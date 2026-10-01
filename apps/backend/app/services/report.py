"""G18 Part 13 — investigation report export (clean HTML).

Turns an `AgentInvestigationResult` (or its serialised dict) into a single
self-contained HTML page: Mission · Inputs · Understood as · Plan · Key findings ·
Spatial findings · Evidence · Verification · Confidence category · Models used ·
Warnings · Execution time. No external assets, no JS, print-friendly.

Deliberately minimal styling — the report's job is to be accurate and portable,
not pretty.
"""

from __future__ import annotations

import html
import json
from typing import Any

_CSS = """
:root{color-scheme:light}
body{font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f7f9;color:#1a1d21}
.wrap{max-width:860px;margin:0 auto;padding:28px 22px 60px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#5b6470;margin:0 0 22px;font-size:12px}
section{background:#fff;border:1px solid #e3e6ea;border-radius:8px;padding:14px 16px;margin:0 0 12px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#5b6470;margin:0 0 8px}
.kv{display:grid;grid-template-columns:150px 1fr;gap:4px 14px}
.kv div:nth-child(odd){color:#5b6470}
ol,ul{margin:4px 0;padding-left:20px}
li{margin:2px 0}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;white-space:pre-wrap;
  background:#f0f2f4;border-radius:6px;padding:8px;overflow:auto}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;font-weight:600}
.b-ok{background:#e4f5e9;color:#1c7a3d}.b-warn{background:#fdf1dc;color:#8a5a12}
.b-bad{background:#fbe6e6;color:#a3282b}.b-mut{background:#eef0f2;color:#5b6470}
.step{padding:3px 0;border-bottom:1px solid #eef0f2}.step:last-child{border:0}
.mut{color:#5b6470}
@media print{body{background:#fff}section{break-inside:avoid;border-color:#ccc}}
"""


def _esc(x: Any) -> str:
    return html.escape(str(x if x is not None else ""))


def _confidence_badge(cat: str | None) -> str:
    c = {"HIGH": "b-ok", "MEDIUM": "b-warn", "LOW": "b-warn",
         "INSUFFICIENT_EVIDENCE": "b-bad"}.get(cat or "", "b-mut")
    return f'<span class="badge {c}">{_esc(cat or "n/a")}</span>'


def _verif_badge(status: str | None) -> str:
    c = {"SUPPORTED": "b-ok", "CONTRADICTED": "b-bad"}.get(status or "", "b-warn")
    return f'<span class="badge {c}">{_esc(status or "n/a")}</span>'


def _status_badge(status: str | None) -> str:
    c = {"SUCCESS": "b-ok", "PARTIAL": "b-warn", "BLOCKED": "b-warn",
         "FAILED": "b-bad"}.get(status or "", "b-mut")
    return f'<span class="badge {c}">{_esc(status or "n/a")}</span>'


def investigation_report_html(res: dict) -> str:
    intent = res.get("intent") or {}
    conf = res.get("confidence") or {}
    verif = res.get("verification") or {}
    plan = res.get("plan") or {}
    steps_by_id = {s.get("step_id"): s for s in (res.get("steps") or [])}
    mark = {"completed": "✓", "failed": "!", "skipped": "·", "running": "→", "pending": "○"}

    understood = (f'{_esc(intent.get("task_family"))} · '
                  f'{", ".join(intent.get("required_capabilities") or []) or "no extra capabilities"}'
                  + (f' <span class="mut">(intent via {_esc(intent.get("source"))})</span>'
                     if intent.get("source") and intent.get("source") != "rule_based" else "")) \
        if intent else _esc(res.get("planner_used"))

    plan_html = ""
    if plan.get("steps"):
        rows = []
        for p in plan["steps"]:
            s = steps_by_id.get(p.get("step_id"), {})
            st = s.get("status", "pending")
            v = s.get("verdict", "")
            vb = (f' <span class="badge {"b-ok" if v=="COHERENT" else "b-bad" if v=="INCOHERENT" else "b-mut"}">'
                  f'{_esc(v)}</span>') if v and v != "NOT_APPLICABLE" else ""
            summ = f'<br><span class="mut">{_esc(s.get("summary"))}</span>' if s.get("summary") else ""
            rows.append(f'<div class="step">{mark.get(st, "○")} <b>{_esc(p.get("step_id"))}</b> '
                        f'{_esc(p.get("task"))} → {_esc(p.get("tool"))}{vb}{summ}</div>')
        plan_html = "".join(rows)

    replans = res.get("replans") or []
    replan_html = "".join(
        f'<li><b>{_esc(r.get("reason"))}</b> <span class="mut">(from {_esc(r.get("triggering_step"))})</span> '
        f'&mdash; {_esc(r.get("detail"))}</li>' for r in replans) or '<li class="mut">none</li>'

    kf = "".join(f"<li>{_esc(f)}</li>" for f in (res.get("key_findings") or [])) or \
        '<li class="mut">no positive findings</li>'

    sf = res.get("spatial_findings") or []
    sf_html = "".join(
        f'<li>{_esc(s.get("label"))} '
        + (f'&mdash; lon/lat {", ".join(f"{x:.5f}" for x in s["where_lonlat"])}'
           if s.get("where_lonlat") else
           f'&mdash; px {", ".join(str(round(x)) for x in s["where_pixel"])}' if s.get("where_pixel") else "")
        + "</li>" for s in sf) or '<li class="mut">none</li>'

    ev = res.get("evidence") or []
    ev_html = "".join(
        f'<li><b>{_esc(e.get("evidence_type"))}</b> · {_esc(e.get("source_model"))}</li>'
        for e in ev) or '<li class="mut">none</li>'

    warns = res.get("warnings") or []
    warn_html = "".join(f"<li>{_esc(w)}</li>" for w in warns) or '<li class="mut">none</li>'

    why = "".join(f"<li>{_esc(r)}</li>" for r in (conf.get("reasons") or []))
    geo = res.get("geojson") or {}
    total_s = (res.get("timings") or {}).get("total_s")

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SatQuery investigation report</title><style>{_CSS}</style></head><body><div class="wrap">
<h1>SatQuery &mdash; investigation report</h1>
<p class="sub">Deterministic planner &middot; policy-constrained execution &middot; evidence-backed &middot;
confidence is an evidence-derived category, NOT a probability</p>

<section><h2>Mission</h2><div>{_esc(res.get("mission"))}</div></section>

<section><h2>Investigation status</h2><div class="kv">
<div>Status</div><div>{_status_badge(res.get("investigation_status"))}</div>
<div>What happened</div><div>{_esc(res.get("investigation_status_reason") or res.get("conclusion"))}</div>
</div></section>

<section><h2>Understood as</h2><div>{understood}</div></section>

<section><h2>Inputs</h2><ul>{"".join(f"<li>{_esc(i)}</li>" for i in (res.get("inputs") or [])) or '<li class="mut">none</li>'}</ul></section>

<section><h2>Plan &amp; execution</h2>
<div class="mut" style="margin-bottom:6px">planner: {_esc(res.get("planner_used"))} &middot;
{_esc(res.get("tool_calls"))} / {_esc(res.get("max_steps"))} tool calls
{" &middot; stopped early" if res.get("early_stopped") else ""}</div>
{plan_html}</section>

<section><h2>Replans (adapted on observation)</h2><ul>{replan_html}</ul></section>

<section><h2>Key findings</h2><ul>{kf}</ul></section>

<section><h2>Spatial findings</h2><ul>{sf_html}</ul>
{f'<div class="mut">GeoJSON: {len(geo.get("features", []))} feature(s), {_esc(geo.get("crs"))}</div>' if geo else ''}</section>

<section><h2>Evidence</h2><ul>{ev_html}</ul></section>

<section><h2>Verification</h2><div class="kv">
<div>Status</div><div>{_verif_badge(verif.get("status"))}</div>
<div>Meaning</div><div>{_esc(verif.get("note")
    or ("no analytical conclusion was produced to verify" if res.get("investigation_status") == "BLOCKED"
        else "structural / deterministic checks on the evidence that was produced — not a success signal"))}</div>
<div>Resolution</div><div>{_esc((res.get("resolution") or {}).get("qualifier"))}</div></div></section>

<section><h2>Confidence category</h2><div class="kv">
<div>Category</div><div>{_confidence_badge(conf.get("category"))}
{f'<span class="mut">(forced: {_esc(conf.get("hard_rule"))})</span>' if conf.get("hard_rule") else ''}</div></div>
<h2 style="margin-top:10px">Why</h2><ul>{why or '<li class="mut">-</li>'}</ul>
<div class="mut">{_esc(conf.get("note"))}</div></section>

<section><h2>Models used</h2><div>{_esc(", ".join(res.get("models_used") or []) or "-")}</div></section>

<section><h2>Warnings</h2><ul>{warn_html}</ul></section>

<section><h2>Execution time</h2><div>{_esc(total_s)} s (CPU, cold model loads)</div></section>

<section><h2>Provenance (raw)</h2><div class="mono">{_esc(json.dumps(res.get("provenance") or {}, indent=1)[:4000])}</div></section>
</div></body></html>"""


def report_from_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return investigation_report_html(json.load(fh))
