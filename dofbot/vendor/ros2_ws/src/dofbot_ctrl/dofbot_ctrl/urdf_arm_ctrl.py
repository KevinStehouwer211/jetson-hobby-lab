#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import math

class JointStatePublisher(Node):
    def __init__(self):
        super().__init__('joint_state_publisher_node')
        self.publisher_ = self.create_publisher(JointState, 'joint_states', 10)
        
        # 10Hz发布频率（必须≥5Hz）
        self.timer_period = 0.1
        self.timer = self.create_timer(self.timer_period, self.timer_callback)
        
        # 核心：和URDF完全一致的关节名（替换为你的实际关节名）
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5']
        
        # 初始化关节角度（弧度）
        self.joint_angles = [0.0] * len(self.joint_names)
        self.angle_increment = 0.01

    def timer_callback(self):
        msg = JointState()
        
        # 关键：有效时间戳
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ''
        print("time: ",self.get_clock().now().to_msg())
        # 关节名（和URDF一致）
        msg.name = self.joint_names       
        # 确保数据长度一致
        msg.position = [0.0, 0.524, -1.57, -1.57, 0.0]
        msg.velocity = [0.0 for _ in msg.name]  # 5个0.0，和name长度匹配
        msg.effort = [0.0 for _ in msg.name]    # 5个0.0，和name长度匹配
        
        self.publisher_.publish(msg)
        # 调试：打印发布的关节角度，确认数据正常
        #self.get_logger().info(f"Published joint angles: {self.joint_angles}")
        '''self.get_logger().info(
            f"字段长度：name={len(msg.name)} | position={len(msg.position)} | velocity={len(msg.velocity)} | effort={len(msg.effort)}",
            throttle_duration_sec=1
        )'''

def main(args=None):
    rclpy.init(args=args)
    node = JointStatePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()