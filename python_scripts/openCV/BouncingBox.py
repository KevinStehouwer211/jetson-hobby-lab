import cv2
print(cv2.__version__)

dispW=640
dispH=480
flip=2

# Size of the rectangle
width = 150
height = 150

# Center of the rectangle
cX = width // 2
cY = height // 2

# Change in position of the rectangle
dX = 5
dY = 5

# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

while True:
    ret, frame=cam.read()
    # (frame , start_point, end_point, color, thickness)
    frame = cv2.rectangle(frame, (cX-(width//2), cY-(height//2)), (cX + (width//2), cY + (height//2)), (0, 255, 0), -1)

    # Shift the rectangle's position
    cX += dX
    cY += dY

    # Bounce the rectangle off the edges of the frame
    if cX < (width//2) or cX > (dispW - (width//2)):
        dX = -dX
    if cY < (height//2) or cY > (dispH - (height//2)):
        dY = -dY

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)

    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()