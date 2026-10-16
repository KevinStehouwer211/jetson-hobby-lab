# !/usr/bin/env python
# coding: utf-8
import math
import threading
import Arm_Lib
from time import sleep
from snake_move import snake_move
from dofbot_interface.srv import Kinemarics
from rclpy.node import Node
import rclpy

if not rclpy.ok():
    rclpy.init()

class snake_ctrl(Node):
    def __init__(self):
        super().__init__('identify')
        '''
        Initialize some parameters
        '''
        self.sbus = Arm_Lib.Arm_Device()
        self.arm_move = snake_move()
        self.color_name = None
        self.image = None
        self.cur_joint = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.Posture = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.move_time = 500

        self.grap_status = 'Waiting'
        # Angle of servo when clip close
        self.grap_joint = 145
        self.num = 1
        self.move_num = 1


        self.client = self.create_client(Kinemarics, 'dofbot_kinemarics')

    def read_joint(self):
        '''
        Read current angle of the servo in loop
        '''
        num = 0
        for i in range(1, 6):
            while 1:
                self.get_logger().info(f"i:{i}")
                joint_bk = self.sbus.Arm_serial_servo_read(i)
                self.get_logger().info(f"joint_bk:{joint_bk}")
                if joint_bk == None:
                    joint_bk = 0.0
                joint = joint_bk*1.0
                self.get_logger().info(f"jointt:{joint}")
                # if num % 10 == 0: print("Please check!Poor contact!")
                if joint_bk == None:
                    joint = 0.0
                if joint != None:
                    self.cur_joint[i - 1] = joint
                    break
                num += 1

        # print("current angle of the servo: {}".format(cur_joint))

    def get_Posture(self):
        '''
        Obtain angle of servo
        '''
        self.read_joint()
        self.get_logger().info("000000000000")
        self.client.wait_for_service()
        self.get_logger().info("1111111")
        self.get_logger().info(f"self.cur_joint:{self.cur_joint}")
        request = Kinemarics.Request()
        self.get_logger().info("2222222")
        request.kin_name = "fk"
        request.cur_joint1 = 180 - self.cur_joint[0]
        request.cur_joint2 = 180 - self.cur_joint[1]
        request.cur_joint3 = 180 - self.cur_joint[2]
        request.cur_joint4 = 180 - self.cur_joint[3]
        request.cur_joint5 = 180 - self.cur_joint[4]
        self.get_logger().info("555555555555555")
        
        try:
            future = self.client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0) 
            response = future.result()
            self.get_logger().info(f"response:{response}")
            self.get_logger().info(f"pos_response:{response}")
            self.Posture[0] = response.x
            self.Posture[1] = response.y
            self.Posture[2] = response.z
            self.Posture[3] = response.Roll
            self.Posture[4] = response.Pitch
            self.Posture[5] = response.Yaw
        except Exception:
            self.get_logger().info("333333333333")

    def joints_limit(self, joints):
        self.get_logger().info('```````````````````````````````````````````````')
        request = Kinemarics.Request()
        request.cur_joint1 = 180 - joints[0]
        request.cur_joint2 = 180 - joints[1]
        request.cur_joint3 = 180 - joints[2]
        request.cur_joint4 = 180 - joints[3]
        request.cur_joint5 = 180 - joints[4]
        request.kin_name = "fk"
        try:
            future = self.client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0) 
            response = future.result()
            #self.get_logger().info(f"joints_response:{response}")
            self.get_logger().info('------------')
            self.get_logger().info(f"joints_response:{response}")
            if 0.20 < response.z  and response.x > 0.0:
                move_joint1 = [90, joints[1], joints[2], joints[3], 0, 180]
                move_joint2 = [90, joints[1], joints[2], joints[3], 0, 30]
                if self.move_num == 1:
                    self.sbus.Arm_serial_servo_write6_array(move_joint1, self.move_time)
                    self.move_num = 2
                if self.move_num == 2:
                    self.sbus.Arm_serial_servo_write6_array(move_joint2, self.move_time)
                    self.move_num = 1
        except Exception:
            self.get_logger().info("joints_limit error")

    def snake_run(self, point_y):
        '''
        Obtain angle of servo
        '''
        self.get_logger().info('+++++++++++++++++++++++')
        request = Kinemarics.Request()
        request.tar_x = point_y
        request.tar_y = 0.0
        request.tar_z = 0.225476
        request.pitch = 0.0
        request.kin_name = "ik"
        try:
            future = self.client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0) 
            response = future.result()
            self.get_logger().info('//////////////////////////////////////////////')
            self.get_logger().info(f"response:{response}")
            joints = [0.0, 0.0, 0.0, 0.0, 0.0]
            joints[0] = 90.0
            joints[1] =  180 - response.joint2
            joints[2] = 180 - response.joint3
            joints[3] = 180 - response.joint4
            joints[4] = 180 - response.joint5
            self.joints_limit(joints)
            
            self.get_logger().info('**********************************')
        except Exception:
            print("snake_run error")

    def snake_main(self, name, msg):
        self.get_Posture()
        self.get_logger().info(f"name:{name}")
        for key, area in msg.items():
            if key == name:

                distance = 27.05 * math.pow(area, -0.51) - 0.2
                
                self.get_logger().info(f"distancee:{distance}")
                target_dist = distance + self.Posture[0]
                self.get_logger().info(f"target_dist:{target_dist}")
                if self.grap_status == 'Waiting':
                    threading.Thread(target=self.snake_run, args=(target_dist,)).start()
                    if self.Posture[0] <= 0.02:
                        # DOFBOT shakes head
                        self.sbus.Arm_serial_servo_write(5,180,300)
                        sleep(0.1)
                        self.sbus.Arm_serial_servo_write(5,0, 300)
                        sleep(0.1)
                        self.num = 1
                        self.get_logger().info('**********************************')
                    elif self.Posture[0] >= 0.18:
                        # Open and close clip
                        self.sbus.Arm_serial_servo_write(6, 30, 100)
                        sleep(0.08)  
                        self.sbus.Arm_serial_servo_write(6, 180, 100)
                        sleep(0.08)
                        self.num += 1
                        self.get_logger().info('0.0.0.0.0.0.0.0..0*')
                    else:  
                        # Open and close clip
                        self.sbus.Arm_serial_servo_write(6, 30, 100)
                        sleep(0.08)
                        self.sbus.Arm_serial_servo_write(6, 180, 100)
                        sleep(0.08)
                        self.num = 1
                        self.get_logger().info('1.1.1.1.1.1.1.1.1.1.1.1.1')
                    self.get_logger().info(f"self.num:{self.num}")
                    if self.num % 5 == 0: self.grap_status = 'Graping'
                elif self.grap_status == 'Graping':
                    self.grap_status = 'Runing'

                    self.arm_move.snake_run(name)

                    self.num = 1

                    self.grap_status = 'Waiting'
            else:
                if self.grap_status == 'Waiting':
                    # DOFBOT shakes head
                    self.sbus.Arm_serial_servo_write(5,180,300)
                    sleep(0.1)
                    self.sbus.Arm_serial_servo_write(5,0, 300)
                    sleep(0.1)
                    if self.Posture[1] > 0.01:
                        joint_1 = [90, 156, 16, 8, 0, 180]
                        self.sbus.Arm_serial_servo_write6_array(joint_1, self.move_time)
