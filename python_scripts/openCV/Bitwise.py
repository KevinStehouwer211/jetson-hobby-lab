import cv2
print(cv2.__version__)
import numpy as np

dispW=640
dispH=480
flip=2

# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

# top half of the image is white, bottom half is black
img1 = np.zeros((dispH, dispW), np.uint8)
img1[:dispH//2, :] = 255

# left half of the image is white, right half is black
img2 = np.zeros((dispH, dispW), np.uint8)
img2[:, :dispW//2] = 255

# Where both images are white
bitAnd = cv2.bitwise_and(img1, img2)

# Where either image is white
bitOr = cv2.bitwise_or(img1, img2)

# Where one image is white and the other is black
bitXor = cv2.bitwise_xor(img1, img2)

while True:
    ret, frame=cam.read()
    cv2.imshow('Image 1', img1)
    cv2.moveWindow('Image 1', 0, 0)
    cv2.imshow('Image 2', img2)
    cv2.moveWindow('Image 2', 0, 500)
    cv2.imshow('Bitwise AND', bitAnd)
    cv2.moveWindow('Bitwise AND', 500, 0)
    cv2.imshow('Bitwise OR', bitOr)
    cv2.moveWindow('Bitwise OR', 500, 500)
    cv2.imshow('Bitwise XOR', bitXor)
    cv2.moveWindow('Bitwise XOR', 1000, 0)

    frame = cv2.bitwise_and(frame, frame, mask=bitXor)
    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 1000, 500)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()