#!/usr/bin/env python3
"""
Write a tiny rosbag2 dataset for BobForBot demos: /diagnostics (WARN then ERROR on
odometry) plus sparse /odom so parse_diagnostics and read_bag have real payloads.

Requires ROS 2 sourced (rosbag2_py, rclpy, message serialization), e.g.:
  source /opt/ros/humble/setup.bash
  python3 scripts/synth_fault_bag.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize fault_scenario_1_odom_loss rosbag2 folder.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (rosbag2 folder). Default: <repo>/demo-robot-workspace/logs/fault_scenario_1_odom_loss",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    out = args.output or (repo_root / "demo-robot-workspace" / "logs" / "fault_scenario_1_odom_loss")

    try:
        import rclpy  # type: ignore
        import rosbag2_py  # type: ignore
        from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue  # type: ignore
        from nav_msgs.msg import Odometry  # type: ignore
        from rclpy.serialization import serialize_message  # type: ignore
        from std_msgs.msg import Header  # type: ignore
    except ImportError as exc:
        print(
            "Missing ROS 2 Python packages. Source ROS first, e.g.\n"
            "  source /opt/ros/humble/setup.bash\n"
            f"Import error: {exc}",
            file=sys.stderr,
        )
        return 1

    if out.exists():
        shutil.rmtree(out)
    # Do not mkdir: SequentialWriter creates the bag directory.

    rclpy.init(args=None)

    writer = rosbag2_py.SequentialWriter()
    storage_options = rosbag2_py.StorageOptions(uri=str(out), storage_id="sqlite3")
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format="cdr",
        output_serialization_format="cdr",
    )
    writer.open(storage_options, converter_options)

    writer.create_topic(
        rosbag2_py.TopicMetadata("/diagnostics", "diagnostic_msgs/msg/DiagnosticArray", "cdr", "")
    )
    writer.create_topic(rosbag2_py.TopicMetadata("/odom", "nav_msgs/msg/Odometry", "cdr", ""))

    t_ns = int(time.time() * 1e9)

    def write_topic(topic: str, msg: object) -> None:
        writer.write(topic, serialize_message(msg), t_ns)

    def skip_ns(delta_ns: int) -> None:
        nonlocal t_ns
        t_ns += delta_ns

    diag_ok = DiagnosticArray()
    st0 = DiagnosticStatus()
    st0.level = DiagnosticStatus.OK
    st0.name = "odometry_health"
    st0.hardware_id = "odometry"
    st0.message = "odometry ok"
    diag_ok.status.append(st0)
    write_topic("/diagnostics", diag_ok)

    for _ in range(3):
        skip_ns(100_000_000)  # 0.1s
        odom = Odometry()
        odom.header = Header()
        odom.header.stamp.sec = int(t_ns // 1_000_000_000)
        odom.header.stamp.nanosec = int(t_ns % 1_000_000_000)
        odom.header.frame_id = "odom"
        write_topic("/odom", odom)

    skip_ns(2_000_000_000)  # 2.0s gap — staleness scenario
    diag_warn = DiagnosticArray()
    st1 = DiagnosticStatus()
    st1.level = DiagnosticStatus.WARN
    st1.name = "odometry_health"
    st1.hardware_id = "odometry"
    st1.message = "odometry stale"
    st1.values.append(KeyValue(key="age_sec", value="1.200"))
    diag_warn.status.append(st1)
    write_topic("/diagnostics", diag_warn)

    skip_ns(500_000_000)
    diag_err = DiagnosticArray()
    st2 = DiagnosticStatus()
    st2.level = DiagnosticStatus.ERROR
    st2.name = "odometry_health"
    st2.hardware_id = "odometry"
    st2.message = "odometry lost — mission fault"
    diag_err.status.append(st2)
    write_topic("/diagnostics", diag_err)

    writer.close()
    rclpy.shutdown()

    print(f"Wrote demo bag: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
