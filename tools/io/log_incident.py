#!/usr/bin/env python3
"""
log_incident.py — collect a structured digest of the latest workspace run for the
Curate beat of the Anamnesis Pattern (see references/anamnesis_pattern.md).

This script does NOT write to INCIDENTS.md. It only emits a JSON digest the model
uses to draft a candidate entry. Append happens after explicit user confirmation
in the /log-incident slash command flow.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Files we look for in a workspace/{Company}_{Date}/ run directory. Each is
# optional — older or shortened runs may not have all of them.
DIGEST_TARGETS = [
    "report_validation.txt",
    "structure_conformance.json",
    "final_report_data_validation.json",
    "qc_audit_trail.json",
    "red_team_numeric_phase_5_7.json",
    "red_team_narrative_phase_5_7.json",
    "incident_postcheck.json",
    "prediction_waterfall.json",
    "porter_analysis.json",
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _strip_email(text: str) -> str:
    """Strip embedded emails from User-Agent-like strings — PII guard."""
    if not isinstance(text, str):
        return text
    return EMAIL_RE.sub("<email-stripped>", text)


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _strip_email(value)
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    return value


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _read_json(path: Path) -> Any:
    raw = _read_text(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"_parse_error": str(e), "_raw_first_500": raw[:500]}


def _summarize_target(workspace: Path, name: str) -> dict[str, Any]:
    path = workspace / name
    if not path.exists():
        return {"present": False}
    out: dict[str, Any] = {"present": True, "path": str(path)}
    if name.endswith(".json"):
        body = _read_json(path)
        out["content"] = _scrub(body)
    else:
        text = _read_text(path) or ""
        out["content_first_500"] = _strip_email(text[:500])
        out["status_line_first"] = next(
            (line.strip() for line in text.splitlines() if line.strip()),
            "",
        )
    return out


def _list_present(workspace: Path) -> list[str]:
    return sorted(p.name for p in workspace.iterdir() if p.is_file())


def collect(workspace: Path, description: str) -> dict[str, Any]:
    if not workspace.is_dir():
        raise SystemExit(f"workspace not found: {workspace}")

    digest: dict[str, Any] = {
        "schema_version": 1,
        "workspace": str(workspace),
        "user_description": description,
        "files_present": _list_present(workspace),
        "targets": {name: _summarize_target(workspace, name) for name in DIGEST_TARGETS},
    }

    # Hint at red-team verdicts at a glance
    rt_num = digest["targets"].get("red_team_numeric_phase_5_7.json", {})
    rt_nar = digest["targets"].get("red_team_narrative_phase_5_7.json", {})
    digest["red_team_summary"] = {
        "numeric": (rt_num.get("content") or {}).get("summary") if rt_num.get("present") else None,
        "narrative": (rt_nar.get("content") or {}).get("summary") if rt_nar.get("present") else None,
    }

    # Hint at packaging verdict
    sc = digest["targets"].get("structure_conformance.json", {})
    sc_content = sc.get("content") if isinstance(sc, dict) else None
    digest["packaging_summary"] = {
        "profile": (sc_content or {}).get("profile") if isinstance(sc_content, dict) else None,
        "html_template_gate_status": (
            (sc_content or {}).get("html_template_gate", {}).get("status")
            if isinstance(sc_content, dict)
            else None
        ),
    }

    # Hint at incident post-check verdict (if a prior post-check exists)
    pc = digest["targets"].get("incident_postcheck.json", {})
    pc_content = pc.get("content") if isinstance(pc, dict) else None
    digest["incident_postcheck_summary"] = (
        {
            "flagged": (pc_content or {}).get("flagged"),
            "incidents": (pc_content or {}).get("incidents"),
        }
        if isinstance(pc_content, dict)
        else None
    )

    # Locate the next available I-NNN id by reading INCIDENTS.md
    incidents_path = REPO_ROOT / "INCIDENTS.md"
    next_id = "I-001"
    if incidents_path.is_file():
        text = incidents_path.read_text(encoding="utf-8")
        ids = sorted(set(re.findall(r"\bI-(\d{3,})\b", text)), key=int)
        if ids:
            next_id = f"I-{int(ids[-1]) + 1:03d}"
    digest["proposed_next_incident_id"] = next_id

    return digest


def latest_workspace(root: Path) -> Path | None:
    candidates = [p for p in root.iterdir() if p.is_dir()] if root.is_dir() else []
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect a workspace digest for /log-incident drafting. Read-only — does NOT modify INCIDENTS.md."
    )
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Run in collect mode (default and only supported mode).",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Path to a workspace/{Company}_{Date}/ directory. If omitted, uses the most recently modified subdir of workspace/.",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="One-line description of the failure (passed by the slash command).",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=REPO_ROOT / "workspace",
        help="Root containing per-run workspace dirs (default: workspace/).",
    )
    args = parser.parse_args(argv)

    workspace = args.workspace
    if workspace is None:
        workspace = latest_workspace(args.workspace_root)
        if workspace is None:
            print(
                f"ERROR: no workspace dirs found under {args.workspace_root}; pass --workspace explicitly.",
                file=sys.stderr,
            )
            return 1

    digest = collect(workspace.expanduser().resolve(), args.description)
    print(json.dumps(digest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
