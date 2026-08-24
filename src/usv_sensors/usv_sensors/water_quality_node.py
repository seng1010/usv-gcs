"""water_quality_node — usv_sensors 패키지 (B1 보드).

발행 토픽: /water_quality/data [std_msgs/msg/String] 단 하나.
MCU가 계산해서 넘겨주는 JSON({"temp_c":..., "ph":..., "do_mg_l":...,
"turbidity_voltage_v":..., "clarity_pct":..., "clarity_level":...})을 그대로
중계한다. 개별 필드별 Float32 토픽은 이 프로젝트의 인터페이스 계약(README.md 1항)에
없으므로 만들지 않는다.
"""

import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from .bridge import Bridge


class WaterQualityNode(Node):

    def __init__(self):
        super().__init__('water_quality_node')

        self.data_pub = self.create_publisher(String, '/water_quality/data', 10)

        self.timer = self.create_timer(1.0, self.read_water_quality)
        self.get_logger().info('Water quality node started')

    def read_water_quality(self):
        try:
            raw = Bridge.call('get_water_quality')
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            data = json.loads(str(raw))
        except Exception as error:
            self.get_logger().warning(f'Bridge error: {error}')
            return

        msg = String()
        msg.data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        self.data_pub.publish(msg)

        self.get_logger().info(
            f"T={data.get('temp_c')} pH={data.get('ph')} "
            f"DO={data.get('do_mg_l')} clarity={data.get('clarity_pct')}"
        )


def main(args=None):
    rclpy.init(args=args)
    node = WaterQualityNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
