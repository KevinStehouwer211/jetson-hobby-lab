import rclpy
from rclpy.node import Node
from dofbot_interface.srv import Kinemarics
from Arm_Lib import Arm_Device
import time

class GraspNode(Node):
    def __init__(self):   
        super().__init__('grap')
        self.Arm = Arm_Device()
        self.client = self.create_client(Kinemarics, 'dofbot_kinemarics')
        self.done = False
        self.grap_joint = 140.0
        
        
    def grasp_xy(self,pos_x,pos_y,cls):
        print(cls)
        request = Kinemarics.Request()
        request.tar_x = pos_x 
        request.tar_y = pos_y - 0.02
        request.tar_z = 0.06
        request.kin_name = "ik"
        request.pitch = 1.04
        try:
            future = self.client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0) 
            response = future.result()
            print("calcutelate_response: ",response)
            joints = [0.0, 0.0, 0.0, 0.0, 0.0,0.0]
            joints[0] = response.joint1 #response.joint1
            joints[1] = 180 - response.joint2 
            joints[2] = 180 - response.joint3  
            joints[3] = 180 - response.joint4 
            joints[4] = 90
            joints[5] = 30
            self.Arm.Arm_serial_servo_write6(joints[0],joints[1],joints[2],joints[3],90,joints[5],2000)
            time.sleep(2.0)
            self.Arm.Arm_serial_servo_write(6, 140, 2000)        
            time.sleep(2.0)
            self.Arm.Arm_serial_servo_write(2, 120, 2000)        
            time.sleep(2.0)
            self.Arm.Arm_serial_servo_write(5, 270, 2000)        
            time.sleep(2.0)
            grasp_joints = [90.0, 120.0, 0.0, 0.0, 270.0, 140.0]
            self.Arm.Arm_serial_servo_write6_array(grasp_joints,2000)
            time.sleep(2.0)
            if cls == 1:
                down_joints = [44.0, 66.0, 20.0, 28.0, 270.0, self.grap_joint]
                self.Arm.Arm_serial_servo_write6_array(down_joints,2000)
            elif cls == 2:
                down_joints = [117.0, 19.0, 66.0, 56.0, 270.0, self.grap_joint]
                self.Arm.Arm_serial_servo_write6_array(down_joints,2000)     
            elif cls == 3:
                down_joints = [136.0, 66.0, 20.0, 29.0, 270.0, self.grap_joint]
                self.Arm.Arm_serial_servo_write6_array(down_joints,2000) 
            elif cls == 4:
                down_joints = [65.0, 22.0, 64.0, 56.0, 270.0, self.grap_joint]
                self.Arm.Arm_serial_servo_write6_array(down_joints,2000) 
                
            time.sleep(2.0)
            self.Arm.Arm_serial_servo_write(6, 30, 2000) 
            time.sleep(2.0)
            
        except Exception:
           pass
   
        

    
    