"""G18 Part 13 — CLI: render a captured investigation JSON as a standalone HTML report.

  .venvs/satquery/Scripts/python.exe scripts/demo/mission_report.py <investigation.json> [-o out.html]

Also `POST /investigate/report` (HTML response) does the same from the live API.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "apps" / "backend"))

from app.services.report import report_from_file  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="a captured AgentInvestigationResult JSON")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(a.json).with_suffix(".report.html")
    out.write_text(report_from_file(a.json), encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
