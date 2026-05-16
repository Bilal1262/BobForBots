#!/usr/bin/env python3
"""
BobForBot Fault Narrator
Uses Groq to generate plain-English mission debriefs from ROS 2 fault data.
Intended to run after parse_diagnostics (and optionally inspect_graph) so judges
get a flight-recorder style narrative without reading raw JSON.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Default Groq model: fast, good for debriefs. Override with GROQ_MODEL.
DEFAULT_GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def _groq_chat(prompt: str, max_tokens: int) -> tuple[bool, str, str]:
    """Returns (ok, text_or_empty, error_hint)."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return False, "", "Set GROQ_API_KEY in the environment (never commit the key)."
    try:
        from groq import Groq  # type: ignore
    except ImportError:
        return False, "", "Install groq: pip install groq"
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=DEFAULT_GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        if not content:
            return False, "", "Groq returned an empty response."
        return True, content, ""
    except Exception as exc:  # noqa: BLE001
        return False, "", str(exc)


def narrate_fault(diagnostics_output: dict[str, Any], graph_output: dict[str, Any] | None = None) -> str:
    """
    Takes raw MCP tool output (typically parse_diagnostics) and returns a mission debrief.
    Raises RuntimeError on failure so callers can convert to MCP error dicts.
    """
    prompt = f"""
You are a robotics mission analyst writing a debrief for a non-technical
engineering manager. A robot experienced a fault during a mission.

FAULT DATA FROM MISSION LOGS:
{json.dumps(diagnostics_output, indent=2, default=str)}

ROBOT SYSTEM CONTEXT:
{json.dumps(graph_output, indent=2, default=str) if graph_output else "Not provided"}

Write a mission debrief with exactly these sections:

## What Happened
2-3 sentences. Plain English. No jargon. What did the robot do wrong?

## When It Went Wrong
The exact timestamp and what the first sign of failure was.

## Why It Happened
The root cause in one sentence a manager can understand.

## What It Would Have Caused
What would happen to a real robot in the field if this went undetected.

## Severity
One word: CRITICAL / HIGH / MEDIUM / LOW. Then one sentence why.

Be direct. No fluff. Write like an aircraft accident investigator.
""".strip()

    ok, text, err = _groq_chat(prompt, max_tokens=500)
    if not ok:
        raise RuntimeError(err or "Groq narration failed")
    return text


def narrate_safety_findings(safety_report: str) -> str:
    """Turn a text safety review into an executive summary."""
    prompt = f"""
You are a robotics safety consultant writing an executive summary
for a CTO who is deciding whether to deploy a robot fleet.

SAFETY REVIEW FINDINGS:
{safety_report}

Write an executive summary with exactly these sections:

## Deployment Readiness
One word verdict: READY / NOT READY / CONDITIONAL

## Critical Risks
List only CRITICAL findings. For each: what could go wrong in the field,
expressed as a real-world consequence (robot crashes, worker injured, etc.)

## Estimated Fix Time
How long would it take a developer to fix all critical issues.

## Recommendation
One paragraph. Deploy or not? What must be fixed first?

Write for a CTO, not a developer. Dollar signs and human safety matter more
than technical details.
""".strip()

    ok, text, err = _groq_chat(prompt, max_tokens=400)
    if not ok:
        raise RuntimeError(err or "Groq narration failed")
    return text


def narrate_fault_mcp_response(diagnostics_output: dict[str, Any], graph_output: dict[str, Any]) -> dict[str, Any]:
    """Return MCP-shaped dict for narrate_fault_report tool."""
    try:
        text = narrate_fault(diagnostics_output, graph_output)
        return {
            "success": True,
            "narration": text,
            "model": DEFAULT_GROQ_MODEL,
            "powered_by": "Groq",
        }
    except RuntimeError as exc:
        return {"success": False, "error": str(exc), "hint": "Set GROQ_API_KEY and pip install groq."}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "hint": "Check GROQ_API_KEY and network."}


def narrate_fault_report_from_json_strings(diagnostics_json: str, graph_json: str = "{}") -> dict[str, Any]:
    """Parse tool JSON strings (as produced by Bob / MCP) and return narrate_fault_report dict."""
    try:
        diagnostics = json.loads(diagnostics_json)
        graph = json.loads(graph_json) if graph_json and graph_json.strip() else {}
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "error": str(exc),
            "hint": "Pass valid JSON strings (e.g. json.dumps(parse_diagnostics output)).",
        }
    if not isinstance(diagnostics, dict) or not isinstance(graph, dict):
        return {
            "success": False,
            "error": "Diagnostics and graph JSON must decode to objects.",
            "hint": "Use dict outputs from parse_diagnostics and inspect_graph.",
        }
    return narrate_fault_mcp_response(diagnostics, graph)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    repo_root = here.parent
    results_path = repo_root / "demo_outputs" / "tool_results.json"

    print("=== BobForBot Fault Narrator ===\n")

    if not results_path.is_file():
        print(f"Missing {results_path}. Run: python3 demo_run.py (from bobpilot-ros2-mcp)\n")
        raise SystemExit(1)

    results = json.loads(results_path.read_text(encoding="utf-8"))
    diag = results.get("parse_diagnostics") or results.get("diagnostics") or {}
    graph = results.get("inspect_graph") or results.get("graph") or {}

    if not isinstance(diag, dict):
        diag = {}
    if not isinstance(graph, dict):
        graph = {}

    print("--- MISSION DEBRIEF ---\n")
    debrief_text = ""
    try:
        debrief_text = narrate_fault(diag, graph if graph else None)
        print(debrief_text)
    except RuntimeError as e:
        print(f"(Skipping debrief: {e})")

    print("\n--- EXECUTIVE SAFETY SUMMARY ---\n")
    safety_path = repo_root / "demo_outputs" / "safety_report_safety_manager.md"
    safety_summary = ""
    if safety_path.is_file():
        try:
            safety_summary = narrate_safety_findings(safety_path.read_text(encoding="utf-8"))
            print(safety_summary)
        except RuntimeError as e:
            print(f"(Skipping safety summary: {e})")
    else:
        print("(No demo_outputs/safety_report_safety_manager.md — skipping)")

    out_path = repo_root / "demo_outputs" / "fault_narration.json"
    out_path.write_text(
        json.dumps(
            {
                "mission_debrief": debrief_text,
                "executive_safety_summary": safety_summary,
                "parse_diagnostics_included": bool(diag),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved to {out_path}")
