"""High-level task supervisor with Nav2 action client (demo, seeded logic bug)."""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String

from task_supervisor.task_list import TaskItem, load_tasks_from_yaml


class SupervisorState(Enum):
    IDLE = auto()
    EXECUTING = auto()


class TaskSupervisorNode(Node):
    """Loads tasks from YAML and dispatches NavigateToPose goals."""

    def __init__(self) -> None:
        super().__init__("task_supervisor")

        self.declare_parameter("task_timeout_sec", 30.0)
        self.declare_parameter("retry_count", 3)

        self._timeout = float(self.get_parameter("task_timeout_sec").value)
        self._retries = int(self.get_parameter("retry_count").value)

        share = Path(get_package_share_directory("task_supervisor"))
        tasks_path = share / "config" / "tasks.yaml"
        self._tasks: List[TaskItem] = load_tasks_from_yaml(tasks_path)
        self._task_index = 0
        self._state = SupervisorState.IDLE

        self._status_pub = self.create_publisher(String, "/task_status", 10)
        self._action_client = ActionClient(self, NavigateToPose, "navigate_to_pose")

        self._timer = self.create_timer(1.0, self._tick)

    def _publish_status(self, text: str) -> None:
        msg = String()
        msg.data = text
        self._status_pub.publish(msg)

    def _tick(self) -> None:
        if self._state != SupervisorState.IDLE:
            return
        if self._task_index >= len(self._tasks):
            return
        self._dispatch_current_task()

    def _dispatch_current_task(self) -> None:
        task = self._tasks[self._task_index]
        self._state = SupervisorState.EXECUTING
        self._publish_status(f"EXECUTING {task.task_id}")

        if not self._action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn("navigate_to_pose action server not available (demo mode)")
            self._mark_task_complete(success=False)
            return

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        goal.pose.pose.position.x = task.goal_x
        goal.pose.pose.position.y = task.goal_y
        goal.pose.pose.orientation.w = 1.0

        send_future = self._action_client.send_goal_async(goal)

        def _on_goal_response(fut) -> None:
            goal_handle = fut.result()
            if not goal_handle.accepted:
                self.get_logger().error("Goal rejected")
                self._mark_task_complete(success=False)
                return
            result_future = goal_handle.get_result_async()
            result_future.add_done_callback(self._on_result)

        send_future.add_done_callback(_on_goal_response)

    def _on_result(self, fut) -> None:
        result_wrapper = fut.result()
        status = result_wrapper.status
        _ = status  # noqa: F841 — would check GoalStatus in a correct implementation
        # BUG: always marks task as success — ignores action result status, causes silent task failure
        self._mark_task_complete(success=True)

    def _mark_task_complete(self, success: bool) -> None:
        if self._task_index < len(self._tasks):
            tid = self._tasks[self._task_index].task_id
            self._publish_status(f"DONE {tid} success={success}")
        self._task_index += 1
        self._state = SupervisorState.IDLE


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = TaskSupervisorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
