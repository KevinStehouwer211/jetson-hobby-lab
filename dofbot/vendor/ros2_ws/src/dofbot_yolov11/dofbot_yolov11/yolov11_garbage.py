#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rclpy
from rclpy.node import Node
import cv2 
import numpy as np
from sensor_msgs.msg import Image
from std_msgs.msg import  Bool,String
from cv_bridge import CvBridge
import cv2 as cv
import threading
from dofbot_interface.srv import Kinemarics
from dofbot_interface.msg import *
import time
import math
from Arm_Lib import Arm_Device
from ultralytics import YOLO
import os
exit_code = os.system('sudo v4l2-ctl -d /dev/video0 -c brightness=10')
# Load the YOLO model
model = YOLO("/root/ultralytics/ultralytics/best.onnx")

from ament_index_python import get_package_share_directory
import yaml
import os
pkg_path = get_package_share_directory('dofbot_sorting')
offset_file = os.path.join(pkg_path,'config', 'offset.yaml')
with open(offset_file, 'r') as file:
    offset_config = yaml.safe_load(file)
print(offset_config)


class AprilTagDetectNode(Node):
    def __init__(self):
        super().__init__('garbage_detect')
        self.Arm = Arm_Device()
        self.init_joints = [90.0, 120.0, 0.0, 0.0, 90.0, 0.0]
        self.pos_info_pub = self.create_publisher(AprilTagInfo, "PosInfo", qos_profile=10)
        self.subscription = self.create_subscription(Bool,'grasp_done',self.GraspStatusCallback,qos_profile=1)
        self.rgb_bridge = CvBridge()
        self.depth_bridge = CvBridge()
        self.pubPos_flag = False
        self.Arm.Arm_serial_servo_write6_array(self.init_joints,2000)
        self.subscription = self.create_subscription(Image,'/image_raw',self.ImageCallback,1)
        self.recyclable_waste=['Newspaper','Zip_top_can','Book','Old_school_bag']
        self.toxic_waste=['Syringe','Expired_cosmetics','Used_batteries','Expired_tablets']
        self.wet_waste=['Fish_bone','Egg_shell','Apple_core','Watermelon_rind']
        self.dry_waste=['Toilet_paper','Peach_pit','Cigarette_butts','Disposable_chopsticks']
        self.x_offset = offset_config.get('x_offset')
        self.y_offset = offset_config.get('y_offset')

    def ImageCallback(self,color_frame):
        #rgb_image
        rgb_image = self.rgb_bridge.imgmsg_to_cv2(color_frame,'rgb8')
        result_image = np.copy(rgb_image)
        frame = np.copy(rgb_image)
        results = model(frame)
        #print("-------results-----------: ",results[0])
        key = cv2.waitKey(10)
        if key == 32:
            self.pubPos_flag = True        
        boxes = results[0].boxes
        if boxes != [None]:
            for box in boxes:  # detections per image
                x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
                class_id = int(box.cls)
                confidence = float(box.conf)
                label = f"{model.names[class_id]} {confidence:.2f}"
                print("model.names[class_id]: ",model.names[class_id])
                # 计算重心位置
                center_x = (x_min + x_max) // 2
                center_y = (y_min + y_max) // 2
                (a, b) = (round(((320 - center_x) / 4000)+ self.y_offset, 5), round(((480 - center_y) / 3000) * 0.8+0.15 + self.x_offset, 5))
                if self.pubPos_flag == True:
                    self.pubPos_flag = False
                    center = AprilTagInfo()
                    center.x = b
                    center.y = a
                    center.z = 0.03
                    if str(model.names[class_id]) in self.recyclable_waste:
                        center.id = 1
                    elif str(model.names[class_id]) in self.toxic_waste:
                        center.id = 2
                    elif str(model.names[class_id]) in self.wet_waste:
                        center.id = 3
                    elif str(model.names[class_id]) in self.dry_waste:
                        center.id = 4
                    print("center: ",center)
                    self.pos_info_pub.publish(center)
            
        annotated_frame = results[0].plot()
        annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)
        cv2.imshow("YOLO Inference", cv2.resize(annotated_frame, (640, 480)))
        key = cv2.waitKey(1)

    def GraspStatusCallback(self,msg):
        print("**")
        if msg.data == True:
            self.pubPos_flag = True


def main(args=None):
    rclpy.init(args=args)
    tag_detect = AprilTagDetectNode()
    try:    
        rclpy.spin(tag_detect)
    except KeyboardInterrupt:
        pass
    finally:
        tag_detect.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

  












