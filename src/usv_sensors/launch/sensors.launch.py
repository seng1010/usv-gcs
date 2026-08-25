"""B1 보드 launch 파일 — water_quality_node + gps_driver_node + camera_node + current_sensor_node.

카메라 장치 번호는 매번 명령줄로 넘기지 않고 config/sensors_params.yaml에서 읽는다.
B1 담당자는 그 파일의 surface_device/underwater_device 값만 실제 번호로 고치면 된다.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    params_file = os.path.join(
        get_package_share_directory('usv_sensors'), 'config', 'sensors_params.yaml'
    )

    return LaunchDescription([
        Node(package='usv_sensors', executable='water_quality_node', name='water_quality_node'),
        Node(package='usv_sensors', executable='gps_driver_node', name='gps_driver_node'),
        Node(package='usv_sensors', executable='current_sensor_node', name='current_sensor_node'),
        Node(
            package='usv_sensors', executable='camera_node', name='camera_node',
            parameters=[params_file],
        ),
    ])
