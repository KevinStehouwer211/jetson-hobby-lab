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

while True:
    ret, frame=cam.read()
    # (frame , start_point, end_point, color, thickness)
    frame = cv2.rectangle(frame, (100, 100), (270, 270), (0, 255, 0), -1)
    # (frame, center_coordinates, radius, color, thickness)
    frame = cv2.circle(frame, (200, 200), 50, (255, 0, 0), -1)

    font = cv2.FONT_HERSHEY_SIMPLEX
    # (frame, text, position, font, fontScale, color, thickness, lineType)
    frame = cv2.putText(frame, 'Hello, OpenCV!', (100, 50), font, 1, (0, 0, 255), 3, cv2.LINE_AA)

    # (frame, start_point, end_point, color, thickness)
    frame = cv2.line(frame, (0, 0), (dispW, dispH), (255, 255, 0), 5)
    frame = cv2.arrowedLine(frame, (dispW, 0), (10, dispH-10), (255, 0, 255), 5)

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)

    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()