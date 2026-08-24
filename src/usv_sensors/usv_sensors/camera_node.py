"""camera_node — usv_sensors 패키지 (B1 보드), 듀얼 USB 카메라.

발행:
  /camera/surface/image_raw     [sensor_msgs/msg/Image]
  /camera/underwater/image_raw  [sensor_msgs/msg/Image]

카메라 장치 인덱스는 ROS 파라미터(surface_device, underwater_device)로 조정한다.
기본값(아래 declare_parameter)은 코드가 직접 참조하는 값이 아니라 파라미터가 아예
안 넘어왔을 때만 쓰이는 안전장치다. 실제로는 config/sensors_params.yaml에 적힌 값을
sensors.launch.py가 읽어서 넘겨주므로, 장치 번호를 바꿀 땐 그 YAML 파일만 고치면 된다.
"""

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class CameraNode(Node):

    def __init__(self):
        super().__init__('camera_node')

        # TODO(B1 담당자): 실제 값은 여기가 아니라 config/sensors_params.yaml에서
        # 관리한다. `v4l2-ctl --list-devices` 또는 `ls /dev/video*`로 확인한 번호를
        # 그 파일에 적을 것 (아래 기본값은 파라미터가 안 넘어왔을 때의 안전장치일 뿐).
        self.declare_parameter('surface_device', 0)
        self.declare_parameter('underwater_device', 2)
        self.declare_parameter('fps', 15.0)

        surface_device = self.get_parameter('surface_device').value
        underwater_device = self.get_parameter('underwater_device').value
        fps = self.get_parameter('fps').value

        self.bridge = CvBridge()

        self.surface_pub = self.create_publisher(Image, '/camera/surface/image_raw', 10)
        self.underwater_pub = self.create_publisher(Image, '/camera/underwater/image_raw', 10)

        self.surface_cap = cv2.VideoCapture(surface_device)
        self.underwater_cap = cv2.VideoCapture(underwater_device)

        if not self.surface_cap.isOpened():
            self.get_logger().error(f'Cannot open surface camera (device {surface_device})')
        if not self.underwater_cap.isOpened():
            self.get_logger().error(f'Cannot open underwater camera (device {underwater_device})')

        self.timer = self.create_timer(1.0 / fps, self.capture_frames)
        self.get_logger().info('Camera node started')

    def capture_frames(self):
        self._publish_frame(self.surface_cap, self.surface_pub, 'surface_link')
        self._publish_frame(self.underwater_cap, self.underwater_pub, 'underwater_link')

    def _publish_frame(self, cap, publisher, frame_id):
        if not cap.isOpened():
            return

        ok, frame = cap.read()
        if not ok:
            self.get_logger().warning(f'Failed to read frame from {frame_id}')
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = frame_id
        publisher.publish(msg)

    def destroy_node(self):
        self.surface_cap.release()
        self.underwater_cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
