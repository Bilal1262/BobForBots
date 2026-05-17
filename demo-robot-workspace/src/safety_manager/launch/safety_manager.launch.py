import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers.on_process_start import OnProcessStart
from launch.event_handlers.on_state_transition import OnStateTransition
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState, matches_action
from lifecycle_msgs.msg import Transition


def generate_launch_description() -> LaunchDescription:
    pkg_share = get_package_share_directory("safety_manager")
    params = Path(pkg_share) / "config" / "params.yaml"

    lifecycle_node = LifecycleNode(
        package="safety_manager",
        executable="safety_manager_node",
        name="safety_manager",
        namespace="",
        parameters=[str(params)],
        output="screen",
    )

    emit_configure = RegisterEventHandler(
        OnProcessStart(
            target_action=lifecycle_node,
            on_start=[
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_action(lifecycle_node),
                        transition_id=Transition.TRANSITION_CONFIGURE,
                    )
                ),
            ],
        )
    )

    emit_activate = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=lifecycle_node,
            goal_state="inactive",
            entities=[
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_action(lifecycle_node),
                        transition_id=Transition.TRANSITION_ACTIVATE,
                    )
                ),
            ],
        )
    )

    return LaunchDescription([lifecycle_node, emit_configure, emit_activate])
