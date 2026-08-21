from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            output='screen',
        ),
        Node(
            package='usv_gcs',
            executable='joy_to_cmd_node',
            name='joy_to_cmd_node',
            output='screen',
            parameters=[{
                'linear_axis': 1,
                'angular_axis': 0,
                'linear_scale': 1.0,
                'angular_scale': 1.0,
                'deadzone': 0.05,
                'enable_heartbeat': False,
                'heartbeat_period_sec': 0.5,
            }],
        ),
    ])
