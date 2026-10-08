from threading import Thread
import cv2
import time
import numpy as np

# Need this class with threading to get the frames of both cams in sync
class vStream:
    def __init__(self,src, width, height):
        self.width = width
        self.height = height
        self.capture = cv2.VideoCapture(src)
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while True:
            _, self.frame = self.capture.read()
            self.frame_res = cv2.resize(self.frame, (self.width, self.height))

    def getFrame(self):
        return self.frame_res

# For Pi camera, use the following line:
dispW = 640
dispH = 480
flip = 2
camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'

cam1 = vStream(camSet, dispW, dispH)
cam2 = vStream(1, dispW, dispH)

startTime = time.time()
dt_av = 0

font = cv2.FONT_HERSHEY_SIMPLEX

while True:
    try:
        myFrame1 = cam1.getFrame()
        myFrame2 = cam2.getFrame()
        myFrame3 = np.hstack((myFrame1, myFrame2))

        dt = time.time() - startTime
        dt_av = 0.9*dt_av + 0.1*dt
        fps = 1/dt_av
        startTime = time.time()
        cv2.rectangle(myFrame3, (0,0), (100,40), (255,255,255), -1)
        cv2.putText(myFrame3, str(round(fps,2))+'fps', (5,25), font, .75, (0,0,0))

        cv2.imshow('ComboCam', myFrame3)
        cv2.moveWindow('ComboCam', 0, 0)


    except:
        print('Frame not available')

    if cv2.waitKey(1)==ord('q'):
        cam1.capture.release()
        cam2.capture.release()
        cv2.destroyAllWindows()
        exit(1)
        break

