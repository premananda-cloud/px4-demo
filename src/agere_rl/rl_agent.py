#!/usr/bin/env python3
"""
Simple RL agent for PX4 drone control
"""
import rclpy
from rclpy.node import Node
from px4_msgs.msg import VehicleAttitude, VehicleLocalPositionV1, TrajectorySetpoint

class RLAgent(Node):
    def __init__(self):
        super().__init__('rl_agent')
        
        # Subscribers for state
        self.attitude_sub = self.create_subscription(
            VehicleAttitude,
            '/fmu/out/vehicle_attitude',
            self.attitude_callback,
            10
        )
        self.position_sub = self.create_subscription(
            VehicleLocalPositionV1,
            '/fmu/out/vehicle_local_position_v1',
            self.position_callback,
            10
        )
        
        # Publisher for actions
        self.setpoint_pub = self.create_publisher(
            TrajectorySetpoint,
            '/fmu/in/trajectory_setpoint',
            10
        )
        
        self.get_logger().info('🤖 RL Agent initialized!')
        self.current_state = {}
    
    def attitude_callback(self, msg):
        self.current_state['attitude'] = msg.q
    
    def position_callback(self, msg):
        self.current_state['position'] = [msg.x, msg.y, msg.z]
        # Send a simple hover command
        self.hover()
    
    def hover(self):
        """Simple hover at current position"""
        if 'position' in self.current_state:
            setpoint = TrajectorySetpoint()
            # Hover at current position
            setpoint.position = [
                self.current_state['position'][0],
                self.current_state['position'][1],
                -2.0  # 2 meters up (NED frame)
            ]
            self.setpoint_pub.publish(setpoint)

def main():
    rclpy.init()
    node = RLAgent()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
