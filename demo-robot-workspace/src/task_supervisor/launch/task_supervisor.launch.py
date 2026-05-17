from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("task_supervisor"))
    params = share / "config" / "params.yaml"
    return LaunchDescription(
        [
            Node(
                package="task_supervisor",
                executable="task_supervisor_node",
                name="task_supervisor",
                parameters=[str(params)],
                output="screen",
            ),
        ]
    )
