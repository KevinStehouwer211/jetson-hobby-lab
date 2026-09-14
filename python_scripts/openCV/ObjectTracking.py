import cv2
print(cv2.__version__)
import os
import numpy as np

cv2.namedWindow('Trackbars')
cv2.moveWindow('Trackbars', 800, 0)
cv2.createTrackbar('HUE lower', 'Trackbars', 50, 179, lambda x: None)
cv2.createTrackbar('HUE upper', 'Trackbars', 100, 179, lambda x: None)
cv2.createTrackbar('HUE2 lower', 'Trackbars', 50, 179, lambda x: None)
cv2.createTrackbar('HUE2 upper', 'Trackbars', 100, 179, lambda x: None)
cv2.createTrackbar('SAT lower', 'Trackbars', 100, 255, lambda x: None)
cv2.createTrackbar('SAT upper', 'Trackbars', 255, 255, lambda x: None)
cv2.createTrackbar('VALUE lower', 'Trackbars', 100, 255, lambda x: None)
cv2.createTrackbar('VALUE upper', 'Trackbars', 255, 255, lambda x: None)


# Load the logo image and create masks
path = os.path.join(os.path.dirname(__file__), '..', 'images', 'smarties.png')
frame = cv2.imread(path)

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

    # For the second range of HUE values, create a separate lower and upper bound (for red color)
    lb2 = np.array([h2_lower, s_lower, v_lower])
    ub2 = np.array([h2_upper, s_upper, v_upper])

    # 2 FG masks are created for the two ranges of HUE values, and then combined using cv2.add() 
    # to create a single mask that captures both ranges. 
    # This is useful for colors like red that wrap around the HUE spectrum.
    FG_mask = cv2.inRange(hsv, lb, ub)
    FG_mask2 = cv2.inRange(hsv, lb2, ub2)
    FG_maskComp = cv2.add(FG_mask, FG_mask2)
    cv2.imshow('FG_MASKCOMP', FG_maskComp)
    cv2.moveWindow('FG_MASKCOMP', 1320, 0)

    # find contours of our mask (mask, external contours, simple approximation)
    contours, _ = cv2.findContours(FG_maskComp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # sort contours by area and keep the largest one (contours, lambda function, reverse order)
    contours = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=True)

    # Draw all contours greater than 50 pixels.
    for cnt in contours:
        area = cv2.contourArea(cnt)
        (x,y,w,h) = cv2.boundingRect(cnt)
        if area > 50:

            # draw contours on the original frame (frame, contours, contour index (-1 for all), color, thickness)
            cv2.drawContours(frame, [cnt], 0, (255, 0, 0), 3)

            # Draw boundingbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Draw center lines
            cv2.line(frame, (x + int(w/2), 0), (x + int(w/2), dispH), (0, 255, 0), 1)
            cv2.line(frame, (0, y + int(h/2)), (dispW, y + int(h/2)), (0, 255, 0), 1)


    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()