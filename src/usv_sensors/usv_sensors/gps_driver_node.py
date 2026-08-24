"""gps_driver_node — usv_sensors 패키지 (B1 보드).

발행:
  /gps/fix        [sensor_msgs/msg/NavSatFix] 유효한 Fix일 때만 발행
  /gps/has_fix    [std_msgs/msg/Bool]         Fix 유무와 무관하게 매 주기 발행
  /gps/satellites [std_msgs/msg/UInt8]        노드 내부에는 유지, GCS는 미구독 (README.md 0항 참고)
  /gps/status     [std_msgs/msg/String]       노드 내부에는 유지, GCS는 미구독 (README.md 0항 참고)
"""

import json

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import NavSatFix
from sensor_msgs.msg import NavSatStatus
from std_msgs.msg import Bool
from std_msgs.msg import String
from std_msgs.msg import UInt8

from .bridge import Bridge
from .telemetry import bounded_integer
from .telemetry import valid_coordinates


class GpsDriverNode(Node):

    def __init__(self):
        super().__init__('gps_driver_node')

        self.fix_pub = self.create_publisher(NavSatFix, '/gps/fix', 10)
        self.has_fix_pub = self.create_publisher(Bool, '/gps/has_fix', 10)
        self.satellites_pub = self.create_publisher(UInt8, '/gps/satellites', 10)
        self.status_pub = self.create_publisher(String, '/gps/status', 10)

        self.timer = self.create_timer(1.0, self.read_gps)
        self.get_logger().info('GPS driver node started')

    def read_gps(self):
        try:
            raw = Bridge.call('get_gps')
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8')
            data = json.loads(str(raw))
        except Exception as error:
            self.get_logger().warning(f'GPS Bridge error: {error}')
            return

        has_fix = data.get('fix') is True

        fix_state = Bool()
        fix_state.data = has_fix
        self.has_fix_pub.publish(fix_state)

        satellites = UInt8()
        satellites.data = bounded_integer(data.get('satellites'), 0, 255)
        self.satellites_pub.publish(satellites)

        status = String()
        status.data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        self.status_pub.publish(status)

        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if has_fix and valid_coordinates(latitude, longitude):
            message = NavSatFix()
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = 'gps_link'
            message.status.status = NavSatStatus.STATUS_FIX
            message.status.service = NavSatStatus.SERVICE_GPS
            message.latitude = float(latitude)
            message.longitude = float(longitude)
            message.altitude = float('nan')
            message.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN
            self.fix_pub.publish(message)

        self.get_logger().info(f"fix={has_fix} satellites={satellites.data}")


def main(args=None):
    rclpy.init(args=args)
    node = GpsDriverNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
