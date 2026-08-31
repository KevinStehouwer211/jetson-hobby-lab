import cv2
print(cv2.__version__)

def click(event, x, y, flags, param):
    global evt, pnt, start_pnt, end_pnt
    # EVENT_LBUTTONDOWN gives event value of 1.
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Mouse clicked at: ({x}, {y})")
        start_pnt=(x, y)
        evt=event
        print(evt)
    # EVENT_LBUTTONUP gives event value of 4.
    if event == cv2.EVENT_LBUTTONUP:
        print(f"Mouse released at: ({x}, {y})")
        end_pnt=(x, y)
        evt=event
        print(evt)

dispW=640
dispH=480
flip=2

start_pnt=None
end_pnt=None
toggle = False
evt=-1

# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

cv2.namedWindow('WEBCAM')
cv2.setMouseCallback('WEBCAM', click)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

while True:
    ret, frame=cam.read()

    # If the mouse button is released, draw a rectangle and show the ROI
    if evt == 4:
        cv2.rectangle(frame, start_pnt, end_pnt, (255, 0, 0), 2)
        roi = frame[start_pnt[1]:end_pnt[1], start_pnt[0]:end_pnt[0]].copy()
        cv2.imshow('ROI', roi)
        cv2.moveWindow('ROI', 640, 0)

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)

    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()