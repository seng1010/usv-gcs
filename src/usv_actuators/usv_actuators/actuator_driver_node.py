"""actuator_driver_node — usv_actuators 패키지 (B2 보드).

구독:
  /actuator/pump_cmd [std_msgs/msg/Bool]       분수 펌프 on/off
  /actuator/led_cmd   [std_msgs/msg/ColorRGBA] RGB LED 색상 (0.0~1.0 범위, PWM 밝기 조절)
발행:
  /battery/actuator [std_msgs/msg/Int32] (제어 배터리 잔량 %, 1개)

주의: 여기서 말하는 LED는 B2 보드에 물리적으로 배선된, 분수 펌프 옆의 별도 RGB LED
조명이다. `gps_and_water_quality_and_ros`(app_utils/leds.py)에 있는 UNO Q 보드 자체의
내장 상태표시 LED(Leds 클래스)와는 다른 하드웨어다 — 그쪽은 on/off만 되는 sysfs 제어라
ColorRGBA의 연속값(PWM)을 표현할 수 없어서 재사용하지 않았다.

TODO(하드웨어 확정 필요): 펌프 릴레이/LED 드라이버 배선과 배터리 ADC 환산식이
아직 없어서 MCU RPC 메서드 이름(set_pump, set_actuator_led, get_actuator_battery)은
임시로 정한 것이다. Arduino 스케치 쪽에 해당 RPC 핸들러를 구현해야 실제로 동작한다.
"""

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool
from std_msgs.msg import ColorRGBA
from std_msgs.msg import Int32

from .bridge import Bridge
from .telemetry import bounded_integer


class ActuatorDriverNode(Node):

    def __init__(self):
        super().__init__('actuator_driver_node')

        self.battery_pub = self.create_publisher(Int32, '/battery/actuator', 10)

        self.pump_sub = self.create_subscription(Bool, '/actuator/pump_cmd', self.on_pump_cmd, 10)
        self.led_sub = self.create_subscription(ColorRGBA, '/actuator/led_cmd', self.on_led_cmd, 10)

        self.battery_timer = self.create_timer(1.0, self.read_battery)
        self.get_logger().info('Actuator driver node started')

    def on_pump_cmd(self, msg: Bool):
        try:
            # TODO(B2 담당자): 'set_pump'은 임시 RPC 이름. 실제 릴레이 제어 스케치의
            # 핸들러 이름에 맞춰 확인·수정할 것.
            Bridge.notify('set_pump', bool(msg.data))
        except Exception as error:
            self.get_logger().warning(f'Pump Bridge error: {error}')

    def on_led_cmd(self, msg: ColorRGBA):
        r = bounded_integer(round(msg.r * 255), 0, 255)
        g = bounded_integer(round(msg.g * 255), 0, 255)
        b = bounded_integer(round(msg.b * 255), 0, 255)

        try:
            # TODO(B2 담당자): 'set_actuator_led'는 임시 RPC 이름. 실제 LED 드라이버
            # 배선(공통 애노드/캐소드 등)에 따라 값 반전이 필요할 수 있음.
            Bridge.notify('set_actuator_led', r, g, b)
        except Exception as error:
            self.get_logger().warning(f'LED Bridge error: {error}')

    def read_battery(self):
        try:
            # TODO(B2 담당자): 'get_actuator_battery'는 임시 RPC 이름이고, MCU가 이미
            # 0~100% 값을 준다고 가정했다. 실제로 전압(V)을 준다면 여기서 환산식을 추가할 것.
            raw = Bridge.call('get_actuator_battery')
        except Exception as error:
            self.get_logger().warning(f'Battery Bridge error: {error}')
            return

        msg = Int32()
        msg.data = bounded_integer(raw, 0, 100)
        self.battery_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ActuatorDriverNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
