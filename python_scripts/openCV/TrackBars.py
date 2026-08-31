import cv2
print(cv2.__version__)

dispW=640
dispH=480
flip=2

# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

cv2.namedWindow('WEBCAM')
cv2.createTrackbar('cX', 'WEBCAM', 0, dispW, lambda x: None)
cv2.createTrackbar('cY', 'WEBCAM', 0, dispH, lambda x: None)
cv2.createTrackbar('width', 'WEBCAM', 0, dispW, lambda x: None)
cv2.createTrackbar('height', 'WEBCAM', 0, dispH, lambda x: None)


while True:
    ret, frame=cam.read()

    cX = cv2.getTrackbarPos('cX', 'WEBCAM')
    cY = cv2.getTrackbarPos('cY', 'WEBCAM')
    width = cv2.getTrackbarPos('width', 'WEBCAM')
    height = cv2.getTrackbarPos('height', 'WEBCAM')

    cv2.rectangle(frame, (cX-width//2, cY-height//2), (cX+width//2, cY+height//2), (0, 255, 0), 2)
    
    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()