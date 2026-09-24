import cv2
print(cv2.__version__)
import os
import numpy as np

exit_program = False

def mouse_callback(event, x, y, flags, param):
    global exit_program
    if event == cv2.EVENT_LBUTTONDOWN and 10 <= x <= 130 and 10 <= y <= 65:
        exit_program = True

cv2.namedWindow('Trackbars')
cv2.moveWindow('Trackbars', 800, 0)
# Focus on blue objects, so we will use HUE values around 100-130
cv2.createTrackbar('HUE lower', 'Trackbars', 80, 179, lambda x: None)
cv2.createTrackbar('HUE upper', 'Trackbars', 120, 179, lambda x: None)
cv2.createTrackbar('HUE2 lower', 'Trackbars', 179, 179, lambda x: None)
cv2.createTrackbar('HUE2 upper', 'Trackbars', 179, 179, lambda x: None)
cv2.createTrackbar('SAT lower', 'Trackbars', 130, 255, lambda x: None)
cv2.createTrackbar('SAT upper', 'Trackbars', 255, 255, lambda x: None)
cv2.createTrackbar('VALUE lower', 'Trackbars', 70, 255, lambda x: None)
cv2.createTrackbar('VALUE upper', 'Trackbars', 140, 255, lambda x: None)

path = os.path.join(os.path.dirname(__file__), '..', 'images', 'smarties.png')
frame = cv2.imread(path)

dispW = 320
dispH = 240
flip = 2

# camSet='nvarguscamerasrc ! video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
# cam = cv2.VideoCapture(camSet)

cam = cv2.VideoCapture(0, cv2.CAP_V4L2)

cv2.namedWindow('WEBCAM', cv2.WINDOW_NORMAL)
cv2.setMouseCallback('WEBCAM', mouse_callback)

cv2.namedWindow('FG_MASKCOMP', cv2.WINDOW_NORMAL)

while True:
    ret, frame = cam.read()
    frame = cv2.resize(frame, (dispW, dispH))

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    h_lower = cv2.getTrackbarPos('HUE lower', 'Trackbars')
    h_upper = cv2.getTrackbarPos('HUE upper', 'Trackbars')
    h2_lower = cv2.getTrackbarPos('HUE2 lower', 'Trackbars')
    h2_upper = cv2.getTrackbarPos('HUE2 upper', 'Trackbars')
    s_lower = cv2.getTrackbarPos('SAT lower', 'Trackbars')
    s_upper = cv2.getTrackbarPos('SAT upper', 'Trackbars')
    v_lower = cv2.getTrackbarPos('VALUE lower', 'Trackbars')
    v_upper = cv2.getTrackbarPos('VALUE upper', 'Trackbars')

    lb = np.array([h_lower, s_lower, v_lower])
    ub = np.array([h_upper, s_upper, v_upper])
    lb2 = np.array([h2_lower, s_lower, v_lower])
    ub2 = np.array([h2_upper, s_upper, v_upper])

    FG_mask = cv2.inRange(hsv, lb, ub)
    FG_mask2 = cv2.inRange(hsv, lb2, ub2)
    FG_maskComp = cv2.add(FG_mask, FG_mask2)
    FG_MaskComp = cv2.resize(FG_maskComp, (dispW, dispH))

    cv2.imshow('FG_MASKCOMP', FG_maskComp)
    cv2.moveWindow('FG_MASKCOMP', 0, 300)

    contours, _ = cv2.findContours(FG_maskComp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)

        if area > 50:
            cv2.drawContours(frame, [cnt], 0, (255, 0, 0), 3)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.line(frame, (x + int(w / 2), 0), (x + int(w / 2), dispH), (0, 255, 0), 1)
            cv2.line(frame, (0, y + int(h / 2)), (dispW, y + int(h / 2)), (0, 255, 0), 1)

    cv2.rectangle(frame, (10, 10), (130, 65), (0, 0, 255), -1)
    cv2.rectangle(frame, (10, 10), (130, 65), (255, 255, 255), 2)
    cv2.putText(frame, 'EXIT', (28, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or exit_program:
        break

cam.release()
cv2.destroyAllWindows()