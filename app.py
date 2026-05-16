#!/usr/bin/env python3
"""
BobForBot — Streamlit robotics operations dashboard.

Theme: `.streamlit/config.toml` (dark base). Run from repo root:
  pip install -r requirements-ui.txt
  export GROQ_API_KEY=...
  streamlit run app.py

Data: demo_outputs/tool_results.json (bobpilot-ros2-mcp/demo_run.py).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
MCP_DIR = ROOT / "bobpilot-ros2-mcp"
sys.path.insert(0, str(MCP_DIR))

RESULTS_PATH = ROOT / "demo_outputs" / "tool_results.json"
NARRATION_PATH = ROOT / "demo_outputs" / "fault_narration.json"
SAFETY_PATH = ROOT / "demo_outputs" / "safety_report_safety_manager.md"

DEFAULT_SAFETY_SNIPPET = """\
CRITICAL — safety_manager/src/safety_manager.cpp (on_activate): No try/catch around subscription setup; exception can stall lifecycle.
WARNING — safety_manager: /emergency_stop subscription uses rclcpp::QoS(1) without explicit reliable() for a safety-related topic name.
CRITICAL — odometry_health_monitor: Watchdog may fail silently at startup (uninitialised last_odom_time + bare except).
INFO — motion_controller: Hard-coded linear clamp 0.8 vs parameter max_linear_vel_.
WARNING — task_supervisor: Action result handler always marks success.
"""


def load_tool_results() -> dict[str, Any]:
    if not RESULTS_PATH.is_file():
        return {}
    try:
        return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def topic_graph_mermaid(inspect: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    pkgs = inspect.get("packages") or []
    if not pkgs:
        return "flowchart LR\n  empty[No inspect_graph data — run demo_run.py]"
    for p in pkgs:
        pid = str(p.get("package", "pkg")).replace(" ", "_")
        lines.append(f'  subgraph sg_{pid}["{p.get("package")}"]')
        pubs = p.get("publishers") or []
        subs = p.get("subscribers") or []
        for t in pubs[:12]:
            tid = t.replace("/", "_").replace("-", "_")
            lines.append(f"    {pid}_p_{tid}[publish: {t}]")
        for t in subs[:12]:
            tid = t.replace("/", "_").replace("-", "_")
            lines.append(f"    {pid}_s_{tid}[subscribe: {t}]")
        lines.append("  end")
    return "\n".join(lines)


def render_mermaid(chart: str, height: int = 520) -> None:
    chart_js = json.dumps(chart)
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;background:#0a0e1a;">
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
mermaid.initialize({{ startOnLoad: false, theme: "dark",
  themeVariables: {{
    primaryColor: "#00d4ff",
    primaryTextColor: "#e2e8f0",
    lineColor: "#22d3ee",
    secondaryColor: "#0f1628",
    tertiaryColor: "#0a0e1a"
  }}
}});
const el = document.createElement("div");
el.className = "mermaid";
el.textContent = {chart_js};
document.body.appendChild(el);
await mermaid.run({{ nodes: [el] }});
</script>
</body></html>"""
    components.html(html, height=height, scrolling=True)


def groq_debrief(diag: dict[str, Any], graph: dict[str, Any]) -> tuple[bool, str]:
    try:
        from fault_narrator import narrate_fault
    except ImportError as e:
        return False, str(e)
    try:
        return True, narrate_fault(diag, graph if graph else None)
    except RuntimeError as e:
        return False, str(e)


def groq_safety_exec(report: str) -> tuple[bool, str]:
    try:
        from fault_narrator import narrate_safety_findings
    except ImportError as e:
        return False, str(e)
    try:
        return True, narrate_safety_findings(report)
    except RuntimeError as e:
        return False, str(e)


def ask_groq(question: str, context: str) -> tuple[bool, str]:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return False, "Set GROQ_API_KEY in the environment."
    try:
        from groq import Groq
    except ImportError:
        return False, "pip install groq"
    client = Groq(api_key=api_key)
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = f"""You are a robotics software assistant. Answer briefly using the workspace summary below.

CONTEXT (from inspect_graph / packages):
{context[:12000]}

QUESTION:
{question}
"""
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        max_tokens=600,
    )
    return True, r.choices[0].message.content or ""


