from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("motion_controller"))
    params = share / "config" / "params.yaml"
    return LaunchDescription(
        [
            Node(
                package="motion_controller",
                executable="motion_controller_node",
                name="motion_controller",
                parameters=[str(params)],
                output="screen",
            ),
        ]
    )
