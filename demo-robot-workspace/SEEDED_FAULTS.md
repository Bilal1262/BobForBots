# Demo workspace: seeded fault ↔ safety check ↔ bag evidence

Each package has **one** intentional defect aligned with **one** item in `bobpilot-pack/.bob/rules-ros2-safety-reviewer/safety-checklist.md`. Judges can run `./scripts/run_demo_tools.sh` (after `source /opt/ros/humble/setup.bash` and `./scripts/synth_fault_bag.py`) to see MCP JSON **before** any LLM reasoning.

| Package | Seeded bug (source) | Check # | Synthetic bag ties to… |
|---------|---------------------|---------|-------------------------|
| `odometry_health_monitor` | Uninitialised `last_odom_time` + bare `except` in watchdog — no reliable fault until first `/odom` | **6** — sensor/odom path without a correct staleness path at startup | `/diagnostics` levels WARN→ERROR on `hardware_id: odometry` |
| `safety_manager` | No try/catch in `on_activate`; `/emergency_stop` uses bare `rclcpp::QoS(1)` | **1** and **4** (lifecycle + safety QoS) | Optional: extend bag with `/diagnostics` from lifecycle faults |
| `task_supervisor` | `_on_result` always marks success | **8** — action result not propagated | Nav2 `GoalStatus` mismatch visible in mission logs; bag focuses on odom/diagnostics |
| `motion_controller` | Linear clamp uses literal **0.8** vs parameter | **7** — hard-coded limits | `/cmd_vel` vs `/safe_cmd_vel` in bag shows clamp inconsistency vs params |

Generate the bag:

```bash
source /opt/ros/humble/setup.bash
python3 scripts/synth_fault_bag.py
```

Rosbag2 output directory: `demo-robot-workspace/logs/fault_scenario_1_odom_loss/` (not a single `.bag` file; ROS 2 uses a folder + sqlite).
