#!/usr/bin/env python3
"""
Minimal PX4 offboard-control agent.

This node does the wiring PX4 requires before it will accept any commands:
publishes the OffboardControlMode heartbeat, arms the vehicle, and switches
it into Offboard mode. It currently just holds a hover setpoint -- this is
the seam an RL policy plugs into: read self.current_state inside
publish_setpoint() and publish a policy action instead of the fixed hover.
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from px4_msgs.msg import (
    VehicleAttitude,
    VehicleLocalPosition,
    TrajectorySetpoint,
    OffboardControlMode,
    VehicleCommand,
)

# PX4 publishes all /fmu/out/* topics as best-effort/volatile. A ROS 2
# subscriber using the default (reliable) QoS is incompatible and will
# silently receive nothing, so this must match.
PX4_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
)

# PX4 needs to see a stream of OffboardControlMode + setpoint messages
# before it will accept the switch into Offboard mode.
OFFBOARD_ENGAGE_AFTER = 10


class RLAgent(Node):
    def __init__(self):
        super().__init__('rl_agent')

        # --- State subscriptions (PX4 -> ROS 2) ---
        self.attitude_sub = self.create_subscription(
            VehicleAttitude, '/fmu/out/vehicle_attitude', self.attitude_callback, PX4_QOS)
        self.position_sub = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position', self.position_callback, PX4_QOS)

        # --- Command publishers (ROS 2 -> PX4) ---
        self.offboard_mode_pub = self.create_publisher(
            OffboardControlMode, '/fmu/in/offboard_control_mode', PX4_QOS)
        self.setpoint_pub = self.create_publisher(
            TrajectorySetpoint, '/fmu/in/trajectory_setpoint', PX4_QOS)
        self.command_pub = self.create_publisher(
            VehicleCommand, '/fmu/in/vehicle_command', PX4_QOS)

        self.current_state = {}
        self.offboard_setpoint_counter = 0
        self.hover_altitude = -2.0  # NED frame: negative = up

        # 10 Hz loop. OffboardControlMode must be published continuously
        # (>2 Hz) or PX4 will drop out of Offboard mode.
        self.timer = self.create_timer(0.1, self.control_loop)

        self.get_logger().info('RL Agent initialized')

    def attitude_callback(self, msg):
        self.current_state['attitude'] = msg.q

    def position_callback(self, msg):
        self.current_state['position'] = [msg.x, msg.y, msg.z]

    def control_loop(self):
        self.publish_offboard_heartbeat()
        self.publish_setpoint()

        # Once PX4 has seen a stream of setpoints, request the mode switch and arm.
        if self.offboard_setpoint_counter == OFFBOARD_ENGAGE_AFTER:
            self.engage_offboard_mode()
            self.arm()

        if self.offboard_setpoint_counter < OFFBOARD_ENGAGE_AFTER + 1:
            self.offboard_setpoint_counter += 1

    def publish_offboard_heartbeat(self):
        msg = OffboardControlMode()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_mode_pub.publish(msg)

    def publish_setpoint(self):
        """Hover at a fixed altitude above wherever the vehicle currently is.
        Replace this body with the RL policy's action once state is flowing."""
        msg = TrajectorySetpoint()
        if 'position' in self.current_state:
            msg.position = [
                self.current_state['position'][0],
                self.current_state['position'][1],
                self.hover_altitude,
            ]
        else:
            msg.position = [0.0, 0.0, self.hover_altitude]
        msg.yaw = 0.0
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.setpoint_pub.publish(msg)

    def arm(self):
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
        self.get_logger().info('Arm command sent')

    def engage_offboard_mode(self):
        # param1=1 (custom mode enabled), param2=6 (PX4_CUSTOM_MAIN_MODE_OFFBOARD)
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, param1=1.0, param2=6.0)
        self.get_logger().info('Offboard mode requested')

    def publish_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.param1 = param1
        msg.param2 = param2
        msg.command = command
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.command_pub.publish(msg)


def main():
    rclpy.init()
    node = RLAgent()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
