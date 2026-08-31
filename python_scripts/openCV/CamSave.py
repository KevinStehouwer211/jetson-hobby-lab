import cv2
print(cv2.__version__)

dispW=320
dispH=240
flip=2

# For Pi camera, use the following lines:
# camSet='nvarguscamerasrc !  video/x-raw(memvory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following lines:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, dispW)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, dispH)
cam.set(cv2.CAP_PROP_FPS, 30)

outVideo = cv2.VideoWriter('python_scripts/saved_vids/output.avi', cv2.VideoWriter_fourcc(*'MJPG'), 30, (int(cam.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))))

while True:
    ret, frame=cam.read()
    # Write the frame to the output video file
    outVideo.write(frame)

    # Use this when there is a monitor attached to the Jetson.
    cv2.imshow('WEBCAM', frame)
    if cv2.waitKey(1)==ord('q'):
        break

outVideo.release()
cam.release()
cv2.destroyAllWindows()