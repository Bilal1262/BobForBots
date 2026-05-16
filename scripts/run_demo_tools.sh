#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f /opt/ros/humble/setup.bash ]]; then
  # shellcheck source=/dev/null
  source /opt/ros/humble/setup.bash
fi
cd "${ROOT}/bobpilot-ros2-mcp"
exec python3 demo_run.py "${ROOT}/demo-robot-workspace"
