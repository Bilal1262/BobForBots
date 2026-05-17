"""Pytest for odometry watchdog — publishes odom first so last_odom_time is initialised."""

from __future__ import annotations

import time

import pytest
import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from nav_msgs.msg import Odometry
from std_msgs.msg import Header

from odometry_health_monitor.odometry_health_monitor_node import OdometryHealthMonitorNode


@pytest.fixture()
def ros_context() -> None:
    rclpy.init()
    yield
    rclpy.shutdown()


def test_diagnostic_error_after_timeout(ros_context: None) -> None:
    node = OdometryHealthMonitorNode()
    diag_msgs: list[DiagnosticArray] = []

    def on_diag(msg: DiagnosticArray) -> None:
        diag_msgs.append(msg)

    node.create_subscription(DiagnosticArray, "/diagnostics", on_diag, 10)
    pub = node.create_publisher(Odometry, "/odom", 10)

    odom = Odometry()
    odom.header = Header()
    odom.header.stamp = node.get_clock().now().to_msg()
    pub.publish(odom)

    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.05)

    time.sleep(1.2)

    for _ in range(40):
        rclpy.spin_once(node, timeout_sec=0.05)

    node.destroy_node()
    assert diag_msgs, "expected at least one diagnostic message"
    last = diag_msgs[-1]
    assert last.status, "diagnostic array empty"
    # After timeout without further odom, expect error level
    assert last.status[0].level >= 1
