#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m pip install -r "${ROOT}/bobpilot-ros2-mcp/requirements.txt"
