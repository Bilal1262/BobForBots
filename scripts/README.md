# BobForBot helper scripts

Run shell scripts from the **repository root** (`BobForBot/`), e.g. `./scripts/run_demo_tools.sh`.

| Script | Purpose |
|--------|---------|
| `install_python_deps.sh` | `pip install` MCP server dependencies (`mcp`, `fastmcp`, `pyyaml`). |
| `run_mcp_stdio.sh` | Start `bobpilot-ros2-mcp/server.py` on stdio (optional: sources `/opt/ros/humble/setup.bash` if present). |
| `run_demo_tools.sh` | Run `demo_run.py` against `demo-robot-workspace` and write `demo_outputs/tool_results.json`. |
| `synth_fault_bag.py` | **Requires sourced ROS 2.** Writes a small rosbag2 folder under `demo-robot-workspace/logs/fault_scenario_1_odom_loss/` with `/diagnostics` (+ sparse `/odom`) for `parse_diagnostics` / `read_bag` demos. |
| `../bobpilot-ros2-mcp/fault_narrator.py` | **Requires `GROQ_API_KEY` + `pip install groq`.** Reads `demo_outputs/tool_results.json`, prints debriefs, writes `demo_outputs/fault_narration.json`. Run from repo root: `python3 bobpilot-ros2-mcp/fault_narrator.py` |
| `../app.py` | **UI:** `pip install -r requirements-ui.txt` then `streamlit run app.py` from repo root. |

For IBM Bob session flow (Plan → Code → export): start by authoring `bobpilot-pack/.bob/` with Bob, commit, then automate the rest with these scripts.
