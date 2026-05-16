# BobForBot 🤖

**IBM Bob as an AI engineer for any ROS2 robotics codebase.**

Built in 48 hours for the IBM Bob Hackathon · May 2026

---

## What is this?

Robotics software is hard. A real ROS2 codebase has hundreds of nodes talking to each other through topics, configured by YAML files, launched by Python scripts. When something breaks during a mission, engineers spend hours digging through gigabytes of binary data files with no intelligent tool to help them.

BobForBot fixes that.

Drop one folder — the `.bob/` pack — into any ROS2 workspace and IBM Bob immediately becomes a domain expert on that robot. It reads the source code, understands the node graph, reads real mission data files, finds bugs, fixes them, generates documentation, and checks every code change for safety issues.

**30 seconds. 9 cents. What would take a human engineer 4-6 hours.**

---

## What it actually did in the demo

These are real results from running BobForBot on our demo workspace:

**Fault diagnosis:** Bob read a binary rosbag from a failed mission, called our MCP tools, traced an odometry watchdog bug to line 27 of the source file, applied the fix, wrote a unit test, and opened a pull request. Time: 30 seconds. Cost: $0.09.

**Safety review:** Bob ran 8 safety checks on a C++ lifecycle node and found a CRITICAL bug — the emergency stop topic was using BEST_EFFORT QoS, meaning emergency stop commands could be silently dropped under network load. The robot could not be halted in an emergency. The fix was one word. Bob found it and wrote it automatically.

**Documentation:** Bob generated a complete professional README for the odometry monitor package in 20 seconds — mermaid node graph, topic table, parameter table, five common failure scenarios with diagnosis and fix. Before BobForBot the README said "TODO: document this."

**Groq CTO verdict:** After Bob's safety analysis, we fed the findings to Groq. Verdict: NOT READY FOR DEPLOYMENT. Two critical risks. Estimated fix time 2-4 days. Cost: $0.004. Time: 8 seconds.

---

## Three things BobForBot does

### 🔍 Repo Whisperer
Ask Bob how the robot works and get answers grounded in the actual source code with file and line citations. What takes a senior engineer 30 minutes takes Bob 30 seconds. Powered by the `ros2-architect` custom mode and `inspect_graph` MCP tool.

### 🔧 Black-Box Analyst
Drop in a rosbag fault log from a failed mission. Bob reads the binary telemetry, traces the root cause through the codebase, proposes the minimal safe fix, writes the test, and opens the PR — all with your approval before any file is touched. Powered by `ros2-recovery-engineer` mode and `parse_diagnostics` + `read_bag` MCP tools.

### 📝 Living Docs + Safety Engine
Bob generates professional documentation directly from source code — never invents behaviour it cannot verify. It also runs 8 safety checks on every PR and reports CRITICAL, WARNING, or INFO findings with exact file and line citations and ready-to-apply fixes. Powered by `ros2-docs-architect` and `ros2-safety-reviewer` custom modes.

---

## How IBM Bob is used

We didn't just prompt Bob. We extended it with every differentiating feature it offers:

| Feature | How we use it |
|---------|--------------|
| **4 custom modes** | `ros2-architect`, `ros2-recovery-engineer`, `ros2-docs-architect`, `ros2-safety-reviewer` — each a specialist with its own rules, tool access, and safety constraints |
| **Custom MCP server** | 6 ROS2-specific tools: `inspect_graph`, `read_bag`, `parse_diagnostics`, `lint_launch`, `get_params`, `diff_packages` — Bob calls these autonomously based on the task |
| **Orchestrator mode** | Coordinates a 5-agent fault diagnosis pipeline — parse diagnostics → read bag → inspect graph → trace source → propose fix |
| **Custom rules** | Per-mode rule files encoding ROS2 conventions, QoS best practice, ISO 26262 traceability requirements, and safe-edit policies |
| **BobShell** | `/diagnose-mission` slash command — one command triggers the full diagnosis workflow |
| **Checkpoints** | Every code change Bob makes is checkpointed — one click to roll back, critical for real robot safety |
| **Exported session reports** | All Bob sessions exported and included in `bob-sessions/` — see `bob-sessions/README.md` |

---

## Quick start

```bash
# Clone the repo
git clone https://github.com/Bilal1262/BobForBots.git
cd BobForBots

# Copy the .bob pack into your own ROS2 workspace
cp -r bobpilot-pack/.bob /path/to/your/ros2_ws/.bob

# Open your workspace in IBM Bob IDE
# The MCP server starts automatically via .bob/mcp.json
# Your 4 custom modes appear in Bob's mode selector immediately
```

That's it. No training data. No configuration. Bob reads your codebase and becomes an expert on your specific robot.

---

## Run the demo yourself

```bash
# Install dependencies
pip install -r requirements.txt --break-system-packages

# Source ROS2 (required for rosbag tools)
source /opt/ros/humble/setup.bash

# Generate the demo fault scenario rosbag
python3 scripts/synth_fault_bag.py

# Test all 6 MCP tools against the demo workspace
cd bobpilot-ros2-mcp
python3 demo_run.py ../demo-robot-workspace

# Run the Streamlit dashboard
cd ..
export GROQ_API_KEY="your_key_here"
pip install -r requirements-ui.txt --break-system-packages
streamlit run app.py
```

