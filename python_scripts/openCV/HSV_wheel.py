import cv2
import os
import numpy as np

dispW=320
dispH=240

cv2.namedWindow('HSV_wheel')
cv2.moveWindow('HSV_wheel', 0, 0)
cv2.createTrackbar('HUE lower', 'HSV_wheel', 0, 179, lambda x: None)
cv2.createTrackbar('HUE upper', 'HSV_wheel', 179, 179, lambda x: None)
cv2.createTrackbar('HUE2 lower', 'HSV_wheel', 179, 179, lambda x: None)
cv2.createTrackbar('HUE2 upper', 'HSV_wheel', 179, 179, lambda x: None)
cv2.createTrackbar('SAT lower', 'HSV_wheel', 0, 255, lambda x: None)
cv2.createTrackbar('SAT upper', 'HSV_wheel', 255, 255, lambda x: None)
cv2.createTrackbar('VALUE lower', 'HSV_wheel', 0, 255, lambda x: None)
cv2.createTrackbar('VALUE upper', 'HSV_wheel', 255, 255, lambda x: None)

path = os.path.join(os.path.dirname(__file__), '..', 'images', 'HSV.jpeg')
img = cv2.imread(path)
img = cv2.resize(img, (dispW, dispH))

img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


while True:
    h_lower = cv2.getTrackbarPos('HUE lower', 'HSV_wheel')
    h_upper = cv2.getTrackbarPos('HUE upper', 'HSV_wheel')
    h2_lower = cv2.getTrackbarPos('HUE2 lower', 'HSV_wheel')
    h2_upper = cv2.getTrackbarPos('HUE2 upper', 'HSV_wheel')
    s_lower = cv2.getTrackbarPos('SAT lower', 'HSV_wheel')
    s_upper = cv2.getTrackbarPos('SAT upper', 'HSV_wheel')
    v_lower = cv2.getTrackbarPos('VALUE lower', 'HSV_wheel')
    v_upper = cv2.getTrackbarPos('VALUE upper', 'HSV_wheel')

    lb = np.array([h_lower, s_lower, v_lower])
    ub = np.array([h_upper, s_upper, v_upper])
    lb2 = np.array([h2_lower, s_lower, v_lower])
    ub2 = np.array([h2_upper, s_upper, v_upper])

    FG_mask = cv2.inRange(img_hsv, lb, ub)
    FG_mask2 = cv2.inRange(img_hsv, lb2, ub2)
    FG_maskComp = cv2.add(FG_mask, FG_mask2)
    FG = cv2.bitwise_and(img, img, mask=FG_maskComp)

    BG_mask = cv2.bitwise_not(FG_maskComp)
    BG = cv2.bitwise_and(img, img, mask=BG_mask)

    Comp = cv2.add(FG, BG)

    cv2.imshow('HSV_wheel', img)

    cv2.imshow('FG', FG)
    cv2.imshow('BG', BG)
    cv2.imshow('Comp', Comp)
    cv2.moveWindow('FG', 700, 0)
    cv2.moveWindow('BG', 1020, 0)
    cv2.moveWindow('Comp', 1340, 0)

    if cv2.waitKey(1) == ord('q'):
        break

cv2.destroyAllWindows()