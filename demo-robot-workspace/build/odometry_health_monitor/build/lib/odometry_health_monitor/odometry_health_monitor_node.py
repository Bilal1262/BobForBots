"""ROS 2 node: watchdog odometry stream, publish diagnostics and zero cmd_vel on fault."""

from __future__ import annotations

import math
from typing import Optional

import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class OdometryHealthMonitorNode(Node):
    """Subscribe to /odom; timer checks staleness; publish diagnostics and /cmd_vel zeros on fault."""

    def __init__(self) -> None:
        super().__init__("odometry_health_monitor")

        self.declare_parameter("odom_timeout_sec", 1.0)
        self.declare_parameter("stop_on_timeout", True)

        self._timeout = float(self.get_parameter("odom_timeout_sec").value)
        self._stop_on_timeout = bool(self.get_parameter("stop_on_timeout").value)

        # Initialize last_odom_time to None (no odometry received yet)
        self.last_odom_time = None

        self._diag_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)

        self._odom_sub = self.create_subscription(
            Odometry,
            "/odom",
            self._on_odom,
            10,
        )

        self._timer = self.create_timer(1.0, self._watchdog_tick)

    def _on_odom(self, msg: Odometry) -> None:
        self.last_odom_time = self.get_clock().now()

    def _watchdog_tick(self) -> None:
        now = self.get_clock().now()
        
        # Treat uninitialized or missing odometry as stale
        if self.last_odom_time is None:
            stale = True
            age = float('inf')
        else:
            age = (now - self.last_odom_time).nanoseconds * 1e-9
            stale = age > self._timeout

        stat = DiagnosticStatus()
        stat.name = "odometry_health"
        stat.hardware_id = "odometry"
        stat.level = DiagnosticStatus.ERROR if stale else DiagnosticStatus.OK
        stat.message = "odometry stale" if stale else "odometry ok"
        stat.values = [
            KeyValue(key="age_sec", value=f"{age:.3f}" if age != float('inf') else "inf"),
        ]

        arr = DiagnosticArray()
        arr.status.append(stat)
        self._diag_pub.publish(arr)

        if stale and self._stop_on_timeout:
            stop = Twist()
            self._cmd_pub.publish(stop)


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node = OdometryHealthMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
