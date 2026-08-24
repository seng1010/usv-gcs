"""joy_to_cmd_node — usv_gcs 패키지 (Raspberry Pi).

구독: /joy       [sensor_msgs/msg/Joy]
발행: /cmd_vel   [geometry_msgs/msg/Twist]  (USV Wi-Fi 경유 + gui_main_node 내부 양쪽이 구독)

축 번호(linear_axis/angular_axis)는 조이스틱 기종마다 달라서 ROS 파라미터로 뺐다.
실제 조이스틱이 정해지면 `ros2 topic echo /joy`로 축 번호를 확인해서 launch 파일에서
지정해야 한다 (기본값 1, 0은 흔한 게임패드 레이아웃 기준 임시값).
"""

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy


class JoyToCmdNode(Node):

    def __init__(self):
        super().__init__('joy_to_cmd_node')

        # TODO(GCS 담당자): 아래 기본값은 흔한 게임패드 레이아웃 기준 추정치.
        # `ros2 topic echo /joy`로 실제 조이스틱의 축 번호를 확인해서
        # launch 파일의 linear_axis/angular_axis 인자로 넘길 것.
        self.declare_parameter('linear_axis', 1)
        self.declare_parameter('angular_axis', 0)
        self.declare_parameter('linear_scale', 1.0)
        self.declare_parameter('angular_scale', 1.0)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.joy_sub = self.create_subscription(Joy, '/joy', self.on_joy, 10)

        self.get_logger().info('Joy to cmd node started')

    def on_joy(self, msg: Joy):
        linear_axis = self.get_parameter('linear_axis').value
        angular_axis = self.get_parameter('angular_axis').value
        linear_scale = self.get_parameter('linear_scale').value
        angular_scale = self.get_parameter('angular_scale').value

        if linear_axis >= len(msg.axes) or angular_axis >= len(msg.axes):
            return

        twist = Twist()
        twist.linear.x = msg.axes[linear_axis] * linear_scale
        twist.angular.z = msg.axes[angular_axis] * angular_scale
        self.cmd_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = JoyToCmdNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
