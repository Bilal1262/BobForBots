"""
Run all BobPilot ROS 2 MCP tools locally against the demo workspace (no IBM Bob).
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from server import (
    diff_packages_core,
    get_params_core,
    inspect_graph_core,
    lint_launch_core,
    parse_diagnostics_core,
    read_bag_core,
)


def _truncate(obj: object, limit: int = 500) -> str:
    text = json.dumps(obj, indent=2, default=str)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


async def main() -> None:
    here = Path(__file__).resolve().parent
    default_ws = (here / ".." / "demo-robot-workspace").resolve()
    workspace = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_ws

    out_path = (here / ".." / "demo_outputs" / "tool_results.json").resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    odom_launch = workspace / "src" / "odometry_health_monitor" / "launch" / "odometry_health_monitor.launch.py"
    bag_dir = workspace / "logs" / "fault_scenario_1_odom_loss"

    tool_results: dict[str, object] = {}

    steps: list[tuple[str, Awaitable[Any]]] = [
        ("inspect_graph", inspect_graph_core(str(workspace))),
        ("lint_launch", lint_launch_core(str(odom_launch))),
        ("get_params", get_params_core(str(workspace))),
        ("diff_packages", diff_packages_core(str(workspace))),
        ("parse_diagnostics", parse_diagnostics_core(str(bag_dir))),
        ("read_bag", read_bag_core(str(bag_dir), "/odom", 0.0, 5.0, 50)),
    ]

    for idx, (name, coro) in enumerate(steps, start=1):
        print(f"[{idx}/{len(steps)}] {name}...")
        try:
            result = await coro
        except Exception as exc:  # noqa: BLE001
            result = {"success": False, "error": str(exc), "hint": "Tool raised unexpectedly."}
        tool_results[name] = result
        print(_truncate(result))

    out_path.write_text(json.dumps(tool_results, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
