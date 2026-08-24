"""B2 보드 launch 파일 — thruster_driver_node + actuator_driver_node.

모터 드라이버 PWM 범위를 확정한 뒤에는 코드를 고치지 말고 인자로 넘기면 된다:

    ros2 launch usv_actuators actuators.launch.py max_pwm:=180
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    max_pwm_arg = DeclareLaunchArgument(
        'max_pwm', default_value='255',
        description='추진기 PWM 최대값 (B2 담당자가 실제 모터 드라이버 사양에 맞춰 확정)',
    )

    return LaunchDescription([
        max_pwm_arg,
        Node(
            package='usv_actuators', executable='thruster_driver_node', name='thruster_driver_node',
            parameters=[{'max_pwm': ParameterValue(LaunchConfiguration('max_pwm'), value_type=int)}],
        ),
        Node(package='usv_actuators', executable='actuator_driver_node', name='actuator_driver_node'),
    ])