The dashboard runs at `http://localhost:8501` with 5 pages:
- **Mission Control** — live workspace metrics from MCP tools
- **Fault Diagnosis** — rosbag fault timeline + Groq plain-English debrief
- **Node Graph** — auto-generated topic connection map
- **Safety Review** — 8-check checklist + Groq CTO deployment verdict
- **Ask Bob** — natural language Q&A about the codebase

---

## Demo workspace — the seeded faults

The `demo-robot-workspace` has 4 packages with real bugs seeded into them. These are what Bob finds and fixes during the demo:

| Package | Type | Seeded bug | Bob finds it via |
|---------|------|-----------|-----------------|
| `odometry_health_monitor` | Python | `self.last_odom_time` never initialised — watchdog silently fails at startup | `parse_diagnostics` + `read_bag` + source trace |
| `safety_manager` | C++ lifecycle | `/emergency_stop` uses BEST_EFFORT QoS — e-stop messages can be dropped | Safety reviewer check #4 |
| `task_supervisor` | Python | Result callback always marks tasks as success regardless of Nav2 result | Safety reviewer check #8 |
| `motion_controller` | C++ | Hardcoded `0.8` m/s instead of reading `max_linear_vel_` parameter | Safety reviewer check #7 |

These are not toy examples. These are the classes of bugs that caused real robot recalls and mission failures.

---

## Project structure

```
BobForBot/
├── bobpilot-pack/
│   └── .bob/
│       ├── custom_modes.yaml      ← 4 specialist Bob modes
│       ├── mcp.json               ← wires the MCP server to Bob
│       ├── rules/                 ← global ROS2 conventions
│       ├── rules-ros2-architect/
│       ├── rules-ros2-recovery-engineer/
│       ├── rules-ros2-docs-architect/
│       └── rules-ros2-safety-reviewer/
│
├── bobpilot-ros2-mcp/
│   ├── server.py                  ← the MCP server (6 tools, STDIO, read-only)
│   ├── demo_run.py                ← test all tools without Bob
│   └── requirements.txt
│
├── demo-robot-workspace/
│   ├── src/                       ← 4 ROS2 packages with seeded bugs
│   └── logs/                      ← real rosbag fault scenarios
│
├── demo_outputs/                  ← tool results, generated docs, Groq reports
├── bob-sessions/                  ← exported IBM Bob session reports (required)
├── docs/                          ← Bob-generated package documentation
├── app.py                         ← Streamlit robotics operations dashboard
└── scripts/                       ← helper scripts for setup and demo
```

---

## IBM Bob session exports

The `bob-sessions/` folder contains the exported session reports for every Bob task used in this project — as required by the hackathon submission rules.

| Session | Mode | What Bob did |
|---------|------|-------------|
| `bob_session_01_architecture.md` | ros2-architect | Complete workspace overview — 4 packages, failure modes, data flow |
| `bob_session_02_fault_diagnosis.md` | ros2-recovery-engineer | Diagnosed odom loss fault, traced to line 27, applied fix, wrote test |
| `bob_session_03_documentation.md` | ros2-docs-architect | Generated complete README for odometry_health_monitor |
| `bob_session_04_safety_review.md` | ros2-safety-reviewer | Found 2 issues (1 CRITICAL, 1 WARNING) in safety_manager.cpp |

---

## Business case

The robot software market is $29.6B in 2026 and growing to $78.8B by 2031 (Mordor Intelligence). 400+ universities and 200+ companies use ROS2 as their standard robotics framework.

Onboarding one robotics developer costs approximately $80,000 over 90 days. IBM's own data shows 45% productivity gains with Bob across 10,000+ internal developers.

For a 50-person robotics team the ROI is straightforward:
- Onboarding savings: $500k/year
- Productivity gain at 45%: $1.7M/year
- Payback: under 3 months

The regulatory angle matters too. The EU Machinery Regulation 2027 mandates traceable, audited software practice for all robots deploying in Europe. Bob's BobShell traces are ISO 26262-compatible audit artefacts. After 2027, this isn't a nice-to-have — it's a compliance requirement.

---

## Architecture

```
Engineer asks a question or drops in a fault log
                    ↓
        IBM Bob — Orchestrator mode
   routes to the right custom mode automatically
                    ↓
    4 specialist modes (defined in .bob/)
  Architect | Recovery | Docs | Safety Reviewer
                    ↓
    bobpilot-ros2-mcp (local Python MCP server)
    6 tools: inspect_graph · read_bag · parse_diagnostics
             lint_launch · get_params · diff_packages
                    ↓
    Your ROS2 workspace (read-only, no live robot needed)
    Source files · rosbag logs · YAML configs · launch files
```

Bob auto-starts the MCP server via `.bob/mcp.json` — you never run it manually.

---

## Who built this

**Bilal Ahmed Qaimkhani**
Visiting Scholar — Ocean Systems Lab, Heriot-Watt University, Edinburgh
Erasmus Mundus MSc in Intelligent Field Robotic Systems (GPA 9.40/10)

Research focus: LLM/VLM-based agentic recovery frameworks for autonomous underwater vehicles. The bugs in this demo are the same classes of bugs that cause real robots to fail in the field.

📧 bk632723@gmail.com
🔗 github.com/Bilal1262/BobForBots

---

## License

MIT — use it, build on it, deploy it on your robot.

Built with IBM Bob · Groq · ROS2 · Python · Streamlit
