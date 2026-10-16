#!/usr/bin/env python3
# encoding: utf-8
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from Arm_Lib import Arm_Device
from dofbot_interface.msg import ArmJoint

class Arm_Ctrl(Node):
    def __init__(self):
        super().__init__('arm_ctrl_node') 
        self.Arm = Arm_Device()
        self.init_joints = [90.0, 120.0, 0.0, 0.0, 90.0, 0.0]
        self.sub_arm_angle = self.create_subscription(ArmJoint,'/TargetAngle',self.GetAngleCallback,1)
        self.sub_beep = self.create_subscription(Bool,'/Beep',self.GetBeepCallback,1) 
        self.Arm.Arm_serial_servo_write6_array(self.init_joints,2000)

    def GetAngleCallback(self,msg):
        arm_joint = ArmJoint()
        
        if len(msg.joints) != 0:
            self.get_logger().info(f"Received joints: {msg.joints}")
            for _ in range(2):
                self.Arm.Arm_serial_servo_write6(
                    msg.joints[0], msg.joints[1], msg.joints[2],
                    msg.joints[3], msg.joints[4], msg.joints[5],
                    time=msg.run_time
                )
        else:
            self.get_logger().info(f"Moving joint {msg.id} to {msg.angle}")
            arm_joint.id = msg.id
            arm_joint.angle = msg.angle
            for _ in range(2):
                self.Arm.Arm_serial_servo_write(msg.id, msg.angle, msg.run_time)

    def GetBeepCallback(self,msg):
        if msg.data == True:
            #蜂鸣器响0.5秒后关闭
            self.Arm.Arm_Buzzer_On(5)
        else:
            self.Arm.Arm_Buzzer_Off()
        
def main(args=None):
    rclpy.init(args=args)
    arm_ctrl = Arm_Ctrl()
    try:    
        rclpy.spin(arm_ctrl)
    except KeyboardInterrupt:
        pass
    finally:
        arm_ctrl.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
        
        
        
        
        
    


