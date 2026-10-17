import cv2
import os   
print(cv2.__version__)

dispW=320
dispH=240
flip=2

# Create window and trackbar for opacity of the watermark image
cv2.namedWindow('BLENDED')
cv2.createTrackbar('BlendValue', 'BLENDED', 50, 100, lambda x: None)

path = os.path.join(os.path.dirname(__file__), '..', 'images', 'cv.jpg')
cv2logo = cv2.imread(path)
cv2logo = cv2.resize(cv2logo, (dispW, dispH))
cv2gray = cv2.cvtColor(cv2logo, cv2.COLOR_BGR2GRAY)
#cv2.imshow('CV LOGO', cv2logo)
#cv2.moveWindow('CV LOGO', 0, 500)
#cv2.imshow('CV GRAY', cv2gray)
#cv2.moveWindow('CV GRAY', 320, 500)



# 225 or above is white, below 225 is black
_, BGMask = cv2.threshold(cv2gray, 225, 255, cv2.THRESH_BINARY)
cv2.imshow('BG Mask', BGMask)
cv2.moveWindow('BG Mask', 640, 500)

FGMask = cv2.bitwise_not(BGMask)
cv2.imshow('FG Mask', FGMask)
cv2.moveWindow('FG Mask', 960, 500)

FG = cv2.bitwise_and(cv2logo, cv2logo, mask=FGMask)
cv2.imshow('FG', FG)
cv2.moveWindow('FG', 640, 0)

# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

while True:
    ret, frame=cam.read()
    frame = cv2.resize(frame, (dispW, dispH))

    # Background is the webcam image where the logo is not present
    BG = cv2.bitwise_and(frame, frame, mask=BGMask)
    cv2.imshow('BG', BG)
    cv2.moveWindow('BG', 320, 0)

    # Complementary image is the combination of the background and foreground images
    compImage = cv2.add(BG, FG)
    cv2.imshow('COMP IMAGE', compImage)
    cv2.moveWindow('COMP IMAGE', 0, 500)

    # Blend the webcam image and the logo image based on the trackbar value
    BV1 = cv2.getTrackbarPos('BlendValue', 'BLENDED')/100
    BV2 = 1-BV1
    blended = cv2.addWeighted(frame, BV1, cv2logo, BV2, 0)
    cv2.imshow('BLENDED', blended)
    cv2.moveWindow('BLENDED', 320, 500)

    # Foreground is the blended image where the logo is present
    FG2 = cv2.bitwise_and(blended, blended, mask=FGMask)
    cv2.imshow('FG2', FG2)
    cv2.moveWindow('FG2', 640, 0)

    # Complementary final is the combination of the background and blended foreground image
    compFinal = cv2.add(BG, FG2)
    cv2.imshow('COMP FINAL', compFinal)
    cv2.moveWindow('COMP FINAL', 960, 0)

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)
    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()