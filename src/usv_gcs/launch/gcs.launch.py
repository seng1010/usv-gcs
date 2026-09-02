"""GCS(Raspberry Pi) launch 파일 — joy_node + joy_to_cmd_node + rosbridge_websocket
+ 웹 대시보드 정적 파일 서버 + web_video_server.

웹 대시보드(web/index.html + web/script.js, DONGWON21의 usv_gui 이식)는 roslibjs로
rosbridge_websocket(ws://<host>:9090 기본값)에 직접 붙어서 /cmd_vel을 publish하고
/gps/fix, /water_quality를 subscribe한다. 이 launch 파일은 그 rosbridge 서버와,
대시보드 정적 파일을 서빙하는 http.server를 함께 띄운다.

조이스틱 축 번호를 확정한 뒤에는 코드를 고치지 말고 인자로 넘기면 된다:

    ros2 launch usv_gcs gcs.launch.py linear_axis:=1 angular_axis:=0

rosbridge_port를 기본값(9090)에서 바꾸면 web/script.js의 ROSLIB.Ros url도 같이 바꿔야
한다 (웹 페이지는 브라우저에서 JS로 직접 접속하므로 launch 인자가 자동으로 전달되지
않는다). web_video_port도 마찬가지로 web/index.html의 카메라 스트림 주소와 맞춰야 한다.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    web_port_arg = DeclareLaunchArgument(
        'web_port', default_value='8000',
        description='대시보드 정적 파일(web/index.html) 서빙 포트',
    )
    rosbridge_port_arg = DeclareLaunchArgument(
        'rosbridge_port', default_value='9090',
        description='rosbridge_websocket 포트 (web/script.js의 ws 접속 주소와 맞춰야 함)',
    )
    web_video_port_arg = DeclareLaunchArgument(
        'web_video_port', default_value='8080',
        description='web_video_server 포트',
    )
    linear_axis_arg = DeclareLaunchArgument(
        'linear_axis', default_value='1',
        description='조이스틱 전진/후진 축 번호 (GCS 담당자가 실제 조이스틱 기준으로 확정)',
    )
    angular_axis_arg = DeclareLaunchArgument(
        'angular_axis', default_value='0',
        description='조이스틱 좌/우 회전 축 번호',
    )
    linear_scale_arg = DeclareLaunchArgument('linear_scale', default_value='1.0')
    angular_scale_arg = DeclareLaunchArgument('angular_scale', default_value='1.0')
    pump_button_arg = DeclareLaunchArgument(
        'pump_button', default_value='0',
        description='펌프/워터캐논 작동 버튼 번호 (GCS 담당자가 실제 조이스틱 기준으로 확정)',
    )

    web_dir = os.path.join(get_package_share_directory('usv_gcs'), 'web')

    return LaunchDescription([
        web_port_arg,
        rosbridge_port_arg,
        web_video_port_arg,
        linear_axis_arg,
        angular_axis_arg,
        linear_scale_arg,
        angular_scale_arg,
        pump_button_arg,
        Node(package='joy', executable='joy_node', name='joy_node'),
        Node(
            package='usv_gcs', executable='joy_to_cmd_node', name='joy_to_cmd_node',
            parameters=[{
                'linear_axis': ParameterValue(LaunchConfiguration('linear_axis'), value_type=int),
                'angular_axis': ParameterValue(LaunchConfiguration('angular_axis'), value_type=int),
                'linear_scale': ParameterValue(LaunchConfiguration('linear_scale'), value_type=float),
                'angular_scale': ParameterValue(LaunchConfiguration('angular_scale'), value_type=float),
                'pump_button': ParameterValue(LaunchConfiguration('pump_button'), value_type=int),
            }],
        ),
        Node(
            package='rosbridge_server', executable='rosbridge_websocket', name='rosbridge_websocket',
            parameters=[{'port': ParameterValue(LaunchConfiguration('rosbridge_port'), value_type=int)}],
        ),
        Node(
            package='web_video_server', executable='web_video_server', name='web_video_server',
            parameters=[{'port': ParameterValue(LaunchConfiguration('web_video_port'), value_type=int)}],
        ),
        ExecuteProcess(
            cmd=['python3', '-m', 'http.server', LaunchConfiguration('web_port')],
            cwd=web_dir,
            name='dashboard_web_server',
            output='screen',
        ),
    ])
