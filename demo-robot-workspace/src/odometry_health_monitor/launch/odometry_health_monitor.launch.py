import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pkg = "odometry_health_monitor"
    share = get_package_share_directory(pkg)
    params_file = Path(share) / "config" / "params.yaml"

    return LaunchDescription(
        [
            Node(
                package=pkg,
                executable="odometry_health_monitor_node",
                name="odometry_health_monitor",
                parameters=[str(params_file)],
                output="screen",
            ),
        ]
    )
