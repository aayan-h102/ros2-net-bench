"""Rover side: echoes every probe straight back to the base station."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt8MultiArray

from net_bench.ros_common import ACK_TOPIC, PROBE_TOPIC, link_qos


class Echo(Node):
    def __init__(self):
        super().__init__("net_bench_echo")
        qos = link_qos()
        self.pub = self.create_publisher(UInt8MultiArray, ACK_TOPIC, qos)
        self.create_subscription(UInt8MultiArray, PROBE_TOPIC, self.pub.publish, qos)
        self.get_logger().info("Echo node ready")


def main():
    rclpy.init()
    node = Echo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
