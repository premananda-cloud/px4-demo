#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from px4_msgs.msg import VehicleAttitude

class TestNode(Node):
    def __init__(self):
        super().__init__('test_node')
        self.sub = self.create_subscription(
            VehicleAttitude,
            '/fmu/out/vehicle_attitude',
            self.callback,
            10
        )
        self.get_logger().info('✅ Test node started! Listening to attitude...')
        
    def callback(self, msg):
        self.get_logger().info(f'Roll: {msg.q[0]:.3f}, Pitch: {msg.q[1]:.3f}, Yaw: {msg.q[2]:.3f}')

def main():
    rclpy.init()
    node = TestNode()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
