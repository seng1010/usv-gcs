"""thruster_driver_node — usv_actuators 패키지 (B2 보드).

구독: /cmd_vel [geometry_msgs/msg/Twist] — watchdog_node가 이번 범위에서 제외되어
      /cmd_vel_safe가 아니라 /cmd_vel을 직접 구독한다 (README.md 0항 참고).

배터리 계측 역할은 이 노드에서 삭제되었다. 전류 센서 4개가 전부 B1 보드에 물려있어서
usv_sensors의 current_sensor_node가 /battery/status로 통합 발행한다 (README.md 1항 참고).

TODO(하드웨어 확정 필요): 실제 모터 드라이버 배선과 PWM 매핑이 아직 없어서 MCU RPC
메서드 이름(set_thruster_pwm)은 임시로 정한 것이다. Arduino 스케치 쪽에 해당 RPC
핸들러를 구현해야 실제로 동작한다.
"""

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist

from .bridge import Bridge
from .telemetry import bounded_integer


class ThrusterDriverNode(Node):

    def __init__(self):
        super().__init__('thruster_driver_node')

        self.declare_parameter('max_pwm', 255)

        self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.on_cmd_vel, 10)

        self.get_logger().info('Thruster driver node started')

    def on_cmd_vel(self, msg: Twist):
        max_pwm = self.get_parameter('max_pwm').value

        linear = max(-1.0, min(1.0, msg.linear.x))
        angular = max(-1.0, min(1.0, msg.angular.z))

        left = linear - angular
        right = linear + angular
        scale = max(1.0, abs(left), abs(right))

        left_pwm = bounded_integer(round(left / scale * max_pwm), -max_pwm, max_pwm)
        right_pwm = bounded_integer(round(right / scale * max_pwm), -max_pwm, max_pwm)

        try:
            # TODO(B2 담당자): 'set_thruster_pwm'은 임시 RPC 이름. 실제 Arduino 스케치의
            # 핸들러 이름/인자 순서(left, right)에 맞춰 확인·수정할 것.
            Bridge.notify('set_thruster_pwm', left_pwm, right_pwm)
        except Exception as error:
            self.get_logger().warning(f'Thruster Bridge error: {error}')


def main(args=None):
    rclpy.init(args=args)
    node = ThrusterDriverNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
