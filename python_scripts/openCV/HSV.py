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
    #ret, frame=cam.read()
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

    FG = cv2.bitwise_and(frame, frame, mask=FG_maskComp)
    cv2.imshow('FG', FG)
    cv2.moveWindow('FG', 1320, 1000)

    BG_mask = cv2.bitwise_not(FG_mask)
    cv2.imshow('BG_mask', BG_mask)
    cv2.moveWindow('BG_mask', 650, 1000)

    BG = cv2.cvtColor(BG_mask, cv2.COLOR_GRAY2BGR)

    final = cv2.add(BG, FG)
    cv2.imshow('FINAL', final)
    cv2.moveWindow('FINAL', 0, 1000)

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()