def inject_shell_styles() -> None:
    """Layer on top of Streamlit theme from .streamlit/config.toml — do not override base background."""
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"]  {
    font-family: 'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif !important;
  }
  code, pre, .stCodeBlock, textarea {
    font-family: 'IBM Plex Mono', ui-monospace, monospace !important;
  }
  [data-testid="stHeader"] { background: rgba(10,14,26,0.92); border-bottom: 1px solid rgba(0,212,255,0.15); }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1628 0%, #0a0e1a 100%);
    border-right: 1px solid rgba(0,212,255,0.12);
  }
  [data-testid="stSidebar"] .stRadio label { font-weight: 500; letter-spacing: 0.02em; }
  div[data-testid="stMetric"] {
    background: #0f1628;
    border: 1px solid rgba(0,212,255,0.18);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
  }
  div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
  div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.75rem !important; font-weight: 600; }
  .bf-hero {
    border-bottom: 1px solid rgba(0,212,255,0.2);
    padding-bottom: 1.25rem;
    margin-bottom: 1.5rem;
  }
  .bf-hero h1 { margin: 0 0 0.35rem 0; font-size: 1.65rem; font-weight: 600; letter-spacing: -0.02em; }
  .bf-kicker {
    color: #00d4ff;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin: 0 0 0.5rem 0;
  }
  .bf-pill {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    border: 1px solid rgba(0,212,255,0.35);
    color: #00d4ff;
    background: rgba(0,212,255,0.08);
  }
  .bf-panel {
    border: 1px solid rgba(0,212,255,0.15);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    background: #0f1628;
    margin-bottom: 1rem;
  }
  .stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid rgba(0,212,255,0.35) !important;
    background: linear-gradient(180deg, rgba(0,212,255,0.12), rgba(0,212,255,0.04)) !important;
  }
  .stButton > button:hover { border-color: #00d4ff !important; color: #e2e8f0 !important; }
  h2, h3 { margin-top: 0.5rem; }
</style>
""",
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, status_pill: str) -> None:
    st.markdown(
        f"""
<div class="bf-hero">
  <p class="bf-kicker">BobForBot · Robotics operations</p>
  <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; flex-wrap:wrap;">
    <div>
      <h1>{title}</h1>
      <p style="margin:0; color:#94a3b8; max-width:42rem;">{subtitle}</p>
    </div>
    <div style="align-self:center;"><span class="bf-pill">{status_pill}</span></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="BobForBot Ops", layout="wide", page_icon="🛰️")
    inject_shell_styles()

    results = load_tool_results()
    data_ok = bool(results.get("inspect_graph", {}).get("packages"))
    status = "LIVE DATA" if data_ok else "NO DATA — run demo_run.py"
    inspect = results.get("inspect_graph") or {}
    diag = results.get("parse_diagnostics") or {}
    read_bag = results.get("read_bag") or {}

    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio(
        "Section",
        [
            "Mission Control",
            "Fault Diagnosis",
            "Node Graph",
            "Safety Review",
            "Ask Bob",
        ],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    st.sidebar.caption("Load `demo_outputs/tool_results.json` via `bobpilot-ros2-mcp/demo_run.py` + optional `scripts/synth_fault_bag.py`.")
    st.sidebar.caption("Theme: `.streamlit/config.toml` — restart Streamlit after edits.")

    if page == "Mission Control":
        render_hero(
            "Mission control",
            "Workspace topology snapshot: packages, topic endpoints, and bag-level diagnostic fault count.",
            status,
        )
        c1, c2, c3, c4 = st.columns(4)
        pkgs = inspect.get("packages") or []
        fault_list = diag.get("faults") or []
        pubs = sum(len(p.get("publishers") or []) for p in pkgs)
        subs = sum(len(p.get("subscribers") or []) for p in pkgs)
        with c1:
            st.metric("Packages", str(inspect.get("package_count") if pkgs else "—"))
        with c2:
            st.metric("Publishers", str(pubs))
        with c3:
            st.metric("Subscribers", str(subs))
        with c4:
            st.metric("Bag faults", str(len(fault_list)))

        left, right = st.columns((1, 1.15))
        with left:
            st.markdown('<div class="bf-panel">', unsafe_allow_html=True)
            st.markdown("**Workspace root**")
            st.code(inspect.get("workspace") or "(run demo_run.py)", language="text")
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            if pkgs:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Package": p.get("package"),
                                "Publishers": len(p.get("publishers") or []),
                                "Subscribers": len(p.get("subscribers") or []),
                            }
                            for p in pkgs
                        ]
                    ),
                    use_container_width=True,
                    height=min(320, 56 + 36 * len(pkgs)),
                    hide_index=True,
                )
            else:
                st.info("No package table until `inspect_graph` is populated.")

    elif page == "Fault Diagnosis":
        render_hero(
            "Fault diagnosis",
            "Diagnostics timeline from the bag and a Groq-powered mission debrief for non-technical stakeholders.",
            status,
        )
        faults = diag.get("faults") or []
        col_left, col_right = st.columns((1.1, 1))

        with col_left:
            st.markdown("##### Telemetry faults")
            if faults:
                df = pd.DataFrame(faults)
                st.dataframe(df, use_container_width=True, height=340, hide_index=True)
            else:
                st.info("No faults — run `demo_run.py` after `scripts/synth_fault_bag.py`.")

        with col_right:
            st.markdown("##### Mission debrief (Groq)")
            if st.button("Generate plain-English debrief", type="primary", use_container_width=True):
                with st.spinner("Narrating…"):
                    ok, text = groq_debrief(diag, inspect)
                    if ok:
                        st.session_state["debrief"] = text
                    else:
                        st.error(text)
            if "debrief" in st.session_state:
                with st.container(border=True):
                    st.markdown(st.session_state["debrief"])

        with st.expander("Raw `parse_diagnostics`"):
            st.json(diag)
        with st.expander("Raw `read_bag` (/odom)"):
            st.json(read_bag)

    elif page == "Node Graph":
        render_hero(
            "Topic graph",
            "Package-grouped publishers and subscribers from static `inspect_graph` (Mermaid).",
            status,
        )
        chart = topic_graph_mermaid(inspect)
        st.markdown("**Mermaid source**")
        st.code(chart, language="mermaid")
        st.markdown("**Preview**")
        render_mermaid(chart)

    elif page == "Safety Review":
        render_hero(
            "Safety review",
            "Paste Bob safety output, then ask Groq for a CTO-facing deployment summary.",
            status,
        )
        report = SAFETY_PATH.read_text(encoding="utf-8") if SAFETY_PATH.is_file() else DEFAULT_SAFETY_SNIPPET
        edited = st.text_area("Findings", report, height=240, label_visibility="collapsed")
        if st.button("Generate CTO summary (Groq)", type="primary"):
            with st.spinner("Summarizing…"):
                ok, text = groq_safety_exec(edited)
                if ok:
                    st.session_state["cto"] = text
                else:
                    st.error(text)
        if "cto" in st.session_state:
            st.markdown(st.session_state["cto"])
        st.divider()
        st.caption("Reference: `bobpilot-pack/.bob/rules-ros2-safety-reviewer/safety-checklist.md`")

    else:
        render_hero(
            "Ask Bob",
            "Quick Groq Q&A grounded in `inspect_graph` (trimmed context).",
            status,
        )
        ctx = json.dumps(inspect, indent=2, default=str)[:14000] if inspect else "No inspect_graph data."
        st.markdown("**Suggested questions**")
        presets = [
            "What is the most likely fault node for odometry loss in this workspace?",
            "Which package publishes /diagnostics?",
            "Summarize publisher/subscriber edges for odometry_health_monitor.",
        ]
        pc1, pc2, pc3 = st.columns(3)
        for i, q in enumerate(presets):
            with (pc1, pc2, pc3)[i]:
                if st.button(q[:56] + ("…" if len(q) > 56 else ""), key=f"preset_{i}", use_container_width=True):
                    st.session_state["pending_q"] = q
        question = st.chat_input("Ask about this workspace…")
        q = question or st.session_state.pop("pending_q", None)
        if q:
            with st.spinner("Groq…"):
                ok, ans = ask_groq(q, ctx)
                if ok:
                    with st.container(border=True):
                        st.markdown(ans)
                else:
                    st.warning(ans)


main()
