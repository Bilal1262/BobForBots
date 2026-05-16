# BobForBot — IBM Bob as an AI engineer for any ROS 2 robotics codebase

BobForBot packages an IBM **Bob** configuration (custom modes, rules, MCP tools) so teams can navigate, debug, document, and safety-review **any ROS 2** workspace with grounded answers tied to real source, bags, and parameters.

## Three capabilities

1. **Repo Whisperer** — explains packages, launch files, topics, and data flow using static analysis and citations (Architect mode + `inspect_graph`).
2. **Black-Box Analyst** — triages missions with diagnostics and bag tools, proposes minimal fixes and tests (Recovery Engineer mode + MCP).
3. **Living Docs** — generates accurate package READMEs, topic/parameter tables, and failure runbooks from code only (Docs Architect mode).

## Project scripts

Helper scripts live in `scripts/` (see `scripts/README.md`):

- **`install_python_deps.sh`** — pip-install MCP dependencies.
- **`run_mcp_stdio.sh`** — run the stdio MCP server (sources Humble `setup.bash` if present).
- **`run_demo_tools.sh`** — run all six tools against `demo-robot-workspace`.
- **`synth_fault_bag.py`** — **requires sourced ROS 2** — writes `demo-robot-workspace/logs/fault_scenario_1_odom_loss/` so `parse_diagnostics` / `read_bag` return real data before any LLM step.
- **`fault_narrator.py`** (in `bobpilot-ros2-mcp/`) — **requires `GROQ_API_KEY`** — reads `demo_outputs/tool_results.json` and writes `demo_outputs/fault_narration.json` (Groq mission debrief + optional CTO safety summary).

**Streamlit robotics dashboard:** from repo root, `pip install -r requirements-ui.txt`, set `GROQ_API_KEY`, then **`streamlit run app.py`**. Dark theme and colors come from **`.streamlit/config.toml`** — **restart Streamlit** after editing that file.

**Groq + IBM Bob:** add your API key to `bobpilot-pack/.bob/mcp.json` under `env.GROQ_API_KEY` (or rely on your shell environment if the IDE forwards it). The MCP tool `narrate_fault_report` runs **after** `parse_diagnostics`; pass `json.dumps(...)` of the tool outputs as the string arguments.

Recommended demo order from the spec: author **`bobpilot-pack/.bob/`** in Bob (Plan → Code), export that session, then implement or refresh `server.py` and the demo workspace; use the scripts to prove tool JSON is real.

Shell conveniences: [`scripts/README.md`](scripts/README.md).

## Quick start

```bash
git clone <https://github.com/your-org/BobForBot.git>
cp -r BobForBot/bobpilot-pack/.bob /path/to/your/ros2_ws/.bob
# Open your ROS 2 workspace in IBM Bob IDE and enable the bobpilot-ros2 MCP server.
```

*(Replace the clone URL with your published repository.)*

## How IBM Bob is used here

| Piece | Role |
|-------|------|
| **Custom modes** | Four slugs (`ros2-architect`, `ros2-recovery-engineer`, `ros2-docs-architect`, `ros2-safety-reviewer`) with roles, scopes, and linked rules. |
| `narrate_fault_report` | After `parse_diagnostics`, turns diagnostic JSON (+ optional graph JSON) into a plain-English mission debrief via **Groq** (`GROQ_API_KEY` required). |
| **Orchestrator** | Routes multi-step missions (e.g. diagnose-then-fix) across modes and tools. |
| **BobShell** | Slash commands and scripted demos (e.g. `/diagnose-mission`). |
| **Custom rules** | Workspace conventions + per-mode rule folders keep outputs consistent and safe. |

## Demo workspace

The included `demo-robot-workspace` has four packages with **seeded defects** for training and demos:

| Package | Intent | Seeded issue |
|---------|--------|----------------|
| `odometry_health_monitor` (Python) | Watchdog on `/odom`, diagnostics, `/cmd_vel` stop | Uninitialised `last_odom_time` + bare `except` swallows `AttributeError` at startup. |
| `safety_manager` (C++ lifecycle) | Safety aggregation | Default QoS on `/emergency_stop`; no try/catch around subscription setup in `on_activate`. |
| `task_supervisor` (Python) | Nav2 goal dispatch | Result callback always marks task success (ignores `GoalStatus`). |
| `motion_controller` (C++) | Clamp and forward cmd_vel | Hardcoded linear limit `0.8` instead of `max_linear_vel_`. |

See `pitch/demo_script.md` for a timed walkthrough.

## Business case

- **Market:** ~$29.6B robot software market (industry analyst ballpark — use your own source in slides).
- **Ecosystem:** 200+ vendors and labs standardise on ROS 2 for autonomy stacks.
- **Onboarding:** senior robotics onboarding often quoted **~$80k** fully loaded; months of graph-tracing before a dev is productive.
- **Incidents:** avoided downtime and mission failure from faster root-cause analysis pays back tooling cost quickly.

## Architecture

```
┌─────────────────────────────────────────────┐
│          IBM Bob (IDE + Orchestrator)        │
│  Modes · Rules · BobShell · Session export   │
└────────────────────┬────────────────────────┘
                     │ stdio MCP
┌────────────────────▼────────────────────────┐
│           bobpilot-ros2-mcp (Python)        │
│  inspect_graph · bags · diagnostics · …     │
└────────────────────┬────────────────────────┘
                     │ read-only FS / git / bags
┌────────────────────▼────────────────────────┐
│        Your ROS 2 workspace (colcon src/)     │
└─────────────────────────────────────────────┘
```

## Evidence trail

Session narratives and export format are described in [`bob-sessions/README.md`](bob-sessions/README.md).

## License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project is licensed under the **MIT License** — see the repository root for the full license text when published.
