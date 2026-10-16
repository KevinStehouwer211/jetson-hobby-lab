#!/usr/bin/env python
# coding: utf-8
#import rospy
import Arm_Lib
import cv2 as cv
import numpy as np
from time import sleep
from identify_grap import identify_grap
#from dofbot_info.srv import kinemarics, kinemaricsRequest, kinemaricsResponse
from dofbot_interface.srv import Kinemarics
from rclpy.node import Node
import rclpy
if not rclpy.ok():
    rclpy.init()
class identify_GetTarget(Node):
    def __init__(self):
        super().__init__('identify')
        
        self.grap = identify_grap()
        # Robotic arm recognition position adjustment
        # 机械臂识别位置调节
        self.xy = [90, 135]
        # Create a robotic arm instance
        # 创建机械臂实例
        self.arm = Arm_Lib.Arm_Device()
        # 创建用于调用的ROS服务的句柄
        self.client = self.create_client(Kinemarics, 'dofbot_kinemarics')
        self.grasp_status = True
        self.grap_joint = 135

    def select_color(self, image, color_hsv, color_list):
        '''
        Choose a recognition color
        选择识别颜色
        :param image:输入图像  input image
        :param color_hsv: HSV的范围阈值  Range threshold for HSV
        :param color_list: 颜色序列:['0'：无 '1'：红色 '2'：绿色 '3'：蓝色 '4'：黄色]  Color sequence: ['0': None '1': Red '2': Green '3': Blue '4': Yellow]
        :return: 输出处理后的图像,(颜色,位置)  Output the processed image, (color, position)
        '''
        # canonical input image size
        # 规范输入图像大小
        self.image = cv.resize(image, (640, 480))
        msg = {}
        # Get information about the first color sequence
        # 获取第一个颜色序列的信息
        if len(color_list)==0:return self.image,msg
        if '1' in color_list:
            self.color_name=color_list['1']
            pos = self.get_Sqaure(color_hsv[self.color_name])
            if pos != None: msg[self.color_name] = pos
        if '2' in color_list:
            self.color_name=color_list['2']
            pos = self.get_Sqaure(color_hsv[self.color_name])
            if pos != None: msg[self.color_name] = pos
        if '3' in color_list:
            self.color_name=color_list['3']
            pos = self.get_Sqaure(color_hsv[self.color_name])
            if pos != None: msg[self.color_name] = pos
        if '4' in color_list:
            self.color_name=color_list['4']
            pos = self.get_Sqaure(color_hsv[self.color_name])
            if pos != None: msg[self.color_name] = pos
        return self.image, msg


    def get_Sqaure(self, color_hsv):
        '''
        Color recognition, get the coordinates of the square
        颜色识别,获得方块的坐标
        '''
        (lowerb, upperb) = color_hsv
        # Copy the original image to avoid interference during processing
        # 复制原始图像,避免处理过程中干扰
        mask = self.image.copy()
        # Convert image to HSV
        # 将图像转换为HSV
        HSV_img = cv.cvtColor(self.image, cv.COLOR_BGR2HSV)
        # filter out elements between two arrays
        # 筛选出位于两个数组之间的元素
        img = cv.inRange(HSV_img, lowerb, upperb)
        # Set the non-mask detection part to be all black
        # 设置非掩码检测部分全为黑色
        mask[img == 0] = [0, 0, 0]
        # Get structuring elements of different shapes
        # 获取不同形状的结构元素
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (5, 5))
        # morphological closure
        # 形态学闭操作
        dst_img = cv.morphologyEx(mask, cv.MORPH_CLOSE, kernel)
        # Convert image to grayscale
        # 将图像转为灰度图
        dst_img = cv.cvtColor(dst_img, cv.COLOR_RGB2GRAY)
        # Image Binarization Operation
        # 图像二值化操作
        ret, binary = cv.threshold(dst_img, 10, 255, cv.THRESH_BINARY)
        # Get the set of contour points (coordinates)
        # 获取轮廓点集(坐标)
        find_contours = cv.findContours(binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        if len(find_contours) == 3: contours = find_contours[1]
        else: contours = find_contours[0]
        for i, cnt in enumerate(contours):
            x, y, w, h = cv.boundingRect(cnt)
            area = cv.contourArea(cnt)
            if area > 1000:
                point_x = float(x + w / 2)
                point_y = float(y + h / 2)
                cv.rectangle(self.image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv.circle(self.image, (int(point_x), int(point_y)), 5, (0, 0, 255), -1)
                cv.putText(self.image, self.color_name, (int(x - 15), int(y - 15)),
                           cv.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
                # Calculate the position of the block in the image
                # 计算方块在图像中的位置
                (a, b) = (round(((320 - point_x) / 4000), 5), round(((480 - point_y) / 3000) * 0.8+0.19, 5))
                return (a, b)

    def target_run(self, msg, xy=None):
        '''
        grab function 抓取函数
        :param msg: (颜色,位置)  (color, position)
        '''
        self.get_logger().info('0.0.0.0.0.0.0.')	
        if xy != None: self.xy = xy
        move_status=0
        for i in msg.values():
            if i !=None: move_status=1
        if move_status==1:
            self.arm.Arm_Buzzer_On(1)
            sleep(0.5)
        self.get_logger().info(f"msg:{msg}")
        for name, pos in msg.items():
            try:
                self.get_logger().info('1.1')
                joints = self.server_joint(pos)
                self.get_logger().info('2.2')
                self.get_logger().info(f"name:{str(name)}")
                self.get_logger().info(f"joints:{joints}")
                if str(name) == "red" and self.grasp_status == True:
                    self.get_logger().info('red')
                    self.grasp_status = False
                    joints = [joints[0], joints[1], joints[2], joints[3], 265, 30]
                    joints_down = [45, 50, 20, 60, 265, self.grap_joint]
                    self.move(joints, joints_down)
                    self.grasp_status = True
                elif str(name) == "blue" and self.grasp_status == True:
                    self.get_logger().info('blue')
                    self.grasp_status = False
                    joints = [joints[0], joints[1], joints[2], joints[3], 265, 30]
                    joints_down = [27, 75, 0, 50, 265, self.grap_joint]
                    self.move(joints, joints_down)
                    self.grasp_status = True
                elif str(name) == "green" and self.grasp_status == True:
                    self.get_logger().info('green')
                    self.grasp_status = False
                    joints = [joints[0], joints[1], joints[2], joints[3], 265, 30]
                    joints_down = [152, 75, 0, 50, 265, self.grap_joint]
                    self.move(joints, joints_down)
                    self.grasp_status = True
                elif str(name) == "yellow" and self.grasp_status == True:
                    self.get_logger().info('yellow')
                    self.grasp_status = False
                    joints = [joints[0], joints[1], joints[2], joints[3], 265, 30]
                    joints_down = [137, 50, 20, 60, 265, self.grap_joint]
                    self.move(joints, joints_down)
                    self.grasp_status = True
                    
                self.get_logger().info('3.3')
            except Exception: self.get_logger().info('011111111111111')
        if move_status==1:
            # set up
            # 架起
            joints_uu = [90, 80, 50, 50, 265, 30]
            # Move over the object's position
            # 移动至物体位置上方
            self.arm.Arm_serial_servo_write6_array(joints_uu, 1000)
            sleep(1)
            # initial position
            # 初始位置
            joints_0 = [self.xy[0], self.xy[1], 0, 0, 90, 30]
            # move to initial position
            # 移动至初始位置
            self.arm.Arm_serial_servo_write6_array(joints_0, 500)
            sleep(0.5)


    def server_joint(self, posxy):
        '''
        Post position request, get joint rotation angle
        发布位置请求,获取关节旋转角度
        :param posxy: 位置点x,y坐标 Location point x,y coordinates
        :return: 每个关节旋转角度    Rotation angle of each joint
        '''
        # Wait for the server to start
        # 等待server端启动
        self.client.wait_for_service()
        # Create a message pack
        # 创建消息包
        request = Kinemarics.Request()
        request.tar_x = posxy[1] - 0.03
        request.tar_y = posxy[0] - 0.01
        request.tar_z = 0.04
        request.kin_name = "ik"
        request.pitch = 1.04
        print("request: ",request)
        self.get_logger().info(f"request:{request}")
        try:
            future = self.client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0) 
            response = future.result()
            self.get_logger().info(f"response:{response}")
            joints = [0.0, 0.0, 0.0, 0.0, 0.0]
            joints[0] = response.joint1
            joints[1] = 180 - response.joint2
            joints[2] = 180 - response.joint3
            joints[3] = 180 - response.joint4
            joints[4] = 180 - response.joint5
            # When the inverse solution is out of bounds and a negative value appears, adjust it appropriately.
            # 当逆解越界,出现负值时,适当调节.
            if joints[2] < 0:
                joints[1] += joints[2] * 3 / 5
                joints[3] += joints[2] * 3 / 5
                joints[2] = 0
            self.get_logger().info(f"joints:{joints}")
            return joints
        except Exception:
            print("Error!")
            
    def move(self, joints, joints_down):
        '''
        Moving process
        移动过程
        :param joints: 移动到物体位置的各关节角度   The angle of each joint moved to the position of the object
        :param joints_up: 机械臂抬起各关节角度     The manipulator raises the angle of each joint
        :param color_angle: 移动到对应垃圾桶的角度  Move to the angle of the corresponding trash can
        '''
        self.get_logger().info('5.5')
        joints_uu = [90, 80, 50, 50, 265, self.grap_joint]
        # raise 抬起
        joints_up = [joints_down[0], 80, 50, 50, 265, 30]
        # put up 架起
        self.arm.Arm_serial_servo_write6_array(joints_uu, 1500)
        sleep(1.5)
        self.get_logger().info('6.6')
        # Opening and closing jaws 开合夹爪
        for i in range(5):
            self.arm.Arm_serial_servo_write(6, 180, 100)
            sleep(0.08)
            self.arm.Arm_serial_servo_write(6, 30, 100)
            sleep(0.08)
        # Release clamping jaws 松开夹爪
        # self.arm.Arm_serial_servo_write(6, 0, 500)
        # sleep(0.5)
        # Move to object position 移动至物体位置
        self.arm.Arm_serial_servo_write6_array(joints, 500)
        sleep(0.5)
        # Grasp and clamp the clamping claw进行抓取,夹紧夹爪
        self.arm.Arm_serial_servo_write(6, self.grap_joint, 500)
        sleep(0.5)
        # put up 架起
        self.arm.Arm_serial_servo_write6_array(joints_uu, 1000)
        sleep(1)
        # Lift to above the corresponding position 抬起至对应位置上方
        self.arm.Arm_serial_servo_write(1, joints_down[0], 500)
        sleep(0.5)
        # Move to target location 移动至目标位置
        self.arm.Arm_serial_servo_write6_array(joints_down, 1000)
        sleep(1)
        # Release the object and release the clamping jaws释放物体,松开夹爪
        self.arm.Arm_serial_servo_write(6, 30, 500)
        sleep(0.5)
        # raise  抬起
        self.arm.Arm_serial_servo_write6_array(joints_up, 1000)
        sleep(1)