import cv2
from ultralytics import YOLO
from Arm_Lib import Arm_Device
Arm = Arm_Device()
init_joints = [90.0, 120.0, 0.0, 0.0, 90.0, 0.0]
Arm.Arm_serial_servo_write6_array(init_joints,2000)

# Load the YOLO model
model = YOLO("/root/ultralytics/ultralytics/best.onnx")

# Open the cammera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Get the video frame size and frame rate
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define the codec and create a VideoWriter object to output the processed video



# Loop through the video frames
while cap.isOpened():
    # Read a frame from the video
    success, frame = cap.read()

    if success:
        # Run YOLO inference on the frame
        results = model(frame)
        boxes = results[0].boxes
        if boxes != [None]:
            for box in boxes:
                class_id = int(box.cls)
                label = model.names[class_id]
                print("label: ",label)
                
            
        

        # Visualize the results on the frame
        annotated_frame = results[0].plot()



        # Display the annotated frame
        cv2.imshow("YOLO Inference", cv2.resize(annotated_frame, (640, 480)))

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        # Break the loop if the end of the video is reached
        break
# Release the video capture and writer objects, and close the display window
cap.release()

cv2.destroyAllWindows()
