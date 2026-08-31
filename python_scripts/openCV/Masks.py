import cv2
import os   
print(cv2.__version__)

dispW=320
dispH=240
flip=2

path = os.path.join(os.path.dirname(__file__), '..', 'images', 'cv.jpg')
cv2logo = cv2.imread(path)
cv2logo = cv2.resize(cv2logo, (dispW, dispH))
cv2gray = cv2.cvtColor(cv2logo, cv2.COLOR_BGR2GRAY)
cv2.imshow('CV LOGO', cv2logo)
cv2.moveWindow('CV LOGO', 0, 500)
cv2.imshow('CV GRAY', cv2gray)
cv2.moveWindow('CV GRAY', 320, 500)

# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

while True:
    ret, frame=cam.read()
    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()