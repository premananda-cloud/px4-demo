#!/usr/bin/env python3
"""Quick sanity check that the ROS 2 <-> PX4 uXRCE-DDS bridge is alive."""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from px4_msgs.msg import VehicleAttitude

# Must match PX4's best-effort/volatile publisher QoS or nothing arrives.
PX4_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
)


class TestNode(Node):
    def __init__(self):
        super().__init__('test_node')
        self.sub = self.create_subscription(
            VehicleAttitude,
            '/fmu/out/vehicle_attitude',
            self.callback,
            PX4_QOS,
        )
        self.get_logger().info('Test node started! Listening to attitude...')

    def callback(self, msg):
        self.get_logger().info(f'q: [{msg.q[0]:.3f}, {msg.q[1]:.3f}, {msg.q[2]:.3f}, {msg.q[3]:.3f}]')


def main():
    rclpy.init()
    node = TestNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
