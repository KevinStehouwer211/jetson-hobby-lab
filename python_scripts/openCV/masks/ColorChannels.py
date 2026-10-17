import cv2
print(cv2.__version__)
import numpy as np

dispW=640
dispH=480
flip=2

# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

blank = np.zeros([dispH, dispW, 1], dtype=np.uint8)
blank[:]=0

while True:
    ret, frame=cam.read()
    b, g, r = cv2.split(frame)

    blue = cv2.merge((b, blank, blank))
    green = cv2.merge((blank, g, blank))
    red = cv2.merge((blank, blank, r))

    # Change the color channels
    merged = cv2.merge((r, b, g))

    cv2.imshow('B', blue)
    cv2.moveWindow('B', 700, 0)
    cv2.imshow('G', green)
    cv2.moveWindow('G', 700, 960)
    cv2.imshow('R', red)
    cv2.moveWindow('R', 0, 960)
    cv2.imshow('Merged', merged)
    cv2.moveWindow('Merged', 1600, 0)
    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)

    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()