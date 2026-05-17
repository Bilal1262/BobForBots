"""Load navigation tasks from a YAML file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class TaskItem:
    task_id: str
    task_type: str
    goal_x: float
    goal_y: float
    timeout_sec: float


def load_tasks_from_yaml(path: str | Path) -> List[TaskItem]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "tasks" not in data:
        return []
    items: List[TaskItem] = []
    for row in data["tasks"]:
        if not isinstance(row, dict):
            continue
        items.append(
            TaskItem(
                task_id=str(row.get("task_id", "")),
                task_type=str(row.get("task_type", "navigate")),
                goal_x=float(row.get("goal_x", 0.0)),
                goal_y=float(row.get("goal_y", 0.0)),
                timeout_sec=float(row.get("timeout_sec", 30.0)),
            )
        )
    return items
