import cv2
print(cv2.__version__)

def click(event, x, y, flags, param):
    global evt
    global coords
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Mouse clicked at: ({x}, {y})")
        pnt=(x, y)
        coords.append(pnt)
        evt=event

dispW=640
dispH=480
flip=2

coords=[]
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
    for pnt in coords:
        cv2.circle(frame, pnt, 5, (0, 0, 255), -1)
        if pnt[0] > dispW-100:
            cv2.putText(frame, f"({pnt[0]}, {pnt[1]})", (pnt[0]-90, pnt[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        else:
            cv2.putText(frame, f"({pnt[0]}, {pnt[1]})", (pnt[0]+10, pnt[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)

    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()