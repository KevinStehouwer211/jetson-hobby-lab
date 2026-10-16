import cv2
from ultralytics import YOLO
from Arm_Lib import Arm_Device
from grasp_node import GraspNode
import rclpy
import time
from Speech_Lib import Speech
rclpy.init()
Arm = Arm_Device()
init_joints = [90.0, 120.0, 0.0, 0.0, 90.0, 0.0]
Arm.Arm_serial_servo_write6_array(init_joints,2000)
mySpeech = Speech()
# Load the YOLO model
model = YOLO("/root/ultralytics/ultralytics/best.onnx")


grasp = GraspNode()
# Open the cammera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Get the video frame size and frame rate
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define the codec and create a VideoWriter object to output the processed video

recyclable_waste=['Newspaper','Zip_top_can','Book','Old_school_bag']
toxic_waste=['Syringe','Expired_cosmetics','Used_batteries','Expired_tablets']
wet_waste=['Fish_bone','Egg_shell','Apple_core','Watermelon_rind']
dry_waste=['Toilet_paper','Peach_pit','Cigarette_butts','Disposable_chopsticks']



# Loop through the video frames
while cap.isOpened():
    # Read a frame from the video
    success, frame = cap.read()
    
    if success:
        # Run YOLO inference on the frame
        result = mySpeech.speech_read()
        results = model(frame)
        boxes = results[0].boxes
        annotated_frame = results[0].plot()
        cv2.imshow("YOLO Inference", cv2.resize(annotated_frame, (640, 480)))
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        if result == 94:
            grasp.done = True
        if boxes != [None] and grasp.done == True:
            for box in boxes:   
                class_id = int(box.cls)
                label = model.names[class_id]
                print("label: ",label)
                if label == 'Newspaper':
                    mySpeech.void_write(96)
                elif label == 'Zip_top_can':
                    mySpeech.void_write(94)
                elif label == 'Book':
                    mySpeech.void_write(97)
                elif label == 'Old_school_bag':
                    mySpeech.void_write(95)
                elif label == 'Syringe':
                    mySpeech.void_write(98)
                elif label == 'Expired_cosmetics':
                    mySpeech.void_write(100)
                elif label == 'Used_batteries':
                    mySpeech.void_write(99)
                elif label == 'Expired_tablets':
                    mySpeech.void_write(101)
                elif label == 'Fish_bone':
                    mySpeech.void_write(102)
                elif label == 'Egg_shell':
                    mySpeech.void_write(105)
                elif label == 'Apple_core':
                    mySpeech.void_write(104)
                elif label == 'Watermelon_rind':
                    mySpeech.void_write(103)
                elif label == 'Toilet_paper':
                    mySpeech.void_write(109)
                elif label == 'Peach_pit':
                    mySpeech.void_write(108)
                elif label == 'Cigarette_butts':
                    mySpeech.void_write(107)
                elif label == 'Disposable_chopsticks':
                    mySpeech.void_write(106)
                if label in recyclable_waste:
                    cls = 1
                elif label in toxic_waste:
                    cls = 2
                elif label in wet_waste:
                    cls = 3
                elif label in dry_waste:
                    cls = 4
                x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
                center_x = (x_min + x_max) // 2
                center_y = (y_min + y_max) // 2
                (a, b) = (round(((320 - center_x) / 4000), 5), round(((480 - center_y) / 3000) * 0.8+0.15, 5))
                grasp.done = False
                grasp.grasp_xy(b,a,cls)
                init_joints = [90.0, 120.0, 0.0, 0.0, 90.0, 0.0]
                Arm.Arm_serial_servo_write6_array(init_joints,2000)
                time.sleep(2.0)
                mySpeech.void_write(81)
                time.sleep(2.0)

    else:
        break
# Release the video capture and writer objects, and close the display window
cap.release()

cv2.destroyAllWindows()
