# !/usr/bin/env python
# coding: utf-8
import cv2
import numpy as np
import random
import time
from Arm_Lib import Arm_Device
import threading


from GestureRecognition import handDetector


class gesture_action:
    def __init__(self):
        '''
        初始化一些参数
        '''
        self.Arm = Arm_Device()
        self.hand_detector = handDetector(detectorCon=0.75)
        self.color_name = None
        self.image = None

        self.look_at = [90, 164, 18, 0, 90, 90]
        self.p_action_1 = [90, 90, 90, 90, 90, 180]
        self.p_action_2 = [90, 90, 0, 180, 90, 180]
        self.p_action_3 = [90, 131, 52, 0, 90, 180]
        self.p_action_4 = [90, 0, 180, 20, 90, 30]
        self.p_action_5 = [90, 0, 90, 180, 90, 0]

        self.g_state_arm = 0
        self.started = 0
        self.running = 0

        self.filter_count = 5
        self.Count_One = 0
        self.Count_Two = 0
        self.Count_Three = 0
        self.Count_Four = 0
        self.Count_Five = 0


    def ctrl_arm_move(self, gesture):
        if gesture == 'One':
            self.Arm.Arm_serial_servo_write6_array(self.p_action_1, 1000)
            time.sleep(1.5)
            self.Arm.Arm_serial_servo_write6_array(self.look_at, 1000)
            time.sleep(1)
        elif gesture == 'Two':
            self.Arm.Arm_serial_servo_write6_array(self.p_action_2, 1000)
            time.sleep(1.5)
            for i in range(5):
                self.Arm.Arm_serial_servo_write(6, 180, 100)
                time.sleep(0.15)
                self.Arm.Arm_serial_servo_write(6, 30, 100)
                time.sleep(0.15)
            self.Arm.Arm_serial_servo_write6_array(self.look_at, 1000)
            time.sleep(1)
        elif gesture == 'Three':
            for i in range(3):
                self.Arm.Arm_serial_servo_write6_array(self.p_action_3, 1200)
                time.sleep(1.2)
                self.Arm.Arm_serial_servo_write6_array(self.look_at, 1000)
                time.sleep(1)
        elif gesture == 'Four':
            self.Arm.Arm_serial_servo_write6_array(self.p_action_4, 1500)
            time.sleep(1.4)
            for i in range(3):
                self.Arm.Arm_serial_servo_write(4, -15, 300)
                time.sleep(0.4)
                self.Arm.Arm_serial_servo_write(4, 20, 300)
                time.sleep(0.4)
            self.Arm.Arm_serial_servo_write6_array(self.look_at, 1000)
            time.sleep(1)
        elif gesture == 'Five':
            for i in range(5):
                self.Arm.Arm_serial_servo_write(5, 60, 300)
                time.sleep(0.4)
                self.Arm.Arm_serial_servo_write(5, 120, 300)
                time.sleep(0.4)
            self.Arm.Arm_serial_servo_write(5, 90, 300)
            time.sleep(0.4)
            self.Arm.Arm_serial_servo_write6_array(self.look_at, 1000)
            time.sleep(1)
        self.g_state_arm = 0

    def start_move_arm(self, gesture):
        # 开启机械臂控制线程
        if self.g_state_arm == 0:
            self.g_state_arm = 1
            closeTid = threading.Thread(target = self.ctrl_arm_move, args = [gesture])
            closeTid.setDaemon(True)
            closeTid.start()



    def bgr8_to_jpeg(self, value, quality=75):
        return bytes(cv2.imencode('.jpg', value)[1])

    
    def reset_state(self):
        self.started = 0

    def start_gesture(self, frame):
        '''
        手势识别函数
        :param img: 输入图像
        :return: 输出处理后的图像和识别结果
        '''
        if self.started == 0:
            self.Arm.Arm_serial_servo_write6_array(self.look_at, 1000)
            time.sleep(1.2)

            self.Arm.Arm_Buzzer_On(1)
            s_time = 300
            self.Arm.Arm_serial_servo_write(4, 10, s_time)
            time.sleep(s_time/1000)
            self.Arm.Arm_serial_servo_write(4, 0, s_time)
            time.sleep(s_time/1000)
            self.Arm.Arm_serial_servo_write(4, 10, s_time)
            time.sleep(s_time/1000)
            self.Arm.Arm_serial_servo_write(4, 0, s_time)
            time.sleep(s_time/1000)
            self.started = 1

        frame, lmList = self.hand_detector.findHands(frame, draw=False)
        if len(lmList) != 0:
            res = self.hand_detector.get_gesture()
            # print('识别结果：' + res)
            if res == 'One': # 1 
                self.Count_One = self.Count_One + 1
                
                self.Count_Two = 0
                self.Count_Three = 0
                self.Count_Four = 0
                self.Count_Five = 0
                self.image = cv2.putText(frame, res, (450, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 2)
                
                if self.Count_One >= self.filter_count:
                    print('识别结果：' + res)
                    self.Count_One = 0
                    self.start_move_arm(res)
            elif res == 'Two': # 2 
                self.Count_Two = self.Count_Two + 1
    
                self.Count_One = 0
                self.Count_Three = 0
                self.Count_Four = 0
                self.Count_Five = 0
                self.image = cv2.putText(frame, res, (450, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 2)

                if self.Count_Two >= self.filter_count: 
                    print('识别结果：' + res)
                    self.Count_Two = 0
                    self.start_move_arm(res)
            elif res == 'Three': # 3 
                self.Count_Three = self.Count_Three + 1
   
                self.Count_One = 0
                self.Count_Two = 0
                self.Count_Four = 0
                self.Count_Five = 0
                self.image = cv2.putText(frame, res, (450, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 2)

                if self.Count_Three >= self.filter_count:
                    print('识别结果：' + res)
                    self.Count_Three = 0
                    self.start_move_arm(res)
            elif res == 'Four': # 4 
                self.Count_Four = self.Count_Four + 1
                
                self.Count_One = 0
                self.Count_Two = 0
                self.Count_Three = 0
                self.Count_Five = 0
                self.image = cv2.putText(frame, res, (450, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 2)

                if self.Count_Four >= self.filter_count:
                    print('识别结果：' + res)
                    self.Count_Four = 0
                    self.start_move_arm(res)
            elif res == 'Five': # 5
                self.Count_Five = self.Count_Five + 1

                self.Count_One = 0
                self.Count_Two = 0
                self.Count_Three = 0
                self.Count_Four = 0
                self.image = cv2.putText(frame, res, (450, 50),
                                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 2)

                if self.Count_Five >= self.filter_count:
                    print('识别结果：' + res)
                    self.Count_Five = 0
                    self.start_move_arm(res)
            else:
                self.image = frame
                res = ''
        else:
            self.image = frame
            res = ''
        return self.image, res

